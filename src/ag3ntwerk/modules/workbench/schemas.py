"""
Workbench Module Schemas - Pydantic models for API contracts.

Defines all request/response models for the workbench API.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field, field_validator


class RuntimeType(str, Enum):
    """Supported runtime types for workspaces."""

    PYTHON = "python"
    NODE = "node"
    GO = "go"
    RUST = "rust"


class WorkspaceStatus(str, Enum):
    """Status of a workspace."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class RunStatus(str, Enum):
    """Status of a command run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class WorkspaceTemplate(str, Enum):
    """Available workspace templates."""

    EMPTY = "empty"
    PYTHON_BASIC = "python-basic"
    NODE_BASIC = "node-basic"
    GO_BASIC = "go-basic"
    RUST_BASIC = "rust-basic"


# =============================================================================
# Workspace Models
# =============================================================================


class WorkspaceCreate(BaseModel):
    """Request model for creating a workspace."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Name of the workspace",
        examples=["my-project"],
    )
    template: Optional[WorkspaceTemplate] = Field(
        default=WorkspaceTemplate.EMPTY,
        description="Template to initialize workspace with",
    )
    runtime: RuntimeType = Field(
        default=RuntimeType.PYTHON,
        description="Runtime environment for the workspace",
    )
    git_clone_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Git repository URL to clone into workspace",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate workspace name is safe for filesystem and Docker."""
        import re

        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "Workspace name must start with alphanumeric and contain "
                "only alphanumeric, underscore, or hyphen characters"
            )
        return v.lower()


class Workspace(BaseModel):
    """Workspace model representing a development environment."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique workspace identifier",
    )
    name: str = Field(
        ...,
        description="Workspace name",
    )
    path: str = Field(
        ...,
        description="Host path to workspace directory",
    )
    runtime: RuntimeType = Field(
        ...,
        description="Runtime environment",
    )
    status: WorkspaceStatus = Field(
        default=WorkspaceStatus.STOPPED,
        description="Current workspace status",
    )
    container_id: Optional[str] = Field(
        default=None,
        description="Docker container ID when running",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "runtime": self.runtime.value,
            "status": self.status.value,
            "container_id": self.container_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class WorkspaceUpdate(BaseModel):
    """Request model for updating workspace metadata."""

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata to merge with existing",
    )


# =============================================================================
# Run Models
# =============================================================================


class RunRequest(BaseModel):
    """Request model for running a command in a workspace."""

    workspace_id: str = Field(
        ...,
        description="ID of the workspace to run command in",
    )
    cmd: List[str] = Field(
        ...,
        min_length=1,
        description="Command as list of arguments (preferred over shell string)",
        examples=[["python", "-c", "print('hello')"]],
    )
    env: Optional[Dict[str, str]] = Field(
        default=None,
        description="Environment variables to set",
    )
    cwd: Optional[str] = Field(
        default=None,
        description="Working directory relative to workspace root",
    )
    timeout: Optional[int] = Field(
        default=300,
        ge=1,
        le=3600,
        description="Timeout in seconds (1-3600)",
    )

    @field_validator("cmd")
    @classmethod
    def validate_cmd(cls, v: List[str]) -> List[str]:
        """Validate command doesn't contain dangerous patterns."""
        dangerous_patterns = [
            "rm -rf /",
            "mkfs",
            ":(){:|:&};:",  # Fork bomb
            "> /dev/sd",
            "dd if=/dev/zero",
        ]
        cmd_str = " ".join(v)
        for pattern in dangerous_patterns:
            if pattern in cmd_str:
                raise ValueError(f"Dangerous command pattern detected: {pattern}")
        return v


class RunResult(BaseModel):
    """Result model for a command execution."""

    run_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique run identifier",
    )
    workspace_id: str = Field(
        ...,
        description="Workspace ID where command ran",
    )
    cmd: List[str] = Field(
        ...,
        description="Command that was executed",
    )
    status: RunStatus = Field(
        default=RunStatus.PENDING,
        description="Current run status",
    )
    exit_code: Optional[int] = Field(
        default=None,
        description="Exit code (None if still running)",
    )
    stdout: Optional[str] = Field(
        default=None,
        description="Standard output",
    )
    stderr: Optional[str] = Field(
        default=None,
        description="Standard error",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Start timestamp",
    )
    ended_at: Optional[datetime] = Field(
        default=None,
        description="End timestamp",
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Execution duration in seconds",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "cmd": self.cmd,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds": self.duration_seconds,
        }


# =============================================================================
# Port Exposure Models
# =============================================================================


class PortProtocol(str, Enum):
    """Protocol for port exposure."""

    HTTP = "http"
    TCP = "tcp"


class PortExposeRequest(BaseModel):
    """Request model for exposing a port from a workspace."""

    workspace_id: str = Field(
        ...,
        description="ID of the workspace",
    )
    port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="Port number to expose",
    )
    proto: PortProtocol = Field(
        default=PortProtocol.HTTP,
        description="Protocol (http or tcp)",
    )
    label: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional label for the port",
    )


class PortExposeResult(BaseModel):
    """Result model for an exposed port."""

    workspace_id: str = Field(
        ...,
        description="Workspace ID",
    )
    port: int = Field(
        ...,
        description="Exposed container port",
    )
    host_port: int = Field(
        ...,
        description="Host port mapped to container port",
    )
    proto: PortProtocol = Field(
        ...,
        description="Protocol",
    )
    preview_url: str = Field(
        ...,
        description="URL to access the exposed port",
    )
    label: Optional[str] = Field(
        default=None,
        description="Port label",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "workspace_id": self.workspace_id,
            "port": self.port,
            "host_port": self.host_port,
            "proto": self.proto.value,
            "preview_url": self.preview_url,
            "label": self.label,
        }


# =============================================================================
# IDE Models
# =============================================================================


class IDEMode(str, Enum):
    """IDE integration mode."""

    CODESERVER_SINGLE = "codeserver_single"
    CODESERVER_PER_WORKSPACE = "codeserver_per_workspace"


class IDEInfo(BaseModel):
    """Information about IDE access for a workspace."""

    workspace_id: str = Field(
        ...,
        description="Workspace ID",
    )
    ide_url: str = Field(
        ...,
        description="URL to access the IDE",
    )
    mode: IDEMode = Field(
        ...,
        description="IDE mode",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "workspace_id": self.workspace_id,
            "ide_url": self.ide_url,
            "mode": self.mode.value,
        }


# =============================================================================
# File Operation Models
# =============================================================================


class FileWriteRequest(BaseModel):
    """Request model for writing files to a workspace."""

    workspace_id: str = Field(
        ...,
        description="ID of the workspace",
    )
    files: Dict[str, str] = Field(
        ...,
        description="Map of relative file paths to contents",
        examples=[{"main.py": "print('hello')", "requirements.txt": "requests>=2.28.0"}],
    )

    @field_validator("files")
    @classmethod
    def validate_files(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate file paths are safe."""
        for path in v.keys():
            # Prevent path traversal
            if ".." in path or path.startswith("/"):
                raise ValueError(f"Invalid file path: {path}")
            # Check for dangerous filenames
            dangerous = [".bashrc", ".profile", ".env", ".git/config"]
            if path in dangerous:
                raise ValueError(f"Cannot write to protected path: {path}")
        return v


class FileReadRequest(BaseModel):
    """Request model for reading files from a workspace."""

    workspace_id: str = Field(
        ...,
        description="ID of the workspace",
    )
    paths: List[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of relative file paths to read",
    )

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, v: List[str]) -> List[str]:
        """Validate file paths are safe."""
        for path in v:
            if ".." in path or path.startswith("/"):
                raise ValueError(f"Invalid file path: {path}")
        return v


class FileContent(BaseModel):
    """Content of a file."""

    path: str = Field(
        ...,
        description="Relative file path",
    )
    content: Optional[str] = Field(
        default=None,
        description="File content (None if error)",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if read failed",
    )
    exists: bool = Field(
        default=True,
        description="Whether file exists",
    )


# =============================================================================
# Stats and Reports Models
# =============================================================================


class WorkbenchStats(BaseModel):
    """Statistics about workbench usage."""

    total_workspaces: int = Field(
        default=0,
        description="Total number of workspaces",
    )
    running_workspaces: int = Field(
        default=0,
        description="Number of running workspaces",
    )
    total_runs: int = Field(
        default=0,
        description="Total command runs",
    )
    active_ports: int = Field(
        default=0,
        description="Number of exposed ports",
    )
    workspaces_by_runtime: Dict[str, int] = Field(
        default_factory=dict,
        description="Workspace count by runtime type",
    )
    workspaces_by_status: Dict[str, int] = Field(
        default_factory=dict,
        description="Workspace count by status",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_workspaces": self.total_workspaces,
            "running_workspaces": self.running_workspaces,
            "total_runs": self.total_runs,
            "active_ports": self.active_ports,
            "workspaces_by_runtime": self.workspaces_by_runtime,
            "workspaces_by_status": self.workspaces_by_status,
        }
