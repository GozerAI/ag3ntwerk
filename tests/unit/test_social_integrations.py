"""
Unit tests for social integration layer (gateway, clients).

All HTTP calls are mocked - no real API access needed.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from ag3ntwerk.models.social import Platform, PostStatus, SocialPost
from ag3ntwerk.integrations.social.base import SocialClient
from ag3ntwerk.integrations.social.gateway import (
    SocialDistributionGateway,
    PLATFORM_LIMITS,
    PLATFORM_TONES,
)


# =============================================================================
# Fixtures
# =============================================================================


class FakeSocialClient(SocialClient):
    """Concrete test implementation of SocialClient."""

    def __init__(self, platform: Platform):
        self.platform = platform
        self._authenticated = False
        self.published: list = []
        self.scheduled: list = []

    async def authenticate(self) -> bool:
        self._authenticated = True
        return True

    async def publish(self, post: SocialPost) -> dict:
        self.published.append(post)
        return {
            "success": True,
            "post_id": f"{self.platform.value}_post_123",
            "post_url": f"https://{self.platform.value}.com/post/123",
        }

    async def schedule(self, post: SocialPost) -> dict:
        self.scheduled.append(post)
        return {
            "success": True,
            "scheduled": True,
            "scheduled_time": post.scheduled_time.isoformat() if post.scheduled_time else None,
        }

    async def get_analytics(self, post_id: str) -> dict:
        return {"likes": 42, "comments": 5, "shares": 10}

    async def delete(self, post_id: str) -> bool:
        return True

    async def get_profile_metrics(self) -> dict:
        return {"followers": 1000, "platform": self.platform.value}


@pytest.fixture
def linkedin_client():
    return FakeSocialClient(Platform.LINKEDIN)


@pytest.fixture
def twitter_client():
    return FakeSocialClient(Platform.TWITTER)


@pytest.fixture
def gateway(linkedin_client, twitter_client):
    gw = SocialDistributionGateway()
    gw.register_client(linkedin_client)
    gw.register_client(twitter_client)
    return gw


# =============================================================================
# SocialDistributionGateway Tests
# =============================================================================


class TestGatewayRegistration:
    """Tests for client registration."""

    def test_register_client(self, linkedin_client):
        gw = SocialDistributionGateway()
        gw.register_client(linkedin_client)
        assert Platform.LINKEDIN in gw.registered_platforms

    def test_register_multiple_clients(self, linkedin_client, twitter_client):
        gw = SocialDistributionGateway()
        gw.register_client(linkedin_client)
        gw.register_client(twitter_client)
        assert len(gw.registered_platforms) == 2

    def test_registered_platforms_property(self, gateway):
        assert Platform.LINKEDIN in gateway.registered_platforms
        assert Platform.TWITTER in gateway.registered_platforms


class TestGatewayInitialization:
    """Tests for gateway initialization."""

    async def test_initialize_authenticates_all(self, gateway, linkedin_client, twitter_client):
        await gateway.initialize()
        assert linkedin_client._authenticated is True
        assert twitter_client._authenticated is True

    async def test_initialize_handles_auth_failure(self):
        gw = SocialDistributionGateway()
        failing_client = FakeSocialClient(Platform.LINKEDIN)
        failing_client.authenticate = AsyncMock(side_effect=ValueError("Bad token"))
        gw.register_client(failing_client)

        # Should not raise, just log warning
        await gw.initialize()


class TestGatewayDistribute:
    """Tests for content distribution."""

    async def test_distribute_single_platform(self, gateway, linkedin_client):
        post = SocialPost(platform=Platform.LINKEDIN, content="Test post")
        results = await gateway.distribute(post, adapt_content=False)

        assert Platform.LINKEDIN in results
        assert results[Platform.LINKEDIN]["success"] is True
        assert len(linkedin_client.published) == 1

    async def test_distribute_multi_platform(self, gateway, linkedin_client, twitter_client):
        post = SocialPost(platform=Platform.LINKEDIN, content="Multi-platform post")
        results = await gateway.distribute(
            post,
            platforms=[Platform.LINKEDIN, Platform.TWITTER],
            adapt_content=False,
        )

        assert results[Platform.LINKEDIN]["success"] is True
        assert results[Platform.TWITTER]["success"] is True
        assert len(linkedin_client.published) == 1
        assert len(twitter_client.published) == 1

    async def test_distribute_unregistered_platform(self, gateway):
        post = SocialPost(platform=Platform.INSTAGRAM, content="Insta post")
        results = await gateway.distribute(
            post,
            platforms=[Platform.INSTAGRAM],
            adapt_content=False,
        )

        assert results[Platform.INSTAGRAM]["success"] is False
        assert "No client registered" in results[Platform.INSTAGRAM]["error"]

    async def test_distribute_scheduled_post(self, gateway, linkedin_client):
        future_time = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
        post = SocialPost(
            platform=Platform.LINKEDIN,
            content="Scheduled post",
            scheduled_time=future_time,
        )
        results = await gateway.distribute(post, adapt_content=False)

        assert results[Platform.LINKEDIN]["success"] is True
        assert len(linkedin_client.scheduled) == 1

    async def test_distribute_defaults_to_post_platform(self, gateway, linkedin_client):
        post = SocialPost(platform=Platform.LINKEDIN, content="Default platform")
        results = await gateway.distribute(post, adapt_content=False)

        assert Platform.LINKEDIN in results
        assert len(results) == 1

    async def test_distribute_handles_client_error(self, gateway):
        failing_client = FakeSocialClient(Platform.LINKEDIN)
        failing_client.publish = AsyncMock(side_effect=RuntimeError("API down"))
        gateway._clients[Platform.LINKEDIN] = failing_client

        post = SocialPost(platform=Platform.LINKEDIN, content="Will fail")
        results = await gateway.distribute(post, adapt_content=False)

        assert results[Platform.LINKEDIN]["success"] is False
        assert "API down" in results[Platform.LINKEDIN]["error"]


class TestGatewayContentAdaptation:
    """Tests for LLM-based content adaptation."""

    async def test_adapt_with_llm(self, linkedin_client, twitter_client):
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="Adapted tweet content #startup")

        gw = SocialDistributionGateway(llm_provider=mock_llm)
        gw.register_client(linkedin_client)
        gw.register_client(twitter_client)

        post = SocialPost(platform=Platform.LINKEDIN, content="Long LinkedIn post...")
        results = await gw.distribute(
            post,
            platforms=[Platform.LINKEDIN, Platform.TWITTER],
            adapt_content=True,
        )

        # LinkedIn gets original (same platform), Twitter gets adapted
        assert results[Platform.LINKEDIN]["success"] is True
        assert results[Platform.TWITTER]["success"] is True
        # LLM should have been called for Twitter adaptation
        mock_llm.generate.assert_called_once()

    async def test_no_adapt_without_llm(self, gateway, linkedin_client, twitter_client):
        post = SocialPost(platform=Platform.LINKEDIN, content="Original content")
        results = await gateway.distribute(
            post,
            platforms=[Platform.LINKEDIN, Platform.TWITTER],
            adapt_content=True,
        )

        # Without LLM, both get original content
        assert results[Platform.LINKEDIN]["success"] is True
        assert results[Platform.TWITTER]["success"] is True


class TestGatewayMetrics:
    """Tests for metrics retrieval."""

    async def test_get_all_metrics(self, gateway):
        metrics = await gateway.get_all_metrics()

        assert Platform.LINKEDIN in metrics
        assert Platform.TWITTER in metrics
        assert metrics[Platform.LINKEDIN]["followers"] == 1000

    async def test_get_post_analytics(self, gateway):
        analytics = await gateway.get_post_analytics("post_123", Platform.LINKEDIN)

        assert analytics["likes"] == 42
        assert analytics["comments"] == 5

    async def test_get_analytics_unregistered(self, gateway):
        result = await gateway.get_post_analytics("post_1", Platform.INSTAGRAM)
        assert "error" in result


# =============================================================================
# Platform Limits Configuration
# =============================================================================


class TestPlatformConfig:
    """Tests for platform limits and tones."""

    def test_twitter_char_limit(self):
        assert PLATFORM_LIMITS[Platform.TWITTER]["chars"] == 280

    def test_linkedin_char_limit(self):
        assert PLATFORM_LIMITS[Platform.LINKEDIN]["chars"] == 3000

    def test_all_platforms_have_tones(self):
        for platform in [Platform.LINKEDIN, Platform.TWITTER, Platform.INSTAGRAM]:
            assert platform in PLATFORM_TONES


# =============================================================================
# LinkedInClient Tests (mocked HTTP)
# =============================================================================


class TestLinkedInClient:
    """Tests for LinkedIn client with mocked HTTP."""

    async def test_authenticate_success(self):
        from ag3ntwerk.integrations.social.linkedin import LinkedInClient

        client = LinkedInClient(
            access_token="test_token",
            person_urn="urn:li:person:123",
        )

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await client.authenticate()
            assert result is True

    async def test_authenticate_missing_token(self):
        from ag3ntwerk.integrations.social.linkedin import LinkedInClient

        client = LinkedInClient(access_token=None)

        with pytest.raises(ValueError, match="LINKEDIN_ACCESS_TOKEN"):
            await client.authenticate()

    async def test_publish_success(self):
        from ag3ntwerk.integrations.social.linkedin import LinkedInClient

        client = LinkedInClient(
            access_token="test_token",
            person_urn="urn:li:person:123",
        )

        post = SocialPost(platform=Platform.LINKEDIN, content="Test LinkedIn post")

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 201
            mock_resp.json.return_value = {"id": "urn:li:ugcPost:456"}
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await client.publish(post)
            assert result["success"] is True
            assert result["post_id"] == "urn:li:ugcPost:456"

    async def test_schedule_returns_local_scheduler_flag(self):
        from ag3ntwerk.integrations.social.linkedin import LinkedInClient

        client = LinkedInClient(access_token="test_token", person_urn="urn:li:person:123")
        post = SocialPost(
            platform=Platform.LINKEDIN,
            content="Scheduled",
            scheduled_time=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )

        result = await client.schedule(post)
        assert result["requires_local_scheduler"] is True

    def test_platform_is_linkedin(self):
        from ag3ntwerk.integrations.social.linkedin import LinkedInClient

        client = LinkedInClient(access_token="test_token", person_urn="urn:li:person:123")
        assert client.platform == Platform.LINKEDIN


# =============================================================================
# TwitterClient Tests (mocked HTTP)
# =============================================================================


class TestTwitterClient:
    """Tests for Twitter client with mocked HTTP."""

    async def test_authenticate_success(self):
        from ag3ntwerk.integrations.social.twitter import TwitterClient

        client = TwitterClient(bearer_token="test_token")

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"data": {"id": "user_123"}}
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await client.authenticate()
            assert result is True
            assert client._user_id == "user_123"

    async def test_authenticate_missing_token(self):
        from ag3ntwerk.integrations.social.twitter import TwitterClient

        client = TwitterClient(bearer_token=None)

        with pytest.raises(ValueError, match="TWITTER_BEARER_TOKEN"):
            await client.authenticate()

    async def test_publish_short_tweet(self):
        from ag3ntwerk.integrations.social.twitter import TwitterClient

        client = TwitterClient(bearer_token="test_token")
        post = SocialPost(platform=Platform.TWITTER, content="Short tweet!")

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 201
            mock_resp.json.return_value = {"data": {"id": "tweet_789"}}
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await client.publish(post)
            assert result["success"] is True
            assert result["post_id"] == "tweet_789"

    def test_split_into_tweets_short(self):
        from ag3ntwerk.integrations.social.twitter import TwitterClient

        chunks = TwitterClient._split_into_tweets("Short content")
        assert len(chunks) == 1
        assert chunks[0] == "Short content"

    def test_split_into_tweets_long(self):
        from ag3ntwerk.integrations.social.twitter import TwitterClient

        long_content = " ".join(["word"] * 100)  # ~500 chars
        chunks = TwitterClient._split_into_tweets(long_content)
        assert len(chunks) > 1
        # Each chunk should have thread numbering
        assert "(1/" in chunks[0]

    def test_split_respects_max_length(self):
        from ag3ntwerk.integrations.social.twitter import TwitterClient

        long_content = " ".join(["abcdefghijklmnop"] * 30)  # ~500 chars
        chunks = TwitterClient._split_into_tweets(long_content, max_len=275)
        for chunk in chunks:
            assert len(chunk) <= 285  # 275 + thread numbering overhead

    def test_platform_is_twitter(self):
        from ag3ntwerk.integrations.social.twitter import TwitterClient

        client = TwitterClient(bearer_token="test_token")
        assert client.platform == Platform.TWITTER
