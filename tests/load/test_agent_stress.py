"""
Stress tests for ag3ntwerk agent systems.

Tests agent task processing under concurrent load, measuring:
- Task queue handling capacity
- Agent response times under load
- Memory usage patterns
- Resource contention handling
"""

import asyncio
import pytest
import time
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.core.base import Task, TaskResult, TaskPriority
from ag3ntwerk.orchestration.registry import AgentRegistry

from .load_test_utils import LoadTester, PerformanceBenchmark, RequestResult


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider that simulates variable latency."""
    provider = MagicMock()
    provider.name = "MockLLM"
    provider._is_connected = True

    async def mock_generate(prompt, **kwargs):
        # Simulate variable processing time (10-50ms)
        await asyncio.sleep(0.01 + 0.04 * (hash(prompt) % 100) / 100)
        return MagicMock(
            content="Mock response",
            model="mock-model",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            latency_ms=25.0,
        )

    async def mock_chat(messages, **kwargs):
        await asyncio.sleep(0.01 + 0.04 * (hash(str(messages)) % 100) / 100)
        return MagicMock(
            content="Mock chat response",
            model="mock-model",
            finish_reason="stop",
            usage={"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
            latency_ms=30.0,
        )

    provider.generate = mock_generate
    provider.chat = mock_chat
    provider.connect = AsyncMock(return_value=True)
    provider.disconnect = AsyncMock()

    return provider


@pytest.fixture
def task_factory():
    """Factory for creating test tasks."""
    counter = 0

    def create_task(
        priority: TaskPriority = TaskPriority.MEDIUM,
        task_type: str = "test",
    ) -> Task:
        nonlocal counter
        counter += 1
        return Task(
            description=f"Stress test task {counter}",
            task_type=task_type,
            priority=priority,
            context={"test_id": counter},
        )

    return create_task


class TestTaskQueueStress:
    """Stress tests for task queue handling."""

    @pytest.mark.asyncio
    async def test_concurrent_task_creation(self, task_factory):
        """Test creating many tasks concurrently."""
        num_tasks = 1000
        tasks: List[Task] = []

        async def create_task():
            task = task_factory()
            tasks.append(task)
            return task

        start = time.perf_counter()
        await asyncio.gather(*[create_task() for _ in range(num_tasks)])
        duration = time.perf_counter() - start

        print(f"\nCreated {num_tasks} tasks in {duration:.3f}s")
        print(f"Rate: {num_tasks / duration:.0f} tasks/second")

        assert len(tasks) == num_tasks
        assert duration < 5.0, "Task creation should be fast"

        # Verify all tasks have unique IDs
        ids = [t.id for t in tasks]
        assert len(set(ids)) == num_tasks, "All task IDs should be unique"

    @pytest.mark.asyncio
    async def test_priority_queue_ordering(self, task_factory):
        """Test that priority queue maintains correct ordering."""
        import heapq

        # Create tasks with different priorities
        tasks = []
        for priority in [
            TaskPriority.LOW,
            TaskPriority.MEDIUM,
            TaskPriority.HIGH,
            TaskPriority.CRITICAL,
        ]:
            for _ in range(25):
                tasks.append(task_factory(priority=priority))

        # Simulate priority queue processing
        heap = [(t.priority.value, t.created_at.timestamp(), t) for t in tasks]
        heapq.heapify(heap)

        processed_order = []
        while heap:
            _, _, task = heapq.heappop(heap)
            processed_order.append(task)

        # Verify CRITICAL tasks (value 4) processed first (highest value = highest priority)
        critical_tasks = [t for t in processed_order[:25]]
        assert all(
            t.priority == TaskPriority.CRITICAL for t in critical_tasks
        ), "Critical tasks should be processed first"


class TestAgentConcurrency:
    """Tests for agent concurrent execution."""

    @pytest.mark.asyncio
    async def test_mock_agent_concurrent_execution(self, mock_llm_provider, task_factory):
        """Test agent handling concurrent task execution."""
        from ag3ntwerk.core.base import Specialist

        class TestSpecialist(Specialist):
            def __init__(self, llm_provider):
                super().__init__(
                    code="TEST",
                    name="Test Specialist",
                    domain="Testing",
                    capabilities=["test"],
                    llm_provider=llm_provider,
                )
                self.execution_count = 0
                self.concurrent_executions = 0
                self.max_concurrent = 0
                self._lock = asyncio.Lock()

            async def execute(self, task: Task) -> TaskResult:
                async with self._lock:
                    self.concurrent_executions += 1
                    self.max_concurrent = max(self.max_concurrent, self.concurrent_executions)

                try:
                    # Simulate work
                    await asyncio.sleep(0.01)
                    self.execution_count += 1
                    return TaskResult(
                        task_id=task.id,
                        success=True,
                        output={"result": "completed"},
                    )
                finally:
                    async with self._lock:
                        self.concurrent_executions -= 1

        agent = TestSpecialist(mock_llm_provider)

        # Execute many tasks concurrently
        num_tasks = 100
        tasks = [task_factory(task_type="test") for _ in range(num_tasks)]

        start = time.perf_counter()
        results = await asyncio.gather(*[agent.execute(t) for t in tasks])
        duration = time.perf_counter() - start

        print(f"\nExecuted {num_tasks} tasks in {duration:.3f}s")
        print(f"Rate: {num_tasks / duration:.0f} tasks/second")
        print(f"Max concurrent executions: {agent.max_concurrent}")

        assert all(r.success for r in results)
        assert agent.execution_count == num_tasks

    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self, mock_llm_provider, task_factory):
        """Test agent handling of slow/timing out tasks."""
        from ag3ntwerk.core.base import Specialist

        class SlowSpecialist(Specialist):
            def __init__(self, llm_provider):
                super().__init__(
                    code="SLOW",
                    name="Slow Specialist",
                    domain="Testing",
                    capabilities=["slow"],
                    llm_provider=llm_provider,
                )

            async def execute(self, task: Task) -> TaskResult:
                # Simulate slow processing
                delay = task.context.get("delay", 0.1)
                await asyncio.sleep(delay)
                return TaskResult(
                    task_id=task.id,
                    success=True,
                    output={"result": "completed"},
                )

        agent = SlowSpecialist(mock_llm_provider)

        # Create tasks with varying delays
        tasks = []
        for i in range(20):
            task = task_factory(task_type="slow")
            task.context["delay"] = 0.01 * (i % 5)  # 0-40ms delay
            tasks.append(task)

        # Execute with timeout
        async def execute_with_timeout(task):
            try:
                return await asyncio.wait_for(
                    agent.execute(task),
                    timeout=0.025,  # 25ms timeout
                )
            except asyncio.TimeoutError:
                return TaskResult(
                    task_id=task.id,
                    success=False,
                    error="Timeout",
                )

        results = await asyncio.gather(*[execute_with_timeout(t) for t in tasks])

        successful = sum(1 for r in results if r.success)
        timed_out = sum(1 for r in results if not r.success)

        print(f"\nSuccessful: {successful}, Timed out: {timed_out}")

        # Some tasks should timeout (those with delay > 25ms)
        assert timed_out > 0, "Some tasks should timeout"
        assert successful > 0, "Some tasks should succeed"


class TestMemoryPressure:
    """Tests for memory handling under load."""

    @pytest.mark.asyncio
    async def test_large_context_handling(self, task_factory):
        """Test handling tasks with large context data."""
        import sys

        # Create tasks with progressively larger contexts
        sizes = [1_000, 10_000, 100_000, 1_000_000]  # bytes
        results = []

        for size in sizes:
            task = task_factory()
            task.context["large_data"] = "x" * size

            memory_before = sys.getsizeof(task)

            # Verify task can be created and serialized
            serialized = task.to_dict()

            results.append(
                {
                    "size": size,
                    "memory": memory_before,
                    "serialized_ok": "large_data" in serialized.get("context", {}),
                }
            )

        for r in results:
            print(f"Size: {r['size']:,} bytes, Memory: {r['memory']:,} bytes")
            assert r["serialized_ok"], f"Failed to serialize task with {r['size']} bytes context"

    @pytest.mark.asyncio
    async def test_result_accumulation(self, task_factory):
        """Test memory behavior when accumulating many results."""
        import gc

        results: List[TaskResult] = []
        num_results = 10000

        gc.collect()
        # Memory measurement is platform-dependent, so we just verify correctness

        for i in range(num_results):
            results.append(
                TaskResult(
                    task_id=f"task-{i}",
                    success=True,
                    output={"iteration": i, "data": "x" * 100},
                )
            )

        assert len(results) == num_results

        # Clear and collect
        results.clear()
        gc.collect()


class TestResourceContention:
    """Tests for resource contention scenarios."""

    @pytest.mark.asyncio
    async def test_shared_lock_contention(self):
        """Test performance under lock contention."""
        lock = asyncio.Lock()
        counter = 0
        acquisition_times: List[float] = []

        async def increment():
            nonlocal counter
            start = time.perf_counter()
            async with lock:
                acquisition_time = time.perf_counter() - start
                acquisition_times.append(acquisition_time)
                counter += 1
                # Simulate some work
                await asyncio.sleep(0.001)

        num_operations = 500
        start = time.perf_counter()
        await asyncio.gather(*[increment() for _ in range(num_operations)])
        duration = time.perf_counter() - start

        print(f"\n{num_operations} lock operations in {duration:.3f}s")
        print(
            f"Avg lock acquisition time: {sum(acquisition_times)/len(acquisition_times)*1000:.3f}ms"
        )
        print(f"Max lock acquisition time: {max(acquisition_times)*1000:.3f}ms")

        assert counter == num_operations

    @pytest.mark.asyncio
    async def test_semaphore_rate_limiting(self):
        """Test semaphore-based rate limiting under load."""
        max_concurrent = 10
        semaphore = asyncio.Semaphore(max_concurrent)

        current_concurrent = 0
        max_observed_concurrent = 0
        lock = asyncio.Lock()

        async def rate_limited_operation():
            nonlocal current_concurrent, max_observed_concurrent

            async with semaphore:
                async with lock:
                    current_concurrent += 1
                    max_observed_concurrent = max(max_observed_concurrent, current_concurrent)

                await asyncio.sleep(0.01)

                async with lock:
                    current_concurrent -= 1

        num_operations = 200
        await asyncio.gather(*[rate_limited_operation() for _ in range(num_operations)])

        print(f"\nMax concurrent operations: {max_observed_concurrent}")
        assert max_observed_concurrent <= max_concurrent, "Semaphore should limit concurrency"


class TestAgentStressBenchmarks:
    """Performance benchmarks for agent operations."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_benchmark_task_creation(self):
        """Benchmark task creation performance."""
        benchmark = PerformanceBenchmark()

        async def create_task():
            return Task(
                description="Benchmark task",
                task_type="benchmark",
                priority=TaskPriority.MEDIUM,
                context={"key": "value"},
            )

        results = await benchmark.measure(
            name="task_creation",
            fn=create_task,
            iterations=1000,
        )

        print(f"\nTask Creation Benchmark:")
        print(f"  Average: {results['avg_ms']:.4f}ms")
        print(f"  Min: {results['min_ms']:.4f}ms")
        print(f"  Max: {results['max_ms']:.4f}ms")

        # Task creation should be very fast
        assert results["avg_ms"] < 1.0, "Task creation should be < 1ms"

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_benchmark_result_creation(self):
        """Benchmark result creation performance."""
        benchmark = PerformanceBenchmark()

        async def create_result():
            return TaskResult(
                task_id="benchmark-task",
                success=True,
                output={"result": "completed", "metrics": {"accuracy": 0.95}},
            )

        results = await benchmark.measure(
            name="result_creation",
            fn=create_result,
            iterations=1000,
        )

        print(f"\nResult Creation Benchmark:")
        print(f"  Average: {results['avg_ms']:.4f}ms")
        print(f"  Min: {results['min_ms']:.4f}ms")
        print(f"  Max: {results['max_ms']:.4f}ms")

        assert results["avg_ms"] < 1.0, "Result creation should be < 1ms"
