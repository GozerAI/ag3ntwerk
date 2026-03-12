"""
Unit tests for core base classes.

Tests:
- Task and TaskResult dataclasses
- TaskStatus and TaskPriority enums
- Agent base class
- Manager class with delegation
- Specialist class with capabilities
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from ag3ntwerk.core.base import (
    Task,
    TaskResult,
    TaskStatus,
    TaskPriority,
    Agent,
    Manager,
    Specialist,
)


class TestTaskStatus:
    """Test TaskStatus enum."""

    def test_all_statuses_exist(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.DELEGATED.value == "delegated"


class TestTaskPriority:
    """Test TaskPriority enum."""

    def test_priority_ordering(self):
        """Critical should be highest priority (lowest value)."""
        assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.MEDIUM.value
        assert TaskPriority.MEDIUM.value < TaskPriority.LOW.value


class TestTask:
    """Test Task dataclass."""

    def test_task_creation_minimal(self):
        task = Task(description="Test", task_type="test")
        assert task.description == "Test"
        assert task.task_type == "test"
        assert task.priority == TaskPriority.MEDIUM
        assert task.status == TaskStatus.PENDING
        assert task.id is not None
        assert isinstance(task.created_at, datetime)

    def test_task_creation_full(self):
        task = Task(
            description="Full test",
            task_type="full_test",
            priority=TaskPriority.HIGH,
            context={"key": "value"},
            parent_task_id="parent-123",
            metadata={"meta": "data"},
        )
        assert task.priority == TaskPriority.HIGH
        assert task.context == {"key": "value"}
        assert task.parent_task_id == "parent-123"
        assert task.metadata == {"meta": "data"}

    def test_task_to_dict(self):
        task = Task(
            description="Dict test",
            task_type="dict",
            context={"test": True},
        )
        d = task.to_dict()

        assert d["description"] == "Dict test"
        assert d["task_type"] == "dict"
        assert d["priority"] == TaskPriority.MEDIUM.value
        assert d["status"] == TaskStatus.PENDING.value
        assert d["context"] == {"test": True}
        assert "id" in d
        assert "created_at" in d


class TestTaskResult:
    """Test TaskResult dataclass."""

    def test_result_success(self):
        result = TaskResult(
            task_id="task-123",
            success=True,
            output={"data": "result"},
        )
        assert result.task_id == "task-123"
        assert result.success is True
        assert result.output == {"data": "result"}
        assert result.error is None

    def test_result_failure(self):
        result = TaskResult(
            task_id="task-456",
            success=False,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_result_with_metrics(self):
        result = TaskResult(
            task_id="task-789",
            success=True,
            metrics={"duration_ms": 1500, "tokens": 100},
        )
        assert result.metrics["duration_ms"] == 1500
        assert result.metrics["tokens"] == 100

    def test_result_to_dict(self):
        result = TaskResult(
            task_id="task-abc",
            success=True,
            output="done",
        )
        d = result.to_dict()

        assert d["task_id"] == "task-abc"
        assert d["success"] is True
        assert d["output"] == "done"
        assert "completed_at" in d


class TestSpecialist:
    """Test Specialist agent class."""

    def test_specialist_creation(self):
        specialist = create_test_specialist()
        assert specialist.code == "TEST"
        assert specialist.name == "Test Specialist"
        assert specialist.capabilities == ["test", "analyze"]

    def test_specialist_can_handle(self):
        specialist = create_test_specialist()
        task_handled = Task(description="Test", task_type="test")
        task_not_handled = Task(description="Other", task_type="other")

        assert specialist.can_handle(task_handled) is True
        assert specialist.can_handle(task_not_handled) is False

    def test_add_capability(self):
        specialist = create_test_specialist()
        specialist.add_capability("new_capability")
        assert "new_capability" in specialist.capabilities

    def test_add_duplicate_capability(self):
        specialist = create_test_specialist()
        initial_count = len(specialist.capabilities)
        specialist.add_capability("test")  # Already exists
        assert len(specialist.capabilities) == initial_count

    def test_remove_capability(self):
        specialist = create_test_specialist()
        specialist.remove_capability("analyze")
        assert "analyze" not in specialist.capabilities

    @pytest.mark.asyncio
    async def test_specialist_execute(self):
        specialist = create_test_specialist()
        task = Task(description="Execute test", task_type="test")
        result = await specialist.execute(task)

        assert result.task_id == task.id
        assert result.success is True


class TestManager:
    """Test Manager agent class."""

    def test_manager_creation(self):
        manager = create_test_manager()
        assert manager.code == "MGR"
        assert manager.subordinates == []

    def test_register_subordinate(self):
        manager = create_test_manager()
        specialist = create_test_specialist()

        manager.register_subordinate(specialist)

        assert len(manager.subordinates) == 1
        assert manager.get_subordinate("TEST") == specialist

    def test_unregister_subordinate(self):
        manager = create_test_manager()
        specialist = create_test_specialist()

        manager.register_subordinate(specialist)
        manager.unregister_subordinate("TEST")

        assert len(manager.subordinates) == 0
        assert manager.get_subordinate("TEST") is None

    @pytest.mark.asyncio
    async def test_delegate_to_subordinate(self):
        manager = create_test_manager()
        specialist = create_test_specialist()
        manager.register_subordinate(specialist)

        task = Task(description="Delegate test", task_type="test")
        result = await manager.delegate(task, "TEST")

        assert result.success is True
        assert task.status == TaskStatus.DELEGATED
        assert task.assigned_to == "TEST"

    @pytest.mark.asyncio
    async def test_delegate_to_unknown_agent(self):
        manager = create_test_manager()

        task = Task(description="Bad delegate", task_type="test")
        result = await manager.delegate(task, "UNKNOWN")

        assert result.success is False
        assert "UNKNOWN" in result.error

    @pytest.mark.asyncio
    async def test_delegate_incompatible_task(self):
        manager = create_test_manager()
        specialist = create_test_specialist()
        manager.register_subordinate(specialist)

        task = Task(description="Incompatible", task_type="other")
        result = await manager.delegate(task, "TEST")

        assert result.success is False
        assert "cannot handle" in result.error

    @pytest.mark.asyncio
    async def test_find_best_agent_single(self):
        manager = create_test_manager()
        specialist = create_test_specialist()
        manager.register_subordinate(specialist)

        task = Task(description="Find agent", task_type="test")
        best = await manager.find_best_agent(task)

        assert best == "TEST"

    @pytest.mark.asyncio
    async def test_find_best_agent_none_capable(self):
        manager = create_test_manager()
        specialist = create_test_specialist()
        manager.register_subordinate(specialist)

        task = Task(description="No match", task_type="unmatchable")
        best = await manager.find_best_agent(task)

        assert best is None


class TestManagerDelegateWithRetry:
    """Test Manager.delegate_with_retry method."""

    @pytest.mark.asyncio
    async def test_delegate_with_retry_success(self):
        manager = create_test_manager()
        specialist = create_test_specialist()
        manager.register_subordinate(specialist)

        task = Task(description="Retry test", task_type="test")
        result = await manager.delegate_with_retry(task, "TEST", max_retries=3)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_delegate_with_retry_unknown_agent(self):
        from ag3ntwerk.core.exceptions import AgentUnavailableError

        manager = create_test_manager()
        task = Task(description="Unknown agent", task_type="test")

        with pytest.raises(AgentUnavailableError):
            await manager.delegate_with_retry(task, "UNKNOWN")

    @pytest.mark.asyncio
    async def test_delegate_with_retry_incompatible_task(self):
        from ag3ntwerk.core.exceptions import AgentCapabilityError

        manager = create_test_manager()
        specialist = create_test_specialist()
        manager.register_subordinate(specialist)

        task = Task(description="Wrong type", task_type="other")

        with pytest.raises(AgentCapabilityError):
            await manager.delegate_with_retry(task, "TEST")


class TestAgentHistory:
    """Test agent task history tracking."""

    @pytest.mark.asyncio
    async def test_record_result(self):
        specialist = create_test_specialist()
        result = TaskResult(task_id="test-1", success=True)

        specialist.record_result(result)

        history = specialist.get_history()
        assert len(history) == 1
        assert history[0].task_id == "test-1"

    @pytest.mark.asyncio
    async def test_history_limit(self):
        specialist = create_test_specialist()

        # Add more than limit
        for i in range(15):
            specialist.record_result(TaskResult(task_id=f"test-{i}", success=True))

        history = specialist.get_history(limit=10)
        assert len(history) == 10
        # Should be most recent
        assert history[-1].task_id == "test-14"


# =============================================================================
# Helper Functions
# =============================================================================


def create_test_specialist():
    """Create a test specialist for testing."""

    class TestSpecialist(Specialist):
        async def execute(self, task: Task) -> TaskResult:
            return TaskResult(
                task_id=task.id,
                success=True,
                output={"executed_by": self.code},
            )

    return TestSpecialist(
        code="TEST",
        name="Test Specialist",
        domain="Testing",
        capabilities=["test", "analyze"],
    )


def create_test_manager():
    """Create a test manager for testing."""

    class TestManager(Manager):
        def can_handle(self, task: Task) -> bool:
            return task.task_type in ["test", "management"]

        async def execute(self, task: Task) -> TaskResult:
            return TaskResult(
                task_id=task.id,
                success=True,
                output={"handled_by": self.code},
            )

    return TestManager(
        code="MGR",
        name="Test Manager",
        domain="Testing",
    )
