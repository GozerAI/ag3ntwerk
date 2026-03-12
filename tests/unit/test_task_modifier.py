"""
Unit tests for the Task Modifier.

Tests:
- Timeout modifications
- Retry configuration
- Agent reassignment
- Priority adjustments
- Context hints
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.learning.task_modifier import (
    TaskModifier,
    ModifiedTask,
    TaskModification,
    create_task_modifier,
)
from ag3ntwerk.learning.failure_predictor import (
    FailurePredictor,
    FailureRisk,
    RiskLevel,
    Mitigation,
    MitigationType,
)
from ag3ntwerk.learning.load_balancer import (
    LoadBalancer,
    LoadBalanceDecision,
    AgentLoad,
)
from ag3ntwerk.learning.models import ErrorCategory


class TestTaskModification:
    """Test TaskModification dataclass."""

    def test_creation(self):
        mod = TaskModification(
            modification_type="timeout",
            field_name="timeout_ms",
            original_value=30000,
            new_value=45000,
            reason="Extended due to timeout risk",
        )
        assert mod.modification_type == "timeout"
        assert mod.original_value == 30000
        assert mod.new_value == 45000

    def test_to_dict(self):
        mod = TaskModification(
            modification_type="retry",
            field_name="max_retries",
            original_value=0,
            new_value=2,
            reason="Added retries",
        )
        d = mod.to_dict()
        assert d["modification_type"] == "retry"
        assert d["original_value"] == "0"
        assert d["new_value"] == "2"


class TestModifiedTask:
    """Test ModifiedTask dataclass."""

    def test_creation(self):
        result = ModifiedTask(
            original_task={"task_type": "code_review"},
            modified_task={"task_type": "code_review", "timeout_ms": 45000},
            modifications=[],
            was_modified=False,
            summary="No modifications needed",
        )
        assert result.was_modified is False

    def test_to_dict(self):
        result = ModifiedTask(
            original_task={"task_type": "test"},
            modified_task={"task_type": "test", "max_retries": 2},
            modifications=[TaskModification("retry", "max_retries", 0, 2, "Added retries")],
            was_modified=True,
            summary="1 modification applied",
        )
        d = result.to_dict()
        assert d["was_modified"] is True
        assert d["modification_count"] == 1
        assert len(d["modifications"]) == 1


class TestTaskModifier:
    """Test TaskModifier class."""

    @pytest.fixture
    def mock_failure_predictor(self):
        predictor = AsyncMock(spec=FailurePredictor)
        predictor.predict_failure_risk = AsyncMock(
            return_value=FailureRisk(
                score=0.2,
                risk_level=RiskLevel.LOW,
                primary_risk=ErrorCategory.TIMEOUT,
                task_type="code_review",
                agent_code="Forge",
            )
        )
        return predictor

    @pytest.fixture
    def mock_load_balancer(self):
        balancer = AsyncMock(spec=LoadBalancer)
        balancer.get_optimal_agent = AsyncMock(
            return_value=LoadBalanceDecision(
                chosen_agent="Forge",
                score=0.8,
                reasoning="Good capacity",
                all_scores=[("Forge", 0.8), ("Keystone", 0.7)],
            )
        )
        return balancer

    @pytest.fixture
    def modifier(self, mock_failure_predictor, mock_load_balancer):
        return TaskModifier(mock_failure_predictor, mock_load_balancer)

    @pytest.mark.asyncio
    async def test_no_modifications_low_risk(self, modifier, mock_failure_predictor):
        """Test that low risk tasks are not heavily modified."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.1,
            risk_level=RiskLevel.LOW,
            primary_risk=None,
            task_type="code_review",
            agent_code="Forge",
        )

        task = {"task_type": "code_review"}
        result = await modifier.modify_task(task, "Forge")

        # Low risk should have minimal or no modifications
        assert result.failure_risk.risk_level == RiskLevel.LOW

    @pytest.mark.asyncio
    async def test_timeout_extension_high_risk(self, modifier, mock_failure_predictor):
        """Test timeout extension for high timeout risk."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.75,
            risk_level=RiskLevel.HIGH,
            primary_risk=ErrorCategory.TIMEOUT,
            task_type="long_task",
            agent_code="Forge",
            risk_factors=["High timeout rate"],
            mitigations=[Mitigation(MitigationType.EXTEND_TIMEOUT, "Extend timeout", 0.8)],
        )

        task = {"task_type": "long_task", "timeout_ms": 30000}
        result = await modifier.modify_task(task, "Forge")

        assert result.was_modified is True
        # Check timeout was extended
        timeout_mods = [m for m in result.modifications if m.modification_type == "timeout"]
        assert len(timeout_mods) == 1
        assert result.modified_task["timeout_ms"] > 30000

    @pytest.mark.asyncio
    async def test_retry_configuration_resource_risk(self, modifier, mock_failure_predictor):
        """Test retry configuration for resource errors."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.5,
            risk_level=RiskLevel.MODERATE,
            primary_risk=ErrorCategory.RESOURCE,
            task_type="api_call",
            agent_code="Forge",
            risk_factors=["Resource constraints"],
            mitigations=[Mitigation(MitigationType.ADD_RETRY, "Add retries", 0.7)],
        )

        task = {"task_type": "api_call", "max_retries": 0}
        result = await modifier.modify_task(task, "Forge")

        # Check retries were added
        retry_mods = [m for m in result.modifications if m.modification_type == "retry"]
        assert len(retry_mods) == 1
        assert result.modified_task["max_retries"] > 0

    @pytest.mark.asyncio
    async def test_no_retry_for_logic_errors(self, modifier, mock_failure_predictor):
        """Test that logic errors don't get retries."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.6,
            risk_level=RiskLevel.MODERATE,
            primary_risk=ErrorCategory.LOGIC,  # Logic errors shouldn't retry
            task_type="calculation",
            agent_code="Forge",
        )

        task = {"task_type": "calculation", "max_retries": 0}
        result = await modifier.modify_task(task, "Forge")

        # Check no retries were added for logic errors
        retry_mods = [m for m in result.modifications if m.modification_type == "retry"]
        assert len(retry_mods) == 0
        assert result.modified_task.get("max_retries", 0) == 0

    @pytest.mark.asyncio
    async def test_agent_reassignment_load_balanced(
        self, modifier, mock_failure_predictor, mock_load_balancer
    ):
        """Test agent reassignment based on load balancing."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.3,
            risk_level=RiskLevel.LOW,
            primary_risk=ErrorCategory.TIMEOUT,
            task_type="code_review",
            agent_code="Forge",
        )

        # Load balancer strongly prefers Keystone
        mock_load_balancer.get_optimal_agent.return_value = LoadBalanceDecision(
            chosen_agent="Keystone",
            score=0.9,
            reasoning="Keystone has much better capacity",
            all_scores=[("Keystone", 0.9), ("Forge", 0.5)],
            load_metrics={
                "Keystone": AgentLoad(agent_code="Keystone", utilization=0.2),
                "Forge": AgentLoad(agent_code="Forge", utilization=0.8),
            },
        )

        task = {"task_type": "code_review"}
        result = await modifier.modify_task(task, "Forge", candidates=["Forge", "Keystone"])

        # Check agent was reassigned
        agent_mods = [m for m in result.modifications if m.modification_type == "agent"]
        assert len(agent_mods) == 1
        assert result.modified_task["target_agent"] == "Keystone"

    @pytest.mark.asyncio
    async def test_no_reassignment_when_similar_scores(
        self, modifier, mock_failure_predictor, mock_load_balancer
    ):
        """Test no reassignment when load balance scores are similar."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.2,
            risk_level=RiskLevel.LOW,
            primary_risk=ErrorCategory.TIMEOUT,
            task_type="code_review",
            agent_code="Forge",
        )

        # Similar scores - shouldn't reassign
        mock_load_balancer.get_optimal_agent.return_value = LoadBalanceDecision(
            chosen_agent="Keystone",
            score=0.82,  # Only slightly better
            reasoning="Marginally better",
            all_scores=[("Keystone", 0.82), ("Forge", 0.80)],  # Within 15%
        )

        task = {"task_type": "code_review"}
        result = await modifier.modify_task(task, "Forge", candidates=["Forge", "Keystone"])

        # Should not reassign for marginal improvement
        agent_mods = [m for m in result.modifications if m.modification_type == "agent"]
        assert len(agent_mods) == 0

    @pytest.mark.asyncio
    async def test_fallback_agent_capability_risk(self, modifier, mock_failure_predictor):
        """Test fallback agent addition for capability risk."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.8,
            risk_level=RiskLevel.HIGH,
            primary_risk=ErrorCategory.CAPABILITY,
            task_type="specialized_task",
            agent_code="Forge",
            mitigations=[
                Mitigation(
                    MitigationType.USE_FALLBACK_AGENT,
                    "Use fallback agent",
                    0.85,
                    parameters={"fallback_agent": "Keystone"},
                )
            ],
        )

        task = {"task_type": "specialized_task"}
        result = await modifier.modify_task(task, "Forge")

        # Check fallback was added
        fallback_mods = [m for m in result.modifications if m.modification_type == "fallback"]
        assert len(fallback_mods) == 1
        assert result.modified_task.get("fallback_agent") == "Keystone"

    @pytest.mark.asyncio
    async def test_priority_increase_critical_risk(
        self, modifier, mock_failure_predictor, mock_load_balancer
    ):
        """Test priority increase for critical risk."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.9,
            risk_level=RiskLevel.CRITICAL,
            primary_risk=ErrorCategory.TIMEOUT,
            task_type="critical_task",
            agent_code="Forge",
        )

        task = {"task_type": "critical_task", "priority": 5}
        result = await modifier.modify_task(task, "Forge")

        # Check priority was increased (lower number = higher priority)
        priority_mods = [m for m in result.modifications if m.modification_type == "priority"]
        assert len(priority_mods) == 1
        assert result.modified_task["priority"] < 5

    @pytest.mark.asyncio
    async def test_priority_decrease_high_load(
        self, modifier, mock_failure_predictor, mock_load_balancer
    ):
        """Test priority decrease when system load is high."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.3,
            risk_level=RiskLevel.LOW,
            primary_risk=ErrorCategory.TIMEOUT,
            task_type="normal_task",
            agent_code="Forge",
        )

        # High system load
        mock_load_balancer.get_optimal_agent.return_value = LoadBalanceDecision(
            chosen_agent="Forge",
            score=0.5,
            reasoning="High load",
            all_scores=[("Forge", 0.5)],
            load_metrics={
                "Forge": AgentLoad(agent_code="Forge", utilization=0.85),
                "Keystone": AgentLoad(agent_code="Keystone", utilization=0.9),
            },
        )

        task = {"task_type": "normal_task", "priority": 5}
        result = await modifier.modify_task(task, "Forge", candidates=["Forge", "Keystone"])

        # Check priority was decreased (higher number = lower priority)
        priority_mods = [m for m in result.modifications if m.modification_type == "priority"]
        assert len(priority_mods) == 1
        assert result.modified_task["priority"] > 5

    @pytest.mark.asyncio
    async def test_context_hints_added(self, modifier, mock_failure_predictor):
        """Test that context hints are added for moderate+ risk."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.6,
            risk_level=RiskLevel.MODERATE,
            primary_risk=ErrorCategory.TIMEOUT,
            task_type="risky_task",
            agent_code="Forge",
            risk_factors=[
                "Recent errors detected",
                "High task complexity",
            ],
            mitigations=[Mitigation(MitigationType.EXTEND_TIMEOUT, "Extend timeout", 0.7)],
        )

        task = {"task_type": "risky_task"}
        result = await modifier.modify_task(task, "Forge")

        # Check hints were added
        context_mods = [m for m in result.modifications if m.modification_type == "context"]
        assert len(context_mods) == 1
        assert "execution_hints" in result.modified_task
        assert len(result.modified_task["execution_hints"]) > 0

    @pytest.mark.asyncio
    async def test_summary_generated(self, modifier, mock_failure_predictor):
        """Test that a summary is generated."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.7,
            risk_level=RiskLevel.HIGH,
            primary_risk=ErrorCategory.TIMEOUT,
            task_type="test",
            agent_code="Forge",
        )

        task = {"task_type": "test", "timeout_ms": 30000}
        result = await modifier.modify_task(task, "Forge")

        assert result.summary
        assert "risk" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_multiple_modifications_combined(self, modifier, mock_failure_predictor):
        """Test that multiple modifications can be applied together."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.85,
            risk_level=RiskLevel.CRITICAL,
            primary_risk=ErrorCategory.TIMEOUT,
            task_type="complex_task",
            agent_code="Forge",
            risk_factors=["High timeout rate"],
            mitigations=[
                Mitigation(MitigationType.EXTEND_TIMEOUT, "Extend timeout", 0.9),
            ],
        )

        task = {"task_type": "complex_task", "timeout_ms": 30000, "priority": 5}
        result = await modifier.modify_task(task, "Forge")

        # Should have multiple modifications
        assert len(result.modifications) >= 2  # At least timeout + priority

        # Verify different types
        mod_types = {m.modification_type for m in result.modifications}
        assert "timeout" in mod_types
        assert "priority" in mod_types


class TestTaskModifierFactory:
    """Test the factory function."""

    @pytest.mark.asyncio
    async def test_create_task_modifier(self):
        """Test creating task modifier via factory."""
        mock_db = AsyncMock()

        modifier = await create_task_modifier(mock_db)

        assert isinstance(modifier, TaskModifier)
        assert modifier._failure_predictor is not None
        assert modifier._load_balancer is not None


class TestTaskModifierEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def mock_failure_predictor(self):
        return AsyncMock(spec=FailurePredictor)

    @pytest.fixture
    def mock_load_balancer(self):
        return AsyncMock(spec=LoadBalancer)

    @pytest.mark.asyncio
    async def test_empty_task(self, mock_failure_predictor, mock_load_balancer):
        """Test handling of minimal task."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.1,
            risk_level=RiskLevel.LOW,
            primary_risk=None,
            task_type="unknown",
            agent_code="Forge",
        )

        modifier = TaskModifier(mock_failure_predictor, mock_load_balancer)
        result = await modifier.modify_task({}, "Forge")

        assert result is not None
        assert result.modified_task is not None

    @pytest.mark.asyncio
    async def test_no_load_balancing_single_candidate(
        self, mock_failure_predictor, mock_load_balancer
    ):
        """Test that load balancing is skipped for single candidate."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.1,
            risk_level=RiskLevel.LOW,
            primary_risk=ErrorCategory.TIMEOUT,
            task_type="test",
            agent_code="Forge",
        )

        modifier = TaskModifier(mock_failure_predictor, mock_load_balancer)
        result = await modifier.modify_task(
            {"task_type": "test"},
            "Forge",
            candidates=["Forge"],  # Only one candidate
        )

        # Load balancer should not be called for single candidate
        mock_load_balancer.get_optimal_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_preserve_existing_task_fields(self, mock_failure_predictor, mock_load_balancer):
        """Test that existing task fields are preserved."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.1,
            risk_level=RiskLevel.LOW,
            primary_risk=ErrorCategory.TIMEOUT,
            task_type="test",
            agent_code="Forge",
        )

        modifier = TaskModifier(mock_failure_predictor, mock_load_balancer)

        task = {
            "task_type": "test",
            "custom_field": "custom_value",
            "another_field": 123,
        }
        result = await modifier.modify_task(task, "Forge")

        # Original fields should be preserved
        assert result.modified_task["custom_field"] == "custom_value"
        assert result.modified_task["another_field"] == 123

    @pytest.mark.asyncio
    async def test_default_timeout_used(self, mock_failure_predictor, mock_load_balancer):
        """Test that default timeout is used when not specified."""
        mock_failure_predictor.predict_failure_risk.return_value = FailureRisk(
            score=0.75,
            risk_level=RiskLevel.HIGH,
            primary_risk=ErrorCategory.TIMEOUT,
            task_type="test",
            agent_code="Forge",
        )

        modifier = TaskModifier(mock_failure_predictor, mock_load_balancer)

        task = {"task_type": "test"}  # No timeout specified
        result = await modifier.modify_task(task, "Forge")

        # Should use default and extend it
        timeout_mods = [m for m in result.modifications if m.modification_type == "timeout"]
        if timeout_mods:
            assert timeout_mods[0].original_value == TaskModifier.DEFAULT_TIMEOUT_MS
