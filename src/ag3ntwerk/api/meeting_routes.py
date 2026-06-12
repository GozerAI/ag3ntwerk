"""
Meeting Intelligence API routes for ag3ntwerk.

Provides endpoints for:
- Meeting listing, detail, upload, and deletion
- Action item management (list, filter, update status)
- Theme trend analysis
- Audio watcher control
"""

import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/meetings", tags=["meetings"])


# ============================================================
# Pydantic Models
# ============================================================


class MeetingListItem(BaseModel):
    id: str
    title: str
    status: str
    duration_seconds: Optional[float] = None
    source: str = "hidock"
    action_item_count: int = 0
    created_at: str


class MeetingDetail(BaseModel):
    id: str
    title: str
    audio_file: str
    status: str
    duration_seconds: Optional[float] = None
    transcript_text: Optional[str] = None
    transcript_segments: List[Dict[str, Any]] = []
    analysis: Optional[Dict[str, Any]] = None
    source: str = "hidock"
    tags: List[str] = []
    error: Optional[str] = None
    created_at: str
    updated_at: str


class ActionItemResponse(BaseModel):
    id: str
    meeting_id: str
    description: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    status: str
    priority: str
    notes: str = ""
    created_at: str


class ActionItemUpdate(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(open|in_progress|done|cancelled)$")
    notes: Optional[str] = None


class ThemeTrend(BaseModel):
    theme: str
    count: int


class WatcherStatusResponse(BaseModel):
    running: bool
    watch_dir: Optional[str] = None


# ============================================================
# Service Access
# ============================================================

# These are set during app startup by state.py
_meeting_service = None
_audio_watcher = None


def set_meeting_service(service):
    global _meeting_service
    _meeting_service = service


def set_audio_watcher(watcher):
    global _audio_watcher
    _audio_watcher = watcher


def _get_service():
    if _meeting_service is None:
        raise HTTPException(status_code=503, detail="Meeting service not initialized")
    return _meeting_service


# ============================================================
# Non-parameterized routes MUST come before /{meeting_id}
# ============================================================


@router.get("")
async def list_meetings(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """List meetings, newest first."""
    svc = _get_service()
    meetings = await svc.list_meetings(limit=limit, offset=offset, status=status)
    total = await svc.count_meetings(status=status)

    # Get action item counts
    items = []
    for m in meetings:
        action_items = await svc.get_action_items(meeting_id=m.id)
        items.append(
            MeetingListItem(
                id=m.id,
                title=m.title or "Untitled",
                status=m.status.value,
                duration_seconds=m.duration_seconds,
                source=m.source,
                action_item_count=len(action_items),
                created_at=str(m.created_at),
            ).model_dump()
        )

    return {"meetings": items, "total": total}


@router.post("/upload")
async def upload_audio(
    audio: UploadFile = File(...),
    source: str = Form(default="upload"),
    title: str = Form(default=""),
) -> Dict[str, Any]:
    """Upload an audio file for processing."""
    svc = _get_service()

    filename = audio.filename or "recording.wav"
    ext = Path(filename).suffix.lower()
    allowed = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".webm"}
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {ext}. Supported: {', '.join(allowed)}",
        )

    content = await audio.read()
    if len(content) > 500 * 1024 * 1024:  # 500MB limit
        raise HTTPException(status_code=400, detail="File too large (500MB max)")

    # Save to temp location
    temp_dir = tempfile.gettempdir()
    temp_path = Path(temp_dir) / f"meeting_upload_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}{ext}"
    with open(temp_path, "wb") as f:
        f.write(content)

    meeting = await svc.process_audio(str(temp_path), source=source, title=title)

    return {
        "id": meeting.id,
        "status": meeting.status.value,
        "title": meeting.title,
    }


@router.get("/action-items")
async def list_all_action_items(
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    meeting_id: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """List action items across all meetings with optional filters."""
    svc = _get_service()
    items = await svc.get_action_items(
        meeting_id=meeting_id,
        status=status,
        assignee=assignee,
        limit=limit,
    )
    return {
        "action_items": [
            ActionItemResponse(
                id=i.id,
                meeting_id=i.meeting_id,
                description=i.description,
                assignee=i.assignee,
                deadline=str(i.deadline) if i.deadline else None,
                status=i.status.value,
                priority=i.priority,
                notes=i.notes,
                created_at=str(i.created_at),
            ).model_dump()
            for i in items
        ],
        "count": len(items),
    }


@router.patch("/action-items/{item_id}")
async def update_action_item(item_id: str, update: ActionItemUpdate) -> Dict[str, Any]:
    """Update an action item's status and/or notes."""
    svc = _get_service()
    updated = await svc.update_action_item(
        item_id,
        status=update.status,
        notes=update.notes,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Action item not found")

    return {
        "id": updated.id,
        "status": updated.status.value,
        "notes": updated.notes,
        "updated": True,
    }


@router.post("/action-items/{item_id}/remind")
async def send_reminder(item_id: str) -> Dict[str, Any]:
    """Manually send a reminder for an action item."""
    svc = _get_service()
    item = await svc._get_action_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    meeting = await svc.get_meeting(item.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Parent meeting not found")

    try:
        await svc._send_reminder(meeting, item)
        return {"sent": True, "item_id": item_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send reminder: {e}")


@router.get("/themes")
async def get_themes(limit: int = 20) -> Dict[str, Any]:
    """Get theme frequency across all meetings."""
    svc = _get_service()
    trends = await svc.get_theme_trends(limit=limit)
    return {"themes": trends}


@router.get("/watcher/status")
async def watcher_status() -> Dict[str, Any]:
    """Get audio watcher status."""
    if _audio_watcher is None:
        return WatcherStatusResponse(running=False).model_dump()

    return WatcherStatusResponse(
        running=_audio_watcher.is_running(),
        watch_dir=_audio_watcher.config.watch_dir if hasattr(_audio_watcher, "config") else None,
    ).model_dump()


@router.post("/watcher/start")
async def start_watcher() -> Dict[str, Any]:
    """Start the audio watcher."""
    if _audio_watcher is None:
        raise HTTPException(status_code=503, detail="Audio watcher not configured")

    _audio_watcher.start()
    return {"started": True}


@router.post("/watcher/stop")
async def stop_watcher() -> Dict[str, Any]:
    """Stop the audio watcher."""
    if _audio_watcher is None:
        raise HTTPException(status_code=503, detail="Audio watcher not configured")

    _audio_watcher.stop()
    return {"stopped": True}


# ============================================================
# Parameterized /{meeting_id} routes MUST come last
# ============================================================


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str) -> Dict[str, Any]:
    """Get meeting detail with full analysis."""
    svc = _get_service()
    meeting = await svc.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return MeetingDetail(
        id=meeting.id,
        title=meeting.title or "Untitled",
        audio_file=meeting.audio_file,
        status=meeting.status.value,
        duration_seconds=meeting.duration_seconds,
        transcript_text=meeting.transcript_text,
        transcript_segments=meeting.transcript_segments,
        analysis=meeting.analysis.model_dump() if meeting.analysis else None,
        source=meeting.source,
        tags=meeting.tags,
        error=meeting.error,
        created_at=str(meeting.created_at),
        updated_at=str(meeting.updated_at),
    ).model_dump()


@router.post("/{meeting_id}/reprocess")
async def reprocess_meeting(meeting_id: str) -> Dict[str, Any]:
    """Re-run LLM analysis on an existing transcript."""
    svc = _get_service()
    try:
        meeting = await svc.reprocess(meeting_id)
        return {
            "id": meeting.id,
            "status": meeting.status.value,
            "title": meeting.title,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{meeting_id}")
async def delete_meeting(meeting_id: str) -> Dict[str, Any]:
    """Delete a meeting and its action items."""
    svc = _get_service()
    deleted = await svc.delete_meeting(meeting_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"deleted": True}


@router.get("/{meeting_id}/action-items")
async def get_meeting_action_items(meeting_id: str) -> Dict[str, Any]:
    """Get action items for a specific meeting."""
    svc = _get_service()
    meeting = await svc.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    items = await svc.get_action_items(meeting_id=meeting_id)
    return {
        "action_items": [
            ActionItemResponse(
                id=i.id,
                meeting_id=i.meeting_id,
                description=i.description,
                assignee=i.assignee,
                deadline=str(i.deadline) if i.deadline else None,
                status=i.status.value,
                priority=i.priority,
                notes=i.notes,
                created_at=str(i.created_at),
            ).model_dump()
            for i in items
        ],
        "count": len(items),
    }
