"""
Experimentation Facade - Pattern experiments, meta-learning, and handler generation.

This facade manages self-improvement learning components:
- PatternExperimenter: A/B testing for pattern effectiveness
- MetaLearner: Self-tuning of learning parameters
- HandlerGenerator: Automatic handler generation for repetitive tasks
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ag3ntwerk.learning.handler_generator import (
    HandlerGenerator,
    GeneratedHandler,
    HandlerStatus,
)
from ag3ntwerk.learning.meta_learner import MetaLearner, EffectivenessMetrics
from ag3ntwerk.learning.pattern_experiment import (
    PatternExperimenter,
    PatternExperiment,
    ExperimentResult,
    ExperimentStatus,
)
from ag3ntwerk.learning.pattern_store import PatternStore

logger = logging.getLogger(__name__)


class ExperimentationFacade:
    """
    Facade for self-improvement learning operations.

    Manages pattern experiments, meta-learning parameter tuning,
    and automatic handler generation.
    """

    def __init__(
        self,
        db: Any,
        pattern_store: PatternStore,
    ):
        """
        Initialize the experimentation facade.

        Args:
            db: Database connection
            pattern_store: Shared pattern store instance
        """
        self._db = db
        self._pattern_store = pattern_store
        self._pattern_experimenter = PatternExperimenter(db, pattern_store)
        self._meta_learner = MetaLearner(db)
        self._handler_generator = HandlerGenerator(db, pattern_store)

    # --- Pattern Experiments ---

    async def create_experiment(
        self,
        pattern_id: str,
        task_type: str,
        target_sample_size: int = 100,
        traffic_percentage: float = 0.5,
    ) -> PatternExperiment:
        """
        Create an A/B experiment for a pattern.

        Args:
            pattern_id: ID of the pattern to test
            task_type: Type of task for the experiment
            target_sample_size: Samples per group
            traffic_percentage: Fraction of traffic to treatment

        Returns:
            Created experiment
        """
        return await self._pattern_experimenter.create_experiment(
            pattern_id=pattern_id,
            task_type=task_type,
            target_sample_size=target_sample_size,
            traffic_percentage=traffic_percentage,
        )

    async def should_apply_pattern_in_experiment(
        self,
        pattern_id: str,
        task_type: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a pattern should be applied (for A/B testing).

        Args:
            pattern_id: Pattern ID
            task_type: Task type

        Returns:
            (should_apply, experiment_id)
        """
        return await self._pattern_experimenter.should_apply_pattern(
            pattern_id=pattern_id,
            task_type=task_type,
        )

    async def record_experiment_outcome(
        self,
        pattern_id: str,
        applied_pattern: bool,
        success: bool,
        duration_ms: float = 0.0,
        effectiveness: float = 0.0,
    ) -> Optional[ExperimentResult]:
        """
        Record outcome for an experiment.

        Args:
            pattern_id: Pattern ID
            applied_pattern: Whether pattern was applied
            success: Whether task succeeded
            duration_ms: Duration
            effectiveness: Effectiveness score

        Returns:
            ExperimentResult if experiment completed
        """
        return await self._pattern_experimenter.record_outcome(
            pattern_id=pattern_id,
            applied_pattern=applied_pattern,
            success=success,
            duration_ms=duration_ms,
            effectiveness=effectiveness,
        )

    async def get_active_experiments(self) -> List[PatternExperiment]:
        """Get all active experiments."""
        return await self._pattern_experimenter.list_active_experiments()

    async def get_experiment(self, pattern_id: str) -> Optional[PatternExperiment]:
        """Get experiment for a pattern."""
        return await self._pattern_experimenter.get_experiment(pattern_id)

    async def abort_experiment(
        self,
        pattern_id: str,
        reason: str = "",
    ) -> Optional[PatternExperiment]:
        """Abort an active experiment."""
        return await self._pattern_experimenter.abort_experiment(pattern_id, reason)

    async def get_patterns_needing_experiments(self) -> List[str]:
        """Find patterns that would benefit from experiments."""
        return await self._pattern_experimenter.get_patterns_needing_experiments()

    # --- Meta-Learning ---

    async def tune_parameters(self) -> List[Any]:
        """
        Run a meta-learner parameter tuning cycle.

        Returns:
            List of tuning results
        """
        return await self._meta_learner.tune_parameters()

    def get_meta_learner_parameter(self, name: str) -> Optional[float]:
        """Get a meta-learner parameter value."""
        return self._meta_learner.get_parameter(name)

    def get_all_meta_learner_parameters(self) -> Dict[str, float]:
        """Get all meta-learner parameter values."""
        return self._meta_learner.get_all_parameters()

    async def measure_effectiveness(
        self,
        window_hours: int = 24,
    ) -> EffectivenessMetrics:
        """
        Measure learning system effectiveness.

        Args:
            window_hours: Time window for metrics

        Returns:
            Effectiveness metrics
        """
        return await self._meta_learner.measure_effectiveness(window_hours)

    async def evaluate_recent_tuning(
        self,
        window_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Evaluate whether recent tuning was beneficial.

        Args:
            window_hours: How far back to look

        Returns:
            Evaluation summary
        """
        return await self._meta_learner.evaluate_recent_tuning(window_hours)

    async def get_meta_learner_stats(self) -> Dict[str, Any]:
        """Get meta-learner statistics."""
        return await self._meta_learner.get_stats()

    # --- Handler Generation ---

    async def analyze_for_handler_generation(
        self,
        task_type: str,
    ) -> Optional[Any]:
        """
        Analyze a task type for potential handler generation.

        Args:
            task_type: Task type to analyze

        Returns:
            HandlerCandidate if viable
        """
        return await self._handler_generator.analyze_task_type(task_type)

    async def generate_handler(
        self,
        task_type: str,
    ) -> Optional[GeneratedHandler]:
        """
        Generate a handler for a task type.

        Args:
            task_type: Task type

        Returns:
            Generated handler if successful
        """
        candidate = await self._handler_generator.analyze_task_type(task_type)
        if not candidate:
            return None
        return await self._handler_generator.generate_handler(candidate)

    async def get_handler_for_task(
        self,
        task_type: str,
    ) -> Optional[GeneratedHandler]:
        """Get an active handler for a task type."""
        return await self._handler_generator.get_handler_for_task(task_type)

    async def record_handler_usage(
        self,
        handler_id: str,
        success: bool,
        duration_ms: float = 0.0,
    ) -> None:
        """Record usage of a generated handler."""
        await self._handler_generator.record_handler_usage(
            handler_id=handler_id,
            success=success,
            duration_ms=duration_ms,
        )

    async def activate_handler(self, handler_id: str) -> bool:
        """Activate a handler for testing."""
        return await self._handler_generator.activate_handler(handler_id)

    async def deprecate_handler(
        self,
        handler_id: str,
        reason: str = "",
    ) -> bool:
        """Deprecate a handler."""
        return await self._handler_generator.deprecate_handler(handler_id, reason)

    async def get_all_handlers(self) -> List[GeneratedHandler]:
        """Get all generated handlers."""
        return await self._handler_generator.get_all_handlers()

    async def get_handler(self, handler_id: str) -> Optional[GeneratedHandler]:
        """Get a specific handler."""
        return await self._handler_generator.get_handler(handler_id)

    async def find_handler_generation_candidates(self) -> List[str]:
        """Find task types that could have handlers generated."""
        return await self._handler_generator.find_generation_candidates()

    # --- Stats ---

    async def get_stats(self) -> Dict[str, Any]:
        """Get experimentation facade statistics."""
        return {
            "pattern_experimenter": (
                await self._pattern_experimenter.get_stats()
                if hasattr(self._pattern_experimenter, "get_stats")
                else {}
            ),
            "meta_learner": await self._meta_learner.get_stats(),
            "handler_generator": (
                await self._handler_generator.get_stats()
                if hasattr(self._handler_generator, "get_stats")
                else {}
            ),
        }

    # --- Accessors for components (used by orchestrator) ---

    @property
    def pattern_experimenter(self) -> PatternExperimenter:
        """Get pattern experimenter."""
        return self._pattern_experimenter

    @property
    def meta_learner(self) -> MetaLearner:
        """Get meta learner."""
        return self._meta_learner

    @property
    def handler_generator(self) -> HandlerGenerator:
        """Get handler generator."""
        return self._handler_generator
