"""
Social media integration layer for ag3ntwerk.

Provides platform-agnostic social media publishing, scheduling,
and analytics through a unified gateway. Each platform client
implements the SocialClient ABC.

Components:
- base: SocialClient abstract base class
- gateway: SocialDistributionGateway for multi-platform distribution
- linkedin: LinkedIn API v2 client
- twitter: Twitter/X API v2 client
"""

from ag3ntwerk.integrations.social.base import SocialClient
from ag3ntwerk.integrations.social.gateway import SocialDistributionGateway

__all__ = [
    "SocialClient",
    "SocialDistributionGateway",
]
