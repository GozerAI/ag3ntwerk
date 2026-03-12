"""
Unit tests for the Failure Predictor.

Tests:
- Risk score calculation
- Error pattern analysis
- Agent health assessment
- Mitigation recommendations
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.learning.failure_predictor import (
    FailurePredictor,
    FailureRisk,
    RiskLevel,
    Mitigation,
    MitigationType,
    ErrorPatternStats,
)
from ag3ntwerk.learning.models import ErrorCategory


class TestRiskLevel:
    """Test RiskLevel enum."""

    def test_risk_levels_exist(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MODERATE.value == "moderate"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"


class TestMitigationType:
    """Test MitigationType enum."""

    def test_mitigation_types_exist(self):
        assert MitigationType.EXTEND_TIMEOUT.value == "extend_timeout"
        assert MitigationType.USE_FALLBACK_AGENT.value == "use_fallback_agent"
        assert MitigationType.ADD_RETRY.value == "add_retry"
        assert MitigationType.ALERT_HUMAN.value == "alert_human"


class TestMitigation:
    """Test Mitigation dataclass."""

    def test_creation(self):
        mitigation = Mitigation(
            mitigation_type=MitigationType.EXTEND_TIMEOUT,
            description="Extend timeout by 50%",
            confidence=0.8,
        )
        assert mitigation.mitigation_type == MitigationType.EXTEND_TIMEOUT
        assert mitigation.confidence == 0.8

    def test_to_dict(self):
        mitigation = Mitigation(
            mitigation_type=MitigationType.ADD_RETRY,
            description="Add retry logic",
            confidence=0.7,
            parameters={"max_retries": 3},
        )
        d = mitigation.to_dict()
        assert d["type"] == "add_retry"
        assert d["confidence"] == 0.7
        assert d["parameters"]["max_retries"] == 3


class TestErrorPatternStats:
    """Test ErrorPatternStats dataclass."""

    def test_creation(self):
        stats = ErrorPatternStats(
            task_type="code_review",
            agent_code="Forge",
            total_tasks=100,
            failed_tasks=20,
        )
        assert stats.failure_rate == 0.2

    def test_most_common_error_timeout(self):
        stats = ErrorPatternStats(
            task_type="code_review",
            agent_code="Forge",
            total_tasks=100,
            failed_tasks=20,
            timeout_count=15,
            capability_count=3,
            resource_count=2,
        )
        assert stats.most_common_error == ErrorCategory.TIMEOUT

    def test_most_common_error_capability(self):
        stats = ErrorPatternStats(
            task_type="code_review",
            agent_code="Forge",
            total_tasks=100,
            failed_tasks=20,
            timeout_count=3,
            capability_count=15,
            resource_count=2,
        )
        assert stats.most_common_error == ErrorCategory.CAPABILITY

    def test_most_common_error_none_when_no_failures(self):
        stats = ErrorPatternStats(
            task_type="code_review",
            agent_code="Forge",
            total_tasks=100,
            failed_tasks=0,
        )
        assert stats.most_common_error is None

    def test_failure_rate_zero_tasks(self):
        stats = ErrorPatternStats(
            task_type="code_review",
            agent_code="Forge",
            total_tasks=0,
            failed_tasks=0,
        )
        assert stats.failure_rate == 0.0


class TestFailureRisk:
    """Test FailureRisk dataclass."""

    def test_creation(self):
        risk = FailureRisk(
            score=0.45,
            risk_level=RiskLevel.MODERATE,
            primary_risk=ErrorCategory.TIMEOUT,
            task_type="code_review",
            agent_code="Forge",
        )
        assert risk.score == 0.45
        assert risk.risk_level == RiskLevel.MODERATE

    def test_to_dict(self):
        risk = FailureRisk(
            score=0.75,
            risk_level=RiskLevel.HIGH,
            primary_risk=ErrorCategory.CAPABILITY,
            task_type="code_review",
            agent_code="Forge",
            risk_factors=["High failure rate"],
            mitigations=[Mitigation(MitigationType.USE_FALLBACK_AGENT, "Use fallback", 0.7)],
        )
        d = risk.to_dict()
        assert d["score"] == 0.75
        assert d["risk_level"] == "high"
        assert len(d["risk_factors"]) == 1
        assert len(d["mitigations"]) == 1


class TestFailurePredictor:
    """Test FailurePredictor class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def predictor(self, mock_db):
        """Create a FailurePredictor instance."""
        return FailurePredictor(mock_db)

    @pytest.mark.asyncio
    async def test_predict_low_risk(self, predictor, mock_db):
        """Test prediction with no risk indicators."""
        # Agent with good health
        mock_db.fetch_one.return_value = {
            "health_score": 0.95,
            "circuit_breaker_open": 0,
            "consecutive_failures": 0,
            "last_failure_at": None,
            "avg_duration_ms": 500,
        }

        risk = await predictor.predict_failure_risk(
            task_type="code_review",
            target_agent="Forge",
        )

        assert risk.risk_level == RiskLevel.LOW
        assert risk.score < 0.3

    @pytest.mark.asyncio
    async def test_predict_with_error_history(self, predictor, mock_db):
        """Test prediction with error history."""
        # First call: error pattern stats, second call: agent health, third: load
        mock_db.fetch_one.side_effect = [
            # Error pattern stats
            {
                "total": 100,
                "failed": 30,
                "timeout_count": 20,
                "capability_count": 5,
                "resource_count": 3,
                "logic_count": 1,
                "external_count": 1,
            },
            # Agent health
            {
                "health_score": 0.8,
                "circuit_breaker_open": 0,
                "consecutive_failures": 1,
                "last_failure_at": None,
                "avg_duration_ms": 500,
            },
            # Load metrics
            {"recent_tasks": 5},
        ]

        risk = await predictor.predict_failure_risk(
            task_type="code_review",
            target_agent="Forge",
        )

        # Should have elevated risk due to error history
        assert risk.score > 0.2
        assert (
            "High failure rate" in " ".join(risk.risk_factors)
            or risk.primary_risk == ErrorCategory.TIMEOUT
        )

    @pytest.mark.asyncio
    async def test_predict_critical_circuit_breaker_open(self, predictor, mock_db):
        """Test prediction when circuit breaker is open."""
        mock_db.fetch_one.side_effect = [
            # Error pattern stats - None
            None,
            # Agent health with open circuit breaker
            {
                "health_score": 0.1,
                "circuit_breaker_open": 1,  # Circuit breaker open!
                "consecutive_failures": 10,
                "last_failure_at": datetime.now(timezone.utc).isoformat(),
                "avg_duration_ms": 500,
            },
            # Load metrics
            {"recent_tasks": 0},
        ]

        risk = await predictor.predict_failure_risk(
            task_type="code_review",
            target_agent="Forge",
        )

        # Should recommend fallback agent
        assert any(m.mitigation_type == MitigationType.USE_FALLBACK_AGENT for m in risk.mitigations)

    @pytest.mark.asyncio
    async def test_predict_with_context(self, predictor, mock_db):
        """Test prediction with context factors."""
        mock_db.fetch_one.side_effect = [
            None,  # No error stats
            {
                "health_score": 0.9,
                "circuit_breaker_open": 0,
                "consecutive_failures": 0,
                "last_failure_at": None,
                "avg_duration_ms": 500,
            },
            {"recent_tasks": 0},
        ]

        # Context with complexity indicator
        risk = await predictor.predict_failure_risk(
            task_type="code_review",
            target_agent="Forge",
            context={"complexity": "high", "priority": "critical"},
        )

        # Should increase risk due to complexity
        assert risk.context_score > 0

    @pytest.mark.asyncio
    async def test_mitigations_for_timeout_risk(self, predictor, mock_db):
        """Test that timeout mitigations are recommended."""
        mock_db.fetch_one.side_effect = [
            # Error stats with timeout errors
            {
                "total": 100,
                "failed": 30,
                "timeout_count": 25,  # High timeout rate
                "capability_count": 2,
                "resource_count": 1,
                "logic_count": 1,
                "external_count": 1,
            },
            {
                "health_score": 0.7,
                "circuit_breaker_open": 0,
                "consecutive_failures": 2,
                "last_failure_at": None,
                "avg_duration_ms": 5000,
            },
            {"recent_tasks": 5},
        ]

        risk = await predictor.predict_failure_risk(
            task_type="long_running_task",
            target_agent="Forge",
        )

        mitigation_types = [m.mitigation_type for m in risk.mitigations]
        assert MitigationType.EXTEND_TIMEOUT in mitigation_types

    @pytest.mark.asyncio
    async def test_mitigations_for_capability_risk(self, predictor, mock_db):
        """Test that capability mitigations are recommended."""
        mock_db.fetch_one.side_effect = [
            # Error stats with capability errors
            {
                "total": 100,
                "failed": 30,
                "timeout_count": 2,
                "capability_count": 25,  # High capability failure rate
                "resource_count": 1,
                "logic_count": 1,
                "external_count": 1,
            },
            {
                "health_score": 0.7,
                "circuit_breaker_open": 0,
                "consecutive_failures": 1,
                "last_failure_at": None,
                "avg_duration_ms": 500,
            },
            {"recent_tasks": 0},
        ]

        risk = await predictor.predict_failure_risk(
            task_type="specialized_task",
            target_agent="Forge",
        )

        assert risk.primary_risk == ErrorCategory.CAPABILITY
        mitigation_types = [m.mitigation_type for m in risk.mitigations]
        assert MitigationType.USE_FALLBACK_AGENT in mitigation_types

    @pytest.mark.asyncio
    async def test_risk_score_clamped(self, predictor, mock_db):
        """Test that risk score is clamped to [0, 1]."""
        # Worst case scenario
        mock_db.fetch_one.side_effect = [
            # High failure rate
            {
                "total": 100,
                "failed": 95,
                "timeout_count": 50,
                "capability_count": 25,
                "resource_count": 10,
                "logic_count": 5,
                "external_count": 5,
            },
            {
                "health_score": 0.0,
                "circuit_breaker_open": 1,
                "consecutive_failures": 100,
                "last_failure_at": datetime.now(timezone.utc).isoformat(),
                "avg_duration_ms": 10000,
            },
            {"recent_tasks": 100},
        ]

        risk = await predictor.predict_failure_risk(
            task_type="doomed_task",
            target_agent="Forge",
            context={"complexity": "high"},
        )

        assert 0.0 <= risk.score <= 1.0

    @pytest.mark.asyncio
    async def test_get_high_risk_agents(self, predictor, mock_db):
        """Test finding high-risk agents."""
        # Mock getting agents
        mock_db.fetch_all.return_value = [
            {"agent_code": "Forge"},
            {"agent_code": "Keystone"},
        ]

        # Mock fetch_one for each agent's stats
        mock_db.fetch_one.side_effect = [
            # Forge error stats - high failure
            {
                "total": 100,
                "failed": 60,
                "timeout_count": 40,
                "capability_count": 10,
                "resource_count": 5,
                "logic_count": 3,
                "external_count": 2,
            },
            # Forge health - bad
            {
                "health_score": 0.4,
                "circuit_breaker_open": 0,
                "consecutive_failures": 5,
                "last_failure_at": None,
                "avg_duration_ms": 5000,
            },
            # Forge load
            {"recent_tasks": 10},
            # Keystone error stats - low failure
            {
                "total": 100,
                "failed": 5,
                "timeout_count": 2,
                "capability_count": 1,
                "resource_count": 1,
                "logic_count": 1,
                "external_count": 0,
            },
            # Keystone health - good
            {
                "health_score": 0.95,
                "circuit_breaker_open": 0,
                "consecutive_failures": 0,
                "last_failure_at": None,
                "avg_duration_ms": 300,
            },
            # Keystone load
            {"recent_tasks": 2},
        ]

        high_risk = await predictor.get_high_risk_agents("code_review", threshold=0.3)

        # Forge should be high risk
        agent_codes = [a[0] for a in high_risk]
        assert "Forge" in agent_codes

    @pytest.mark.asyncio
    async def test_get_safest_agent(self, predictor, mock_db):
        """Test finding safest agent."""
        # Mock different risk levels for different agents
        mock_db.fetch_one.side_effect = [
            # Forge - high risk
            {
                "total": 100,
                "failed": 50,
                "timeout_count": 30,
                "capability_count": 10,
                "resource_count": 5,
                "logic_count": 3,
                "external_count": 2,
            },
            {
                "health_score": 0.5,
                "circuit_breaker_open": 0,
                "consecutive_failures": 3,
                "last_failure_at": None,
                "avg_duration_ms": 3000,
            },
            {"recent_tasks": 5},
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
                "circuit_breaker_open": 0,
                "consecutive_failures": 0,
                "last_failure_at": None,
                "avg_duration_ms": 300,
            },
            {"recent_tasks": 1},
        ]

        result = await predictor.get_safest_agent("code_review", ["Forge", "Keystone"])

        assert result is not None
        agent_code, risk = result
        assert agent_code == "Keystone"  # Keystone has lower risk

    @pytest.mark.asyncio
    async def test_get_safest_agent_empty_candidates(self, predictor, mock_db):
        """Test get_safest_agent with no candidates."""
        result = await predictor.get_safest_agent("code_review", [])
        assert result is None


class TestFailurePredictorEdgeCases:
    """Test edge cases for FailurePredictor."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.mark.asyncio
    async def test_no_historical_data(self, mock_db):
        """Test prediction with no historical data."""
        predictor = FailurePredictor(mock_db)

        risk = await predictor.predict_failure_risk(
            task_type="new_task_type",
            target_agent="NEW_AGENT",
        )

        # Should return with baseline risk
        assert risk is not None
        assert risk.task_type == "new_task_type"
        assert risk.agent_code == "NEW_AGENT"

    @pytest.mark.asyncio
    async def test_database_error_handling(self, mock_db):
        """Test graceful handling of database errors."""
        mock_db.fetch_one.side_effect = Exception("Database error")
        predictor = FailurePredictor(mock_db)

        # Should not raise, should return default risk
        risk = await predictor.predict_failure_risk(
            task_type="code_review",
            target_agent="Forge",
        )

        assert risk is not None

    @pytest.mark.asyncio
    async def test_empty_context(self, mock_db):
        """Test prediction with empty context."""
        mock_db.fetch_one.return_value = {
            "health_score": 0.8,
            "circuit_breaker_open": 0,
            "consecutive_failures": 0,
            "last_failure_at": None,
            "avg_duration_ms": 500,
        }
        predictor = FailurePredictor(mock_db)

        risk = await predictor.predict_failure_risk(
            task_type="code_review",
            target_agent="Forge",
            context={},
        )

        assert risk is not None
        assert risk.context_score == 0.0

    @pytest.mark.asyncio
    async def test_weights_sum_to_one(self, mock_db):
        """Verify prediction weights sum to 1.0."""
        predictor = FailurePredictor(mock_db)
        total_weight = sum(predictor.WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.001
