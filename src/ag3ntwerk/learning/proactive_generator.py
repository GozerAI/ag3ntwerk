"""
Proactive Task Generator - Generates maintenance and improvement tasks automatically.

Takes initiative to create tasks for:
1. Confidence calibration checks
2. Performance investigations
3. Pattern analysis runs
4. Handler generation
5. System health checks
6. Error pattern analysis
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum
from uuid import uuid4

if TYPE_CHECKING:
    from ag3ntwerk.learning.opportunity_detector import Opportunity, OpportunityType

logger = logging.getLogger(__name__)


class ProactiveTaskType(Enum):
    """Types of proactive tasks the system can generate."""

    CALIBRATION_CHECK = "calibration_check"  # Re-calibrate agent confidence
    PERFORMANCE_INVESTIGATION = "performance_investigation"  # Investigate declining performance
    PATTERN_ANALYSIS = "pattern_analysis"  # Run pattern detection
    HANDLER_GENERATION = "handler_generation"  # Generate a handler
    HEALTH_CHECK = "health_check"  # System health verification
    ERROR_ANALYSIS = "error_analysis"  # Analyze error patterns
    LOAD_REBALANCING = "load_rebalancing"  # Redistribute load
    EXPERIMENT_REVIEW = "experiment_review"  # Review experiment results


class TaskPriority(Enum):
    """Priority levels for generated tasks."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class ProactiveTask:
    """A task generated proactively by the system."""

    id: str = field(default_factory=lambda: str(uuid4()))
    task_type: ProactiveTaskType = ProactiveTaskType.HEALTH_CHECK
    priority: TaskPriority = TaskPriority.MEDIUM

    # Task details
    title: str = ""
    description: str = ""
    target_agent: Optional[str] = None
    target_task_type: Optional[str] = None

    # Execution context
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_duration_ms: float = 0.0

    # Source
    source_opportunity_id: Optional[str] = None
    reason: str = ""

    # Status
    status: str = "pending"  # pending, queued, executing, completed, failed
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    queued_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "target_agent": self.target_agent,
            "target_task_type": self.target_task_type,
            "parameters": self.parameters,
            "expected_duration_ms": self.expected_duration_ms,
            "source_opportunity_id": self.source_opportunity_id,
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "queued_at": self.queued_at.isoformat() if self.queued_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
        }


class ProactiveTaskGenerator:
    """
    Generates maintenance and improvement tasks automatically.

    Works with OpportunityDetector to convert opportunities into actionable tasks,
    and independently generates routine maintenance tasks.
    """

    # Maximum tasks to generate per category
    MAX_CALIBRATION_TASKS = 5
    MAX_INVESTIGATION_TASKS = 3
    MAX_HANDLER_TASKS = 3
    MAX_PATTERN_TASKS = 5

    # Cooldown periods (hours) before regenerating similar tasks
    CALIBRATION_COOLDOWN_HOURS = 24
    INVESTIGATION_COOLDOWN_HOURS = 12
    HANDLER_COOLDOWN_HOURS = 48

    def __init__(
        self,
        db: Any,
        task_queue: Optional[Any] = None,
        opportunity_detector: Optional[Any] = None,
    ):
        """
        Initialize the proactive task generator.

        Args:
            db: Database connection
            task_queue: Optional task queue for enqueuing tasks
            opportunity_detector: Optional opportunity detector for conversion
        """
        self._db = db
        self._task_queue = task_queue
        self._opportunity_detector = opportunity_detector

        # Generated tasks
        self._tasks: Dict[str, ProactiveTask] = {}

        # Cooldown tracking
        self._last_generated: Dict[str, datetime] = {}

    async def generate_all_tasks(
        self,
        window_hours: int = 24,
    ) -> List[ProactiveTask]:
        """
        Generate all types of proactive tasks.

        Args:
            window_hours: Time window for analysis

        Returns:
            List of generated tasks
        """
        tasks = []

        # Generate various task types
        tasks.extend(await self.generate_calibration_tasks(window_hours))
        tasks.extend(await self.generate_investigation_tasks(window_hours))
        tasks.extend(await self.generate_pattern_analysis_tasks(window_hours))
        tasks.extend(await self.generate_handler_tasks(window_hours))
        tasks.extend(await self.generate_health_check_tasks())

        # Convert opportunities to tasks if detector is available
        if self._opportunity_detector:
            tasks.extend(await self.convert_opportunities_to_tasks())

        # Store tasks
        for task in tasks:
            self._tasks[task.id] = task

        # Sort by priority
        tasks.sort(key=lambda t: t.priority.value)

        logger.info(f"Generated {len(tasks)} proactive tasks")

        return tasks

    async def generate_calibration_tasks(
        self,
        window_hours: int = 24,
    ) -> List[ProactiveTask]:
        """Generate calibration check tasks for agents with poor calibration."""
        tasks = []
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # Check cooldown
        if self._is_on_cooldown("calibration"):
            return tasks

        try:
            # Find agents with calibration issues
            rows = await self._db.fetch_all(
                """
                SELECT
                    agent_code as agent_code,
                    COUNT(*) as task_count,
                    AVG(initial_confidence) as avg_confidence,
                    AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as actual_rate,
                    ABS(AVG(initial_confidence) - AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END)) as calibration_error
                FROM learning_outcomes
                WHERE created_at >= ? AND initial_confidence IS NOT NULL
                GROUP BY agent_code
                HAVING task_count >= 10 AND calibration_error > 0.15
                ORDER BY calibration_error DESC
                LIMIT ?
                """,
                (window_start.isoformat(), self.MAX_CALIBRATION_TASKS),
            )

            for row in rows:
                agent_code = row["agent_code"]
                calibration_error = row["calibration_error"]

                task = ProactiveTask(
                    task_type=ProactiveTaskType.CALIBRATION_CHECK,
                    priority=TaskPriority.MEDIUM if calibration_error < 0.25 else TaskPriority.HIGH,
                    title=f"Calibration check for {agent_code}",
                    description=(
                        f"Agent {agent_code} shows {calibration_error:.1%} calibration error. "
                        f"Running confidence recalibration."
                    ),
                    target_agent=agent_code,
                    parameters={
                        "calibration_error": calibration_error,
                        "avg_confidence": row["avg_confidence"],
                        "actual_rate": row["actual_rate"],
                        "sample_size": row["task_count"],
                    },
                    expected_duration_ms=5000.0,
                    reason=f"Calibration error of {calibration_error:.1%} exceeds threshold",
                )

                tasks.append(task)

            if tasks:
                self._last_generated["calibration"] = datetime.now(timezone.utc)

        except Exception as e:
            logger.warning(f"Failed to generate calibration tasks: {e}")

        return tasks

    async def generate_investigation_tasks(
        self,
        window_hours: int = 24,
    ) -> List[ProactiveTask]:
        """Generate performance investigation tasks for declining agents."""
        tasks = []
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        recent_start = datetime.now(timezone.utc) - timedelta(hours=window_hours // 2)

        # Check cooldown
        if self._is_on_cooldown("investigation"):
            return tasks

        try:
            # Find agents with declining performance
            rows = await self._db.fetch_all(
                """
                SELECT
                    agent_code as agent_code,
                    COUNT(CASE WHEN created_at < ? THEN 1 END) as old_tasks,
                    SUM(CASE WHEN created_at < ? AND success = 1 THEN 1 ELSE 0 END) as old_successes,
                    COUNT(CASE WHEN created_at >= ? THEN 1 END) as recent_tasks,
                    SUM(CASE WHEN created_at >= ? AND success = 1 THEN 1 ELSE 0 END) as recent_successes
                FROM learning_outcomes
                WHERE created_at >= ?
                GROUP BY agent_code
                HAVING old_tasks >= 10 AND recent_tasks >= 5
                """,
                (
                    recent_start.isoformat(),
                    recent_start.isoformat(),
                    recent_start.isoformat(),
                    recent_start.isoformat(),
                    window_start.isoformat(),
                ),
            )

            for row in rows:
                agent_code = row["agent_code"]
                old_rate = row["old_successes"] / row["old_tasks"] if row["old_tasks"] > 0 else 0
                recent_rate = (
                    row["recent_successes"] / row["recent_tasks"] if row["recent_tasks"] > 0 else 0
                )
                decline = old_rate - recent_rate

                if decline > 0.1:  # More than 10% decline
                    task = ProactiveTask(
                        task_type=ProactiveTaskType.PERFORMANCE_INVESTIGATION,
                        priority=TaskPriority.HIGH if decline > 0.2 else TaskPriority.MEDIUM,
                        title=f"Investigate {agent_code} performance decline",
                        description=(
                            f"Agent {agent_code} shows {decline:.1%} performance decline. "
                            f"Old rate: {old_rate:.1%}, Recent rate: {recent_rate:.1%}."
                        ),
                        target_agent=agent_code,
                        parameters={
                            "old_success_rate": old_rate,
                            "recent_success_rate": recent_rate,
                            "decline": decline,
                            "old_tasks": row["old_tasks"],
                            "recent_tasks": row["recent_tasks"],
                        },
                        expected_duration_ms=10000.0,
                        reason=f"Performance declined by {decline:.1%}",
                    )

                    tasks.append(task)

                    if len(tasks) >= self.MAX_INVESTIGATION_TASKS:
                        break

            if tasks:
                self._last_generated["investigation"] = datetime.now(timezone.utc)

        except Exception as e:
            logger.warning(f"Failed to generate investigation tasks: {e}")

        return tasks

    async def generate_pattern_analysis_tasks(
        self,
        window_hours: int = 24,
    ) -> List[ProactiveTask]:
        """Generate pattern analysis tasks for task types lacking patterns."""
        tasks = []
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        try:
            # Find task types with significant volume but potentially missing patterns
            rows = await self._db.fetch_all(
                """
                SELECT
                    task_type,
                    COUNT(*) as task_count,
                    AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
                FROM learning_outcomes
                WHERE created_at >= ?
                GROUP BY task_type
                HAVING task_count >= 20 AND success_rate < 0.9
                ORDER BY task_count DESC
                LIMIT ?
                """,
                (window_start.isoformat(), self.MAX_PATTERN_TASKS),
            )

            for row in rows:
                task_type = row["task_type"]
                success_rate = row["success_rate"]

                task = ProactiveTask(
                    task_type=ProactiveTaskType.PATTERN_ANALYSIS,
                    priority=TaskPriority.LOW,
                    title=f"Analyze patterns for {task_type}",
                    description=(
                        f"Run pattern analysis for {task_type} "
                        f"({row['task_count']} tasks, {success_rate:.1%} success rate)."
                    ),
                    target_task_type=task_type,
                    parameters={
                        "task_count": row["task_count"],
                        "success_rate": success_rate,
                    },
                    expected_duration_ms=15000.0,
                    reason=f"High volume task type with {1-success_rate:.1%} failure rate",
                )

                tasks.append(task)

        except Exception as e:
            logger.warning(f"Failed to generate pattern analysis tasks: {e}")

        return tasks

    async def generate_handler_tasks(
        self,
        window_hours: int = 168,  # 1 week
    ) -> List[ProactiveTask]:
        """Generate handler creation tasks for eligible task types."""
        tasks = []
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # Check cooldown
        if self._is_on_cooldown("handler"):
            return tasks

        try:
            # Find task types suitable for handler generation
            rows = await self._db.fetch_all(
                """
                SELECT
                    task_type,
                    COUNT(*) as task_count,
                    AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
                FROM learning_outcomes
                WHERE created_at >= ?
                GROUP BY task_type
                HAVING task_count >= 30 AND success_rate >= 0.75
                ORDER BY task_count DESC
                LIMIT ?
                """,
                (window_start.isoformat(), self.MAX_HANDLER_TASKS),
            )

            for row in rows:
                task_type = row["task_type"]
                success_rate = row["success_rate"]

                task = ProactiveTask(
                    task_type=ProactiveTaskType.HANDLER_GENERATION,
                    priority=TaskPriority.BACKGROUND,
                    title=f"Generate handler for {task_type}",
                    description=(
                        f"Task type {task_type} has {row['task_count']} executions "
                        f"with {success_rate:.1%} success rate. Candidate for handler generation."
                    ),
                    target_task_type=task_type,
                    parameters={
                        "task_count": row["task_count"],
                        "success_rate": success_rate,
                    },
                    expected_duration_ms=30000.0,
                    reason=f"High-volume task type with good success rate",
                )

                tasks.append(task)

            if tasks:
                self._last_generated["handler"] = datetime.now(timezone.utc)

        except Exception as e:
            logger.warning(f"Failed to generate handler tasks: {e}")

        return tasks

    async def generate_health_check_tasks(self) -> List[ProactiveTask]:
        """Generate routine health check tasks."""
        tasks = []

        # System health check (always generate if not recently done)
        if not self._is_on_cooldown("health_check", cooldown_hours=6):
            task = ProactiveTask(
                task_type=ProactiveTaskType.HEALTH_CHECK,
                priority=TaskPriority.BACKGROUND,
                title="System health check",
                description="Routine health verification of the learning system.",
                parameters={
                    "check_patterns": True,
                    "check_experiments": True,
                    "check_handlers": True,
                    "check_calibration": True,
                },
                expected_duration_ms=5000.0,
                reason="Routine maintenance",
            )

            tasks.append(task)
            self._last_generated["health_check"] = datetime.now(timezone.utc)

        return tasks

    async def convert_opportunities_to_tasks(self) -> List[ProactiveTask]:
        """Convert actionable opportunities into tasks."""
        tasks = []

        if not self._opportunity_detector:
            return tasks

        try:
            opportunities = await self._opportunity_detector.get_actionable_opportunities()

            for opp in opportunities[:10]:  # Limit to 10 conversions
                task = self._opportunity_to_task(opp)
                if task:
                    tasks.append(task)
                    # Mark opportunity as acknowledged
                    await self._opportunity_detector.acknowledge_opportunity(opp.id)

        except Exception as e:
            logger.warning(f"Failed to convert opportunities to tasks: {e}")

        return tasks

    def _opportunity_to_task(self, opportunity: "Opportunity") -> Optional[ProactiveTask]:
        """Convert a single opportunity to a task."""
        from ag3ntwerk.learning.opportunity_detector import OpportunityType, OpportunityPriority

        # Map opportunity type to task type
        type_mapping = {
            OpportunityType.CAPABILITY_GAP: ProactiveTaskType.PERFORMANCE_INVESTIGATION,
            OpportunityType.WORKFLOW_OPTIMIZATION: ProactiveTaskType.PATTERN_ANALYSIS,
            OpportunityType.PATTERN_COVERAGE: ProactiveTaskType.PATTERN_ANALYSIS,
            OpportunityType.RESOURCE_REBALANCING: ProactiveTaskType.LOAD_REBALANCING,
            OpportunityType.TRAINING_NEED: ProactiveTaskType.CALIBRATION_CHECK,
            OpportunityType.ERROR_PREVENTION: ProactiveTaskType.ERROR_ANALYSIS,
            OpportunityType.HANDLER_OPPORTUNITY: ProactiveTaskType.HANDLER_GENERATION,
        }

        # Map opportunity priority to task priority
        priority_mapping = {
            OpportunityPriority.CRITICAL: TaskPriority.CRITICAL,
            OpportunityPriority.HIGH: TaskPriority.HIGH,
            OpportunityPriority.MEDIUM: TaskPriority.MEDIUM,
            OpportunityPriority.LOW: TaskPriority.LOW,
        }

        task_type = type_mapping.get(opportunity.opportunity_type)
        if not task_type:
            return None

        return ProactiveTask(
            task_type=task_type,
            priority=priority_mapping.get(opportunity.priority, TaskPriority.MEDIUM),
            title=f"[Auto] {opportunity.title}",
            description=opportunity.description,
            target_agent=opportunity.affected_agent,
            target_task_type=opportunity.affected_task_type,
            parameters=opportunity.evidence,
            source_opportunity_id=opportunity.id,
            reason=opportunity.suggested_action,
        )

    def _is_on_cooldown(
        self,
        category: str,
        cooldown_hours: Optional[int] = None,
    ) -> bool:
        """Check if a category is on cooldown."""
        if category not in self._last_generated:
            return False

        cooldown = cooldown_hours
        if cooldown is None:
            cooldown_map = {
                "calibration": self.CALIBRATION_COOLDOWN_HOURS,
                "investigation": self.INVESTIGATION_COOLDOWN_HOURS,
                "handler": self.HANDLER_COOLDOWN_HOURS,
                "health_check": 6,
            }
            cooldown = cooldown_map.get(category, 24)

        last_time = self._last_generated[category]
        return datetime.now(timezone.utc) - last_time < timedelta(hours=cooldown)

    async def enqueue_task(self, task: ProactiveTask) -> bool:
        """
        Enqueue a task to the task queue.

        Args:
            task: Task to enqueue

        Returns:
            True if enqueued successfully
        """
        if not self._task_queue:
            logger.warning("No task queue available for enqueuing")
            return False

        try:
            # Convert to task queue format
            await self._task_queue.enqueue(
                task_type=task.task_type.value,
                payload={
                    "proactive_task_id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "target_agent": task.target_agent,
                    "target_task_type": task.target_task_type,
                    **task.parameters,
                },
                priority=task.priority.value,
            )

            task.status = "queued"
            task.queued_at = datetime.now(timezone.utc)

            logger.info(f"Enqueued proactive task: {task.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to enqueue task: {e}")
            return False

    async def enqueue_all_pending(self) -> int:
        """
        Enqueue all pending tasks.

        Returns:
            Number of tasks enqueued
        """
        count = 0
        pending = [t for t in self._tasks.values() if t.status == "pending"]

        for task in pending:
            if await self.enqueue_task(task):
                count += 1

        return count

    async def get_task(self, task_id: str) -> Optional[ProactiveTask]:
        """Get a specific task by ID."""
        return self._tasks.get(task_id)

    async def get_tasks_by_type(
        self,
        task_type: ProactiveTaskType,
    ) -> List[ProactiveTask]:
        """Get tasks of a specific type."""
        return [t for t in self._tasks.values() if t.task_type == task_type]

    async def get_pending_tasks(self) -> List[ProactiveTask]:
        """Get all pending tasks."""
        return [t for t in self._tasks.values() if t.status == "pending"]

    async def complete_task(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Mark a task as completed."""
        task = self._tasks.get(task_id)
        if task:
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.result = result
            return True
        return False

    async def fail_task(
        self,
        task_id: str,
        error: str = "",
    ) -> bool:
        """Mark a task as failed."""
        task = self._tasks.get(task_id)
        if task:
            task.status = "failed"
            task.completed_at = datetime.now(timezone.utc)
            task.result = {"error": error}
            return True
        return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get task generation statistics."""
        by_type = {}
        by_status = {}
        by_priority = {}

        for task in self._tasks.values():
            type_key = task.task_type.value
            status_key = task.status
            priority_key = task.priority.value

            by_type[type_key] = by_type.get(type_key, 0) + 1
            by_status[status_key] = by_status.get(status_key, 0) + 1
            by_priority[priority_key] = by_priority.get(priority_key, 0) + 1

        return {
            "total_tasks": len(self._tasks),
            "pending_tasks": len([t for t in self._tasks.values() if t.status == "pending"]),
            "completed_tasks": len([t for t in self._tasks.values() if t.status == "completed"]),
            "failed_tasks": len([t for t in self._tasks.values() if t.status == "failed"]),
            "by_type": by_type,
            "by_status": by_status,
            "by_priority": by_priority,
            "last_generated": {k: v.isoformat() for k, v in self._last_generated.items()},
        }

    async def clear_completed_tasks(self) -> int:
        """Clear completed tasks from memory."""
        to_remove = [
            task_id
            for task_id, task in self._tasks.items()
            if task.status in ("completed", "failed")
        ]

        for task_id in to_remove:
            del self._tasks[task_id]

        return len(to_remove)
