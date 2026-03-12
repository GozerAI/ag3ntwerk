"""
Data models for Foundry (Foundry) agent.

Models for engineering execution including delivery management,
quality assurance, and DevOps operations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class SprintStatus(Enum):
    """Sprint lifecycle status."""

    PLANNING = "planning"
    ACTIVE = "active"
    REVIEW = "review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DeliveryStatus(Enum):
    """Delivery/release status."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    STAGING = "staging"
    RELEASED = "released"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class QualityGateStatus(Enum):
    """Quality gate check status."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    BYPASSED = "bypassed"


class TestStatus(Enum):
    """Test execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class PipelineStatus(Enum):
    """CI/CD pipeline status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EnvironmentType(Enum):
    """Deployment environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentStrategy(Enum):
    """Deployment strategies."""

    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    RECREATE = "recreate"
    FEATURE_FLAG = "feature_flag"


@dataclass
class Sprint:
    """Represents an engineering sprint."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    goal: str = ""
    status: SprintStatus = SprintStatus.PLANNING

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    team: str = ""
    capacity_points: int = 0
    committed_points: int = 0
    completed_points: int = 0

    stories: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=_utcnow)

    @property
    def velocity(self) -> float:
        """Calculate sprint velocity as completed/committed ratio."""
        if self.committed_points == 0:
            return 0.0
        return (self.completed_points / self.committed_points) * 100

    @property
    def is_active(self) -> bool:
        """Check if sprint is currently active."""
        return self.status == SprintStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "goal": self.goal,
            "status": self.status.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "team": self.team,
            "capacity_points": self.capacity_points,
            "committed_points": self.committed_points,
            "completed_points": self.completed_points,
            "velocity": self.velocity,
        }


@dataclass
class Release:
    """Represents a software release."""

    id: str = field(default_factory=lambda: str(uuid4()))
    version: str = ""
    name: str = ""
    description: str = ""
    status: DeliveryStatus = DeliveryStatus.PLANNED

    release_type: str = "minor"  # major, minor, patch, hotfix
    target_date: Optional[datetime] = None
    released_at: Optional[datetime] = None

    features: List[str] = field(default_factory=list)
    bug_fixes: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)

    artifacts: List[str] = field(default_factory=list)
    environments_deployed: List[str] = field(default_factory=list)

    rollback_plan: str = ""

    created_at: datetime = field(default_factory=_utcnow)

    @property
    def is_released(self) -> bool:
        """Check if release has been deployed."""
        return self.status == DeliveryStatus.RELEASED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "status": self.status.value,
            "release_type": self.release_type,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "released_at": self.released_at.isoformat() if self.released_at else None,
            "features_count": len(self.features),
            "bug_fixes_count": len(self.bug_fixes),
            "breaking_changes": len(self.breaking_changes) > 0,
        }


@dataclass
class QualityGate:
    """Quality gate check configuration."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    gate_type: str = "standard"  # standard, security, performance, compliance

    conditions: List[Dict[str, Any]] = field(default_factory=list)
    threshold: float = 80.0  # Minimum pass percentage

    is_blocking: bool = True  # If True, failure blocks deployment
    is_active: bool = True

    def evaluate(self, metrics: Dict[str, float]) -> QualityGateStatus:
        """Evaluate quality gate against metrics."""
        if not self.is_active:
            return QualityGateStatus.BYPASSED

        passed_conditions = 0
        for condition in self.conditions:
            metric_name = condition.get("metric")
            operator = condition.get("operator", ">=")
            target = condition.get("target", 0)

            actual = metrics.get(metric_name, 0)

            if operator == ">=" and actual >= target:
                passed_conditions += 1
            elif operator == "<=" and actual <= target:
                passed_conditions += 1
            elif operator == "==" and actual == target:
                passed_conditions += 1

        if not self.conditions:
            return QualityGateStatus.PASSED

        pass_rate = (passed_conditions / len(self.conditions)) * 100
        return QualityGateStatus.PASSED if pass_rate >= self.threshold else QualityGateStatus.FAILED


@dataclass
class TestSuite:
    """Test suite configuration and results."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    suite_type: str = "unit"  # unit, integration, e2e, performance, security

    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0

    coverage_percentage: float = 0.0
    execution_time_seconds: float = 0.0

    status: TestStatus = TestStatus.PENDING

    failures: List[Dict[str, str]] = field(default_factory=list)

    executed_at: Optional[datetime] = None

    @property
    def pass_rate(self) -> float:
        """Calculate test pass rate."""
        if self.total_tests == 0:
            return 100.0
        return (self.passed_tests / self.total_tests) * 100

    @property
    def is_passing(self) -> bool:
        """Check if test suite is passing."""
        return self.failed_tests == 0 and self.status != TestStatus.ERROR


@dataclass
class CodeCoverage:
    """Code coverage metrics."""

    id: str = field(default_factory=lambda: str(uuid4()))
    project: str = ""
    branch: str = "main"

    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    function_coverage: float = 0.0
    statement_coverage: float = 0.0

    uncovered_lines: List[Dict[str, Any]] = field(default_factory=list)

    target_coverage: float = 80.0

    measured_at: datetime = field(default_factory=_utcnow)

    @property
    def overall_coverage(self) -> float:
        """Calculate overall coverage as average of all metrics."""
        metrics = [
            self.line_coverage,
            self.branch_coverage,
            self.function_coverage,
            self.statement_coverage,
        ]
        return sum(metrics) / len(metrics)

    @property
    def meets_target(self) -> bool:
        """Check if coverage meets target."""
        return self.overall_coverage >= self.target_coverage


@dataclass
class Pipeline:
    """CI/CD pipeline definition and status."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""

    trigger: str = "push"  # push, pull_request, schedule, manual
    branch_pattern: str = "*"

    stages: List[Dict[str, Any]] = field(default_factory=list)

    status: PipelineStatus = PipelineStatus.PENDING
    current_stage: Optional[str] = None

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    artifacts: List[str] = field(default_factory=list)
    logs_url: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate pipeline duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_running(self) -> bool:
        """Check if pipeline is currently running."""
        return self.status == PipelineStatus.RUNNING


@dataclass
class Deployment:
    """Deployment record."""

    id: str = field(default_factory=lambda: str(uuid4()))
    release_id: str = ""
    environment: EnvironmentType = EnvironmentType.DEVELOPMENT

    strategy: DeploymentStrategy = DeploymentStrategy.ROLLING

    status: DeliveryStatus = DeliveryStatus.PLANNED

    replicas_desired: int = 1
    replicas_ready: int = 0

    health_check_url: Optional[str] = None
    health_status: str = "unknown"

    deployed_by: str = ""
    deployed_at: Optional[datetime] = None

    rollback_revision: Optional[str] = None

    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        """Check if deployment is healthy."""
        return (
            self.status == DeliveryStatus.RELEASED
            and self.replicas_ready >= self.replicas_desired
            and self.health_status == "healthy"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "release_id": self.release_id,
            "environment": self.environment.value,
            "strategy": self.strategy.value,
            "status": self.status.value,
            "replicas": f"{self.replicas_ready}/{self.replicas_desired}",
            "health_status": self.health_status,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
        }


@dataclass
class InfrastructureResource:
    """Infrastructure resource definition."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    resource_type: str = ""  # compute, storage, network, database, cache
    provider: str = ""  # aws, azure, gcp, kubernetes, docker

    status: str = "active"

    configuration: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)

    cost_per_hour: float = 0.0

    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class IncidentReport:
    """Engineering incident report."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""

    severity: str = "medium"  # critical, high, medium, low
    status: str = "open"  # open, investigating, mitigating, resolved, closed

    environment: EnvironmentType = EnvironmentType.PRODUCTION

    detected_at: datetime = field(default_factory=_utcnow)
    resolved_at: Optional[datetime] = None

    impact: str = ""
    root_cause: str = ""
    resolution: str = ""

    action_items: List[str] = field(default_factory=list)

    @property
    def time_to_resolve_hours(self) -> Optional[float]:
        """Calculate time to resolution in hours."""
        if self.resolved_at:
            return (self.resolved_at - self.detected_at).total_seconds() / 3600
        return None


@dataclass
class EngineeringMetrics:
    """Aggregated engineering metrics."""

    team: str = ""
    period: str = ""  # weekly, monthly, quarterly

    # Sprint/Delivery counts
    total_sprints: int = 0
    active_sprints: int = 0
    total_releases: int = 0
    pending_releases: int = 0
    total_deployments: int = 0
    deployment_count: int = 0

    # Pipeline/Quality counts
    active_pipelines: int = 0
    quality_gates_active: int = 0
    test_suites: int = 0

    # Incident counts
    open_incidents: int = 0

    # DORA Delivery metrics
    velocity: float = 0.0
    lead_time_days: float = 0.0
    deployment_frequency: float = 0.0  # deployments per day
    change_failure_rate: float = 0.0  # percentage
    mean_time_to_recovery_hours: float = 0.0

    # Quality metrics
    defect_density: float = 0.0  # defects per 1000 lines
    code_coverage: float = 0.0
    technical_debt_hours: float = 0.0

    # Productivity metrics
    commits_per_day: float = 0.0
    pr_merge_time_hours: float = 0.0
    sprint_burndown_rate: float = 0.0

    measured_at: datetime = field(default_factory=_utcnow)
