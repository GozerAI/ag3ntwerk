"""
Docker Registry Deployer.

Builds and pushes container images to a Docker registry.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from ag3ntwerk.modules.workbench.deployers.base import BaseDeployer
from ag3ntwerk.modules.workbench.pipeline_schemas import DeployResult, DeploymentTarget

if TYPE_CHECKING:
    from ag3ntwerk.modules.workbench.pipeline_schemas import PipelineOptions
    from ag3ntwerk.modules.workbench.service import WorkbenchService

logger = logging.getLogger(__name__)


class DockerRegistryDeployer(BaseDeployer):
    """
    Deployer for Docker registries.

    Builds a container image in the workspace and pushes it to a
    configured registry (Docker Hub, ECR, GCR, etc.).
    """

    @property
    def target(self) -> DeploymentTarget:
        return DeploymentTarget.DOCKER_REGISTRY

    @property
    def name(self) -> str:
        return "Docker Registry"

    async def deploy(
        self,
        workspace_id: str,
        workbench: "WorkbenchService",
        options: "PipelineOptions",
    ) -> DeployResult:
        """
        Build and push Docker image.

        Strategy:
        1. Build image from Dockerfile in workspace
        2. Tag image appropriately
        3. Push to configured registry

        Args:
            workspace_id: Workspace ID
            workbench: WorkbenchService instance
            options: Pipeline options

        Returns:
            DeployResult with image URL
        """
        deployment_id = f"docker-{uuid.uuid4().hex[:8]}"
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

            # Check for Dockerfile
            files = await workbench.list_files(workspace_id, "Dockerfile*")
            dockerfile = "Dockerfile"
            if not files:
                # Try to find any dockerfile
                all_files = await workbench.list_files(workspace_id)
                for f in all_files:
                    if "dockerfile" in f.lower():
                        dockerfile = f
                        break
                else:
                    return self._create_error_result(
                        deployment_id,
                        "No Dockerfile found in workspace",
                        started_at,
                    )

            # Get registry configuration
            registry = options.environment_config.get("DOCKER_REGISTRY", "docker.io")
            image_name = options.environment_config.get(
                "DOCKER_IMAGE_NAME",
                f"ag3ntwerk-{workspace_id}",
            )
            tag = options.environment_config.get("DOCKER_TAG", "latest")

            full_image_name = f"{registry}/{image_name}:{tag}"

            # Build the image
            logger.info(f"Building Docker image: {full_image_name}")
            build_result = await self._build_image(
                workbench,
                workspace_id,
                full_image_name,
                dockerfile,
                options.environment_config,
            )

            if not build_result["success"]:
                return self._create_error_result(
                    deployment_id,
                    f"Build failed: {build_result.get('error', 'Unknown error')}",
                    started_at,
                )

            # Push the image
            logger.info(f"Pushing Docker image: {full_image_name}")
            push_result = await self._push_image(
                workbench,
                workspace_id,
                full_image_name,
                options.environment_config,
            )

            if not push_result["success"]:
                return self._create_error_result(
                    deployment_id,
                    f"Push failed: {push_result.get('error', 'Unknown error')}",
                    started_at,
                )

            logger.info(f"Docker deployment successful: {full_image_name}")

            return self._create_success_result(
                deployment_id=deployment_id,
                url=full_image_name,
                started_at=started_at,
                metadata={
                    "registry": registry,
                    "image_name": image_name,
                    "tag": tag,
                    "workspace_id": workspace_id,
                    "build_logs": build_result.get("logs", ""),
                    "push_logs": push_result.get("logs", ""),
                },
            )

        except Exception as e:
            logger.error(f"Docker deployment error: {e}")
            return self._create_error_result(
                deployment_id,
                str(e),
                started_at,
            )

    async def _build_image(
        self,
        workbench: "WorkbenchService",
        workspace_id: str,
        image_name: str,
        dockerfile: str,
        env_config: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Build Docker image in workspace.

        Args:
            workbench: WorkbenchService instance
            workspace_id: Workspace ID
            image_name: Full image name with tag
            dockerfile: Dockerfile path
            env_config: Environment configuration

        Returns:
            Dict with success status and logs
        """
        from ag3ntwerk.modules.workbench.schemas import RunRequest

        # Build command
        cmd = [
            "docker",
            "build",
            "-t",
            image_name,
            "-f",
            dockerfile,
        ]

        # Add build args if specified
        build_args = env_config.get("DOCKER_BUILD_ARGS", "").split(",")
        for arg in build_args:
            if "=" in arg:
                cmd.extend(["--build-arg", arg.strip()])

        cmd.append(".")  # Build context

        run_request = RunRequest(
            workspace_id=workspace_id,
            cmd=cmd,
            timeout=600,  # 10 minutes for build
        )

        result = await workbench.run_command_sync(run_request)

        return {
            "success": result.exit_code == 0,
            "logs": result.stdout or "",
            "error": result.stderr if result.exit_code != 0 else None,
        }

    async def _push_image(
        self,
        workbench: "WorkbenchService",
        workspace_id: str,
        image_name: str,
        env_config: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Push Docker image to registry.

        Args:
            workbench: WorkbenchService instance
            workspace_id: Workspace ID
            image_name: Full image name with tag
            env_config: Environment configuration

        Returns:
            Dict with success status and logs
        """
        from ag3ntwerk.modules.workbench.schemas import RunRequest

        # Check for registry credentials
        registry_user = env_config.get("DOCKER_REGISTRY_USER")
        registry_pass = env_config.get("DOCKER_REGISTRY_PASSWORD")

        # Login if credentials provided
        if registry_user and registry_pass:
            registry = env_config.get("DOCKER_REGISTRY", "docker.io")
            login_cmd = [
                "docker",
                "login",
                "-u",
                registry_user,
                "-p",
                registry_pass,
                registry,
            ]

            login_request = RunRequest(
                workspace_id=workspace_id,
                cmd=login_cmd,
                timeout=60,
            )

            login_result = await workbench.run_command_sync(login_request)
            if login_result.exit_code != 0:
                return {
                    "success": False,
                    "error": f"Login failed: {login_result.stderr}",
                }

        # Push the image
        push_cmd = ["docker", "push", image_name]

        push_request = RunRequest(
            workspace_id=workspace_id,
            cmd=push_cmd,
            timeout=300,  # 5 minutes for push
        )

        result = await workbench.run_command_sync(push_request)

        return {
            "success": result.exit_code == 0,
            "logs": result.stdout or "",
            "error": result.stderr if result.exit_code != 0 else None,
        }
