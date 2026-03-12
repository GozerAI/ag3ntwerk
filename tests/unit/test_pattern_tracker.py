"""
Unit tests for the Pattern Tracker.

Tests:
- Recording pattern applications
- Recording outcomes and updating stats
- Calculating pattern effectiveness
- Identifying declining patterns
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.learning.pattern_tracker import (
    PatternTracker,
    PatternApplication,
    PatternEffectiveness,
)


class TestPatternApplication:
    """Test PatternApplication dataclass."""

    def test_creation(self):
        app = PatternApplication(
            pattern_id="pat-123",
            task_id="task-456",
            task_type="code_review",
            agent_code="Forge",
        )
        assert app.pattern_id == "pat-123"
        assert app.task_id == "task-456"
        assert app.task_type == "code_review"
        assert app.outcome_recorded is False

    def test_to_dict(self):
        app = PatternApplication(
            pattern_id="pat-123",
            task_id="task-456",
            task_type="code_review",
            agent_code="Forge",
            was_routing_pattern=True,
        )
        d = app.to_dict()
        assert d["pattern_id"] == "pat-123"
        assert d["was_routing_pattern"] is True


class TestPatternEffectiveness:
    """Test PatternEffectiveness dataclass."""

    def test_creation(self):
        now = datetime.now(timezone.utc)
        eff = PatternEffectiveness(
            pattern_id="pat-123",
            window_start=now - timedelta(hours=24),
            window_end=now,
            total_applications=100,
            successful_applications=85,
            success_rate=0.85,
        )
        assert eff.total_applications == 100
        assert eff.success_rate == 0.85

    def test_improvement_over_baseline(self):
        now = datetime.now(timezone.utc)
        eff = PatternEffectiveness(
            pattern_id="pat-123",
            window_start=now - timedelta(hours=24),
            window_end=now,
            success_rate=0.85,
            baseline_success_rate=0.70,
            improvement_over_baseline=0.15,
            is_improving=True,
        )
        assert eff.improvement_over_baseline == 0.15
        assert eff.is_improving is True


class TestPatternTracker:
    """Test PatternTracker class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def tracker(self, mock_db):
        """Create a PatternTracker instance."""
        return PatternTracker(mock_db)

    @pytest.mark.asyncio
    async def test_record_application(self, tracker, mock_db):
        """Test recording a pattern application."""
        app_id = await tracker.record_application(
            pattern_id="pat-123",
            task_id="task-456",
            task_type="code_review",
            agent_code="Forge",
            was_routing_pattern=True,
        )

        assert app_id is not None
        assert "task-456" in tracker._pending_applications
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_outcome_from_cache(self, tracker, mock_db):
        """Test recording outcome for a cached application."""
        # First record the application
        await tracker.record_application(
            pattern_id="pat-123",
            task_id="task-456",
            task_type="code_review",
            agent_code="Forge",
        )

        # Mock pattern stats query
        mock_db.fetch_one.return_value = {
            "application_count": 5,
            "success_rate": 0.8,
            "sample_size": 5,
        }

        # Record outcome
        await tracker.record_outcome(
            task_id="task-456",
            success=True,
            duration_ms=100.0,
            effectiveness=0.9,
        )

        # Should be removed from cache
        assert "task-456" not in tracker._pending_applications
        # Should have updated the database
        assert mock_db.execute.call_count >= 2  # Insert + update

    @pytest.mark.asyncio
    async def test_record_outcome_no_application(self, tracker, mock_db):
        """Test recording outcome when no application exists."""
        await tracker.record_outcome(
            task_id="nonexistent",
            success=True,
            duration_ms=100.0,
        )

        # Should not error, just return
        # Only fetch_one should be called to look up the application
        mock_db.fetch_one.assert_called()

    @pytest.mark.asyncio
    async def test_get_pattern_effectiveness_insufficient_data(self, tracker, mock_db):
        """Test effectiveness calculation with insufficient data."""
        mock_db.fetch_all.return_value = [
            # Only 3 applications - below MIN_APPLICATIONS_FOR_STATS
            {
                "id": "1",
                "pattern_id": "pat-123",
                "task_id": "t1",
                "task_type": "code_review",
                "agent_code": "Forge",
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "was_routing_pattern": 0,
                "was_confidence_pattern": 0,
                "outcome_recorded": 1,
                "outcome_success": 1,
                "outcome_duration_ms": 100,
                "outcome_effectiveness": 0.9,
                "baseline_agent": None,
                "baseline_success_rate": None,
            },
            {
                "id": "2",
                "pattern_id": "pat-123",
                "task_id": "t2",
                "task_type": "code_review",
                "agent_code": "Forge",
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "was_routing_pattern": 0,
                "was_confidence_pattern": 0,
                "outcome_recorded": 1,
                "outcome_success": 1,
                "outcome_duration_ms": 100,
                "outcome_effectiveness": 0.9,
                "baseline_agent": None,
                "baseline_success_rate": None,
            },
            {
                "id": "3",
                "pattern_id": "pat-123",
                "task_id": "t3",
                "task_type": "code_review",
                "agent_code": "Forge",
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "was_routing_pattern": 0,
                "was_confidence_pattern": 0,
                "outcome_recorded": 1,
                "outcome_success": 0,
                "outcome_duration_ms": 100,
                "outcome_effectiveness": 0.5,
                "baseline_agent": None,
                "baseline_success_rate": None,
            },
        ]

        result = await tracker.get_pattern_effectiveness("pat-123")

        # Should return None due to insufficient data
        assert result is None

    @pytest.mark.asyncio
    async def test_get_pattern_effectiveness_sufficient_data(self, tracker, mock_db):
        """Test effectiveness calculation with sufficient data."""
        # Create 10 applications (above MIN_APPLICATIONS_FOR_STATS)
        applications = []
        for i in range(10):
            applications.append(
                {
                    "id": str(i),
                    "pattern_id": "pat-123",
                    "task_id": f"t{i}",
                    "task_type": "code_review",
                    "agent_code": "Forge",
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                    "was_routing_pattern": 0,
                    "was_confidence_pattern": 0,
                    "outcome_recorded": 1,
                    "outcome_success": 1 if i < 8 else 0,  # 80% success
                    "outcome_duration_ms": 100,
                    "outcome_effectiveness": 0.9 if i < 8 else 0.3,
                    "baseline_agent": "Keystone",
                    "baseline_success_rate": 0.7,  # 70% baseline
                }
            )

        mock_db.fetch_all.return_value = applications

        result = await tracker.get_pattern_effectiveness("pat-123")

        assert result is not None
        assert result.total_applications == 10
        assert result.successful_applications == 8
        assert result.success_rate == 0.8
        assert result.baseline_success_rate == 0.7
        assert result.improvement_over_baseline == pytest.approx(0.1, abs=0.01)
        assert result.is_declining is False

    @pytest.mark.asyncio
    async def test_get_declining_patterns(self, tracker, mock_db):
        """Test identifying declining patterns."""
        # Mock getting recently applied patterns
        mock_db.fetch_all.side_effect = [
            # First call: get distinct pattern IDs
            [{"pattern_id": "pat-123"}, {"pattern_id": "pat-456"}],
            # Second call: get applications for pat-123 (declining)
            [
                {
                    "id": str(i),
                    "pattern_id": "pat-123",
                    "task_id": f"t{i}",
                    "task_type": "code_review",
                    "agent_code": "Forge",
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                    "was_routing_pattern": 0,
                    "was_confidence_pattern": 0,
                    "outcome_recorded": 1,
                    "outcome_success": 1 if i < 3 else 0,  # 30% success
                    "outcome_duration_ms": 100,
                    "outcome_effectiveness": 0.3,
                    "baseline_agent": "Keystone",
                    "baseline_success_rate": 0.7,
                }  # 70% baseline
                for i in range(10)
            ],
            # Third call: get applications for pat-456 (improving)
            [
                {
                    "id": str(i),
                    "pattern_id": "pat-456",
                    "task_id": f"t{i}",
                    "task_type": "code_review",
                    "agent_code": "Sentinel",
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                    "was_routing_pattern": 0,
                    "was_confidence_pattern": 0,
                    "outcome_recorded": 1,
                    "outcome_success": 1 if i < 9 else 0,  # 90% success
                    "outcome_duration_ms": 100,
                    "outcome_effectiveness": 0.9,
                    "baseline_agent": "Keystone",
                    "baseline_success_rate": 0.7,
                }  # 70% baseline
                for i in range(10)
            ],
        ]

        declining = await tracker.get_declining_patterns(window_hours=24)

        # Only pat-123 should be declining (30% vs 70% baseline = -40%)
        assert len(declining) == 1
        assert declining[0].pattern_id == "pat-123"
        assert declining[0].is_declining is True

    @pytest.mark.asyncio
    async def test_cleanup_old_records(self, tracker, mock_db):
        """Test cleanup of old records."""
        mock_result = MagicMock()
        mock_result.rowcount = 50
        mock_db.execute.return_value = mock_result

        deleted = await tracker.cleanup_old_records()

        # Should have called delete
        mock_db.execute.assert_called_once()
        assert deleted == 50


class TestPatternTrackerIntegration:
    """Integration-style tests for PatternTracker."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_one = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, mock_db):
        """Test the full pattern application lifecycle."""
        tracker = PatternTracker(mock_db)

        # 1. Record application
        app_id = await tracker.record_application(
            pattern_id="pat-123",
            task_id="task-456",
            task_type="code_review",
            agent_code="Forge",
            was_routing_pattern=True,
            baseline_agent="Keystone",
            baseline_success_rate=0.7,
        )

        assert app_id is not None

        # 2. Mock pattern stats for update
        mock_db.fetch_one.return_value = {
            "application_count": 10,
            "success_rate": 0.8,
            "sample_size": 10,
        }

        # 3. Record successful outcome
        await tracker.record_outcome(
            task_id="task-456",
            success=True,
            duration_ms=150.0,
            effectiveness=0.95,
        )

        # 4. Verify database was updated
        assert mock_db.execute.call_count >= 3  # Insert, outcome update, stats update

    @pytest.mark.asyncio
    async def test_baseline_comparison(self, mock_db):
        """Test that baseline comparisons work correctly."""
        tracker = PatternTracker(mock_db)

        # Create applications with known baseline
        applications = []
        for i in range(10):
            applications.append(
                {
                    "id": str(i),
                    "pattern_id": "pat-123",
                    "task_id": f"t{i}",
                    "task_type": "code_review",
                    "agent_code": "Forge",
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                    "was_routing_pattern": 1,
                    "was_confidence_pattern": 0,
                    "outcome_recorded": 1,
                    "outcome_success": 1,  # 100% success with pattern
                    "outcome_duration_ms": 100,
                    "outcome_effectiveness": 1.0,
                    "baseline_agent": "Keystone",
                    "baseline_success_rate": 0.5,  # 50% baseline
                }
            )

        mock_db.fetch_all.return_value = applications

        result = await tracker.get_pattern_effectiveness("pat-123")

        assert result is not None
        assert result.success_rate == 1.0
        assert result.baseline_success_rate == 0.5
        assert result.improvement_over_baseline == 0.5  # 100% - 50% = 50% improvement
        assert result.is_improving is True
        assert result.is_declining is False
