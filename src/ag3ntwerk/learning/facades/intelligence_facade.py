"""
Intelligence Facade - Demand forecasting, cascade prediction, and context optimization.

This facade manages predictive intelligence components:
- DemandForecaster: Forecasts task demand and detects anomalies
- CascadePredictor: Predicts downstream cascade effects
- ContextOptimizer: Optimizes task execution based on context
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.learning.cascade_predictor import (
    CascadePredictor,
    CascadeEffect,
    RoutingDecision as CascadeRoutingDecision,
    CascadeRisk,
    DownstreamAgent,
)
from ag3ntwerk.learning.context_optimizer import (
    ContextOptimizer,
    OptimizedTask,
    ExecutionContext,
    Task as OptTask,
    AgentRecommendation,
)
from ag3ntwerk.learning.demand_forecaster import (
    DemandForecaster,
    DemandForecast,
    SeasonalPattern,
    TrendInfo,
    ScalingRecommendation,
)
from ag3ntwerk.learning.outcome_tracker import OutcomeTracker
from ag3ntwerk.learning.pattern_store import PatternStore

logger = logging.getLogger(__name__)


class IntelligenceFacade:
    """
    Facade for predictive intelligence operations.

    Manages demand forecasting, cascade prediction,
    and context-based task optimization.
    """

    def __init__(
        self,
        db: Any,
        outcome_tracker: OutcomeTracker,
        pattern_store: PatternStore,
    ):
        """
        Initialize the intelligence facade.

        Args:
            db: Database connection
            outcome_tracker: Shared outcome tracker instance
            pattern_store: Shared pattern store instance
        """
        self._db = db
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store
        self._demand_forecaster = DemandForecaster(db, outcome_tracker, pattern_store)
        self._cascade_predictor = CascadePredictor(db, outcome_tracker, pattern_store)
        self._context_optimizer = ContextOptimizer(db, outcome_tracker, pattern_store)

    # --- Demand Forecasting ---

    def get_demand_forecaster(self) -> DemandForecaster:
        """Get the demand forecaster."""
        return self._demand_forecaster

    async def forecast_demand(
        self,
        horizon_hours: int = 24,
        history_hours: Optional[int] = None,
        agent_filter: Optional[str] = None,
    ) -> DemandForecast:
        """
        Forecast task demand for the specified horizon.

        Args:
            horizon_hours: How many hours ahead to forecast
            history_hours: How many hours of history to analyze
            agent_filter: Optional agent code to filter predictions

        Returns:
            DemandForecast with volume, distribution, and scaling recommendations
        """
        return await self._demand_forecaster.forecast_demand(
            horizon_hours=horizon_hours,
            history_hours=history_hours,
            agent_filter=agent_filter,
        )

    async def get_demand_anomalies(
        self,
        hours: int = 24,
        threshold: float = 2.0,
    ) -> List[Dict[str, Any]]:
        """
        Detect demand anomalies in recent history.

        Args:
            hours: Hours of history to check
            threshold: Standard deviations for anomaly detection

        Returns:
            List of detected anomalies
        """
        return await self._demand_forecaster.get_demand_anomalies(
            hours=hours,
            threshold=threshold,
        )

    async def save_demand_forecast(self, forecast: DemandForecast) -> None:
        """Save a forecast for historical tracking."""
        await self._demand_forecaster.save_forecast(forecast)

    # --- Cascade Prediction ---

    def get_cascade_predictor(self) -> CascadePredictor:
        """Get the cascade predictor."""
        return self._cascade_predictor

    async def predict_cascade(
        self,
        task_type: str,
        selected_agent: str,
        context: Optional[Dict[str, Any]] = None,
        priority: int = 1,
        estimated_duration_ms: float = 0.0,
    ) -> CascadeEffect:
        """
        Predict cascade effects of a routing decision.

        Args:
            task_type: Type of task
            selected_agent: Agent selected for the task
            context: Additional context
            priority: Task priority
            estimated_duration_ms: Estimated task duration

        Returns:
            CascadeEffect with downstream impact and risk assessment
        """
        decision = CascadeRoutingDecision(
            task_type=task_type,
            selected_agent=selected_agent,
            context=context or {},
            priority=priority,
            estimated_duration_ms=estimated_duration_ms,
        )
        return await self._cascade_predictor.predict_cascade(decision)

    async def record_cascade_outcome(
        self,
        prediction_id: str,
        actual_duration_ms: float,
        had_failures: bool,
        downstream_agents_used: List[str],
    ) -> None:
        """
        Record actual cascade outcome for learning.

        Args:
            prediction_id: ID of the prediction
            actual_duration_ms: Actual duration
            had_failures: Whether failures occurred
            downstream_agents_used: Agents actually used downstream
        """
        await self._cascade_predictor.record_cascade_outcome(
            prediction_id=prediction_id,
            actual_duration_ms=actual_duration_ms,
            had_failures=had_failures,
            downstream_agents_used=downstream_agents_used,
        )

    async def get_cascade_accuracy(
        self,
        window_hours: int = 168,
    ) -> Dict[str, Any]:
        """Get prediction accuracy for cascade predictions."""
        return await self._cascade_predictor.get_cascade_accuracy(window_hours)

    def set_agent_capacity(self, agent_code: str, capacity: float) -> None:
        """Set capacity for an agent (used in cascade prediction)."""
        self._cascade_predictor.set_agent_capacity(agent_code, capacity)

    async def save_cascade_prediction(self, prediction: CascadeEffect) -> None:
        """Save a cascade prediction for tracking."""
        await self._cascade_predictor.save_prediction(prediction)

    # --- Context Optimization ---

    def get_context_optimizer(self) -> ContextOptimizer:
        """Get the context optimizer."""
        return self._context_optimizer

    async def optimize_task_for_context(
        self,
        task_id: str,
        task_type: str,
        priority: int,
        timeout_ms: float,
        context: ExecutionContext,
        task_context: Optional[Dict[str, Any]] = None,
    ) -> OptimizedTask:
        """
        Optimize a task for the current execution context.

        Args:
            task_id: Task ID
            task_type: Type of task
            priority: Current priority
            timeout_ms: Current timeout
            context: Execution context (load, failures, etc.)
            task_context: Additional task context

        Returns:
            OptimizedTask with recommended adjustments
        """
        task = OptTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            timeout_ms=timeout_ms,
            context=task_context or {},
        )
        return await self._context_optimizer.optimize_for_context(task, context)

    async def record_optimization_outcome(
        self,
        optimization_id: str,
        outcome_success: bool,
        actual_duration_ms: float,
    ) -> None:
        """
        Record outcome of an optimization for learning.

        Args:
            optimization_id: ID of the optimization
            outcome_success: Whether the task succeeded
            actual_duration_ms: Actual execution duration
        """
        await self._context_optimizer.record_optimization_outcome(
            optimization_id=optimization_id,
            outcome_success=outcome_success,
            actual_duration_ms=actual_duration_ms,
        )

    async def get_optimization_stats(
        self,
        window_hours: int = 168,
    ) -> Dict[str, Any]:
        """Get optimization effectiveness statistics."""
        return await self._context_optimizer.get_optimization_stats(window_hours)

    async def save_optimization(self, optimization: OptimizedTask) -> None:
        """Save an optimization record for tracking."""
        await self._context_optimizer.save_optimization(optimization)

    # --- Orchestration ---

    async def run_predictive_cycle(
        self,
        horizon_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Run a complete predictive intelligence cycle (Phase 9).

        Includes demand forecasting, scaling recommendations,
        and anomaly detection.

        Args:
            horizon_hours: Forecast horizon

        Returns:
            Summary of predictions and recommendations
        """
        results: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "forecast": {},
            "anomalies": [],
            "optimization_stats": {},
        }

        # Generate demand forecast
        forecast = await self.forecast_demand(horizon_hours=horizon_hours)
        await self.save_demand_forecast(forecast)
        results["forecast"] = {
            "expected_volume": forecast.expected_volume,
            "horizon_hours": forecast.horizon_hours,
            "scaling_action": forecast.recommended_scaling.action.value,
            "scaling_urgency": forecast.recommended_scaling.urgency,
            "confidence_lower": forecast.confidence_interval.lower,
            "confidence_upper": forecast.confidence_interval.upper,
            "trend": forecast.trend.direction.value if forecast.trend else None,
            "seasonality": (
                forecast.seasonality.seasonality_type.value if forecast.seasonality else None
            ),
        }

        # Detect anomalies
        anomalies = await self.get_demand_anomalies(hours=horizon_hours)
        results["anomalies"] = anomalies

        # Get optimization stats
        opt_stats = await self.get_optimization_stats(window_hours=168)
        results["optimization_stats"] = opt_stats

        # Get cascade accuracy
        cascade_accuracy = await self.get_cascade_accuracy(window_hours=168)
        results["cascade_accuracy"] = cascade_accuracy

        return results

    # --- Stats ---

    async def get_stats(self) -> Dict[str, Any]:
        """Get intelligence facade statistics."""
        return {
            "demand_forecaster": (
                await self._demand_forecaster.get_stats()
                if hasattr(self._demand_forecaster, "get_stats")
                else {}
            ),
            "cascade_predictor": (
                await self._cascade_predictor.get_stats()
                if hasattr(self._cascade_predictor, "get_stats")
                else {}
            ),
            "context_optimizer": await self._context_optimizer.get_optimization_stats(168),
        }

    # --- Accessors for components (used by orchestrator) ---

    @property
    def demand_forecaster(self) -> DemandForecaster:
        """Get demand forecaster."""
        return self._demand_forecaster

    @property
    def cascade_predictor(self) -> CascadePredictor:
        """Get cascade predictor."""
        return self._cascade_predictor

    @property
    def context_optimizer(self) -> ContextOptimizer:
        """Get context optimizer."""
        return self._context_optimizer
