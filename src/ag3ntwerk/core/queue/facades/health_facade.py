"""
Health Facade - Queue health monitoring and maintenance.

This facade handles:
- Queue health status checks
- Stuck task recovery
- Maintenance task scheduling
- Performance tracking
"""

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from ag3ntwerk.core.queue.models import QueueHealthStatus
from ag3ntwerk.core.queue._connection import ConnectionManager
from ag3ntwerk.core.queue._utils import utc_now, parse_iso_datetime

logger = logging.getLogger(__name__)


class HealthFacade:
    """
    Facade for health and maintenance operations.

    Manages queue health checks and maintenance tasks.
    """

    def __init__(
        self,
        connection: ConnectionManager,
        stuck_task_threshold: float = 600.0,
    ):
        """
        Initialize the health facade.

        Args:
            connection: Shared connection manager
            stuck_task_threshold: Seconds before a processing task is considered stuck
        """
        self._connection = connection
        self._stuck_task_threshold = stuck_task_threshold
        self._maintenance_task: Optional[asyncio.Task] = None
        self._running = False

        # Callbacks for cross-facade operations
        self._recover_stuck_callback: Optional[Any] = None
        self._purge_callback: Optional[Any] = None
        self._cleanup_tracking_callback: Optional[Any] = None

    def set_callbacks(
        self,
        recover_stuck: Optional[Any] = None,
        purge_completed: Optional[Any] = None,
        cleanup_tracking: Optional[Any] = None,
    ) -> None:
        """
        Set callbacks for cross-facade operations.

        Args:
            recover_stuck: Callback to recover stuck tasks
            purge_completed: Callback to purge completed tasks
            cleanup_tracking: Callback to clean up performance tracking
        """
        self._recover_stuck_callback = recover_stuck
        self._purge_callback = purge_completed
        self._cleanup_tracking_callback = cleanup_tracking

    async def get_health(self) -> QueueHealthStatus:
        """
        Get queue health status.

        Returns:
            QueueHealthStatus with health indicators
        """
        now = utc_now()
        status = QueueHealthStatus()

        # Get counts by state
        cursor = self._connection.execute(
            """
            SELECT state, COUNT(*) as count
            FROM tasks
            GROUP BY state
            """
        )

        pending = 0
        dead = 0
        for row in cursor.fetchall():
            if row["state"] == "pending":
                pending = row["count"]
            elif row["state"] == "dead":
                dead = row["count"]

        status.processing_backlog = pending
        status.dead_letter_count = dead

        # Check for stuck tasks
        stuck_threshold = (now - timedelta(seconds=self._stuck_task_threshold)).isoformat()
        cursor = self._connection.execute(
            """
            SELECT COUNT(*) as count FROM tasks
            WHERE state = 'processing' AND started_at < ?
            """,
            (stuck_threshold,),
        )
        status.stuck_tasks = cursor.fetchone()["count"]

        # Get oldest pending task age
        cursor = self._connection.execute(
            """
            SELECT MIN(created_at) as oldest FROM tasks
            WHERE state = 'pending'
            """
        )
        row = cursor.fetchone()
        if row["oldest"]:
            oldest = parse_iso_datetime(row["oldest"])
            if oldest:
                status.oldest_pending_age_seconds = (now - oldest).total_seconds()

        # Determine health
        issues = []

        if status.stuck_tasks > 0:
            issues.append(f"{status.stuck_tasks} stuck tasks detected")
            status.healthy = False

        if status.dead_letter_count > 100:
            issues.append(f"High dead letter count: {status.dead_letter_count}")

        if status.processing_backlog > 1000:
            issues.append(f"Large processing backlog: {status.processing_backlog}")

        if status.oldest_pending_age_seconds and status.oldest_pending_age_seconds > 3600:
            hours = status.oldest_pending_age_seconds / 3600
            issues.append(f"Oldest pending task is {hours:.1f} hours old")

        status.issues = issues
        return status

    async def recover_stuck(self) -> int:
        """
        Recover tasks stuck in processing state.

        Returns:
            Number of tasks recovered
        """
        threshold = (utc_now() - timedelta(seconds=self._stuck_task_threshold)).isoformat()

        cursor = self._connection.execute(
            """
            UPDATE tasks
            SET state = 'pending', started_at = NULL, worker_id = NULL
            WHERE state = 'processing' AND started_at < ?
            """,
            (threshold,),
        )
        self._connection.commit()

        count = cursor.rowcount
        if count > 0:
            logger.warning(f"Recovered {count} stuck tasks")

        return count

    async def start_maintenance(
        self,
        interval: float = 60.0,
        purge_hours: int = 168,
    ) -> None:
        """
        Start the maintenance task.

        Args:
            interval: Seconds between maintenance runs
            purge_hours: Hours after which to purge completed tasks
        """
        self._running = True

        async def maintenance_loop():
            while self._running:
                try:
                    await self._run_maintenance(purge_hours)
                except Exception as e:
                    logger.error(f"Maintenance error: {e}")
                await asyncio.sleep(interval)

        self._maintenance_task = asyncio.create_task(maintenance_loop())
        logger.info("Started queue maintenance task")

    async def stop_maintenance(self) -> None:
        """Stop the maintenance task."""
        self._running = False

        if self._maintenance_task and not self._maintenance_task.done():
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass

        self._maintenance_task = None
        logger.info("Stopped queue maintenance task")

    async def _run_maintenance(self, purge_hours: int = 168) -> None:
        """
        Run maintenance tasks.

        Args:
            purge_hours: Hours after which to purge completed tasks
        """
        # Recover stuck tasks
        await self.recover_stuck()

        # Purge old completed tasks
        if self._purge_callback:
            await self._purge_callback(older_than_hours=purge_hours)

        # Clean up performance tracking
        if self._cleanup_tracking_callback:
            self._cleanup_tracking_callback()

    async def get_processing_tasks(self) -> list:
        """
        Get all tasks currently being processed.

        Returns:
            List of task info dicts
        """
        cursor = self._connection.execute(
            """
            SELECT id, task_type, started_at, worker_id
            FROM tasks
            WHERE state = 'processing'
            ORDER BY started_at ASC
            """
        )

        now = utc_now()
        result = []

        for row in cursor.fetchall():
            started = parse_iso_datetime(row["started_at"])
            age_seconds = (now - started).total_seconds() if started else 0

            result.append(
                {
                    "id": row["id"],
                    "task_type": row["task_type"],
                    "started_at": row["started_at"],
                    "worker_id": row["worker_id"],
                    "age_seconds": age_seconds,
                    "is_stuck": age_seconds > self._stuck_task_threshold,
                }
            )

        return result

    async def get_queue_depth_by_type(self) -> Dict[str, int]:
        """
        Get pending task count by type.

        Returns:
            Dictionary mapping task_type to count
        """
        cursor = self._connection.execute(
            """
            SELECT task_type, COUNT(*) as count
            FROM tasks
            WHERE state IN ('pending', 'scheduled')
            GROUP BY task_type
            ORDER BY count DESC
            """
        )

        return {row["task_type"]: row["count"] for row in cursor.fetchall()}

    def get_stats(self) -> Dict[str, Any]:
        """Get health facade statistics."""
        return {
            "maintenance_running": self._maintenance_task is not None
            and not self._maintenance_task.done(),
            "stuck_threshold_seconds": self._stuck_task_threshold,
        }
