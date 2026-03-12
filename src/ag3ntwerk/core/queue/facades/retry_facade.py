"""
Retry Facade - Retry logic and dead letter queue operations.

This facade handles:
- Exponential backoff calculation
- Retry scheduling
- Dead letter queue operations
- Purging completed/dead tasks
"""

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from ag3ntwerk.core.queue._connection import ConnectionManager
from ag3ntwerk.core.queue._utils import utc_now

logger = logging.getLogger(__name__)


class RetryFacade:
    """
    Facade for retry-related operations.

    Manages retry scheduling and dead letter queue.
    """

    def __init__(
        self,
        connection: ConnectionManager,
        retry_base_delay: float = 5.0,
        retry_max_delay: float = 300.0,
    ):
        """
        Initialize the retry facade.

        Args:
            connection: Shared connection manager
            retry_base_delay: Base delay for retries (seconds)
            retry_max_delay: Maximum retry delay (seconds)
        """
        self._connection = connection
        self._retry_base_delay = retry_base_delay
        self._retry_max_delay = retry_max_delay

    def calculate_backoff(self, attempts: int) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempts: Number of attempts so far

        Returns:
            Delay in seconds
        """
        delay = min(
            self._retry_base_delay * (2 ** (attempts - 1)),
            self._retry_max_delay,
        )
        return delay

    async def schedule_retry(
        self,
        task_id: str,
        error: str,
    ) -> Optional[str]:
        """
        Schedule a task for retry.

        Args:
            task_id: Task ID
            error: Error message

        Returns:
            ISO timestamp of next retry, or None if moved to dead letter
        """
        # Get current attempt count
        cursor = self._connection.execute(
            "SELECT attempts, max_attempts FROM tasks WHERE id = ?",
            (task_id,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        attempts = row["attempts"]
        max_attempts = row["max_attempts"]

        if attempts >= max_attempts:
            # Move to dead letter queue
            await self.move_to_dead(task_id, error)
            return None

        # Calculate backoff
        delay = self.calculate_backoff(attempts)
        next_retry = utc_now() + timedelta(seconds=delay)

        self._connection.execute(
            """
            UPDATE tasks
            SET state = 'failed', last_error = ?, next_retry_at = ?
            WHERE id = ?
            """,
            (error, next_retry.isoformat(), task_id),
        )
        self._connection.commit()

        logger.debug(f"Task scheduled for retry: {task_id} at {next_retry}")
        return next_retry.isoformat()

    async def move_to_dead(self, task_id: str, error: str) -> None:
        """
        Move a task to the dead letter queue.

        Args:
            task_id: Task ID
            error: Error message
        """
        now = utc_now()

        self._connection.execute(
            """
            UPDATE tasks
            SET state = 'dead', last_error = ?, completed_at = ?
            WHERE id = ?
            """,
            (error, now.isoformat(), task_id),
        )
        self._connection.commit()

        logger.warning(f"Task moved to dead letter queue: {task_id}")

    async def retry_dead(self, task_id: str) -> bool:
        """
        Retry a task from the dead letter queue.

        Args:
            task_id: Task ID

        Returns:
            True if requeued, False if not found
        """
        now = utc_now().isoformat()

        cursor = self._connection.execute(
            """
            UPDATE tasks
            SET state = 'pending',
                attempts = 0,
                last_error = NULL,
                next_retry_at = NULL,
                started_at = NULL,
                completed_at = NULL,
                created_at = ?
            WHERE id = ? AND state = 'dead'
            """,
            (now, task_id),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    async def purge_completed(self, older_than_hours: int = 24) -> int:
        """
        Remove completed tasks older than specified hours.

        Only removes successfully completed tasks. Dead letter tasks are
        preserved for debugging/analysis. Use purge_dead() separately.

        Args:
            older_than_hours: Age threshold in hours

        Returns:
            Number of tasks removed
        """
        cutoff = (utc_now() - timedelta(hours=older_than_hours)).isoformat()

        cursor = self._connection.execute(
            """
            DELETE FROM tasks
            WHERE state = 'completed'
            AND completed_at < ?
            """,
            (cutoff,),
        )
        self._connection.commit()

        count = cursor.rowcount
        if count > 0:
            logger.info(f"Purged {count} completed tasks")

        return count

    async def purge_dead(self, older_than_hours: int = 168) -> int:
        """
        Remove dead letter tasks older than specified hours.

        Args:
            older_than_hours: Age threshold in hours (default 7 days)

        Returns:
            Number of tasks removed
        """
        cutoff = (utc_now() - timedelta(hours=older_than_hours)).isoformat()

        cursor = self._connection.execute(
            """
            DELETE FROM tasks
            WHERE state = 'dead'
            AND completed_at < ?
            """,
            (cutoff,),
        )
        self._connection.commit()
        return cursor.rowcount

    async def get_dead_count(self) -> int:
        """Get count of tasks in dead letter queue."""
        cursor = self._connection.execute(
            "SELECT COUNT(*) as count FROM tasks WHERE state = 'dead'"
        )
        return cursor.fetchone()["count"]

    async def list_dead(self, limit: int = 100) -> list:
        """
        List tasks in the dead letter queue.

        Args:
            limit: Maximum tasks to return

        Returns:
            List of (task_id, task_type, error) tuples
        """
        cursor = self._connection.execute(
            """
            SELECT id, task_type, last_error, completed_at
            FROM tasks
            WHERE state = 'dead'
            ORDER BY completed_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        return [
            {
                "id": row["id"],
                "task_type": row["task_type"],
                "error": row["last_error"],
                "dead_at": row["completed_at"],
            }
            for row in cursor.fetchall()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get retry facade statistics."""
        cursor = self._connection.execute(
            """
            SELECT
                COUNT(CASE WHEN state = 'dead' THEN 1 END) as dead_count,
                COUNT(CASE WHEN state = 'failed' AND next_retry_at IS NOT NULL THEN 1 END) as pending_retry
            FROM tasks
            """
        )
        row = cursor.fetchone()

        return {
            "dead_letter_count": row["dead_count"],
            "pending_retries": row["pending_retry"],
            "retry_base_delay": self._retry_base_delay,
            "retry_max_delay": self._retry_max_delay,
        }
