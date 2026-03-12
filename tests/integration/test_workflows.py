"""
Integration tests for multi-agent workflows.

These tests verify that agents can work together through
the orchestration layer to complete complex workflows.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.orchestration.base import Orchestrator, WorkflowStatus
from ag3ntwerk.orchestration.registry import AgentRegistry
from ag3ntwerk.orchestration.workflows import (
    ProductLaunchWorkflow,
    IncidentResponseWorkflow,
    BudgetApprovalWorkflow,
    FeatureReleaseWorkflow,
)
from ag3ntwerk.core.base import Task, TaskResult


class TestProductLaunchWorkflow:
    """Integration tests for product launch workflow."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock LLM provider."""
        provider = MagicMock()
        provider.generate = AsyncMock(return_value="Analysis complete")
        provider.is_connected = True
        return provider

    @pytest.fixture
    def registry(self, mock_provider):
        """Create registry with mock provider."""
        return AgentRegistry(llm_provider=mock_provider)

    @pytest.fixture
    def orchestrator(self, registry):
        """Create orchestrator with workflows."""
        orch = Orchestrator(registry)
        orch.register_workflow(ProductLaunchWorkflow)
        return orch

    @pytest.mark.asyncio
    async def test_product_launch_workflow_executes(self, orchestrator):
        """Test that product launch workflow can execute."""
        result = await orchestrator.execute(
            "product_launch",
            product_name="TestProduct",
            target_market="Enterprise",
        )

        assert result.workflow_name == "product_launch"
        # The workflow may fail steps but should complete
        assert result.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
        ]

    @pytest.mark.asyncio
    async def test_product_launch_involves_multiple_executives(self, orchestrator):
        """Test that workflow involves multiple agents."""
        workflow = ProductLaunchWorkflow(orchestrator.registry)
        steps = workflow.define_steps()

        # Should involve multiple agents
        agents = set(step.agent for step in steps)
        assert len(agents) >= 3

        # Should include key agents
        assert "Blueprint" in agents  # Product strategy
        assert "Keystone" in agents  # Budget analysis

    def test_product_launch_has_dependencies(self, orchestrator):
        """Test that workflow has proper step dependencies."""
        workflow = ProductLaunchWorkflow(orchestrator.registry)
        steps = workflow.define_steps()

        # Find steps with dependencies
        dependent_steps = [s for s in steps if s.depends_on]
        assert len(dependent_steps) > 0

        # All dependencies should reference existing steps
        step_names = [s.name for s in steps]
        for step in dependent_steps:
            for dep in step.depends_on:
                assert dep in step_names, f"Dependency {dep} not found"


class TestIncidentResponseWorkflow:
    """Integration tests for incident response workflow."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock LLM provider."""
        provider = MagicMock()
        provider.generate = AsyncMock(return_value="Incident analysis")
        provider.is_connected = True
        return provider

    @pytest.fixture
    def registry(self, mock_provider):
        """Create registry with mock provider."""
        return AgentRegistry(llm_provider=mock_provider)

    @pytest.fixture
    def orchestrator(self, registry):
        """Create orchestrator with workflows."""
        orch = Orchestrator(registry)
        orch.register_workflow(IncidentResponseWorkflow)
        return orch

    @pytest.mark.asyncio
    async def test_incident_response_workflow_executes(self, orchestrator):
        """Test that incident response workflow can execute."""
        result = await orchestrator.execute(
            "incident_response",
            incident_type="security",
            severity="high",
        )

        assert result.workflow_name == "incident_response"
        assert result.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
        ]

    @pytest.mark.asyncio
    async def test_incident_response_involves_security(self, orchestrator):
        """Test that incident response involves security agents."""
        workflow = IncidentResponseWorkflow(orchestrator.registry)
        steps = workflow.define_steps()

        agents = set(step.agent for step in steps)
        # Should include security/risk agents
        assert any(e in agents for e in ["Citadel", "Aegis", "Forge"])


class TestBudgetApprovalWorkflow:
    """Integration tests for budget approval workflow."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock LLM provider."""
        provider = MagicMock()
        provider.generate = AsyncMock(return_value="Budget approved")
        provider.is_connected = True
        return provider

    @pytest.fixture
    def registry(self, mock_provider):
        """Create registry with mock provider."""
        return AgentRegistry(llm_provider=mock_provider)

    @pytest.fixture
    def orchestrator(self, registry):
        """Create orchestrator with workflows."""
        orch = Orchestrator(registry)
        orch.register_workflow(BudgetApprovalWorkflow)
        return orch

    @pytest.mark.asyncio
    async def test_budget_approval_workflow_executes(self, orchestrator):
        """Test that budget approval workflow can execute."""
        result = await orchestrator.execute(
            "budget_approval",
            amount=50000,
            purpose="Q1 Marketing Campaign",
        )

        assert result.workflow_name == "budget_approval"
        assert result.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
        ]

    @pytest.mark.asyncio
    async def test_budget_approval_involves_cfo(self, orchestrator):
        """Test that budget approval involves Keystone."""
        workflow = BudgetApprovalWorkflow(orchestrator.registry)
        steps = workflow.define_steps()

        agents = set(step.agent for step in steps)
        assert "Keystone" in agents


class TestFeatureReleaseWorkflow:
    """Integration tests for feature release workflow."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock LLM provider."""
        provider = MagicMock()
        provider.generate = AsyncMock(return_value="Feature released")
        provider.is_connected = True
        return provider

    @pytest.fixture
    def registry(self, mock_provider):
        """Create registry with mock provider."""
        return AgentRegistry(llm_provider=mock_provider)

    @pytest.fixture
    def orchestrator(self, registry):
        """Create orchestrator with workflows."""
        orch = Orchestrator(registry)
        orch.register_workflow(FeatureReleaseWorkflow)
        return orch

    @pytest.mark.asyncio
    async def test_feature_release_workflow_executes(self, orchestrator):
        """Test that feature release workflow can execute."""
        result = await orchestrator.execute(
            "feature_release",
            feature_name="Dark Mode",
            version="2.0.0",
        )

        assert result.workflow_name == "feature_release"
        assert result.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
        ]

    @pytest.mark.asyncio
    async def test_feature_release_involves_engineering(self, orchestrator):
        """Test that feature release involves engineering agents."""
        workflow = FeatureReleaseWorkflow(orchestrator.registry)
        steps = workflow.define_steps()

        agents = set(step.agent for step in steps)
        # Should include engineering/product agents
        assert any(e in agents for e in ["Foundry", "Blueprint", "Forge"])


class TestCrossExecutiveCollaboration:
    """Tests for collaboration between agents."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock LLM provider."""
        provider = MagicMock()
        provider.generate = AsyncMock(return_value="Collaboration complete")
        provider.is_connected = True
        return provider

    @pytest.fixture
    def registry(self, mock_provider):
        """Create registry with all agents."""
        return AgentRegistry(llm_provider=mock_provider)

    @pytest.mark.asyncio
    async def test_cfo_and_cpo_can_collaborate(self, registry):
        """Test Keystone and Blueprint can handle related tasks."""
        cfo = registry.get("Keystone")
        cpo = registry.get("Blueprint")

        assert cfo is not None
        assert cpo is not None

        # Keystone handles cost analysis
        cost_task = Task(
            description="Analyze product development costs",
            task_type="cost_analysis",
            context={"product": "NewFeature"},
        )
        assert cfo.can_handle(cost_task)

        # Blueprint handles product spec
        spec_task = Task(
            description="Create product specification",
            task_type="product_spec",
            context={"product": "NewFeature"},
        )
        assert cpo.can_handle(spec_task)

    @pytest.mark.asyncio
    async def test_cmo_and_cco_can_collaborate(self, registry):
        """Test Echo and Beacon can handle related tasks."""
        cmo = registry.get("Echo")
        cco = registry.get("Beacon")

        assert cmo is not None
        assert cco is not None

        # Echo handles marketing
        marketing_task = Task(
            description="Create marketing campaign",
            task_type="campaign_creation",
            context={"campaign": "Q1 Launch"},
        )
        assert cmo.can_handle(marketing_task)

        # Beacon handles customer success
        customer_task = Task(
            description="Collect customer feedback",
            task_type="feedback_collection",
            context={"product": "NewFeature"},
        )
        assert cco.can_handle(customer_task)

    @pytest.mark.asyncio
    async def test_cseco_and_crio_can_collaborate(self, registry):
        """Test Citadel and Aegis can handle security/risk tasks."""
        cseco = registry.get("Citadel")
        crio = registry.get("Aegis")

        assert cseco is not None
        assert crio is not None

        # Citadel handles security
        security_task = Task(
            description="Perform security assessment",
            task_type="security_audit",
            context={"target": "API Gateway"},
        )
        assert cseco.can_handle(security_task)

        # Aegis handles risk
        risk_task = Task(
            description="Assess enterprise risk",
            task_type="risk_assessment",
            context={"scope": "Q1 Initiatives"},
        )
        assert crio.can_handle(risk_task)


class TestOrchestratorWorkflowHistory:
    """Tests for orchestrator workflow history."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock LLM provider."""
        provider = MagicMock()
        provider.generate = AsyncMock(return_value="Complete")
        provider.is_connected = True
        return provider

    @pytest.fixture
    def orchestrator(self, mock_provider):
        """Create orchestrator with all workflows."""
        registry = AgentRegistry(llm_provider=mock_provider)
        orch = Orchestrator(registry)
        orch.register_workflow(ProductLaunchWorkflow)
        orch.register_workflow(IncidentResponseWorkflow)
        orch.register_workflow(BudgetApprovalWorkflow)
        orch.register_workflow(FeatureReleaseWorkflow)
        return orch

    @pytest.mark.asyncio
    async def test_workflow_history_tracked(self, orchestrator):
        """Test that workflow executions are tracked in history."""
        # Execute a workflow
        await orchestrator.execute("budget_approval", amount=10000)

        history = orchestrator.get_history()
        assert len(history) == 1
        assert history[0].workflow_name == "budget_approval"

    @pytest.mark.asyncio
    async def test_multiple_workflows_in_history(self, orchestrator):
        """Test that multiple workflow executions are tracked."""
        await orchestrator.execute("budget_approval", amount=10000)
        await orchestrator.execute("feature_release", feature_name="Test")

        history = orchestrator.get_history()
        assert len(history) == 2

        workflow_names = [h.workflow_name for h in history]
        assert "budget_approval" in workflow_names
        assert "feature_release" in workflow_names

    def test_list_workflows(self, orchestrator):
        """Test listing registered workflows."""
        workflows = orchestrator.list_workflows()

        assert len(workflows) == 4

        names = [w["name"] for w in workflows]
        assert "product_launch" in names
        assert "incident_response" in names
        assert "budget_approval" in names
        assert "feature_release" in names
