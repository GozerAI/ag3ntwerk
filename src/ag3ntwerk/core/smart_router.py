"""
Smart Router - Learning-informed task routing.

Recommends optimal agents based on historical performance data
from the learning system, with fallback to static routing rules.

Factors:
- Historical success rate per agent per task type
- Current load (if available via metacognition)
- Personality fit (if metacognition service connected)
"""

from typing import Any, Dict, List, Optional, Tuple

from ag3ntwerk.core.logging import get_logger

logger = get_logger(__name__)


class SmartRouter:
    """Learning-informed task router.

    Queries the learning orchestrator for agent performance on task types
    and returns ranked agent recommendations.

    Falls back to static routing rules when no learning data is available
    (cold-start).
    """

    # Weights for scoring components
    WEIGHT_SUCCESS_RATE = 0.45
    WEIGHT_SPEED = 0.20
    WEIGHT_PERSONALITY = 0.15
    WEIGHT_LOAD = 0.20

    # Minimum outcomes before trusting learning data
    MIN_OUTCOMES_THRESHOLD = 5

    def __init__(
        self,
        learning_orchestrator=None,
        metacognition_service=None,
        static_rules: Optional[Dict[str, str]] = None,
        fallback_routes: Optional[Dict[str, List[str]]] = None,
    ):
        self._learning = learning_orchestrator
        self._metacognition = metacognition_service
        self._static_rules = static_rules or {}
        self._fallback_routes = fallback_routes or {}

        # Cache for performance data (refreshed periodically)
        self._perf_cache: Dict[str, Dict[str, Dict[str, float]]] = {}

    def connect_learning(self, orchestrator) -> None:
        """Connect or update the learning orchestrator."""
        self._learning = orchestrator

    def connect_metacognition(self, service) -> None:
        """Connect or update the metacognition service."""
        self._metacognition = service

    async def rank_agents(
        self,
        task_type: str,
        available_agents: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float]]:
        """Rank agents for a task type by predicted performance.

        Args:
            task_type: Type of task to route
            available_agents: Dict of agent_code -> agent instance
            context: Optional task context for personality matching

        Returns:
            List of (agent_code, score) tuples, highest score first
        """
        if not available_agents:
            return []

        scores: List[Tuple[str, float]] = []

        for agent_code in available_agents:
            score = await self._score_agent(agent_code, task_type, context)
            scores.append((agent_code, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    async def get_best_agent(
        self,
        task_type: str,
        available_agents: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[str, float]]:
        """Get the single best agent for a task type.

        Returns:
            (agent_code, score) or None if no agents available
        """
        ranked = await self.rank_agents(task_type, available_agents, context)
        return ranked[0] if ranked else None

    async def _score_agent(
        self,
        agent_code: str,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Compute a composite score for an agent on a task type."""
        success_rate = await self._get_success_rate(agent_code, task_type)
        speed_score = await self._get_speed_score(agent_code, task_type)
        personality_score = self._get_personality_score(agent_code, task_type, context)
        load_score = self._get_load_score(agent_code)

        score = (
            self.WEIGHT_SUCCESS_RATE * success_rate
            + self.WEIGHT_SPEED * speed_score
            + self.WEIGHT_PERSONALITY * personality_score
            + self.WEIGHT_LOAD * load_score
        )

        return round(score, 4)

    async def _get_success_rate(self, agent_code: str, task_type: str) -> float:
        """Get historical success rate from learning system."""
        if not self._learning:
            return 0.5  # Neutral default

        try:
            stats = await self._learning.get_agent_performance(
                agent_code=agent_code,
                task_type=task_type,
            )
            if stats and stats.get("total_outcomes", 0) >= self.MIN_OUTCOMES_THRESHOLD:
                return stats.get("success_rate", 0.5)
        except Exception as e:
            logger.debug("Failed to get success rate for %s: %s", agent_code, e)

        return 0.5  # Cold-start default

    async def _get_speed_score(self, agent_code: str, task_type: str) -> float:
        """Get speed score from learning system (lower latency = higher score)."""
        if not self._learning:
            return 0.5

        try:
            stats = await self._learning.get_agent_performance(
                agent_code=agent_code,
                task_type=task_type,
            )
            if stats and stats.get("avg_duration_ms"):
                avg_ms = stats["avg_duration_ms"]
                # Normalize: <1s = 1.0, >10s = 0.0
                if avg_ms <= 1000:
                    return 1.0
                if avg_ms >= 10000:
                    return 0.0
                return 1.0 - (avg_ms - 1000) / 9000
        except Exception as e:
            logger.debug("Failed to get speed score for %s: %s", agent_code, e)

        return 0.5

    def _get_personality_score(
        self,
        agent_code: str,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Get personality fit score from metacognition service."""
        if not self._metacognition:
            return 0.5

        try:
            profile = self._metacognition.get_profile(agent_code)
            if profile and context:
                task_traits = context.get("task_traits", {})
                if task_traits:
                    return profile.compute_task_fit(task_traits)
        except Exception as e:
            logger.debug("Failed to get personality score for %s: %s", agent_code, e)

        return 0.5

    def _get_load_score(self, agent_code: str) -> float:
        """Get load score (lower load = higher score)."""
        if not self._metacognition:
            return 0.5

        try:
            stats = self._metacognition.get_agent_stats(agent_code)
            if stats:
                active_tasks = stats.get("active_tasks", 0)
                # Normalize: 0 active = 1.0, 10+ active = 0.0
                if active_tasks >= 10:
                    return 0.0
                return 1.0 - (active_tasks / 10.0)
        except Exception as e:
            logger.debug("Failed to get load score for %s: %s", agent_code, e)

        return 0.5

    def get_static_route(self, task_type: str) -> Optional[str]:
        """Get the static route for a task type (cold-start fallback)."""
        return self._static_rules.get(task_type)

    def get_fallback_routes(self, task_type: str) -> List[str]:
        """Get fallback routes for a task type."""
        return self._fallback_routes.get(task_type, [])

    def has_learning_data(self) -> bool:
        """Check if learning system is connected and has data."""
        return self._learning is not None
