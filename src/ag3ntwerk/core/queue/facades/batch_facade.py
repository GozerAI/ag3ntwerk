"""
Batch Facade - Batch operations for tasks.

This facade handles:
- Batch enqueueing (single transaction)
- Batch cancellation
- Batch retry from dead letter
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.queue.models import TaskState
from ag3ntwerk.core.queue._connection import ConnectionManager
from ag3ntwerk.core.queue._utils import generate_id, utc_now, to_json

logger = logging.getLogger(__name__)


class BatchFacade:
    """
    Facade for batch operations.

    Manages bulk task operations in single transactions.
    """

    def __init__(self, connection: ConnectionManager):
        """
        Initialize the batch facade.

        Args:
            connection: Shared connection manager
        """
        self._connection = connection

    async def enqueue_batch(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Enqueue multiple tasks in a single transaction.

        Args:
            tasks: List of task dicts with keys: task_type, payload, priority, etc.

        Returns:
            List of task IDs

        Raises:
            Exception: If transaction fails (will be rolled back)
        """
        task_ids = []
        now = utc_now()

        try:
            for task_data in tasks:
                task_id = generate_id()
                task_ids.append(task_id)

                scheduled_at = task_data.get("scheduled_at")
                delay = task_data.get("delay_seconds")
                if delay:
                    scheduled_at = now + timedelta(seconds=delay)

                state = TaskState.SCHEDULED if scheduled_at else TaskState.PENDING

                self._connection.execute(
                    """
                    INSERT INTO tasks (
                        id, task_type, payload, priority, state,
                        created_at, scheduled_at, max_attempts, metadata,
                        group_id, parent_id, timeout
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        task_data["task_type"],
                        to_json(task_data.get("payload", {})),
                        task_data.get("priority", 5),
                        state.value,
                        now.isoformat(),
                        scheduled_at.isoformat() if scheduled_at else None,
                        task_data.get("max_attempts", 3),
                        to_json(task_data.get("metadata", {})),
                        task_data.get("group_id"),
                        task_data.get("parent_id"),
                        task_data.get("timeout"),
                    ),
                )

            self._connection.commit()
            logger.info(f"Batch enqueued {len(task_ids)} tasks")

        except Exception as e:
            self._connection.rollback()
            logger.error(f"Batch enqueue failed: {e}")
            raise

        return task_ids

    async def cancel_batch(
        self,
        task_ids: Optional[List[str]] = None,
        task_type: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> int:
        """
        Cancel multiple tasks.

        Args:
            task_ids: Specific task IDs to cancel
            task_type: Cancel all pending tasks of this type
            group_id: Cancel all tasks in this group

        Returns:
            Number of tasks cancelled
        """
        now = utc_now().isoformat()

        if task_ids:
            placeholders = ",".join("?" * len(task_ids))
            cursor = self._connection.execute(
                f"""
                UPDATE tasks
                SET state = 'dead', last_error = 'Batch cancelled', completed_at = ?
                WHERE id IN ({placeholders}) AND state IN ('pending', 'scheduled')
                """,
                [now] + task_ids,
            )
        elif task_type:
            cursor = self._connection.execute(
                """
                UPDATE tasks
                SET state = 'dead', last_error = 'Batch cancelled', completed_at = ?
                WHERE task_type = ? AND state IN ('pending', 'scheduled')
                """,
                (now, task_type),
            )
        elif group_id:
            cursor = self._connection.execute(
                """
                UPDATE tasks
                SET state = 'dead', last_error = 'Batch cancelled', completed_at = ?
                WHERE group_id = ? AND state IN ('pending', 'scheduled')
                """,
                (now, group_id),
            )
        else:
            return 0

        self._connection.commit()
        count = cursor.rowcount
        logger.info(f"Batch cancelled {count} tasks")
        return count

    async def retry_batch(
        self,
        task_type: Optional[str] = None,
        group_id: Optional[str] = None,
        max_tasks: int = 100,
    ) -> int:
        """
        Retry multiple dead tasks.

        Args:
            task_type: Only retry tasks of this type
            group_id: Only retry tasks in this group
            max_tasks: Maximum tasks to retry

        Returns:
            Number of tasks requeued
        """
        now = utc_now().isoformat()

        if task_type:
            cursor = self._connection.execute(
                """
                UPDATE tasks
                SET state = 'pending', attempts = 0, last_error = NULL,
                    next_retry_at = NULL, started_at = NULL, completed_at = NULL,
                    created_at = ?
                WHERE id IN (
                    SELECT id FROM tasks
                    WHERE state = 'dead' AND task_type = ?
                    LIMIT ?
                )
                """,
                (now, task_type, max_tasks),
            )
        elif group_id:
            cursor = self._connection.execute(
                """
                UPDATE tasks
                SET state = 'pending', attempts = 0, last_error = NULL,
                    next_retry_at = NULL, started_at = NULL, completed_at = NULL,
                    created_at = ?
                WHERE id IN (
                    SELECT id FROM tasks
                    WHERE state = 'dead' AND group_id = ?
                    LIMIT ?
                )
                """,
                (now, group_id, max_tasks),
            )
        else:
            cursor = self._connection.execute(
                """
                UPDATE tasks
                SET state = 'pending', attempts = 0, last_error = NULL,
                    next_retry_at = NULL, started_at = NULL, completed_at = NULL,
                    created_at = ?
                WHERE id IN (
                    SELECT id FROM tasks WHERE state = 'dead' LIMIT ?
                )
                """,
                (now, max_tasks),
            )

        self._connection.commit()
        count = cursor.rowcount
        logger.info(f"Batch retried {count} tasks")
        return count

    async def get_group_stats(self, group_id: str) -> Dict[str, int]:
        """
        Get statistics for a task group.

        Args:
            group_id: Group ID

        Returns:
            Dictionary of state counts
        """
        cursor = self._connection.execute(
            """
            SELECT state, COUNT(*) as count
            FROM tasks
            WHERE group_id = ?
            GROUP BY state
            """,
            (group_id,),
        )

        stats = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "dead": 0,
            "scheduled": 0,
            "total": 0,
        }

        for row in cursor.fetchall():
            stats[row["state"]] = row["count"]
            stats["total"] += row["count"]

        return stats

    def get_stats(self) -> Dict[str, Any]:
        """Get batch facade statistics."""
        # Get count of groups
        cursor = self._connection.execute(
            """
            SELECT COUNT(DISTINCT group_id) as count
            FROM tasks
            WHERE group_id IS NOT NULL
            """
        )
        group_count = cursor.fetchone()["count"]

        return {
            "active_groups": group_count,
        }
