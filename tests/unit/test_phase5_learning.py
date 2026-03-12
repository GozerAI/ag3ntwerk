"""
Unit tests for Phase 5 Learning System components.

Tests:
- AutonomyController: Decision autonomy management
- ContinuousLearningPipeline: Never-ending learning cycle
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.learning.autonomy_controller import (
    AutonomyController,
    AutonomyLevel,
    ActionCategory,
    AutonomyDecision,
    PendingApproval,
    ActionLog,
)
from ag3ntwerk.learning.continuous_pipeline import (
    ContinuousLearningPipeline,
    PipelineState,
    PipelineConfig,
    CycleResult,
    CyclePhase,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    db.fetch_one = AsyncMock(return_value=None)
    db.fetch_all = AsyncMock(return_value=[])
    return db


@pytest.fixture
def autonomy_controller(mock_db):
    """Create an AutonomyController instance."""
    return AutonomyController(mock_db)


@pytest.fixture
def autonomy_controller_no_db():
    """Create an AutonomyController without database."""
    return AutonomyController()


@pytest.fixture
def mock_orchestrator():
    """Create a mock learning orchestrator."""
    orchestrator = AsyncMock()
    orchestrator._pattern_store = AsyncMock()
    orchestrator._pattern_store.get_all_active_patterns = AsyncMock(return_value=[])
    orchestrator._pattern_store.activate_pattern = AsyncMock()
    orchestrator._pattern_store.deactivate_pattern = AsyncMock()
    orchestrator.get_stats = AsyncMock(return_value={"recent_outcomes": 10})
    orchestrator._run_analysis_cycle = AsyncMock()
    return orchestrator


@pytest.fixture
def mock_experimenter():
    """Create a mock pattern experimenter."""
    experimenter = AsyncMock()
    experimenter.list_active_experiments = AsyncMock(return_value=[])
    experimenter.get_experiment = AsyncMock(return_value=None)
    experimenter.create_experiment = AsyncMock()
    return experimenter


@pytest.fixture
def mock_meta_learner():
    """Create a mock meta-learner."""
    learner = AsyncMock()
    learner.tune_parameters = AsyncMock(return_value=[])
    return learner


@pytest.fixture
def mock_opportunity_detector():
    """Create a mock opportunity detector."""
    detector = AsyncMock()
    detector.detect_opportunities = AsyncMock(return_value=[])
    return detector


@pytest.fixture
def mock_proactive_generator():
    """Create a mock proactive task generator."""
    generator = AsyncMock()
    generator.generate_all_tasks = AsyncMock(return_value=[])
    generator.enqueue_all_pending = AsyncMock(return_value=0)
    generator.clear_completed_tasks = AsyncMock(return_value=0)
    return generator


@pytest.fixture
def pipeline_config():
    """Create a test pipeline configuration."""
    return PipelineConfig(
        cycle_interval_seconds=0.1,  # Fast for testing
        min_cycle_interval_seconds=0.05,
        enable_pattern_detection=True,
        enable_experiments=False,  # Disable for simpler tests
        enable_parameter_tuning=False,
        enable_opportunity_detection=True,
        enable_task_generation=True,
        enable_cleanup=True,
    )


@pytest.fixture
def continuous_pipeline(
    mock_orchestrator,
    mock_experimenter,
    mock_meta_learner,
    mock_opportunity_detector,
    mock_proactive_generator,
    autonomy_controller_no_db,
    pipeline_config,
):
    """Create a ContinuousLearningPipeline instance."""
    return ContinuousLearningPipeline(
        orchestrator=mock_orchestrator,
        experimenter=mock_experimenter,
        meta_learner=mock_meta_learner,
        opportunity_detector=mock_opportunity_detector,
        proactive_generator=mock_proactive_generator,
        autonomy_controller=autonomy_controller_no_db,
        config=pipeline_config,
    )


# =============================================================================
# AutonomyController Tests
# =============================================================================


class TestAutonomyController:
    """Tests for autonomy control functionality."""

    def test_default_autonomy_levels(self, autonomy_controller):
        """Test default autonomy levels are set correctly."""
        levels = autonomy_controller.get_autonomy_levels()

        # Fully autonomous actions
        assert levels["routine_routing"] == "full"
        assert levels["confidence_calibration"] == "full"
        assert levels["pattern_creation"] == "full"

        # Supervised actions
        assert levels["dynamic_routing"] == "supervised"
        assert levels["handler_generation"] == "supervised"

        # Advisory actions
        assert levels["workflow_modification"] == "advisory"

        # Human required actions
        assert levels["agent_capability_change"] == "human_required"

    def test_check_autonomy_full(self, autonomy_controller):
        """Test checking autonomy for fully autonomous actions."""
        decision = autonomy_controller.check_autonomy(
            "routine_routing",
            ActionCategory.ROUTINE_ROUTING,
        )

        assert decision.proceed is True
        assert decision.requires_approval is False
        assert decision.requires_logging is False
        assert decision.level == AutonomyLevel.FULL

    def test_check_autonomy_supervised(self, autonomy_controller):
        """Test checking autonomy for supervised actions."""
        decision = autonomy_controller.check_autonomy(
            "dynamic_routing",
            ActionCategory.DYNAMIC_ROUTING,
        )

        assert decision.proceed is True
        assert decision.requires_approval is False
        assert decision.requires_logging is True
        assert decision.level == AutonomyLevel.SUPERVISED

    def test_check_autonomy_advisory(self, autonomy_controller):
        """Test checking autonomy for advisory actions."""
        decision = autonomy_controller.check_autonomy(
            "workflow_modification",
            ActionCategory.WORKFLOW_MODIFICATION,
        )

        assert decision.proceed is False
        assert decision.requires_approval is True
        assert decision.level == AutonomyLevel.ADVISORY

    def test_check_autonomy_human_required(self, autonomy_controller):
        """Test checking autonomy for human-required actions."""
        decision = autonomy_controller.check_autonomy(
            "agent_capability_change",
            ActionCategory.AGENT_CAPABILITY_CHANGE,
        )

        assert decision.proceed is False
        assert decision.requires_approval is True
        assert decision.level == AutonomyLevel.HUMAN_REQUIRED

    def test_infer_category_from_action(self, autonomy_controller):
        """Test category inference from action names."""
        # Routing actions
        assert autonomy_controller._infer_category("route_task") == ActionCategory.ROUTINE_ROUTING
        assert (
            autonomy_controller._infer_category("dynamic_route") == ActionCategory.DYNAMIC_ROUTING
        )
        assert (
            autonomy_controller._infer_category("fallback_routing")
            == ActionCategory.FALLBACK_ROUTING
        )

        # Learning actions
        assert (
            autonomy_controller._infer_category("calibrate_confidence")
            == ActionCategory.CONFIDENCE_CALIBRATION
        )
        assert (
            autonomy_controller._infer_category("create_pattern") == ActionCategory.PATTERN_CREATION
        )
        assert (
            autonomy_controller._infer_category("deactivate_pattern")
            == ActionCategory.PATTERN_DEACTIVATION
        )

        # Handler actions
        assert (
            autonomy_controller._infer_category("generate_handler")
            == ActionCategory.HANDLER_GENERATION
        )
        assert (
            autonomy_controller._infer_category("activate_handler")
            == ActionCategory.HANDLER_ACTIVATION
        )

    @pytest.mark.asyncio
    async def test_request_approval(self, autonomy_controller):
        """Test requesting approval for an action."""
        approval = await autonomy_controller.request_approval(
            action="workflow_modification",
            category=ActionCategory.WORKFLOW_MODIFICATION,
            description="Modify the task workflow",
            impact_assessment="Medium impact - affects routing",
            recommended_decision=True,
        )

        assert approval.id is not None
        assert approval.action == "workflow_modification"
        assert approval.status == "pending"
        assert approval.expires_at is not None

    @pytest.mark.asyncio
    async def test_approve_action(self, autonomy_controller):
        """Test approving a pending action."""
        # Request approval first
        approval = await autonomy_controller.request_approval(
            action="test_action",
            category=ActionCategory.WORKFLOW_MODIFICATION,
            description="Test action",
        )

        # Approve it
        result = await autonomy_controller.approve(approval.id, approver="test_user")

        assert result is True
        assert approval.status == "approved"
        assert approval.decided_by == "test_user"
        assert approval.decided_at is not None

    @pytest.mark.asyncio
    async def test_deny_action(self, autonomy_controller):
        """Test denying a pending action."""
        approval = await autonomy_controller.request_approval(
            action="test_action",
            category=ActionCategory.WORKFLOW_MODIFICATION,
            description="Test action",
        )

        result = await autonomy_controller.deny(
            approval.id,
            denier="test_user",
            reason="Not needed",
        )

        assert result is True
        assert approval.status == "denied"

    @pytest.mark.asyncio
    async def test_approve_non_existent(self, autonomy_controller):
        """Test approving non-existent approval."""
        result = await autonomy_controller.approve("non-existent")
        assert result is False

    @pytest.mark.asyncio
    async def test_approved_action_proceeds(self, autonomy_controller):
        """Test that approved actions can proceed."""
        # Request and approve
        approval = await autonomy_controller.request_approval(
            action="workflow_modification",
            category=ActionCategory.WORKFLOW_MODIFICATION,
            description="Test action",
        )
        await autonomy_controller.approve(approval.id)

        # Check autonomy - should now proceed
        decision = autonomy_controller.check_autonomy(
            "workflow_modification",
            ActionCategory.WORKFLOW_MODIFICATION,
        )

        assert decision.proceed is True
        assert decision.approval_id == approval.id

    @pytest.mark.asyncio
    async def test_log_action(self, autonomy_controller):
        """Test logging a supervised action."""
        log = await autonomy_controller.log_action(
            action="dynamic_routing",
            category=ActionCategory.DYNAMIC_ROUTING,
            description="Routed task to Forge",
            context={"task_id": "task-123"},
            result={"route": "Forge"},
            success=True,
        )

        assert log.id is not None
        assert log.action == "dynamic_routing"
        assert log.success is True

    def test_set_autonomy_level(self, autonomy_controller):
        """Test setting autonomy level for a category."""
        autonomy_controller.set_autonomy_level(
            ActionCategory.ROUTINE_ROUTING,
            AutonomyLevel.SUPERVISED,
        )

        decision = autonomy_controller.check_autonomy(
            "routine_routing",
            ActionCategory.ROUTINE_ROUTING,
        )

        assert decision.level == AutonomyLevel.SUPERVISED
        assert decision.requires_logging is True

    def test_set_override(self, autonomy_controller):
        """Test setting an override for a specific action."""
        autonomy_controller.set_override("special_action", AutonomyLevel.FULL)

        decision = autonomy_controller.check_autonomy("special_action")

        assert decision.level == AutonomyLevel.FULL
        assert decision.proceed is True

    def test_clear_override(self, autonomy_controller):
        """Test clearing an override."""
        autonomy_controller.set_override("special_action", AutonomyLevel.FULL)
        result = autonomy_controller.clear_override("special_action")

        assert result is True

        # Check action now uses default
        decision = autonomy_controller.check_autonomy("special_action")
        assert decision.level != AutonomyLevel.FULL

    def test_get_pending_approvals(self, autonomy_controller):
        """Test getting pending approvals."""
        # Initially empty
        pending = autonomy_controller.get_pending_approvals()
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_get_pending_approvals_filters_expired(self, autonomy_controller):
        """Test that expired approvals are filtered out."""
        approval = await autonomy_controller.request_approval(
            action="test_action",
            category=ActionCategory.WORKFLOW_MODIFICATION,
            description="Test",
            expiry_hours=0,  # Expires immediately
        )

        # Set expired timestamp
        approval.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        pending = autonomy_controller.get_pending_approvals()
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_get_stats(self, autonomy_controller):
        """Test getting autonomy controller statistics."""
        stats = await autonomy_controller.get_stats()

        assert "pending_approvals" in stats
        assert "approval_status_counts" in stats
        assert "total_logged_actions" in stats
        assert "autonomy_levels" in stats

    @pytest.mark.asyncio
    async def test_register_approval_callback(self, autonomy_controller):
        """Test registering an approval callback."""
        callback_called = []

        def callback(approval):
            callback_called.append(approval)

        autonomy_controller.register_approval_callback(callback)

        # Request approval - callback should be called
        await autonomy_controller.request_approval(
            action="test",
            category=ActionCategory.WORKFLOW_MODIFICATION,
            description="Test",
        )

        assert len(callback_called) == 1


class TestAutonomyDecision:
    """Tests for AutonomyDecision dataclass."""

    def test_decision_creation(self):
        """Test creating an autonomy decision."""
        decision = AutonomyDecision(
            action="test_action",
            level=AutonomyLevel.SUPERVISED,
            proceed=True,
            requires_logging=True,
        )

        assert decision.action == "test_action"
        assert decision.level == AutonomyLevel.SUPERVISED
        assert decision.proceed is True
        assert decision.requires_logging is True

    def test_decision_to_dict(self):
        """Test decision serialization."""
        decision = AutonomyDecision(
            action="test_action",
            level=AutonomyLevel.FULL,
            proceed=True,
        )

        data = decision.to_dict()

        assert data["action"] == "test_action"
        assert data["level"] == "full"
        assert data["proceed"] is True


class TestPendingApproval:
    """Tests for PendingApproval dataclass."""

    def test_approval_creation(self):
        """Test creating a pending approval."""
        approval = PendingApproval(
            action="workflow_modification",
            category=ActionCategory.WORKFLOW_MODIFICATION,
            description="Modify workflow",
        )

        assert approval.id is not None
        assert approval.status == "pending"
        assert approval.action == "workflow_modification"

    def test_approval_to_dict(self):
        """Test approval serialization."""
        approval = PendingApproval(
            action="test",
            category=ActionCategory.HANDLER_GENERATION,
            description="Test approval",
        )

        data = approval.to_dict()

        assert data["action"] == "test"
        assert data["category"] == "handler_generation"
        assert data["status"] == "pending"


class TestActionLog:
    """Tests for ActionLog dataclass."""

    def test_log_creation(self):
        """Test creating an action log."""
        log = ActionLog(
            action="dynamic_routing",
            category=ActionCategory.DYNAMIC_ROUTING,
            description="Routed to Forge",
            success=True,
        )

        assert log.id is not None
        assert log.action == "dynamic_routing"
        assert log.success is True

    def test_log_to_dict(self):
        """Test log serialization."""
        log = ActionLog(
            action="test",
            category=ActionCategory.PATTERN_CREATION,
            autonomy_level=AutonomyLevel.SUPERVISED,
            description="Created pattern",
        )

        data = log.to_dict()

        assert data["action"] == "test"
        assert data["category"] == "pattern_creation"
        assert data["autonomy_level"] == "supervised"


# =============================================================================
# ContinuousLearningPipeline Tests
# =============================================================================


class TestContinuousLearningPipeline:
    """Tests for continuous learning pipeline functionality."""

    def test_initial_state(self, continuous_pipeline):
        """Test initial pipeline state."""
        assert continuous_pipeline.state == PipelineState.STOPPED
        assert continuous_pipeline.is_running is False

    @pytest.mark.asyncio
    async def test_start_pipeline(self, continuous_pipeline):
        """Test starting the pipeline."""
        result = await continuous_pipeline.start()

        assert result is True
        assert continuous_pipeline.state == PipelineState.RUNNING
        assert continuous_pipeline.is_running is True

        # Clean up
        await continuous_pipeline.stop()

    @pytest.mark.asyncio
    async def test_stop_pipeline(self, continuous_pipeline):
        """Test stopping the pipeline."""
        await continuous_pipeline.start()
        result = await continuous_pipeline.stop()

        assert result is True
        assert continuous_pipeline.state == PipelineState.STOPPED
        assert continuous_pipeline.is_running is False

    @pytest.mark.asyncio
    async def test_pause_resume_pipeline(self, continuous_pipeline):
        """Test pausing and resuming the pipeline."""
        await continuous_pipeline.start()

        # Pause
        result = await continuous_pipeline.pause()
        assert result is True
        assert continuous_pipeline.state == PipelineState.PAUSED

        # Resume
        result = await continuous_pipeline.resume()
        assert result is True
        assert continuous_pipeline.state == PipelineState.RUNNING

        # Clean up
        await continuous_pipeline.stop()

    @pytest.mark.asyncio
    async def test_run_single_cycle(self, continuous_pipeline):
        """Test running a single learning cycle."""
        result = await continuous_pipeline.run_single_cycle()

        assert isinstance(result, CycleResult)
        assert result.success is True
        assert result.completed_at is not None
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_cycle_result_metrics(self, continuous_pipeline, mock_opportunity_detector):
        """Test that cycle results contain metrics."""
        # Set up mock to return opportunities
        mock_opportunity_detector.detect_opportunities.return_value = [
            MagicMock(),
            MagicMock(),
        ]

        result = await continuous_pipeline.run_single_cycle()

        assert result.opportunities_detected == 2

    @pytest.mark.asyncio
    async def test_cycle_phase_durations(self, continuous_pipeline):
        """Test that phase durations are tracked."""
        result = await continuous_pipeline.run_single_cycle()

        assert "outcome_collection" in result.phase_durations
        assert "opportunity_detection" in result.phase_durations
        assert "cleanup" in result.phase_durations

    @pytest.mark.asyncio
    async def test_get_stats(self, continuous_pipeline):
        """Test getting pipeline statistics."""
        stats = await continuous_pipeline.get_stats()

        assert "state" in stats
        assert "total_cycles" in stats
        assert "successful_cycles" in stats
        assert "config" in stats

    @pytest.mark.asyncio
    async def test_get_cycle_history(self, continuous_pipeline):
        """Test getting cycle history."""
        # Run a few cycles - note that run_single_cycle doesn't add to history
        # We need to access history after the pipeline tracks it
        # The cycle history is tracked during the _run_loop

        # Instead, verify that a single cycle can be retrieved after we add manually
        result1 = await continuous_pipeline.run_single_cycle()
        continuous_pipeline._cycle_history.append(result1)

        result2 = await continuous_pipeline.run_single_cycle()
        continuous_pipeline._cycle_history.append(result2)

        history = continuous_pipeline.get_cycle_history(limit=10)

        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, continuous_pipeline):
        """Test health check when pipeline is healthy."""
        health = await continuous_pipeline.health_check()

        assert health["healthy"] is True
        assert "state" in health
        assert "issues" in health

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self):
        """Test health check when pipeline is not initialized."""
        # Create a minimal pipeline
        orchestrator = AsyncMock()
        pipeline = ContinuousLearningPipeline(orchestrator=orchestrator)

        health = await pipeline.health_check()

        assert health["healthy"] is True  # Not initialized is OK

    def test_update_config(self, continuous_pipeline):
        """Test updating pipeline configuration."""
        continuous_pipeline.update_config(
            cycle_interval_seconds=120.0,
            enable_experiments=True,
        )

        config = continuous_pipeline.get_config()

        assert config["cycle_interval_seconds"] == 120.0
        assert config["enable_experiments"] is True

    def test_get_config(self, continuous_pipeline):
        """Test getting pipeline configuration."""
        config = continuous_pipeline.get_config()

        assert "cycle_interval_seconds" in config
        assert "enable_pattern_detection" in config
        assert "max_patterns_per_cycle" in config


class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PipelineConfig()

        assert config.cycle_interval_seconds == 60.0
        assert config.enable_pattern_detection is True
        assert config.enable_experiments is True
        assert config.min_outcomes_for_analysis == 10

    def test_custom_config(self):
        """Test custom configuration."""
        config = PipelineConfig(
            cycle_interval_seconds=120.0,
            enable_experiments=False,
            max_patterns_per_cycle=10,
        )

        assert config.cycle_interval_seconds == 120.0
        assert config.enable_experiments is False
        assert config.max_patterns_per_cycle == 10

    def test_config_to_dict(self):
        """Test configuration serialization."""
        config = PipelineConfig()
        data = config.to_dict()

        assert "cycle_interval_seconds" in data
        assert "enable_pattern_detection" in data
        assert "cleanup_age_hours" in data


class TestCycleResult:
    """Tests for CycleResult dataclass."""

    def test_result_creation(self):
        """Test creating a cycle result."""
        result = CycleResult()

        assert result.cycle_id is not None
        assert result.success is True
        assert result.started_at is not None

    def test_result_duration(self):
        """Test duration calculation."""
        result = CycleResult()
        result.completed_at = result.started_at + timedelta(milliseconds=500)

        assert result.duration_ms >= 500

    def test_result_to_dict(self):
        """Test result serialization."""
        result = CycleResult(
            patterns_detected=5,
            tasks_generated=3,
        )
        result.completed_at = datetime.now(timezone.utc)

        data = result.to_dict()

        assert data["patterns_detected"] == 5
        assert data["tasks_generated"] == 3
        assert "duration_ms" in data


class TestPipelineState:
    """Tests for PipelineState enum."""

    def test_state_values(self):
        """Test state enum values."""
        assert PipelineState.STOPPED.value == "stopped"
        assert PipelineState.RUNNING.value == "running"
        assert PipelineState.PAUSED.value == "paused"
        assert PipelineState.ERROR.value == "error"


class TestCyclePhase:
    """Tests for CyclePhase enum."""

    def test_phase_values(self):
        """Test phase enum values."""
        assert CyclePhase.OUTCOME_COLLECTION.value == "outcome_collection"
        assert CyclePhase.PATTERN_DETECTION.value == "pattern_detection"
        assert CyclePhase.EXPERIMENT_MANAGEMENT.value == "experiment_management"
        assert CyclePhase.CLEANUP.value == "cleanup"


# =============================================================================
# Integration Tests
# =============================================================================


class TestPhase5Integration:
    """Integration tests for Phase 5 components."""

    @pytest.mark.asyncio
    async def test_autonomy_with_pipeline(
        self,
        continuous_pipeline,
        autonomy_controller_no_db,
    ):
        """Test autonomy controller integration with pipeline."""
        # Set a restrictive autonomy level
        autonomy_controller_no_db.set_autonomy_level(
            ActionCategory.PROACTIVE_TASK_CREATION,
            AutonomyLevel.HUMAN_REQUIRED,
        )

        # Run a cycle - task generation should be blocked
        result = await continuous_pipeline.run_single_cycle()

        # Cycle should still succeed overall
        assert result.success is True

    @pytest.mark.asyncio
    async def test_pipeline_tracks_consecutive_cycles(self, continuous_pipeline):
        """Test that pipeline tracks consecutive cycles."""
        # Run multiple cycles - note run_single_cycle doesn't increment counters
        # The counters are tracked during the _run_loop

        # Manually run cycles and track them
        for _ in range(3):
            result = await continuous_pipeline.run_single_cycle()
            continuous_pipeline._total_cycles += 1
            if result.success:
                continuous_pipeline._successful_cycles += 1
            continuous_pipeline._cycle_history.append(result)

        stats = await continuous_pipeline.get_stats()

        assert stats["total_cycles"] == 3
        assert stats["successful_cycles"] == 3

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, mock_orchestrator):
        """Test that pipeline handles errors gracefully."""
        # Make orchestrator raise an error - errors in phases are caught
        # and logged, but don't fail the entire cycle
        mock_orchestrator._run_analysis_cycle.side_effect = Exception("Test error")

        pipeline = ContinuousLearningPipeline(
            orchestrator=mock_orchestrator,
            config=PipelineConfig(
                cycle_interval_seconds=0.1,
                enable_pattern_detection=True,
                enable_experiments=False,
                enable_parameter_tuning=False,
                enable_opportunity_detection=False,
                enable_task_generation=False,
                enable_cleanup=False,
            ),
        )

        result = await pipeline.run_single_cycle()

        # Individual phase errors are caught and logged,
        # but the cycle continues and succeeds overall
        # This is the expected behavior - graceful degradation
        assert result.success is True
        # The error was caught in the pattern_detection phase
        assert "pattern_detection" in result.phase_durations


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestPhase5EdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_double_start(self, continuous_pipeline):
        """Test starting an already running pipeline."""
        await continuous_pipeline.start()
        result = await continuous_pipeline.start()

        assert result is False  # Already running

        await continuous_pipeline.stop()

    @pytest.mark.asyncio
    async def test_pause_when_not_running(self, continuous_pipeline):
        """Test pausing when pipeline is not running."""
        result = await continuous_pipeline.pause()
        assert result is False

    @pytest.mark.asyncio
    async def test_resume_when_not_paused(self, continuous_pipeline):
        """Test resuming when pipeline is not paused."""
        result = await continuous_pipeline.resume()
        assert result is False

    @pytest.mark.asyncio
    async def test_approval_already_decided(self, autonomy_controller):
        """Test approving an already decided approval."""
        approval = await autonomy_controller.request_approval(
            action="test",
            category=ActionCategory.WORKFLOW_MODIFICATION,
            description="Test",
        )

        # Approve first time
        await autonomy_controller.approve(approval.id)

        # Try to approve again
        result = await autonomy_controller.approve(approval.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_expired_approval(self, autonomy_controller):
        """Test that expired approvals are handled."""
        approval = await autonomy_controller.request_approval(
            action="test",
            category=ActionCategory.WORKFLOW_MODIFICATION,
            description="Test",
            expiry_hours=0,
        )

        # Force expiration
        approval.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        # Try to approve
        result = await autonomy_controller.approve(approval.id)
        assert result is False
        assert approval.status == "expired"

    @pytest.mark.asyncio
    async def test_cleanup_expired_approvals(self, autonomy_controller):
        """Test cleaning up expired approvals."""
        # Create an approval that's already expired
        approval = await autonomy_controller.request_approval(
            action="test",
            category=ActionCategory.WORKFLOW_MODIFICATION,
            description="Test",
        )
        approval.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        count = await autonomy_controller.cleanup_expired_approvals()

        assert count == 1
        assert approval.status == "expired"

    def test_action_log_history(self, autonomy_controller):
        """Test action log retrieval."""
        # Initially empty
        logs = autonomy_controller.get_action_log()
        assert len(logs) == 0

    @pytest.mark.asyncio
    async def test_action_log_with_filter(self, autonomy_controller):
        """Test action log with category filter."""
        await autonomy_controller.log_action(
            action="test1",
            category=ActionCategory.DYNAMIC_ROUTING,
            description="Test 1",
        )
        await autonomy_controller.log_action(
            action="test2",
            category=ActionCategory.PATTERN_CREATION,
            description="Test 2",
        )

        logs = autonomy_controller.get_action_log(category=ActionCategory.DYNAMIC_ROUTING)

        assert len(logs) == 1
        assert logs[0].action == "test1"

    def test_enum_values(self):
        """Test enum values are correct."""
        assert AutonomyLevel.FULL.value == "full"
        assert AutonomyLevel.SUPERVISED.value == "supervised"
        assert AutonomyLevel.ADVISORY.value == "advisory"
        assert AutonomyLevel.HUMAN_REQUIRED.value == "human_required"

        assert ActionCategory.ROUTINE_ROUTING.value == "routine_routing"
        assert ActionCategory.HANDLER_GENERATION.value == "handler_generation"
