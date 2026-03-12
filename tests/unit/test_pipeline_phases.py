"""Tests for continuous pipeline phases, lifecycle, and state machine.

Verifies:
- Individual phase isolation (one phase failure does not crash the cycle)
- Full cycle lifecycle with mocked components
- CycleResult structure correctness
- Pipeline state machine transitions (STOPPED -> RUNNING -> ERROR -> STOPPED)
- Cycle history bounding (deque maxlen)
- Stats key correctness from orchestrator integration
"""

import asyncio
import pytest
from collections import deque
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.learning.continuous_pipeline import (
    ContinuousLearningPipeline,
    CyclePhase,
    CycleResult,
    PipelineConfig,
    PipelineState,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_orchestrator():
    """Create a mock LearningOrchestrator with expected methods."""
    orch = AsyncMock()
    orch.get_stats = AsyncMock(
        return_value={
            "core": {
                "outcome_stats": {"total_outcomes_24h": 5},
            },
            "patterns": {"total_patterns": 2},
            "loops": {"agents": 1, "managers": 1, "specialists": 1},
        }
    )
    orch._run_analysis_cycle = AsyncMock()
    orch._pattern_store = AsyncMock()
    orch._pattern_store.get_all_active_patterns = AsyncMock(return_value=[])
    return orch


@pytest.fixture
def config():
    """Create a pipeline config with fast cycle times for testing."""
    return PipelineConfig(
        cycle_interval_seconds=0.1,
        min_cycle_interval_seconds=0.01,
        max_consecutive_errors=3,
        error_backoff_seconds=0.01,
    )


@pytest.fixture
def pipeline(mock_orchestrator, config):
    """Create a pipeline with mocked orchestrator."""
    return ContinuousLearningPipeline(
        orchestrator=mock_orchestrator,
        config=config,
    )


# ============================================================
# Phase Isolation Tests
# ============================================================


class TestPhaseIsolation:
    """Verify that individual phase failures do not crash the entire cycle."""

    @pytest.mark.asyncio
    async def test_single_phase_failure_does_not_crash_cycle(self, mock_orchestrator, config):
        """A failing phase should be caught; the cycle still completes."""
        mock_orchestrator.get_stats = AsyncMock(side_effect=RuntimeError("stats exploded"))
        pipeline = ContinuousLearningPipeline(
            orchestrator=mock_orchestrator,
            config=config,
        )

        result = await pipeline.run_single_cycle()

        # Cycle completes (success=True because _execute_phase catches per-phase errors)
        assert result.completed_at is not None
        assert result.success is True
        # The outcome_collection phase duration should still be recorded
        assert CyclePhase.OUTCOME_COLLECTION.value in result.phase_durations

    @pytest.mark.asyncio
    async def test_phase_result_metrics_reflect_work(self, mock_orchestrator, config):
        """Phase metrics should reflect values returned by the orchestrator."""
        mock_orchestrator.get_stats = AsyncMock(
            return_value={
                "core": {
                    "outcome_stats": {"total_outcomes_24h": 42},
                },
                "patterns": {"total_patterns": 7},
            }
        )
        pipeline = ContinuousLearningPipeline(
            orchestrator=mock_orchestrator,
            config=config,
        )

        result = await pipeline.run_single_cycle()

        assert result.outcomes_collected == 42
        assert result.patterns_detected == 7

    @pytest.mark.asyncio
    async def test_phase_skip_when_component_is_none(self, mock_orchestrator, config):
        """Phases that depend on optional components (None) should be skipped."""
        pipeline = ContinuousLearningPipeline(
            orchestrator=mock_orchestrator,
            experimenter=None,
            meta_learner=None,
            opportunity_detector=None,
            proactive_generator=None,
            config=config,
        )

        result = await pipeline.run_single_cycle()

        # Optional phases should not appear in phase_durations
        assert CyclePhase.EXPERIMENT_MANAGEMENT.value not in result.phase_durations
        assert CyclePhase.PARAMETER_TUNING.value not in result.phase_durations
        assert CyclePhase.OPPORTUNITY_DETECTION.value not in result.phase_durations
        assert CyclePhase.TASK_GENERATION.value not in result.phase_durations
        # Required phases should appear
        assert CyclePhase.OUTCOME_COLLECTION.value in result.phase_durations
        assert CyclePhase.PATTERN_DETECTION.value in result.phase_durations

    @pytest.mark.asyncio
    async def test_multiple_phases_fail_independently(self, mock_orchestrator, config):
        """Multiple failing phases should each be isolated; cycle still succeeds."""
        mock_orchestrator.get_stats = AsyncMock(side_effect=RuntimeError("stats error"))
        mock_orchestrator._run_analysis_cycle = AsyncMock(
            side_effect=RuntimeError("analysis error")
        )
        mock_orchestrator._pattern_store.get_all_active_patterns = AsyncMock(
            side_effect=RuntimeError("pattern store error")
        )

        pipeline = ContinuousLearningPipeline(
            orchestrator=mock_orchestrator,
            config=config,
        )

        result = await pipeline.run_single_cycle()

        # All phases should have recorded durations despite errors
        assert CyclePhase.OUTCOME_COLLECTION.value in result.phase_durations
        assert CyclePhase.PATTERN_DETECTION.value in result.phase_durations
        assert CyclePhase.PATTERN_ACTIVATION.value in result.phase_durations
        assert result.success is True


# ============================================================
# Cycle Lifecycle Tests
# ============================================================


class TestCycleLifecycle:
    """Verify cycle execution, result structure, and history bounding."""

    @pytest.mark.asyncio
    async def test_full_cycle_completes_with_all_phases(self, pipeline):
        """A full cycle should complete with all mandatory phases run."""
        result = await pipeline.run_single_cycle()

        assert result.success is True
        assert result.completed_at is not None
        assert result.cycle_id is not None
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_cycle_result_has_correct_structure(self, pipeline):
        """CycleResult.to_dict() should contain all expected fields."""
        result = await pipeline.run_single_cycle()
        d = result.to_dict()

        expected_keys = {
            "cycle_id",
            "started_at",
            "completed_at",
            "duration_ms",
            "success",
            "error",
            "outcomes_collected",
            "patterns_detected",
            "experiments_started",
            "experiments_concluded",
            "patterns_activated",
            "patterns_deactivated",
            "parameters_tuned",
            "opportunities_detected",
            "tasks_generated",
            "items_cleaned",
            "phase_durations",
        }
        assert expected_keys.issubset(d.keys())

    @pytest.mark.asyncio
    async def test_cycle_result_duration_positive(self, pipeline):
        """Completed cycle should have a positive duration."""
        result = await pipeline.run_single_cycle()
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_cycle_history_is_bounded(self, mock_orchestrator):
        """Cycle history deque should not exceed maxlen."""
        config = PipelineConfig(
            cycle_interval_seconds=0.01,
            min_cycle_interval_seconds=0.01,
        )
        pipeline = ContinuousLearningPipeline(
            orchestrator=mock_orchestrator,
            config=config,
        )

        # Verify the internal deque has maxlen=100
        assert pipeline._cycle_history.maxlen == 100

        # Run more cycles than maxlen
        for _ in range(5):
            result = await pipeline.run_single_cycle()
            pipeline._cycle_history.append(result)

        assert len(pipeline._cycle_history) <= 100

    @pytest.mark.asyncio
    async def test_get_cycle_history_returns_dicts(self, pipeline):
        """get_cycle_history should return serialised dicts."""
        await pipeline.run_single_cycle()
        pipeline._cycle_history.append(await pipeline.run_single_cycle())

        history = pipeline.get_cycle_history(limit=5)
        assert isinstance(history, list)
        for entry in history:
            assert isinstance(entry, dict)
            assert "cycle_id" in entry

    @pytest.mark.asyncio
    async def test_get_cycle_history_success_only_filter(self, pipeline):
        """success_only filter should exclude failed cycles."""
        # Add a successful cycle
        good = CycleResult(success=True)
        good.completed_at = datetime.now(timezone.utc)
        pipeline._cycle_history.append(good)

        # Add a failed cycle
        bad = CycleResult(success=False, error="test failure")
        bad.completed_at = datetime.now(timezone.utc)
        pipeline._cycle_history.append(bad)

        history = pipeline.get_cycle_history(success_only=True)
        for entry in history:
            assert entry["success"] is True


# ============================================================
# Pipeline State Machine Tests
# ============================================================


class TestPipelineStateMachine:
    """Verify state transitions of the pipeline."""

    def test_initial_state_is_stopped(self, pipeline):
        """Pipeline should start in STOPPED state."""
        assert pipeline.state == PipelineState.STOPPED
        assert pipeline.is_running is False

    @pytest.mark.asyncio
    async def test_start_transitions_to_running(self, pipeline):
        """Starting the pipeline should transition to RUNNING."""
        started = await pipeline.start()
        assert started is True
        assert pipeline.state == PipelineState.RUNNING
        assert pipeline.is_running is True

        # Cleanup
        await pipeline.stop(timeout=2.0)

    @pytest.mark.asyncio
    async def test_stop_transitions_to_stopped(self, pipeline):
        """Stopping a running pipeline should transition to STOPPED."""
        await pipeline.start()
        assert pipeline.state == PipelineState.RUNNING

        stopped = await pipeline.stop(timeout=2.0)
        assert stopped is True
        assert pipeline.state == PipelineState.STOPPED
        assert pipeline.is_running is False

    @pytest.mark.asyncio
    async def test_stop_already_stopped_is_noop(self, pipeline):
        """Stopping a STOPPED pipeline should return True (no-op)."""
        assert pipeline.state == PipelineState.STOPPED
        stopped = await pipeline.stop(timeout=1.0)
        assert stopped is True

    @pytest.mark.asyncio
    async def test_start_already_running_returns_false(self, pipeline):
        """Starting an already-running pipeline should return False."""
        await pipeline.start()
        result = await pipeline.start()
        assert result is False

        await pipeline.stop(timeout=2.0)

    @pytest.mark.asyncio
    async def test_consecutive_errors_trigger_error_state(self, mock_orchestrator):
        """Exceeding max_consecutive_errors should put pipeline in ERROR state."""
        config = PipelineConfig(
            cycle_interval_seconds=0.01,
            min_cycle_interval_seconds=0.01,
            max_consecutive_errors=2,
            error_backoff_seconds=0.01,
        )

        # Make _execute_cycle raise every time by making orchestrator fail hard
        # We need the error to propagate past _execute_phase to the main loop
        pipeline = ContinuousLearningPipeline(
            orchestrator=mock_orchestrator,
            config=config,
        )

        # Patch _execute_cycle to always raise
        original_execute = pipeline._execute_cycle

        async def failing_cycle():
            raise RuntimeError("catastrophic failure")

        pipeline._execute_cycle = failing_cycle

        await pipeline.start()

        # Give the loop time to hit the error threshold
        await asyncio.sleep(0.5)

        assert pipeline.state == PipelineState.ERROR
        assert pipeline._consecutive_errors >= 2

        # Cleanup: force stop
        pipeline._stop_event.set()
        pipeline._state = PipelineState.STOPPED
        if pipeline._task and not pipeline._task.done():
            pipeline._task.cancel()
            try:
                await pipeline._task
            except (asyncio.CancelledError, Exception):
                pass

    @pytest.mark.asyncio
    async def test_pause_and_resume(self, pipeline):
        """Pausing and resuming should work correctly."""
        await pipeline.start()

        paused = await pipeline.pause()
        assert paused is True
        assert pipeline.state == PipelineState.PAUSED

        resumed = await pipeline.resume()
        assert resumed is True
        assert pipeline.state == PipelineState.RUNNING

        await pipeline.stop(timeout=2.0)

    @pytest.mark.asyncio
    async def test_pause_when_not_running_returns_false(self, pipeline):
        """Pausing when not RUNNING should return False."""
        assert pipeline.state == PipelineState.STOPPED
        paused = await pipeline.pause()
        assert paused is False

    @pytest.mark.asyncio
    async def test_resume_when_not_paused_returns_false(self, pipeline):
        """Resuming when not PAUSED should return False."""
        assert pipeline.state == PipelineState.STOPPED
        resumed = await pipeline.resume()
        assert resumed is False


# ============================================================
# Stats Key Correctness Tests
# ============================================================


class TestStatsKeyCorrectness:
    """Verify pipeline reads correct keys from the orchestrator stats."""

    @pytest.mark.asyncio
    async def test_outcome_collection_uses_correct_stats_keys(self, mock_orchestrator, config):
        """Outcome collection should read core.outcome_stats.total_outcomes_24h."""
        mock_orchestrator.get_stats = AsyncMock(
            return_value={
                "core": {
                    "outcome_stats": {"total_outcomes_24h": 99},
                },
                "patterns": {"total_patterns": 0},
            }
        )
        pipeline = ContinuousLearningPipeline(
            orchestrator=mock_orchestrator,
            config=config,
        )

        result = await pipeline.run_single_cycle()
        assert result.outcomes_collected == 99

    @pytest.mark.asyncio
    async def test_pattern_detection_uses_correct_stats_keys(self, mock_orchestrator, config):
        """Pattern detection should read patterns.total_patterns."""
        mock_orchestrator.get_stats = AsyncMock(
            return_value={
                "core": {
                    "outcome_stats": {"total_outcomes_24h": 0},
                },
                "patterns": {"total_patterns": 15},
            }
        )
        pipeline = ContinuousLearningPipeline(
            orchestrator=mock_orchestrator,
            config=config,
        )

        result = await pipeline.run_single_cycle()
        assert result.patterns_detected == 15

    @pytest.mark.asyncio
    async def test_missing_stats_keys_default_to_zero(self, mock_orchestrator, config):
        """Missing keys in stats should default to 0 without error."""
        mock_orchestrator.get_stats = AsyncMock(return_value={})
        pipeline = ContinuousLearningPipeline(
            orchestrator=mock_orchestrator,
            config=config,
        )

        result = await pipeline.run_single_cycle()
        assert result.outcomes_collected == 0
        assert result.patterns_detected == 0


# ============================================================
# Pipeline get_stats and health_check Tests
# ============================================================


class TestPipelineStats:
    """Verify pipeline-level get_stats and health_check methods."""

    @pytest.mark.asyncio
    async def test_get_stats_contains_expected_keys(self, pipeline):
        """get_stats should return all expected top-level keys."""
        stats = await pipeline.get_stats()

        expected = {
            "state",
            "is_running",
            "total_cycles",
            "successful_cycles",
            "failed_cycles",
            "consecutive_errors",
            "success_rate",
            "started_at",
            "stopped_at",
            "last_cycle",
            "config",
        }
        assert expected.issubset(stats.keys())

    @pytest.mark.asyncio
    async def test_get_stats_initial_values(self, pipeline):
        """Initial stats should reflect zero cycles and STOPPED state."""
        stats = await pipeline.get_stats()

        assert stats["state"] == "stopped"
        assert stats["is_running"] is False
        assert stats["total_cycles"] == 0
        assert stats["successful_cycles"] == 0
        assert stats["failed_cycles"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["last_cycle"] is None

    @pytest.mark.asyncio
    async def test_health_check_healthy_by_default(self, pipeline):
        """Fresh pipeline should report healthy."""
        health = await pipeline.health_check()
        assert health["healthy"] is True
        assert health["state"] == "stopped"

    @pytest.mark.asyncio
    async def test_health_check_reports_error_state(self, pipeline):
        """Pipeline in ERROR state should report unhealthy."""
        pipeline._state = PipelineState.ERROR
        health = await pipeline.health_check()
        assert health["healthy"] is False
        assert "error state" in health["issues"][0].lower()


# ============================================================
# Config Tests
# ============================================================


class TestPipelineConfig:
    """Verify pipeline configuration updates and defaults."""

    def test_default_config_values(self):
        """Default config should have sensible values."""
        config = PipelineConfig()
        assert config.cycle_interval_seconds == 60.0
        assert config.min_cycle_interval_seconds == 10.0
        assert config.max_consecutive_errors == 5
        assert config.enable_pattern_detection is True
        assert config.enable_cleanup is True

    def test_update_config(self, pipeline):
        """update_config should modify the active configuration."""
        pipeline.update_config(cycle_interval_seconds=30.0)
        config = pipeline.get_config()
        assert config["cycle_interval_seconds"] == 30.0

    def test_update_config_ignores_unknown_keys(self, pipeline):
        """Unknown keys should be ignored (no AttributeError)."""
        pipeline.update_config(nonexistent_key="value")
        config = pipeline.get_config()
        assert "nonexistent_key" not in config

    def test_config_to_dict(self):
        """Config to_dict should contain all expected keys."""
        config = PipelineConfig()
        d = config.to_dict()
        expected = {
            "cycle_interval_seconds",
            "min_cycle_interval_seconds",
            "enable_pattern_detection",
            "enable_experiments",
            "enable_parameter_tuning",
            "enable_opportunity_detection",
            "enable_task_generation",
            "enable_cleanup",
            "min_outcomes_for_analysis",
            "max_patterns_per_cycle",
            "max_experiments_per_cycle",
            "max_tasks_per_cycle",
            "outcome_window_hours",
            "pattern_window_hours",
            "cleanup_age_hours",
            "max_consecutive_errors",
            "error_backoff_seconds",
        }
        assert expected.issubset(d.keys())


# ============================================================
# Metacognition Phase Tests
# ============================================================


class TestMetacognitionPhase:
    """Verify the metacognition phase integration."""

    @pytest.mark.asyncio
    async def test_metacognition_phase_runs_when_facade_present(self, mock_orchestrator, config):
        """Metacognition phase should run when facade is provided."""
        mock_facade = MagicMock()
        mock_facade.run_metacognition_phase.return_value = {"heuristics_tuned": 3}

        pipeline = ContinuousLearningPipeline(
            orchestrator=mock_orchestrator,
            metacognition_facade=mock_facade,
            config=config,
        )

        result = await pipeline.run_single_cycle()

        mock_facade.run_metacognition_phase.assert_called_once()
        assert CyclePhase.METACOGNITION.value in result.phase_durations

    @pytest.mark.asyncio
    async def test_metacognition_phase_skipped_when_no_facade(self, pipeline):
        """Metacognition phase should be skipped when facade is None."""
        result = await pipeline.run_single_cycle()
        assert CyclePhase.METACOGNITION.value not in result.phase_durations

    @pytest.mark.asyncio
    async def test_metacognition_phase_error_does_not_crash(self, mock_orchestrator, config):
        """Metacognition facade error should be caught; cycle still succeeds."""
        mock_facade = MagicMock()
        mock_facade.run_metacognition_phase.side_effect = RuntimeError("metacog error")

        pipeline = ContinuousLearningPipeline(
            orchestrator=mock_orchestrator,
            metacognition_facade=mock_facade,
            config=config,
        )

        result = await pipeline.run_single_cycle()

        assert result.success is True
        assert CyclePhase.METACOGNITION.value in result.phase_durations
