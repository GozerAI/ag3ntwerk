"""
Webhook API routes for ag3ntwerk.

Provides endpoints for receiving webhooks from:
- Gumroad: /webhooks/gumroad/{event_type}
- Twitter: /webhooks/twitter
- LinkedIn: /webhooks/linkedin

These routes validate incoming webhooks and dispatch to the appropriate handlers.
Events are broadcast to WebSocket clients and relevant agents (Vector, Echo).
"""

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Query

from ag3ntwerk.integrations.webhooks import (
    GumroadWebhookHandler,
    GumroadSaleEvent,
    SocialWebhookHandler,
    SocialEngagementEvent,
)
from ag3ntwerk.api.websocket_events import (
    get_broadcaster,
    _get_broadcaster_async,
    create_gumroad_sale_event,
    create_gumroad_refund_event,
    create_twitter_mention_event,
    create_twitter_follow_event,
    create_linkedin_engagement_event,
    EventType,
    initialize_default_handlers,
)

logger = logging.getLogger(__name__)

# Initialize default handlers (WebSocket broadcast, Vector/Echo notifications)
initialize_default_handlers()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Initialize handlers with secrets from environment
_gumroad_handler = GumroadWebhookHandler(webhook_secret=os.getenv("GUMROAD_WEBHOOK_SECRET"))
_social_handler = SocialWebhookHandler(
    twitter_consumer_secret=os.getenv("TWITTER_API_SECRET"),
    linkedin_client_secret=os.getenv("LINKEDIN_CLIENT_SECRET"),
)


def get_gumroad_handler() -> GumroadWebhookHandler:
    """Get the Gumroad webhook handler instance."""
    return _gumroad_handler


def get_social_handler() -> SocialWebhookHandler:
    """Get the social webhook handler instance."""
    return _social_handler


# ============================================================
# Gumroad Webhooks
# ============================================================


@router.post("/gumroad/{event_type}")
async def gumroad_webhook(
    event_type: str,
    request: Request,
) -> Dict[str, Any]:
    """
    Receive Gumroad webhook events.

    Gumroad sends webhooks as form-encoded data. Supported event types:
    - sale: New sale completed
    - refund: Sale refunded
    - cancelled_subscription: Subscription cancelled
    - subscription_updated: Subscription status changed

    Configure webhook URL in Gumroad:
        https://your-domain.com/webhooks/gumroad/sale
    """
    try:
        # Parse form data
        form_data = await request.form()
        data = {key: form_data[key] for key in form_data}

        # Get signature if present
        signature = request.headers.get("X-Gumroad-Signature")
        raw_body = await request.body()

        # Process webhook
        event = await _gumroad_handler.process(
            data=data,
            event_type=event_type,
            signature=signature,
            raw_body=raw_body,
        )

        logger.info(
            f"Gumroad webhook processed: {event_type}",
            extra={"sale_id": event.sale_id, "product_id": event.product_id},
        )

        return {
            "success": True,
            "event_type": event.event_type.value,
            "sale_id": event.sale_id,
        }

    except ValueError as e:
        logger.warning(f"Invalid Gumroad webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Gumroad webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing failed")


# ============================================================
# Twitter Webhooks
# ============================================================


@router.get("/twitter")
async def twitter_webhook_crc(
    crc_token: str = Query(..., description="CRC token for challenge-response check"),
) -> Dict[str, str]:
    """
    Twitter CRC challenge endpoint.

    Twitter sends periodic GET requests with a crc_token that must be
    signed and returned to verify webhook ownership.
    """
    try:
        response_token = _social_handler.generate_twitter_crc_response(crc_token)
        return {"response_token": response_token}
    except ValueError as e:
        logger.warning(f"Twitter CRC validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/twitter")
async def twitter_webhook(request: Request) -> Dict[str, Any]:
    """
    Receive Twitter Account Activity webhook events.

    Twitter sends JSON payloads with events like:
    - favorite_events: Likes
    - tweet_create_events: Mentions, replies
    - follow_events: New followers
    - direct_message_events: DMs
    """
    try:
        data = await request.json()
        signature = request.headers.get("X-Twitter-Webhooks-Signature")
        raw_body = await request.body()

        event = await _social_handler.process_twitter(
            data=data,
            signature=signature,
            raw_body=raw_body,
        )

        logger.info(
            f"Twitter webhook processed: {event.event_type.value}",
            extra={"user_handle": event.user_handle, "event_id": event.event_id},
        )

        return {
            "success": True,
            "event_type": event.event_type.value,
            "event_id": event.event_id,
        }

    except ValueError as e:
        logger.warning(f"Invalid Twitter webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Twitter webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing failed")


# ============================================================
# LinkedIn Webhooks
# ============================================================


@router.post("/linkedin")
async def linkedin_webhook(request: Request) -> Dict[str, Any]:
    """
    Receive LinkedIn webhook events.

    LinkedIn sends JSON payloads for events like:
    - UGCPOST_LIKE: Post liked
    - UGCPOST_COMMENT: Post commented
    - UGCPOST_SHARE: Post shared
    - SHARE_MENTION: Mentioned in a post
    """
    try:
        data = await request.json()

        event = await _social_handler.process_linkedin(data)

        logger.info(
            f"LinkedIn webhook processed: {event.event_type.value}",
            extra={"user_name": event.user_name, "event_id": event.event_id},
        )

        return {
            "success": True,
            "event_type": event.event_type.value,
            "event_id": event.event_id,
        }

    except ValueError as e:
        logger.warning(f"Invalid LinkedIn webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"LinkedIn webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing failed")


# ============================================================
# Default Handlers (integrate with ag3ntwerk system)
# ============================================================

# Register default handlers that broadcast events to the system
# These can be extended by registering additional handlers


@_gumroad_handler.on_sale
async def _default_sale_handler(event: GumroadSaleEvent) -> None:
    """Default handler that logs sales and broadcasts to WebSocket clients."""
    logger.info(
        f"New Gumroad sale: {event.product_name}",
        extra={
            "sale_id": event.sale_id,
            "price_cents": event.price,
            "net_revenue_cents": event.price - event.gumroad_fee,
        },
    )

    # Create and broadcast webhook event
    webhook_event = create_gumroad_sale_event(
        sale_id=event.sale_id,
        product_id=event.product_id,
        product_name=event.product_name,
        price_cents=event.price,
        gumroad_fee_cents=event.gumroad_fee,
        buyer_email=event.buyer_email,
    )
    await (await _get_broadcaster_async()).broadcast(webhook_event)


@_gumroad_handler.on_refund
async def _default_refund_handler(event: GumroadSaleEvent) -> None:
    """Default handler that logs refunds and broadcasts to WebSocket clients."""
    logger.warning(
        f"Gumroad refund: {event.product_name}",
        extra={
            "sale_id": event.sale_id,
            "refund_amount_cents": event.price,
        },
    )

    # Create and broadcast webhook event
    webhook_event = create_gumroad_refund_event(
        sale_id=event.sale_id,
        product_id=event.product_id,
        product_name=event.product_name,
        refund_amount_cents=event.price,
    )
    await (await _get_broadcaster_async()).broadcast(webhook_event)


@_social_handler.on_mention
async def _default_mention_handler(event: SocialEngagementEvent) -> None:
    """Default handler that logs mentions and broadcasts to WebSocket clients."""
    logger.info(
        f"Social mention on {event.platform.value}",
        extra={
            "user": event.user_handle or event.user_name,
            "content": event.content[:100] if event.content else None,
        },
    )

    # Create and broadcast webhook event based on platform
    if event.platform.value == "twitter":
        webhook_event = create_twitter_mention_event(
            event_id=event.event_id,
            user_handle=event.user_handle or "",
            content=event.content or "",
        )
    else:  # LinkedIn
        webhook_event = create_linkedin_engagement_event(
            event_type=EventType.LINKEDIN_MENTION,
            event_id=event.event_id,
            user_name=event.user_name or "",
            content=event.content,
        )
    await (await _get_broadcaster_async()).broadcast(webhook_event)


@_social_handler.on_follow
async def _default_follow_handler(event: SocialEngagementEvent) -> None:
    """Default handler that logs new followers and broadcasts to WebSocket clients."""
    logger.info(
        f"New follower on {event.platform.value}",
        extra={
            "user": event.user_handle or event.user_name,
        },
    )

    # Create and broadcast webhook event
    webhook_event = create_twitter_follow_event(
        event_id=event.event_id,
        user_handle=event.user_handle or event.user_name or "",
    )
    await (await _get_broadcaster_async()).broadcast(webhook_event)
