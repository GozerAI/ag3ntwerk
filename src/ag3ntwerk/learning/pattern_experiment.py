"""
Pattern Experiment - A/B Testing for learned patterns.

Enables controlled experiments to measure whether patterns actually improve outcomes:
1. Splits traffic between pattern-applied and control groups
2. Measures success rate, duration, and effectiveness differences
3. Calculates statistical significance of improvements
4. Auto-promotes or demotes patterns based on results
"""

import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    """Status of an experiment."""

    PENDING = "pending"  # Not yet started
    RUNNING = "running"  # Actively collecting data
    COMPLETED = "completed"  # Finished with conclusion
    ABORTED = "aborted"  # Stopped early


class ExperimentConclusion(Enum):
    """Conclusion of a completed experiment."""

    POSITIVE = "positive"  # Pattern significantly improves outcomes
    NEGATIVE = "negative"  # Pattern significantly worsens outcomes
    NEUTRAL = "neutral"  # No significant difference
    INCONCLUSIVE = "inconclusive"  # Not enough data


@dataclass
class ExperimentGroup:
    """Statistics for one group (treatment or control) in an experiment."""

    name: str  # "treatment" or "control"

    # Sample counts
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0

    # Metrics
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    avg_effectiveness: float = 0.0
    total_duration_ms: float = 0.0
    total_effectiveness: float = 0.0

    def record_outcome(
        self,
        success: bool,
        duration_ms: float = 0.0,
        effectiveness: float = 0.0,
    ) -> None:
        """Record an outcome for this group."""
        self.total_tasks += 1
        if success:
            self.successful_tasks += 1
        else:
            self.failed_tasks += 1

        self.total_duration_ms += duration_ms
        self.total_effectiveness += effectiveness

        # Update averages
        self.success_rate = self.successful_tasks / self.total_tasks
        self.avg_duration_ms = self.total_duration_ms / self.total_tasks
        self.avg_effectiveness = self.total_effectiveness / self.total_tasks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "avg_effectiveness": self.avg_effectiveness,
        }


@dataclass
class ExperimentResult:
    """Result of a completed experiment."""

    experiment_id: str
    pattern_id: str

    # Groups
    treatment: ExperimentGroup
    control: ExperimentGroup

    # Statistical analysis
    success_rate_diff: float = 0.0  # Treatment - Control
    duration_diff_ms: float = 0.0
    effectiveness_diff: float = 0.0

    # Statistical significance
    p_value: Optional[float] = None
    is_significant: bool = False
    confidence_level: float = 0.95  # 95% confidence

    # Conclusion
    conclusion: ExperimentConclusion = ExperimentConclusion.INCONCLUSIVE
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "pattern_id": self.pattern_id,
            "treatment": self.treatment.to_dict(),
            "control": self.control.to_dict(),
            "success_rate_diff": self.success_rate_diff,
            "duration_diff_ms": self.duration_diff_ms,
            "effectiveness_diff": self.effectiveness_diff,
            "p_value": self.p_value,
            "is_significant": self.is_significant,
            "conclusion": self.conclusion.value,
            "recommendation": self.recommendation,
        }


@dataclass
class PatternExperiment:
    """An A/B test experiment for a pattern."""

    id: str = field(default_factory=lambda: str(uuid4()))
    pattern_id: str = ""
    pattern_type: str = ""  # routing, confidence, etc.

    # Configuration
    task_type: str = ""
    target_sample_size: int = 100  # Per group
    traffic_percentage: float = 0.5  # Fraction of traffic to treatment

    # Groups
    treatment: ExperimentGroup = field(default_factory=lambda: ExperimentGroup(name="treatment"))
    control: ExperimentGroup = field(default_factory=lambda: ExperimentGroup(name="control"))

    # Status
    status: ExperimentStatus = ExperimentStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    result: Optional[ExperimentResult] = None

    def should_apply_pattern(self) -> bool:
        """
        Determine whether to apply the pattern for a new task.

        Uses random assignment based on traffic_percentage.
        """
        if self.status != ExperimentStatus.RUNNING:
            return False
        return random.random() < self.traffic_percentage

    def record_outcome(
        self,
        applied_pattern: bool,
        success: bool,
        duration_ms: float = 0.0,
        effectiveness: float = 0.0,
    ) -> None:
        """Record the outcome of a task in the experiment."""
        if self.status != ExperimentStatus.RUNNING:
            return

        if applied_pattern:
            self.treatment.record_outcome(success, duration_ms, effectiveness)
        else:
            self.control.record_outcome(success, duration_ms, effectiveness)

        # Check if experiment should complete
        if self._should_complete():
            self._complete_experiment()

    def _should_complete(self) -> bool:
        """Check if the experiment has enough data to complete."""
        return (
            self.treatment.total_tasks >= self.target_sample_size
            and self.control.total_tasks >= self.target_sample_size
        )

    def _complete_experiment(self) -> None:
        """Complete the experiment and calculate results."""
        self.status = ExperimentStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

        # Calculate result
        self.result = self._calculate_result()

    def _calculate_result(self) -> ExperimentResult:
        """Calculate the experiment result with statistical analysis."""
        result = ExperimentResult(
            experiment_id=self.id,
            pattern_id=self.pattern_id,
            treatment=self.treatment,
            control=self.control,
        )

        # Calculate differences
        result.success_rate_diff = self.treatment.success_rate - self.control.success_rate
        result.duration_diff_ms = self.treatment.avg_duration_ms - self.control.avg_duration_ms
        result.effectiveness_diff = (
            self.treatment.avg_effectiveness - self.control.avg_effectiveness
        )

        # Calculate statistical significance using two-proportion z-test
        result.p_value = self._calculate_p_value()
        result.is_significant = result.p_value is not None and result.p_value < (
            1 - result.confidence_level
        )

        # Determine conclusion
        result.conclusion = self._determine_conclusion(result)
        result.recommendation = self._generate_recommendation(result)

        return result

    def _calculate_p_value(self) -> Optional[float]:
        """
        Calculate p-value using two-proportion z-test.

        Tests whether the difference in success rates is statistically significant.
        """
        n1 = self.treatment.total_tasks
        n2 = self.control.total_tasks

        if n1 < 10 or n2 < 10:
            return None  # Not enough samples

        p1 = self.treatment.success_rate
        p2 = self.control.success_rate

        # Pooled proportion
        p_pool = (self.treatment.successful_tasks + self.control.successful_tasks) / (n1 + n2)

        if p_pool == 0 or p_pool == 1:
            return None  # Cannot calculate

        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))

        if se == 0:
            return None

        # Z-score
        z = (p1 - p2) / se

        # Two-tailed p-value (using normal approximation)
        # Using standard normal CDF approximation
        p_value = 2 * (1 - self._normal_cdf(abs(z)))

        return p_value

    @staticmethod
    def _normal_cdf(x: float) -> float:
        """Approximate the standard normal CDF."""
        # Approximation using error function
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _determine_conclusion(self, result: ExperimentResult) -> ExperimentConclusion:
        """Determine the conclusion based on results."""
        if not result.is_significant:
            if result.p_value is None:
                return ExperimentConclusion.INCONCLUSIVE
            return ExperimentConclusion.NEUTRAL

        # Significant result - check direction
        if result.success_rate_diff > 0.05:  # 5% improvement threshold
            return ExperimentConclusion.POSITIVE
        elif result.success_rate_diff < -0.05:  # 5% degradation threshold
            return ExperimentConclusion.NEGATIVE
        else:
            return ExperimentConclusion.NEUTRAL

    def _generate_recommendation(self, result: ExperimentResult) -> str:
        """Generate a recommendation based on results."""
        if result.conclusion == ExperimentConclusion.POSITIVE:
            return (
                f"PROMOTE: Pattern improves success rate by "
                f"{result.success_rate_diff:.1%} (p={result.p_value:.4f})"
            )
        elif result.conclusion == ExperimentConclusion.NEGATIVE:
            return (
                f"DEMOTE: Pattern decreases success rate by "
                f"{abs(result.success_rate_diff):.1%} (p={result.p_value:.4f})"
            )
        elif result.conclusion == ExperimentConclusion.NEUTRAL:
            return (
                f"KEEP: Pattern shows no significant impact "
                f"(diff={result.success_rate_diff:.1%}, p={result.p_value:.4f})"
            )
        else:
            return "CONTINUE: Need more data for conclusive results"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "task_type": self.task_type,
            "target_sample_size": self.target_sample_size,
            "traffic_percentage": self.traffic_percentage,
            "treatment": self.treatment.to_dict(),
            "control": self.control.to_dict(),
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result.to_dict() if self.result else None,
        }


class PatternExperimenter:
    """
    Manages A/B experiments for patterns.

    Responsibilities:
    - Create and run experiments for patterns
    - Assign tasks to treatment/control groups
    - Track outcomes and calculate results
    - Auto-update pattern confidence based on results
    """

    # Minimum improvement to promote a pattern
    MIN_IMPROVEMENT_THRESHOLD = 0.05  # 5%

    # Maximum degradation before demoting
    MAX_DEGRADATION_THRESHOLD = -0.03  # 3%

    # Confidence adjustment based on experiment results
    CONFIDENCE_BOOST = 0.1  # Add to confidence on positive result
    CONFIDENCE_PENALTY = 0.15  # Subtract from confidence on negative result

    def __init__(self, db: Any, pattern_store: Any):
        """
        Initialize the pattern experimenter.

        Args:
            db: Database connection
            pattern_store: PatternStore for updating patterns
        """
        self._db = db
        self._pattern_store = pattern_store

        # Active experiments by pattern_id
        self._experiments: Dict[str, PatternExperiment] = {}

        # Completed experiment results
        self._completed: List[ExperimentResult] = []

    async def create_experiment(
        self,
        pattern_id: str,
        task_type: str,
        pattern_type: str = "routing",
        target_sample_size: int = 100,
        traffic_percentage: float = 0.5,
    ) -> PatternExperiment:
        """
        Create a new experiment for a pattern.

        Args:
            pattern_id: ID of the pattern to test
            task_type: Type of task to run the experiment on
            pattern_type: Type of pattern (routing, confidence, etc.)
            target_sample_size: Number of samples per group
            traffic_percentage: Fraction of traffic to treatment

        Returns:
            The created experiment
        """
        experiment = PatternExperiment(
            pattern_id=pattern_id,
            task_type=task_type,
            pattern_type=pattern_type,
            target_sample_size=target_sample_size,
            traffic_percentage=traffic_percentage,
            status=ExperimentStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        self._experiments[pattern_id] = experiment

        # Persist to database
        await self._save_experiment(experiment)

        logger.info(
            f"Created experiment {experiment.id} for pattern {pattern_id} "
            f"(target: {target_sample_size} samples per group)"
        )

        return experiment

    async def should_apply_pattern(
        self,
        pattern_id: str,
        task_type: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine whether to apply a pattern for a task.

        Args:
            pattern_id: ID of the pattern
            task_type: Type of the task

        Returns:
            (should_apply, experiment_id) - whether to apply and which experiment
        """
        experiment = self._experiments.get(pattern_id)

        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            # No active experiment - apply pattern normally
            return True, None

        if experiment.task_type != task_type:
            # Experiment is for different task type
            return True, None

        # Use experiment's randomization
        should_apply = experiment.should_apply_pattern()
        return should_apply, experiment.id

    async def record_outcome(
        self,
        pattern_id: str,
        applied_pattern: bool,
        success: bool,
        duration_ms: float = 0.0,
        effectiveness: float = 0.0,
    ) -> Optional[ExperimentResult]:
        """
        Record the outcome of a task in an experiment.

        Args:
            pattern_id: ID of the pattern
            applied_pattern: Whether the pattern was applied
            success: Whether the task succeeded
            duration_ms: Task duration
            effectiveness: Effectiveness score

        Returns:
            ExperimentResult if experiment completed, None otherwise
        """
        experiment = self._experiments.get(pattern_id)

        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return None

        # Record outcome
        experiment.record_outcome(applied_pattern, success, duration_ms, effectiveness)

        # Check if completed
        if experiment.status == ExperimentStatus.COMPLETED:
            result = experiment.result

            # Apply result to pattern
            if result:
                await self._apply_experiment_result(result)
                self._completed.append(result)

            # Remove from active experiments
            del self._experiments[pattern_id]

            # Persist final state
            await self._save_experiment(experiment)

            logger.info(
                f"Experiment {experiment.id} completed: {result.conclusion.value} "
                f"({result.recommendation})"
            )

            return result

        # Persist progress periodically
        if (experiment.treatment.total_tasks + experiment.control.total_tasks) % 10 == 0:
            await self._save_experiment(experiment)

        return None

    async def get_experiment(self, pattern_id: str) -> Optional[PatternExperiment]:
        """Get the active experiment for a pattern."""
        return self._experiments.get(pattern_id)

    async def get_experiment_by_id(
        self,
        experiment_id: str,
    ) -> Optional[PatternExperiment]:
        """Get an experiment by its ID."""
        for experiment in self._experiments.values():
            if experiment.id == experiment_id:
                return experiment
        return None

    async def list_active_experiments(self) -> List[PatternExperiment]:
        """List all active experiments."""
        return [exp for exp in self._experiments.values() if exp.status == ExperimentStatus.RUNNING]

    async def get_completed_results(
        self,
        limit: int = 100,
    ) -> List[ExperimentResult]:
        """Get recently completed experiment results."""
        return self._completed[-limit:]

    async def abort_experiment(
        self,
        pattern_id: str,
        reason: str = "",
    ) -> Optional[PatternExperiment]:
        """
        Abort an active experiment.

        Args:
            pattern_id: ID of the pattern
            reason: Reason for aborting

        Returns:
            The aborted experiment or None
        """
        experiment = self._experiments.get(pattern_id)

        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return None

        experiment.status = ExperimentStatus.ABORTED
        experiment.completed_at = datetime.now(timezone.utc)

        del self._experiments[pattern_id]
        await self._save_experiment(experiment)

        logger.info(f"Aborted experiment {experiment.id}: {reason}")

        return experiment

    async def _conclude_experiment(
        self,
        experiment: PatternExperiment,
    ) -> Optional[ExperimentResult]:
        """
        Conclude an active experiment by analyzing its collected outcomes.

        Marks the experiment as completed, calculates the statistical result,
        applies the result to the pattern's confidence, and persists the
        final state.

        Args:
            experiment: The experiment to conclude

        Returns:
            ExperimentResult if successfully concluded, None otherwise
        """
        if experiment.status != ExperimentStatus.RUNNING:
            return None

        # Complete the experiment (sets status, calculates result)
        experiment._complete_experiment()

        result = experiment.result

        # Apply result to pattern confidence
        if result:
            await self._apply_experiment_result(result)
            self._completed.append(result)

        # Remove from active experiments
        if experiment.pattern_id in self._experiments:
            del self._experiments[experiment.pattern_id]

        # Persist final state
        await self._save_experiment(experiment)

        logger.info(
            f"Concluded experiment {experiment.id}: "
            f"{result.conclusion.value if result else 'no result'}"
            f"{' (' + result.recommendation + ')' if result else ''}"
        )

        return result

    async def get_patterns_needing_experiments(
        self,
        min_applications: int = 20,
        max_confidence_gap: float = 0.3,
    ) -> List[str]:
        """
        Find patterns that would benefit from experiments.

        Patterns are candidates if:
        - Applied enough times to have meaningful data
        - Confidence is not already very high or very low
        - No active experiment running

        Args:
            min_applications: Minimum applications to consider
            max_confidence_gap: Max distance from 0.5 to consider

        Returns:
            List of pattern IDs that need experiments
        """
        try:
            rows = await self._db.fetch_all(
                """
                SELECT id, confidence, application_count
                FROM learned_patterns
                WHERE is_active = 1
                AND application_count >= ?
                AND confidence > ?
                AND confidence < ?
                """,
                (min_applications, 0.5 - max_confidence_gap, 0.5 + max_confidence_gap),
            )

            candidates = []
            for row in rows:
                pattern_id = row["id"]
                if pattern_id not in self._experiments:
                    candidates.append(pattern_id)

            return candidates

        except Exception as e:
            logger.warning(f"Failed to find patterns needing experiments: {e}")
            return []

    async def _apply_experiment_result(self, result: ExperimentResult) -> None:
        """Apply experiment result to pattern confidence."""
        try:
            # Get current pattern
            pattern = await self._pattern_store.get_pattern(result.pattern_id)
            if not pattern:
                return

            # Adjust confidence based on conclusion
            if result.conclusion == ExperimentConclusion.POSITIVE:
                new_confidence = min(1.0, pattern.confidence + self.CONFIDENCE_BOOST)
                logger.info(
                    f"Boosting pattern {result.pattern_id} confidence: "
                    f"{pattern.confidence:.2f} -> {new_confidence:.2f}"
                )
            elif result.conclusion == ExperimentConclusion.NEGATIVE:
                new_confidence = max(0.0, pattern.confidence - self.CONFIDENCE_PENALTY)
                logger.info(
                    f"Reducing pattern {result.pattern_id} confidence: "
                    f"{pattern.confidence:.2f} -> {new_confidence:.2f}"
                )

                # Deactivate if confidence drops too low
                if new_confidence < 0.2:
                    await self._pattern_store.deactivate_pattern(
                        result.pattern_id,
                        reason=f"Experiment showed negative impact: {result.recommendation}",
                    )
                    return
            else:
                # Neutral or inconclusive - no change
                return

            # Update pattern confidence
            await self._pattern_store.update_pattern_confidence(
                result.pattern_id,
                new_confidence,
            )

        except Exception as e:
            logger.error(f"Failed to apply experiment result: {e}")

    async def _save_experiment(self, experiment: PatternExperiment) -> None:
        """Save experiment state to database."""
        import json

        try:
            await self._db.execute(
                """
                INSERT OR REPLACE INTO pattern_experiments (
                    id, pattern_id, pattern_type, task_type,
                    target_sample_size, traffic_percentage,
                    treatment_json, control_json,
                    status, started_at, completed_at,
                    result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    experiment.id,
                    experiment.pattern_id,
                    experiment.pattern_type,
                    experiment.task_type,
                    experiment.target_sample_size,
                    experiment.traffic_percentage,
                    json.dumps(experiment.treatment.to_dict()),
                    json.dumps(experiment.control.to_dict()),
                    experiment.status.value,
                    experiment.started_at.isoformat() if experiment.started_at else None,
                    experiment.completed_at.isoformat() if experiment.completed_at else None,
                    json.dumps(experiment.result.to_dict()) if experiment.result else None,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to save experiment: {e}")

    async def load_active_experiments(self) -> int:
        """
        Load active experiments from database.

        Returns:
            Number of experiments loaded
        """
        import json

        try:
            rows = await self._db.fetch_all(
                """
                SELECT * FROM pattern_experiments
                WHERE status = 'running'
                """
            )

            self._experiments.clear()

            for row in rows:
                treatment_data = json.loads(row["treatment_json"])
                control_data = json.loads(row["control_json"])

                treatment = ExperimentGroup(name="treatment")
                treatment.total_tasks = treatment_data.get("total_tasks", 0)
                treatment.successful_tasks = treatment_data.get("successful_tasks", 0)
                treatment.failed_tasks = treatment_data.get("failed_tasks", 0)
                treatment.success_rate = treatment_data.get("success_rate", 0.0)
                treatment.avg_duration_ms = treatment_data.get("avg_duration_ms", 0.0)
                treatment.avg_effectiveness = treatment_data.get("avg_effectiveness", 0.0)

                control = ExperimentGroup(name="control")
                control.total_tasks = control_data.get("total_tasks", 0)
                control.successful_tasks = control_data.get("successful_tasks", 0)
                control.failed_tasks = control_data.get("failed_tasks", 0)
                control.success_rate = control_data.get("success_rate", 0.0)
                control.avg_duration_ms = control_data.get("avg_duration_ms", 0.0)
                control.avg_effectiveness = control_data.get("avg_effectiveness", 0.0)

                experiment = PatternExperiment(
                    id=row["id"],
                    pattern_id=row["pattern_id"],
                    pattern_type=row["pattern_type"],
                    task_type=row["task_type"],
                    target_sample_size=row["target_sample_size"],
                    traffic_percentage=row["traffic_percentage"],
                    treatment=treatment,
                    control=control,
                    status=ExperimentStatus(row["status"]),
                    started_at=(
                        datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
                    ),
                )

                self._experiments[experiment.pattern_id] = experiment

            logger.info(f"Loaded {len(self._experiments)} active experiments")
            return len(self._experiments)

        except Exception as e:
            logger.warning(f"Failed to load experiments: {e}")
            return 0
