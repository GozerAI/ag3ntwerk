"""
Shared social media models for ag3ntwerk.

Used by:
- Echo (Echo) for social media strategy and distribution
- Vector (Vector) for attribution tracking
- Social integration layer for platform-specific publishing

These are Pydantic models designed for validation at system boundaries
(API calls, integration inputs/outputs). The existing dataclass-based
models in agents/cmo/models.py and agents/crevo/models.py remain
for internal agent state.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Platform(str, Enum):
    """Supported social media platforms."""

    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    BLUESKY = "bluesky"
    MEDIUM = "medium"


class PostStatus(str, Enum):
    """Lifecycle status of a social media post."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class SocialPost(BaseModel):
    """
    Platform-agnostic social media post.

    Represents a single piece of content destined for one or more
    social platforms. Used by the SocialDistributionGateway to
    publish, schedule, and track content.
    """

    id: Optional[str] = None
    platform: Platform
    content: str

    # Media
    media_urls: List[str] = Field(default_factory=list)
    link: Optional[str] = None

    # Metadata
    hashtags: List[str] = Field(default_factory=list)
    mentions: List[str] = Field(default_factory=list)

    # Scheduling
    scheduled_time: Optional[datetime] = None
    status: PostStatus = PostStatus.DRAFT

    # Results (populated after publish)
    post_id: Optional[str] = None
    post_url: Optional[str] = None

    # Attribution
    campaign_id: Optional[str] = None
    source_content_id: Optional[str] = None

    created_at: datetime = Field(default_factory=_utcnow)


class Campaign(BaseModel):
    """
    Marketing campaign container.

    Groups social posts under a single campaign objective for
    coordinated distribution and unified analytics.
    """

    id: str
    name: str
    objective: str  # awareness, engagement, conversion

    # Content
    source_content_ids: List[str] = Field(default_factory=list)
    posts: List[SocialPost] = Field(default_factory=list)

    # Targeting
    platforms: List[Platform] = Field(default_factory=list)

    # Timeline
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = "draft"

    # Metrics (populated by analytics)
    impressions: int = 0
    engagements: int = 0
    clicks: int = 0
    conversions: int = 0


class ContentCalendar(BaseModel):
    """
    Editorial calendar for scheduled content.

    Organizes posts across platforms with frequency targets
    for consistent publishing cadence.
    """

    id: str
    name: str
    posts: List[SocialPost] = Field(default_factory=list)

    # Frequency settings (posts per week per platform)
    posts_per_week: Dict[Platform, int] = Field(default_factory=dict)
