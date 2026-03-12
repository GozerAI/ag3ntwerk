"""
Workbench Pipeline Schemas.

Pydantic models for pipeline orchestration requests, responses, and status tracking.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums
# =============================================================================


class DeploymentTarget(str, Enum):
    """Deployment target types."""

    VERCEL = "vercel"
    DOCKER_REGISTRY = "docker_registry"
    LOCAL_PREVIEW = "local"


class DatabaseType(str, Enum):
    """Supported database types."""

    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"


class PipelineStatus(str, Enum):
    """Overall pipeline status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StageStatus(str, Enum):
    """Individual stage status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# Pipeline Options
# =============================================================================


class PipelineOptions(BaseModel):
    """Options for running a pipeline."""

    skip_stages: List[str] = Field(
        default_factory=list,
        description="Stage names to skip",
    )
    deployment_target: DeploymentTarget = Field(
        default=DeploymentTarget.LOCAL_PREVIEW,
        description="Where to deploy the build",
    )
    database_type: Optional[DatabaseType] = Field(
        default=None,
        description="Database type for provisioning",
    )
    generate_secrets: bool = Field(
        default=False,
        description="Whether to generate production secrets",
    )
    auto_fix: bool = Field(
        default=True,
        description="Automatically fix issues found in code review",
    )
    coverage_target: int = Field(
        default=80,
        ge=0,
        le=100,
        description="Target test coverage percentage",
    )
    quality_thresholds: Dict[str, Any] = Field(
        default_factory=dict,
        description="Quality gate thresholds",
    )
    environment_config: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for deployment",
    )

    model_config = ConfigDict(use_enum_values=True)


class EvaluationOptions(BaseModel):
    """Options for code evaluation only (no deployment)."""

    review_scope: str = Field(
        default="full",
        description="Scope of review: full, diff, or specific paths",
    )
    focus_areas: List[str] = Field(
        default_factory=list,
        description="Specific areas to focus on (security, performance, etc.)",
    )
    security_standards: List[str] = Field(
        default_factory=lambda: ["OWASP"],
        description="Security standards to check against",
    )


class VercelOptions(BaseModel):
    """Options for Vercel deployment."""

    project_name: Optional[str] = Field(
        default=None,
        description="Vercel project name (auto-detected if not provided)",
    )
    team_id: Optional[str] = Field(
        default=None,
        description="Vercel team ID",
    )
    production: bool = Field(
        default=False,
        description="Deploy to production (vs preview)",
    )
    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for deployment",
    )


class DockerOptions(BaseModel):
    """Options for Docker registry deployment."""

    registry: str = Field(
        default="docker.io",
        description="Docker registry URL",
    )
    image_name: Optional[str] = Field(
        default=None,
        description="Image name (auto-generated if not provided)",
    )
    tag: str = Field(
        default="latest",
        description="Image tag",
    )
    dockerfile_path: str = Field(
        default="Dockerfile",
        description="Path to Dockerfile",
    )
    build_args: Dict[str, str] = Field(
        default_factory=dict,
        description="Docker build arguments",
    )


class DatabaseOptions(BaseModel):
    """Options for database provisioning."""

    database_type: DatabaseType = Field(
        default=DatabaseType.POSTGRES,
        description="Type of database to provision",
    )
    db_name: Optional[str] = Field(
        default=None,
        description="Database name (auto-generated if not provided)",
    )
    entities: List[str] = Field(
        default_factory=list,
        description="Entity names to include in schema",
    )
    seed_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Initial data to seed",
    )
    migration_tool: str = Field(
        default="alembic",
        description="Migration tool to use",
    )


class SecretsOptions(BaseModel):
    """Options for secrets management."""

    secret_types: List[str] = Field(
        default_factory=lambda: ["api_key", "db_password"],
        description="Types of secrets to generate",
    )
    encryption_method: str = Field(
        default="aes256",
        description="Encryption method for secrets",
    )
    env_file_path: str = Field(
        default=".env",
        description="Path for environment file",
    )
    scan_for_exposed: bool = Field(
        default=True,
        description="Scan codebase for exposed secrets",
    )


# =============================================================================
# Pipeline Results
# =============================================================================


class StageResult(BaseModel):
    """Result of a single pipeline stage."""

    name: str = Field(description="Stage name")
    status: StageStatus = Field(description="Stage status")
    agent: str = Field(description="Agent that handled this stage")
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None)
    output: Optional[Dict[str, Any]] = Field(default=None)
    error: Optional[str] = Field(default=None)

    model_config = ConfigDict(use_enum_values=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status,
            "agent": self.agent,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "output": self.output,
            "error": self.error,
        }


class PipelineResult(BaseModel):
    """Result of a pipeline execution."""

    pipeline_id: str = Field(description="Unique pipeline execution ID")
    workspace_id: str = Field(description="Workspace ID")
    pipeline_type: str = Field(description="Type of pipeline (full, evaluate, etc.)")
    status: PipelineStatus = Field(description="Overall pipeline status")
    stages: List[StageResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None)
    deployment_url: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pipeline_id": self.pipeline_id,
            "workspace_id": self.workspace_id,
            "pipeline_type": self.pipeline_type,
            "status": self.status,
            "stages": [s.to_dict() for s in self.stages],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "deployment_url": self.deployment_url,
            "error": self.error,
            "metadata": self.metadata,
        }


class DeployResult(BaseModel):
    """Result of a deployment operation."""

    deployment_id: str = Field(description="Deployment ID")
    target: DeploymentTarget = Field(description="Deployment target")
    status: str = Field(description="Deployment status")
    url: Optional[str] = Field(default=None, description="Deployment URL")
    logs_url: Optional[str] = Field(default=None, description="URL to build logs")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)
    error: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "deployment_id": self.deployment_id,
            "target": self.target,
            "status": self.status,
            "url": self.url,
            "logs_url": self.logs_url,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "metadata": self.metadata,
        }


# =============================================================================
# API Request/Response Models
# =============================================================================


class PipelineRequest(BaseModel):
    """Request to run a pipeline."""

    workspace_id: str = Field(description="Workspace ID to run pipeline on")
    options: PipelineOptions = Field(default_factory=PipelineOptions)


class PipelineResponse(BaseModel):
    """Response for pipeline operations."""

    pipeline: Dict[str, Any] = Field(description="Pipeline result data")


class PipelineStatusResponse(BaseModel):
    """Response for pipeline status check."""

    pipeline_id: str
    status: PipelineStatus
    progress: float = Field(ge=0, le=100, description="Progress percentage")
    current_stage: Optional[str] = Field(default=None)
    stages_completed: int = Field(default=0)
    stages_total: int = Field(default=0)

    model_config = ConfigDict(use_enum_values=True)


class PipelineLogsResponse(BaseModel):
    """Response for pipeline logs."""

    pipeline_id: str
    stage: Optional[str] = Field(default=None)
    logs: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
