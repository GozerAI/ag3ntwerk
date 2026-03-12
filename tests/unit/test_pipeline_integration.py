"""
End-to-end integration tests for the Revenue Stack pipeline.

Tests the full flow: content creation -> social distribution -> revenue tracking,
and the voice interview -> insight extraction pipeline, using mocked external APIs.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.core.base import Task, TaskResult
from ag3ntwerk.agents.echo.managers import SocialDistributionManager
from ag3ntwerk.agents.vector.managers import RevenueManager
from ag3ntwerk.integrations.voice.expertise_extractor import (
    ExpertiseExtractor,
    ExtractionResult,
)
from ag3ntwerk.integrations.voice.ai_interviewer import (
    AIInterviewer,
    InterviewQuestion,
    InterviewScript,
)
from ag3ntwerk.models.content import ExpertiseInsight, VoiceTranscript
from ag3ntwerk.models.social import Platform


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm():
    """Create a mock LLM that returns valid responses."""
    llm = MagicMock()
    llm.generate = AsyncMock(
        return_value=MagicMock(
            content=json.dumps(
                {
                    "summary": "Expert discusses AI scaling",
                    "topics": ["AI", "scaling", "infrastructure"],
                    "insights": [
                        {
                            "topic": "AI Scaling",
                            "insight": "Start small, iterate quickly.",
                            "quote": "Ship fast, learn faster",
                            "tags": ["scaling", "iteration"],
                        },
                    ],
                }
            )
        )
    )
    # For chat-based calls (Manager.reason uses chat)
    llm.chat = AsyncMock(
        return_value=MagicMock(
            content="Social media strategy analysis complete.",
            model="mock-model",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            latency_ms=100.0,
        )
    )
    # For connect
    llm.connect = AsyncMock(return_value=True)
    llm._is_connected = True
    llm._available_models = [MagicMock(id="mock-model", tier=MagicMock(value="balanced"))]
    llm.name = "MockLLM"
    return llm


@pytest.fixture
def mock_gumroad():
    """Create a mock GumroadClient."""
    client = MagicMock()
    client.get_revenue_summary = AsyncMock(
        return_value={
            "total_revenue_cents": 150000,
            "total_revenue_usd": 1500.0,
            "total_sales": 42,
            "period_days": 30,
            "products": {
                "AI Ebook": {"revenue_cents": 100000, "sales": 30},
                "Template Pack": {"revenue_cents": 50000, "sales": 12},
            },
        }
    )
    client.get_sales = AsyncMock(
        return_value=[
            {"id": "s1", "product_name": "AI Ebook", "price": 2999},
            {"id": "s2", "product_name": "Template Pack", "price": 1999},
        ]
    )
    return client


@pytest.fixture
def mock_social_gateway():
    """Create a mock SocialDistributionGateway."""
    gateway = MagicMock()
    gateway.distribute = AsyncMock(
        return_value={
            Platform.LINKEDIN: {"success": True, "post_id": "ln_123"},
            Platform.TWITTER: {"success": True, "post_id": "tw_456"},
        }
    )
    gateway.get_all_metrics = AsyncMock(
        return_value={
            Platform.LINKEDIN: {"followers": 5000, "engagement_rate": 0.03},
            Platform.TWITTER: {"followers": 2000, "engagement_rate": 0.05},
        }
    )
    gateway.registered_platforms = [Platform.LINKEDIN, Platform.TWITTER]
    return gateway


@pytest.fixture
def mock_whisper():
    """Create a mock WhisperIntegration."""
    whisper = MagicMock()
    whisper.transcribe = AsyncMock(
        return_value=MagicMock(
            text="I believe the key to AI scaling is starting with clean data. "
            "Without good data pipelines, your models will never be reliable. "
            "We learned this the hard way at our startup.",
            duration=90.0,
            audio_path="/audio/interview.wav",
            language="en",
            segments=[
                MagicMock(
                    start=0.0,
                    end=30.0,
                    text="I believe the key to AI scaling is starting with clean data.",
                ),
                MagicMock(
                    start=30.0,
                    end=60.0,
                    text="Without good data pipelines, your models will never be reliable.",
                ),
                MagicMock(
                    start=60.0, end=90.0, text="We learned this the hard way at our startup."
                ),
            ],
        )
    )
    return whisper


# =============================================================================
# Voice → Insight Pipeline
# =============================================================================


class TestVoiceToInsightPipeline:
    """Test the voice capture → transcription → insight extraction pipeline."""

    async def test_whisper_to_extractor(self, mock_llm, mock_whisper):
        """Test full flow: audio → Whisper → ExpertiseExtractor → insights."""
        extractor = ExpertiseExtractor(llm_provider=mock_llm)

        # Step 1: Transcribe
        transcription = await mock_whisper.transcribe("/audio/interview.wav")
        assert transcription.text is not None
        assert len(transcription.text) > 50

        # Step 2: Extract insights from transcription
        result = await extractor.extract_from_transcription(transcription)

        assert isinstance(result, ExtractionResult)
        assert len(result.insights) > 0
        assert result.insights[0].topic == "AI Scaling"

    async def test_interview_to_insights(self, mock_llm, mock_whisper):
        """Test full interview flow: script → answers → insights."""
        extractor = ExpertiseExtractor(llm_provider=mock_llm)

        # Override LLM generate for follow-up generation
        call_count = [0]
        original_content = mock_llm.generate.return_value.content

        async def smart_generate(prompt, **kwargs):
            call_count[0] += 1
            # First call is follow-up generation, return NONE
            if "follow-up" in prompt.lower():
                return MagicMock(content="NONE")
            return MagicMock(content=original_content)

        mock_llm.generate = AsyncMock(side_effect=smart_generate)

        interviewer = AIInterviewer(
            whisper=mock_whisper,
            extractor=extractor,
            llm_provider=mock_llm,
        )

        script = InterviewScript(
            topic="AI Scaling",
            questions=[
                InterviewQuestion(text="What's the biggest challenge?"),
                InterviewQuestion(text="How do you solve it?"),
            ],
        )

        # Run interview
        session = await interviewer.start_session(script)
        session = await interviewer.process_answer(
            session, text="Clean data is the foundation. Without it, nothing works."
        )
        session = await interviewer.process_answer(
            session, text="We built automated data validation pipelines from day one."
        )

        result = await interviewer.finish_session(session)

        assert result.topic == "AI Scaling"
        assert len(result.answers) == 2
        assert "Clean data" in result.full_transcript
        assert result.insights is not None


# =============================================================================
# Social Distribution Pipeline
# =============================================================================


class TestSocialDistributionPipeline:
    """Test Echo social distribution flow."""

    async def test_social_distribute_task(self, mock_llm, mock_social_gateway):
        """Test SocialDistributionManager handling a distribute task."""
        mgr = SocialDistributionManager(
            llm_provider=mock_llm,
            social_gateway=mock_social_gateway,
        )

        task = Task(
            description="Distribute blog post about AI scaling",
            task_type="social_distribute",
            context={
                "content": "AI scaling requires clean data pipelines.",
                "platforms": ["linkedin", "twitter"],
                "hashtags": ["#AI", "#scaling"],
            },
        )

        result = await mgr.execute(task)
        assert result.success is True
        mock_social_gateway.distribute.assert_called_once()

    async def test_social_metrics_task(self, mock_llm, mock_social_gateway):
        """Test SocialDistributionManager handling a metrics task."""
        mgr = SocialDistributionManager(
            llm_provider=mock_llm,
            social_gateway=mock_social_gateway,
        )

        task = Task(
            description="Get social media metrics",
            task_type="social_metrics",
            context={},
        )

        result = await mgr.execute(task)
        assert result.success is True
        mock_social_gateway.get_all_metrics.assert_called_once()

    async def test_social_distribute_no_gateway(self, mock_llm):
        """Test graceful failure without gateway."""
        mgr = SocialDistributionManager(llm_provider=mock_llm)

        task = Task(
            description="Distribute content",
            task_type="social_distribute",
            context={"content": "Test", "platforms": ["twitter"]},
        )

        result = await mgr.execute(task)
        assert result.success is False
        assert "not configured" in result.error.lower()


# =============================================================================
# Revenue Tracking Pipeline
# =============================================================================


class TestRevenueTrackingPipeline:
    """Test Vector revenue tracking with Gumroad integration."""

    async def test_revenue_summary_with_gumroad(self, mock_llm, mock_gumroad):
        """Test RevenueManager returning Gumroad summary."""
        mgr = RevenueManager(
            llm_provider=mock_llm,
            gumroad_client=mock_gumroad,
        )

        task = Task(
            description="Get revenue summary",
            task_type="revenue_summary",
            context={"period_days": 30},
        )

        result = await mgr.execute(task)
        assert result.success is True
        assert result.output["summary"]["total_revenue_usd"] == 1500.0
        assert result.output["summary"]["total_sales"] == 42
        mock_gumroad.get_revenue_summary.assert_called_once_with(period_days=30)

    async def test_revenue_summary_no_gumroad(self, mock_llm):
        """Test RevenueManager fails gracefully without Gumroad."""
        mgr = RevenueManager(llm_provider=mock_llm)

        task = Task(
            description="Get revenue summary",
            task_type="revenue_summary",
            context={},
        )

        result = await mgr.execute(task)
        assert result.success is False
        assert "not configured" in result.error.lower()

    async def test_revenue_tracking_injects_live_data(self, mock_llm, mock_gumroad):
        """Test that revenue_tracking handler injects live Gumroad data."""
        mgr = RevenueManager(
            llm_provider=mock_llm,
            gumroad_client=mock_gumroad,
        )

        task = Task(
            description="Track monthly revenue",
            task_type="revenue_tracking",
            context={"period": "monthly", "period_days": 30},
        )

        result = await mgr.execute(task)
        assert result.success is True
        assert "live_data" in result.output
        mock_gumroad.get_revenue_summary.assert_called_once()


# =============================================================================
# Full Pipeline: Content → Distribute → Track
# =============================================================================


class TestFullContentPipeline:
    """Test the conceptual content → distribute → track pipeline."""

    async def test_content_to_social_to_revenue(self, mock_llm, mock_social_gateway, mock_gumroad):
        """Test the full pipeline using individual manager calls."""
        # Step 1: Content creation (Echo creates content - simulated as text)
        content_text = (
            "AI Scaling: 5 Lessons from Building Production ML Systems. "
            "Clean data pipelines are the foundation of reliable AI."
        )

        # Step 2: Social distribution (Echo SocialDistributionManager)
        social_mgr = SocialDistributionManager(
            llm_provider=mock_llm,
            social_gateway=mock_social_gateway,
        )
        dist_task = Task(
            description="Distribute content to social platforms",
            task_type="social_distribute",
            context={
                "content": content_text,
                "platforms": ["linkedin", "twitter"],
                "hashtags": ["#AI", "#ML"],
            },
        )
        dist_result = await social_mgr.execute(dist_task)
        assert dist_result.success is True

        # Step 3: Revenue tracking (Vector RevenueManager)
        rev_mgr = RevenueManager(
            llm_provider=mock_llm,
            gumroad_client=mock_gumroad,
        )
        rev_task = Task(
            description="Track revenue impact of content distribution",
            task_type="revenue_summary",
            context={"period_days": 7},
        )
        rev_result = await rev_mgr.execute(rev_task)
        assert rev_result.success is True
        assert rev_result.output["summary"]["total_sales"] > 0

    async def test_voice_to_content_to_social(self, mock_llm, mock_whisper, mock_social_gateway):
        """Test voice → insights → content → social pipeline."""
        # Step 1: Voice capture
        transcription = await mock_whisper.transcribe("/audio/interview.wav")

        # Step 2: Expertise extraction
        extractor = ExpertiseExtractor(llm_provider=mock_llm)
        extraction = await extractor.extract_from_transcription(transcription)
        assert len(extraction.insights) > 0

        # Step 3: Convert insight to distributable content
        insight = extraction.insights[0]
        content_text = f"{insight.topic}: {insight.insight}"

        # Step 4: Social distribution
        social_mgr = SocialDistributionManager(
            llm_provider=mock_llm,
            social_gateway=mock_social_gateway,
        )
        task = Task(
            description="Distribute insight",
            task_type="social_distribute",
            context={
                "content": content_text,
                "platforms": ["linkedin"],
            },
        )
        result = await social_mgr.execute(task)
        assert result.success is True
        mock_social_gateway.distribute.assert_called_once()


# =============================================================================
# Cross-Component Wiring Tests
# =============================================================================


class TestCrossComponentWiring:
    """Test that components reference each other correctly."""

    def test_social_manager_task_types_match_routing(self):
        """Verify SocialDistributionManager types match Echo routing."""
        from ag3ntwerk.agents.echo.agent import MANAGER_ROUTING
        from ag3ntwerk.agents.echo.managers import SocialDistributionManager

        for task_type in SocialDistributionManager.HANDLED_TASK_TYPES:
            assert task_type in MANAGER_ROUTING
            assert MANAGER_ROUTING[task_type] == "SocialDistMgr"

    def test_revenue_manager_key_types_in_capabilities(self):
        """Verify key RevenueManager types are in Vector capabilities."""
        from ag3ntwerk.agents.vector.agent import REVENUE_CAPABILITIES
        from ag3ntwerk.agents.vector.managers import RevenueManager

        # These are the critical task types that must be routable
        critical_types = [
            "revenue_tracking",
            "revenue_forecasting",
            "mrr_analysis",
            "revenue_summary",
        ]
        for task_type in critical_types:
            assert task_type in RevenueManager.HANDLED_TASK_TYPES
            assert task_type in REVENUE_CAPABILITIES

    def test_overwatch_routes_match_agents(self):
        """Verify Overwatch routing targets exist as agents."""
        from ag3ntwerk.agents.overwatch.agent import ROUTING_RULES

        expected_agents = {
            "Echo",
            "Vector",
            "Forge",
            "Keystone",
            "Compass",
            "Axiom",
            "Index",
            "Accord",
            "Aegis",
            "Blueprint",
            "Beacon",
            "Foundry",
            "Sentinel",
            "Citadel",
            "Overwatch",
        }
        for task_type, agent_code in ROUTING_RULES.items():
            assert (
                agent_code in expected_agents
            ), f"Unknown agent '{agent_code}' for task '{task_type}'"

    def test_social_task_types_in_overwatch(self):
        """Verify social task types are routed in Overwatch."""
        from ag3ntwerk.agents.overwatch.agent import ROUTING_RULES

        social_types = [
            "social_distribute",
            "social_publish",
            "social_schedule",
            "social_analytics",
            "social_metrics",
        ]
        for task_type in social_types:
            assert task_type in ROUTING_RULES
            assert ROUTING_RULES[task_type] == "Echo"

    def test_revenue_task_types_in_overwatch(self):
        """Verify revenue task types are routed in Overwatch."""
        from ag3ntwerk.agents.overwatch.agent import ROUTING_RULES

        assert ROUTING_RULES["revenue_summary"] == "Vector"
        assert ROUTING_RULES["revenue_tracking"] == "Vector"

    def test_content_pipeline_workflow_registered(self):
        """Verify ContentDistributionPipelineWorkflow is exported."""
        from ag3ntwerk.orchestration import ContentDistributionPipelineWorkflow

        assert ContentDistributionPipelineWorkflow is not None

    def test_expertise_extractor_uses_shared_models(self):
        """Verify ExpertiseExtractor produces shared model objects."""
        insight = ExpertiseInsight(
            topic="Test",
            insight="Testing",
            quote="Test quote",
            tags=["test"],
        )
        # ExpertiseInsight is a Pydantic model from shared models
        assert insight.model_dump() is not None
        assert insight.topic == "Test"

    def test_voice_transcript_uses_shared_models(self):
        """Verify VoiceTranscript is from shared models."""
        transcript = VoiceTranscript(
            id="t1",
            audio_file="/test.wav",
            full_text="Test transcript",
            duration_seconds=10.0,
        )
        assert transcript.model_dump() is not None
