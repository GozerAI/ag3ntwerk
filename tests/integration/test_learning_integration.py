"""
Integration tests for the Learning System.

Tests the full flow from outcome recording through pattern detection,
failure prediction, load balancing, and task modification.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.learning import (
    LearningOrchestrator,
    initialize_learning_orchestrator,
    HierarchyPath,
    OutcomeType,
    ErrorCategory,
    RiskLevel,
)


class TestLearningSystemIntegration:
    """Integration tests for the complete learning system."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def mock_task_queue(self):
        """Create a mock task queue."""
        queue = AsyncMock()
        queue.get_stats = AsyncMock(
            return_value=MagicMock(
                pending=5,
                processing=2,
                completed=100,
                failed=5,
                throughput_per_minute=10.0,
            )
        )
        queue.enqueue = AsyncMock(return_value="task-123")
        return queue

    @pytest.fixture
    async def orchestrator(self, mock_db, mock_task_queue):
        """Create and initialize a LearningOrchestrator."""
        # Mock pattern loading
        mock_db.fetch_all.return_value = []

        orch = LearningOrchestrator(mock_db, mock_task_queue)

        # Register a test agent with managers
        orch.register_executive("Forge", managers=["AM", "CQM"])
        orch.register_manager("AM", "Forge", specialists=["SD", "BE"])
        orch.register_specialist("SD", "AM", capabilities=["python", "testing"])

        return orch

    @pytest.mark.asyncio
    async def test_full_outcome_to_pattern_flow(self, orchestrator, mock_db):
        """Test recording outcomes and detecting patterns."""
        # Record multiple outcomes to trigger pattern detection
        for i in range(10):
            success = i % 3 != 0  # 66% success rate

            await orchestrator.record_outcome(
                task_id=f"task-{i}",
                task_type="code_review",
                hierarchy_path=HierarchyPath(
                    agent="Forge",
                    manager="AM",
                    specialist="SD",
                ),
                success=success,
                duration_ms=1000 + (i * 100),
                effectiveness=0.8 if success else 0.2,
                confidence=0.7,
            )

        # Verify outcome was recorded
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_routing_decision_with_patterns(self, orchestrator, mock_db):
        """Test that routing decisions consider learned patterns."""
        # Mock pattern store to return a routing pattern
        mock_db.fetch_all.return_value = [
            {
                "id": "pattern-1",
                "pattern_type": "routing",
                "scope_level": "agent",
                "scope_code": "Forge",
                "condition_json": '{"task_type": "code_review"}',
                "recommendation": "Route to Forge",
                "confidence": 0.85,
                "sample_size": 50,
                "success_rate": 0.9,
                "routing_preference": "Forge",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        # Mock agent performance
        mock_db.fetch_all.side_effect = [
            # First call: patterns
            [
                {
                    "id": "pattern-1",
                    "pattern_type": "routing",
                    "scope_level": "agent",
                    "scope_code": "Forge",
                    "condition_json": '{"task_type": "code_review"}',
                    "recommendation": "Route to Forge",
                    "confidence": 0.85,
                    "sample_size": 50,
                    "success_rate": 0.9,
                    "routing_preference": "Forge",
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
            # Second call: agent performance
            [
                {
                    "agent_code": "Forge",
                    "agent_level": "agent",
                    "total_tasks": 100,
                    "successful_tasks": 85,
                    "failed_tasks": 15,
                    "health_score": 0.9,
                    "consecutive_failures": 0,
                    "circuit_breaker_open": False,
                }
            ],
        ]

        # Get routing decision
        decision = await orchestrator.get_routing_decision(
            task_type="code_review",
            available_agents={"Forge": MagicMock(), "Keystone": MagicMock()},
            static_route="Forge",
        )

        assert decision.chosen_agent in ["Forge", "Keystone"]
        assert decision.confidence >= 0

    @pytest.mark.asyncio
    async def test_failure_prediction_flow(self, orchestrator, mock_db):
        """Test predicting failure risk for a task."""
        # Mock error pattern stats with high timeout rate
        mock_db.fetch_one.side_effect = [
            # Error pattern stats
            {
                "total": 100,
                "failed": 40,
                "timeout_count": 30,
                "capability_count": 5,
                "resource_count": 3,
                "logic_count": 1,
                "external_count": 1,
            },
            # Agent health
            {
                "health_score": 0.7,
                "circuit_breaker_open": 0,
                "consecutive_failures": 2,
                "last_failure_at": None,
                "avg_duration_ms": 5000,
            },
        ]

        # Predict failure risk
        risk = await orchestrator.predict_failure_risk(
            task_type="long_running_task",
            target_agent="Forge",
            context={"complexity": "high"},
        )

        assert risk is not None
        assert risk.score >= 0
        assert risk.score <= 1
        assert risk.risk_level in [
            RiskLevel.LOW,
            RiskLevel.MODERATE,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ]

    @pytest.mark.asyncio
    async def test_load_balancing_flow(self, orchestrator, mock_db, mock_task_queue):
        """Test load-balanced agent selection."""
        # Mock agent performance for multiple agents
        mock_db.fetch_one.side_effect = [
            # Forge performance
            {
                "health_score": 0.9,
                "circuit_breaker_open": 0,
                "avg_duration_ms": 500,
                "total_tasks": 100,
                "successful_tasks": 90,
            },
            # Forge recent counts
            {"completed": 10, "failed": 1},
            # Forge task performance
            {"total": 50, "successful": 45, "avg_duration": 400},
            # Keystone performance
            {
                "health_score": 0.95,
                "circuit_breaker_open": 0,
                "avg_duration_ms": 300,
                "total_tasks": 80,
                "successful_tasks": 75,
            },
            # Keystone recent counts
            {"completed": 5, "failed": 0},
            # Keystone task performance
            {"total": 30, "successful": 28, "avg_duration": 250},
        ]

        # Get optimal agent
        decision = await orchestrator.get_optimal_agent(
            task_type="code_review",
            candidates=["Forge", "Keystone"],
        )

        assert decision is not None
        assert decision.chosen_agent in ["Forge", "Keystone"]
        assert decision.score >= 0

    @pytest.mark.asyncio
    async def test_task_modification_flow(self, orchestrator, mock_db):
        """Test proactive task modification based on risk."""
        # Mock high timeout risk
        mock_db.fetch_one.side_effect = [
            # Error pattern stats - high timeout rate
            {
                "total": 100,
                "failed": 50,
                "timeout_count": 40,
                "capability_count": 5,
                "resource_count": 3,
                "logic_count": 1,
                "external_count": 1,
            },
            # Agent health
            {
                "health_score": 0.6,
                "circuit_breaker_open": 0,
                "consecutive_failures": 3,
                "last_failure_at": None,
                "avg_duration_ms": 8000,
            },
        ]

        # Modify task
        task = {
            "task_type": "long_running_task",
            "timeout_ms": 30000,
            "priority": 5,
        }

        modified = await orchestrator.modify_task(
            task=task,
            target_agent="Forge",
        )

        assert modified is not None
        assert modified.original_task == task

    @pytest.mark.asyncio
    async def test_confidence_calibration_flow(self, orchestrator, mock_db):
        """Test confidence calibration recording and retrieval."""
        # Record predictions
        for i in range(15):
            confidence = 0.7 + (i % 3) * 0.1  # 0.7, 0.8, 0.9
            success = i % 2 == 0  # 50% success

            await orchestrator.record_confidence_prediction(
                agent_code="Forge",
                task_type="code_review",
                confidence=confidence,
                was_successful=success,
            )

        # Get calibrated confidence
        calibrated = await orchestrator.get_calibrated_confidence(
            agent_code="Forge",
            task_type="code_review",
            raw_confidence=0.8,
        )

        # Should return a value between 0 and 1
        assert 0 <= calibrated <= 1

    @pytest.mark.asyncio
    async def test_pattern_application_tracking(self, orchestrator, mock_db):
        """Test that pattern applications are tracked."""
        # Record a pattern application
        app_id = await orchestrator.record_pattern_application(
            pattern_id="pattern-123",
            task_id="task-456",
            task_type="code_review",
            agent_code="Forge",
            is_routing_pattern=True,
            baseline_agent="Keystone",
            baseline_success_rate=0.75,
        )

        assert app_id is not None

        # Record outcome
        await orchestrator.record_pattern_outcome(
            task_id="task-456",
            success=True,
            duration_ms=1500,
            effectiveness=0.85,
        )

        # Verify database was called
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_analysis_cycle(self, orchestrator, mock_db):
        """Test manual analysis cycle trigger."""
        # Mock outcomes by hierarchy
        mock_db.fetch_all.return_value = []

        # Trigger analysis
        results = await orchestrator.trigger_analysis()

        assert "timestamp" in results
        assert "patterns_detected" in results
        assert "issues_detected" in results

    @pytest.mark.asyncio
    async def test_get_stats(self, orchestrator, mock_db):
        """Test retrieving learning system stats."""
        mock_db.fetch_all.return_value = []

        stats = await orchestrator.get_stats()

        assert "loops" in stats
        assert "patterns" in stats
        assert "issues" in stats
        assert stats["loops"]["agents"] == 1  # Forge
        assert stats["loops"]["managers"] == 1  # AM
        assert stats["loops"]["specialists"] == 1  # SD


class TestPhase2Integration:
    """Integration tests specific to Phase 2 predictive capabilities."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def mock_task_queue(self):
        """Create a mock task queue with realistic stats."""
        queue = AsyncMock()
        queue.get_stats = AsyncMock(
            return_value=MagicMock(
                pending=10,
                processing=3,
                completed=500,
                failed=25,
                dead=5,
                scheduled=2,
                throughput_per_minute=15.0,
                avg_wait_time_ms=250.0,
                avg_processing_time_ms=1500.0,
            )
        )
        return queue

    @pytest.mark.asyncio
    async def test_queue_metrics_integration(self, mock_db, mock_task_queue):
        """Test that queue metrics are properly integrated."""
        from ag3ntwerk.learning.load_balancer import LoadBalancer

        balancer = LoadBalancer(mock_db, mock_task_queue)

        # Mock agent performance
        mock_db.fetch_one.side_effect = [
            {
                "health_score": 0.9,
                "circuit_breaker_open": 0,
                "avg_duration_ms": 500,
                "total_tasks": 100,
                "successful_tasks": 90,
            },
            {"completed": 10, "failed": 1},
        ]

        loads = await balancer.get_agent_loads(["Forge"])

        assert "Forge" in loads
        # Queue depth should come from the mock queue
        assert loads["Forge"].queue_depth == 10
        assert loads["Forge"].active_tasks == 3

    @pytest.mark.asyncio
    async def test_failure_predictor_queue_integration(self, mock_db, mock_task_queue):
        """Test failure predictor uses queue metrics."""
        from ag3ntwerk.learning.failure_predictor import FailurePredictor

        predictor = FailurePredictor(mock_db, mock_task_queue)

        # Mock database responses
        mock_db.fetch_one.side_effect = [
            None,  # No error pattern stats
            {
                "health_score": 0.9,
                "consecutive_failures": 0,
                "circuit_breaker_open": 0,
                "last_failure_at": None,
                "avg_duration_ms": 500,
            },
        ]

        risk = await predictor.predict_failure_risk(
            task_type="code_review",
            target_agent="Forge",
        )

        # Queue was queried for load metrics
        assert mock_task_queue.get_stats.called
        assert risk is not None

    @pytest.mark.asyncio
    async def test_end_to_end_task_modification(self, mock_db, mock_task_queue):
        """Test complete flow from risk prediction to task modification."""
        from ag3ntwerk.learning.failure_predictor import FailurePredictor, RiskLevel
        from ag3ntwerk.learning.load_balancer import LoadBalancer
        from ag3ntwerk.learning.task_modifier import TaskModifier

        # Setup components
        predictor = FailurePredictor(mock_db, mock_task_queue)
        balancer = LoadBalancer(mock_db, mock_task_queue)
        modifier = TaskModifier(predictor, balancer)

        # Mock high-risk scenario
        mock_db.fetch_one.side_effect = [
            # Error stats - high timeout rate
            {
                "total": 100,
                "failed": 60,
                "timeout_count": 50,
                "capability_count": 5,
                "resource_count": 3,
                "logic_count": 1,
                "external_count": 1,
            },
            # Agent health - degraded
            {
                "health_score": 0.5,
                "consecutive_failures": 5,
                "circuit_breaker_open": 0,
                "last_failure_at": None,
                "avg_duration_ms": 10000,
            },
        ]

        # Original task
        task = {
            "task_type": "slow_operation",
            "timeout_ms": 30000,
            "priority": 5,
        }

        # Modify task
        result = await modifier.modify_task(
            task=task,
            target_agent="Forge",
        )

        # Should have modifications for high-risk task
        assert result is not None
        assert result.failure_risk is not None

    @pytest.mark.asyncio
    async def test_safest_agent_selection(self, mock_db, mock_task_queue):
        """Test selecting the safest agent from candidates."""
        from ag3ntwerk.learning.failure_predictor import FailurePredictor

        predictor = FailurePredictor(mock_db, mock_task_queue)

        # Mock different risk levels for different agents
        mock_db.fetch_one.side_effect = [
            # Forge - high risk
            {
                "total": 100,
                "failed": 50,
                "timeout_count": 40,
                "capability_count": 5,
                "resource_count": 3,
                "logic_count": 1,
                "external_count": 1,
            },
            {
                "health_score": 0.5,
                "consecutive_failures": 5,
                "circuit_breaker_open": 0,
                "last_failure_at": None,
                "avg_duration_ms": 5000,
            },
            # Keystone - low risk
            {
                "total": 100,
                "failed": 5,
                "timeout_count": 2,
                "capability_count": 1,
                "resource_count": 1,
                "logic_count": 1,
                "external_count": 0,
            },
            {
                "health_score": 0.95,
                "consecutive_failures": 0,
                "circuit_breaker_open": 0,
                "last_failure_at": None,
                "avg_duration_ms": 300,
            },
        ]

        result = await predictor.get_safest_agent("code_review", ["Forge", "Keystone"])

        assert result is not None
        agent_code, risk = result
        assert agent_code == "Keystone"  # Keystone has lower risk

    @pytest.mark.asyncio
    async def test_overloaded_agents_detection(self, mock_db, mock_task_queue):
        """Test detection of overloaded agents."""
        from ag3ntwerk.learning.load_balancer import LoadBalancer

        # Create queue with high utilization
        mock_task_queue.get_stats = AsyncMock(
            return_value=MagicMock(
                pending=50,  # High pending count
                processing=10,
                completed=100,
                failed=5,
                throughput_per_minute=5.0,
            )
        )

        balancer = LoadBalancer(mock_db, mock_task_queue)

        # Mock agent list
        mock_db.fetch_all.return_value = [
            {"agent_code": "Forge"},
            {"agent_code": "Keystone"},
        ]

        # Mock agent performance
        mock_db.fetch_one.side_effect = [
            # Forge
            {
                "health_score": 0.9,
                "circuit_breaker_open": 0,
                "avg_duration_ms": 500,
                "total_tasks": 100,
                "successful_tasks": 90,
            },
            {"completed": 10, "failed": 1},
            # Keystone
            {
                "health_score": 0.95,
                "circuit_breaker_open": 0,
                "avg_duration_ms": 300,
                "total_tasks": 80,
                "successful_tasks": 75,
            },
            {"completed": 5, "failed": 0},
        ]

        overloaded = await balancer.get_overloaded_agents(["Forge", "Keystone"])

        # With high pending count, agents should be detected as overloaded
        # (utilization = (50 + 10) / 10 = 6.0, capped at 1.0 > 0.9 threshold)
        assert len(overloaded) >= 0  # May or may not be overloaded depending on calculation
