"""
Task Queue with Persistence for ag3ntwerk.

Provides a durable task queue with:
- SQLite persistence for reliability
- Priority-based scheduling
- Retry logic with exponential backoff
- Dead letter queue for failed tasks
- Scheduled/delayed tasks

Usage:
    from ag3ntwerk.core.queue import (
        TaskQueue,
        QueuedTask,
        get_task_queue,
        enqueue_task,
    )

    # Enqueue a task
    task_id = await enqueue_task(
        task_type="code_review",
        payload={"pr_url": "..."},
        priority=5,
    )

    # Process tasks
    queue = get_task_queue()
    await queue.process_loop(handler=my_handler)
"""

from typing import Any, Dict, Optional
from datetime import datetime

# Models
from ag3ntwerk.core.queue.models import (
    TaskPriority,
    TaskState,
    QueuedTask,
    QueueStats,
    TaskEvent,
    QueueHealthStatus,
)

# Manager (with backward-compatible alias)
from ag3ntwerk.core.queue.manager import TaskQueueManager, TaskQueue

# Facades (for direct access)
from ag3ntwerk.core.queue.facades import (
    PersistenceFacade,
    EventFacade,
    DependencyFacade,
    LifecycleFacade,
    RetryFacade,
    BatchFacade,
    HealthFacade,
)


# Global task queue instance
_queue: Optional[TaskQueue] = None


async def get_task_queue(db_path: Optional[str] = None) -> TaskQueue:
    """
    Get the global task queue.

    Args:
        db_path: Database path (only used on first call)

    Returns:
        TaskQueue instance
    """
    global _queue
    if _queue is None:
        _queue = TaskQueue(db_path=db_path)
        await _queue.initialize()
    return _queue


async def enqueue_task(
    task_type: str,
    payload: Dict[str, Any],
    priority: int = 5,
    scheduled_at: Optional[datetime] = None,
    delay_seconds: Optional[float] = None,
    max_attempts: int = 3,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Enqueue a task in the global queue.

    Returns task ID.
    """
    queue = await get_task_queue()
    return await queue.enqueue(
        task_type=task_type,
        payload=payload,
        priority=priority,
        scheduled_at=scheduled_at,
        delay_seconds=delay_seconds,
        max_attempts=max_attempts,
        metadata=metadata,
    )


async def shutdown_queue() -> None:
    """Shutdown the global task queue."""
    global _queue
    if _queue:
        await _queue.close()
        _queue = None


__all__ = [
    # Enums/Constants
    "TaskState",
    "TaskPriority",
    # Data classes
    "QueuedTask",
    "QueueStats",
    "TaskEvent",
    "QueueHealthStatus",
    # Queue
    "TaskQueue",
    "TaskQueueManager",
    "get_task_queue",
    # Functions
    "enqueue_task",
    "shutdown_queue",
    # Facades
    "PersistenceFacade",
    "EventFacade",
    "DependencyFacade",
    "LifecycleFacade",
    "RetryFacade",
    "BatchFacade",
    "HealthFacade",
]
