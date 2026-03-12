"""
Tests for ExpertiseExtractor and voice capture integration.

Phase 4: Voice Capture Integration tests.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.integrations.voice.expertise_extractor import (
    ExpertiseExtractor,
    ExtractionResult,
)
from ag3ntwerk.models.content import ExpertiseInsight, VoiceTranscript


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm():
    """Create mock LLM provider that returns valid extraction JSON."""
    llm = MagicMock()
    llm.generate = AsyncMock(
        return_value=MagicMock(
            content=json.dumps(
                {
                    "summary": "Discussion about scaling AI startups",
                    "topics": ["AI", "startups", "scaling", "infrastructure"],
                    "insights": [
                        {
                            "topic": "AI Scaling",
                            "insight": "Start with a single model and optimize before adding complexity.",
                            "quote": "One model, well-tuned, beats five mediocre ones",
                            "tags": ["scaling", "optimization"],
                        },
                        {
                            "topic": "Infrastructure Costs",
                            "insight": "GPU costs drop 40% per year; lease don't buy.",
                            "quote": "Lease your GPUs, buy your data",
                            "tags": ["costs", "infrastructure"],
                        },
                    ],
                }
            )
        )
    )
    return llm


@pytest.fixture
def extractor(mock_llm):
    """Create an ExpertiseExtractor with mock LLM."""
    return ExpertiseExtractor(llm_provider=mock_llm, max_insights=10)


@pytest.fixture
def sample_transcript():
    """Create a sample VoiceTranscript."""
    return VoiceTranscript(
        id="transcript-001",
        audio_file="/audio/interview.wav",
        full_text=(
            "I think the key to scaling AI startups is starting simple. "
            "One model, well-tuned, beats five mediocre ones every time. "
            "And when it comes to infrastructure, lease your GPUs, buy your data. "
            "GPU costs drop about 40% per year, so leasing makes more sense. "
            "The real moat is in your data and your fine-tuning pipeline."
        ),
        duration_seconds=180.0,
        language="en",
        segments=[
            {
                "start": 0.0,
                "end": 30.0,
                "text": "I think the key to scaling AI startups is starting simple.",
            },
            {
                "start": 30.0,
                "end": 60.0,
                "text": "One model, well-tuned, beats five mediocre ones every time.",
            },
        ],
    )


@pytest.fixture
def mock_transcription_result():
    """Create a mock TranscriptionResult (dataclass from Whisper)."""
    result = MagicMock()
    result.text = (
        "The future of AI is local-first. Running models on-device gives you "
        "privacy, speed, and no API costs. The tradeoff is model size, but "
        "quantization is closing that gap fast."
    )
    result.audio_path = "/audio/talk.wav"
    result.duration = 120.0
    result.language = "en"
    seg1 = MagicMock()
    seg1.start = 0.0
    seg1.end = 40.0
    seg1.text = "The future of AI is local-first."
    seg2 = MagicMock()
    seg2.start = 40.0
    seg2.end = 80.0
    seg2.text = "Running models on-device gives you privacy, speed, and no API costs."
    result.segments = [seg1, seg2]
    return result


# =============================================================================
# ExtractionResult Tests
# =============================================================================


class TestExtractionResult:
    """Tests for ExtractionResult."""

    def test_creation(self):
        """Test basic ExtractionResult creation."""
        result = ExtractionResult(
            transcript_id="t1",
            insights=[],
            topics=["AI"],
            summary="A summary",
        )
        assert result.transcript_id == "t1"
        assert result.topics == ["AI"]
        assert result.summary == "A summary"
        assert result.insights == []
        assert result.metadata == {}

    def test_to_dict(self):
        """Test serialization."""
        insight = ExpertiseInsight(
            topic="Testing",
            insight="Write tests first",
            quote="Tests are documentation",
            tags=["testing"],
        )
        result = ExtractionResult(
            transcript_id="t1",
            insights=[insight],
            topics=["testing"],
            summary="About testing",
            metadata={"source": "interview"},
        )
        d = result.to_dict()
        assert d["transcript_id"] == "t1"
        assert d["insight_count"] == 1
        assert d["topics"] == ["testing"]
        assert d["summary"] == "About testing"
        assert len(d["insights"]) == 1
        assert d["insights"][0]["topic"] == "Testing"

    def test_empty_result(self):
        """Test empty extraction result."""
        result = ExtractionResult(
            transcript_id="empty",
            insights=[],
            topics=[],
        )
        d = result.to_dict()
        assert d["insight_count"] == 0
        assert d["insights"] == []


# =============================================================================
# ExpertiseExtractor Tests
# =============================================================================


class TestExpertiseExtractor:
    """Tests for ExpertiseExtractor."""

    def test_init_defaults(self):
        """Test default initialization."""
        ext = ExpertiseExtractor()
        assert ext.llm_provider is None
        assert ext._max_insights == 10

    def test_init_with_params(self, mock_llm):
        """Test initialization with parameters."""
        ext = ExpertiseExtractor(llm_provider=mock_llm, max_insights=5)
        assert ext.llm_provider is mock_llm
        assert ext._max_insights == 5

    def test_llm_property_setter(self, mock_llm):
        """Test LLM provider property setter."""
        ext = ExpertiseExtractor()
        assert ext.llm_provider is None
        ext.llm_provider = mock_llm
        assert ext.llm_provider is mock_llm

    async def test_extract_from_transcript(self, extractor, sample_transcript):
        """Test extraction from VoiceTranscript."""
        result = await extractor.extract_from_transcript(sample_transcript)

        assert isinstance(result, ExtractionResult)
        assert result.transcript_id == "transcript-001"
        assert len(result.insights) == 2
        assert result.summary == "Discussion about scaling AI startups"
        assert "AI" in result.topics
        assert result.metadata["duration_seconds"] == 180.0
        assert result.metadata["language"] == "en"

    async def test_extract_insights_structure(self, extractor, sample_transcript):
        """Test that extracted insights have correct structure."""
        result = await extractor.extract_from_transcript(sample_transcript)

        for insight in result.insights:
            assert isinstance(insight, ExpertiseInsight)
            assert insight.topic != ""
            assert insight.insight != ""
            assert insight.quote != ""
            assert isinstance(insight.tags, list)
            assert insight.source_transcript_id == "transcript-001"

    async def test_extract_from_transcription_result(self, extractor, mock_transcription_result):
        """Test extraction from Whisper TranscriptionResult."""
        result = await extractor.extract_from_transcription(mock_transcription_result)

        assert isinstance(result, ExtractionResult)
        assert result.transcript_id == "/audio/talk.wav"
        assert len(result.insights) == 2

    async def test_extract_from_text(self, extractor):
        """Test extraction from raw text."""
        text = (
            "The best way to build software is iteratively. Ship early, "
            "get feedback, and iterate. Don't spend months building "
            "something nobody wants."
        )
        result = await extractor.extract_from_text(text, source_id="raw-001")

        assert isinstance(result, ExtractionResult)
        assert result.transcript_id == "raw-001"
        assert len(result.insights) == 2

    async def test_no_llm_returns_empty(self, sample_transcript):
        """Test graceful handling when no LLM is configured."""
        ext = ExpertiseExtractor()  # No LLM
        result = await ext.extract_from_transcript(sample_transcript)

        assert result.insights == []
        assert result.topics == []
        assert result.metadata.get("error") == "no_llm"

    async def test_short_transcript_returns_empty(self, extractor):
        """Test that very short transcripts are skipped."""
        short = VoiceTranscript(
            id="short",
            audio_file="/audio/short.wav",
            full_text="Hi.",
            duration_seconds=1.0,
        )
        result = await extractor.extract_from_transcript(short)

        assert result.insights == []
        assert result.metadata.get("error") == "too_short"

    async def test_short_text_returns_empty(self, extractor):
        """Test that very short raw text is skipped."""
        result = await extractor.extract_from_text("OK")
        assert result.insights == []
        assert result.metadata.get("error") == "too_short"

    async def test_llm_failure_graceful(self, sample_transcript):
        """Test graceful handling of LLM failure."""
        llm = MagicMock()
        llm.generate = AsyncMock(side_effect=Exception("LLM down"))
        ext = ExpertiseExtractor(llm_provider=llm)

        result = await ext.extract_from_transcript(sample_transcript)
        assert result.insights == []
        assert "failed" in result.summary.lower()

    async def test_malformed_json_graceful(self, sample_transcript):
        """Test handling of malformed JSON from LLM."""
        llm = MagicMock()
        llm.generate = AsyncMock(return_value=MagicMock(content="This is not JSON at all"))
        ext = ExpertiseExtractor(llm_provider=llm)

        result = await ext.extract_from_transcript(sample_transcript)
        assert result.insights == []

    def test_clean_json_strips_markdown(self):
        """Test JSON cleaning with markdown fences."""
        raw = '```json\n{"key": "value"}\n```'
        cleaned = ExpertiseExtractor._clean_json(raw)
        assert cleaned == '{"key": "value"}'

    def test_clean_json_finds_object(self):
        """Test JSON cleaning extracts object from surrounding text."""
        raw = 'Here is the result: {"key": "value"} That is all.'
        cleaned = ExpertiseExtractor._clean_json(raw)
        assert cleaned == '{"key": "value"}'

    def test_clean_json_plain(self):
        """Test JSON cleaning with clean input."""
        raw = '{"key": "value"}'
        cleaned = ExpertiseExtractor._clean_json(raw)
        assert cleaned == '{"key": "value"}'


# =============================================================================
# Package Import Tests
# =============================================================================


class TestPackageImports:
    """Test that the voice package exports correctly."""

    def test_import_from_voice_package(self):
        """Test importing ExpertiseExtractor from voice package."""
        from ag3ntwerk.integrations.voice import ExpertiseExtractor, ExtractionResult

        assert ExpertiseExtractor is not None
        assert ExtractionResult is not None

    def test_import_from_module(self):
        """Test importing directly from module."""
        from ag3ntwerk.integrations.voice.expertise_extractor import (
            ExpertiseExtractor,
            ExtractionResult,
        )

        assert ExpertiseExtractor is not None
        assert ExtractionResult is not None
