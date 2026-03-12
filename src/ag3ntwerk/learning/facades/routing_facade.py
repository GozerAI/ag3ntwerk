"""
Routing Facade - Dynamic routing, pattern tracking, and confidence calibration.

This facade manages routing-related learning components:
- DynamicRouter: Learning-based task routing decisions
- PatternTracker: Tracks pattern applications and effectiveness
- ConfidenceCalibrator: Calibrates agent confidence predictions
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ag3ntwerk.learning.confidence_calibrator import ConfidenceCalibrator
from ag3ntwerk.learning.dynamic_router import DynamicRouter, RoutingDecision
from ag3ntwerk.learning.models import LearnedPattern
from ag3ntwerk.learning.pattern_store import PatternStore
from ag3ntwerk.learning.pattern_tracker import PatternTracker

if TYPE_CHECKING:
    from ag3ntwerk.learning.load_balancer import LoadBalancer

logger = logging.getLogger(__name__)


class RoutingFacade:
    """
    Facade for routing-related learning operations.

    Manages dynamic routing decisions, pattern application tracking,
    and confidence calibration.
    """

    def __init__(
        self,
        db: Any,
        pattern_store: PatternStore,
        load_balancer: Optional["LoadBalancer"] = None,
    ):
        """
        Initialize the routing facade.

        Args:
            db: Database connection
            pattern_store: Shared pattern store instance
            load_balancer: Optional LoadBalancer for real-time load metrics
        """
        self._db = db
        self._pattern_store = pattern_store
        self._dynamic_router = DynamicRouter(db, pattern_store, load_balancer)
        self._pattern_tracker = PatternTracker(db)
        self._confidence_calibrator = ConfidenceCalibrator(db)

    def set_load_balancer(self, load_balancer: "LoadBalancer") -> None:
        """
        Set or update the load balancer for dynamic routing.

        This allows late binding of the load balancer after initialization.

        Args:
            load_balancer: LoadBalancer instance for real-time load metrics
        """
        self._dynamic_router.set_load_balancer(load_balancer)

    # --- Dynamic Routing ---

    async def get_routing_decision(
        self,
        task_type: str,
        available_agents: Dict[str, Any],
        static_route: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """
        Get a learning-informed routing decision.

        This is the main entry point for dynamic routing. It uses learned
        patterns and performance metrics to select the best agent.

        Args:
            task_type: Type of task to route
            available_agents: Dict of agent_code -> agent instances
            static_route: The static routing rule (for fallback)
            context: Additional context about the task

        Returns:
            RoutingDecision with chosen agent and confidence
        """
        return await self._dynamic_router.get_routing_decision(
            task_type=task_type,
            available_agents=available_agents,
            static_route=static_route,
            context=context,
        )

    async def get_routing_patterns(
        self,
        task_type: str,
    ) -> List[LearnedPattern]:
        """
        Get routing patterns for a task type.

        Args:
            task_type: Type of task

        Returns:
            List of relevant routing patterns
        """
        return await self._dynamic_router.get_routing_patterns(task_type)

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

        Used to track whether dynamic routing decisions were successful.

        Args:
            task_type: Type of task
            chosen_agent: Agent that was chosen
            success: Whether the task succeeded
            was_dynamic: Whether dynamic routing was used
            duration_ms: Execution time
        """
        await self._dynamic_router.record_routing_outcome(
            task_type=task_type,
            chosen_agent=chosen_agent,
            success=success,
            was_dynamic=was_dynamic,
            duration_ms=duration_ms,
        )

    # --- Pattern Tracking ---

    async def record_pattern_application(
        self,
        pattern_id: str,
        task_id: str,
        task_type: str,
        agent_code: str,
        is_routing_pattern: bool = False,
        is_confidence_pattern: bool = False,
        baseline_agent: Optional[str] = None,
        baseline_success_rate: Optional[float] = None,
    ) -> str:
        """
        Record that a pattern was applied to a task.

        Call this before task execution to enable outcome tracking.

        Args:
            pattern_id: ID of the applied pattern
            task_id: ID of the task
            task_type: Type of task
            agent_code: Agent handling the task
            is_routing_pattern: Whether this was a routing pattern
            is_confidence_pattern: Whether this was a confidence pattern
            baseline_agent: What agent would have been used without pattern
            baseline_success_rate: Historical success rate for baseline

        Returns:
            Application record ID
        """
        return await self._pattern_tracker.record_application(
            pattern_id=pattern_id,
            task_id=task_id,
            task_type=task_type,
            agent_code=agent_code,
            was_routing_pattern=is_routing_pattern,
            was_confidence_pattern=is_confidence_pattern,
            baseline_agent=baseline_agent,
            baseline_success_rate=baseline_success_rate,
        )

    async def record_pattern_outcome(
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
        await self._pattern_tracker.record_outcome(
            task_id=task_id,
            success=success,
            duration_ms=duration_ms,
            effectiveness=effectiveness,
        )

    async def get_declining_patterns(
        self,
        window_hours: int = 24,
    ) -> List[Any]:
        """
        Get patterns that are performing worse than their baseline.

        Args:
            window_hours: Time window for analysis

        Returns:
            List of declining patterns with effectiveness metrics
        """
        return await self._pattern_tracker.get_declining_patterns(window_hours)

    # --- Confidence Calibration ---

    async def get_calibrated_confidence(
        self,
        agent_code: str,
        task_type: str,
        raw_confidence: float,
    ) -> float:
        """
        Get calibrated confidence for an agent's prediction.

        Adjusts raw confidence based on historical accuracy.

        Args:
            agent_code: Agent making the prediction
            task_type: Type of task
            raw_confidence: Agent's raw confidence (0-1)

        Returns:
            Calibrated confidence (0-1)
        """
        return await self._confidence_calibrator.get_calibrated_confidence(
            agent_code=agent_code,
            task_type=task_type,
            raw_confidence=raw_confidence,
        )

    async def record_confidence_prediction(
        self,
        agent_code: str,
        task_type: str,
        confidence: float,
        was_successful: bool,
    ) -> None:
        """
        Record a confidence prediction and its outcome.

        Used to update calibration curves.

        Args:
            agent_code: Agent that made the prediction
            task_type: Type of task
            confidence: Confidence prediction (0-1)
            was_successful: Whether the prediction was correct
        """
        await self._confidence_calibrator.record_prediction(
            agent_code=agent_code,
            task_type=task_type,
            confidence=confidence,
            was_successful=was_successful,
        )

    async def get_calibration_summary(
        self,
        agent_code: str,
    ) -> Dict[str, Any]:
        """
        Get calibration summary for an agent.

        Args:
            agent_code: Agent code

        Returns:
            Summary of calibration across all task types
        """
        return await self._confidence_calibrator.get_agent_calibration_summary(agent_code)

    async def get_poorly_calibrated_agents(
        self,
        threshold: float = 0.15,
    ) -> List[Dict[str, Any]]:
        """
        Find agents with poor calibration.

        Args:
            threshold: Calibration score threshold

        Returns:
            List of poorly calibrated agent summaries
        """
        return await self._confidence_calibrator.get_poorly_calibrated_agents(threshold)

    # --- Stats ---

    async def get_stats(self) -> Dict[str, Any]:
        """Get routing facade statistics."""
        return {
            "dynamic_router": (
                await self._dynamic_router.get_stats()
                if hasattr(self._dynamic_router, "get_stats")
                else {}
            ),
            "pattern_tracker": (
                await self._pattern_tracker.get_stats()
                if hasattr(self._pattern_tracker, "get_stats")
                else {}
            ),
            "confidence_calibrator": (
                await self._confidence_calibrator.get_stats()
                if hasattr(self._confidence_calibrator, "get_stats")
                else {}
            ),
        }

    # --- Accessors for components (used by orchestrator) ---

    @property
    def dynamic_router(self) -> DynamicRouter:
        """Get dynamic router."""
        return self._dynamic_router

    @property
    def pattern_tracker(self) -> PatternTracker:
        """Get pattern tracker."""
        return self._pattern_tracker

    @property
    def confidence_calibrator(self) -> ConfidenceCalibrator:
        """Get confidence calibrator."""
        return self._confidence_calibrator
