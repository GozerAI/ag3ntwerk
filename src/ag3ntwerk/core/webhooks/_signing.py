"""
HMAC-SHA256 payload signing and verification for webhooks.
"""

import hashlib
import hmac


class PayloadSigner:
    """HMAC-SHA256 payload signing and verification."""

    @staticmethod
    def sign(payload: str, secret: str) -> str:
        """
        Sign a payload with HMAC-SHA256.

        Args:
            payload: JSON payload string
            secret: Secret key

        Returns:
            Signature string (sha256=...)
        """
        signature = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={signature}"

    @staticmethod
    def verify(payload: str, signature: str, secret: str) -> bool:
        """
        Verify a webhook signature using constant-time comparison.

        Args:
            payload: JSON payload string
            signature: Signature to verify
            secret: Secret key

        Returns:
            True if signature is valid
        """
        expected = PayloadSigner.sign(payload, secret)
        return hmac.compare_digest(signature, expected)
