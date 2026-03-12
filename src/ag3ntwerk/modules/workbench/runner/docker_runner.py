"""
Workbench Docker Runner - Docker-based container runtime.

Implements the BaseRunner interface using Docker for container management.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.modules.workbench.runner.base import BaseRunner, RunnerCapabilities
from ag3ntwerk.modules.workbench.schemas import (
    Workspace,
    WorkspaceStatus,
    RunResult,
    RunStatus,
    PortExposeResult,
    PortProtocol,
    RuntimeType,
)
from ag3ntwerk.modules.workbench.settings import WorkbenchSettings, get_workbench_settings

logger = logging.getLogger(__name__)


class DockerRunner(BaseRunner):
    """
    Docker-based runner for workspaces.

    Uses the Docker SDK to manage container lifecycles. Containers are
    configured with security best practices:
    - Non-root user
    - Dropped capabilities
    - Resource limits
    - No privileged mode
    - Isolated network
    """

    def __init__(self, settings: Optional[WorkbenchSettings] = None):
        """
        Initialize the Docker runner.

        Args:
            settings: Workbench settings. Uses global settings if not provided.
        """
        self._settings = settings or get_workbench_settings()
        self._client = None
        self._network = None
        self._initialized = False

        # Track workspaces and their containers
        self._workspace_containers: Dict[str, str] = {}  # workspace_id -> container_id

        # Track running executions
        self._runs: Dict[str, RunResult] = {}  # run_id -> RunResult

        # Track exposed ports
        self._exposed_ports: Dict[str, List[PortExposeResult]] = {}  # workspace_id -> ports

        # Port allocation tracking
        self._allocated_ports: Dict[int, str] = {}  # host_port -> workspace_id
        self._next_port = self._settings.preview_port_start

        # Stats
        self._total_runs = 0

    async def initialize(self) -> None:
        """Initialize Docker client and network."""
        if self._initialized:
            return

        try:
            import docker

            self._client = docker.from_env()

            # Verify Docker is accessible
            self._client.ping()
            logger.info("Docker client connected successfully")

            # Create or get the workbench network
            network_name = self._settings.docker.network_name
            try:
                self._network = self._client.networks.get(network_name)
                logger.info(f"Using existing Docker network: {network_name}")
            except docker.errors.NotFound:
                self._network = self._client.networks.create(
                    network_name,
                    driver="bridge",
                    internal=False,  # Allow outbound access
                    attachable=True,
                )
                logger.info(f"Created Docker network: {network_name}")

            self._initialized = True

        except ImportError:
            logger.error("Docker SDK not installed. Install with: pip install docker")
            raise RuntimeError("Docker SDK not available")
        except Exception as e:
            logger.error(f"Failed to initialize Docker runner: {e}")
            raise RuntimeError(f"Docker initialization failed: {e}")

    async def shutdown(self) -> None:
        """Shutdown Docker runner and cleanup resources."""
        if not self._initialized:
            return

        # Stop all running containers
        for workspace_id in list(self._workspace_containers.keys()):
            try:
                await self.stop(workspace_id)
            except Exception as e:
                logger.warning(f"Error stopping workspace {workspace_id}: {e}")

        self._initialized = False
        logger.info("Docker runner shutdown complete")

    def get_capabilities(self) -> RunnerCapabilities:
        """Get Docker runner capabilities."""
        return RunnerCapabilities(
            supports_docker=True,
            supports_port_mapping=True,
            supports_resource_limits=True,
            supports_network_isolation=True,
            max_concurrent_workspaces=20,
            supported_runtimes=list(RuntimeType),
        )

    async def create_workspace_container(
        self,
        workspace: Workspace,
    ) -> None:
        """Create a Docker container for a workspace."""
        if not self._initialized:
            await self.initialize()

        # Get the image for this runtime
        runtime_str = workspace.runtime.value
        image = self._settings.docker.images.get(runtime_str)
        if not image:
            raise ValueError(f"No image configured for runtime: {runtime_str}")

        # Pull image if needed
        try:
            self._client.images.get(image)
        except Exception:  # docker.errors.ImageNotFound (imported dynamically)
            logger.info("Pulling image: %s", image)
            self._client.images.pull(image)

        # Container configuration
        container_name = f"ag3ntwerk-workbench-{workspace.id[:12]}"
        workdir = self._settings.docker.container_workdir

        # Security configuration
        security_opts = []
        if self._settings.security.drop_capabilities:
            security_opts.append("no-new-privileges:true")

        # Host config with resource limits
        host_config = {
            "binds": {
                workspace.path: {
                    "bind": workdir,
                    "mode": "rw",
                }
            },
            "network_mode": self._settings.docker.network_name,
            "auto_remove": False,
            "mem_limit": self._settings.resources.memory_limit,
            "pids_limit": self._settings.security.pids_limit,
            "security_opt": security_opts,
            "privileged": False,
        }

        # CPU limits (docker-py uses nano_cpus which is CPU * 1e9)
        cpu_quota = self._settings.resources.cpu_quota
        if cpu_quota > 0:
            host_config["nano_cpus"] = int(cpu_quota * 1e9)

        # Read-only root filesystem (if enabled)
        if self._settings.security.read_only_rootfs:
            host_config["read_only"] = True

        try:
            container = self._client.containers.create(
                image=image,
                name=container_name,
                command=self._settings.docker.default_command,
                working_dir=workdir,
                user=self._settings.security.container_user,
                hostname=f"ws-{workspace.id[:8]}",
                detach=True,
                stdin_open=True,
                tty=True,
                **host_config,
            )

            self._workspace_containers[workspace.id] = container.id
            logger.info(f"Created container {container.id[:12]} for workspace {workspace.id}")

        except Exception as e:
            logger.error(f"Failed to create container for workspace {workspace.id}: {e}")
            raise RuntimeError(f"Container creation failed: {e}")

    async def start(self, workspace_id: str) -> None:
        """Start a workspace's container."""
        container_id = self._workspace_containers.get(workspace_id)
        if not container_id:
            raise ValueError(f"No container found for workspace: {workspace_id}")

        try:
            container = self._client.containers.get(container_id)
            container.start()
            logger.info(f"Started container {container_id[:12]} for workspace {workspace_id}")
        except Exception as e:
            logger.error(f"Failed to start container for workspace {workspace_id}: {e}")
            raise RuntimeError(f"Container start failed: {e}")

    async def stop(self, workspace_id: str) -> None:
        """Stop a workspace's container."""
        container_id = self._workspace_containers.get(workspace_id)
        if not container_id:
            raise ValueError(f"No container found for workspace: {workspace_id}")

        try:
            container = self._client.containers.get(container_id)
            container.stop(timeout=10)
            logger.info(f"Stopped container {container_id[:12]} for workspace {workspace_id}")
        except Exception as e:
            logger.error(f"Failed to stop container for workspace {workspace_id}: {e}")
            raise RuntimeError(f"Container stop failed: {e}")

    async def remove(self, workspace_id: str) -> None:
        """Remove a workspace's container."""
        container_id = self._workspace_containers.get(workspace_id)
        if not container_id:
            return  # Already removed

        try:
            container = self._client.containers.get(container_id)
            container.remove(force=True)
            del self._workspace_containers[workspace_id]
            logger.info(f"Removed container {container_id[:12]} for workspace {workspace_id}")
        except Exception as e:
            logger.warning(f"Error removing container for workspace {workspace_id}: {e}")
            # Still remove from tracking
            self._workspace_containers.pop(workspace_id, None)

        # Clean up port allocations
        if workspace_id in self._exposed_ports:
            for port_info in self._exposed_ports[workspace_id]:
                self._allocated_ports.pop(port_info.host_port, None)
            del self._exposed_ports[workspace_id]

    async def exec(
        self,
        workspace_id: str,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """Execute a command asynchronously and return run_id."""
        run_id = str(uuid.uuid4())

        # Create initial run result
        run_result = RunResult(
            run_id=run_id,
            workspace_id=workspace_id,
            cmd=cmd,
            status=RunStatus.PENDING,
            started_at=datetime.now(timezone.utc),
        )
        self._runs[run_id] = run_result
        self._total_runs += 1

        # Start async execution
        asyncio.create_task(
            self._execute_in_background(
                run_id=run_id,
                workspace_id=workspace_id,
                cmd=cmd,
                env=env,
                cwd=cwd,
                timeout=timeout,
            )
        )

        return run_id

    async def _execute_in_background(
        self,
        run_id: str,
        workspace_id: str,
        cmd: List[str],
        env: Optional[Dict[str, str]],
        cwd: Optional[str],
        timeout: Optional[int],
    ) -> None:
        """Execute command in background and update result."""
        run_result = self._runs[run_id]
        run_result.status = RunStatus.RUNNING

        try:
            result = await self.exec_sync(
                workspace_id=workspace_id,
                cmd=cmd,
                env=env,
                cwd=cwd,
                timeout=timeout,
            )

            # Update the stored result
            run_result.status = result.status
            run_result.exit_code = result.exit_code
            run_result.stdout = result.stdout
            run_result.stderr = result.stderr
            run_result.ended_at = result.ended_at
            run_result.duration_seconds = result.duration_seconds

        except Exception as e:
            run_result.status = RunStatus.FAILED
            run_result.stderr = str(e)
            run_result.ended_at = datetime.now(timezone.utc)
            run_result.duration_seconds = (
                run_result.ended_at - run_result.started_at
            ).total_seconds()

    async def exec_sync(
        self,
        workspace_id: str,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> RunResult:
        """Execute a command synchronously and wait for completion."""
        container_id = self._workspace_containers.get(workspace_id)
        if not container_id:
            raise ValueError(f"No container found for workspace: {workspace_id}")

        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        try:
            container = self._client.containers.get(container_id)

            # Check container is running
            container.reload()
            if container.status != "running":
                raise RuntimeError(f"Container is not running: {container.status}")

            # Build working directory
            workdir = self._settings.docker.container_workdir
            if cwd:
                workdir = f"{workdir}/{cwd}"

            # Execute command
            exec_result = container.exec_run(
                cmd=cmd,
                workdir=workdir,
                environment=env,
                demux=True,  # Separate stdout/stderr
            )

            exit_code = exec_result.exit_code
            stdout_bytes, stderr_bytes = exec_result.output

            ended_at = datetime.now(timezone.utc)

            return RunResult(
                run_id=run_id,
                workspace_id=workspace_id,
                cmd=cmd,
                status=RunStatus.COMPLETED if exit_code == 0 else RunStatus.FAILED,
                exit_code=exit_code,
                stdout=stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else "",
                stderr=stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else "",
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=(ended_at - started_at).total_seconds(),
            )

        except Exception as e:
            ended_at = datetime.now(timezone.utc)
            return RunResult(
                run_id=run_id,
                workspace_id=workspace_id,
                cmd=cmd,
                status=RunStatus.FAILED,
                stderr=str(e),
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=(ended_at - started_at).total_seconds(),
            )

    async def get_run_result(self, run_id: str) -> Optional[RunResult]:
        """Get the result of a command execution."""
        return self._runs.get(run_id)

    async def get_logs(
        self,
        run_id: str,
        stdout: bool = True,
        stderr: bool = True,
    ) -> str:
        """Get logs from a command execution."""
        run_result = self._runs.get(run_id)
        if not run_result:
            raise ValueError(f"Run not found: {run_id}")

        logs = []
        if stdout and run_result.stdout:
            logs.append(run_result.stdout)
        if stderr and run_result.stderr:
            logs.append(run_result.stderr)

        return "\n".join(logs)

    async def expose_port(
        self,
        workspace_id: str,
        port: int,
        proto: str = "http",
        label: Optional[str] = None,
    ) -> PortExposeResult:
        """Expose a port from a workspace's container."""
        container_id = self._workspace_containers.get(workspace_id)
        if not container_id:
            raise ValueError(f"No container found for workspace: {workspace_id}")

        # Allocate a host port
        host_port = self._allocate_port(workspace_id)

        # Docker port mapping requires container recreation, so for MVP
        # we'll use a simple proxy approach or rely on the network being accessible
        # For a more complete implementation, we'd use iptables or a reverse proxy

        result = PortExposeResult(
            workspace_id=workspace_id,
            port=port,
            host_port=host_port,
            proto=PortProtocol(proto),
            preview_url=self._settings.get_preview_url(workspace_id, port, host_port),
            label=label,
        )

        # Track exposed port
        if workspace_id not in self._exposed_ports:
            self._exposed_ports[workspace_id] = []
        self._exposed_ports[workspace_id].append(result)

        logger.info(f"Exposed port {port} for workspace {workspace_id} on host port {host_port}")
        return result

    def _allocate_port(self, workspace_id: str) -> int:
        """Allocate a host port for a workspace."""
        start = self._settings.preview_port_start
        end = self._settings.preview_port_end

        for port in range(start, end):
            if port not in self._allocated_ports:
                self._allocated_ports[port] = workspace_id
                return port

        raise RuntimeError("No available ports for preview")

    async def list_exposed_ports(
        self,
        workspace_id: str,
    ) -> List[PortExposeResult]:
        """List all exposed ports for a workspace."""
        return self._exposed_ports.get(workspace_id, [])

    async def get_container_status(
        self,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Get detailed status of a workspace's container."""
        container_id = self._workspace_containers.get(workspace_id)
        if not container_id:
            return {
                "running": False,
                "state": "not_found",
                "started_at": None,
                "cpu_usage": None,
                "memory_usage": None,
            }

        try:
            container = self._client.containers.get(container_id)
            container.reload()

            # Get basic stats
            stats = {
                "running": container.status == "running",
                "state": container.status,
                "started_at": container.attrs.get("State", {}).get("StartedAt"),
            }

            # Try to get resource usage
            if container.status == "running":
                try:
                    usage = container.stats(stream=False)
                    # Calculate CPU percentage
                    cpu_delta = (
                        usage["cpu_stats"]["cpu_usage"]["total_usage"]
                        - usage["precpu_stats"]["cpu_usage"]["total_usage"]
                    )
                    system_delta = (
                        usage["cpu_stats"]["system_cpu_usage"]
                        - usage["precpu_stats"]["system_cpu_usage"]
                    )
                    if system_delta > 0:
                        stats["cpu_usage"] = (cpu_delta / system_delta) * 100

                    # Memory usage
                    mem_usage = usage["memory_stats"].get("usage", 0)
                    mem_limit = usage["memory_stats"].get("limit", 1)
                    stats["memory_usage"] = f"{mem_usage / (1024*1024):.1f}MB"
                    stats["memory_percent"] = (mem_usage / mem_limit) * 100
                except Exception as e:
                    logger.debug(
                        "Failed to parse container resource stats for %s: %s", workspace_id, e
                    )

            return stats

        except Exception as e:
            logger.warning(f"Error getting container status for {workspace_id}: {e}")
            return {
                "running": False,
                "state": "error",
                "error": str(e),
            }

    async def is_healthy(self) -> bool:
        """Check if Docker is accessible."""
        if not self._initialized:
            return False

        try:
            self._client.ping()
            return True
        except Exception as e:
            logger.debug("Docker health check failed: %s", e)
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the runner."""
        running_count = 0
        for workspace_id, container_id in self._workspace_containers.items():
            try:
                container = self._client.containers.get(container_id)
                container.reload()
                if container.status == "running":
                    running_count += 1
            except Exception as e:
                logger.debug(
                    "Failed to check container status for workspace %s: %s", workspace_id, e
                )

        # Count available images
        images_available = []
        for runtime, image in self._settings.docker.images.items():
            try:
                self._client.images.get(image)
                images_available.append(runtime)
            except Exception as e:
                logger.debug(
                    "Docker image '%s' for runtime '%s' not available: %s", image, runtime, e
                )

        return {
            "total_containers": len(self._workspace_containers),
            "running_containers": running_count,
            "total_runs": self._total_runs,
            "active_runs": sum(1 for r in self._runs.values() if r.status == RunStatus.RUNNING),
            "exposed_ports": sum(len(ports) for ports in self._exposed_ports.values()),
            "allocated_ports": len(self._allocated_ports),
            "images_available": images_available,
            "network": self._settings.docker.network_name,
        }
