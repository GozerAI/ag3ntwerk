"""
Compass (Compass) Strategy Domain Models.

Data models for strategic planning, market analysis, competitive intelligence, and content strategy.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class StrategicPriority(Enum):
    """Strategic priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    EXPLORATORY = "exploratory"


class InitiativeStatus(Enum):
    """Strategic initiative status."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MarketPosition(Enum):
    """Market positioning categories."""

    LEADER = "leader"
    CHALLENGER = "challenger"
    FOLLOWER = "follower"
    NICHE = "niche"
    EMERGING = "emerging"


class CompetitorThreatLevel(Enum):
    """Competitor threat assessment levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    MINIMAL = "minimal"


class ContentType(Enum):
    """Content types."""

    BLOG_POST = "blog_post"
    WHITEPAPER = "whitepaper"
    CASE_STUDY = "case_study"
    VIDEO = "video"
    INFOGRAPHIC = "infographic"
    SOCIAL_POST = "social_post"
    EMAIL = "email"
    PRESS_RELEASE = "press_release"
    WEBINAR = "webinar"
    PODCAST = "podcast"


class ContentStatus(Enum):
    """Content lifecycle status."""

    IDEATION = "ideation"
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ChannelType(Enum):
    """Marketing/content channel types."""

    WEBSITE = "website"
    BLOG = "blog"
    SOCIAL_MEDIA = "social_media"
    EMAIL = "email"
    PAID_ADS = "paid_ads"
    EVENTS = "events"
    PR = "pr"
    PARTNERSHIPS = "partnerships"


class AnalysisFramework(Enum):
    """Strategic analysis frameworks."""

    SWOT = "swot"
    PESTLE = "pestle"
    PORTERS_FIVE = "porters_five"
    VALUE_CHAIN = "value_chain"
    BCG_MATRIX = "bcg_matrix"
    ANSOFF_MATRIX = "ansoff_matrix"


@dataclass
class StrategicPlan:
    """Represents a strategic plan."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    vision: str = ""
    mission: str = ""
    timeframe: str = ""  # e.g., "2024-2026"
    objectives: List[Dict[str, Any]] = field(default_factory=list)
    initiatives: List[str] = field(default_factory=list)  # Initiative IDs
    kpis: List[Dict[str, Any]] = field(default_factory=list)
    resources_required: Dict[str, Any] = field(default_factory=dict)
    risks: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: InitiativeStatus = InitiativeStatus.PROPOSED
    owner: str = ""
    stakeholders: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategicInitiative:
    """Represents a strategic initiative."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    objective: str = ""
    priority: StrategicPriority = StrategicPriority.MEDIUM
    status: InitiativeStatus = InitiativeStatus.PROPOSED
    plan_id: Optional[str] = None
    owner: str = ""
    team: List[str] = field(default_factory=list)
    budget: float = 0.0
    start_date: Optional[datetime] = None
    target_end_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    risks: List[Dict[str, Any]] = field(default_factory=list)
    progress_percent: float = 0.0
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketAnalysis:
    """Represents a market analysis."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    market: str = ""
    description: str = ""
    market_size: Dict[str, Any] = field(default_factory=dict)  # current, projected, growth_rate
    segments: List[Dict[str, Any]] = field(default_factory=list)
    trends: List[Dict[str, Any]] = field(default_factory=list)
    drivers: List[str] = field(default_factory=list)
    barriers: List[str] = field(default_factory=list)
    opportunities: List[Dict[str, Any]] = field(default_factory=list)
    threats: List[Dict[str, Any]] = field(default_factory=list)
    regulatory_factors: List[str] = field(default_factory=list)
    key_players: List[Dict[str, Any]] = field(default_factory=list)
    outlook: str = ""
    confidence_level: str = "medium"  # low, medium, high
    analyst: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    valid_until: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Competitor:
    """Represents a competitor profile."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    website: str = ""
    market_position: MarketPosition = MarketPosition.CHALLENGER
    threat_level: CompetitorThreatLevel = CompetitorThreatLevel.MODERATE
    products: List[Dict[str, Any]] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    market_share: Optional[float] = None
    target_segments: List[str] = field(default_factory=list)
    pricing_strategy: str = ""
    differentiators: List[str] = field(default_factory=list)
    recent_moves: List[Dict[str, Any]] = field(default_factory=list)
    partnerships: List[str] = field(default_factory=list)
    funding: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompetitiveAnalysis:
    """Represents a competitive analysis."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    industry: str = ""
    description: str = ""
    competitors: List[str] = field(default_factory=list)  # Competitor IDs
    our_position: MarketPosition = MarketPosition.CHALLENGER
    competitive_advantages: List[str] = field(default_factory=list)
    competitive_gaps: List[str] = field(default_factory=list)
    positioning_map: Dict[str, Any] = field(default_factory=dict)
    threat_assessment: Dict[str, Any] = field(default_factory=dict)
    strategic_responses: List[Dict[str, Any]] = field(default_factory=list)
    analyst: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    valid_until: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SWOTAnalysis:
    """Represents a SWOT analysis."""

    id: str = field(default_factory=lambda: str(uuid4()))
    subject: str = ""
    description: str = ""
    strengths: List[Dict[str, Any]] = field(default_factory=list)
    weaknesses: List[Dict[str, Any]] = field(default_factory=list)
    opportunities: List[Dict[str, Any]] = field(default_factory=list)
    threats: List[Dict[str, Any]] = field(default_factory=list)
    strategic_implications: List[str] = field(default_factory=list)
    recommended_actions: List[Dict[str, Any]] = field(default_factory=list)
    analyst: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentStrategy:
    """Represents a content strategy."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    target_audience: List[Dict[str, Any]] = field(default_factory=list)  # Personas
    objectives: List[str] = field(default_factory=list)
    content_pillars: List[Dict[str, Any]] = field(default_factory=list)
    channels: List[ChannelType] = field(default_factory=list)
    content_types: List[ContentType] = field(default_factory=list)
    tone_and_voice: Dict[str, Any] = field(default_factory=dict)
    posting_frequency: Dict[str, Any] = field(default_factory=dict)
    kpis: List[Dict[str, Any]] = field(default_factory=list)
    budget: float = 0.0
    owner: str = ""
    status: InitiativeStatus = InitiativeStatus.PROPOSED
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentPiece:
    """Represents a content piece."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    content_type: ContentType = ContentType.BLOG_POST
    description: str = ""
    content: str = ""
    target_audience: str = ""
    channel: ChannelType = ChannelType.BLOG
    status: ContentStatus = ContentStatus.IDEATION
    author: str = ""
    editor: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    call_to_action: str = ""
    scheduled_date: Optional[datetime] = None
    published_date: Optional[datetime] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentCalendar:
    """Represents a content calendar."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    period: str = ""  # e.g., "Q1 2024"
    content_items: List[Dict[str, Any]] = field(
        default_factory=list
    )  # {date, content_id, channel, status}
    themes: List[str] = field(default_factory=list)
    campaigns: List[str] = field(default_factory=list)
    owner: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValueProposition:
    """Represents a value proposition."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    target_segment: str = ""
    customer_jobs: List[str] = field(default_factory=list)
    pains: List[str] = field(default_factory=list)
    gains: List[str] = field(default_factory=list)
    products_services: List[str] = field(default_factory=list)
    pain_relievers: List[str] = field(default_factory=list)
    gain_creators: List[str] = field(default_factory=list)
    unique_value_statement: str = ""
    differentiators: List[str] = field(default_factory=list)
    proof_points: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GoToMarketPlan:
    """Represents a go-to-market plan."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    product_service: str = ""
    description: str = ""
    target_market: Dict[str, Any] = field(default_factory=dict)
    value_proposition_id: Optional[str] = None
    positioning: str = ""
    pricing_strategy: Dict[str, Any] = field(default_factory=dict)
    distribution_channels: List[Dict[str, Any]] = field(default_factory=list)
    marketing_plan: Dict[str, Any] = field(default_factory=dict)
    sales_strategy: Dict[str, Any] = field(default_factory=dict)
    launch_timeline: List[Dict[str, Any]] = field(default_factory=list)
    success_metrics: List[Dict[str, Any]] = field(default_factory=list)
    budget: float = 0.0
    risks: List[Dict[str, Any]] = field(default_factory=list)
    status: InitiativeStatus = InitiativeStatus.PROPOSED
    owner: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MessagingFramework:
    """Represents a messaging framework."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    brand: str = ""
    mission_statement: str = ""
    vision_statement: str = ""
    brand_promise: str = ""
    tagline: str = ""
    elevator_pitch: str = ""
    key_messages: List[Dict[str, Any]] = field(
        default_factory=list
    )  # {audience, message, proof_points}
    tone_attributes: List[str] = field(default_factory=list)
    do_say: List[str] = field(default_factory=list)
    dont_say: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyMetrics:
    """Strategy department metrics."""

    timestamp: datetime = field(default_factory=_utcnow)

    # Strategic planning metrics
    total_initiatives: int = 0
    active_initiatives: int = 0
    completed_initiatives: int = 0
    initiative_success_rate: float = 0.0

    # Market analysis metrics
    market_analyses_completed: int = 0
    competitors_tracked: int = 0
    market_coverage_score: float = 0.0

    # Content metrics
    content_pieces_published: int = 0
    content_engagement_rate: float = 0.0
    content_calendar_adherence: float = 0.0

    # Performance metrics
    strategic_goals_achieved: int = 0
    goals_on_track: int = 0
    goals_at_risk: int = 0

    metadata: Dict[str, Any] = field(default_factory=dict)


# Strategy capabilities
STRATEGY_DOMAIN_CAPABILITIES = [
    # Market Analysis
    "market_analysis",
    "competitive_analysis",
    "trend_analysis",
    "swot_analysis",
    "opportunity_assessment",
    # Strategic Planning
    "strategic_planning",
    "roadmap_creation",
    "initiative_management",
    "kpi_definition",
    # Content & Messaging
    "content_strategy",
    "content_creation",
    "messaging_framework",
    "value_proposition",
    "brand_positioning",
    # Go-to-Market
    "go_to_market",
    "pricing_strategy",
    "channel_strategy",
    # Execution
    "campaign_planning",
    "stakeholder_alignment",
]
