"""
Vercel Deployer.

Deploys workspaces to the Vercel platform using the Vercel CLI or API.
"""

import asyncio
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


class VercelDeployer(BaseDeployer):
    """
    Deployer for Vercel platform.

    Uses the Vercel CLI within the workspace container to deploy.
    Alternatively can use the Vercel API directly if configured.
    """

    @property
    def target(self) -> DeploymentTarget:
        return DeploymentTarget.VERCEL

    @property
    def name(self) -> str:
        return "Vercel"

    async def deploy(
        self,
        workspace_id: str,
        workbench: "WorkbenchService",
        options: "PipelineOptions",
    ) -> DeployResult:
        """
        Deploy to Vercel.

        Strategy:
        1. Check for vercel.json or auto-detect framework
        2. Run vercel CLI in workspace container
        3. Parse deployment URL from output

        Args:
            workspace_id: Workspace ID
            workbench: WorkbenchService instance
            options: Pipeline options

        Returns:
            DeployResult with Vercel deployment URL
        """
        deployment_id = f"vercel-{uuid.uuid4().hex[:8]}"
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

            # Check for Vercel token in environment
            vercel_token = options.environment_config.get("VERCEL_TOKEN")
            if not vercel_token:
                # Try to get from container environment
                logger.warning("No VERCEL_TOKEN provided, deployment may fail")

            # Build the vercel deploy command
            cmd = ["npx", "vercel", "--yes"]

            # Add production flag if specified
            if options.environment_config.get("production", False):
                cmd.append("--prod")

            # Add token if available
            if vercel_token:
                cmd.extend(["--token", vercel_token])

            # Run vercel CLI in container
            from ag3ntwerk.modules.workbench.schemas import RunRequest

            run_request = RunRequest(
                workspace_id=workspace_id,
                cmd=cmd,
                timeout=300,  # 5 minutes for deployment
                env={"VERCEL_TOKEN": vercel_token} if vercel_token else None,
            )

            result = await workbench.run_command_sync(run_request)

            # Parse deployment URL from output
            deployment_url = self._parse_vercel_url(result.stdout or "")

            if result.exit_code != 0:
                error_msg = result.stderr or result.stdout or "Unknown deployment error"
                logger.error(f"Vercel deployment failed: {error_msg}")
                return self._create_error_result(
                    deployment_id,
                    f"Deployment failed: {error_msg}",
                    started_at,
                )

            if not deployment_url:
                return self._create_error_result(
                    deployment_id,
                    "Could not parse deployment URL from Vercel output",
                    started_at,
                )

            logger.info(f"Vercel deployment successful: {deployment_url}")

            return self._create_success_result(
                deployment_id=deployment_id,
                url=deployment_url,
                started_at=started_at,
                metadata={
                    "stdout": result.stdout,
                    "workspace_id": workspace_id,
                },
            )

        except Exception as e:
            logger.error(f"Vercel deployment error: {e}")
            return self._create_error_result(
                deployment_id,
                str(e),
                started_at,
            )

    def _parse_vercel_url(self, output: str) -> Optional[str]:
        """
        Parse the deployment URL from Vercel CLI output.

        The URL typically appears in the format:
        - https://project-xxxx.vercel.app
        - Production: https://project.vercel.app

        Args:
            output: Vercel CLI stdout

        Returns:
            Deployment URL or None if not found
        """
        import re

        # Look for Vercel deployment URLs
        patterns = [
            r"(https://[a-zA-Z0-9-]+\.vercel\.app)",
            r"Production: (https://[a-zA-Z0-9.-]+)",
            r"Preview: (https://[a-zA-Z0-9.-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(1)

        return None

    async def get_deployment_status(
        self,
        deployment_id: str,
        workbench: "WorkbenchService",
        workspace_id: str,
    ) -> Dict[str, Any]:
        """
        Get the status of a Vercel deployment.

        Args:
            deployment_id: Vercel deployment ID
            workbench: WorkbenchService instance
            workspace_id: Workspace ID

        Returns:
            Deployment status dict
        """
        # This would typically call Vercel API
        # For now, return basic status
        return {
            "deployment_id": deployment_id,
            "status": "unknown",
            "message": "Status check requires Vercel API integration",
        }
