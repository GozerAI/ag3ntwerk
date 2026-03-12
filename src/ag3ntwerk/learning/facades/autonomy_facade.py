"""
Autonomy Facade - Autonomy control and continuous learning pipeline.

This facade manages autonomy components:
- AutonomyController: Controls autonomous action approval/execution
- ContinuousLearningPipeline: Background learning cycle management
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

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

if TYPE_CHECKING:
    from ag3ntwerk.learning.meta_learner import MetaLearner
    from ag3ntwerk.learning.opportunity_detector import OpportunityDetector
    from ag3ntwerk.learning.pattern_experiment import PatternExperimenter
    from ag3ntwerk.learning.proactive_generator import ProactiveTaskGenerator

logger = logging.getLogger(__name__)


class AutonomyFacade:
    """
    Facade for autonomy operations.

    Manages autonomy control and the continuous learning pipeline
    that enables autonomous learning behavior.
    """

    def __init__(
        self,
        db: Any,
    ):
        """
        Initialize the autonomy facade.

        Args:
            db: Database connection
        """
        self._db = db
        self._autonomy_controller = AutonomyController(db)
        self._continuous_pipeline: Optional[ContinuousLearningPipeline] = None

        # Store references to components needed for pipeline initialization
        # These are set later via set_pipeline_dependencies
        self._orchestrator = None
        self._experimenter = None
        self._meta_learner = None
        self._opportunity_detector = None
        self._proactive_generator = None

    def set_pipeline_dependencies(
        self,
        orchestrator: Any,
        experimenter: "PatternExperimenter",
        meta_learner: "MetaLearner",
        opportunity_detector: "OpportunityDetector",
        proactive_generator: "ProactiveTaskGenerator",
    ) -> None:
        """
        Set dependencies needed for pipeline initialization.

        Called by orchestrator after facade construction.

        Args:
            orchestrator: Parent orchestrator instance
            experimenter: Pattern experimenter instance
            meta_learner: Meta learner instance
            opportunity_detector: Opportunity detector instance
            proactive_generator: Proactive task generator instance
        """
        self._orchestrator = orchestrator
        self._experimenter = experimenter
        self._meta_learner = meta_learner
        self._opportunity_detector = opportunity_detector
        self._proactive_generator = proactive_generator

    # --- Autonomy Controller ---

    def get_autonomy_controller(self) -> AutonomyController:
        """Get the autonomy controller."""
        return self._autonomy_controller

    def check_autonomy(
        self,
        action: str,
        category: Optional[ActionCategory] = None,
    ) -> AutonomyDecision:
        """
        Check autonomy level for an action.

        Args:
            action: Action name
            category: Optional action category

        Returns:
            AutonomyDecision with proceed/approval requirements
        """
        return self._autonomy_controller.check_autonomy(action, category)

    async def request_approval(
        self,
        action: str,
        category: ActionCategory,
        description: str,
        impact_assessment: str = "",
        recommended_decision: bool = True,
    ) -> PendingApproval:
        """
        Request human approval for an action.

        Args:
            action: Action name
            category: Action category
            description: Human-readable description
            impact_assessment: Assessment of potential impact
            recommended_decision: Whether system recommends approval

        Returns:
            PendingApproval object
        """
        return await self._autonomy_controller.request_approval(
            action=action,
            category=category,
            description=description,
            impact_assessment=impact_assessment,
            recommended_decision=recommended_decision,
        )

    async def approve_action(
        self,
        approval_id: str,
        approver: str = "human",
    ) -> bool:
        """Approve a pending action."""
        return await self._autonomy_controller.approve(approval_id, approver)

    async def deny_action(
        self,
        approval_id: str,
        denier: str = "human",
        reason: str = "",
    ) -> bool:
        """Deny a pending action."""
        return await self._autonomy_controller.deny(approval_id, denier, reason)

    def get_pending_approvals(self) -> List[PendingApproval]:
        """Get all pending approval requests."""
        return self._autonomy_controller.get_pending_approvals()

    def set_autonomy_level(
        self,
        category: ActionCategory,
        level: AutonomyLevel,
    ) -> None:
        """Set the autonomy level for a category."""
        self._autonomy_controller.set_autonomy_level(category, level)

    async def get_autonomy_stats(self) -> Dict[str, Any]:
        """Get autonomy controller statistics."""
        return await self._autonomy_controller.get_stats()

    # --- Continuous Pipeline ---

    async def initialize_continuous_pipeline(
        self,
        config: Optional[PipelineConfig] = None,
    ) -> ContinuousLearningPipeline:
        """
        Initialize and return the continuous learning pipeline.

        Args:
            config: Optional pipeline configuration

        Returns:
            Initialized pipeline
        """
        if self._orchestrator is None:
            raise RuntimeError(
                "Pipeline dependencies not set. " "Call set_pipeline_dependencies() first."
            )

        self._continuous_pipeline = ContinuousLearningPipeline(
            orchestrator=self._orchestrator,
            experimenter=self._experimenter,
            meta_learner=self._meta_learner,
            opportunity_detector=self._opportunity_detector,
            proactive_generator=self._proactive_generator,
            autonomy_controller=self._autonomy_controller,
            config=config,
        )
        return self._continuous_pipeline

    async def start_continuous_pipeline(self) -> bool:
        """
        Start the continuous learning pipeline.

        Returns:
            True if started successfully
        """
        if not self._continuous_pipeline:
            await self.initialize_continuous_pipeline()

        return await self._continuous_pipeline.start()

    async def stop_continuous_pipeline(self, timeout: float = 30.0) -> bool:
        """
        Stop the continuous learning pipeline.

        Args:
            timeout: Maximum time to wait for clean shutdown

        Returns:
            True if stopped successfully
        """
        if not self._continuous_pipeline:
            return True

        return await self._continuous_pipeline.stop(timeout)

    async def pause_continuous_pipeline(self) -> bool:
        """Pause the continuous learning pipeline."""
        if not self._continuous_pipeline:
            return False
        return await self._continuous_pipeline.pause()

    async def resume_continuous_pipeline(self) -> bool:
        """Resume the continuous learning pipeline."""
        if not self._continuous_pipeline:
            return False
        return await self._continuous_pipeline.resume()

    async def run_single_learning_cycle(self) -> CycleResult:
        """
        Run a single learning cycle manually.

        Returns:
            CycleResult with metrics
        """
        if not self._continuous_pipeline:
            await self.initialize_continuous_pipeline()

        return await self._continuous_pipeline.run_single_cycle()

    def get_pipeline_state(self) -> PipelineState:
        """Get current pipeline state."""
        if not self._continuous_pipeline:
            return PipelineState.STOPPED
        return self._continuous_pipeline.state

    def is_pipeline_running(self) -> bool:
        """Check if pipeline is running."""
        if not self._continuous_pipeline:
            return False
        return self._continuous_pipeline.is_running

    async def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        if not self._continuous_pipeline:
            return {"state": "not_initialized"}
        return await self._continuous_pipeline.get_stats()

    def get_pipeline_cycle_history(
        self,
        limit: int = 20,
        success_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get recent pipeline cycle history."""
        if not self._continuous_pipeline:
            return []
        return self._continuous_pipeline.get_cycle_history(limit, success_only)

    async def pipeline_health_check(self) -> Dict[str, Any]:
        """Perform a health check on the pipeline."""
        if not self._continuous_pipeline:
            return {"healthy": False, "issues": ["Pipeline not initialized"]}
        return await self._continuous_pipeline.health_check()

    def update_pipeline_config(self, **kwargs) -> None:
        """Update pipeline configuration."""
        if self._continuous_pipeline:
            self._continuous_pipeline.update_config(**kwargs)

    # --- Stats ---

    async def get_stats(self) -> Dict[str, Any]:
        """Get autonomy facade statistics."""
        stats = {
            "autonomy_controller": await self._autonomy_controller.get_stats(),
        }
        if self._continuous_pipeline:
            stats["continuous_pipeline"] = await self._continuous_pipeline.get_stats()
        else:
            stats["continuous_pipeline"] = {"state": "not_initialized"}
        return stats

    # --- Accessors for components (used by orchestrator) ---

    @property
    def autonomy_controller(self) -> AutonomyController:
        """Get autonomy controller."""
        return self._autonomy_controller

    @property
    def continuous_pipeline(self) -> Optional[ContinuousLearningPipeline]:
        """Get continuous pipeline (may be None if not initialized)."""
        return self._continuous_pipeline
