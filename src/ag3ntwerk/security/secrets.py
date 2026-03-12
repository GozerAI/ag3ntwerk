"""
Secrets management for ag3ntwerk.

Provides secure handling of sensitive configuration values,
API keys, and credentials with support for multiple backends.
"""

import base64
import hashlib
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class SecretBackend(Enum):
    """Supported secrets backends."""

    ENVIRONMENT = "environment"  # Environment variables
    FILE = "file"  # Encrypted file
    MEMORY = "memory"  # In-memory (for testing)


@dataclass
class SecretReference:
    """Reference to a secret value."""

    key: str
    backend: SecretBackend = SecretBackend.ENVIRONMENT
    env_var: Optional[str] = None  # Override env var name
    file_path: Optional[str] = None  # For file backend
    required: bool = True
    default: Optional[str] = None
    description: str = ""

    @property
    def resolved_env_var(self) -> str:
        """Get the environment variable name."""
        return self.env_var or self.key.upper().replace("-", "_").replace(".", "_")


@dataclass
class SecretMetadata:
    """Metadata about a secret."""

    key: str
    exists: bool
    backend: SecretBackend
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    masked_value: str = "***"  # For logging


class SecretsBackend(ABC):
    """Abstract base class for secrets backends."""

    @abstractmethod
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret value."""
        pass

    @abstractmethod
    def set(self, key: str, value: str) -> bool:
        """Set a secret value (if supported)."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a secret (if supported)."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a secret exists."""
        pass

    @abstractmethod
    def list_keys(self) -> List[str]:
        """List available secret keys."""
        pass


class EnvironmentSecretsBackend(SecretsBackend):
    """Secrets backend using environment variables."""

    def __init__(self, prefix: str = ""):
        """
        Initialize environment backend.

        Args:
            prefix: Prefix for environment variable names (e.g., "AGENTWERK_")
        """
        self.prefix = prefix

    def _env_key(self, key: str) -> str:
        """Convert key to environment variable name."""
        return self.prefix + key.upper().replace("-", "_").replace(".", "_")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from environment."""
        return os.environ.get(self._env_key(key), default)

    def set(self, key: str, value: str) -> bool:
        """Set environment variable (process-local only)."""
        os.environ[self._env_key(key)] = value
        return True

    def delete(self, key: str) -> bool:
        """Delete environment variable."""
        env_key = self._env_key(key)
        if env_key in os.environ:
            del os.environ[env_key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if environment variable exists."""
        return self._env_key(key) in os.environ

    def list_keys(self) -> List[str]:
        """List environment variables with prefix."""
        if not self.prefix:
            return []  # Too many to list without prefix
        return [
            k[len(self.prefix) :].lower().replace("_", "-")
            for k in os.environ
            if k.startswith(self.prefix)
        ]


class FileSecretsBackend(SecretsBackend):
    """
    Secrets backend using Fernet-encrypted file storage.

    Uses AES-128-CBC encryption with HMAC-SHA256 authentication
    via the cryptography library's Fernet implementation.
    """

    def __init__(
        self,
        file_path: str = "~/.ag3ntwerk/secrets.enc",
        encryption_key: Optional[str] = None,
    ):
        """
        Initialize file backend.

        Args:
            file_path: Path to encrypted secrets file
            encryption_key: Fernet key for encryption (from env if not provided)
        """
        self.file_path = Path(file_path).expanduser().resolve()
        self._encryption_key = encryption_key or os.environ.get("AGENTWERK_SECRETS_KEY")
        self._secrets: Dict[str, str] = {}
        self._loaded = False
        self._encryptor = None

    def _get_encryptor(self):
        """Get or create the encryption manager."""
        if self._encryptor is None:
            if not self._encryption_key:
                # Auto-generate and store key if not provided
                from ag3ntwerk.security.encryption import get_or_create_encryption_key

                self._encryption_key = get_or_create_encryption_key()

            from ag3ntwerk.security.encryption import EncryptionManager

            self._encryptor = EncryptionManager(self._encryption_key)

        return self._encryptor

    def _ensure_loaded(self) -> None:
        """Load secrets from file if not loaded."""
        if self._loaded:
            return

        if not self.file_path.exists():
            self._secrets = {}
            self._loaded = True
            return

        try:
            with open(self.file_path, "r") as f:
                encrypted_data = f.read().strip()

            if encrypted_data:
                import json

                encryptor = self._get_encryptor()
                decrypted = encryptor.decrypt(encrypted_data)
                self._secrets = json.loads(decrypted)
            else:
                self._secrets = {}

        except Exception as e:
            logger.warning(f"Failed to load secrets file: {e}")
            # Check if it's an old base64-encoded file (migration path)
            if self._try_migrate_legacy():
                logger.info("Migrated legacy secrets file to encrypted format")
            else:
                self._secrets = {}

        self._loaded = True

    def _try_migrate_legacy(self) -> bool:
        """Try to migrate legacy base64-encoded secrets file."""
        try:
            with open(self.file_path, "r") as f:
                encoded = f.read().strip()

            if encoded:
                import json

                decoded = base64.b64decode(encoded).decode("utf-8")
                self._secrets = json.loads(decoded)
                # Re-save with proper encryption
                self._save()
                return True
        except Exception as e:
            logger.warning("Failed to migrate legacy secrets: %s", e)
        return False

    def _save(self) -> None:
        """Save secrets to file with Fernet encryption."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            import json

            data = json.dumps(self._secrets)
            encryptor = self._get_encryptor()
            encrypted = encryptor.encrypt(data)

            with open(self.file_path, "w") as f:
                f.write(encrypted)

            # Set restrictive permissions (Unix only)
            try:
                os.chmod(self.file_path, 0o600)
            except OSError:
                pass  # Windows doesn't support Unix permissions

        except Exception as e:
            logger.error(f"Failed to save secrets file: {e}")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from file."""
        self._ensure_loaded()
        return self._secrets.get(key, default)

    def set(self, key: str, value: str) -> bool:
        """Set secret in file."""
        self._ensure_loaded()
        self._secrets[key] = value
        self._save()
        return True

    def delete(self, key: str) -> bool:
        """Delete secret from file."""
        self._ensure_loaded()
        if key in self._secrets:
            del self._secrets[key]
            self._save()
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if secret exists."""
        self._ensure_loaded()
        return key in self._secrets

    def list_keys(self) -> List[str]:
        """List secret keys."""
        self._ensure_loaded()
        return list(self._secrets.keys())


class MemorySecretsBackend(SecretsBackend):
    """In-memory secrets backend for testing."""

    def __init__(self):
        """Initialize memory backend."""
        self._secrets: Dict[str, str] = {}

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from memory."""
        return self._secrets.get(key, default)

    def set(self, key: str, value: str) -> bool:
        """Set secret in memory."""
        self._secrets[key] = value
        return True

    def delete(self, key: str) -> bool:
        """Delete secret from memory."""
        if key in self._secrets:
            del self._secrets[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if secret exists."""
        return key in self._secrets

    def list_keys(self) -> List[str]:
        """List secret keys."""
        return list(self._secrets.keys())


class SecretsManager:
    """
    Unified secrets manager supporting multiple backends.

    Features:
    - Multiple backend support (environment, file, memory)
    - Secret references with defaults
    - Access logging and auditing
    - Validation of required secrets
    - Masking for logging

    Usage:
        manager = SecretsManager()

        # Get a secret
        api_key = manager.get("openai-api-key")

        # Define required secrets
        manager.register(SecretReference(
            key="database-password",
            required=True,
            description="PostgreSQL database password",
        ))

        # Validate all required secrets exist
        missing = manager.validate()
        if missing:
            raise ConfigError(f"Missing secrets: {missing}")
    """

    def __init__(
        self,
        primary_backend: SecretBackend = SecretBackend.ENVIRONMENT,
        env_prefix: str = "",
        file_path: str = "~/.ag3ntwerk/secrets.enc",
    ):
        """
        Initialize secrets manager.

        Args:
            primary_backend: Primary backend to use
            env_prefix: Prefix for environment variables
            file_path: Path for file-based secrets
        """
        self.primary_backend = primary_backend

        # Initialize backends
        self._backends: Dict[SecretBackend, SecretsBackend] = {
            SecretBackend.ENVIRONMENT: EnvironmentSecretsBackend(env_prefix),
            SecretBackend.FILE: FileSecretsBackend(file_path),
            SecretBackend.MEMORY: MemorySecretsBackend(),
        }

        # Registered secret references
        self._references: Dict[str, SecretReference] = {}

        # Access tracking
        self._access_log: Dict[str, SecretMetadata] = {}

        # Sensitive key patterns (for auto-detection)
        self._sensitive_patterns: Set[str] = {
            "password",
            "secret",
            "key",
            "token",
            "credential",
            "api-key",
            "apikey",
            "auth",
            "private",
        }

    def register(self, reference: SecretReference) -> None:
        """Register a secret reference."""
        self._references[reference.key] = reference
        logger.debug(f"Registered secret reference: {reference.key}")

    def register_many(self, references: List[SecretReference]) -> None:
        """Register multiple secret references."""
        for ref in references:
            self.register(ref)

    def get(
        self,
        key: str,
        default: Optional[str] = None,
        backend: Optional[SecretBackend] = None,
    ) -> Optional[str]:
        """
        Get a secret value.

        Args:
            key: Secret key
            default: Default value if not found
            backend: Specific backend to use (default: primary)

        Returns:
            Secret value or default
        """
        # Check if registered
        reference = self._references.get(key)
        if reference:
            backend = backend or reference.backend
            default = reference.default if default is None else default
        else:
            backend = backend or self.primary_backend

        # Get from backend
        value = self._backends[backend].get(key, default)

        # Update access log
        self._log_access(key, backend, value is not None)

        # Validate required
        if value is None and reference and reference.required:
            logger.warning(f"Required secret not found: {key}")

        return value

    def set(
        self,
        key: str,
        value: str,
        backend: Optional[SecretBackend] = None,
    ) -> bool:
        """
        Set a secret value.

        Args:
            key: Secret key
            value: Secret value
            backend: Backend to use (default: primary)

        Returns:
            True if successful
        """
        backend = backend or self.primary_backend

        # Don't allow setting in environment backend for security
        if backend == SecretBackend.ENVIRONMENT:
            logger.warning("Setting secrets via environment is not recommended")

        result = self._backends[backend].set(key, value)

        if result:
            logger.info(f"Secret set: {key} (backend: {backend.value})")

        return result

    def delete(
        self,
        key: str,
        backend: Optional[SecretBackend] = None,
    ) -> bool:
        """Delete a secret."""
        backend = backend or self.primary_backend
        result = self._backends[backend].delete(key)

        if result:
            logger.info(f"Secret deleted: {key} (backend: {backend.value})")

        return result

    def exists(
        self,
        key: str,
        backend: Optional[SecretBackend] = None,
    ) -> bool:
        """Check if a secret exists."""
        backend = backend or self.primary_backend
        return self._backends[backend].exists(key)

    def validate(self) -> List[str]:
        """
        Validate all required secrets exist.

        Returns:
            List of missing required secret keys
        """
        missing = []

        for key, reference in self._references.items():
            if reference.required:
                if not self.exists(key, reference.backend):
                    missing.append(key)

        return missing

    def validate_or_raise(self) -> None:
        """Validate and raise exception if missing secrets."""
        missing = self.validate()
        if missing:
            raise RuntimeError(f"Missing required secrets: {', '.join(missing)}")

    def list_registered(self) -> List[SecretReference]:
        """List all registered secret references."""
        return list(self._references.values())

    def get_metadata(self, key: str) -> Optional[SecretMetadata]:
        """Get metadata about a secret."""
        return self._access_log.get(key)

    def is_sensitive(self, key: str) -> bool:
        """Check if a key appears to be sensitive."""
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in self._sensitive_patterns)

    def mask_value(self, value: str, show_chars: int = 4) -> str:
        """Mask a secret value for logging."""
        if not value:
            return "***"
        if len(value) <= show_chars * 2:
            return "***"
        return value[:show_chars] + "***" + value[-show_chars:]

    def _log_access(
        self,
        key: str,
        backend: SecretBackend,
        found: bool,
    ) -> None:
        """Log secret access."""
        now = datetime.now(timezone.utc)

        if key in self._access_log:
            meta = self._access_log[key]
            meta.last_accessed = now
            meta.access_count += 1
            meta.exists = found
        else:
            self._access_log[key] = SecretMetadata(
                key=key,
                exists=found,
                backend=backend,
                last_accessed=now,
                access_count=1,
            )

    def get_access_report(self) -> Dict[str, Any]:
        """Get access report for auditing."""
        return {
            "total_secrets_registered": len(self._references),
            "total_accesses": sum(m.access_count for m in self._access_log.values()),
            "secrets": [
                {
                    "key": m.key,
                    "exists": m.exists,
                    "backend": m.backend.value,
                    "access_count": m.access_count,
                    "last_accessed": m.last_accessed.isoformat() if m.last_accessed else None,
                }
                for m in self._access_log.values()
            ],
        }


# Global instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


# Convenience function
def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a secret using the global manager."""
    return get_secrets_manager().get(key, default)
