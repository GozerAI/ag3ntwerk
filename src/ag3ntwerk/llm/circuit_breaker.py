"""
Circuit Breaker pattern implementation for LLM providers.

This module provides resilience patterns to prevent cascading failures
when LLM providers become unavailable or slow. It implements:

1. Circuit Breaker: Stops calling a failing service temporarily
2. Retry with exponential backoff: Retries failed requests with increasing delays
3. Timeout handling: Prevents requests from hanging indefinitely

Usage:
    from ag3ntwerk.llm.circuit_breaker import CircuitBreaker, with_circuit_breaker

    # Create a circuit breaker
    breaker = CircuitBreaker(name="ollama", failure_threshold=5)

    # Use as decorator
    @with_circuit_breaker(breaker)
    async def call_llm():
        ...

    # Or use directly
    async with breaker:
        result = await provider.generate(prompt)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, ParamSpec

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests flow through
    OPEN = "open"  # Circuit tripped, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    # Number of failures before opening circuit
    failure_threshold: int = 5

    # Time in seconds before attempting recovery
    recovery_timeout: float = 30.0

    # Number of successful calls needed to close circuit from half-open
    success_threshold: int = 2

    # Request timeout in seconds
    request_timeout: float = 60.0

    # Retry configuration
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0
    retry_exponential_base: float = 2.0

    # Exceptions that should trigger circuit breaker
    # None means all exceptions trigger it
    tracked_exceptions: Optional[tuple] = None


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0  # Calls rejected when circuit is open
    timeouts: int = 0
    retries: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: int = 0

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "timeouts": self.timeouts,
            "retries": self.retries,
            "success_rate": (
                self.successful_calls / self.total_calls if self.total_calls > 0 else 0.0
            ),
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "state_changes": self.state_changes,
        }


class CircuitBreakerError(Exception):
    """Base exception for circuit breaker errors."""

    pass


class CircuitOpenError(CircuitBreakerError):
    """Raised when circuit is open and rejecting requests."""

    def __init__(self, breaker_name: str, remaining_time: float):
        self.breaker_name = breaker_name
        self.remaining_time = remaining_time
        super().__init__(
            f"Circuit breaker '{breaker_name}' is open. "
            f"Will retry in {remaining_time:.1f} seconds."
        )


class CircuitBreaker:
    """
    Circuit breaker implementation for async operations.

    The circuit breaker has three states:
    - CLOSED: Normal operation. Requests flow through. Failures are counted.
    - OPEN: Service is considered down. Requests fail fast without calling service.
    - HALF_OPEN: Testing recovery. Limited requests allowed through.

    State transitions:
    - CLOSED -> OPEN: When failure count exceeds threshold
    - OPEN -> HALF_OPEN: After recovery timeout
    - HALF_OPEN -> CLOSED: When success threshold met
    - HALF_OPEN -> OPEN: On any failure
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        **kwargs,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig(**kwargs)
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._state_changed_at = time.monotonic()
        self._lock = asyncio.Lock()
        self.stats = CircuitBreakerStats()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state == CircuitState.OPEN

    async def _check_state(self) -> None:
        """Check and potentially update circuit state."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                time_in_open = time.monotonic() - self._state_changed_at
                if time_in_open >= self.config.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
                    logger.info(
                        f"Circuit breaker '{self.name}' transitioning to HALF_OPEN "
                        f"after {time_in_open:.1f}s recovery timeout"
                    )

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._state_changed_at = time.monotonic()
        self._failure_count = 0
        self._success_count = 0
        self.stats.state_changes += 1

        logger.info(f"Circuit breaker '{self.name}': {old_state.value} -> {new_state.value}")

    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self.stats.successful_calls += 1
            self.stats.last_success_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
                    logger.info(
                        f"Circuit breaker '{self.name}' closed after "
                        f"{self._success_count} successful calls"
                    )

    async def _record_failure(self, error: Exception) -> None:
        """Record a failed call."""
        async with self._lock:
            self.stats.failed_calls += 1
            self.stats.last_failure_time = time.time()
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open state opens the circuit
                self._transition_to(CircuitState.OPEN)
                logger.warning(
                    f"Circuit breaker '{self.name}' reopened due to failure "
                    f"in HALF_OPEN state: {error}"
                )
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
                    logger.warning(
                        f"Circuit breaker '{self.name}' opened after "
                        f"{self._failure_count} failures"
                    )

    def _should_track_exception(self, error: Exception) -> bool:
        """Check if this exception should be tracked by the circuit breaker."""
        if self.config.tracked_exceptions is None:
            return True
        return isinstance(error, self.config.tracked_exceptions)

    async def call(
        self,
        func: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result from the function

        Raises:
            CircuitOpenError: If circuit is open
            Exception: If function fails after retries
        """
        async with self._lock:
            self.stats.total_calls += 1

        # Check current state
        await self._check_state()

        # Reject if open
        if self._state == CircuitState.OPEN:
            self.stats.rejected_calls += 1
            remaining = self.config.recovery_timeout - (time.monotonic() - self._state_changed_at)
            raise CircuitOpenError(self.name, max(0, remaining))

        # Execute with retries
        last_error: Optional[Exception] = None
        attempts = 0
        max_attempts = self.config.max_retries + 1

        while attempts < max_attempts:
            attempts += 1

            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.request_timeout,
                )
                await self._record_success()
                return result

            except asyncio.TimeoutError as e:
                self.stats.timeouts += 1
                last_error = e
                logger.warning(
                    f"Circuit breaker '{self.name}': request timed out "
                    f"(attempt {attempts}/{max_attempts})"
                )

            except Exception as e:
                last_error = e

                if not self._should_track_exception(e):
                    # Don't retry or track non-tracked exceptions
                    raise

                logger.warning(
                    f"Circuit breaker '{self.name}': request failed "
                    f"(attempt {attempts}/{max_attempts}): {e}"
                )

            # Should we retry?
            if attempts < max_attempts:
                self.stats.retries += 1
                delay = min(
                    self.config.retry_base_delay
                    * (self.config.retry_exponential_base ** (attempts - 1)),
                    self.config.retry_max_delay,
                )
                logger.debug(f"Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)

        # All attempts failed
        if last_error:
            await self._record_failure(last_error)
            raise last_error

        raise RuntimeError("Unexpected: no result and no error")

    async def __aenter__(self) -> "CircuitBreaker":
        """Context manager entry - check state before executing."""
        await self._check_state()

        if self._state == CircuitState.OPEN:
            remaining = self.config.recovery_timeout - (time.monotonic() - self._state_changed_at)
            raise CircuitOpenError(self.name, max(0, remaining))

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Context manager exit - record success or failure."""
        if exc_type is None:
            await self._record_success()
        elif exc_val is not None and self._should_track_exception(exc_val):
            await self._record_failure(exc_val)
        return False  # Don't suppress exceptions

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._state_changed_at = time.monotonic()
        logger.info(f"Circuit breaker '{self.name}' manually reset")

    def get_status(self) -> dict:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "stats": self.stats.to_dict(),
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "request_timeout": self.config.request_timeout,
                "max_retries": self.config.max_retries,
            },
        }


def with_circuit_breaker(breaker: CircuitBreaker):
    """
    Decorator to wrap an async function with circuit breaker protection.

    Usage:
        breaker = CircuitBreaker("my-service")

        @with_circuit_breaker(breaker)
        async def call_service():
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Usage:
        registry = CircuitBreakerRegistry()
        breaker = registry.get_or_create("ollama")
        await breaker.call(my_func)
    """

    def __init__(self, default_config: Optional[CircuitBreakerConfig] = None):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._default_config = default_config or CircuitBreakerConfig()
        self._lock = asyncio.Lock()

    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create a new one."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                config=config or self._default_config,
            )
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return self._breakers.get(name)

    def get_all_status(self) -> dict[str, dict]:
        """Get status of all circuit breakers."""
        return {name: breaker.get_status() for name, breaker in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers to closed state."""
        for breaker in self._breakers.values():
            breaker.reset()


# Global registry for convenience
_global_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = CircuitBreakerRegistry()
    return _global_registry


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create a circuit breaker from the global registry."""
    return get_circuit_breaker_registry().get_or_create(name)
