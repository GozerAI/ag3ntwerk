"""
Encryption utilities for ag3ntwerk.

Provides Fernet-based symmetric encryption for secure storage of secrets.
"""

import base64
import hashlib
import logging
import os
import secrets
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def derive_key(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """
    Derive a Fernet-compatible key from a password using PBKDF2.

    Args:
        password: The password to derive the key from
        salt: Optional salt (generated if not provided)

    Returns:
        Tuple of (derived_key, salt)
    """
    if salt is None:
        salt = os.urandom(16)

    # Use PBKDF2 with SHA256
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations=480000,  # OWASP recommended minimum for PBKDF2-SHA256
        dklen=32,
    )

    # Fernet requires base64-encoded 32-byte key
    fernet_key = base64.urlsafe_b64encode(key)
    return fernet_key, salt


def generate_key() -> str:
    """
    Generate a new random encryption key.

    Returns:
        Base64-encoded Fernet key
    """
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode("utf-8")


class EncryptionManager:
    """
    Manages encryption and decryption using Fernet symmetric encryption.

    Fernet guarantees that a message encrypted using it cannot be manipulated
    or read without the key. It uses AES-128-CBC with PKCS7 padding and HMAC
    using SHA256 for authentication.

    Usage:
        # With a password (key is derived)
        manager = EncryptionManager.from_password("my-secret-password")

        # With a pre-generated key
        key = EncryptionManager.generate_key()
        manager = EncryptionManager(key)

        # Encrypt/decrypt
        encrypted = manager.encrypt("secret data")
        decrypted = manager.decrypt(encrypted)
    """

    def __init__(self, key: str):
        """
        Initialize with a Fernet key.

        Args:
            key: Base64-encoded Fernet key
        """
        from cryptography.fernet import Fernet

        self._fernet = Fernet(key.encode("utf-8") if isinstance(key, str) else key)
        self._key = key

    @classmethod
    def from_password(
        cls,
        password: str,
        salt: Optional[bytes] = None,
        salt_file: Optional[Path] = None,
    ) -> tuple["EncryptionManager", bytes]:
        """
        Create an EncryptionManager from a password.

        Args:
            password: The password to derive the key from
            salt: Optional salt bytes
            salt_file: Optional file to store/load salt

        Returns:
            Tuple of (EncryptionManager, salt)
        """
        # Try to load salt from file
        if salt is None and salt_file and salt_file.exists():
            salt = salt_file.read_bytes()

        key, salt = derive_key(password, salt)

        # Save salt to file
        if salt_file:
            salt_file.parent.mkdir(parents=True, exist_ok=True)
            salt_file.write_bytes(salt)
            os.chmod(salt_file, 0o600)

        return cls(key.decode("utf-8")), salt

    @staticmethod
    def generate_key() -> str:
        """Generate a new random Fernet key."""
        return generate_key()

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted data
        """
        encrypted = self._fernet.encrypt(plaintext.encode("utf-8"))
        return encrypted.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a string.

        Args:
            ciphertext: Base64-encoded encrypted data

        Returns:
            Decrypted string

        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        decrypted = self._fernet.decrypt(ciphertext.encode("utf-8"))
        return decrypted.decode("utf-8")

    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypt bytes."""
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, data: bytes) -> bytes:
        """Decrypt bytes."""
        return self._fernet.decrypt(data)


def get_or_create_encryption_key(
    key_file: Path = Path("~/.ag3ntwerk/encryption.key").expanduser(),
) -> str:
    """
    Get existing encryption key or create a new one.

    Args:
        key_file: Path to store the encryption key

    Returns:
        Encryption key string
    """
    key_file = key_file.expanduser().resolve()

    if key_file.exists():
        return key_file.read_text().strip()

    # Generate new key
    key = generate_key()

    # Save with restrictive permissions
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text(key)
    os.chmod(key_file, 0o600)

    logger.info(f"Generated new encryption key at {key_file}")
    return key
