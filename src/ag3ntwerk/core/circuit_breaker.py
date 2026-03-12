"""
Circuit Breaker for external calls.

Implements the circuit breaker pattern to prevent cascading failures
when external services (LLM providers, Redis, Nexus, etc.) are down.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is down, requests fail immediately
- HALF_OPEN: Testing if service recovered, limited requests allowed

Usage:
    breaker = CircuitBreaker(name="llm", failure_threshold=3, recovery_timeout=30.0)

    async def call_llm(prompt):
        if not breaker.allow_request():
            raise ServiceUnavailableError("LLM circuit breaker is open")
        try:
            result = await llm.generate(prompt)
            breaker.record_success()
            return result
        except Exception as e:
            breaker.record_failure()
            raise
"""

import time
from enum import Enum
from typing import Optional

from ag3ntwerk.core.logging import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Simple circuit breaker for external service calls.

    Args:
        name: Identifier for this circuit breaker
        failure_threshold: Consecutive failures before opening (default 5)
        recovery_timeout: Seconds to wait before half-open test (default 30)
        half_open_max_calls: Max calls in half-open state before deciding (default 1)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit breaker state, with automatic transition to half-open."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit breaker %s transitioned to HALF_OPEN", self.name)
        return self._state

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def allow_request(self) -> bool:
        """Check if a request should be allowed through.

        Returns:
            True if the request is allowed
        """
        current = self.state
        if current == CircuitState.CLOSED:
            return True
        if current == CircuitState.HALF_OPEN:
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False
        # OPEN
        return False

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._half_open_calls = 0
            logger.info("Circuit breaker %s closed (recovery confirmed)", self.name)
        # Always reset consecutive failure count on success
        self._failure_count = 0
        self._success_count += 1

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            # Recovery failed, go back to open
            self._state = CircuitState.OPEN
            self._half_open_calls = 0
            logger.warning("Circuit breaker %s reopened (recovery failed)", self.name)
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker %s opened (failures=%d)",
                self.name,
                self._failure_count,
            )

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0

    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }
