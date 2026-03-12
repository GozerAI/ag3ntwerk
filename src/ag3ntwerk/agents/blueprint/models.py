"""
Blueprint (Blueprint) Product Domain Models.

Data models for product management, roadmaps, features, and requirements.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class FeatureStatus(Enum):
    """Feature lifecycle status."""

    IDEA = "idea"
    DISCOVERY = "discovery"
    DEFINED = "defined"
    IN_DEVELOPMENT = "in_development"
    TESTING = "testing"
    RELEASED = "released"
    DEPRECATED = "deprecated"


class FeaturePriority(Enum):
    """Feature priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NICE_TO_HAVE = "nice_to_have"


class RequirementType(Enum):
    """Requirement types."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    TECHNICAL = "technical"
    BUSINESS = "business"
    USER_STORY = "user_story"


class RequirementStatus(Enum):
    """Requirement status."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    REJECTED = "rejected"


class RoadmapHorizon(Enum):
    """Roadmap time horizons."""

    NOW = "now"
    NEXT = "next"
    LATER = "later"
    FUTURE = "future"


class SprintStatus(Enum):
    """Sprint status."""

    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Feature:
    """Represents a product feature."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: FeatureStatus = FeatureStatus.IDEA
    priority: FeaturePriority = FeaturePriority.MEDIUM
    value_score: float = 0.0
    effort_score: float = 0.0
    rice_score: float = 0.0  # Reach, Impact, Confidence, Effort
    target_release: str = ""
    owner: str = ""
    stakeholders: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)  # Requirement IDs
    dependencies: List[str] = field(default_factory=list)
    user_impact: str = ""
    success_metrics: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    released_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Requirement:
    """Represents a product requirement."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    requirement_type: RequirementType = RequirementType.FUNCTIONAL
    status: RequirementStatus = RequirementStatus.DRAFT
    feature_id: Optional[str] = None
    priority: FeaturePriority = FeaturePriority.MEDIUM
    acceptance_criteria: List[str] = field(default_factory=list)
    user_story: str = ""  # As a..., I want..., So that...
    author: str = ""
    approver: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    approved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Roadmap:
    """Represents a product roadmap."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0"
    timeframe: str = ""  # e.g., "2024"
    themes: List[str] = field(default_factory=list)
    now_items: List[str] = field(default_factory=list)  # Feature IDs
    next_items: List[str] = field(default_factory=list)
    later_items: List[str] = field(default_factory=list)
    strategic_goals: List[str] = field(default_factory=list)
    owner: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Sprint:
    """Represents a development sprint."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    goal: str = ""
    status: SprintStatus = SprintStatus.PLANNED
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    items: List[Dict[str, Any]] = field(default_factory=list)  # Backlog items
    capacity: float = 0.0  # Story points
    committed_points: float = 0.0
    completed_points: float = 0.0
    velocity: float = 0.0
    team: List[str] = field(default_factory=list)
    retrospective_notes: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BacklogItem:
    """Represents a backlog item."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    item_type: str = ""  # story, bug, task, spike
    priority: FeaturePriority = FeaturePriority.MEDIUM
    story_points: float = 0.0
    feature_id: Optional[str] = None
    sprint_id: Optional[str] = None
    assignee: Optional[str] = None
    status: str = "todo"  # todo, in_progress, done
    acceptance_criteria: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Release:
    """Represents a product release."""

    id: str = field(default_factory=lambda: str(uuid4()))
    version: str = ""
    name: str = ""
    description: str = ""
    features: List[str] = field(default_factory=list)  # Feature IDs
    release_date: Optional[datetime] = None
    release_notes: str = ""
    status: str = "planned"  # planned, in_progress, released, rolled_back
    owner: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProductMetrics:
    """Product department metrics."""

    timestamp: datetime = field(default_factory=_utcnow)
    total_features: int = 0
    features_in_development: int = 0
    features_released: int = 0
    backlog_size: int = 0
    avg_velocity: float = 0.0
    sprint_completion_rate: float = 0.0
    feature_lead_time_days: float = 0.0
    roadmap_completion_rate: float = 0.0
    nps_impact: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# Product capabilities
PRODUCT_DOMAIN_CAPABILITIES = [
    "feature_prioritization",
    "roadmap_planning",
    "requirements_gathering",
    "sprint_planning",
    "backlog_grooming",
    "release_planning",
    "milestone_tracking",
    "market_research",
    "competitive_analysis",
    "user_story_writing",
]
