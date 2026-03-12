"""Tests for circuit breaker pattern implementation."""

import time

import pytest

from ag3ntwerk.core.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreakerInitialState:
    """Test 1: Initial state is CLOSED."""

    def test_initial_state_is_closed(self):
        breaker = CircuitBreaker("test-service")
        assert breaker.state == CircuitState.CLOSED

    def test_is_closed_true_initially(self):
        breaker = CircuitBreaker("test-service")
        assert breaker.is_closed is True

    def test_is_open_false_initially(self):
        breaker = CircuitBreaker("test-service")
        assert breaker.is_open is False


class TestCircuitBreakerClosedState:
    """Test 2: Requests allowed when closed."""

    def test_allow_request_when_closed(self):
        breaker = CircuitBreaker("test-service")
        assert breaker.allow_request() is True

    def test_multiple_requests_allowed_when_closed(self):
        breaker = CircuitBreaker("test-service")
        for _ in range(20):
            assert breaker.allow_request() is True

    def test_stays_closed_after_some_failures(self):
        breaker = CircuitBreaker("test-service", failure_threshold=5)
        for _ in range(4):
            breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.allow_request() is True


class TestCircuitBreakerOpensAfterThreshold:
    """Test 3: Opens after failure_threshold consecutive failures."""

    def test_opens_after_reaching_failure_threshold(self):
        breaker = CircuitBreaker("test-service", failure_threshold=5)
        for _ in range(5):
            breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open is True
        assert breaker.is_closed is False

    def test_success_resets_failure_count(self):
        breaker = CircuitBreaker("test-service", failure_threshold=3)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()
        breaker.record_failure()
        breaker.record_failure()
        # Only 2 consecutive failures after the success, not 3
        assert breaker.state == CircuitState.CLOSED

    def test_opens_at_exact_threshold(self):
        breaker = CircuitBreaker("test-service", failure_threshold=1)
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN


class TestCircuitBreakerOpenState:
    """Test 4: Requests blocked when open."""

    def test_requests_blocked_when_open(self):
        breaker = CircuitBreaker("test-service", failure_threshold=3)
        for _ in range(3):
            breaker.record_failure()
        assert breaker.allow_request() is False

    def test_multiple_requests_blocked_when_open(self):
        breaker = CircuitBreaker("test-service", failure_threshold=3)
        for _ in range(3):
            breaker.record_failure()
        for _ in range(10):
            assert breaker.allow_request() is False


class TestCircuitBreakerHalfOpenTransition:
    """Test 5: Transitions to half-open after recovery_timeout."""

    def test_transitions_to_half_open_after_timeout(self):
        breaker = CircuitBreaker("test-service", failure_threshold=3, recovery_timeout=30.0)
        for _ in range(3):
            breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Simulate time passing beyond recovery_timeout
        breaker._last_failure_time = time.monotonic() - 31
        assert breaker.state == CircuitState.HALF_OPEN

    def test_allow_request_true_in_half_open(self):
        breaker = CircuitBreaker("test-service", failure_threshold=3, recovery_timeout=30.0)
        for _ in range(3):
            breaker.record_failure()

        breaker._last_failure_time = time.monotonic() - 31
        assert breaker.allow_request() is True

    def test_stays_open_before_timeout(self):
        breaker = CircuitBreaker("test-service", failure_threshold=3, recovery_timeout=30.0)
        for _ in range(3):
            breaker.record_failure()

        breaker._last_failure_time = time.monotonic() - 10
        assert breaker.state == CircuitState.OPEN


class TestCircuitBreakerHalfOpenSuccess:
    """Test 6: Closes again after success in half-open state."""

    def test_closes_after_success_in_half_open(self):
        breaker = CircuitBreaker("test-service", failure_threshold=3, recovery_timeout=30.0)
        for _ in range(3):
            breaker.record_failure()

        # Move to half-open
        breaker._last_failure_time = time.monotonic() - 31
        assert breaker.state == CircuitState.HALF_OPEN

        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed is True
        assert breaker.allow_request() is True


class TestCircuitBreakerHalfOpenFailure:
    """Test 7: Reopens if failure in half-open state."""

    def test_reopens_on_failure_in_half_open(self):
        breaker = CircuitBreaker("test-service", failure_threshold=3, recovery_timeout=30.0)
        for _ in range(3):
            breaker.record_failure()

        # Move to half-open
        breaker._last_failure_time = time.monotonic() - 31
        assert breaker.state == CircuitState.HALF_OPEN

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open is True


class TestCircuitBreakerReset:
    """Test 8: Reset returns to closed state."""

    def test_reset_from_open(self):
        breaker = CircuitBreaker("test-service", failure_threshold=3)
        for _ in range(3):
            breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed is True
        assert breaker.allow_request() is True

    def test_reset_from_half_open(self):
        breaker = CircuitBreaker("test-service", failure_threshold=3, recovery_timeout=30.0)
        for _ in range(3):
            breaker.record_failure()
        breaker._last_failure_time = time.monotonic() - 31

        assert breaker.state == CircuitState.HALF_OPEN
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED

    def test_reset_clears_failure_count(self):
        breaker = CircuitBreaker("test-service", failure_threshold=3)
        breaker.record_failure()
        breaker.record_failure()
        breaker.reset()
        # After reset, should need full threshold again to open
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED


class TestCircuitBreakerGetStats:
    """Test 9: get_stats returns correct data."""

    def test_get_stats_initial(self):
        breaker = CircuitBreaker("test-service", failure_threshold=5, recovery_timeout=30.0)
        stats = breaker.get_stats()
        assert stats["name"] == "test-service"
        assert (
            stats["state"] == CircuitState.CLOSED.value
            if isinstance(stats["state"], str)
            else stats["state"] == CircuitState.CLOSED
        )
        assert stats["failure_threshold"] == 5
        assert stats["recovery_timeout"] == 30.0

    def test_get_stats_after_failures(self):
        breaker = CircuitBreaker("test-service", failure_threshold=5)
        breaker.record_failure()
        breaker.record_failure()
        stats = breaker.get_stats()
        assert "failure_count" in stats or "consecutive_failures" in stats
        # Check whichever key is used
        failure_key = "failure_count" if "failure_count" in stats else "consecutive_failures"
        assert stats[failure_key] == 2

    def test_get_stats_returns_dict(self):
        breaker = CircuitBreaker("test-service")
        stats = breaker.get_stats()
        assert isinstance(stats, dict)
        assert "name" in stats
        assert "state" in stats


class TestCircuitBreakerCustomThresholds:
    """Test 10: Custom thresholds work."""

    def test_custom_failure_threshold(self):
        breaker = CircuitBreaker("test-service", failure_threshold=2)
        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

    def test_custom_recovery_timeout(self):
        breaker = CircuitBreaker("test-service", failure_threshold=2, recovery_timeout=5.0)
        for _ in range(2):
            breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Not enough time elapsed
        breaker._last_failure_time = time.monotonic() - 3
        assert breaker.state == CircuitState.OPEN

        # Enough time elapsed
        breaker._last_failure_time = time.monotonic() - 6
        assert breaker.state == CircuitState.HALF_OPEN

    def test_custom_half_open_max_calls(self):
        breaker = CircuitBreaker(
            "test-service",
            failure_threshold=2,
            recovery_timeout=10.0,
            half_open_max_calls=1,
        )
        for _ in range(2):
            breaker.record_failure()
        breaker._last_failure_time = time.monotonic() - 11
        assert breaker.state == CircuitState.HALF_OPEN

        # First call in half-open should be allowed
        assert breaker.allow_request() is True

    def test_large_failure_threshold(self):
        breaker = CircuitBreaker("test-service", failure_threshold=100)
        for _ in range(99):
            breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
