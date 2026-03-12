"""
Gumroad webhook handler for ag3ntwerk.

Receives and processes webhook events from Gumroad:
- sale: New sale completed
- refund: Sale refunded
- cancelled_subscription: Subscription cancelled
- subscription_updated: Subscription status changed

Gumroad webhook format:
    POST /webhooks/gumroad/sale
    Content-Type: application/x-www-form-urlencoded

    seller_id=xxx&product_id=xxx&product_name=xxx&permalink=xxx&...

Security:
    Gumroad webhooks can be configured with a secret that's sent
    in the request. Validate using the resource_name + sale_id combo.

Documentation:
    https://help.gumroad.com/article/173-resource-subscriptions-pings
"""

import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class GumroadEventType(Enum):
    """Types of Gumroad webhook events."""

    SALE = "sale"
    REFUND = "refund"
    CANCELLED_SUBSCRIPTION = "cancelled_subscription"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_ENDED = "subscription_ended"
    SUBSCRIPTION_RESTARTED = "subscription_restarted"


@dataclass
class GumroadSaleEvent:
    """Parsed Gumroad sale webhook event."""

    event_type: GumroadEventType
    sale_id: str
    seller_id: str
    product_id: str
    product_name: str
    email: str
    price: int  # cents
    gumroad_fee: int  # cents
    currency: str
    quantity: int
    is_recurring: bool
    refunded: bool
    created_at: datetime
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_webhook_data(
        cls, data: Dict[str, Any], event_type: GumroadEventType
    ) -> "GumroadSaleEvent":
        """Create from webhook form data."""
        # Parse timestamp - Gumroad uses ISO format
        created_str = data.get("sale_timestamp") or data.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            created_at = datetime.now(timezone.utc)

        return cls(
            event_type=event_type,
            sale_id=data.get("sale_id", ""),
            seller_id=data.get("seller_id", ""),
            product_id=data.get("product_id", ""),
            product_name=data.get("product_name", ""),
            email=data.get("email", ""),
            price=int(data.get("price", 0)),
            gumroad_fee=int(data.get("gumroad_fee", 0)),
            currency=data.get("currency", "USD"),
            quantity=int(data.get("quantity", 1)),
            is_recurring=data.get("is_recurring_billing", "false").lower() == "true",
            refunded=data.get("refunded", "false").lower() == "true",
            created_at=created_at,
            raw_data=data,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission."""
        return {
            "event_type": self.event_type.value,
            "sale_id": self.sale_id,
            "seller_id": self.seller_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "email": self.email,
            "price_cents": self.price,
            "gumroad_fee_cents": self.gumroad_fee,
            "net_revenue_cents": self.price - self.gumroad_fee,
            "currency": self.currency,
            "quantity": self.quantity,
            "is_recurring": self.is_recurring,
            "refunded": self.refunded,
            "created_at": self.created_at.isoformat(),
        }


# Type alias for event handlers
EventHandler = Callable[[GumroadSaleEvent], Coroutine[Any, Any, None]]


class GumroadWebhookHandler:
    """
    Handler for Gumroad webhook events.

    Validates incoming webhooks and dispatches to registered handlers.

    Example:
        handler = GumroadWebhookHandler()

        @handler.on_sale
        async def handle_sale(event: GumroadSaleEvent):
            print(f"New sale: {event.product_name}")

        # In FastAPI route:
        await handler.process(request_data, event_type="sale")
    """

    def __init__(self, webhook_secret: Optional[str] = None):
        """
        Initialize webhook handler.

        Args:
            webhook_secret: Optional secret for signature verification.
                           If set, webhooks without valid signature are rejected.
        """
        self.webhook_secret = webhook_secret
        self._handlers: Dict[GumroadEventType, List[EventHandler]] = {
            event_type: [] for event_type in GumroadEventType
        }

    def register(self, event_type: GumroadEventType, handler: EventHandler) -> None:
        """Register a handler for an event type."""
        self._handlers[event_type].append(handler)

    def on_sale(self, handler: EventHandler) -> EventHandler:
        """Decorator to register a sale event handler."""
        self.register(GumroadEventType.SALE, handler)
        return handler

    def on_refund(self, handler: EventHandler) -> EventHandler:
        """Decorator to register a refund event handler."""
        self.register(GumroadEventType.REFUND, handler)
        return handler

    def on_subscription_cancelled(self, handler: EventHandler) -> EventHandler:
        """Decorator to register a subscription cancelled handler."""
        self.register(GumroadEventType.CANCELLED_SUBSCRIPTION, handler)
        return handler

    def on_subscription_updated(self, handler: EventHandler) -> EventHandler:
        """Decorator to register a subscription updated handler."""
        self.register(GumroadEventType.SUBSCRIPTION_UPDATED, handler)
        return handler

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature.

        Gumroad doesn't have built-in signature verification by default,
        but can be configured with custom headers. This method supports
        HMAC-SHA256 verification if a secret is configured.

        Args:
            payload: Raw request body bytes
            signature: Signature from X-Gumroad-Signature header

        Returns:
            True if signature is valid or no secret is configured.
        """
        if not self.webhook_secret:
            return True

        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    async def process(
        self,
        data: Dict[str, Any],
        event_type: str,
        signature: Optional[str] = None,
        raw_body: Optional[bytes] = None,
    ) -> GumroadSaleEvent:
        """
        Process an incoming webhook.

        Args:
            data: Parsed form data from webhook
            event_type: Event type string (sale, refund, etc.)
            signature: Optional signature for verification
            raw_body: Raw request body for signature verification

        Returns:
            Parsed event object

        Raises:
            ValueError: If event type is unknown or signature is invalid
        """
        # Verify signature if configured
        if self.webhook_secret and raw_body:
            if not signature or not self.verify_signature(raw_body, signature):
                raise ValueError("Invalid webhook signature")

        # Parse event type
        try:
            parsed_type = GumroadEventType(event_type)
        except ValueError:
            raise ValueError(f"Unknown event type: {event_type}")

        # Create event object
        event = GumroadSaleEvent.from_webhook_data(data, parsed_type)

        logger.info(
            "Gumroad webhook received",
            extra={
                "event_type": event.event_type.value,
                "sale_id": event.sale_id,
                "product_id": event.product_id,
                "price_cents": event.price,
            },
        )

        # Dispatch to handlers
        handlers = self._handlers.get(parsed_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    f"Handler error for {event_type}",
                    exc_info=True,
                    extra={"handler": handler.__name__, "error": str(e)},
                )

        return event
