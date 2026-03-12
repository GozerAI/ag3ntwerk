"""
Workbench Pipeline - Nexus-Orchestrated Code Evaluation and Deployment.

This module provides the interface for orchestrating code evaluation/deployment
pipelines using existing ag3ntwerk specialists. The Workbench provides the execution
surface (containers, files) while the Nexus orchestrates specialists from Forge,
Foundry, Citadel, and Index.

Architecture:
    User Request → WorkbenchPipeline → Nexus Orchestrator → Agent Specialists
                        ↓
                  Workbench Service
                  (containers, files, ports)

Example:
    ```python
    from ag3ntwerk.modules.workbench import WorkbenchService, WorkbenchPipeline
    from ag3ntwerk.modules.workbench.pipeline_schemas import PipelineOptions, DeploymentTarget

    service = get_workbench_service()
    pipeline = WorkbenchPipeline(service)

    result = await pipeline.run_full_pipeline(
        workspace_id="ws-123",
        options=PipelineOptions(
            deployment_target=DeploymentTarget.VERCEL,
            generate_secrets=True,
        ),
    )
    ```
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ag3ntwerk.core.logging import get_logger

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

if TYPE_CHECKING:
    from ag3ntwerk.modules.workbench.service import WorkbenchService
    from ag3ntwerk.orchestration import AgentRegistry, Workflow

logger = get_logger(__name__)


class WorkbenchPipeline:
    """
    Interface for orchestrating code evaluation/deployment pipelines.

    Uses existing Workbench for execution surface (containers, files)
    and Nexus for specialist recruitment and workflow orchestration.

    Attributes:
        _workbench: WorkbenchService instance for container operations
        _registry: AgentRegistry for accessing agents and workflows
        _active_pipelines: Dict tracking active pipeline executions
    """

    def __init__(
        self,
        workbench_service: "WorkbenchService",
        registry: Optional["AgentRegistry"] = None,
    ):
        """
        Initialize the pipeline interface.

        Args:
            workbench_service: WorkbenchService for container/file operations
            registry: Optional AgentRegistry. If not provided, creates one.
        """
        self._workbench = workbench_service
        self._registry = registry
        self._active_pipelines: Dict[str, PipelineResult] = {}

    async def _get_registry(self) -> "AgentRegistry":
        """Get or create the agent registry."""
        if self._registry is None:
            from ag3ntwerk.orchestration import AgentRegistry

            self._registry = AgentRegistry()
        return self._registry

    def _generate_pipeline_id(self) -> str:
        """Generate a unique pipeline ID."""
        return f"pipe-{uuid.uuid4().hex[:12]}"

    async def _execute_workflow(
        self,
        workflow: "Workflow",
        context: Dict[str, Any],
        pipeline_result: PipelineResult,
    ) -> Dict[str, Any]:
        """
        Execute a workflow and update pipeline result with stage progress.

        Args:
            workflow: Workflow instance to execute
            context: Context dict for workflow
            pipeline_result: PipelineResult to update

        Returns:
            Workflow result dict
        """
        from ag3ntwerk.orchestration import WorkflowContext

        # Create workflow context
        wf_context = WorkflowContext(initial_data=context)

        # Get steps for tracking
        steps = workflow.define_steps()

        # Initialize stage results
        for step in steps:
            stage_result = StageResult(
                name=step.name,
                status=StageStatus.PENDING,
                agent=step.agent,
            )
            pipeline_result.stages.append(stage_result)

        # Execute workflow
        registry = await self._get_registry()
        try:
            result = await workflow.execute(registry, **context)

            # Update stage results from workflow result
            if hasattr(result, "step_results"):
                for name, step_result in result.step_results.items():
                    for stage in pipeline_result.stages:
                        if stage.name == name:
                            stage.status = StageStatus.COMPLETED
                            stage.output = step_result
                            stage.completed_at = datetime.now(timezone.utc)

            return result.to_dict() if hasattr(result, "to_dict") else {"result": result}

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            # Mark remaining stages as failed
            for stage in pipeline_result.stages:
                if stage.status == StageStatus.RUNNING:
                    stage.status = StageStatus.FAILED
                    stage.error = str(e)
            raise

    async def run_evaluation(
        self,
        workspace_id: str,
        options: Optional[EvaluationOptions] = None,
    ) -> PipelineResult:
        """
        Run code evaluation only (no deployment).

        Stages:
        1. Code Review (Forge)
        2. Security Review (Forge)

        Args:
            workspace_id: Workspace to evaluate
            options: Evaluation options

        Returns:
            PipelineResult with evaluation findings
        """
        options = options or EvaluationOptions()
        pipeline_id = self._generate_pipeline_id()

        pipeline_result = PipelineResult(
            pipeline_id=pipeline_id,
            workspace_id=workspace_id,
            pipeline_type="evaluation",
            status=PipelineStatus.RUNNING,
        )
        self._active_pipelines[pipeline_id] = pipeline_result

        try:
            # Get workspace info
            workspace = await self._workbench.get_workspace(workspace_id)
            if not workspace:
                raise ValueError(f"Workspace not found: {workspace_id}")

            # Execute code review via Forge
            registry = await self._get_registry()
            cto = registry.get_agent("Forge")

            # Stage 1: Code Review
            code_review_stage = StageResult(
                name="code_review",
                status=StageStatus.RUNNING,
                agent="Forge",
                started_at=datetime.now(timezone.utc),
            )
            pipeline_result.stages.append(code_review_stage)

            code_review_result = await cto.process_task(
                {
                    "task_type": "code_review",
                    "workspace_id": workspace_id,
                    "workspace_path": str(workspace.path),
                    "review_scope": options.review_scope,
                    "focus_areas": options.focus_areas,
                }
            )

            code_review_stage.status = StageStatus.COMPLETED
            code_review_stage.completed_at = datetime.now(timezone.utc)
            code_review_stage.output = code_review_result

            # Stage 2: Security Review
            security_stage = StageResult(
                name="security_review",
                status=StageStatus.RUNNING,
                agent="Forge",
                started_at=datetime.now(timezone.utc),
            )
            pipeline_result.stages.append(security_stage)

            security_result = await cto.process_task(
                {
                    "task_type": "security_review",
                    "workspace_id": workspace_id,
                    "workspace_path": str(workspace.path),
                    "security_standards": options.security_standards,
                }
            )

            security_stage.status = StageStatus.COMPLETED
            security_stage.completed_at = datetime.now(timezone.utc)
            security_stage.output = security_result

            # Complete pipeline
            pipeline_result.status = PipelineStatus.COMPLETED
            pipeline_result.completed_at = datetime.now(timezone.utc)
            pipeline_result.duration_seconds = (
                pipeline_result.completed_at - pipeline_result.started_at
            ).total_seconds()

        except Exception as e:
            logger.error(f"Evaluation pipeline failed: {e}")
            pipeline_result.status = PipelineStatus.FAILED
            pipeline_result.error = str(e)
            pipeline_result.completed_at = datetime.now(timezone.utc)

        return pipeline_result

    async def run_full_pipeline(
        self,
        workspace_id: str,
        options: Optional[PipelineOptions] = None,
    ) -> PipelineResult:
        """
        Run: Evaluate → Correct → Secure → Test → Build → Deploy.

        This is the main pipeline that takes code from evaluation through
        deployment using the CodeEvaluationDeploymentWorkflow.

        Args:
            workspace_id: Workspace ID to process
            options: Pipeline options

        Returns:
            PipelineResult with all stage results
        """
        options = options or PipelineOptions()
        pipeline_id = self._generate_pipeline_id()

        pipeline_result = PipelineResult(
            pipeline_id=pipeline_id,
            workspace_id=workspace_id,
            pipeline_type="full",
            status=PipelineStatus.RUNNING,
        )
        self._active_pipelines[pipeline_id] = pipeline_result

        try:
            # Get workspace info
            workspace = await self._workbench.get_workspace(workspace_id)
            if not workspace:
                raise ValueError(f"Workspace not found: {workspace_id}")

            # Ensure workspace is running
            if workspace.status.value != "running":
                workspace = await self._workbench.start_workspace(workspace_id)

            # Import workflow
            from ag3ntwerk.orchestration.workflows import CodeEvaluationDeploymentWorkflow

            workflow = CodeEvaluationDeploymentWorkflow()

            # Build context
            context = {
                "workspace_id": workspace_id,
                "code_path": str(workspace.path),
                "deployment_target": options.deployment_target,
                "auto_fix": options.auto_fix,
                "coverage_target": options.coverage_target,
                "quality_thresholds": options.quality_thresholds,
                "environment_config": options.environment_config,
                "skip_stages": options.skip_stages,
            }

            # Execute workflow
            result = await self._execute_workflow(workflow, context, pipeline_result)

            # Get deployment URL if available
            if "deploy" in result:
                deploy_result = result.get("deploy", {})
                pipeline_result.deployment_url = deploy_result.get("url")

            # Complete pipeline
            pipeline_result.status = PipelineStatus.COMPLETED
            pipeline_result.completed_at = datetime.now(timezone.utc)
            pipeline_result.duration_seconds = (
                pipeline_result.completed_at - pipeline_result.started_at
            ).total_seconds()
            pipeline_result.metadata = result

        except Exception as e:
            logger.error(f"Full pipeline failed: {e}")
            pipeline_result.status = PipelineStatus.FAILED
            pipeline_result.error = str(e)
            pipeline_result.completed_at = datetime.now(timezone.utc)

        return pipeline_result

    async def run_with_database(
        self,
        workspace_id: str,
        options: Optional[PipelineOptions] = None,
        db_options: Optional[DatabaseOptions] = None,
    ) -> PipelineResult:
        """
        Run full pipeline + database provisioning workflow.

        Stages:
        1. Full code pipeline (evaluate → deploy)
        2. Database provisioning (schema → provision → migrate → seed)

        Args:
            workspace_id: Workspace ID
            options: Pipeline options
            db_options: Database provisioning options

        Returns:
            PipelineResult with code and database stages
        """
        options = options or PipelineOptions()
        db_options = db_options or DatabaseOptions()
        pipeline_id = self._generate_pipeline_id()

        pipeline_result = PipelineResult(
            pipeline_id=pipeline_id,
            workspace_id=workspace_id,
            pipeline_type="full_with_database",
            status=PipelineStatus.RUNNING,
        )
        self._active_pipelines[pipeline_id] = pipeline_result

        try:
            # Run main code pipeline first
            code_result = await self.run_full_pipeline(workspace_id, options)

            # Copy stages from code pipeline
            pipeline_result.stages.extend(code_result.stages)

            if code_result.status == PipelineStatus.FAILED:
                pipeline_result.status = PipelineStatus.FAILED
                pipeline_result.error = f"Code pipeline failed: {code_result.error}"
                return pipeline_result

            # Now run database provisioning
            from ag3ntwerk.orchestration.workflows import DatabaseProvisioningWorkflow

            db_workflow = DatabaseProvisioningWorkflow()

            db_context = {
                "workspace_id": workspace_id,
                "database_type": db_options.database_type,
                "entities": db_options.entities,
                "seed_data": db_options.seed_data,
                "migration_tool": db_options.migration_tool,
            }

            await self._execute_workflow(db_workflow, db_context, pipeline_result)

            # Complete pipeline
            pipeline_result.status = PipelineStatus.COMPLETED
            pipeline_result.completed_at = datetime.now(timezone.utc)
            pipeline_result.duration_seconds = (
                pipeline_result.completed_at - pipeline_result.started_at
            ).total_seconds()
            pipeline_result.deployment_url = code_result.deployment_url

        except Exception as e:
            logger.error(f"Pipeline with database failed: {e}")
            pipeline_result.status = PipelineStatus.FAILED
            pipeline_result.error = str(e)
            pipeline_result.completed_at = datetime.now(timezone.utc)

        return pipeline_result

    async def run_with_secrets(
        self,
        workspace_id: str,
        options: Optional[PipelineOptions] = None,
        secrets_options: Optional[SecretsOptions] = None,
    ) -> PipelineResult:
        """
        Run full pipeline + secrets management workflow.

        Stages:
        1. Full code pipeline (evaluate → deploy)
        2. Secrets management (audit → generate → encrypt → configure)

        Args:
            workspace_id: Workspace ID
            options: Pipeline options
            secrets_options: Secrets management options

        Returns:
            PipelineResult with code and secrets stages
        """
        options = options or PipelineOptions()
        secrets_options = secrets_options or SecretsOptions()
        pipeline_id = self._generate_pipeline_id()

        pipeline_result = PipelineResult(
            pipeline_id=pipeline_id,
            workspace_id=workspace_id,
            pipeline_type="full_with_secrets",
            status=PipelineStatus.RUNNING,
        )
        self._active_pipelines[pipeline_id] = pipeline_result

        try:
            # Run secrets management first (to configure env before deployment)
            from ag3ntwerk.orchestration.workflows import SecretsManagementWorkflow

            secrets_workflow = SecretsManagementWorkflow()

            workspace = await self._workbench.get_workspace(workspace_id)
            if not workspace:
                raise ValueError(f"Workspace not found: {workspace_id}")

            secrets_context = {
                "workspace_id": workspace_id,
                "code_path": str(workspace.path),
                "secret_types": secrets_options.secret_types,
                "encryption_method": secrets_options.encryption_method,
                "env_file_path": secrets_options.env_file_path,
                "scan_for_exposed": secrets_options.scan_for_exposed,
            }

            await self._execute_workflow(secrets_workflow, secrets_context, pipeline_result)

            # Now run main code pipeline
            code_result = await self.run_full_pipeline(workspace_id, options)

            # Copy stages from code pipeline
            pipeline_result.stages.extend(code_result.stages)

            # Complete pipeline
            pipeline_result.status = (
                PipelineStatus.COMPLETED
                if code_result.status == PipelineStatus.COMPLETED
                else PipelineStatus.FAILED
            )
            pipeline_result.completed_at = datetime.now(timezone.utc)
            pipeline_result.duration_seconds = (
                pipeline_result.completed_at - pipeline_result.started_at
            ).total_seconds()
            pipeline_result.deployment_url = code_result.deployment_url

            if code_result.error:
                pipeline_result.error = code_result.error

        except Exception as e:
            logger.error(f"Pipeline with secrets failed: {e}")
            pipeline_result.status = PipelineStatus.FAILED
            pipeline_result.error = str(e)
            pipeline_result.completed_at = datetime.now(timezone.utc)

        return pipeline_result

    async def run_complete(
        self,
        workspace_id: str,
        options: Optional[PipelineOptions] = None,
        db_options: Optional[DatabaseOptions] = None,
        secrets_options: Optional[SecretsOptions] = None,
    ) -> PipelineResult:
        """
        Run all workflows: Code + Database + Secrets + Deploy.

        This is the comprehensive pipeline for production-ready deployment:
        1. Secrets management (audit, generate, encrypt)
        2. Full code pipeline (evaluate, correct, test, build)
        3. Database provisioning (schema, provision, migrate, seed)
        4. Final deployment

        Args:
            workspace_id: Workspace ID
            options: Pipeline options
            db_options: Database provisioning options
            secrets_options: Secrets management options

        Returns:
            PipelineResult with all stages
        """
        options = options or PipelineOptions()
        db_options = db_options or DatabaseOptions()
        secrets_options = secrets_options or SecretsOptions()
        pipeline_id = self._generate_pipeline_id()

        pipeline_result = PipelineResult(
            pipeline_id=pipeline_id,
            workspace_id=workspace_id,
            pipeline_type="complete",
            status=PipelineStatus.RUNNING,
        )
        self._active_pipelines[pipeline_id] = pipeline_result

        try:
            workspace = await self._workbench.get_workspace(workspace_id)
            if not workspace:
                raise ValueError(f"Workspace not found: {workspace_id}")

            # Phase 1: Secrets Management
            logger.info(f"Pipeline {pipeline_id}: Starting secrets management")
            from ag3ntwerk.orchestration.workflows import SecretsManagementWorkflow

            secrets_workflow = SecretsManagementWorkflow()
            secrets_context = {
                "workspace_id": workspace_id,
                "code_path": str(workspace.path),
                "secret_types": secrets_options.secret_types,
                "encryption_method": secrets_options.encryption_method,
                "env_file_path": secrets_options.env_file_path,
                "scan_for_exposed": secrets_options.scan_for_exposed,
            }
            await self._execute_workflow(secrets_workflow, secrets_context, pipeline_result)

            # Phase 2: Full Code Pipeline (without final deploy)
            logger.info(f"Pipeline {pipeline_id}: Starting code evaluation and build")
            from ag3ntwerk.orchestration.workflows import CodeEvaluationDeploymentWorkflow

            code_workflow = CodeEvaluationDeploymentWorkflow()
            code_context = {
                "workspace_id": workspace_id,
                "code_path": str(workspace.path),
                "deployment_target": options.deployment_target,
                "auto_fix": options.auto_fix,
                "coverage_target": options.coverage_target,
                "quality_thresholds": options.quality_thresholds,
                "environment_config": options.environment_config,
                "skip_stages": options.skip_stages + ["deploy"],  # Skip deploy for now
            }
            code_result = await self._execute_workflow(code_workflow, code_context, pipeline_result)

            # Phase 3: Database Provisioning
            logger.info(f"Pipeline {pipeline_id}: Starting database provisioning")
            from ag3ntwerk.orchestration.workflows import DatabaseProvisioningWorkflow

            db_workflow = DatabaseProvisioningWorkflow()
            db_context = {
                "workspace_id": workspace_id,
                "database_type": db_options.database_type,
                "entities": db_options.entities,
                "seed_data": db_options.seed_data,
                "migration_tool": db_options.migration_tool,
            }
            await self._execute_workflow(db_workflow, db_context, pipeline_result)

            # Phase 4: Final Deployment
            logger.info(f"Pipeline {pipeline_id}: Starting deployment")
            deploy_result = await self._deploy(workspace_id, options)

            deploy_stage = StageResult(
                name="final_deploy",
                status=StageStatus.COMPLETED if deploy_result.url else StageStatus.FAILED,
                agent="Foundry",
                started_at=deploy_result.started_at,
                completed_at=deploy_result.completed_at,
                output=deploy_result.to_dict(),
                error=deploy_result.error,
            )
            pipeline_result.stages.append(deploy_stage)
            pipeline_result.deployment_url = deploy_result.url

            # Complete pipeline
            pipeline_result.status = PipelineStatus.COMPLETED
            pipeline_result.completed_at = datetime.now(timezone.utc)
            pipeline_result.duration_seconds = (
                pipeline_result.completed_at - pipeline_result.started_at
            ).total_seconds()

            logger.info(f"Pipeline {pipeline_id}: Completed successfully")

        except Exception as e:
            logger.error(f"Complete pipeline failed: {e}")
            pipeline_result.status = PipelineStatus.FAILED
            pipeline_result.error = str(e)
            pipeline_result.completed_at = datetime.now(timezone.utc)

        return pipeline_result

    async def _deploy(
        self,
        workspace_id: str,
        options: PipelineOptions,
    ) -> DeployResult:
        """
        Execute deployment to target.

        Args:
            workspace_id: Workspace ID
            options: Pipeline options with deployment target

        Returns:
            DeployResult
        """
        from ag3ntwerk.modules.workbench.deployers import get_deployer

        deployer = get_deployer(options.deployment_target)
        return await deployer.deploy(
            workspace_id=workspace_id,
            workbench=self._workbench,
            options=options,
        )

    async def get_pipeline_status(self, pipeline_id: str) -> Optional[PipelineResult]:
        """Get the status of a pipeline execution."""
        return self._active_pipelines.get(pipeline_id)

    async def get_pipeline_logs(
        self,
        pipeline_id: str,
        stage: Optional[str] = None,
    ) -> str:
        """
        Get logs for a pipeline execution.

        Args:
            pipeline_id: Pipeline ID
            stage: Optional specific stage to get logs for

        Returns:
            Combined logs string
        """
        pipeline = self._active_pipelines.get(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline not found: {pipeline_id}")

        logs = []
        for stage_result in pipeline.stages:
            if stage and stage_result.name != stage:
                continue

            logs.append(f"=== Stage: {stage_result.name} ({stage_result.agent}) ===")
            logs.append(f"Status: {stage_result.status}")

            if stage_result.started_at:
                logs.append(f"Started: {stage_result.started_at.isoformat()}")
            if stage_result.completed_at:
                logs.append(f"Completed: {stage_result.completed_at.isoformat()}")
            if stage_result.error:
                logs.append(f"Error: {stage_result.error}")
            if stage_result.output:
                logs.append(f"Output: {stage_result.output}")
            logs.append("")

        return "\n".join(logs)

    async def cancel_pipeline(self, pipeline_id: str) -> bool:
        """
        Cancel a running pipeline.

        Args:
            pipeline_id: Pipeline ID to cancel

        Returns:
            True if cancelled, False if not found or already completed
        """
        pipeline = self._active_pipelines.get(pipeline_id)
        if not pipeline:
            return False

        if pipeline.status not in [PipelineStatus.PENDING, PipelineStatus.RUNNING]:
            return False

        pipeline.status = PipelineStatus.CANCELLED
        pipeline.completed_at = datetime.now(timezone.utc)

        # Mark running stages as cancelled
        for stage in pipeline.stages:
            if stage.status == StageStatus.RUNNING:
                stage.status = StageStatus.SKIPPED
                stage.completed_at = datetime.now(timezone.utc)

        return True


# =============================================================================
# Factory Functions
# =============================================================================


def get_workbench_pipeline(
    workbench_service: Optional["WorkbenchService"] = None,
    registry: Optional["AgentRegistry"] = None,
) -> WorkbenchPipeline:
    """
    Get a WorkbenchPipeline instance.

    Args:
        workbench_service: Optional WorkbenchService. Created if not provided.
        registry: Optional AgentRegistry. Created if not provided.

    Returns:
        Configured WorkbenchPipeline
    """
    if workbench_service is None:
        from ag3ntwerk.modules.workbench.service import get_workbench_service

        workbench_service = get_workbench_service()

    return WorkbenchPipeline(
        workbench_service=workbench_service,
        registry=registry,
    )
