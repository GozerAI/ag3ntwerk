"""
Continuous Learning Pipeline - Never-ending learning cycle for autonomous intelligence.

Coordinates all learning components in a continuous loop:
1. Collect recent outcomes
2. Detect new patterns
3. Run experiments on promising patterns
4. Activate successful patterns
5. Tune system parameters
6. Generate proactive tasks
7. Clean up expired data
"""

import asyncio
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING
from enum import Enum
from uuid import uuid4

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.core.metrics import record_pipeline_cycle

if TYPE_CHECKING:
    from ag3ntwerk.learning.orchestrator import LearningOrchestrator
    from ag3ntwerk.learning.pattern_experiment import PatternExperimenter
    from ag3ntwerk.learning.meta_learner import MetaLearner
    from ag3ntwerk.learning.opportunity_detector import OpportunityDetector
    from ag3ntwerk.learning.proactive_generator import ProactiveTaskGenerator
    from ag3ntwerk.learning.autonomy_controller import AutonomyController

logger = get_logger(__name__)


class PipelineState(Enum):
    """States of the continuous pipeline."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class CyclePhase(Enum):
    """Phases within a learning cycle."""

    OUTCOME_COLLECTION = "outcome_collection"
    PATTERN_DETECTION = "pattern_detection"
    EXPERIMENT_MANAGEMENT = "experiment_management"
    PATTERN_ACTIVATION = "pattern_activation"
    PARAMETER_TUNING = "parameter_tuning"
    METACOGNITION = "metacognition"
    OPPORTUNITY_DETECTION = "opportunity_detection"
    TASK_GENERATION = "task_generation"
    CLEANUP = "cleanup"


@dataclass
class CycleResult:
    """Result of a single learning cycle."""

    cycle_id: str = field(default_factory=lambda: str(uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    success: bool = True
    error: Optional[str] = None

    # Metrics
    outcomes_collected: int = 0
    patterns_detected: int = 0
    experiments_started: int = 0
    experiments_concluded: int = 0
    patterns_activated: int = 0
    patterns_deactivated: int = 0
    parameters_tuned: int = 0
    opportunities_detected: int = 0
    tasks_generated: int = 0
    items_cleaned: int = 0

    # Phase timings (ms)
    phase_durations: Dict[str, float] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "outcomes_collected": self.outcomes_collected,
            "patterns_detected": self.patterns_detected,
            "experiments_started": self.experiments_started,
            "experiments_concluded": self.experiments_concluded,
            "patterns_activated": self.patterns_activated,
            "patterns_deactivated": self.patterns_deactivated,
            "parameters_tuned": self.parameters_tuned,
            "opportunities_detected": self.opportunities_detected,
            "tasks_generated": self.tasks_generated,
            "items_cleaned": self.items_cleaned,
            "phase_durations": self.phase_durations,
        }


@dataclass
class PipelineConfig:
    """Configuration for the continuous learning pipeline."""

    # Cycle timing
    cycle_interval_seconds: float = 60.0  # Time between cycles
    min_cycle_interval_seconds: float = 10.0  # Minimum time between cycles

    # Component enablement
    enable_pattern_detection: bool = True
    enable_experiments: bool = True
    enable_parameter_tuning: bool = True
    enable_opportunity_detection: bool = True
    enable_task_generation: bool = True
    enable_cleanup: bool = True

    # Thresholds
    min_outcomes_for_analysis: int = 10
    max_patterns_per_cycle: int = 5
    max_experiments_per_cycle: int = 3
    max_tasks_per_cycle: int = 10

    # Windows
    outcome_window_hours: int = 24
    pattern_window_hours: int = 168  # 1 week
    cleanup_age_hours: int = 720  # 30 days

    # Error handling
    max_consecutive_errors: int = 5
    error_backoff_seconds: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_interval_seconds": self.cycle_interval_seconds,
            "min_cycle_interval_seconds": self.min_cycle_interval_seconds,
            "enable_pattern_detection": self.enable_pattern_detection,
            "enable_experiments": self.enable_experiments,
            "enable_parameter_tuning": self.enable_parameter_tuning,
            "enable_opportunity_detection": self.enable_opportunity_detection,
            "enable_task_generation": self.enable_task_generation,
            "enable_cleanup": self.enable_cleanup,
            "min_outcomes_for_analysis": self.min_outcomes_for_analysis,
            "max_patterns_per_cycle": self.max_patterns_per_cycle,
            "max_experiments_per_cycle": self.max_experiments_per_cycle,
            "max_tasks_per_cycle": self.max_tasks_per_cycle,
            "outcome_window_hours": self.outcome_window_hours,
            "pattern_window_hours": self.pattern_window_hours,
            "cleanup_age_hours": self.cleanup_age_hours,
            "max_consecutive_errors": self.max_consecutive_errors,
            "error_backoff_seconds": self.error_backoff_seconds,
        }


class ContinuousLearningPipeline:
    """
    Never-ending learning cycle for autonomous intelligence.

    Coordinates all learning components to continuously:
    - Collect and analyze outcomes
    - Detect and activate patterns
    - Run experiments
    - Tune parameters
    - Generate proactive tasks
    """

    def __init__(
        self,
        orchestrator: "LearningOrchestrator",
        experimenter: Optional["PatternExperimenter"] = None,
        meta_learner: Optional["MetaLearner"] = None,
        opportunity_detector: Optional["OpportunityDetector"] = None,
        proactive_generator: Optional["ProactiveTaskGenerator"] = None,
        autonomy_controller: Optional["AutonomyController"] = None,
        config: Optional[PipelineConfig] = None,
        metacognition_facade: Optional[Any] = None,
    ):
        """
        Initialize the continuous learning pipeline.

        Args:
            orchestrator: Learning orchestrator (required)
            experimenter: Pattern experimenter for A/B testing
            meta_learner: Meta-learner for parameter tuning
            opportunity_detector: Opportunity detector for proactive detection
            proactive_generator: Task generator for maintenance tasks
            autonomy_controller: Autonomy controller for decision management
            config: Pipeline configuration
            metacognition_facade: Optional MetacognitionFacade for personality/reflection
        """
        self._orchestrator = orchestrator
        self._experimenter = experimenter
        self._meta_learner = meta_learner
        self._opportunity_detector = opportunity_detector
        self._proactive_generator = proactive_generator
        self._autonomy_controller = autonomy_controller
        self._metacognition_facade = metacognition_facade
        self._config = config or PipelineConfig()

        # State
        self._state = PipelineState.STOPPED
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        # Metrics
        self._total_cycles = 0
        self._successful_cycles = 0
        self._failed_cycles = 0
        self._consecutive_errors = 0
        self._last_cycle_result: Optional[CycleResult] = None
        self._cycle_history: deque[CycleResult] = deque(maxlen=100)

        # Started/stopped times
        self._started_at: Optional[datetime] = None
        self._stopped_at: Optional[datetime] = None

    @property
    def state(self) -> PipelineState:
        """Get current pipeline state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._state == PipelineState.RUNNING

    async def start(self) -> bool:
        """
        Start the continuous learning pipeline.

        Returns:
            True if started successfully
        """
        if self._state == PipelineState.RUNNING:
            logger.warning("Pipeline is already running")
            return False

        logger.info("Starting continuous learning pipeline", component="pipeline", phase="startup")

        self._state = PipelineState.STARTING
        self._stop_event.clear()
        self._started_at = datetime.now(timezone.utc)
        self._consecutive_errors = 0

        # Start the background task
        self._task = asyncio.create_task(self._run_loop())

        self._state = PipelineState.RUNNING
        logger.info("Continuous learning pipeline started", component="pipeline", phase="startup")

        return True

    async def stop(self, timeout: float = 30.0) -> bool:
        """
        Stop the continuous learning pipeline.

        Args:
            timeout: Maximum time to wait for clean shutdown

        Returns:
            True if stopped successfully
        """
        if self._state == PipelineState.STOPPED:
            return True

        logger.info("Stopping continuous learning pipeline", component="pipeline", phase="shutdown")

        self._state = PipelineState.STOPPING
        self._stop_event.set()

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    "Pipeline stop timed out, cancelling task",
                    component="pipeline",
                    phase="shutdown",
                )
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        self._state = PipelineState.STOPPED
        self._stopped_at = datetime.now(timezone.utc)
        self._task = None

        logger.info("Continuous learning pipeline stopped", component="pipeline", phase="shutdown")

        return True

    async def pause(self) -> bool:
        """
        Pause the pipeline (completes current cycle then pauses).

        Returns:
            True if paused successfully
        """
        if self._state != PipelineState.RUNNING:
            return False

        self._state = PipelineState.PAUSED
        logger.info("Continuous learning pipeline paused", component="pipeline")

        return True

    async def resume(self) -> bool:
        """
        Resume a paused pipeline.

        Returns:
            True if resumed successfully
        """
        if self._state != PipelineState.PAUSED:
            return False

        self._state = PipelineState.RUNNING
        logger.info("Continuous learning pipeline resumed", component="pipeline")

        return True

    async def run_single_cycle(self) -> CycleResult:
        """
        Run a single learning cycle manually.

        Returns:
            CycleResult with metrics
        """
        return await self._execute_cycle()

    async def _run_loop(self) -> None:
        """Main loop for continuous learning."""
        logger.info("Continuous learning loop started", component="pipeline")

        while not self._stop_event.is_set():
            # Check if paused
            if self._state == PipelineState.PAUSED:
                await asyncio.sleep(1.0)
                continue

            cycle_start = datetime.now(timezone.utc)

            try:
                # Execute the learning cycle
                result = await self._execute_cycle()

                self._total_cycles += 1
                self._last_cycle_result = result

                if result.success:
                    self._successful_cycles += 1
                    self._consecutive_errors = 0
                else:
                    self._failed_cycles += 1
                    self._consecutive_errors += 1

                # Store in history (deque maxlen=100 handles eviction)
                self._cycle_history.append(result)

                # Record pipeline cycle metrics
                try:
                    record_pipeline_cycle(
                        duration_ms=result.duration_ms,
                        success=result.success,
                    )
                except Exception:  # Metrics recording must never break the pipeline
                    pass

            except Exception as e:  # Intentional catch-all: main loop must not crash
                logger.error(
                    "Critical error in learning cycle",
                    component="pipeline",
                    error=str(e),
                    error_type=type(e).__name__,
                    consecutive_errors=self._consecutive_errors + 1,
                    exc_info=True,
                )
                self._failed_cycles += 1
                self._consecutive_errors += 1

                # Record failed pipeline cycle metrics
                try:
                    cycle_dur = (datetime.now(timezone.utc) - cycle_start).total_seconds() * 1000
                    record_pipeline_cycle(duration_ms=cycle_dur, success=False)
                except Exception:  # Metrics recording must never break the pipeline
                    pass

                # Check if we should enter error state
                if self._consecutive_errors >= self._config.max_consecutive_errors:
                    self._state = PipelineState.ERROR
                    logger.error(
                        "Pipeline entering error state",
                        component="pipeline",
                        consecutive_failures=self._consecutive_errors,
                        max_allowed=self._config.max_consecutive_errors,
                    )
                    break

            # Calculate sleep time
            cycle_duration = (datetime.now(timezone.utc) - cycle_start).total_seconds()
            sleep_time = max(
                self._config.min_cycle_interval_seconds,
                self._config.cycle_interval_seconds - cycle_duration,
            )

            # Apply error backoff if needed
            if self._consecutive_errors > 0:
                sleep_time += self._config.error_backoff_seconds * self._consecutive_errors

            # Wait for next cycle or stop signal
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=sleep_time,
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue loop

        logger.info(
            "Continuous learning loop ended",
            component="pipeline",
            total_cycles=self._total_cycles,
            successful=self._successful_cycles,
            failed=self._failed_cycles,
        )

    async def _execute_cycle(self) -> CycleResult:
        """Execute a single learning cycle."""
        result = CycleResult()

        try:
            # Phase 1: Outcome Collection
            await self._execute_phase(
                CyclePhase.OUTCOME_COLLECTION,
                result,
                self._collect_outcomes,
            )

            # Phase 2: Pattern Detection
            if self._config.enable_pattern_detection:
                await self._execute_phase(
                    CyclePhase.PATTERN_DETECTION,
                    result,
                    self._detect_patterns,
                )

            # Phase 3: Experiment Management
            if self._config.enable_experiments and self._experimenter:
                await self._execute_phase(
                    CyclePhase.EXPERIMENT_MANAGEMENT,
                    result,
                    self._manage_experiments,
                )

            # Phase 4: Pattern Activation
            await self._execute_phase(
                CyclePhase.PATTERN_ACTIVATION,
                result,
                self._activate_patterns,
            )

            # Phase 5: Parameter Tuning
            if self._config.enable_parameter_tuning and self._meta_learner:
                await self._execute_phase(
                    CyclePhase.PARAMETER_TUNING,
                    result,
                    self._tune_parameters,
                )

            # Phase 5.5: Metacognition (personality evolution, reflection, heuristic tuning)
            if self._metacognition_facade:
                await self._execute_phase(
                    CyclePhase.METACOGNITION,
                    result,
                    self._run_metacognition,
                )

            # Phase 6: Opportunity Detection
            if self._config.enable_opportunity_detection and self._opportunity_detector:
                await self._execute_phase(
                    CyclePhase.OPPORTUNITY_DETECTION,
                    result,
                    self._detect_opportunities,
                )

            # Phase 7: Task Generation
            if self._config.enable_task_generation and self._proactive_generator:
                await self._execute_phase(
                    CyclePhase.TASK_GENERATION,
                    result,
                    self._generate_tasks,
                )

            # Phase 8: Cleanup
            if self._config.enable_cleanup:
                await self._execute_phase(
                    CyclePhase.CLEANUP,
                    result,
                    self._cleanup,
                )

            result.success = True

        except Exception as e:  # Intentional catch-all: cycle must return CycleResult
            result.success = False
            result.error = str(e)
            logger.error(
                "Cycle failed",
                component="pipeline",
                cycle_id=result.cycle_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )

        result.completed_at = datetime.now(timezone.utc)

        logger.info(
            "Cycle completed",
            component="pipeline",
            cycle_id=result.cycle_id,
            duration_ms=round(result.duration_ms),
            success=result.success,
            patterns_detected=result.patterns_detected,
            tasks_generated=result.tasks_generated,
            outcomes_collected=result.outcomes_collected,
        )

        return result

    async def _execute_phase(
        self,
        phase: CyclePhase,
        result: CycleResult,
        phase_func,
    ) -> None:
        """Execute a single phase and track timing."""
        start = datetime.now(timezone.utc)

        try:
            await phase_func(result)
        except Exception as e:  # Intentional catch-all: isolate phase failures
            logger.warning(
                "Phase failed",
                component="pipeline",
                phase=phase.value,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )

        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        result.phase_durations[phase.value] = duration

    async def _collect_outcomes(self, result: CycleResult) -> None:
        """Collect recent outcomes for analysis."""
        # The orchestrator tracks outcomes automatically
        # Here we just get a count for reporting
        stats = await self._orchestrator.get_stats()
        core_stats = stats.get("core", {})
        outcome_stats = core_stats.get("outcome_stats", {})
        result.outcomes_collected = outcome_stats.get("total_outcomes_24h", 0)

    async def _detect_patterns(self, result: CycleResult) -> None:
        """Detect new patterns from outcomes."""
        # Run analysis cycle through orchestrator
        await self._orchestrator._run_analysis_cycle()

        # Get count of new patterns
        stats = await self._orchestrator.get_stats()
        pattern_stats = stats.get("patterns", {})
        result.patterns_detected = pattern_stats.get("total_patterns", 0)

    async def _manage_experiments(self, result: CycleResult) -> None:
        """Manage running experiments."""
        if not self._experimenter:
            return

        # Check for experiments to conclude
        active_experiments = await self._experimenter.list_active_experiments()

        for experiment in active_experiments:
            # Check if experiment has enough data
            total_samples = experiment.treatment.total_tasks + experiment.control.total_tasks

            if total_samples >= experiment.target_sample_size:
                # Conclude the experiment
                exp_result = await self._experimenter._conclude_experiment(experiment)
                if exp_result:
                    result.experiments_concluded += 1

        # Start new experiments for promising patterns
        if len(active_experiments) < self._config.max_experiments_per_cycle:
            # Get candidate patterns for experiments
            patterns = await self._orchestrator._pattern_store.get_all_active_patterns()

            for pattern in patterns[: self._config.max_experiments_per_cycle]:
                # Skip if already being experimented
                existing = await self._experimenter.get_experiment(pattern.id)
                if existing:
                    continue

                # Check autonomy
                if self._autonomy_controller:
                    decision = self._autonomy_controller.check_autonomy(
                        "experiment_start",
                    )
                    if not decision.proceed:
                        continue

                # Extract task_type from condition_json
                try:
                    condition = json.loads(pattern.condition_json)
                    task_type = condition.get("task_type", "unknown")
                    # task_type may be a list for correlation patterns
                    if isinstance(task_type, list):
                        task_type = task_type[0] if task_type else "unknown"
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        "Malformed condition_json, skipping experiment",
                        component="pipeline",
                        pattern_id=pattern.id,
                    )
                    continue

                # Start experiment
                await self._experimenter.create_experiment(
                    pattern_id=pattern.id,
                    task_type=task_type,
                    pattern_type=pattern.pattern_type.value,
                )
                result.experiments_started += 1

    async def _activate_patterns(self, result: CycleResult) -> None:
        """Activate successful patterns, deactivate poor ones."""
        patterns = await self._orchestrator._pattern_store.get_all_active_patterns()

        for pattern in patterns:
            # Skip patterns with insufficient samples
            if pattern.sample_size < self._config.min_outcomes_for_analysis:
                continue

            # Activate high-confidence patterns
            if pattern.confidence >= 0.8 and pattern.success_rate >= 0.7:
                if not pattern.is_active:
                    await self._orchestrator._pattern_store.activate_pattern(pattern.id)
                    result.patterns_activated += 1

            # Deactivate poor-performing patterns
            elif pattern.confidence < 0.3 or pattern.success_rate < 0.4:
                if pattern.is_active:
                    # Check autonomy
                    if self._autonomy_controller:
                        decision = self._autonomy_controller.check_autonomy(
                            "pattern_deactivation",
                        )
                        if decision.requires_logging:
                            await self._autonomy_controller.log_action(
                                "pattern_deactivation",
                                category=decision.level,
                                description=f"Deactivating pattern {pattern.id}",
                                context={"confidence": pattern.confidence},
                            )

                    await self._orchestrator._pattern_store.deactivate_pattern(pattern.id)
                    result.patterns_deactivated += 1

    async def _tune_parameters(self, result: CycleResult) -> None:
        """Tune system parameters using meta-learner."""
        if not self._meta_learner:
            return

        # Check autonomy
        if self._autonomy_controller:
            decision = self._autonomy_controller.check_autonomy("parameter_tuning")
            if not decision.proceed:
                return

        tuning_results = await self._meta_learner.tune_parameters()
        result.parameters_tuned = len(tuning_results)

        # Log if supervised
        if self._autonomy_controller and tuning_results:
            for tuning in tuning_results:
                await self._autonomy_controller.log_action(
                    "parameter_tuning",
                    category=decision.level,
                    description=f"Tuned {tuning.parameter_name}",
                    context={
                        "old_value": tuning.old_value,
                        "new_value": tuning.new_value,
                    },
                )

    async def _run_metacognition(self, result: CycleResult) -> None:
        """Run metacognition phase: reflection, evolution, heuristic tuning."""
        if not self._metacognition_facade:
            return

        try:
            phase_result = self._metacognition_facade.run_metacognition_phase()
            # Store metrics in phase_durations for visibility
            if isinstance(phase_result, dict):
                result.phase_durations["metacognition_details"] = phase_result.get(
                    "heuristics_tuned", 0
                )
        except Exception as e:  # Intentional catch-all: metacognition is optional
            logger.warning(
                "Metacognition phase error",
                component="pipeline",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )

    async def _detect_opportunities(self, result: CycleResult) -> None:
        """Detect improvement opportunities."""
        if not self._opportunity_detector:
            return

        opportunities = await self._opportunity_detector.detect_opportunities(
            window_hours=self._config.pattern_window_hours
        )

        result.opportunities_detected = len(opportunities)

    async def _generate_tasks(self, result: CycleResult) -> None:
        """Generate proactive maintenance tasks."""
        if not self._proactive_generator:
            return

        # Check autonomy
        if self._autonomy_controller:
            decision = self._autonomy_controller.check_autonomy("proactive_task_creation")
            if not decision.proceed:
                return

        tasks = await self._proactive_generator.generate_all_tasks(
            window_hours=self._config.outcome_window_hours
        )

        # Limit tasks per cycle
        tasks = tasks[: self._config.max_tasks_per_cycle]

        # Enqueue tasks
        enqueued = await self._proactive_generator.enqueue_all_pending()
        result.tasks_generated = enqueued

    async def _cleanup(self, result: CycleResult) -> None:
        """Clean up old data."""
        cleaned = 0

        # Clean up completed proactive tasks
        if self._proactive_generator:
            cleaned += await self._proactive_generator.clear_completed_tasks()

        # Clean up expired approvals
        if self._autonomy_controller:
            cleaned += await self._autonomy_controller.cleanup_expired_approvals()

        result.items_cleaned = cleaned

    def update_config(self, **kwargs) -> None:
        """
        Update pipeline configuration.

        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
                logger.info(
                    "Pipeline config updated",
                    component="pipeline",
                    config_key=key,
                    config_value=value,
                )

    def get_config(self) -> Dict[str, Any]:
        """Get current pipeline configuration."""
        return self._config.to_dict()

    async def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "state": self._state.value,
            "is_running": self.is_running,
            "total_cycles": self._total_cycles,
            "successful_cycles": self._successful_cycles,
            "failed_cycles": self._failed_cycles,
            "consecutive_errors": self._consecutive_errors,
            "success_rate": (
                self._successful_cycles / self._total_cycles if self._total_cycles > 0 else 0.0
            ),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "stopped_at": self._stopped_at.isoformat() if self._stopped_at else None,
            "last_cycle": (self._last_cycle_result.to_dict() if self._last_cycle_result else None),
            "config": self._config.to_dict(),
        }

    def get_cycle_history(
        self,
        limit: int = 20,
        success_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get recent cycle history.

        Args:
            limit: Maximum cycles to return
            success_only: Only return successful cycles

        Returns:
            List of cycle results
        """
        cycles = list(self._cycle_history)

        if success_only:
            cycles = [c for c in cycles if c.success]

        # Return most recent first
        return [c.to_dict() for c in reversed(cycles[-limit:])]

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the pipeline.

        Returns:
            Health check result
        """
        health = {
            "healthy": True,
            "state": self._state.value,
            "issues": [],
        }

        # Check state
        if self._state == PipelineState.ERROR:
            health["healthy"] = False
            health["issues"].append("Pipeline is in error state")

        # Check consecutive errors
        if self._consecutive_errors > 0:
            health["issues"].append(f"{self._consecutive_errors} consecutive errors")
            if self._consecutive_errors >= self._config.max_consecutive_errors // 2:
                health["healthy"] = False

        # Check success rate
        if self._total_cycles > 10:
            success_rate = self._successful_cycles / self._total_cycles
            if success_rate < 0.9:
                health["issues"].append(f"Low success rate: {success_rate:.1%}")
            if success_rate < 0.7:
                health["healthy"] = False

        # Check cycle timing
        if self._last_cycle_result:
            if self._last_cycle_result.duration_ms > self._config.cycle_interval_seconds * 1000:
                health["issues"].append(
                    f"Cycles taking longer than interval: "
                    f"{self._last_cycle_result.duration_ms:.0f}ms"
                )

        return health
