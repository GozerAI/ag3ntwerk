"""
Beacon (Beacon) Customer Domain Models.

Data models for customer success, satisfaction, support, and feedback.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class CustomerHealthStatus(Enum):
    """Customer health status."""

    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    CHURNING = "churning"
    NEW = "new"
    UNKNOWN = "unknown"


class TicketStatus(Enum):
    """Support ticket status."""

    NEW = "new"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(Enum):
    """Support ticket priority."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FeedbackType(Enum):
    """Feedback types."""

    NPS = "nps"
    CSAT = "csat"
    CES = "ces"  # Customer Effort Score
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    GENERAL = "general"


class FeedbackSentiment(Enum):
    """Feedback sentiment."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class OnboardingStage(Enum):
    """Customer onboarding stage."""

    SIGNED = "signed"
    KICKOFF = "kickoff"
    IMPLEMENTATION = "implementation"
    TRAINING = "training"
    GO_LIVE = "go_live"
    ADOPTED = "adopted"


@dataclass
class Customer:
    """Represents a customer."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    company: str = ""
    tier: str = ""  # enterprise, pro, free
    health_status: CustomerHealthStatus = CustomerHealthStatus.UNKNOWN
    health_score: float = 0.0
    mrr: float = 0.0  # Monthly recurring revenue
    contract_start: Optional[datetime] = None
    contract_end: Optional[datetime] = None
    csm: str = ""  # Customer Success Manager
    onboarding_stage: OnboardingStage = OnboardingStage.SIGNED
    last_contact: Optional[datetime] = None
    nps_score: Optional[int] = None
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SupportTicket:
    """Represents a support ticket."""

    id: str = field(default_factory=lambda: str(uuid4()))
    customer_id: str = ""
    subject: str = ""
    description: str = ""
    status: TicketStatus = TicketStatus.NEW
    priority: TicketPriority = TicketPriority.MEDIUM
    category: str = ""
    assigned_to: Optional[str] = None
    resolution: str = ""
    first_response_time_hours: Optional[float] = None
    resolution_time_hours: Optional[float] = None
    created_at: datetime = field(default_factory=_utcnow)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Feedback:
    """Represents customer feedback."""

    id: str = field(default_factory=lambda: str(uuid4()))
    customer_id: str = ""
    feedback_type: FeedbackType = FeedbackType.GENERAL
    score: Optional[int] = None
    comment: str = ""
    sentiment: FeedbackSentiment = FeedbackSentiment.NEUTRAL
    topics: List[str] = field(default_factory=list)
    actionable: bool = False
    follow_up_required: bool = False
    collected_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthScore:
    """Represents a customer health score calculation."""

    id: str = field(default_factory=lambda: str(uuid4()))
    customer_id: str = ""
    overall_score: float = 0.0
    engagement_score: float = 0.0
    product_usage_score: float = 0.0
    support_score: float = 0.0
    relationship_score: float = 0.0
    financial_score: float = 0.0
    risk_factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    calculated_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OnboardingPlan:
    """Represents a customer onboarding plan."""

    id: str = field(default_factory=lambda: str(uuid4()))
    customer_id: str = ""
    current_stage: OnboardingStage = OnboardingStage.SIGNED
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    completion_percent: float = 0.0
    target_completion_date: Optional[datetime] = None
    blockers: List[str] = field(default_factory=list)
    owner: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChurnRisk:
    """Represents a churn risk assessment."""

    id: str = field(default_factory=lambda: str(uuid4()))
    customer_id: str = ""
    risk_score: float = 0.0
    risk_level: str = ""  # high, medium, low
    indicators: List[Dict[str, Any]] = field(default_factory=list)
    predicted_churn_date: Optional[datetime] = None
    retention_actions: List[str] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CustomerMetrics:
    """Customer department metrics."""

    timestamp: datetime = field(default_factory=_utcnow)
    total_customers: int = 0
    healthy_customers: int = 0
    at_risk_customers: int = 0
    nps_score: float = 0.0
    csat_score: float = 0.0
    avg_health_score: float = 0.0
    churn_rate: float = 0.0
    retention_rate: float = 0.0
    avg_first_response_hours: float = 0.0
    avg_resolution_hours: float = 0.0
    open_tickets: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# Customer capabilities
CUSTOMER_DOMAIN_CAPABILITIES = [
    "health_scoring",
    "churn_prediction",
    "feedback_analysis",
    "satisfaction_tracking",
    "support_triage",
    "onboarding_optimization",
    "customer_segmentation",
    "retention_planning",
    "escalation_management",
    "voice_of_customer",
]
