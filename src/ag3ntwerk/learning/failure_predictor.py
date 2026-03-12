"""
Failure Predictor - Predicts task failure risk before execution.

Analyzes historical patterns to anticipate problems:
1. Error patterns for task type + agent combinations
2. Agent health and recent failure streaks
3. Queue depth and load indicators
4. Context-specific risk factors

This enables proactive mitigations like:
- Extended timeouts for timeout-prone tasks
- Fallback agent assignment for capability issues
- Priority adjustments for overloaded agents
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from ag3ntwerk.learning.models import ErrorCategory, ScopeLevel

if TYPE_CHECKING:
    from ag3ntwerk.core.queue import TaskQueue

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classifications."""

    LOW = "low"  # < 20% failure risk
    MODERATE = "moderate"  # 20-50% failure risk
    HIGH = "high"  # 50-80% failure risk
    CRITICAL = "critical"  # > 80% failure risk


class MitigationType(Enum):
    """Types of mitigations that can be applied."""

    EXTEND_TIMEOUT = "extend_timeout"
    USE_FALLBACK_AGENT = "use_fallback_agent"
    REDUCE_PRIORITY = "reduce_priority"
    ADD_RETRY = "add_retry"
    SIMPLIFY_TASK = "simplify_task"
    DELAY_EXECUTION = "delay_execution"
    ALERT_HUMAN = "alert_human"


@dataclass
class Mitigation:
    """A recommended mitigation for a predicted risk."""

    mitigation_type: MitigationType
    description: str
    confidence: float = 0.5  # How confident we are this will help
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.mitigation_type.value,
            "description": self.description,
            "confidence": self.confidence,
            "parameters": self.parameters,
        }


@dataclass
class FailureRisk:
    """
    Predicted failure risk for a task.

    Contains the risk score, primary risk category,
    and recommended mitigations.
    """

    score: float  # 0.0 to 1.0, higher = more likely to fail
    risk_level: RiskLevel

    # Primary risk factors
    primary_risk: Optional[ErrorCategory] = None
    risk_factors: List[str] = field(default_factory=list)

    # Component scores (for analysis)
    error_pattern_score: float = 0.0
    agent_health_score: float = 0.0
    load_score: float = 0.0
    context_score: float = 0.0

    # Mitigations
    mitigations: List[Mitigation] = field(default_factory=list)

    # Metadata
    agent_code: str = ""
    task_type: str = ""
    predicted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "risk_level": self.risk_level.value,
            "primary_risk": self.primary_risk.value if self.primary_risk else None,
            "risk_factors": self.risk_factors,
            "components": {
                "error_pattern": self.error_pattern_score,
                "agent_health": self.agent_health_score,
                "load": self.load_score,
                "context": self.context_score,
            },
            "mitigations": [m.to_dict() for m in self.mitigations],
            "agent_code": self.agent_code,
            "task_type": self.task_type,
        }


@dataclass
class ErrorPatternStats:
    """Statistics about error patterns for a task type + agent."""

    task_type: str
    agent_code: str
    total_tasks: int = 0
    failed_tasks: int = 0

    # Error category breakdown
    timeout_count: int = 0
    capability_count: int = 0
    resource_count: int = 0
    logic_count: int = 0
    external_count: int = 0

    # Recent trends
    recent_failure_rate: float = 0.0  # Last 24 hours
    historical_failure_rate: float = 0.0  # Overall

    @property
    def failure_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.failed_tasks / self.total_tasks

    @property
    def most_common_error(self) -> Optional[ErrorCategory]:
        counts = {
            ErrorCategory.TIMEOUT: self.timeout_count,
            ErrorCategory.CAPABILITY: self.capability_count,
            ErrorCategory.RESOURCE: self.resource_count,
            ErrorCategory.LOGIC: self.logic_count,
            ErrorCategory.EXTERNAL: self.external_count,
        }
        if not any(counts.values()):
            return None
        return max(counts, key=counts.get)


class FailurePredictor:
    """
    Predicts task failure risk based on historical patterns.

    Uses multiple signals:
    - Error patterns (historical failure rates by error category)
    - Agent health (circuit breaker state, consecutive failures)
    - Load indicators (queue depth, active tasks)
    - Context factors (task complexity, time of day, etc.)
    """

    # Weight configuration
    WEIGHTS = {
        "error_pattern": 0.35,
        "agent_health": 0.30,
        "load": 0.20,
        "context": 0.15,
    }

    # Risk thresholds
    RISK_THRESHOLDS = {
        RiskLevel.LOW: 0.2,
        RiskLevel.MODERATE: 0.5,
        RiskLevel.HIGH: 0.8,
        RiskLevel.CRITICAL: 1.0,
    }

    # Minimum samples for reliable prediction
    MIN_SAMPLES = 10

    def __init__(self, db: Any, task_queue: Optional["TaskQueue"] = None):
        """
        Initialize the failure predictor.

        Args:
            db: Database connection
            task_queue: Optional task queue for real-time queue metrics
        """
        self._db = db
        self._task_queue = task_queue

        # Cache for error pattern stats
        self._pattern_cache: Dict[Tuple[str, str], ErrorPatternStats] = {}
        self._cache_updated_at: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minute cache

    async def predict_failure_risk(
        self,
        task_type: str,
        target_agent: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> FailureRisk:
        """
        Predict the failure risk for a task.

        Args:
            task_type: Type of task
            target_agent: Agent that will handle the task
            context: Additional context about the task

        Returns:
            FailureRisk with score, risk level, and mitigations
        """
        risk = FailureRisk(
            score=0.0,
            risk_level=RiskLevel.LOW,
            agent_code=target_agent,
            task_type=task_type,
        )

        # 1. Error pattern score
        error_stats = await self._get_error_pattern_stats(task_type, target_agent)
        risk.error_pattern_score = self._calculate_error_pattern_score(error_stats)
        if error_stats and error_stats.most_common_error:
            risk.primary_risk = error_stats.most_common_error
            if error_stats.failure_rate > 0.3:
                risk.risk_factors.append(
                    f"High failure rate ({error_stats.failure_rate:.0%}) for {task_type}"
                )

        # 2. Agent health score
        agent_health = await self._get_agent_health(target_agent)
        risk.agent_health_score = self._calculate_agent_health_score(agent_health)
        if agent_health.get("circuit_breaker_open"):
            risk.risk_factors.append("Agent circuit breaker is open")
        if agent_health.get("consecutive_failures", 0) > 2:
            risk.risk_factors.append(
                f"Agent has {agent_health['consecutive_failures']} consecutive failures"
            )

        # 3. Load score
        load_metrics = await self._get_load_metrics(target_agent)
        risk.load_score = self._calculate_load_score(load_metrics)
        if load_metrics.get("queue_depth", 0) > 10:
            risk.risk_factors.append(f"High queue depth ({load_metrics['queue_depth']})")

        # 4. Context score
        risk.context_score = self._calculate_context_score(context or {})

        # Calculate total risk score
        risk.score = (
            self.WEIGHTS["error_pattern"] * risk.error_pattern_score
            + self.WEIGHTS["agent_health"] * risk.agent_health_score
            + self.WEIGHTS["load"] * risk.load_score
            + self.WEIGHTS["context"] * risk.context_score
        )

        # Clamp to [0, 1]
        risk.score = max(0.0, min(1.0, risk.score))

        # Determine risk level
        risk.risk_level = self._get_risk_level(risk.score)

        # Generate mitigations
        risk.mitigations = self._generate_mitigations(risk, error_stats, agent_health)

        return risk

    async def get_high_risk_agents(
        self,
        task_type: str,
        threshold: float = 0.5,
    ) -> List[Tuple[str, FailureRisk]]:
        """
        Find agents with high failure risk for a task type.

        Args:
            task_type: Type of task
            threshold: Risk score threshold

        Returns:
            List of (agent_code, risk) tuples sorted by risk descending
        """
        # Get all agents that have handled this task type
        rows = await self._db.fetch_all(
            """
            SELECT DISTINCT agent_code FROM learning_outcomes
            WHERE task_type = ?
            """,
            (task_type,),
        )

        high_risk = []
        for row in rows:
            agent_code = row["agent_code"]
            risk = await self.predict_failure_risk(task_type, agent_code)
            if risk.score >= threshold:
                high_risk.append((agent_code, risk))

        # Sort by risk score descending
        high_risk.sort(key=lambda x: x[1].score, reverse=True)
        return high_risk

    async def get_safest_agent(
        self,
        task_type: str,
        candidates: List[str],
    ) -> Optional[Tuple[str, FailureRisk]]:
        """
        Find the agent with lowest failure risk for a task.

        Args:
            task_type: Type of task
            candidates: List of candidate agent codes

        Returns:
            (agent_code, risk) tuple for safest agent, or None
        """
        if not candidates:
            return None

        risks = []
        for agent_code in candidates:
            risk = await self.predict_failure_risk(task_type, agent_code)
            risks.append((agent_code, risk))

        # Sort by risk score ascending
        risks.sort(key=lambda x: x[1].score)
        return risks[0]

    # Private methods

    async def _get_error_pattern_stats(
        self,
        task_type: str,
        agent_code: str,
    ) -> Optional[ErrorPatternStats]:
        """Get error pattern statistics for a task type + agent."""
        cache_key = (task_type, agent_code)

        # Check cache
        if self._is_cache_fresh() and cache_key in self._pattern_cache:
            return self._pattern_cache[cache_key]

        try:
            # Query recent outcomes
            window = datetime.now(timezone.utc) - timedelta(days=7)

            row = await self._db.fetch_one(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN error_category = 'timeout' THEN 1 ELSE 0 END) as timeout_count,
                    SUM(CASE WHEN error_category = 'capability' THEN 1 ELSE 0 END) as capability_count,
                    SUM(CASE WHEN error_category = 'resource' THEN 1 ELSE 0 END) as resource_count,
                    SUM(CASE WHEN error_category = 'logic' THEN 1 ELSE 0 END) as logic_count,
                    SUM(CASE WHEN error_category = 'external' THEN 1 ELSE 0 END) as external_count
                FROM learning_outcomes
                WHERE task_type = ? AND agent_code = ? AND created_at >= ?
                """,
                (task_type, agent_code, window.isoformat()),
            )

            if not row or row["total"] == 0:
                return None

            stats = ErrorPatternStats(
                task_type=task_type,
                agent_code=agent_code,
                total_tasks=row["total"] or 0,
                failed_tasks=row["failed"] or 0,
                timeout_count=row["timeout_count"] or 0,
                capability_count=row["capability_count"] or 0,
                resource_count=row["resource_count"] or 0,
                logic_count=row["logic_count"] or 0,
                external_count=row["external_count"] or 0,
            )

            # Cache result
            self._pattern_cache[cache_key] = stats
            self._cache_updated_at = datetime.now(timezone.utc)

            return stats

        except Exception as e:
            logger.warning(f"Failed to get error pattern stats: {e}")
            return None

    async def _get_agent_health(self, agent_code: str) -> Dict[str, Any]:
        """Get agent health metrics."""
        try:
            row = await self._db.fetch_one(
                """
                SELECT health_score, consecutive_failures, circuit_breaker_open,
                       last_failure_at, avg_duration_ms
                FROM agent_performance
                WHERE agent_code = ?
                """,
                (agent_code,),
            )

            if row:
                return {
                    "health_score": row["health_score"] or 1.0,
                    "consecutive_failures": row["consecutive_failures"] or 0,
                    "circuit_breaker_open": bool(row["circuit_breaker_open"]),
                    "last_failure_at": row["last_failure_at"],
                    "avg_duration_ms": row["avg_duration_ms"] or 0.0,
                }

            return {"health_score": 1.0, "consecutive_failures": 0}

        except Exception as e:
            logger.warning(f"Failed to get agent health: {e}")
            return {"health_score": 1.0, "consecutive_failures": 0}

    async def _get_load_metrics(self, agent_code: str) -> Dict[str, Any]:
        """Get agent load metrics from task queue and database."""
        try:
            # Get real-time queue metrics if task queue is available
            if self._task_queue:
                stats = await self._task_queue.get_stats()
                # Calculate utilization based on queue state
                total_active = stats.pending + stats.processing
                max_capacity = 20  # Configurable max tasks
                utilization = min(1.0, total_active / max_capacity)

                return {
                    "queue_depth": stats.pending,
                    "active_tasks": stats.processing,
                    "utilization": utilization,
                    "throughput": stats.throughput_per_minute,
                }

            # Fallback: estimate from recent task volume
            window = datetime.now(timezone.utc) - timedelta(minutes=5)

            row = await self._db.fetch_one(
                """
                SELECT COUNT(*) as recent_tasks
                FROM learning_outcomes
                WHERE agent_code = ? AND created_at >= ?
                """,
                (agent_code, window.isoformat()),
            )

            recent_tasks = row["recent_tasks"] if row else 0
            # Estimate utilization: assume 4 tasks per 5 minutes is full utilization
            utilization = min(1.0, recent_tasks / 4)

            return {
                "queue_depth": 0,
                "active_tasks": recent_tasks,
                "utilization": utilization,
            }

        except Exception as e:
            logger.warning(f"Failed to get load metrics: {e}")
            return {"queue_depth": 0, "active_tasks": 0, "utilization": 0.5}

    def _calculate_error_pattern_score(
        self,
        stats: Optional[ErrorPatternStats],
    ) -> float:
        """Calculate risk score from error patterns."""
        if not stats or stats.total_tasks < self.MIN_SAMPLES:
            return 0.3  # Unknown - moderate baseline

        # Base score from failure rate
        score = stats.failure_rate

        # Increase score for specific error types
        if stats.timeout_count > stats.failed_tasks * 0.5:
            score *= 1.2  # Timeout issues are harder to recover from

        if stats.capability_count > stats.failed_tasks * 0.5:
            score *= 1.3  # Capability issues suggest wrong agent

        return min(1.0, score)

    def _calculate_agent_health_score(self, health: Dict[str, Any]) -> float:
        """Calculate risk score from agent health."""
        if health.get("circuit_breaker_open"):
            return 1.0  # Maximum risk

        base_score = 1.0 - health.get("health_score", 1.0)

        # Add penalty for consecutive failures
        failures = health.get("consecutive_failures", 0)
        if failures > 0:
            base_score += min(0.5, failures * 0.1)

        return min(1.0, base_score)

    def _calculate_load_score(self, load: Dict[str, Any]) -> float:
        """Calculate risk score from load metrics."""
        score = 0.0

        # Queue depth factor
        queue_depth = load.get("queue_depth", 0)
        if queue_depth > 20:
            score += 0.5
        elif queue_depth > 10:
            score += 0.3
        elif queue_depth > 5:
            score += 0.1

        # Utilization factor
        utilization = load.get("utilization", 0.5)
        if utilization > 0.9:
            score += 0.3
        elif utilization > 0.8:
            score += 0.1

        return min(1.0, score)

    def _calculate_context_score(self, context: Dict[str, Any]) -> float:
        """Calculate risk score from task context."""
        score = 0.0

        # Check for complexity indicators
        if context.get("complexity", "normal") == "high":
            score += 0.3

        # Check for time-sensitive tasks
        if context.get("priority") == "critical":
            score += 0.1  # Higher visibility but also higher pressure

        # Check for large payloads
        if context.get("payload_size", 0) > 10000:
            score += 0.2

        return min(1.0, score)

    def _get_risk_level(self, score: float) -> RiskLevel:
        """Get risk level from score."""
        if score < self.RISK_THRESHOLDS[RiskLevel.LOW]:
            return RiskLevel.LOW
        elif score < self.RISK_THRESHOLDS[RiskLevel.MODERATE]:
            return RiskLevel.MODERATE
        elif score < self.RISK_THRESHOLDS[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _generate_mitigations(
        self,
        risk: FailureRisk,
        error_stats: Optional[ErrorPatternStats],
        agent_health: Dict[str, Any],
    ) -> List[Mitigation]:
        """Generate recommended mitigations based on risk factors."""
        mitigations = []

        # Circuit breaker open - must use different agent
        if agent_health.get("circuit_breaker_open"):
            mitigations.append(
                Mitigation(
                    mitigation_type=MitigationType.USE_FALLBACK_AGENT,
                    description="Agent circuit breaker is open, use fallback agent",
                    confidence=0.95,
                )
            )

        if not error_stats:
            return mitigations

        # Timeout issues - extend timeout
        if error_stats.most_common_error == ErrorCategory.TIMEOUT and error_stats.timeout_count > 3:
            mitigations.append(
                Mitigation(
                    mitigation_type=MitigationType.EXTEND_TIMEOUT,
                    description="Task type prone to timeouts, extend timeout",
                    confidence=0.7,
                    parameters={"multiplier": 2.0},
                )
            )

        # Capability issues - use different agent
        if (
            error_stats.most_common_error == ErrorCategory.CAPABILITY
            and error_stats.capability_count > 3
        ):
            mitigations.append(
                Mitigation(
                    mitigation_type=MitigationType.USE_FALLBACK_AGENT,
                    description="Agent may lack capability for this task type",
                    confidence=0.8,
                )
            )

        # High failure rate - add retry
        if error_stats.failure_rate > 0.3:
            mitigations.append(
                Mitigation(
                    mitigation_type=MitigationType.ADD_RETRY,
                    description="High failure rate, add automatic retry",
                    confidence=0.6,
                    parameters={"max_retries": 2},
                )
            )

        # Very high risk - alert human
        if risk.score > 0.8:
            mitigations.append(
                Mitigation(
                    mitigation_type=MitigationType.ALERT_HUMAN,
                    description="Very high failure risk, consider human review",
                    confidence=0.5,
                )
            )

        # Sort by confidence
        mitigations.sort(key=lambda m: m.confidence, reverse=True)
        return mitigations

    def _is_cache_fresh(self) -> bool:
        """Check if the pattern cache is still fresh."""
        if not self._cache_updated_at:
            return False
        age = (datetime.now(timezone.utc) - self._cache_updated_at).total_seconds()
        return age < self._cache_ttl_seconds
