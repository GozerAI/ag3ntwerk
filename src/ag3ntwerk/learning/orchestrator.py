"""
Learning Orchestrator - Central coordinator for the Learning Loops system.

Manages all learning loops, coordinates analysis cycles, and provides
the unified API for learning consumption and outcome recording.

This orchestrator delegates to domain-focused facades for actual implementation.
The facades own the subsystems and provide focused APIs for their domains.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.logging import get_logger

# Core models and types (re-exported for backward compatibility)
from ag3ntwerk.learning.models import (
    HierarchyPath,
    LearnedPattern,
    LearningAdjustment,
    LearningIssue,
    ScopeLevel,
    TaskOutcomeRecord,
)
from ag3ntwerk.learning.outcome_tracker import OutcomeTracker
from ag3ntwerk.learning.pattern_store import PatternStore

# Type imports from subsystems (for method signatures)
from ag3ntwerk.learning.dynamic_router import RoutingDecision
from ag3ntwerk.learning.failure_predictor import FailureRisk
from ag3ntwerk.learning.load_balancer import LoadBalanceDecision, AgentLoad
from ag3ntwerk.learning.task_modifier import ModifiedTask
from ag3ntwerk.learning.pattern_experiment import (
    PatternExperiment,
    ExperimentResult,
)
from ag3ntwerk.learning.meta_learner import EffectivenessMetrics
from ag3ntwerk.learning.handler_generator import GeneratedHandler
from ag3ntwerk.learning.opportunity_detector import (
    Opportunity,
    OpportunityType,
    OpportunityPriority,
)
from ag3ntwerk.learning.proactive_generator import (
    ProactiveTask,
    ProactiveTaskType,
    TaskPriority,
)
from ag3ntwerk.learning.autonomy_controller import (
    AutonomyController,
    AutonomyLevel,
    ActionCategory,
    AutonomyDecision,
    PendingApproval,
)
from ag3ntwerk.learning.continuous_pipeline import (
    ContinuousLearningPipeline,
    PipelineState,
    PipelineConfig,
    CycleResult,
)
from ag3ntwerk.learning.workbench_bridge import LearningDashboard
from ag3ntwerk.learning.plugin_telemetry import PluginStats
from ag3ntwerk.learning.service_adapter import ConfigRecommendation
from ag3ntwerk.learning.capability_evolver import (
    NewCapability,
    DemandGap,
    EvolutionStatus,
)
from ag3ntwerk.learning.pattern_propagator import (
    PropagationRecord,
    PropagationResult,
    AgentSimilarity,
)
from ag3ntwerk.learning.failure_investigator import (
    Investigation,
    RecommendedFix,
)
from ag3ntwerk.learning.demand_forecaster import DemandForecast
from ag3ntwerk.learning.cascade_predictor import CascadeEffect
from ag3ntwerk.learning.context_optimizer import (
    OptimizedTask,
    ExecutionContext,
)
from ag3ntwerk.learning.self_architect import ArchitectureProposal
from ag3ntwerk.learning.goal_aligner import AlignmentScore
from ag3ntwerk.learning.handoff_optimizer import HandoffStrategy

# Domain facades
from ag3ntwerk.learning.facades import (
    CoreLearningFacade,
    RoutingFacade,
    PredictionFacade,
    ExperimentationFacade,
    ProactiveFacade,
    AutonomyFacade,
    IntegrationFacade,
    EvolutionFacade,
    IntelligenceFacade,
    AdvancedAutonomyFacade,
    MetacognitionFacade,
)

logger = get_logger(__name__)


class LearningOrchestrator:
    """
    Central coordinator for the Learning Loops system.

    This orchestrator delegates to domain-focused facades:
    - CoreLearningFacade: Outcome tracking, pattern storage, learning loops
    - RoutingFacade: Dynamic routing, pattern tracking, confidence calibration
    - PredictionFacade: Failure prediction, load balancing, task modification
    - ExperimentationFacade: A/B experiments, meta-learning, handler generation
    - ProactiveFacade: Opportunity detection, proactive task generation
    - AutonomyFacade: Autonomy control, continuous learning pipeline
    - IntegrationFacade: Workbench, plugin, and service integrations
    - EvolutionFacade: Capability evolution, pattern propagation, failure investigation
    - IntelligenceFacade: Demand forecasting, cascade prediction, context optimization
    - AdvancedAutonomyFacade: Self-architecture, goal alignment, handoff optimization

    All existing methods are maintained for backward compatibility and delegate
    to the appropriate facade.
    """

    def __init__(
        self,
        db: Any,
        task_queue: Optional[Any] = None,
    ):
        """
        Initialize the learning orchestrator.

        Args:
            db: Database connection
            task_queue: Optional task queue for issue task creation
        """
        self._db = db
        self._task_queue = task_queue

        # Shared components (passed to facades)
        self._outcome_tracker = OutcomeTracker(db)
        self._pattern_store = PatternStore(db)

        # Domain facades
        self._core = CoreLearningFacade(db, task_queue, self._outcome_tracker, self._pattern_store)
        self._prediction = PredictionFacade(db, task_queue)
        # Wire LoadBalancer from PredictionFacade to RoutingFacade for load-aware routing
        self._routing = RoutingFacade(db, self._pattern_store, self._prediction.load_balancer)
        self._experimentation = ExperimentationFacade(db, self._pattern_store)
        self._proactive = ProactiveFacade(db, task_queue, self._pattern_store)
        self._autonomy = AutonomyFacade(db)
        self._integration = IntegrationFacade(db, self._outcome_tracker, self._pattern_store)
        self._evolution = EvolutionFacade(db, self._outcome_tracker, self._pattern_store)
        self._intelligence = IntelligenceFacade(db, self._outcome_tracker, self._pattern_store)
        self._advanced_autonomy = AdvancedAutonomyFacade(
            db, self._outcome_tracker, self._pattern_store
        )
        self._metacognition = MetacognitionFacade()

        # Set cross-references for facades that need them
        self._integration.set_orchestrator(self)
        self._autonomy.set_pipeline_dependencies(
            orchestrator=self,
            experimenter=self._experimentation.pattern_experimenter,
            meta_learner=self._experimentation.meta_learner,
            opportunity_detector=self._proactive.opportunity_detector,
            proactive_generator=self._proactive.proactive_generator,
        )

        # Background analysis
        self._analysis_task: Optional[asyncio.Task] = None
        self._running = False
        self._analysis_interval_seconds = 60

        # Configuration
        self._min_outcomes_for_analysis = 5

        # Nexus sync bridge (optional)
        self._nexus_sync_bridge = None

    # ==================== Lifecycle ====================

    async def initialize(self) -> None:
        """Initialize the orchestrator and load existing patterns."""
        count = await self._pattern_store.load_patterns()
        logger.info("Loaded existing patterns", component="orchestrator", pattern_count=count)

        self._running = True
        self._analysis_task = asyncio.create_task(self._analysis_loop())

        logger.info("Learning Orchestrator initialized", component="orchestrator")

    async def shutdown(self) -> None:
        """Shutdown the orchestrator gracefully."""
        self._running = False

        if self._analysis_task:
            self._analysis_task.cancel()
            try:
                await self._analysis_task
            except asyncio.CancelledError:
                pass

        # Stop continuous pipeline if running
        if self._autonomy.continuous_pipeline:
            await self._autonomy.stop_continuous_pipeline()

        # Stop Nexus sync if running
        if self._nexus_sync_bridge:
            await self._nexus_sync_bridge.stop_periodic_sync()

        logger.info("Learning Orchestrator shutdown", component="orchestrator")

    async def _analysis_loop(self) -> None:
        """Background analysis loop."""
        while self._running:
            try:
                await asyncio.sleep(self._analysis_interval_seconds)
                if self._running:
                    await self._run_analysis_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:  # Intentional catch-all: analysis loop must not crash
                logger.error(
                    "Analysis cycle error",
                    component="orchestrator",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )

    async def _run_analysis_cycle(self) -> Dict[str, Any]:
        """Run one analysis cycle."""
        return await self._core.run_analysis_cycle()

    # ==================== Registration (Core) ====================

    def register_executive(self, agent_code: str, managers: List[str]) -> None:
        """Register an agent and create its learning loop."""
        self._core.register_executive(agent_code, managers)

    def register_manager(
        self, manager_code: str, agent_code: str, specialists: List[str]
    ) -> None:
        """Register a manager and create its learning loop."""
        self._core.register_manager(manager_code, agent_code, specialists)

    def register_specialist(
        self, specialist_code: str, manager_code: str, capabilities: Optional[List[str]] = None
    ) -> None:
        """Register a specialist and create its learning loop."""
        self._core.register_specialist(specialist_code, manager_code, capabilities)

    # ==================== Outcome Recording (Core) ====================

    async def record_outcome(
        self,
        task_id: str,
        task_type: str,
        hierarchy_path: HierarchyPath,
        success: bool,
        duration_ms: float = 0.0,
        effectiveness: Optional[float] = None,
        confidence: Optional[float] = None,
        actual_accuracy: Optional[float] = None,
        error: Optional[str] = None,
        output_summary: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        applied_pattern_ids: Optional[List[str]] = None,
        was_routing_influenced: bool = False,
        was_confidence_calibrated: bool = False,
    ) -> str:
        """Record a task outcome."""
        record_id = await self._core.record_outcome(
            task_id=task_id,
            task_type=task_type,
            hierarchy_path=hierarchy_path,
            success=success,
            duration_ms=duration_ms,
            effectiveness=effectiveness,
            confidence=confidence,
            actual_accuracy=actual_accuracy,
            error=error,
            output_summary=output_summary,
            context=context,
            applied_pattern_ids=applied_pattern_ids,
            was_routing_influenced=was_routing_influenced,
            was_confidence_calibrated=was_confidence_calibrated,
        )

        # Forward to Nexus sync bridge if configured
        if self._nexus_sync_bridge:
            try:
                # Create a lightweight record for sync
                from ag3ntwerk.learning.models import TaskOutcomeRecord, ErrorCategory

                record = TaskOutcomeRecord(
                    id=record_id,
                    task_id=task_id,
                    task_type=task_type,
                    agent_code=hierarchy_path.agent,
                    manager_code=hierarchy_path.manager,
                    specialist_code=hierarchy_path.specialist,
                    success=success,
                    duration_ms=duration_ms,
                    effectiveness=effectiveness or 0.0,
                    initial_confidence=confidence,
                    actual_accuracy=actual_accuracy,
                    error_message=error,
                    error_category=ErrorCategory.UNKNOWN if error else None,
                    applied_pattern_ids=applied_pattern_ids or [],
                    was_routing_influenced=was_routing_influenced,
                    was_confidence_calibrated=was_confidence_calibrated,
                )
                await self._nexus_sync_bridge.forward_outcome(record)
            except Exception as e:
                logger.warning(
                    "Failed to forward outcome to Nexus sync",
                    component="orchestrator",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )

        return record_id

    async def get_task_adjustments(self, task_type: str, target_agent: str) -> LearningAdjustment:
        """Get learning-based adjustments for a task before execution."""
        return await self._core.get_task_adjustments(task_type, target_agent)

    async def get_patterns(
        self,
        scope_level: Optional[ScopeLevel] = None,
        scope_code: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> List[LearnedPattern]:
        """Get patterns matching criteria."""
        return await self._core.get_patterns(
            scope=scope_level,
            pattern_type=task_type,
            agent_code=scope_code,
        )

    async def get_open_issues(self, agent_code: Optional[str] = None) -> List[LearningIssue]:
        """Get open issues."""
        return await self._core.get_open_issues(agent_code)

    async def trigger_analysis(self) -> Dict[str, Any]:
        """Manually trigger an analysis cycle."""
        return await self._run_analysis_cycle()

    # ==================== Routing (RoutingFacade) ====================

    async def get_routing_decision(
        self,
        task_type: str,
        available_agents: Dict[str, Any],
        static_route: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """Get a learning-informed routing decision."""
        return await self._routing.get_routing_decision(
            task_type=task_type,
            available_agents=available_agents,
            static_route=static_route,
            context=context,
        )

    async def get_routing_patterns(self, task_type: str) -> List[LearnedPattern]:
        """Get routing patterns for a task type."""
        return await self._routing.get_routing_patterns(task_type)

    async def record_routing_outcome(
        self,
        task_type: str,
        chosen_agent: str,
        success: bool,
        was_dynamic: bool,
        duration_ms: float = 0.0,
    ) -> None:
        """Record the outcome of a routing decision."""
        await self._routing.record_routing_outcome(
            task_type=task_type,
            chosen_agent=chosen_agent,
            success=success,
            was_dynamic=was_dynamic,
            duration_ms=duration_ms,
        )

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
        """Record that a pattern was applied to a task."""
        return await self._routing.record_pattern_application(
            pattern_id=pattern_id,
            task_id=task_id,
            task_type=task_type,
            agent_code=agent_code,
            is_routing_pattern=is_routing_pattern,
            is_confidence_pattern=is_confidence_pattern,
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
        """Record the outcome of a task where a pattern was applied."""
        await self._routing.record_pattern_outcome(
            task_id=task_id,
            success=success,
            duration_ms=duration_ms,
            effectiveness=effectiveness,
        )

    async def get_declining_patterns(self, window_hours: int = 24) -> List[Any]:
        """Get patterns that are performing worse than their baseline."""
        return await self._routing.get_declining_patterns(window_hours)

    async def get_calibrated_confidence(
        self,
        agent_code: str,
        task_type: str,
        raw_confidence: float,
    ) -> float:
        """Get calibrated confidence for an agent's prediction."""
        return await self._routing.get_calibrated_confidence(
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
        """Record a confidence prediction and its outcome."""
        await self._routing.record_confidence_prediction(
            agent_code=agent_code,
            task_type=task_type,
            confidence=confidence,
            was_successful=was_successful,
        )

    async def get_calibration_summary(self, agent_code: str) -> Dict[str, Any]:
        """Get calibration summary for an agent."""
        return await self._routing.get_calibration_summary(agent_code)

    async def get_poorly_calibrated_agents(self, threshold: float = 0.15) -> List[Dict[str, Any]]:
        """Find agents with poor calibration."""
        return await self._routing.get_poorly_calibrated_agents(threshold)

    # ==================== Prediction (PredictionFacade) ====================

    async def predict_failure_risk(
        self,
        task_type: str,
        target_agent: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> FailureRisk:
        """Predict the failure risk for a task before execution."""
        return await self._prediction.predict_failure_risk(
            task_type=task_type,
            target_agent=target_agent,
            context=context,
        )

    async def get_safest_agent(self, task_type: str, candidates: List[str]) -> Optional[tuple]:
        """Find the agent with lowest failure risk for a task."""
        return await self._prediction.get_safest_agent(task_type, candidates)

    async def get_high_risk_agents(self, task_type: str, threshold: float = 0.5) -> List[tuple]:
        """Find agents with high failure risk for a task type."""
        return await self._prediction.get_high_risk_agents(task_type, threshold)

    async def get_optimal_agent(
        self,
        task_type: str,
        candidates: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> LoadBalanceDecision:
        """Get the optimal agent based on load balancing."""
        return await self._prediction.get_optimal_agent(
            task_type=task_type,
            candidates=candidates,
            context=context,
        )

    async def get_agent_loads(self, agent_codes: List[str]) -> Dict[str, AgentLoad]:
        """Get load metrics for multiple agents."""
        return await self._prediction.get_agent_loads(agent_codes)

    async def get_overloaded_agents(self, agent_codes: Optional[List[str]] = None) -> List[tuple]:
        """Find agents that are currently overloaded."""
        return await self._prediction.get_overloaded_agents(agent_codes)

    async def get_idle_agents(
        self,
        agent_codes: Optional[List[str]] = None,
        idle_threshold: float = 0.2,
    ) -> List[tuple]:
        """Find agents with low utilization."""
        return await self._prediction.get_idle_agents(agent_codes, idle_threshold)

    async def modify_task(
        self,
        task: Dict[str, Any],
        target_agent: str,
        candidates: Optional[List[str]] = None,
    ) -> ModifiedTask:
        """Proactively modify a task based on predicted risks."""
        return await self._prediction.modify_task(
            task=task,
            target_agent=target_agent,
            candidates=candidates,
        )

    # ==================== Experimentation (ExperimentationFacade) ====================

    async def create_experiment(
        self,
        pattern_id: str,
        task_type: str,
        target_sample_size: int = 100,
        traffic_percentage: float = 0.5,
    ) -> PatternExperiment:
        """Create an A/B experiment for a pattern."""
        return await self._experimentation.create_experiment(
            pattern_id=pattern_id,
            task_type=task_type,
            target_sample_size=target_sample_size,
            traffic_percentage=traffic_percentage,
        )

    async def should_apply_pattern_in_experiment(self, pattern_id: str, task_type: str) -> tuple:
        """Check if a pattern should be applied (for A/B testing)."""
        return await self._experimentation.should_apply_pattern_in_experiment(pattern_id, task_type)

    async def record_experiment_outcome(
        self,
        pattern_id: str,
        applied_pattern: bool,
        success: bool,
        duration_ms: float = 0.0,
        effectiveness: float = 0.0,
    ) -> Optional[ExperimentResult]:
        """Record outcome for an experiment."""
        return await self._experimentation.record_experiment_outcome(
            pattern_id=pattern_id,
            applied_pattern=applied_pattern,
            success=success,
            duration_ms=duration_ms,
            effectiveness=effectiveness,
        )

    async def get_active_experiments(self) -> List[PatternExperiment]:
        """Get all active experiments."""
        return await self._experimentation.get_active_experiments()

    async def get_experiment(self, pattern_id: str) -> Optional[PatternExperiment]:
        """Get experiment for a pattern."""
        return await self._experimentation.get_experiment(pattern_id)

    async def abort_experiment(
        self, pattern_id: str, reason: str = ""
    ) -> Optional[PatternExperiment]:
        """Abort an active experiment."""
        return await self._experimentation.abort_experiment(pattern_id, reason)

    async def get_patterns_needing_experiments(self) -> List[str]:
        """Find patterns that would benefit from experiments."""
        return await self._experimentation.get_patterns_needing_experiments()

    async def tune_parameters(self) -> List[Any]:
        """Run a meta-learner parameter tuning cycle."""
        return await self._experimentation.tune_parameters()

    async def get_meta_learner_parameter(self, name: str) -> Optional[float]:
        """Get a meta-learner parameter value."""
        return self._experimentation.get_meta_learner_parameter(name)

    async def get_all_meta_learner_parameters(self) -> Dict[str, float]:
        """Get all meta-learner parameter values."""
        return self._experimentation.get_all_meta_learner_parameters()

    async def measure_effectiveness(self, window_hours: int = 24) -> EffectivenessMetrics:
        """Measure learning system effectiveness."""
        return await self._experimentation.measure_effectiveness(window_hours)

    async def evaluate_recent_tuning(self, window_hours: int = 24) -> Dict[str, Any]:
        """Evaluate whether recent tuning was beneficial."""
        return await self._experimentation.evaluate_recent_tuning(window_hours)

    async def get_meta_learner_stats(self) -> Dict[str, Any]:
        """Get meta-learner statistics."""
        return await self._experimentation.get_meta_learner_stats()

    async def analyze_for_handler_generation(self, task_type: str) -> Optional[Any]:
        """Analyze a task type for potential handler generation."""
        return await self._experimentation.analyze_for_handler_generation(task_type)

    async def generate_handler(self, task_type: str) -> Optional[GeneratedHandler]:
        """Generate a handler for a task type."""
        return await self._experimentation.generate_handler(task_type)

    async def get_handler_for_task(self, task_type: str) -> Optional[GeneratedHandler]:
        """Get an active handler for a task type."""
        return await self._experimentation.get_handler_for_task(task_type)

    async def record_handler_usage(
        self, handler_id: str, success: bool, duration_ms: float = 0.0
    ) -> None:
        """Record usage of a generated handler."""
        await self._experimentation.record_handler_usage(handler_id, success, duration_ms)

    async def activate_handler(self, handler_id: str) -> bool:
        """Activate a handler for testing."""
        return await self._experimentation.activate_handler(handler_id)

    async def deprecate_handler(self, handler_id: str, reason: str = "") -> bool:
        """Deprecate a handler."""
        return await self._experimentation.deprecate_handler(handler_id, reason)

    async def get_all_handlers(self) -> List[GeneratedHandler]:
        """Get all generated handlers."""
        return await self._experimentation.get_all_handlers()

    async def get_handler(self, handler_id: str) -> Optional[GeneratedHandler]:
        """Get a specific handler."""
        return await self._experimentation.get_handler(handler_id)

    async def find_handler_generation_candidates(self) -> List[str]:
        """Find task types that could have handlers generated."""
        return await self._experimentation.find_handler_generation_candidates()

    # ==================== Proactive (ProactiveFacade) ====================

    async def detect_opportunities(self, window_hours: int = 168) -> List[Opportunity]:
        """Run opportunity detection cycle."""
        return await self._proactive.detect_opportunities(window_hours)

    async def get_open_opportunities(self) -> List[Opportunity]:
        """Get all open opportunities."""
        return await self._proactive.get_open_opportunities()

    async def get_actionable_opportunities(self) -> List[Opportunity]:
        """Get opportunities that can be addressed automatically."""
        return await self._proactive.get_actionable_opportunities()

    async def get_opportunities_by_type(
        self, opportunity_type: OpportunityType
    ) -> List[Opportunity]:
        """Get opportunities of a specific type."""
        return await self._proactive.get_opportunities_by_type(opportunity_type)

    async def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get a specific opportunity."""
        return await self._proactive.get_opportunity(opportunity_id)

    async def acknowledge_opportunity(self, opportunity_id: str) -> bool:
        """Acknowledge an opportunity."""
        return await self._proactive.acknowledge_opportunity(opportunity_id)

    async def address_opportunity(self, opportunity_id: str, resolution: str = "") -> bool:
        """Mark an opportunity as addressed."""
        return await self._proactive.address_opportunity(opportunity_id, resolution)

    async def dismiss_opportunity(self, opportunity_id: str, reason: str = "") -> bool:
        """Dismiss an opportunity."""
        return await self._proactive.dismiss_opportunity(opportunity_id, reason)

    async def get_opportunity_stats(self) -> Dict[str, Any]:
        """Get opportunity detection statistics."""
        return await self._proactive.get_opportunity_stats()

    async def generate_proactive_tasks(self, window_hours: int = 24) -> List[ProactiveTask]:
        """Generate all types of proactive tasks."""
        return await self._proactive.generate_proactive_tasks(window_hours)

    async def get_pending_proactive_tasks(self) -> List[ProactiveTask]:
        """Get all pending proactive tasks."""
        return await self._proactive.get_pending_proactive_tasks()

    async def get_proactive_task(self, task_id: str) -> Optional[ProactiveTask]:
        """Get a specific proactive task."""
        return await self._proactive.get_proactive_task(task_id)

    async def get_proactive_tasks_by_type(
        self, task_type: ProactiveTaskType
    ) -> List[ProactiveTask]:
        """Get proactive tasks of a specific type."""
        return await self._proactive.get_proactive_tasks_by_type(task_type)

    async def enqueue_proactive_task(self, task: ProactiveTask) -> bool:
        """Enqueue a proactive task to the task queue."""
        return await self._proactive.enqueue_proactive_task(task)

    async def enqueue_all_proactive_tasks(self) -> int:
        """Enqueue all pending proactive tasks."""
        return await self._proactive.enqueue_all_proactive_tasks()

    async def complete_proactive_task(
        self, task_id: str, result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Mark a proactive task as completed."""
        return await self._proactive.complete_proactive_task(task_id, result)

    async def fail_proactive_task(self, task_id: str, error: str = "") -> bool:
        """Mark a proactive task as failed."""
        return await self._proactive.fail_proactive_task(task_id, error)

    async def get_proactive_task_stats(self) -> Dict[str, Any]:
        """Get proactive task generation statistics."""
        return await self._proactive.get_proactive_task_stats()

    async def run_proactive_cycle(self, window_hours: int = 24) -> Dict[str, Any]:
        """Run a full proactive behavior cycle."""
        return await self._proactive.run_proactive_cycle(window_hours)

    # ==================== Autonomy (AutonomyFacade) ====================

    def get_autonomy_controller(self) -> AutonomyController:
        """Get the autonomy controller."""
        return self._autonomy.get_autonomy_controller()

    def check_autonomy(
        self, action: str, category: Optional[ActionCategory] = None
    ) -> AutonomyDecision:
        """Check autonomy level for an action."""
        return self._autonomy.check_autonomy(action, category)

    async def request_approval(
        self,
        action: str,
        category: ActionCategory,
        description: str,
        impact_assessment: str = "",
        recommended_decision: bool = True,
    ) -> PendingApproval:
        """Request human approval for an action."""
        return await self._autonomy.request_approval(
            action=action,
            category=category,
            description=description,
            impact_assessment=impact_assessment,
            recommended_decision=recommended_decision,
        )

    async def approve_action(self, approval_id: str, approver: str = "human") -> bool:
        """Approve a pending action."""
        return await self._autonomy.approve_action(approval_id, approver)

    async def deny_action(self, approval_id: str, denier: str = "human", reason: str = "") -> bool:
        """Deny a pending action."""
        return await self._autonomy.deny_action(approval_id, denier, reason)

    def get_pending_approvals(self) -> List[PendingApproval]:
        """Get all pending approval requests."""
        return self._autonomy.get_pending_approvals()

    def set_autonomy_level(self, category: ActionCategory, level: AutonomyLevel) -> None:
        """Set the autonomy level for a category."""
        self._autonomy.set_autonomy_level(category, level)

    async def get_autonomy_stats(self) -> Dict[str, Any]:
        """Get autonomy controller statistics."""
        return await self._autonomy.get_autonomy_stats()

    async def initialize_continuous_pipeline(
        self, config: Optional[PipelineConfig] = None
    ) -> ContinuousLearningPipeline:
        """Initialize and return the continuous learning pipeline."""
        return await self._autonomy.initialize_continuous_pipeline(config)

    async def start_continuous_pipeline(self) -> bool:
        """Start the continuous learning pipeline."""
        return await self._autonomy.start_continuous_pipeline()

    async def stop_continuous_pipeline(self, timeout: float = 30.0) -> bool:
        """Stop the continuous learning pipeline."""
        return await self._autonomy.stop_continuous_pipeline(timeout)

    async def pause_continuous_pipeline(self) -> bool:
        """Pause the continuous learning pipeline."""
        return await self._autonomy.pause_continuous_pipeline()

    async def resume_continuous_pipeline(self) -> bool:
        """Resume the continuous learning pipeline."""
        return await self._autonomy.resume_continuous_pipeline()

    async def run_single_learning_cycle(self) -> CycleResult:
        """Run a single learning cycle manually."""
        return await self._autonomy.run_single_learning_cycle()

    def get_pipeline_state(self) -> PipelineState:
        """Get current pipeline state."""
        return self._autonomy.get_pipeline_state()

    def is_pipeline_running(self) -> bool:
        """Check if pipeline is running."""
        return self._autonomy.is_pipeline_running()

    async def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return await self._autonomy.get_pipeline_stats()

    def get_pipeline_cycle_history(
        self, limit: int = 20, success_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get recent pipeline cycle history."""
        return self._autonomy.get_pipeline_cycle_history(limit, success_only)

    async def pipeline_health_check(self) -> Dict[str, Any]:
        """Perform a health check on the pipeline."""
        return await self._autonomy.pipeline_health_check()

    def update_pipeline_config(self, **kwargs) -> None:
        """Update pipeline configuration."""
        self._autonomy.update_pipeline_config(**kwargs)

    # ==================== Integration (IntegrationFacade) ====================

    def get_workbench_bridge(self) -> Any:
        """Get the Workbench bridge for UI integration."""
        return self._integration.get_workbench_bridge()

    async def get_learning_dashboard(self, refresh: bool = False) -> LearningDashboard:
        """Get the learning dashboard data."""
        return await self._integration.get_learning_dashboard(refresh)

    async def get_workbench_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get pending approvals for Workbench display."""
        return await self._integration.get_workbench_pending_approvals()

    async def workbench_approve_action(
        self,
        approval_id: str,
        approved_by: str = "workbench_user",
        notes: Optional[str] = None,
    ) -> Any:
        """Approve an action from Workbench."""
        return await self._integration.workbench_approve_action(approval_id, approved_by, notes)

    async def workbench_reject_action(
        self,
        approval_id: str,
        rejected_by: str = "workbench_user",
        notes: Optional[str] = None,
    ) -> Any:
        """Reject an action from Workbench."""
        return await self._integration.workbench_reject_action(approval_id, rejected_by, notes)

    async def get_agent_insight(self, agent_code: str) -> Any:
        """Get learning insight for an agent."""
        return await self._integration.get_agent_insight(agent_code)

    async def get_all_agent_insights(self) -> List[Any]:
        """Get learning insights for all agents."""
        return await self._integration.get_all_agent_insights()

    def get_plugin_telemetry(self) -> Any:
        """Get the plugin telemetry adapter."""
        return self._integration.get_plugin_telemetry()

    def register_plugin(
        self,
        plugin_id: str,
        name: str,
        version: str,
        operations: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a plugin for telemetry tracking."""
        self._integration.register_plugin(plugin_id, name, version, operations, metadata)

    async def record_plugin_outcome(
        self,
        plugin_id: str,
        operation: str,
        success: bool,
        duration_ms: float,
        error: Optional[str] = None,
        input_summary: Optional[str] = None,
        output_summary: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record a plugin operation outcome."""
        return await self._integration.record_plugin_outcome(
            plugin_id=plugin_id,
            operation=operation,
            success=success,
            duration_ms=duration_ms,
            error=error,
            input_summary=input_summary,
            output_summary=output_summary,
            context=context,
        )

    async def start_plugin_operation(
        self,
        plugin_id: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Start tracking a plugin operation."""
        return await self._integration.start_plugin_operation(plugin_id, operation, context)

    async def get_plugin_stats(self, plugin_id: str, window_hours: int = 24) -> PluginStats:
        """Get statistics for a plugin."""
        return await self._integration.get_plugin_stats(plugin_id, window_hours)

    async def get_all_plugin_stats(self, window_hours: int = 24) -> List[PluginStats]:
        """Get statistics for all plugins."""
        return await self._integration.get_all_plugin_stats(window_hours)

    def get_service_adapter(self) -> Any:
        """Get the service adapter."""
        return self._integration.get_service_adapter()

    async def register_service(
        self,
        service_id: str,
        initial_config: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Register a service for adaptation tracking."""
        return await self._integration.register_service(service_id, initial_config, metadata)

    async def get_service_config(self, service_id: str) -> Optional[Any]:
        """Get current configuration for a service."""
        return await self._integration.get_service_config(service_id)

    async def get_config_recommendations(
        self,
        service_id: str,
        min_confidence: float = 0.6,
    ) -> List[ConfigRecommendation]:
        """Get configuration recommendations for a service."""
        return await self._integration.get_config_recommendations(service_id, min_confidence)

    async def apply_config_recommendation(
        self,
        service_id: str,
        recommendation: ConfigRecommendation,
    ) -> Any:
        """Apply a configuration recommendation."""
        return await self._integration.apply_config_recommendation(service_id, recommendation)

    async def get_service_adaptation_stats(
        self, service_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get adaptation statistics."""
        return await self._integration.get_service_adaptation_stats(service_id)

    # ==================== Evolution (EvolutionFacade) ====================

    def get_capability_evolver(self) -> Any:
        """Get the capability evolver."""
        return self._evolution.get_capability_evolver()

    async def evolve_capabilities(
        self, agent_code: str, window_hours: int = 168
    ) -> List[NewCapability]:
        """Evolve capabilities for an agent based on demand patterns."""
        return await self._evolution.evolve_capabilities(agent_code, window_hours)

    async def get_agent_capabilities(
        self,
        agent_code: str,
        status: Optional[EvolutionStatus] = None,
    ) -> List[NewCapability]:
        """Get capabilities for an agent."""
        return await self._evolution.get_agent_capabilities(agent_code, status)

    async def get_active_capabilities(
        self, agent_code: Optional[str] = None
    ) -> List[NewCapability]:
        """Get all active capabilities."""
        return await self._evolution.get_active_capabilities(agent_code)

    async def get_demand_gaps(
        self,
        agent_code: Optional[str] = None,
        min_severity: float = 0.0,
    ) -> List[DemandGap]:
        """Get detected demand gaps."""
        return await self._evolution.get_demand_gaps(agent_code, min_severity)

    async def start_capability_testing(self, capability_id: str) -> bool:
        """Start testing a proposed capability."""
        return await self._evolution.start_capability_testing(capability_id)

    async def record_capability_usage(
        self,
        capability_id: str,
        success: bool,
        duration_ms: float = 0.0,
    ) -> None:
        """Record usage of a capability."""
        await self._evolution.record_capability_usage(capability_id, success, duration_ms)

    def get_pattern_propagator(self) -> Any:
        """Get the pattern propagator."""
        return self._evolution.get_pattern_propagator()

    async def propagate_patterns(self, window_hours: int = 168) -> PropagationResult:
        """Propagate successful patterns to similar agents."""
        return await self._evolution.propagate_patterns(window_hours)

    async def get_propagation_candidates(self, limit: int = 20) -> List[tuple]:
        """Get patterns that are candidates for propagation."""
        return await self._evolution.get_propagation_candidates(limit)

    async def get_agent_similarity(self, agent1: str, agent2: str) -> AgentSimilarity:
        """Get similarity between two agents."""
        return await self._evolution.get_agent_similarity(agent1, agent2)

    async def get_propagation_records(
        self,
        pattern_id: Optional[str] = None,
        target_agent: Optional[str] = None,
    ) -> List[PropagationRecord]:
        """Get propagation records."""
        return await self._evolution.get_propagation_records(pattern_id, target_agent)

    def get_failure_investigator(self) -> Any:
        """Get the failure investigator."""
        return self._evolution.get_failure_investigator()

    async def investigate_failure(self, outcome: TaskOutcomeRecord) -> Investigation:
        """Investigate a specific failure."""
        return await self._evolution.investigate_failure(outcome)

    async def investigate_failures_batch(
        self,
        window_hours: int = 24,
        min_failure_rate: float = 0.1,
    ) -> List[Investigation]:
        """Investigate failures in batch."""
        return await self._evolution.investigate_failures_batch(window_hours, min_failure_rate)

    async def get_investigation(self, investigation_id: str) -> Optional[Investigation]:
        """Get an investigation by ID."""
        return await self._evolution.get_investigation(investigation_id)

    async def get_investigations(
        self,
        task_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Investigation]:
        """Get investigations with optional filters."""
        return await self._evolution.get_investigations(task_type, limit)

    async def get_common_root_causes(self, window_hours: int = 168, limit: int = 10) -> List[tuple]:
        """Get the most common root causes."""
        return await self._evolution.get_common_root_causes(window_hours, limit)

    async def get_auto_applicable_fixes(self) -> List[RecommendedFix]:
        """Get all auto-applicable fixes from recent investigations."""
        return await self._evolution.get_auto_applicable_fixes()

    async def run_feedback_cycle(self, window_hours: int = 24) -> Dict[str, Any]:
        """Run a complete feedback cycle (Phase 8)."""
        return await self._evolution.run_feedback_cycle(window_hours)

    # ==================== Intelligence (IntelligenceFacade) ====================

    def get_demand_forecaster(self) -> Any:
        """Get the demand forecaster."""
        return self._intelligence.get_demand_forecaster()

    async def forecast_demand(
        self,
        horizon_hours: int = 24,
        history_hours: Optional[int] = None,
        agent_filter: Optional[str] = None,
    ) -> DemandForecast:
        """Forecast task demand for the specified horizon."""
        return await self._intelligence.forecast_demand(horizon_hours, history_hours, agent_filter)

    async def get_demand_anomalies(
        self, hours: int = 24, threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Detect demand anomalies in recent history."""
        return await self._intelligence.get_demand_anomalies(hours, threshold)

    async def save_demand_forecast(self, forecast: DemandForecast) -> None:
        """Save a forecast for historical tracking."""
        await self._intelligence.save_demand_forecast(forecast)

    def get_cascade_predictor(self) -> Any:
        """Get the cascade predictor."""
        return self._intelligence.get_cascade_predictor()

    async def predict_cascade(
        self,
        task_type: str,
        selected_agent: str,
        context: Optional[Dict[str, Any]] = None,
        priority: int = 1,
        estimated_duration_ms: float = 0.0,
    ) -> CascadeEffect:
        """Predict cascade effects of a routing decision."""
        return await self._intelligence.predict_cascade(
            task_type=task_type,
            selected_agent=selected_agent,
            context=context,
            priority=priority,
            estimated_duration_ms=estimated_duration_ms,
        )

    async def record_cascade_outcome(
        self,
        prediction_id: str,
        actual_duration_ms: float,
        had_failures: bool,
        downstream_agents_used: List[str],
    ) -> None:
        """Record actual cascade outcome for learning."""
        await self._intelligence.record_cascade_outcome(
            prediction_id=prediction_id,
            actual_duration_ms=actual_duration_ms,
            had_failures=had_failures,
            downstream_agents_used=downstream_agents_used,
        )

    async def get_cascade_accuracy(self, window_hours: int = 168) -> Dict[str, Any]:
        """Get prediction accuracy for cascade predictions."""
        return await self._intelligence.get_cascade_accuracy(window_hours)

    def set_agent_capacity(self, agent_code: str, capacity: float) -> None:
        """Set capacity for an agent (used in cascade prediction)."""
        self._intelligence.set_agent_capacity(agent_code, capacity)

    async def save_cascade_prediction(self, prediction: CascadeEffect) -> None:
        """Save a cascade prediction for tracking."""
        await self._intelligence.save_cascade_prediction(prediction)

    def get_context_optimizer(self) -> Any:
        """Get the context optimizer."""
        return self._intelligence.get_context_optimizer()

    async def optimize_task_for_context(
        self,
        task_id: str,
        task_type: str,
        priority: int,
        timeout_ms: float,
        context: ExecutionContext,
        task_context: Optional[Dict[str, Any]] = None,
    ) -> OptimizedTask:
        """Optimize a task for the current execution context."""
        return await self._intelligence.optimize_task_for_context(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            timeout_ms=timeout_ms,
            context=context,
            task_context=task_context,
        )

    async def record_optimization_outcome(
        self,
        optimization_id: str,
        outcome_success: bool,
        actual_duration_ms: float,
    ) -> None:
        """Record outcome of an optimization for learning."""
        await self._intelligence.record_optimization_outcome(
            optimization_id=optimization_id,
            outcome_success=outcome_success,
            actual_duration_ms=actual_duration_ms,
        )

    async def get_optimization_stats(self, window_hours: int = 168) -> Dict[str, Any]:
        """Get optimization effectiveness statistics."""
        return await self._intelligence.get_optimization_stats(window_hours)

    async def save_optimization(self, optimization: OptimizedTask) -> None:
        """Save an optimization record for tracking."""
        await self._intelligence.save_optimization(optimization)

    async def run_predictive_cycle(self, horizon_hours: int = 24) -> Dict[str, Any]:
        """Run a complete predictive intelligence cycle (Phase 9)."""
        return await self._intelligence.run_predictive_cycle(horizon_hours)

    # ==================== Advanced Autonomy (AdvancedAutonomyFacade) ====================

    async def evaluate_architecture(
        self, window_hours: int = 168
    ) -> Optional[ArchitectureProposal]:
        """Evaluate current system architecture and propose improvements."""
        return await self._advanced_autonomy.evaluate_architecture(window_hours)

    async def approve_architecture_proposal(
        self,
        proposal_id: str,
        approved: bool,
        approver: str,
        notes: Optional[str] = None,
    ) -> bool:
        """Approve or reject an architecture proposal."""
        return await self._advanced_autonomy.approve_architecture_proposal(
            proposal_id, approved, approver, notes
        )

    async def implement_architecture_proposal(self, proposal_id: str) -> bool:
        """Implement an approved architecture proposal."""
        return await self._advanced_autonomy.implement_architecture_proposal(proposal_id)

    async def get_architecture_proposals(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get architecture proposals."""
        return await self._advanced_autonomy.get_architecture_proposals(status, limit)

    async def get_architecture_stats(self, window_hours: int = 168) -> Dict[str, Any]:
        """Get architecture evaluation statistics."""
        return await self._advanced_autonomy.get_architecture_stats(window_hours)

    async def verify_decision_alignment(
        self,
        decision_id: str,
        action: str,
        category: str,
        context: Optional[Dict[str, Any]] = None,
        impact_level: str = "medium",
    ) -> Optional[AlignmentScore]:
        """Verify that a decision aligns with user, system, and safety goals."""
        return await self._advanced_autonomy.verify_decision_alignment(
            decision_id=decision_id,
            action=action,
            category=category,
            context=context,
            impact_level=impact_level,
        )

    async def add_alignment_goal(
        self,
        goal_type: str,
        priority: str,
        description: str,
        criteria: Optional[Dict[str, Any]] = None,
        weight: float = 1.0,
    ) -> str:
        """Add a new alignment goal."""
        return await self._advanced_autonomy.add_alignment_goal(
            goal_type, priority, description, criteria, weight
        )

    async def get_alignment_goals(
        self,
        goal_type: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get alignment goals."""
        return await self._advanced_autonomy.get_alignment_goals(goal_type, active_only)

    async def get_alignment_history(
        self,
        window_hours: int = 168,
        alignment_level: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get alignment verification history."""
        return await self._advanced_autonomy.get_alignment_history(window_hours, alignment_level)

    async def get_alignment_stats(self, window_hours: int = 168) -> Dict[str, Any]:
        """Get alignment verification statistics."""
        return await self._advanced_autonomy.get_alignment_stats(window_hours)

    async def optimize_handoffs(self, window_hours: int = 168) -> Optional[HandoffStrategy]:
        """Optimize human handoff strategy based on approval history."""
        return await self._advanced_autonomy.optimize_handoffs(window_hours)

    async def record_approval(
        self,
        action: str,
        category: str,
        approved: bool,
        time_to_decision_ms: float = 0.0,
        approver: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        """Record a human approval decision."""
        return await self._advanced_autonomy.record_approval(
            action, category, approved, time_to_decision_ms, approver, notes
        )

    async def get_trust_level(self, action: str, category: str) -> str:
        """Get the current trust level for an action."""
        return await self._advanced_autonomy.get_trust_level(action, category)

    async def promote_action(
        self,
        action: str,
        category: str,
        new_trust_level: str,
        changed_by: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Manually promote an action to a higher trust level."""
        return await self._advanced_autonomy.promote_action(
            action, category, new_trust_level, changed_by, reason
        )

    async def demote_action(
        self,
        action: str,
        category: str,
        new_trust_level: str,
        changed_by: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Manually demote an action to a lower trust level."""
        return await self._advanced_autonomy.demote_action(
            action, category, new_trust_level, changed_by, reason
        )

    async def get_handoff_stats(self, window_hours: int = 168) -> Dict[str, Any]:
        """Get handoff optimization statistics."""
        return await self._advanced_autonomy.get_handoff_stats(window_hours)

    async def get_trust_changes(
        self,
        action: Optional[str] = None,
        window_hours: int = 168,
    ) -> List[Dict[str, Any]]:
        """Get history of trust level changes."""
        return await self._advanced_autonomy.get_trust_changes(action, window_hours)

    async def run_autonomy_cycle(self) -> Dict[str, Any]:
        """Run a full autonomy optimization cycle."""
        return await self._advanced_autonomy.run_autonomy_cycle()

    # ==================== Metacognition (MetacognitionFacade) ====================

    def connect_metacognition_service(self, service: Any) -> None:
        """Connect a MetacognitionService to the learning system."""
        self._metacognition.connect_service(service)

    def get_personality_insights(self) -> Dict[str, Any]:
        """Get personality insights from the metacognition system."""
        return self._metacognition.get_personality_insights()

    @property
    def metacognition(self) -> "MetacognitionFacade":
        """Direct access to MetacognitionFacade."""
        return self._metacognition

    # ==================== Nexus Sync ====================

    def set_nexus_sync_bridge(self, sync_bridge) -> None:
        """
        Set the Nexus sync bridge for forwarding learning data.

        Args:
            sync_bridge: NexusSyncBridge instance

        Example:
            ```python
            from ag3ntwerk.learning.nexus_sync import NexusSyncBridge

            sync_bridge = NexusSyncBridge(nexus_bridge)
            orchestrator.set_nexus_sync_bridge(sync_bridge)
            await sync_bridge.start_periodic_sync()
            ```
        """
        self._nexus_sync_bridge = sync_bridge
        logger.info("Nexus sync bridge configured", component="orchestrator")

    def get_nexus_sync_bridge(self):
        """Get the configured Nexus sync bridge."""
        return self._nexus_sync_bridge

    async def sync_to_nexus(self, window_hours: int = 24) -> Dict[str, int]:
        """
        Perform a full sync of learning data to Nexus.

        Args:
            window_hours: Time window for data to sync

        Returns:
            Dict with counts of synced items
        """
        if not self._nexus_sync_bridge:
            logger.warning("No Nexus sync bridge configured", component="orchestrator")
            return {"outcomes": 0, "patterns": 0, "aggregates": 0}

        return await self._nexus_sync_bridge.full_sync(
            outcome_tracker=self._outcome_tracker,
            pattern_store=self._pattern_store,
            window_hours=window_hours,
        )

    def get_nexus_sync_metrics(self) -> Dict[str, Any]:
        """Get Nexus sync metrics."""
        if not self._nexus_sync_bridge:
            return {"configured": False}

        return {
            "configured": True,
            **self._nexus_sync_bridge.get_metrics(),
        }

    # ==================== Stats ====================

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all facades."""
        core_stats = await self._core.get_stats()

        return {
            # Legacy keys for backward compatibility
            "loops": {
                "agents": core_stats.get("agent_loops", 0),
                "managers": core_stats.get("manager_loops", 0),
                "specialists": core_stats.get("specialist_loops", 0),
            },
            "patterns": core_stats.get("pattern_stats", {}),
            "issues": core_stats.get("issue_stats", {}),
            # Facade stats
            "core": core_stats,
            "routing": await self._routing.get_stats(),
            "prediction": await self._prediction.get_stats(),
            "experimentation": await self._experimentation.get_stats(),
            "proactive": await self._proactive.get_stats(),
            "autonomy": await self._autonomy.get_stats(),
            "integration": await self._integration.get_stats(),
            "evolution": await self._evolution.get_stats(),
            "intelligence": await self._intelligence.get_stats(),
            "advanced_autonomy": await self._advanced_autonomy.get_stats(),
            "metacognition": await self._metacognition.get_stats(),
            "nexus_sync": self.get_nexus_sync_metrics(),
        }

    # ==================== Direct Facade Access (for advanced usage) ====================

    @property
    def core(self) -> CoreLearningFacade:
        """Direct access to CoreLearningFacade."""
        return self._core

    @property
    def routing(self) -> RoutingFacade:
        """Direct access to RoutingFacade."""
        return self._routing

    @property
    def prediction(self) -> PredictionFacade:
        """Direct access to PredictionFacade."""
        return self._prediction

    @property
    def experimentation(self) -> ExperimentationFacade:
        """Direct access to ExperimentationFacade."""
        return self._experimentation

    @property
    def proactive(self) -> ProactiveFacade:
        """Direct access to ProactiveFacade."""
        return self._proactive

    @property
    def autonomy(self) -> AutonomyFacade:
        """Direct access to AutonomyFacade."""
        return self._autonomy

    @property
    def integration(self) -> IntegrationFacade:
        """Direct access to IntegrationFacade."""
        return self._integration

    @property
    def evolution(self) -> EvolutionFacade:
        """Direct access to EvolutionFacade."""
        return self._evolution

    @property
    def intelligence(self) -> IntelligenceFacade:
        """Direct access to IntelligenceFacade."""
        return self._intelligence

    @property
    def advanced_autonomy(self) -> AdvancedAutonomyFacade:
        """Direct access to AdvancedAutonomyFacade."""
        return self._advanced_autonomy

    # Legacy accessors for backward compatibility
    @property
    def _continuous_pipeline(self) -> Optional[ContinuousLearningPipeline]:
        """Legacy accessor for continuous pipeline."""
        return self._autonomy.continuous_pipeline

    @property
    def _agent_loops(self) -> Dict[str, Any]:
        """Legacy accessor for agent loops."""
        return self._core.agent_loops

    @property
    def _manager_loops(self) -> Dict[str, Any]:
        """Legacy accessor for manager loops."""
        return self._core.manager_loops

    @property
    def _specialist_loops(self) -> Dict[str, Any]:
        """Legacy accessor for specialist loops."""
        return self._core.specialist_loops

    @property
    def _self_architect(self) -> Any:
        """Legacy accessor for self architect."""
        return self._advanced_autonomy.self_architect

    @property
    def _goal_aligner(self) -> Any:
        """Legacy accessor for goal aligner."""
        return self._advanced_autonomy.goal_aligner

    @property
    def _handoff_optimizer(self) -> Any:
        """Legacy accessor for handoff optimizer."""
        return self._advanced_autonomy.handoff_optimizer


# Singleton instance
_learning_orchestrator: Optional[LearningOrchestrator] = None


def get_learning_orchestrator(
    db: Any = None,
    task_queue: Optional[Any] = None,
) -> LearningOrchestrator:
    """
    Get the singleton Learning Orchestrator instance.

    Args:
        db: Database connection (required on first call)
        task_queue: Optional task queue

    Returns:
        LearningOrchestrator instance
    """
    global _learning_orchestrator

    if _learning_orchestrator is None:
        if db is None:
            raise ValueError("db is required when creating orchestrator")
        _learning_orchestrator = LearningOrchestrator(db, task_queue)

    return _learning_orchestrator


def reset_learning_orchestrator() -> None:
    """Reset the singleton instance (for testing)."""
    global _learning_orchestrator
    _learning_orchestrator = None


async def initialize_learning_orchestrator(
    db: Any,
    task_queue: Optional[Any] = None,
) -> LearningOrchestrator:
    """
    Initialize and return the Learning Orchestrator.

    This is an async wrapper around get_learning_orchestrator that calls
    initialize() on the orchestrator. Use this for backward compatibility.

    Args:
        db: Database connection
        task_queue: Optional task queue

    Returns:
        Initialized LearningOrchestrator instance
    """
    orchestrator = get_learning_orchestrator(db, task_queue)
    await orchestrator.initialize()
    return orchestrator
