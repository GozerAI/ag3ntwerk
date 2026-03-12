"""Tests for internal delegation tracking in Manager (Phase 3, Step 1)."""

import pytest

from ag3ntwerk.core.base import Manager, Task, TaskResult, Specialist


class FakeMetacognitionService:
    """Fake service that records on_task_completed calls."""

    def __init__(self):
        self.calls = []

    def on_task_completed(self, **kwargs):
        self.calls.append(kwargs)


class FakeSpecialist(Specialist):
    """Minimal specialist for delegation tests."""

    def __init__(self, code="S1", success=True, output="done"):
        super().__init__(code=code, name=code, domain="test", capabilities=["general"])
        self._success = success
        self._output = output

    async def execute(self, task: Task) -> TaskResult:
        return TaskResult(task_id=task.id, success=self._success, output=self._output)


class FakeManager(Manager):
    """Concrete manager for testing."""

    def can_handle(self, task: Task) -> bool:
        return True

    async def execute(self, task: Task) -> TaskResult:
        return await self.delegate(task, "S1")


class TestDelegationTracking:
    """Tests for _record_delegation_to_metacognition in Manager.delegate()."""

    @pytest.fixture
    def manager_with_service(self):
        mgr = FakeManager(code="MGR", name="TestManager", domain="test")
        specialist = FakeSpecialist(code="S1", success=True)
        mgr.register_subordinate(specialist)
        svc = FakeMetacognitionService()
        mgr._metacognition_service = svc
        return mgr, svc

    async def test_delegate_records_success_to_metacognition(self, manager_with_service):
        mgr, svc = manager_with_service
        task = Task(description="test", task_type="general")
        result = await mgr.delegate(task, "S1")
        assert result.success
        assert len(svc.calls) == 1
        call = svc.calls[0]
        assert call["agent_code"] == "S1"
        assert call["task_type"] == "general"
        assert call["success"] is True
        assert call["duration_ms"] >= 0

    async def test_delegate_records_failure_to_metacognition(self):
        mgr = FakeManager(code="MGR", name="TestManager", domain="test")
        specialist = FakeSpecialist(code="S1", success=False, output=None)
        mgr.register_subordinate(specialist)
        svc = FakeMetacognitionService()
        mgr._metacognition_service = svc

        task = Task(description="test", task_type="general")
        result = await mgr.delegate(task, "S1")
        assert not result.success
        assert len(svc.calls) == 1
        assert svc.calls[0]["success"] is False

    async def test_delegate_noop_without_service(self):
        mgr = FakeManager(code="MGR", name="TestManager", domain="test")
        specialist = FakeSpecialist(code="S1")
        mgr.register_subordinate(specialist)
        # No _metacognition_service set — should not raise
        task = Task(description="test", task_type="general")
        result = await mgr.delegate(task, "S1")
        assert result.success

    async def test_delegate_best_effort_on_service_error(self):
        class BreakingService:
            def on_task_completed(self, **kwargs):
                raise RuntimeError("boom")

        mgr = FakeManager(code="MGR", name="TestManager", domain="test")
        specialist = FakeSpecialist(code="S1")
        mgr.register_subordinate(specialist)
        mgr._metacognition_service = BreakingService()

        task = Task(description="test", task_type="general")
        result = await mgr.delegate(task, "S1")
        # Should not raise — best-effort
        assert result.success

    async def test_metacognition_service_field_default_none(self):
        mgr = FakeManager(code="MGR", name="TestManager", domain="test")
        assert mgr._metacognition_service is None

    async def test_delegation_not_found_skips_metacognition(self):
        mgr = FakeManager(code="MGR", name="TestManager", domain="test")
        svc = FakeMetacognitionService()
        mgr._metacognition_service = svc
        task = Task(description="test", task_type="general")
        result = await mgr.delegate(task, "NONEXISTENT")
        assert not result.success
        # No call to metacognition since delegation failed before execution
        assert len(svc.calls) == 0
