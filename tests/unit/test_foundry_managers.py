"""
Unit tests for Foundry (Foundry) managers and specialists.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.foundry import (
    Foundry,
    DeliveryManager,
    QualityManager,
    DevOpsManager,
    SprintCoordinator,
    ReleaseEngineer,
    QAEngineer,
    QAAutomationEngineer,
    BuildEngineer,
    DeploymentEngineer,
)
from ag3ntwerk.core.base import Task, TaskStatus


class TestDeliveryManager:
    """Test DeliveryManager functionality."""

    @pytest.fixture
    def dm(self, mock_llm_provider):
        return DeliveryManager(llm_provider=mock_llm_provider)

    def test_dm_initialization(self, dm):
        assert dm.code == "DM"
        assert dm.name == "Delivery Manager"
        assert "sprint_planning" in dm.capabilities
        assert "release_coordination" in dm.capabilities

    def test_dm_can_handle_sprint(self, dm):
        task = Task(description="Plan sprint", task_type="sprint_planning")
        assert dm.can_handle(task) is True

    def test_dm_cannot_handle_quality(self, dm):
        task = Task(description="Run tests", task_type="quality_gate_check")
        assert dm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_dm_execute(self, dm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Sprint planned"))

        task = Task(
            description="Plan next sprint",
            task_type="sprint_planning",
            context={"team": "backend"},
        )

        result = await dm.execute(task)
        assert result.success is True


class TestQualityManager:
    """Test QualityManager functionality."""

    @pytest.fixture
    def qm(self, mock_llm_provider):
        return QualityManager(llm_provider=mock_llm_provider)

    def test_qm_initialization(self, qm):
        assert qm.code == "QM"
        assert qm.name == "Quality Manager"
        assert "quality_gate_check" in qm.capabilities
        assert "test_planning" in qm.capabilities

    def test_qm_can_handle_quality(self, qm):
        task = Task(description="Check quality gate", task_type="quality_gate_check")
        assert qm.can_handle(task) is True

    def test_qm_cannot_handle_deployment(self, qm):
        task = Task(description="Deploy app", task_type="deployment_execution")
        assert qm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_qm_execute(self, qm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Quality check passed")
        )

        task = Task(
            description="Check quality gate for release",
            task_type="quality_gate_check",
            context={"release": "v1.0"},
        )

        result = await qm.execute(task)
        assert result.success is True


class TestDevOpsManager:
    """Test DevOpsManager functionality."""

    @pytest.fixture
    def dvm(self, mock_llm_provider):
        return DevOpsManager(llm_provider=mock_llm_provider)

    def test_dvm_initialization(self, dvm):
        assert dvm.code == "DVM"
        assert dvm.name == "DevOps Manager"
        assert "pipeline_design" in dvm.capabilities
        assert "deployment_execution" in dvm.capabilities

    def test_dvm_can_handle_pipeline(self, dvm):
        task = Task(description="Design pipeline", task_type="pipeline_design")
        assert dvm.can_handle(task) is True

    def test_dvm_cannot_handle_sprint(self, dvm):
        task = Task(description="Plan sprint", task_type="sprint_planning")
        assert dvm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_dvm_execute(self, dvm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Pipeline designed"))

        task = Task(
            description="Design CI/CD pipeline",
            task_type="pipeline_design",
            context={"project": "api-service"},
        )

        result = await dvm.execute(task)
        assert result.success is True


class TestSprintCoordinator:
    """Test SprintCoordinator specialist."""

    @pytest.fixture
    def sc(self, mock_llm_provider):
        return SprintCoordinator(llm_provider=mock_llm_provider)

    def test_sc_initialization(self, sc):
        assert sc.code == "SC"
        assert sc.name == "Sprint Coordinator"
        assert "sprint_planning" in sc.capabilities

    def test_sc_can_handle(self, sc):
        task = Task(description="Plan sprint", task_type="sprint_planning")
        assert sc.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_sc_execute(self, sc, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Sprint coordination complete")
        )

        task = Task(
            description="Coordinate sprint activities",
            task_type="sprint_planning",
        )

        result = await sc.execute(task)
        assert result.success is True


class TestReleaseEngineer:
    """Test ReleaseEngineer specialist."""

    @pytest.fixture
    def re(self, mock_llm_provider):
        return ReleaseEngineer(llm_provider=mock_llm_provider)

    def test_re_initialization(self, re):
        assert re.code == "RE"
        assert re.name == "Release Engineer"
        assert "release_planning" in re.capabilities

    def test_re_can_handle(self, re):
        task = Task(description="Plan release", task_type="release_planning")
        assert re.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_re_execute(self, re, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Release planned"))

        task = Task(
            description="Plan release v2.0",
            task_type="release_planning",
        )

        result = await re.execute(task)
        assert result.success is True


class TestQAEngineer:
    """Test QAEngineer specialist."""

    @pytest.fixture
    def qae(self, mock_llm_provider):
        return QAEngineer(llm_provider=mock_llm_provider)

    def test_qae_initialization(self, qae):
        assert qae.code == "QAE"
        assert qae.name == "QA Engineer"
        assert "quality_gate_check" in qae.capabilities

    def test_qae_can_handle(self, qae):
        task = Task(description="Check quality gate", task_type="quality_gate_check")
        assert qae.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_qae_execute(self, qae, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Quality gate passed")
        )

        task = Task(
            description="Check quality gate for release",
            task_type="quality_gate_check",
        )

        result = await qae.execute(task)
        assert result.success is True


class TestQAAutomationEngineer:
    """Test QAAutomationEngineer specialist."""

    @pytest.fixture
    def tae(self, mock_llm_provider):
        return QAAutomationEngineer(llm_provider=mock_llm_provider)

    def test_tae_initialization(self, tae):
        assert tae.code == "TAE"
        assert tae.name == "QA Automation Engineer"
        assert "test_automation" in tae.capabilities

    def test_tae_can_handle(self, tae):
        task = Task(description="Automate tests", task_type="test_automation")
        assert tae.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_tae_execute(self, tae, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Tests automated"))

        task = Task(
            description="Create automated tests",
            task_type="test_automation",
        )

        result = await tae.execute(task)
        assert result.success is True


class TestBuildEngineer:
    """Test BuildEngineer specialist."""

    @pytest.fixture
    def be(self, mock_llm_provider):
        return BuildEngineer(llm_provider=mock_llm_provider)

    def test_be_initialization(self, be):
        assert be.code == "BE"
        assert be.name == "Build Engineer"
        assert "pipeline_design" in be.capabilities

    def test_be_can_handle(self, be):
        task = Task(description="Design pipeline", task_type="pipeline_design")
        assert be.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_be_execute(self, be, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Pipeline designed"))

        task = Task(
            description="Design CI/CD pipeline",
            task_type="pipeline_design",
        )

        result = await be.execute(task)
        assert result.success is True


class TestDeploymentEngineer:
    """Test DeploymentEngineer specialist."""

    @pytest.fixture
    def de(self, mock_llm_provider):
        return DeploymentEngineer(llm_provider=mock_llm_provider)

    def test_de_initialization(self, de):
        assert de.code == "DE"
        assert de.name == "Deployment Engineer"
        assert "deployment_execution" in de.capabilities

    def test_de_can_handle(self, de):
        task = Task(description="Execute deployment", task_type="deployment_execution")
        assert de.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_de_execute(self, de, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Deployment complete")
        )

        task = Task(
            description="Deploy to production",
            task_type="deployment_execution",
        )

        result = await de.execute(task)
        assert result.success is True


class TestCEngOManagerHierarchy:
    """Test Foundry manager and specialist hierarchy."""

    @pytest.fixture
    def cengo(self, mock_llm_provider):
        return Foundry(llm_provider=mock_llm_provider)

    def test_cengo_initialization(self, cengo):
        assert cengo.code == "Foundry"
        assert cengo.name == "Foundry"
        assert cengo.codename == "Foundry"

    def test_cengo_has_managers(self, cengo):
        """Test that Foundry has registered managers."""
        assert len(cengo.subordinates) == 3

        manager_codes = [m.code for m in cengo.subordinates]
        assert "DM" in manager_codes
        assert "QM" in manager_codes
        assert "DVM" in manager_codes

    def test_dm_has_specialists(self, cengo):
        """Test that DeliveryManager has specialists."""
        dm = cengo.get_subordinate("DM")
        assert dm is not None

        specialist_codes = [s.code for s in dm.subordinates]
        assert "SC" in specialist_codes
        assert "RE" in specialist_codes

    def test_qm_has_specialists(self, cengo):
        """Test that QualityManager has specialists."""
        qm = cengo.get_subordinate("QM")
        assert qm is not None

        specialist_codes = [s.code for s in qm.subordinates]
        assert "QAE" in specialist_codes
        assert "TAE" in specialist_codes

    def test_dvm_has_specialists(self, cengo):
        """Test that DevOpsManager has specialists."""
        dvm = cengo.get_subordinate("DVM")
        assert dvm is not None

        specialist_codes = [s.code for s in dvm.subordinates]
        assert "BE" in specialist_codes
        assert "DE" in specialist_codes

    def test_cengo_can_handle_sprint(self, cengo):
        """Test Foundry can handle sprint planning."""
        task = Task(description="Plan sprint", task_type="sprint_planning")
        assert cengo.can_handle(task) is True

    def test_cengo_can_handle_quality(self, cengo):
        """Test Foundry can handle quality tasks."""
        task = Task(description="Quality gate", task_type="quality_gate_check")
        assert cengo.can_handle(task) is True

    def test_cengo_can_handle_pipeline(self, cengo):
        """Test Foundry can handle pipeline tasks."""
        task = Task(description="Design pipeline", task_type="pipeline_design")
        assert cengo.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_cengo_delegate_to_manager(self, cengo, mock_llm_provider):
        """Test delegation from Foundry to manager."""
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Task delegated"))

        task = Task(
            description="Sprint planning for API team",
            task_type="sprint_planning",
        )

        result = await cengo.delegate(task, "DM")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_cengo_execute_sprint_task(self, cengo, mock_llm_provider):
        """Test Foundry execute sprint task."""
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Sprint planned successfully")
        )

        task = Task(
            description="Plan Q1 sprint",
            task_type="sprint_planning",
            context={"quarter": "Q1", "team": "platform"},
        )

        result = await cengo.execute(task)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_cengo_execute_deployment_task(self, cengo, mock_llm_provider):
        """Test Foundry execute deployment task."""
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Deployment executed")
        )

        task = Task(
            description="Deploy v2.0 to production",
            task_type="deployment_execution",
            context={"version": "v2.0", "environment": "production"},
        )

        result = await cengo.execute(task)
        assert result.success is True

    def test_cengo_engineering_metrics(self, cengo):
        """Test engineering metrics tracking."""
        metrics = cengo.get_engineering_metrics()

        assert metrics is not None
        assert hasattr(metrics, "total_sprints")
        assert hasattr(metrics, "active_pipelines")
        assert hasattr(metrics, "deployment_count")
