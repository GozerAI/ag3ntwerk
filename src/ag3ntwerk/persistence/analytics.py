"""
Analytics storage and querying for ag3ntwerk.

Provides persistent storage for metrics, dashboards data,
and analytical queries over time-series data.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from .database import DatabaseManager, get_database

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class AggregationType(Enum):
    """Types of metric aggregation."""

    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    LAST = "last"


class TimeGranularity(Enum):
    """Time granularity for aggregations."""

    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class MetricPoint:
    """A single metric data point."""

    metric_name: str
    value: float
    timestamp: datetime = field(default_factory=_utcnow)
    dimensions: Dict[str, str] = field(default_factory=dict)
    source: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "dimensions": self.dimensions,
            "source": self.source,
        }


@dataclass
class AggregatedMetric:
    """Aggregated metric result."""

    metric_name: str
    value: float
    period_start: datetime
    period_end: datetime
    aggregation: AggregationType
    count: int = 0
    dimensions: Dict[str, str] = field(default_factory=dict)


class AnalyticsStore:
    """
    Analytics storage for metrics and time-series data.

    Features:
    - Store metric data points with dimensions
    - Query metrics with filtering and aggregation
    - Time-series aggregation at various granularities
    - Dashboard data support

    Usage:
        store = AnalyticsStore()
        await store.initialize()

        # Record metrics
        await store.record("api_requests", 1, dimensions={"endpoint": "/health"})
        await store.record("response_time_ms", 45.2, dimensions={"agent": "Nexus"})

        # Query metrics
        results = await store.query(
            metric_name="api_requests",
            start_time=datetime.now() - timedelta(hours=1),
            aggregation=AggregationType.SUM,
            granularity=TimeGranularity.MINUTE,
        )
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """Initialize analytics store."""
        self._db = db
        self._initialized = False

    async def _get_db(self) -> DatabaseManager:
        """Get database instance."""
        if self._db is None:
            self._db = await get_database()
        return self._db

    async def initialize(self) -> None:
        """Initialize the analytics store."""
        if self._initialized:
            return
        await self._get_db()
        self._initialized = True

    async def record(
        self,
        metric_name: str,
        value: float,
        dimensions: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
        source: str = "system",
    ) -> None:
        """
        Record a metric data point.

        Args:
            metric_name: Name of the metric
            value: Numeric value
            dimensions: Optional key-value dimensions for filtering
            timestamp: Optional timestamp (defaults to now)
            source: Source identifier
        """
        db = await self._get_db()

        ts = timestamp or _utcnow()
        dims = json.dumps(dimensions or {})

        await db.execute(
            """
            INSERT INTO analytics (metric_name, metric_value, dimensions, timestamp, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (metric_name, value, dims, ts.isoformat(), source),
        )

    async def record_batch(self, metrics: List[MetricPoint]) -> int:
        """
        Record multiple metrics in a batch.

        Args:
            metrics: List of MetricPoint objects

        Returns:
            Number of metrics recorded
        """
        if not metrics:
            return 0

        db = await self._get_db()

        params = [
            (
                m.metric_name,
                m.value,
                json.dumps(m.dimensions),
                m.timestamp.isoformat(),
                m.source,
            )
            for m in metrics
        ]

        return await db.execute_many(
            """
            INSERT INTO analytics (metric_name, metric_value, dimensions, timestamp, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            params,
        )

    async def query(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        dimensions: Optional[Dict[str, str]] = None,
        aggregation: Optional[AggregationType] = None,
        granularity: Optional[TimeGranularity] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Query metrics with optional aggregation.

        Args:
            metric_name: Name of metric to query
            start_time: Start of time range
            end_time: End of time range (defaults to now)
            dimensions: Filter by dimensions
            aggregation: Aggregation type (if None, returns raw points)
            granularity: Time granularity for aggregation
            limit: Maximum results to return

        Returns:
            List of metric data points or aggregated results
        """
        db = await self._get_db()

        # Build query
        conditions = ["metric_name = ?"]
        params: List[Any] = [metric_name]

        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())

        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())

        where_clause = " AND ".join(conditions)

        if aggregation and granularity:
            # Aggregated query
            agg_func = self._get_agg_function(aggregation)
            time_bucket = self._get_time_bucket(granularity)

            query = f"""
                SELECT
                    {time_bucket} as period,
                    {agg_func}(metric_value) as value,
                    COUNT(*) as count
                FROM analytics
                WHERE {where_clause}
                GROUP BY period
                ORDER BY period DESC
                LIMIT ?
            """
            params.append(limit)
        else:
            # Raw query
            query = f"""
                SELECT metric_name, metric_value, dimensions, timestamp, source
                FROM analytics
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params.append(limit)

        results = await db.fetch_all(query, tuple(params))

        # Filter by dimensions if specified
        if dimensions and not aggregation:
            filtered = []
            for row in results:
                row_dims = json.loads(row.get("dimensions", "{}"))
                if all(row_dims.get(k) == v for k, v in dimensions.items()):
                    filtered.append(row)
            results = filtered

        return results

    async def get_latest(
        self,
        metric_name: str,
        dimensions: Optional[Dict[str, str]] = None,
    ) -> Optional[float]:
        """
        Get the most recent value for a metric.

        Args:
            metric_name: Name of metric
            dimensions: Optional dimension filter

        Returns:
            Latest value or None
        """
        results = await self.query(
            metric_name=metric_name,
            dimensions=dimensions,
            limit=1,
        )

        if results:
            return results[0].get("metric_value")
        return None

    async def get_time_series(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        granularity: TimeGranularity = TimeGranularity.HOUR,
        aggregation: AggregationType = AggregationType.AVG,
    ) -> List[Tuple[datetime, float]]:
        """
        Get time-series data for charting.

        Args:
            metric_name: Name of metric
            start_time: Start of time range
            end_time: End of time range
            granularity: Time bucket size
            aggregation: How to aggregate values

        Returns:
            List of (timestamp, value) tuples
        """
        results = await self.query(
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            aggregation=aggregation,
            granularity=granularity,
        )

        time_series = []
        for row in results:
            ts = (
                datetime.fromisoformat(row["period"])
                if isinstance(row["period"], str)
                else row["period"]
            )
            time_series.append((ts, row["value"]))

        return sorted(time_series, key=lambda x: x[0])

    async def get_dashboard_stats(
        self,
        time_window: timedelta = timedelta(hours=24),
    ) -> Dict[str, Any]:
        """
        Get dashboard statistics for display.

        Args:
            time_window: Time window for stats

        Returns:
            Dictionary of dashboard metrics
        """
        db = await self._get_db()
        start_time = _utcnow() - time_window

        # Get various stats
        stats = {}

        # Total request count
        result = await db.fetch_one(
            """
            SELECT COUNT(*) as count, SUM(metric_value) as total
            FROM analytics
            WHERE metric_name = 'api_requests' AND timestamp >= ?
            """,
            (start_time.isoformat(),),
        )
        stats["total_requests"] = result["total"] if result and result["total"] else 0

        # Average response time
        result = await db.fetch_one(
            """
            SELECT AVG(metric_value) as avg_value
            FROM analytics
            WHERE metric_name = 'response_time_ms' AND timestamp >= ?
            """,
            (start_time.isoformat(),),
        )
        stats["avg_response_time_ms"] = (
            round(result["avg_value"], 2) if result and result["avg_value"] else 0
        )

        # Task completion rate
        result = await db.fetch_one(
            """
            SELECT
                SUM(CASE WHEN metric_name = 'task_completed' THEN metric_value ELSE 0 END) as completed,
                SUM(CASE WHEN metric_name = 'task_failed' THEN metric_value ELSE 0 END) as failed
            FROM analytics
            WHERE timestamp >= ?
            """,
            (start_time.isoformat(),),
        )
        completed = result["completed"] or 0 if result else 0
        failed = result["failed"] or 0 if result else 0
        total = completed + failed
        stats["task_success_rate"] = round(completed / total * 100, 2) if total > 0 else 100.0

        # Active agents (metrics recorded by agent)
        result = await db.fetch_all(
            """
            SELECT DISTINCT json_extract(dimensions, '$.agent') as agent
            FROM analytics
            WHERE timestamp >= ? AND json_extract(dimensions, '$.agent') IS NOT NULL
            """,
            (start_time.isoformat(),),
        )
        stats["active_agents"] = len(result)

        return stats

    async def cleanup_old_data(self, retention_days: int = 30) -> int:
        """
        Remove data older than retention period.

        Args:
            retention_days: Days of data to keep

        Returns:
            Number of rows deleted
        """
        db = await self._get_db()
        cutoff = (_utcnow() - timedelta(days=retention_days)).isoformat()

        return await db.execute(
            "DELETE FROM analytics WHERE timestamp < ?",
            (cutoff,),
        )

    def _get_agg_function(self, agg: AggregationType) -> str:
        """Get SQL aggregation function."""
        mapping = {
            AggregationType.SUM: "SUM",
            AggregationType.AVG: "AVG",
            AggregationType.MIN: "MIN",
            AggregationType.MAX: "MAX",
            AggregationType.COUNT: "COUNT",
            AggregationType.LAST: "MAX",  # Approximation for SQLite
        }
        return mapping.get(agg, "AVG")

    def _get_time_bucket(self, granularity: TimeGranularity) -> str:
        """Get SQL time bucket expression (SQLite-compatible)."""
        # SQLite uses strftime for date manipulation
        mapping = {
            TimeGranularity.MINUTE: "strftime('%Y-%m-%d %H:%M:00', timestamp)",
            TimeGranularity.HOUR: "strftime('%Y-%m-%d %H:00:00', timestamp)",
            TimeGranularity.DAY: "strftime('%Y-%m-%d', timestamp)",
            TimeGranularity.WEEK: "strftime('%Y-%W', timestamp)",
            TimeGranularity.MONTH: "strftime('%Y-%m', timestamp)",
        }
        return mapping.get(granularity, mapping[TimeGranularity.HOUR])


# Convenience functions
async def record_metric(
    name: str,
    value: float,
    dimensions: Optional[Dict[str, str]] = None,
) -> None:
    """Record a metric using the default store."""
    store = AnalyticsStore()
    await store.record(name, value, dimensions)


async def get_dashboard_stats() -> Dict[str, Any]:
    """Get dashboard stats using the default store."""
    store = AnalyticsStore()
    return await store.get_dashboard_stats()
