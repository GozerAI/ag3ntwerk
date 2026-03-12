"""
Security module for ag3ntwerk.

Provides:
- Input validation and sanitization
- Secrets management
- Security audit logging
- Rate limiting utilities
- Security headers middleware
"""

from .validation import (
    InputValidator,
    ValidationResult,
    validate_input,
    sanitize_string,
    sanitize_html,
)
from .secrets import (
    SecretsManager,
    SecretReference,
    get_secrets_manager,
)
from .audit_logger import (
    SecurityAuditLogger,
    SecurityEvent,
    SecurityEventType,
    log_security_event,
)

__all__ = [
    # Validation
    "InputValidator",
    "ValidationResult",
    "validate_input",
    "sanitize_string",
    "sanitize_html",
    # Secrets
    "SecretsManager",
    "SecretReference",
    "get_secrets_manager",
    # Audit
    "SecurityAuditLogger",
    "SecurityEvent",
    "SecurityEventType",
    "log_security_event",
]
