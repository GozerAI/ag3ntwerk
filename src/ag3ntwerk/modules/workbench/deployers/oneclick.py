"""
One-Click Deployer - Automated deployment orchestration.

Combines framework detection, config generation, and deployment
into a single automated workflow.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ag3ntwerk.modules.workbench.detection.framework_detector import (
    FrameworkDetector,
    FrameworkInfo,
    FrameworkType,
)
from ag3ntwerk.modules.workbench.detection.config_generator import (
    ConfigGenerator,
    GeneratedConfigs,
)
from ag3ntwerk.modules.workbench.pipeline_schemas import (
    DeploymentTarget,
    DeployResult,
    PipelineOptions,
)
from ag3ntwerk.modules.workbench.deployers import get_deployer

if TYPE_CHECKING:
    from ag3ntwerk.modules.workbench.service import WorkbenchService

logger = logging.getLogger(__name__)


@dataclass
class OneClickResult:
    """Result of one-click deployment."""

    deployment_id: str
    status: str  # "success", "failed", "pending"

    # Detection phase
    detected_framework: str = "unknown"
    build_command: Optional[str] = None
    start_command: Optional[str] = None
    install_command: Optional[str] = None
    port: int = 3000

    # Config phase
    configs_generated: List[str] = field(default_factory=list)

    # Deploy phase
    deployment_target: Optional[str] = None
    deployment_url: Optional[str] = None
    logs_url: Optional[str] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Errors
    error: Optional[str] = None
    error_phase: Optional[str] = None  # "detection", "config", "deploy"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "deployment_id": self.deployment_id,
            "status": self.status,
            "detected_framework": self.detected_framework,
            "build_command": self.build_command,
            "start_command": self.start_command,
            "install_command": self.install_command,
            "port": self.port,
            "configs_generated": self.configs_generated,
            "deployment_target": self.deployment_target,
            "deployment_url": self.deployment_url,
            "logs_url": self.logs_url,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "error_phase": self.error_phase,
        }


@dataclass
class DeployPreview:
    """Preview of what one-click deploy would do."""

    workspace_id: str
    detected_framework: str
    framework_version: Optional[str]
    build_command: Optional[str]
    start_command: Optional[str]
    install_command: Optional[str]
    port: int
    recommended_target: str
    configs_to_generate: Dict[str, bool]
    existing_configs: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "workspace_id": self.workspace_id,
            "detected_framework": self.detected_framework,
            "framework_version": self.framework_version,
            "build_command": self.build_command,
            "start_command": self.start_command,
            "install_command": self.install_command,
            "port": self.port,
            "recommended_target": self.recommended_target,
            "configs_to_generate": self.configs_to_generate,
            "existing_configs": self.existing_configs,
        }


class OneClickDeployer:
    """
    One-click deployment orchestrator.

    Combines:
    1. Framework detection
    2. Config generation (Dockerfile, vercel.json, .env)
    3. Target selection (auto or specified)
    4. Deployment execution

    Example:
        ```python
        from ag3ntwerk.modules.workbench.deployers.oneclick import OneClickDeployer

        deployer = OneClickDeployer(workbench_service)

        # Preview what would happen
        preview = await deployer.preview("ws-123")
        print(f"Detected: {preview.detected_framework}")

        # Execute deployment
        result = await deployer.deploy(
            workspace_id="ws-123",
            target="auto",  # Auto-select best target
        )
        print(f"Deployed to: {result.deployment_url}")
        ```
    """

    def __init__(self, workbench: "WorkbenchService"):
        """
        Initialize the one-click deployer.

        Args:
            workbench: WorkbenchService instance
        """
        self._workbench = workbench

    async def deploy(
        self,
        workspace_id: str,
        target: str = "auto",
        generate_configs: bool = True,
        environment: Optional[Dict[str, str]] = None,
    ) -> OneClickResult:
        """
        Execute one-click deployment.

        Args:
            workspace_id: Workspace to deploy
            target: "auto", "vercel", "docker_registry", "local"
            generate_configs: Auto-generate missing configs
            environment: Environment variables

        Returns:
            OneClickResult with deployment details
        """
        deployment_id = f"oneclick-{uuid.uuid4().hex[:8]}"
        started_at = datetime.now(timezone.utc)

        result = OneClickResult(
            deployment_id=deployment_id,
            status="pending",
            started_at=started_at,
        )

        try:
            # Phase 1: Get workspace
            workspace = await self._workbench.get_workspace(workspace_id)
            if not workspace:
                raise ValueError(f"Workspace not found: {workspace_id}")

            logger.info(f"OneClick deploy starting for workspace {workspace_id}")

            # Phase 2: Framework detection
            try:
                detector = FrameworkDetector(workspace.path)
                framework_info = await detector.detect()

                result.detected_framework = framework_info.framework.value
                result.build_command = framework_info.build_command
                result.start_command = framework_info.start_command
                result.install_command = framework_info.install_command
                result.port = framework_info.port

                logger.info(f"Detected framework: {framework_info.framework.value}")

            except Exception as e:
                result.error = f"Framework detection failed: {e}"
                result.error_phase = "detection"
                result.status = "failed"
                logger.error(result.error)
                return self._finalize_result(result)

            # Phase 3: Config generation
            if generate_configs:
                try:
                    generator = ConfigGenerator(workspace.path, framework_info)
                    configs = await generator.generate_all(write_files=True)
                    result.configs_generated = configs.files_written

                    logger.info(f"Generated configs: {configs.files_written}")

                except Exception as e:
                    result.error = f"Config generation failed: {e}"
                    result.error_phase = "config"
                    result.status = "failed"
                    logger.error(result.error)
                    return self._finalize_result(result)

            # Phase 4: Select deployment target
            deployment_target = self._select_target(target, framework_info)
            result.deployment_target = deployment_target.value
            logger.info(f"Selected deployment target: {deployment_target.value}")

            # Phase 5: Execute deployment
            try:
                deployer = get_deployer(deployment_target)

                # Build environment config
                env_config = environment or {}
                if framework_info.start_command:
                    env_config["START_COMMAND"] = framework_info.start_command
                if framework_info.port:
                    env_config["PORT"] = str(framework_info.port)
                env_config["FRAMEWORK"] = framework_info.framework.value

                options = PipelineOptions(
                    deployment_target=deployment_target,
                    environment_config=env_config,
                )

                deploy_result = await deployer.deploy(
                    workspace_id=workspace_id,
                    workbench=self._workbench,
                    options=options,
                )

                result.deployment_url = deploy_result.url
                result.logs_url = deploy_result.logs_url
                result.status = "success" if deploy_result.url else "failed"

                if deploy_result.error:
                    result.error = deploy_result.error
                    result.error_phase = "deploy"
                    result.status = "failed"

                logger.info(f"Deployment completed: {deploy_result.url}")

            except Exception as e:
                result.error = f"Deployment failed: {e}"
                result.error_phase = "deploy"
                result.status = "failed"
                logger.error(result.error)

        except Exception as e:
            logger.error(f"OneClick deploy failed: {e}")
            result.status = "failed"
            result.error = str(e)

        return self._finalize_result(result)

    async def preview(self, workspace_id: str) -> DeployPreview:
        """
        Preview what one-click deploy would do without executing.

        Args:
            workspace_id: Workspace ID

        Returns:
            DeployPreview with planned actions
        """
        workspace = await self._workbench.get_workspace(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {workspace_id}")

        # Detect framework
        detector = FrameworkDetector(workspace.path)
        framework_info = await detector.detect()

        # Determine target
        target = self._select_target("auto", framework_info)

        # Check what configs would be generated
        generator = ConfigGenerator(workspace.path, framework_info)
        configs = await generator.generate_all(write_files=False)

        # Check for existing configs
        from pathlib import Path

        workspace_path = Path(workspace.path)
        existing_configs = []
        for config_file in ["Dockerfile", "vercel.json", ".env", "docker-compose.yml"]:
            if (workspace_path / config_file).exists():
                existing_configs.append(config_file)

        return DeployPreview(
            workspace_id=workspace_id,
            detected_framework=framework_info.framework.value,
            framework_version=framework_info.version,
            build_command=framework_info.build_command,
            start_command=framework_info.start_command,
            install_command=framework_info.install_command,
            port=framework_info.port,
            recommended_target=target.value,
            configs_to_generate={
                "Dockerfile": configs.dockerfile is not None,
                "dockerignore": configs.dockerignore is not None,
                "vercel_json": configs.vercel_json is not None,
                "env_file": configs.env_file is not None,
            },
            existing_configs=existing_configs,
        )

    def _select_target(
        self,
        requested: str,
        framework_info: FrameworkInfo,
    ) -> DeploymentTarget:
        """
        Auto-select best deployment target based on framework.

        Args:
            requested: Requested target ("auto" or specific target)
            framework_info: Detected framework info

        Returns:
            Selected DeploymentTarget
        """
        if requested != "auto":
            try:
                return DeploymentTarget(requested)
            except ValueError:
                logger.warning(f"Unknown target '{requested}', falling back to auto")

        # Auto-selection logic based on framework
        # Frontend frameworks → Vercel (optimized for static/SSR)
        vercel_frameworks = [
            FrameworkType.NEXTJS,
            FrameworkType.REACT,
            FrameworkType.VUE,
            FrameworkType.NUXT,
            FrameworkType.SVELTE,
            FrameworkType.STATIC_SITE,
        ]

        if framework_info.framework in vercel_frameworks:
            return DeploymentTarget.VERCEL

        # Backend frameworks → Docker (more control, any runtime)
        docker_frameworks = [
            FrameworkType.FASTAPI,
            FrameworkType.FLASK,
            FrameworkType.DJANGO,
            FrameworkType.EXPRESS,
            FrameworkType.GIN,
            FrameworkType.ECHO,
            FrameworkType.FIBER,
            FrameworkType.ACTIX,
            FrameworkType.ROCKET,
            FrameworkType.AXUM,
        ]

        if framework_info.framework in docker_frameworks:
            return DeploymentTarget.DOCKER_REGISTRY

        # Simple scripts → Local preview
        if framework_info.framework in [
            FrameworkType.PYTHON_SCRIPT,
            FrameworkType.NODEJS,
            FrameworkType.GO_MODULE,
            FrameworkType.RUST_BIN,
        ]:
            return DeploymentTarget.LOCAL_PREVIEW

        # Default fallback
        return DeploymentTarget.LOCAL_PREVIEW

    def _finalize_result(self, result: OneClickResult) -> OneClickResult:
        """Finalize result with timing information."""
        result.completed_at = datetime.now(timezone.utc)
        if result.started_at:
            delta = result.completed_at - result.started_at
            result.duration_seconds = delta.total_seconds()
        return result
