"""
Meeting Intelligence service for ag3ntwerk.

Orchestrates the full meeting pipeline:
audio -> transcription -> LLM analysis -> persistence -> reminders.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ag3ntwerk.integrations.communication.ics_generator import generate_ics
from ag3ntwerk.integrations.voice.meeting_analyzer import MeetingAnalyzer
from ag3ntwerk.integrations.voice.whisper import (
    TranscriptionConfig,
    WhisperIntegration,
    WhisperModel,
)
from ag3ntwerk.models.meeting import (
    ActionItem,
    ActionItemStatus,
    Meeting,
    MeetingAnalysis,
    MeetingStatus,
)
from ag3ntwerk.persistence.database import DatabaseManager

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _utcnow().isoformat()


class MeetingService:
    """
    Orchestrates meeting recording processing and action item management.

    Pipeline: transcribe audio -> analyze with LLM -> persist -> schedule reminders.
    """

    # Schema creation SQL (fallback when Alembic not used)
    _MEETINGS_DDL = """
        CREATE TABLE IF NOT EXISTS meetings (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            audio_file TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            duration_seconds REAL,
            transcript_text TEXT,
            transcript_segments TEXT DEFAULT '[]',
            analysis TEXT,
            source TEXT DEFAULT 'hidock',
            tags TEXT DEFAULT '[]',
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """
    _ACTION_ITEMS_DDL = """
        CREATE TABLE IF NOT EXISTS action_items (
            id TEXT PRIMARY KEY,
            meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            assignee TEXT,
            assignee_email TEXT,
            deadline TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            priority TEXT NOT NULL DEFAULT 'medium',
            notes TEXT DEFAULT '',
            calendar_event_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """

    def __init__(
        self,
        database: DatabaseManager,
        whisper: Optional[WhisperIntegration] = None,
        analyzer: Optional[MeetingAnalyzer] = None,
        calendar=None,
        email=None,
        whisper_model: WhisperModel = WhisperModel.MEDIUM,
    ):
        self._db = database
        self._whisper = whisper
        self._analyzer = analyzer
        self._calendar = calendar
        self._email = email
        self._whisper_model = whisper_model

    async def initialize_tables(self):
        """Create tables if they don't exist (fallback for non-Alembic setups)."""
        await self._db.execute(self._MEETINGS_DDL)
        await self._db.execute(self._ACTION_ITEMS_DDL)

    # ------------------------------------------------------------------
    # Full Pipeline
    # ------------------------------------------------------------------

    async def process_audio(
        self,
        audio_path: str,
        source: str = "hidock",
        title: str = "",
    ) -> Meeting:
        """
        Process an audio recording through the full pipeline.

        1. Create meeting record
        2. Transcribe with Whisper
        3. Analyze with LLM
        4. Persist results
        5. Schedule reminders for action items with deadlines
        """
        meeting_id = f"mtg_{uuid4().hex[:12]}"
        now = _now_iso()

        # 1. Create meeting record
        meeting = Meeting(
            id=meeting_id,
            title=title,
            audio_file=audio_path,
            status=MeetingStatus.QUEUED,
            source=source,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        await self._insert_meeting(meeting)

        # 2. Transcribe
        try:
            await self._update_status(meeting_id, MeetingStatus.TRANSCRIBING)

            if not self._whisper:
                raise RuntimeError("Whisper integration not configured")

            config = TranscriptionConfig(model=self._whisper_model)
            result = await self._whisper.transcribe(audio_path, config)

            meeting.transcript_text = result.text
            meeting.transcript_segments = [
                {"id": s.id, "start": s.start, "end": s.end, "text": s.text}
                for s in result.segments
            ]
            meeting.duration_seconds = result.duration

            await self._db.execute(
                "UPDATE meetings SET transcript_text = ?, transcript_segments = ?, "
                "duration_seconds = ?, updated_at = ? WHERE id = ?",
                (
                    result.text,
                    json.dumps(meeting.transcript_segments),
                    result.duration,
                    _now_iso(),
                    meeting_id,
                ),
            )

        except Exception as e:
            logger.error("Transcription failed for %s: %s", meeting_id, e)
            await self._fail_meeting(meeting_id, f"Transcription failed: {e}")
            meeting.status = MeetingStatus.FAILED
            meeting.error = str(e)
            return meeting

        # 3. Analyze
        try:
            await self._update_status(meeting_id, MeetingStatus.ANALYZING)

            if not self._analyzer:
                raise RuntimeError("Meeting analyzer not configured")

            analysis = await self._analyzer.analyze(result.text, meeting_id)
            meeting.analysis = analysis

            # Set title from LLM suggestion if not provided
            if not title and analysis.suggested_title:
                meeting.title = analysis.suggested_title

            await self._db.execute(
                "UPDATE meetings SET analysis = ?, title = ?, updated_at = ? WHERE id = ?",
                (
                    json.dumps(analysis.model_dump(), default=str),
                    meeting.title,
                    _now_iso(),
                    meeting_id,
                ),
            )

            # 4. Create action items
            await self._create_action_items(meeting_id, analysis)

        except Exception as e:
            logger.error("Analysis failed for %s: %s", meeting_id, e)
            await self._fail_meeting(meeting_id, f"Analysis failed: {e}")
            meeting.status = MeetingStatus.FAILED
            meeting.error = str(e)
            return meeting

        # 5. Mark complete
        await self._update_status(meeting_id, MeetingStatus.COMPLETE)
        meeting.status = MeetingStatus.COMPLETE

        # 6. Schedule reminders (best-effort)
        try:
            await self.schedule_reminders(meeting)
        except Exception as e:
            logger.warning("Reminder scheduling failed for %s: %s", meeting_id, e)

        return meeting

    async def reprocess(self, meeting_id: str) -> Meeting:
        """Re-run LLM analysis on an existing transcript."""
        meeting = await self.get_meeting(meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")
        if not meeting.transcript_text:
            raise ValueError(f"Meeting {meeting_id} has no transcript")

        await self._update_status(meeting_id, MeetingStatus.ANALYZING)

        try:
            if not self._analyzer:
                raise RuntimeError("Meeting analyzer not configured")

            analysis = await self._analyzer.analyze(meeting.transcript_text, meeting_id)
            meeting.analysis = analysis

            if not meeting.title and analysis.suggested_title:
                meeting.title = analysis.suggested_title

            await self._db.execute(
                "UPDATE meetings SET analysis = ?, title = ?, status = ?, updated_at = ? WHERE id = ?",
                (
                    json.dumps(analysis.model_dump(), default=str),
                    meeting.title,
                    MeetingStatus.COMPLETE.value,
                    _now_iso(),
                    meeting_id,
                ),
            )

            # Delete old action items and recreate
            await self._db.execute(
                "DELETE FROM action_items WHERE meeting_id = ?", (meeting_id,)
            )
            await self._create_action_items(meeting_id, analysis)

            meeting.status = MeetingStatus.COMPLETE
            return meeting

        except Exception as e:
            await self._fail_meeting(meeting_id, f"Reprocessing failed: {e}")
            meeting.status = MeetingStatus.FAILED
            meeting.error = str(e)
            return meeting

    # ------------------------------------------------------------------
    # Meeting CRUD
    # ------------------------------------------------------------------

    async def get_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """Get a single meeting by ID."""
        row = await self._db.fetch_one(
            "SELECT * FROM meetings WHERE id = ?", (meeting_id,)
        )
        if not row:
            return None
        return self._row_to_meeting(row)

    async def list_meetings(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[Meeting]:
        """List meetings, newest first."""
        if status:
            rows = await self._db.fetch_all(
                "SELECT * FROM meetings WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset),
            )
        else:
            rows = await self._db.fetch_all(
                "SELECT * FROM meetings ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [self._row_to_meeting(r) for r in rows]

    async def delete_meeting(self, meeting_id: str) -> bool:
        """Delete a meeting and its action items."""
        affected = await self._db.execute(
            "DELETE FROM meetings WHERE id = ?", (meeting_id,)
        )
        return affected > 0

    async def count_meetings(self, status: Optional[str] = None) -> int:
        """Count meetings, optionally filtered by status."""
        if status:
            row = await self._db.fetch_one(
                "SELECT COUNT(*) as cnt FROM meetings WHERE status = ?", (status,)
            )
        else:
            row = await self._db.fetch_one("SELECT COUNT(*) as cnt FROM meetings")
        return row["cnt"] if row else 0

    # ------------------------------------------------------------------
    # Action Items
    # ------------------------------------------------------------------

    async def get_action_items(
        self,
        meeting_id: Optional[str] = None,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        limit: int = 100,
    ) -> List[ActionItem]:
        """Get action items with optional filters."""
        conditions = []
        params: list = []

        if meeting_id:
            conditions.append("meeting_id = ?")
            params.append(meeting_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if assignee:
            conditions.append("assignee = ?")
            params.append(assignee)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        rows = await self._db.fetch_all(
            f"SELECT * FROM action_items WHERE {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        return [self._row_to_action_item(r) for r in rows]

    async def update_action_item(
        self,
        item_id: str,
        status: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[ActionItem]:
        """Update an action item's status and/or notes."""
        updates = []
        params: list = []

        if status:
            updates.append("status = ?")
            params.append(status)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if not updates:
            return await self._get_action_item(item_id)

        updates.append("updated_at = ?")
        params.append(_now_iso())
        params.append(item_id)

        await self._db.execute(
            f"UPDATE action_items SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        return await self._get_action_item(item_id)

    async def _get_action_item(self, item_id: str) -> Optional[ActionItem]:
        row = await self._db.fetch_one(
            "SELECT * FROM action_items WHERE id = ?", (item_id,)
        )
        return self._row_to_action_item(row) if row else None

    # ------------------------------------------------------------------
    # Themes
    # ------------------------------------------------------------------

    async def get_theme_trends(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Aggregate themes across all completed meetings."""
        rows = await self._db.fetch_all(
            "SELECT analysis FROM meetings WHERE status = ? AND analysis IS NOT NULL",
            (MeetingStatus.COMPLETE.value,),
        )
        theme_counts: Dict[str, int] = {}
        for row in rows:
            try:
                analysis = json.loads(row["analysis"])
                for theme in analysis.get("themes", []):
                    theme_lower = theme.lower().strip()
                    if theme_lower:
                        theme_counts[theme_lower] = theme_counts.get(theme_lower, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue

        sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"theme": t, "count": c}
            for t, c in sorted_themes[:limit]
        ]

    # ------------------------------------------------------------------
    # Reminders
    # ------------------------------------------------------------------

    async def schedule_reminders(self, meeting: Meeting):
        """Send email reminders with .ics for action items that have deadlines."""
        if not self._email:
            logger.debug("No email integration configured, skipping reminders")
            return

        items = await self.get_action_items(meeting_id=meeting.id)
        for item in items:
            if not item.deadline:
                continue

            try:
                await self._send_reminder(meeting, item)
            except Exception as e:
                logger.warning(
                    "Failed to send reminder for action item %s: %s", item.id, e
                )

    async def _send_reminder(self, meeting: Meeting, item: ActionItem):
        """Send a single reminder for an action item."""
        from ag3ntwerk.integrations.communication.email import EmailMessage

        deadline = item.deadline
        # Event: 30 min block ending at deadline
        event_end = deadline
        event_start = deadline - timedelta(minutes=30)

        description = (
            f"Action item from meeting: {meeting.title or 'Untitled'}\n\n"
            f"{item.description}\n\n"
            f"Priority: {item.priority}\n"
            f"Meeting ID: {meeting.id}"
        )

        ics_bytes = generate_ics(
            title=f"[Action Item] {item.description[:80]}",
            description=description,
            start=event_start,
            end=event_end,
            attendees=[item.assignee_email] if item.assignee_email else [],
            uid=f"{item.id}@ag3ntwerk",
        )

        # Build email
        recipient = item.assignee_email or ""
        if not recipient:
            logger.debug("No email for action item %s, skipping", item.id)
            return

        msg = EmailMessage(
            subject=f"Reminder: {item.description[:80]}",
            to=[recipient],
            body=(
                f"You have an action item due {deadline.strftime('%B %d, %Y')}:\n\n"
                f"{item.description}\n\n"
                f"From meeting: {meeting.title or 'Untitled'}\n"
                f"Priority: {item.priority}\n\n"
                "An .ics calendar invite is attached."
            ),
        )
        msg.attachments = [
            {
                "filename": "reminder.ics",
                "content": ics_bytes,
                "content_type": "text/calendar",
            }
        ]

        await self._email.send(msg)
        logger.info("Sent reminder for action item %s to %s", item.id, recipient)

        # If calendar integration available, also create event
        if self._calendar:
            try:
                from ag3ntwerk.integrations.communication.calendar import CalendarEvent

                event = CalendarEvent(
                    title=f"[Action Item] {item.description[:80]}",
                    description=description,
                    start=event_start,
                    end=event_end,
                )
                created = await self._calendar.create_event(event)
                if created and hasattr(created, "id"):
                    await self._db.execute(
                        "UPDATE action_items SET calendar_event_id = ? WHERE id = ?",
                        (created.id, item.id),
                    )
            except Exception as e:
                logger.warning("Calendar event creation failed: %s", e)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _insert_meeting(self, meeting: Meeting):
        now = _now_iso()
        await self._db.execute(
            "INSERT INTO meetings (id, title, audio_file, status, source, tags, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                meeting.id,
                meeting.title,
                meeting.audio_file,
                meeting.status.value,
                meeting.source,
                json.dumps(meeting.tags),
                now,
                now,
            ),
        )

    async def _update_status(self, meeting_id: str, status: MeetingStatus):
        await self._db.execute(
            "UPDATE meetings SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, _now_iso(), meeting_id),
        )

    async def _fail_meeting(self, meeting_id: str, error: str):
        await self._db.execute(
            "UPDATE meetings SET status = ?, error = ?, updated_at = ? WHERE id = ?",
            (MeetingStatus.FAILED.value, error, _now_iso(), meeting_id),
        )

    async def _create_action_items(self, meeting_id: str, analysis: MeetingAnalysis):
        now = _now_iso()
        for item_data in analysis.action_items:
            item_id = f"ai_{uuid4().hex[:12]}"
            deadline = item_data.get("deadline")

            await self._db.execute(
                "INSERT INTO action_items "
                "(id, meeting_id, description, assignee, deadline, status, priority, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item_id,
                    meeting_id,
                    item_data.get("description", ""),
                    item_data.get("assignee"),
                    deadline,
                    ActionItemStatus.OPEN.value,
                    item_data.get("priority", "medium"),
                    now,
                    now,
                ),
            )

    def _row_to_meeting(self, row: Dict[str, Any]) -> Meeting:
        analysis = None
        if row.get("analysis"):
            try:
                analysis = MeetingAnalysis(**json.loads(row["analysis"]))
            except (json.JSONDecodeError, TypeError):
                pass

        segments = []
        if row.get("transcript_segments"):
            try:
                segments = json.loads(row["transcript_segments"])
            except (json.JSONDecodeError, TypeError):
                pass

        tags = []
        if row.get("tags"):
            try:
                tags = json.loads(row["tags"])
            except (json.JSONDecodeError, TypeError):
                pass

        return Meeting(
            id=row["id"],
            title=row.get("title", ""),
            audio_file=row["audio_file"],
            status=MeetingStatus(row["status"]),
            duration_seconds=row.get("duration_seconds"),
            transcript_text=row.get("transcript_text"),
            transcript_segments=segments,
            analysis=analysis,
            source=row.get("source", "hidock"),
            tags=tags,
            error=row.get("error"),
            created_at=row.get("created_at", _now_iso()),
            updated_at=row.get("updated_at", _now_iso()),
        )

    def _row_to_action_item(self, row: Dict[str, Any]) -> ActionItem:
        deadline = None
        if row.get("deadline"):
            try:
                deadline = datetime.fromisoformat(row["deadline"])
            except (ValueError, TypeError):
                pass

        return ActionItem(
            id=row["id"],
            meeting_id=row["meeting_id"],
            description=row["description"],
            assignee=row.get("assignee"),
            assignee_email=row.get("assignee_email"),
            deadline=deadline,
            status=ActionItemStatus(row.get("status", "open")),
            priority=row.get("priority", "medium"),
            notes=row.get("notes", ""),
            calendar_event_id=row.get("calendar_event_id"),
            created_at=row.get("created_at", _now_iso()),
            updated_at=row.get("updated_at", _now_iso()),
        )
