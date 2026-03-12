"""
End-to-End Integration Tests (Item 8).

Verifies full integration flows WITHOUT requiring external services
(LLM, Redis). All external dependencies are mocked.

Tests cover:
1. Full delegation chain records to learning
2. Module feedback captured end-to-end
3. Tool usage recorded
4. Nexus broadcast verified
5. Smart routing uses real learning data
6. Capability registry works with live agents
7. Circuit breaker integrates correctly
8. Learning wiring propagates through hierarchy
9. Multi-level delegation chain
10. Module integration with circuit breaker resilience
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ag3ntwerk.core.base import (
    Agent,
    Manager,
    Specialist,
    Task,
    TaskPriority,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.core.capability_registry import CapabilityRegistry
from ag3ntwerk.core.circuit_breaker import CircuitBreaker, CircuitState
from ag3ntwerk.core.smart_router import SmartRouter
from ag3ntwerk.learning.models import HierarchyPath
from ag3ntwerk.modules.integration import ModuleIntegration


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class MockSpecialist(Specialist):
    """Specialist that always succeeds with a fixed output."""

    def __init__(self, code="SP1", capabilities=None):
        super().__init__(
            code=code,
            name=f"Mock Specialist {code}",
            domain="testing",
            capabilities=capabilities or ["test_task", "analysis"],
        )

    async def execute(self, task: Task) -> TaskResult:
        return TaskResult(task_id=task.id, success=True, output=f"done-{self.code}")


class FailingSpecialist(Specialist):
    """Specialist that always fails."""

    def __init__(self, code="FAIL1", capabilities=None):
        super().__init__(
            code=code,
            name=f"Failing Specialist {code}",
            domain="testing",
            capabilities=capabilities or ["test_task"],
        )

    async def execute(self, task: Task) -> TaskResult:
        return TaskResult(
            task_id=task.id,
            success=False,
            error="intentional failure",
        )


class MockManager(Manager):
    """Manager concrete subclass for testing."""

    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(task_type="test_task", description="integration test task"):
    return Task(description=description, task_type=task_type)


def _make_mock_orchestrator():
    """Create a mock LearningOrchestrator with the record_outcome signature."""
    orch = AsyncMock()
    orch.record_outcome = AsyncMock(return_value="rec-001")
    orch.get_agent_performance = AsyncMock(return_value=None)
    return orch


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestFullDelegationChain:
    """Test 1: Full delegation chain records to learning."""

    async def test_delegate_records_to_learning_orchestrator(self):
        """Manager.delegate() records outcome to the learning orchestrator."""
        mgr = MockManager(code="MGR", name="Test Manager", domain="testing")
        spec = MockSpecialist(code="SP1")
        mgr.register_subordinate(spec)

        orch = _make_mock_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()

        with patch(
            "ag3ntwerk.core.plugins.dispatch_plugin_event", new_callable=AsyncMock, return_value=[]
        ):
            result = await mgr.delegate(task, "SP1")

        assert result.success is True
        assert result.output == "done-SP1"

        orch.record_outcome.assert_awaited_once()
        call_kwargs = orch.record_outcome.call_args
        # Verify HierarchyPath was built correctly
        hp = call_kwargs.kwargs.get("hierarchy_path") or call_kwargs[1].get("hierarchy_path")
        assert hp.agent == "MGR"
        assert call_kwargs.kwargs.get("success") or call_kwargs[1].get("success") is True

    async def test_failed_delegation_also_recorded(self):
        """Failed delegations are still recorded to learning."""
        mgr = MockManager(code="MGR", name="Test Manager", domain="testing")
        spec = FailingSpecialist(code="FAIL1")
        mgr.register_subordinate(spec)

        orch = _make_mock_orchestrator()
        mgr.connect_learning_orchestrator(orch)

        task = _make_task()

        with patch(
            "ag3ntwerk.core.plugins.dispatch_plugin_event", new_callable=AsyncMock, return_value=[]
        ):
            result = await mgr.delegate(task, "FAIL1")

        assert result.success is False
        orch.record_outcome.assert_awaited_once()
        call_kwargs = orch.record_outcome.call_args.kwargs
        assert call_kwargs["success"] is False
        assert call_kwargs["error"] == "intentional failure"


@pytest.mark.integration
class TestModuleFeedback:
    """Test 2: Module feedback captured end-to-end."""

    async def test_execute_module_task_records_outcome(self):
        """ModuleIntegration.execute_module_task records to learning."""
        integration = ModuleIntegration()
        orch = _make_mock_orchestrator()
        integration.connect_learning(orch)

        # Mock the internal brand task executor (sync, so no await needed)
        integration._execute_brand_task = MagicMock(
            return_value={"success": True, "identity": "test"}
        )

        result = await integration.execute_module_task(
            module_id="brand",
            task_type="get_identity",
            params={},
        )

        assert result["success"] is True

        # _record_module_outcome should have called orchestrator.record_outcome
        orch.record_outcome.assert_awaited_once()
        call_kwargs = orch.record_outcome.call_args.kwargs
        assert call_kwargs["task_type"] == "module.brand.get_identity"
        assert call_kwargs["success"] is True

        hp = call_kwargs["hierarchy_path"]
        assert hp.agent == "module.brand"

    async def test_module_task_failure_records_error(self):
        """Module task errors are recorded to learning as failures."""
        integration = ModuleIntegration()
        orch = _make_mock_orchestrator()
        integration.connect_learning(orch)

        # Simulate a module returning an error dict
        integration._execute_brand_task = MagicMock(return_value={"error": "Identity not found"})

        result = await integration.execute_module_task(
            module_id="brand",
            task_type="get_identity",
            params={},
        )

        assert "error" in result
        orch.record_outcome.assert_awaited_once()
        call_kwargs = orch.record_outcome.call_args.kwargs
        assert call_kwargs["success"] is False


@pytest.mark.integration
class TestToolUsage:
    """Test 3: Tool usage recorded via executor."""

    async def test_use_tool_calls_executor(self):
        """Agent.use_tool dispatches to the global executor."""
        spec = MockSpecialist(code="TS1")

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {"info": "ok"}

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(return_value=mock_result)
        mock_executor._generate_execution_id = MagicMock(return_value="exec-123")

        with patch("ag3ntwerk.tools.executor.get_executor", return_value=mock_executor):
            result = await spec.use_tool("search_files", query="*.py")

        assert result.success is True
        mock_executor.execute.assert_awaited_once()
        call_args = mock_executor.execute.call_args
        assert call_args[0][0] == "search_files"  # tool_name positional arg


@pytest.mark.integration
class TestNexusBroadcast:
    """Test 4: Nexus broadcast verified."""

    async def test_broadcast_nexus_context_reaches_all_subordinates(self):
        """_broadcast_nexus_context propagates to every registered agent."""
        from ag3ntwerk.agents.overwatch.nexus_mixin import NexusMixin

        class MockCoS(NexusMixin, Manager):
            """Minimal Overwatch with NexusMixin for testing broadcast."""

            def __init__(self):
                Manager.__init__(self, code="Overwatch", name="Overwatch", domain="operations")
                self._nexus_bridge = None

        cos = MockCoS()

        agents = []
        for code in ["Forge", "Keystone", "Echo"]:
            agent = MockSpecialist(code=code, capabilities=["test_task"])
            cos.register_subordinate(agent)
            agents.append(agent)

        context = {"strategic_context": {"priority": "growth", "quarter": "Q1"}}
        cos._broadcast_nexus_context(context)

        for agent in agents:
            assert agent._strategic_context == context

    async def test_broadcast_survives_single_agent_error(self):
        """If one agent raises on receive, others still get context."""
        from ag3ntwerk.agents.overwatch.nexus_mixin import NexusMixin

        class MockCoS(NexusMixin, Manager):
            def __init__(self):
                Manager.__init__(self, code="Overwatch", name="Overwatch", domain="operations")
                self._nexus_bridge = None

        cos = MockCoS()

        good_agent = MockSpecialist(code="Forge", capabilities=["test_task"])
        bad_agent = MockSpecialist(code="Keystone", capabilities=["test_task"])
        bad_agent.receive_strategic_context = MagicMock(side_effect=RuntimeError("boom"))
        trailing_agent = MockSpecialist(code="Echo", capabilities=["test_task"])

        cos.register_subordinate(good_agent)
        cos.register_subordinate(bad_agent)
        cos.register_subordinate(trailing_agent)

        context = {"strategic_context": {"priority": "efficiency"}}
        cos._broadcast_nexus_context(context)

        # good_agent and trailing_agent received context despite bad_agent error
        assert good_agent._strategic_context == context
        assert trailing_agent._strategic_context == context


@pytest.mark.integration
class TestSmartRouting:
    """Test 5: Smart routing uses real learning data."""

    async def test_router_prefers_high_success_rate_agent(self):
        """SmartRouter ranks agents by historical success rate from learning."""
        orch = AsyncMock()

        async def mock_perf(agent_code, task_type):
            if agent_code == "Forge":
                return {
                    "total_outcomes": 20,
                    "success_rate": 0.95,
                    "avg_duration_ms": 500,
                }
            elif agent_code == "Keystone":
                return {
                    "total_outcomes": 20,
                    "success_rate": 0.60,
                    "avg_duration_ms": 2000,
                }
            return None

        orch.get_agent_performance = AsyncMock(side_effect=mock_perf)

        router = SmartRouter(learning_orchestrator=orch)
        agents = {"Forge": MagicMock(), "Keystone": MagicMock()}

        best = await router.get_best_agent("code_review", agents)

        assert best is not None
        assert best[0] == "Forge"
        assert best[1] > 0  # has a positive score

    async def test_router_cold_start_returns_neutral_scores(self):
        """Without learning data, all agents get default 0.5 scores."""
        router = SmartRouter()  # no learning orchestrator
        agents = {"Forge": MagicMock(), "Keystone": MagicMock()}

        ranked = await router.rank_agents("unknown_task", agents)

        assert len(ranked) == 2
        # All scores should be the same (neutral defaults)
        scores = [score for _, score in ranked]
        assert scores[0] == scores[1]


@pytest.mark.integration
class TestCapabilityRegistry:
    """Test 6: Capability registry works with live agents."""

    async def test_register_and_request_capability(self):
        """Register handlers and route a request to the best provider."""
        registry = CapabilityRegistry()

        async def cto_handler(capability, params):
            return {"reviewed": True, "issues": 0}

        async def cseco_handler(capability, params):
            return {"scanned": True, "vulnerabilities": []}

        registry.register("Forge", ["code_review", "architecture"], handler=cto_handler, priority=10)
        registry.register(
            "Citadel", ["security_scan", "code_review"], handler=cseco_handler, priority=5
        )

        # code_review has two providers; Forge has higher priority
        providers = registry.find_providers("code_review")
        assert providers[0] == "Forge"

        result = await registry.request("code_review", {"file": "main.py"})
        assert result["reviewed"] is True

    async def test_request_missing_capability_returns_error(self):
        """Requesting a capability with no provider returns an error dict."""
        registry = CapabilityRegistry()

        result = await registry.request("nonexistent_capability", {})
        assert "error" in result

    async def test_fallback_to_next_provider_on_handler_error(self):
        """If the top-priority handler fails, try the next provider."""
        registry = CapabilityRegistry()

        async def failing_handler(capability, params):
            raise RuntimeError("handler crashed")

        async def fallback_handler(capability, params):
            return {"fallback": True}

        registry.register("Forge", ["code_review"], handler=failing_handler, priority=10)
        registry.register("Citadel", ["code_review"], handler=fallback_handler, priority=5)

        result = await registry.request("code_review", {"file": "main.py"})
        assert result["fallback"] is True


@pytest.mark.integration
class TestCircuitBreaker:
    """Test 7: Circuit breaker integrates correctly."""

    async def test_circuit_opens_after_threshold_failures(self):
        """Circuit breaker transitions to OPEN after consecutive failures."""
        breaker = CircuitBreaker(
            name="test-llm",
            failure_threshold=3,
            recovery_timeout=0.1,
        )

        assert breaker.state == CircuitState.CLOSED
        assert breaker.allow_request() is True

        # Record failures up to threshold
        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
        assert breaker.allow_request() is False

    async def test_circuit_transitions_to_half_open_after_timeout(self):
        """After recovery_timeout, circuit transitions to HALF_OPEN."""
        breaker = CircuitBreaker(
            name="test-llm",
            failure_threshold=2,
            recovery_timeout=0.05,  # 50ms for fast test
        )

        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.06)

        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.allow_request() is True  # one test request allowed

    async def test_half_open_success_closes_circuit(self):
        """A success in HALF_OPEN state closes the circuit."""
        breaker = CircuitBreaker(
            name="test-llm",
            failure_threshold=2,
            recovery_timeout=0.05,
        )

        breaker.record_failure()
        breaker.record_failure()
        time.sleep(0.06)

        assert breaker.state == CircuitState.HALF_OPEN
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.allow_request() is True

    async def test_half_open_failure_reopens_circuit(self):
        """A failure in HALF_OPEN state reopens the circuit."""
        breaker = CircuitBreaker(
            name="test-llm",
            failure_threshold=2,
            recovery_timeout=0.05,
        )

        breaker.record_failure()
        breaker.record_failure()
        time.sleep(0.06)

        assert breaker.state == CircuitState.HALF_OPEN
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN


@pytest.mark.integration
class TestLearningPropagation:
    """Test 8: Learning wiring propagates through hierarchy."""

    async def test_learning_orchestrator_accessible_after_connect(self):
        """connect_learning_orchestrator stores the reference on Manager."""
        mgr = MockManager(code="MGR", name="Test Mgr", domain="testing")
        orch = _make_mock_orchestrator()

        mgr.connect_learning_orchestrator(orch)

        assert mgr._learning_orchestrator is orch

    async def test_multi_level_hierarchy_delegates_and_records(self):
        """
        Manager -> sub-Manager -> Specialist chain.

        Both levels should record to their respective learning orchestrators.
        """
        top_mgr = MockManager(code="Overwatch", name="Overwatch", domain="operations")
        sub_mgr = MockManager(code="Forge", name="Forge", domain="technology")
        spec = MockSpecialist(code="SP1", capabilities=["test_task"])

        sub_mgr.register_subordinate(spec)
        top_mgr.register_subordinate(sub_mgr)

        top_orch = _make_mock_orchestrator()
        sub_orch = _make_mock_orchestrator()

        top_mgr.connect_learning_orchestrator(top_orch)
        sub_mgr.connect_learning_orchestrator(sub_orch)

        task = _make_task()

        # Forge can_handle delegates to subordinates, which includes SP1
        with patch(
            "ag3ntwerk.core.plugins.dispatch_plugin_event", new_callable=AsyncMock, return_value=[]
        ):
            result = await top_mgr.delegate(task, "Forge")

        assert result.success is True
        # top_mgr recorded to top_orch
        top_orch.record_outcome.assert_awaited_once()
        top_hp = top_orch.record_outcome.call_args.kwargs["hierarchy_path"]
        assert top_hp.agent == "Overwatch"

        # sub_mgr also recorded to sub_orch when it delegated to SP1
        sub_orch.record_outcome.assert_awaited_once()
        sub_hp = sub_orch.record_outcome.call_args.kwargs["hierarchy_path"]
        assert sub_hp.agent == "Forge"


@pytest.mark.integration
class TestMultiLevelDelegation:
    """Test 9: Multi-level delegation chain end-to-end."""

    async def test_delegation_sets_task_status_and_assigned_to(self):
        """Delegation correctly updates task status and assigned_to fields."""
        mgr = MockManager(code="MGR", name="Test Manager", domain="testing")
        spec = MockSpecialist(code="SP1")
        mgr.register_subordinate(spec)

        task = _make_task()
        assert task.status == TaskStatus.PENDING
        assert task.assigned_to is None

        with patch(
            "ag3ntwerk.core.plugins.dispatch_plugin_event", new_callable=AsyncMock, return_value=[]
        ):
            result = await mgr.delegate(task, "SP1")

        assert result.success is True
        assert task.status == TaskStatus.DELEGATED
        assert task.assigned_to == "SP1"


@pytest.mark.integration
class TestModuleCircuitBreakerResilience:
    """Test 10: Module integration with circuit breaker resilience."""

    async def test_module_with_circuit_breaker_pattern(self):
        """
        Simulate using a circuit breaker around module calls.

        The circuit breaker protects the system from repeated module failures.
        """
        breaker = CircuitBreaker(
            name="brand-module",
            failure_threshold=2,
            recovery_timeout=0.05,
        )
        integration = ModuleIntegration()
        orch = _make_mock_orchestrator()
        integration.connect_learning(orch)

        call_count = 0

        def failing_brand_task(task_type, params):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("module unavailable")

        integration._execute_brand_task = failing_brand_task

        # First two calls go through and fail, tripping the breaker
        for _ in range(2):
            if breaker.allow_request():
                try:
                    await integration.execute_module_task(
                        module_id="brand",
                        task_type="get_identity",
                        params={},
                    )
                    breaker.record_success()
                except RuntimeError:
                    breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
        assert call_count == 2

        # Third call is rejected by circuit breaker without hitting the module
        assert breaker.allow_request() is False
        assert call_count == 2  # no additional calls

        # Wait for recovery, then half-open allows one probe
        time.sleep(0.06)
        assert breaker.state == CircuitState.HALF_OPEN

        # Fix the module
        integration._execute_brand_task = MagicMock(return_value={"success": True})

        if breaker.allow_request():
            result = await integration.execute_module_task(
                module_id="brand",
                task_type="get_identity",
                params={},
            )
            breaker.record_success()

        assert breaker.state == CircuitState.CLOSED
        assert result["success"] is True
