"""Tests for meeting intelligence models."""

import pytest
from datetime import datetime, timezone

from ag3ntwerk.models.meeting import (
    ActionItem,
    ActionItemStatus,
    Meeting,
    MeetingAnalysis,
    MeetingDecision,
    MeetingParticipant,
    MeetingQuestion,
    MeetingStatus,
)


# ============================================================
# MeetingStatus Enum
# ============================================================


class TestMeetingStatus:
    def test_all_values(self):
        assert MeetingStatus.QUEUED == "queued"
        assert MeetingStatus.TRANSCRIBING == "transcribing"
        assert MeetingStatus.ANALYZING == "analyzing"
        assert MeetingStatus.COMPLETE == "complete"
        assert MeetingStatus.FAILED == "failed"

    def test_from_string(self):
        assert MeetingStatus("queued") == MeetingStatus.QUEUED
        assert MeetingStatus("complete") == MeetingStatus.COMPLETE

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            MeetingStatus("invalid")


# ============================================================
# ActionItemStatus Enum
# ============================================================


class TestActionItemStatus:
    def test_all_values(self):
        assert ActionItemStatus.OPEN == "open"
        assert ActionItemStatus.IN_PROGRESS == "in_progress"
        assert ActionItemStatus.DONE == "done"
        assert ActionItemStatus.CANCELLED == "cancelled"

    def test_from_string(self):
        assert ActionItemStatus("open") == ActionItemStatus.OPEN
        assert ActionItemStatus("done") == ActionItemStatus.DONE


# ============================================================
# MeetingParticipant
# ============================================================


class TestMeetingParticipant:
    def test_minimal(self):
        p = MeetingParticipant(name="Alice")
        assert p.name == "Alice"
        assert p.email is None
        assert p.role is None

    def test_full(self):
        p = MeetingParticipant(name="Bob", email="bob@example.com", role="Engineering Lead")
        assert p.email == "bob@example.com"
        assert p.role == "Engineering Lead"


# ============================================================
# MeetingDecision
# ============================================================


class TestMeetingDecision:
    def test_minimal(self):
        d = MeetingDecision(summary="Use Postgres for prod")
        assert d.summary == "Use Postgres for prod"
        assert d.context == ""
        assert d.decided_by is None

    def test_full(self):
        d = MeetingDecision(
            summary="Migrate to k8s",
            context="Current docker-compose is hitting scaling limits",
            decided_by="CTO",
        )
        assert d.decided_by == "CTO"


# ============================================================
# MeetingQuestion
# ============================================================


class TestMeetingQuestion:
    def test_unanswered(self):
        q = MeetingQuestion(question="When is the deadline?")
        assert q.answered is False
        assert q.answer is None

    def test_answered(self):
        q = MeetingQuestion(
            question="What's the budget?",
            answered=True,
            answer="$50,000",
            asked_by="CFO",
        )
        assert q.answered is True
        assert q.answer == "$50,000"


# ============================================================
# ActionItem
# ============================================================


class TestActionItem:
    def test_defaults(self):
        item = ActionItem(id="ai_001", meeting_id="m_001", description="Write tests")
        assert item.status == ActionItemStatus.OPEN
        assert item.priority == "medium"
        assert item.assignee is None
        assert item.deadline is None
        assert item.notes == ""
        assert item.calendar_event_id is None

    def test_full(self):
        deadline = datetime(2026, 4, 1, tzinfo=timezone.utc)
        item = ActionItem(
            id="ai_002",
            meeting_id="m_001",
            description="Deploy to staging",
            assignee="Alice",
            assignee_email="alice@example.com",
            deadline=deadline,
            status=ActionItemStatus.IN_PROGRESS,
            priority="high",
            notes="Needs QA sign-off first",
        )
        assert item.assignee == "Alice"
        assert item.deadline == deadline
        assert item.priority == "high"

    def test_serialization_roundtrip(self):
        item = ActionItem(id="ai_003", meeting_id="m_001", description="Test")
        data = item.model_dump()
        restored = ActionItem(**data)
        assert restored.id == "ai_003"
        assert restored.description == "Test"

    def test_timestamps_auto_set(self):
        item = ActionItem(id="ai_004", meeting_id="m_001", description="Auto time")
        assert item.created_at is not None
        assert item.updated_at is not None


# ============================================================
# MeetingAnalysis
# ============================================================


class TestMeetingAnalysis:
    def test_defaults(self):
        a = MeetingAnalysis()
        assert a.executive_summary == ""
        assert a.key_decisions == []
        assert a.action_items == []
        assert a.themes == []
        assert a.questions == []
        assert a.sentiment == "neutral"
        assert a.participants == []
        assert a.suggested_title == ""

    def test_populated(self):
        a = MeetingAnalysis(
            executive_summary="Good meeting about product roadmap.",
            key_decisions=[
                MeetingDecision(summary="Ship v2 in April"),
            ],
            themes=["roadmap", "hiring"],
            sentiment="productive",
            suggested_title="Q2 Product Roadmap Review",
        )
        assert len(a.key_decisions) == 1
        assert a.sentiment == "productive"

    def test_serialization(self):
        a = MeetingAnalysis(
            executive_summary="Test",
            themes=["a", "b"],
        )
        data = a.model_dump()
        assert data["themes"] == ["a", "b"]


# ============================================================
# Meeting
# ============================================================


class TestMeeting:
    def test_defaults(self):
        m = Meeting(id="m_001", audio_file="/path/to/audio.wav")
        assert m.title == ""
        assert m.status == MeetingStatus.QUEUED
        assert m.source == "hidock"
        assert m.transcript_text is None
        assert m.analysis is None
        assert m.error is None
        assert m.tags == []

    def test_with_analysis(self):
        analysis = MeetingAnalysis(
            executive_summary="Sprint review went well.",
            themes=["sprint", "velocity"],
        )
        m = Meeting(
            id="m_002",
            title="Sprint Review",
            audio_file="/recordings/sprint.wav",
            status=MeetingStatus.COMPLETE,
            duration_seconds=1800.0,
            transcript_text="Today we discussed sprint velocity...",
            analysis=analysis,
        )
        assert m.analysis.themes == ["sprint", "velocity"]
        assert m.duration_seconds == 1800.0

    def test_failed_state(self):
        m = Meeting(
            id="m_003",
            audio_file="/bad.wav",
            status=MeetingStatus.FAILED,
            error="Whisper transcription failed: corrupt audio",
        )
        assert m.status == MeetingStatus.FAILED
        assert "corrupt" in m.error

    def test_serialization_roundtrip(self):
        m = Meeting(
            id="m_004",
            audio_file="/test.wav",
            tags=["standup", "engineering"],
        )
        data = m.model_dump()
        restored = Meeting(**data)
        assert restored.tags == ["standup", "engineering"]
        assert restored.id == "m_004"
