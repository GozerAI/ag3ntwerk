"""
Tests for Phase 6 Integration - Wiring learning components to runtime behavior.

Tests:
- DynamicRouter integration with Nexus
- Confidence calibration in task execution
- Pattern attribution in outcome tracking
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.learning.models import (
    HierarchyPath,
    TaskOutcomeRecord,
    OutcomeType,
    ErrorCategory,
    LearnedPattern,
    PatternType,
    ScopeLevel,
    LearningAdjustment,
)
from ag3ntwerk.learning.outcome_tracker import OutcomeTracker
from ag3ntwerk.learning.orchestrator import LearningOrchestrator
from ag3ntwerk.learning.dynamic_router import DynamicRouter, RoutingDecision, RoutingScore
from ag3ntwerk.learning.confidence_calibrator import ConfidenceCalibrator, CalibrationCurve


# ============================================================================
# Pattern Attribution Tests
# ============================================================================


class TestPatternAttributionModel:
    """Test pattern attribution fields in TaskOutcomeRecord."""

    def test_task_outcome_has_pattern_fields(self):
        """TaskOutcomeRecord should have pattern attribution fields."""
        record = TaskOutcomeRecord(
            task_id="task-1",
            task_type="code_review",
            agent_code="Forge",
            applied_pattern_ids=["pat-1", "pat-2"],
            was_routing_influenced=True,
            was_confidence_calibrated=True,
        )
        assert record.applied_pattern_ids == ["pat-1", "pat-2"]
        assert record.was_routing_influenced is True
        assert record.was_confidence_calibrated is True

    def test_task_outcome_default_pattern_fields(self):
        """Pattern attribution fields should default to empty/False."""
        record = TaskOutcomeRecord(
            task_id="task-1",
            task_type="code_review",
            agent_code="Forge",
        )
        assert record.applied_pattern_ids == []
        assert record.was_routing_influenced is False
        assert record.was_confidence_calibrated is False

    def test_task_outcome_to_dict_includes_pattern_fields(self):
        """to_dict should include pattern attribution fields."""
        record = TaskOutcomeRecord(
            task_id="task-1",
            task_type="code_review",
            agent_code="Forge",
            applied_pattern_ids=["pat-1"],
            was_routing_influenced=True,
            was_confidence_calibrated=False,
        )
        data = record.to_dict()
        assert "applied_pattern_ids" in data
        assert data["applied_pattern_ids"] == ["pat-1"]
        assert data["was_routing_influenced"] is True
        assert data["was_confidence_calibrated"] is False


class TestOutcomeTrackerPatternAttribution:
    """Test OutcomeTracker records pattern attribution."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def tracker(self, mock_db):
        """Create an OutcomeTracker with mock database."""
        return OutcomeTracker(mock_db)

    @pytest.mark.asyncio
    async def test_record_outcome_with_pattern_attribution(self, tracker, mock_db):
        """record_outcome should accept and store pattern attribution."""
        hierarchy = HierarchyPath(agent="Forge")

        outcome_id = await tracker.record_outcome(
            task_id="task-1",
            task_type="code_review",
            hierarchy_path=hierarchy,
            success=True,
            applied_pattern_ids=["pat-1", "pat-2"],
            was_routing_influenced=True,
            was_confidence_calibrated=True,
        )

        # Check outcome was buffered
        assert len(tracker._outcome_buffer) == 1
        record = tracker._outcome_buffer[0]
        assert record.applied_pattern_ids == ["pat-1", "pat-2"]
        assert record.was_routing_influenced is True
        assert record.was_confidence_calibrated is True

    @pytest.mark.asyncio
    async def test_persist_outcome_includes_pattern_fields(self, tracker, mock_db):
        """_persist_outcome should include pattern attribution in SQL."""
        record = TaskOutcomeRecord(
            task_id="task-1",
            task_type="code_review",
            agent_code="Forge",
            applied_pattern_ids=["pat-1"],
            was_routing_influenced=True,
            was_confidence_calibrated=False,
        )

        await tracker._persist_outcome(record)

        # Verify execute was called with the new fields
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert "applied_pattern_ids" in sql
        assert "was_routing_influenced" in sql
        assert "was_confidence_calibrated" in sql

        # Check params include the pattern attribution values
        assert '["pat-1"]' in str(params)  # JSON serialized
        assert 1 in params  # was_routing_influenced = True
        assert 0 in params  # was_confidence_calibrated = False

    def test_row_to_outcome_parses_pattern_fields(self, tracker):
        """_row_to_outcome should parse pattern attribution fields."""
        row = {
            "id": "out-1",
            "task_id": "task-1",
            "task_type": "code_review",
            "agent_code": "Forge",
            "manager_code": None,
            "specialist_code": None,
            "outcome_type": "success",
            "success": 1,
            "effectiveness": 0.9,
            "duration_ms": 100.0,
            "initial_confidence": 0.8,
            "actual_accuracy": 0.9,
            "error_category": None,
            "error_message": None,
            "is_recoverable": 1,
            "input_hash": None,
            "output_summary": None,
            "context_snapshot": "{}",
            "applied_pattern_ids": '["pat-1", "pat-2"]',
            "was_routing_influenced": 1,
            "was_confidence_calibrated": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        record = tracker._row_to_outcome(row)

        assert record.applied_pattern_ids == ["pat-1", "pat-2"]
        assert record.was_routing_influenced is True
        assert record.was_confidence_calibrated is False

    def test_row_to_outcome_handles_missing_pattern_fields(self, tracker):
        """_row_to_outcome should handle missing pattern fields gracefully."""
        row = {
            "id": "out-1",
            "task_id": "task-1",
            "task_type": "code_review",
            "agent_code": "Forge",
            "manager_code": None,
            "specialist_code": None,
            "outcome_type": "success",
            "success": 1,
            "effectiveness": 0.9,
            "duration_ms": 100.0,
            "initial_confidence": None,
            "actual_accuracy": None,
            "error_category": None,
            "error_message": None,
            "is_recoverable": 1,
            "input_hash": None,
            "output_summary": None,
            "context_snapshot": None,
            # No pattern attribution fields
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        record = tracker._row_to_outcome(row)

        # Should use defaults
        assert record.applied_pattern_ids == []
        assert record.was_routing_influenced is False
        assert record.was_confidence_calibrated is False


# ============================================================================
# Orchestrator Integration Tests
# ============================================================================


class TestOrchestratorPatternAttribution:
    """Test LearningOrchestrator passes pattern attribution through."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(return_value=None)
        return db

    @pytest.fixture
    def mock_task_queue(self):
        """Create a mock task queue."""
        return AsyncMock()

    @pytest.fixture
    async def orchestrator(self, mock_db, mock_task_queue):
        """Create a LearningOrchestrator."""
        from ag3ntwerk.learning.orchestrator import initialize_learning_orchestrator

        return await initialize_learning_orchestrator(mock_db, mock_task_queue)

    @pytest.mark.asyncio
    async def test_record_outcome_with_pattern_attribution(self, orchestrator, mock_db):
        """record_outcome should pass pattern attribution to tracker."""
        hierarchy = HierarchyPath(agent="Forge")

        outcome_id = await orchestrator.record_outcome(
            task_id="task-1",
            task_type="code_review",
            hierarchy_path=hierarchy,
            success=True,
            applied_pattern_ids=["pat-1", "pat-2"],
            was_routing_influenced=True,
            was_confidence_calibrated=True,
        )

        assert outcome_id is not None

    @pytest.mark.asyncio
    async def test_get_calibrated_confidence(self, orchestrator, mock_db):
        """get_calibrated_confidence should return calibrated value."""
        # With no calibration data, should return raw confidence
        calibrated = await orchestrator.get_calibrated_confidence(
            agent_code="Forge",
            task_type="code_review",
            raw_confidence=0.7,
        )

        # Without data, returns raw confidence
        assert calibrated == 0.7

    @pytest.mark.asyncio
    async def test_record_confidence_prediction(self, orchestrator, mock_db):
        """record_confidence_prediction should update calibration data."""
        await orchestrator.record_confidence_prediction(
            agent_code="Forge",
            task_type="code_review",
            confidence=0.8,
            was_successful=True,
        )

        # Should not raise an error


# ============================================================================
# Dynamic Router Tests
# ============================================================================


class TestDynamicRouterIntegration:
    """Test DynamicRouter integration."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def mock_pattern_store(self):
        """Create a mock pattern store."""
        store = AsyncMock()
        store.get_patterns = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def router(self, mock_db, mock_pattern_store):
        """Create a DynamicRouter."""
        return DynamicRouter(mock_db, mock_pattern_store)

    @pytest.mark.asyncio
    async def test_get_routing_decision_with_no_agents(self, router):
        """get_routing_decision should handle empty agent list."""
        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents={},
        )

        assert decision.chosen_agent == ""
        assert decision.confidence == 0.0

    @pytest.mark.asyncio
    async def test_get_routing_decision_falls_back_to_static(self, router, mock_pattern_store):
        """get_routing_decision should fall back to static route when confidence is low."""
        mock_pattern_store.get_patterns.return_value = []

        agents = {
            "Forge": MagicMock(code="Forge"),
            "Keystone": MagicMock(code="Keystone"),
        }

        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=agents,
            static_route="Forge",
        )

        # With no patterns, should fall back to static route
        assert decision.chosen_agent == "Forge"
        assert decision.used_static_fallback is True

    @pytest.mark.asyncio
    async def test_get_routing_decision_with_patterns(self, router, mock_db, mock_pattern_store):
        """get_routing_decision should use patterns when available."""
        # Create a pattern that recommends Keystone for this task type
        pattern = LearnedPattern(
            pattern_type=PatternType.ROUTING,
            scope_level=ScopeLevel.AGENT,
            scope_code="Keystone",
            condition_json='{"task_type": "financial_review"}',
            recommendation="Route to Keystone",
            routing_preference="Keystone",
            confidence=0.9,
            sample_size=50,
        )
        mock_pattern_store.get_patterns.return_value = [pattern]

        # Add performance data for Keystone
        mock_db.fetch_all.return_value = [
            {
                "agent_code": "Keystone",
                "agent_level": "agent",
                "total_tasks": 100,
                "successful_tasks": 90,
                "failed_tasks": 10,
                "avg_duration_ms": 100.0,
                "avg_confidence": 0.8,
                "avg_actual_accuracy": 0.9,
                "confidence_calibration_score": 0.1,
                "health_score": 1.0,
                "consecutive_failures": 0,
                "circuit_breaker_open": 0,
            }
        ]

        agents = {
            "Forge": MagicMock(code="Forge"),
            "Keystone": MagicMock(code="Keystone"),
        }

        decision = await router.get_routing_decision(
            task_type="financial_review",
            available_agents=agents,
            static_route="Forge",  # Static says Forge
        )

        # Should use pattern-informed routing
        assert decision.chosen_agent in ["Forge", "Keystone"]
        assert len(decision.scores) == 2

    @pytest.mark.asyncio
    async def test_record_routing_outcome(self, router):
        """record_routing_outcome should track task type -> agent mapping."""
        await router.record_routing_outcome(
            task_type="code_review",
            chosen_agent="Forge",
            success=True,
            was_dynamic=True,
            duration_ms=100.0,
        )

        assert "code_review" in router._task_type_candidates
        assert "Forge" in router._task_type_candidates["code_review"]


# ============================================================================
# Confidence Calibration Tests
# ============================================================================


class TestConfidenceCalibrationIntegration:
    """Test ConfidenceCalibrator integration."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def calibrator(self, mock_db):
        """Create a ConfidenceCalibrator."""
        return ConfidenceCalibrator(mock_db)

    @pytest.mark.asyncio
    async def test_get_calibrated_confidence_no_data(self, calibrator):
        """get_calibrated_confidence should return raw when no data."""
        calibrated = await calibrator.get_calibrated_confidence(
            agent_code="Forge",
            task_type="code_review",
            raw_confidence=0.7,
        )

        # With no data, should return raw confidence
        assert calibrated == 0.7

    @pytest.mark.asyncio
    async def test_record_prediction_creates_curve(self, calibrator, mock_db):
        """record_prediction should create calibration curve."""
        await calibrator.record_prediction(
            agent_code="Forge",
            task_type="code_review",
            confidence=0.8,
            was_successful=True,
        )

        # Should have created a curve
        key = ("Forge", "code_review")
        assert key in calibrator._curves
        curve = calibrator._curves[key]
        assert curve.total_predictions == 1

    @pytest.mark.asyncio
    async def test_calibration_adjusts_overconfidence(self, calibrator, mock_db):
        """Calibration should reduce overconfident predictions."""
        # Record predictions where high confidence leads to failures
        for _ in range(20):
            await calibrator.record_prediction(
                agent_code="Forge",
                task_type="code_review",
                confidence=0.9,  # High confidence
                was_successful=False,  # But fails
            )

        # Get calibrated confidence
        calibrated = await calibrator.get_calibrated_confidence(
            agent_code="Forge",
            task_type="code_review",
            raw_confidence=0.9,
        )

        # Should be reduced (calibration error is positive for over-confidence)
        assert calibrated < 0.9

    @pytest.mark.asyncio
    async def test_calibration_adjusts_underconfidence(self, calibrator, mock_db):
        """Calibration should increase underconfident predictions."""
        # Record predictions where low confidence still succeeds
        for _ in range(20):
            await calibrator.record_prediction(
                agent_code="Keystone",
                task_type="financial_analysis",
                confidence=0.3,  # Low confidence
                was_successful=True,  # But succeeds
            )

        # Get calibrated confidence
        calibrated = await calibrator.get_calibrated_confidence(
            agent_code="Keystone",
            task_type="financial_analysis",
            raw_confidence=0.3,
        )

        # Should be increased
        assert calibrated > 0.3


class TestCalibrationCurve:
    """Test CalibrationCurve directly."""

    def test_bucket_index(self):
        """get_bucket_index should return correct bucket."""
        curve = CalibrationCurve(agent_code="Forge", task_type="test")

        assert curve.get_bucket_index(0.0) == 0
        assert curve.get_bucket_index(0.15) == 1
        assert curve.get_bucket_index(0.5) == 5
        assert curve.get_bucket_index(0.99) == 9
        assert curve.get_bucket_index(1.0) == 9

    def test_add_prediction(self):
        """add_prediction should update bucket stats."""
        curve = CalibrationCurve(agent_code="Forge", task_type="test")

        curve.add_prediction(0.75, was_successful=True)
        curve.add_prediction(0.75, was_successful=True)
        curve.add_prediction(0.75, was_successful=False)

        bucket = curve.buckets[7]  # 0.7-0.8 bucket
        assert bucket.total_predictions == 3
        assert bucket.successful_outcomes == 2
        assert bucket.actual_accuracy == pytest.approx(2 / 3)

    def test_get_calibrated_confidence_insufficient_data(self):
        """get_calibrated_confidence should return raw with insufficient data."""
        curve = CalibrationCurve(agent_code="Forge", task_type="test")

        # Only 2 predictions in bucket - not enough
        curve.add_prediction(0.75, was_successful=True)
        curve.add_prediction(0.75, was_successful=False)

        calibrated = curve.get_calibrated_confidence(0.75)
        assert calibrated == 0.75  # Returns raw

    def test_get_calibrated_confidence_with_data(self):
        """get_calibrated_confidence should adjust based on history."""
        curve = CalibrationCurve(agent_code="Forge", task_type="test")

        # Add enough predictions (over-confident: predicts 0.75 but fails often)
        for _ in range(6):
            curve.add_prediction(0.75, was_successful=False)
        for _ in range(4):
            curve.add_prediction(0.75, was_successful=True)

        # Actual accuracy is 40%, predicted 75%
        # Calibration error = 0.75 - 0.4 = 0.35 (over-confident)
        calibrated = curve.get_calibrated_confidence(0.75)

        # Should be reduced significantly
        assert calibrated < 0.75
        assert calibrated == pytest.approx(0.4, abs=0.05)


# ============================================================================
# End-to-End Integration Tests
# ============================================================================


class TestEndToEndPatternFlow:
    """Test end-to-end pattern flow."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(return_value=None)
        return db

    @pytest.fixture
    def mock_task_queue(self):
        """Create a mock task queue."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_pattern_influences_routing_and_is_tracked(self, mock_db, mock_task_queue):
        """Patterns should influence routing and outcomes should track which patterns were used."""
        from ag3ntwerk.learning.orchestrator import initialize_learning_orchestrator

        orchestrator = await initialize_learning_orchestrator(mock_db, mock_task_queue)

        # 1. Get a routing decision (would normally use patterns)
        agents = {"Forge": MagicMock(code="Forge"), "Keystone": MagicMock(code="Keystone")}
        decision = await orchestrator.get_routing_decision(
            task_type="code_review",
            available_agents=agents,
            static_route="Forge",
        )

        # 2. Track that patterns influenced the decision
        was_routing_influenced = not decision.used_static_fallback

        # 3. Get calibrated confidence
        calibrated = await orchestrator.get_calibrated_confidence(
            agent_code=decision.chosen_agent,
            task_type="code_review",
            raw_confidence=0.7,
        )
        was_calibrated = True  # In a real scenario, we'd check if value changed

        # 4. Record outcome with pattern attribution
        hierarchy = HierarchyPath(agent=decision.chosen_agent)
        outcome_id = await orchestrator.record_outcome(
            task_id="task-1",
            task_type="code_review",
            hierarchy_path=hierarchy,
            success=True,
            applied_pattern_ids=[s.agent_code for s in decision.scores if s.applied_patterns],
            was_routing_influenced=was_routing_influenced,
            was_confidence_calibrated=was_calibrated,
        )

        assert outcome_id is not None

    @pytest.mark.asyncio
    async def test_calibration_loop(self, mock_db, mock_task_queue):
        """Test that calibration data is recorded and can be retrieved."""
        from ag3ntwerk.learning.orchestrator import initialize_learning_orchestrator

        orchestrator = await initialize_learning_orchestrator(mock_db, mock_task_queue)

        # Record several predictions
        for i in range(15):
            await orchestrator.record_confidence_prediction(
                agent_code="Forge",
                task_type="code_review",
                confidence=0.8,
                was_successful=i % 2 == 0,  # 50% success rate
            )

        # Get calibrated confidence
        calibrated = await orchestrator.get_calibrated_confidence(
            agent_code="Forge",
            task_type="code_review",
            raw_confidence=0.8,
        )

        # Should be adjusted down (predicted 0.8 but actual ~0.5)
        assert calibrated <= 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
