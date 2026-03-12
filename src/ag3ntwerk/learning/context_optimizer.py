"""
Context-aware optimization for the ag3ntwerk learning system.

Optimizes task execution decisions based on rich context including
time patterns, system load, and recent outcomes.
"""

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .models import TaskOutcomeRecord
from .outcome_tracker import OutcomeTracker
from .pattern_store import PatternStore


class OptimizationType(str, Enum):
    """Types of optimization applied."""

    PRIORITY_ADJUSTMENT = "priority_adjustment"
    TIMEOUT_ADJUSTMENT = "timeout_adjustment"
    AGENT_SELECTION = "agent_selection"
    BATCHING = "batching"
    DEFERRAL = "deferral"


class TimeOfDay(str, Enum):
    """Time of day categories."""

    PEAK = "peak"
    OFF_PEAK = "off_peak"
    OVERNIGHT = "overnight"


class LoadLevel(str, Enum):
    """System load levels."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ExecutionContext:
    """Context for task execution."""

    timestamp: datetime
    system_load: float
    active_tasks: int
    recent_failure_rate: float
    queue_depth: int
    avg_response_time_ms: float
    custom_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "system_load": self.system_load,
            "active_tasks": self.active_tasks,
            "recent_failure_rate": self.recent_failure_rate,
            "queue_depth": self.queue_depth,
            "avg_response_time_ms": self.avg_response_time_ms,
            "custom_context": self.custom_context,
        }


@dataclass
class Task:
    """Task to be optimized."""

    task_id: str
    task_type: str
    priority: int
    timeout_ms: float
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "priority": self.priority,
            "timeout_ms": self.timeout_ms,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class TimePattern:
    """Pattern based on time of day."""

    time_of_day: TimeOfDay
    avg_success_rate: float
    avg_duration_ms: float
    typical_load: float
    sample_size: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time_of_day": self.time_of_day.value,
            "avg_success_rate": self.avg_success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "typical_load": self.typical_load,
            "sample_size": self.sample_size,
        }


@dataclass
class LoadPattern:
    """Pattern based on system load."""

    load_level: LoadLevel
    avg_success_rate: float
    avg_duration_ms: float
    timeout_factor: float
    sample_size: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "load_level": self.load_level.value,
            "avg_success_rate": self.avg_success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "timeout_factor": self.timeout_factor,
            "sample_size": self.sample_size,
        }


@dataclass
class OptimizationAction:
    """A single optimization action."""

    optimization_type: OptimizationType
    original_value: Any
    optimized_value: Any
    confidence: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "optimization_type": self.optimization_type.value,
            "original_value": self.original_value,
            "optimized_value": self.optimized_value,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass
class AgentRecommendation:
    """Recommended agent for task execution."""

    agent_code: str
    score: float
    success_rate: float
    avg_duration_ms: float
    current_load: float
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "score": self.score,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "current_load": self.current_load,
            "reasons": self.reasons,
        }


@dataclass
class OptimizedTask:
    """Result of task optimization."""

    optimization_id: str
    created_at: datetime
    original: Task
    recommended_priority: int
    recommended_timeout: float
    recommended_agent: Optional[AgentRecommendation]
    optimizations_applied: List[OptimizationAction]
    should_defer: bool
    defer_until: Optional[datetime]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "optimization_id": self.optimization_id,
            "created_at": self.created_at.isoformat(),
            "original": self.original.to_dict(),
            "recommended_priority": self.recommended_priority,
            "recommended_timeout": self.recommended_timeout,
            "recommended_agent": (
                self.recommended_agent.to_dict() if self.recommended_agent else None
            ),
            "optimizations_applied": [o.to_dict() for o in self.optimizations_applied],
            "should_defer": self.should_defer,
            "defer_until": (self.defer_until.isoformat() if self.defer_until else None),
            "confidence": self.confidence,
        }


class ContextOptimizer:
    """
    Optimizes task execution based on rich context.

    Considers multiple factors to optimize:
    - Priority: Adjust based on system state and task characteristics
    - Timeout: Adjust based on historical performance and load
    - Agent selection: Choose optimal agent based on context
    - Deferral: Recommend delaying tasks when beneficial
    """

    # Priority adjustment thresholds
    PRIORITY_BOOST_THRESHOLD = 0.8
    PRIORITY_REDUCE_THRESHOLD = 0.3

    # Timeout adjustment factors
    MIN_TIMEOUT_FACTOR = 0.5
    MAX_TIMEOUT_FACTOR = 3.0

    # Load level thresholds
    LOW_LOAD_THRESHOLD = 0.3
    MODERATE_LOAD_THRESHOLD = 0.6
    HIGH_LOAD_THRESHOLD = 0.8

    # Peak hours (configurable)
    PEAK_HOURS = range(9, 18)  # 9 AM to 6 PM
    OVERNIGHT_HOURS = range(0, 6)  # Midnight to 6 AM

    def __init__(
        self,
        db: Any,
        outcome_tracker: OutcomeTracker,
        pattern_store: PatternStore,
    ):
        self._db = db
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store

    async def optimize_for_context(
        self,
        task: Task,
        context: ExecutionContext,
    ) -> OptimizedTask:
        """
        Optimize task execution for the given context.

        Args:
            task: The task to optimize
            context: Current execution context

        Returns:
            Optimized task with recommendations
        """
        import uuid

        optimizations = []
        confidence_factors = []

        # Get historical patterns
        time_patterns = await self._get_time_patterns(context.timestamp)
        load_patterns = await self._get_load_patterns(context.system_load)
        recent_outcomes = await self._get_recent_outcomes(task.task_type)

        # Optimize priority
        priority_action, priority_confidence = self._adjust_priority(
            task, time_patterns, load_patterns, context
        )
        if priority_action:
            optimizations.append(priority_action)
            confidence_factors.append(priority_confidence)
        recommended_priority = priority_action.optimized_value if priority_action else task.priority

        # Optimize timeout
        timeout_action, timeout_confidence = self._adjust_timeout(
            task, load_patterns, recent_outcomes, context
        )
        if timeout_action:
            optimizations.append(timeout_action)
            confidence_factors.append(timeout_confidence)
        recommended_timeout = timeout_action.optimized_value if timeout_action else task.timeout_ms

        # Select optimal agent
        recommended_agent = await self._select_optimal_agent(task, recent_outcomes, context)
        if recommended_agent:
            optimizations.append(
                OptimizationAction(
                    optimization_type=OptimizationType.AGENT_SELECTION,
                    original_value=None,
                    optimized_value=recommended_agent.agent_code,
                    confidence=recommended_agent.score,
                    reason="; ".join(recommended_agent.reasons),
                )
            )
            confidence_factors.append(recommended_agent.score)

        # Check if should defer
        should_defer, defer_until, defer_reason = self._check_deferral(task, time_patterns, context)
        if should_defer:
            optimizations.append(
                OptimizationAction(
                    optimization_type=OptimizationType.DEFERRAL,
                    original_value=task.created_at or datetime.now(timezone.utc),
                    optimized_value=defer_until,
                    confidence=0.7,
                    reason=defer_reason,
                )
            )
            confidence_factors.append(0.7)

        # Calculate overall confidence
        overall_confidence = statistics.mean(confidence_factors) if confidence_factors else 0.5

        return OptimizedTask(
            optimization_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            original=task,
            recommended_priority=recommended_priority,
            recommended_timeout=recommended_timeout,
            recommended_agent=recommended_agent,
            optimizations_applied=optimizations,
            should_defer=should_defer,
            defer_until=defer_until,
            confidence=overall_confidence,
        )

    async def _get_time_patterns(
        self,
        timestamp: datetime,
    ) -> Optional[TimePattern]:
        """Get performance patterns for the time of day."""
        hour = timestamp.hour
        time_of_day = self._classify_time_of_day(hour)

        # Query historical data for this time period
        if time_of_day == TimeOfDay.PEAK:
            hour_range = self.PEAK_HOURS
        elif time_of_day == TimeOfDay.OVERNIGHT:
            hour_range = self.OVERNIGHT_HOURS
        else:
            hour_range = range(6, 9) if hour < 9 else range(18, 24)

        hours_list = list(hour_range)
        if not hours_list:
            return None

        placeholders = ",".join("?" * len(hours_list))
        query = f"""
            SELECT
                AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate,
                AVG(duration_ms) as avg_duration,
                COUNT(*) as sample_size
            FROM learning_outcomes
            WHERE CAST(strftime('%H', created_at) AS INTEGER) IN ({placeholders})
            AND created_at >= ?
        """

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        params = hours_list + [cutoff.isoformat()]

        row = await self._db.fetch_one(query, params)

        if not row or row["sample_size"] < 10:
            return None

        return TimePattern(
            time_of_day=time_of_day,
            avg_success_rate=row["success_rate"] or 0.0,
            avg_duration_ms=row["avg_duration"] or 0.0,
            typical_load=0.5,  # Would need load metrics table
            sample_size=row["sample_size"],
        )

    def _classify_time_of_day(self, hour: int) -> TimeOfDay:
        """Classify hour into time of day category."""
        if hour in self.PEAK_HOURS:
            return TimeOfDay.PEAK
        elif hour in self.OVERNIGHT_HOURS:
            return TimeOfDay.OVERNIGHT
        else:
            return TimeOfDay.OFF_PEAK

    async def _get_load_patterns(
        self,
        system_load: float,
    ) -> Optional[LoadPattern]:
        """Get performance patterns for the load level."""
        load_level = self._classify_load_level(system_load)

        # Query historical data for this load level
        # This would require load metrics in outcomes
        # For now, return a synthetic pattern based on load level

        if load_level == LoadLevel.CRITICAL:
            return LoadPattern(
                load_level=load_level,
                avg_success_rate=0.7,
                avg_duration_ms=5000.0,
                timeout_factor=2.0,
                sample_size=100,
            )
        elif load_level == LoadLevel.HIGH:
            return LoadPattern(
                load_level=load_level,
                avg_success_rate=0.85,
                avg_duration_ms=3000.0,
                timeout_factor=1.5,
                sample_size=100,
            )
        elif load_level == LoadLevel.MODERATE:
            return LoadPattern(
                load_level=load_level,
                avg_success_rate=0.92,
                avg_duration_ms=1500.0,
                timeout_factor=1.2,
                sample_size=100,
            )
        else:
            return LoadPattern(
                load_level=load_level,
                avg_success_rate=0.95,
                avg_duration_ms=1000.0,
                timeout_factor=1.0,
                sample_size=100,
            )

    def _classify_load_level(self, system_load: float) -> LoadLevel:
        """Classify system load into level category."""
        if system_load >= self.HIGH_LOAD_THRESHOLD:
            return LoadLevel.CRITICAL if system_load >= 0.95 else LoadLevel.HIGH
        elif system_load >= self.MODERATE_LOAD_THRESHOLD:
            return LoadLevel.MODERATE
        else:
            return LoadLevel.LOW

    async def _get_recent_outcomes(
        self,
        task_type: str,
    ) -> List[TaskOutcomeRecord]:
        """Get recent outcomes for task type."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        query = """
            SELECT *
            FROM learning_outcomes
            WHERE task_type = ?
            AND created_at >= ?
            ORDER BY created_at DESC
            LIMIT 100
        """

        rows = await self._db.fetch_all(query, [task_type, cutoff.isoformat()])

        outcomes = []
        for row in rows:
            outcomes.append(
                TaskOutcomeRecord(
                    id=row["id"],
                    task_id=row["task_id"],
                    task_type=row["task_type"],
                    agent_code=row["agent_code"],
                    manager_code=row.get("manager_code"),
                    specialist_code=row.get("specialist_code"),
                    success=bool(row["success"]),
                    duration_ms=row.get("duration_ms", 0.0),
                    error_message=row.get("error_message"),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )

        return outcomes

    def _adjust_priority(
        self,
        task: Task,
        time_pattern: Optional[TimePattern],
        load_pattern: Optional[LoadPattern],
        context: ExecutionContext,
    ) -> tuple[Optional[OptimizationAction], float]:
        """Adjust task priority based on context."""
        original_priority = task.priority
        new_priority = original_priority
        reasons = []
        confidence = 0.5

        # Boost priority during off-peak for better throughput
        if time_pattern and time_pattern.time_of_day == TimeOfDay.OFF_PEAK:
            if original_priority > 1:
                new_priority = max(1, original_priority - 1)
                reasons.append("Off-peak hours allow higher priority")
                confidence = 0.7

        # Reduce priority during high load
        if load_pattern and load_pattern.load_level in (LoadLevel.HIGH, LoadLevel.CRITICAL):
            if original_priority < 5:
                new_priority = min(5, original_priority + 1)
                reasons.append(f"High system load ({context.system_load:.0%})")
                confidence = 0.8

        # Boost priority if recent failures are high
        if context.recent_failure_rate > 0.3:
            if new_priority > 1:
                new_priority = max(1, new_priority - 1)
                reasons.append(f"High recent failure rate ({context.recent_failure_rate:.0%})")
                confidence = max(confidence, 0.75)

        if new_priority != original_priority:
            return (
                OptimizationAction(
                    optimization_type=OptimizationType.PRIORITY_ADJUSTMENT,
                    original_value=original_priority,
                    optimized_value=new_priority,
                    confidence=confidence,
                    reason="; ".join(reasons),
                ),
                confidence,
            )

        return None, 0.0

    def _adjust_timeout(
        self,
        task: Task,
        load_pattern: Optional[LoadPattern],
        recent_outcomes: List[TaskOutcomeRecord],
        context: ExecutionContext,
    ) -> tuple[Optional[OptimizationAction], float]:
        """Adjust task timeout based on context."""
        original_timeout = task.timeout_ms
        new_timeout = original_timeout
        reasons = []
        confidence = 0.5

        # Apply load factor
        if load_pattern:
            load_factor = load_pattern.timeout_factor
            if load_factor != 1.0:
                new_timeout = original_timeout * load_factor
                reasons.append(
                    f"Load level {load_pattern.load_level.value} " f"(factor: {load_factor:.1f}x)"
                )
                confidence = 0.8

        # Adjust based on recent performance
        if recent_outcomes:
            durations = [o.duration_ms for o in recent_outcomes if o.duration_ms > 0]
            if durations:
                p95_duration = sorted(durations)[int(len(durations) * 0.95)]
                if p95_duration > original_timeout * 0.8:
                    # Timeout might be too tight
                    suggested = p95_duration * 1.5
                    if suggested > new_timeout:
                        new_timeout = suggested
                        reasons.append(f"P95 duration ({p95_duration:.0f}ms) near timeout")
                        confidence = max(confidence, 0.85)

        # Apply bounds
        new_timeout = max(
            original_timeout * self.MIN_TIMEOUT_FACTOR,
            min(original_timeout * self.MAX_TIMEOUT_FACTOR, new_timeout),
        )

        if abs(new_timeout - original_timeout) > original_timeout * 0.1:
            return (
                OptimizationAction(
                    optimization_type=OptimizationType.TIMEOUT_ADJUSTMENT,
                    original_value=original_timeout,
                    optimized_value=new_timeout,
                    confidence=confidence,
                    reason="; ".join(reasons),
                ),
                confidence,
            )

        return None, 0.0

    async def _select_optimal_agent(
        self,
        task: Task,
        recent_outcomes: List[TaskOutcomeRecord],
        context: ExecutionContext,
    ) -> Optional[AgentRecommendation]:
        """Select optimal agent for task execution."""
        # Get agent performance for this task type
        query = """
            SELECT
                agent_code,
                COUNT(*) as count,
                AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate,
                AVG(duration_ms) as avg_duration
            FROM learning_outcomes
            WHERE task_type = ?
            AND created_at >= ?
            GROUP BY agent_code
            HAVING count >= 5
            ORDER BY success_rate DESC, avg_duration ASC
        """

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        rows = await self._db.fetch_all(query, [task.task_type, cutoff.isoformat()])

        if not rows:
            return None

        # Score each agent
        scored_agents = []
        for row in rows:
            agent_code = row["agent_code"]
            success_rate = row["success_rate"] or 0.0
            avg_duration = row["avg_duration"] or float("inf")

            # Get current load for agent
            current_load = await self._get_agent_load(agent_code)

            # Calculate score
            score = self._calculate_agent_score(success_rate, avg_duration, current_load, context)

            reasons = []
            if success_rate > 0.9:
                reasons.append(f"High success rate ({success_rate:.0%})")
            if avg_duration < 2000:
                reasons.append(f"Fast response ({avg_duration:.0f}ms)")
            if current_load < 0.5:
                reasons.append(f"Low current load ({current_load:.0%})")

            scored_agents.append(
                AgentRecommendation(
                    agent_code=agent_code,
                    score=score,
                    success_rate=success_rate,
                    avg_duration_ms=avg_duration,
                    current_load=current_load,
                    reasons=reasons,
                )
            )

        # Return best agent
        scored_agents.sort(key=lambda x: x.score, reverse=True)
        return scored_agents[0] if scored_agents else None

    async def _get_agent_load(self, agent_code: str) -> float:
        """Get current load for an agent."""
        # Get tasks in the last hour
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

        query = """
            SELECT COUNT(*) as count
            FROM learning_outcomes
            WHERE agent_code = ?
            AND created_at >= ?
        """

        row = await self._db.fetch_one(query, [agent_code, cutoff.isoformat()])
        task_count = row["count"] if row else 0

        # Normalize to 0-1 range (assume 100 tasks/hour is full load)
        return min(1.0, task_count / 100.0)

    def _calculate_agent_score(
        self,
        success_rate: float,
        avg_duration: float,
        current_load: float,
        context: ExecutionContext,
    ) -> float:
        """Calculate overall score for agent selection."""
        # Weight factors
        success_weight = 0.4
        speed_weight = 0.3
        load_weight = 0.3

        # Normalize duration to 0-1 (assume 10000ms is worst case)
        speed_score = max(0.0, 1.0 - avg_duration / 10000.0)

        # Invert load (lower is better)
        load_score = 1.0 - current_load

        score = (
            success_rate * success_weight + speed_score * speed_weight + load_score * load_weight
        )

        return min(1.0, max(0.0, score))

    def _check_deferral(
        self,
        task: Task,
        time_pattern: Optional[TimePattern],
        context: ExecutionContext,
    ) -> tuple[bool, Optional[datetime], str]:
        """Check if task should be deferred."""
        # Don't defer high priority tasks
        if task.priority <= 2:
            return False, None, ""

        # Defer during critical load
        if context.system_load >= 0.95:
            defer_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            return True, defer_until, "System at critical load"

        # Defer non-urgent tasks from peak to off-peak
        if (
            time_pattern
            and time_pattern.time_of_day == TimeOfDay.PEAK
            and task.priority >= 4
            and context.queue_depth > 50
        ):
            # Defer to off-peak hours
            now = datetime.now(timezone.utc)
            if now.hour < 18:
                defer_until = now.replace(hour=18, minute=0, second=0)
            else:
                defer_until = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0)
            return True, defer_until, "Deferring non-urgent task to off-peak hours"

        return False, None, ""

    async def get_optimization_stats(
        self,
        window_hours: int = 168,
    ) -> Dict[str, Any]:
        """Get optimization effectiveness statistics."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        query = """
            SELECT
                optimization_type,
                COUNT(*) as count,
                AVG(confidence) as avg_confidence,
                AVG(CASE WHEN outcome_success THEN 1 ELSE 0 END) as success_rate
            FROM optimization_outcomes
            WHERE created_at >= ?
            GROUP BY optimization_type
        """

        rows = await self._db.fetch_all(query, [cutoff.isoformat()])

        stats = {}
        for row in rows:
            stats[row["optimization_type"]] = {
                "count": row["count"],
                "avg_confidence": row["avg_confidence"],
                "success_rate": row["success_rate"],
            }

        return stats

    async def record_optimization_outcome(
        self,
        optimization_id: str,
        outcome_success: bool,
        actual_duration_ms: float,
    ) -> None:
        """Record outcome of an optimization for learning."""
        await self._db.execute(
            """
            UPDATE context_optimizations
            SET outcome_success = ?, actual_duration_ms = ?, completed_at = ?
            WHERE id = ?
            """,
            [
                outcome_success,
                actual_duration_ms,
                datetime.now(timezone.utc).isoformat(),
                optimization_id,
            ],
        )

    async def save_optimization(self, optimization: OptimizedTask) -> None:
        """Save optimization record for tracking."""
        await self._db.execute(
            """
            INSERT INTO context_optimizations (
                id, created_at, task_id, task_type,
                original_priority, recommended_priority,
                original_timeout, recommended_timeout,
                recommended_agent, should_defer, confidence,
                optimizations_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                optimization.optimization_id,
                optimization.created_at.isoformat(),
                optimization.original.task_id,
                optimization.original.task_type,
                optimization.original.priority,
                optimization.recommended_priority,
                optimization.original.timeout_ms,
                optimization.recommended_timeout,
                (
                    optimization.recommended_agent.agent_code
                    if optimization.recommended_agent
                    else None
                ),
                optimization.should_defer,
                optimization.confidence,
                json.dumps([o.to_dict() for o in optimization.optimizations_applied]),
            ],
        )
