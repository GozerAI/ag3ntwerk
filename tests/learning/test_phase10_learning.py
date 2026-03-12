"""
Tests for Phase 10: True Autonomy.

Tests cover:
- SelfArchitect: Self-modifying architecture
- GoalAligner: Goal alignment verification
- HandoffOptimizer: Human handoff optimization
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from ag3ntwerk.learning.self_architect import (
    SelfArchitect,
    ProposalType,
    ProposalStatus,
    BottleneckType,
)
from ag3ntwerk.learning.goal_aligner import (
    GoalAligner,
    GoalType,
    GoalPriority,
    AlignmentLevel,
    ActionRecommendation,
    Goal,
    AutonomousDecision,
)
from ag3ntwerk.learning.handoff_optimizer import (
    HandoffOptimizer,
    TrustLevel,
    HandoffReason,
    PromotionStatus,
)


# =============================================================================
# SelfArchitect Tests
# =============================================================================


class TestSelfArchitectEnums:
    """Test SelfArchitect enums."""

    def test_proposal_type_values(self):
        """Test ProposalType enum values."""
        assert ProposalType.ADD_AGENT.value == "add_agent"
        assert ProposalType.REMOVE_AGENT.value == "remove_agent"
        assert ProposalType.MERGE_AGENTS.value == "merge_agents"
        assert ProposalType.SPLIT_AGENT.value == "split_agent"
        assert ProposalType.REASSIGN_CAPABILITY.value == "reassign_capability"
        assert ProposalType.ADD_CAPABILITY.value == "add_capability"

    def test_proposal_status_values(self):
        """Test ProposalStatus enum values."""
        assert ProposalStatus.PROPOSED.value == "proposed"
        assert ProposalStatus.APPROVED.value == "approved"
        assert ProposalStatus.REJECTED.value == "rejected"
        assert ProposalStatus.IMPLEMENTED.value == "implemented"
        assert ProposalStatus.ROLLED_BACK.value == "rolled_back"

    def test_bottleneck_type_values(self):
        """Test BottleneckType enum values."""
        assert BottleneckType.CAPACITY.value == "capacity"
        assert BottleneckType.LATENCY.value == "latency"
        assert BottleneckType.FAILURE_RATE.value == "failure_rate"
        assert BottleneckType.SKILL_GAP.value == "skill_gap"


class TestSelfArchitect:
    """Test SelfArchitect functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(return_value=None)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_outcome_tracker(self):
        """Create mock outcome tracker."""
        tracker = AsyncMock()
        tracker.get_outcomes = AsyncMock(return_value=[])
        return tracker

    @pytest.fixture
    def mock_pattern_store(self):
        """Create mock pattern store."""
        store = AsyncMock()
        store.get_patterns = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def architect(self, mock_db, mock_outcome_tracker, mock_pattern_store):
        """Create SelfArchitect instance."""
        return SelfArchitect(mock_db, mock_outcome_tracker, mock_pattern_store)

    @pytest.mark.asyncio
    async def test_evaluate_architecture_no_data(self, architect, mock_db):
        """Test architecture evaluation with no data."""
        mock_db.fetch_all.return_value = []

        proposal = await architect.evaluate_architecture()

        assert proposal is not None
        assert proposal.status == ProposalStatus.PROPOSED
        assert isinstance(proposal.agents_to_add, list)
        assert isinstance(proposal.agents_to_merge, list)
        assert isinstance(proposal.agents_to_split, list)
        assert isinstance(proposal.agents_to_remove, list)

    @pytest.mark.asyncio
    async def test_architect_has_required_methods(self, architect):
        """Test that SelfArchitect has all required methods."""
        assert hasattr(architect, "evaluate_architecture")
        assert hasattr(architect, "approve_proposal")
        assert hasattr(architect, "reject_proposal")
        assert hasattr(architect, "save_proposal")
        assert hasattr(architect, "get_proposal")
        assert hasattr(architect, "get_pending_proposals")
        assert hasattr(architect, "get_stats")

    @pytest.mark.asyncio
    async def test_get_stats_returns_dict(self, architect, mock_db):
        """Test get_stats returns a dictionary."""
        mock_db.fetch_one.return_value = {"count": 5}
        mock_db.fetch_all.return_value = []

        stats = await architect.get_stats()

        assert isinstance(stats, dict)
        assert "total_proposals" in stats

    @pytest.mark.asyncio
    async def test_get_pending_proposals(self, architect, mock_db):
        """Test getting pending proposals."""
        mock_db.fetch_all.return_value = []

        proposals = await architect.get_pending_proposals()

        assert isinstance(proposals, list)


# =============================================================================
# GoalAligner Tests
# =============================================================================


class TestGoalAlignerEnums:
    """Test GoalAligner enums."""

    def test_goal_type_values(self):
        """Test GoalType enum values."""
        assert GoalType.USER.value == "user"
        assert GoalType.SYSTEM.value == "system"
        assert GoalType.SAFETY.value == "safety"
        assert GoalType.PERFORMANCE.value == "performance"
        assert GoalType.EFFICIENCY.value == "efficiency"

    def test_goal_priority_values(self):
        """Test GoalPriority enum values."""
        assert GoalPriority.CRITICAL.value == "critical"
        assert GoalPriority.HIGH.value == "high"
        assert GoalPriority.MEDIUM.value == "medium"
        assert GoalPriority.LOW.value == "low"

    def test_alignment_level_values(self):
        """Test AlignmentLevel enum values."""
        assert AlignmentLevel.FULL.value == "full"
        assert AlignmentLevel.PARTIAL.value == "partial"
        assert AlignmentLevel.MISALIGNED.value == "misaligned"
        assert AlignmentLevel.CONFLICTING.value == "conflicting"

    def test_action_recommendation_values(self):
        """Test ActionRecommendation enum values."""
        assert ActionRecommendation.PROCEED.value == "proceed"
        assert ActionRecommendation.PROCEED_WITH_CAUTION.value == "proceed_with_caution"
        assert ActionRecommendation.REQUIRES_REVIEW.value == "requires_review"
        assert ActionRecommendation.BLOCK.value == "block"


class TestGoalAligner:
    """Test GoalAligner functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(return_value=None)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_outcome_tracker(self):
        """Create mock outcome tracker."""
        tracker = AsyncMock()
        return tracker

    @pytest.fixture
    def mock_pattern_store(self):
        """Create mock pattern store."""
        store = AsyncMock()
        return store

    @pytest.fixture
    def aligner(self, mock_db, mock_outcome_tracker, mock_pattern_store):
        """Create GoalAligner instance."""
        return GoalAligner(mock_db, mock_outcome_tracker, mock_pattern_store)

    @pytest.mark.asyncio
    async def test_aligner_has_required_methods(self, aligner):
        """Test that GoalAligner has all required methods."""
        assert hasattr(aligner, "verify_alignment")
        assert hasattr(aligner, "add_goal")
        assert hasattr(aligner, "remove_goal")
        assert hasattr(aligner, "get_goal")
        assert hasattr(aligner, "get_all_goals")
        assert hasattr(aligner, "get_stats")
        assert hasattr(aligner, "save_alignment_result")

    @pytest.mark.asyncio
    async def test_verify_alignment_returns_alignment_score(self, aligner, mock_db):
        """Test alignment verification returns an AlignmentScore."""
        mock_db.fetch_all.return_value = []

        decision = AutonomousDecision(
            decision_id="dec-123",
            action="test_action",
            category="test",
            description="Test decision for verification",
            impact="low",
            affected_entities=["test_entity"],
            context={},
        )

        score = await aligner.verify_alignment(decision)

        assert score is not None
        assert hasattr(score, "overall_alignment")
        assert hasattr(score, "alignment_level")
        assert hasattr(score, "recommendation")

    @pytest.mark.asyncio
    async def test_add_and_get_goal(self, aligner, mock_db):
        """Test adding a goal."""
        goal = Goal(
            goal_id="goal-123",
            goal_type=GoalType.SAFETY,
            priority=GoalPriority.CRITICAL,
            description="Test goal",
            criteria={},
            weight=1.0,
            is_active=True,
        )

        await aligner.add_goal(goal)
        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_get_all_goals(self, aligner, mock_db):
        """Test getting all goals."""
        mock_db.fetch_all.return_value = []

        goals = await aligner.get_all_goals()

        assert isinstance(goals, list)


# =============================================================================
# HandoffOptimizer Tests
# =============================================================================


class TestHandoffOptimizerEnums:
    """Test HandoffOptimizer enums."""

    def test_trust_level_values(self):
        """Test TrustLevel enum values."""
        assert TrustLevel.UNTRUSTED.value == "untrusted"
        assert TrustLevel.LOW.value == "low"
        assert TrustLevel.MEDIUM.value == "medium"
        assert TrustLevel.HIGH.value == "high"
        assert TrustLevel.FULL.value == "full"

    def test_handoff_reason_values(self):
        """Test HandoffReason enum values."""
        assert HandoffReason.NOVEL_SITUATION.value == "novel_situation"
        assert HandoffReason.LOW_CONFIDENCE.value == "low_confidence"
        assert HandoffReason.HIGH_IMPACT.value == "high_impact"
        assert HandoffReason.SAFETY_CHECK.value == "safety_check"
        assert HandoffReason.USER_PREFERENCE.value == "user_preference"
        assert HandoffReason.PATTERN_VIOLATION.value == "pattern_violation"

    def test_promotion_status_values(self):
        """Test PromotionStatus enum values."""
        assert PromotionStatus.PENDING.value == "pending"
        assert PromotionStatus.PROMOTED.value == "promoted"
        assert PromotionStatus.DEMOTED.value == "demoted"
        assert PromotionStatus.STABLE.value == "stable"


class TestHandoffOptimizer:
    """Test HandoffOptimizer functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(return_value=None)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_outcome_tracker(self):
        """Create mock outcome tracker."""
        tracker = AsyncMock()
        return tracker

    @pytest.fixture
    def mock_pattern_store(self):
        """Create mock pattern store."""
        store = AsyncMock()
        return store

    @pytest.fixture
    def optimizer(self, mock_db, mock_outcome_tracker, mock_pattern_store):
        """Create HandoffOptimizer instance."""
        return HandoffOptimizer(mock_db, mock_outcome_tracker, mock_pattern_store)

    @pytest.mark.asyncio
    async def test_optimizer_has_required_methods(self, optimizer):
        """Test that HandoffOptimizer has all required methods."""
        assert hasattr(optimizer, "optimize_handoffs")
        assert hasattr(optimizer, "record_approval")
        assert hasattr(optimizer, "promote_action")
        assert hasattr(optimizer, "demote_action")
        assert hasattr(optimizer, "get_action_trust")
        assert hasattr(optimizer, "get_all_action_trusts")
        assert hasattr(optimizer, "get_stats")
        assert hasattr(optimizer, "save_strategy")

    @pytest.mark.asyncio
    async def test_optimize_handoffs_returns_strategy(self, optimizer, mock_db):
        """Test handoff optimization returns a strategy."""
        mock_db.fetch_all.return_value = []

        strategy = await optimizer.optimize_handoffs()

        assert strategy is not None
        assert hasattr(strategy, "actions_to_promote")
        assert hasattr(strategy, "actions_to_demote")
        assert hasattr(strategy, "current_handoff_rate")
        assert hasattr(strategy, "projected_handoff_rate")

    @pytest.mark.asyncio
    async def test_record_approval(self, optimizer, mock_db):
        """Test recording an approval."""
        await optimizer.record_approval(
            approval_id="apr-123",
            action="deploy",
            category="deployment",
            approved=True,
            time_to_decision_ms=3000.0,
            approver="admin",
            notes="Production deploy",
        )

        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_get_action_trust_returns_none_for_unknown(self, optimizer, mock_db):
        """Test getting trust for unknown action returns None."""
        mock_db.fetch_one.return_value = None

        trust = await optimizer.get_action_trust("unknown_action", "unknown_category")

        assert trust is None

    @pytest.mark.asyncio
    async def test_get_all_action_trusts(self, optimizer, mock_db):
        """Test getting all action trusts."""
        mock_db.fetch_all.return_value = []

        trusts = await optimizer.get_all_action_trusts()

        assert isinstance(trusts, list)


# =============================================================================
# Orchestrator Integration Tests
# =============================================================================


class TestOrchestratorPhase10Integration:
    """Test Phase 10 integration with LearningOrchestrator."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(
            return_value={
                "count": 0,
                "success_rate": 0.9,
                "avg_duration": 2000.0,
                "sample_size": 50,
            }
        )
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_task_queue(self):
        """Create mock task queue."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_orchestrator_creates_phase10_components(self, mock_db, mock_task_queue):
        """Test orchestrator creates Phase 10 components."""
        from ag3ntwerk.learning.orchestrator import LearningOrchestrator

        orchestrator = LearningOrchestrator(mock_db, mock_task_queue)

        assert orchestrator._self_architect is not None
        assert orchestrator._goal_aligner is not None
        assert orchestrator._handoff_optimizer is not None

    @pytest.mark.asyncio
    async def test_orchestrator_evaluate_architecture(self, mock_db, mock_task_queue):
        """Test orchestrator architecture evaluation."""
        from ag3ntwerk.learning.orchestrator import LearningOrchestrator

        orchestrator = LearningOrchestrator(mock_db, mock_task_queue)

        proposal = await orchestrator.evaluate_architecture()

        assert proposal is not None

    @pytest.mark.asyncio
    async def test_orchestrator_optimize_handoffs(self, mock_db, mock_task_queue):
        """Test orchestrator handoff optimization."""
        from ag3ntwerk.learning.orchestrator import LearningOrchestrator

        orchestrator = LearningOrchestrator(mock_db, mock_task_queue)

        strategy = await orchestrator.optimize_handoffs()

        assert strategy is not None

    @pytest.mark.asyncio
    async def test_orchestrator_run_autonomy_cycle(self, mock_db, mock_task_queue):
        """Test orchestrator autonomy cycle."""
        from ag3ntwerk.learning.orchestrator import LearningOrchestrator

        orchestrator = LearningOrchestrator(mock_db, mock_task_queue)

        results = await orchestrator.run_autonomy_cycle()

        assert "timestamp" in results
        assert "architecture" in results
        assert "alignment" in results
        assert "handoff" in results


# =============================================================================
# End-to-End Tests
# =============================================================================


class TestPhase10EndToEnd:
    """End-to-end tests for Phase 10 components."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(
            return_value={
                "count": 0,
                "success_rate": 0.9,
                "avg_duration": 2000.0,
                "sample_size": 50,
            }
        )
        db.execute = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_full_autonomy_workflow(self, mock_db):
        """Test full autonomy workflow: architecture → alignment → handoff."""
        from ag3ntwerk.learning.orchestrator import LearningOrchestrator

        orchestrator = LearningOrchestrator(mock_db, AsyncMock())

        # 1. Evaluate architecture
        proposal = await orchestrator.evaluate_architecture()
        assert proposal is not None

        # 2. Verify we have Phase 10 components
        assert orchestrator._self_architect is not None
        assert orchestrator._goal_aligner is not None
        assert orchestrator._handoff_optimizer is not None

        # 3. Optimize handoffs
        strategy = await orchestrator.optimize_handoffs()
        assert strategy is not None

        # 4. Run full autonomy cycle
        results = await orchestrator.run_autonomy_cycle()
        assert results["timestamp"] is not None

    @pytest.mark.asyncio
    async def test_component_coordination(self, mock_db):
        """Test that Phase 10 components can work together."""
        from ag3ntwerk.learning.orchestrator import LearningOrchestrator

        orchestrator = LearningOrchestrator(mock_db, AsyncMock())

        # Run autonomy cycle which coordinates all components
        results = await orchestrator.run_autonomy_cycle()

        # Check that all components contributed
        assert "architecture" in results
        assert "alignment" in results
        assert "handoff" in results

    @pytest.mark.asyncio
    async def test_self_architect_proposal_lifecycle(self, mock_db):
        """Test SelfArchitect proposal creation."""
        architect = SelfArchitect(mock_db, AsyncMock(), AsyncMock())

        # Create proposal
        proposal = await architect.evaluate_architecture()
        assert proposal.status == ProposalStatus.PROPOSED

        # Save proposal
        await architect.save_proposal(proposal)
        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_goal_aligner_verification(self, mock_db):
        """Test GoalAligner alignment verification."""
        aligner = GoalAligner(mock_db, AsyncMock(), AsyncMock())

        decision = AutonomousDecision(
            decision_id="dec-1",
            action="deploy",
            category="deployment",
            description="Deploy to production",
            impact="high",
            affected_entities=["production_server"],
            context={},
        )

        score = await aligner.verify_alignment(decision)
        assert score is not None
        assert score.alignment_level in [
            AlignmentLevel.FULL,
            AlignmentLevel.PARTIAL,
            AlignmentLevel.MISALIGNED,
            AlignmentLevel.CONFLICTING,
        ]

    @pytest.mark.asyncio
    async def test_handoff_optimizer_strategy(self, mock_db):
        """Test HandoffOptimizer strategy generation."""
        optimizer = HandoffOptimizer(mock_db, AsyncMock(), AsyncMock())

        strategy = await optimizer.optimize_handoffs()
        assert strategy is not None
        assert isinstance(strategy.actions_to_promote, list)
        assert isinstance(strategy.actions_to_demote, list)
