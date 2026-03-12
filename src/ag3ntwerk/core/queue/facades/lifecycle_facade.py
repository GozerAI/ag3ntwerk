"""
Lifecycle Facade - Core task operations (enqueue, dequeue, complete, fail).

This facade handles:
- Task enqueueing with priority
- Task dequeueing with promotion of scheduled/retry tasks
- Task completion and failure
- Task queries
- Handler registration and process loop
- Task type pause/resume
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Dict, List, Optional, Set, TYPE_CHECKING

from ag3ntwerk.core.queue.models import QueuedTask, QueueStats, TaskState
from ag3ntwerk.core.queue._connection import ConnectionManager
from ag3ntwerk.core.queue._utils import generate_id, utc_now, to_json
from ag3ntwerk.core.queue.facades.persistence_facade import PersistenceFacade
from ag3ntwerk.core.queue.facades.event_facade import EventFacade

if TYPE_CHECKING:
    from ag3ntwerk.core.queue.facades.retry_facade import RetryFacade

logger = logging.getLogger(__name__)


class LifecycleFacade:
    """
    Facade for task lifecycle operations.

    Manages task creation, processing, and completion.
    """

    def __init__(
        self,
        connection: ConnectionManager,
        persistence: PersistenceFacade,
        event: EventFacade,
        max_concurrent: int = 5,
        task_timeout: float = 300.0,
    ):
        """
        Initialize the lifecycle facade.

        Args:
            connection: Shared connection manager
            persistence: Persistence facade for row conversion
            event: Event facade for event emission
            max_concurrent: Maximum concurrent task processing
            task_timeout: Default task timeout in seconds
        """
        self._connection = connection
        self._persistence = persistence
        self._event = event
        self._max_concurrent = max_concurrent
        self._task_timeout = task_timeout

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()
        self._running = False

        # Task handlers
        self._handlers: Dict[str, Callable[[QueuedTask], Awaitable[Dict[str, object]]]] = {}

        # Paused task types
        self._paused_types: Set[str] = set()

        # Active task tracking
        self._active_tasks: Dict[str, datetime] = {}

        # Performance tracking (bounded to prevent memory leaks)
        self._completed_times: List[datetime] = []
        self._processing_times: List[float] = []
        self._wait_times: List[float] = []
        self._max_tracking_entries = 1000

        # Retry facade callback (set by manager)
        self._retry_facade: Optional["RetryFacade"] = None

    def set_retry_facade(self, retry_facade: "RetryFacade") -> None:
        """Set the retry facade for retry scheduling."""
        self._retry_facade = retry_facade

    # --- Enqueueing ---

    async def enqueue(
        self,
        task_type: str,
        payload: Dict[str, object],
        priority: int = 5,
        scheduled_at: Optional[datetime] = None,
        delay_seconds: Optional[float] = None,
        max_attempts: int = 3,
        metadata: Optional[Dict[str, object]] = None,
        timeout: Optional[float] = None,
        parent_id: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> str:
        """
        Add a task to the queue.

        Args:
            task_type: Type of task
            payload: Task payload
            priority: Priority (1=highest, 10=lowest)
            scheduled_at: When to execute (for delayed tasks)
            delay_seconds: Delay in seconds (alternative to scheduled_at)
            max_attempts: Maximum retry attempts
            metadata: Optional metadata
            timeout: Task timeout in seconds
            parent_id: Parent task ID
            group_id: Group ID for batch operations

        Returns:
            Task ID
        """
        task_id = generate_id()
        now = utc_now()

        if delay_seconds:
            scheduled_at = now + timedelta(seconds=delay_seconds)

        state = TaskState.SCHEDULED if scheduled_at else TaskState.PENDING

        self._connection.execute(
            """
            INSERT INTO tasks (
                id, task_type, payload, priority, state,
                created_at, scheduled_at, max_attempts, metadata,
                timeout, parent_id, group_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                task_type,
                to_json(payload),
                priority,
                state.value,
                now.isoformat(),
                scheduled_at.isoformat() if scheduled_at else None,
                max_attempts,
                to_json(metadata or {}),
                timeout or self._task_timeout,
                parent_id,
                group_id,
            ),
        )
        self._connection.commit()

        await self._event.emit("created", task_id, task_type, {"priority": priority})
        logger.debug(f"Enqueued task: {task_id} ({task_type})")

        return task_id

    # --- Dequeueing ---

    async def dequeue(self) -> Optional[QueuedTask]:
        """
        Get the next task to process.

        Returns highest priority pending task, or None if queue is empty.
        Also promotes scheduled tasks that are ready.

        Uses BEGIN IMMEDIATE to acquire a write lock immediately,
        preventing race conditions when multiple workers dequeue.
        """
        now = utc_now().isoformat()

        async with self._lock:
            # Use BEGIN IMMEDIATE to acquire write lock at transaction start
            # This prevents race conditions with multiple workers
            self._connection.execute("BEGIN IMMEDIATE")

            try:
                # First, promote scheduled tasks that are ready
                self._connection.execute(
                    """
                    UPDATE tasks
                    SET state = 'pending'
                    WHERE state = 'scheduled'
                    AND scheduled_at <= ?
                    """,
                    (now,),
                )

                # Also promote tasks ready for retry
                self._connection.execute(
                    """
                    UPDATE tasks
                    SET state = 'pending'
                    WHERE state = 'failed'
                    AND next_retry_at IS NOT NULL
                    AND next_retry_at <= ?
                    AND attempts < max_attempts
                    """,
                    (now,),
                )

                # Build exclusion for paused types
                query = """
                    SELECT id FROM tasks
                    WHERE state = 'pending'
                """
                params: List[object] = []

                if self._paused_types:
                    placeholders = ",".join("?" * len(self._paused_types))
                    query += f" AND task_type NOT IN ({placeholders})"
                    params.extend(self._paused_types)

                query += " ORDER BY priority ASC, created_at ASC LIMIT 1"

                cursor = self._connection.execute(query, params)
                row = cursor.fetchone()

                if not row:
                    self._connection.commit()
                    return None

                task_id = row["id"]

                # Atomically mark as processing and get full row
                # The WHERE state='pending' ensures we don't double-process
                cursor = self._connection.execute(
                    """
                    UPDATE tasks
                    SET state = 'processing', started_at = ?, attempts = attempts + 1
                    WHERE id = ? AND state = 'pending'
                    RETURNING *
                    """,
                    (now, task_id),
                )
                updated_row = cursor.fetchone()

                if not updated_row:
                    # Another worker got it first (shouldn't happen with BEGIN IMMEDIATE)
                    self._connection.commit()
                    return None

                self._connection.commit()

                # Track active task
                self._active_tasks[task_id] = utc_now()

            except Exception:  # Intentional catch-all: rollback transaction before re-raising
                self._connection.rollback()
                raise

        task = self._persistence.row_to_task(updated_row)
        await self._event.emit("started", task.id, task.task_type)

        return task

    # --- Completion ---

    async def complete(
        self,
        task_id: str,
        result: Optional[Dict[str, object]] = None,
    ) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: Task ID
            result: Optional result data

        Returns:
            True if task was completed, False if not found or not in processing state
        """
        now = utc_now()

        # Only complete tasks that are currently processing (idempotency)
        cursor = self._connection.execute(
            """
            UPDATE tasks
            SET state = 'completed', completed_at = ?, result = ?
            WHERE id = ? AND state = 'processing'
            """,
            (now.isoformat(), to_json(result) if result else None, task_id),
        )
        self._connection.commit()

        if cursor.rowcount == 0:
            logger.warning(f"Task {task_id} not in processing state, cannot complete")
            return False

        # Track performance (with bounds to prevent memory leak)
        if task_id in self._active_tasks:
            started = self._active_tasks.pop(task_id)
            processing_time = (now - started).total_seconds() * 1000
            self._processing_times.append(processing_time)
            self._completed_times.append(now)

            # Enforce bounds
            if len(self._processing_times) > self._max_tracking_entries:
                self._processing_times = self._processing_times[-self._max_tracking_entries // 2 :]
            if len(self._completed_times) > self._max_tracking_entries:
                self._completed_times = self._completed_times[-self._max_tracking_entries // 2 :]

        # Get task type for event
        row = self._persistence.get_task_row(task_id)
        task_type = row["task_type"] if row else "unknown"

        await self._event.emit(
            "completed", task_id, task_type, {"result_keys": list(result.keys()) if result else []}
        )
        logger.debug(f"Completed task: {task_id}")
        return True

    # --- Failure ---

    async def fail(
        self,
        task_id: str,
        error: str,
        move_to_dead: bool = False,
    ) -> bool:
        """
        Mark a task as failed. Schedules retry via RetryFacade if attempts remain.

        Args:
            task_id: Task ID
            error: Error message
            move_to_dead: Force move to dead letter queue

        Returns:
            True if task was failed, False if not found or not in processing state
        """
        # Get current task state (only fail tasks that are processing)
        cursor = self._connection.execute(
            "SELECT attempts, max_attempts, task_type FROM tasks WHERE id = ? AND state = 'processing'",
            (task_id,),
        )
        row = cursor.fetchone()

        if not row:
            logger.warning(f"Task {task_id} not in processing state, cannot fail")
            return False

        task_type = row["task_type"]

        # Remove from active tracking
        self._active_tasks.pop(task_id, None)

        if move_to_dead or row["attempts"] >= row["max_attempts"]:
            # Move to dead letter queue
            if self._retry_facade:
                await self._retry_facade.move_to_dead(task_id, error)
            else:
                # Fallback if no retry facade
                now = utc_now()
                self._connection.execute(
                    """
                    UPDATE tasks
                    SET state = 'dead', last_error = ?, completed_at = ?
                    WHERE id = ? AND state = 'processing'
                    """,
                    (error, now.isoformat(), task_id),
                )
                self._connection.commit()

            await self._event.emit("dead", task_id, task_type, {"error": error})
            logger.warning(f"Task moved to dead letter queue: {task_id}")
        else:
            # Schedule retry via RetryFacade
            if self._retry_facade:
                await self._retry_facade.schedule_retry(task_id, error)
            else:
                # Fallback - just mark failed without retry scheduling
                self._connection.execute(
                    """
                    UPDATE tasks
                    SET state = 'failed', last_error = ?
                    WHERE id = ? AND state = 'processing'
                    """,
                    (error, task_id),
                )
                self._connection.commit()

            await self._event.emit(
                "failed", task_id, task_type, {"error": error, "attempts": row["attempts"]}
            )

        return True

    # --- Queries ---

    async def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """Get a task by ID."""
        row = self._persistence.get_task_row(task_id)
        return self._persistence.row_to_task(row) if row else None

    async def cancel(self, task_id: str) -> bool:
        """
        Cancel a pending task.

        Returns True if cancelled, False if not found or already processing.
        """
        cursor = self._connection.execute(
            """
            UPDATE tasks
            SET state = 'dead', last_error = 'Cancelled'
            WHERE id = ? AND state IN ('pending', 'scheduled')
            """,
            (task_id,),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    async def list_tasks(
        self,
        state: Optional[TaskState] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[QueuedTask]:
        """
        List tasks with optional filtering.

        Args:
            state: Filter by state
            task_type: Filter by task type
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of tasks
        """
        query = "SELECT * FROM tasks WHERE 1=1"
        params: List[Any] = []

        if state:
            query += " AND state = ?"
            params.append(state.value)

        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)

        query += " ORDER BY priority ASC, created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self._connection.execute(query, params)
        return [self._persistence.row_to_task(row) for row in cursor.fetchall()]

    async def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        cursor = self._connection.execute(
            """
            SELECT state, COUNT(*) as count
            FROM tasks
            GROUP BY state
            """,
        )

        stats = QueueStats()
        for row in cursor.fetchall():
            state = row["state"]
            count = row["count"]

            if state == "pending":
                stats.pending = count
            elif state == "processing":
                stats.processing = count
            elif state == "completed":
                stats.completed = count
            elif state == "failed":
                stats.failed = count
            elif state == "dead":
                stats.dead = count
            elif state == "scheduled":
                stats.scheduled = count

            stats.total += count

        # Calculate performance metrics
        if self._processing_times:
            stats.avg_processing_time_ms = sum(self._processing_times) / len(self._processing_times)

        if self._wait_times:
            stats.avg_wait_time_ms = sum(self._wait_times) / len(self._wait_times)

        # Throughput
        now = utc_now()
        recent = [t for t in self._completed_times if (now - t).total_seconds() < 60]
        stats.throughput_per_minute = float(len(recent))

        return stats

    # --- Handlers ---

    def register_handler(
        self,
        task_type: str,
        handler: Callable[[QueuedTask], Awaitable[Dict[str, Any]]],
    ) -> None:
        """
        Register a handler for a task type.

        Args:
            task_type: Task type to handle
            handler: Async handler function
        """
        self._handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

    async def process_one(self) -> bool:
        """
        Process one task from the queue.

        Returns True if a task was processed, False if queue was empty.
        """
        async with self._semaphore:
            task = await self.dequeue()
            if not task:
                return False

            handler = self._handlers.get(task.task_type)
            if not handler:
                await self.fail(task.id, f"No handler for task type: {task.task_type}")
                return True

            try:
                result = await handler(task)
                await self.complete(task.id, result)
            except Exception as e:
                logger.exception(f"Task failed: {task.id}")
                await self.fail(task.id, str(e))

            return True

    async def process_loop(
        self,
        poll_interval: float = 1.0,
    ) -> None:
        """
        Run the task processing loop.

        Args:
            poll_interval: Seconds between queue polls when empty
        """
        self._running = True
        logger.info("Task queue processing started")

        while self._running:
            try:
                processed = await self.process_one()
                if not processed:
                    await asyncio.sleep(poll_interval)
            except Exception as e:
                logger.exception("Error in task processing loop")
                await asyncio.sleep(poll_interval)

        logger.info("Task queue processing stopped")

    def stop(self) -> None:
        """Stop the processing loop."""
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if processing loop is running."""
        return self._running

    # --- Task Type Management ---

    def pause_task_type(self, task_type: str) -> None:
        """Pause processing of a task type."""
        self._paused_types.add(task_type)
        logger.info(f"Paused task type: {task_type}")

    def resume_task_type(self, task_type: str) -> None:
        """Resume processing of a task type."""
        self._paused_types.discard(task_type)
        logger.info(f"Resumed task type: {task_type}")

    def is_type_paused(self, task_type: str) -> bool:
        """Check if a task type is paused."""
        return task_type in self._paused_types

    def get_paused_types(self) -> Set[str]:
        """Get all paused task types."""
        return self._paused_types.copy()

    # --- Performance Tracking ---

    def cleanup_performance_tracking(self) -> None:
        """Clean up old performance tracking data."""
        now = utc_now()
        cutoff = now - timedelta(minutes=5)

        self._completed_times = [t for t in self._completed_times if t > cutoff]
        if len(self._processing_times) > 1000:
            self._processing_times = self._processing_times[-500:]
        if len(self._wait_times) > 1000:
            self._wait_times = self._wait_times[-500:]
