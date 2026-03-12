"""
Local Preview Deployer.

Exposes workspace ports for local preview access.
Uses existing Workbench port exposure functionality.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ag3ntwerk.modules.workbench.deployers.base import BaseDeployer
from ag3ntwerk.modules.workbench.pipeline_schemas import DeployResult, DeploymentTarget

if TYPE_CHECKING:
    from ag3ntwerk.modules.workbench.pipeline_schemas import PipelineOptions
    from ag3ntwerk.modules.workbench.service import WorkbenchService

logger = logging.getLogger(__name__)


class LocalDeployer(BaseDeployer):
    """
    Deployer for local preview.

    Exposes the application port from the workspace container
    for local development access. Does not actually "deploy" anywhere
    but provides a preview URL.
    """

    @property
    def target(self) -> DeploymentTarget:
        return DeploymentTarget.LOCAL_PREVIEW

    @property
    def name(self) -> str:
        return "Local Preview"

    async def deploy(
        self,
        workspace_id: str,
        workbench: "WorkbenchService",
        options: "PipelineOptions",
    ) -> DeployResult:
        """
        Expose workspace for local preview.

        Strategy:
        1. Start the application in the workspace container
        2. Expose the application port
        3. Return the local preview URL

        Args:
            workspace_id: Workspace ID
            workbench: WorkbenchService instance
            options: Pipeline options

        Returns:
            DeployResult with local preview URL
        """
        deployment_id = f"local-{uuid.uuid4().hex[:8]}"
        started_at = datetime.now(timezone.utc)

        try:
            # Validate workspace
            if not await self.validate_workspace(workspace_id, workbench):
                return self._create_error_result(
                    deployment_id,
                    "Workspace not found or empty",
                    started_at,
                )

            workspace = await workbench.get_workspace(workspace_id)

            # Ensure workspace is running
            if workspace.status.value != "running":
                workspace = await workbench.start_workspace(workspace_id)

            # Determine the port to expose
            app_port = self._detect_app_port(options.environment_config)

            # Start the application if a start command is provided
            start_cmd = options.environment_config.get("START_COMMAND")
            if start_cmd:
                from ag3ntwerk.modules.workbench.schemas import RunRequest

                # Run in background (don't wait)
                run_request = RunRequest(
                    workspace_id=workspace_id,
                    cmd=start_cmd.split(),
                    timeout=10,  # Just start it, don't wait for completion
                )

                # Start the process (async, don't wait)
                await workbench.run_command(run_request)

                # Give it a moment to start
                import asyncio

                await asyncio.sleep(2)

            # Expose the port
            from ag3ntwerk.modules.workbench.schemas import PortExposeRequest, PortProtocol

            expose_request = PortExposeRequest(
                workspace_id=workspace_id,
                port=app_port,
                proto=PortProtocol.HTTP,
                label="preview",
            )

            port_result = await workbench.expose_port(expose_request)

            preview_url = f"http://{port_result.host}:{port_result.host_port}"

            logger.info(f"Local preview available at: {preview_url}")

            return self._create_success_result(
                deployment_id=deployment_id,
                url=preview_url,
                started_at=started_at,
                metadata={
                    "workspace_id": workspace_id,
                    "container_port": app_port,
                    "host_port": port_result.host_port,
                    "host": port_result.host,
                },
            )

        except Exception as e:
            logger.error(f"Local preview error: {e}")
            return self._create_error_result(
                deployment_id,
                str(e),
                started_at,
            )

    def _detect_app_port(self, env_config: dict) -> int:
        """
        Detect the application port to expose.

        Checks for common port configurations in environment.

        Args:
            env_config: Environment configuration dict

        Returns:
            Port number to expose
        """
        # Check explicit configuration
        if "PORT" in env_config:
            return int(env_config["PORT"])

        if "APP_PORT" in env_config:
            return int(env_config["APP_PORT"])

        # Common defaults by framework
        framework = env_config.get("FRAMEWORK", "").lower()
        framework_ports = {
            "nextjs": 3000,
            "next": 3000,
            "react": 3000,
            "vue": 8080,
            "nuxt": 3000,
            "svelte": 5173,
            "angular": 4200,
            "flask": 5000,
            "django": 8000,
            "fastapi": 8000,
            "express": 3000,
            "node": 3000,
            "rails": 3000,
            "go": 8080,
            "rust": 8080,
        }

        return framework_ports.get(framework, 3000)
