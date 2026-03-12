"""
Workbench Module API Routes - FastAPI endpoints for the workbench module.

Provides REST API access to workspace management, command execution,
and development environment functionality.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ag3ntwerk.modules.workbench.pipeline import WorkbenchPipeline

from ag3ntwerk.modules.workbench.schemas import (
    Workspace,
    WorkspaceCreate,
    WorkspaceStatus,
    RuntimeType,
    RunRequest,
    RunResult,
    PortExposeRequest,
    PortExposeResult,
    FileWriteRequest,
    FileReadRequest,
    FileContent,
    WorkbenchStats,
    IDEInfo,
)
from ag3ntwerk.modules.workbench.service import WorkbenchService, get_workbench_service
from ag3ntwerk.modules.workbench.security import workbench_auth

logger = logging.getLogger(__name__)


# =============================================================================
# Additional Request/Response Models
# =============================================================================


class WorkspaceResponse(BaseModel):
    """Response model for workspace operations."""

    workspace: Dict[str, Any]


class WorkspaceListResponse(BaseModel):
    """Response model for workspace list."""

    workspaces: List[Dict[str, Any]]
    count: int


class RunResponse(BaseModel):
    """Response model for run operations."""

    run: Dict[str, Any]


class LogsResponse(BaseModel):
    """Response model for logs."""

    run_id: str
    logs: str


class PortsResponse(BaseModel):
    """Response model for port list."""

    ports: List[Dict[str, Any]]
    count: int


class FilesResponse(BaseModel):
    """Response model for file operations."""

    files: List[Dict[str, Any]]


class FileListResponse(BaseModel):
    """Response model for file listing."""

    files: List[str]
    count: int


class IDEResponse(BaseModel):
    """Response model for IDE URL."""

    workspace_id: str
    ide_url: str
    mode: str


class IDEStatusResponse(BaseModel):
    """Response model for IDE status."""

    workspace_id: str
    running: bool
    container_id: Optional[str] = None
    ide_url: Optional[str] = None
    auth_token: Optional[str] = None
    started_at: Optional[str] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[str] = None


class IDEStartRequest(BaseModel):
    """Request model for starting IDE."""

    password: Optional[str] = Field(
        None, description="Optional password. Auto-generated if not provided."
    )


class OneClickDeployRequest(BaseModel):
    """Request model for one-click deployment."""

    target: str = Field(
        "auto", description="Deployment target: auto, vercel, docker_registry, local"
    )
    generate_configs: bool = Field(
        True, description="Generate missing configs (Dockerfile, vercel.json)"
    )
    environment: Optional[Dict[str, str]] = Field(
        None, description="Additional environment variables"
    )


class DeployPreviewResponse(BaseModel):
    """Response model for deployment preview."""

    workspace_id: str
    detected_framework: str
    framework_version: Optional[str]
    build_command: Optional[str]
    start_command: Optional[str]
    recommended_target: str
    configs_needed: List[str]
    configs_existing: List[str]


class HealthResponse(BaseModel):
    """Response model for health check."""

    healthy: bool
    runner_type: str


class StatsResponse(BaseModel):
    """Response model for stats."""

    stats: Dict[str, Any]


# =============================================================================
# Service Singleton
# =============================================================================


_service: Optional[WorkbenchService] = None


def get_service() -> WorkbenchService:
    """Get or create the workbench service."""
    global _service
    if _service is None:
        _service = get_workbench_service()
    return _service


# =============================================================================
# Router
# =============================================================================


workbench_router = APIRouter(
    prefix="/api/v1/modules/workbench",
    tags=["Workbench"],
)


# =============================================================================
# Overview Endpoints
# =============================================================================


@workbench_router.get("/")
async def workbench_overview(auth: bool = Depends(workbench_auth)):
    """Get workbench module overview."""
    service = get_service()
    stats = service.get_stats()
    return {
        "module": "workbench",
        "primary_owner": "Forge",
        "description": "Development environment management and sandboxed runtimes",
        "stats": stats.to_dict(),
    }


@workbench_router.get("/health", response_model=HealthResponse)
async def health_check(auth: bool = Depends(workbench_auth)):
    """Check workbench service health."""
    service = get_service()
    healthy = await service.is_healthy()
    return HealthResponse(
        healthy=healthy,
        runner_type=service._settings.runner_type,
    )


@workbench_router.get("/stats", response_model=StatsResponse)
async def get_stats(auth: bool = Depends(workbench_auth)):
    """Get workbench statistics."""
    service = get_service()
    stats = service.get_stats()
    return StatsResponse(stats=stats.to_dict())


# =============================================================================
# Workspace Management Endpoints
# =============================================================================


@workbench_router.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(
    request: WorkspaceCreate,
    auth: bool = Depends(workbench_auth),
):
    """
    Create a new workspace.

    Creates a workspace directory and optionally initializes it from a template.
    The workspace runtime container is created but not started.
    """
    try:
        service = get_service()
        workspace = await service.create_workspace(request)
        return WorkspaceResponse(workspace=workspace.to_dict())
    except Exception as e:
        logger.error(f"Failed to create workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.get("/workspaces", response_model=WorkspaceListResponse)
async def list_workspaces(
    status: Optional[str] = Query(None, description="Filter by status"),
    runtime: Optional[str] = Query(None, description="Filter by runtime"),
    auth: bool = Depends(workbench_auth),
):
    """List all workspaces with optional filtering."""
    try:
        service = get_service()

        status_enum = None
        if status:
            try:
                status_enum = WorkspaceStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        runtime_enum = None
        if runtime:
            try:
                runtime_enum = RuntimeType(runtime)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid runtime: {runtime}")

        workspaces = await service.list_workspaces(
            status=status_enum,
            runtime=runtime_enum,
        )
        return WorkspaceListResponse(
            workspaces=[w.to_dict() for w in workspaces],
            count=len(workspaces),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list workspaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    auth: bool = Depends(workbench_auth),
):
    """Get a workspace by ID."""
    try:
        service = get_service()
        workspace = await service.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")
        return WorkspaceResponse(workspace=workspace.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.delete("/workspaces/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    auth: bool = Depends(workbench_auth),
):
    """Delete a workspace."""
    try:
        service = get_service()
        success = await service.delete_workspace(workspace_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")
        return {"success": True, "workspace_id": workspace_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Workspace Lifecycle Endpoints
# =============================================================================


@workbench_router.post("/workspaces/{workspace_id}/start", response_model=WorkspaceResponse)
async def start_workspace(
    workspace_id: str,
    auth: bool = Depends(workbench_auth),
):
    """Start a workspace's runtime container."""
    try:
        service = get_service()
        workspace = await service.start_workspace(workspace_id)
        return WorkspaceResponse(workspace=workspace.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.post("/workspaces/{workspace_id}/stop", response_model=WorkspaceResponse)
async def stop_workspace(
    workspace_id: str,
    auth: bool = Depends(workbench_auth),
):
    """Stop a workspace's runtime container."""
    try:
        service = get_service()
        workspace = await service.stop_workspace(workspace_id)
        return WorkspaceResponse(workspace=workspace.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to stop workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Command Execution Endpoints
# =============================================================================


@workbench_router.post("/workspaces/{workspace_id}/run", response_model=RunResponse)
async def run_command(
    workspace_id: str,
    cmd: List[str] = Query(..., description="Command to run"),
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    timeout: int = 300,
    auth: bool = Depends(workbench_auth),
):
    """
    Run a command in a workspace.

    This is asynchronous - returns immediately with a run_id.
    Use GET /runs/{run_id} to check status and get results.
    """
    try:
        service = get_service()
        request = RunRequest(
            workspace_id=workspace_id,
            cmd=cmd,
            env=env,
            cwd=cwd,
            timeout=timeout,
        )
        result = await service.run_command(request)
        return RunResponse(run=result.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to run command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.post("/workspaces/{workspace_id}/run/sync", response_model=RunResponse)
async def run_command_sync(
    workspace_id: str,
    cmd: List[str] = Query(..., description="Command to run"),
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    timeout: int = 300,
    auth: bool = Depends(workbench_auth),
):
    """
    Run a command and wait for completion.

    Returns the full result including stdout, stderr, and exit code.
    """
    try:
        service = get_service()
        request = RunRequest(
            workspace_id=workspace_id,
            cmd=cmd,
            env=env,
            cwd=cwd,
            timeout=timeout,
        )
        result = await service.run_command_sync(request)
        return RunResponse(run=result.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to run command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    auth: bool = Depends(workbench_auth),
):
    """Get the result of a command execution."""
    try:
        service = get_service()
        result = await service.get_run_result(run_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        return RunResponse(run=result.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.get("/runs/{run_id}/logs", response_model=LogsResponse)
async def get_run_logs(
    run_id: str,
    auth: bool = Depends(workbench_auth),
):
    """Get logs from a command execution."""
    try:
        service = get_service()
        logs = await service.get_run_logs(run_id)
        return LogsResponse(run_id=run_id, logs=logs)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Port Management Endpoints
# =============================================================================


@workbench_router.post("/workspaces/{workspace_id}/ports")
async def expose_port(
    workspace_id: str,
    port: int = Query(..., ge=1, le=65535, description="Port to expose"),
    proto: str = Query("http", description="Protocol (http or tcp)"),
    label: Optional[str] = Query(None, description="Optional label"),
    auth: bool = Depends(workbench_auth),
):
    """Expose a port from a workspace."""
    try:
        from ag3ntwerk.modules.workbench.schemas import PortProtocol

        service = get_service()
        request = PortExposeRequest(
            workspace_id=workspace_id,
            port=port,
            proto=PortProtocol(proto),
            label=label,
        )
        result = await service.expose_port(request)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to expose port: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.get("/workspaces/{workspace_id}/ports", response_model=PortsResponse)
async def list_ports(
    workspace_id: str,
    auth: bool = Depends(workbench_auth),
):
    """List all exposed ports for a workspace."""
    try:
        service = get_service()
        ports = await service.list_exposed_ports(workspace_id)
        return PortsResponse(
            ports=[p.to_dict() for p in ports],
            count=len(ports),
        )
    except Exception as e:
        logger.error(f"Failed to list ports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# File Operations Endpoints
# =============================================================================


@workbench_router.post("/workspaces/{workspace_id}/files")
async def write_files(
    workspace_id: str,
    files: Dict[str, str],
    auth: bool = Depends(workbench_auth),
):
    """Write files to a workspace."""
    try:
        service = get_service()
        request = FileWriteRequest(
            workspace_id=workspace_id,
            files=files,
        )
        results = await service.write_files(request)
        return {"success": True, "results": results}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to write files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.get("/workspaces/{workspace_id}/files", response_model=FileListResponse)
async def list_files(
    workspace_id: str,
    pattern: str = Query("**/*", description="Glob pattern"),
    auth: bool = Depends(workbench_auth),
):
    """List files in a workspace."""
    try:
        service = get_service()
        files = await service.list_files(workspace_id, pattern)
        return FileListResponse(files=files, count=len(files))
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.post("/workspaces/{workspace_id}/files/read", response_model=FilesResponse)
async def read_files(
    workspace_id: str,
    paths: List[str],
    auth: bool = Depends(workbench_auth),
):
    """Read files from a workspace."""
    try:
        service = get_service()
        request = FileReadRequest(
            workspace_id=workspace_id,
            paths=paths,
        )
        contents = await service.read_files(request)
        return FilesResponse(
            files=[
                {
                    "path": c.path,
                    "content": c.content,
                    "exists": c.exists,
                    "error": c.error,
                }
                for c in contents
            ]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to read files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# IDE Integration Endpoints
# =============================================================================


@workbench_router.get("/workspaces/{workspace_id}/ide", response_model=IDEResponse)
async def get_ide_url(
    workspace_id: str,
    auth: bool = Depends(workbench_auth),
):
    """Get the IDE URL for a workspace."""
    try:
        service = get_service()
        ide_info = await service.get_ide_url(workspace_id)
        return IDEResponse(
            workspace_id=ide_info.workspace_id,
            ide_url=ide_info.ide_url,
            mode=ide_info.mode.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get IDE URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.post("/workspaces/{workspace_id}/ide/start", response_model=IDEResponse)
async def start_ide(
    workspace_id: str,
    request: Optional[IDEStartRequest] = None,
    auth: bool = Depends(workbench_auth),
):
    """
    Start the browser IDE (code-server) for a workspace.

    Creates and starts a code-server container that provides a browser-based
    VS Code experience for editing workspace files.

    Returns the URL and auth token to access the IDE.
    """
    try:
        service = get_service()
        password = request.password if request else None
        ide_info = await service.start_ide(workspace_id, password)
        return IDEResponse(
            workspace_id=ide_info.workspace_id,
            ide_url=ide_info.ide_url,
            mode=ide_info.mode.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start IDE: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.post("/workspaces/{workspace_id}/ide/stop")
async def stop_ide(
    workspace_id: str,
    auth: bool = Depends(workbench_auth),
):
    """
    Stop the browser IDE for a workspace.

    Stops and removes the code-server container, freeing resources.
    """
    try:
        service = get_service()
        success = await service.stop_ide(workspace_id)
        return {"success": success, "workspace_id": workspace_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to stop IDE: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.get("/workspaces/{workspace_id}/ide/status", response_model=IDEStatusResponse)
async def get_ide_status(
    workspace_id: str,
    auth: bool = Depends(workbench_auth),
):
    """
    Get the status of the browser IDE for a workspace.

    Returns detailed information including whether it's running,
    resource usage, and access URL.
    """
    try:
        service = get_service()
        status = await service.get_ide_status(workspace_id)
        return IDEStatusResponse(
            workspace_id=status.workspace_id,
            running=status.running,
            container_id=status.container_id,
            ide_url=status.ide_url,
            auth_token=status.auth_token,
            started_at=status.started_at.isoformat() if status.started_at else None,
            cpu_usage=status.cpu_usage,
            memory_usage=status.memory_usage,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get IDE status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# One-Click Deployment Endpoints
# =============================================================================


@workbench_router.post("/workspaces/{workspace_id}/deploy/oneclick")
async def oneclick_deploy(
    workspace_id: str,
    request: Optional[OneClickDeployRequest] = None,
    auth: bool = Depends(workbench_auth),
):
    """
    One-click deployment: detect framework, generate configs, and deploy.

    Automatically:
    1. Detects the framework (Next.js, FastAPI, etc.)
    2. Generates missing configs (Dockerfile, vercel.json)
    3. Selects the best deployment target
    4. Deploys to production

    This is the simplest way to go from code to deployed application.
    """
    try:
        from ag3ntwerk.modules.workbench.deployers.oneclick import OneClickDeployer

        service = get_service()
        deployer = OneClickDeployer(service)

        target = request.target if request else "auto"
        generate_configs = request.generate_configs if request else True
        environment = request.environment if request else None

        result = await deployer.deploy(
            workspace_id=workspace_id,
            target=target,
            generate_configs=generate_configs,
            environment=environment,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"One-click deploy failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.get(
    "/workspaces/{workspace_id}/deploy/preview", response_model=DeployPreviewResponse
)
async def preview_deploy(
    workspace_id: str,
    auth: bool = Depends(workbench_auth),
):
    """
    Preview what one-click deployment would do.

    Shows the detected framework, what configs would be generated,
    and the recommended deployment target - without actually deploying.

    Use this to understand what will happen before running oneclick_deploy.
    """
    try:
        from ag3ntwerk.modules.workbench.deployers.oneclick import OneClickDeployer

        service = get_service()
        deployer = OneClickDeployer(service)

        preview = await deployer.preview(workspace_id)

        return DeployPreviewResponse(
            workspace_id=preview.workspace_id,
            detected_framework=preview.framework_info.framework.value,
            framework_version=preview.framework_info.version,
            build_command=preview.framework_info.build_command,
            start_command=preview.framework_info.start_command,
            recommended_target=preview.recommended_target.value,
            configs_needed=preview.configs_needed,
            configs_existing=preview.configs_existing,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Deploy preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Agent Report Endpoints
# =============================================================================


@workbench_router.get("/report/{agent_code}")
async def get_agent_report(
    agent_code: str,
    auth: bool = Depends(workbench_auth),
):
    """Get agent-tailored workbench report."""
    try:
        service = get_service()
        report = service.get_agent_report(agent_code.upper())
        return report
    except Exception as e:
        logger.error(f"Failed to get report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Pipeline Orchestration Endpoints
# =============================================================================


_pipeline: Optional["WorkbenchPipeline"] = None


def get_pipeline() -> "WorkbenchPipeline":
    """Get or create the workbench pipeline."""
    global _pipeline
    if _pipeline is None:
        from ag3ntwerk.modules.workbench.pipeline import WorkbenchPipeline

        _pipeline = WorkbenchPipeline(get_service())
    return _pipeline


@workbench_router.post("/pipeline/evaluate")
async def run_evaluation_pipeline(
    workspace_id: str,
    review_scope: str = Query("full", description="Review scope: full, diff, or paths"),
    focus_areas: Optional[List[str]] = Query(None, description="Focus areas"),
    security_standards: Optional[List[str]] = Query(None, description="Security standards"),
    auth: bool = Depends(workbench_auth),
):
    """
    Run code evaluation only (no deployment).

    Evaluates code quality and security without building or deploying.
    Returns findings from Forge specialists.
    """
    try:
        from ag3ntwerk.modules.workbench.pipeline_schemas import EvaluationOptions

        pipeline = get_pipeline()
        options = EvaluationOptions(
            review_scope=review_scope,
            focus_areas=focus_areas or [],
            security_standards=security_standards or ["OWASP"],
        )
        result = await pipeline.run_evaluation(workspace_id, options)
        return {"pipeline": result.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Evaluation pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.post("/pipeline/full")
async def run_full_pipeline(
    workspace_id: str,
    deployment_target: str = Query(
        "local", description="Deployment target: vercel, docker_registry, local"
    ),
    skip_stages: Optional[List[str]] = Query(None, description="Stages to skip"),
    auto_fix: bool = Query(True, description="Auto-fix issues found"),
    coverage_target: int = Query(80, ge=0, le=100, description="Test coverage target"),
    auth: bool = Depends(workbench_auth),
):
    """
    Run full pipeline: Evaluate → Correct → Secure → Test → Build → Deploy.

    This is the main code-to-production pipeline that orchestrates specialists
    from Forge, Citadel, and Foundry.
    """
    try:
        from ag3ntwerk.modules.workbench.pipeline_schemas import DeploymentTarget, PipelineOptions

        pipeline = get_pipeline()
        options = PipelineOptions(
            deployment_target=DeploymentTarget(deployment_target),
            skip_stages=skip_stages or [],
            auto_fix=auto_fix,
            coverage_target=coverage_target,
        )
        result = await pipeline.run_full_pipeline(workspace_id, options)
        return {"pipeline": result.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Full pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.post("/pipeline/with-database")
async def run_pipeline_with_database(
    workspace_id: str,
    deployment_target: str = Query("local", description="Deployment target"),
    database_type: str = Query("postgres", description="Database type"),
    skip_stages: Optional[List[str]] = Query(None, description="Stages to skip"),
    auth: bool = Depends(workbench_auth),
):
    """
    Run full pipeline + database provisioning.

    Includes schema design, provisioning, migrations, and seeding
    via Index and Forge specialists.
    """
    try:
        from ag3ntwerk.modules.workbench.pipeline_schemas import (
            DatabaseOptions,
            DatabaseType,
            DeploymentTarget,
            PipelineOptions,
        )

        pipeline = get_pipeline()
        options = PipelineOptions(
            deployment_target=DeploymentTarget(deployment_target),
            skip_stages=skip_stages or [],
        )
        db_options = DatabaseOptions(
            database_type=DatabaseType(database_type),
        )
        result = await pipeline.run_with_database(workspace_id, options, db_options)
        return {"pipeline": result.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Pipeline with database failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.post("/pipeline/with-secrets")
async def run_pipeline_with_secrets(
    workspace_id: str,
    deployment_target: str = Query("local", description="Deployment target"),
    secret_types: Optional[List[str]] = Query(None, description="Types of secrets to generate"),
    scan_for_exposed: bool = Query(True, description="Scan for exposed secrets"),
    auth: bool = Depends(workbench_auth),
):
    """
    Run full pipeline + secrets management.

    Includes secrets audit, generation, encryption, and environment configuration
    via Citadel and Forge specialists.
    """
    try:
        from ag3ntwerk.modules.workbench.pipeline_schemas import (
            DeploymentTarget,
            PipelineOptions,
            SecretsOptions,
        )

        pipeline = get_pipeline()
        options = PipelineOptions(
            deployment_target=DeploymentTarget(deployment_target),
            generate_secrets=True,
        )
        secrets_options = SecretsOptions(
            secret_types=secret_types or ["api_key", "db_password"],
            scan_for_exposed=scan_for_exposed,
        )
        result = await pipeline.run_with_secrets(workspace_id, options, secrets_options)
        return {"pipeline": result.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Pipeline with secrets failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.post("/pipeline/complete")
async def run_complete_pipeline(
    workspace_id: str,
    deployment_target: str = Query("local", description="Deployment target"),
    database_type: Optional[str] = Query(None, description="Database type (optional)"),
    generate_secrets: bool = Query(False, description="Generate production secrets"),
    auth: bool = Depends(workbench_auth),
):
    """
    Run complete pipeline: Code + Database + Secrets + Deploy.

    This is the comprehensive production-ready deployment pipeline
    that orchestrates all workflows together.
    """
    try:
        from ag3ntwerk.modules.workbench.pipeline_schemas import (
            DatabaseOptions,
            DatabaseType,
            DeploymentTarget,
            PipelineOptions,
            SecretsOptions,
        )

        pipeline = get_pipeline()
        options = PipelineOptions(
            deployment_target=DeploymentTarget(deployment_target),
            generate_secrets=generate_secrets,
        )

        db_options = None
        if database_type:
            db_options = DatabaseOptions(database_type=DatabaseType(database_type))

        secrets_options = None
        if generate_secrets:
            secrets_options = SecretsOptions()

        result = await pipeline.run_complete(
            workspace_id,
            options,
            db_options,
            secrets_options,
        )
        return {"pipeline": result.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Complete pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.get("/pipeline/{pipeline_id}/status")
async def get_pipeline_status(
    pipeline_id: str,
    auth: bool = Depends(workbench_auth),
):
    """Get the status of a pipeline execution."""
    try:
        pipeline = get_pipeline()
        result = await pipeline.get_pipeline_status(pipeline_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")

        # Calculate progress
        total_stages = len(result.stages)
        completed_stages = sum(1 for s in result.stages if s.status in ["completed", "skipped"])
        progress = (completed_stages / total_stages * 100) if total_stages > 0 else 0

        current_stage = None
        for s in result.stages:
            if s.status == "running":
                current_stage = s.name
                break

        return {
            "pipeline_id": pipeline_id,
            "status": result.status,
            "progress": progress,
            "current_stage": current_stage,
            "stages_completed": completed_stages,
            "stages_total": total_stages,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.get("/pipeline/{pipeline_id}/logs")
async def get_pipeline_logs(
    pipeline_id: str,
    stage: Optional[str] = Query(None, description="Specific stage to get logs for"),
    auth: bool = Depends(workbench_auth),
):
    """Get logs from a pipeline execution."""
    try:
        pipeline = get_pipeline()
        logs = await pipeline.get_pipeline_logs(pipeline_id, stage)
        return {
            "pipeline_id": pipeline_id,
            "stage": stage,
            "logs": logs,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get pipeline logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.post("/pipeline/{pipeline_id}/cancel")
async def cancel_pipeline(
    pipeline_id: str,
    auth: bool = Depends(workbench_auth),
):
    """Cancel a running pipeline."""
    try:
        pipeline = get_pipeline()
        success = await pipeline.cancel_pipeline(pipeline_id)
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Pipeline not found or already completed",
            )
        return {"success": True, "pipeline_id": pipeline_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Deployment Target Endpoints
# =============================================================================


@workbench_router.post("/deploy/vercel")
async def deploy_to_vercel(
    workspace_id: str,
    production: bool = Query(False, description="Deploy to production"),
    vercel_token: Optional[str] = Query(None, description="Vercel token (or use env var)"),
    auth: bool = Depends(workbench_auth),
):
    """
    Deploy workspace to Vercel.

    Uses Vercel CLI in the workspace container to deploy.
    """
    try:
        from ag3ntwerk.modules.workbench.deployers import get_deployer
        from ag3ntwerk.modules.workbench.pipeline_schemas import DeploymentTarget, PipelineOptions

        deployer = get_deployer(DeploymentTarget.VERCEL)
        service = get_service()

        options = PipelineOptions(
            deployment_target=DeploymentTarget.VERCEL,
            environment_config={
                "VERCEL_TOKEN": vercel_token or "",
                "production": str(production).lower(),
            },
        )

        result = await deployer.deploy(workspace_id, service, options)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Vercel deployment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@workbench_router.post("/deploy/docker")
async def deploy_to_docker_registry(
    workspace_id: str,
    registry: str = Query("docker.io", description="Docker registry URL"),
    image_name: Optional[str] = Query(None, description="Image name"),
    tag: str = Query("latest", description="Image tag"),
    auth: bool = Depends(workbench_auth),
):
    """
    Build and push to Docker registry.

    Builds a container image from the workspace and pushes to the registry.
    """
    try:
        from ag3ntwerk.modules.workbench.deployers import get_deployer
        from ag3ntwerk.modules.workbench.pipeline_schemas import DeploymentTarget, PipelineOptions

        deployer = get_deployer(DeploymentTarget.DOCKER_REGISTRY)
        service = get_service()

        options = PipelineOptions(
            deployment_target=DeploymentTarget.DOCKER_REGISTRY,
            environment_config={
                "DOCKER_REGISTRY": registry,
                "DOCKER_IMAGE_NAME": image_name or f"ag3ntwerk-{workspace_id}",
                "DOCKER_TAG": tag,
            },
        )

        result = await deployer.deploy(workspace_id, service, options)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Docker deployment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
