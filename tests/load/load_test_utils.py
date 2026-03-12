"""
Load testing utilities for ag3ntwerk.

Provides tools for simulating concurrent requests, measuring performance,
and stress testing system components.
"""

import asyncio
import time
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RequestResult:
    """Result of a single test request."""

    success: bool
    latency_ms: float
    status_code: Optional[int] = None
    response_data: Any = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class LoadTestResult:
    """Aggregate results from a load test run."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration_seconds: float
    requests_per_second: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    errors: Dict[str, int] = field(default_factory=dict)
    individual_results: List[RequestResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "requests_per_second": round(self.requests_per_second, 2),
            "latency": {
                "avg_ms": round(self.avg_latency_ms, 2),
                "min_ms": round(self.min_latency_ms, 2),
                "max_ms": round(self.max_latency_ms, 2),
                "p50_ms": round(self.p50_latency_ms, 2),
                "p95_ms": round(self.p95_latency_ms, 2),
                "p99_ms": round(self.p99_latency_ms, 2),
            },
            "error_rate": round(self.error_rate, 4),
            "errors": self.errors,
        }

    def print_summary(self):
        """Print a human-readable summary."""
        print("\n" + "=" * 60)
        print("LOAD TEST RESULTS")
        print("=" * 60)
        print(f"Total Requests:      {self.total_requests}")
        print(f"Successful:          {self.successful_requests}")
        print(f"Failed:              {self.failed_requests}")
        print(f"Duration:            {self.total_duration_seconds:.2f}s")
        print(f"Requests/sec:        {self.requests_per_second:.2f}")
        print(f"Error Rate:          {self.error_rate * 100:.2f}%")
        print("-" * 60)
        print("Latency (ms):")
        print(f"  Average:           {self.avg_latency_ms:.2f}")
        print(f"  Min:               {self.min_latency_ms:.2f}")
        print(f"  Max:               {self.max_latency_ms:.2f}")
        print(f"  P50:               {self.p50_latency_ms:.2f}")
        print(f"  P95:               {self.p95_latency_ms:.2f}")
        print(f"  P99:               {self.p99_latency_ms:.2f}")
        if self.errors:
            print("-" * 60)
            print("Errors:")
            for error, count in self.errors.items():
                print(f"  {error}: {count}")
        print("=" * 60 + "\n")


class LoadTester:
    """
    Load testing utility for running concurrent requests.

    Usage:
        tester = LoadTester()

        async def my_request():
            # Your async request logic
            return response

        result = await tester.run(
            request_fn=my_request,
            num_requests=1000,
            concurrency=50,
        )
        result.print_summary()
    """

    def __init__(self, warmup_requests: int = 10):
        """
        Initialize load tester.

        Args:
            warmup_requests: Number of warmup requests before actual test
        """
        self.warmup_requests = warmup_requests

    async def run(
        self,
        request_fn: Callable[[], Coroutine[Any, Any, T]],
        num_requests: int,
        concurrency: int,
        timeout_seconds: float = 30.0,
        warmup: bool = True,
    ) -> LoadTestResult:
        """
        Run a load test with concurrent requests.

        Args:
            request_fn: Async function that performs a single request
            num_requests: Total number of requests to make
            concurrency: Maximum concurrent requests
            timeout_seconds: Timeout for individual requests
            warmup: Whether to run warmup requests first

        Returns:
            LoadTestResult with aggregate statistics
        """
        # Warmup phase
        if warmup and self.warmup_requests > 0:
            logger.info(f"Running {self.warmup_requests} warmup requests...")
            warmup_tasks = [
                self._execute_request(request_fn, timeout_seconds)
                for _ in range(self.warmup_requests)
            ]
            await asyncio.gather(*warmup_tasks, return_exceptions=True)
            logger.info("Warmup complete")

        # Main test phase
        logger.info(f"Starting load test: {num_requests} requests, concurrency={concurrency}")

        semaphore = asyncio.Semaphore(concurrency)
        results: List[RequestResult] = []

        async def limited_request():
            async with semaphore:
                return await self._execute_request(request_fn, timeout_seconds)

        start_time = time.time()
        tasks = [limited_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Process results
        valid_results: List[RequestResult] = []
        for r in results:
            if isinstance(r, RequestResult):
                valid_results.append(r)
            elif isinstance(r, Exception):
                valid_results.append(
                    RequestResult(
                        success=False,
                        latency_ms=0,
                        error=str(r),
                    )
                )

        return self._compute_statistics(valid_results, end_time - start_time)

    async def _execute_request(
        self,
        request_fn: Callable[[], Coroutine[Any, Any, T]],
        timeout_seconds: float,
    ) -> RequestResult:
        """Execute a single request with timing."""
        start = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                request_fn(),
                timeout=timeout_seconds,
            )
            latency_ms = (time.perf_counter() - start) * 1000

            # Handle different return types
            if isinstance(result, RequestResult):
                return result
            elif hasattr(result, "status_code"):
                return RequestResult(
                    success=result.status_code < 400,
                    latency_ms=latency_ms,
                    status_code=result.status_code,
                    response_data=getattr(result, "json", lambda: None)(),
                )
            else:
                return RequestResult(
                    success=True,
                    latency_ms=latency_ms,
                    response_data=result,
                )
        except asyncio.TimeoutError:
            return RequestResult(
                success=False,
                latency_ms=(time.perf_counter() - start) * 1000,
                error="Timeout",
            )
        except Exception as e:
            return RequestResult(
                success=False,
                latency_ms=(time.perf_counter() - start) * 1000,
                error=str(e),
            )

    def _compute_statistics(
        self,
        results: List[RequestResult],
        total_duration: float,
    ) -> LoadTestResult:
        """Compute aggregate statistics from results."""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        latencies = [r.latency_ms for r in results if r.latency_ms > 0]

        if not latencies:
            latencies = [0]

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        # Compute percentiles
        def percentile(p: float) -> float:
            idx = int(n * p)
            return sorted_latencies[min(idx, n - 1)]

        # Count errors
        error_counts: Dict[str, int] = {}
        for r in failed:
            error = r.error or "Unknown"
            error_counts[error] = error_counts.get(error, 0) + 1

        return LoadTestResult(
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            total_duration_seconds=total_duration,
            requests_per_second=len(results) / total_duration if total_duration > 0 else 0,
            avg_latency_ms=statistics.mean(latencies),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            p50_latency_ms=percentile(0.50),
            p95_latency_ms=percentile(0.95),
            p99_latency_ms=percentile(0.99),
            error_rate=len(failed) / len(results) if results else 0,
            errors=error_counts,
            individual_results=results,
        )


class StressTester:
    """
    Stress testing utility that gradually increases load.

    Ramps up from initial concurrency to max concurrency,
    monitoring for degradation points.
    """

    def __init__(self):
        self.load_tester = LoadTester(warmup_requests=5)

    async def run_ramp_test(
        self,
        request_fn: Callable[[], Coroutine[Any, Any, Any]],
        requests_per_level: int = 100,
        initial_concurrency: int = 10,
        max_concurrency: int = 200,
        step_size: int = 20,
        acceptable_error_rate: float = 0.05,
        max_acceptable_latency_ms: float = 5000,
    ) -> Dict[str, Any]:
        """
        Run a stress test that ramps up concurrency.

        Args:
            request_fn: Async function for requests
            requests_per_level: Requests to run at each concurrency level
            initial_concurrency: Starting concurrency
            max_concurrency: Maximum concurrency to test
            step_size: Concurrency increase per step
            acceptable_error_rate: Stop if error rate exceeds this
            max_acceptable_latency_ms: Stop if p95 latency exceeds this

        Returns:
            Dict with results at each level and breaking point info
        """
        results: List[Dict[str, Any]] = []
        breaking_point: Optional[int] = None
        breaking_reason: Optional[str] = None

        concurrency = initial_concurrency

        while concurrency <= max_concurrency:
            logger.info(f"Testing concurrency level: {concurrency}")

            result = await self.load_tester.run(
                request_fn=request_fn,
                num_requests=requests_per_level,
                concurrency=concurrency,
                warmup=False,
            )

            level_result = {
                "concurrency": concurrency,
                "results": result.to_dict(),
            }
            results.append(level_result)

            # Check for breaking point
            if result.error_rate > acceptable_error_rate:
                breaking_point = concurrency
                breaking_reason = f"Error rate {result.error_rate:.2%} exceeded threshold {acceptable_error_rate:.2%}"
                logger.warning(f"Breaking point found: {breaking_reason}")
                break

            if result.p95_latency_ms > max_acceptable_latency_ms:
                breaking_point = concurrency
                breaking_reason = f"P95 latency {result.p95_latency_ms:.0f}ms exceeded threshold {max_acceptable_latency_ms:.0f}ms"
                logger.warning(f"Breaking point found: {breaking_reason}")
                break

            concurrency += step_size

        return {
            "levels": results,
            "breaking_point": breaking_point,
            "breaking_reason": breaking_reason,
            "max_successful_concurrency": (
                breaking_point - step_size if breaking_point else max_concurrency
            ),
        }


@asynccontextmanager
async def timed_section(name: str):
    """Context manager for timing code sections."""
    start = time.perf_counter()
    logger.info(f"Starting: {name}")
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        logger.info(f"Completed: {name} in {duration:.3f}s")


class PerformanceBenchmark:
    """
    Benchmark utility for measuring component performance.
    """

    def __init__(self):
        self.results: Dict[str, List[float]] = {}

    async def measure(
        self,
        name: str,
        fn: Callable[[], Coroutine[Any, Any, Any]],
        iterations: int = 100,
    ) -> Dict[str, float]:
        """
        Measure performance of a function over multiple iterations.

        Returns dict with timing statistics.
        """
        times: List[float] = []

        for _ in range(iterations):
            start = time.perf_counter()
            await fn()
            times.append((time.perf_counter() - start) * 1000)

        self.results[name] = times

        return {
            "name": name,
            "iterations": iterations,
            "avg_ms": statistics.mean(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0,
        }

    def summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of all benchmarks."""
        return {
            name: {
                "avg_ms": statistics.mean(times),
                "min_ms": min(times),
                "max_ms": max(times),
            }
            for name, times in self.results.items()
        }
