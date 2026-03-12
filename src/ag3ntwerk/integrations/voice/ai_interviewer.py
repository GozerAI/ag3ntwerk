"""
AI Interviewer for ag3ntwerk.

Orchestrates voice-guided interviews to extract expertise insights.
Combines Whisper transcription with LLM-generated follow-up questions
and ExpertiseExtractor for structured insight capture.

Usage:
    interviewer = AIInterviewer(
        whisper=WhisperIntegration(),
        extractor=ExpertiseExtractor(llm_provider=llm),
        llm_provider=llm,
    )

    # Define a question script
    script = InterviewScript(
        topic="AI Scaling Strategies",
        questions=[
            InterviewQuestion(text="What's the biggest mistake founders make when scaling AI?"),
            InterviewQuestion(text="How do you approach GPU cost optimization?"),
        ],
    )

    # Run the interview
    session = await interviewer.start_session(script)

    # Simulate answering (in production, each answer is an audio file)
    session = await interviewer.process_answer(session, audio_path="answer1.wav")
    session = await interviewer.process_answer(session, audio_path="answer2.wav")

    # Finish and extract insights
    result = await interviewer.finish_session(session)
    print(result.insights)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ag3ntwerk.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class InterviewStatus(str, Enum):
    """Status of an interview session."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class InterviewQuestion:
    """A question in an interview script."""

    text: str
    topic: str = ""
    is_followup: bool = False
    follow_up_of: Optional[int] = None  # Index of parent question


@dataclass
class InterviewAnswer:
    """An answer captured during an interview."""

    question_index: int
    question_text: str
    transcript_text: str
    audio_path: str = ""
    duration_seconds: float = 0.0


@dataclass
class InterviewScript:
    """Script defining an interview flow."""

    topic: str
    questions: List[InterviewQuestion] = field(default_factory=list)
    max_followups_per_question: int = 2
    description: str = ""

    def __post_init__(self):
        if not self.description:
            self.description = f"Interview about {self.topic}"


@dataclass
class InterviewSession:
    """State of an ongoing interview."""

    id: str = field(default_factory=lambda: str(uuid4()))
    script: InterviewScript = field(default_factory=lambda: InterviewScript(topic=""))
    status: InterviewStatus = InterviewStatus.NOT_STARTED
    current_question_index: int = 0
    answers: List[InterviewAnswer] = field(default_factory=list)
    followup_questions: List[InterviewQuestion] = field(default_factory=list)
    followups_used: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def all_questions(self) -> List[InterviewQuestion]:
        """Get all questions including dynamic follow-ups."""
        result = []
        for i, q in enumerate(self.script.questions):
            result.append(q)
            # Insert follow-ups after their parent question
            for fq in self.followup_questions:
                if fq.follow_up_of == i:
                    result.append(fq)
        return result

    @property
    def current_question(self) -> Optional[InterviewQuestion]:
        """Get the current question to ask."""
        questions = self.all_questions
        if self.current_question_index < len(questions):
            return questions[self.current_question_index]
        return None

    @property
    def is_complete(self) -> bool:
        """Check if all questions have been answered."""
        return self.current_question_index >= len(self.all_questions)

    @property
    def progress(self) -> float:
        """Get interview progress as 0.0-1.0."""
        total = len(self.all_questions)
        if total == 0:
            return 1.0
        return min(self.current_question_index / total, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "topic": self.script.topic,
            "status": self.status.value,
            "current_question_index": self.current_question_index,
            "total_questions": len(self.all_questions),
            "answers_count": len(self.answers),
            "followups_used": self.followups_used,
            "progress": self.progress,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class InterviewResult:
    """Final result of a completed interview."""

    session_id: str
    topic: str
    answers: List[InterviewAnswer]
    full_transcript: str
    insights: Any = None  # ExtractionResult from ExpertiseExtractor
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "answers_count": len(self.answers),
            "full_transcript_length": len(self.full_transcript),
            "insights": self.insights.to_dict() if self.insights else None,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


class AIInterviewer:
    """
    Orchestrates voice-guided interviews for expertise extraction.

    Combines:
    - WhisperIntegration for speech-to-text transcription
    - LLM for generating follow-up questions
    - ExpertiseExtractor for structured insight extraction

    The interviewer supports both audio-based answers (transcribed via
    Whisper) and text-based answers (for testing or text-input scenarios).

    Example:
        interviewer = AIInterviewer(
            whisper=WhisperIntegration(),
            extractor=ExpertiseExtractor(llm_provider=llm),
            llm_provider=llm,
        )

        script = InterviewScript(
            topic="Scaling AI Startups",
            questions=[
                InterviewQuestion(text="What's your biggest lesson?"),
            ],
        )

        session = await interviewer.start_session(script)
        session = await interviewer.process_answer(
            session, audio_path="answer.wav"
        )
        result = await interviewer.finish_session(session)
    """

    def __init__(
        self,
        whisper=None,
        extractor=None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        """
        Initialize the AIInterviewer.

        Args:
            whisper: WhisperIntegration instance for transcription
            extractor: ExpertiseExtractor instance for insight extraction
            llm_provider: LLM provider for generating follow-up questions
        """
        self._whisper = whisper
        self._extractor = extractor
        self._llm = llm_provider

    async def start_session(self, script: InterviewScript) -> InterviewSession:
        """
        Start a new interview session.

        Args:
            script: InterviewScript defining the questions

        Returns:
            InterviewSession in IN_PROGRESS state
        """
        session = InterviewSession(
            script=script,
            status=InterviewStatus.IN_PROGRESS,
            started_at=_utcnow(),
        )
        logger.info(
            "Interview session %s started: %s (%d questions)",
            session.id,
            script.topic,
            len(script.questions),
        )
        return session

    async def process_answer(
        self,
        session: InterviewSession,
        audio_path: Optional[str] = None,
        text: Optional[str] = None,
    ) -> InterviewSession:
        """
        Process an answer to the current question.

        Accepts either an audio file (transcribed via Whisper) or
        direct text input.

        Args:
            session: Current interview session
            audio_path: Path to audio file with the answer
            text: Text answer (alternative to audio)

        Returns:
            Updated InterviewSession with the answer recorded
            and question index advanced

        Raises:
            ValueError: If session is not in progress or no input provided
        """
        if session.status != InterviewStatus.IN_PROGRESS:
            raise ValueError(f"Session is {session.status.value}, not in_progress")

        current_q = session.current_question
        if current_q is None:
            raise ValueError("No more questions to answer")

        if not audio_path and not text:
            raise ValueError("Must provide either audio_path or text")

        # Transcribe audio if provided
        transcript_text = ""
        duration = 0.0

        if audio_path and self._whisper:
            try:
                result = await self._whisper.transcribe(audio_path)
                transcript_text = result.text
                duration = result.duration
            except Exception as e:
                logger.warning("Transcription failed: %s", e)
                transcript_text = text or ""
        elif text:
            transcript_text = text
        else:
            raise ValueError("Audio provided but no WhisperIntegration configured")

        # Record answer
        answer = InterviewAnswer(
            question_index=session.current_question_index,
            question_text=current_q.text,
            transcript_text=transcript_text,
            audio_path=audio_path or "",
            duration_seconds=duration,
        )
        session.answers.append(answer)

        # Generate follow-up if applicable
        await self._maybe_generate_followup(session, answer)

        # Advance to next question
        session.current_question_index += 1

        # Check completion
        if session.is_complete:
            session.status = InterviewStatus.COMPLETED
            session.completed_at = _utcnow()

        return session

    async def finish_session(self, session: InterviewSession) -> InterviewResult:
        """
        Finish the interview and extract insights.

        Can be called early (before all questions answered) or
        after natural completion.

        Args:
            session: Interview session to finish

        Returns:
            InterviewResult with full transcript and extracted insights
        """
        if session.status == InterviewStatus.IN_PROGRESS:
            session.status = InterviewStatus.COMPLETED
            session.completed_at = _utcnow()

        # Build full transcript
        full_transcript = self._build_transcript(session)

        # Calculate total duration
        total_duration = sum(a.duration_seconds for a in session.answers)

        # Extract insights if extractor available
        insights = None
        if self._extractor and full_transcript.strip():
            try:
                insights = await self._extractor.extract_from_text(
                    full_transcript,
                    source_id=session.id,
                )
            except Exception as e:
                logger.warning("Insight extraction failed: %s", e)

        # Compute session duration from timestamps
        session_duration = total_duration
        if session.started_at and session.completed_at:
            session_duration = max(
                session_duration,
                (session.completed_at - session.started_at).total_seconds(),
            )

        return InterviewResult(
            session_id=session.id,
            topic=session.script.topic,
            answers=session.answers,
            full_transcript=full_transcript,
            insights=insights,
            duration_seconds=session_duration,
            metadata={
                "questions_asked": session.current_question_index,
                "followups_generated": session.followups_used,
                "total_questions": len(session.all_questions),
            },
        )

    async def cancel_session(self, session: InterviewSession) -> InterviewSession:
        """
        Cancel an in-progress interview.

        Args:
            session: Session to cancel

        Returns:
            Session with CANCELLED status
        """
        session.status = InterviewStatus.CANCELLED
        session.completed_at = _utcnow()
        return session

    def get_next_question(self, session: InterviewSession) -> Optional[str]:
        """
        Get the next question text for the interview.

        Args:
            session: Current session

        Returns:
            Question text or None if complete
        """
        q = session.current_question
        return q.text if q else None

    async def _maybe_generate_followup(
        self,
        session: InterviewSession,
        answer: InterviewAnswer,
    ) -> None:
        """Generate a follow-up question if warranted."""
        if not self._llm:
            return

        # Respect follow-up limits
        max_followups = session.script.max_followups_per_question
        if session.followups_used >= max_followups * len(session.script.questions):
            return

        # Only generate follow-ups for scripted questions (not for other follow-ups)
        current_q = session.current_question
        if current_q and current_q.is_followup:
            return

        # Check if the answer warrants a follow-up
        if len(answer.transcript_text.strip()) < 30:
            return  # Too short to warrant follow-up

        try:
            followup_text = await self._generate_followup_question(
                session.script.topic,
                answer.question_text,
                answer.transcript_text,
            )
            if followup_text:
                followup = InterviewQuestion(
                    text=followup_text,
                    topic=current_q.topic if current_q else "",
                    is_followup=True,
                    follow_up_of=answer.question_index,
                )
                session.followup_questions.append(followup)
                session.followups_used += 1
        except Exception as e:
            logger.warning("Follow-up generation failed: %s", e)

    async def _generate_followup_question(
        self,
        topic: str,
        question: str,
        answer: str,
    ) -> Optional[str]:
        """Use LLM to generate a follow-up question."""
        prompt = f"""You are conducting an expert interview about "{topic}".

The question was: {question}
The answer was: {answer[:500]}

Based on this answer, generate ONE concise follow-up question that:
1. Digs deeper into the most interesting point raised
2. Asks for a specific example, data point, or framework
3. Is under 30 words

Return ONLY the question text, nothing else. If no follow-up is warranted, return "NONE"."""

        response = await self._llm.generate(prompt)
        text = response.content.strip().strip('"')

        if text.upper() == "NONE" or len(text) < 10:
            return None
        return text

    def _build_transcript(self, session: InterviewSession) -> str:
        """Build a full Q&A transcript from the session."""
        lines = []
        for answer in session.answers:
            lines.append(f"Q: {answer.question_text}")
            lines.append(f"A: {answer.transcript_text}")
            lines.append("")
        return "\n".join(lines)
