"""
Outcome Tracker - Unified task outcome collection.

Records all task outcomes across the agent hierarchy, providing the
data foundation for learning loop analysis.
"""

import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.learning.models import (
    ErrorCategory,
    HierarchyPath,
    OutcomeType,
    TaskOutcomeRecord,
)

logger = logging.getLogger(__name__)


class OutcomeTracker:
    """
    Tracks task outcomes across the entire agent hierarchy.

    This is the central data collection point for the learning system.
    All task completions should be recorded through this tracker.
    """

    def __init__(self, db: Any):
        """
        Initialize the outcome tracker.

        Args:
            db: Database connection (DatabaseManager or similar)
        """
        self._db = db
        self._outcome_buffer: List[TaskOutcomeRecord] = []
        self._flush_threshold = 50  # Flush buffer when this many outcomes accumulate
        self._last_flush = datetime.now(timezone.utc)

    async def record_outcome(
        self,
        task_id: str,
        task_type: str,
        hierarchy_path: HierarchyPath,
        success: bool,
        duration_ms: float = 0.0,
        effectiveness: Optional[float] = None,
        confidence: Optional[float] = None,
        actual_accuracy: Optional[float] = None,
        error: Optional[str] = None,
        output_summary: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        applied_pattern_ids: Optional[List[str]] = None,
        was_routing_influenced: bool = False,
        was_confidence_calibrated: bool = False,
    ) -> str:
        """
        Record a task outcome.

        Args:
            task_id: ID of the executed task
            task_type: Type of task (e.g., "code_review")
            hierarchy_path: Path through hierarchy (exec -> mgr -> spec)
            success: Whether the task succeeded
            duration_ms: Execution duration in milliseconds
            effectiveness: Optional effectiveness score (0.0-1.0)
            confidence: Initial confidence before execution
            actual_accuracy: Post-hoc accuracy assessment
            error: Error message if failed
            output_summary: Summary of output
            context: Additional context information
            applied_pattern_ids: IDs of patterns that influenced this task
            was_routing_influenced: Whether routing was influenced by patterns
            was_confidence_calibrated: Whether confidence was calibrated

        Returns:
            Outcome record ID
        """
        # Determine outcome type
        outcome_type = self._determine_outcome_type(success, error)

        # Categorize error if present
        error_category = None
        is_recoverable = True
        if error:
            error_category = self._categorize_error(error)
            is_recoverable = self._is_recoverable_error(error_category)

        # Calculate effectiveness if not provided
        if effectiveness is None:
            effectiveness = 1.0 if success else 0.0

        # Create outcome record
        record = TaskOutcomeRecord(
            task_id=task_id,
            task_type=task_type,
            agent_code=hierarchy_path.agent,
            manager_code=hierarchy_path.manager,
            specialist_code=hierarchy_path.specialist,
            outcome_type=outcome_type,
            success=success,
            effectiveness=effectiveness,
            duration_ms=duration_ms,
            initial_confidence=confidence,
            actual_accuracy=actual_accuracy,
            error_category=error_category,
            error_message=error,
            is_recoverable=is_recoverable,
            input_hash=self._hash_context(context) if context else None,
            output_summary=output_summary,
            context_snapshot=context or {},
            applied_pattern_ids=applied_pattern_ids or [],
            was_routing_influenced=was_routing_influenced,
            was_confidence_calibrated=was_confidence_calibrated,
        )

        # Buffer for batch persistence
        self._outcome_buffer.append(record)

        # Flush if buffer is full or enough time has passed
        if len(self._outcome_buffer) >= self._flush_threshold or (
            datetime.now(timezone.utc) - self._last_flush
        ) > timedelta(seconds=30):
            await self._flush_buffer()

        return record.id

    async def get_outcomes(
        self,
        agent_code: Optional[str] = None,
        agent_level: Optional[str] = None,
        task_type: Optional[str] = None,
        success_only: Optional[bool] = None,
        window_hours: int = 24,
        limit: int = 1000,
    ) -> List[TaskOutcomeRecord]:
        """
        Get outcomes matching the specified criteria.

        Args:
            agent_code: Filter by specific agent
            agent_level: Filter by level ("agent", "manager", "specialist")
            task_type: Filter by task type
            success_only: If True, only successes; if False, only failures
            window_hours: Time window in hours
            limit: Maximum number of outcomes to return

        Returns:
            List of matching outcomes
        """
        # First flush buffer to ensure recent outcomes are included
        await self._flush_buffer()

        conditions = []
        params: List[Any] = []

        # Time window
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).isoformat()
        conditions.append("created_at >= ?")
        params.append(cutoff)

        # Agent filters
        if agent_code:
            conditions.append("(agent_code = ? OR manager_code = ? OR specialist_code = ?)")
            params.extend([agent_code, agent_code, agent_code])

        if agent_level == "agent":
            # Only include outcomes where this agent was the agent
            if agent_code:
                conditions[-1] = "agent_code = ?"
                params = params[:-2]  # Remove the extra params
        elif agent_level == "manager" and agent_code:
            conditions[-1] = "manager_code = ?"
            params = params[:-2]
        elif agent_level == "specialist" and agent_code:
            conditions[-1] = "specialist_code = ?"
            params = params[:-2]

        # Task type filter
        if task_type:
            conditions.append("task_type = ?")
            params.append(task_type)

        # Success filter
        if success_only is True:
            conditions.append("success = 1")
        elif success_only is False:
            conditions.append("success = 0")

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT * FROM learning_outcomes
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)

        rows = await self._db.fetch_all(query, tuple(params))
        return [self._row_to_outcome(row) for row in rows]

    async def get_recent_outcomes(self, hours: int = 1) -> List[TaskOutcomeRecord]:
        """Get outcomes from the last N hours."""
        return await self.get_outcomes(window_hours=hours)

    async def get_agent_outcomes(
        self,
        agent_code: str,
        window_hours: int = 24,
        limit: int = 100,
    ) -> List[TaskOutcomeRecord]:
        """Get recent outcomes for a specific agent."""
        return await self.get_outcomes(
            agent_code=agent_code,
            window_hours=window_hours,
            limit=limit,
        )

    async def get_outcome_stats(
        self,
        agent_code: str,
        window_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics for an agent.

        Returns:
            Dictionary with stats like success_rate, avg_duration, etc.
        """
        outcomes = await self.get_agent_outcomes(
            agent_code=agent_code,
            window_hours=window_hours,
            limit=1000,
        )

        if not outcomes:
            return {
                "total": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "avg_effectiveness": 0.0,
            }

        total = len(outcomes)
        successes = sum(1 for o in outcomes if o.success)
        durations = [o.duration_ms for o in outcomes if o.duration_ms > 0]
        effectiveness = [o.effectiveness for o in outcomes]

        return {
            "total": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": successes / total if total > 0 else 0.0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0.0,
            "avg_effectiveness": sum(effectiveness) / len(effectiveness) if effectiveness else 0.0,
        }

    async def get_outcomes_by_hierarchy(
        self,
        window_hours: int = 24,
    ) -> Dict[str, Dict[str, List[TaskOutcomeRecord]]]:
        """
        Get outcomes grouped by hierarchy level.

        Returns:
            Dictionary with keys "agent", "manager", "specialist",
            each containing outcomes grouped by agent code.
        """
        outcomes = await self.get_outcomes(window_hours=window_hours, limit=5000)

        result: Dict[str, Dict[str, List[TaskOutcomeRecord]]] = {
            "agent": defaultdict(list),
            "manager": defaultdict(list),
            "specialist": defaultdict(list),
        }

        for outcome in outcomes:
            result["agent"][outcome.agent_code].append(outcome)
            if outcome.manager_code:
                result["manager"][outcome.manager_code].append(outcome)
            if outcome.specialist_code:
                result["specialist"][outcome.specialist_code].append(outcome)

        return result

    # Private methods

    def _determine_outcome_type(
        self,
        success: bool,
        error: Optional[str],
    ) -> OutcomeType:
        """Determine the outcome type based on success and error."""
        if success:
            return OutcomeType.SUCCESS
        if error:
            error_lower = error.lower()
            if "timeout" in error_lower:
                return OutcomeType.TIMEOUT
            if "partial" in error_lower:
                return OutcomeType.PARTIAL
        return OutcomeType.FAILURE

    def _categorize_error(self, error: str) -> ErrorCategory:
        """
        Categorize error for pattern analysis.

        Args:
            error: Error message

        Returns:
            Error category
        """
        error_lower = error.lower()

        # Check for timeout
        if any(kw in error_lower for kw in ["timeout", "timed out", "deadline"]):
            return ErrorCategory.TIMEOUT

        # Check for capability issues
        if any(
            kw in error_lower
            for kw in [
                "cannot handle",
                "not supported",
                "capability",
                "unknown task",
                "unsupported",
            ]
        ):
            return ErrorCategory.CAPABILITY

        # Check for resource issues
        if any(
            kw in error_lower
            for kw in [
                "memory",
                "resource",
                "cpu",
                "disk",
                "quota",
                "limit exceeded",
                "out of memory",
            ]
        ):
            return ErrorCategory.RESOURCE

        # Check for external service issues
        if any(
            kw in error_lower
            for kw in [
                "llm",
                "provider",
                "api",
                "connection",
                "network",
                "service unavailable",
                "503",
                "502",
                "429",
            ]
        ):
            return ErrorCategory.EXTERNAL

        # Default to logic error
        return ErrorCategory.LOGIC

    def _is_recoverable_error(self, category: ErrorCategory) -> bool:
        """Determine if an error category is recoverable."""
        recoverable = {
            ErrorCategory.TIMEOUT,
            ErrorCategory.EXTERNAL,
            ErrorCategory.RESOURCE,
        }
        return category in recoverable

    def _hash_context(self, context: Dict[str, Any]) -> str:
        """Create a hash of the context for pattern matching."""
        # Serialize and hash
        context_str = json.dumps(context, sort_keys=True, default=str)
        return hashlib.sha256(context_str.encode()).hexdigest()[:16]

    async def _flush_buffer(self) -> None:
        """Flush buffered outcomes to the database."""
        if not self._outcome_buffer:
            return

        # Batch insert
        for outcome in self._outcome_buffer:
            await self._persist_outcome(outcome)

        count = len(self._outcome_buffer)
        self._outcome_buffer.clear()
        self._last_flush = datetime.now(timezone.utc)

        logger.debug(f"Flushed {count} outcomes to database")

    async def _persist_outcome(self, outcome: TaskOutcomeRecord) -> None:
        """Persist a single outcome to the database."""
        await self._db.execute(
            """
            INSERT INTO learning_outcomes (
                id, task_id, task_type,
                agent_code, manager_code, specialist_code,
                outcome_type, success, effectiveness, duration_ms,
                initial_confidence, actual_accuracy,
                error_category, error_message, is_recoverable,
                input_hash, output_summary, context_snapshot,
                applied_pattern_ids, was_routing_influenced, was_confidence_calibrated,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                outcome.id,
                outcome.task_id,
                outcome.task_type,
                outcome.agent_code,
                outcome.manager_code,
                outcome.specialist_code,
                outcome.outcome_type.value,
                1 if outcome.success else 0,
                outcome.effectiveness,
                outcome.duration_ms,
                outcome.initial_confidence,
                outcome.actual_accuracy,
                outcome.error_category.value if outcome.error_category else None,
                outcome.error_message,
                1 if outcome.is_recoverable else 0,
                outcome.input_hash,
                outcome.output_summary,
                json.dumps(outcome.context_snapshot),
                json.dumps(outcome.applied_pattern_ids),
                1 if outcome.was_routing_influenced else 0,
                1 if outcome.was_confidence_calibrated else 0,
                outcome.created_at.isoformat(),
            ),
        )

    def _row_to_outcome(self, row: Dict[str, Any]) -> TaskOutcomeRecord:
        """Convert a database row to a TaskOutcomeRecord."""
        context_snapshot = {}
        if row.get("context_snapshot"):
            try:
                context_snapshot = json.loads(row["context_snapshot"])
            except (json.JSONDecodeError, TypeError):
                pass

        applied_pattern_ids = []
        if row.get("applied_pattern_ids"):
            try:
                applied_pattern_ids = json.loads(row["applied_pattern_ids"])
            except (json.JSONDecodeError, TypeError):
                pass

        return TaskOutcomeRecord(
            id=row["id"],
            task_id=row["task_id"],
            task_type=row["task_type"],
            agent_code=row["agent_code"],
            manager_code=row["manager_code"],
            specialist_code=row["specialist_code"],
            outcome_type=OutcomeType(row["outcome_type"]),
            success=bool(row["success"]),
            effectiveness=row["effectiveness"] or 0.0,
            duration_ms=row["duration_ms"] or 0.0,
            initial_confidence=row["initial_confidence"],
            actual_accuracy=row["actual_accuracy"],
            error_category=ErrorCategory(row["error_category"]) if row["error_category"] else None,
            error_message=row["error_message"],
            is_recoverable=bool(row["is_recoverable"]),
            input_hash=row["input_hash"],
            output_summary=row["output_summary"],
            context_snapshot=context_snapshot,
            applied_pattern_ids=applied_pattern_ids,
            was_routing_influenced=bool(row.get("was_routing_influenced", 0)),
            was_confidence_calibrated=bool(row.get("was_confidence_calibrated", 0)),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
