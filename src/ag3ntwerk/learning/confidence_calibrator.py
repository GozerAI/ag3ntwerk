"""
Confidence Calibrator - Calibrates agent confidence predictions.

The confidence calibrator maintains calibration curves per (agent, task_type) pair
and adjusts raw confidence predictions to be more accurate based on historical data.

Key concepts:
- Raw confidence: What the agent predicts
- Calibrated confidence: Adjusted based on historical accuracy
- Calibration score: How well-calibrated an agent's predictions are (0 = perfect)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CalibrationBucket:
    """
    A bucket in the calibration curve.

    Represents a range of confidence predictions and tracks actual outcomes.
    """

    bucket_min: float  # e.g., 0.7
    bucket_max: float  # e.g., 0.8
    bucket_center: float = 0.0  # e.g., 0.75

    total_predictions: int = 0
    successful_outcomes: int = 0
    actual_accuracy: float = 0.0

    # Delta between predicted confidence and actual accuracy
    # Positive = over-confident, Negative = under-confident
    calibration_error: float = 0.0

    def __post_init__(self):
        self.bucket_center = (self.bucket_min + self.bucket_max) / 2

    def update(self, was_successful: bool) -> None:
        """Update the bucket with a new outcome."""
        self.total_predictions += 1
        if was_successful:
            self.successful_outcomes += 1
        self.actual_accuracy = self.successful_outcomes / self.total_predictions
        self.calibration_error = self.bucket_center - self.actual_accuracy


@dataclass
class CalibrationCurve:
    """
    Calibration curve for an (agent, task_type) pair.

    Contains buckets for different confidence levels.
    """

    agent_code: str
    task_type: str

    # Buckets by confidence range (0.0-0.1, 0.1-0.2, ..., 0.9-1.0)
    buckets: Dict[int, CalibrationBucket] = field(default_factory=dict)

    # Overall metrics
    total_predictions: int = 0
    mean_calibration_error: float = 0.0
    calibration_score: float = 0.0  # Lower is better (0 = perfectly calibrated)

    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not self.buckets:
            # Initialize 10 buckets for 0.0-0.1, 0.1-0.2, ..., 0.9-1.0
            for i in range(10):
                bucket_min = i / 10
                bucket_max = (i + 1) / 10
                self.buckets[i] = CalibrationBucket(
                    bucket_min=bucket_min,
                    bucket_max=bucket_max,
                )

    def get_bucket_index(self, confidence: float) -> int:
        """Get the bucket index for a confidence value."""
        # Clamp to [0, 1]
        confidence = max(0.0, min(1.0, confidence))
        # Handle edge case at 1.0
        if confidence >= 1.0:
            return 9
        return int(confidence * 10)

    def add_prediction(self, confidence: float, was_successful: bool) -> None:
        """Add a prediction and its outcome to the curve."""
        bucket_idx = self.get_bucket_index(confidence)
        self.buckets[bucket_idx].update(was_successful)
        self.total_predictions += 1
        self.last_updated = datetime.now(timezone.utc)
        self._recalculate_metrics()

    def get_calibrated_confidence(self, raw_confidence: float) -> float:
        """
        Get the calibrated confidence for a raw confidence value.

        This adjusts the prediction based on historical accuracy in this bucket.
        """
        bucket_idx = self.get_bucket_index(raw_confidence)
        bucket = self.buckets[bucket_idx]

        if bucket.total_predictions < 5:
            # Not enough data in this bucket - use raw confidence
            return raw_confidence

        # Adjust based on calibration error
        # If over-confident (error > 0), reduce confidence
        # If under-confident (error < 0), increase confidence
        calibrated = raw_confidence - bucket.calibration_error

        # Clamp to [0, 1]
        return max(0.0, min(1.0, calibrated))

    def _recalculate_metrics(self) -> None:
        """Recalculate overall calibration metrics."""
        total_error = 0.0
        weighted_sum = 0.0
        total_weight = 0

        for bucket in self.buckets.values():
            if bucket.total_predictions > 0:
                # Weight by number of predictions in bucket
                weight = bucket.total_predictions
                total_error += abs(bucket.calibration_error) * weight
                weighted_sum += bucket.calibration_error * weight
                total_weight += weight

        if total_weight > 0:
            self.mean_calibration_error = weighted_sum / total_weight
            self.calibration_score = total_error / total_weight
        else:
            self.mean_calibration_error = 0.0
            self.calibration_score = 0.0


class ConfidenceCalibrator:
    """
    Manages calibration curves for all agents and task types.

    Provides calibrated confidence predictions based on historical accuracy.
    """

    # Minimum predictions before trusting calibration
    MIN_PREDICTIONS_FOR_CALIBRATION = 10

    # Maximum age for calibration data (days)
    MAX_CALIBRATION_AGE_DAYS = 30

    def __init__(self, db: Any):
        """
        Initialize the confidence calibrator.

        Args:
            db: Database connection
        """
        self._db = db

        # In-memory cache of calibration curves
        self._curves: Dict[Tuple[str, str], CalibrationCurve] = {}
        self._cache_loaded = False

    async def load_curves(self) -> int:
        """
        Load calibration curves from the database.

        Returns:
            Number of curves loaded
        """
        try:
            rows = await self._db.fetch_all(
                """
                SELECT * FROM calibration_curves
                WHERE last_updated >= ?
                """,
                (
                    (
                        datetime.now(timezone.utc) - timedelta(days=self.MAX_CALIBRATION_AGE_DAYS)
                    ).isoformat(),
                ),
            )

            self._curves.clear()
            for row in rows:
                curve = self._row_to_curve(row)
                key = (curve.agent_code, curve.task_type)
                self._curves[key] = curve

            self._cache_loaded = True
            logger.info(f"Loaded {len(rows)} calibration curves")
            return len(rows)

        except Exception as e:
            logger.warning(f"Failed to load calibration curves: {e}")
            self._cache_loaded = True  # Mark as loaded to avoid repeated attempts
            return 0

    async def get_calibrated_confidence(
        self,
        agent_code: str,
        task_type: str,
        raw_confidence: float,
    ) -> float:
        """
        Get calibrated confidence for an agent's prediction.

        Args:
            agent_code: Agent making the prediction
            task_type: Type of task
            raw_confidence: Agent's raw confidence prediction (0-1)

        Returns:
            Calibrated confidence (0-1)
        """
        if not self._cache_loaded:
            await self.load_curves()

        key = (agent_code, task_type)
        curve = self._curves.get(key)

        if not curve or curve.total_predictions < self.MIN_PREDICTIONS_FOR_CALIBRATION:
            # Not enough data - return raw confidence
            return raw_confidence

        return curve.get_calibrated_confidence(raw_confidence)

    async def record_prediction(
        self,
        agent_code: str,
        task_type: str,
        confidence: float,
        was_successful: bool,
    ) -> None:
        """
        Record a prediction and its outcome.

        This updates the calibration curve for future predictions.

        Args:
            agent_code: Agent that made the prediction
            task_type: Type of task
            confidence: Confidence prediction (0-1)
            was_successful: Whether the prediction was correct
        """
        if not self._cache_loaded:
            await self.load_curves()

        key = (agent_code, task_type)
        curve = self._curves.get(key)

        if not curve:
            curve = CalibrationCurve(agent_code=agent_code, task_type=task_type)
            self._curves[key] = curve

        curve.add_prediction(confidence, was_successful)

        # Persist to database
        await self._save_curve(curve)

    async def get_calibration_score(
        self,
        agent_code: str,
        task_type: Optional[str] = None,
    ) -> float:
        """
        Get the calibration score for an agent.

        Lower scores indicate better calibration (0 = perfectly calibrated).

        Args:
            agent_code: Agent code
            task_type: Optional task type (if None, returns average across all types)

        Returns:
            Calibration score (0-1, lower is better)
        """
        if not self._cache_loaded:
            await self.load_curves()

        if task_type:
            key = (agent_code, task_type)
            curve = self._curves.get(key)
            if curve and curve.total_predictions >= self.MIN_PREDICTIONS_FOR_CALIBRATION:
                return curve.calibration_score
            return 0.5  # Unknown

        # Average across all task types for this agent
        agent_curves = [
            c
            for (a, _), c in self._curves.items()
            if a == agent_code and c.total_predictions >= self.MIN_PREDICTIONS_FOR_CALIBRATION
        ]

        if not agent_curves:
            return 0.5  # Unknown

        total_score = sum(c.calibration_score * c.total_predictions for c in agent_curves)
        total_predictions = sum(c.total_predictions for c in agent_curves)
        return total_score / total_predictions

    async def get_agent_calibration_summary(
        self,
        agent_code: str,
    ) -> Dict[str, Any]:
        """
        Get a summary of an agent's calibration across all task types.

        Args:
            agent_code: Agent code

        Returns:
            Summary dictionary
        """
        if not self._cache_loaded:
            await self.load_curves()

        agent_curves = [
            (task_type, curve) for (a, task_type), curve in self._curves.items() if a == agent_code
        ]

        if not agent_curves:
            return {
                "agent_code": agent_code,
                "task_types": 0,
                "total_predictions": 0,
                "calibration_score": None,
                "tendency": "unknown",
            }

        total_predictions = sum(c.total_predictions for _, c in agent_curves)
        weighted_score = sum(c.calibration_score * c.total_predictions for _, c in agent_curves)
        weighted_error = sum(
            c.mean_calibration_error * c.total_predictions for _, c in agent_curves
        )

        avg_score = weighted_score / total_predictions if total_predictions > 0 else 0.5
        avg_error = weighted_error / total_predictions if total_predictions > 0 else 0.0

        # Determine tendency
        if avg_error > 0.1:
            tendency = "over-confident"
        elif avg_error < -0.1:
            tendency = "under-confident"
        else:
            tendency = "well-calibrated"

        return {
            "agent_code": agent_code,
            "task_types": len(agent_curves),
            "total_predictions": total_predictions,
            "calibration_score": avg_score,
            "mean_calibration_error": avg_error,
            "tendency": tendency,
            "by_task_type": {
                task_type: {
                    "predictions": curve.total_predictions,
                    "calibration_score": curve.calibration_score,
                    "mean_error": curve.mean_calibration_error,
                }
                for task_type, curve in agent_curves
            },
        }

    async def get_poorly_calibrated_agents(
        self,
        threshold: float = 0.15,
    ) -> List[Dict[str, Any]]:
        """
        Find agents with poor calibration.

        Args:
            threshold: Calibration score threshold (agents above this are poorly calibrated)

        Returns:
            List of agent summaries for poorly calibrated agents
        """
        if not self._cache_loaded:
            await self.load_curves()

        # Group curves by agent
        agent_codes = set(a for (a, _) in self._curves.keys())

        poorly_calibrated = []
        for agent_code in agent_codes:
            summary = await self.get_agent_calibration_summary(agent_code)
            if (
                summary["calibration_score"] is not None
                and summary["calibration_score"] > threshold
                and summary["total_predictions"] >= self.MIN_PREDICTIONS_FOR_CALIBRATION
            ):
                poorly_calibrated.append(summary)

        # Sort by calibration score (worst first)
        poorly_calibrated.sort(
            key=lambda x: x["calibration_score"] or 0,
            reverse=True,
        )

        return poorly_calibrated

    # Private methods

    async def _save_curve(self, curve: CalibrationCurve) -> None:
        """Save a calibration curve to the database."""
        import json

        # Serialize buckets
        buckets_data = {
            str(idx): {
                "bucket_min": b.bucket_min,
                "bucket_max": b.bucket_max,
                "total_predictions": b.total_predictions,
                "successful_outcomes": b.successful_outcomes,
                "actual_accuracy": b.actual_accuracy,
                "calibration_error": b.calibration_error,
            }
            for idx, b in curve.buckets.items()
        }

        try:
            await self._db.execute(
                """
                INSERT OR REPLACE INTO calibration_curves (
                    agent_code, task_type, buckets_json,
                    total_predictions, mean_calibration_error, calibration_score,
                    last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    curve.agent_code,
                    curve.task_type,
                    json.dumps(buckets_data),
                    curve.total_predictions,
                    curve.mean_calibration_error,
                    curve.calibration_score,
                    curve.last_updated.isoformat(),
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to save calibration curve: {e}")

    def _row_to_curve(self, row: Dict[str, Any]) -> CalibrationCurve:
        """Convert a database row to a CalibrationCurve."""
        import json

        curve = CalibrationCurve(
            agent_code=row["agent_code"],
            task_type=row["task_type"],
            total_predictions=row["total_predictions"] or 0,
            mean_calibration_error=row["mean_calibration_error"] or 0.0,
            calibration_score=row["calibration_score"] or 0.0,
            last_updated=datetime.fromisoformat(row["last_updated"]),
        )

        # Deserialize buckets
        if row.get("buckets_json"):
            try:
                buckets_data = json.loads(row["buckets_json"])
                for idx_str, b_data in buckets_data.items():
                    idx = int(idx_str)
                    curve.buckets[idx] = CalibrationBucket(
                        bucket_min=b_data["bucket_min"],
                        bucket_max=b_data["bucket_max"],
                        total_predictions=b_data["total_predictions"],
                        successful_outcomes=b_data["successful_outcomes"],
                        actual_accuracy=b_data["actual_accuracy"],
                        calibration_error=b_data["calibration_error"],
                    )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to deserialize buckets: {e}")

        return curve
