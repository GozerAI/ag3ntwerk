"""
Security audit logging for ag3ntwerk.

Provides comprehensive security event logging for:
- Authentication events
- Authorization decisions
- Security incidents
- Configuration changes
- Data access patterns
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """Types of security events."""

    # Authentication
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_LOGOUT = "auth_logout"
    AUTH_TOKEN_REFRESH = "auth_token_refresh"
    AUTH_TOKEN_REVOKED = "auth_token_revoked"
    AUTH_MFA_CHALLENGE = "auth_mfa_challenge"
    AUTH_MFA_SUCCESS = "auth_mfa_success"
    AUTH_MFA_FAILURE = "auth_mfa_failure"

    # Authorization
    AUTHZ_GRANTED = "authz_granted"
    AUTHZ_DENIED = "authz_denied"
    AUTHZ_ELEVATED = "authz_elevated"

    # Access
    ACCESS_RESOURCE = "access_resource"
    ACCESS_SENSITIVE_DATA = "access_sensitive_data"
    ACCESS_DENIED = "access_denied"

    # Data Operations
    DATA_CREATE = "data_create"
    DATA_READ = "data_read"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"

    # Configuration
    CONFIG_CHANGED = "config_changed"
    CONFIG_SECRET_ACCESSED = "config_secret_accessed"
    CONFIG_SECRET_CHANGED = "config_secret_changed"

    # Security Incidents
    INCIDENT_DETECTED = "incident_detected"
    INCIDENT_ESCALATED = "incident_escalated"
    INCIDENT_RESOLVED = "incident_resolved"

    # Threats
    THREAT_DETECTED = "threat_detected"
    THREAT_BLOCKED = "threat_blocked"
    THREAT_MITIGATED = "threat_mitigated"

    # Validation
    VALIDATION_FAILED = "validation_failed"
    INPUT_SANITIZED = "input_sanitized"
    INJECTION_ATTEMPT = "injection_attempt"

    # Rate Limiting
    RATE_LIMIT_WARNING = "rate_limit_warning"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Session
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    SESSION_INVALIDATED = "session_invalidated"

    # System
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_ERROR = "system_error"


class SecuritySeverity(Enum):
    """Severity levels for security events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """A security audit event."""

    id: str = field(default_factory=lambda: str(uuid4()))
    event_type: SecurityEventType = SecurityEventType.SYSTEM_ERROR
    severity: SecuritySeverity = SecuritySeverity.INFO
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Actor information
    actor_id: Optional[str] = None
    actor_type: str = "system"  # user, service, system, agent
    actor_ip: Optional[str] = None
    actor_user_agent: Optional[str] = None

    # Target information
    target_type: Optional[str] = None  # resource, user, config, etc.
    target_id: Optional[str] = None
    target_name: Optional[str] = None

    # Event details
    action: str = ""
    outcome: str = "success"  # success, failure, blocked
    reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    # Context
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None

    # Source
    source_service: str = "ag3ntwerk"
    source_component: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "actor": {
                "id": self.actor_id,
                "type": self.actor_type,
                "ip": self.actor_ip,
                "user_agent": self.actor_user_agent,
            },
            "target": {
                "type": self.target_type,
                "id": self.target_id,
                "name": self.target_name,
            },
            "action": self.action,
            "outcome": self.outcome,
            "reason": self.reason,
            "details": self.details,
            "context": {
                "request_id": self.request_id,
                "session_id": self.session_id,
                "correlation_id": self.correlation_id,
            },
            "source": {
                "service": self.source_service,
                "component": self.source_component,
            },
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class SecurityAuditLogger:
    """
    Security audit logger for comprehensive security event tracking.

    Features:
    - Structured security event logging
    - Multiple output destinations
    - Event filtering by severity
    - Correlation tracking
    - Compliance-ready format

    Usage:
        audit = SecurityAuditLogger()

        # Log authentication event
        audit.log_auth_event(
            event_type=SecurityEventType.AUTH_SUCCESS,
            actor_id="user-123",
            actor_ip="192.168.1.100",
            details={"method": "api_key"},
        )

        # Log access event
        audit.log_access_event(
            event_type=SecurityEventType.ACCESS_SENSITIVE_DATA,
            actor_id="user-123",
            target_type="secret",
            target_id="api-key-openai",
            action="read",
        )

        # Log security incident
        audit.log_incident(
            event_type=SecurityEventType.INJECTION_ATTEMPT,
            severity=SecuritySeverity.HIGH,
            actor_ip="10.0.0.1",
            details={"pattern": "SQL injection", "input": "1' OR '1'='1"},
        )
    """

    # Event type to default severity mapping
    DEFAULT_SEVERITIES: Dict[SecurityEventType, SecuritySeverity] = {
        SecurityEventType.AUTH_SUCCESS: SecuritySeverity.INFO,
        SecurityEventType.AUTH_FAILURE: SecuritySeverity.WARNING,
        SecurityEventType.AUTH_LOGOUT: SecuritySeverity.INFO,
        SecurityEventType.AUTHZ_GRANTED: SecuritySeverity.DEBUG,
        SecurityEventType.AUTHZ_DENIED: SecuritySeverity.WARNING,
        SecurityEventType.ACCESS_SENSITIVE_DATA: SecuritySeverity.INFO,
        SecurityEventType.ACCESS_DENIED: SecuritySeverity.WARNING,
        SecurityEventType.INCIDENT_DETECTED: SecuritySeverity.HIGH,
        SecurityEventType.THREAT_DETECTED: SecuritySeverity.HIGH,
        SecurityEventType.THREAT_BLOCKED: SecuritySeverity.WARNING,
        SecurityEventType.INJECTION_ATTEMPT: SecuritySeverity.HIGH,
        SecurityEventType.RATE_LIMIT_EXCEEDED: SecuritySeverity.WARNING,
        SecurityEventType.VALIDATION_FAILED: SecuritySeverity.INFO,
        SecurityEventType.CONFIG_SECRET_ACCESSED: SecuritySeverity.INFO,
        SecurityEventType.CONFIG_SECRET_CHANGED: SecuritySeverity.WARNING,
    }

    def __init__(
        self,
        log_file: Optional[str] = None,
        min_severity: SecuritySeverity = SecuritySeverity.DEBUG,
        log_to_console: bool = True,
        log_to_file: bool = True,
        source_service: str = "ag3ntwerk",
    ):
        """
        Initialize security audit logger.

        Args:
            log_file: Path to audit log file
            min_severity: Minimum severity to log
            log_to_console: Whether to log to console
            log_to_file: Whether to log to file
            source_service: Service name for events
        """
        self.log_file = log_file or os.path.expanduser("~/.ag3ntwerk/logs/security_audit.log")
        self.min_severity = min_severity
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.source_service = source_service

        # Severity order for filtering
        self._severity_order = {
            SecuritySeverity.DEBUG: 0,
            SecuritySeverity.INFO: 1,
            SecuritySeverity.WARNING: 2,
            SecuritySeverity.HIGH: 3,
            SecuritySeverity.CRITICAL: 4,
        }

        # Event handlers for real-time processing
        self._handlers: List[callable] = []

        # Statistics
        self._event_counts: Dict[SecurityEventType, int] = {}

        # Ensure log directory exists
        if self.log_to_file:
            log_dir = os.path.dirname(self.log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

    def add_handler(self, handler: callable) -> None:
        """Add an event handler for real-time processing."""
        self._handlers.append(handler)

    def log(self, event: SecurityEvent) -> None:
        """
        Log a security event.

        Args:
            event: SecurityEvent to log
        """
        # Check severity threshold
        if self._severity_order.get(event.severity, 0) < self._severity_order.get(
            self.min_severity, 0
        ):
            return

        # Set source service
        event.source_service = self.source_service

        # Update statistics
        self._event_counts[event.event_type] = self._event_counts.get(event.event_type, 0) + 1

        # Format log message
        log_dict = event.to_dict()

        # Log to console
        if self.log_to_console:
            log_level = self._get_log_level(event.severity)
            logger.log(
                log_level,
                f"[SECURITY] {event.event_type.value}: {event.action or 'N/A'} - {event.outcome}",
                extra={"security_event": log_dict},
            )

        # Log to file
        if self.log_to_file:
            self._write_to_file(event.to_json())

        # Call handlers
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Security event handler error: {e}")

    def _write_to_file(self, log_line: str) -> None:
        """Write log line to file."""
        try:
            with open(self.log_file, "a") as f:
                f.write(log_line + "\n")
        except Exception as e:
            logger.error(f"Failed to write security audit log: {e}")

    def _get_log_level(self, severity: SecuritySeverity) -> int:
        """Map security severity to logging level."""
        mapping = {
            SecuritySeverity.DEBUG: logging.DEBUG,
            SecuritySeverity.INFO: logging.INFO,
            SecuritySeverity.WARNING: logging.WARNING,
            SecuritySeverity.HIGH: logging.ERROR,
            SecuritySeverity.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(severity, logging.INFO)

    def log_auth_event(
        self,
        event_type: SecurityEventType,
        actor_id: Optional[str] = None,
        actor_ip: Optional[str] = None,
        actor_user_agent: Optional[str] = None,
        outcome: str = "success",
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> SecurityEvent:
        """Log an authentication event."""
        event = SecurityEvent(
            event_type=event_type,
            severity=self.DEFAULT_SEVERITIES.get(event_type, SecuritySeverity.INFO),
            actor_id=actor_id,
            actor_type="user",
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            action=event_type.value,
            outcome=outcome,
            reason=reason,
            details=details or {},
            **kwargs,
        )
        self.log(event)
        return event

    def log_access_event(
        self,
        event_type: SecurityEventType,
        actor_id: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        target_name: Optional[str] = None,
        action: str = "access",
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> SecurityEvent:
        """Log an access event."""
        event = SecurityEvent(
            event_type=event_type,
            severity=self.DEFAULT_SEVERITIES.get(event_type, SecuritySeverity.INFO),
            actor_id=actor_id,
            actor_type="user",
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            action=action,
            outcome=outcome,
            details=details or {},
            **kwargs,
        )
        self.log(event)
        return event

    def log_data_event(
        self,
        event_type: SecurityEventType,
        actor_id: Optional[str] = None,
        target_type: str = "data",
        target_id: Optional[str] = None,
        action: str = "access",
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> SecurityEvent:
        """Log a data operation event."""
        event = SecurityEvent(
            event_type=event_type,
            severity=self.DEFAULT_SEVERITIES.get(event_type, SecuritySeverity.INFO),
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
            outcome=outcome,
            details=details or {},
            **kwargs,
        )
        self.log(event)
        return event

    def log_incident(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity = SecuritySeverity.HIGH,
        actor_id: Optional[str] = None,
        actor_ip: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        action: str = "detected",
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> SecurityEvent:
        """Log a security incident."""
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            actor_id=actor_id,
            actor_ip=actor_ip,
            target_type=target_type,
            target_id=target_id,
            action=action,
            outcome="blocked" if event_type == SecurityEventType.THREAT_BLOCKED else "detected",
            details=details or {},
            **kwargs,
        )
        self.log(event)
        return event

    def log_config_change(
        self,
        actor_id: Optional[str] = None,
        config_key: str = "",
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> SecurityEvent:
        """Log a configuration change."""
        event_details = details or {}
        event_details.update(
            {
                "config_key": config_key,
                "old_value": "***" if old_value else None,  # Mask values
                "new_value": "***" if new_value else None,
            }
        )

        event = SecurityEvent(
            event_type=SecurityEventType.CONFIG_CHANGED,
            severity=SecuritySeverity.WARNING,
            actor_id=actor_id,
            target_type="config",
            target_id=config_key,
            action="changed",
            outcome="success",
            details=event_details,
            **kwargs,
        )
        self.log(event)
        return event

    def log_validation_failure(
        self,
        field_name: str,
        error_type: str,
        actor_id: Optional[str] = None,
        actor_ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> SecurityEvent:
        """Log a validation failure."""
        event_details = details or {}
        event_details.update(
            {
                "field": field_name,
                "error_type": error_type,
            }
        )

        # Elevate severity for injection attempts
        severity = (
            SecuritySeverity.HIGH if "injection" in error_type.lower() else SecuritySeverity.INFO
        )
        event_type = (
            SecurityEventType.INJECTION_ATTEMPT
            if "injection" in error_type.lower()
            else SecurityEventType.VALIDATION_FAILED
        )

        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            actor_id=actor_id,
            actor_ip=actor_ip,
            target_type="input",
            target_id=field_name,
            action="validate",
            outcome="blocked",
            details=event_details,
            **kwargs,
        )
        self.log(event)
        return event

    def get_statistics(self) -> Dict[str, Any]:
        """Get logging statistics."""
        return {
            "total_events": sum(self._event_counts.values()),
            "by_type": {
                event_type.value: count for event_type, count in self._event_counts.items()
            },
        }


# Global instance
_security_logger: Optional[SecurityAuditLogger] = None


def get_security_logger() -> SecurityAuditLogger:
    """Get the global security audit logger."""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityAuditLogger()
    return _security_logger


def log_security_event(
    event_type: SecurityEventType,
    severity: Optional[SecuritySeverity] = None,
    **kwargs,
) -> SecurityEvent:
    """Log a security event using the global logger."""
    audit = get_security_logger()
    event = SecurityEvent(
        event_type=event_type,
        severity=severity
        or SecurityAuditLogger.DEFAULT_SEVERITIES.get(event_type, SecuritySeverity.INFO),
        **kwargs,
    )
    audit.log(event)
    return event
