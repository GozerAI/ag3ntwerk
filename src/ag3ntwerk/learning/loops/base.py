"""
Base class for learning loops at each hierarchy level.

Provides the abstract interface and common functionality for
Agent, Manager, and Specialist learning loops.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.learning.models import (
    AgentPerformance,
    LearnedPattern,
    LearningAdjustment,
    LearningIssue,
    PerformanceTrend,
    ScopeLevel,
    TaskOutcomeRecord,
)
from ag3ntwerk.learning.pattern_store import PatternStore

logger = logging.getLogger(__name__)


class LearningLoop(ABC):
    """
    Abstract base class for learning loops.

    Each loop level (Agent, Manager, Specialist) implements
    specific learning strategies appropriate to its scope.
    """

    def __init__(
        self,
        agent_code: str,
        level: ScopeLevel,
        pattern_store: PatternStore,
        db: Any,
    ):
        """
        Initialize the learning loop.

        Args:
            agent_code: Code of the agent this loop serves
            level: Hierarchy level (agent, manager, specialist)
            pattern_store: Pattern persistence store
            db: Database connection
        """
        self.agent_code = agent_code
        self.level = level
        self.pattern_store = pattern_store
        self._db = db

        # Configuration
        self.min_samples_for_pattern = 10
        self.pattern_confidence_threshold = 0.7
        self.performance_window_hours = 24

    @abstractmethod
    async def analyze_outcomes(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearnedPattern]:
        """
        Analyze outcomes and generate patterns.

        Args:
            outcomes: List of task outcomes to analyze

        Returns:
            List of detected patterns
        """
        pass

    @abstractmethod
    async def apply_learning(
        self,
        task_type: str,
        patterns: List[LearnedPattern],
    ) -> LearningAdjustment:
        """
        Apply learned patterns to influence task handling.

        Args:
            task_type: Type of task being handled
            patterns: Applicable patterns

        Returns:
            Adjustments to apply
        """
        pass

    @abstractmethod
    async def detect_issues(
        self,
        outcomes: List[TaskOutcomeRecord],
        patterns: List[LearnedPattern],
    ) -> List[LearningIssue]:
        """
        Detect issues that need investigation.

        Args:
            outcomes: Recent outcomes
            patterns: Current patterns

        Returns:
            List of detected issues
        """
        pass

    async def get_applicable_patterns(
        self,
        task_type: str,
    ) -> List[LearnedPattern]:
        """
        Get patterns that apply to a task type.

        Args:
            task_type: Type of task

        Returns:
            List of applicable patterns
        """
        return await self.pattern_store.get_patterns(
            scope_level=self.level,
            scope_code=self.agent_code,
            task_type=task_type,
            is_active=True,
        )

    async def update_performance_metrics(
        self,
        outcome: TaskOutcomeRecord,
    ) -> None:
        """
        Update rolling performance metrics for this agent.

        Args:
            outcome: New outcome to incorporate
        """
        # Fetch current metrics
        metrics = await self._get_or_create_performance()

        # Update metrics with exponential moving average
        alpha = 0.1  # Smoothing factor

        metrics.total_tasks += 1
        if outcome.success:
            metrics.successful_tasks += 1
        else:
            metrics.failed_tasks += 1
            metrics.consecutive_failures += 1
            metrics.last_failure_at = datetime.now(timezone.utc)

        # Reset consecutive failures on success
        if outcome.success:
            metrics.consecutive_failures = 0

        # Update averages with EMA
        if outcome.duration_ms > 0:
            metrics.avg_duration_ms = (
                alpha * outcome.duration_ms + (1 - alpha) * metrics.avg_duration_ms
            )

        if outcome.initial_confidence is not None:
            metrics.avg_confidence = (
                alpha * outcome.initial_confidence + (1 - alpha) * metrics.avg_confidence
            )

        if outcome.actual_accuracy is not None:
            metrics.avg_actual_accuracy = (
                alpha * outcome.actual_accuracy + (1 - alpha) * metrics.avg_actual_accuracy
            )

        # Update task type success rates
        task_type = outcome.task_type
        current_rate = metrics.task_type_success_rates.get(task_type, 0.5)
        new_value = 1.0 if outcome.success else 0.0
        metrics.task_type_success_rates[task_type] = alpha * new_value + (1 - alpha) * current_rate

        # Calculate health score
        metrics.health_score = self._calculate_health_score(metrics)

        # Update circuit breaker
        if metrics.consecutive_failures >= 3:
            metrics.circuit_breaker_open = True
        elif outcome.success:
            metrics.circuit_breaker_open = False

        metrics.last_updated = datetime.now(timezone.utc)

        # Persist
        await self._save_performance(metrics)

    async def get_performance(self) -> Optional[AgentPerformance]:
        """Get current performance metrics for this agent."""
        row = await self._db.fetch_one(
            "SELECT * FROM agent_performance WHERE agent_code = ?",
            (self.agent_code,),
        )
        return self._row_to_performance(row) if row else None

    # Protected helper methods

    def _calculate_success_rate(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> float:
        """Calculate success rate from outcomes."""
        if not outcomes:
            return 0.0
        return sum(1 for o in outcomes if o.success) / len(outcomes)

    def _calculate_avg_effectiveness(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> float:
        """Calculate average effectiveness from outcomes."""
        if not outcomes:
            return 0.0
        return sum(o.effectiveness for o in outcomes) / len(outcomes)

    def _detect_trend(
        self,
        recent_rate: float,
        older_rate: float,
        threshold: float = 0.1,
    ) -> PerformanceTrend:
        """
        Detect performance trend from rates.

        Args:
            recent_rate: Recent success rate
            older_rate: Older success rate
            threshold: Minimum difference to detect trend

        Returns:
            Performance trend
        """
        delta = recent_rate - older_rate

        if delta > threshold:
            return PerformanceTrend.IMPROVING
        elif delta < -threshold:
            return PerformanceTrend.DECLINING
        else:
            return PerformanceTrend.STABLE

    def _matches_condition(
        self,
        task_type: str,
        condition: Dict[str, Any],
    ) -> bool:
        """
        Check if a task type matches a pattern condition.

        Args:
            task_type: Task type to check
            condition: Pattern condition

        Returns:
            True if matches
        """
        condition_task_type = condition.get("task_type")

        if condition_task_type is None:
            return True

        if isinstance(condition_task_type, list):
            return task_type in condition_task_type

        return condition_task_type == task_type

    def _calculate_health_score(
        self,
        metrics: AgentPerformance,
    ) -> float:
        """
        Calculate health score from metrics.

        Score is based on:
        - Success rate (40%)
        - Consecutive failures penalty (30%)
        - Confidence calibration (30%)

        Returns:
            Health score between 0.0 and 1.0
        """
        # Base on success rate
        success_rate = metrics.success_rate
        health = success_rate * 0.4

        # Penalty for consecutive failures
        failure_penalty = min(metrics.consecutive_failures * 0.1, 0.3)
        health += 0.3 - failure_penalty

        # Confidence calibration score
        calibration = 1.0 - abs(metrics.avg_confidence - metrics.avg_actual_accuracy)
        health += calibration * 0.3

        return max(0.0, min(1.0, health))

    # Private methods

    async def _get_or_create_performance(self) -> AgentPerformance:
        """Get or create performance metrics for this agent."""
        existing = await self.get_performance()
        if existing:
            return existing

        # Create new metrics
        metrics = AgentPerformance(
            agent_code=self.agent_code,
            agent_level=self.level,
        )
        await self._save_performance(metrics)
        return metrics

    async def _save_performance(self, metrics: AgentPerformance) -> None:
        """Save performance metrics to database."""
        now = datetime.now(timezone.utc).isoformat()

        # Use upsert pattern
        await self._db.execute(
            """
            INSERT INTO agent_performance (
                agent_code, agent_level, parent_code,
                total_tasks, successful_tasks, failed_tasks, avg_duration_ms,
                task_type_success_rates,
                avg_confidence, avg_actual_accuracy, confidence_calibration_score,
                performance_trend, trend_magnitude,
                health_score, consecutive_failures, last_failure_at, circuit_breaker_open,
                last_updated, window_start
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_code) DO UPDATE SET
                total_tasks = excluded.total_tasks,
                successful_tasks = excluded.successful_tasks,
                failed_tasks = excluded.failed_tasks,
                avg_duration_ms = excluded.avg_duration_ms,
                task_type_success_rates = excluded.task_type_success_rates,
                avg_confidence = excluded.avg_confidence,
                avg_actual_accuracy = excluded.avg_actual_accuracy,
                confidence_calibration_score = excluded.confidence_calibration_score,
                performance_trend = excluded.performance_trend,
                trend_magnitude = excluded.trend_magnitude,
                health_score = excluded.health_score,
                consecutive_failures = excluded.consecutive_failures,
                last_failure_at = excluded.last_failure_at,
                circuit_breaker_open = excluded.circuit_breaker_open,
                last_updated = excluded.last_updated
            """,
            (
                metrics.agent_code,
                metrics.agent_level.value,
                metrics.parent_code,
                metrics.total_tasks,
                metrics.successful_tasks,
                metrics.failed_tasks,
                metrics.avg_duration_ms,
                json.dumps(metrics.task_type_success_rates),
                metrics.avg_confidence,
                metrics.avg_actual_accuracy,
                metrics.confidence_calibration_score,
                metrics.performance_trend.value,
                metrics.trend_magnitude,
                metrics.health_score,
                metrics.consecutive_failures,
                metrics.last_failure_at.isoformat() if metrics.last_failure_at else None,
                1 if metrics.circuit_breaker_open else 0,
                now,
                metrics.window_start.isoformat(),
            ),
        )

    def _row_to_performance(self, row: Dict[str, Any]) -> AgentPerformance:
        """Convert a database row to AgentPerformance."""
        task_type_rates = {}
        if row.get("task_type_success_rates"):
            try:
                task_type_rates = json.loads(row["task_type_success_rates"])
            except (json.JSONDecodeError, TypeError):
                pass

        return AgentPerformance(
            agent_code=row["agent_code"],
            agent_level=ScopeLevel(row["agent_level"]),
            parent_code=row["parent_code"],
            total_tasks=row["total_tasks"] or 0,
            successful_tasks=row["successful_tasks"] or 0,
            failed_tasks=row["failed_tasks"] or 0,
            avg_duration_ms=row["avg_duration_ms"] or 0.0,
            task_type_success_rates=task_type_rates,
            avg_confidence=row["avg_confidence"] or 0.5,
            avg_actual_accuracy=row["avg_actual_accuracy"] or 0.5,
            confidence_calibration_score=row["confidence_calibration_score"] or 0.0,
            performance_trend=PerformanceTrend(row["performance_trend"] or "stable"),
            trend_magnitude=row["trend_magnitude"] or 0.0,
            health_score=row["health_score"] or 1.0,
            consecutive_failures=row["consecutive_failures"] or 0,
            last_failure_at=(
                datetime.fromisoformat(row["last_failure_at"]) if row["last_failure_at"] else None
            ),
            circuit_breaker_open=bool(row["circuit_breaker_open"]),
            last_updated=datetime.fromisoformat(row["last_updated"]),
            window_start=datetime.fromisoformat(row["window_start"]),
        )
