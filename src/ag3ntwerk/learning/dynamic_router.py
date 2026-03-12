"""
Dynamic Router - Learning-based routing for task assignment.

Replaces static ROUTING_RULES with dynamic, pattern-informed routing decisions.
Scores agents based on:
1. Learned patterns (historical success rates for task types)
2. Current performance metrics (recent success rate, health)
3. Load balancing (queue depth, utilization from LoadBalancer)
4. Confidence calibration (how well-calibrated an agent's predictions are)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from ag3ntwerk.learning.models import (
    AgentPerformance,
    LearnedPattern,
    PatternType,
    ScopeLevel,
)

if TYPE_CHECKING:
    from ag3ntwerk.learning.load_balancer import LoadBalancer

logger = logging.getLogger(__name__)


@dataclass
class RoutingScore:
    """
    Score for an agent's suitability to handle a task.

    Higher scores indicate better suitability.
    """

    agent_code: str
    total_score: float = 0.0

    # Component scores (for debugging/analysis)
    pattern_score: float = 0.0  # From learned patterns
    performance_score: float = 0.0  # From recent performance
    health_score: float = 0.0  # From agent health
    calibration_score: float = 0.0  # From confidence calibration
    load_score: float = 0.0  # From current load

    # Explanation
    reasons: List[str] = field(default_factory=list)
    applied_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "total_score": self.total_score,
            "components": {
                "pattern": self.pattern_score,
                "performance": self.performance_score,
                "health": self.health_score,
                "calibration": self.calibration_score,
                "load": self.load_score,
            },
            "reasons": self.reasons,
            "applied_patterns": self.applied_patterns,
        }


@dataclass
class RoutingDecision:
    """
    Result of a routing decision.

    Includes the chosen agent, alternatives, and explanation.
    """

    chosen_agent: str
    confidence: float = 0.0

    # All candidates with scores
    scores: List[RoutingScore] = field(default_factory=list)

    # Why this agent was chosen
    reasoning: str = ""

    # Was this a fallback to static routing?
    used_static_fallback: bool = False
    static_route: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chosen_agent": self.chosen_agent,
            "confidence": self.confidence,
            "scores": [s.to_dict() for s in self.scores],
            "reasoning": self.reasoning,
            "used_static_fallback": self.used_static_fallback,
            "static_route": self.static_route,
        }


class DynamicRouter:
    """
    Learning-based router for task assignment.

    Replaces static routing rules with dynamic decisions based on:
    - Learned patterns (routing patterns from past outcomes)
    - Agent performance (success rates, response times)
    - Agent health (circuit breaker state, consecutive failures)
    - Confidence calibration (how accurate are agent predictions)
    """

    # Weights for score components (can be tuned)
    # NOTE: Load weight is conservative (5%) since load balancing was just implemented.
    # Consider increasing to 10-15% after observing real-world behavior and validating
    # that queue depth metrics are accurate. The meta-learner could also tune these
    # weights automatically based on routing outcome data.
    WEIGHTS = {
        "pattern": 0.35,  # Historical patterns
        "performance": 0.30,  # Recent success rate
        "health": 0.20,  # Current health
        "calibration": 0.10,  # Confidence accuracy
        "load": 0.05,  # Current load (from LoadBalancer)
    }

    # Minimum samples before trusting pattern-based routing
    MIN_SAMPLES_FOR_CONFIDENCE = 10

    # Minimum confidence to override static routing
    MIN_CONFIDENCE_FOR_OVERRIDE = 0.6

    def __init__(
        self,
        db: Any,
        pattern_store: Any,
        load_balancer: Optional["LoadBalancer"] = None,
    ):
        """
        Initialize the dynamic router.

        Args:
            db: Database connection
            pattern_store: PatternStore for querying learned patterns
            load_balancer: Optional LoadBalancer for real-time load metrics
        """
        self._db = db
        self._pattern_store = pattern_store
        self._load_balancer = load_balancer

        # Cache for agent performance (refreshed periodically)
        self._performance_cache: Dict[str, AgentPerformance] = {}
        self._cache_updated_at: Optional[datetime] = None
        self._cache_ttl_seconds = 60  # Refresh cache every minute

        # Task type to candidate mapping (learned over time)
        self._task_type_candidates: Dict[str, Set[str]] = {}

    def set_load_balancer(self, load_balancer: "LoadBalancer") -> None:
        """
        Set or update the load balancer.

        This allows late binding of the load balancer after initialization.

        Args:
            load_balancer: LoadBalancer instance for real-time load metrics
        """
        self._load_balancer = load_balancer

    async def get_routing_decision(
        self,
        task_type: str,
        available_agents: Dict[str, Any],
        static_route: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """
        Get the best agent for a task type.

        Args:
            task_type: Type of task to route
            available_agents: Dict of agent_code -> agent instances
            static_route: The static routing rule (for fallback)
            context: Additional context about the task

        Returns:
            RoutingDecision with chosen agent and reasoning
        """
        if not available_agents:
            return RoutingDecision(
                chosen_agent="",
                confidence=0.0,
                reasoning="No agents available",
            )

        # Refresh performance cache if needed
        await self._refresh_performance_cache()

        # Get routing patterns for this task type
        patterns = await self._get_routing_patterns(task_type)

        # Score all available agents
        scores: List[RoutingScore] = []
        for agent_code, agent in available_agents.items():
            score = await self._score_agent(
                agent_code=agent_code,
                task_type=task_type,
                patterns=patterns,
                context=context,
            )
            scores.append(score)

        # Sort by total score descending
        scores.sort(key=lambda s: s.total_score, reverse=True)

        if not scores:
            return RoutingDecision(
                chosen_agent=static_route or "",
                confidence=0.0,
                used_static_fallback=True,
                static_route=static_route,
                reasoning="No scores computed, falling back to static",
            )

        best_score = scores[0]

        # Determine confidence in the decision
        confidence = self._calculate_confidence(scores, patterns)

        # Decide whether to use dynamic routing or fall back to static
        if confidence >= self.MIN_CONFIDENCE_FOR_OVERRIDE or static_route is None:
            return RoutingDecision(
                chosen_agent=best_score.agent_code,
                confidence=confidence,
                scores=scores,
                reasoning=self._build_reasoning(best_score, confidence),
                used_static_fallback=False,
                static_route=static_route,
            )
        else:
            # Low confidence - fall back to static routing
            # But only if the static route is available
            if static_route and static_route in available_agents:
                return RoutingDecision(
                    chosen_agent=static_route,
                    confidence=confidence,
                    scores=scores,
                    reasoning=f"Low confidence ({confidence:.2f}), using static route",
                    used_static_fallback=True,
                    static_route=static_route,
                )
            else:
                # Static route not available, use best score anyway
                return RoutingDecision(
                    chosen_agent=best_score.agent_code,
                    confidence=confidence,
                    scores=scores,
                    reasoning=f"Static route unavailable, using best score",
                    used_static_fallback=False,
                    static_route=static_route,
                )

    async def get_routing_patterns(
        self,
        task_type: str,
    ) -> List[LearnedPattern]:
        """
        Get routing patterns for a task type.

        This is a public method for the orchestrator to use.

        Args:
            task_type: Type of task

        Returns:
            List of relevant routing patterns
        """
        return await self._get_routing_patterns(task_type)

    async def record_routing_outcome(
        self,
        task_type: str,
        chosen_agent: str,
        success: bool,
        was_dynamic: bool,
        duration_ms: float = 0.0,
    ) -> None:
        """
        Record the outcome of a routing decision.

        Used to update patterns and track routing effectiveness.

        Args:
            task_type: Type of task
            chosen_agent: Agent that was chosen
            success: Whether the task succeeded
            was_dynamic: Whether dynamic routing was used
            duration_ms: Execution time
        """
        # Track task type → agent mapping
        if task_type not in self._task_type_candidates:
            self._task_type_candidates[task_type] = set()
        self._task_type_candidates[task_type].add(chosen_agent)

        # Performance cache will be refreshed on next request
        # The actual outcome is recorded by the LearningOrchestrator

    # Private methods

    async def _get_routing_patterns(self, task_type: str) -> List[LearnedPattern]:
        """Get routing patterns for a task type."""
        try:
            patterns = await self._pattern_store.get_patterns(
                pattern_type=PatternType.ROUTING,
                task_type=task_type,
                is_active=True,
            )
            return patterns
        except Exception as e:
            logger.warning(f"Failed to get routing patterns: {e}")
            return []

    async def _score_agent(
        self,
        agent_code: str,
        task_type: str,
        patterns: List[LearnedPattern],
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingScore:
        """
        Score an agent for handling a task.

        Combines multiple signals into a total score.
        """
        score = RoutingScore(agent_code=agent_code)

        # 1. Pattern score - from learned routing patterns
        pattern_score, pattern_reasons, applied = self._calculate_pattern_score(
            agent_code, task_type, patterns
        )
        score.pattern_score = pattern_score
        score.applied_patterns = applied
        score.reasons.extend(pattern_reasons)

        # 2. Performance score - from recent success rate
        perf = self._performance_cache.get(agent_code)
        if perf:
            score.performance_score = self._calculate_performance_score(perf, task_type)
            if perf.success_rate > 0.8:
                score.reasons.append(f"High success rate: {perf.success_rate:.0%}")
            elif perf.success_rate < 0.5:
                score.reasons.append(f"Low success rate: {perf.success_rate:.0%}")
        else:
            # Unknown agent - give neutral score
            score.performance_score = 0.5
            score.reasons.append("No performance history")

        # 3. Health score
        if perf:
            score.health_score = perf.health_score
            if perf.circuit_breaker_open:
                score.health_score = 0.0
                score.reasons.append("Circuit breaker open")
            elif perf.consecutive_failures > 2:
                score.reasons.append(f"Recent failures: {perf.consecutive_failures}")
        else:
            score.health_score = 1.0  # Assume healthy if unknown

        # 4. Calibration score - how accurate are predictions
        if perf and perf.total_tasks > self.MIN_SAMPLES_FOR_CONFIDENCE:
            score.calibration_score = 1.0 - abs(perf.confidence_calibration_score)
        else:
            score.calibration_score = 0.5  # Neutral if not enough data

        # 5. Load score - from LoadBalancer if available
        score.load_score = await self._calculate_load_score(agent_code, score)

        # Calculate total weighted score
        score.total_score = (
            self.WEIGHTS["pattern"] * score.pattern_score
            + self.WEIGHTS["performance"] * score.performance_score
            + self.WEIGHTS["health"] * score.health_score
            + self.WEIGHTS["calibration"] * score.calibration_score
            + self.WEIGHTS["load"] * score.load_score
        )

        return score

    def _calculate_pattern_score(
        self,
        agent_code: str,
        task_type: str,
        patterns: List[LearnedPattern],
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate score from routing patterns.

        Returns:
            (score, reasons, applied_pattern_ids)
        """
        if not patterns:
            return 0.5, ["No routing patterns"], []

        score = 0.5  # Start neutral
        reasons = []
        applied = []

        for pattern in patterns:
            # Check if pattern recommends this agent
            if pattern.routing_preference == agent_code:
                # Positive signal - pattern recommends this agent
                weight = pattern.confidence * (
                    pattern.sample_size / max(pattern.sample_size, self.MIN_SAMPLES_FOR_CONFIDENCE)
                )
                score += weight * 0.5  # Max +0.5 from patterns
                reasons.append(
                    f"Pattern {pattern.id[:8]} recommends (conf: {pattern.confidence:.2f})"
                )
                applied.append(pattern.id)

            # Check if pattern applies to this agent but has low success
            try:
                condition = json.loads(pattern.condition_json)
                if condition.get("scope_code") == agent_code:
                    if pattern.success_rate is not None and pattern.success_rate < 0.5:
                        # Negative signal - poor performance on this task type
                        score -= 0.3 * pattern.confidence
                        reasons.append(f"Pattern shows low success: {pattern.success_rate:.0%}")
                        applied.append(pattern.id)
            except (json.JSONDecodeError, TypeError):
                pass

        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))

        return score, reasons, applied

    def _calculate_performance_score(
        self,
        perf: AgentPerformance,
        task_type: str,
    ) -> float:
        """Calculate score from agent performance metrics."""
        # Check task-type-specific success rate first
        if task_type in perf.task_type_success_rates:
            task_rate = perf.task_type_success_rates[task_type]
            # Weight task-specific rate higher than overall
            return 0.7 * task_rate + 0.3 * perf.success_rate

        # Fall back to overall success rate
        return perf.success_rate

    async def _calculate_load_score(
        self,
        agent_code: str,
        score: RoutingScore,
    ) -> float:
        """
        Calculate load score from LoadBalancer metrics.

        The load score is inversely proportional to utilization:
        - 0% utilization = 1.0 score (fully available)
        - 100% utilization = 0.0 score (fully loaded)

        Applies additional penalty for overloaded agents (>90% utilization).

        Args:
            agent_code: Agent to check load for
            score: RoutingScore to update with reasons

        Returns:
            Load score between 0.0 and 1.0
        """
        if not self._load_balancer:
            # No load balancer - assume all agents equally available
            return 1.0

        try:
            loads = await self._load_balancer.get_agent_loads([agent_code])
            agent_load = loads.get(agent_code)

            if not agent_load:
                # Unknown agent - neutral score
                score.reasons.append("No load data available")
                return 0.5

            # Check availability first
            if not agent_load.is_available:
                score.reasons.append("Agent unavailable (circuit breaker open)")
                return 0.0

            # Calculate base score: inverse of utilization
            # Higher capacity = higher score
            load_score = max(0.0, 1.0 - agent_load.utilization)

            # Apply overload penalty
            if agent_load.utilization >= 0.9:
                load_score *= 0.5
                score.reasons.append(f"Overloaded (utilization: {agent_load.utilization:.0%})")
            elif agent_load.utilization >= 0.7:
                score.reasons.append(f"High load (utilization: {agent_load.utilization:.0%})")
            elif agent_load.utilization <= 0.2:
                score.reasons.append(f"Low load (utilization: {agent_load.utilization:.0%})")

            # Bonus for high available capacity
            if agent_load.available_capacity >= 5:
                load_score = min(1.0, load_score * 1.1)
                score.reasons.append(f"High available capacity ({agent_load.available_capacity})")

            return load_score

        except Exception as e:
            logger.warning(f"Failed to get load for {agent_code}: {e}")
            return 1.0  # Assume available on error

    def _calculate_confidence(
        self,
        scores: List[RoutingScore],
        patterns: List[LearnedPattern],
    ) -> float:
        """
        Calculate confidence in the routing decision.

        Based on:
        - Difference between top scores (clear winner = high confidence)
        - Number and quality of applicable patterns
        - Sample size behind the patterns
        """
        if len(scores) < 2:
            return 0.5 if scores else 0.0

        # Score gap between first and second
        gap = scores[0].total_score - scores[1].total_score
        gap_confidence = min(1.0, gap * 2)  # Max at 0.5 gap

        # Pattern-based confidence
        pattern_confidence = 0.0
        if patterns:
            total_samples = sum(p.sample_size for p in patterns)
            if total_samples >= self.MIN_SAMPLES_FOR_CONFIDENCE:
                pattern_confidence = min(1.0, sum(p.confidence for p in patterns) / len(patterns))

        # Combine
        return 0.6 * gap_confidence + 0.4 * pattern_confidence

    def _build_reasoning(self, score: RoutingScore, confidence: float) -> str:
        """Build human-readable reasoning for the decision."""
        parts = [f"Selected {score.agent_code} (score: {score.total_score:.2f})"]

        if score.reasons:
            parts.append("Reasons: " + "; ".join(score.reasons[:3]))

        parts.append(f"Confidence: {confidence:.0%}")

        return " | ".join(parts)

    async def _refresh_performance_cache(self) -> None:
        """Refresh the agent performance cache if stale."""
        now = datetime.now(timezone.utc)

        if (
            self._cache_updated_at
            and (now - self._cache_updated_at).total_seconds() < self._cache_ttl_seconds
        ):
            return  # Cache is fresh

        try:
            rows = await self._db.fetch_all(
                """
                SELECT * FROM agent_performance
                WHERE circuit_breaker_open = 0
                """
            )

            self._performance_cache.clear()
            for row in rows:
                perf = self._row_to_performance(row)
                self._performance_cache[perf.agent_code] = perf

            self._cache_updated_at = now

        except Exception as e:
            logger.warning(f"Failed to refresh performance cache: {e}")

    def _row_to_performance(self, row: Dict[str, Any]) -> AgentPerformance:
        """Convert a database row to AgentPerformance."""
        return AgentPerformance(
            agent_code=row["agent_code"],
            agent_level=ScopeLevel(row["agent_level"]),
            parent_code=row.get("parent_code"),
            total_tasks=row.get("total_tasks", 0),
            successful_tasks=row.get("successful_tasks", 0),
            failed_tasks=row.get("failed_tasks", 0),
            avg_duration_ms=row.get("avg_duration_ms", 0.0),
            avg_confidence=row.get("avg_confidence", 0.5),
            avg_actual_accuracy=row.get("avg_actual_accuracy", 0.5),
            confidence_calibration_score=row.get("confidence_calibration_score", 0.0),
            health_score=row.get("health_score", 1.0),
            consecutive_failures=row.get("consecutive_failures", 0),
            circuit_breaker_open=bool(row.get("circuit_breaker_open", False)),
        )
