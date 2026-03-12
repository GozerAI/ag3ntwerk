"""
Workbench Service - High-level service interface for agents.

Provides a unified API for ag3ntwerk agents to interact with
workspaces, command execution, and development environments.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.modules.workbench.schemas import (
    Workspace,
    WorkspaceCreate,
    WorkspaceStatus,
    WorkspaceUpdate,
    RuntimeType,
    RunRequest,
    RunResult,
    RunStatus,
    PortExposeRequest,
    PortExposeResult,
    FileWriteRequest,
    FileReadRequest,
    FileContent,
    WorkbenchStats,
    IDEInfo,
)
from ag3ntwerk.modules.workbench.settings import (
    WorkbenchSettings,
    get_workbench_settings,
)
from ag3ntwerk.modules.workbench.runner.base import BaseRunner
from ag3ntwerk.modules.workbench.runner.docker_runner import DockerRunner
from ag3ntwerk.modules.workbench.runner.fake_runner import FakeRunner
from ag3ntwerk.modules.workbench.utils.paths import (
    ensure_workspace_dir,
    init_workspace_from_template,
    clean_workspace,
    list_workspace_files,
    get_workspace_size,
)
from ag3ntwerk.modules.workbench.utils.ports import PortAllocator
from ag3ntwerk.modules.workbench.ide.manager import IDEContainerManager, IDEStatus
from ag3ntwerk.modules.workbench.persistence import WorkbenchPersistence, get_workbench_persistence

logger = get_logger(__name__)


class WorkbenchService:
    """
    High-level workbench service for ag3ntwerk agents.

    This service provides a unified interface for:
    - Forge: Development environment management
    - Foundry: Engineering team workspace provisioning
    - Nexus: Operations automation workspace
    - Blueprint: Product experimentation environments

    Example:
        ```python
        service = WorkbenchService()
        await service.initialize()

        # Create a workspace
        workspace = await service.create_workspace(
            WorkspaceCreate(name="my-project", runtime="python")
        )

        # Start the workspace
        await service.start_workspace(workspace.id)

        # Run a command
        result = await service.run_command(
            RunRequest(
                workspace_id=workspace.id,
                cmd=["python", "main.py"],
            )
        )

        # Get agent report
        report = service.get_agent_report("Forge")
        ```
    """

    def __init__(self, settings: Optional[WorkbenchSettings] = None):
        """
        Initialize the workbench service.

        Args:
            settings: Optional custom settings. Uses global settings if not provided.
        """
        self._settings = settings or get_workbench_settings()
        self._runner: Optional[BaseRunner] = None
        self._initialized = False

        # Persistence layer for surviving restarts
        self._persistence: Optional[WorkbenchPersistence] = None

        # Workspace storage (in-memory index backed by persistence)
        self._workspaces: Dict[str, Workspace] = {}

        # Run tracking
        self._runs: Dict[str, RunResult] = {}

        # Port allocator
        self._port_allocator = PortAllocator(
            start_port=self._settings.preview_port_start,
            end_port=self._settings.preview_port_end,
        )

        # Stats tracking
        self._total_workspaces_created = 0
        self._total_runs_executed = 0

        # IDE container manager (lazy initialized)
        self._ide_manager: Optional[IDEContainerManager] = None

    async def initialize(self) -> None:
        """
        Initialize the workbench service.

        Creates necessary directories, initializes the runner,
        and recovers existing workspaces from persistence.
        """
        if self._initialized:
            return

        # Validate settings
        errors = self._settings.validate()
        if errors:
            raise RuntimeError(f"Invalid workbench settings: {errors}")

        # Ensure root directory exists
        root_path = self._settings.get_root_path()
        root_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Workbench root directory: {root_path}")

        # Initialize persistence layer
        self._persistence = get_workbench_persistence()

        # Initialize runner based on settings
        if self._settings.runner_type == "docker":
            self._runner = DockerRunner(self._settings)
        else:
            self._runner = FakeRunner(self._settings)

        await self._runner.initialize()

        # Recover existing workspaces from persistence
        await self._recover_workspaces()

        self._initialized = True
        logger.info(f"WorkbenchService initialized with {self._settings.runner_type} runner")

    async def _recover_workspaces(self) -> None:
        """
        Recover workspaces from persistence and reconnect to Docker containers.

        This enables the system to survive restarts without losing state.
        """
        if not self._persistence:
            return

        # Load all persisted workspaces
        persisted_workspaces = self._persistence.load_all_workspaces()
        logger.info(f"Recovering {len(persisted_workspaces)} workspaces from persistence")

        # Get container mappings
        container_mappings = self._persistence.get_all_container_mappings()

        # Recover port allocations
        port_allocations = self._persistence.load_all_port_allocations()
        for host_port, workspace_id in port_allocations.items():
            self._port_allocator._allocated.add(host_port)

        for workspace in persisted_workspaces:
            workspace_id = workspace.id
            container_id = container_mappings.get(workspace_id)

            # Add to in-memory cache
            self._workspaces[workspace_id] = workspace

            # Try to reconnect to existing container
            if container_id and isinstance(self._runner, DockerRunner):
                try:
                    container_status = await self._verify_container(container_id)
                    if container_status:
                        # Container still exists - reconnect
                        self._runner._workspace_containers[workspace_id] = container_id

                        # Update status based on container state
                        if container_status.get("running"):
                            workspace.status = WorkspaceStatus.RUNNING
                        else:
                            workspace.status = WorkspaceStatus.STOPPED

                        logger.info(
                            f"Reconnected workspace {workspace_id} to container {container_id[:12]} "
                            f"(status: {workspace.status.value})"
                        )
                    else:
                        # Container no longer exists - mark as stopped
                        workspace.status = WorkspaceStatus.STOPPED
                        self._persistence.update_workspace_status(
                            workspace_id, WorkspaceStatus.STOPPED, None
                        )
                        logger.warning(f"Container for workspace {workspace_id} no longer exists")

                except Exception as e:
                    logger.warning(f"Failed to reconnect workspace {workspace_id}: {e}")
                    workspace.status = WorkspaceStatus.STOPPED

            # Load exposed ports
            exposed_ports = self._persistence.load_exposed_ports(workspace_id)
            if isinstance(self._runner, DockerRunner):
                self._runner._exposed_ports[workspace_id] = exposed_ports

            self._total_workspaces_created += 1

        logger.info(f"Recovered {len(self._workspaces)} workspaces")

    async def _verify_container(self, container_id: str) -> Optional[Dict[str, Any]]:
        """
        Verify a Docker container still exists and get its status.

        Args:
            container_id: The container ID to verify.

        Returns:
            Container status dict or None if container doesn't exist.
        """
        if not isinstance(self._runner, DockerRunner):
            return None

        try:
            import docker

            container = self._runner._client.containers.get(container_id)
            container.reload()
            return {
                "running": container.status == "running",
                "state": container.status,
                "id": container.id,
            }
        except docker.errors.NotFound:
            return None
        except Exception as e:
            logger.warning(f"Error verifying container {container_id}: {e}")
            return None

    async def shutdown(self) -> None:
        """Shutdown the workbench service."""
        if not self._initialized:
            return

        if self._runner:
            await self._runner.shutdown()

        self._initialized = False
        logger.info("WorkbenchService shutdown complete")

    # =========================================================================
    # Workspace Management
    # =========================================================================

    async def create_workspace(self, request: WorkspaceCreate) -> Workspace:
        """
        Create a new workspace.

        Args:
            request: Workspace creation parameters.

        Returns:
            The created Workspace.
        """
        if not self._initialized:
            await self.initialize()

        # Create workspace object
        workspace = Workspace(
            name=request.name,
            path="",  # Will be set below
            runtime=request.runtime,
            status=WorkspaceStatus.STOPPED,
        )

        # Initialize workspace directory
        workspace_path = init_workspace_from_template(
            workspace.id,
            request.template,
            request.runtime,
        )
        workspace.path = str(workspace_path)

        # Git clone if URL provided
        if request.git_clone_url:
            # For MVP, we'll just log this - actual git clone would be done in container
            logger.info(f"Git clone requested: {request.git_clone_url}")
            workspace.metadata["git_clone_url"] = request.git_clone_url

        # Create container (but don't start it)
        await self._runner.create_workspace_container(workspace)

        # Get container ID for persistence
        container_id = None
        if isinstance(self._runner, DockerRunner):
            container_id = self._runner._workspace_containers.get(workspace.id)

        # Store workspace in memory and persistence
        self._workspaces[workspace.id] = workspace
        self._total_workspaces_created += 1

        # Persist to database
        if self._persistence:
            self._persistence.save_workspace(workspace, container_id)

        logger.info(f"Created workspace: {workspace.id} ({workspace.name})")
        return workspace

    async def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """
        Get a workspace by ID.

        Args:
            workspace_id: The workspace ID.

        Returns:
            The Workspace or None if not found.
        """
        workspace = self._workspaces.get(workspace_id)
        if workspace:
            # Update status from runner
            status = await self._runner.get_container_status(workspace_id)
            if status.get("running"):
                workspace.status = WorkspaceStatus.RUNNING
            elif status.get("state") == "error":
                workspace.status = WorkspaceStatus.ERROR
            else:
                workspace.status = WorkspaceStatus.STOPPED
            workspace.updated_at = datetime.now(timezone.utc)
        return workspace

    async def list_workspaces(
        self,
        status: Optional[WorkspaceStatus] = None,
        runtime: Optional[RuntimeType] = None,
    ) -> List[Workspace]:
        """
        List all workspaces with optional filtering.

        Args:
            status: Filter by status.
            runtime: Filter by runtime type.

        Returns:
            List of Workspace objects.
        """
        workspaces = list(self._workspaces.values())

        if status:
            workspaces = [w for w in workspaces if w.status == status]

        if runtime:
            workspaces = [w for w in workspaces if w.runtime == runtime]

        return workspaces

    async def delete_workspace(self, workspace_id: str) -> bool:
        """
        Delete a workspace.

        Stops the container if running, removes it, and cleans up files.

        Args:
            workspace_id: The workspace ID.

        Returns:
            True if deleted successfully.
        """
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False

        try:
            # Stop and remove container
            await self._runner.remove(workspace_id)

            # Clean up files
            clean_workspace(workspace_id)

            # Release ports
            self._port_allocator.release_all(workspace_id)

            # Remove from persistence
            if self._persistence:
                self._persistence.delete_workspace(workspace_id)

            # Remove from index
            del self._workspaces[workspace_id]

            logger.info(f"Deleted workspace: {workspace_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete workspace {workspace_id}: {e}")
            return False

    # =========================================================================
    # Workspace Lifecycle
    # =========================================================================

    async def start_workspace(self, workspace_id: str) -> Workspace:
        """
        Start a workspace's runtime container.

        Args:
            workspace_id: The workspace ID.

        Returns:
            Updated Workspace.

        Raises:
            ValueError: If workspace not found.
        """
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {workspace_id}")

        workspace.status = WorkspaceStatus.STARTING
        workspace.updated_at = datetime.now(timezone.utc)

        try:
            await self._runner.start(workspace_id)
            workspace.status = WorkspaceStatus.RUNNING
        except Exception as e:
            workspace.status = WorkspaceStatus.ERROR
            workspace.metadata["error"] = str(e)
            raise

        workspace.updated_at = datetime.now(timezone.utc)

        # Update persistence
        if self._persistence:
            container_id = None
            if isinstance(self._runner, DockerRunner):
                container_id = self._runner._workspace_containers.get(workspace_id)
            self._persistence.update_workspace_status(workspace_id, workspace.status, container_id)

        logger.info(f"Started workspace: {workspace_id}")
        return workspace

    async def stop_workspace(self, workspace_id: str) -> Workspace:
        """
        Stop a workspace's runtime container.

        Args:
            workspace_id: The workspace ID.

        Returns:
            Updated Workspace.

        Raises:
            ValueError: If workspace not found.
        """
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {workspace_id}")

        workspace.status = WorkspaceStatus.STOPPING
        workspace.updated_at = datetime.now(timezone.utc)

        try:
            await self._runner.stop(workspace_id)
            workspace.status = WorkspaceStatus.STOPPED
        except Exception as e:
            workspace.status = WorkspaceStatus.ERROR
            workspace.metadata["error"] = str(e)
            raise

        workspace.updated_at = datetime.now(timezone.utc)

        # Update persistence
        if self._persistence:
            self._persistence.update_workspace_status(workspace_id, workspace.status)

        logger.info(f"Stopped workspace: {workspace_id}")
        return workspace

    # =========================================================================
    # Command Execution
    # =========================================================================

    async def run_command(self, request: RunRequest) -> RunResult:
        """
        Run a command in a workspace.

        This is asynchronous - returns immediately with a run_id.
        Use get_run_result to check status.

        Args:
            request: Run request parameters.

        Returns:
            RunResult with run_id for tracking.
        """
        workspace = self._workspaces.get(request.workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {request.workspace_id}")

        if workspace.status != WorkspaceStatus.RUNNING:
            raise RuntimeError(f"Workspace is not running: {workspace.status}")

        run_id = await self._runner.exec(
            workspace_id=request.workspace_id,
            cmd=request.cmd,
            env=request.env,
            cwd=request.cwd,
            timeout=request.timeout,
        )

        self._total_runs_executed += 1

        # Get initial result
        result = await self._runner.get_run_result(run_id)
        if result:
            self._runs[run_id] = result
            return result

        # Return placeholder if not ready
        return RunResult(
            run_id=run_id,
            workspace_id=request.workspace_id,
            cmd=request.cmd,
            status=RunStatus.PENDING,
        )

    async def run_command_sync(self, request: RunRequest) -> RunResult:
        """
        Run a command and wait for completion.

        Args:
            request: Run request parameters.

        Returns:
            RunResult with execution details.
        """
        workspace = self._workspaces.get(request.workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {request.workspace_id}")

        if workspace.status != WorkspaceStatus.RUNNING:
            raise RuntimeError(f"Workspace is not running: {workspace.status}")

        result = await self._runner.exec_sync(
            workspace_id=request.workspace_id,
            cmd=request.cmd,
            env=request.env,
            cwd=request.cwd,
            timeout=request.timeout,
        )

        self._total_runs_executed += 1
        self._runs[result.run_id] = result

        # Persist run result
        if self._persistence:
            self._persistence.save_run(result)

        return result

    async def get_run_result(self, run_id: str) -> Optional[RunResult]:
        """
        Get the result of a command execution.

        Args:
            run_id: The run ID.

        Returns:
            RunResult or None if not found.
        """
        # Check cache first
        if run_id in self._runs:
            result = self._runs[run_id]
            if result.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.TIMEOUT):
                return result

        # Get fresh result from runner
        result = await self._runner.get_run_result(run_id)
        if result:
            self._runs[run_id] = result
        return result

    async def get_run_logs(self, run_id: str) -> str:
        """
        Get logs from a command execution.

        Args:
            run_id: The run ID.

        Returns:
            Log output string.
        """
        return await self._runner.get_logs(run_id)

    # =========================================================================
    # Port Management
    # =========================================================================

    async def expose_port(self, request: PortExposeRequest) -> PortExposeResult:
        """
        Expose a port from a workspace.

        Args:
            request: Port expose parameters.

        Returns:
            PortExposeResult with preview URL.
        """
        workspace = self._workspaces.get(request.workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {request.workspace_id}")

        result = await self._runner.expose_port(
            workspace_id=request.workspace_id,
            port=request.port,
            proto=request.proto.value,
            label=request.label,
        )

        # Persist exposed port
        if self._persistence:
            self._persistence.save_exposed_port(result)

        return result

    async def list_exposed_ports(self, workspace_id: str) -> List[PortExposeResult]:
        """
        List all exposed ports for a workspace.

        Args:
            workspace_id: The workspace ID.

        Returns:
            List of exposed ports.
        """
        return await self._runner.list_exposed_ports(workspace_id)

    # =========================================================================
    # File Operations
    # =========================================================================

    async def write_files(self, request: FileWriteRequest) -> Dict[str, bool]:
        """
        Write files to a workspace.

        Args:
            request: File write parameters.

        Returns:
            Dictionary of path -> success for each file.
        """
        workspace = self._workspaces.get(request.workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {request.workspace_id}")

        workspace_path = self._settings.get_workspace_path(request.workspace_id)
        results = {}

        for rel_path, content in request.files.items():
            file_path = workspace_path / rel_path
            try:
                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                results[rel_path] = True
                logger.debug(f"Wrote file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to write {rel_path}: {e}")
                results[rel_path] = False

        workspace.updated_at = datetime.now(timezone.utc)
        return results

    async def read_files(self, request: FileReadRequest) -> List[FileContent]:
        """
        Read files from a workspace.

        Args:
            request: File read parameters.

        Returns:
            List of FileContent objects.
        """
        workspace = self._workspaces.get(request.workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {request.workspace_id}")

        workspace_path = self._settings.get_workspace_path(request.workspace_id)
        results = []

        for rel_path in request.paths:
            file_path = workspace_path / rel_path
            try:
                if file_path.exists():
                    content = file_path.read_text()
                    results.append(
                        FileContent(
                            path=rel_path,
                            content=content,
                            exists=True,
                        )
                    )
                else:
                    results.append(
                        FileContent(
                            path=rel_path,
                            exists=False,
                        )
                    )
            except Exception as e:
                results.append(
                    FileContent(
                        path=rel_path,
                        error=str(e),
                        exists=True,
                    )
                )

        return results

    async def list_files(
        self,
        workspace_id: str,
        pattern: str = "**/*",
    ) -> List[str]:
        """
        List files in a workspace.

        Args:
            workspace_id: The workspace ID.
            pattern: Glob pattern.

        Returns:
            List of relative file paths.
        """
        return list_workspace_files(workspace_id, pattern)

    # =========================================================================
    # IDE Integration
    # =========================================================================

    async def get_ide_url(self, workspace_id: str) -> IDEInfo:
        """
        Get the IDE URL for a workspace.

        Args:
            workspace_id: The workspace ID.

        Returns:
            IDEInfo with URL to access IDE.
        """
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {workspace_id}")

        # Allocate a port for the IDE
        host_port = self._port_allocator.allocate(workspace_id)
        if not host_port:
            raise RuntimeError("No available ports for IDE")

        ide_url = self._settings.get_ide_url(workspace_id, host_port)

        return IDEInfo(
            workspace_id=workspace_id,
            ide_url=ide_url,
            mode=self._settings.ide.mode,
        )

    def _get_ide_manager(self) -> IDEContainerManager:
        """Get or create the IDE container manager."""
        if self._ide_manager is None:
            self._ide_manager = IDEContainerManager(
                settings=self._settings,
                port_allocator=self._port_allocator,
            )
        return self._ide_manager

    async def start_ide(
        self,
        workspace_id: str,
        password: Optional[str] = None,
    ) -> IDEInfo:
        """
        Start the browser IDE (code-server) for a workspace.

        Creates and starts a code-server container that provides a
        browser-based VS Code experience for the workspace.

        Args:
            workspace_id: The workspace ID.
            password: Optional password for IDE auth. Auto-generated if not provided.

        Returns:
            IDEInfo with URL and auth details to access the IDE.

        Raises:
            ValueError: If workspace not found.
            RuntimeError: If IDE cannot be started.

        Example:
            ```python
            ide_info = await service.start_ide("ws-123")
            print(f"Open IDE at: {ide_info.ide_url}")
            # Use ide_info.auth_token for authentication
            ```
        """
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {workspace_id}")

        ide_manager = self._get_ide_manager()

        # Start the IDE container
        ide_info = await ide_manager.start_ide(
            workspace_id=workspace_id,
            workspace_path=workspace.path,
            password=password,
        )

        logger.info(f"Started IDE for workspace {workspace_id} at {ide_info.ide_url}")
        return ide_info

    async def stop_ide(self, workspace_id: str) -> bool:
        """
        Stop the browser IDE for a workspace.

        Stops and removes the code-server container, freeing resources.

        Args:
            workspace_id: The workspace ID.

        Returns:
            True if stopped successfully, False otherwise.

        Example:
            ```python
            success = await service.stop_ide("ws-123")
            ```
        """
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {workspace_id}")

        ide_manager = self._get_ide_manager()
        success = await ide_manager.stop_ide(workspace_id)

        if success:
            logger.info(f"Stopped IDE for workspace {workspace_id}")
        else:
            logger.warning(f"Failed to stop IDE for workspace {workspace_id}")

        return success

    async def get_ide_status(self, workspace_id: str) -> IDEStatus:
        """
        Get the status of the browser IDE for a workspace.

        Returns detailed information about the IDE container including
        whether it's running, resource usage, and access URL.

        Args:
            workspace_id: The workspace ID.

        Returns:
            IDEStatus with container details.

        Example:
            ```python
            status = await service.get_ide_status("ws-123")
            if status.running:
                print(f"IDE URL: {status.ide_url}")
                print(f"CPU: {status.cpu_usage}%")
            ```
        """
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {workspace_id}")

        ide_manager = self._get_ide_manager()
        return await ide_manager.get_ide_status(workspace_id)

    async def ide_health_check(self, workspace_id: str) -> bool:
        """
        Check if the IDE for a workspace is healthy and responding.

        Args:
            workspace_id: The workspace ID.

        Returns:
            True if IDE is healthy and responding.
        """
        ide_manager = self._get_ide_manager()
        return await ide_manager.health_check(workspace_id)

    # =========================================================================
    # Agent Reports
    # =========================================================================

    def get_agent_report(self, agent_code: str) -> Dict[str, Any]:
        """
        Generate a report tailored for a specific agent.

        Args:
            agent_code: The agent code (Forge, Foundry, Nexus, etc.)

        Returns:
            Agent-specific workbench report.
        """
        base_info = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "module": "workbench",
            "runner_type": self._settings.runner_type,
            "initialized": self._initialized,
        }

        stats = self.get_stats()

        if agent_code == "Forge":
            # Technology focus: development environment health
            return {
                "agent": "Forge",
                "focus": "Development Environments",
                **base_info,
                "overview": {
                    "total_workspaces": stats.total_workspaces,
                    "running_workspaces": stats.running_workspaces,
                    "total_commands_run": stats.total_runs,
                },
                "workspaces_by_runtime": stats.workspaces_by_runtime,
                "workspaces_by_status": stats.workspaces_by_status,
                "exposed_services": stats.active_ports,
                "recommendations": self._generate_cto_recommendations(stats),
            }

        elif agent_code == "Foundry":
            # Engineering focus: team workspace management
            return {
                "agent": "Foundry",
                "focus": "Engineering Workspaces",
                **base_info,
                "workspace_health": {
                    "total": stats.total_workspaces,
                    "active": stats.running_workspaces,
                    "idle": stats.total_workspaces - stats.running_workspaces,
                },
                "resource_usage": {
                    "workspaces_by_runtime": stats.workspaces_by_runtime,
                    "exposed_ports": stats.active_ports,
                },
                "automation_metrics": {
                    "total_commands_executed": stats.total_runs,
                },
            }

        elif agent_code == "Nexus":
            # Operations focus: automation and efficiency
            return {
                "agent": "Nexus",
                "focus": "Operations Automation",
                **base_info,
                "operational_health": {
                    "workspaces_running": stats.running_workspaces,
                    "total_workspaces": stats.total_workspaces,
                    "utilization_rate": (
                        (stats.running_workspaces / stats.total_workspaces * 100)
                        if stats.total_workspaces > 0
                        else 0
                    ),
                },
                "automation_stats": {
                    "total_automated_runs": stats.total_runs,
                },
            }

        else:
            # Default: basic overview
            return {
                "agent": agent_code,
                "focus": "General Overview",
                **base_info,
                "stats": stats.to_dict(),
            }

    def _generate_cto_recommendations(self, stats: WorkbenchStats) -> List[str]:
        """Generate recommendations for Forge."""
        recommendations = []

        if stats.total_workspaces == 0:
            recommendations.append(
                "No workspaces created - consider setting up development environments"
            )

        if stats.running_workspaces > 5:
            recommendations.append("Many workspaces running - review resource usage")

        if stats.total_runs == 0:
            recommendations.append("No commands executed - workbench may be underutilized")

        if not recommendations:
            recommendations.append("Workbench operating normally")

        return recommendations

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> WorkbenchStats:
        """
        Get comprehensive workbench statistics.

        Returns:
            WorkbenchStats object.
        """
        workspaces = list(self._workspaces.values())

        # Count by runtime
        by_runtime = {}
        for ws in workspaces:
            runtime = ws.runtime.value
            by_runtime[runtime] = by_runtime.get(runtime, 0) + 1

        # Count by status
        by_status = {}
        for ws in workspaces:
            status = ws.status.value
            by_status[status] = by_status.get(status, 0) + 1

        running_count = sum(1 for ws in workspaces if ws.status == WorkspaceStatus.RUNNING)

        return WorkbenchStats(
            total_workspaces=len(workspaces),
            running_workspaces=running_count,
            total_runs=self._total_runs_executed,
            active_ports=sum(len(self._port_allocator.get_ports(ws.id)) for ws in workspaces),
            workspaces_by_runtime=by_runtime,
            workspaces_by_status=by_status,
        )

    async def is_healthy(self) -> bool:
        """
        Check if the workbench service is healthy.

        Returns:
            True if healthy.
        """
        if not self._initialized:
            return False

        if self._runner:
            return await self._runner.is_healthy()

        return False


# Global service singleton
_workbench_service: Optional[WorkbenchService] = None


def get_workbench_service() -> WorkbenchService:
    """Get or create the global workbench service instance."""
    global _workbench_service
    if _workbench_service is None:
        _workbench_service = WorkbenchService()
    return _workbench_service
