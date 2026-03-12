"""
Health Check Aggregation for ag3ntwerk.

Provides a comprehensive health check system that aggregates health status
from multiple subsystems and services.

Usage:
    from ag3ntwerk.core.health import (
        HealthAggregator,
        HealthStatus,
        register_health_check,
        get_aggregated_health,
    )

    # Register a health check
    @register_health_check("database")
    async def check_database():
        # Return True/False or raise exception
        return await db.ping()

    # Get aggregated health
    health = await get_aggregated_health()
    print(health.status)  # HealthStatus.HEALTHY
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional
import time

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Overall health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Some non-critical checks failing
    UNHEALTHY = "unhealthy"  # Critical checks failing
    UNKNOWN = "unknown"  # Unable to determine health


class CheckStatus(Enum):
    """Individual check status."""

    PASSING = "passing"
    WARNING = "warning"
    FAILING = "failing"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: CheckStatus
    message: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    critical: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2),
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "critical": self.critical,
        }


@dataclass
class AggregatedHealth:
    """Aggregated health status from all checks."""

    status: HealthStatus
    checks: List[HealthCheckResult]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"
    uptime_seconds: float = 0.0

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    @property
    def summary(self) -> Dict[str, int]:
        """Summary count of check statuses."""
        counts = {s.value: 0 for s in CheckStatus}
        for check in self.checks:
            counts[check.status.value] += 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "summary": self.summary,
            "checks": [c.to_dict() for c in self.checks],
        }


# Type alias for health check functions
HealthCheckFunc = Callable[[], Coroutine[Any, Any, bool | Dict[str, Any]]]


@dataclass
class HealthCheck:
    """Registered health check."""

    name: str
    func: HealthCheckFunc
    critical: bool = False
    timeout: float = 5.0
    interval: float = 30.0  # How often to run (for caching)
    description: str = ""


class HealthAggregator:
    """
    Aggregates health checks from multiple subsystems.

    Usage:
        aggregator = HealthAggregator()

        # Register checks
        aggregator.register("ollama", check_ollama, critical=True)
        aggregator.register("cache", check_cache, critical=False)

        # Get health
        health = await aggregator.check_health()
    """

    def __init__(self, version: str = "1.0.0"):
        self._checks: Dict[str, HealthCheck] = {}
        self._cache: Dict[str, HealthCheckResult] = {}
        self._lock = asyncio.Lock()
        self._start_time = datetime.now(timezone.utc)
        self._version = version

    def register(
        self,
        name: str,
        func: HealthCheckFunc,
        critical: bool = False,
        timeout: float = 5.0,
        interval: float = 30.0,
        description: str = "",
    ) -> None:
        """
        Register a health check.

        Args:
            name: Unique name for the check
            func: Async function that returns True/False or dict with status info
            critical: If True, failure means system is unhealthy
            timeout: Maximum time to wait for check (seconds)
            interval: Cache interval (seconds)
            description: Human-readable description
        """
        self._checks[name] = HealthCheck(
            name=name,
            func=func,
            critical=critical,
            timeout=timeout,
            interval=interval,
            description=description,
        )
        logger.debug(f"Registered health check: {name} (critical={critical})")

    def unregister(self, name: str) -> None:
        """Unregister a health check."""
        if name in self._checks:
            del self._checks[name]
            if name in self._cache:
                del self._cache[name]
            logger.debug(f"Unregistered health check: {name}")

    async def run_check(self, check: HealthCheck) -> HealthCheckResult:
        """Run a single health check."""
        start_time = time.time()

        try:
            # Run with timeout
            result = await asyncio.wait_for(check.func(), timeout=check.timeout)
            latency_ms = (time.time() - start_time) * 1000

            # Handle different return types
            if isinstance(result, bool):
                if result:
                    return HealthCheckResult(
                        name=check.name,
                        status=CheckStatus.PASSING,
                        message="Check passed",
                        latency_ms=latency_ms,
                        critical=check.critical,
                    )
                else:
                    return HealthCheckResult(
                        name=check.name,
                        status=CheckStatus.FAILING,
                        message="Check failed",
                        latency_ms=latency_ms,
                        critical=check.critical,
                    )
            elif isinstance(result, dict):
                # Dict result with optional status, message, details
                status_str = result.get("status", "passing").lower()
                status_map = {
                    "passing": CheckStatus.PASSING,
                    "pass": CheckStatus.PASSING,
                    "ok": CheckStatus.PASSING,
                    "healthy": CheckStatus.PASSING,
                    "warning": CheckStatus.WARNING,
                    "warn": CheckStatus.WARNING,
                    "degraded": CheckStatus.WARNING,
                    "failing": CheckStatus.FAILING,
                    "fail": CheckStatus.FAILING,
                    "unhealthy": CheckStatus.FAILING,
                    "error": CheckStatus.FAILING,
                }
                status = status_map.get(status_str, CheckStatus.UNKNOWN)

                return HealthCheckResult(
                    name=check.name,
                    status=status,
                    message=result.get("message", ""),
                    latency_ms=latency_ms,
                    details=result.get("details", {}),
                    critical=check.critical,
                )
            else:
                # Truthy/falsy
                status = CheckStatus.PASSING if result else CheckStatus.FAILING
                return HealthCheckResult(
                    name=check.name,
                    status=status,
                    latency_ms=latency_ms,
                    critical=check.critical,
                )

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=check.name,
                status=CheckStatus.TIMEOUT,
                message=f"Check timed out after {check.timeout}s",
                latency_ms=latency_ms,
                critical=check.critical,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(
                f"Health check '{check.name}' failed with exception",
                exc_info=True,
            )
            return HealthCheckResult(
                name=check.name,
                status=CheckStatus.FAILING,
                message=str(e),
                latency_ms=latency_ms,
                details={"error_type": type(e).__name__},
                critical=check.critical,
            )

    def _is_cache_valid(self, name: str) -> bool:
        """Check if cached result is still valid."""
        if name not in self._cache:
            return False

        check = self._checks.get(name)
        if not check:
            return False

        cached = self._cache[name]
        age = (datetime.now(timezone.utc) - cached.timestamp).total_seconds()
        return age < check.interval

    async def check_health(
        self,
        force_refresh: bool = False,
        include_details: bool = True,
    ) -> AggregatedHealth:
        """
        Run all health checks and aggregate results.

        Args:
            force_refresh: Ignore cache and run all checks
            include_details: Include detailed check results

        Returns:
            AggregatedHealth with aggregated status
        """
        async with self._lock:
            results: List[HealthCheckResult] = []

            # Run checks in parallel
            tasks = []
            check_names = []

            for name, check in self._checks.items():
                if not force_refresh and self._is_cache_valid(name):
                    results.append(self._cache[name])
                else:
                    tasks.append(self.run_check(check))
                    check_names.append(name)

            # Execute parallel checks
            if tasks:
                check_results = await asyncio.gather(*tasks, return_exceptions=True)

                for name, result in zip(check_names, check_results):
                    if isinstance(result, Exception):
                        result = HealthCheckResult(
                            name=name,
                            status=CheckStatus.FAILING,
                            message=str(result),
                            critical=self._checks[name].critical,
                        )

                    self._cache[name] = result
                    results.append(result)

            # Determine overall status
            status = self._calculate_status(results)

            # Calculate uptime
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()

            return AggregatedHealth(
                status=status,
                checks=results if include_details else [],
                version=self._version,
                uptime_seconds=uptime,
            )

    def _calculate_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Calculate overall status from check results."""
        if not results:
            return HealthStatus.UNKNOWN

        critical_failing = False
        any_failing = False
        any_warning = False

        for result in results:
            if result.status in (CheckStatus.FAILING, CheckStatus.TIMEOUT):
                if result.critical:
                    critical_failing = True
                any_failing = True
            elif result.status == CheckStatus.WARNING:
                any_warning = True

        if critical_failing:
            return HealthStatus.UNHEALTHY
        elif any_failing or any_warning:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    async def check_readiness(self) -> bool:
        """
        Quick readiness check - are critical systems ready?

        Use for Kubernetes readiness probes.
        """
        for name, check in self._checks.items():
            if check.critical:
                result = await self.run_check(check)
                if result.status in (CheckStatus.FAILING, CheckStatus.TIMEOUT):
                    return False
        return True

    async def check_liveness(self) -> bool:
        """
        Quick liveness check - is the service alive?

        Use for Kubernetes liveness probes.
        """
        # Liveness is simpler - just return True if we can respond
        return True


# Global aggregator instance
_global_aggregator: Optional[HealthAggregator] = None


def get_health_aggregator() -> HealthAggregator:
    """Get the global health aggregator."""
    global _global_aggregator
    if _global_aggregator is None:
        _global_aggregator = HealthAggregator()
    return _global_aggregator


def register_health_check(
    name: str,
    critical: bool = False,
    timeout: float = 5.0,
    interval: float = 30.0,
    description: str = "",
) -> Callable[[HealthCheckFunc], HealthCheckFunc]:
    """
    Decorator to register a health check function.

    Usage:
        @register_health_check("database", critical=True)
        async def check_database():
            return await db.ping()
    """

    def decorator(func: HealthCheckFunc) -> HealthCheckFunc:
        aggregator = get_health_aggregator()
        aggregator.register(
            name=name,
            func=func,
            critical=critical,
            timeout=timeout,
            interval=interval,
            description=description,
        )
        return func

    return decorator


async def get_aggregated_health(
    force_refresh: bool = False,
    include_details: bool = True,
) -> AggregatedHealth:
    """Get aggregated health from global aggregator."""
    return await get_health_aggregator().check_health(
        force_refresh=force_refresh,
        include_details=include_details,
    )


async def check_readiness() -> bool:
    """Check if the service is ready."""
    return await get_health_aggregator().check_readiness()


async def check_liveness() -> bool:
    """Check if the service is alive."""
    return await get_health_aggregator().check_liveness()


__all__ = [
    # Enums
    "HealthStatus",
    "CheckStatus",
    # Data classes
    "HealthCheckResult",
    "AggregatedHealth",
    "HealthCheck",
    # Main class
    "HealthAggregator",
    # Functions
    "get_health_aggregator",
    "register_health_check",
    "get_aggregated_health",
    "check_readiness",
    "check_liveness",
]
