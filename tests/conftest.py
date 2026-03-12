"""
Pytest configuration and shared fixtures for ag3ntwerk tests.
"""

import asyncio
import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.core.base import Task, TaskResult, TaskPriority, TaskStatus
from ag3ntwerk.llm.base import LLMProvider, LLMResponse, Message, ModelInfo, ModelTier


# =============================================================================
# Event Loop Fixture
# =============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Mock LLM Provider
# =============================================================================


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(
        self,
        name: str = "MockLLM",
        models: Optional[List[ModelInfo]] = None,
        default_response: str = "Mock response",
    ):
        super().__init__(name)
        self._models = models or [
            ModelInfo(
                id="mock-model",
                name="Mock Model",
                tier=ModelTier.BALANCED,
                context_length=4096,
                capabilities=["chat", "completion"],
            )
        ]
        self.default_response = default_response
        self.call_history: List[Dict[str, Any]] = []

    async def connect(self) -> bool:
        self._is_connected = True
        self._available_models = self._models
        return True

    async def disconnect(self) -> None:
        self._is_connected = False

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        self.call_history.append(
            {
                "method": "generate",
                "prompt": prompt,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        return LLMResponse(
            content=self.default_response,
            model=model or "mock-model",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            latency_ms=100.0,
        )

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        self.call_history.append(
            {
                "method": "chat",
                "messages": [m.to_dict() for m in messages],
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        return LLMResponse(
            content=self.default_response,
            model=model or "mock-model",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            latency_ms=100.0,
        )

    async def list_models(self) -> List[ModelInfo]:
        return self._models


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider for testing."""
    return MockLLMProvider()


@pytest.fixture
def mock_llm_with_models():
    """Create mock LLM with multiple models."""
    models = [
        ModelInfo(
            id="fast-model",
            name="Fast Model",
            tier=ModelTier.FAST,
            context_length=2048,
        ),
        ModelInfo(
            id="balanced-model",
            name="Balanced Model",
            tier=ModelTier.BALANCED,
            context_length=4096,
        ),
        ModelInfo(
            id="code-model",
            name="Code Model",
            tier=ModelTier.SPECIALIZED,
            context_length=8192,
            capabilities=["code", "code-completion"],
        ),
    ]
    return MockLLMProvider(models=models)


# =============================================================================
# Task Fixtures
# =============================================================================


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        description="Test task description",
        task_type="test_type",
        priority=TaskPriority.MEDIUM,
        context={"test_key": "test_value"},
    )


@pytest.fixture
def high_priority_task():
    """Create a high priority task."""
    return Task(
        description="Urgent task",
        task_type="urgent",
        priority=TaskPriority.HIGH,
        context={"urgent": True},
    )


@pytest.fixture
def security_task():
    """Create a security-related task."""
    return Task(
        description="Perform security scan",
        task_type="security_scan",
        priority=TaskPriority.HIGH,
        context={"target": "/app"},
    )


@pytest.fixture
def code_task():
    """Create a code-related task."""
    return Task(
        description="Review code changes",
        task_type="code_review",
        priority=TaskPriority.MEDIUM,
        context={"files": ["main.py", "utils.py"]},
    )


# =============================================================================
# Agent Fixtures
# =============================================================================


@pytest.fixture
def mock_specialist():
    """Create a mock specialist agent."""
    from ag3ntwerk.core.base import Specialist

    class MockSpecialist(Specialist):
        def __init__(self, llm_provider=None):
            super().__init__(
                code="SPEC",
                name="Mock Specialist",
                domain="Testing",
                capabilities=["test_type", "analysis"],
                llm_provider=llm_provider,
            )
            self.executed_tasks = []

        async def execute(self, task: Task) -> TaskResult:
            self.executed_tasks.append(task)
            return TaskResult(
                task_id=task.id,
                success=True,
                output={"result": "completed"},
            )

    return MockSpecialist


@pytest.fixture
def mock_manager(mock_llm_provider):
    """Create a mock manager agent."""
    from ag3ntwerk.core.base import Manager

    class MockManager(Manager):
        def __init__(self, llm_provider=None):
            super().__init__(
                code="MGR",
                name="Mock Manager",
                domain="Testing",
                llm_provider=llm_provider,
            )
            self.executed_tasks = []

        def can_handle(self, task: Task) -> bool:
            return task.task_type in ["test_type", "management"]

        async def execute(self, task: Task) -> TaskResult:
            self.executed_tasks.append(task)

            # Try to delegate to subordinates
            best_agent = await self.find_best_agent(task)
            if best_agent:
                return await self.delegate(task, best_agent)

            return TaskResult(
                task_id=task.id,
                success=True,
                output={"handled_by": self.code},
            )

    return MockManager(llm_provider=mock_llm_provider)


# =============================================================================
# State Store Fixtures
# =============================================================================


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_state.db"


@pytest.fixture
async def state_store(temp_db_path):
    """Create and initialize a state store."""
    from ag3ntwerk.memory.state_store import StateStore

    store = StateStore(db_path=temp_db_path)
    await store.initialize()
    yield store
    await store.close()


# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def test_config():
    """Sample test configuration."""
    return {
        "llm": {
            "provider": "ollama",
            "ollama": {
                "base_url": "http://localhost:11434",
                "timeout": 60.0,
            },
        },
        "agents": {
            "coo": {"enabled": True},
            "cio": {"enabled": True},
            "cto": {"enabled": True},
        },
        "tasks": {
            "default_timeout": 30.0,
            "max_retries": 3,
        },
    }


# =============================================================================
# Helper Functions
# =============================================================================


def create_task_result(
    task_id: str,
    success: bool = True,
    output: Any = None,
    error: Optional[str] = None,
) -> TaskResult:
    """Helper to create task results."""
    return TaskResult(
        task_id=task_id,
        success=success,
        output=output,
        error=error,
    )


# =============================================================================
# Test Markers and Configuration
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "load: marks tests as load tests")
    config.addinivalue_line("markers", "benchmark: marks tests as benchmarks")
    config.addinivalue_line("markers", "stress: marks tests as stress tests")
    config.addinivalue_line("markers", "redis: marks tests that require Redis")


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on location."""
    for item in items:
        # Auto-mark tests in load/ directory
        if "load" in str(item.fspath):
            item.add_marker(pytest.mark.load)

        # Auto-mark tests in integration/ directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# =============================================================================
# Performance Testing Fixtures
# =============================================================================


@pytest.fixture
def timer():
    """Fixture for timing test sections."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None

        def start(self):
            self.start_time = time.perf_counter()
            return self

        def stop(self):
            if self.start_time:
                self.elapsed = time.perf_counter() - self.start_time
            return self.elapsed

        def __enter__(self):
            self.start()
            return self

        def __exit__(self, *args):
            self.stop()

    return Timer()


@pytest.fixture
def async_timer():
    """Fixture for timing async operations."""
    import time

    class AsyncTimer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None

        async def __aenter__(self):
            self.start_time = time.perf_counter()
            return self

        async def __aexit__(self, *args):
            self.elapsed = time.perf_counter() - self.start_time

    return AsyncTimer()


# =============================================================================
# Async Test Helpers
# =============================================================================


@pytest.fixture
def run_with_timeout():
    """Fixture for running async operations with timeout."""

    async def _run_with_timeout(coro, timeout: float = 5.0):
        import asyncio

        return await asyncio.wait_for(coro, timeout=timeout)

    return _run_with_timeout


@pytest.fixture
def assert_completes_within():
    """Fixture for asserting operation completes within time limit."""

    async def _assert_completes_within(coro, max_seconds: float):
        import asyncio
        import time

        start = time.perf_counter()
        try:
            result = await asyncio.wait_for(coro, timeout=max_seconds)
            elapsed = time.perf_counter() - start
            return result, elapsed
        except asyncio.TimeoutError:
            elapsed = time.perf_counter() - start
            pytest.fail(
                f"Operation did not complete within {max_seconds}s (elapsed: {elapsed:.2f}s)"
            )

    return _assert_completes_within


# =============================================================================
# Redis Fixtures (for Nexus-ag3ntwerk bridge integration tests)
# =============================================================================


def is_redis_available(url: str = "redis://localhost:6379") -> bool:
    """Check if Redis is available at the given URL."""
    try:
        import redis

        r = redis.from_url(url)
        r.ping()
        r.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def redis_available():
    """Check if Redis is available for tests."""
    return is_redis_available()


@pytest.fixture
def redis_url():
    """Redis connection URL for tests."""
    return "redis://localhost:6379"


@pytest.fixture
def redis_channel_prefix():
    """Unique channel prefix for test isolation."""
    import uuid

    return f"ag3ntwerk:test:{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def redis_client(redis_url, redis_available):
    """
    Create an async Redis client for tests.

    Skips the test if Redis is not available.
    """
    if not redis_available:
        pytest.skip("Redis not available")

    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(redis_url)
        await client.ping()
        yield client
        await client.close()
    except ImportError:
        pytest.skip("redis package not installed")
    except Exception as e:
        pytest.skip(f"Could not connect to Redis: {e}")


@pytest.fixture
async def clean_redis_channels(redis_client, redis_channel_prefix):
    """
    Clean up Redis channels after test.

    This fixture ensures test isolation by cleaning up any channels
    used during the test.
    """
    yield redis_channel_prefix

    # Clean up after test
    try:
        # Get all keys matching the test prefix
        keys = []
        async for key in redis_client.scan_iter(f"{redis_channel_prefix}:*"):
            keys.append(key)

        if keys:
            await redis_client.delete(*keys)
    except Exception:
        pass  # Best effort cleanup
