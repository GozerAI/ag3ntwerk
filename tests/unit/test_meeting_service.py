"""Tests for MeetingService pipeline and CRUD operations."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ag3ntwerk.api.meeting_service import MeetingService
from ag3ntwerk.models.meeting import (
    ActionItemStatus,
    Meeting,
    MeetingAnalysis,
    MeetingStatus,
)


# ============================================================
# Fixtures
# ============================================================


def _make_mock_db():
    """Create a mock DatabaseManager backed by in-memory dicts."""
    db = MagicMock()
    _meetings = {}
    _action_items = {}

    async def mock_execute(query, params=None):
        q = query.strip().upper()
        if q.startswith("CREATE"):
            return 0
        if q.startswith("INSERT INTO MEETINGS"):
            _meetings[params[0]] = {
                "id": params[0],
                "title": params[1],
                "audio_file": params[2],
                "status": params[3],
                "source": params[4],
                "tags": params[5],
                "created_at": params[6],
                "updated_at": params[7],
                "duration_seconds": None,
                "transcript_text": None,
                "transcript_segments": "[]",
                "analysis": None,
                "error": None,
            }
            return 1
        if q.startswith("INSERT INTO ACTION_ITEMS"):
            _action_items[params[0]] = {
                "id": params[0],
                "meeting_id": params[1],
                "description": params[2],
                "assignee": params[3],
                "deadline": params[4],
                "status": params[5],
                "priority": params[6],
                "created_at": params[7],
                "updated_at": params[8],
                "assignee_email": None,
                "notes": "",
                "calendar_event_id": None,
            }
            return 1
        if q.startswith("UPDATE MEETINGS"):
            mid = params[-1]
            if mid in _meetings:
                if "STATUS" in q and "ERROR" in q:
                    _meetings[mid]["status"] = params[0]
                    _meetings[mid]["error"] = params[1]
                    _meetings[mid]["updated_at"] = params[2]
                elif "TRANSCRIPT_TEXT" in q:
                    _meetings[mid]["transcript_text"] = params[0]
                    _meetings[mid]["transcript_segments"] = params[1]
                    _meetings[mid]["duration_seconds"] = params[2]
                    _meetings[mid]["updated_at"] = params[3]
                elif "ANALYSIS" in q:
                    _meetings[mid]["analysis"] = params[0]
                    _meetings[mid]["title"] = params[1]
                    _meetings[mid]["updated_at"] = params[2]
                elif "STATUS" in q:
                    _meetings[mid]["status"] = params[0]
                    _meetings[mid]["updated_at"] = params[1]
            return 1
        if q.startswith("UPDATE ACTION_ITEMS"):
            aid = params[-1]
            if aid in _action_items:
                # Parse SET clauses from params positionally
                set_part = query.split("SET")[1].split("WHERE")[0]
                fields = [f.strip().split("=")[0].strip().lower() for f in set_part.split(",")]
                for i, field in enumerate(fields):
                    if field in _action_items[aid]:
                        _action_items[aid][field] = params[i]
            return 1
        if q.startswith("DELETE FROM ACTION_ITEMS"):
            mid = params[0]
            to_del = [k for k, v in _action_items.items() if v["meeting_id"] == mid]
            for k in to_del:
                del _action_items[k]
            return len(to_del)
        if q.startswith("DELETE FROM MEETINGS"):
            mid = params[0]
            if mid in _meetings:
                del _meetings[mid]
                return 1
            return 0
        return 0

    async def mock_fetch_one(query, params=None):
        q = query.strip().upper()
        if "FROM MEETINGS" in q and "WHERE ID" in q:
            return _meetings.get(params[0])
        if "FROM ACTION_ITEMS" in q and "WHERE ID" in q:
            return _action_items.get(params[0])
        if "COUNT" in q:
            if params and params[0]:
                count = sum(1 for m in _meetings.values() if m["status"] == params[0])
            else:
                count = len(_meetings)
            return {"cnt": count}
        return None

    async def mock_fetch_all(query, params=None):
        q = query.strip().upper()
        if "FROM MEETINGS" in q:
            rows = list(_meetings.values())
            if params and "STATUS" in q and "WHERE STATUS" in q:
                rows = [r for r in rows if r["status"] == params[0]]
            rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
            return rows
        if "FROM ACTION_ITEMS" in q:
            rows = list(_action_items.values())
            return rows
        return []

    db.execute = AsyncMock(side_effect=mock_execute)
    db.fetch_one = AsyncMock(side_effect=mock_fetch_one)
    db.fetch_all = AsyncMock(side_effect=mock_fetch_all)
    db._meetings = _meetings
    db._action_items = _action_items
    return db


def _make_mock_whisper(text="Hello from the meeting", duration=120.0):
    """Create a mock WhisperIntegration."""
    whisper = MagicMock()
    result = MagicMock()
    result.text = text
    result.segments = [
        MagicMock(id=0, start=0.0, end=5.0, text="Hello from"),
        MagicMock(id=1, start=5.0, end=10.0, text="the meeting"),
    ]
    result.duration = duration
    result.language = "en"
    whisper.transcribe = AsyncMock(return_value=result)
    return whisper


def _make_mock_analyzer(analysis=None):
    """Create a mock MeetingAnalyzer."""
    if analysis is None:
        analysis = MeetingAnalysis(
            executive_summary="The team discussed priorities.",
            themes=["priorities", "roadmap"],
            sentiment="productive",
            suggested_title="Team Sync",
            action_items=[
                {
                    "description": "Write proposal",
                    "assignee": "Alice",
                    "deadline": "2026-04-01",
                    "priority": "high",
                },
                {
                    "description": "Review docs",
                    "assignee": None,
                    "deadline": None,
                    "priority": "low",
                },
            ],
        )
    analyzer = MagicMock()
    analyzer.analyze = AsyncMock(return_value=analysis)
    return analyzer


# ============================================================
# Pipeline Tests
# ============================================================


class TestMeetingServicePipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_success(self):
        db = _make_mock_db()
        whisper = _make_mock_whisper()
        analyzer = _make_mock_analyzer()
        svc = MeetingService(database=db, whisper=whisper, analyzer=analyzer)

        meeting = await svc.process_audio("/recordings/test.wav")

        assert meeting.status == MeetingStatus.COMPLETE
        assert meeting.title == "Team Sync"  # from suggested_title
        assert meeting.transcript_text == "Hello from the meeting"
        assert meeting.duration_seconds == 120.0
        assert meeting.analysis is not None
        assert meeting.analysis.sentiment == "productive"

    @pytest.mark.asyncio
    async def test_pipeline_preserves_explicit_title(self):
        db = _make_mock_db()
        whisper = _make_mock_whisper()
        analyzer = _make_mock_analyzer()
        svc = MeetingService(database=db, whisper=whisper, analyzer=analyzer)

        meeting = await svc.process_audio("/test.wav", title="My Custom Title")
        assert meeting.title == "My Custom Title"

    @pytest.mark.asyncio
    async def test_pipeline_transcription_failure(self):
        db = _make_mock_db()
        whisper = MagicMock()
        whisper.transcribe = AsyncMock(side_effect=RuntimeError("Corrupt audio"))
        analyzer = _make_mock_analyzer()
        svc = MeetingService(database=db, whisper=whisper, analyzer=analyzer)

        meeting = await svc.process_audio("/bad.wav")
        assert meeting.status == MeetingStatus.FAILED
        assert "Corrupt audio" in meeting.error

    @pytest.mark.asyncio
    async def test_pipeline_analysis_failure(self):
        db = _make_mock_db()
        whisper = _make_mock_whisper()
        analyzer = MagicMock()
        analyzer.analyze = AsyncMock(side_effect=RuntimeError("LLM timeout"))
        svc = MeetingService(database=db, whisper=whisper, analyzer=analyzer)

        meeting = await svc.process_audio("/test.wav")
        assert meeting.status == MeetingStatus.FAILED
        assert "LLM timeout" in meeting.error
        # Transcript should still be stored
        assert meeting.transcript_text == "Hello from the meeting"

    @pytest.mark.asyncio
    async def test_pipeline_no_whisper(self):
        db = _make_mock_db()
        svc = MeetingService(database=db, whisper=None, analyzer=_make_mock_analyzer())

        meeting = await svc.process_audio("/test.wav")
        assert meeting.status == MeetingStatus.FAILED
        assert "not configured" in meeting.error.lower()

    @pytest.mark.asyncio
    async def test_pipeline_no_analyzer(self):
        db = _make_mock_db()
        whisper = _make_mock_whisper()
        svc = MeetingService(database=db, whisper=whisper, analyzer=None)

        meeting = await svc.process_audio("/test.wav")
        assert meeting.status == MeetingStatus.FAILED
        assert "not configured" in meeting.error.lower()

    @pytest.mark.asyncio
    async def test_pipeline_creates_action_items(self):
        db = _make_mock_db()
        whisper = _make_mock_whisper()
        analyzer = _make_mock_analyzer()
        svc = MeetingService(database=db, whisper=whisper, analyzer=analyzer)

        meeting = await svc.process_audio("/test.wav")
        assert len(db._action_items) == 2


# ============================================================
# Meeting CRUD
# ============================================================


class TestMeetingServiceCrud:
    @pytest.mark.asyncio
    async def test_get_meeting(self):
        db = _make_mock_db()
        svc = MeetingService(database=db, whisper=_make_mock_whisper(), analyzer=_make_mock_analyzer())
        await svc.process_audio("/test.wav")

        meetings = await svc.list_meetings()
        assert len(meetings) == 1

        meeting = await svc.get_meeting(meetings[0].id)
        assert meeting is not None
        assert meeting.audio_file == "/test.wav"

    @pytest.mark.asyncio
    async def test_get_meeting_not_found(self):
        db = _make_mock_db()
        svc = MeetingService(database=db)
        result = await svc.get_meeting("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_meetings(self):
        db = _make_mock_db()
        svc = MeetingService(database=db, whisper=_make_mock_whisper(), analyzer=_make_mock_analyzer())
        await svc.process_audio("/a.wav")
        await svc.process_audio("/b.wav")

        meetings = await svc.list_meetings()
        assert len(meetings) == 2

    @pytest.mark.asyncio
    async def test_delete_meeting(self):
        db = _make_mock_db()
        svc = MeetingService(database=db, whisper=_make_mock_whisper(), analyzer=_make_mock_analyzer())
        meeting = await svc.process_audio("/test.wav")

        deleted = await svc.delete_meeting(meeting.id)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        db = _make_mock_db()
        svc = MeetingService(database=db)
        deleted = await svc.delete_meeting("nope")
        assert deleted is False


# ============================================================
# Action Items
# ============================================================


class TestMeetingServiceActionItems:
    @pytest.mark.asyncio
    async def test_get_action_items_for_meeting(self):
        db = _make_mock_db()
        svc = MeetingService(database=db, whisper=_make_mock_whisper(), analyzer=_make_mock_analyzer())
        meeting = await svc.process_audio("/test.wav")

        items = await svc.get_action_items(meeting_id=meeting.id)
        assert len(items) == 2
        assert items[0].description in ("Write proposal", "Review docs")

    @pytest.mark.asyncio
    async def test_update_action_item_status(self):
        db = _make_mock_db()
        svc = MeetingService(database=db, whisper=_make_mock_whisper(), analyzer=_make_mock_analyzer())
        await svc.process_audio("/test.wav")

        items = await svc.get_action_items()
        item = items[0]

        updated = await svc.update_action_item(item.id, status="done")
        assert updated is not None
        assert updated.status == ActionItemStatus.DONE

    @pytest.mark.asyncio
    async def test_update_action_item_notes(self):
        db = _make_mock_db()
        svc = MeetingService(database=db, whisper=_make_mock_whisper(), analyzer=_make_mock_analyzer())
        await svc.process_audio("/test.wav")

        items = await svc.get_action_items()
        item = items[0]

        updated = await svc.update_action_item(item.id, notes="In progress, waiting on review")
        assert updated is not None


# ============================================================
# Theme Trends
# ============================================================


class TestMeetingServiceThemes:
    @pytest.mark.asyncio
    async def test_get_theme_trends(self):
        db = _make_mock_db()
        svc = MeetingService(database=db, whisper=_make_mock_whisper(), analyzer=_make_mock_analyzer())
        await svc.process_audio("/a.wav")
        await svc.process_audio("/b.wav")

        trends = await svc.get_theme_trends()
        # Both meetings have same themes: priorities, roadmap
        assert len(trends) >= 1


# ============================================================
# Reprocess
# ============================================================


class TestMeetingServiceReprocess:
    @pytest.mark.asyncio
    async def test_reprocess_success(self):
        db = _make_mock_db()
        svc = MeetingService(database=db, whisper=_make_mock_whisper(), analyzer=_make_mock_analyzer())
        meeting = await svc.process_audio("/test.wav")

        # Reprocess with a new analyzer response
        new_analysis = MeetingAnalysis(
            executive_summary="Updated analysis",
            themes=["new-theme"],
            suggested_title="Updated Title",
            action_items=[{"description": "New task", "priority": "low"}],
        )
        svc._analyzer = _make_mock_analyzer(new_analysis)
        result = await svc.reprocess(meeting.id)
        assert result.status == MeetingStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_reprocess_not_found(self):
        db = _make_mock_db()
        svc = MeetingService(database=db, analyzer=_make_mock_analyzer())
        with pytest.raises(ValueError, match="not found"):
            await svc.reprocess("nonexistent")


# ============================================================
# Initialize Tables
# ============================================================


class TestMeetingServiceInit:
    @pytest.mark.asyncio
    async def test_initialize_tables(self):
        db = _make_mock_db()
        svc = MeetingService(database=db)
        await svc.initialize_tables()
        assert db.execute.call_count >= 2  # Two CREATE TABLE calls
