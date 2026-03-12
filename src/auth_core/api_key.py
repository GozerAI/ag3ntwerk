"""API key generation and verification.

Shared across ag3ntwerk services to ensure consistent hashing.
"""

import hashlib
import hmac
import secrets


def generate_key(prefix: str = "") -> tuple[str, str]:
    """Generate a new API key and its hash.

    Args:
        prefix: Optional prefix for the raw key (e.g. "cskey_").

    Returns:
        Tuple of (raw_key, key_hash). Store only the hash.
    """
    raw = prefix + secrets.token_urlsafe(32)
    return raw, hash_key(raw)


def hash_key(key: str) -> str:
    """Compute SHA-256 hash of an API key."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_key(key: str, stored_hash: str) -> bool:
    """Constant-time comparison of a key against a stored hash."""
    return hmac.compare_digest(hash_key(key), stored_hash)
