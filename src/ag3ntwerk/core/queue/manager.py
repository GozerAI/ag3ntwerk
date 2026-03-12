"""
Task Queue Manager - Central coordinator for the Task Queue system.

Delegates to domain-focused facades for actual implementation.
Maintains backward compatibility with existing TaskQueue API.
"""

import logging
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ag3ntwerk.core.queue.models import (
    QueuedTask,
    QueueStats,
    QueueHealthStatus,
    TaskEvent,
    TaskState,
)
from ag3ntwerk.core.queue._connection import ConnectionManager
from ag3ntwerk.core.queue.facades import (
    PersistenceFacade,
    EventFacade,
    DependencyFacade,
    LifecycleFacade,
    RetryFacade,
    BatchFacade,
    HealthFacade,
)

logger = logging.getLogger(__name__)


class TaskQueueManager:
    """
    Central manager for the task queue.

    Delegates to domain facades:
    - PersistenceFacade: Row conversion and recovery
    - EventFacade: Event system
    - DependencyFacade: Task dependencies
    - LifecycleFacade: Core task operations
    - RetryFacade: Retry logic
    - BatchFacade: Batch operations
    - HealthFacade: Health monitoring

    All existing methods are maintained for backward compatibility.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        max_concurrent: int = 5,
        retry_base_delay: float = 5.0,
        retry_max_delay: float = 300.0,
        task_timeout: float = 300.0,
        stuck_task_threshold: float = 600.0,
    ):
        """
        Initialize the task queue manager.

        Args:
            db_path: Path to SQLite database (None for in-memory)
            max_concurrent: Maximum concurrent task processing
            retry_base_delay: Base delay for retries (seconds)
            retry_max_delay: Maximum retry delay (seconds)
            task_timeout: Default task timeout in seconds
            stuck_task_threshold: Seconds before a processing task is considered stuck
        """
        # Configuration
        self._db_path = db_path
        self._max_concurrent = max_concurrent
        self._retry_base_delay = retry_base_delay
        self._retry_max_delay = retry_max_delay
        self._task_timeout = task_timeout
        self._stuck_task_threshold = stuck_task_threshold

        # Shared connection
        self._connection = ConnectionManager(db_path)

        # Facades (initialized after connection)
        self._persistence: Optional[PersistenceFacade] = None
        self._event: Optional[EventFacade] = None
        self._dependency: Optional[DependencyFacade] = None
        self._lifecycle: Optional[LifecycleFacade] = None
        self._retry: Optional[RetryFacade] = None
        self._batch: Optional[BatchFacade] = None
        self._health: Optional[HealthFacade] = None

    async def initialize(self) -> None:
        """Initialize the database and facades."""
        await self._connection.initialize()

        # Initialize facades with shared connection
        self._persistence = PersistenceFacade(self._connection)
        self._event = EventFacade(self._connection)
        self._dependency = DependencyFacade(self._connection)
        self._lifecycle = LifecycleFacade(
            self._connection,
            self._persistence,
            self._event,
            max_concurrent=self._max_concurrent,
            task_timeout=self._task_timeout,
        )
        self._retry = RetryFacade(
            self._connection,
            retry_base_delay=self._retry_base_delay,
            retry_max_delay=self._retry_max_delay,
        )
        self._batch = BatchFacade(self._connection)
        self._health = HealthFacade(
            self._connection,
            stuck_task_threshold=self._stuck_task_threshold,
        )

        # Wire up retry facade for proper retry scheduling
        self._lifecycle.set_retry_facade(self._retry)

        # Set up cross-facade callbacks for health maintenance
        self._health.set_callbacks(
            recover_stuck=self._health.recover_stuck,
            purge_completed=self._retry.purge_completed,
            cleanup_tracking=self._lifecycle.cleanup_performance_tracking,
        )

        # Recover any stuck tasks on startup
        await self._persistence.recover_stuck_tasks()

        logger.info(f"Task queue initialized: {self._db_path or ':memory:'}")

    async def close(self) -> None:
        """Close the queue and database connection."""
        if self._lifecycle:
            self._lifecycle.stop()

        if self._health:
            await self._health.stop_maintenance()

        await self._connection.close()

    # ==========================================================================
    # Core Operations (delegates to LifecycleFacade)
    # ==========================================================================

    async def enqueue(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = 5,
        scheduled_at: Optional[datetime] = None,
        delay_seconds: Optional[float] = None,
        max_attempts: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
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

        Returns:
            Task ID
        """
        return await self._lifecycle.enqueue(
            task_type=task_type,
            payload=payload,
            priority=priority,
            scheduled_at=scheduled_at,
            delay_seconds=delay_seconds,
            max_attempts=max_attempts,
            metadata=metadata,
        )

    async def dequeue(self) -> Optional[QueuedTask]:
        """Get the next task to process."""
        return await self._lifecycle.dequeue()

    async def complete(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark a task as completed."""
        await self._lifecycle.complete(task_id, result)

    async def fail(
        self,
        task_id: str,
        error: str,
        move_to_dead: bool = False,
    ) -> None:
        """Mark a task as failed."""
        await self._lifecycle.fail(task_id, error, move_to_dead)

    async def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """Get a task by ID."""
        return await self._lifecycle.get_task(task_id)

    async def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        return await self._lifecycle.cancel(task_id)

    async def list_tasks(
        self,
        state: Optional[TaskState] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[QueuedTask]:
        """List tasks with optional filtering."""
        return await self._lifecycle.list_tasks(
            state=state,
            task_type=task_type,
            limit=limit,
            offset=offset,
        )

    async def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        return await self._lifecycle.get_stats()

    def register_handler(
        self,
        task_type: str,
        handler: Callable[[QueuedTask], Awaitable[Dict[str, Any]]],
    ) -> None:
        """Register a handler for a task type."""
        self._lifecycle.register_handler(task_type, handler)

    async def process_one(self) -> bool:
        """Process one task from the queue."""
        return await self._lifecycle.process_one()

    async def process_loop(
        self,
        poll_interval: float = 1.0,
    ) -> None:
        """Run the task processing loop."""
        await self._lifecycle.process_loop(poll_interval)

    def stop(self) -> None:
        """Stop the processing loop."""
        self._lifecycle.stop()

    # ==========================================================================
    # Retry Operations (delegates to RetryFacade)
    # ==========================================================================

    async def retry_dead(self, task_id: str) -> bool:
        """Retry a task from the dead letter queue."""
        return await self._retry.retry_dead(task_id)

    async def purge_completed(self, older_than_hours: int = 24) -> int:
        """Remove completed tasks older than specified hours."""
        return await self._retry.purge_completed(older_than_hours)

    # ==========================================================================
    # Batch Operations (delegates to BatchFacade)
    # ==========================================================================

    async def enqueue_batch(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[str]:
        """Enqueue multiple tasks in a single transaction."""
        return await self._batch.enqueue_batch(tasks)

    async def cancel_batch(
        self,
        task_ids: Optional[List[str]] = None,
        task_type: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> int:
        """Cancel multiple tasks."""
        return await self._batch.cancel_batch(
            task_ids=task_ids,
            task_type=task_type,
            group_id=group_id,
        )

    async def retry_batch(
        self,
        task_type: Optional[str] = None,
        max_tasks: int = 100,
    ) -> int:
        """Retry multiple dead tasks."""
        return await self._batch.retry_batch(
            task_type=task_type,
            max_tasks=max_tasks,
        )

    # ==========================================================================
    # Health & Monitoring (delegates to HealthFacade)
    # ==========================================================================

    async def get_health(self) -> QueueHealthStatus:
        """Get queue health status."""
        return await self._health.get_health()

    async def recover_stuck(self) -> int:
        """Recover tasks stuck in processing state."""
        return await self._health.recover_stuck()

    async def start_maintenance(self, interval: float = 60.0) -> None:
        """Start the maintenance task."""
        await self._health.start_maintenance(interval)

    # ==========================================================================
    # Events (delegates to EventFacade)
    # ==========================================================================

    def add_event_listener(
        self,
        listener: Callable[[TaskEvent], Awaitable[None]],
    ) -> None:
        """Add an event listener."""
        self._event.add_listener(listener)

    async def get_task_history(
        self,
        task_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get event history for a task."""
        return await self._event.get_task_history(task_id, limit)

    # ==========================================================================
    # Dependencies (delegates to DependencyFacade)
    # ==========================================================================

    async def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a dependency between tasks."""
        await self._dependency.add_dependency(task_id, depends_on)

    async def get_dependencies(self, task_id: str) -> List[str]:
        """Get task IDs that this task depends on."""
        return await self._dependency.get_dependencies(task_id)

    async def are_dependencies_met(self, task_id: str) -> bool:
        """Check if all dependencies are completed."""
        return await self._dependency.are_dependencies_met(task_id)

    # ==========================================================================
    # Task Type Management (delegates to LifecycleFacade)
    # ==========================================================================

    def pause_task_type(self, task_type: str) -> None:
        """Pause processing of a task type."""
        self._lifecycle.pause_task_type(task_type)

    def resume_task_type(self, task_type: str) -> None:
        """Resume processing of a task type."""
        self._lifecycle.resume_task_type(task_type)

    def is_type_paused(self, task_type: str) -> bool:
        """Check if a task type is paused."""
        return self._lifecycle.is_type_paused(task_type)

    # ==========================================================================
    # Direct Facade Access
    # ==========================================================================

    @property
    def persistence(self) -> PersistenceFacade:
        """Get the persistence facade."""
        return self._persistence

    @property
    def event(self) -> EventFacade:
        """Get the event facade."""
        return self._event

    @property
    def dependency(self) -> DependencyFacade:
        """Get the dependency facade."""
        return self._dependency

    @property
    def lifecycle(self) -> LifecycleFacade:
        """Get the lifecycle facade."""
        return self._lifecycle

    @property
    def retry(self) -> RetryFacade:
        """Get the retry facade."""
        return self._retry

    @property
    def batch(self) -> BatchFacade:
        """Get the batch facade."""
        return self._batch

    @property
    def health(self) -> HealthFacade:
        """Get the health facade."""
        return self._health


# Backward compatibility alias
TaskQueue = TaskQueueManager
