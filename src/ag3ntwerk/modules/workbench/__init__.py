"""
ag3ntwerk Workbench Module - Local Development Environment.

Provides a secure, local-first browser IDE + sandboxed runtimes + terminal + previews,
enabling agent-assisted code generation, execution, testing, and promotion into
first-class modules/plugins.

Primary owners: Forge, Foundry
Secondary owners: Nexus, Blueprint

Features:
- Workspace lifecycle management
- Docker-based sandboxed runtimes
- Command execution with logs
- Port exposure for previews
- Web IDE integration (code-server) with container management
- Framework detection and config generation
- One-click deployment (auto-detect → generate configs → deploy)
- Pipeline orchestration (Nexus-orchestrated code-to-production workflows)
- Multi-target deployment (Vercel, Docker Registry, Local)
- Automation hooks (TaskQueue, Triggers, Scheduler)

Example IDE Usage:
    ```python
    from ag3ntwerk.modules.workbench import WorkbenchService

    service = WorkbenchService()
    await service.initialize()

    # Start browser IDE for a workspace
    ide_info = await service.start_ide("ws-123")
    print(f"Open IDE at: {ide_info.ide_url}")

    # Check IDE status
    status = await service.get_ide_status("ws-123")
    print(f"Running: {status.running}, CPU: {status.cpu_usage}%")

    # Stop when done
    await service.stop_ide("ws-123")
    ```

Example One-Click Deploy:
    ```python
    from ag3ntwerk.modules.workbench import WorkbenchService
    from ag3ntwerk.modules.workbench.deployers.oneclick import OneClickDeployer

    service = WorkbenchService()
    deployer = OneClickDeployer(service)

    # Preview what would happen
    preview = await deployer.preview("ws-123")
    print(f"Detected: {preview.framework_info.framework}")
    print(f"Will generate: {preview.configs_needed}")

    # Deploy with one click
    result = await deployer.deploy("ws-123")
    print(f"Deployed to: {result.deployment_url}")
    ```

Example Pipeline Usage:
    ```python
    from ag3ntwerk.modules.workbench import (
        WorkbenchService,
        WorkbenchPipeline,
        PipelineOptions,
        DeploymentTarget,
    )

    service = WorkbenchService()
    pipeline = WorkbenchPipeline(service)

    # Run full code-to-production pipeline
    result = await pipeline.run_full_pipeline(
        workspace_id="ws-123",
        options=PipelineOptions(
            deployment_target=DeploymentTarget.VERCEL,
        ),
    )
    ```
"""

from ag3ntwerk.modules.workbench.service import WorkbenchService
from ag3ntwerk.modules.workbench.schemas import (
    Workspace,
    WorkspaceCreate,
    WorkspaceStatus,
    RuntimeType,
    RunRequest,
    RunResult,
    RunStatus,
    PortExposeRequest,
    PortExposeResult,
)
from ag3ntwerk.modules.workbench.pipeline import WorkbenchPipeline, get_workbench_pipeline
from ag3ntwerk.modules.workbench.pipeline_schemas import (
    DeploymentTarget,
    DatabaseType,
    PipelineStatus,
    StageStatus,
    PipelineOptions,
    EvaluationOptions,
    VercelOptions,
    DockerOptions,
    DatabaseOptions,
    SecretsOptions,
    StageResult,
    PipelineResult,
    DeployResult,
)
from ag3ntwerk.modules.workbench.deployers import (
    BaseDeployer,
    VercelDeployer,
    DockerRegistryDeployer,
    LocalDeployer,
    get_deployer,
)
from ag3ntwerk.modules.workbench.ide.manager import IDEContainerManager, IDEStatus
from ag3ntwerk.modules.workbench.detection import (
    FrameworkDetector,
    FrameworkInfo,
    FrameworkType,
    ConfigGenerator,
    GeneratedConfigs,
    detect_framework,
)
from ag3ntwerk.modules.workbench.deployers.oneclick import OneClickDeployer, OneClickResult
from ag3ntwerk.modules.workbench.automation import (
    bootstrap_workbench_automation,
    register_workbench_handlers,
    register_workbench_triggers,
    register_workbench_schedules,
)

__all__ = [
    # Service
    "WorkbenchService",
    # Schemas
    "Workspace",
    "WorkspaceCreate",
    "WorkspaceStatus",
    "RuntimeType",
    "RunRequest",
    "RunResult",
    "RunStatus",
    "PortExposeRequest",
    "PortExposeResult",
    # IDE
    "IDEContainerManager",
    "IDEStatus",
    # Detection
    "FrameworkDetector",
    "FrameworkInfo",
    "FrameworkType",
    "ConfigGenerator",
    "GeneratedConfigs",
    "detect_framework",
    # One-Click Deploy
    "OneClickDeployer",
    "OneClickResult",
    # Pipeline
    "WorkbenchPipeline",
    "get_workbench_pipeline",
    # Pipeline Schemas
    "DeploymentTarget",
    "DatabaseType",
    "PipelineStatus",
    "StageStatus",
    "PipelineOptions",
    "EvaluationOptions",
    "VercelOptions",
    "DockerOptions",
    "DatabaseOptions",
    "SecretsOptions",
    "StageResult",
    "PipelineResult",
    "DeployResult",
    # Deployers
    "BaseDeployer",
    "VercelDeployer",
    "DockerRegistryDeployer",
    "LocalDeployer",
    "get_deployer",
    # Automation
    "bootstrap_workbench_automation",
    "register_workbench_handlers",
    "register_workbench_triggers",
    "register_workbench_schedules",
]
