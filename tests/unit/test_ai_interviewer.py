"""
Tests for AIInterviewer - voice-guided interview system.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.integrations.voice.ai_interviewer import (
    AIInterviewer,
    InterviewAnswer,
    InterviewQuestion,
    InterviewResult,
    InterviewScript,
    InterviewSession,
    InterviewStatus,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm():
    """Create mock LLM provider."""
    llm = MagicMock()
    llm.generate = AsyncMock(
        return_value=MagicMock(content="Can you give a specific example of that approach?")
    )
    return llm


@pytest.fixture
def mock_llm_no_followup():
    """Create mock LLM that declines to generate follow-ups."""
    llm = MagicMock()
    llm.generate = AsyncMock(return_value=MagicMock(content="NONE"))
    return llm


@pytest.fixture
def mock_whisper():
    """Create mock WhisperIntegration."""
    whisper = MagicMock()
    whisper.transcribe = AsyncMock(
        return_value=MagicMock(
            text="I think the key is starting small and iterating fast. "
            "Don't try to build the perfect system from day one.",
            duration=45.0,
        )
    )
    return whisper


@pytest.fixture
def mock_extractor():
    """Create mock ExpertiseExtractor."""
    extractor = MagicMock()
    result = MagicMock()
    result.insights = []
    result.topics = ["iteration", "startups"]
    result.summary = "Focus on iterative development"
    result.to_dict = MagicMock(
        return_value={
            "transcript_id": "test",
            "insights": [],
            "topics": ["iteration"],
            "summary": "Focus on iteration",
            "insight_count": 0,
            "metadata": {},
        }
    )
    extractor.extract_from_text = AsyncMock(return_value=result)
    return extractor


@pytest.fixture
def sample_script():
    """Create a sample interview script."""
    return InterviewScript(
        topic="AI Scaling Strategies",
        questions=[
            InterviewQuestion(text="What's your biggest lesson scaling AI?", topic="scaling"),
            InterviewQuestion(text="How do you approach GPU cost optimization?", topic="costs"),
            InterviewQuestion(text="What's your hiring strategy for ML teams?", topic="hiring"),
        ],
        max_followups_per_question=1,
    )


@pytest.fixture
def two_question_script():
    """Create a minimal 2-question script."""
    return InterviewScript(
        topic="Quick Interview",
        questions=[
            InterviewQuestion(text="What do you do?"),
            InterviewQuestion(text="What's your advice?"),
        ],
    )


@pytest.fixture
def interviewer(mock_whisper, mock_extractor, mock_llm):
    """Create an AIInterviewer with all mocks."""
    return AIInterviewer(
        whisper=mock_whisper,
        extractor=mock_extractor,
        llm_provider=mock_llm,
    )


@pytest.fixture
def interviewer_no_llm(mock_whisper, mock_extractor):
    """Create an AIInterviewer without LLM (no follow-ups)."""
    return AIInterviewer(
        whisper=mock_whisper,
        extractor=mock_extractor,
    )


# =============================================================================
# InterviewScript Tests
# =============================================================================


class TestInterviewScript:
    """Tests for InterviewScript dataclass."""

    def test_creation(self, sample_script):
        """Test basic script creation."""
        assert sample_script.topic == "AI Scaling Strategies"
        assert len(sample_script.questions) == 3
        assert sample_script.max_followups_per_question == 1

    def test_default_description(self):
        """Test auto-generated description."""
        script = InterviewScript(topic="Testing")
        assert "Testing" in script.description

    def test_custom_description(self):
        """Test custom description overrides auto."""
        script = InterviewScript(topic="Testing", description="My custom description")
        assert script.description == "My custom description"

    def test_empty_questions(self):
        """Test script with no questions."""
        script = InterviewScript(topic="Empty")
        assert script.questions == []


# =============================================================================
# InterviewSession Tests
# =============================================================================


class TestInterviewSession:
    """Tests for InterviewSession dataclass."""

    def test_default_status(self):
        """Test default session status."""
        session = InterviewSession()
        assert session.status == InterviewStatus.NOT_STARTED
        assert session.current_question_index == 0
        assert session.answers == []

    def test_all_questions_no_followups(self, sample_script):
        """Test all_questions returns script questions when no follow-ups."""
        session = InterviewSession(script=sample_script)
        assert len(session.all_questions) == 3

    def test_all_questions_with_followups(self, sample_script):
        """Test all_questions includes follow-ups."""
        session = InterviewSession(script=sample_script)
        session.followup_questions.append(
            InterviewQuestion(text="Follow-up?", is_followup=True, follow_up_of=0)
        )
        all_q = session.all_questions
        assert len(all_q) == 4
        # Follow-up should come after its parent (index 0)
        assert all_q[0].text == sample_script.questions[0].text
        assert all_q[1].text == "Follow-up?"
        assert all_q[1].is_followup is True

    def test_current_question(self, sample_script):
        """Test current_question property."""
        session = InterviewSession(script=sample_script)
        assert session.current_question.text == sample_script.questions[0].text
        session.current_question_index = 1
        assert session.current_question.text == sample_script.questions[1].text

    def test_current_question_none_when_complete(self, sample_script):
        """Test current_question returns None when complete."""
        session = InterviewSession(script=sample_script)
        session.current_question_index = 3
        assert session.current_question is None

    def test_is_complete(self, sample_script):
        """Test is_complete property."""
        session = InterviewSession(script=sample_script)
        assert session.is_complete is False
        session.current_question_index = 3
        assert session.is_complete is True

    def test_progress(self, sample_script):
        """Test progress calculation."""
        session = InterviewSession(script=sample_script)
        assert session.progress == 0.0
        session.current_question_index = 1
        assert abs(session.progress - 1 / 3) < 0.01
        session.current_question_index = 3
        assert session.progress == 1.0

    def test_progress_empty_script(self):
        """Test progress with no questions."""
        session = InterviewSession(script=InterviewScript(topic="Empty"))
        assert session.progress == 1.0

    def test_to_dict(self, sample_script):
        """Test session serialization."""
        session = InterviewSession(script=sample_script)
        d = session.to_dict()
        assert d["topic"] == "AI Scaling Strategies"
        assert d["status"] == "not_started"
        assert d["total_questions"] == 3
        assert d["answers_count"] == 0
        assert d["progress"] == 0.0


# =============================================================================
# InterviewResult Tests
# =============================================================================


class TestInterviewResult:
    """Tests for InterviewResult dataclass."""

    def test_creation(self):
        """Test basic result creation."""
        result = InterviewResult(
            session_id="s1",
            topic="Testing",
            answers=[],
            full_transcript="Q: Hi?\nA: Hello.\n",
        )
        assert result.session_id == "s1"
        assert result.topic == "Testing"
        assert result.insights is None

    def test_to_dict(self):
        """Test result serialization."""
        result = InterviewResult(
            session_id="s1",
            topic="Testing",
            answers=[],
            full_transcript="Q: Hi?\nA: Hello.\n",
            duration_seconds=60.0,
        )
        d = result.to_dict()
        assert d["session_id"] == "s1"
        assert d["duration_seconds"] == 60.0
        assert d["insights"] is None

    def test_to_dict_with_insights(self, mock_extractor):
        """Test result serialization with insights."""
        mock_insights = MagicMock()
        mock_insights.to_dict.return_value = {"insight_count": 2}
        result = InterviewResult(
            session_id="s1",
            topic="Testing",
            answers=[],
            full_transcript="text",
            insights=mock_insights,
        )
        d = result.to_dict()
        assert d["insights"] == {"insight_count": 2}


# =============================================================================
# AIInterviewer Core Flow Tests
# =============================================================================


class TestAIInterviewerFlow:
    """Tests for the main interview flow."""

    async def test_start_session(self, interviewer, sample_script):
        """Test starting a new interview session."""
        session = await interviewer.start_session(sample_script)

        assert session.status == InterviewStatus.IN_PROGRESS
        assert session.started_at is not None
        assert session.script.topic == "AI Scaling Strategies"
        assert session.current_question_index == 0
        assert len(session.id) > 0

    async def test_process_answer_with_audio(self, interviewer, sample_script, mock_whisper):
        """Test processing an audio answer."""
        session = await interviewer.start_session(sample_script)
        session = await interviewer.process_answer(session, audio_path="/audio/answer1.wav")

        mock_whisper.transcribe.assert_called_once_with("/audio/answer1.wav")
        assert len(session.answers) == 1
        assert session.answers[0].audio_path == "/audio/answer1.wav"
        assert "starting small" in session.answers[0].transcript_text

    async def test_process_answer_with_text(self, interviewer, sample_script):
        """Test processing a text answer."""
        session = await interviewer.start_session(sample_script)
        session = await interviewer.process_answer(
            session, text="My answer is to focus on data quality first."
        )

        assert len(session.answers) == 1
        assert "data quality" in session.answers[0].transcript_text

    async def test_process_answer_advances_index(self, interviewer_no_llm, two_question_script):
        """Test that processing advances the question index."""
        session = await interviewer_no_llm.start_session(two_question_script)
        assert session.current_question_index == 0

        session = await interviewer_no_llm.process_answer(session, text="I build software.")
        assert session.current_question_index == 1

        session = await interviewer_no_llm.process_answer(session, text="Ship fast.")
        # Should auto-complete after last answer
        assert session.status == InterviewStatus.COMPLETED
        assert session.completed_at is not None

    async def test_process_answer_no_input_raises(self, interviewer, sample_script):
        """Test that no input raises ValueError."""
        session = await interviewer.start_session(sample_script)
        with pytest.raises(ValueError, match="Must provide"):
            await interviewer.process_answer(session)

    async def test_process_answer_not_in_progress_raises(self, interviewer, sample_script):
        """Test that answering a completed session raises."""
        session = await interviewer.start_session(sample_script)
        session.status = InterviewStatus.COMPLETED
        with pytest.raises(ValueError, match="not in_progress"):
            await interviewer.process_answer(session, text="Late answer")

    async def test_full_interview_flow(
        self, interviewer_no_llm, two_question_script, mock_extractor
    ):
        """Test a complete interview from start to finish."""
        session = await interviewer_no_llm.start_session(two_question_script)

        session = await interviewer_no_llm.process_answer(
            session, text="I'm an AI researcher focused on local models."
        )
        session = await interviewer_no_llm.process_answer(
            session, text="Focus on solving real problems, not chasing benchmarks."
        )

        assert session.status == InterviewStatus.COMPLETED
        assert len(session.answers) == 2

        result = await interviewer_no_llm.finish_session(session)
        assert result.topic == "Quick Interview"
        assert len(result.answers) == 2
        assert "AI researcher" in result.full_transcript
        assert "benchmarks" in result.full_transcript
        mock_extractor.extract_from_text.assert_called_once()

    async def test_finish_session_early(self, interviewer, sample_script, mock_extractor):
        """Test finishing a session before all questions answered."""
        session = await interviewer.start_session(sample_script)
        session = await interviewer.process_answer(session, text="Only answering one question.")

        # Finish early (still had questions remaining)
        result = await interviewer.finish_session(session)
        assert result.session_id == session.id
        assert len(result.answers) == 1
        # questions_asked = current_question_index (advanced past answered + any followup)
        assert result.metadata["questions_asked"] >= 1


# =============================================================================
# Follow-up Generation Tests
# =============================================================================


class TestFollowUpGeneration:
    """Tests for LLM-based follow-up question generation."""

    async def test_followup_generated(self, interviewer, sample_script, mock_llm):
        """Test that follow-ups are generated after scripted questions."""
        session = await interviewer.start_session(sample_script)
        session = await interviewer.process_answer(
            session,
            text="The biggest lesson is that you need strong data pipelines before anything else. "
            "Without clean data, your models are garbage no matter how fancy.",
        )

        # LLM should have been asked to generate a follow-up
        mock_llm.generate.assert_called()
        assert session.followups_used == 1
        assert len(session.followup_questions) == 1
        assert session.followup_questions[0].is_followup is True

    async def test_no_followup_without_llm(self, interviewer_no_llm, sample_script):
        """Test that no follow-ups are generated without LLM."""
        session = await interviewer_no_llm.start_session(sample_script)
        session = await interviewer_no_llm.process_answer(
            session,
            text="Some detailed answer about scaling challenges and approaches.",
        )

        assert session.followups_used == 0
        assert session.followup_questions == []

    async def test_no_followup_for_short_answers(self, interviewer, sample_script):
        """Test that very short answers don't trigger follow-ups."""
        session = await interviewer.start_session(sample_script)
        session = await interviewer.process_answer(session, text="Not sure.")

        assert session.followups_used == 0

    async def test_no_followup_on_followup_questions(self, interviewer, sample_script, mock_llm):
        """Test that follow-ups don't generate more follow-ups."""
        session = await interviewer.start_session(sample_script)

        # Answer first question (generates follow-up)
        session = await interviewer.process_answer(
            session,
            text="You need to start with a solid data pipeline. Clean data is everything in AI scaling.",
        )
        calls_after_first = mock_llm.generate.call_count

        # Now answer the follow-up question
        session = await interviewer.process_answer(
            session,
            text="A specific example: we reduced data noise by 30% using automated validation scripts.",
        )

        # Should not have generated another follow-up
        assert session.followups_used == 1

    async def test_llm_returns_none_no_followup(
        self, mock_whisper, mock_extractor, mock_llm_no_followup, sample_script
    ):
        """Test that LLM returning NONE creates no follow-up."""
        interviewer = AIInterviewer(
            whisper=mock_whisper,
            extractor=mock_extractor,
            llm_provider=mock_llm_no_followup,
        )
        session = await interviewer.start_session(sample_script)
        session = await interviewer.process_answer(
            session,
            text="A long enough answer about scaling that should be considered for followup generation.",
        )

        assert session.followups_used == 0


# =============================================================================
# Cancel and Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for cancellation and edge cases."""

    async def test_cancel_session(self, interviewer, sample_script):
        """Test cancelling a session."""
        session = await interviewer.start_session(sample_script)
        session = await interviewer.cancel_session(session)

        assert session.status == InterviewStatus.CANCELLED
        assert session.completed_at is not None

    async def test_get_next_question(self, interviewer, sample_script):
        """Test getting the next question text."""
        session = await interviewer.start_session(sample_script)
        q = interviewer.get_next_question(session)
        assert q == "What's your biggest lesson scaling AI?"

    async def test_get_next_question_none_when_done(self, interviewer, sample_script):
        """Test get_next_question returns None when done."""
        session = await interviewer.start_session(sample_script)
        session.current_question_index = 99
        assert interviewer.get_next_question(session) is None

    async def test_whisper_failure_falls_back_to_text(
        self, mock_extractor, mock_llm, sample_script
    ):
        """Test that Whisper failure falls back to text if provided."""
        bad_whisper = MagicMock()
        bad_whisper.transcribe = AsyncMock(side_effect=Exception("No audio device"))
        interviewer = AIInterviewer(
            whisper=bad_whisper,
            extractor=mock_extractor,
            llm_provider=mock_llm,
        )

        session = await interviewer.start_session(sample_script)
        session = await interviewer.process_answer(
            session,
            audio_path="/bad/path.wav",
            text="Fallback text answer",
        )

        assert session.answers[0].transcript_text == "Fallback text answer"

    async def test_audio_without_whisper_raises(self, mock_extractor, sample_script):
        """Test that audio input without Whisper configured raises."""
        interviewer = AIInterviewer(extractor=mock_extractor)

        session = await interviewer.start_session(sample_script)
        with pytest.raises(ValueError, match="WhisperIntegration"):
            await interviewer.process_answer(session, audio_path="/audio/test.wav")

    async def test_extractor_failure_graceful(self, mock_whisper, mock_llm, two_question_script):
        """Test graceful handling when extractor fails."""
        bad_extractor = MagicMock()
        bad_extractor.extract_from_text = AsyncMock(side_effect=Exception("Extractor broke"))
        interviewer = AIInterviewer(
            whisper=mock_whisper,
            extractor=bad_extractor,
            llm_provider=mock_llm,
        )

        session = await interviewer.start_session(two_question_script)
        session = await interviewer.process_answer(session, text="Answer 1 here")
        session = await interviewer.process_answer(session, text="Answer 2 here")

        result = await interviewer.finish_session(session)
        assert result.insights is None  # Graceful — no crash

    async def test_finish_with_no_extractor(self, mock_whisper, two_question_script):
        """Test finishing without an extractor."""
        interviewer = AIInterviewer(whisper=mock_whisper)

        session = await interviewer.start_session(two_question_script)
        session = await interviewer.process_answer(session, text="Answer")
        session = await interviewer.process_answer(session, text="Another")

        result = await interviewer.finish_session(session)
        assert result.insights is None
        assert len(result.answers) == 2


# =============================================================================
# Transcript Building Tests
# =============================================================================


class TestTranscriptBuilding:
    """Tests for transcript assembly."""

    async def test_transcript_format(self, interviewer_no_llm, two_question_script):
        """Test that the full transcript has correct Q&A format."""
        session = await interviewer_no_llm.start_session(two_question_script)
        session = await interviewer_no_llm.process_answer(session, text="I'm an engineer.")
        session = await interviewer_no_llm.process_answer(session, text="Ship fast.")

        result = await interviewer_no_llm.finish_session(session)
        lines = result.full_transcript.strip().split("\n")

        # Should have Q/A pairs with blank lines between
        assert lines[0].startswith("Q: ")
        assert lines[1].startswith("A: ")
        assert lines[3].startswith("Q: ")
        assert lines[4].startswith("A: ")


# =============================================================================
# Package Import Tests
# =============================================================================


class TestPackageImports:
    """Test that the voice package exports AIInterviewer correctly."""

    def test_import_from_voice_package(self):
        """Test importing from voice package."""
        from ag3ntwerk.integrations.voice import (
            AIInterviewer,
            InterviewScript,
            InterviewQuestion,
            InterviewSession,
            InterviewResult,
            InterviewAnswer,
            InterviewStatus,
        )

        assert AIInterviewer is not None
        assert InterviewScript is not None
        assert InterviewQuestion is not None
        assert InterviewSession is not None
        assert InterviewResult is not None
        assert InterviewAnswer is not None
        assert InterviewStatus is not None

    def test_import_from_module(self):
        """Test direct module import."""
        from ag3ntwerk.integrations.voice.ai_interviewer import AIInterviewer

        assert AIInterviewer is not None
