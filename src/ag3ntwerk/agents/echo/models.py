"""
Echo (Echo) Marketing Domain Models.

Data models for marketing campaigns, brand management, and customer engagement.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class CampaignStatus(Enum):
    """Campaign status."""

    DRAFT = "draft"
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CampaignType(Enum):
    """Campaign types."""

    BRAND_AWARENESS = "brand_awareness"
    LEAD_GENERATION = "lead_generation"
    PRODUCT_LAUNCH = "product_launch"
    DEMAND_GEN = "demand_gen"
    RETENTION = "retention"
    EVENT = "event"


class ChannelType(Enum):
    """Marketing channel types."""

    EMAIL = "email"
    SOCIAL_MEDIA = "social_media"
    PAID_ADS = "paid_ads"
    CONTENT = "content"
    SEO = "seo"
    EVENTS = "events"
    PR = "pr"
    REFERRAL = "referral"


class ContentStatus(Enum):
    """Content status."""

    IDEATION = "ideation"
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SegmentType(Enum):
    """Customer segment types."""

    DEMOGRAPHIC = "demographic"
    BEHAVIORAL = "behavioral"
    FIRMOGRAPHIC = "firmographic"
    PSYCHOGRAPHIC = "psychographic"


@dataclass
class Campaign:
    """Represents a marketing campaign."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    campaign_type: CampaignType = CampaignType.BRAND_AWARENESS
    status: CampaignStatus = CampaignStatus.DRAFT
    objectives: List[str] = field(default_factory=list)
    target_audience: str = ""
    channels: List[ChannelType] = field(default_factory=list)
    budget: float = 0.0
    spent: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    kpis: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    owner: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CustomerSegment:
    """Represents a customer segment."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    segment_type: SegmentType = SegmentType.BEHAVIORAL
    criteria: Dict[str, Any] = field(default_factory=dict)
    size: int = 0
    value: float = 0.0
    personas: List[Dict[str, Any]] = field(default_factory=list)
    needs: List[str] = field(default_factory=list)
    pain_points: List[str] = field(default_factory=list)
    channels_preferred: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrandStrategy:
    """Represents a brand strategy."""

    id: str = field(default_factory=lambda: str(uuid4()))
    brand_name: str = ""
    mission: str = ""
    vision: str = ""
    positioning_statement: str = ""
    value_proposition: str = ""
    personality_traits: List[str] = field(default_factory=list)
    voice_tone: Dict[str, Any] = field(default_factory=dict)
    visual_guidelines: Dict[str, Any] = field(default_factory=dict)
    differentiators: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketingContent:
    """Represents marketing content."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    content_type: str = ""  # blog, whitepaper, video, social
    status: ContentStatus = ContentStatus.DRAFT
    channel: ChannelType = ChannelType.CONTENT
    target_segment: str = ""
    content: str = ""
    keywords: List[str] = field(default_factory=list)
    cta: str = ""
    performance: Dict[str, float] = field(default_factory=dict)
    author: str = ""
    published_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketingMetrics:
    """Marketing department metrics."""

    timestamp: datetime = field(default_factory=_utcnow)
    total_campaigns: int = 0
    active_campaigns: int = 0
    total_spend: float = 0.0
    marketing_roi: float = 0.0
    cac: float = 0.0  # Customer acquisition cost
    leads_generated: int = 0
    conversion_rate: float = 0.0
    brand_awareness_score: float = 0.0
    engagement_rate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# Marketing capabilities
MARKETING_DOMAIN_CAPABILITIES = [
    "campaign_creation",
    "campaign_management",
    "brand_strategy",
    "market_analysis",
    "content_marketing",
    "social_media_strategy",
    "marketing_analytics",
    "customer_segmentation",
    "competitive_positioning",
    "go_to_market",
    "demand_generation",
    "marketing_roi",
]
