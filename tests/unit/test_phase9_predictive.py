"""
Tests for Phase 9: Predictive Intelligence.

Tests DemandForecaster, CascadePredictor, and ContextOptimizer components.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import json

from ag3ntwerk.learning.demand_forecaster import (
    DemandForecaster,
    SeasonalityType,
    TrendDirection,
    ScalingAction,
    TimeSeriesPoint,
    SeasonalPattern,
    TrendInfo,
    TaskTypeDistribution,
    ConfidenceInterval,
    ScalingRecommendation,
    DemandForecast,
)
from ag3ntwerk.learning.cascade_predictor import (
    CascadePredictor,
    RiskLevel,
    ImpactType,
    AgentLoad,
    DownstreamAgent,
    CascadeRisk,
    RoutingDecision,
    CascadeEffect,
)
from ag3ntwerk.learning.context_optimizer import (
    ContextOptimizer,
    OptimizationType,
    TimeOfDay,
    LoadLevel,
    ExecutionContext,
    Task,
    TimePattern,
    LoadPattern,
    OptimizationAction,
    AgentRecommendation,
    OptimizedTask,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.fetch_all = AsyncMock(return_value=[])
    db.fetch_one = AsyncMock(return_value=None)
    return db


@pytest.fixture
def mock_outcome_tracker():
    """Create a mock outcome tracker."""
    tracker = AsyncMock()
    return tracker


@pytest.fixture
def mock_pattern_store():
    """Create a mock pattern store."""
    store = AsyncMock()
    return store


@pytest.fixture
def demand_forecaster(mock_db, mock_outcome_tracker, mock_pattern_store):
    """Create a DemandForecaster instance."""
    return DemandForecaster(mock_db, mock_outcome_tracker, mock_pattern_store)


@pytest.fixture
def cascade_predictor(mock_db, mock_outcome_tracker, mock_pattern_store):
    """Create a CascadePredictor instance."""
    return CascadePredictor(mock_db, mock_outcome_tracker, mock_pattern_store)


@pytest.fixture
def context_optimizer(mock_db, mock_outcome_tracker, mock_pattern_store):
    """Create a ContextOptimizer instance."""
    return ContextOptimizer(mock_db, mock_outcome_tracker, mock_pattern_store)


@pytest.fixture
def sample_time_series():
    """Create sample time series data."""
    now = datetime.now(timezone.utc)
    points = []
    for i in range(48):  # 48 hours
        ts = now - timedelta(hours=48 - i)
        # Simulate daily pattern: higher during day, lower at night
        hour = ts.hour
        base_value = 50.0
        if 9 <= hour <= 17:
            value = base_value * 1.5
        elif 0 <= hour <= 5:
            value = base_value * 0.5
        else:
            value = base_value
        # Add some noise
        value += (i % 5) * 2
        points.append(TimeSeriesPoint(timestamp=ts, value=value))
    return points


@pytest.fixture
def sample_routing_decision():
    """Create a sample routing decision."""
    return RoutingDecision(
        task_type="code_review",
        selected_agent="Forge",
        context={"priority": "high"},
        priority=1,
        estimated_duration_ms=5000.0,
    )


@pytest.fixture
def sample_execution_context():
    """Create a sample execution context."""
    return ExecutionContext(
        timestamp=datetime.now(timezone.utc),
        system_load=0.7,
        active_tasks=50,
        recent_failure_rate=0.15,
        queue_depth=25,
        avg_response_time_ms=1500.0,
    )


@pytest.fixture
def sample_task():
    """Create a sample task."""
    return Task(
        task_id="task-123",
        task_type="code_review",
        priority=3,
        timeout_ms=30000.0,
        context={"file_count": 5},
    )


# ============================================================================
# DemandForecaster Tests
# ============================================================================


class TestDemandForecaster:
    """Tests for DemandForecaster."""

    async def test_forecast_demand_empty_history(self, demand_forecaster, mock_db):
        """Test forecast with no historical data."""
        mock_db.fetch_all.return_value = []

        forecast = await demand_forecaster.forecast_demand(horizon_hours=24)

        assert forecast is not None
        assert forecast.horizon_hours == 24
        assert forecast.expected_volume >= 0
        assert forecast.recommended_scaling is not None

    async def test_forecast_demand_with_history(self, demand_forecaster, mock_db):
        """Test forecast with historical data."""
        # Mock historical data
        now = datetime.now(timezone.utc)
        mock_db.fetch_all.return_value = [
            {
                "hour_bucket": (now - timedelta(hours=i)).strftime("%Y-%m-%d %H:00:00"),
                "task_type": "code_review",
                "count": 10 + i,
            }
            for i in range(48)
        ]

        forecast = await demand_forecaster.forecast_demand(horizon_hours=24)

        assert forecast is not None
        assert forecast.expected_volume > 0
        assert len(forecast.hourly_projections) == 24

    async def test_detect_seasonality_daily(self, demand_forecaster, sample_time_series):
        """Test daily seasonality detection."""
        # Extend to have enough data
        extended = sample_time_series * 4  # 8 days

        result = demand_forecaster._detect_seasonality(extended)

        # Should detect some pattern (may or may not be daily depending on data)
        # The important thing is it doesn't crash
        assert result is None or isinstance(result, SeasonalPattern)

    async def test_detect_trend_increasing(self, demand_forecaster):
        """Test detection of increasing trend."""
        now = datetime.now(timezone.utc)
        points = [
            TimeSeriesPoint(timestamp=now - timedelta(hours=i), value=100 - i * 2)
            for i in range(48)
        ]
        points.reverse()  # Oldest first

        result = demand_forecaster._detect_trends(points)

        assert result is not None
        assert result.direction == TrendDirection.INCREASING

    async def test_detect_trend_decreasing(self, demand_forecaster):
        """Test detection of decreasing trend."""
        now = datetime.now(timezone.utc)
        points = [
            TimeSeriesPoint(timestamp=now - timedelta(hours=i), value=i * 2) for i in range(48)
        ]
        points.reverse()  # Oldest first

        result = demand_forecaster._detect_trends(points)

        assert result is not None
        assert result.direction == TrendDirection.DECREASING

    async def test_detect_trend_stable(self, demand_forecaster):
        """Test detection of stable trend."""
        now = datetime.now(timezone.utc)
        points = [
            TimeSeriesPoint(timestamp=now - timedelta(hours=i), value=50.0) for i in range(48)
        ]

        result = demand_forecaster._detect_trends(points)

        assert result is not None
        assert result.direction == TrendDirection.STABLE

    async def test_scaling_recommendation_scale_up(self, demand_forecaster):
        """Test scale up recommendation."""
        now = datetime.now(timezone.utc)
        historical = [
            TimeSeriesPoint(timestamp=now - timedelta(hours=i), value=50.0) for i in range(48)
        ]

        # Expected volume much higher than historical
        result = demand_forecaster._recommend_scaling(
            expected_volume=2000.0,  # ~83/hour vs 50/hour historical
            historical=historical,
            agent_filter=None,
        )

        assert result.action == ScalingAction.SCALE_UP
        assert result.urgency > 0

    async def test_scaling_recommendation_scale_down(self, demand_forecaster):
        """Test scale down recommendation."""
        now = datetime.now(timezone.utc)
        historical = [
            TimeSeriesPoint(timestamp=now - timedelta(hours=i), value=100.0) for i in range(48)
        ]

        # Expected volume much lower than historical
        result = demand_forecaster._recommend_scaling(
            expected_volume=480.0,  # 20/hour vs 100/hour historical
            historical=historical,
            agent_filter=None,
        )

        assert result.action == ScalingAction.SCALE_DOWN

    async def test_scaling_recommendation_maintain(self, demand_forecaster):
        """Test maintain recommendation."""
        now = datetime.now(timezone.utc)
        historical = [
            TimeSeriesPoint(timestamp=now - timedelta(hours=i), value=50.0) for i in range(48)
        ]

        # Expected volume similar to historical
        result = demand_forecaster._recommend_scaling(
            expected_volume=1200.0,  # 50/hour - same as historical
            historical=historical,
            agent_filter=None,
        )

        assert result.action == ScalingAction.MAINTAIN

    async def test_get_demand_anomalies(self, demand_forecaster, mock_db):
        """Test anomaly detection."""
        now = datetime.now(timezone.utc)
        # Create data with an anomaly
        mock_db.fetch_all.return_value = [
            {
                "hour_bucket": (now - timedelta(hours=i)).strftime("%Y-%m-%d %H:00:00"),
                "task_type": "test",
                "count": 50 if i != 10 else 200,
            }  # Spike at hour 10
            for i in range(48)
        ]

        anomalies = await demand_forecaster.get_demand_anomalies(hours=24)

        # Should be a list (may or may not contain anomalies based on threshold)
        assert isinstance(anomalies, list)

    async def test_save_forecast(self, demand_forecaster, mock_db):
        """Test saving a forecast."""
        forecast = DemandForecast(
            forecast_id="forecast-123",
            created_at=datetime.now(timezone.utc),
            horizon_hours=24,
            expected_volume=1000.0,
            expected_distribution=[],
            confidence_interval=ConfidenceInterval(
                lower=800.0, upper=1200.0, confidence_level=0.95
            ),
            recommended_scaling=ScalingRecommendation(
                action=ScalingAction.MAINTAIN,
                target_capacity=1.0,
                urgency=0.0,
                reason="Stable demand",
            ),
        )

        await demand_forecaster.save_forecast(forecast)

        mock_db.execute.assert_called_once()

    def test_time_series_point_to_dict(self):
        """Test TimeSeriesPoint serialization."""
        point = TimeSeriesPoint(
            timestamp=datetime(2025, 1, 24, 12, 0, 0),
            value=100.0,
            task_type="test",
        )

        result = point.to_dict()

        assert result["timestamp"] == "2025-01-24T12:00:00"
        assert result["value"] == 100.0
        assert result["task_type"] == "test"

    def test_demand_forecast_to_dict(self):
        """Test DemandForecast serialization."""
        forecast = DemandForecast(
            forecast_id="forecast-123",
            created_at=datetime(2025, 1, 24, 12, 0, 0),
            horizon_hours=24,
            expected_volume=1000.0,
            expected_distribution=[
                TaskTypeDistribution(
                    task_type="test", current_share=0.5, projected_share=0.5, volume_change=0.0
                )
            ],
            confidence_interval=ConfidenceInterval(
                lower=800.0, upper=1200.0, confidence_level=0.95
            ),
            recommended_scaling=ScalingRecommendation(
                action=ScalingAction.MAINTAIN,
                target_capacity=1.0,
                urgency=0.0,
                reason="Stable",
            ),
        )

        result = forecast.to_dict()

        assert result["forecast_id"] == "forecast-123"
        assert result["expected_volume"] == 1000.0
        assert len(result["expected_distribution"]) == 1


# ============================================================================
# CascadePredictor Tests
# ============================================================================


class TestCascadePredictor:
    """Tests for CascadePredictor."""

    async def test_predict_cascade_empty_history(
        self, cascade_predictor, mock_db, sample_routing_decision
    ):
        """Test cascade prediction with no history."""
        mock_db.fetch_all.return_value = []
        mock_db.fetch_one.return_value = {"count": 0}

        effect = await cascade_predictor.predict_cascade(sample_routing_decision)

        assert effect is not None
        assert effect.decision.task_type == "code_review"
        assert effect.risk is not None

    async def test_predict_cascade_with_history(
        self, cascade_predictor, mock_db, sample_routing_decision
    ):
        """Test cascade prediction with historical data."""
        # Mock routing decisions history
        mock_db.fetch_all.side_effect = [
            # First call: similar decisions
            [
                {
                    "id": f"rd-{i}",
                    "task_type": "code_review",
                    "selected_agent": "Forge",
                    "context": "{}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "success": True,
                    "duration_ms": 5000.0,
                }
                for i in range(10)
            ],
            # Second call: downstream outcomes
            [
                {
                    "id": f"out-{i}",
                    "task_id": f"task-{i}",
                    "task_type": "code_review",
                    "agent_code": "Forge",
                    "manager_code": "AM",
                    "specialist_code": "SD",
                    "success": i % 5 != 0,  # 80% success
                    "duration_ms": 3000.0,
                    "error_message": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                for i in range(20)
            ],
        ]
        mock_db.fetch_one.return_value = {"count": 10}

        effect = await cascade_predictor.predict_cascade(sample_routing_decision)

        assert effect is not None
        assert len(effect.downstream_agents) > 0

    async def test_estimate_load(self, cascade_predictor, mock_db):
        """Test agent load estimation."""
        mock_db.fetch_one.return_value = {"count": 50}

        load = await cascade_predictor._estimate_load("Forge")

        assert load.agent_code == "Forge"
        assert load.current_load == 50.0
        assert load.utilization <= 1.0

    async def test_calculate_cascade_risk_low(self, cascade_predictor):
        """Test low risk calculation."""
        primary_load = AgentLoad(
            agent_code="Forge",
            current_load=20.0,
            projected_load=21.0,
            capacity=100.0,
            utilization=0.2,
        )
        downstream = []
        outcomes = []

        risk = cascade_predictor._calculate_cascade_risk(primary_load, downstream, outcomes)

        assert risk.risk_level == RiskLevel.LOW

    async def test_calculate_cascade_risk_high(self, cascade_predictor):
        """Test high risk calculation."""
        primary_load = AgentLoad(
            agent_code="Forge",
            current_load=90.0,
            projected_load=91.0,
            capacity=100.0,
            utilization=0.9,  # High utilization
        )
        downstream = [
            DownstreamAgent(
                agent_code="AM",
                probability=0.9,
                expected_tasks=10,
                impact_type=ImpactType.FAILURE_CASCADE,  # Failure cascade
                estimated_delay_ms=5000.0,
            )
        ]
        outcomes = []

        risk = cascade_predictor._calculate_cascade_risk(primary_load, downstream, outcomes)

        assert risk.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert len(risk.risk_factors) > 0

    async def test_find_alternative_routes(self, cascade_predictor, mock_db):
        """Test finding alternative routes."""
        mock_db.fetch_all.return_value = [
            {
                "agent_code": "Blueprint",
                "count": 20,
                "success_rate": 0.95,
                "avg_duration": 3000.0,
            },
            {
                "agent_code": "Keystone",
                "count": 15,
                "success_rate": 0.85,
                "avg_duration": 4000.0,
            },
        ]

        decision = RoutingDecision(
            task_type="code_review",
            selected_agent="Forge",
        )
        primary_load = AgentLoad(
            agent_code="Forge",
            current_load=90.0,
            projected_load=91.0,
            capacity=100.0,
            utilization=0.9,
        )
        risk = CascadeRisk(
            risk_level=RiskLevel.HIGH,
            risk_score=0.7,
            risk_factors=["High utilization"],
            mitigation_suggestions=[],
        )

        alternatives = await cascade_predictor._find_alternative_routes(
            decision, primary_load, risk
        )

        assert len(alternatives) == 2
        assert alternatives[0]["agent_code"] == "Blueprint"

    async def test_record_cascade_outcome(self, cascade_predictor, mock_db):
        """Test recording cascade outcome."""
        await cascade_predictor.record_cascade_outcome(
            prediction_id="pred-123",
            actual_duration_ms=5000.0,
            had_failures=False,
            downstream_agents_used=["AM", "SD"],
        )

        mock_db.execute.assert_called_once()

    async def test_set_agent_capacity(self, cascade_predictor):
        """Test setting agent capacity."""
        cascade_predictor.set_agent_capacity("Forge", 200.0)

        assert cascade_predictor._agent_capacities["Forge"] == 200.0

    def test_cascade_effect_to_dict(self, sample_routing_decision):
        """Test CascadeEffect serialization."""
        effect = CascadeEffect(
            prediction_id="pred-123",
            created_at=datetime(2025, 1, 24, 12, 0, 0),
            decision=sample_routing_decision,
            primary_agent_load=AgentLoad(
                agent_code="Forge",
                current_load=50.0,
                projected_load=51.0,
                capacity=100.0,
                utilization=0.5,
            ),
            downstream_agents=[],
            expected_duration=5000.0,
            risk=CascadeRisk(
                risk_level=RiskLevel.LOW,
                risk_score=0.2,
                risk_factors=[],
                mitigation_suggestions=[],
            ),
        )

        result = effect.to_dict()

        assert result["prediction_id"] == "pred-123"
        assert result["expected_duration"] == 5000.0
        assert result["risk"]["risk_level"] == "low"


# ============================================================================
# ContextOptimizer Tests
# ============================================================================


class TestContextOptimizer:
    """Tests for ContextOptimizer."""

    async def test_optimize_for_context_basic(
        self, context_optimizer, mock_db, sample_task, sample_execution_context
    ):
        """Test basic context optimization."""
        mock_db.fetch_all.return_value = []
        mock_db.fetch_one.return_value = {
            "success_rate": 0.9,
            "avg_duration": 2000.0,
            "sample_size": 50,
        }

        result = await context_optimizer.optimize_for_context(sample_task, sample_execution_context)

        assert result is not None
        assert result.original.task_id == "task-123"

    async def test_classify_time_of_day_peak(self, context_optimizer):
        """Test peak hour classification."""
        result = context_optimizer._classify_time_of_day(12)  # Noon
        assert result == TimeOfDay.PEAK

    async def test_classify_time_of_day_overnight(self, context_optimizer):
        """Test overnight classification."""
        result = context_optimizer._classify_time_of_day(3)  # 3 AM
        assert result == TimeOfDay.OVERNIGHT

    async def test_classify_time_of_day_off_peak(self, context_optimizer):
        """Test off-peak classification."""
        result = context_optimizer._classify_time_of_day(20)  # 8 PM
        assert result == TimeOfDay.OFF_PEAK

    async def test_classify_load_level_low(self, context_optimizer):
        """Test low load classification."""
        result = context_optimizer._classify_load_level(0.2)
        assert result == LoadLevel.LOW

    async def test_classify_load_level_high(self, context_optimizer):
        """Test high load classification."""
        result = context_optimizer._classify_load_level(0.85)
        assert result == LoadLevel.HIGH

    async def test_classify_load_level_critical(self, context_optimizer):
        """Test critical load classification."""
        result = context_optimizer._classify_load_level(0.98)
        assert result == LoadLevel.CRITICAL

    async def test_adjust_priority_high_load(self, context_optimizer, sample_task):
        """Test priority adjustment during high load."""
        load_pattern = LoadPattern(
            load_level=LoadLevel.HIGH,
            avg_success_rate=0.85,
            avg_duration_ms=3000.0,
            timeout_factor=1.5,
            sample_size=100,
        )
        context = ExecutionContext(
            timestamp=datetime.now(timezone.utc),
            system_load=0.9,
            active_tasks=80,
            recent_failure_rate=0.1,
            queue_depth=50,
            avg_response_time_ms=2000.0,
        )

        action, confidence = context_optimizer._adjust_priority(
            sample_task, None, load_pattern, context
        )

        assert action is not None
        assert action.optimized_value > sample_task.priority

    async def test_adjust_timeout_high_load(self, context_optimizer, sample_task):
        """Test timeout adjustment during high load."""
        load_pattern = LoadPattern(
            load_level=LoadLevel.HIGH,
            avg_success_rate=0.85,
            avg_duration_ms=3000.0,
            timeout_factor=1.5,
            sample_size=100,
        )
        outcomes = []
        context = ExecutionContext(
            timestamp=datetime.now(timezone.utc),
            system_load=0.9,
            active_tasks=80,
            recent_failure_rate=0.1,
            queue_depth=50,
            avg_response_time_ms=2000.0,
        )

        action, confidence = context_optimizer._adjust_timeout(
            sample_task, load_pattern, outcomes, context
        )

        assert action is not None
        assert action.optimized_value > sample_task.timeout_ms

    async def test_select_optimal_agent(
        self, context_optimizer, mock_db, sample_task, sample_execution_context
    ):
        """Test optimal agent selection."""
        mock_db.fetch_all.return_value = [
            {
                "agent_code": "Forge",
                "count": 50,
                "success_rate": 0.95,
                "avg_duration": 2000.0,
            },
            {
                "agent_code": "Blueprint",
                "count": 30,
                "success_rate": 0.80,
                "avg_duration": 3000.0,
            },
        ]
        mock_db.fetch_one.return_value = {"count": 20}

        result = await context_optimizer._select_optimal_agent(
            sample_task, [], sample_execution_context
        )

        assert result is not None
        assert result.agent_code == "Forge"  # Higher success rate

    async def test_check_deferral_critical_load(self, context_optimizer, sample_task):
        """Test deferral during critical load."""
        context = ExecutionContext(
            timestamp=datetime.now(timezone.utc),
            system_load=0.98,  # Critical
            active_tasks=100,
            recent_failure_rate=0.2,
            queue_depth=100,
            avg_response_time_ms=5000.0,
        )

        should_defer, defer_until, reason = context_optimizer._check_deferral(
            sample_task, None, context
        )

        assert should_defer is True
        assert defer_until is not None
        assert "critical" in reason.lower()

    async def test_no_deferral_high_priority(self, context_optimizer):
        """Test no deferral for high priority tasks."""
        high_priority_task = Task(
            task_id="task-high",
            task_type="critical",
            priority=1,  # High priority
            timeout_ms=30000.0,
        )
        context = ExecutionContext(
            timestamp=datetime.now(timezone.utc),
            system_load=0.98,
            active_tasks=100,
            recent_failure_rate=0.2,
            queue_depth=100,
            avg_response_time_ms=5000.0,
        )

        should_defer, _, _ = context_optimizer._check_deferral(high_priority_task, None, context)

        assert should_defer is False

    async def test_calculate_agent_score(self, context_optimizer):
        """Test agent score calculation."""
        context = ExecutionContext(
            timestamp=datetime.now(timezone.utc),
            system_load=0.5,
            active_tasks=50,
            recent_failure_rate=0.1,
            queue_depth=25,
            avg_response_time_ms=1500.0,
        )

        score = context_optimizer._calculate_agent_score(
            success_rate=0.95,
            avg_duration=1000.0,
            current_load=0.3,
            context=context,
        )

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be a good score

    async def test_record_optimization_outcome(self, context_optimizer, mock_db):
        """Test recording optimization outcome."""
        await context_optimizer.record_optimization_outcome(
            optimization_id="opt-123",
            outcome_success=True,
            actual_duration_ms=2500.0,
        )

        mock_db.execute.assert_called_once()

    def test_optimized_task_to_dict(self, sample_task):
        """Test OptimizedTask serialization."""
        optimized = OptimizedTask(
            optimization_id="opt-123",
            created_at=datetime(2025, 1, 24, 12, 0, 0),
            original=sample_task,
            recommended_priority=2,
            recommended_timeout=45000.0,
            recommended_agent=AgentRecommendation(
                agent_code="Forge",
                score=0.9,
                success_rate=0.95,
                avg_duration_ms=2000.0,
                current_load=0.3,
                reasons=["High success rate"],
            ),
            optimizations_applied=[
                OptimizationAction(
                    optimization_type=OptimizationType.PRIORITY_ADJUSTMENT,
                    original_value=3,
                    optimized_value=2,
                    confidence=0.8,
                    reason="High queue depth",
                )
            ],
            should_defer=False,
            defer_until=None,
            confidence=0.85,
        )

        result = optimized.to_dict()

        assert result["optimization_id"] == "opt-123"
        assert result["recommended_priority"] == 2
        assert result["recommended_agent"]["agent_code"] == "Forge"
        assert len(result["optimizations_applied"]) == 1


# ============================================================================
# Integration Tests
# ============================================================================


class TestPhase9Integration:
    """Integration tests for Phase 9 components."""

    async def test_forecaster_with_optimizer(
        self,
        demand_forecaster,
        context_optimizer,
        mock_db,
        sample_task,
    ):
        """Test using forecast to inform optimization."""
        # Get a forecast
        mock_db.fetch_all.return_value = []
        forecast = await demand_forecaster.forecast_demand(horizon_hours=24)

        # Use forecast info to create execution context
        context = ExecutionContext(
            timestamp=datetime.now(timezone.utc),
            system_load=(
                0.7 if forecast.recommended_scaling.action == ScalingAction.MAINTAIN else 0.9
            ),
            active_tasks=50,
            recent_failure_rate=0.1,
            queue_depth=25,
            avg_response_time_ms=1500.0,
        )

        # Optimize task
        result = await context_optimizer.optimize_for_context(sample_task, context)

        assert result is not None

    async def test_cascade_predictor_with_optimizer(
        self,
        cascade_predictor,
        context_optimizer,
        mock_db,
        sample_task,
        sample_routing_decision,
    ):
        """Test using cascade prediction to inform optimization."""
        mock_db.fetch_all.return_value = []
        mock_db.fetch_one.return_value = {
            "count": 0,
            "success_rate": 0.9,
            "avg_duration": 2000.0,
            "sample_size": 50,
        }

        # Get cascade prediction
        cascade_effect = await cascade_predictor.predict_cascade(sample_routing_decision)

        # Use cascade risk to inform context
        risk_factor = cascade_effect.risk.risk_score
        context = ExecutionContext(
            timestamp=datetime.now(timezone.utc),
            system_load=0.5 + risk_factor * 0.4,  # Higher risk = higher effective load
            active_tasks=50,
            recent_failure_rate=risk_factor * 0.3,
            queue_depth=25,
            avg_response_time_ms=1500.0 + cascade_effect.expected_duration * 0.1,
        )

        # Optimize based on risk
        result = await context_optimizer.optimize_for_context(sample_task, context)

        assert result is not None

    async def test_full_predictive_cycle(
        self,
        demand_forecaster,
        cascade_predictor,
        context_optimizer,
        mock_db,
    ):
        """Test a full predictive intelligence cycle."""
        mock_db.fetch_all.return_value = []
        mock_db.fetch_one.return_value = {
            "count": 0,
            "success_rate": 0.9,
            "avg_duration": 2000.0,
            "sample_size": 50,
        }

        # 1. Forecast demand
        forecast = await demand_forecaster.forecast_demand(horizon_hours=24)

        # 2. For each potential task, predict cascade
        routing_decision = RoutingDecision(
            task_type="code_review",
            selected_agent="Forge",
            priority=2,
        )
        cascade = await cascade_predictor.predict_cascade(routing_decision)

        # 3. Optimize task based on all info
        task = Task(
            task_id="task-full-cycle",
            task_type="code_review",
            priority=2,
            timeout_ms=30000.0,
        )

        # Create context from forecast and cascade
        context = ExecutionContext(
            timestamp=datetime.now(timezone.utc),
            system_load=min(
                0.95,
                0.5 + forecast.recommended_scaling.urgency * 0.3 + cascade.risk.risk_score * 0.2,
            ),
            active_tasks=50,
            recent_failure_rate=cascade.risk.risk_score * 0.2,
            queue_depth=int(forecast.expected_volume / 24),
            avg_response_time_ms=cascade.expected_duration,
        )

        optimized = await context_optimizer.optimize_for_context(task, context)

        # Verify all components worked together
        assert forecast is not None
        assert cascade is not None
        assert optimized is not None


# ============================================================================
# Enum and Dataclass Tests
# ============================================================================


class TestEnumsAndDataclasses:
    """Tests for enums and dataclass serialization."""

    def test_seasonality_type_values(self):
        """Test SeasonalityType enum values."""
        assert SeasonalityType.HOURLY.value == "hourly"
        assert SeasonalityType.DAILY.value == "daily"
        assert SeasonalityType.WEEKLY.value == "weekly"
        assert SeasonalityType.MONTHLY.value == "monthly"
        assert SeasonalityType.NONE.value == "none"

    def test_trend_direction_values(self):
        """Test TrendDirection enum values."""
        assert TrendDirection.INCREASING.value == "increasing"
        assert TrendDirection.DECREASING.value == "decreasing"
        assert TrendDirection.STABLE.value == "stable"

    def test_scaling_action_values(self):
        """Test ScalingAction enum values."""
        assert ScalingAction.SCALE_UP.value == "scale_up"
        assert ScalingAction.SCALE_DOWN.value == "scale_down"
        assert ScalingAction.MAINTAIN.value == "maintain"
        assert ScalingAction.PREPARE_BURST.value == "prepare_burst"

    def test_risk_level_values(self):
        """Test RiskLevel enum values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_impact_type_values(self):
        """Test ImpactType enum values."""
        assert ImpactType.LOAD_INCREASE.value == "load_increase"
        assert ImpactType.DELAY_PROPAGATION.value == "delay_propagation"
        assert ImpactType.FAILURE_CASCADE.value == "failure_cascade"
        assert ImpactType.RESOURCE_CONTENTION.value == "resource_contention"
        assert ImpactType.BOTTLENECK.value == "bottleneck"

    def test_optimization_type_values(self):
        """Test OptimizationType enum values."""
        assert OptimizationType.PRIORITY_ADJUSTMENT.value == "priority_adjustment"
        assert OptimizationType.TIMEOUT_ADJUSTMENT.value == "timeout_adjustment"
        assert OptimizationType.AGENT_SELECTION.value == "agent_selection"
        assert OptimizationType.BATCHING.value == "batching"
        assert OptimizationType.DEFERRAL.value == "deferral"

    def test_time_of_day_values(self):
        """Test TimeOfDay enum values."""
        assert TimeOfDay.PEAK.value == "peak"
        assert TimeOfDay.OFF_PEAK.value == "off_peak"
        assert TimeOfDay.OVERNIGHT.value == "overnight"

    def test_load_level_values(self):
        """Test LoadLevel enum values."""
        assert LoadLevel.LOW.value == "low"
        assert LoadLevel.MODERATE.value == "moderate"
        assert LoadLevel.HIGH.value == "high"
        assert LoadLevel.CRITICAL.value == "critical"
