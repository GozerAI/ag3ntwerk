"""
Workbench Runner Base - Abstract interface for container runtimes.

Defines the contract that all runner implementations must follow.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ag3ntwerk.modules.workbench.schemas import (
    Workspace,
    RunResult,
    PortExposeResult,
    RuntimeType,
)


@dataclass
class RunnerCapabilities:
    """Capabilities of a runner implementation."""

    supports_docker: bool = False
    """Whether the runner uses Docker."""

    supports_port_mapping: bool = False
    """Whether the runner can map container ports to host."""

    supports_resource_limits: bool = False
    """Whether the runner supports CPU/memory limits."""

    supports_network_isolation: bool = False
    """Whether containers are network isolated."""

    max_concurrent_workspaces: int = 10
    """Maximum concurrent running workspaces."""

    supported_runtimes: List[RuntimeType] = field(default_factory=lambda: list(RuntimeType))
    """List of supported runtime types."""


class BaseRunner(ABC):
    """
    Abstract base class for workspace runners.

    A runner manages the lifecycle of container-based workspaces,
    including creation, starting, stopping, and command execution.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the runner.

        This is called once when the workbench service starts.
        Implementations should set up networks, pull images, etc.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown the runner.

        This is called when the workbench service stops.
        Implementations should clean up resources.
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> RunnerCapabilities:
        """
        Get the capabilities of this runner.

        Returns:
            RunnerCapabilities describing what this runner supports.
        """
        pass

    @abstractmethod
    async def create_workspace_container(
        self,
        workspace: Workspace,
    ) -> None:
        """
        Create a container for a workspace.

        This creates but does not start the container. The container
        should be configured with:
        - Workspace directory mounted at /workspace
        - Non-root user
        - Resource limits
        - No privileged mode
        - Dropped capabilities

        Args:
            workspace: The workspace to create container for.

        Raises:
            RuntimeError: If container creation fails.
        """
        pass

    @abstractmethod
    async def start(self, workspace_id: str) -> None:
        """
        Start a workspace's container.

        Args:
            workspace_id: ID of workspace to start.

        Raises:
            ValueError: If workspace not found.
            RuntimeError: If start fails.
        """
        pass

    @abstractmethod
    async def stop(self, workspace_id: str) -> None:
        """
        Stop a workspace's container.

        Args:
            workspace_id: ID of workspace to stop.

        Raises:
            ValueError: If workspace not found.
            RuntimeError: If stop fails.
        """
        pass

    @abstractmethod
    async def remove(self, workspace_id: str) -> None:
        """
        Remove a workspace's container.

        This stops the container if running and removes it.

        Args:
            workspace_id: ID of workspace to remove.

        Raises:
            ValueError: If workspace not found.
        """
        pass

    @abstractmethod
    async def exec(
        self,
        workspace_id: str,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """
        Execute a command in a workspace's container.

        The command runs inside the container in the workspace directory.
        This is non-blocking and returns a run_id for tracking.

        Args:
            workspace_id: ID of workspace to run command in.
            cmd: Command as list of arguments.
            env: Optional environment variables.
            cwd: Optional working directory relative to workspace.
            timeout: Optional timeout in seconds.

        Returns:
            run_id: Unique identifier for this execution.

        Raises:
            ValueError: If workspace not found or not running.
            RuntimeError: If execution fails to start.
        """
        pass

    @abstractmethod
    async def exec_sync(
        self,
        workspace_id: str,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> RunResult:
        """
        Execute a command synchronously and wait for completion.

        Args:
            workspace_id: ID of workspace to run command in.
            cmd: Command as list of arguments.
            env: Optional environment variables.
            cwd: Optional working directory relative to workspace.
            timeout: Optional timeout in seconds.

        Returns:
            RunResult with execution details.

        Raises:
            ValueError: If workspace not found or not running.
            RuntimeError: If execution fails.
        """
        pass

    @abstractmethod
    async def get_run_result(self, run_id: str) -> Optional[RunResult]:
        """
        Get the result of a command execution.

        Args:
            run_id: The run ID returned from exec().

        Returns:
            RunResult if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_logs(
        self,
        run_id: str,
        stdout: bool = True,
        stderr: bool = True,
    ) -> str:
        """
        Get logs from a command execution.

        Args:
            run_id: The run ID to get logs for.
            stdout: Include stdout.
            stderr: Include stderr.

        Returns:
            Combined log output.

        Raises:
            ValueError: If run_id not found.
        """
        pass

    @abstractmethod
    async def expose_port(
        self,
        workspace_id: str,
        port: int,
        proto: str = "http",
        label: Optional[str] = None,
    ) -> PortExposeResult:
        """
        Expose a port from a workspace's container.

        Args:
            workspace_id: ID of workspace.
            port: Container port to expose.
            proto: Protocol (http or tcp).
            label: Optional label for the port.

        Returns:
            PortExposeResult with preview URL.

        Raises:
            ValueError: If workspace not found.
            RuntimeError: If port mapping fails.
        """
        pass

    @abstractmethod
    async def list_exposed_ports(
        self,
        workspace_id: str,
    ) -> List[PortExposeResult]:
        """
        List all exposed ports for a workspace.

        Args:
            workspace_id: ID of workspace.

        Returns:
            List of exposed ports.
        """
        pass

    @abstractmethod
    async def get_container_status(
        self,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """
        Get detailed status of a workspace's container.

        Args:
            workspace_id: ID of workspace.

        Returns:
            Dictionary with container status details including:
            - running: bool
            - state: str
            - started_at: Optional[str]
            - cpu_usage: Optional[float]
            - memory_usage: Optional[str]
        """
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """
        Check if the runner is healthy and operational.

        Returns:
            True if runner is healthy.
        """
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the runner.

        Returns:
            Dictionary with stats like:
            - total_containers
            - running_containers
            - total_runs
            - images_available
        """
        pass
