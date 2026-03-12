"""JWT token creation and verification using PyJWT.

This is the single source of truth for JWT operations across all
ag3ntwerk services (ag3ntwerk, sentinel, nexus, forge).
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
from jwt.exceptions import InvalidTokenError


def create_token(
    subject: str,
    secret: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None,
    expire_minutes: int = 60,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a signed JWT token.

    Args:
        subject: The token subject (user or client ID).
        secret: Signing key.
        algorithm: JWT algorithm (default HS256).
        expires_delta: Custom expiration timedelta.
        expire_minutes: Fallback expiration in minutes if expires_delta is None.
        extra_claims: Additional claims merged into the payload.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=expire_minutes)
    expire = now + expires_delta

    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, secret, algorithm=algorithm)


def verify_token(
    token: str,
    secret: str,
    algorithms: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Verify a JWT token and return its payload.

    Args:
        token: Encoded JWT string.
        secret: Signing key.
        algorithms: Allowed algorithms (default ["HS256"]).

    Returns:
        Decoded payload dict.

    Raises:
        ValueError: If the token is invalid, expired, or tampered with.
    """
    if algorithms is None:
        algorithms = ["HS256"]

    try:
        return jwt.decode(token, secret, algorithms=algorithms)
    except InvalidTokenError as e:
        raise ValueError(f"Token verification failed: {e}") from e
