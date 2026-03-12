"""
Unit tests for Nexus (Nexus) agent.

Note: Nexus is now a deprecated alias for Overwatch (Overwatch).
These tests verify the backward-compatible import still works.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.agents.nexus import Nexus, Nexus
from ag3ntwerk.core.base import Task, TaskStatus, TaskPriority


class TestCOOAgent:
    """Tests for Nexus agent (now alias for Overwatch)."""

    def test_coo_creation(self):
        """Test Nexus agent creation (returns Overwatch instance)."""
        coo = Nexus()

        # Nexus is now an alias for Overwatch
        assert coo.code == "Overwatch"
        assert coo.name == "Overwatch"
        assert coo.codename == "Overwatch"
        assert "Coordination" in coo.domain

    def test_nexus_alias(self):
        """Test Nexus is an alias for Nexus (which is Overwatch)."""
        nexus = Nexus()

        assert nexus.code == "Overwatch"
        assert nexus.codename == "Overwatch"

    def test_can_handle_coordination_tasks(self):
        """Test Nexus can handle coordination tasks."""
        coo = Nexus()

        coordination_tasks = [
            "task_routing",
            "executive_coordination",
            "workflow_management",
            "priority_management",
        ]

        for task_type in coordination_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert coo.can_handle(task), f"Nexus should handle {task_type}"

    def test_coo_can_handle_any_task(self):
        """Test Nexus can handle any task type for routing."""
        coo = Nexus()

        # Nexus should be able to handle any task type since it routes to other agents
        various_tasks = [
            "code_review",  # Would route to Forge
            "cost_analysis",  # Would route to Keystone
            "campaign_creation",  # Would route to Echo
            "security_scan",  # Would route to Compass
        ]

        for task_type in various_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            # Nexus can handle by routing to appropriate agent
            assert coo.can_handle(task)


class TestCOOTaskRouting:
    """Tests for Nexus task routing functionality via ROUTING_RULES."""

    def test_routing_rules_technical_tasks(self):
        """Test routing technical tasks to Forge in ROUTING_RULES."""
        from ag3ntwerk.agents.overwatch.routing_rules import ROUTING_RULES

        technical_tasks = ["code_review", "debugging", "testing", "deployment"]
        for task_type in technical_tasks:
            assert ROUTING_RULES.get(task_type) == "Forge", f"{task_type} should route to Forge"

    def test_routing_rules_financial_tasks(self):
        """Test routing financial tasks to Keystone in ROUTING_RULES."""
        from ag3ntwerk.agents.overwatch.routing_rules import ROUTING_RULES

        financial_tasks = ["cost_analysis", "budget_planning", "financial_modeling"]
        for task_type in financial_tasks:
            assert ROUTING_RULES.get(task_type) == "Keystone", f"{task_type} should route to Keystone"

    def test_routing_rules_marketing_tasks(self):
        """Test routing marketing tasks to Echo in ROUTING_RULES."""
        from ag3ntwerk.agents.overwatch.routing_rules import ROUTING_RULES

        marketing_tasks = ["campaign_creation", "brand_strategy", "campaign_management"]
        for task_type in marketing_tasks:
            assert ROUTING_RULES.get(task_type) == "Echo", f"{task_type} should route to Echo"

    def test_routing_rules_product_tasks(self):
        """Test routing product tasks to Blueprint in ROUTING_RULES."""
        from ag3ntwerk.agents.overwatch.routing_rules import ROUTING_RULES

        product_tasks = ["roadmap_update", "feature_prioritization", "sprint_planning"]
        for task_type in product_tasks:
            assert ROUTING_RULES.get(task_type) == "Blueprint", f"{task_type} should route to Blueprint"


class TestCOOExecute:
    """Tests for Nexus task execution."""

    @pytest.mark.asyncio
    async def test_execute_task_routing(self):
        """Test executing task routing."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Task routed successfully")

        coo = Nexus(llm_provider=mock_provider)

        task = Task(
            description="Route this task to the appropriate agent",
            task_type="task_routing",
            context={
                "original_task": "Analyze cloud costs",
                "original_type": "cost_analysis",
            },
        )

        result = await coo.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_workflow_management(self):
        """Test executing workflow management task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Workflow coordinated")

        coo = Nexus(llm_provider=mock_provider)

        task = Task(
            description="Manage product launch workflow",
            task_type="workflow_management",
            context={
                "workflow": "product_launch",
                "agents": ["Forge", "Echo", "Blueprint"],
            },
        )

        result = await coo.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_priority_management(self):
        """Test executing priority management task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Priorities set")

        coo = Nexus(llm_provider=mock_provider)

        task = Task(
            description="Prioritize Q2 initiatives",
            task_type="priority_management",
            context={
                "initiatives": [
                    {"name": "Security Update", "urgency": "high"},
                    {"name": "New Feature", "urgency": "medium"},
                ],
            },
        )

        result = await coo.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_status_monitoring(self):
        """Test executing status monitoring task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Status report generated")

        coo = Nexus(llm_provider=mock_provider)

        task = Task(
            description="Generate agent status report",
            task_type="status_monitoring",
        )

        result = await coo.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_escalation_management(self):
        """Test executing escalation management task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Escalation handled")

        coo = Nexus(llm_provider=mock_provider)

        task = Task(
            description="Handle critical incident escalation",
            task_type="escalation_management",
            context={
                "incident": "Database outage",
                "severity": "critical",
                "escalated_from": "Forge",
            },
        )

        result = await coo.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self):
        """Test handling of LLM errors during execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=Exception("LLM Error"))

        coo = Nexus(llm_provider=mock_provider)

        task = Task(
            description="Route task",
            task_type="task_routing",
        )

        result = await coo.execute(task)

        assert result.success is False
        assert "failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_without_provider(self):
        """Test execution without LLM provider."""
        coo = Nexus(llm_provider=None)

        task = Task(
            description="Unknown task",
            task_type="unknown_type",
        )

        result = await coo.execute(task)

        assert result.success is False
        # Error message may vary, just check it exists
        assert result.error is not None


class TestCOOCrossExecutiveCoordination:
    """Tests for Nexus cross-agent coordination."""

    @pytest.mark.asyncio
    async def test_coordinate_multi_executive_task(self):
        """Test coordinating task across multiple agents."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Coordination complete")

        coo = Nexus(llm_provider=mock_provider)

        task = Task(
            description="Coordinate product launch across teams",
            task_type="cross_functional_coordination",
            context={
                "agents": ["Forge", "Echo", "Blueprint"],
                "objective": "Launch new AI product",
            },
        )

        result = await coo.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_delegate_to_executive(self):
        """Test delegating task to specific agent."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Delegated successfully")

        coo = Nexus(llm_provider=mock_provider)

        task = Task(
            description="Delegate code review to Forge",
            task_type="task_routing",
            context={
                "delegate_to": "Forge",
                "task_details": "Review authentication module",
            },
        )

        result = await coo.execute(task)

        assert result.success is True
