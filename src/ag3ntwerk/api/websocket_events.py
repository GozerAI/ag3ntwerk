"""
WebSocket event broadcasting for ag3ntwerk webhooks.

Provides a centralized event broadcaster that:
- Broadcasts webhook events to connected WebSocket clients
- Notifies relevant agents (Vector for revenue, Echo for engagement)
- Supports event filtering by type/category
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class EventCategory(str, Enum):
    """Categories of webhook events."""

    REVENUE = "revenue"
    SOCIAL = "social"
    SYSTEM = "system"


class EventType(str, Enum):
    """Specific webhook event types."""

    # Revenue events
    GUMROAD_SALE = "gumroad.sale"
    GUMROAD_REFUND = "gumroad.refund"
    GUMROAD_SUBSCRIPTION = "gumroad.subscription"

    # Social events
    TWITTER_MENTION = "twitter.mention"
    TWITTER_FOLLOW = "twitter.follow"
    TWITTER_LIKE = "twitter.like"
    TWITTER_RETWEET = "twitter.retweet"
    LINKEDIN_MENTION = "linkedin.mention"
    LINKEDIN_LIKE = "linkedin.like"
    LINKEDIN_COMMENT = "linkedin.comment"
    LINKEDIN_SHARE = "linkedin.share"


@dataclass
class WebhookEvent:
    """Represents a webhook event to be broadcast."""

    event_type: EventType
    category: EventCategory
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=_utcnow)
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.value,
            "category": self.category.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


# Type alias for async event handlers
EventHandler = Callable[[WebhookEvent], Coroutine[Any, Any, None]]


class WebhookEventBroadcaster:
    """
    Broadcasts webhook events to WebSocket clients and agents.

    Usage:
        broadcaster = WebhookEventBroadcaster()

        # Register handlers
        broadcaster.on_revenue(handle_revenue_event)
        broadcaster.on_social(handle_social_event)

        # Broadcast an event
        await broadcaster.broadcast(WebhookEvent(
            event_type=EventType.GUMROAD_SALE,
            category=EventCategory.REVENUE,
            data={"sale_id": "123", "amount": 4999},
        ))
    """

    def __init__(self):
        self._handlers: Dict[EventCategory, List[EventHandler]] = {
            EventCategory.REVENUE: [],
            EventCategory.SOCIAL: [],
            EventCategory.SYSTEM: [],
        }
        self._type_handlers: Dict[EventType, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self._subscribed_categories: Set[EventCategory] = set()

    def on_revenue(self, handler: EventHandler) -> None:
        """Register a handler for revenue events."""
        self._handlers[EventCategory.REVENUE].append(handler)
        self._subscribed_categories.add(EventCategory.REVENUE)

    def on_social(self, handler: EventHandler) -> None:
        """Register a handler for social events."""
        self._handlers[EventCategory.SOCIAL].append(handler)
        self._subscribed_categories.add(EventCategory.SOCIAL)

    def on_event_type(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self._type_handlers:
            self._type_handlers[event_type] = []
        self._type_handlers[event_type].append(handler)

    def on_all(self, handler: EventHandler) -> None:
        """Register a handler for all events."""
        self._global_handlers.append(handler)

    async def broadcast(self, event: WebhookEvent) -> None:
        """
        Broadcast an event to all registered handlers.

        Handlers are called concurrently for performance.
        Errors in individual handlers are logged but don't affect others.
        """
        handlers_to_call: List[EventHandler] = []

        # Collect all applicable handlers
        handlers_to_call.extend(self._global_handlers)
        handlers_to_call.extend(self._handlers.get(event.category, []))
        handlers_to_call.extend(self._type_handlers.get(event.event_type, []))

        if not handlers_to_call:
            logger.debug(
                f"No handlers for event {event.event_type.value}",
                extra={"category": event.category.value},
            )
            return

        # Call all handlers concurrently
        results = await asyncio.gather(
            *[self._safe_call(handler, event) for handler in handlers_to_call],
            return_exceptions=True,
        )

        # Log any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Handler error for {event.event_type.value}: {result}",
                    exc_info=result,
                )

    async def _safe_call(self, handler: EventHandler, event: WebhookEvent) -> None:
        """Safely call a handler with error handling."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Handler {handler.__name__} failed: {e}", exc_info=True)
            raise


# Global broadcaster instance
_broadcaster: Optional[WebhookEventBroadcaster] = None
_broadcaster_init_lock = asyncio.Lock()


def get_broadcaster() -> WebhookEventBroadcaster:
    """Get the global webhook event broadcaster (sync fast-path)."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = WebhookEventBroadcaster()
    return _broadcaster


async def _get_broadcaster_async() -> WebhookEventBroadcaster:
    """Get the global webhook event broadcaster with async lock."""
    global _broadcaster
    if _broadcaster is None:
        async with _broadcaster_init_lock:
            if _broadcaster is None:
                _broadcaster = WebhookEventBroadcaster()
    return _broadcaster


async def broadcast_to_websocket(event: WebhookEvent) -> None:
    """
    Broadcast a webhook event to all connected WebSocket clients.

    This is the primary handler that forwards events to the UI.
    """
    from ag3ntwerk.api.state import state

    message = {
        "type": f"webhook.{event.event_type.value}",
        "category": event.category.value,
        "data": event.data,
        "timestamp": event.timestamp.isoformat(),
        "source": event.source,
    }

    await state.broadcast(f"webhook.{event.category.value}", message)

    logger.info(
        f"Broadcast webhook event to {len(state.websocket_clients)} clients",
        extra={
            "event_type": event.event_type.value,
            "category": event.category.value,
            "client_count": len(state.websocket_clients),
        },
    )


async def notify_crevo(event: WebhookEvent) -> None:
    """
    Notify Vector (Vector) about revenue events.

    Vector tracks revenue metrics and can trigger follow-up actions.
    """
    from ag3ntwerk.api.state import state

    if not state.coo:
        logger.debug("Vector notification skipped: Overwatch not initialized")
        return

    try:
        # Route a tracking task to Vector
        from ag3ntwerk.core.base import Task

        task = Task(
            task_type="revenue_tracking",
            description=f"Track {event.event_type.value} event",
            context={
                "event_type": event.event_type.value,
                "event_data": event.data,
                "timestamp": event.timestamp.isoformat(),
            },
        )

        # Use Overwatch to route to Vector
        result = await state.coo.route_task(task)

        logger.info(
            f"Vector notified of {event.event_type.value}",
            extra={
                "routed_to": result.get("routed_to") if isinstance(result, dict) else None,
            },
        )
    except Exception as e:
        logger.warning(f"Failed to notify Vector: {e}")


async def notify_cmo(event: WebhookEvent) -> None:
    """
    Notify Echo (Echo) about social engagement events.

    Echo tracks engagement metrics and can trigger follow-up actions.
    """
    from ag3ntwerk.api.state import state

    if not state.coo:
        logger.debug("Echo notification skipped: Overwatch not initialized")
        return

    try:
        # Route a tracking task to Echo
        from ag3ntwerk.core.base import Task

        task = Task(
            task_type="social_analytics",
            description=f"Track {event.event_type.value} engagement",
            context={
                "event_type": event.event_type.value,
                "event_data": event.data,
                "timestamp": event.timestamp.isoformat(),
            },
        )

        # Use Overwatch to route to Echo
        result = await state.coo.route_task(task)

        logger.info(
            f"Echo notified of {event.event_type.value}",
            extra={
                "routed_to": result.get("routed_to") if isinstance(result, dict) else None,
            },
        )
    except Exception as e:
        logger.warning(f"Failed to notify Echo: {e}")


def initialize_default_handlers() -> None:
    """
    Initialize the broadcaster with default handlers.

    Called during application startup to wire up:
    - WebSocket broadcasting for all events
    - Vector notification for revenue events
    - Echo notification for social events
    """
    broadcaster = get_broadcaster()

    # Broadcast all events to WebSocket clients
    broadcaster.on_all(broadcast_to_websocket)

    # Notify Vector for revenue events
    broadcaster.on_revenue(notify_crevo)

    # Notify Echo for social events
    broadcaster.on_social(notify_cmo)

    logger.info("Webhook event handlers initialized")


# Convenience functions for creating events
def create_gumroad_sale_event(
    sale_id: str,
    product_id: str,
    product_name: str,
    price_cents: int,
    gumroad_fee_cents: int,
    buyer_email: Optional[str] = None,
) -> WebhookEvent:
    """Create a Gumroad sale event."""
    return WebhookEvent(
        event_type=EventType.GUMROAD_SALE,
        category=EventCategory.REVENUE,
        source="gumroad",
        data={
            "sale_id": sale_id,
            "product_id": product_id,
            "product_name": product_name,
            "price_cents": price_cents,
            "gumroad_fee_cents": gumroad_fee_cents,
            "net_revenue_cents": price_cents - gumroad_fee_cents,
            "buyer_email": buyer_email,
        },
    )


def create_gumroad_refund_event(
    sale_id: str,
    product_id: str,
    product_name: str,
    refund_amount_cents: int,
) -> WebhookEvent:
    """Create a Gumroad refund event."""
    return WebhookEvent(
        event_type=EventType.GUMROAD_REFUND,
        category=EventCategory.REVENUE,
        source="gumroad",
        data={
            "sale_id": sale_id,
            "product_id": product_id,
            "product_name": product_name,
            "refund_amount_cents": refund_amount_cents,
        },
    )


def create_twitter_mention_event(
    event_id: str,
    user_handle: str,
    content: str,
    tweet_url: Optional[str] = None,
) -> WebhookEvent:
    """Create a Twitter mention event."""
    return WebhookEvent(
        event_type=EventType.TWITTER_MENTION,
        category=EventCategory.SOCIAL,
        source="twitter",
        data={
            "event_id": event_id,
            "user_handle": user_handle,
            "content": content,
            "tweet_url": tweet_url,
        },
    )


def create_twitter_follow_event(
    event_id: str,
    user_handle: str,
    follower_count: Optional[int] = None,
) -> WebhookEvent:
    """Create a Twitter follow event."""
    return WebhookEvent(
        event_type=EventType.TWITTER_FOLLOW,
        category=EventCategory.SOCIAL,
        source="twitter",
        data={
            "event_id": event_id,
            "user_handle": user_handle,
            "follower_count": follower_count,
        },
    )


def create_linkedin_engagement_event(
    event_type: EventType,
    event_id: str,
    user_name: str,
    content: Optional[str] = None,
    post_id: Optional[str] = None,
) -> WebhookEvent:
    """Create a LinkedIn engagement event."""
    return WebhookEvent(
        event_type=event_type,
        category=EventCategory.SOCIAL,
        source="linkedin",
        data={
            "event_id": event_id,
            "user_name": user_name,
            "content": content,
            "post_id": post_id,
        },
    )
