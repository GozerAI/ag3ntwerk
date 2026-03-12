"""
Unit tests for Overwatch (Overwatch) agent - internal coordination layer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.agents.overwatch import Overwatch, Overwatch
from ag3ntwerk.agents.overwatch.models import (
    DriftType,
    DriftSignal,
    StrategicContext,
    WorkflowStatus,
    TaskRoutingStrategy,
)
from ag3ntwerk.core.base import Task, TaskStatus, TaskPriority


class TestCoSAgent:
    """Tests for Overwatch agent."""

    def test_cos_creation(self):
        """Test Overwatch agent creation."""
        cos = Overwatch()

        assert cos.code == "Overwatch"
        assert cos.name == "Overwatch"
        assert cos.codename == "Overwatch"
        assert cos.domain == "Operations, Coordination, Task Routing"

    def test_overwatch_alias(self):
        """Test Overwatch is an alias for Overwatch."""
        assert Overwatch is Overwatch

        overwatch = Overwatch()
        assert overwatch.code == "Overwatch"
        assert overwatch.codename == "Overwatch"

    def test_cos_capabilities(self):
        """Test Overwatch has expected capabilities."""
        cos = Overwatch()

        expected_capabilities = [
            "task_routing",
            "task_delegation",
            "workflow_creation",
            "workflow_execution",
            "system_monitoring",
            "drift_detection",
        ]

        for cap in expected_capabilities:
            assert cap in cos.capabilities, f"Missing capability: {cap}"

    def test_can_handle_coordination_tasks(self):
        """Test Overwatch can handle coordination tasks."""
        cos = Overwatch()

        coordination_tasks = [
            "task_routing",
            "task_delegation",
            "workflow_creation",
            "workflow_execution",
        ]

        for task_type in coordination_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert cos.can_handle(task), f"Overwatch should handle {task_type}"


class TestCoSTaskRouting:
    """Tests for Overwatch task routing functionality."""

    def test_determine_target_agent_technical(self):
        """Test routing technical tasks to Forge."""
        cos = Overwatch()

        task = Task(
            description="Review authentication code",
            task_type="code_review",
        )

        target = cos._determine_target_agent(task)
        assert target == "Forge"

    def test_determine_target_agent_financial(self):
        """Test routing financial tasks to Keystone."""
        cos = Overwatch()

        task = Task(
            description="Analyze Q4 budget",
            task_type="budget_analysis",
        )

        target = cos._determine_target_agent(task)
        assert target == "Keystone"

    def test_determine_target_agent_security(self):
        """Test routing security tasks to Citadel."""
        cos = Overwatch()

        task = Task(
            description="Run security scan",
            task_type="security_scan",
        )

        target = cos._determine_target_agent(task)
        # security_scan routes to Citadel per ROUTING_RULES
        assert target == "Citadel"


class TestDriftDetection:
    """Tests for Overwatch drift detection functionality."""

    def test_drift_signal_creation(self):
        """Test creating drift signals."""
        signal = DriftSignal(
            drift_type=DriftType.PERFORMANCE,
            severity=0.7,
            description="Success rate dropped below threshold",
            affected_executive="Forge",
            current_value=0.5,
            threshold_value=0.7,
        )

        assert signal.drift_type == DriftType.PERFORMANCE
        assert signal.severity == 0.7
        assert signal.exceeds_tolerance is True  # > 0.5

    def test_drift_signal_below_tolerance(self):
        """Test drift signal below tolerance threshold."""
        signal = DriftSignal(
            drift_type=DriftType.LATENCY,
            severity=0.3,
            description="Minor latency increase",
        )

        assert signal.exceeds_tolerance is False  # <= 0.5

    def test_strategic_context_defaults(self):
        """Test strategic context default values."""
        context = StrategicContext()

        assert context.success_rate_threshold == 0.7
        assert context.latency_slo_ms == 5000.0
        assert context.max_agent_load == 0.9
        assert context.auto_escalation_enabled is True


class TestCoSModels:
    """Tests for Overwatch data models."""

    def test_drift_type_values(self):
        """Test all drift types exist."""
        expected_types = [
            "performance",
            "routing",
            "load",
            "conflict",
            "context",
            "resource",
            "latency",
        ]

        for dtype in expected_types:
            assert DriftType(dtype) is not None

    def test_workflow_status_values(self):
        """Test workflow status values."""
        statuses = [
            WorkflowStatus.PENDING,
            WorkflowStatus.QUEUED,
            WorkflowStatus.IN_PROGRESS,
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
        ]

        for status in statuses:
            assert status is not None

    def test_task_routing_strategy_values(self):
        """Test task routing strategy values."""
        strategies = [
            TaskRoutingStrategy.RULE_BASED,
            TaskRoutingStrategy.CAPABILITY_MATCH,
            TaskRoutingStrategy.LOAD_BALANCED,
            TaskRoutingStrategy.AI_DECISION,
        ]

        for strategy in strategies:
            assert strategy is not None


class TestCoSExecution:
    """Tests for Overwatch task execution."""

    @pytest.mark.asyncio
    async def test_execute_routing_task(self):
        """Test executing a routing task."""
        cos = Overwatch()

        # Mock subordinate for delegation
        mock_cto = MagicMock()
        mock_cto.code = "Forge"
        mock_cto.can_handle.return_value = True
        mock_cto.is_active = True
        mock_cto.execute = AsyncMock(
            return_value=MagicMock(
                success=True,
                output="Task completed",
            )
        )

        cos.register_subordinate(mock_cto)

        task = Task(
            description="Review code",
            task_type="code_review",
        )

        result = await cos.execute(task)

        # Overwatch should route this to Forge
        assert result.success or mock_cto.execute.called

    @pytest.mark.asyncio
    async def test_execute_workflow_task(self):
        """Test executing a workflow management task."""
        cos = Overwatch()

        task = Task(
            description="Create deployment workflow",
            task_type="workflow_creation",
        )

        result = await cos.execute(task)
        assert result is not None


class TestBackwardCompatibility:
    """Tests for backward compatibility with Nexus."""

    def test_coo_still_works(self):
        """Test that Nexus import still works (returns Overwatch)."""
        from ag3ntwerk.agents.nexus import Nexus

        coo = Nexus()
        # Nexus is now an alias for Overwatch
        assert coo.code == "Overwatch"
        assert coo.codename == "Overwatch"
