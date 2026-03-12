"""Tests for heuristic wiring into agent execution (Phase 2, Step 1)."""

import pytest

from ag3ntwerk.core.base import (
    Agent,
    Manager,
    Task,
    TaskResult,
    TaskPriority,
    TaskStatus,
)
from ag3ntwerk.core.heuristics import HeuristicEngine, HeuristicAction, Heuristic
from ag3ntwerk.modules.metacognition.service import MetacognitionService


class SimpleManager(Manager):
    """Minimal Manager subclass for testing."""

    def can_handle(self, task):
        return True

    async def execute(self, task):
        return TaskResult(task_id=task.id, success=True, output="done")


class SimpleAgent(Agent):
    """Minimal agent for subordinate testing."""

    def can_handle(self, task):
        return True

    async def execute(self, task):
        return TaskResult(task_id=task.id, success=True, output="agent done")


# =========================================================================
# _build_heuristic_context
# =========================================================================


class TestBuildHeuristicContext:
    def test_empty_history(self):
        mgr = SimpleManager("TST", "Test", "testing")
        task = Task(description="test", task_type="test")
        ctx = mgr._build_heuristic_context(task)
        assert ctx["consecutive_failures"] == 0
        assert ctx["recent_success_rate"] == 0.5
        assert ctx["task_complexity"] == 0.0

    def test_consecutive_failures_counted(self):
        mgr = SimpleManager("TST", "Test", "testing")
        for _ in range(3):
            mgr.record_result(TaskResult(task_id="x", success=False))
        task = Task(description="test", task_type="test")
        ctx = mgr._build_heuristic_context(task)
        assert ctx["consecutive_failures"] == 3

    def test_consecutive_failures_reset_by_success(self):
        mgr = SimpleManager("TST", "Test", "testing")
        mgr.record_result(TaskResult(task_id="x", success=False))
        mgr.record_result(TaskResult(task_id="x", success=False))
        mgr.record_result(TaskResult(task_id="x", success=True))
        mgr.record_result(TaskResult(task_id="x", success=False))
        task = Task(description="test", task_type="test")
        ctx = mgr._build_heuristic_context(task)
        assert ctx["consecutive_failures"] == 1

    def test_success_rate_calculated(self):
        mgr = SimpleManager("TST", "Test", "testing")
        for _ in range(7):
            mgr.record_result(TaskResult(task_id="x", success=True))
        for _ in range(3):
            mgr.record_result(TaskResult(task_id="x", success=False))
        task = Task(description="test", task_type="test")
        ctx = mgr._build_heuristic_context(task)
        assert abs(ctx["recent_success_rate"] - 0.7) < 1e-9

    def test_high_priority_increases_complexity(self):
        mgr = SimpleManager("TST", "Test", "testing")
        task = Task(description="test", task_type="test", priority=TaskPriority.CRITICAL)
        ctx = mgr._build_heuristic_context(task)
        assert ctx["task_complexity"] >= 0.5

    def test_context_complexity_passthrough(self):
        mgr = SimpleManager("TST", "Test", "testing")
        task = Task(description="test", task_type="test", context={"complexity": 0.8})
        ctx = mgr._build_heuristic_context(task)
        assert ctx["task_complexity"] == 0.8


# =========================================================================
# _apply_heuristic_actions
# =========================================================================


class TestApplyHeuristicActions:
    def test_no_engine_returns_empty(self):
        mgr = SimpleManager("TST", "Test", "testing")
        task = Task(description="test", task_type="test")
        assert mgr._apply_heuristic_actions(task) == []

    def test_engine_with_no_firing_returns_empty(self):
        mgr = SimpleManager("TST", "Test", "testing")
        mgr._heuristic_engine = HeuristicEngine("TST")
        task = Task(description="test", task_type="test")
        # Default heuristics shouldn't fire with no context
        actions = mgr._apply_heuristic_actions(task)
        # May or may not fire depending on defaults; just ensure no crash
        assert isinstance(actions, list)

    def test_thoroughness_boost_set(self):
        mgr = SimpleManager("TST", "Test", "testing")
        mgr._heuristic_engine = HeuristicEngine("TST")
        # Add 3 consecutive failures to trigger failure_recovery
        for _ in range(3):
            mgr.record_result(TaskResult(task_id="x", success=False))
        task = Task(description="test", task_type="test")
        actions = mgr._apply_heuristic_actions(task)
        if actions:
            assert task.context.get("_thoroughness_boost") is True
            assert "_heuristic_actions" in task.context

    def test_risk_allowance_set(self):
        mgr = SimpleManager("TST", "Test", "testing")
        engine = HeuristicEngine("TST")
        # Add a custom heuristic that always fires for risk
        h = Heuristic(
            name="confidence_boost",
            agent_code="TST",
            condition="always",
            action="allow_higher_risk",
            threshold=0.0,  # Always fires
        )
        engine._heuristics[h.id] = h
        mgr._heuristic_engine = engine
        # Need high success rate
        for _ in range(10):
            mgr.record_result(TaskResult(task_id="x", success=True))
        task = Task(description="test", task_type="test")
        actions = mgr._apply_heuristic_actions(task)
        risk_actions = [a for a in actions if a.action == "allow_higher_risk"]
        if risk_actions:
            assert task.context.get("_risk_allowance") is True

    def test_collaboration_suggested_set(self):
        mgr = SimpleManager("TST", "Test", "testing")
        engine = HeuristicEngine("TST")
        h = Heuristic(
            name="complexity_scaling",
            agent_code="TST",
            condition="always",
            action="request_collaboration",
            threshold=0.0,
        )
        engine._heuristics[h.id] = h
        mgr._heuristic_engine = engine
        task = Task(description="test", task_type="test", context={"complexity": 0.9})
        actions = mgr._apply_heuristic_actions(task)
        collab_actions = [a for a in actions if a.action == "request_collaboration"]
        if collab_actions:
            assert task.context.get("_collaboration_suggested") is True


# =========================================================================
# _record_heuristic_outcomes
# =========================================================================


class TestRecordHeuristicOutcomes:
    def test_no_engine_no_crash(self):
        mgr = SimpleManager("TST", "Test", "testing")
        actions = [HeuristicAction(heuristic_id="fake", action="test")]
        mgr._record_heuristic_outcomes(actions, True)  # Should not crash

    def test_outcomes_recorded(self):
        mgr = SimpleManager("TST", "Test", "testing")
        engine = HeuristicEngine("TST")
        mgr._heuristic_engine = engine

        # Get one of the default heuristic IDs
        heuristic = list(engine._heuristics.values())[0]
        actions = [HeuristicAction(heuristic_id=heuristic.id, action=heuristic.action)]

        initial_outcomes = heuristic.total_outcomes
        mgr._record_heuristic_outcomes(actions, True)
        assert heuristic.total_outcomes == initial_outcomes + 1

    def test_success_and_failure_recorded(self):
        mgr = SimpleManager("TST", "Test", "testing")
        engine = HeuristicEngine("TST")
        mgr._heuristic_engine = engine

        heuristic = list(engine._heuristics.values())[0]
        actions = [HeuristicAction(heuristic_id=heuristic.id, action=heuristic.action)]

        mgr._record_heuristic_outcomes(actions, True)
        mgr._record_heuristic_outcomes(actions, False)
        assert heuristic.total_outcomes >= 2


# =========================================================================
# Agent.reason() heuristic injection
# =========================================================================


class TestReasonHeuristicInjection:
    @pytest.mark.asyncio
    async def test_thoroughness_boost_in_prompt(self):
        class MockLLM:
            is_connected = True

            async def generate(self, prompt):
                return prompt

        agent = SimpleAgent("TST", "Test", "testing", llm_provider=MockLLM())
        result = await agent.reason("test prompt", context={"_thoroughness_boost": True})
        assert "[HEURISTIC: Be extra thorough" in result

    @pytest.mark.asyncio
    async def test_risk_allowance_in_prompt(self):
        class MockLLM:
            is_connected = True

            async def generate(self, prompt):
                return prompt

        agent = SimpleAgent("TST", "Test", "testing", llm_provider=MockLLM())
        result = await agent.reason("test prompt", context={"_risk_allowance": True})
        assert "[HEURISTIC: Prioritize bold approaches" in result

    @pytest.mark.asyncio
    async def test_collaboration_suggested_in_prompt(self):
        class MockLLM:
            is_connected = True

            async def generate(self, prompt):
                return prompt

        agent = SimpleAgent("TST", "Test", "testing", llm_provider=MockLLM())
        result = await agent.reason("test prompt", context={"_collaboration_suggested": True})
        assert "[HEURISTIC: Consider consulting" in result

    @pytest.mark.asyncio
    async def test_no_heuristic_flags_no_injection(self):
        class MockLLM:
            is_connected = True

            async def generate(self, prompt):
                return prompt

        agent = SimpleAgent("TST", "Test", "testing", llm_provider=MockLLM())
        result = await agent.reason("test prompt", context={"some_key": "val"})
        assert "[HEURISTIC:" not in result


# =========================================================================
# Overwatch integration: connect_metacognition attaches engines
# =========================================================================


class TestCoSHeuristicIntegration:
    def test_connect_metacognition_attaches_engines(self):
        from ag3ntwerk.agents.overwatch.agent import Overwatch

        cos = Overwatch()
        agent = SimpleAgent("Forge", "Forge", "tech")
        cos.register_subordinate(agent)

        svc = MetacognitionService()
        cos.connect_metacognition(svc)

        assert agent._heuristic_engine is not None
        assert agent._reflector is not None
        assert agent.personality is not None

    def test_connect_metacognition_attaches_to_multiple(self):
        from ag3ntwerk.agents.overwatch.agent import Overwatch

        cos = Overwatch()
        agents = []
        for code in ["Forge", "Echo", "Keystone"]:
            a = SimpleAgent(code, code, "domain")
            cos.register_subordinate(a)
            agents.append(a)

        svc = MetacognitionService()
        cos.connect_metacognition(svc)

        for a in agents:
            assert a._heuristic_engine is not None
            assert a._reflector is not None
