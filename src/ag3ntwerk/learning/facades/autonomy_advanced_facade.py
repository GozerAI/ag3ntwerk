"""
Advanced Autonomy Facade - Self-architecture, goal alignment, and handoff optimization.

This facade manages true autonomy components:
- SelfArchitect: Evaluates and proposes architecture improvements
- GoalAligner: Verifies decision alignment with goals
- HandoffOptimizer: Optimizes human-AI handoff strategy
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.learning.goal_aligner import (
    GoalAligner,
    Goal,
    GoalType,
    GoalPriority,
    AlignmentScore,
    AlignmentLevel,
    AutonomousDecision,
)
from ag3ntwerk.learning.handoff_optimizer import (
    HandoffOptimizer,
    HandoffStrategy,
    TrustLevel,
    ActionTrust,
    PromotableAction,
)
from ag3ntwerk.learning.outcome_tracker import OutcomeTracker
from ag3ntwerk.learning.pattern_store import PatternStore
from ag3ntwerk.learning.self_architect import (
    SelfArchitect,
    ArchitectureProposal,
    ProposalType,
    ProposalStatus,
    Bottleneck,
    AgentProposal,
)

logger = logging.getLogger(__name__)


class AdvancedAutonomyFacade:
    """
    Facade for advanced autonomy operations.

    Manages self-architecture proposals, goal alignment verification,
    and human-AI handoff optimization.
    """

    def __init__(
        self,
        db: Any,
        outcome_tracker: OutcomeTracker,
        pattern_store: PatternStore,
    ):
        """
        Initialize the advanced autonomy facade.

        Args:
            db: Database connection
            outcome_tracker: Shared outcome tracker instance
            pattern_store: Shared pattern store instance
        """
        self._db = db
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store
        self._self_architect = SelfArchitect(db, outcome_tracker, pattern_store)
        self._goal_aligner = GoalAligner(db, outcome_tracker, pattern_store)
        self._handoff_optimizer = HandoffOptimizer(db, outcome_tracker, pattern_store)

    # --- Self-Architecture ---

    async def evaluate_architecture(
        self, window_hours: int = 168
    ) -> Optional[ArchitectureProposal]:
        """
        Evaluate current system architecture and propose improvements.

        Uses SelfArchitect to identify bottlenecks, underutilized agents,
        and capability gaps, then proposes architectural changes.

        Args:
            window_hours: Hours of history to analyze

        Returns:
            ArchitectureProposal with suggested changes, or None if not available
        """
        return await self._self_architect.evaluate_architecture(window_hours)

    async def approve_architecture_proposal(
        self,
        proposal_id: str,
        approved: bool,
        approver: str,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Approve or reject an architecture proposal.

        Args:
            proposal_id: ID of the proposal
            approved: Whether to approve the proposal
            approver: Who approved/rejected
            notes: Optional notes about the decision

        Returns:
            True if processed successfully
        """
        return await self._self_architect.process_approval(proposal_id, approved, approver, notes)

    async def implement_architecture_proposal(self, proposal_id: str) -> bool:
        """
        Implement an approved architecture proposal.

        Args:
            proposal_id: ID of the approved proposal

        Returns:
            True if implemented successfully
        """
        return await self._self_architect.implement_proposal(proposal_id)

    async def get_architecture_proposals(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get architecture proposals.

        Args:
            status: Optional status filter (proposed, approved, rejected, implemented)
            limit: Maximum proposals to return

        Returns:
            List of proposal dictionaries
        """
        return await self._self_architect.get_proposals(status, limit)

    async def get_architecture_stats(self, window_hours: int = 168) -> Dict[str, Any]:
        """
        Get architecture evaluation statistics.

        Args:
            window_hours: Hours of history to analyze

        Returns:
            Statistics about bottlenecks, utilization, and proposals
        """
        return await self._self_architect.get_stats(window_hours)

    # --- Goal Alignment ---

    async def verify_decision_alignment(
        self,
        decision_id: str,
        action: str,
        category: str,
        context: Optional[Dict[str, Any]] = None,
        impact_level: str = "medium",
    ) -> Optional[AlignmentScore]:
        """
        Verify that a decision aligns with user, system, and safety goals.

        Args:
            decision_id: Unique identifier for the decision
            action: The action being taken
            category: Category of the action
            context: Optional context information
            impact_level: Impact level (low, medium, high, critical)

        Returns:
            AlignmentScore with alignment measurements and recommendation
        """
        decision = AutonomousDecision(
            decision_id=decision_id,
            action=action,
            category=category,
            context=context or {},
            impact_level=impact_level,
        )

        return await self._goal_aligner.verify_alignment(decision)

    async def add_alignment_goal(
        self,
        goal_type: str,
        priority: str,
        description: str,
        criteria: Optional[Dict[str, Any]] = None,
        weight: float = 1.0,
    ) -> str:
        """
        Add a new alignment goal.

        Args:
            goal_type: Type of goal (user, system, safety, performance, efficiency)
            priority: Priority level (critical, high, medium, low)
            description: Description of the goal
            criteria: Optional criteria for measuring alignment
            weight: Weight for this goal in alignment calculations

        Returns:
            ID of the created goal
        """
        return await self._goal_aligner.add_goal(goal_type, priority, description, criteria, weight)

    async def get_alignment_goals(
        self,
        goal_type: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get alignment goals.

        Args:
            goal_type: Optional type filter
            active_only: Whether to return only active goals

        Returns:
            List of goal dictionaries
        """
        return await self._goal_aligner.get_goals(goal_type, active_only)

    async def get_alignment_history(
        self,
        window_hours: int = 168,
        alignment_level: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get alignment verification history.

        Args:
            window_hours: Hours of history to retrieve
            alignment_level: Optional filter by alignment level

        Returns:
            List of alignment result dictionaries
        """
        return await self._goal_aligner.get_alignment_history(window_hours, alignment_level)

    async def get_alignment_stats(self, window_hours: int = 168) -> Dict[str, Any]:
        """
        Get alignment verification statistics.

        Args:
            window_hours: Hours of history to analyze

        Returns:
            Statistics about alignment verification results
        """
        return await self._goal_aligner.get_stats(window_hours)

    # --- Handoff Optimization ---

    async def optimize_handoffs(self, window_hours: int = 168) -> Optional[HandoffStrategy]:
        """
        Optimize human handoff strategy based on approval history.

        Analyzes past approvals to identify actions that can be promoted
        to higher autonomy levels or demoted due to failures.

        Args:
            window_hours: Hours of history to analyze

        Returns:
            HandoffStrategy with optimization recommendations
        """
        return await self._handoff_optimizer.optimize_handoffs(window_hours)

    async def record_approval(
        self,
        action: str,
        category: str,
        approved: bool,
        time_to_decision_ms: float = 0.0,
        approver: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        """
        Record a human approval decision.

        Args:
            action: The action that was approved/rejected
            category: Category of the action
            approved: Whether it was approved
            time_to_decision_ms: How long the decision took
            approver: Who made the decision
            notes: Optional notes

        Returns:
            ID of the recorded approval
        """
        return await self._handoff_optimizer.record_approval(
            action, category, approved, time_to_decision_ms, approver, notes
        )

    async def get_trust_level(self, action: str, category: str) -> str:
        """
        Get the current trust level for an action.

        Args:
            action: The action to check
            category: Category of the action

        Returns:
            Trust level (untrusted, low, medium, high, full)
        """
        return await self._handoff_optimizer.get_trust_level(action, category)

    async def promote_action(
        self,
        action: str,
        category: str,
        new_trust_level: str,
        changed_by: str,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Manually promote an action to a higher trust level.

        Args:
            action: The action to promote
            category: Category of the action
            new_trust_level: The new trust level
            changed_by: Who authorized the change
            reason: Optional reason for the change

        Returns:
            True if promoted successfully
        """
        return await self._handoff_optimizer.promote_action(
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
        """
        Manually demote an action to a lower trust level.

        Args:
            action: The action to demote
            category: Category of the action
            new_trust_level: The new trust level
            changed_by: Who authorized the change
            reason: Optional reason for the change

        Returns:
            True if demoted successfully
        """
        return await self._handoff_optimizer.demote_action(
            action, category, new_trust_level, changed_by, reason
        )

    async def get_handoff_stats(self, window_hours: int = 168) -> Dict[str, Any]:
        """
        Get handoff optimization statistics.

        Args:
            window_hours: Hours of history to analyze

        Returns:
            Statistics about approvals, trust levels, and handoff rates
        """
        return await self._handoff_optimizer.get_stats(window_hours)

    async def get_trust_changes(
        self,
        action: Optional[str] = None,
        window_hours: int = 168,
    ) -> List[Dict[str, Any]]:
        """
        Get history of trust level changes.

        Args:
            action: Optional action filter
            window_hours: Hours of history to retrieve

        Returns:
            List of trust change records
        """
        return await self._handoff_optimizer.get_trust_changes(action, window_hours)

    # --- Orchestration ---

    async def run_autonomy_cycle(self) -> Dict[str, Any]:
        """
        Run a full autonomy optimization cycle.

        This includes:
        - Architecture evaluation
        - Alignment verification stats
        - Handoff optimization

        Returns:
            Combined results from all autonomy components
        """
        results: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "architecture": None,
            "alignment": None,
            "handoff": None,
        }

        # Evaluate architecture
        try:
            proposal = await self.evaluate_architecture()
            if proposal:
                results["architecture"] = {
                    "proposal_id": proposal.id,
                    "agents_to_add": len(proposal.agents_to_add),
                    "agents_to_merge": len(proposal.agents_to_merge),
                    "agents_to_split": len(proposal.agents_to_split),
                    "agents_to_remove": len(proposal.agents_to_remove),
                    "estimated_improvement": proposal.estimated_improvement,
                    "risk_assessment": proposal.risk_assessment,
                }
        except Exception as e:
            logger.error(f"Architecture evaluation failed: {e}")
            results["architecture"] = {"error": str(e)}

        # Get alignment stats
        try:
            alignment_stats = await self.get_alignment_stats()
            results["alignment"] = alignment_stats
        except Exception as e:
            logger.error(f"Alignment stats failed: {e}")
            results["alignment"] = {"error": str(e)}

        # Optimize handoffs
        try:
            strategy = await self.optimize_handoffs()
            if strategy:
                results["handoff"] = {
                    "strategy_id": strategy.id,
                    "actions_to_promote": len(strategy.actions_to_promote),
                    "actions_to_demote": len(strategy.actions_to_demote),
                    "estimated_savings_hours": strategy.estimated_savings_hours,
                    "estimated_risk": strategy.estimated_risk,
                    "current_handoff_rate": strategy.current_handoff_rate,
                    "projected_handoff_rate": strategy.projected_handoff_rate,
                }
        except Exception as e:
            logger.error(f"Handoff optimization failed: {e}")
            results["handoff"] = {"error": str(e)}

        return results

    # --- Stats ---

    async def get_stats(self) -> Dict[str, Any]:
        """Get advanced autonomy facade statistics."""
        return {
            "self_architect": await self._self_architect.get_stats(),
            "goal_aligner": await self._goal_aligner.get_stats(),
            "handoff_optimizer": await self._handoff_optimizer.get_stats(),
        }

    # --- Accessors for components (used by orchestrator) ---

    @property
    def self_architect(self) -> SelfArchitect:
        """Get self architect."""
        return self._self_architect

    @property
    def goal_aligner(self) -> GoalAligner:
        """Get goal aligner."""
        return self._goal_aligner

    @property
    def handoff_optimizer(self) -> HandoffOptimizer:
        """Get handoff optimizer."""
        return self._handoff_optimizer
