"""
Agent Analytics Dashboard for ag3ntwerk.

Provides analytics and insights on agent agent performance:
- Performance metrics by agent
- Task distribution analysis
- Response time trends
- Success/failure analysis
- Cost tracking
- Comparative analysis

Usage:
    from ag3ntwerk.core.analytics import (
        AnalyticsDashboard,
        ExecutivePerformance,
        get_analytics_dashboard,
    )

    # Get analytics
    dashboard = get_analytics_dashboard()

    # Get agent performance
    performance = dashboard.get_agent_performance("Forge")
    print(f"Success rate: {performance.success_rate}")

    # Get dashboard summary
    summary = dashboard.get_dashboard_summary()
"""

import asyncio
import csv
import io
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Awaitable
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Analytics alert."""

    id: str
    severity: AlertSeverity
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent: Optional[str] = None
    task_type: Optional[str] = None
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "message": self.message,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "timestamp": self.timestamp.isoformat(),
            "agent": self.agent,
            "task_type": self.task_type,
            "acknowledged": self.acknowledged,
        }


@dataclass
class AlertRule:
    """Rule for triggering alerts."""

    name: str
    metric: str  # success_rate, avg_duration_ms, error_count, etc.
    operator: str  # lt, gt, lte, gte, eq
    threshold: float
    severity: AlertSeverity
    cooldown_minutes: int = 15  # Minimum time between alerts
    scope: str = "global"  # global, agent, task_type

    last_triggered: Optional[datetime] = None

    def check(self, value: float) -> bool:
        """Check if value triggers this rule."""
        if self.operator == "lt":
            return value < self.threshold
        elif self.operator == "gt":
            return value > self.threshold
        elif self.operator == "lte":
            return value <= self.threshold
        elif self.operator == "gte":
            return value >= self.threshold
        elif self.operator == "eq":
            return value == self.threshold
        return False

    def can_trigger(self) -> bool:
        """Check if enough time has passed since last trigger."""
        if not self.last_triggered:
            return True
        elapsed = (datetime.now(timezone.utc) - self.last_triggered).total_seconds()
        return elapsed >= self.cooldown_minutes * 60


class TimeRange(Enum):
    """Time range for analytics queries."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    ALL = "all"


@dataclass
class TaskRecord:
    """Record of a task execution for analytics."""

    task_id: str
    task_type: str
    agent: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: float = 0
    success: bool = True
    error: Optional[str] = None
    tokens_used: int = 0
    model: Optional[str] = None
    delegations: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutivePerformance:
    """Performance metrics for an agent."""

    agent: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_duration_ms: float = 0
    total_tokens: int = 0
    delegations_made: int = 0
    delegations_received: int = 0

    # Task type breakdown
    tasks_by_type: Dict[str, int] = field(default_factory=dict)

    # Time series data
    hourly_tasks: Dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 1.0
        return self.successful_tasks / self.total_tasks

    @property
    def avg_duration_ms(self) -> float:
        """Calculate average task duration."""
        if self.total_tasks == 0:
            return 0
        return self.total_duration_ms / self.total_tasks

    @property
    def avg_tokens_per_task(self) -> float:
        """Calculate average tokens per task."""
        if self.total_tasks == 0:
            return 0
        return self.total_tokens / self.total_tasks

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent": self.agent,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "total_tokens": self.total_tokens,
            "avg_tokens_per_task": self.avg_tokens_per_task,
            "delegations_made": self.delegations_made,
            "delegations_received": self.delegations_received,
            "tasks_by_type": self.tasks_by_type,
        }


@dataclass
class TaskTypeAnalytics:
    """Analytics for a specific task type."""

    task_type: str
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration_ms: float = 0
    durations: List[float] = field(default_factory=list)
    agents: Dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 1.0
        return self.success_count / self.total_count

    @property
    def avg_duration_ms(self) -> float:
        if self.total_count == 0:
            return 0
        return self.total_duration_ms / self.total_count

    @property
    def p50_duration_ms(self) -> float:
        if not self.durations:
            return 0
        return statistics.median(self.durations)

    @property
    def p95_duration_ms(self) -> float:
        if len(self.durations) < 2:
            return self.avg_duration_ms
        sorted_durations = sorted(self.durations)
        idx = int(len(sorted_durations) * 0.95)
        return sorted_durations[idx]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "total_count": self.total_count,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "p50_duration_ms": self.p50_duration_ms,
            "p95_duration_ms": self.p95_duration_ms,
            "agents": self.agents,
        }


@dataclass
class DashboardSummary:
    """Overall dashboard summary."""

    # Totals
    total_tasks: int = 0
    total_success: int = 0
    total_failed: int = 0
    total_tokens: int = 0
    total_duration_ms: float = 0

    # Rates
    overall_success_rate: float = 1.0
    avg_duration_ms: float = 0

    # Agents
    active_executives: int = 0
    top_performers: List[Dict[str, Any]] = field(default_factory=list)

    # Task types
    unique_task_types: int = 0
    most_common_tasks: List[Dict[str, Any]] = field(default_factory=list)

    # Time series
    tasks_over_time: List[Dict[str, Any]] = field(default_factory=list)

    # Period
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "totals": {
                "tasks": self.total_tasks,
                "success": self.total_success,
                "failed": self.total_failed,
                "tokens": self.total_tokens,
            },
            "rates": {
                "success_rate": self.overall_success_rate,
                "avg_duration_ms": self.avg_duration_ms,
            },
            "agents": {
                "active": self.active_executives,
                "top_performers": self.top_performers,
            },
            "task_types": {
                "unique": self.unique_task_types,
                "most_common": self.most_common_tasks,
            },
            "time_series": self.tasks_over_time,
            "period": {
                "start": self.period_start.isoformat() if self.period_start else None,
                "end": self.period_end.isoformat() if self.period_end else None,
            },
        }


@dataclass
class CacheEntry:
    """Cache entry with TTL."""

    value: Any
    expires_at: datetime

    def is_valid(self) -> bool:
        return datetime.now(timezone.utc) < self.expires_at


class AnalyticsDashboard:
    """
    Agent analytics dashboard for ag3ntwerk.

    Tracks and analyzes task execution across agents.
    Features:
    - Performance metrics by agent and task type
    - Alert rules with configurable thresholds
    - Caching for expensive computations
    - Export to CSV and JSON formats
    """

    def __init__(
        self,
        max_records: int = 10000,
        cache_ttl_seconds: int = 60,
    ):
        """
        Initialize the analytics dashboard.

        Args:
            max_records: Maximum task records to keep in memory
            cache_ttl_seconds: TTL for cached computations
        """
        self._max_records = max_records
        self._cache_ttl = cache_ttl_seconds
        self._records: List[TaskRecord] = []
        self._agent_stats: Dict[str, ExecutivePerformance] = {}
        self._task_type_stats: Dict[str, TaskTypeAnalytics] = {}

        # Alert management
        self._alert_rules: Dict[str, AlertRule] = {}
        self._alerts: List[Alert] = []
        self._max_alerts = 1000
        self._alert_listeners: List[Callable[[Alert], Awaitable[None]]] = []

        # Caching
        self._cache: Dict[str, CacheEntry] = {}

    def record_task(
        self,
        task_id: str,
        task_type: str,
        agent: str,
        started_at: datetime,
        completed_at: Optional[datetime] = None,
        duration_ms: float = 0,
        success: bool = True,
        error: Optional[str] = None,
        tokens_used: int = 0,
        model: Optional[str] = None,
        delegations: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a task execution for analytics.

        Args:
            task_id: Unique task ID
            task_type: Type of task
            agent: Agent that handled the task
            started_at: When task started
            completed_at: When task completed
            duration_ms: Duration in milliseconds
            success: Whether task succeeded
            error: Error message if failed
            tokens_used: LLM tokens used
            model: Model used
            delegations: Number of delegations
            metadata: Additional metadata
        """
        record = TaskRecord(
            task_id=task_id,
            task_type=task_type,
            agent=agent,
            started_at=started_at,
            completed_at=completed_at or datetime.now(timezone.utc),
            duration_ms=duration_ms,
            success=success,
            error=error,
            tokens_used=tokens_used,
            model=model,
            delegations=delegations,
            metadata=metadata or {},
        )

        # Add to records (with size limit)
        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records :]

        # Update agent stats
        self._update_agent_stats(record)

        # Update task type stats
        self._update_task_type_stats(record)

        # Invalidate cache on new data
        self._invalidate_cache()

        # Check alert rules
        self._check_alerts(record)

        logger.debug(f"Recorded analytics for task: {task_id}")

    def _update_agent_stats(self, record: TaskRecord) -> None:
        """Update agent performance stats."""
        agent = record.agent

        if agent not in self._agent_stats:
            self._agent_stats[agent] = ExecutivePerformance(agent=agent)

        stats = self._agent_stats[agent]
        stats.total_tasks += 1

        if record.success:
            stats.successful_tasks += 1
        else:
            stats.failed_tasks += 1

        stats.total_duration_ms += record.duration_ms
        stats.total_tokens += record.tokens_used
        stats.delegations_made += record.delegations

        # Task type breakdown
        task_type = record.task_type
        stats.tasks_by_type[task_type] = stats.tasks_by_type.get(task_type, 0) + 1

        # Hourly breakdown
        hour_key = record.started_at.strftime("%Y-%m-%d-%H")
        stats.hourly_tasks[hour_key] = stats.hourly_tasks.get(hour_key, 0) + 1

    def _update_task_type_stats(self, record: TaskRecord) -> None:
        """Update task type analytics."""
        task_type = record.task_type

        if task_type not in self._task_type_stats:
            self._task_type_stats[task_type] = TaskTypeAnalytics(task_type=task_type)

        stats = self._task_type_stats[task_type]
        stats.total_count += 1

        if record.success:
            stats.success_count += 1
        else:
            stats.failure_count += 1

        stats.total_duration_ms += record.duration_ms
        stats.durations.append(record.duration_ms)

        # Limit duration list
        if len(stats.durations) > 1000:
            stats.durations = stats.durations[-1000:]

        # Agent breakdown
        agent = record.agent
        stats.agents[agent] = stats.agents.get(agent, 0) + 1

    def get_agent_performance(
        self,
        agent: str,
        time_range: TimeRange = TimeRange.ALL,
    ) -> Optional[ExecutivePerformance]:
        """
        Get performance metrics for an agent.

        Args:
            agent: Agent name
            time_range: Time range to analyze

        Returns:
            ExecutivePerformance or None if not found
        """
        if time_range == TimeRange.ALL:
            return self._agent_stats.get(agent)

        # Calculate for specific time range
        cutoff = self._get_cutoff_time(time_range)
        records = [r for r in self._records if r.agent == agent and r.started_at >= cutoff]

        if not records:
            return None

        perf = ExecutivePerformance(agent=agent)

        for record in records:
            perf.total_tasks += 1
            if record.success:
                perf.successful_tasks += 1
            else:
                perf.failed_tasks += 1
            perf.total_duration_ms += record.duration_ms
            perf.total_tokens += record.tokens_used
            perf.delegations_made += record.delegations

            task_type = record.task_type
            perf.tasks_by_type[task_type] = perf.tasks_by_type.get(task_type, 0) + 1

        return perf

    def get_task_type_analytics(
        self,
        task_type: str,
        time_range: TimeRange = TimeRange.ALL,
    ) -> Optional[TaskTypeAnalytics]:
        """
        Get analytics for a task type.

        Args:
            task_type: Task type to analyze
            time_range: Time range

        Returns:
            TaskTypeAnalytics or None if not found
        """
        if time_range == TimeRange.ALL:
            return self._task_type_stats.get(task_type)

        cutoff = self._get_cutoff_time(time_range)
        records = [r for r in self._records if r.task_type == task_type and r.started_at >= cutoff]

        if not records:
            return None

        analytics = TaskTypeAnalytics(task_type=task_type)

        for record in records:
            analytics.total_count += 1
            if record.success:
                analytics.success_count += 1
            else:
                analytics.failure_count += 1
            analytics.total_duration_ms += record.duration_ms
            analytics.durations.append(record.duration_ms)

            agent = record.agent
            analytics.agents[agent] = analytics.agents.get(agent, 0) + 1

        return analytics

    def get_all_executives_performance(
        self,
        time_range: TimeRange = TimeRange.ALL,
    ) -> List[ExecutivePerformance]:
        """
        Get performance metrics for all agents.

        Args:
            time_range: Time range

        Returns:
            List of ExecutivePerformance
        """
        if time_range == TimeRange.ALL:
            return list(self._agent_stats.values())

        agents = set(r.agent for r in self._records)
        return [
            perf
            for perf in (self.get_agent_performance(e, time_range) for e in agents)
            if perf is not None
        ]

    def get_dashboard_summary(
        self,
        time_range: TimeRange = TimeRange.ALL,
    ) -> DashboardSummary:
        """
        Get overall dashboard summary.

        Args:
            time_range: Time range

        Returns:
            DashboardSummary
        """
        cutoff = self._get_cutoff_time(time_range) if time_range != TimeRange.ALL else None

        records = self._records
        if cutoff:
            records = [r for r in self._records if r.started_at >= cutoff]

        summary = DashboardSummary()

        if not records:
            return summary

        # Calculate totals
        summary.total_tasks = len(records)
        summary.total_success = sum(1 for r in records if r.success)
        summary.total_failed = summary.total_tasks - summary.total_success
        summary.total_tokens = sum(r.tokens_used for r in records)
        summary.total_duration_ms = sum(r.duration_ms for r in records)

        # Calculate rates
        summary.overall_success_rate = summary.total_success / summary.total_tasks
        summary.avg_duration_ms = summary.total_duration_ms / summary.total_tasks

        # Agent analysis
        exec_performance = self.get_all_executives_performance(time_range)
        summary.active_executives = len(exec_performance)

        # Top performers (by success rate, min 5 tasks)
        qualified = [e for e in exec_performance if e.total_tasks >= 5]
        sorted_by_success = sorted(
            qualified,
            key=lambda e: (e.success_rate, -e.avg_duration_ms),
            reverse=True,
        )
        summary.top_performers = [
            {
                "agent": e.agent,
                "success_rate": e.success_rate,
                "total_tasks": e.total_tasks,
            }
            for e in sorted_by_success[:5]
        ]

        # Task type analysis
        task_type_counts: Dict[str, int] = defaultdict(int)
        for record in records:
            task_type_counts[record.task_type] += 1

        summary.unique_task_types = len(task_type_counts)
        sorted_types = sorted(task_type_counts.items(), key=lambda x: x[1], reverse=True)
        summary.most_common_tasks = [{"task_type": t, "count": c} for t, c in sorted_types[:10]]

        # Time series (hourly)
        hourly_counts: Dict[str, int] = defaultdict(int)
        for record in records:
            hour_key = record.started_at.strftime("%Y-%m-%d %H:00")
            hourly_counts[hour_key] += 1

        summary.tasks_over_time = [
            {"time": t, "count": c} for t, c in sorted(hourly_counts.items())[-24:]
        ]

        # Period
        if records:
            summary.period_start = min(r.started_at for r in records)
            summary.period_end = max(r.completed_at for r in records if r.completed_at)

        return summary

    def get_comparison(
        self,
        agents: List[str],
        time_range: TimeRange = TimeRange.ALL,
    ) -> Dict[str, Any]:
        """
        Compare multiple agents.

        Args:
            agents: List of agent names
            time_range: Time range

        Returns:
            Comparison data
        """
        performances = [self.get_agent_performance(e, time_range) for e in agents]

        comparison = {
            "agents": agents,
            "metrics": {},
        }

        # Compare metrics
        for metric in ["success_rate", "avg_duration_ms", "total_tasks", "avg_tokens_per_task"]:
            values = []
            for i, perf in enumerate(performances):
                if perf:
                    values.append(
                        {
                            "agent": agents[i],
                            "value": getattr(perf, metric),
                        }
                    )

            comparison["metrics"][metric] = values

        return comparison

    def get_trends(
        self,
        agent: Optional[str] = None,
        task_type: Optional[str] = None,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        Get trends over time.

        Args:
            agent: Filter by agent
            task_type: Filter by task type
            days: Number of days to analyze

        Returns:
            Trend data
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        records = self._records
        if agent:
            records = [r for r in records if r.agent == agent]
        if task_type:
            records = [r for r in records if r.task_type == task_type]

        records = [r for r in records if r.started_at >= cutoff]

        # Daily aggregation
        daily_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "success": 0,
                "duration_total": 0,
                "tokens_total": 0,
            }
        )

        for record in records:
            day_key = record.started_at.strftime("%Y-%m-%d")
            daily_data[day_key]["count"] += 1
            if record.success:
                daily_data[day_key]["success"] += 1
            daily_data[day_key]["duration_total"] += record.duration_ms
            daily_data[day_key]["tokens_total"] += record.tokens_used

        # Build trend data
        trends = []
        for day in sorted(daily_data.keys()):
            data = daily_data[day]
            trends.append(
                {
                    "date": day,
                    "count": data["count"],
                    "success_rate": data["success"] / data["count"] if data["count"] > 0 else 0,
                    "avg_duration_ms": (
                        data["duration_total"] / data["count"] if data["count"] > 0 else 0
                    ),
                    "avg_tokens": data["tokens_total"] / data["count"] if data["count"] > 0 else 0,
                }
            )

        return {
            "period_days": days,
            "total_records": len(records),
            "trends": trends,
        }

    def _get_cutoff_time(self, time_range: TimeRange) -> datetime:
        """Get cutoff time for a time range."""
        now = datetime.now(timezone.utc)

        if time_range == TimeRange.HOUR:
            return now - timedelta(hours=1)
        elif time_range == TimeRange.DAY:
            return now - timedelta(days=1)
        elif time_range == TimeRange.WEEK:
            return now - timedelta(weeks=1)
        elif time_range == TimeRange.MONTH:
            return now - timedelta(days=30)
        else:
            return datetime.min.replace(tzinfo=timezone.utc)

    def clear(self) -> None:
        """Clear all analytics data."""
        self._records.clear()
        self._agent_stats.clear()
        self._task_type_stats.clear()
        self._cache.clear()
        logger.info("Analytics data cleared")

    # ==========================================================================
    # Caching
    # ==========================================================================

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache if valid."""
        entry = self._cache.get(key)
        if entry and entry.is_valid():
            return entry.value
        return None

    def _set_cached(self, key: str, value: Any) -> None:
        """Set value in cache."""
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._cache_ttl)
        self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    def _invalidate_cache(self) -> None:
        """Invalidate all cached data."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now(timezone.utc)
        valid_entries = sum(1 for e in self._cache.values() if e.is_valid())
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
        }

    # ==========================================================================
    # Alert Management
    # ==========================================================================

    def add_alert_rule(self, rule: AlertRule) -> None:
        """
        Add an alert rule.

        Args:
            rule: AlertRule to add
        """
        self._alert_rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_alert_rule(self, name: str) -> bool:
        """
        Remove an alert rule.

        Args:
            name: Rule name

        Returns:
            True if removed
        """
        if name in self._alert_rules:
            del self._alert_rules[name]
            logger.info(f"Removed alert rule: {name}")
            return True
        return False

    def get_alert_rules(self) -> List[AlertRule]:
        """Get all alert rules."""
        return list(self._alert_rules.values())

    def add_alert_listener(
        self,
        listener: Callable[[Alert], Awaitable[None]],
    ) -> None:
        """
        Add a listener for alerts.

        Args:
            listener: Async function called when alert triggers
        """
        self._alert_listeners.append(listener)

    def _check_alerts(self, record: TaskRecord) -> None:
        """Check alert rules against new data."""
        agent = record.agent
        task_type = record.task_type

        # Get current metrics
        exec_stats = self._agent_stats.get(agent)
        type_stats = self._task_type_stats.get(task_type)

        for rule in self._alert_rules.values():
            if not rule.can_trigger():
                continue

            value = None
            scope_exec = None
            scope_type = None

            # Get metric value based on scope
            if rule.scope == "global":
                # Use overall stats
                if rule.metric == "success_rate":
                    total = sum(s.total_tasks for s in self._agent_stats.values())
                    success = sum(s.successful_tasks for s in self._agent_stats.values())
                    value = success / total if total > 0 else 1.0
                elif rule.metric == "error_count":
                    value = sum(s.failed_tasks for s in self._agent_stats.values())

            elif rule.scope == "agent" and exec_stats:
                scope_exec = agent
                if rule.metric == "success_rate":
                    value = exec_stats.success_rate
                elif rule.metric == "avg_duration_ms":
                    value = exec_stats.avg_duration_ms
                elif rule.metric == "error_count":
                    value = exec_stats.failed_tasks

            elif rule.scope == "task_type" and type_stats:
                scope_type = task_type
                if rule.metric == "success_rate":
                    value = type_stats.success_rate
                elif rule.metric == "avg_duration_ms":
                    value = type_stats.avg_duration_ms
                elif rule.metric == "error_count":
                    value = type_stats.failure_count

            # Check if rule triggers
            if value is not None and rule.check(value):
                self._trigger_alert(rule, value, scope_exec, scope_type)

    def _trigger_alert(
        self,
        rule: AlertRule,
        current_value: float,
        agent: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> None:
        """Trigger an alert."""
        import uuid

        alert = Alert(
            id=str(uuid.uuid4()),
            severity=rule.severity,
            message=f"Alert: {rule.name} - {rule.metric} {rule.operator} {rule.threshold}",
            metric_name=rule.metric,
            current_value=current_value,
            threshold_value=rule.threshold,
            agent=agent,
            task_type=task_type,
        )

        # Update rule last triggered
        rule.last_triggered = datetime.now(timezone.utc)

        # Store alert
        self._alerts.append(alert)
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts :]

        logger.warning(
            f"Alert triggered: {rule.name} - "
            f"{rule.metric}={current_value} {rule.operator} {rule.threshold}"
        )

        # Notify listeners
        for listener in self._alert_listeners:
            try:
                asyncio.create_task(listener(alert))
            except Exception as e:
                logger.error(f"Alert listener error: {e}")

    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Alert]:
        """
        Get alerts.

        Args:
            severity: Filter by severity
            acknowledged: Filter by acknowledged status
            limit: Maximum alerts to return

        Returns:
            List of alerts
        """
        alerts = self._alerts

        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]

        return alerts[-limit:]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID

        Returns:
            True if acknowledged
        """
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def clear_alerts(self, before: Optional[datetime] = None) -> int:
        """
        Clear alerts.

        Args:
            before: Clear alerts before this time

        Returns:
            Number of alerts cleared
        """
        if before:
            original_count = len(self._alerts)
            self._alerts = [a for a in self._alerts if a.timestamp >= before]
            return original_count - len(self._alerts)
        else:
            count = len(self._alerts)
            self._alerts.clear()
            return count

    # ==========================================================================
    # Export Functionality
    # ==========================================================================

    def export_to_csv(
        self,
        time_range: TimeRange = TimeRange.ALL,
        include_metadata: bool = False,
    ) -> str:
        """
        Export task records to CSV format.

        Args:
            time_range: Time range to export
            include_metadata: Include metadata column

        Returns:
            CSV string
        """
        cutoff = self._get_cutoff_time(time_range) if time_range != TimeRange.ALL else None

        records = self._records
        if cutoff:
            records = [r for r in records if r.started_at >= cutoff]

        output = io.StringIO()
        fieldnames = [
            "task_id",
            "task_type",
            "agent",
            "started_at",
            "completed_at",
            "duration_ms",
            "success",
            "error",
            "tokens_used",
            "model",
            "delegations",
        ]
        if include_metadata:
            fieldnames.append("metadata")

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            row = {
                "task_id": record.task_id,
                "task_type": record.task_type,
                "agent": record.agent,
                "started_at": record.started_at.isoformat(),
                "completed_at": record.completed_at.isoformat() if record.completed_at else "",
                "duration_ms": record.duration_ms,
                "success": record.success,
                "error": record.error or "",
                "tokens_used": record.tokens_used,
                "model": record.model or "",
                "delegations": record.delegations,
            }
            if include_metadata:
                row["metadata"] = json.dumps(record.metadata)

            writer.writerow(row)

        return output.getvalue()

    def export_to_json(
        self,
        time_range: TimeRange = TimeRange.ALL,
        include_summary: bool = True,
        include_records: bool = True,
        include_alerts: bool = False,
    ) -> str:
        """
        Export analytics to JSON format.

        Args:
            time_range: Time range to export
            include_summary: Include dashboard summary
            include_records: Include raw task records
            include_alerts: Include alerts

        Returns:
            JSON string
        """
        cutoff = self._get_cutoff_time(time_range) if time_range != TimeRange.ALL else None

        data: Dict[str, Any] = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "time_range": time_range.value,
        }

        if include_summary:
            summary = self.get_dashboard_summary(time_range)
            data["summary"] = summary.to_dict()

        if include_records:
            records = self._records
            if cutoff:
                records = [r for r in records if r.started_at >= cutoff]

            data["records"] = [
                {
                    "task_id": r.task_id,
                    "task_type": r.task_type,
                    "agent": r.agent,
                    "started_at": r.started_at.isoformat(),
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "duration_ms": r.duration_ms,
                    "success": r.success,
                    "error": r.error,
                    "tokens_used": r.tokens_used,
                    "model": r.model,
                    "delegations": r.delegations,
                    "metadata": r.metadata,
                }
                for r in records
            ]

        if include_alerts:
            data["alerts"] = [a.to_dict() for a in self._alerts]

        return json.dumps(data, indent=2)

    def export_executive_report(self, agent: str) -> Dict[str, Any]:
        """
        Generate a detailed report for an agent.

        Args:
            agent: Agent name

        Returns:
            Report dictionary
        """
        perf = self._agent_stats.get(agent)
        if not perf:
            return {"error": f"No data for agent: {agent}"}

        # Get time-based performance
        perf_hour = self.get_agent_performance(agent, TimeRange.HOUR)
        perf_day = self.get_agent_performance(agent, TimeRange.DAY)
        perf_week = self.get_agent_performance(agent, TimeRange.WEEK)

        # Get trends
        trends = self.get_trends(agent=agent, days=7)

        # Get recent errors
        recent_errors = [
            {
                "task_id": r.task_id,
                "task_type": r.task_type,
                "error": r.error,
                "timestamp": r.started_at.isoformat(),
            }
            for r in self._records[-100:]
            if r.agent == agent and not r.success
        ]

        return {
            "agent": agent,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall": perf.to_dict(),
            "last_hour": perf_hour.to_dict() if perf_hour else None,
            "last_day": perf_day.to_dict() if perf_day else None,
            "last_week": perf_week.to_dict() if perf_week else None,
            "trends": trends,
            "recent_errors": recent_errors[-10:],
        }


# Global analytics dashboard
_dashboard: Optional[AnalyticsDashboard] = None


def get_analytics_dashboard() -> AnalyticsDashboard:
    """Get the global analytics dashboard."""
    global _dashboard
    if _dashboard is None:
        _dashboard = AnalyticsDashboard()
    return _dashboard


def record_task_analytics(
    task_id: str,
    task_type: str,
    agent: str,
    started_at: datetime,
    completed_at: Optional[datetime] = None,
    duration_ms: float = 0,
    success: bool = True,
    error: Optional[str] = None,
    tokens_used: int = 0,
    model: Optional[str] = None,
    delegations: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record a task execution in the global dashboard."""
    dashboard = get_analytics_dashboard()
    dashboard.record_task(
        task_id=task_id,
        task_type=task_type,
        agent=agent,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        success=success,
        error=error,
        tokens_used=tokens_used,
        model=model,
        delegations=delegations,
        metadata=metadata,
    )


__all__ = [
    # Enums
    "TimeRange",
    "AlertSeverity",
    # Data classes
    "TaskRecord",
    "ExecutivePerformance",
    "TaskTypeAnalytics",
    "DashboardSummary",
    "Alert",
    "AlertRule",
    "CacheEntry",
    # Dashboard
    "AnalyticsDashboard",
    "get_analytics_dashboard",
    # Functions
    "record_task_analytics",
]
