"""
Webhook receivers for external service integrations.

Provides webhook handlers for:
- Gumroad: Sale completed, refund, subscription events
- Social: Engagement notifications, mentions

These webhooks allow ag3ntwerk to react to external events in real-time.
"""

from ag3ntwerk.integrations.webhooks.gumroad import GumroadWebhookHandler, GumroadSaleEvent
from ag3ntwerk.integrations.webhooks.social import SocialWebhookHandler, SocialEngagementEvent

__all__ = [
    "GumroadWebhookHandler",
    "GumroadSaleEvent",
    "SocialWebhookHandler",
    "SocialEngagementEvent",
]
