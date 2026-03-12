"""
Forge (Forge) Development Domain Models.

Data models for development operations, architecture, and engineering standards.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ProjectStatus(Enum):
    """Project status."""

    PLANNING = "planning"
    IN_DEVELOPMENT = "in_development"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    MAINTENANCE = "maintenance"
    ARCHIVED = "archived"


class TaskPriority(Enum):
    """Development task priority."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKLOG = "backlog"


class CodeQuality(Enum):
    """Code quality rating."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"


class ReviewStatus(Enum):
    """Code review status."""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class TestStatus(Enum):
    """Test execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class DeploymentStatus(Enum):
    """Deployment status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ArchitecturePattern(Enum):
    """Software architecture patterns."""

    MONOLITHIC = "monolithic"
    MICROSERVICES = "microservices"
    SERVERLESS = "serverless"
    EVENT_DRIVEN = "event_driven"
    LAYERED = "layered"
    HEXAGONAL = "hexagonal"
    CQRS = "cqrs"
    HYBRID = "hybrid"


class TechStackLayer(Enum):
    """Technology stack layers."""

    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    INFRASTRUCTURE = "infrastructure"
    DEVOPS = "devops"
    SECURITY = "security"
    MONITORING = "monitoring"


class BugSeverity(Enum):
    """Bug severity levels."""

    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    TRIVIAL = "trivial"


class BugStatus(Enum):
    """Bug tracking status."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    VERIFIED = "verified"
    CLOSED = "closed"
    WONT_FIX = "wont_fix"


@dataclass
class Project:
    """Represents a development project."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: ProjectStatus = ProjectStatus.PLANNING
    repository: Optional[str] = None
    architecture: ArchitecturePattern = ArchitecturePattern.LAYERED
    tech_stack: Dict[str, List[str]] = field(default_factory=dict)
    team_members: List[str] = field(default_factory=list)
    lead: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    started_at: Optional[datetime] = None
    target_completion: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeReview:
    """Represents a code review."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    status: ReviewStatus = ReviewStatus.PENDING
    file_path: str = ""
    repository: Optional[str] = None
    branch: str = "main"
    commit_sha: Optional[str] = None
    author: Optional[str] = None
    reviewer: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    reviewed_at: Optional[datetime] = None
    quality_rating: Optional[CodeQuality] = None
    issues_found: int = 0
    issues_critical: int = 0
    issues_high: int = 0
    issues_medium: int = 0
    issues_low: int = 0
    comments: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    approved_by: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeGeneration:
    """Represents a code generation request/result."""

    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    language: str = "python"
    framework: Optional[str] = None
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    generated_code: Optional[str] = None
    file_path: Optional[str] = None
    tests_included: bool = False
    documentation_included: bool = False
    created_at: datetime = field(default_factory=_utcnow)
    generation_time_ms: Optional[int] = None
    quality_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Bug:
    """Represents a bug/defect."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    severity: BugSeverity = BugSeverity.MAJOR
    status: BugStatus = BugStatus.OPEN
    priority: TaskPriority = TaskPriority.MEDIUM
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    steps_to_reproduce: List[str] = field(default_factory=list)
    expected_behavior: str = ""
    actual_behavior: str = ""
    root_cause: Optional[str] = None
    fix_description: Optional[str] = None
    reporter: Optional[str] = None
    assignee: Optional[str] = None
    reported_at: datetime = field(default_factory=_utcnow)
    resolved_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    environment: Dict[str, str] = field(default_factory=dict)
    related_bugs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuite:
    """Represents a test suite."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    test_type: str = "unit"  # unit, integration, e2e, performance
    status: TestStatus = TestStatus.PENDING
    target_file: Optional[str] = None
    target_function: Optional[str] = None
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    coverage_percentage: Optional[float] = None
    execution_time_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    generated_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Refactoring:
    """Represents a refactoring operation."""

    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    goal: str = ""
    refactoring_type: str = ""  # extract_method, rename, move, simplify, etc.
    file_path: str = ""
    original_code: Optional[str] = None
    refactored_code: Optional[str] = None
    improvements: List[str] = field(default_factory=list)
    trade_offs: List[str] = field(default_factory=list)
    breaking_changes: bool = False
    tests_updated: bool = False
    documentation_updated: bool = False
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchitectureDesign:
    """Represents an architecture design."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    pattern: ArchitecturePattern = ArchitecturePattern.LAYERED
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    components: List[Dict[str, Any]] = field(default_factory=list)
    data_flows: List[Dict[str, Any]] = field(default_factory=list)
    api_contracts: List[Dict[str, Any]] = field(default_factory=list)
    tech_recommendations: Dict[str, str] = field(default_factory=dict)
    scalability_notes: List[str] = field(default_factory=list)
    security_considerations: List[str] = field(default_factory=list)
    trade_offs: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    author: Optional[str] = None
    reviewers: List[str] = field(default_factory=list)
    approved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Deployment:
    """Represents a deployment."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: DeploymentStatus = DeploymentStatus.PENDING
    environment: str = "development"  # development, staging, production
    version: str = ""
    commit_sha: Optional[str] = None
    repository: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    deployed_by: Optional[str] = None
    rollback_version: Optional[str] = None
    health_checks: List[Dict[str, Any]] = field(default_factory=list)
    logs_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TechStack:
    """Represents a technology stack."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    project_id: Optional[str] = None
    frontend: List[str] = field(default_factory=list)
    backend: List[str] = field(default_factory=list)
    database: List[str] = field(default_factory=list)
    infrastructure: List[str] = field(default_factory=list)
    devops: List[str] = field(default_factory=list)
    monitoring: List[str] = field(default_factory=list)
    security: List[str] = field(default_factory=list)
    other: Dict[str, List[str]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodingStandard:
    """Represents coding standards for a language/framework."""

    id: str = field(default_factory=lambda: str(uuid4()))
    language: str = ""
    framework: Optional[str] = None
    version: str = "1.0"
    naming_conventions: Dict[str, str] = field(default_factory=dict)
    formatting_rules: Dict[str, str] = field(default_factory=dict)
    documentation_requirements: List[str] = field(default_factory=list)
    testing_requirements: List[str] = field(default_factory=list)
    security_guidelines: List[str] = field(default_factory=list)
    error_handling: List[str] = field(default_factory=list)
    performance_guidelines: List[str] = field(default_factory=list)
    linter_config: Optional[str] = None
    formatter_config: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DebugSession:
    """Represents a debugging session."""

    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    symptoms: str = ""
    file_path: Optional[str] = None
    code_snippet: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    possible_causes: List[Dict[str, Any]] = field(default_factory=list)
    diagnostic_steps: List[str] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    root_cause: Optional[str] = None
    fix_applied: Optional[str] = None
    prevention_notes: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=_utcnow)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceOptimization:
    """Represents a performance optimization."""

    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    target: str = ""  # function, module, service
    file_path: Optional[str] = None
    original_metrics: Dict[str, Any] = field(default_factory=dict)
    optimized_metrics: Dict[str, Any] = field(default_factory=dict)
    improvement_percentage: Optional[float] = None
    optimizations_applied: List[str] = field(default_factory=list)
    trade_offs: List[str] = field(default_factory=list)
    before_code: Optional[str] = None
    after_code: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIDesign:
    """Represents an API design."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0"
    api_type: str = "REST"  # REST, GraphQL, gRPC, WebSocket
    base_path: str = ""
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    authentication: Dict[str, Any] = field(default_factory=dict)
    rate_limiting: Dict[str, Any] = field(default_factory=dict)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    request_examples: List[Dict[str, Any]] = field(default_factory=list)
    response_examples: List[Dict[str, Any]] = field(default_factory=list)
    openapi_spec: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatabaseDesign:
    """Represents a database design."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    database_type: str = "postgresql"  # postgresql, mysql, mongodb, etc.
    tables: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    migrations: List[str] = field(default_factory=list)
    seed_data: Optional[str] = None
    performance_notes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DevelopmentMetrics:
    """Development metrics and KPIs."""

    timestamp: datetime = field(default_factory=_utcnow)

    # Code metrics
    lines_of_code: int = 0
    files_modified: int = 0
    commits: int = 0
    pull_requests: int = 0
    code_coverage: float = 0.0

    # Review metrics
    reviews_completed: int = 0
    review_turnaround_hours: float = 0.0
    issues_found: int = 0
    issues_resolved: int = 0

    # Bug metrics
    bugs_open: int = 0
    bugs_resolved: int = 0
    mttr_bugs_hours: float = 0.0  # Mean time to resolve

    # Deployment metrics
    deployments: int = 0
    deployment_success_rate: float = 0.0
    rollbacks: int = 0

    # Test metrics
    tests_written: int = 0
    tests_passed: int = 0
    test_coverage: float = 0.0

    # Velocity metrics
    story_points_completed: int = 0
    cycle_time_hours: float = 0.0
    lead_time_hours: float = 0.0

    metadata: Dict[str, Any] = field(default_factory=dict)


# Development capabilities list
DEVELOPMENT_CAPABILITIES = [
    # Code Operations
    "code_review",
    "code_generation",
    "bug_fix",
    "refactoring",
    "optimization",
    # Testing
    "testing",
    "test_generation",
    "test_review",
    # Architecture
    "architecture",
    "system_design",
    "api_design",
    "database_design",
    # Debugging
    "debugging",
    "root_cause_analysis",
    "performance_analysis",
    # DevOps
    "deployment",
    "ci_cd",
    "infrastructure",
    # Documentation
    "documentation",
    "api_documentation",
    "technical_writing",
]
