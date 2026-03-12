"""
Event Facade - Task event emission and listener management.

This facade handles:
- Storing events in the database
- Notifying event listeners
- Querying task history
"""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ag3ntwerk.core.queue.models import TaskEvent
from ag3ntwerk.core.queue._connection import ConnectionManager
from ag3ntwerk.core.queue._utils import utc_now, to_json, from_json

logger = logging.getLogger(__name__)


class EventFacade:
    """
    Facade for event-related operations.

    Manages event emission and listeners.
    """

    def __init__(self, connection: ConnectionManager):
        """
        Initialize the event facade.

        Args:
            connection: Shared connection manager
        """
        self._connection = connection
        self._listeners: List[Callable[[TaskEvent], Awaitable[None]]] = []

    def add_listener(
        self,
        listener: Callable[[TaskEvent], Awaitable[None]],
    ) -> None:
        """
        Add an event listener.

        Args:
            listener: Async function called with TaskEvent
        """
        self._listeners.append(listener)

    async def emit(
        self,
        event_type: str,
        task_id: str,
        task_type: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit a task event.

        Args:
            event_type: Type of event (created, started, completed, failed, etc.)
            task_id: Task ID
            task_type: Task type
            details: Optional event details
        """
        now = utc_now()

        # Store in database
        self._connection.execute(
            """
            INSERT INTO task_events (task_id, event_type, timestamp, details)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, event_type, now.isoformat(), to_json(details or {})),
        )
        self._connection.commit()

        # Notify listeners
        event = TaskEvent(
            event_type=event_type,
            task_id=task_id,
            task_type=task_type,
            timestamp=now,
            details=details or {},
        )

        for listener in self._listeners:
            try:
                await listener(event)
            except Exception as e:
                logger.error(f"Event listener error: {e}")

    async def get_task_history(
        self,
        task_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get event history for a task.

        Args:
            task_id: Task ID
            limit: Maximum events to return

        Returns:
            List of event dictionaries
        """
        cursor = self._connection.execute(
            """
            SELECT * FROM task_events
            WHERE task_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (task_id, limit),
        )

        return [
            {
                "event_type": row["event_type"],
                "timestamp": row["timestamp"],
                "details": from_json(row["details"]) or {},
            }
            for row in cursor.fetchall()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get event facade statistics."""
        cursor = self._connection.execute("SELECT COUNT(*) as count FROM task_events")
        total_events = cursor.fetchone()["count"]

        return {
            "total_events": total_events,
            "listener_count": len(self._listeners),
        }
