"""
API Authentication for ag3ntwerk.

Provides JWT-based authentication and API key authentication
for securing API endpoints.
"""

import asyncio
import hashlib
import hmac
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from functools import wraps

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)


class AuthMethod(Enum):
    """Supported authentication methods."""

    API_KEY = "api_key"
    JWT = "jwt"
    BASIC = "basic"
    NONE = "none"


class Permission(Enum):
    """API permissions."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    EXECUTE_TASK = "execute_task"
    EXECUTE_WORKFLOW = "execute_workflow"
    MANAGE_AGENTS = "manage_agents"
    VIEW_METRICS = "view_metrics"
    MANAGE_CONFIG = "manage_config"


@dataclass
class APIKey:
    """Represents an API key."""

    key_id: str
    name: str
    hashed_key: str
    permissions: Set[Permission] = field(default_factory=lambda: {Permission.READ})
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    use_count: int = 0
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def has_permission(self, permission: Permission) -> bool:
        """Check if key has a specific permission."""
        if Permission.ADMIN in self.permissions:
            return True
        return permission in self.permissions


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user/client."""

    user_id: str
    auth_method: AuthMethod
    permissions: Set[Permission]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        if Permission.ADMIN in self.permissions:
            return True
        return permission in self.permissions


class APIKeyManager:
    """
    Manages API keys for authentication.

    Features:
    - Secure key generation and hashing
    - Key validation with rate limiting
    - Permission management
    - Key lifecycle management

    Usage:
        manager = APIKeyManager()

        # Create a new key
        key_id, raw_key = manager.create_key(
            name="Production App",
            permissions={Permission.READ, Permission.EXECUTE_TASK},
            expires_in_days=365,
        )
        print(f"Save this key: {raw_key}")

        # Validate a key
        api_key = manager.validate_key(raw_key)
        if api_key:
            print(f"Valid key: {api_key.name}")
    """

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize API key manager.

        Args:
            secret_key: Secret for key hashing (from env if not provided)
        """
        env_secret = os.environ.get("AGENTWERK_API_SECRET")
        if secret_key:
            self._secret_key = secret_key
        elif env_secret:
            self._secret_key = env_secret
        else:
            # Check if we're in production — ephemeral secrets are not safe there
            _env = os.environ.get(
                "AGENTWERK_ENV", os.environ.get("ENVIRONMENT", "development")
            ).lower()
            if _env == "production":
                raise RuntimeError(
                    "AGENTWERK_API_SECRET environment variable is required in production. "
                    "API key authentication cannot use ephemeral secrets."
                )
            self._secret_key = secrets.token_hex(32)
            logger.warning(
                "AGENTWERK_API_SECRET not set — using ephemeral secret key. "
                "API keys will not persist across restarts. "
                "Set AGENTWERK_API_SECRET for production use."
            )
        self._keys: Dict[str, APIKey] = {}
        self._key_hash_index: Dict[str, str] = {}  # hashed_key -> key_id

    def _hash_key(self, raw_key: str) -> str:
        """Hash an API key for storage."""
        return hmac.new(self._secret_key.encode(), raw_key.encode(), hashlib.sha256).hexdigest()

    def create_key(
        self,
        name: str,
        permissions: Optional[Set[Permission]] = None,
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, str]:
        """
        Create a new API key.

        Args:
            name: Name/description for the key
            permissions: Set of permissions to grant
            expires_in_days: Days until expiration (None = never)
            metadata: Additional metadata

        Returns:
            Tuple of (key_id, raw_key). Save raw_key securely - it cannot be retrieved!
        """
        # Generate key
        key_id = f"csk_{secrets.token_hex(8)}"  # ag3ntwerk key
        raw_key = f"cskey_{secrets.token_urlsafe(32)}"

        # Hash for storage
        hashed_key = self._hash_key(raw_key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        # Create key record
        api_key = APIKey(
            key_id=key_id,
            name=name,
            hashed_key=hashed_key,
            permissions=permissions or {Permission.READ},
            expires_at=expires_at,
            metadata=metadata or {},
        )

        # Store
        self._keys[key_id] = api_key
        self._key_hash_index[hashed_key] = key_id

        logger.info(
            f"API key created: {key_id}",
            extra={"key_name": name, "permissions": [p.value for p in api_key.permissions]},
        )

        return key_id, raw_key

    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """
        Validate an API key.

        Args:
            raw_key: The raw API key to validate

        Returns:
            APIKey if valid, None otherwise
        """
        if not raw_key or not raw_key.startswith("cskey_"):
            return None

        hashed = self._hash_key(raw_key)
        # Use constant-time comparison to prevent timing attacks
        key_id = None
        for stored_hash, stored_id in self._key_hash_index.items():
            if hmac.compare_digest(stored_hash, hashed):
                key_id = stored_id
                break

        if not key_id:
            return None

        api_key = self._keys.get(key_id)
        if not api_key:
            return None

        # Check if active and not expired
        if not api_key.active:
            logger.warning(f"Inactive API key used: {key_id}")
            return None

        if api_key.is_expired:
            logger.warning(f"Expired API key used: {key_id}")
            return None

        # Update usage tracking
        api_key.last_used = datetime.now(timezone.utc)
        api_key.use_count += 1

        return api_key

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if key_id not in self._keys:
            return False

        api_key = self._keys[key_id]
        api_key.active = False

        logger.info(f"API key revoked: {key_id}")
        return True

    def list_keys(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """List all API keys (without secrets)."""
        keys = []
        for api_key in self._keys.values():
            if not include_inactive and not api_key.active:
                continue
            keys.append(
                {
                    "key_id": api_key.key_id,
                    "name": api_key.name,
                    "permissions": [p.value for p in api_key.permissions],
                    "created_at": api_key.created_at.isoformat(),
                    "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
                    "last_used": api_key.last_used.isoformat() if api_key.last_used else None,
                    "use_count": api_key.use_count,
                    "active": api_key.active,
                }
            )
        return keys

    def get_key(self, key_id: str) -> Optional[APIKey]:
        """Get an API key by ID."""
        return self._keys.get(key_id)


class JWTManager:
    """
    JWT token management for authentication.

    Note: This is a simplified implementation. For production,
    use a proper JWT library like PyJWT.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
    ):
        """
        Initialize JWT manager.

        Args:
            secret_key: Secret for signing tokens
            algorithm: Signing algorithm
            access_token_expire_minutes: Token expiration time
        """
        env_secret = os.environ.get("AGENTWERK_JWT_SECRET")
        if secret_key:
            self._secret_key = secret_key
        elif env_secret:
            self._secret_key = env_secret
        else:
            _env = os.environ.get(
                "AGENTWERK_ENV", os.environ.get("ENVIRONMENT", "development")
            ).lower()
            if _env == "production":
                raise RuntimeError(
                    "AGENTWERK_JWT_SECRET environment variable is required in production. "
                    "JWT authentication cannot use ephemeral secrets."
                )
            self._secret_key = secrets.token_hex(32)
            logger.warning(
                "AGENTWERK_JWT_SECRET not set — using ephemeral secret key. "
                "JWT tokens will not persist across restarts. "
                "Set AGENTWERK_JWT_SECRET for production use."
            )
        self._algorithm = algorithm
        self._expire_minutes = access_token_expire_minutes

    def create_token(
        self,
        user_id: str,
        permissions: Set[Permission],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a JWT token."""
        from auth_core.jwt import create_token as _create

        return _create(
            subject=user_id,
            secret=self._secret_key,
            algorithm=self._algorithm,
            expire_minutes=self._expire_minutes,
            extra_claims={
                "permissions": [p.value for p in permissions],
                "metadata": metadata or {},
            },
        )

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a JWT token and return payload."""
        try:
            from auth_core.jwt import verify_token as _verify

            return _verify(token, self._secret_key, algorithms=[self._algorithm])
        except ValueError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None


# FastAPI Security Schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


# Global instances (double-checked locking)
_api_key_manager: Optional[APIKeyManager] = None
_api_key_manager_lock = asyncio.Lock()
_jwt_manager: Optional[JWTManager] = None
_jwt_manager_lock = asyncio.Lock()


def get_api_key_manager() -> APIKeyManager:
    """Get the global API key manager (sync fast-path)."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager


async def _get_api_key_manager_async() -> APIKeyManager:
    """Get the global API key manager with async lock."""
    global _api_key_manager
    if _api_key_manager is None:
        async with _api_key_manager_lock:
            if _api_key_manager is None:
                _api_key_manager = APIKeyManager()
    return _api_key_manager


def get_jwt_manager() -> JWTManager:
    """Get the global JWT manager (sync fast-path)."""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


async def _get_jwt_manager_async() -> JWTManager:
    """Get the global JWT manager with async lock."""
    global _jwt_manager
    if _jwt_manager is None:
        async with _jwt_manager_lock:
            if _jwt_manager is None:
                _jwt_manager = JWTManager()
    return _jwt_manager


# FastAPI Dependencies


async def get_api_key(
    api_key: Optional[str] = Depends(api_key_header),
) -> Optional[APIKey]:
    """Extract and validate API key from request header."""
    if not api_key:
        return None

    manager = await _get_api_key_manager_async()
    return manager.validate_key(api_key)


async def get_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[Dict[str, Any]]:
    """Extract and validate JWT from Authorization header."""
    if not credentials:
        return None

    manager = await _get_jwt_manager_async()
    return manager.verify_token(credentials.credentials)


async def get_current_user(
    request: Request,
    api_key: Optional[APIKey] = Depends(get_api_key),
    jwt_payload: Optional[Dict[str, Any]] = Depends(get_bearer_token),
) -> Optional[AuthenticatedUser]:
    """
    Get the current authenticated user from request.

    Supports both API key and JWT authentication.
    """
    # Try API key first
    if api_key:
        return AuthenticatedUser(
            user_id=api_key.key_id,
            auth_method=AuthMethod.API_KEY,
            permissions=api_key.permissions,
            metadata=api_key.metadata,
        )

    # Try JWT
    if jwt_payload:
        permissions = {
            Permission(p)
            for p in jwt_payload.get("permissions", [])
            if p in [e.value for e in Permission]
        }
        return AuthenticatedUser(
            user_id=jwt_payload.get("sub", "unknown"),
            auth_method=AuthMethod.JWT,
            permissions=permissions,
            metadata=jwt_payload.get("metadata", {}),
        )

    return None


def require_auth(
    permissions: Optional[Set[Permission]] = None,
):
    """
    Dependency that requires authentication with optional permission check.

    Usage:
        @app.get("/protected")
        async def protected_endpoint(
            user: AuthenticatedUser = Depends(require_auth({Permission.READ}))
        ):
            return {"user_id": user.user_id}
    """
    permissions = permissions or set()

    async def dependency(
        user: Optional[AuthenticatedUser] = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check permissions
        for permission in permissions:
            if not user.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {permission.value}",
                )

        return user

    return dependency


def optional_auth():
    """
    Dependency that optionally extracts authenticated user.

    Returns None if not authenticated.
    """

    async def dependency(
        user: Optional[AuthenticatedUser] = Depends(get_current_user),
    ) -> Optional[AuthenticatedUser]:
        return user

    return dependency


# Rate Limiting by User
class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Max requests per minute
            burst_size: Max burst requests
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self._buckets: Dict[str, List[float]] = {}

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for a key."""
        now = time.time()
        window_start = now - 60  # 1 minute window

        # Get or create bucket
        if key not in self._buckets:
            self._buckets[key] = []

        # Clean old entries
        self._buckets[key] = [t for t in self._buckets[key] if t > window_start]

        # Check limit
        if len(self._buckets[key]) >= self.requests_per_minute:
            return False

        # Record request
        self._buckets[key].append(now)
        return True

    def get_remaining(self, key: str) -> int:
        """Get remaining requests for a key."""
        now = time.time()
        window_start = now - 60

        if key not in self._buckets:
            return self.requests_per_minute

        current = len([t for t in self._buckets[key] if t > window_start])

        return max(0, self.requests_per_minute - current)


# Global rate limiter
_rate_limiter = RateLimiter()


def check_rate_limit(user_id: str) -> bool:
    """Check rate limit for a user."""
    return _rate_limiter.is_allowed(user_id)


def get_rate_limit_remaining(user_id: str) -> int:
    """Get remaining requests for a user."""
    return _rate_limiter.get_remaining(user_id)
