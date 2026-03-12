"""
Pattern Application Tracker - Measures the effectiveness of applied patterns.

Tracks pattern applications and their outcomes to:
1. Measure whether patterns are actually helping
2. Update pattern confidence based on outcome
3. Identify declining patterns that should be deactivated
4. Generate A/B-style comparison metrics
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class PatternApplication:
    """
    Record of a pattern being applied to a task.

    Tracks both the application and its outcome.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    pattern_id: str = ""
    task_id: str = ""
    task_type: str = ""
    agent_code: str = ""

    # Application details
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    was_routing_pattern: bool = False
    was_confidence_pattern: bool = False

    # Outcome (filled in after task completes)
    outcome_recorded: bool = False
    outcome_success: bool = False
    outcome_duration_ms: float = 0.0
    outcome_effectiveness: float = 0.0

    # Comparison baseline (what would have happened without pattern)
    baseline_agent: Optional[str] = None  # Static route that would have been used
    baseline_success_rate: Optional[float] = None  # Historical success rate for baseline

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pattern_id": self.pattern_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "agent_code": self.agent_code,
            "applied_at": self.applied_at.isoformat(),
            "was_routing_pattern": self.was_routing_pattern,
            "was_confidence_pattern": self.was_confidence_pattern,
            "outcome_recorded": self.outcome_recorded,
            "outcome_success": self.outcome_success,
            "outcome_duration_ms": self.outcome_duration_ms,
            "outcome_effectiveness": self.outcome_effectiveness,
            "baseline_agent": self.baseline_agent,
            "baseline_success_rate": self.baseline_success_rate,
        }


@dataclass
class PatternEffectiveness:
    """
    Effectiveness metrics for a pattern over a time window.
    """

    pattern_id: str
    window_start: datetime
    window_end: datetime

    # Application counts
    total_applications: int = 0
    successful_applications: int = 0
    failed_applications: int = 0

    # Success metrics
    success_rate: float = 0.0
    avg_effectiveness: float = 0.0
    avg_duration_ms: float = 0.0

    # Comparison to baseline
    baseline_success_rate: Optional[float] = None
    improvement_over_baseline: Optional[float] = None  # Positive = better than baseline

    # Trend
    is_improving: bool = False
    is_declining: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "total_applications": self.total_applications,
            "successful_applications": self.successful_applications,
            "success_rate": self.success_rate,
            "avg_effectiveness": self.avg_effectiveness,
            "improvement_over_baseline": self.improvement_over_baseline,
            "is_declining": self.is_declining,
        }


class PatternTracker:
    """
    Tracks pattern applications and measures their effectiveness.

    This enables the learning system to:
    - Know if patterns are actually helping
    - Adjust pattern confidence based on outcomes
    - Identify patterns that should be deactivated
    """

    # Minimum applications before calculating effectiveness
    MIN_APPLICATIONS_FOR_STATS = 5

    # Threshold for considering a pattern declining
    DECLINE_THRESHOLD = 0.15  # 15% worse than baseline

    # How long to keep application records
    RETENTION_HOURS = 168  # 1 week

    def __init__(self, db: Any):
        """
        Initialize the pattern tracker.

        Args:
            db: Database connection
        """
        self._db = db

        # In-memory cache of recent applications (for quick lookup)
        self._pending_applications: Dict[str, PatternApplication] = {}

    async def record_application(
        self,
        pattern_id: str,
        task_id: str,
        task_type: str,
        agent_code: str,
        was_routing_pattern: bool = False,
        was_confidence_pattern: bool = False,
        baseline_agent: Optional[str] = None,
        baseline_success_rate: Optional[float] = None,
    ) -> str:
        """
        Record that a pattern was applied to a task.

        Call this before task execution.

        Args:
            pattern_id: ID of the applied pattern
            task_id: ID of the task
            task_type: Type of task
            agent_code: Agent handling the task
            was_routing_pattern: Whether this was a routing pattern
            was_confidence_pattern: Whether this was a confidence pattern
            baseline_agent: What agent would have been used without pattern
            baseline_success_rate: Historical success rate for baseline

        Returns:
            Application record ID
        """
        application = PatternApplication(
            pattern_id=pattern_id,
            task_id=task_id,
            task_type=task_type,
            agent_code=agent_code,
            was_routing_pattern=was_routing_pattern,
            was_confidence_pattern=was_confidence_pattern,
            baseline_agent=baseline_agent,
            baseline_success_rate=baseline_success_rate,
        )

        # Store in pending cache
        self._pending_applications[task_id] = application

        # Persist to database
        await self._insert_application(application)

        logger.debug(f"Recorded pattern application: {pattern_id} -> {task_id}")
        return application.id

    async def record_outcome(
        self,
        task_id: str,
        success: bool,
        duration_ms: float = 0.0,
        effectiveness: float = 0.0,
    ) -> None:
        """
        Record the outcome of a task where a pattern was applied.

        Call this after task execution.

        Args:
            task_id: ID of the task
            success: Whether the task succeeded
            duration_ms: Execution duration
            effectiveness: Effectiveness score (0-1)
        """
        # Get from cache or database
        application = self._pending_applications.pop(task_id, None)
        if not application:
            # Try to find in database
            application = await self._get_application_by_task(task_id)

        if not application:
            return  # No pattern was applied to this task

        # Update with outcome
        application.outcome_recorded = True
        application.outcome_success = success
        application.outcome_duration_ms = duration_ms
        application.outcome_effectiveness = effectiveness

        # Persist outcome
        await self._update_application_outcome(application)

        # Update pattern statistics
        await self._update_pattern_stats(application)

        logger.debug(
            f"Recorded outcome for pattern {application.pattern_id}: "
            f"success={success}, effectiveness={effectiveness:.2f}"
        )

    async def get_pattern_effectiveness(
        self,
        pattern_id: str,
        window_hours: int = 24,
    ) -> Optional[PatternEffectiveness]:
        """
        Calculate effectiveness metrics for a pattern.

        Args:
            pattern_id: Pattern ID
            window_hours: Time window for analysis

        Returns:
            Effectiveness metrics or None if not enough data
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=window_hours)

        # Get applications in window
        applications = await self._get_applications_for_pattern(pattern_id, window_start)

        if len(applications) < self.MIN_APPLICATIONS_FOR_STATS:
            return None

        # Calculate metrics
        total = len(applications)
        successful = sum(1 for a in applications if a.outcome_success)
        failed = total - successful

        success_rate = successful / total if total > 0 else 0.0
        avg_effectiveness = (
            sum(a.outcome_effectiveness for a in applications) / total if total > 0 else 0.0
        )
        avg_duration = (
            sum(a.outcome_duration_ms for a in applications) / total if total > 0 else 0.0
        )

        # Calculate baseline comparison
        baseline_rates = [
            a.baseline_success_rate for a in applications if a.baseline_success_rate is not None
        ]
        baseline_success_rate = (
            sum(baseline_rates) / len(baseline_rates) if baseline_rates else None
        )
        improvement = (
            success_rate - baseline_success_rate if baseline_success_rate is not None else None
        )

        # Determine trend
        is_declining = improvement is not None and improvement < -self.DECLINE_THRESHOLD
        is_improving = improvement is not None and improvement > self.DECLINE_THRESHOLD

        return PatternEffectiveness(
            pattern_id=pattern_id,
            window_start=window_start,
            window_end=now,
            total_applications=total,
            successful_applications=successful,
            failed_applications=failed,
            success_rate=success_rate,
            avg_effectiveness=avg_effectiveness,
            avg_duration_ms=avg_duration,
            baseline_success_rate=baseline_success_rate,
            improvement_over_baseline=improvement,
            is_improving=is_improving,
            is_declining=is_declining,
        )

    async def get_declining_patterns(
        self,
        window_hours: int = 24,
    ) -> List[PatternEffectiveness]:
        """
        Find patterns that are performing worse than their baseline.

        Args:
            window_hours: Time window for analysis

        Returns:
            List of declining patterns with their effectiveness metrics
        """
        # Get all patterns that have been applied recently
        pattern_ids = await self._get_recently_applied_patterns(window_hours)

        declining = []
        for pattern_id in pattern_ids:
            effectiveness = await self.get_pattern_effectiveness(pattern_id, window_hours)
            if effectiveness and effectiveness.is_declining:
                declining.append(effectiveness)

        return declining

    async def cleanup_old_records(self) -> int:
        """
        Remove old application records.

        Returns:
            Number of records deleted
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.RETENTION_HOURS)

        result = await self._db.execute(
            """
            DELETE FROM pattern_applications
            WHERE applied_at < ?
            """,
            (cutoff.isoformat(),),
        )

        deleted = result.rowcount if hasattr(result, "rowcount") else 0
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old pattern application records")

        return deleted

    # Private methods

    async def _insert_application(self, application: PatternApplication) -> None:
        """Insert a new application record."""
        await self._db.execute(
            """
            INSERT INTO pattern_applications (
                id, pattern_id, task_id, task_type, agent_code,
                applied_at, was_routing_pattern, was_confidence_pattern,
                outcome_recorded, outcome_success, outcome_duration_ms,
                outcome_effectiveness, baseline_agent, baseline_success_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application.id,
                application.pattern_id,
                application.task_id,
                application.task_type,
                application.agent_code,
                application.applied_at.isoformat(),
                1 if application.was_routing_pattern else 0,
                1 if application.was_confidence_pattern else 0,
                0,  # outcome_recorded = False initially
                0,
                0.0,
                0.0,
                application.baseline_agent,
                application.baseline_success_rate,
            ),
        )

    async def _update_application_outcome(
        self,
        application: PatternApplication,
    ) -> None:
        """Update an application record with its outcome."""
        await self._db.execute(
            """
            UPDATE pattern_applications
            SET outcome_recorded = 1,
                outcome_success = ?,
                outcome_duration_ms = ?,
                outcome_effectiveness = ?
            WHERE id = ?
            """,
            (
                1 if application.outcome_success else 0,
                application.outcome_duration_ms,
                application.outcome_effectiveness,
                application.id,
            ),
        )

    async def _update_pattern_stats(
        self,
        application: PatternApplication,
    ) -> None:
        """Update the pattern's overall statistics based on this application."""
        now = datetime.now(timezone.utc).isoformat()

        # Get current pattern stats
        row = await self._db.fetch_one(
            """
            SELECT application_count, success_rate, sample_size
            FROM learned_patterns
            WHERE id = ?
            """,
            (application.pattern_id,),
        )

        if not row:
            return

        # Calculate new success rate using exponential moving average
        current_count = row["application_count"] or 0
        current_rate = row["success_rate"] or 0.5
        sample_size = row["sample_size"] or 0

        # Weight recent outcomes more heavily
        alpha = 0.1  # Smoothing factor
        new_rate = (
            alpha * (1.0 if application.outcome_success else 0.0) + (1 - alpha) * current_rate
        )

        # Also update sample size based on outcomes
        new_sample_size = sample_size + 1

        await self._db.execute(
            """
            UPDATE learned_patterns
            SET success_rate = ?,
                sample_size = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (new_rate, new_sample_size, now, application.pattern_id),
        )

    async def _get_application_by_task(
        self,
        task_id: str,
    ) -> Optional[PatternApplication]:
        """Get application record by task ID."""
        row = await self._db.fetch_one(
            """
            SELECT * FROM pattern_applications
            WHERE task_id = ?
            """,
            (task_id,),
        )
        return self._row_to_application(row) if row else None

    async def _get_applications_for_pattern(
        self,
        pattern_id: str,
        since: datetime,
    ) -> List[PatternApplication]:
        """Get all applications for a pattern since a given time."""
        rows = await self._db.fetch_all(
            """
            SELECT * FROM pattern_applications
            WHERE pattern_id = ?
            AND applied_at >= ?
            AND outcome_recorded = 1
            ORDER BY applied_at DESC
            """,
            (pattern_id, since.isoformat()),
        )
        return [self._row_to_application(row) for row in rows]

    async def _get_recently_applied_patterns(
        self,
        window_hours: int,
    ) -> List[str]:
        """Get IDs of patterns applied in the time window."""
        since = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        rows = await self._db.fetch_all(
            """
            SELECT DISTINCT pattern_id FROM pattern_applications
            WHERE applied_at >= ?
            AND outcome_recorded = 1
            """,
            (since.isoformat(),),
        )
        return [row["pattern_id"] for row in rows]

    def _row_to_application(self, row: Dict[str, Any]) -> PatternApplication:
        """Convert database row to PatternApplication."""
        return PatternApplication(
            id=row["id"],
            pattern_id=row["pattern_id"],
            task_id=row["task_id"],
            task_type=row["task_type"],
            agent_code=row["agent_code"],
            applied_at=datetime.fromisoformat(row["applied_at"]),
            was_routing_pattern=bool(row["was_routing_pattern"]),
            was_confidence_pattern=bool(row["was_confidence_pattern"]),
            outcome_recorded=bool(row["outcome_recorded"]),
            outcome_success=bool(row["outcome_success"]),
            outcome_duration_ms=row["outcome_duration_ms"] or 0.0,
            outcome_effectiveness=row["outcome_effectiveness"] or 0.0,
            baseline_agent=row.get("baseline_agent"),
            baseline_success_rate=row.get("baseline_success_rate"),
        )
