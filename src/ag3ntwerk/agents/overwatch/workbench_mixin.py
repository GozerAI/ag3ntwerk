"""Workbench pipeline integration mixin for Overwatch."""

from typing import Any, Dict, List

from ag3ntwerk.core.logging import get_logger

logger = get_logger(__name__)


class WorkbenchMixin:
    """Workbench pipeline integration for Overwatch."""

    async def connect_workbench_pipeline(self, pipeline: "WorkbenchPipeline") -> None:
        """
        Connect the Workbench pipeline to the Overwatch.

        This enables:
        - Workspace management via Overwatch
        - Command execution in development environments
        - IDE integration

        Args:
            pipeline: The workbench pipeline instance
        """
        self._workbench_pipeline = pipeline
        logger.info("Workbench pipeline connected to Overwatch", component="cos")

    async def disconnect_workbench_pipeline(self) -> None:
        """Disconnect the workbench pipeline."""
        self._workbench_pipeline = None
        logger.info("Workbench pipeline disconnected from Overwatch", component="cos")

    def is_workbench_connected(self) -> bool:
        """Check if workbench pipeline is connected."""
        return self._workbench_pipeline is not None

    async def run_workbench_pipeline(
        self,
        workspace_id: str,
        cmd: List[str],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Run a command in a workbench workspace.

        Args:
            workspace_id: The workspace ID
            cmd: Command to execute
            **kwargs: Additional arguments

        Returns:
            Execution result
        """
        if not self.is_workbench_connected():
            return {"error": "Workbench pipeline not connected"}

        return await self._workbench_pipeline.execute(
            workspace_id=workspace_id,
            cmd=cmd,
            **kwargs,
        )

    async def get_workbench_status(self) -> Dict[str, Any]:
        """Get workbench pipeline status."""
        if not self.is_workbench_connected():
            return {"connected": False}

        return {
            "connected": True,
            "stats": await self._workbench_pipeline.get_stats(),
        }
