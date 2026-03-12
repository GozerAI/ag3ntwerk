"""
Persistence Facade - Row conversion and database recovery operations.

This facade handles:
- Converting database rows to QueuedTask objects
- Recovery operations for crashed sessions
"""

import logging
import sqlite3
from typing import Optional

from ag3ntwerk.core.queue.models import QueuedTask, TaskState
from ag3ntwerk.core.queue._connection import ConnectionManager
from ag3ntwerk.core.queue._utils import from_json, parse_iso_datetime

logger = logging.getLogger(__name__)


class PersistenceFacade:
    """
    Facade for persistence-related operations.

    Handles row conversion and recovery.
    """

    def __init__(self, connection: ConnectionManager):
        """
        Initialize the persistence facade.

        Args:
            connection: Shared connection manager
        """
        self._connection = connection

    def row_to_task(self, row: sqlite3.Row) -> QueuedTask:
        """
        Convert a database row to a QueuedTask.

        Args:
            row: SQLite row

        Returns:
            QueuedTask instance
        """
        return QueuedTask(
            id=row["id"],
            task_type=row["task_type"],
            payload=from_json(row["payload"]) or {},
            priority=row["priority"],
            state=TaskState(row["state"]),
            created_at=parse_iso_datetime(row["created_at"]),
            scheduled_at=parse_iso_datetime(row["scheduled_at"]),
            started_at=parse_iso_datetime(row["started_at"]),
            completed_at=parse_iso_datetime(row["completed_at"]),
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            last_error=row["last_error"],
            next_retry_at=parse_iso_datetime(row["next_retry_at"]),
            metadata=from_json(row["metadata"]) or {},
            result=from_json(row["result"]),
        )

    async def recover_stuck_tasks(self) -> int:
        """
        Recover tasks that were processing when the system crashed.

        Returns:
            Number of tasks recovered
        """
        cursor = self._connection.execute(
            """
            UPDATE tasks
            SET state = 'pending', started_at = NULL, worker_id = NULL
            WHERE state = 'processing'
            """
        )
        self._connection.commit()

        count = cursor.rowcount
        if count > 0:
            logger.warning(f"Recovered {count} stuck tasks from previous session")

        return count

    def get_task_row(self, task_id: str) -> Optional[sqlite3.Row]:
        """
        Get a raw database row for a task.

        Args:
            task_id: Task ID

        Returns:
            Database row or None
        """
        cursor = self._connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        )
        return cursor.fetchone()
