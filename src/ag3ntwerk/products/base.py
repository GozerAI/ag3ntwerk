"""
Product Lifecycle Models.

Core data models for managing products within the ag3ntwerk framework.
Products represent software systems that ag3ntwerk agents build, deploy, and operate.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ProductStatus(Enum):
    """Product lifecycle status."""

    PLANNING = "planning"
    DEVELOPMENT = "development"
    ALPHA = "alpha"
    BETA = "beta"
    GA = "ga"  # General Availability
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"
    EOL = "eol"  # End of Life


class ReleaseStatus(Enum):
    """Release status."""

    DRAFT = "draft"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    RELEASED = "released"
    ROLLED_BACK = "rolled_back"


class ReleaseType(Enum):
    """Release type following semver conventions."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    HOTFIX = "hotfix"
    RC = "rc"  # Release Candidate


class FeatureStatus(Enum):
    """Feature lifecycle status."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    RELEASED = "released"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class EffortSize(Enum):
    """T-shirt sizing for effort estimation."""

    XS = "xs"
    S = "s"
    M = "m"
    L = "l"
    XL = "xl"
    XXL = "xxl"


class Priority(Enum):
    """Feature priority levels."""

    P0_CRITICAL = 0
    P1_HIGH = 1
    P2_MEDIUM = 2
    P3_LOW = 3
    P4_BACKLOG = 4


@dataclass
class Product:
    """
    Represents a product managed by ag3ntwerk.

    Products are software systems in the GozerAI portfolio that agents
    build, deploy, and operate.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    codename: str = ""  # e.g., "vinzy-engine", "zuultimate"
    description: str = ""
    status: ProductStatus = ProductStatus.PLANNING
    repository_url: Optional[str] = None
    documentation_url: Optional[str] = None
    current_version: Optional[str] = None
    tech_stack: List[str] = field(default_factory=list)
    owners: List[str] = field(default_factory=list)  # Agent codes
    team_members: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    launched_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Other product IDs
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Release:
    """
    Represents a product release.

    Tracks version releases including changelog, release notes,
    and associated features/commits.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    product_id: str = ""
    version: str = ""
    status: ReleaseStatus = ReleaseStatus.DRAFT
    release_type: ReleaseType = ReleaseType.MINOR
    title: str = ""
    changelog: str = ""
    release_notes: str = ""
    target_date: Optional[datetime] = None
    released_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    commits: List[str] = field(default_factory=list)  # Commit SHAs
    features: List[str] = field(default_factory=list)  # Feature IDs
    bugs_fixed: List[str] = field(default_factory=list)  # Bug/Issue IDs
    breaking_changes: List[str] = field(default_factory=list)
    known_issues: List[str] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)  # name -> url
    approvers: List[str] = field(default_factory=list)
    rollback_version: Optional[str] = None  # Version to rollback to if needed
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Feature:
    """
    Represents a product feature.

    Features are units of product functionality that go through
    the product lifecycle from proposal to release.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    product_id: str = ""
    title: str = ""
    description: str = ""
    status: FeatureStatus = FeatureStatus.PROPOSED
    priority: Priority = Priority.P2_MEDIUM
    effort_estimate: Optional[EffortSize] = None
    target_release: Optional[str] = None  # Release version
    requested_by: Optional[str] = None
    assigned_to: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)  # Other feature IDs
    acceptance_criteria: List[str] = field(default_factory=list)
    user_stories: List[str] = field(default_factory=list)
    technical_notes: str = ""
    design_docs: List[str] = field(default_factory=list)  # URLs
    test_plan: str = ""
    feedback_ids: List[str] = field(default_factory=list)  # Customer feedback IDs
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Milestone:
    """
    Represents a product milestone.

    Milestones are significant checkpoints in product development
    that group features and releases.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    product_id: str = ""
    name: str = ""
    description: str = ""
    target_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "open"  # open, in_progress, completed, missed
    features: List[str] = field(default_factory=list)  # Feature IDs
    releases: List[str] = field(default_factory=list)  # Release IDs
    success_criteria: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Roadmap:
    """
    Represents a product roadmap.

    Roadmaps organize milestones and features into a timeline
    for product planning.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    product_id: str = ""
    name: str = ""
    description: str = ""
    timeframe: str = ""  # e.g., "Q1 2026", "2026 H1"
    milestones: List[str] = field(default_factory=list)  # Milestone IDs
    themes: List[str] = field(default_factory=list)  # Strategic themes
    objectives: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    owner: Optional[str] = None  # Agent code
    status: str = "draft"  # draft, active, archived
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CustomerFeedback:
    """
    Represents customer feedback for a product.

    Feedback is collected by Beacon (Beacon) and used by Blueprint (Blueprint)
    for prioritization.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    product_id: str = ""
    customer_id: Optional[str] = None
    source: str = ""  # support_ticket, survey, interview, etc.
    category: str = ""  # feature_request, bug_report, usability, etc.
    title: str = ""
    description: str = ""
    sentiment: str = ""  # positive, negative, neutral
    priority: Priority = Priority.P2_MEDIUM
    status: str = "new"  # new, reviewed, actionable, closed
    received_at: datetime = field(default_factory=_utcnow)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    linked_features: List[str] = field(default_factory=list)  # Feature IDs
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# Product task types mapped to agents
PRODUCT_TASK_TYPES = {
    "forge": [
        "architecture_review",
        "technical_debt_assessment",
        "tech_stack_evaluation",
        "system_design",
        "dependency_audit",
    ],
    "foundry": [
        "release_planning",
        "deployment_orchestration",
        "pipeline_management",
        "version_bump",
        "changelog_generation",
        "branch_management",
        "environment_setup",
    ],
    "blueprint": [
        "feature_prioritization",
        "roadmap_update",
        "requirements_gathering",
        "sprint_planning",
        "backlog_grooming",
        "milestone_tracking",
    ],
    "beacon": [
        "feedback_collection",
        "satisfaction_tracking",
        "support_escalation",
        "customer_health_scoring",
        "onboarding_optimization",
    ],
    "vector": [
        "revenue_tracking",
        "churn_analysis",
        "feature_adoption_metrics",
        "conversion_analysis",
        "growth_experiment_design",
    ],
    "keystone": [
        "development_cost_analysis",
        "pricing_strategy",
        "margin_analysis",
        "budget_forecasting",
        "roi_calculation",
    ],
}


# Product capabilities
PRODUCT_CAPABILITIES = [
    # Product Management
    "product_planning",
    "roadmap_management",
    "feature_lifecycle",
    "release_management",
    # Customer Focus
    "feedback_collection",
    "customer_success",
    "satisfaction_tracking",
    # Revenue
    "revenue_tracking",
    "pricing_optimization",
    "growth_analysis",
    # Technical
    "repository_management",
    "version_control",
    "deployment_coordination",
]
