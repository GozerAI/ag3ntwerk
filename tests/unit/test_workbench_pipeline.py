"""
Unit tests for Workbench Pipeline.

Tests the pipeline orchestration, schemas, and deployers.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.modules.workbench.pipeline_schemas import (
    DatabaseOptions,
    DatabaseType,
    DeploymentTarget,
    DeployResult,
    EvaluationOptions,
    PipelineOptions,
    PipelineResult,
    PipelineStatus,
    SecretsOptions,
    StageResult,
    StageStatus,
)


# =============================================================================
# Pipeline Schema Tests
# =============================================================================


class TestPipelineSchemas:
    """Tests for pipeline Pydantic models."""

    def test_deployment_target_enum(self):
        """Test DeploymentTarget enum values."""
        assert DeploymentTarget.VERCEL == "vercel"
        assert DeploymentTarget.DOCKER_REGISTRY == "docker_registry"
        assert DeploymentTarget.LOCAL_PREVIEW == "local"

    def test_database_type_enum(self):
        """Test DatabaseType enum values."""
        assert DatabaseType.POSTGRES == "postgres"
        assert DatabaseType.MYSQL == "mysql"
        assert DatabaseType.SQLITE == "sqlite"
        assert DatabaseType.MONGODB == "mongodb"

    def test_pipeline_options_defaults(self):
        """Test PipelineOptions default values."""
        options = PipelineOptions()

        assert options.skip_stages == []
        assert options.deployment_target == DeploymentTarget.LOCAL_PREVIEW
        assert options.database_type is None
        assert options.generate_secrets is False
        assert options.auto_fix is True
        assert options.coverage_target == 80
        assert options.quality_thresholds == {}
        assert options.environment_config == {}

    def test_pipeline_options_custom_values(self):
        """Test PipelineOptions with custom values."""
        options = PipelineOptions(
            skip_stages=["test_execution"],
            deployment_target=DeploymentTarget.VERCEL,
            auto_fix=False,
            coverage_target=90,
        )

        assert options.skip_stages == ["test_execution"]
        assert options.deployment_target == DeploymentTarget.VERCEL
        assert options.auto_fix is False
        assert options.coverage_target == 90

    def test_evaluation_options_defaults(self):
        """Test EvaluationOptions default values."""
        options = EvaluationOptions()

        assert options.review_scope == "full"
        assert options.focus_areas == []
        assert options.security_standards == ["OWASP"]

    def test_database_options(self):
        """Test DatabaseOptions model."""
        options = DatabaseOptions(
            database_type=DatabaseType.POSTGRES,
            db_name="myapp_db",
            migration_tool="alembic",
        )

        assert options.database_type == DatabaseType.POSTGRES
        assert options.db_name == "myapp_db"
        assert options.migration_tool == "alembic"

    def test_secrets_options(self):
        """Test SecretsOptions model."""
        options = SecretsOptions(
            secret_types=["api_key", "jwt_secret"],
            encryption_method="aes256",
        )

        assert "api_key" in options.secret_types
        assert options.encryption_method == "aes256"

    def test_stage_result_to_dict(self):
        """Test StageResult.to_dict() method."""
        stage = StageResult(
            name="code_review",
            status=StageStatus.COMPLETED,
            agent="Forge",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            completed_at=datetime(2024, 1, 1, 12, 5, 0),
            duration_seconds=300.0,
            output={"issues": 5},
        )

        result = stage.to_dict()

        assert result["name"] == "code_review"
        assert result["status"] == "completed"
        assert result["agent"] == "Forge"
        assert result["duration_seconds"] == 300.0
        assert result["output"] == {"issues": 5}

    def test_pipeline_result_to_dict(self):
        """Test PipelineResult.to_dict() method."""
        pipeline = PipelineResult(
            pipeline_id="pipe-abc123",
            workspace_id="ws-xyz",
            pipeline_type="full",
            status=PipelineStatus.COMPLETED,
            deployment_url="https://example.vercel.app",
        )

        result = pipeline.to_dict()

        assert result["pipeline_id"] == "pipe-abc123"
        assert result["workspace_id"] == "ws-xyz"
        assert result["pipeline_type"] == "full"
        assert result["status"] == "completed"
        assert result["deployment_url"] == "https://example.vercel.app"

    def test_deploy_result_to_dict(self):
        """Test DeployResult.to_dict() method."""
        deploy = DeployResult(
            deployment_id="deploy-123",
            target=DeploymentTarget.VERCEL,
            status="success",
            url="https://myapp.vercel.app",
        )

        result = deploy.to_dict()

        assert result["deployment_id"] == "deploy-123"
        assert result["target"] == "vercel"
        assert result["status"] == "success"
        assert result["url"] == "https://myapp.vercel.app"


# =============================================================================
# Deployer Tests
# =============================================================================


class TestDeployers:
    """Tests for deployer implementations."""

    def test_get_deployer_vercel(self):
        """Test getting Vercel deployer."""
        from ag3ntwerk.modules.workbench.deployers import get_deployer, VercelDeployer

        deployer = get_deployer(DeploymentTarget.VERCEL)
        assert isinstance(deployer, VercelDeployer)
        assert deployer.target == DeploymentTarget.VERCEL
        assert deployer.name == "Vercel"

    def test_get_deployer_docker(self):
        """Test getting Docker deployer."""
        from ag3ntwerk.modules.workbench.deployers import get_deployer, DockerRegistryDeployer

        deployer = get_deployer(DeploymentTarget.DOCKER_REGISTRY)
        assert isinstance(deployer, DockerRegistryDeployer)
        assert deployer.target == DeploymentTarget.DOCKER_REGISTRY
        assert deployer.name == "Docker Registry"

    def test_get_deployer_local(self):
        """Test getting Local deployer."""
        from ag3ntwerk.modules.workbench.deployers import get_deployer, LocalDeployer

        deployer = get_deployer(DeploymentTarget.LOCAL_PREVIEW)
        assert isinstance(deployer, LocalDeployer)
        assert deployer.target == DeploymentTarget.LOCAL_PREVIEW
        assert deployer.name == "Local Preview"

    def test_vercel_parse_url(self):
        """Test Vercel URL parsing."""
        from ag3ntwerk.modules.workbench.deployers.vercel import VercelDeployer

        deployer = VercelDeployer()

        # Test standard Vercel URL
        url = deployer._parse_vercel_url("Deployment complete: https://myproject-abc123.vercel.app")
        assert url == "https://myproject-abc123.vercel.app"

        # Test production URL
        url = deployer._parse_vercel_url("Production: https://myproject.vercel.app")
        assert url == "https://myproject.vercel.app"

        # Test no URL
        url = deployer._parse_vercel_url("Some other output")
        assert url is None

    def test_local_detect_port(self):
        """Test local deployer port detection."""
        from ag3ntwerk.modules.workbench.deployers.local import LocalDeployer

        deployer = LocalDeployer()

        # Test explicit PORT
        port = deployer._detect_app_port({"PORT": "8080"})
        assert port == 8080

        # Test framework-based detection
        port = deployer._detect_app_port({"FRAMEWORK": "nextjs"})
        assert port == 3000

        port = deployer._detect_app_port({"FRAMEWORK": "flask"})
        assert port == 5000

        # Test default
        port = deployer._detect_app_port({})
        assert port == 3000


# =============================================================================
# Pipeline Class Tests
# =============================================================================


class TestWorkbenchPipeline:
    """Tests for WorkbenchPipeline class."""

    @pytest.fixture
    def mock_workbench_service(self):
        """Create a mock workbench service."""
        service = MagicMock()
        service.get_workspace = AsyncMock()
        service.start_workspace = AsyncMock()
        service.run_command = AsyncMock()
        service.run_command_sync = AsyncMock()
        service.expose_port = AsyncMock()
        service.list_files = AsyncMock(return_value=["main.py", "requirements.txt"])
        return service

    @pytest.fixture
    def mock_workspace(self):
        """Create a mock workspace."""
        workspace = MagicMock()
        workspace.id = "ws-test123"
        workspace.path = "/workspace"
        workspace.status = MagicMock()
        workspace.status.value = "running"
        return workspace

    def test_generate_pipeline_id(self, mock_workbench_service):
        """Test pipeline ID generation."""
        from ag3ntwerk.modules.workbench.pipeline import WorkbenchPipeline

        pipeline = WorkbenchPipeline(mock_workbench_service)
        id1 = pipeline._generate_pipeline_id()
        id2 = pipeline._generate_pipeline_id()

        assert id1.startswith("pipe-")
        assert id2.startswith("pipe-")
        assert id1 != id2  # IDs should be unique

    @pytest.mark.asyncio
    async def test_get_pipeline_status_not_found(self, mock_workbench_service):
        """Test getting status of non-existent pipeline."""
        from ag3ntwerk.modules.workbench.pipeline import WorkbenchPipeline

        pipeline = WorkbenchPipeline(mock_workbench_service)
        result = await pipeline.get_pipeline_status("pipe-nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_pipeline_not_found(self, mock_workbench_service):
        """Test cancelling non-existent pipeline."""
        from ag3ntwerk.modules.workbench.pipeline import WorkbenchPipeline

        pipeline = WorkbenchPipeline(mock_workbench_service)
        result = await pipeline.cancel_pipeline("pipe-nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_pipeline_logs_not_found(self, mock_workbench_service):
        """Test getting logs of non-existent pipeline."""
        from ag3ntwerk.modules.workbench.pipeline import WorkbenchPipeline

        pipeline = WorkbenchPipeline(mock_workbench_service)

        with pytest.raises(ValueError, match="Pipeline not found"):
            await pipeline.get_pipeline_logs("pipe-nonexistent")


# =============================================================================
# Workflow Tests
# =============================================================================


class TestPipelineWorkflows:
    """Tests for pipeline workflow definitions."""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock registry for workflow tests."""
        return MagicMock()

    def test_code_evaluation_deployment_workflow(self, mock_registry):
        """Test CodeEvaluationDeploymentWorkflow structure."""
        from ag3ntwerk.orchestration.workflows import CodeEvaluationDeploymentWorkflow

        workflow = CodeEvaluationDeploymentWorkflow(mock_registry)

        assert workflow.name == "code_evaluation_deployment"
        assert "evaluation" in workflow.description.lower()

        steps = workflow.define_steps()
        step_names = [s.name for s in steps]

        # Verify expected stages exist
        assert "code_review" in step_names
        assert "security_review" in step_names
        assert "bug_fix" in step_names
        assert "sast_scan" in step_names
        assert "test_planning" in step_names
        assert "test_execution" in step_names
        assert "quality_gate" in step_names
        assert "build" in step_names
        assert "deploy" in step_names

        # Verify dependencies
        bug_fix_step = next(s for s in steps if s.name == "bug_fix")
        assert "code_review" in bug_fix_step.depends_on
        assert "security_review" in bug_fix_step.depends_on

    def test_database_provisioning_workflow(self, mock_registry):
        """Test DatabaseProvisioningWorkflow structure."""
        from ag3ntwerk.orchestration.workflows import DatabaseProvisioningWorkflow

        workflow = DatabaseProvisioningWorkflow(mock_registry)

        assert workflow.name == "database_provisioning"
        assert "database" in workflow.description.lower()

        steps = workflow.define_steps()
        step_names = [s.name for s in steps]

        assert "schema_design" in step_names
        assert "db_provisioning" in step_names
        assert "migration_run" in step_names
        assert "data_seeding" in step_names

        # Verify Index handles schema
        schema_step = next(s for s in steps if s.name == "schema_design")
        assert schema_step.agent == "Index"

    def test_secrets_management_workflow(self, mock_registry):
        """Test SecretsManagementWorkflow structure."""
        from ag3ntwerk.orchestration.workflows import SecretsManagementWorkflow

        workflow = SecretsManagementWorkflow(mock_registry)

        assert workflow.name == "secrets_management"
        assert "secrets" in workflow.description.lower()

        steps = workflow.define_steps()
        step_names = [s.name for s in steps]

        assert "secret_audit" in step_names
        assert "secret_generation" in step_names
        assert "secret_encryption" in step_names
        assert "env_configuration" in step_names

        # Verify Citadel handles security steps
        audit_step = next(s for s in steps if s.name == "secret_audit")
        assert audit_step.agent == "Citadel"


# =============================================================================
# Nexus Routing Tests
# =============================================================================


class TestCOOWorkbenchRouting:
    """Tests for Overwatch workbench routing rules."""

    def test_workbench_routing_rules_exist(self):
        """Test that workbench routing rules are defined."""
        from ag3ntwerk.agents.overwatch.routing_rules import ROUTING_RULES

        # Check primary routing rules
        assert "workbench_pipeline" in ROUTING_RULES
        assert ROUTING_RULES["workbench_pipeline"] == "Overwatch"

        assert "workbench_evaluate" in ROUTING_RULES
        assert ROUTING_RULES["workbench_evaluate"] == "Forge"

        assert "workbench_security_scan" in ROUTING_RULES
        assert ROUTING_RULES["workbench_security_scan"] == "Citadel"

        assert "workbench_test" in ROUTING_RULES
        assert ROUTING_RULES["workbench_test"] == "Foundry"

        assert "workbench_deploy" in ROUTING_RULES
        assert ROUTING_RULES["workbench_deploy"] == "Foundry"

        assert "workbench_database" in ROUTING_RULES
        assert ROUTING_RULES["workbench_database"] == "Index"

        assert "workbench_secrets" in ROUTING_RULES
        assert ROUTING_RULES["workbench_secrets"] == "Citadel"

    def test_additional_task_types(self):
        """Test additional task types for pipeline stages."""
        from ag3ntwerk.agents.overwatch.routing_rules import ROUTING_RULES

        assert "containerization" in ROUTING_RULES
        assert "infrastructure" in ROUTING_RULES
        assert "configuration" in ROUTING_RULES
        assert "deployment_execution" in ROUTING_RULES
        assert "encryption" in ROUTING_RULES
