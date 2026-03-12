"""
Tests for webhook handlers.
"""

import pytest
from datetime import datetime

from ag3ntwerk.integrations.webhooks.gumroad import (
    GumroadWebhookHandler,
    GumroadSaleEvent,
    GumroadEventType,
)
from ag3ntwerk.integrations.webhooks.social import (
    SocialWebhookHandler,
    SocialEngagementEvent,
    SocialPlatform,
    SocialEventType,
)


class TestGumroadSaleEvent:
    """Tests for GumroadSaleEvent parsing."""

    def test_from_webhook_data_basic(self):
        """Test parsing basic sale webhook data."""
        data = {
            "sale_id": "sale_123",
            "seller_id": "seller_456",
            "product_id": "prod_789",
            "product_name": "Test Product",
            "email": "buyer@example.com",
            "price": "999",
            "gumroad_fee": "100",
            "currency": "USD",
            "quantity": "1",
            "is_recurring_billing": "false",
            "refunded": "false",
            "sale_timestamp": "2024-01-15T10:30:00Z",
        }

        event = GumroadSaleEvent.from_webhook_data(data, GumroadEventType.SALE)

        assert event.event_type == GumroadEventType.SALE
        assert event.sale_id == "sale_123"
        assert event.seller_id == "seller_456"
        assert event.product_id == "prod_789"
        assert event.product_name == "Test Product"
        assert event.email == "buyer@example.com"
        assert event.price == 999
        assert event.gumroad_fee == 100
        assert event.currency == "USD"
        assert event.quantity == 1
        assert not event.is_recurring
        assert not event.refunded

    def test_from_webhook_data_recurring(self):
        """Test parsing recurring subscription sale."""
        data = {
            "sale_id": "sale_sub",
            "seller_id": "seller_456",
            "product_id": "prod_sub",
            "product_name": "Subscription",
            "email": "sub@example.com",
            "price": "1999",
            "gumroad_fee": "200",
            "currency": "USD",
            "quantity": "1",
            "is_recurring_billing": "true",
            "refunded": "false",
        }

        event = GumroadSaleEvent.from_webhook_data(data, GumroadEventType.SALE)

        assert event.is_recurring is True

    def test_from_webhook_data_refund(self):
        """Test parsing refund event."""
        data = {
            "sale_id": "sale_refund",
            "seller_id": "seller_456",
            "product_id": "prod_789",
            "product_name": "Refunded Product",
            "email": "refund@example.com",
            "price": "500",
            "gumroad_fee": "50",
            "currency": "USD",
            "quantity": "1",
            "is_recurring_billing": "false",
            "refunded": "true",
        }

        event = GumroadSaleEvent.from_webhook_data(data, GumroadEventType.REFUND)

        assert event.event_type == GumroadEventType.REFUND
        assert event.refunded is True

    def test_to_dict(self):
        """Test event serialization."""
        event = GumroadSaleEvent(
            event_type=GumroadEventType.SALE,
            sale_id="sale_123",
            seller_id="seller_456",
            product_id="prod_789",
            product_name="Test",
            email="test@example.com",
            price=999,
            gumroad_fee=100,
            currency="USD",
            quantity=1,
            is_recurring=False,
            refunded=False,
            created_at=datetime(2024, 1, 15, 10, 30),
        )

        result = event.to_dict()

        assert result["event_type"] == "sale"
        assert result["sale_id"] == "sale_123"
        assert result["net_revenue_cents"] == 899


class TestGumroadWebhookHandler:
    """Tests for GumroadWebhookHandler."""

    @pytest.mark.asyncio
    async def test_process_sale_event(self):
        """Test processing a sale event."""
        handler = GumroadWebhookHandler()
        events_received = []

        @handler.on_sale
        async def capture_sale(event):
            events_received.append(event)

        data = {
            "sale_id": "sale_123",
            "seller_id": "seller_456",
            "product_id": "prod_789",
            "product_name": "Test",
            "email": "test@example.com",
            "price": "999",
            "gumroad_fee": "100",
            "currency": "USD",
            "quantity": "1",
            "is_recurring_billing": "false",
            "refunded": "false",
        }

        event = await handler.process(data, "sale")

        assert len(events_received) == 1
        assert events_received[0].sale_id == "sale_123"

    @pytest.mark.asyncio
    async def test_process_refund_event(self):
        """Test processing a refund event."""
        handler = GumroadWebhookHandler()
        refunds_received = []

        @handler.on_refund
        async def capture_refund(event):
            refunds_received.append(event)

        data = {
            "sale_id": "refund_123",
            "seller_id": "seller_456",
            "product_id": "prod_789",
            "product_name": "Refunded",
            "email": "test@example.com",
            "price": "500",
            "gumroad_fee": "50",
            "currency": "USD",
            "quantity": "1",
            "is_recurring_billing": "false",
            "refunded": "true",
        }

        event = await handler.process(data, "refund")

        assert len(refunds_received) == 1
        assert refunds_received[0].event_type == GumroadEventType.REFUND

    @pytest.mark.asyncio
    async def test_process_unknown_event_type(self):
        """Test that unknown event types raise ValueError."""
        handler = GumroadWebhookHandler()

        with pytest.raises(ValueError, match="Unknown event type"):
            await handler.process({}, "unknown_type")

    def test_signature_verification_no_secret(self):
        """Test signature verification passes when no secret is configured."""
        handler = GumroadWebhookHandler()
        assert handler.verify_signature(b"payload", "any_signature")

    def test_signature_verification_with_secret(self):
        """Test signature verification with a configured secret."""
        import hashlib
        import hmac

        secret = "test_secret"
        handler = GumroadWebhookHandler(webhook_secret=secret)

        payload = b"test_payload"
        expected_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert handler.verify_signature(payload, expected_sig)
        assert not handler.verify_signature(payload, "wrong_signature")


class TestSocialEngagementEvent:
    """Tests for SocialEngagementEvent parsing."""

    def test_from_twitter_like_event(self):
        """Test parsing Twitter favorite (like) event."""
        data = {
            "for_user_id": "12345",
            "favorite_events": [
                {
                    "id": 67890,
                    "id_str": "67890",
                    "user": {
                        "id": 11111,
                        "id_str": "11111",
                        "name": "Test User",
                        "screen_name": "testuser",
                    },
                    "created_at": "Wed Oct 10 20:19:24 +0000 2018",
                }
            ],
        }

        event = SocialEngagementEvent.from_twitter_webhook(data)

        assert event.platform == SocialPlatform.TWITTER
        assert event.event_type == SocialEventType.LIKE
        assert event.event_id == "67890"
        assert event.user_handle == "testuser"
        assert event.user_name == "Test User"

    def test_from_twitter_follow_event(self):
        """Test parsing Twitter follow event."""
        data = {
            "for_user_id": "12345",
            "follow_events": [
                {
                    "id": 99999,
                    "source": {
                        "id": 22222,
                        "name": "New Follower",
                        "screen_name": "newfollower",
                    },
                }
            ],
        }

        event = SocialEngagementEvent.from_twitter_webhook(data)

        assert event.event_type == SocialEventType.FOLLOW
        assert event.user_handle == "newfollower"

    def test_from_twitter_empty_events(self):
        """Test parsing Twitter webhook with no matching events."""
        data = {"for_user_id": "12345"}

        event = SocialEngagementEvent.from_twitter_webhook(data)

        assert event.event_type == SocialEventType.UNKNOWN
        assert event.user_id == "12345"

    def test_from_linkedin_like_event(self):
        """Test parsing LinkedIn like event."""
        data = {
            "type": "UGCPOST_LIKE",
            "activity": {
                "urn": "urn:li:activity:123456",
                "object": {"urn": "urn:li:ugcPost:789"},
            },
            "actor": {
                "urn": "urn:li:person:999",
                "name": {"localized": {"en_US": "LinkedIn User"}},
            },
        }

        event = SocialEngagementEvent.from_linkedin_webhook(data)

        assert event.platform == SocialPlatform.LINKEDIN
        assert event.event_type == SocialEventType.LIKE
        assert event.event_id == "urn:li:activity:123456"
        assert event.user_name == "LinkedIn User"
        assert event.post_id == "urn:li:ugcPost:789"

    def test_to_dict(self):
        """Test event serialization."""
        event = SocialEngagementEvent(
            platform=SocialPlatform.TWITTER,
            event_type=SocialEventType.MENTION,
            event_id="12345",
            post_id="67890",
            user_id="user_123",
            user_name="Test User",
            user_handle="testuser",
            content="Hey @ag3ntwerk check this out!",
            created_at=datetime(2024, 1, 15, 10, 30),
        )

        result = event.to_dict()

        assert result["platform"] == "twitter"
        assert result["event_type"] == "mention"
        assert result["user_handle"] == "testuser"


class TestSocialWebhookHandler:
    """Tests for SocialWebhookHandler."""

    @pytest.mark.asyncio
    async def test_process_twitter_like(self):
        """Test processing Twitter like event."""
        handler = SocialWebhookHandler()
        likes_received = []

        @handler.on_like
        async def capture_like(event):
            likes_received.append(event)

        data = {
            "for_user_id": "12345",
            "favorite_events": [
                {
                    "id": 67890,
                    "user": {
                        "id": 11111,
                        "name": "Liker",
                        "screen_name": "liker",
                    },
                }
            ],
        }

        event = await handler.process_twitter(data)

        assert len(likes_received) == 1
        assert likes_received[0].event_type == SocialEventType.LIKE

    @pytest.mark.asyncio
    async def test_process_linkedin_mention(self):
        """Test processing LinkedIn mention event."""
        handler = SocialWebhookHandler()
        mentions_received = []

        @handler.on_mention
        async def capture_mention(event):
            mentions_received.append(event)

        data = {
            "type": "SHARE_MENTION",
            "activity": {"urn": "urn:li:activity:123"},
            "actor": {
                "urn": "urn:li:person:456",
                "name": {"localized": {"en_US": "Mentioner"}},
            },
        }

        event = await handler.process_linkedin(data)

        assert len(mentions_received) == 1
        assert mentions_received[0].platform == SocialPlatform.LINKEDIN

    def test_twitter_crc_response(self):
        """Test Twitter CRC challenge-response generation."""
        handler = SocialWebhookHandler(twitter_consumer_secret="test_secret")

        crc_token = "test_crc_token"
        response = handler.generate_twitter_crc_response(crc_token)

        assert response.startswith("sha256=")

    def test_twitter_crc_response_no_secret(self):
        """Test CRC response fails without secret."""
        handler = SocialWebhookHandler()

        with pytest.raises(ValueError, match="not configured"):
            handler.generate_twitter_crc_response("token")

    def test_twitter_signature_verification(self):
        """Test Twitter signature verification."""
        import base64
        import hashlib
        import hmac

        secret = "test_secret"
        handler = SocialWebhookHandler(twitter_consumer_secret=secret)

        payload = b'{"test": "data"}'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
        sig_header = f"sha256={base64.b64encode(sig).decode()}"

        assert handler.verify_twitter_signature(payload, sig_header)
        assert not handler.verify_twitter_signature(payload, "sha256=wrong")
