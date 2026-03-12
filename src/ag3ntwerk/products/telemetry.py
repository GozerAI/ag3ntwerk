"""
Product Telemetry and Metrics.

Provides telemetry collection and metrics tracking for products
managed by ag3ntwerk agents. Used by Vector (Vector) for revenue
tracking and Beacon (Beacon) for customer metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class MetricType(Enum):
    """Types of product metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class TimeGranularity(Enum):
    """Time granularity for metrics aggregation."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class MetricPoint:
    """A single metric data point."""

    timestamp: datetime = field(default_factory=_utcnow)
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ProductMetric:
    """
    Represents a product metric.

    Metrics track various aspects of product performance,
    usage, and business outcomes.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    product_id: str = ""
    name: str = ""
    description: str = ""
    metric_type: MetricType = MetricType.GAUGE
    unit: str = ""  # e.g., "requests", "users", "dollars"
    current_value: float = 0.0
    previous_value: float = 0.0
    target_value: Optional[float] = None
    data_points: List[MetricPoint] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def change_percent(self) -> Optional[float]:
        """Calculate percentage change from previous value."""
        if self.previous_value == 0:
            return None
        return ((self.current_value - self.previous_value) / self.previous_value) * 100

    @property
    def on_target(self) -> Optional[bool]:
        """Check if metric meets target."""
        if self.target_value is None:
            return None
        return self.current_value >= self.target_value


@dataclass
class UsageMetrics:
    """
    Product usage metrics.

    Tracked by Vector (Vector) for adoption analysis.
    """

    product_id: str = ""
    period_start: datetime = field(default_factory=_utcnow)
    period_end: Optional[datetime] = None
    granularity: TimeGranularity = TimeGranularity.DAILY

    # User metrics
    daily_active_users: int = 0
    weekly_active_users: int = 0
    monthly_active_users: int = 0
    new_users: int = 0
    churned_users: int = 0
    returning_users: int = 0

    # Engagement metrics
    sessions: int = 0
    avg_session_duration_seconds: float = 0.0
    pages_per_session: float = 0.0
    bounce_rate: float = 0.0

    # Feature usage
    feature_usage: Dict[str, int] = field(default_factory=dict)
    api_calls: int = 0
    errors: int = 0
    error_rate: float = 0.0

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RevenueMetrics:
    """
    Product revenue metrics.

    Tracked by Vector (Vector) and Keystone (Keystone).
    """

    product_id: str = ""
    period_start: datetime = field(default_factory=_utcnow)
    period_end: Optional[datetime] = None
    granularity: TimeGranularity = TimeGranularity.MONTHLY
    currency: str = "USD"

    # Revenue
    gross_revenue: float = 0.0
    net_revenue: float = 0.0
    recurring_revenue: float = 0.0  # MRR/ARR
    one_time_revenue: float = 0.0

    # Growth
    revenue_growth_percent: float = 0.0
    mrr_growth_percent: float = 0.0

    # Customer revenue
    arpu: float = 0.0  # Average Revenue Per User
    arppu: float = 0.0  # Average Revenue Per Paying User
    ltv: float = 0.0  # Lifetime Value

    # Churn
    churn_rate: float = 0.0
    revenue_churn: float = 0.0
    net_revenue_retention: float = 0.0

    # Conversion
    conversion_rate: float = 0.0
    trial_to_paid_rate: float = 0.0

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CustomerMetrics:
    """
    Customer satisfaction and health metrics.

    Tracked by Beacon (Beacon).
    """

    product_id: str = ""
    period_start: datetime = field(default_factory=_utcnow)
    period_end: Optional[datetime] = None
    granularity: TimeGranularity = TimeGranularity.MONTHLY

    # Satisfaction
    nps_score: Optional[float] = None  # Net Promoter Score (-100 to 100)
    csat_score: Optional[float] = None  # Customer Satisfaction (0-100)
    ces_score: Optional[float] = None  # Customer Effort Score

    # Response rates
    survey_responses: int = 0
    response_rate: float = 0.0

    # Support metrics
    support_tickets: int = 0
    avg_response_time_hours: float = 0.0
    avg_resolution_time_hours: float = 0.0
    first_contact_resolution_rate: float = 0.0
    ticket_escalation_rate: float = 0.0

    # Health scoring
    healthy_customers: int = 0
    at_risk_customers: int = 0
    churned_customers: int = 0

    # Feedback
    feedback_count: int = 0
    feature_requests: int = 0
    bug_reports: int = 0
    positive_feedback: int = 0
    negative_feedback: int = 0

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DevelopmentMetrics:
    """
    Development and engineering metrics.

    Tracked by Foundry (Foundry).
    """

    product_id: str = ""
    period_start: datetime = field(default_factory=_utcnow)
    period_end: Optional[datetime] = None
    granularity: TimeGranularity = TimeGranularity.WEEKLY

    # Velocity
    commits: int = 0
    pull_requests_opened: int = 0
    pull_requests_merged: int = 0
    pull_requests_closed: int = 0
    avg_pr_cycle_time_hours: float = 0.0

    # Quality
    bugs_opened: int = 0
    bugs_closed: int = 0
    bug_fix_rate: float = 0.0
    code_coverage_percent: float = 0.0
    test_pass_rate: float = 0.0

    # Releases
    releases: int = 0
    hotfixes: int = 0
    rollbacks: int = 0
    deployment_frequency: float = 0.0  # Deployments per day
    deployment_success_rate: float = 0.0

    # DORA metrics
    lead_time_hours: float = 0.0  # Commit to production
    mttr_hours: float = 0.0  # Mean time to recovery
    change_failure_rate: float = 0.0

    # Technical debt
    tech_debt_items: int = 0
    tech_debt_resolved: int = 0

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostMetrics:
    """
    Product cost metrics.

    Tracked by Keystone (Keystone).
    """

    product_id: str = ""
    period_start: datetime = field(default_factory=_utcnow)
    period_end: Optional[datetime] = None
    granularity: TimeGranularity = TimeGranularity.MONTHLY
    currency: str = "USD"

    # Infrastructure costs
    compute_cost: float = 0.0
    storage_cost: float = 0.0
    network_cost: float = 0.0
    third_party_services_cost: float = 0.0
    total_infrastructure_cost: float = 0.0

    # Development costs
    personnel_cost: float = 0.0
    tools_and_licenses_cost: float = 0.0
    total_development_cost: float = 0.0

    # Unit economics
    cost_per_user: float = 0.0
    cost_per_transaction: float = 0.0
    gross_margin: float = 0.0
    contribution_margin: float = 0.0

    # Efficiency
    cost_growth_percent: float = 0.0
    infrastructure_efficiency: float = 0.0  # Revenue / Infrastructure cost

    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_cost(self) -> float:
        """Calculate total cost."""
        return self.total_infrastructure_cost + self.total_development_cost


@dataclass
class ProductTelemetry:
    """
    Aggregated product telemetry.

    Combines all metrics for a product.
    """

    product_id: str = ""
    collected_at: datetime = field(default_factory=_utcnow)

    usage: Optional[UsageMetrics] = None
    revenue: Optional[RevenueMetrics] = None
    customer: Optional[CustomerMetrics] = None
    development: Optional[DevelopmentMetrics] = None
    cost: Optional[CostMetrics] = None

    # Custom metrics
    custom_metrics: List[ProductMetric] = field(default_factory=list)

    # Health indicators
    overall_health_score: float = 0.0  # 0-100
    health_trend: str = "stable"  # improving, stable, declining

    metadata: Dict[str, Any] = field(default_factory=dict)


class TelemetryCollector:
    """
    Collects and aggregates product telemetry.

    Used by agents to gather product metrics.
    """

    def __init__(self, product_id: str):
        """
        Initialize telemetry collector.

        Args:
            product_id: Product to collect telemetry for
        """
        self.product_id = product_id
        self._metrics: Dict[str, ProductMetric] = {}

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            labels: Optional labels
        """
        if name not in self._metrics:
            self._metrics[name] = ProductMetric(
                product_id=self.product_id,
                name=name,
                metric_type=metric_type,
                labels=labels or {},
            )

        metric = self._metrics[name]
        metric.previous_value = metric.current_value
        metric.current_value = value
        metric.updated_at = _utcnow()
        metric.data_points.append(
            MetricPoint(
                value=value,
                labels=labels or {},
            )
        )

    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Counter name
            value: Value to increment by
            labels: Optional labels
        """
        if name not in self._metrics:
            self._metrics[name] = ProductMetric(
                product_id=self.product_id,
                name=name,
                metric_type=MetricType.COUNTER,
                labels=labels or {},
            )

        metric = self._metrics[name]
        metric.previous_value = metric.current_value
        metric.current_value += value
        metric.updated_at = _utcnow()

    def get_metric(self, name: str) -> Optional[ProductMetric]:
        """
        Get a metric by name.

        Args:
            name: Metric name

        Returns:
            Metric if found
        """
        return self._metrics.get(name)

    def get_all_metrics(self) -> List[ProductMetric]:
        """
        Get all collected metrics.

        Returns:
            List of all metrics
        """
        return list(self._metrics.values())

    def collect_telemetry(self) -> ProductTelemetry:
        """
        Collect all telemetry into a single object.

        Returns:
            Aggregated product telemetry
        """
        return ProductTelemetry(
            product_id=self.product_id,
            custom_metrics=self.get_all_metrics(),
        )

    def calculate_health_score(
        self,
        usage: Optional[UsageMetrics] = None,
        revenue: Optional[RevenueMetrics] = None,
        customer: Optional[CustomerMetrics] = None,
    ) -> float:
        """
        Calculate overall product health score.

        Args:
            usage: Usage metrics
            revenue: Revenue metrics
            customer: Customer metrics

        Returns:
            Health score 0-100
        """
        scores = []
        weights = []

        # Usage health (weight: 25%)
        if usage:
            usage_score = min(
                100, (usage.daily_active_users / max(1, usage.monthly_active_users)) * 300
            )
            if usage.error_rate < 0.01:
                usage_score = min(100, usage_score + 20)
            scores.append(usage_score)
            weights.append(0.25)

        # Revenue health (weight: 30%)
        if revenue:
            revenue_score = 50
            if revenue.revenue_growth_percent > 0:
                revenue_score = min(100, 50 + revenue.revenue_growth_percent * 2)
            if revenue.net_revenue_retention > 100:
                revenue_score = min(100, revenue_score + 10)
            if revenue.churn_rate < 5:
                revenue_score = min(100, revenue_score + 10)
            scores.append(revenue_score)
            weights.append(0.30)

        # Customer health (weight: 30%)
        if customer:
            customer_score = 50
            if customer.nps_score is not None:
                customer_score = min(100, 50 + customer.nps_score / 2)
            if customer.csat_score is not None:
                customer_score = min(100, (customer_score + customer.csat_score) / 2)
            scores.append(customer_score)
            weights.append(0.30)

        # Custom metrics health (weight: 15%)
        if self._metrics:
            on_target_count = sum(1 for m in self._metrics.values() if m.on_target is True)
            total_with_targets = sum(
                1 for m in self._metrics.values() if m.target_value is not None
            )
            if total_with_targets > 0:
                custom_score = (on_target_count / total_with_targets) * 100
                scores.append(custom_score)
                weights.append(0.15)

        if not scores:
            return 50.0  # Default neutral score

        # Calculate weighted average
        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        return round(weighted_sum / total_weight, 1)


# Standard product metrics
STANDARD_METRICS = {
    "usage": [
        "dau",
        "wau",
        "mau",
        "sessions",
        "api_calls",
        "errors",
    ],
    "revenue": [
        "mrr",
        "arr",
        "arpu",
        "ltv",
        "churn_rate",
    ],
    "customer": [
        "nps",
        "csat",
        "support_tickets",
        "response_time",
    ],
    "development": [
        "commits",
        "prs_merged",
        "deployment_frequency",
        "lead_time",
    ],
    "cost": [
        "infrastructure_cost",
        "personnel_cost",
        "cost_per_user",
    ],
}
