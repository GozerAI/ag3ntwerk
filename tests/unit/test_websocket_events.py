"""
Tests for WebSocket event broadcasting.

Tests the webhook event broadcaster functionality:
- Event creation and serialization
- Handler registration and invocation
- Concurrent handler execution
- Error handling
- Integration with WebSocket clients
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.api.websocket_events import (
    WebhookEvent,
    WebhookEventBroadcaster,
    EventCategory,
    EventType,
    get_broadcaster,
    broadcast_to_websocket,
    notify_crevo,
    notify_cmo,
    create_gumroad_sale_event,
    create_gumroad_refund_event,
    create_twitter_mention_event,
    create_twitter_follow_event,
    create_linkedin_engagement_event,
    initialize_default_handlers,
)


class TestWebhookEvent:
    """Tests for WebhookEvent dataclass."""

    def test_create_event(self):
        """Test creating a webhook event."""
        event = WebhookEvent(
            event_type=EventType.GUMROAD_SALE,
            category=EventCategory.REVENUE,
            data={"sale_id": "123", "amount": 4999},
            source="gumroad",
        )

        assert event.event_type == EventType.GUMROAD_SALE
        assert event.category == EventCategory.REVENUE
        assert event.data["sale_id"] == "123"
        assert event.source == "gumroad"
        assert isinstance(event.timestamp, datetime)

    def test_event_to_dict(self):
        """Test event serialization to dictionary."""
        event = WebhookEvent(
            event_type=EventType.TWITTER_MENTION,
            category=EventCategory.SOCIAL,
            data={"user": "@test"},
            source="twitter",
        )

        d = event.to_dict()

        assert d["event_type"] == "twitter.mention"
        assert d["category"] == "social"
        assert d["data"]["user"] == "@test"
        assert d["source"] == "twitter"
        assert "timestamp" in d

    def test_event_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated if not provided."""
        from datetime import timezone

        before = datetime.now(timezone.utc)
        event = WebhookEvent(
            event_type=EventType.GUMROAD_SALE,
            category=EventCategory.REVENUE,
            data={},
        )
        after = datetime.now(timezone.utc)

        assert before <= event.timestamp <= after


class TestWebhookEventBroadcaster:
    """Tests for WebhookEventBroadcaster class."""

    @pytest.fixture
    def broadcaster(self):
        """Create a fresh broadcaster for each test."""
        return WebhookEventBroadcaster()

    @pytest.mark.asyncio
    async def test_register_revenue_handler(self, broadcaster):
        """Test registering a revenue handler."""
        handler = AsyncMock()
        broadcaster.on_revenue(handler)

        event = WebhookEvent(
            event_type=EventType.GUMROAD_SALE,
            category=EventCategory.REVENUE,
            data={},
        )

        await broadcaster.broadcast(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_register_social_handler(self, broadcaster):
        """Test registering a social handler."""
        handler = AsyncMock()
        broadcaster.on_social(handler)

        event = WebhookEvent(
            event_type=EventType.TWITTER_MENTION,
            category=EventCategory.SOCIAL,
            data={},
        )

        await broadcaster.broadcast(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_register_event_type_handler(self, broadcaster):
        """Test registering a handler for specific event type."""
        handler = AsyncMock()
        broadcaster.on_event_type(EventType.GUMROAD_REFUND, handler)

        # This should trigger the handler
        refund_event = WebhookEvent(
            event_type=EventType.GUMROAD_REFUND,
            category=EventCategory.REVENUE,
            data={},
        )
        await broadcaster.broadcast(refund_event)
        handler.assert_called_once_with(refund_event)

        # This should NOT trigger the handler
        handler.reset_mock()
        sale_event = WebhookEvent(
            event_type=EventType.GUMROAD_SALE,
            category=EventCategory.REVENUE,
            data={},
        )
        await broadcaster.broadcast(sale_event)
        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_global_handler(self, broadcaster):
        """Test registering a handler for all events."""
        handler = AsyncMock()
        broadcaster.on_all(handler)

        events = [
            WebhookEvent(
                event_type=EventType.GUMROAD_SALE, category=EventCategory.REVENUE, data={}
            ),
            WebhookEvent(
                event_type=EventType.TWITTER_MENTION, category=EventCategory.SOCIAL, data={}
            ),
        ]

        for event in events:
            await broadcaster.broadcast(event)

        assert handler.call_count == 2

    @pytest.mark.asyncio
    async def test_multiple_handlers_called(self, broadcaster):
        """Test that multiple handlers are called for same event."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        global_handler = AsyncMock()

        broadcaster.on_revenue(handler1)
        broadcaster.on_revenue(handler2)
        broadcaster.on_all(global_handler)

        event = WebhookEvent(
            event_type=EventType.GUMROAD_SALE,
            category=EventCategory.REVENUE,
            data={},
        )

        await broadcaster.broadcast(event)

        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)
        global_handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handlers_called_concurrently(self, broadcaster):
        """Test that handlers are executed concurrently."""
        call_order = []

        async def slow_handler(event):
            call_order.append("slow_start")
            await asyncio.sleep(0.1)
            call_order.append("slow_end")

        async def fast_handler(event):
            call_order.append("fast")

        broadcaster.on_revenue(slow_handler)
        broadcaster.on_revenue(fast_handler)

        event = WebhookEvent(
            event_type=EventType.GUMROAD_SALE,
            category=EventCategory.REVENUE,
            data={},
        )

        await broadcaster.broadcast(event)

        # Fast handler should complete before slow handler ends
        assert "fast" in call_order
        assert call_order.index("fast") < call_order.index("slow_end")

    @pytest.mark.asyncio
    async def test_handler_error_does_not_stop_others(self, broadcaster):
        """Test that one handler's error doesn't prevent others from running."""
        successful_handler = AsyncMock()
        failing_handler = AsyncMock(side_effect=ValueError("Test error"))

        broadcaster.on_revenue(failing_handler)
        broadcaster.on_revenue(successful_handler)

        event = WebhookEvent(
            event_type=EventType.GUMROAD_SALE,
            category=EventCategory.REVENUE,
            data={},
        )

        # Should not raise, errors are logged
        await broadcaster.broadcast(event)

        # Both handlers should have been called
        failing_handler.assert_called_once()
        successful_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_handlers_for_event(self, broadcaster):
        """Test broadcasting with no registered handlers."""
        event = WebhookEvent(
            event_type=EventType.GUMROAD_SALE,
            category=EventCategory.REVENUE,
            data={},
        )

        # Should not raise
        await broadcaster.broadcast(event)


class TestEventCreationHelpers:
    """Tests for event creation helper functions."""

    def test_create_gumroad_sale_event(self):
        """Test creating a Gumroad sale event."""
        event = create_gumroad_sale_event(
            sale_id="sale_123",
            product_id="prod_456",
            product_name="Test Product",
            price_cents=4999,
            gumroad_fee_cents=500,
            buyer_email="buyer@example.com",
        )

        assert event.event_type == EventType.GUMROAD_SALE
        assert event.category == EventCategory.REVENUE
        assert event.source == "gumroad"
        assert event.data["sale_id"] == "sale_123"
        assert event.data["product_id"] == "prod_456"
        assert event.data["product_name"] == "Test Product"
        assert event.data["price_cents"] == 4999
        assert event.data["gumroad_fee_cents"] == 500
        assert event.data["net_revenue_cents"] == 4499
        assert event.data["buyer_email"] == "buyer@example.com"

    def test_create_gumroad_refund_event(self):
        """Test creating a Gumroad refund event."""
        event = create_gumroad_refund_event(
            sale_id="sale_123",
            product_id="prod_456",
            product_name="Test Product",
            refund_amount_cents=4999,
        )

        assert event.event_type == EventType.GUMROAD_REFUND
        assert event.category == EventCategory.REVENUE
        assert event.source == "gumroad"
        assert event.data["sale_id"] == "sale_123"
        assert event.data["refund_amount_cents"] == 4999

    def test_create_twitter_mention_event(self):
        """Test creating a Twitter mention event."""
        event = create_twitter_mention_event(
            event_id="evt_123",
            user_handle="@testuser",
            content="Hello @ag3ntwerk!",
            tweet_url="https://twitter.com/testuser/status/123",
        )

        assert event.event_type == EventType.TWITTER_MENTION
        assert event.category == EventCategory.SOCIAL
        assert event.source == "twitter"
        assert event.data["event_id"] == "evt_123"
        assert event.data["user_handle"] == "@testuser"
        assert event.data["content"] == "Hello @ag3ntwerk!"
        assert event.data["tweet_url"] == "https://twitter.com/testuser/status/123"

    def test_create_twitter_follow_event(self):
        """Test creating a Twitter follow event."""
        event = create_twitter_follow_event(
            event_id="evt_456",
            user_handle="@newFollower",
            follower_count=1000,
        )

        assert event.event_type == EventType.TWITTER_FOLLOW
        assert event.category == EventCategory.SOCIAL
        assert event.source == "twitter"
        assert event.data["event_id"] == "evt_456"
        assert event.data["user_handle"] == "@newFollower"
        assert event.data["follower_count"] == 1000

    def test_create_linkedin_engagement_event(self):
        """Test creating a LinkedIn engagement event."""
        event = create_linkedin_engagement_event(
            event_type=EventType.LINKEDIN_LIKE,
            event_id="evt_789",
            user_name="John Doe",
            post_id="post_abc",
        )

        assert event.event_type == EventType.LINKEDIN_LIKE
        assert event.category == EventCategory.SOCIAL
        assert event.source == "linkedin"
        assert event.data["event_id"] == "evt_789"
        assert event.data["user_name"] == "John Doe"
        assert event.data["post_id"] == "post_abc"


class TestBroadcastToWebSocket:
    """Tests for WebSocket broadcast functionality."""

    @pytest.mark.asyncio
    async def test_broadcast_to_websocket_clients(self):
        """Test broadcasting event to WebSocket clients."""
        with patch("ag3ntwerk.api.state.state") as mock_state:
            mock_state.websocket_clients = [MagicMock(), MagicMock()]
            mock_state.broadcast = AsyncMock()

            event = WebhookEvent(
                event_type=EventType.GUMROAD_SALE,
                category=EventCategory.REVENUE,
                data={"sale_id": "123"},
                source="gumroad",
            )

            await broadcast_to_websocket(event)

            mock_state.broadcast.assert_called_once()
            call_args = mock_state.broadcast.call_args
            assert call_args[0][0] == "webhook.revenue"
            assert call_args[0][1]["category"] == "revenue"

    @pytest.mark.asyncio
    async def test_broadcast_with_no_clients(self):
        """Test broadcasting when no clients connected."""
        with patch("ag3ntwerk.api.state.state") as mock_state:
            mock_state.websocket_clients = []
            mock_state.broadcast = AsyncMock()

            event = WebhookEvent(
                event_type=EventType.GUMROAD_SALE,
                category=EventCategory.REVENUE,
                data={},
            )

            # Should not raise
            await broadcast_to_websocket(event)

            mock_state.broadcast.assert_called_once()


class TestNotifyCRevO:
    """Tests for Vector notification functionality."""

    @pytest.mark.asyncio
    async def test_notify_crevo_when_coo_available(self):
        """Test notifying Vector when Overwatch is available."""
        with patch("ag3ntwerk.api.state.state") as mock_state:
            mock_coo = MagicMock()
            mock_coo.route_task = AsyncMock(return_value={"routed_to": "Vector"})
            mock_state.coo = mock_coo

            event = WebhookEvent(
                event_type=EventType.GUMROAD_SALE,
                category=EventCategory.REVENUE,
                data={"sale_id": "123"},
            )

            await notify_crevo(event)

            mock_coo.route_task.assert_called_once()
            task = mock_coo.route_task.call_args[0][0]
            assert task.task_type == "revenue_tracking"

    @pytest.mark.asyncio
    async def test_notify_crevo_when_coo_unavailable(self):
        """Test that notification is skipped when Overwatch is unavailable."""
        with patch("ag3ntwerk.api.state.state") as mock_state:
            mock_state.coo = None

            event = WebhookEvent(
                event_type=EventType.GUMROAD_SALE,
                category=EventCategory.REVENUE,
                data={},
            )

            # Should not raise
            await notify_crevo(event)


class TestNotifyCMO:
    """Tests for Echo notification functionality."""

    @pytest.mark.asyncio
    async def test_notify_cmo_when_coo_available(self):
        """Test notifying Echo when Overwatch is available."""
        with patch("ag3ntwerk.api.state.state") as mock_state:
            mock_coo = MagicMock()
            mock_coo.route_task = AsyncMock(return_value={"routed_to": "Echo"})
            mock_state.coo = mock_coo

            event = WebhookEvent(
                event_type=EventType.TWITTER_MENTION,
                category=EventCategory.SOCIAL,
                data={"user": "@test"},
            )

            await notify_cmo(event)

            mock_coo.route_task.assert_called_once()
            task = mock_coo.route_task.call_args[0][0]
            assert task.task_type == "social_analytics"

    @pytest.mark.asyncio
    async def test_notify_cmo_when_coo_unavailable(self):
        """Test that notification is skipped when Overwatch is unavailable."""
        with patch("ag3ntwerk.api.state.state") as mock_state:
            mock_state.coo = None

            event = WebhookEvent(
                event_type=EventType.TWITTER_MENTION,
                category=EventCategory.SOCIAL,
                data={},
            )

            # Should not raise
            await notify_cmo(event)


class TestGlobalBroadcaster:
    """Tests for global broadcaster singleton."""

    def test_get_broadcaster_returns_singleton(self):
        """Test that get_broadcaster returns the same instance."""
        broadcaster1 = get_broadcaster()
        broadcaster2 = get_broadcaster()

        assert broadcaster1 is broadcaster2

    def test_initialize_default_handlers(self):
        """Test that default handlers are initialized."""
        # This should not raise
        initialize_default_handlers()

        broadcaster = get_broadcaster()
        # Check that handlers are registered
        assert len(broadcaster._global_handlers) > 0
        assert len(broadcaster._handlers[EventCategory.REVENUE]) > 0
        assert len(broadcaster._handlers[EventCategory.SOCIAL]) > 0


class TestEventTypes:
    """Tests for event type enums."""

    def test_event_category_values(self):
        """Test EventCategory enum values."""
        assert EventCategory.REVENUE.value == "revenue"
        assert EventCategory.SOCIAL.value == "social"
        assert EventCategory.SYSTEM.value == "system"

    def test_event_type_values(self):
        """Test EventType enum values."""
        # Revenue events
        assert EventType.GUMROAD_SALE.value == "gumroad.sale"
        assert EventType.GUMROAD_REFUND.value == "gumroad.refund"
        assert EventType.GUMROAD_SUBSCRIPTION.value == "gumroad.subscription"

        # Twitter events
        assert EventType.TWITTER_MENTION.value == "twitter.mention"
        assert EventType.TWITTER_FOLLOW.value == "twitter.follow"
        assert EventType.TWITTER_LIKE.value == "twitter.like"
        assert EventType.TWITTER_RETWEET.value == "twitter.retweet"

        # LinkedIn events
        assert EventType.LINKEDIN_MENTION.value == "linkedin.mention"
        assert EventType.LINKEDIN_LIKE.value == "linkedin.like"
        assert EventType.LINKEDIN_COMMENT.value == "linkedin.comment"
        assert EventType.LINKEDIN_SHARE.value == "linkedin.share"
