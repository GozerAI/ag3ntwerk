"""
Shared models for ag3ntwerk agents.

These models are used across multiple agents and integrations,
providing a common data language for cross-agent workflows.

Model Modules:
- social: Social media posts, platforms, campaigns
- revenue: Revenue records, MRR snapshots, metrics
- content: Content pieces, editorial calendars
"""

from ag3ntwerk.models.social import (
    Platform,
    PostStatus,
    SocialPost,
    Campaign,
    ContentCalendar,
)
from ag3ntwerk.models.revenue import (
    RevenueType,
    RevenueRecord,
    MRRSnapshot,
    RevenueMetrics,
)
from ag3ntwerk.models.content import (
    ContentFormat,
    ContentPiece,
    VoiceTranscript,
    ExpertiseInsight,
)

__all__ = [
    # Social
    "Platform",
    "PostStatus",
    "SocialPost",
    "Campaign",
    "ContentCalendar",
    # Revenue
    "RevenueType",
    "RevenueRecord",
    "MRRSnapshot",
    "RevenueMetrics",
    # Content
    "ContentFormat",
    "ContentPiece",
    "VoiceTranscript",
    "ExpertiseInsight",
]
