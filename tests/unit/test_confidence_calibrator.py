"""
Unit tests for the Confidence Calibrator.

Tests:
- Calibration bucket updates
- Calibration curve calculations
- Getting calibrated confidence
- Recording predictions and outcomes
- Finding poorly calibrated agents
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.learning.confidence_calibrator import (
    ConfidenceCalibrator,
    CalibrationBucket,
    CalibrationCurve,
)


class TestCalibrationBucket:
    """Test CalibrationBucket class."""

    def test_creation(self):
        bucket = CalibrationBucket(bucket_min=0.7, bucket_max=0.8)
        assert bucket.bucket_min == 0.7
        assert bucket.bucket_max == 0.8
        assert bucket.bucket_center == 0.75
        assert bucket.total_predictions == 0

    def test_update_success(self):
        bucket = CalibrationBucket(bucket_min=0.7, bucket_max=0.8)
        bucket.update(was_successful=True)

        assert bucket.total_predictions == 1
        assert bucket.successful_outcomes == 1
        assert bucket.actual_accuracy == 1.0
        assert bucket.calibration_error == -0.25  # 0.75 - 1.0 = -0.25 (under-confident)

    def test_update_failure(self):
        bucket = CalibrationBucket(bucket_min=0.7, bucket_max=0.8)
        bucket.update(was_successful=False)

        assert bucket.total_predictions == 1
        assert bucket.successful_outcomes == 0
        assert bucket.actual_accuracy == 0.0
        assert bucket.calibration_error == 0.75  # 0.75 - 0.0 = 0.75 (over-confident)

    def test_multiple_updates(self):
        bucket = CalibrationBucket(bucket_min=0.7, bucket_max=0.8)

        # 7 successes, 3 failures = 70% accuracy
        for _ in range(7):
            bucket.update(was_successful=True)
        for _ in range(3):
            bucket.update(was_successful=False)

        assert bucket.total_predictions == 10
        assert bucket.actual_accuracy == 0.7
        assert bucket.calibration_error == pytest.approx(0.05, abs=0.01)  # 0.75 - 0.70


class TestCalibrationCurve:
    """Test CalibrationCurve class."""

    def test_creation_initializes_buckets(self):
        curve = CalibrationCurve(agent_code="Forge", task_type="code_review")

        assert curve.agent_code == "Forge"
        assert curve.task_type == "code_review"
        assert len(curve.buckets) == 10

    def test_get_bucket_index(self):
        curve = CalibrationCurve(agent_code="Forge", task_type="code_review")

        assert curve.get_bucket_index(0.0) == 0
        assert curve.get_bucket_index(0.15) == 1
        assert curve.get_bucket_index(0.75) == 7
        assert curve.get_bucket_index(0.99) == 9
        assert curve.get_bucket_index(1.0) == 9  # Edge case

    def test_add_prediction_updates_bucket(self):
        curve = CalibrationCurve(agent_code="Forge", task_type="code_review")

        curve.add_prediction(confidence=0.75, was_successful=True)

        bucket = curve.buckets[7]  # 0.7-0.8 bucket
        assert bucket.total_predictions == 1

    def test_get_calibrated_confidence_insufficient_data(self):
        curve = CalibrationCurve(agent_code="Forge", task_type="code_review")

        # Only 3 predictions - below threshold
        for _ in range(3):
            curve.add_prediction(0.75, True)

        # Should return raw confidence when insufficient data
        result = curve.get_calibrated_confidence(0.75)
        assert result == 0.75

    def test_get_calibrated_confidence_with_data(self):
        curve = CalibrationCurve(agent_code="Forge", task_type="code_review")

        # 10 predictions at 0.75 confidence, but only 50% success
        for i in range(10):
            curve.add_prediction(0.75, was_successful=(i % 2 == 0))

        # Bucket should show 50% accuracy but 75% confidence -> over-confident
        bucket = curve.buckets[7]
        assert bucket.actual_accuracy == 0.5
        assert bucket.calibration_error == pytest.approx(0.25, abs=0.01)

        # Calibrated confidence should be lower than raw
        calibrated = curve.get_calibrated_confidence(0.75)
        assert calibrated < 0.75
        assert calibrated == pytest.approx(0.5, abs=0.05)

    def test_calibration_score(self):
        curve = CalibrationCurve(agent_code="Forge", task_type="code_review")

        # Well-calibrated: 80% confidence -> 80% success
        for i in range(10):
            curve.add_prediction(0.85, was_successful=(i < 8))

        # Should have low calibration score (well calibrated)
        assert curve.calibration_score < 0.1


class TestConfidenceCalibrator:
    """Test ConfidenceCalibrator class."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def calibrator(self, mock_db):
        return ConfidenceCalibrator(mock_db)

    @pytest.mark.asyncio
    async def test_get_calibrated_confidence_no_data(self, calibrator):
        """Returns raw confidence when no calibration data."""
        result = await calibrator.get_calibrated_confidence(
            agent_code="Forge",
            task_type="code_review",
            raw_confidence=0.8,
        )
        assert result == 0.8

    @pytest.mark.asyncio
    async def test_record_prediction_creates_curve(self, calibrator, mock_db):
        """Recording a prediction creates a curve if none exists."""
        await calibrator.record_prediction(
            agent_code="Forge",
            task_type="code_review",
            confidence=0.8,
            was_successful=True,
        )

        key = ("Forge", "code_review")
        assert key in calibrator._curves
        assert calibrator._curves[key].total_predictions == 1

    @pytest.mark.asyncio
    async def test_record_multiple_predictions(self, calibrator, mock_db):
        """Multiple predictions update the same curve."""
        for i in range(10):
            await calibrator.record_prediction(
                agent_code="Forge",
                task_type="code_review",
                confidence=0.8,
                was_successful=(i < 8),
            )

        curve = calibrator._curves[("Forge", "code_review")]
        assert curve.total_predictions == 10

    @pytest.mark.asyncio
    async def test_get_calibration_score_no_data(self, calibrator):
        """Returns 0.5 (unknown) when no calibration data."""
        score = await calibrator.get_calibration_score("Forge", "code_review")
        assert score == 0.5

    @pytest.mark.asyncio
    async def test_get_calibration_score_with_data(self, calibrator, mock_db):
        """Returns actual calibration score with sufficient data."""
        # Add enough predictions
        for i in range(20):
            await calibrator.record_prediction(
                agent_code="Forge",
                task_type="code_review",
                confidence=0.8,
                was_successful=(i < 16),  # 80% accuracy at 80% confidence
            )

        score = await calibrator.get_calibration_score("Forge", "code_review")
        # Should be well-calibrated (low score)
        assert score < 0.1

    @pytest.mark.asyncio
    async def test_get_agent_calibration_summary_no_data(self, calibrator):
        """Returns empty summary when no data."""
        summary = await calibrator.get_agent_calibration_summary("Forge")

        assert summary["agent_code"] == "Forge"
        assert summary["task_types"] == 0
        assert summary["tendency"] == "unknown"

    @pytest.mark.asyncio
    async def test_get_agent_calibration_summary_with_data(self, calibrator, mock_db):
        """Returns proper summary with data."""
        # Over-confident agent: 90% confidence but only 60% success
        for i in range(20):
            await calibrator.record_prediction(
                agent_code="Forge",
                task_type="code_review",
                confidence=0.95,
                was_successful=(i < 12),  # 60% accuracy
            )

        summary = await calibrator.get_agent_calibration_summary("Forge")

        assert summary["task_types"] == 1
        assert summary["total_predictions"] == 20
        assert summary["tendency"] == "over-confident"

    @pytest.mark.asyncio
    async def test_get_poorly_calibrated_agents(self, calibrator, mock_db):
        """Finds poorly calibrated agents."""
        # Create over-confident agent
        for i in range(20):
            await calibrator.record_prediction(
                agent_code="Forge",
                task_type="code_review",
                confidence=0.95,
                was_successful=(i < 8),  # 40% accuracy at 95% confidence
            )

        # Create well-calibrated agent
        for i in range(20):
            await calibrator.record_prediction(
                agent_code="Keystone",
                task_type="budget",
                confidence=0.7,
                was_successful=(i < 14),  # 70% accuracy at 70% confidence
            )

        poorly_calibrated = await calibrator.get_poorly_calibrated_agents(threshold=0.15)

        # Forge should be poorly calibrated, Keystone should be well calibrated
        agent_codes = [a["agent_code"] for a in poorly_calibrated]
        assert "Forge" in agent_codes
        assert "Keystone" not in agent_codes


class TestConfidenceCalibratorPersistence:
    """Test persistence of calibration data."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.mark.asyncio
    async def test_save_curve_on_prediction(self, mock_db):
        """Curves are saved to database on prediction."""
        calibrator = ConfidenceCalibrator(mock_db)

        await calibrator.record_prediction(
            agent_code="Forge",
            task_type="code_review",
            confidence=0.8,
            was_successful=True,
        )

        # Should have called execute to save
        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_load_curves_from_database(self, mock_db):
        """Curves are loaded from database."""
        import json

        # Mock database response
        mock_db.fetch_all.return_value = [
            {
                "agent_code": "Forge",
                "task_type": "code_review",
                "buckets_json": json.dumps(
                    {
                        "7": {
                            "bucket_min": 0.7,
                            "bucket_max": 0.8,
                            "total_predictions": 10,
                            "successful_outcomes": 8,
                            "actual_accuracy": 0.8,
                            "calibration_error": -0.05,
                        }
                    }
                ),
                "total_predictions": 10,
                "mean_calibration_error": -0.05,
                "calibration_score": 0.05,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
        ]

        calibrator = ConfidenceCalibrator(mock_db)
        count = await calibrator.load_curves()

        assert count == 1
        assert ("Forge", "code_review") in calibrator._curves


class TestCalibrationIntegration:
    """Integration-style tests for calibration."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.mark.asyncio
    async def test_calibration_improves_over_time(self, mock_db):
        """Calibration adjusts predictions based on history."""
        calibrator = ConfidenceCalibrator(mock_db)

        # Agent is over-confident: predicts 90% but achieves 60%
        for i in range(20):
            await calibrator.record_prediction(
                agent_code="Forge",
                task_type="code_review",
                confidence=0.95,
                was_successful=(i < 12),  # 60% success
            )

        # Now get calibrated confidence for 90%
        calibrated = await calibrator.get_calibrated_confidence(
            agent_code="Forge",
            task_type="code_review",
            raw_confidence=0.95,
        )

        # Should be adjusted downward significantly
        assert calibrated < 0.8
        # Should be closer to actual accuracy
        assert abs(calibrated - 0.6) < 0.2

    @pytest.mark.asyncio
    async def test_under_confident_correction(self, mock_db):
        """Under-confident predictions are adjusted upward."""
        calibrator = ConfidenceCalibrator(mock_db)

        # Agent is under-confident: predicts 50% but achieves 80%
        for i in range(20):
            await calibrator.record_prediction(
                agent_code="Keystone",
                task_type="budget",
                confidence=0.55,
                was_successful=(i < 16),  # 80% success
            )

        # Now get calibrated confidence for 50%
        calibrated = await calibrator.get_calibrated_confidence(
            agent_code="Keystone",
            task_type="budget",
            raw_confidence=0.55,
        )

        # Should be adjusted upward
        assert calibrated > 0.6
