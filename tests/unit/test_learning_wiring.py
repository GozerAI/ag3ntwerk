"""Tests for wiring the learning system into all 16 agents.

Covers:
- Manager records outcomes on successful delegation
- Manager records outcomes on failed delegation
- Propagation from Overwatch reaches all managers
- Graceful no-op without orchestrator
- Error in recording doesn't break delegation
- HierarchyPath correctly populated
- Duration_ms is calculated
- connect_learning_orchestrator sets the attribute
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ag3ntwerk.core.base import Manager, Specialist, Task, TaskResult, TaskPriority, TaskStatus
from ag3ntwerk.learning.models import HierarchyPath


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manager(code="MGR", name="Test Manager", domain="testing"):
    """Create a bare Manager for testing."""
    return Manager(code=code, name=name, domain=domain, llm_provider=None)


class _ConcreteSpecialist(Specialist):
    """Non-abstract Specialist for testing."""

    async def execute(self, task):
        return TaskResult(task_id=task.id, success=True, output="done")


def _make_specialist(code="SPC", name="Test Specialist", domain="testing"):
    """Create a concrete Specialist for testing."""
    return _ConcreteSpecialist(
        code=code,
        name=name,
        domain=domain,
        capabilities=["testing"],
        llm_provider=None,
    )


def _make_task(task_type="analysis", description="test task"):
    """Create a minimal Task."""
    return Task(
        task_type=task_type,
        description=description,
        priority=TaskPriority.MEDIUM,
    )


def _make_orchestrator():
    """Create a mock learning orchestrator with an async record_outcome."""
    orch = MagicMock()
    orch.record_outcome = AsyncMock(return_value="outcome-id-123")
    orch.register_executive = MagicMock()
    orch.register_manager = MagicMock()
    orch.register_specialist = MagicMock()
    return orch


def _success_result(task):
    """Return a successful TaskResult."""
    return TaskResult(
        task_id=task.id,
        success=True,
        output={"answer": 42},
    )


def _failure_result(task):
    """Return a failed TaskResult."""
    return TaskResult(
        task_id=task.id,
        success=False,
        error="something went wrong",
    )


# ---------------------------------------------------------------------------
# 1. connect_learning_orchestrator sets the attribute
# ---------------------------------------------------------------------------


class TestConnectLearningOrchestrator:

    def test_sets_attribute(self):
        mgr = _make_manager()
        orch = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch)
        assert mgr._learning_orchestrator is orch

    def test_none_by_default(self):
        mgr = _make_manager()
        assert mgr._learning_orchestrator is None

    def test_can_replace_orchestrator(self):
        mgr = _make_manager()
        orch1 = _make_orchestrator()
        orch2 = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch1)
        mgr.connect_learning_orchestrator(orch2)
        assert mgr._learning_orchestrator is orch2


# ---------------------------------------------------------------------------
# 2. _record_delegation_to_learning on success
# ---------------------------------------------------------------------------


class TestRecordDelegationSuccess:

    async def test_calls_record_outcome(self):
        mgr = _make_manager(code="Forge")
        orch = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()
        result = _success_result(task)
        start_time = datetime.now() - timedelta(milliseconds=50)

        await mgr._record_delegation_to_learning(task, result, start_time)

        orch.record_outcome.assert_awaited_once()

    async def test_success_flag_is_true(self):
        mgr = _make_manager(code="Keystone")
        orch = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()
        result = _success_result(task)
        start_time = datetime.now()

        await mgr._record_delegation_to_learning(task, result, start_time)

        call_kwargs = orch.record_outcome.call_args.kwargs
        assert call_kwargs["success"] is True

    async def test_task_id_passed(self):
        mgr = _make_manager(code="Echo")
        orch = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task(task_type="marketing")
        result = _success_result(task)
        start_time = datetime.now()

        await mgr._record_delegation_to_learning(task, result, start_time)

        call_kwargs = orch.record_outcome.call_args.kwargs
        assert call_kwargs["task_id"] == task.id

    async def test_task_type_passed(self):
        mgr = _make_manager(code="Axiom")
        orch = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task(task_type="revenue_analysis")
        result = _success_result(task)
        start_time = datetime.now()

        await mgr._record_delegation_to_learning(task, result, start_time)

        call_kwargs = orch.record_outcome.call_args.kwargs
        assert call_kwargs["task_type"] == "revenue_analysis"


# ---------------------------------------------------------------------------
# 3. _record_delegation_to_learning on failure
# ---------------------------------------------------------------------------


class TestRecordDelegationFailure:

    async def test_calls_record_outcome_on_failure(self):
        mgr = _make_manager(code="Sentinel")
        orch = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()
        result = _failure_result(task)
        start_time = datetime.now()

        await mgr._record_delegation_to_learning(task, result, start_time)

        orch.record_outcome.assert_awaited_once()

    async def test_success_flag_is_false(self):
        mgr = _make_manager(code="Blueprint")
        orch = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()
        result = _failure_result(task)
        start_time = datetime.now()

        await mgr._record_delegation_to_learning(task, result, start_time)

        call_kwargs = orch.record_outcome.call_args.kwargs
        assert call_kwargs["success"] is False

    async def test_error_field_passed(self):
        mgr = _make_manager(code="Axiom")
        orch = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()
        result = _failure_result(task)
        start_time = datetime.now()

        await mgr._record_delegation_to_learning(task, result, start_time)

        call_kwargs = orch.record_outcome.call_args.kwargs
        assert call_kwargs["error"] == "something went wrong"


# ---------------------------------------------------------------------------
# 4. Graceful no-op without orchestrator
# ---------------------------------------------------------------------------


class TestNoOpWithoutOrchestrator:

    async def test_no_orchestrator_no_error(self):
        mgr = _make_manager()
        task = _make_task()
        result = _success_result(task)
        start_time = datetime.now()

        # Should not raise -- returns silently
        await mgr._record_delegation_to_learning(task, result, start_time)

    async def test_none_orchestrator_no_error(self):
        mgr = _make_manager()
        mgr._learning_orchestrator = None
        task = _make_task()
        result = _failure_result(task)
        start_time = datetime.now()

        # Should not raise -- returns silently
        await mgr._record_delegation_to_learning(task, result, start_time)


# ---------------------------------------------------------------------------
# 5. Error in recording doesn't break delegation
# ---------------------------------------------------------------------------


class TestRecordingErrorResilience:

    async def test_record_outcome_exception_is_swallowed(self):
        mgr = _make_manager(code="Index")
        orch = _make_orchestrator()
        orch.record_outcome = AsyncMock(side_effect=RuntimeError("db down"))
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()
        result = _success_result(task)
        start_time = datetime.now()

        # Should not raise even though record_outcome explodes
        await mgr._record_delegation_to_learning(task, result, start_time)

    async def test_record_outcome_exception_does_not_alter_result(self):
        mgr = _make_manager(code="Foundry")
        orch = _make_orchestrator()
        orch.record_outcome = AsyncMock(side_effect=ValueError("bad data"))
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()
        result = _success_result(task)
        start_time = datetime.now()

        # The method should complete without propagating the error
        await mgr._record_delegation_to_learning(task, result, start_time)
        # Verify the original result is unmodified
        assert result.success is True
        assert result.output == {"answer": 42}


# ---------------------------------------------------------------------------
# 6. HierarchyPath correctly populated
# ---------------------------------------------------------------------------


class TestHierarchyPathPopulation:

    async def test_hierarchy_path_has_executive_matching_manager_code(self):
        mgr = _make_manager(code="Citadel")
        orch = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()
        result = _success_result(task)
        start_time = datetime.now()

        await mgr._record_delegation_to_learning(task, result, start_time)

        call_kwargs = orch.record_outcome.call_args.kwargs
        hp = call_kwargs["hierarchy_path"]

        assert isinstance(hp, HierarchyPath)
        assert hp.agent == "Citadel"

    async def test_hierarchy_path_manager_matches_assigned_to(self):
        mgr = _make_manager(code="Beacon")
        orch = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()
        task.assigned_to = "LEGAL-MGR"
        result = _success_result(task)
        start_time = datetime.now()

        await mgr._record_delegation_to_learning(task, result, start_time)

        call_kwargs = orch.record_outcome.call_args.kwargs
        hp = call_kwargs["hierarchy_path"]
        assert hp.manager == "LEGAL-MGR"

    async def test_hierarchy_path_model_construction(self):
        hp = HierarchyPath(agent="Forge", manager="Forge-MGR", specialist="SPC-1")
        assert hp.agent == "Forge"
        assert hp.manager == "Forge-MGR"
        assert hp.specialist == "SPC-1"

    async def test_hierarchy_path_optional_fields(self):
        hp = HierarchyPath(agent="Keystone")
        assert hp.agent == "Keystone"
        assert hp.manager is None
        assert hp.specialist is None


# ---------------------------------------------------------------------------
# 7. Duration_ms is calculated
# ---------------------------------------------------------------------------


class TestDurationCalculation:

    async def test_duration_ms_is_positive(self):
        mgr = _make_manager(code="Compass")
        orch = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()
        result = _success_result(task)
        start_time = datetime.now() - timedelta(milliseconds=100)

        await mgr._record_delegation_to_learning(task, result, start_time)

        call_kwargs = orch.record_outcome.call_args.kwargs
        assert call_kwargs["duration_ms"] > 0.0

    async def test_duration_ms_reasonable_range(self):
        mgr = _make_manager(code="Vector")
        orch = _make_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()
        result = _success_result(task)
        start_time = datetime.now() - timedelta(milliseconds=50)

        await mgr._record_delegation_to_learning(task, result, start_time)

        call_kwargs = orch.record_outcome.call_args.kwargs
        duration = call_kwargs["duration_ms"]
        # Should be at least ~50ms, allow generous tolerance
        assert 10.0 < duration < 5000.0


# ---------------------------------------------------------------------------
# 8. Overwatch learning mixin propagation
# ---------------------------------------------------------------------------


class TestCoSLearningPropagation:

    async def test_propagation_to_subordinate_managers(self):
        """Overwatch LearningMixin.connect_learning_system propagates to managers."""
        from ag3ntwerk.agents.overwatch.learning_mixin import LearningMixin

        mixin = LearningMixin()
        orch = _make_orchestrator()

        # Create subordinate managers (agent-level)
        mgr1 = _make_manager(code="Forge")
        mgr2 = _make_manager(code="Keystone")
        mgr3 = _make_manager(code="Echo")

        # LearningMixin accesses self._subordinates (dict of code -> agent)
        mixin._subordinates = {"Forge": mgr1, "Keystone": mgr2, "Echo": mgr3}

        await mixin.connect_learning_system(orch)

        # All subordinate managers should have the orchestrator
        for mgr in [mgr1, mgr2, mgr3]:
            assert mgr._learning_orchestrator is orch

    async def test_propagation_skips_non_managers(self):
        """Propagation doesn't fail on non-Manager subordinates."""
        from ag3ntwerk.agents.overwatch.learning_mixin import LearningMixin

        mixin = LearningMixin()
        orch = _make_orchestrator()

        mgr = _make_manager(code="Forge")
        spc = _make_specialist(code="SPC")

        mixin._subordinates = {"Forge": mgr, "SPC": spc}

        # Should not raise even if SPC is a Specialist (not a Manager)
        await mixin.connect_learning_system(orch)

        assert mgr._learning_orchestrator is orch
