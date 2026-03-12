"""
Echo (Echo) Agent - Echo.

Codename: Echo
Core function: Amplify brand voice; orchestrate growth through strategic marketing.

The Echo handles all marketing and growth tasks:
- Campaign creation and management
- Brand strategy and positioning
- Market analysis and research
- Content marketing strategy
- Customer segmentation
"""

from ag3ntwerk.agents.echo.agent import Echo
from ag3ntwerk.agents.echo.managers import (
    BrandManager,
    CampaignManager,
    ContentManager,
    SocialDistributionManager,
)
from ag3ntwerk.agents.echo.specialists import (
    DigitalMarketer,
    ContentCreator,
    SocialMediaManager,
    MarketingAnalyticsSpecialist,
    SEOSpecialist,
    EmailMarketer,
    MarketResearchAnalyst,
    DemandGenSpecialist,
)
from ag3ntwerk.agents.echo.models import (
    # Enums
    CampaignStatus,
    CampaignType,
    ChannelType,
    ContentStatus,
    SegmentType,
    # Dataclasses
    Campaign,
    CustomerSegment,
    BrandStrategy,
    MarketingContent,
    MarketingMetrics,
    # Capabilities
    MARKETING_DOMAIN_CAPABILITIES,
)

# Codename alias
Echo = Echo

__all__ = [
    # Agent
    "Echo",
    "Echo",
    # Managers
    "BrandManager",
    "CampaignManager",
    "ContentManager",
    "SocialDistributionManager",
    # Specialists
    "DigitalMarketer",
    "ContentCreator",
    "SocialMediaManager",
    "MarketingAnalyticsSpecialist",
    "SEOSpecialist",
    "EmailMarketer",
    "MarketResearchAnalyst",
    "DemandGenSpecialist",
    # Enums
    "CampaignStatus",
    "CampaignType",
    "ChannelType",
    "ContentStatus",
    "SegmentType",
    # Dataclasses
    "Campaign",
    "CustomerSegment",
    "BrandStrategy",
    "MarketingContent",
    "MarketingMetrics",
    # Capabilities
    "MARKETING_DOMAIN_CAPABILITIES",
]
