"""
Demand forecasting for the ag3ntwerk learning system.

Predicts task volume and type distribution for proactive scaling
and resource allocation.
"""

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .models import TaskOutcomeRecord
from .outcome_tracker import OutcomeTracker
from .pattern_store import PatternStore


class SeasonalityType(str, Enum):
    """Types of seasonal patterns detected."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    NONE = "none"


class TrendDirection(str, Enum):
    """Direction of detected trends."""

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"


class ScalingAction(str, Enum):
    """Recommended scaling actions."""

    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    MAINTAIN = "maintain"
    PREPARE_BURST = "prepare_burst"


@dataclass
class TimeSeriesPoint:
    """A point in a time series."""

    timestamp: datetime
    value: float
    task_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "task_type": self.task_type,
        }


@dataclass
class SeasonalPattern:
    """Detected seasonal pattern."""

    seasonality_type: SeasonalityType
    period_hours: int
    amplitude: float
    phase_shift: float
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seasonality_type": self.seasonality_type.value,
            "period_hours": self.period_hours,
            "amplitude": self.amplitude,
            "phase_shift": self.phase_shift,
            "confidence": self.confidence,
        }


@dataclass
class TrendInfo:
    """Detected trend information."""

    direction: TrendDirection
    slope: float
    intercept: float
    r_squared: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction.value,
            "slope": self.slope,
            "intercept": self.intercept,
            "r_squared": self.r_squared,
        }


@dataclass
class TaskTypeDistribution:
    """Distribution of task types."""

    task_type: str
    current_share: float
    projected_share: float
    volume_change: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "current_share": self.current_share,
            "projected_share": self.projected_share,
            "volume_change": self.volume_change,
        }


@dataclass
class ConfidenceInterval:
    """Confidence interval for predictions."""

    lower: float
    upper: float
    confidence_level: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lower": self.lower,
            "upper": self.upper,
            "confidence_level": self.confidence_level,
        }


@dataclass
class ScalingRecommendation:
    """Recommendation for scaling."""

    action: ScalingAction
    target_capacity: float
    urgency: float
    reason: str
    affected_agents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "target_capacity": self.target_capacity,
            "urgency": self.urgency,
            "reason": self.reason,
            "affected_agents": self.affected_agents,
        }


@dataclass
class DemandForecast:
    """Complete demand forecast."""

    forecast_id: str
    created_at: datetime
    horizon_hours: int
    expected_volume: float
    expected_distribution: List[TaskTypeDistribution]
    confidence_interval: ConfidenceInterval
    recommended_scaling: ScalingRecommendation
    seasonality: Optional[SeasonalPattern] = None
    trend: Optional[TrendInfo] = None
    hourly_projections: List[TimeSeriesPoint] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forecast_id": self.forecast_id,
            "created_at": self.created_at.isoformat(),
            "horizon_hours": self.horizon_hours,
            "expected_volume": self.expected_volume,
            "expected_distribution": [d.to_dict() for d in self.expected_distribution],
            "confidence_interval": self.confidence_interval.to_dict(),
            "recommended_scaling": self.recommended_scaling.to_dict(),
            "seasonality": self.seasonality.to_dict() if self.seasonality else None,
            "trend": self.trend.to_dict() if self.trend else None,
            "hourly_projections": [p.to_dict() for p in self.hourly_projections],
        }


class DemandForecaster:
    """
    Predicts future task demand for proactive scaling.

    Uses historical outcome data to:
    - Detect seasonal patterns (hourly, daily, weekly)
    - Identify trends (increasing, decreasing, stable)
    - Forecast volume for configurable horizon
    - Recommend scaling actions
    """

    # Minimum data points for reliable forecasting
    MIN_DATA_POINTS = 24

    # Hours of history to analyze
    DEFAULT_HISTORY_HOURS = 168  # 1 week

    # Confidence level for intervals
    DEFAULT_CONFIDENCE = 0.95

    def __init__(
        self,
        db: Any,
        outcome_tracker: OutcomeTracker,
        pattern_store: PatternStore,
    ):
        self._db = db
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store

    async def forecast_demand(
        self,
        horizon_hours: int = 24,
        history_hours: Optional[int] = None,
        agent_filter: Optional[str] = None,
    ) -> DemandForecast:
        """
        Forecast demand for the specified horizon.

        Args:
            horizon_hours: How many hours ahead to forecast
            history_hours: How many hours of history to analyze
            agent_filter: Optional agent code to filter predictions for

        Returns:
            Complete demand forecast with recommendations
        """
        import uuid

        history_hours = history_hours or self.DEFAULT_HISTORY_HOURS

        # Get historical patterns
        historical = await self._get_historical_patterns(history_hours, agent_filter)

        # Detect seasonality
        seasonality = self._detect_seasonality(historical)

        # Detect trends
        trends = self._detect_trends(historical)

        # Project volume
        expected_volume, hourly_projections = self._project_volume(
            historical, trends, seasonality, horizon_hours
        )

        # Project distribution
        expected_distribution = await self._project_distribution(historical, horizon_hours)

        # Calculate confidence interval
        confidence_interval = self._calculate_confidence(historical, expected_volume)

        # Generate scaling recommendation
        recommended_scaling = self._recommend_scaling(expected_volume, historical, agent_filter)

        return DemandForecast(
            forecast_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            horizon_hours=horizon_hours,
            expected_volume=expected_volume,
            expected_distribution=expected_distribution,
            confidence_interval=confidence_interval,
            recommended_scaling=recommended_scaling,
            seasonality=seasonality,
            trend=trends,
            hourly_projections=hourly_projections,
        )

    async def _get_historical_patterns(
        self,
        hours: int,
        agent_filter: Optional[str] = None,
    ) -> List[TimeSeriesPoint]:
        """Get historical task volume data."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Query outcomes grouped by hour
        query = """
            SELECT
                strftime('%Y-%m-%d %H:00:00', created_at) as hour_bucket,
                task_type,
                COUNT(*) as count
            FROM learning_outcomes
            WHERE created_at >= ?
        """
        params: List[Any] = [cutoff.isoformat()]

        if agent_filter:
            query += " AND agent_code = ?"
            params.append(agent_filter)

        query += " GROUP BY hour_bucket, task_type ORDER BY hour_bucket"

        rows = await self._db.fetch_all(query, params)

        # Aggregate into time series
        hourly_totals: Dict[str, float] = {}
        for row in rows:
            hour_bucket = row["hour_bucket"]
            count = row["count"]
            hourly_totals[hour_bucket] = hourly_totals.get(hour_bucket, 0) + count

        # Convert to time series points
        points = []
        for hour_str, total in sorted(hourly_totals.items()):
            try:
                ts = datetime.fromisoformat(hour_str)
                # Make timezone-aware if naive (assume UTC for DB values)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                points.append(TimeSeriesPoint(timestamp=ts, value=total))
            except ValueError:
                continue

        return points

    def _detect_seasonality(
        self,
        historical: List[TimeSeriesPoint],
    ) -> Optional[SeasonalPattern]:
        """Detect seasonal patterns in historical data."""
        if len(historical) < self.MIN_DATA_POINTS:
            return None

        values = [p.value for p in historical]

        # Check for daily seasonality (24 hours)
        daily_pattern = self._check_period_seasonality(values, 24)
        if daily_pattern and daily_pattern.confidence > 0.6:
            return daily_pattern

        # Check for weekly seasonality (168 hours)
        if len(values) >= 168:
            weekly_pattern = self._check_period_seasonality(values, 168)
            if weekly_pattern and weekly_pattern.confidence > 0.6:
                return weekly_pattern

        # Check for hourly patterns (work hours vs off hours)
        hourly_pattern = self._check_period_seasonality(values, 8)
        if hourly_pattern and hourly_pattern.confidence > 0.6:
            return hourly_pattern

        return None

    def _check_period_seasonality(
        self,
        values: List[float],
        period: int,
    ) -> Optional[SeasonalPattern]:
        """Check for seasonality with a specific period."""
        if len(values) < period * 2:
            return None

        # Calculate autocorrelation at the given period
        n = len(values)
        mean = statistics.mean(values)
        variance = statistics.variance(values) if len(values) > 1 else 1.0

        if variance == 0:
            return None

        # Autocorrelation at lag = period
        autocorr = 0.0
        for i in range(n - period):
            autocorr += (values[i] - mean) * (values[i + period] - mean)
        autocorr /= (n - period) * variance

        # Estimate amplitude
        period_values = [[] for _ in range(period)]
        for i, v in enumerate(values):
            period_values[i % period].append(v)

        period_means = [statistics.mean(pv) if pv else mean for pv in period_values]
        amplitude = max(period_means) - min(period_means)

        # Find phase shift (hour of peak)
        peak_idx = period_means.index(max(period_means))
        phase_shift = peak_idx / period

        # Determine seasonality type
        if period == 24:
            seasonality_type = SeasonalityType.DAILY
        elif period == 168:
            seasonality_type = SeasonalityType.WEEKLY
        elif period <= 12:
            seasonality_type = SeasonalityType.HOURLY
        else:
            seasonality_type = SeasonalityType.NONE

        # Confidence based on autocorrelation strength
        confidence = max(0.0, min(1.0, autocorr))

        return SeasonalPattern(
            seasonality_type=seasonality_type,
            period_hours=period,
            amplitude=amplitude,
            phase_shift=phase_shift,
            confidence=confidence,
        )

    def _detect_trends(
        self,
        historical: List[TimeSeriesPoint],
    ) -> Optional[TrendInfo]:
        """Detect trends using linear regression."""
        if len(historical) < self.MIN_DATA_POINTS:
            return None

        # Simple linear regression
        n = len(historical)
        x = list(range(n))
        y = [p.value for p in historical]

        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)

        # Calculate slope and intercept
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return TrendInfo(
                direction=TrendDirection.STABLE,
                slope=0.0,
                intercept=y_mean,
                r_squared=0.0,
            )

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # Calculate R-squared
        y_pred = [slope * x[i] + intercept for i in range(n)]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Determine direction
        if abs(slope) < 0.01 * y_mean:
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING

        return TrendInfo(
            direction=direction,
            slope=slope,
            intercept=intercept,
            r_squared=max(0.0, min(1.0, r_squared)),
        )

    def _project_volume(
        self,
        historical: List[TimeSeriesPoint],
        trend: Optional[TrendInfo],
        seasonality: Optional[SeasonalPattern],
        horizon_hours: int,
    ) -> Tuple[float, List[TimeSeriesPoint]]:
        """Project volume for the forecast horizon."""
        if not historical:
            return 0.0, []

        # Base projection from recent average
        recent_values = [p.value for p in historical[-24:]]
        base_hourly = statistics.mean(recent_values) if recent_values else 0.0

        # Generate hourly projections
        projections = []
        now = datetime.now(timezone.utc)
        total_projected = 0.0

        for hour in range(horizon_hours):
            projected_time = now + timedelta(hours=hour)
            projected_value = base_hourly

            # Apply trend adjustment
            if trend and trend.direction != TrendDirection.STABLE:
                # Project trend forward
                hours_from_start = len(historical) + hour
                trend_adjustment = trend.slope * hour
                projected_value += trend_adjustment

            # Apply seasonal adjustment
            if seasonality:
                period = seasonality.period_hours
                phase = (hour % period) / period
                seasonal_factor = 1.0 + seasonality.amplitude * 0.1 * (1.0 if phase < 0.5 else -1.0)
                projected_value *= seasonal_factor

            projected_value = max(0.0, projected_value)
            total_projected += projected_value

            projections.append(
                TimeSeriesPoint(
                    timestamp=projected_time,
                    value=projected_value,
                )
            )

        return total_projected, projections

    async def _project_distribution(
        self,
        historical: List[TimeSeriesPoint],
        horizon_hours: int,
    ) -> List[TaskTypeDistribution]:
        """Project task type distribution."""
        # Get recent task type distribution
        cutoff = datetime.now(timezone.utc) - timedelta(hours=168)

        query = """
            SELECT
                task_type,
                COUNT(*) as count
            FROM learning_outcomes
            WHERE created_at >= ?
            GROUP BY task_type
            ORDER BY count DESC
        """

        rows = await self._db.fetch_all(query, [cutoff.isoformat()])

        if not rows:
            return []

        total = sum(row["count"] for row in rows)
        if total == 0:
            return []

        distributions = []
        for row in rows:
            task_type = row["task_type"]
            current_share = row["count"] / total

            # Simple projection - assume stable distribution
            projected_share = current_share
            volume_change = 0.0

            distributions.append(
                TaskTypeDistribution(
                    task_type=task_type,
                    current_share=current_share,
                    projected_share=projected_share,
                    volume_change=volume_change,
                )
            )

        return distributions[:10]  # Top 10 task types

    def _calculate_confidence(
        self,
        historical: List[TimeSeriesPoint],
        expected_volume: float,
    ) -> ConfidenceInterval:
        """Calculate confidence interval for the forecast."""
        if len(historical) < 2:
            return ConfidenceInterval(
                lower=0.0,
                upper=expected_volume * 2,
                confidence_level=0.5,
            )

        values = [p.value for p in historical]
        std_dev = statistics.stdev(values)

        # 95% confidence interval (1.96 standard deviations)
        margin = 1.96 * std_dev * (len(values) ** 0.5)

        return ConfidenceInterval(
            lower=max(0.0, expected_volume - margin),
            upper=expected_volume + margin,
            confidence_level=self.DEFAULT_CONFIDENCE,
        )

    def _recommend_scaling(
        self,
        expected_volume: float,
        historical: List[TimeSeriesPoint],
        agent_filter: Optional[str],
    ) -> ScalingRecommendation:
        """Generate scaling recommendation based on forecast."""
        if not historical:
            return ScalingRecommendation(
                action=ScalingAction.MAINTAIN,
                target_capacity=1.0,
                urgency=0.0,
                reason="Insufficient historical data for recommendations",
            )

        recent_values = [p.value for p in historical[-24:]]
        recent_avg = statistics.mean(recent_values) if recent_values else 0.0

        if recent_avg == 0:
            return ScalingRecommendation(
                action=ScalingAction.MAINTAIN,
                target_capacity=1.0,
                urgency=0.0,
                reason="No recent activity detected",
            )

        # Calculate projected hourly average
        projected_hourly = expected_volume / 24 if expected_volume > 0 else 0.0

        # Determine scaling action
        ratio = projected_hourly / recent_avg if recent_avg > 0 else 1.0

        if ratio > 1.5:
            action = ScalingAction.SCALE_UP
            urgency = min(1.0, (ratio - 1.5) / 1.5)
            reason = f"Expected {ratio:.1f}x increase in demand"
        elif ratio > 1.2:
            action = ScalingAction.PREPARE_BURST
            urgency = min(1.0, (ratio - 1.2) / 0.3)
            reason = f"Expected {ratio:.1f}x moderate increase in demand"
        elif ratio < 0.5:
            action = ScalingAction.SCALE_DOWN
            urgency = min(1.0, (0.5 - ratio) / 0.5)
            reason = f"Expected {ratio:.1f}x decrease in demand"
        else:
            action = ScalingAction.MAINTAIN
            urgency = 0.0
            reason = "Demand expected to remain stable"

        affected_agents = [agent_filter] if agent_filter else []

        return ScalingRecommendation(
            action=action,
            target_capacity=ratio,
            urgency=urgency,
            reason=reason,
            affected_agents=affected_agents,
        )

    async def get_demand_anomalies(
        self,
        hours: int = 24,
        threshold: float = 2.0,
    ) -> List[Dict[str, Any]]:
        """
        Detect demand anomalies in recent history.

        Args:
            hours: Hours of history to check
            threshold: Standard deviations for anomaly detection

        Returns:
            List of detected anomalies
        """
        historical = await self._get_historical_patterns(hours * 2)

        if len(historical) < self.MIN_DATA_POINTS:
            return []

        values = [p.value for p in historical]
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0.0

        if std_dev == 0:
            return []

        anomalies = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        for point in historical:
            if point.timestamp < cutoff:
                continue

            z_score = abs(point.value - mean) / std_dev
            if z_score > threshold:
                anomalies.append(
                    {
                        "timestamp": point.timestamp.isoformat(),
                        "value": point.value,
                        "expected": mean,
                        "z_score": z_score,
                        "type": "spike" if point.value > mean else "drop",
                    }
                )

        return anomalies

    async def save_forecast(self, forecast: DemandForecast) -> None:
        """Save forecast to database for historical tracking."""
        await self._db.execute(
            """
            INSERT INTO demand_forecasts (
                id, created_at, horizon_hours, expected_volume,
                distribution_json, confidence_lower, confidence_upper,
                scaling_action, scaling_urgency, seasonality_type,
                trend_direction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                forecast.forecast_id,
                forecast.created_at.isoformat(),
                forecast.horizon_hours,
                forecast.expected_volume,
                json.dumps([d.to_dict() for d in forecast.expected_distribution]),
                forecast.confidence_interval.lower,
                forecast.confidence_interval.upper,
                forecast.recommended_scaling.action.value,
                forecast.recommended_scaling.urgency,
                forecast.seasonality.seasonality_type.value if forecast.seasonality else None,
                forecast.trend.direction.value if forecast.trend else None,
            ],
        )
