"""Tests for heuristic application in Manager.delegate() (Phase 3, Step 2)."""

import pytest

from ag3ntwerk.core.base import Manager, Task, TaskResult, Specialist
from ag3ntwerk.core.heuristics import HeuristicEngine, HeuristicAction


class FakeSpecialist(Specialist):
    def __init__(self, code="S1", success=True):
        super().__init__(code=code, name=code, domain="test", capabilities=["general"])
        self._success = success

    async def execute(self, task: Task) -> TaskResult:
        return TaskResult(task_id=task.id, success=self._success, output="ok")


class TrackingHeuristicEngine(HeuristicEngine):
    """Heuristic engine that always fires a known action for testing."""

    def __init__(self):
        super().__init__("test")
        self.outcomes_recorded = []
        self._force_action = None

    def set_force_action(self, action: HeuristicAction):
        self._force_action = action

    def evaluate(self, task=None, context=None):
        if self._force_action:
            return [self._force_action]
        return []

    def record_outcome(self, heuristic_id, success):
        self.outcomes_recorded.append((heuristic_id, success))


class FakeManager(Manager):
    def can_handle(self, task: Task) -> bool:
        return True

    async def execute(self, task: Task) -> TaskResult:
        return await self.delegate(task, "S1")


class TestHeuristicDelegation:
    """Tests for heuristic actions being applied/recorded in delegate()."""

    @pytest.fixture
    def setup(self):
        mgr = FakeManager(code="MGR", name="TestManager", domain="test")
        specialist = FakeSpecialist(code="S1", success=True)
        mgr.register_subordinate(specialist)
        engine = TrackingHeuristicEngine()
        mgr._heuristic_engine = engine
        return mgr, engine

    async def test_heuristic_actions_applied_before_delegation(self, setup):
        mgr, engine = setup
        action = HeuristicAction(
            heuristic_id="h1",
            action="increase_thoroughness",
        )
        engine.set_force_action(action)

        task = Task(description="test", task_type="general")
        result = await mgr.delegate(task, "S1")
        assert result.success
        # Heuristic should have set context flag
        assert task.context.get("_thoroughness_boost") is True
        assert "_heuristic_actions" in task.context

    async def test_heuristic_outcomes_recorded_after_delegation(self, setup):
        mgr, engine = setup
        action = HeuristicAction(heuristic_id="h1", action="increase_thoroughness")
        engine.set_force_action(action)

        task = Task(description="test", task_type="general")
        await mgr.delegate(task, "S1")
        assert len(engine.outcomes_recorded) == 1
        assert engine.outcomes_recorded[0] == ("h1", True)

    async def test_no_heuristic_when_engine_is_none(self):
        mgr = FakeManager(code="MGR", name="TestManager", domain="test")
        specialist = FakeSpecialist(code="S1")
        mgr.register_subordinate(specialist)
        # _heuristic_engine is None by default
        task = Task(description="test", task_type="general")
        result = await mgr.delegate(task, "S1")
        assert result.success
        # No heuristic actions should be set
        assert "_heuristic_actions" not in (task.context or {})

    async def test_heuristic_failure_outcome_recorded(self):
        mgr = FakeManager(code="MGR", name="TestManager", domain="test")
        specialist = FakeSpecialist(code="S1", success=False)
        mgr.register_subordinate(specialist)
        engine = TrackingHeuristicEngine()
        mgr._heuristic_engine = engine
        action = HeuristicAction(heuristic_id="h2", action="allow_higher_risk")
        engine.set_force_action(action)

        task = Task(description="test", task_type="general")
        await mgr.delegate(task, "S1")
        assert len(engine.outcomes_recorded) == 1
        assert engine.outcomes_recorded[0] == ("h2", False)

    async def test_no_actions_when_heuristic_returns_empty(self, setup):
        mgr, engine = setup
        # Don't set any force_action — evaluate returns []
        task = Task(description="test", task_type="general")
        result = await mgr.delegate(task, "S1")
        assert result.success
        assert len(engine.outcomes_recorded) == 0
