"""
IDE Container Manager - Code-server container lifecycle management.

Manages code-server containers for browser-based IDE access to workspaces.
"""

import asyncio
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING

from ag3ntwerk.modules.workbench.schemas import IDEMode, IDEInfo
from ag3ntwerk.modules.workbench.utils.ports import PortAllocator

if TYPE_CHECKING:
    from ag3ntwerk.modules.workbench.settings import WorkbenchSettings

logger = logging.getLogger(__name__)


class IDEStatus:
    """IDE container status information."""

    def __init__(
        self,
        workspace_id: str,
        running: bool = False,
        container_id: Optional[str] = None,
        ide_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        started_at: Optional[datetime] = None,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[str] = None,
    ):
        self.workspace_id = workspace_id
        self.running = running
        self.container_id = container_id
        self.ide_url = ide_url
        self.auth_token = auth_token
        self.started_at = started_at
        self.cpu_usage = cpu_usage
        self.memory_usage = memory_usage

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "workspace_id": self.workspace_id,
            "running": self.running,
            "container_id": self.container_id,
            "ide_url": self.ide_url,
            "auth_token": self.auth_token,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
        }


class IDEContainerManager:
    """
    Manages code-server containers for browser IDE access.

    Supports two modes:
    - CODESERVER_SINGLE: One code-server for all workspaces (shared)
    - CODESERVER_PER_WORKSPACE: Dedicated code-server per workspace

    Example:
        ```python
        manager = IDEContainerManager(settings, docker_client, port_allocator)
        ide_info = await manager.start_ide("ws-123", "/path/to/workspace")
        # User can now access IDE at ide_info.ide_url
        await manager.stop_ide("ws-123")
        ```
    """

    def __init__(
        self,
        settings: "WorkbenchSettings",
        docker_client: Any = None,
        port_allocator: Optional[PortAllocator] = None,
    ):
        """
        Initialize the IDE container manager.

        Args:
            settings: Workbench settings
            docker_client: Docker client (optional, will create if not provided)
            port_allocator: Port allocator for IDE ports
        """
        self._settings = settings
        self._docker = docker_client
        self._ports = port_allocator or PortAllocator(
            start_port=settings.ide.host_port_start,
            end_port=settings.ide.host_port_end,
        )

        # Track IDE containers: workspace_id -> container_id
        self._ide_containers: Dict[str, str] = {}

        # Track auth tokens: workspace_id -> token
        self._auth_tokens: Dict[str, str] = {}

        # Track start times: workspace_id -> datetime
        self._start_times: Dict[str, datetime] = {}

        # Track allocated ports: workspace_id -> host_port
        self._ide_ports: Dict[str, int] = {}

    async def _get_docker_client(self):
        """Get or create Docker client."""
        if self._docker is None:
            try:
                import docker

                self._docker = docker.from_env()
            except Exception as e:
                logger.error(f"Failed to create Docker client: {e}")
                raise RuntimeError("Docker not available") from e
        return self._docker

    async def start_ide(
        self,
        workspace_id: str,
        workspace_path: str,
        password: Optional[str] = None,
    ) -> IDEInfo:
        """
        Start code-server container for a workspace.

        Args:
            workspace_id: The workspace ID
            workspace_path: Host path to workspace directory
            password: Optional password (auto-generated if not provided)

        Returns:
            IDEInfo with URL and auth details
        """
        # Check if already running
        if workspace_id in self._ide_containers:
            existing_status = await self.get_ide_status(workspace_id)
            if existing_status.running:
                logger.info(f"IDE already running for workspace {workspace_id}")
                return IDEInfo(
                    workspace_id=workspace_id,
                    ide_url=existing_status.ide_url,
                    mode=self._settings.ide.mode,
                )

        # Generate auth token
        auth_token = password or secrets.token_urlsafe(16)
        self._auth_tokens[workspace_id] = auth_token

        # Allocate host port
        host_port = self._ports.allocate(f"ide-{workspace_id}")
        if not host_port:
            raise RuntimeError("No available ports for IDE")
        self._ide_ports[workspace_id] = host_port

        try:
            docker = await self._get_docker_client()

            # Build container configuration
            container_config = self._create_ide_container_config(
                workspace_id=workspace_id,
                workspace_path=workspace_path,
                host_port=host_port,
                auth_token=auth_token,
            )

            # Create and start container
            container = docker.containers.run(**container_config)
            container_id = container.id

            self._ide_containers[workspace_id] = container_id
            self._start_times[workspace_id] = datetime.now(timezone.utc)

            # Wait for code-server to be ready
            await self._wait_for_ready(workspace_id, host_port)

            # Build IDE URL
            ide_url = self._build_ide_url(workspace_id, host_port)

            logger.info(f"Started IDE for workspace {workspace_id} at {ide_url}")

            return IDEInfo(
                workspace_id=workspace_id,
                ide_url=ide_url,
                mode=self._settings.ide.mode,
            )

        except Exception as e:
            # Cleanup on failure
            self._ports.release_all(f"ide-{workspace_id}")
            self._ide_ports.pop(workspace_id, None)
            self._auth_tokens.pop(workspace_id, None)
            logger.error(f"Failed to start IDE for {workspace_id}: {e}")
            raise

    async def stop_ide(self, workspace_id: str) -> bool:
        """
        Stop and remove code-server container.

        Args:
            workspace_id: The workspace ID

        Returns:
            True if stopped successfully
        """
        container_id = self._ide_containers.get(workspace_id)
        if not container_id:
            logger.warning(f"No IDE container found for workspace {workspace_id}")
            return False

        try:
            docker = await self._get_docker_client()

            try:
                container = docker.containers.get(container_id)
                container.stop(timeout=10)
                container.remove(force=True)
            except Exception as e:
                logger.warning(f"Error stopping container {container_id}: {e}")

            # Cleanup tracking
            self._ide_containers.pop(workspace_id, None)
            self._auth_tokens.pop(workspace_id, None)
            self._start_times.pop(workspace_id, None)

            # Release port
            self._ports.release_all(f"ide-{workspace_id}")
            self._ide_ports.pop(workspace_id, None)

            logger.info(f"Stopped IDE for workspace {workspace_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop IDE for {workspace_id}: {e}")
            return False

    async def get_ide_status(self, workspace_id: str) -> IDEStatus:
        """
        Get IDE container status.

        Args:
            workspace_id: The workspace ID

        Returns:
            IDEStatus with container details
        """
        container_id = self._ide_containers.get(workspace_id)
        if not container_id:
            return IDEStatus(workspace_id=workspace_id, running=False)

        try:
            docker = await self._get_docker_client()
            container = docker.containers.get(container_id)

            running = container.status == "running"
            host_port = self._ide_ports.get(workspace_id)
            ide_url = self._build_ide_url(workspace_id, host_port) if host_port else None

            # Get resource usage if running
            cpu_usage = None
            memory_usage = None
            if running:
                try:
                    stats = container.stats(stream=False)
                    # Calculate CPU percentage
                    cpu_delta = (
                        stats["cpu_stats"]["cpu_usage"]["total_usage"]
                        - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                    )
                    system_delta = (
                        stats["cpu_stats"]["system_cpu_usage"]
                        - stats["precpu_stats"]["system_cpu_usage"]
                    )
                    if system_delta > 0:
                        cpu_usage = (cpu_delta / system_delta) * 100

                    # Memory usage
                    mem_usage = stats["memory_stats"].get("usage", 0)
                    mem_limit = stats["memory_stats"].get("limit", 1)
                    memory_usage = f"{mem_usage // (1024*1024)}MB / {mem_limit // (1024*1024)}MB"
                except Exception as e:
                    logger.debug("Failed to retrieve IDE container stats: %s", e)

            return IDEStatus(
                workspace_id=workspace_id,
                running=running,
                container_id=container_id,
                ide_url=ide_url,
                auth_token=self._auth_tokens.get(workspace_id),
                started_at=self._start_times.get(workspace_id),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
            )

        except Exception as e:
            logger.error(f"Failed to get IDE status for {workspace_id}: {e}")
            return IDEStatus(workspace_id=workspace_id, running=False)

    async def health_check(self, workspace_id: str) -> bool:
        """
        Check if code-server is healthy and responding.

        Args:
            workspace_id: The workspace ID

        Returns:
            True if IDE is healthy
        """
        host_port = self._ide_ports.get(workspace_id)
        if not host_port:
            return False

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                url = f"http://localhost:{host_port}/healthz"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.debug("IDE health check failed for workspace %s: %s", workspace_id, e)
            return False

    def get_auth_token(self, workspace_id: str) -> Optional[str]:
        """Get the auth token for a workspace's IDE."""
        return self._auth_tokens.get(workspace_id)

    def _create_ide_container_config(
        self,
        workspace_id: str,
        workspace_path: str,
        host_port: int,
        auth_token: str,
    ) -> Dict[str, Any]:
        """
        Create Docker container configuration for code-server.

        Args:
            workspace_id: Workspace ID
            workspace_path: Host path to workspace
            host_port: Host port to bind
            auth_token: Password for code-server

        Returns:
            Docker container configuration dict
        """
        ide_settings = self._settings.ide
        container_port = ide_settings.codeserver_port

        return {
            "image": ide_settings.codeserver_image,
            "name": f"ag3ntwerk-ide-{workspace_id[:12]}",
            "detach": True,
            "ports": {f"{container_port}/tcp": host_port},
            "volumes": {
                workspace_path: {
                    "bind": "/home/coder/workspace",
                    "mode": "rw",
                }
            },
            "environment": {
                "PASSWORD": auth_token,
                "DOCKER_USER": "coder",
            },
            "command": [
                "--auth",
                "password",
                "--bind-addr",
                f"0.0.0.0:{container_port}",
                "/home/coder/workspace",
            ],
            "network": self._settings.docker.network_name,
            "mem_limit": "1g",
            "restart_policy": {"Name": "unless-stopped"},
            "labels": {
                "ag3ntwerk.module": "workbench",
                "ag3ntwerk.component": "ide",
                "ag3ntwerk.workspace": workspace_id,
            },
        }

    def _build_ide_url(self, workspace_id: str, host_port: int) -> str:
        """Build the IDE access URL."""
        host = (
            "localhost" if self._settings.security.localhost_only else self._settings.preview_host
        )
        return f"http://{host}:{host_port}/?folder=/home/coder/workspace"

    async def _wait_for_ready(
        self,
        workspace_id: str,
        host_port: int,
        timeout: int = 30,
    ) -> bool:
        """
        Wait for code-server to be ready.

        Args:
            workspace_id: Workspace ID
            host_port: Host port
            timeout: Maximum wait time in seconds

        Returns:
            True if ready within timeout
        """
        start_time = datetime.now(timezone.utc)
        while (datetime.now(timezone.utc) - start_time).seconds < timeout:
            if await self.health_check(workspace_id):
                return True
            await asyncio.sleep(1)

        logger.warning(f"IDE startup timeout for workspace {workspace_id}")
        return False

    async def cleanup_orphaned_containers(self) -> int:
        """
        Clean up any orphaned IDE containers.

        Returns:
            Number of containers cleaned up
        """
        try:
            docker = await self._get_docker_client()
            containers = docker.containers.list(
                all=True,
                filters={"label": "ag3ntwerk.component=ide"},
            )

            cleaned = 0
            for container in containers:
                workspace_id = container.labels.get("ag3ntwerk.workspace")
                if workspace_id and workspace_id not in self._ide_containers:
                    logger.info(f"Cleaning up orphaned IDE container: {container.id}")
                    try:
                        container.stop(timeout=5)
                        container.remove(force=True)
                        cleaned += 1
                    except Exception as e:
                        logger.warning(f"Failed to clean up container {container.id}: {e}")

            return cleaned

        except Exception as e:
            logger.error(f"Failed to cleanup orphaned containers: {e}")
            return 0
