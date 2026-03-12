"""
Docker Integration for ag3ntwerk.

Provides container management and orchestration.

Requirements:
    - pip install docker

Docker is ideal for:
    - Application deployment
    - Development environments
    - Service orchestration
    - CI/CD pipelines
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class DockerConfig:
    """Configuration for Docker integration."""

    base_url: str = "unix://var/run/docker.sock"  # or tcp://host:port
    timeout: int = 60
    tls: bool = False
    tls_verify: bool = True


@dataclass
class Container:
    """Represents a Docker container."""

    id: str
    name: str
    image: str
    status: str
    state: str = ""
    ports: Dict[str, Any] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)
    created: Optional[datetime] = None
    started_at: Optional[datetime] = None
    networks: List[str] = field(default_factory=list)
    mounts: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class Image:
    """Represents a Docker image."""

    id: str
    tags: List[str] = field(default_factory=list)
    size: int = 0
    created: Optional[datetime] = None
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Network:
    """Represents a Docker network."""

    id: str
    name: str
    driver: str = "bridge"
    scope: str = "local"
    containers: List[str] = field(default_factory=list)


@dataclass
class Volume:
    """Represents a Docker volume."""

    name: str
    driver: str = "local"
    mountpoint: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    created: Optional[datetime] = None


class DockerIntegration:
    """
    Integration with Docker for container management.

    Provides container, image, network, and volume operations.

    Example:
        integration = DockerIntegration()

        # List containers
        containers = await integration.list_containers()

        # Run a container
        container = await integration.run_container(
            image="nginx:latest",
            name="web-server",
            ports={"80/tcp": 8080},
        )

        # Get logs
        logs = await integration.get_logs(container.id)
    """

    def __init__(self, config: Optional[DockerConfig] = None):
        """Initialize Docker integration."""
        self.config = config or DockerConfig()
        self._client = None

    def _get_client(self):
        """Get Docker client."""
        if self._client is None:
            try:
                import docker

                self._client = docker.from_env()
            except ImportError:
                raise ImportError("docker not installed. Install with: pip install docker")
        return self._client

    # Container Operations

    async def list_containers(
        self,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Container]:
        """
        List containers.

        Args:
            all: Include stopped containers
            filters: Filter dict

        Returns:
            List of Containers
        """
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _list():
            containers = client.containers.list(all=all, filters=filters)
            return [
                Container(
                    id=c.id[:12],
                    name=c.name,
                    image=c.image.tags[0] if c.image.tags else c.image.id[:12],
                    status=c.status,
                    state=c.attrs.get("State", {}).get("Status", ""),
                    ports=c.ports,
                    labels=c.labels,
                    created=datetime.fromisoformat(c.attrs["Created"].replace("Z", "+00:00")),
                    networks=list(c.attrs.get("NetworkSettings", {}).get("Networks", {}).keys()),
                )
                for c in containers
            ]

        return await loop.run_in_executor(None, _list)

    async def get_container(self, container_id: str) -> Container:
        """Get a specific container."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _get():
            c = client.containers.get(container_id)
            return Container(
                id=c.id[:12],
                name=c.name,
                image=c.image.tags[0] if c.image.tags else c.image.id[:12],
                status=c.status,
                state=c.attrs.get("State", {}).get("Status", ""),
                ports=c.ports,
                labels=c.labels,
                created=datetime.fromisoformat(c.attrs["Created"].replace("Z", "+00:00")),
                networks=list(c.attrs.get("NetworkSettings", {}).get("Networks", {}).keys()),
            )

        return await loop.run_in_executor(None, _get)

    async def run_container(
        self,
        image: str,
        name: Optional[str] = None,
        command: Optional[Union[str, List[str]]] = None,
        ports: Optional[Dict[str, int]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        environment: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        network: Optional[str] = None,
        detach: bool = True,
        remove: bool = False,
        restart_policy: Optional[Dict[str, Any]] = None,
    ) -> Container:
        """
        Run a new container.

        Args:
            image: Image name/tag
            name: Container name
            command: Command to run
            ports: Port mappings {container_port: host_port}
            volumes: Volume mounts {host_path: {"bind": container_path, "mode": "rw"}}
            environment: Environment variables
            labels: Container labels
            network: Network to connect to
            detach: Run in background
            remove: Remove when stopped
            restart_policy: Restart policy config

        Returns:
            Created Container
        """
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _run():
            container = client.containers.run(
                image,
                command=command,
                name=name,
                ports=ports,
                volumes=volumes,
                environment=environment,
                labels=labels,
                network=network,
                detach=detach,
                remove=remove,
                restart_policy=restart_policy,
            )

            if detach:
                return Container(
                    id=container.id[:12],
                    name=container.name,
                    image=image,
                    status=container.status,
                    ports=container.ports,
                    labels=container.labels,
                )
            else:
                return Container(
                    id="",
                    name=name or "",
                    image=image,
                    status="exited",
                )

        return await loop.run_in_executor(None, _run)

    async def stop_container(
        self,
        container_id: str,
        timeout: int = 10,
    ) -> bool:
        """Stop a container."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _stop():
            container = client.containers.get(container_id)
            container.stop(timeout=timeout)
            return True

        return await loop.run_in_executor(None, _stop)

    async def start_container(self, container_id: str) -> bool:
        """Start a stopped container."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _start():
            container = client.containers.get(container_id)
            container.start()
            return True

        return await loop.run_in_executor(None, _start)

    async def restart_container(
        self,
        container_id: str,
        timeout: int = 10,
    ) -> bool:
        """Restart a container."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _restart():
            container = client.containers.get(container_id)
            container.restart(timeout=timeout)
            return True

        return await loop.run_in_executor(None, _restart)

    async def remove_container(
        self,
        container_id: str,
        force: bool = False,
        volumes: bool = False,
    ) -> bool:
        """Remove a container."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _remove():
            container = client.containers.get(container_id)
            container.remove(force=force, v=volumes)
            return True

        return await loop.run_in_executor(None, _remove)

    async def get_logs(
        self,
        container_id: str,
        tail: int = 100,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        timestamps: bool = False,
    ) -> str:
        """
        Get container logs.

        Args:
            container_id: Container ID
            tail: Number of lines from end
            since: Start time
            until: End time
            timestamps: Include timestamps

        Returns:
            Log output as string
        """
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _logs():
            container = client.containers.get(container_id)
            logs = container.logs(
                tail=tail,
                since=since,
                until=until,
                timestamps=timestamps,
            )
            return logs.decode("utf-8")

        return await loop.run_in_executor(None, _logs)

    async def exec_command(
        self,
        container_id: str,
        command: Union[str, List[str]],
        workdir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
    ) -> tuple:
        """
        Execute a command in a running container.

        Args:
            container_id: Container ID
            command: Command to execute
            workdir: Working directory
            environment: Environment variables

        Returns:
            Tuple of (exit_code, output)
        """
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _exec():
            container = client.containers.get(container_id)
            exit_code, output = container.exec_run(
                command,
                workdir=workdir,
                environment=environment,
            )
            return exit_code, output.decode("utf-8")

        return await loop.run_in_executor(None, _exec)

    async def get_stats(self, container_id: str) -> Dict[str, Any]:
        """Get container resource stats."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _stats():
            container = client.containers.get(container_id)
            stats = container.stats(stream=False)

            # Calculate CPU percentage
            cpu_delta = (
                stats["cpu_stats"]["cpu_usage"]["total_usage"]
                - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            )
            system_delta = (
                stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
            )
            cpu_percent = (cpu_delta / system_delta) * 100 if system_delta > 0 else 0

            # Memory
            mem_usage = stats["memory_stats"].get("usage", 0)
            mem_limit = stats["memory_stats"].get("limit", 1)
            mem_percent = (mem_usage / mem_limit) * 100

            return {
                "cpu_percent": round(cpu_percent, 2),
                "memory_usage": mem_usage,
                "memory_limit": mem_limit,
                "memory_percent": round(mem_percent, 2),
                "network_rx": stats.get("networks", {}).get("eth0", {}).get("rx_bytes", 0),
                "network_tx": stats.get("networks", {}).get("eth0", {}).get("tx_bytes", 0),
            }

        return await loop.run_in_executor(None, _stats)

    # Image Operations

    async def list_images(
        self,
        name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Image]:
        """List images."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _list():
            images = client.images.list(name=name, filters=filters)
            return [
                Image(
                    id=img.id[:12],
                    tags=img.tags,
                    size=img.attrs.get("Size", 0),
                    created=datetime.fromisoformat(img.attrs["Created"].replace("Z", "+00:00")),
                    labels=img.labels or {},
                )
                for img in images
            ]

        return await loop.run_in_executor(None, _list)

    async def pull_image(
        self,
        repository: str,
        tag: str = "latest",
    ) -> Image:
        """Pull an image from a registry."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _pull():
            image = client.images.pull(repository, tag=tag)
            return Image(
                id=image.id[:12],
                tags=image.tags,
                size=image.attrs.get("Size", 0),
            )

        return await loop.run_in_executor(None, _pull)

    async def build_image(
        self,
        path: str,
        tag: str,
        dockerfile: str = "Dockerfile",
        buildargs: Optional[Dict[str, str]] = None,
        nocache: bool = False,
    ) -> Image:
        """
        Build an image from a Dockerfile.

        Args:
            path: Build context path
            tag: Image tag
            dockerfile: Dockerfile name
            buildargs: Build arguments
            nocache: Disable cache

        Returns:
            Built Image
        """
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _build():
            image, logs = client.images.build(
                path=path,
                tag=tag,
                dockerfile=dockerfile,
                buildargs=buildargs,
                nocache=nocache,
            )
            return Image(
                id=image.id[:12],
                tags=image.tags,
                size=image.attrs.get("Size", 0),
            )

        return await loop.run_in_executor(None, _build)

    async def remove_image(
        self,
        image: str,
        force: bool = False,
    ) -> bool:
        """Remove an image."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _remove():
            client.images.remove(image, force=force)
            return True

        return await loop.run_in_executor(None, _remove)

    # Network Operations

    async def list_networks(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Network]:
        """List networks."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _list():
            networks = client.networks.list(filters=filters)
            return [
                Network(
                    id=net.id[:12],
                    name=net.name,
                    driver=net.attrs.get("Driver", ""),
                    scope=net.attrs.get("Scope", ""),
                    containers=list(net.attrs.get("Containers", {}).keys()),
                )
                for net in networks
            ]

        return await loop.run_in_executor(None, _list)

    async def create_network(
        self,
        name: str,
        driver: str = "bridge",
        labels: Optional[Dict[str, str]] = None,
    ) -> Network:
        """Create a network."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _create():
            network = client.networks.create(
                name=name,
                driver=driver,
                labels=labels,
            )
            return Network(
                id=network.id[:12],
                name=network.name,
                driver=driver,
            )

        return await loop.run_in_executor(None, _create)

    async def remove_network(self, network_id: str) -> bool:
        """Remove a network."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _remove():
            network = client.networks.get(network_id)
            network.remove()
            return True

        return await loop.run_in_executor(None, _remove)

    # Volume Operations

    async def list_volumes(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Volume]:
        """List volumes."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _list():
            volumes = client.volumes.list(filters=filters)
            return [
                Volume(
                    name=vol.name,
                    driver=vol.attrs.get("Driver", ""),
                    mountpoint=vol.attrs.get("Mountpoint", ""),
                    labels=vol.attrs.get("Labels", {}) or {},
                )
                for vol in volumes
            ]

        return await loop.run_in_executor(None, _list)

    async def create_volume(
        self,
        name: str,
        driver: str = "local",
        labels: Optional[Dict[str, str]] = None,
    ) -> Volume:
        """Create a volume."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _create():
            volume = client.volumes.create(
                name=name,
                driver=driver,
                labels=labels,
            )
            return Volume(
                name=volume.name,
                driver=driver,
                mountpoint=volume.attrs.get("Mountpoint", ""),
            )

        return await loop.run_in_executor(None, _create)

    async def remove_volume(self, volume_name: str, force: bool = False) -> bool:
        """Remove a volume."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _remove():
            volume = client.volumes.get(volume_name)
            volume.remove(force=force)
            return True

        return await loop.run_in_executor(None, _remove)

    # System Operations

    async def system_info(self) -> Dict[str, Any]:
        """Get Docker system information."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _info():
            return client.info()

        return await loop.run_in_executor(None, _info)

    async def disk_usage(self) -> Dict[str, Any]:
        """Get Docker disk usage."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _usage():
            return client.df()

        return await loop.run_in_executor(None, _usage)

    async def prune_system(
        self,
        containers: bool = True,
        images: bool = True,
        networks: bool = True,
        volumes: bool = False,
    ) -> Dict[str, Any]:
        """
        Prune unused Docker objects.

        Args:
            containers: Prune containers
            images: Prune images
            networks: Prune networks
            volumes: Prune volumes (dangerous!)

        Returns:
            Prune results
        """
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _prune():
            results = {}
            if containers:
                results["containers"] = client.containers.prune()
            if images:
                results["images"] = client.images.prune()
            if networks:
                results["networks"] = client.networks.prune()
            if volumes:
                results["volumes"] = client.volumes.prune()
            return results

        return await loop.run_in_executor(None, _prune)
