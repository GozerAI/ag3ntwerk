"""
Workbench Module Settings - Configuration management.

Provides configuration for the workbench module with environment variable support.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ag3ntwerk.modules.workbench.schemas import IDEMode


@dataclass
class SecuritySettings:
    """Security-related settings."""

    localhost_only: bool = True
    """Bind services to 127.0.0.1 only."""

    auth_token: Optional[str] = None
    """Bearer token for API authentication."""

    container_user: str = "runner"
    """Non-root user to run containers as."""

    drop_capabilities: bool = True
    """Drop Linux capabilities in containers."""

    disable_privileged: bool = True
    """Disable privileged mode in containers."""

    read_only_rootfs: bool = False
    """Mount container root filesystem as read-only."""

    pids_limit: int = 256
    """Maximum number of PIDs per container."""


@dataclass
class ResourceLimits:
    """Container resource limits."""

    cpu_quota: float = 2.0
    """CPU quota (cores)."""

    memory_limit: str = "2g"
    """Memory limit (e.g., '2g', '512m')."""

    storage_limit: str = "10g"
    """Disk storage limit per workspace."""


@dataclass
class IDESettings:
    """IDE integration settings."""

    mode: IDEMode = IDEMode.CODESERVER_SINGLE
    """IDE mode - single instance or per-workspace."""

    codeserver_image: str = "codercom/code-server:latest"
    """Docker image for code-server."""

    codeserver_port: int = 8080
    """Port code-server listens on inside container."""

    host_port_start: int = 9000
    """Starting port for host port allocation."""

    host_port_end: int = 9100
    """Ending port for host port allocation."""


@dataclass
class DockerSettings:
    """Docker-specific settings."""

    network_name: str = "ag3ntwerk_workbench_net"
    """Docker network name for workbench containers."""

    image_prefix: str = "ag3ntwerk-workbench"
    """Prefix for workbench Docker images."""

    images: dict = field(
        default_factory=lambda: {
            "python": "python:3.11-slim",
            "node": "node:20-slim",
            "go": "golang:1.22-alpine",
            "rust": "rust:1.77-slim",
        }
    )
    """Runtime images by type."""

    container_workdir: str = "/workspace"
    """Working directory inside containers."""

    default_command: list = field(default_factory=lambda: ["sleep", "infinity"])
    """Default command to keep containers running."""


@dataclass
class WorkbenchSettings:
    """
    Main settings for the workbench module.

    Settings can be configured via:
    1. Environment variables (AGENTWERK_WORKBENCH_*)
    2. config.yaml under workbench section
    3. Direct instantiation with parameters
    """

    enabled: bool = True
    """Whether the workbench module is enabled."""

    root_dir: str = ""
    """Root directory for workspace storage. Defaults to data/workspaces."""

    runner_type: str = "docker"
    """Runner type (docker, fake)."""

    security: SecuritySettings = field(default_factory=SecuritySettings)
    """Security settings."""

    resources: ResourceLimits = field(default_factory=ResourceLimits)
    """Resource limit settings."""

    ide: IDESettings = field(default_factory=IDESettings)
    """IDE settings."""

    docker: DockerSettings = field(default_factory=DockerSettings)
    """Docker-specific settings."""

    preview_host: str = "localhost"
    """Host for preview URLs."""

    preview_port_start: int = 8100
    """Starting port for preview port allocation."""

    preview_port_end: int = 8200
    """Ending port for preview port allocation."""

    @classmethod
    def from_env(cls) -> "WorkbenchSettings":
        """
        Create settings from environment variables.

        Environment variables:
        - AGENTWERK_WORKBENCH_ENABLED: Enable/disable module (true/false)
        - AGENTWERK_WORKBENCH_ROOT: Root directory for workspaces
        - AGENTWERK_WORKBENCH_RUNNER: Runner type (docker/fake)
        - AGENTWERK_WORKBENCH_AUTH_TOKEN: Bearer token for auth
        - AGENTWERK_WORKBENCH_LOCALHOST_ONLY: Bind to localhost only (true/false)
        - AGENTWERK_WORKBENCH_IDE_MODE: IDE mode (codeserver_single/codeserver_per_workspace)
        - AGENTWERK_WORKBENCH_CPU_LIMIT: CPU limit in cores
        - AGENTWERK_WORKBENCH_MEMORY_LIMIT: Memory limit (e.g., '4g')
        """
        settings = cls()

        # Basic settings
        if enabled := os.getenv("AGENTWERK_WORKBENCH_ENABLED"):
            settings.enabled = enabled.lower() in ("true", "1", "yes")

        if root_dir := os.getenv("AGENTWERK_WORKBENCH_ROOT"):
            settings.root_dir = root_dir

        if runner := os.getenv("AGENTWERK_WORKBENCH_RUNNER"):
            settings.runner_type = runner

        # Security settings
        if auth_token := os.getenv("AGENTWERK_WORKBENCH_AUTH_TOKEN"):
            settings.security.auth_token = auth_token

        if localhost := os.getenv("AGENTWERK_WORKBENCH_LOCALHOST_ONLY"):
            settings.security.localhost_only = localhost.lower() in ("true", "1", "yes")

        # IDE settings
        if ide_mode := os.getenv("AGENTWERK_WORKBENCH_IDE_MODE"):
            try:
                settings.ide.mode = IDEMode(ide_mode)
            except ValueError:
                pass

        # Resource limits
        if cpu := os.getenv("AGENTWERK_WORKBENCH_CPU_LIMIT"):
            try:
                settings.resources.cpu_quota = float(cpu)
            except ValueError:
                pass

        if memory := os.getenv("AGENTWERK_WORKBENCH_MEMORY_LIMIT"):
            settings.resources.memory_limit = memory

        return settings

    def get_root_path(self) -> Path:
        """Get the root path for workspace storage."""
        if self.root_dir:
            return Path(self.root_dir)
        # Default to data/workspaces relative to project
        return Path("data") / "workspaces"

    def get_workspace_path(self, workspace_id: str) -> Path:
        """Get the path for a specific workspace."""
        return self.get_root_path() / workspace_id

    def get_preview_url(self, workspace_id: str, port: int, host_port: int) -> str:
        """Generate a preview URL for an exposed port."""
        host = self.preview_host
        if self.security.localhost_only:
            host = "localhost"
        return f"http://{host}:{host_port}/preview/{workspace_id}/{port}/"

    def get_ide_url(self, workspace_id: str, host_port: int) -> str:
        """Generate an IDE URL for a workspace."""
        host = self.preview_host
        if self.security.localhost_only:
            host = "localhost"
        return f"http://{host}:{host_port}/?folder=/workspace"

    def validate(self) -> list:
        """
        Validate settings and return list of errors.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        # Check root directory
        root_path = self.get_root_path()
        if root_path.exists() and not root_path.is_dir():
            errors.append(f"Root path exists but is not a directory: {root_path}")

        # Check port ranges
        if self.preview_port_start >= self.preview_port_end:
            errors.append("preview_port_start must be less than preview_port_end")

        if self.ide.host_port_start >= self.ide.host_port_end:
            errors.append("ide.host_port_start must be less than ide.host_port_end")

        # Check resource limits
        if self.resources.cpu_quota <= 0:
            errors.append("resources.cpu_quota must be positive")

        if self.security.pids_limit < 10:
            errors.append("security.pids_limit must be at least 10")

        return errors


# Global settings instance
_settings: Optional[WorkbenchSettings] = None


def get_workbench_settings() -> WorkbenchSettings:
    """Get or create the global workbench settings instance."""
    global _settings
    if _settings is None:
        _settings = WorkbenchSettings.from_env()
    return _settings


def configure_workbench_settings(settings: WorkbenchSettings) -> None:
    """Configure the global workbench settings instance."""
    global _settings
    _settings = settings
