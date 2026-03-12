"""
Social platform webhook handlers for ag3ntwerk.

Receives and processes webhook events from social platforms:
- LinkedIn: Engagement notifications (via LinkedIn Marketing API webhooks)
- Twitter/X: Account activity webhooks

These allow real-time response to social engagement.

Security:
    Each platform has its own signature verification mechanism.
    - LinkedIn: Validate via OAuth signature
    - Twitter: Uses CRC-based challenge-response validation

Documentation:
    LinkedIn: https://learn.microsoft.com/en-us/linkedin/marketing/integrations/
    Twitter: https://developer.twitter.com/en/docs/twitter-api/enterprise/account-activity-api
"""

import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class SocialPlatform(Enum):
    """Supported social platforms."""

    LINKEDIN = "linkedin"
    TWITTER = "twitter"


class SocialEventType(Enum):
    """Types of social engagement events."""

    # Engagement events
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    RETWEET = "retweet"
    REPLY = "reply"
    QUOTE = "quote"

    # Mentions
    MENTION = "mention"
    DIRECT_MESSAGE = "direct_message"

    # Follower events
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"

    # Post events
    POST_IMPRESSION = "post_impression"
    POST_CLICK = "post_click"

    # Other
    UNKNOWN = "unknown"


@dataclass
class SocialEngagementEvent:
    """Parsed social engagement webhook event."""

    platform: SocialPlatform
    event_type: SocialEventType
    event_id: str
    post_id: Optional[str]
    user_id: str
    user_name: str
    user_handle: Optional[str]
    content: Optional[str]
    created_at: datetime
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_linkedin_webhook(cls, data: Dict[str, Any]) -> "SocialEngagementEvent":
        """
        Create from LinkedIn webhook payload.

        LinkedIn sends events in this format:
        {
            "type": "UGCPOST_LIKE",
            "activity": {
                "urn": "urn:li:activity:123",
                "actor": "urn:li:person:456",
                ...
            }
        }
        """
        event_type_map = {
            "UGCPOST_LIKE": SocialEventType.LIKE,
            "UGCPOST_COMMENT": SocialEventType.COMMENT,
            "UGCPOST_SHARE": SocialEventType.SHARE,
            "SHARE_MENTION": SocialEventType.MENTION,
        }

        linkedin_type = data.get("type", "")
        event_type = event_type_map.get(linkedin_type, SocialEventType.UNKNOWN)

        activity = data.get("activity", {})
        actor = data.get("actor", {})

        return cls(
            platform=SocialPlatform.LINKEDIN,
            event_type=event_type,
            event_id=activity.get("urn", ""),
            post_id=activity.get("object", {}).get("urn"),
            user_id=actor.get("urn", ""),
            user_name=actor.get("name", {}).get("localized", {}).get("en_US", "Unknown"),
            user_handle=None,  # LinkedIn doesn't have handles
            content=activity.get("commentary", {}).get("text"),
            created_at=datetime.now(timezone.utc),
            raw_data=data,
        )

    @classmethod
    def from_twitter_webhook(cls, data: Dict[str, Any]) -> "SocialEngagementEvent":
        """
        Create from Twitter Account Activity webhook payload.

        Twitter sends events wrapped in event-specific keys:
        {
            "for_user_id": "123",
            "tweet_create_events": [...],
            "favorite_events": [...],
            ...
        }
        """
        # Determine event type based on which key is present
        if "favorite_events" in data:
            events = data["favorite_events"]
            event_type = SocialEventType.LIKE
        elif "tweet_create_events" in data:
            events = data["tweet_create_events"]
            event_type = SocialEventType.REPLY
        elif "follow_events" in data:
            events = data["follow_events"]
            event_type = SocialEventType.FOLLOW
        elif "direct_message_events" in data:
            events = data["direct_message_events"]
            event_type = SocialEventType.DIRECT_MESSAGE
        else:
            events = []
            event_type = SocialEventType.UNKNOWN

        if not events:
            return cls(
                platform=SocialPlatform.TWITTER,
                event_type=SocialEventType.UNKNOWN,
                event_id="",
                post_id=None,
                user_id=data.get("for_user_id", ""),
                user_name="Unknown",
                user_handle=None,
                content=None,
                created_at=datetime.now(timezone.utc),
                raw_data=data,
            )

        event = events[0]
        user = event.get("user", {}) or event.get("source", {})

        # Parse timestamp
        created_str = event.get("created_at", "")
        try:
            # Twitter uses format like "Wed Oct 10 20:19:24 +0000 2018"
            created_at = datetime.strptime(created_str, "%a %b %d %H:%M:%S %z %Y")
        except (ValueError, TypeError):
            created_at = datetime.now(timezone.utc)

        return cls(
            platform=SocialPlatform.TWITTER,
            event_type=event_type,
            event_id=str(event.get("id", event.get("id_str", ""))),
            post_id=event.get("in_reply_to_status_id_str"),
            user_id=str(user.get("id", user.get("id_str", ""))),
            user_name=user.get("name", "Unknown"),
            user_handle=user.get("screen_name"),
            content=event.get("text"),
            created_at=created_at,
            raw_data=data,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission."""
        return {
            "platform": self.platform.value,
            "event_type": self.event_type.value,
            "event_id": self.event_id,
            "post_id": self.post_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_handle": self.user_handle,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }


# Type alias for event handlers
EventHandler = Callable[[SocialEngagementEvent], Coroutine[Any, Any, None]]


class SocialWebhookHandler:
    """
    Handler for social platform webhook events.

    Validates incoming webhooks and dispatches to registered handlers.
    Supports both LinkedIn and Twitter webhook formats.

    Example:
        handler = SocialWebhookHandler(twitter_consumer_secret="xxx")

        @handler.on_mention
        async def handle_mention(event: SocialEngagementEvent):
            print(f"Mentioned by @{event.user_handle}")

        # In FastAPI route:
        await handler.process_twitter(request_data, signature)
    """

    def __init__(
        self,
        twitter_consumer_secret: Optional[str] = None,
        linkedin_client_secret: Optional[str] = None,
    ):
        """
        Initialize webhook handler.

        Args:
            twitter_consumer_secret: Twitter app consumer secret for CRC validation
            linkedin_client_secret: LinkedIn app client secret for signature validation
        """
        self.twitter_secret = twitter_consumer_secret
        self.linkedin_secret = linkedin_client_secret
        self._handlers: Dict[SocialEventType, List[EventHandler]] = {
            event_type: [] for event_type in SocialEventType
        }

    def register(self, event_type: SocialEventType, handler: EventHandler) -> None:
        """Register a handler for an event type."""
        self._handlers[event_type].append(handler)

    def on_like(self, handler: EventHandler) -> EventHandler:
        """Decorator to register a like event handler."""
        self.register(SocialEventType.LIKE, handler)
        return handler

    def on_comment(self, handler: EventHandler) -> EventHandler:
        """Decorator to register a comment event handler."""
        self.register(SocialEventType.COMMENT, handler)
        return handler

    def on_mention(self, handler: EventHandler) -> EventHandler:
        """Decorator to register a mention event handler."""
        self.register(SocialEventType.MENTION, handler)
        return handler

    def on_follow(self, handler: EventHandler) -> EventHandler:
        """Decorator to register a follow event handler."""
        self.register(SocialEventType.FOLLOW, handler)
        return handler

    def on_reply(self, handler: EventHandler) -> EventHandler:
        """Decorator to register a reply event handler."""
        self.register(SocialEventType.REPLY, handler)
        return handler

    def generate_twitter_crc_response(self, crc_token: str) -> str:
        """
        Generate CRC response for Twitter webhook validation.

        Twitter sends a CRC challenge that must be signed with HMAC-SHA256.

        Args:
            crc_token: The crc_token from Twitter's challenge request

        Returns:
            Base64-encoded HMAC-SHA256 signature
        """
        if not self.twitter_secret:
            raise ValueError("Twitter consumer secret not configured")

        import base64

        signature = hmac.new(
            self.twitter_secret.encode(),
            crc_token.encode(),
            hashlib.sha256,
        ).digest()

        return f"sha256={base64.b64encode(signature).decode()}"

    def verify_twitter_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Twitter webhook signature.

        Args:
            payload: Raw request body
            signature: X-Twitter-Webhooks-Signature header value

        Returns:
            True if valid
        """
        if not self.twitter_secret:
            return True  # Skip verification if no secret

        import base64

        expected = hmac.new(
            self.twitter_secret.encode(),
            payload,
            hashlib.sha256,
        ).digest()

        expected_b64 = f"sha256={base64.b64encode(expected).decode()}"
        return hmac.compare_digest(expected_b64, signature)

    async def process_twitter(
        self,
        data: Dict[str, Any],
        signature: Optional[str] = None,
        raw_body: Optional[bytes] = None,
    ) -> SocialEngagementEvent:
        """
        Process Twitter webhook event.

        Args:
            data: Parsed JSON data
            signature: X-Twitter-Webhooks-Signature header
            raw_body: Raw request body for signature verification

        Returns:
            Parsed event object
        """
        # Verify signature
        if self.twitter_secret and raw_body:
            if not signature or not self.verify_twitter_signature(raw_body, signature):
                raise ValueError("Invalid Twitter webhook signature")

        event = SocialEngagementEvent.from_twitter_webhook(data)
        await self._dispatch(event)
        return event

    async def process_linkedin(
        self,
        data: Dict[str, Any],
    ) -> SocialEngagementEvent:
        """
        Process LinkedIn webhook event.

        Args:
            data: Parsed JSON data

        Returns:
            Parsed event object
        """
        event = SocialEngagementEvent.from_linkedin_webhook(data)
        await self._dispatch(event)
        return event

    async def _dispatch(self, event: SocialEngagementEvent) -> None:
        """Dispatch event to registered handlers."""
        logger.info(
            "Social webhook received",
            extra={
                "platform": event.platform.value,
                "event_type": event.event_type.value,
                "event_id": event.event_id,
                "user_handle": event.user_handle,
            },
        )

        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    f"Handler error for {event.event_type.value}",
                    exc_info=True,
                    extra={"handler": handler.__name__, "error": str(e)},
                )
