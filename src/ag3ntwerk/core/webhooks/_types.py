"""
Webhook data types, enums, and dataclasses.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Pattern

import logging

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker state."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for webhook endpoints."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_at: Optional[datetime] = None
    half_open_calls: int = 0

    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker closed after recovery")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_at = datetime.now(timezone.utc)

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            logger.warning("Circuit breaker reopened after half-open failure")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def can_execute(self) -> bool:
        """Check if a call can be made."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure_at:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_at).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.success_count = 0
                    logger.info("Circuit breaker entering half-open state")
                    return True
            return False

        # Half-open: allow limited calls
        if self.half_open_calls < self.half_open_max_calls:
            self.half_open_calls += 1
            return True
        return False


@dataclass
class WebhookFilter:
    """Filter for webhook events."""

    field_equals: Dict[str, Any] = field(default_factory=dict)
    field_contains: Dict[str, str] = field(default_factory=dict)
    field_regex: Dict[str, str] = field(default_factory=dict)

    _compiled_regex: Dict[str, Pattern] = field(default_factory=dict, repr=False)

    def matches(self, payload: Dict[str, Any]) -> bool:
        """Check if payload matches all filters."""
        for field_path, expected in self.field_equals.items():
            value = self._get_nested(payload, field_path)
            if value != expected:
                return False

        for field_path, substring in self.field_contains.items():
            value = self._get_nested(payload, field_path)
            if not isinstance(value, str) or substring not in value:
                return False

        for field_path, pattern in self.field_regex.items():
            value = self._get_nested(payload, field_path)
            if not isinstance(value, str):
                return False

            if field_path not in self._compiled_regex:
                self._compiled_regex[field_path] = re.compile(pattern)

            if not self._compiled_regex[field_path].search(value):
                return False

        return True

    def _get_nested(self, data: Dict, path: str) -> Any:
        """Get a nested value using dot notation."""
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current


class WebhookEventType(str, Enum):
    """Standard webhook event types."""

    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_STEP_COMPLETED = "workflow.step_completed"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"

    AGENT_RESPONSE = "agent.response"
    AGENT_DELEGATION = "agent.delegation"

    HEALTH_CHANGED = "system.health_changed"
    RATE_LIMIT_EXCEEDED = "system.rate_limit_exceeded"


class DeliveryStatus(str, Enum):
    """Webhook delivery status."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class WebhookEvent:
    """A webhook event to be dispatched."""

    id: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class DeliveryAttempt:
    """Record of a delivery attempt."""

    attempt_number: int
    timestamp: datetime
    status_code: Optional[int]
    response_body: Optional[str]
    error: Optional[str]
    duration_ms: float


@dataclass
class DeliveryRecord:
    """Complete delivery record for an event."""

    event_id: str
    webhook_id: str
    status: DeliveryStatus
    attempts: List[DeliveryAttempt] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: Optional[datetime] = None

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)


@dataclass
class Webhook:
    """Webhook subscription configuration."""

    id: str
    url: str
    events: Set[str]
    secret: Optional[str] = None
    active: bool = True
    description: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Delivery settings
    max_retries: int = 3
    retry_delay: float = 5.0
    timeout: float = 30.0

    # Circuit breaker
    circuit_breaker: CircuitBreaker = field(default_factory=CircuitBreaker)

    # Payload filtering
    filters: Optional[WebhookFilter] = None

    # Headers to include
    custom_headers: Dict[str, str] = field(default_factory=dict)

    # Statistics
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    last_delivery_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    consecutive_failures: int = 0

    # Rate limiting
    rate_limit: Optional[int] = None
    _delivery_times: List[datetime] = field(default_factory=list, repr=False)

    def is_rate_limited(self) -> bool:
        """Check if webhook is currently rate limited."""
        if not self.rate_limit:
            return False

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=1)

        self._delivery_times = [t for t in self._delivery_times if t > cutoff]

        return len(self._delivery_times) >= self.rate_limit

    def record_delivery(self) -> None:
        """Record a delivery for rate limiting."""
        if self.rate_limit:
            self._delivery_times.append(datetime.now(timezone.utc))

    def matches_event(self, event_type: str) -> bool:
        """Check if this webhook subscribes to an event type."""
        if "*" in self.events:
            return True
        if event_type in self.events:
            return True
        for pattern in self.events:
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                if event_type.startswith(prefix + "."):
                    return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "url": self.url,
            "events": list(self.events),
            "active": self.active,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "max_retries": self.max_retries,
            "rate_limit": self.rate_limit,
            "circuit_breaker": {
                "state": self.circuit_breaker.state.value,
                "failure_count": self.circuit_breaker.failure_count,
            },
            "stats": {
                "total_deliveries": self.total_deliveries,
                "successful_deliveries": self.successful_deliveries,
                "failed_deliveries": self.failed_deliveries,
                "consecutive_failures": self.consecutive_failures,
                "last_delivery_at": (
                    self.last_delivery_at.isoformat() if self.last_delivery_at else None
                ),
                "success_rate": (
                    self.successful_deliveries / self.total_deliveries
                    if self.total_deliveries > 0
                    else 1.0
                ),
            },
        }
