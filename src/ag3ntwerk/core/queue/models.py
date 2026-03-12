"""
Queue Models - Enums and Dataclasses for the Task Queue system.

Contains all data structures used by the queue facades and manager.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# Constants
# =============================================================================


class TaskPriority:
    """Task priority levels."""

    CRITICAL = 1
    HIGH = 3
    NORMAL = 5
    LOW = 7
    BACKGROUND = 9


# =============================================================================
# Enums
# =============================================================================


class TaskState(str, Enum):
    """Task state in the queue."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"  # Moved to dead letter queue
    SCHEDULED = "scheduled"  # Delayed execution


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class QueuedTask:
    """A task in the queue."""

    id: str
    task_type: str
    payload: Dict[str, Any]
    priority: int = 5  # 1 = highest, 10 = lowest
    state: TaskState = TaskState.PENDING

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Retry handling
    attempts: int = 0
    max_attempts: int = 3
    last_error: Optional[str] = None
    next_retry_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_error": self.last_error,
            "metadata": self.metadata,
            "result": self.result,
        }


@dataclass
class QueueStats:
    """Queue statistics."""

    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    dead: int = 0
    scheduled: int = 0
    total: int = 0

    # Performance metrics
    avg_wait_time_ms: float = 0.0
    avg_processing_time_ms: float = 0.0
    throughput_per_minute: float = 0.0

    # By type breakdown
    by_type: Dict[str, int] = field(default_factory=dict)

    @property
    def active(self) -> int:
        return self.pending + self.processing + self.scheduled

    @property
    def success_rate(self) -> float:
        total_finished = self.completed + self.failed + self.dead
        if total_finished == 0:
            return 1.0
        return self.completed / total_finished


@dataclass
class TaskEvent:
    """Event emitted during task lifecycle."""

    event_type: str  # created, started, completed, failed, retrying, dead
    task_id: str
    task_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueueHealthStatus:
    """Health status of the queue."""

    healthy: bool = True
    issues: List[str] = field(default_factory=list)
    processing_backlog: int = 0
    stuck_tasks: int = 0
    dead_letter_count: int = 0
    oldest_pending_age_seconds: Optional[float] = None
