"""
Load tests for the ag3ntwerk API.

These tests verify the API can handle concurrent requests and measure performance.
Run with: pytest tests/load/ -v --tb=short

Note: Requires a running API server at http://localhost:3737
"""

import asyncio
import pytest
import httpx
from typing import Optional

from .load_test_utils import LoadTester, StressTester, PerformanceBenchmark, RequestResult


# Configuration
API_BASE_URL = "http://localhost:3737"
TIMEOUT = 30.0


@pytest.fixture
def api_client():
    """Create an async HTTP client for testing."""
    return httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT)


@pytest.fixture
def load_tester():
    """Create a load tester instance."""
    return LoadTester(warmup_requests=5)


@pytest.fixture
def stress_tester():
    """Create a stress tester instance."""
    return StressTester()


class TestHealthEndpointLoad:
    """Load tests for health endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_health_endpoint_load(self, load_tester):
        """Test health endpoint under load."""
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT) as client:

            async def health_request():
                response = await client.get("/health")
                return RequestResult(
                    success=response.status_code == 200,
                    latency_ms=response.elapsed.total_seconds() * 1000,
                    status_code=response.status_code,
                )

            result = await load_tester.run(
                request_fn=health_request,
                num_requests=100,
                concurrency=20,
            )

            result.print_summary()

            # Assertions
            assert result.error_rate < 0.01, "Error rate should be < 1%"
            assert result.p95_latency_ms < 500, "P95 latency should be < 500ms"
            assert result.requests_per_second > 10, "Should handle > 10 req/s"

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_health_endpoint_stress(self, stress_tester):
        """Stress test health endpoint with ramping concurrency."""
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT) as client:

            async def health_request():
                response = await client.get("/health")
                return RequestResult(
                    success=response.status_code == 200,
                    latency_ms=response.elapsed.total_seconds() * 1000,
                    status_code=response.status_code,
                )

            result = await stress_tester.run_ramp_test(
                request_fn=health_request,
                requests_per_level=50,
                initial_concurrency=10,
                max_concurrency=100,
                step_size=20,
            )

            print(f"\nStress Test Results:")
            print(f"Max successful concurrency: {result['max_successful_concurrency']}")
            if result["breaking_point"]:
                print(f"Breaking point: {result['breaking_point']}")
                print(f"Reason: {result['breaking_reason']}")

            # Should handle at least 30 concurrent requests
            assert result["max_successful_concurrency"] >= 30


class TestAgentEndpointLoad:
    """Load tests for agent endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_agents_list_load(self, load_tester):
        """Test agents listing endpoint under load."""
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT) as client:

            async def agents_request():
                response = await client.get("/api/agents")
                return RequestResult(
                    success=response.status_code in (200, 404),  # 404 if no agents
                    latency_ms=response.elapsed.total_seconds() * 1000,
                    status_code=response.status_code,
                )

            result = await load_tester.run(
                request_fn=agents_request,
                num_requests=100,
                concurrency=20,
            )

            result.print_summary()

            assert result.error_rate < 0.05, "Error rate should be < 5%"
            assert result.p95_latency_ms < 1000, "P95 latency should be < 1s"


class TestTaskEndpointLoad:
    """Load tests for task submission endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_task_submission_load(self, load_tester):
        """Test task submission under load."""
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
            task_counter = 0

            async def task_request():
                nonlocal task_counter
                task_counter += 1
                task_data = {
                    "description": f"Load test task {task_counter}",
                    "task_type": "test",
                    "priority": "low",
                }
                response = await client.post("/api/tasks", json=task_data)
                return RequestResult(
                    success=response.status_code in (200, 201, 202, 404),
                    latency_ms=response.elapsed.total_seconds() * 1000,
                    status_code=response.status_code,
                )

            result = await load_tester.run(
                request_fn=task_request,
                num_requests=50,
                concurrency=10,
            )

            result.print_summary()

            # Task submission may be slower due to processing
            assert result.error_rate < 0.10, "Error rate should be < 10%"


class TestChatEndpointLoad:
    """Load tests for chat endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_chat_endpoint_load(self, load_tester):
        """Test chat endpoint under moderate load."""
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as client:

            async def chat_request():
                chat_data = {
                    "message": "What is your status?",
                    "agent": "coo",
                }
                response = await client.post("/api/chat", json=chat_data)
                return RequestResult(
                    success=response.status_code in (200, 201, 404, 503),
                    latency_ms=response.elapsed.total_seconds() * 1000,
                    status_code=response.status_code,
                )

            # Chat is slower due to LLM calls, use lower concurrency
            result = await load_tester.run(
                request_fn=chat_request,
                num_requests=20,
                concurrency=5,
                timeout_seconds=60.0,
            )

            result.print_summary()


class TestMixedWorkloadLoad:
    """Load tests simulating realistic mixed workloads."""

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_mixed_workload(self, load_tester):
        """Test with a mix of different request types."""
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
            import random

            request_counter = 0

            async def mixed_request():
                nonlocal request_counter
                request_counter += 1

                # Simulate realistic request distribution
                # 60% health checks, 30% agent queries, 10% task submission
                rand = random.random()

                if rand < 0.6:
                    response = await client.get("/health")
                elif rand < 0.9:
                    response = await client.get("/api/agents")
                else:
                    response = await client.post(
                        "/api/tasks",
                        json={
                            "description": f"Mixed load task {request_counter}",
                            "task_type": "test",
                        },
                    )

                return RequestResult(
                    success=response.status_code < 500,
                    latency_ms=response.elapsed.total_seconds() * 1000,
                    status_code=response.status_code,
                )

            result = await load_tester.run(
                request_fn=mixed_request,
                num_requests=200,
                concurrency=30,
            )

            result.print_summary()

            assert result.error_rate < 0.05, "Error rate should be < 5%"


class TestPerformanceBenchmarks:
    """Performance benchmarks for critical paths."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_benchmark_health_check(self):
        """Benchmark health check latency."""
        benchmark = PerformanceBenchmark()

        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT) as client:

            async def health_check():
                await client.get("/health")

            results = await benchmark.measure(
                name="health_check",
                fn=health_check,
                iterations=50,
            )

            print(f"\nHealth Check Benchmark:")
            print(f"  Average: {results['avg_ms']:.2f}ms")
            print(f"  Min: {results['min_ms']:.2f}ms")
            print(f"  Max: {results['max_ms']:.2f}ms")
            print(f"  Std Dev: {results['std_dev_ms']:.2f}ms")

            assert results["avg_ms"] < 100, "Average health check should be < 100ms"


# Skip these tests by default (require running server)
def pytest_configure(config):
    config.addinivalue_line("markers", "load: marks tests as load tests (require running server)")
    config.addinivalue_line("markers", "benchmark: marks tests as benchmarks")
