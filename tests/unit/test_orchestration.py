"""
Tests for the orchestration module.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.orchestration.base import (
    WorkflowStatus,
    StepStatus,
    WorkflowStep,
    WorkflowContext,
    WorkflowResult,
    Workflow,
    Orchestrator,
)
from ag3ntwerk.orchestration.registry import AgentRegistry
from ag3ntwerk.orchestration.workflows import (
    ProductLaunchWorkflow,
    IncidentResponseWorkflow,
    BudgetApprovalWorkflow,
    FeatureReleaseWorkflow,
)
from ag3ntwerk.core.base import Task, TaskResult


class TestWorkflowStatus:
    """Tests for WorkflowStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        assert WorkflowStatus.PENDING
        assert WorkflowStatus.IN_PROGRESS
        assert WorkflowStatus.COMPLETED
        assert WorkflowStatus.FAILED
        assert WorkflowStatus.CANCELLED
        assert WorkflowStatus.PAUSED


class TestStepStatus:
    """Tests for StepStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        assert StepStatus.PENDING
        assert StepStatus.IN_PROGRESS
        assert StepStatus.COMPLETED
        assert StepStatus.FAILED
        assert StepStatus.SKIPPED


class TestWorkflowStep:
    """Tests for WorkflowStep dataclass."""

    def test_step_creation(self):
        """Test creating a workflow step."""
        step = WorkflowStep(
            name="test_step",
            agent="Blueprint",
            task_type="product_spec",
            description="Test step description",
        )

        assert step.name == "test_step"
        assert step.agent == "Blueprint"
        assert step.task_type == "product_spec"
        assert step.description == "Test step description"
        assert step.required is True
        assert step.depends_on == []
        assert step.status == StepStatus.PENDING

    def test_step_with_dependencies(self):
        """Test step with dependencies."""
        step = WorkflowStep(
            name="dependent_step",
            agent="Keystone",
            task_type="budget_planning",
            description="Depends on others",
            depends_on=["step1", "step2"],
            required=False,
        )

        assert step.depends_on == ["step1", "step2"]
        assert step.required is False

    def test_step_to_dict(self):
        """Test step serialization."""
        step = WorkflowStep(
            name="test_step",
            agent="Blueprint",
            task_type="product_spec",
            description="Test",
        )
        step.status = StepStatus.COMPLETED
        step.result = {"key": "value"}
        step.started_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        step.completed_at = datetime(2025, 1, 1, 12, 5, 0, tzinfo=timezone.utc)

        data = step.to_dict()

        assert data["name"] == "test_step"
        assert data["agent"] == "Blueprint"
        assert data["status"] == "completed"
        assert data["result"] == {"key": "value"}
        assert data["started_at"] is not None
        assert data["completed_at"] is not None


class TestWorkflowContext:
    """Tests for WorkflowContext dataclass."""

    def test_context_creation(self):
        """Test creating a workflow context."""
        ctx = WorkflowContext(
            workflow_id="wf-123",
            workflow_name="test_workflow",
            initial_params={"product": "GozerAI"},
        )

        assert ctx.workflow_id == "wf-123"
        assert ctx.workflow_name == "test_workflow"
        assert ctx.initial_params == {"product": "GozerAI"}
        assert ctx.step_results == {}

    def test_context_get(self):
        """Test getting values from context."""
        ctx = WorkflowContext(
            workflow_id="wf-123",
            workflow_name="test",
            initial_params={"key1": "value1"},
        )
        ctx.step_results["step1"] = {"key2": "value2"}

        # Get from initial params
        assert ctx.get("key1") == "value1"

        # Get from step results (takes precedence)
        ctx.step_results["key1"] = "overridden"
        assert ctx.get("key1") == "overridden"

        # Get with default
        assert ctx.get("missing", "default") == "default"

    def test_context_set_step_result(self):
        """Test setting step results."""
        ctx = WorkflowContext(
            workflow_id="wf-123",
            workflow_name="test",
            initial_params={},
        )

        ctx.set_step_result("step1", {"result": "data"})

        assert ctx.step_results["step1"] == {"result": "data"}

    def test_context_to_dict(self):
        """Test context serialization."""
        ctx = WorkflowContext(
            workflow_id="wf-123",
            workflow_name="test",
            initial_params={"key": "value"},
        )

        data = ctx.to_dict()

        assert data["workflow_id"] == "wf-123"
        assert data["workflow_name"] == "test"
        assert data["initial_params"] == {"key": "value"}
        assert "started_at" in data


class TestWorkflowResult:
    """Tests for WorkflowResult dataclass."""

    def test_result_success(self):
        """Test successful workflow result."""
        result = WorkflowResult(
            workflow_id="wf-123",
            workflow_name="test",
            status=WorkflowStatus.COMPLETED,
            steps=[{"name": "step1", "status": "completed"}],
            output={"key": "value"},
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2025, 1, 1, 12, 5, 0, tzinfo=timezone.utc),
        )

        assert result.success is True
        assert result.duration_seconds == 300.0

    def test_result_failure(self):
        """Test failed workflow result."""
        result = WorkflowResult(
            workflow_id="wf-123",
            workflow_name="test",
            status=WorkflowStatus.FAILED,
            steps=[],
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"

    def test_result_to_dict(self):
        """Test result serialization."""
        result = WorkflowResult(
            workflow_id="wf-123",
            workflow_name="test",
            status=WorkflowStatus.COMPLETED,
            steps=[],
        )

        data = result.to_dict()

        assert data["workflow_id"] == "wf-123"
        assert data["status"] == "completed"
        assert data["success"] is True


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    def test_registry_creation(self):
        """Test creating a registry."""
        registry = AgentRegistry(auto_register=True)

        assert "Blueprint" in registry
        assert "Keystone" in registry
        assert "Foundry" in registry

    def test_registry_list_agents(self):
        """Test listing agents."""
        registry = AgentRegistry()

        agents = registry.list_agents()

        assert len(agents) > 0
        codes = [e["code"] for e in agents]
        assert "Blueprint" in codes
        assert "Keystone" in codes

    def test_registry_get_available_codes(self):
        """Test getting available codes."""
        registry = AgentRegistry()

        codes = registry.get_available_codes()

        # Should include implemented agents
        assert "Blueprint" in codes
        assert "Keystone" in codes

    def test_registry_get_agent(self):
        """Test getting an agent."""
        mock_provider = MagicMock()
        registry = AgentRegistry(llm_provider=mock_provider)

        # Get should lazily instantiate
        cpo = registry.get("Blueprint")

        assert cpo is not None
        assert cpo.code == "Blueprint"

    def test_registry_get_by_codename(self):
        """Test getting agent by codename."""
        mock_provider = MagicMock()
        registry = AgentRegistry(llm_provider=mock_provider)

        blueprint = registry.get_by_codename("Blueprint")

        assert blueprint is not None
        assert blueprint.code == "Blueprint"

    def test_registry_contains(self):
        """Test checking if agent exists."""
        registry = AgentRegistry()

        assert "Blueprint" in registry
        assert "Keystone" in registry
        assert "FAKE" not in registry

    def test_registry_getitem(self):
        """Test getting agent with []."""
        mock_provider = MagicMock()
        registry = AgentRegistry(llm_provider=mock_provider)

        cpo = registry["Blueprint"]

        assert cpo is not None
        assert cpo.code == "Blueprint"

    def test_registry_getitem_not_found(self):
        """Test KeyError for missing agent."""
        registry = AgentRegistry()

        with pytest.raises(KeyError):
            _ = registry["FAKE"]

    def test_registry_clear(self):
        """Test clearing cached agents."""
        mock_provider = MagicMock()
        registry = AgentRegistry(llm_provider=mock_provider)

        # Instantiate an agent
        _ = registry.get("Blueprint")
        assert "Blueprint" in registry._executives

        # Clear
        registry.clear()
        assert "Blueprint" not in registry._executives


class SimpleTestWorkflow(Workflow):
    """Simple workflow for testing."""

    @property
    def name(self) -> str:
        return "simple_test"

    def define_steps(self) -> list:
        return [
            WorkflowStep(
                name="step1",
                agent="Blueprint",
                task_type="product_spec",
                description="First step",
            ),
            WorkflowStep(
                name="step2",
                agent="Keystone",
                task_type="budget_planning",
                description="Second step",
                depends_on=["step1"],
            ),
        ]


class TestWorkflow:
    """Tests for Workflow base class."""

    def test_workflow_execution_order(self):
        """Test that steps are ordered by dependencies."""
        mock_registry = MagicMock()
        workflow = SimpleTestWorkflow(mock_registry)

        # Need to set _steps before calling _get_execution_order
        workflow._steps = workflow.define_steps()
        ordered = workflow._get_execution_order()

        # step1 should come before step2
        step_names = [s.name for s in ordered]
        assert step_names.index("step1") < step_names.index("step2")

    def test_dependencies_met(self):
        """Test dependency checking."""
        mock_registry = MagicMock()
        workflow = SimpleTestWorkflow(mock_registry)

        steps = workflow.define_steps()
        step2 = steps[1]  # Has dependency on step1

        # Not met
        assert workflow._dependencies_met(step2, []) is False

        # Met
        assert workflow._dependencies_met(step2, ["step1"]) is True

    @pytest.mark.asyncio
    async def test_workflow_execute(self):
        """Test workflow execution."""
        # Create mock agents
        mock_cpo = MagicMock()
        mock_cpo.execute = AsyncMock(
            return_value=TaskResult(
                task_id="t1",
                success=True,
                output={"spec": "data"},
            )
        )

        mock_cfo = MagicMock()
        mock_cfo.execute = AsyncMock(
            return_value=TaskResult(
                task_id="t2",
                success=True,
                output={"budget": "approved"},
            )
        )

        # Create mock registry
        mock_registry = MagicMock()
        mock_registry.get = MagicMock(
            side_effect=lambda code: {
                "Blueprint": mock_cpo,
                "Keystone": mock_cfo,
            }.get(code)
        )

        workflow = SimpleTestWorkflow(mock_registry)
        result = await workflow.execute(product="Test")

        assert result.success is True
        assert result.status == WorkflowStatus.COMPLETED
        assert len(result.steps) == 2

    @pytest.mark.asyncio
    async def test_workflow_execute_step_failure(self):
        """Test workflow handles step failure."""
        mock_cpo = MagicMock()
        mock_cpo.execute = AsyncMock(
            return_value=TaskResult(
                task_id="t1",
                success=False,
                error="Step failed",
            )
        )

        mock_registry = MagicMock()
        mock_registry.get = MagicMock(return_value=mock_cpo)

        workflow = SimpleTestWorkflow(mock_registry)
        result = await workflow.execute(product="Test")

        assert result.success is False
        assert result.status == WorkflowStatus.FAILED
        assert "step1" in result.error


class TestOrchestrator:
    """Tests for Orchestrator."""

    def test_register_workflow(self):
        """Test registering workflows."""
        mock_registry = MagicMock()
        orchestrator = Orchestrator(mock_registry)

        orchestrator.register_workflow(SimpleTestWorkflow)

        assert "simple_test" in orchestrator._workflows

    def test_list_workflows(self):
        """Test listing workflows."""
        mock_registry = MagicMock()
        orchestrator = Orchestrator(mock_registry)
        orchestrator.register_workflow(SimpleTestWorkflow)

        workflows = orchestrator.list_workflows()

        assert len(workflows) == 1
        assert workflows[0]["name"] == "simple_test"

    @pytest.mark.asyncio
    async def test_orchestrator_execute(self):
        """Test executing workflow through orchestrator."""
        mock_cpo = MagicMock()
        mock_cpo.execute = AsyncMock(
            return_value=TaskResult(
                task_id="t1",
                success=True,
                output={"spec": "data"},
            )
        )

        mock_cfo = MagicMock()
        mock_cfo.execute = AsyncMock(
            return_value=TaskResult(
                task_id="t2",
                success=True,
                output={"budget": "approved"},
            )
        )

        mock_registry = MagicMock()
        mock_registry.get = MagicMock(
            side_effect=lambda code: {
                "Blueprint": mock_cpo,
                "Keystone": mock_cfo,
            }.get(code)
        )

        orchestrator = Orchestrator(mock_registry)
        orchestrator.register_workflow(SimpleTestWorkflow)

        result = await orchestrator.execute("simple_test", product="Test")

        assert result.success is True
        assert len(orchestrator.get_history()) == 1

    @pytest.mark.asyncio
    async def test_orchestrator_unknown_workflow(self):
        """Test error on unknown workflow."""
        mock_registry = MagicMock()
        orchestrator = Orchestrator(mock_registry)

        with pytest.raises(ValueError, match="Unknown workflow"):
            await orchestrator.execute("nonexistent")


class TestProductLaunchWorkflow:
    """Tests for ProductLaunchWorkflow."""

    def test_workflow_name(self):
        """Test workflow has correct name."""
        mock_registry = MagicMock()
        workflow = ProductLaunchWorkflow(mock_registry)

        assert workflow.name == "product_launch"

    def test_workflow_steps(self):
        """Test workflow defines expected steps."""
        mock_registry = MagicMock()
        workflow = ProductLaunchWorkflow(mock_registry)

        steps = workflow.define_steps()
        step_names = [s.name for s in steps]

        assert "product_strategy" in step_names
        assert "budget_analysis" in step_names
        assert "security_review" in step_names
        assert "engineering_assessment" in step_names
        assert "marketing_plan" in step_names
        assert "customer_success_plan" in step_names
        assert "launch_approval" in step_names


class TestIncidentResponseWorkflow:
    """Tests for IncidentResponseWorkflow."""

    def test_workflow_name(self):
        """Test workflow has correct name."""
        mock_registry = MagicMock()
        workflow = IncidentResponseWorkflow(mock_registry)

        assert workflow.name == "incident_response"

    def test_workflow_steps(self):
        """Test workflow defines expected steps."""
        mock_registry = MagicMock()
        workflow = IncidentResponseWorkflow(mock_registry)

        steps = workflow.define_steps()
        step_names = [s.name for s in steps]

        assert "initial_assessment" in step_names
        assert "security_check" in step_names
        assert "customer_impact" in step_names
        assert "remediation_plan" in step_names
        assert "customer_communication" in step_names
        assert "post_incident_review" in step_names


class TestBudgetApprovalWorkflow:
    """Tests for BudgetApprovalWorkflow."""

    def test_workflow_name(self):
        """Test workflow has correct name."""
        mock_registry = MagicMock()
        workflow = BudgetApprovalWorkflow(mock_registry)

        assert workflow.name == "budget_approval"

    def test_workflow_steps(self):
        """Test workflow defines expected steps."""
        mock_registry = MagicMock()
        workflow = BudgetApprovalWorkflow(mock_registry)

        steps = workflow.define_steps()
        step_names = [s.name for s in steps]

        assert "budget_analysis" in step_names
        assert "product_impact" in step_names
        assert "technical_feasibility" in step_names
        assert "final_approval" in step_names


class TestFeatureReleaseWorkflow:
    """Tests for FeatureReleaseWorkflow."""

    def test_workflow_name(self):
        """Test workflow has correct name."""
        mock_registry = MagicMock()
        workflow = FeatureReleaseWorkflow(mock_registry)

        assert workflow.name == "feature_release"

    def test_workflow_steps(self):
        """Test workflow defines expected steps."""
        mock_registry = MagicMock()
        workflow = FeatureReleaseWorkflow(mock_registry)

        steps = workflow.define_steps()
        step_names = [s.name for s in steps]

        assert "feature_review" in step_names
        assert "security_check" in step_names
        assert "release_execution" in step_names
        assert "adoption_tracking" in step_names
