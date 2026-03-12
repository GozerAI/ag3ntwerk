"""
Unit tests for shared Pydantic models (social, revenue, content).
"""

import pytest
from datetime import date, datetime, timezone

from ag3ntwerk.models.social import (
    Platform,
    PostStatus,
    SocialPost,
    Campaign,
    ContentCalendar,
)
from ag3ntwerk.models.revenue import (
    RevenueType,
    RevenueRecord,
    MRRSnapshot,
    RevenueMetrics,
)
from ag3ntwerk.models.content import (
    ContentFormat,
    ContentPiece,
    VoiceTranscript,
    ExpertiseInsight,
)


# =============================================================================
# Social Models
# =============================================================================


class TestPlatformEnum:
    """Tests for Platform enum."""

    def test_all_platforms_exist(self):
        assert Platform.LINKEDIN == "linkedin"
        assert Platform.TWITTER == "twitter"
        assert Platform.FACEBOOK == "facebook"
        assert Platform.INSTAGRAM == "instagram"
        assert Platform.BLUESKY == "bluesky"
        assert Platform.MEDIUM == "medium"


class TestSocialPost:
    """Tests for SocialPost model."""

    def test_minimal_creation(self):
        post = SocialPost(platform=Platform.LINKEDIN, content="Hello world")
        assert post.platform == Platform.LINKEDIN
        assert post.content == "Hello world"
        assert post.status == PostStatus.DRAFT
        assert post.media_urls == []
        assert post.hashtags == []
        assert post.post_id is None

    def test_full_creation(self):
        post = SocialPost(
            platform=Platform.TWITTER,
            content="Check out our product!",
            media_urls=["https://example.com/img.png"],
            link="https://example.com",
            hashtags=["#startup", "#saas"],
            mentions=["@user1"],
            status=PostStatus.PUBLISHED,
            post_id="tweet_123",
            post_url="https://twitter.com/i/status/tweet_123",
            campaign_id="camp_1",
            source_content_id="content_1",
        )
        assert post.post_id == "tweet_123"
        assert len(post.hashtags) == 2
        assert post.campaign_id == "camp_1"

    def test_created_at_auto_populated(self):
        post = SocialPost(platform=Platform.LINKEDIN, content="Test")
        assert post.created_at is not None
        assert post.created_at.tzinfo == timezone.utc

    def test_serialization_roundtrip(self):
        post = SocialPost(
            platform=Platform.TWITTER,
            content="Test content",
            hashtags=["#test"],
        )
        data = post.model_dump()
        restored = SocialPost(**data)
        assert restored.platform == post.platform
        assert restored.content == post.content
        assert restored.hashtags == post.hashtags


class TestCampaign:
    """Tests for Campaign model."""

    def test_creation(self):
        campaign = Campaign(
            id="camp_1",
            name="Launch Campaign",
            objective="awareness",
            platforms=[Platform.LINKEDIN, Platform.TWITTER],
            start_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        assert campaign.id == "camp_1"
        assert len(campaign.platforms) == 2
        assert campaign.impressions == 0

    def test_defaults(self):
        campaign = Campaign(
            id="camp_2",
            name="Test",
            objective="engagement",
            start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        assert campaign.status == "draft"
        assert campaign.posts == []
        assert campaign.conversions == 0


class TestContentCalendar:
    """Tests for ContentCalendar model."""

    def test_creation(self):
        cal = ContentCalendar(
            id="cal_1",
            name="Q1 Calendar",
            posts_per_week={Platform.LINKEDIN: 3, Platform.TWITTER: 7},
        )
        assert cal.posts_per_week[Platform.LINKEDIN] == 3
        assert len(cal.posts) == 0


# =============================================================================
# Revenue Models
# =============================================================================


class TestRevenueRecord:
    """Tests for RevenueRecord model."""

    def test_creation_with_cents(self):
        record = RevenueRecord(
            id="sale_1",
            amount_cents=4999,
            product_id="prod_abc",
            product_name="E-book",
            platform="gumroad",
            transaction_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        )
        assert record.amount_cents == 4999
        assert record.amount_usd == 49.99
        assert record.revenue_type == RevenueType.ONE_TIME
        assert record.refunded is False

    def test_usd_auto_computed(self):
        record = RevenueRecord(
            id="sale_2",
            amount_cents=10000,
            product_id="prod_xyz",
            product_name="Course",
            platform="stripe",
            transaction_date=datetime(2026, 1, 20, tzinfo=timezone.utc),
        )
        assert record.amount_usd == 100.0

    def test_explicit_usd_not_overwritten(self):
        record = RevenueRecord(
            id="sale_3",
            amount_cents=5000,
            amount_usd=55.0,  # Explicit, different from cents/100
            product_id="prod_1",
            product_name="Widget",
            platform="manual",
            transaction_date=datetime(2026, 1, 25, tzinfo=timezone.utc),
        )
        assert record.amount_usd == 55.0

    def test_subscription_type(self):
        record = RevenueRecord(
            id="sub_1",
            amount_cents=2999,
            product_id="prod_sub",
            product_name="Pro Plan",
            platform="stripe",
            revenue_type=RevenueType.SUBSCRIPTION,
            transaction_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert record.revenue_type == RevenueType.SUBSCRIPTION


class TestMRRSnapshot:
    """Tests for MRRSnapshot model."""

    def test_creation(self):
        snap = MRRSnapshot(
            date=date(2026, 1, 1),
            mrr=5000.0,
            new_mrr=1200.0,
            churned_mrr=300.0,
            net_new_mrr=900.0,
            total_customers=50,
            new_customers=12,
            churned_customers=3,
        )
        assert snap.mrr == 5000.0
        assert snap.net_new_mrr == 900.0

    def test_defaults(self):
        snap = MRRSnapshot(date=date(2026, 2, 1), mrr=0.0)
        assert snap.new_mrr == 0.0
        assert snap.total_customers == 0


class TestRevenueMetrics:
    """Tests for RevenueMetrics model."""

    def test_creation(self):
        metrics = RevenueMetrics(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            total_revenue_usd=15000.0,
            transaction_count=120,
            average_order_value=125.0,
            by_product={"ebook": 5000.0, "course": 10000.0},
            by_platform={"gumroad": 12000.0, "stripe": 3000.0},
        )
        assert metrics.total_revenue_usd == 15000.0
        assert metrics.by_product["ebook"] == 5000.0
        assert metrics.growth_rate is None


# =============================================================================
# Content Models
# =============================================================================


class TestContentPiece:
    """Tests for ContentPiece model."""

    def test_creation(self):
        piece = ContentPiece(
            id="cp_1",
            title="How to Scale SaaS Revenue",
            body="Full article body here...",
            format=ContentFormat.ARTICLE,
            author="Echo",
            tags=["saas", "revenue"],
            keywords=["saas scaling", "revenue growth"],
            summary="A guide to scaling SaaS revenue.",
        )
        assert piece.id == "cp_1"
        assert piece.format == ContentFormat.ARTICLE
        assert len(piece.tags) == 2

    def test_ebook_format(self):
        piece = ContentPiece(
            id="cp_2",
            title="The Complete Guide",
            body="Chapter 1...",
            format=ContentFormat.EBOOK,
        )
        assert piece.format == ContentFormat.EBOOK

    def test_marketplace_product(self):
        piece = ContentPiece(
            id="cp_3",
            title="Premium Content",
            body="Premium body...",
            marketplace_product_id="gumroad_prod_123",
        )
        assert piece.marketplace_product_id == "gumroad_prod_123"


class TestVoiceTranscript:
    """Tests for VoiceTranscript model."""

    def test_creation(self):
        transcript = VoiceTranscript(
            id="vt_1",
            audio_file="/recordings/interview.wav",
            full_text="This is the full transcription text.",
            duration_seconds=1800.0,
            language="en",
            segments=[
                {"start": 0.0, "end": 5.0, "text": "Hello"},
                {"start": 5.0, "end": 10.0, "text": "Welcome"},
            ],
        )
        assert transcript.duration_seconds == 1800.0
        assert len(transcript.segments) == 2

    def test_defaults(self):
        transcript = VoiceTranscript(
            id="vt_2",
            audio_file="/test.wav",
            full_text="Short.",
            duration_seconds=5.0,
        )
        assert transcript.language == "en"
        assert transcript.segments == []


class TestExpertiseInsight:
    """Tests for ExpertiseInsight model."""

    def test_creation(self):
        insight = ExpertiseInsight(
            topic="SaaS Pricing",
            insight="Value-based pricing outperforms cost-plus in B2B SaaS.",
            quote="Price on value, not cost.",
            tags=["pricing", "saas", "b2b"],
            source_transcript_id="vt_1",
        )
        assert insight.topic == "SaaS Pricing"
        assert len(insight.tags) == 3
        assert insight.source_transcript_id == "vt_1"


# =============================================================================
# Package-level imports
# =============================================================================


class TestPackageImports:
    """Test that the models package __init__.py exports work."""

    def test_import_from_models(self):
        from ag3ntwerk.models import (
            Platform,
            SocialPost,
            Campaign,
            ContentCalendar,
            RevenueType,
            RevenueRecord,
            MRRSnapshot,
            RevenueMetrics,
            ContentFormat,
            ContentPiece,
            VoiceTranscript,
            ExpertiseInsight,
        )

        # Just verify they imported without error
        assert Platform is not None
        assert SocialPost is not None
        assert RevenueRecord is not None
        assert ContentPiece is not None
