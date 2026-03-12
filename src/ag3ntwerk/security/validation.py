"""
Input validation and sanitization for ag3ntwerk.

Provides comprehensive input validation to prevent:
- SQL injection
- XSS attacks
- Command injection
- Path traversal
- Other OWASP Top 10 vulnerabilities
"""

import html
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Pattern, Set, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ValidationErrorType(Enum):
    """Types of validation errors."""

    REQUIRED = "required"
    TYPE_MISMATCH = "type_mismatch"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN_MISMATCH = "pattern_mismatch"
    INVALID_FORMAT = "invalid_format"
    DANGEROUS_CONTENT = "dangerous_content"
    PATH_TRAVERSAL = "path_traversal"
    SQL_INJECTION = "sql_injection"
    XSS_DETECTED = "xss_detected"
    COMMAND_INJECTION = "command_injection"


@dataclass
class ValidationError:
    """A single validation error."""

    field: str
    error_type: ValidationErrorType
    message: str
    value: Any = None


@dataclass
class ValidationResult:
    """Result of input validation."""

    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    sanitized_value: Any = None

    def add_error(
        self,
        field: str,
        error_type: ValidationErrorType,
        message: str,
        value: Any = None,
    ) -> None:
        """Add a validation error."""
        self.valid = False
        self.errors.append(ValidationError(field, error_type, message, value))


class InputValidator:
    """
    Comprehensive input validator for security-sensitive applications.

    Features:
    - SQL injection detection
    - XSS detection and sanitization
    - Command injection detection
    - Path traversal prevention
    - Type validation
    - Length constraints
    - Pattern matching
    - Custom validators

    Usage:
        validator = InputValidator()

        # Validate a single field
        result = validator.validate_string(
            value=user_input,
            field_name="username",
            min_length=3,
            max_length=50,
            pattern=r"^[a-zA-Z0-9_]+$",
        )

        # Validate a dictionary of inputs
        result = validator.validate_dict(
            data={"name": "John", "email": "john@example.com"},
            schema={
                "name": {"type": "string", "required": True, "max_length": 100},
                "email": {"type": "email", "required": True},
            },
        )
    """

    # SQL injection patterns
    SQL_INJECTION_PATTERNS: List[Pattern] = [
        re.compile(
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)", re.IGNORECASE
        ),
        re.compile(r"(--|;|/\*|\*/)", re.IGNORECASE),
        re.compile(r"(\bOR\b|\bAND\b)\s+\d+\s*=\s*\d+", re.IGNORECASE),
        re.compile(r"'\s*(OR|AND)\s+'", re.IGNORECASE),
        re.compile(r"(\bEXEC\b|\bEXECUTE\b|\bXP_\b)", re.IGNORECASE),
    ]

    # XSS patterns
    XSS_PATTERNS: List[Pattern] = [
        re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),
        re.compile(r"<\s*iframe", re.IGNORECASE),
        re.compile(r"<\s*object", re.IGNORECASE),
        re.compile(r"<\s*embed", re.IGNORECASE),
        re.compile(r"<\s*link", re.IGNORECASE),
        re.compile(r"expression\s*\(", re.IGNORECASE),
        re.compile(r"vbscript:", re.IGNORECASE),
        re.compile(r"data:\s*text/html", re.IGNORECASE),
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS: List[Pattern] = [
        re.compile(r"[;&|`$]"),
        re.compile(r"\$\([^)]+\)"),
        re.compile(r"`[^`]+`"),
        re.compile(r"\|\|"),
        re.compile(r"&&"),
        re.compile(r">\s*[/\w]"),
        re.compile(r"<\s*[/\w]"),
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS: List[Pattern] = [
        re.compile(r"\.\.[\\/]"),
        re.compile(r"\.\.%2[fF]"),
        re.compile(r"\.\.%5[cC]"),
        re.compile(r"%2[eE]%2[eE]"),
        re.compile(r"^[/\\]"),  # Absolute paths
        re.compile(r"^[a-zA-Z]:"),  # Windows drive letters
    ]

    # Email pattern
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    # URL pattern (basic)
    URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)

    # UUID pattern
    UUID_PATTERN = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
    )

    def __init__(
        self,
        strict_mode: bool = True,
        custom_validators: Optional[Dict[str, Callable]] = None,
    ):
        """
        Initialize validator.

        Args:
            strict_mode: If True, any suspicious content fails validation
            custom_validators: Dict of custom validation functions
        """
        self.strict_mode = strict_mode
        self.custom_validators = custom_validators or {}

    def validate_string(
        self,
        value: Any,
        field_name: str = "value",
        required: bool = False,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        check_sql_injection: bool = True,
        check_xss: bool = True,
        check_command_injection: bool = False,
        sanitize: bool = True,
    ) -> ValidationResult:
        """
        Validate a string input.

        Args:
            value: Value to validate
            field_name: Name of the field (for error messages)
            required: Whether the field is required
            min_length: Minimum string length
            max_length: Maximum string length
            pattern: Regex pattern to match
            check_sql_injection: Check for SQL injection
            check_xss: Check for XSS attacks
            check_command_injection: Check for command injection
            sanitize: Sanitize the value if valid

        Returns:
            ValidationResult with validation status and sanitized value
        """
        result = ValidationResult(valid=True)

        # Handle None/empty
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                result.add_error(
                    field_name, ValidationErrorType.REQUIRED, f"{field_name} is required"
                )
            else:
                result.sanitized_value = ""
            return result

        # Type check
        if not isinstance(value, str):
            try:
                value = str(value)
            except (TypeError, ValueError):
                result.add_error(
                    field_name, ValidationErrorType.TYPE_MISMATCH, f"{field_name} must be a string"
                )
                return result

        # Length checks
        if min_length is not None and len(value) < min_length:
            result.add_error(
                field_name,
                ValidationErrorType.MIN_LENGTH,
                f"{field_name} must be at least {min_length} characters",
            )

        if max_length is not None and len(value) > max_length:
            result.add_error(
                field_name,
                ValidationErrorType.MAX_LENGTH,
                f"{field_name} must be at most {max_length} characters",
            )

        # Pattern check
        if pattern:
            if not re.match(pattern, value):
                result.add_error(
                    field_name,
                    ValidationErrorType.PATTERN_MISMATCH,
                    f"{field_name} does not match required pattern",
                )

        # Security checks
        if check_sql_injection and self._detect_sql_injection(value):
            result.add_error(
                field_name,
                ValidationErrorType.SQL_INJECTION,
                f"{field_name} contains potentially dangerous SQL content",
            )

        if check_xss and self._detect_xss(value):
            result.add_error(
                field_name,
                ValidationErrorType.XSS_DETECTED,
                f"{field_name} contains potentially dangerous HTML/JavaScript content",
            )

        if check_command_injection and self._detect_command_injection(value):
            result.add_error(
                field_name,
                ValidationErrorType.COMMAND_INJECTION,
                f"{field_name} contains potentially dangerous shell characters",
            )

        # Sanitize if valid
        if result.valid and sanitize:
            result.sanitized_value = self._sanitize_string(value, check_xss)
        elif result.valid:
            result.sanitized_value = value

        return result

    def validate_path(
        self,
        value: str,
        field_name: str = "path",
        allowed_base_paths: Optional[List[str]] = None,
    ) -> ValidationResult:
        """
        Validate a file path.

        Args:
            value: Path to validate
            field_name: Field name for errors
            allowed_base_paths: List of allowed base directories

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)

        if not value:
            result.add_error(field_name, ValidationErrorType.REQUIRED, f"{field_name} is required")
            return result

        # Check for path traversal
        if self._detect_path_traversal(value):
            result.add_error(
                field_name,
                ValidationErrorType.PATH_TRAVERSAL,
                f"{field_name} contains path traversal attempt",
            )
            return result

        # Check against allowed base paths
        if allowed_base_paths:
            normalized = value.replace("\\", "/")
            allowed = any(
                normalized.startswith(base.replace("\\", "/")) for base in allowed_base_paths
            )
            if not allowed:
                result.add_error(
                    field_name,
                    ValidationErrorType.DANGEROUS_CONTENT,
                    f"{field_name} is not within allowed directories",
                )

        if result.valid:
            result.sanitized_value = value

        return result

    def validate_email(
        self,
        value: str,
        field_name: str = "email",
        required: bool = False,
    ) -> ValidationResult:
        """Validate an email address."""
        result = ValidationResult(valid=True)

        if not value:
            if required:
                result.add_error(
                    field_name, ValidationErrorType.REQUIRED, f"{field_name} is required"
                )
            else:
                result.sanitized_value = ""
            return result

        if not self.EMAIL_PATTERN.match(value):
            result.add_error(
                field_name,
                ValidationErrorType.INVALID_FORMAT,
                f"{field_name} is not a valid email address",
            )
        else:
            result.sanitized_value = value.lower().strip()

        return result

    def validate_url(
        self,
        value: str,
        field_name: str = "url",
        required: bool = False,
        allowed_schemes: Optional[Set[str]] = None,
        allowed_hosts: Optional[Set[str]] = None,
    ) -> ValidationResult:
        """
        Validate a URL.

        Args:
            value: URL to validate
            field_name: Field name for errors
            required: Whether the field is required
            allowed_schemes: Set of allowed URL schemes (default: http, https)
            allowed_hosts: Set of allowed hostnames (optional)

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)
        allowed_schemes = allowed_schemes or {"http", "https"}

        if not value:
            if required:
                result.add_error(
                    field_name, ValidationErrorType.REQUIRED, f"{field_name} is required"
                )
            else:
                result.sanitized_value = ""
            return result

        try:
            parsed = urlparse(value)

            if not parsed.scheme:
                result.add_error(
                    field_name,
                    ValidationErrorType.INVALID_FORMAT,
                    f"{field_name} must have a scheme (e.g., https://)",
                )
            elif parsed.scheme.lower() not in allowed_schemes:
                result.add_error(
                    field_name,
                    ValidationErrorType.INVALID_FORMAT,
                    f"{field_name} scheme must be one of: {', '.join(allowed_schemes)}",
                )

            if not parsed.netloc:
                result.add_error(
                    field_name, ValidationErrorType.INVALID_FORMAT, f"{field_name} must have a host"
                )

            if allowed_hosts and parsed.netloc.lower() not in allowed_hosts:
                result.add_error(
                    field_name,
                    ValidationErrorType.DANGEROUS_CONTENT,
                    f"{field_name} host is not allowed",
                )

            # Check for XSS in URL
            if self._detect_xss(value):
                result.add_error(
                    field_name,
                    ValidationErrorType.XSS_DETECTED,
                    f"{field_name} contains potentially dangerous content",
                )

        except (ValueError, TypeError):
            result.add_error(
                field_name, ValidationErrorType.INVALID_FORMAT, f"{field_name} is not a valid URL"
            )

        if result.valid:
            result.sanitized_value = value

        return result

    def validate_dict(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Dict[str, Any]],
    ) -> ValidationResult:
        """
        Validate a dictionary against a schema.

        Args:
            data: Dictionary to validate
            schema: Validation schema

        Schema format:
            {
                "field_name": {
                    "type": "string" | "email" | "url" | "int" | "float" | "bool" | "path",
                    "required": bool,
                    "min_length": int,
                    "max_length": int,
                    "pattern": str,
                    "min_value": number,
                    "max_value": number,
                    "allowed_values": list,
                    ...
                }
            }

        Returns:
            ValidationResult with sanitized data
        """
        result = ValidationResult(valid=True, sanitized_value={})

        for field_name, rules in schema.items():
            value = data.get(field_name)
            field_type = rules.get("type", "string")
            required = rules.get("required", False)

            # Type-specific validation
            if field_type == "string":
                field_result = self.validate_string(
                    value=value,
                    field_name=field_name,
                    required=required,
                    min_length=rules.get("min_length"),
                    max_length=rules.get("max_length"),
                    pattern=rules.get("pattern"),
                )
            elif field_type == "email":
                field_result = self.validate_email(value, field_name, required)
            elif field_type == "url":
                field_result = self.validate_url(
                    value,
                    field_name,
                    required,
                    allowed_schemes=rules.get("allowed_schemes"),
                    allowed_hosts=rules.get("allowed_hosts"),
                )
            elif field_type == "path":
                field_result = self.validate_path(
                    value,
                    field_name,
                    allowed_base_paths=rules.get("allowed_base_paths"),
                )
            elif field_type in ("int", "integer"):
                field_result = self._validate_number(
                    value,
                    field_name,
                    required,
                    int,
                    rules.get("min_value"),
                    rules.get("max_value"),
                )
            elif field_type == "float":
                field_result = self._validate_number(
                    value,
                    field_name,
                    required,
                    float,
                    rules.get("min_value"),
                    rules.get("max_value"),
                )
            elif field_type in ("bool", "boolean"):
                field_result = self._validate_bool(value, field_name, required)
            else:
                # Default to string validation
                field_result = self.validate_string(value, field_name, required)

            # Check allowed values
            if field_result.valid and "allowed_values" in rules:
                if field_result.sanitized_value not in rules["allowed_values"]:
                    field_result.add_error(
                        field_name,
                        ValidationErrorType.INVALID_FORMAT,
                        f"{field_name} must be one of: {rules['allowed_values']}",
                    )

            # Merge results
            if not field_result.valid:
                result.valid = False
                result.errors.extend(field_result.errors)
            else:
                result.sanitized_value[field_name] = field_result.sanitized_value

        return result

    def _validate_number(
        self,
        value: Any,
        field_name: str,
        required: bool,
        num_type: type,
        min_value: Optional[float],
        max_value: Optional[float],
    ) -> ValidationResult:
        """Validate a numeric value."""
        result = ValidationResult(valid=True)

        if value is None:
            if required:
                result.add_error(
                    field_name, ValidationErrorType.REQUIRED, f"{field_name} is required"
                )
            else:
                result.sanitized_value = None
            return result

        try:
            converted = num_type(value)
        except (ValueError, TypeError):
            result.add_error(
                field_name,
                ValidationErrorType.TYPE_MISMATCH,
                f"{field_name} must be a {num_type.__name__}",
            )
            return result

        if min_value is not None and converted < min_value:
            result.add_error(
                field_name,
                ValidationErrorType.INVALID_FORMAT,
                f"{field_name} must be at least {min_value}",
            )

        if max_value is not None and converted > max_value:
            result.add_error(
                field_name,
                ValidationErrorType.INVALID_FORMAT,
                f"{field_name} must be at most {max_value}",
            )

        if result.valid:
            result.sanitized_value = converted

        return result

    def _validate_bool(
        self,
        value: Any,
        field_name: str,
        required: bool,
    ) -> ValidationResult:
        """Validate a boolean value."""
        result = ValidationResult(valid=True)

        if value is None:
            if required:
                result.add_error(
                    field_name, ValidationErrorType.REQUIRED, f"{field_name} is required"
                )
            else:
                result.sanitized_value = None
            return result

        if isinstance(value, bool):
            result.sanitized_value = value
        elif isinstance(value, str):
            if value.lower() in ("true", "1", "yes", "on"):
                result.sanitized_value = True
            elif value.lower() in ("false", "0", "no", "off"):
                result.sanitized_value = False
            else:
                result.add_error(
                    field_name, ValidationErrorType.TYPE_MISMATCH, f"{field_name} must be a boolean"
                )
        else:
            result.sanitized_value = bool(value)

        return result

    def _detect_sql_injection(self, value: str) -> bool:
        """Detect potential SQL injection."""
        for pattern in self.SQL_INJECTION_PATTERNS:
            if pattern.search(value):
                logger.warning(f"SQL injection pattern detected: {pattern.pattern}")
                return True
        return False

    def _detect_xss(self, value: str) -> bool:
        """Detect potential XSS attacks."""
        for pattern in self.XSS_PATTERNS:
            if pattern.search(value):
                logger.warning(f"XSS pattern detected: {pattern.pattern}")
                return True
        return False

    def _detect_command_injection(self, value: str) -> bool:
        """Detect potential command injection."""
        for pattern in self.COMMAND_INJECTION_PATTERNS:
            if pattern.search(value):
                logger.warning(f"Command injection pattern detected: {pattern.pattern}")
                return True
        return False

    def _detect_path_traversal(self, value: str) -> bool:
        """Detect potential path traversal."""
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if pattern.search(value):
                logger.warning(f"Path traversal pattern detected: {pattern.pattern}")
                return True
        return False

    def _sanitize_string(self, value: str, html_escape: bool = True) -> str:
        """Sanitize a string value."""
        # Strip whitespace
        value = value.strip()

        # HTML escape if needed
        if html_escape:
            value = html.escape(value)

        return value


# Convenience functions
_default_validator = InputValidator()


def validate_input(
    value: Any,
    field_name: str = "value",
    **kwargs,
) -> ValidationResult:
    """Validate input using the default validator."""
    return _default_validator.validate_string(value, field_name, **kwargs)


def sanitize_string(value: str) -> str:
    """Sanitize a string, escaping HTML."""
    if not value:
        return ""
    return html.escape(value.strip())


def sanitize_html(value: str, allowed_tags: Optional[Set[str]] = None) -> str:
    """
    Sanitize HTML, keeping only allowed tags.

    Args:
        value: HTML string to sanitize
        allowed_tags: Set of allowed tag names (default: none)

    Returns:
        Sanitized HTML string
    """
    if not value:
        return ""

    allowed_tags = allowed_tags or set()

    # Simple implementation - for production, use a library like bleach
    if not allowed_tags:
        return html.escape(value)

    # This is a basic implementation - consider using bleach for production
    result = []
    in_tag = False
    tag_buffer = []

    for char in value:
        if char == "<":
            in_tag = True
            tag_buffer = []
        elif char == ">":
            in_tag = False
            tag_name = "".join(tag_buffer).split()[0].lstrip("/").lower()
            if tag_name in allowed_tags:
                result.append("<" + "".join(tag_buffer) + ">")
            else:
                result.append(html.escape("<" + "".join(tag_buffer) + ">"))
        elif in_tag:
            tag_buffer.append(char)
        else:
            result.append(char)

    return "".join(result)
