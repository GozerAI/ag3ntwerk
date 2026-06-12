"""Tests for Meeting Intelligence API routes."""

import json
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from ag3ntwerk.api.meeting_routes import (
    router,
    set_meeting_service,
    set_audio_watcher,
)
from ag3ntwerk.models.meeting import (
    ActionItem,
    ActionItemStatus,
    Meeting,
    MeetingAnalysis,
    MeetingStatus,
)


# ============================================================
# Fixtures
# ============================================================


def _now():
    return datetime.now(timezone.utc)


def _sample_meeting(
    id="mtg_001",
    title="Team Sync",
    status=MeetingStatus.COMPLETE,
    with_analysis=True,
):
    analysis = None
    if with_analysis:
        analysis = MeetingAnalysis(
            executive_summary="Good meeting.",
            themes=["roadmap", "hiring"],
            sentiment="productive",
            suggested_title="Team Sync",
            action_items=[
                {"description": "Write tests", "assignee": "Alice", "priority": "high"},
            ],
        )
    return Meeting(
        id=id,
        title=title,
        audio_file="/test.wav",
        status=status,
        duration_seconds=600.0,
        transcript_text="We discussed the roadmap...",
        analysis=analysis,
        created_at=_now(),
        updated_at=_now(),
    )


def _sample_action_item(id="ai_001", meeting_id="mtg_001"):
    return ActionItem(
        id=id,
        meeting_id=meeting_id,
        description="Write tests",
        assignee="Alice",
        status=ActionItemStatus.OPEN,
        priority="high",
        created_at=_now(),
        updated_at=_now(),
    )


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.list_meetings = AsyncMock(return_value=[_sample_meeting()])
    svc.count_meetings = AsyncMock(return_value=1)
    svc.get_meeting = AsyncMock(return_value=_sample_meeting())
    svc.delete_meeting = AsyncMock(return_value=True)
    svc.process_audio = AsyncMock(return_value=_sample_meeting())
    svc.reprocess = AsyncMock(return_value=_sample_meeting())
    svc.get_action_items = AsyncMock(return_value=[_sample_action_item()])
    svc.update_action_item = AsyncMock(return_value=_sample_action_item())
    svc.get_theme_trends = AsyncMock(return_value=[{"theme": "roadmap", "count": 5}])
    svc._get_action_item = AsyncMock(return_value=_sample_action_item())
    svc._send_reminder = AsyncMock()
    return svc


@pytest.fixture
def client(mock_service):
    app = FastAPI()
    app.include_router(router)
    set_meeting_service(mock_service)
    set_audio_watcher(None)
    yield TestClient(app)
    set_meeting_service(None)
    set_audio_watcher(None)


# ============================================================
# Meeting List & Detail
# ============================================================


class TestMeetingEndpoints:
    def test_list_meetings(self, client, mock_service):
        resp = client.get("/api/v1/meetings")
        assert resp.status_code == 200
        data = resp.json()
        assert "meetings" in data
        assert data["total"] == 1
        assert data["meetings"][0]["title"] == "Team Sync"

    def test_list_meetings_with_status_filter(self, client, mock_service):
        resp = client.get("/api/v1/meetings?status=complete")
        assert resp.status_code == 200
        mock_service.list_meetings.assert_called_once()

    def test_get_meeting_detail(self, client, mock_service):
        resp = client.get("/api/v1/meetings/mtg_001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "mtg_001"
        assert data["analysis"] is not None
        assert data["analysis"]["sentiment"] == "productive"

    def test_get_meeting_not_found(self, client, mock_service):
        mock_service.get_meeting = AsyncMock(return_value=None)
        resp = client.get("/api/v1/meetings/nonexistent")
        assert resp.status_code == 404

    def test_delete_meeting(self, client, mock_service):
        resp = client.delete("/api/v1/meetings/mtg_001")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_meeting_not_found(self, client, mock_service):
        mock_service.delete_meeting = AsyncMock(return_value=False)
        resp = client.delete("/api/v1/meetings/nonexistent")
        assert resp.status_code == 404


# ============================================================
# Upload
# ============================================================


class TestUploadEndpoint:
    def test_upload_audio(self, client, mock_service):
        audio_bytes = b"\x00" * 1024
        resp = client.post(
            "/api/v1/meetings/upload",
            files={"audio": ("test.wav", BytesIO(audio_bytes), "audio/wav")},
            data={"source": "upload", "title": "Test Meeting"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "mtg_001"
        mock_service.process_audio.assert_called_once()

    def test_upload_unsupported_format(self, client, mock_service):
        resp = client.post(
            "/api/v1/meetings/upload",
            files={"audio": ("test.txt", BytesIO(b"not audio"), "text/plain")},
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]


# ============================================================
# Reprocess
# ============================================================


class TestReprocessEndpoint:
    def test_reprocess(self, client, mock_service):
        resp = client.post("/api/v1/meetings/mtg_001/reprocess")
        assert resp.status_code == 200
        assert resp.json()["status"] == "complete"

    def test_reprocess_not_found(self, client, mock_service):
        mock_service.reprocess = AsyncMock(side_effect=ValueError("Meeting not found"))
        resp = client.post("/api/v1/meetings/nonexistent/reprocess")
        assert resp.status_code == 404


# ============================================================
# Action Items
# ============================================================


class TestActionItemEndpoints:
    def test_list_all_action_items(self, client, mock_service):
        resp = client.get("/api/v1/meetings/action-items")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["action_items"][0]["description"] == "Write tests"

    def test_list_action_items_with_filters(self, client, mock_service):
        resp = client.get("/api/v1/meetings/action-items?status=open&assignee=Alice")
        assert resp.status_code == 200

    def test_get_meeting_action_items(self, client, mock_service):
        resp = client.get("/api/v1/meetings/mtg_001/action-items")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_get_meeting_action_items_not_found(self, client, mock_service):
        mock_service.get_meeting = AsyncMock(return_value=None)
        resp = client.get("/api/v1/meetings/nonexistent/action-items")
        assert resp.status_code == 404

    def test_update_action_item_status(self, client, mock_service):
        resp = client.patch(
            "/api/v1/meetings/action-items/ai_001",
            json={"status": "done"},
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] is True

    def test_update_action_item_not_found(self, client, mock_service):
        mock_service.update_action_item = AsyncMock(return_value=None)
        resp = client.patch(
            "/api/v1/meetings/action-items/nonexistent",
            json={"status": "done"},
        )
        assert resp.status_code == 404

    def test_update_action_item_invalid_status(self, client, mock_service):
        resp = client.patch(
            "/api/v1/meetings/action-items/ai_001",
            json={"status": "invalid_status"},
        )
        assert resp.status_code == 422  # Validation error

    def test_send_reminder(self, client, mock_service):
        resp = client.post("/api/v1/meetings/action-items/ai_001/remind")
        assert resp.status_code == 200
        assert resp.json()["sent"] is True

    def test_send_reminder_item_not_found(self, client, mock_service):
        mock_service._get_action_item = AsyncMock(return_value=None)
        resp = client.post("/api/v1/meetings/action-items/nonexistent/remind")
        assert resp.status_code == 404


# ============================================================
# Themes
# ============================================================


class TestThemeEndpoints:
    def test_get_themes(self, client, mock_service):
        resp = client.get("/api/v1/meetings/themes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["themes"]) == 1
        assert data["themes"][0]["theme"] == "roadmap"


# ============================================================
# Watcher Control
# ============================================================


class TestWatcherEndpoints:
    def test_watcher_status_not_configured(self, client):
        resp = client.get("/api/v1/meetings/watcher/status")
        assert resp.status_code == 200
        assert resp.json()["running"] is False

    def test_watcher_start_not_configured(self, client):
        resp = client.post("/api/v1/meetings/watcher/start")
        assert resp.status_code == 503

    def test_watcher_stop_not_configured(self, client):
        resp = client.post("/api/v1/meetings/watcher/stop")
        assert resp.status_code == 503

    def test_watcher_status_configured(self, client):
        watcher = MagicMock()
        watcher.is_running = MagicMock(return_value=True)
        watcher.config = MagicMock()
        watcher.config.watch_dir = "/recordings"
        set_audio_watcher(watcher)

        resp = client.get("/api/v1/meetings/watcher/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["running"] is True
        assert data["watch_dir"] == "/recordings"

    def test_watcher_start(self, client):
        watcher = MagicMock()
        set_audio_watcher(watcher)

        resp = client.post("/api/v1/meetings/watcher/start")
        assert resp.status_code == 200
        watcher.start.assert_called_once()

    def test_watcher_stop(self, client):
        watcher = MagicMock()
        set_audio_watcher(watcher)

        resp = client.post("/api/v1/meetings/watcher/stop")
        assert resp.status_code == 200
        watcher.stop.assert_called_once()


# ============================================================
# Service Not Initialized
# ============================================================


class TestServiceNotInitialized:
    def test_returns_503_when_no_service(self):
        app = FastAPI()
        app.include_router(router)
        set_meeting_service(None)
        client = TestClient(app)

        resp = client.get("/api/v1/meetings")
        assert resp.status_code == 503
