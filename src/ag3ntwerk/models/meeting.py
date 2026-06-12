"""
Meeting intelligence models for ag3ntwerk.

Used by:
- Meeting Intelligence pipeline for transcription analysis
- Audio watcher for auto-ingestion
- Meeting dashboard for display and action item tracking
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class MeetingStatus(str, Enum):
    """Processing status of a meeting recording."""

    QUEUED = "queued"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"


class ActionItemStatus(str, Enum):
    """Lifecycle status of an action item."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class MeetingParticipant(BaseModel):
    """A detected meeting participant."""

    name: str
    email: Optional[str] = None
    role: Optional[str] = None


class MeetingDecision(BaseModel):
    """A decision made during the meeting."""

    summary: str
    context: str = ""
    decided_by: Optional[str] = None


class MeetingQuestion(BaseModel):
    """A question raised during the meeting."""

    question: str
    answered: bool = False
    answer: Optional[str] = None
    asked_by: Optional[str] = None


class ActionItem(BaseModel):
    """An action item extracted from a meeting."""

    id: str
    meeting_id: str
    description: str
    assignee: Optional[str] = None
    assignee_email: Optional[str] = None
    deadline: Optional[datetime] = None
    status: ActionItemStatus = ActionItemStatus.OPEN
    priority: str = "medium"
    notes: str = ""
    calendar_event_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class MeetingAnalysis(BaseModel):
    """Structured analysis of a meeting transcript."""

    executive_summary: str = ""
    key_decisions: List[MeetingDecision] = Field(default_factory=list)
    action_items: List[Dict[str, Any]] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    questions: List[MeetingQuestion] = Field(default_factory=list)
    sentiment: str = "neutral"
    participants: List[MeetingParticipant] = Field(default_factory=list)
    suggested_title: str = ""


class Meeting(BaseModel):
    """A meeting recording with transcript and analysis."""

    id: str
    title: str = ""
    audio_file: str
    status: MeetingStatus = MeetingStatus.QUEUED
    duration_seconds: Optional[float] = None
    transcript_text: Optional[str] = None
    transcript_segments: List[Dict[str, Any]] = Field(default_factory=list)
    analysis: Optional[MeetingAnalysis] = None
    source: str = "hidock"
    tags: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
