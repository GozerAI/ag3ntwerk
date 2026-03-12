"""
Meta-Learner - Self-tuning system parameters.

Automatically tunes the learning system's own parameters:
1. Analysis intervals and thresholds
2. Pattern detection sensitivity
3. Confidence thresholds for routing decisions
4. Risk assessment weights
5. Load balancing weights

Uses a feedback loop to measure learning effectiveness and adjust parameters.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ParameterCategory(Enum):
    """Categories of tunable parameters."""

    ANALYSIS = "analysis"
    ROUTING = "routing"
    PREDICTION = "prediction"
    LOAD_BALANCING = "load_balancing"
    EXPERIMENTATION = "experimentation"


@dataclass
class TunableParameter:
    """A parameter that can be tuned by the meta-learner."""

    name: str
    category: ParameterCategory
    current_value: float
    min_value: float
    max_value: float
    step_size: float
    description: str = ""

    # Performance tracking
    last_tuned: Optional[datetime] = None
    tune_count: int = 0

    def propose_increase(self) -> float:
        """Propose an increased value."""
        return min(self.max_value, self.current_value + self.step_size)

    def propose_decrease(self) -> float:
        """Propose a decreased value."""
        return max(self.min_value, self.current_value - self.step_size)

    def update(self, new_value: float) -> None:
        """Update the parameter value."""
        self.current_value = max(self.min_value, min(self.max_value, new_value))
        self.last_tuned = datetime.now(timezone.utc)
        self.tune_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "current_value": self.current_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "step_size": self.step_size,
            "description": self.description,
            "last_tuned": self.last_tuned.isoformat() if self.last_tuned else None,
            "tune_count": self.tune_count,
        }


@dataclass
class EffectivenessMetrics:
    """Metrics measuring learning system effectiveness."""

    # Pattern effectiveness
    patterns_created: int = 0
    patterns_applied: int = 0
    pattern_success_rate: float = 0.0

    # Routing effectiveness
    dynamic_routing_decisions: int = 0
    dynamic_routing_success_rate: float = 0.0
    static_fallback_rate: float = 0.0

    # Prediction effectiveness
    predictions_made: int = 0
    prediction_accuracy: float = 0.0
    high_risk_correctly_identified: float = 0.0

    # Load balancing effectiveness
    load_balance_decisions: int = 0
    load_variance: float = 0.0  # Lower is better

    # Issue detection
    issues_created: int = 0
    issues_resolved: int = 0
    false_positive_rate: float = 0.0

    # Overall
    overall_task_success_rate: float = 0.0
    avg_task_duration_ms: float = 0.0

    def calculate_score(self) -> float:
        """Calculate an overall effectiveness score (0-1)."""
        weights = {
            "pattern_success": 0.2,
            "routing_success": 0.2,
            "prediction_accuracy": 0.2,
            "load_balance": 0.1,
            "issue_detection": 0.1,
            "overall_success": 0.2,
        }

        score = 0.0
        score += weights["pattern_success"] * self.pattern_success_rate
        score += weights["routing_success"] * self.dynamic_routing_success_rate
        score += weights["prediction_accuracy"] * self.prediction_accuracy
        score += weights["load_balance"] * (1.0 - min(1.0, self.load_variance))
        score += weights["issue_detection"] * (1.0 - self.false_positive_rate)
        score += weights["overall_success"] * self.overall_task_success_rate

        return score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patterns_created": self.patterns_created,
            "patterns_applied": self.patterns_applied,
            "pattern_success_rate": self.pattern_success_rate,
            "dynamic_routing_decisions": self.dynamic_routing_decisions,
            "dynamic_routing_success_rate": self.dynamic_routing_success_rate,
            "static_fallback_rate": self.static_fallback_rate,
            "predictions_made": self.predictions_made,
            "prediction_accuracy": self.prediction_accuracy,
            "load_balance_decisions": self.load_balance_decisions,
            "load_variance": self.load_variance,
            "issues_created": self.issues_created,
            "issues_resolved": self.issues_resolved,
            "overall_task_success_rate": self.overall_task_success_rate,
            "avg_task_duration_ms": self.avg_task_duration_ms,
            "overall_score": self.calculate_score(),
        }


@dataclass
class TuningResult:
    """Result of a parameter tuning cycle."""

    timestamp: datetime
    parameter_name: str
    old_value: float
    new_value: float
    reason: str
    effectiveness_before: float
    effectiveness_after: Optional[float] = None
    was_beneficial: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "parameter_name": self.parameter_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "effectiveness_before": self.effectiveness_before,
            "effectiveness_after": self.effectiveness_after,
            "was_beneficial": self.was_beneficial,
        }


class MetaLearner:
    """
    Self-tuning component for the learning system.

    Monitors learning effectiveness and adjusts parameters to improve performance.
    """

    # Default parameters with their ranges
    DEFAULT_PARAMETERS = {
        # Analysis parameters
        "analysis_interval_seconds": {
            "category": ParameterCategory.ANALYSIS,
            "default": 60.0,
            "min": 10.0,
            "max": 300.0,
            "step": 10.0,
            "description": "Interval between analysis cycles",
        },
        "min_outcomes_for_analysis": {
            "category": ParameterCategory.ANALYSIS,
            "default": 5.0,
            "min": 2.0,
            "max": 20.0,
            "step": 1.0,
            "description": "Minimum outcomes before running analysis",
        },
        "pattern_detection_threshold": {
            "category": ParameterCategory.ANALYSIS,
            "default": 0.7,
            "min": 0.5,
            "max": 0.95,
            "step": 0.05,
            "description": "Confidence threshold for creating patterns",
        },
        # Routing parameters
        "min_confidence_for_override": {
            "category": ParameterCategory.ROUTING,
            "default": 0.6,
            "min": 0.3,
            "max": 0.9,
            "step": 0.05,
            "description": "Minimum confidence to override static routing",
        },
        "routing_pattern_weight": {
            "category": ParameterCategory.ROUTING,
            "default": 0.35,
            "min": 0.1,
            "max": 0.6,
            "step": 0.05,
            "description": "Weight of patterns in routing decisions",
        },
        "routing_performance_weight": {
            "category": ParameterCategory.ROUTING,
            "default": 0.30,
            "min": 0.1,
            "max": 0.5,
            "step": 0.05,
            "description": "Weight of performance in routing decisions",
        },
        # Prediction parameters
        "risk_error_pattern_weight": {
            "category": ParameterCategory.PREDICTION,
            "default": 0.35,
            "min": 0.1,
            "max": 0.6,
            "step": 0.05,
            "description": "Weight of error patterns in risk prediction",
        },
        "risk_agent_health_weight": {
            "category": ParameterCategory.PREDICTION,
            "default": 0.30,
            "min": 0.1,
            "max": 0.5,
            "step": 0.05,
            "description": "Weight of agent health in risk prediction",
        },
        "high_risk_threshold": {
            "category": ParameterCategory.PREDICTION,
            "default": 0.5,
            "min": 0.3,
            "max": 0.8,
            "step": 0.05,
            "description": "Threshold for high risk classification",
        },
        # Load balancing parameters
        "lb_capacity_weight": {
            "category": ParameterCategory.LOAD_BALANCING,
            "default": 0.30,
            "min": 0.1,
            "max": 0.5,
            "step": 0.05,
            "description": "Weight of capacity in load balancing",
        },
        "lb_success_rate_weight": {
            "category": ParameterCategory.LOAD_BALANCING,
            "default": 0.25,
            "min": 0.1,
            "max": 0.4,
            "step": 0.05,
            "description": "Weight of success rate in load balancing",
        },
        "overload_threshold": {
            "category": ParameterCategory.LOAD_BALANCING,
            "default": 0.9,
            "min": 0.7,
            "max": 0.95,
            "step": 0.05,
            "description": "Utilization threshold for overload",
        },
        # Experimentation parameters
        "experiment_sample_size": {
            "category": ParameterCategory.EXPERIMENTATION,
            "default": 100.0,
            "min": 30.0,
            "max": 500.0,
            "step": 20.0,
            "description": "Target sample size for experiments",
        },
        "experiment_traffic_percentage": {
            "category": ParameterCategory.EXPERIMENTATION,
            "default": 0.5,
            "min": 0.1,
            "max": 0.9,
            "step": 0.1,
            "description": "Traffic percentage for treatment group",
        },
    }

    # Minimum improvement to keep a parameter change
    MIN_IMPROVEMENT_THRESHOLD = 0.02  # 2% improvement

    # How long to wait between tuning the same parameter
    PARAMETER_COOLDOWN_HOURS = 24

    def __init__(self, db: Any):
        """
        Initialize the meta-learner.

        Args:
            db: Database connection
        """
        self._db = db

        # Initialize parameters
        self._parameters: Dict[str, TunableParameter] = {}
        self._initialize_parameters()

        # Tracking
        self._tuning_history: List[TuningResult] = []
        self._effectiveness_history: List[Tuple[datetime, EffectivenessMetrics]] = []

        # Current baseline
        self._baseline_effectiveness: Optional[float] = None

    def _initialize_parameters(self) -> None:
        """Initialize tunable parameters from defaults."""
        for name, config in self.DEFAULT_PARAMETERS.items():
            self._parameters[name] = TunableParameter(
                name=name,
                category=config["category"],
                current_value=config["default"],
                min_value=config["min"],
                max_value=config["max"],
                step_size=config["step"],
                description=config["description"],
            )

    def get_parameter(self, name: str) -> Optional[float]:
        """Get the current value of a parameter."""
        param = self._parameters.get(name)
        return param.current_value if param else None

    def get_all_parameters(self) -> Dict[str, float]:
        """Get all parameter values."""
        return {name: param.current_value for name, param in self._parameters.items()}

    def get_parameters_by_category(
        self,
        category: ParameterCategory,
    ) -> Dict[str, float]:
        """Get parameters for a specific category."""
        return {
            name: param.current_value
            for name, param in self._parameters.items()
            if param.category == category
        }

    async def measure_effectiveness(
        self,
        window_hours: int = 24,
    ) -> EffectivenessMetrics:
        """
        Measure current learning system effectiveness.

        Args:
            window_hours: Time window for metrics

        Returns:
            Effectiveness metrics
        """
        metrics = EffectivenessMetrics()
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        try:
            # Pattern metrics
            pattern_row = await self._db.fetch_one(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) as recent
                FROM learned_patterns
                WHERE is_active = 1
                """,
                (window_start.isoformat(),),
            )
            if pattern_row:
                metrics.patterns_created = pattern_row["recent"] or 0

            # Pattern application metrics
            app_row = await self._db.fetch_one(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome_success = 1 THEN 1 ELSE 0 END) as successful
                FROM pattern_applications
                WHERE applied_at >= ? AND outcome_recorded = 1
                """,
                (window_start.isoformat(),),
            )
            if app_row and app_row["total"] > 0:
                metrics.patterns_applied = app_row["total"]
                metrics.pattern_success_rate = app_row["successful"] / app_row["total"]

            # Overall task metrics
            outcome_row = await self._db.fetch_one(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    AVG(duration_ms) as avg_duration
                FROM learning_outcomes
                WHERE created_at >= ?
                """,
                (window_start.isoformat(),),
            )
            if outcome_row and outcome_row["total"] > 0:
                metrics.overall_task_success_rate = outcome_row["successful"] / outcome_row["total"]
                metrics.avg_task_duration_ms = outcome_row["avg_duration"] or 0.0

            # Issue metrics
            issue_row = await self._db.fetch_one(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved
                FROM learning_issues
                WHERE created_at >= ?
                """,
                (window_start.isoformat(),),
            )
            if issue_row:
                metrics.issues_created = issue_row["total"] or 0
                metrics.issues_resolved = issue_row["resolved"] or 0

        except Exception as e:
            logger.warning(f"Failed to measure effectiveness: {e}")

        # Store in history
        self._effectiveness_history.append((datetime.now(timezone.utc), metrics))

        # Keep only last 7 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        self._effectiveness_history = [
            (ts, m) for ts, m in self._effectiveness_history if ts > cutoff
        ]

        return metrics

    async def tune_parameters(self) -> List[TuningResult]:
        """
        Run a parameter tuning cycle.

        Analyzes effectiveness and proposes parameter adjustments.

        Returns:
            List of tuning results
        """
        results = []

        # Measure current effectiveness
        current_metrics = await self.measure_effectiveness()
        current_score = current_metrics.calculate_score()

        # Update baseline if not set
        if self._baseline_effectiveness is None:
            self._baseline_effectiveness = current_score

        # Find parameters that need tuning
        candidates = self._get_tuning_candidates()

        for param_name in candidates:
            param = self._parameters[param_name]

            # Determine direction based on effectiveness trend
            direction = self._determine_tuning_direction(param, current_metrics)

            if direction == 0:
                continue  # No change needed

            # Propose new value
            if direction > 0:
                new_value = param.propose_increase()
            else:
                new_value = param.propose_decrease()

            if new_value == param.current_value:
                continue  # Already at limit

            # Apply change
            old_value = param.current_value
            param.update(new_value)

            result = TuningResult(
                timestamp=datetime.now(timezone.utc),
                parameter_name=param_name,
                old_value=old_value,
                new_value=new_value,
                reason=self._get_tuning_reason(param, direction, current_metrics),
                effectiveness_before=current_score,
            )

            results.append(result)
            self._tuning_history.append(result)

            logger.info(f"Tuned {param_name}: {old_value} -> {new_value} " f"({result.reason})")

        # Persist parameters
        await self._save_parameters()

        return results

    def _get_tuning_candidates(self) -> List[str]:
        """Get parameters that are candidates for tuning."""
        candidates = []
        now = datetime.now(timezone.utc)
        cooldown = timedelta(hours=self.PARAMETER_COOLDOWN_HOURS)

        for name, param in self._parameters.items():
            # Skip if recently tuned
            if param.last_tuned and (now - param.last_tuned) < cooldown:
                continue

            candidates.append(name)

        return candidates

    def _determine_tuning_direction(
        self,
        param: TunableParameter,
        metrics: EffectivenessMetrics,
    ) -> int:
        """
        Determine which direction to tune a parameter.

        Returns:
            1 for increase, -1 for decrease, 0 for no change
        """
        # Category-specific logic
        if param.category == ParameterCategory.ANALYSIS:
            return self._tune_analysis_param(param, metrics)
        elif param.category == ParameterCategory.ROUTING:
            return self._tune_routing_param(param, metrics)
        elif param.category == ParameterCategory.PREDICTION:
            return self._tune_prediction_param(param, metrics)
        elif param.category == ParameterCategory.LOAD_BALANCING:
            return self._tune_load_balance_param(param, metrics)
        elif param.category == ParameterCategory.EXPERIMENTATION:
            return self._tune_experiment_param(param, metrics)

        return 0

    def _tune_analysis_param(
        self,
        param: TunableParameter,
        metrics: EffectivenessMetrics,
    ) -> int:
        """Tune analysis parameters."""
        if param.name == "analysis_interval_seconds":
            # If patterns are effective, keep interval; otherwise increase
            if metrics.pattern_success_rate > 0.8:
                return 0  # Working well
            elif metrics.patterns_created == 0:
                return 1  # Increase interval (less noise)
            return 0

        elif param.name == "min_outcomes_for_analysis":
            # If creating too many low-confidence patterns, increase threshold
            if metrics.pattern_success_rate < 0.5 and metrics.patterns_created > 5:
                return 1  # Need more data before patterns
            return 0

        elif param.name == "pattern_detection_threshold":
            # Balance between pattern creation and quality
            if metrics.pattern_success_rate < 0.6:
                return 1  # Be more selective
            elif metrics.patterns_created == 0 and param.current_value > 0.6:
                return -1  # Too selective, lower threshold
            return 0

        return 0

    def _tune_routing_param(
        self,
        param: TunableParameter,
        metrics: EffectivenessMetrics,
    ) -> int:
        """Tune routing parameters."""
        if param.name == "min_confidence_for_override":
            # If dynamic routing performs worse, increase threshold
            if metrics.dynamic_routing_success_rate < metrics.overall_task_success_rate:
                return 1  # Be more conservative
            elif metrics.static_fallback_rate > 0.7:
                return -1  # Using static too often, lower threshold
            return 0

        return 0

    def _tune_prediction_param(
        self,
        param: TunableParameter,
        metrics: EffectivenessMetrics,
    ) -> int:
        """Tune prediction parameters."""
        if param.name == "high_risk_threshold":
            # If predictions are too conservative (everything is high risk)
            if metrics.high_risk_correctly_identified < 0.5:
                return 1  # Raise threshold
            return 0

        return 0

    def _tune_load_balance_param(
        self,
        param: TunableParameter,
        metrics: EffectivenessMetrics,
    ) -> int:
        """Tune load balancing parameters."""
        if param.name == "overload_threshold":
            # If load is very uneven, lower threshold
            if metrics.load_variance > 0.3:
                return -1  # Be more aggressive about balancing
            return 0

        return 0

    def _tune_experiment_param(
        self,
        param: TunableParameter,
        metrics: EffectivenessMetrics,
    ) -> int:
        """Tune experimentation parameters."""
        # Generally keep experiment params stable
        return 0

    def _get_tuning_reason(
        self,
        param: TunableParameter,
        direction: int,
        metrics: EffectivenessMetrics,
    ) -> str:
        """Generate a human-readable reason for the tuning."""
        action = "increased" if direction > 0 else "decreased"

        if param.category == ParameterCategory.ANALYSIS:
            if param.name == "pattern_detection_threshold":
                rate = metrics.pattern_success_rate
                return f"{action} due to pattern success rate of {rate:.1%}"
            return f"{action} based on analysis effectiveness"

        elif param.category == ParameterCategory.ROUTING:
            rate = metrics.dynamic_routing_success_rate
            return f"{action} due to routing success rate of {rate:.1%}"

        elif param.category == ParameterCategory.PREDICTION:
            acc = metrics.prediction_accuracy
            return f"{action} due to prediction accuracy of {acc:.1%}"

        elif param.category == ParameterCategory.LOAD_BALANCING:
            var = metrics.load_variance
            return f"{action} due to load variance of {var:.2f}"

        return f"{action} based on effectiveness metrics"

    async def evaluate_recent_tuning(
        self,
        window_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Evaluate whether recent parameter tuning was beneficial.

        Args:
            window_hours: How far back to look

        Returns:
            Evaluation summary
        """
        # Get recent tuning results
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        recent_tuning = [r for r in self._tuning_history if r.timestamp > cutoff]

        if not recent_tuning:
            return {"message": "No recent tuning to evaluate"}

        # Measure current effectiveness
        current_metrics = await self.measure_effectiveness(window_hours=window_hours)
        current_score = current_metrics.calculate_score()

        # Update tuning results with outcomes
        beneficial_count = 0
        harmful_count = 0

        for result in recent_tuning:
            result.effectiveness_after = current_score
            improvement = current_score - result.effectiveness_before

            if improvement > self.MIN_IMPROVEMENT_THRESHOLD:
                result.was_beneficial = True
                beneficial_count += 1
            elif improvement < -self.MIN_IMPROVEMENT_THRESHOLD:
                result.was_beneficial = False
                harmful_count += 1
            else:
                result.was_beneficial = None  # Neutral

        # Revert harmful changes
        reverted = []
        for result in recent_tuning:
            if result.was_beneficial is False:
                param = self._parameters.get(result.parameter_name)
                if param:
                    param.update(result.old_value)
                    reverted.append(result.parameter_name)
                    logger.info(
                        f"Reverted {result.parameter_name}: "
                        f"{result.new_value} -> {result.old_value}"
                    )

        if reverted:
            await self._save_parameters()

        return {
            "tuning_evaluated": len(recent_tuning),
            "beneficial": beneficial_count,
            "harmful": harmful_count,
            "reverted": reverted,
            "current_effectiveness": current_score,
            "baseline_effectiveness": self._baseline_effectiveness,
        }

    async def get_stats(self) -> Dict[str, Any]:
        """Get meta-learner statistics."""
        return {
            "parameters": {name: param.to_dict() for name, param in self._parameters.items()},
            "tuning_history_count": len(self._tuning_history),
            "recent_tuning": [r.to_dict() for r in self._tuning_history[-10:]],
            "baseline_effectiveness": self._baseline_effectiveness,
            "effectiveness_samples": len(self._effectiveness_history),
        }

    async def _save_parameters(self) -> None:
        """Save parameter values to database."""
        import json

        try:
            params_json = json.dumps(
                {name: param.current_value for name, param in self._parameters.items()}
            )

            await self._db.execute(
                """
                INSERT OR REPLACE INTO meta_learner_state (
                    id, parameters_json, baseline_effectiveness, updated_at
                ) VALUES ('current', ?, ?, ?)
                """,
                (
                    params_json,
                    self._baseline_effectiveness,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to save parameters: {e}")

    async def load_parameters(self) -> int:
        """
        Load parameter values from database.

        Returns:
            Number of parameters loaded
        """
        import json

        try:
            row = await self._db.fetch_one("SELECT * FROM meta_learner_state WHERE id = 'current'")

            if not row:
                return 0

            params_data = json.loads(row["parameters_json"])
            loaded = 0

            for name, value in params_data.items():
                if name in self._parameters:
                    self._parameters[name].current_value = value
                    loaded += 1

            if row["baseline_effectiveness"]:
                self._baseline_effectiveness = row["baseline_effectiveness"]

            logger.info(f"Loaded {loaded} meta-learner parameters")
            return loaded

        except Exception as e:
            logger.warning(f"Failed to load parameters: {e}")
            return 0
