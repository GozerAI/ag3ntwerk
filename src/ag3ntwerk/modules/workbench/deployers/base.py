"""
Base Deployer Interface.

Abstract base class for all deployment implementations.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import BaseModel, Field

from ag3ntwerk.modules.workbench.pipeline_schemas import DeployResult, DeploymentTarget

if TYPE_CHECKING:
    from ag3ntwerk.modules.workbench.pipeline_schemas import PipelineOptions
    from ag3ntwerk.modules.workbench.service import WorkbenchService


class DeployOptions(BaseModel):
    """Base deployment options."""

    environment: str = Field(
        default="development",
        description="Target environment",
    )
    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set",
    )
    timeout_seconds: int = Field(
        default=600,
        description="Deployment timeout in seconds",
    )


class BaseDeployer(ABC):
    """
    Abstract base class for deployers.

    All deployer implementations must inherit from this class and
    implement the deploy() method.
    """

    @property
    @abstractmethod
    def target(self) -> DeploymentTarget:
        """Get the deployment target type."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the deployer name."""
        pass

    @abstractmethod
    async def deploy(
        self,
        workspace_id: str,
        workbench: "WorkbenchService",
        options: "PipelineOptions",
    ) -> DeployResult:
        """
        Deploy the workspace to the target.

        Args:
            workspace_id: Workspace ID to deploy
            workbench: WorkbenchService instance for file/container operations
            options: Pipeline options with deployment configuration

        Returns:
            DeployResult with deployment URL and status
        """
        pass

    async def validate_workspace(
        self,
        workspace_id: str,
        workbench: "WorkbenchService",
    ) -> bool:
        """
        Validate that workspace is ready for deployment.

        Args:
            workspace_id: Workspace ID
            workbench: WorkbenchService instance

        Returns:
            True if workspace is valid for deployment
        """
        workspace = await workbench.get_workspace(workspace_id)
        if not workspace:
            return False

        # Check workspace has files
        files = await workbench.list_files(workspace_id)
        return len(files) > 0

    def _create_error_result(
        self,
        deployment_id: str,
        error: str,
        started_at: Optional[datetime] = None,
    ) -> DeployResult:
        """Create an error deployment result."""
        now = datetime.now(timezone.utc)
        return DeployResult(
            deployment_id=deployment_id,
            target=self.target,
            status="failed",
            error=error,
            started_at=started_at or now,
            completed_at=now,
        )

    def _create_success_result(
        self,
        deployment_id: str,
        url: str,
        started_at: datetime,
        logs_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DeployResult:
        """Create a successful deployment result."""
        now = datetime.now(timezone.utc)
        return DeployResult(
            deployment_id=deployment_id,
            target=self.target,
            status="success",
            url=url,
            logs_url=logs_url,
            started_at=started_at,
            completed_at=now,
            metadata=metadata or {},
        )
