"""
Vector (Vector) Revenue Domain Models.

Data models for revenue operations, growth metrics, and business performance.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class RevenueType(Enum):
    """Revenue types."""

    RECURRING = "recurring"  # MRR/ARR
    ONE_TIME = "one_time"
    USAGE_BASED = "usage_based"
    EXPANSION = "expansion"
    CONTRACTION = "contraction"


class ChurnType(Enum):
    """Churn types."""

    VOLUNTARY = "voluntary"
    INVOLUNTARY = "involuntary"
    LOGO_CHURN = "logo_churn"
    REVENUE_CHURN = "revenue_churn"


class GrowthStage(Enum):
    """Company growth stages."""

    SEED = "seed"
    EARLY = "early"
    GROWTH = "growth"
    SCALE = "scale"
    MATURE = "mature"


class FunnelStage(Enum):
    """Conversion funnel stages."""

    AWARENESS = "awareness"
    INTEREST = "interest"
    CONSIDERATION = "consideration"
    INTENT = "intent"
    EVALUATION = "evaluation"
    PURCHASE = "purchase"


class MetricTrend(Enum):
    """Metric trend direction."""

    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class ExperimentStatus(Enum):
    """Growth experiment status."""

    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"


@dataclass
class Revenue:
    """Represents revenue data."""

    id: str = field(default_factory=lambda: str(uuid4()))
    period: str = ""  # e.g., "2024-01"
    revenue_type: RevenueType = RevenueType.RECURRING
    amount: float = 0.0
    mrr: float = 0.0
    arr: float = 0.0
    new_revenue: float = 0.0
    expansion_revenue: float = 0.0
    contraction_revenue: float = 0.0
    churn_revenue: float = 0.0
    net_new_mrr: float = 0.0
    customer_count: int = 0
    arpu: float = 0.0  # Average Revenue Per User
    recorded_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RevenueforecastForecast:
    """Represents a revenue forecast."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    forecast_period: str = ""
    base_mrr: float = 0.0
    projected_mrr: float = 0.0
    growth_rate: float = 0.0
    assumptions: List[str] = field(default_factory=list)
    scenarios: Dict[str, float] = field(default_factory=dict)  # optimistic, realistic, pessimistic
    confidence_level: str = "medium"
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChurnAnalysis:
    """Represents churn analysis."""

    id: str = field(default_factory=lambda: str(uuid4()))
    period: str = ""
    churn_type: ChurnType = ChurnType.LOGO_CHURN
    churn_rate: float = 0.0
    churned_customers: int = 0
    churned_revenue: float = 0.0
    retention_rate: float = 0.0
    reasons: List[Dict[str, Any]] = field(default_factory=list)
    at_risk_customers: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Cohort:
    """Represents a customer cohort."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    cohort_period: str = ""  # e.g., "2024-01"
    initial_customers: int = 0
    retention_by_period: Dict[str, float] = field(default_factory=dict)  # {period: retention%}
    ltv: float = 0.0
    avg_revenue: float = 0.0
    characteristics: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionFunnel:
    """Represents a conversion funnel."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    period: str = ""
    stages: List[Dict[str, Any]] = field(default_factory=list)  # {stage, count, conversion_rate}
    overall_conversion_rate: float = 0.0
    bottlenecks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureAdoption:
    """Represents feature adoption metrics."""

    id: str = field(default_factory=lambda: str(uuid4()))
    feature_name: str = ""
    period: str = ""
    total_users: int = 0
    active_users: int = 0
    adoption_rate: float = 0.0
    usage_frequency: float = 0.0
    time_to_adopt_days: float = 0.0
    retention_impact: float = 0.0
    segments: Dict[str, float] = field(default_factory=dict)  # {segment: adoption%}
    tracked_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GrowthExperiment:
    """Represents a growth experiment."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    hypothesis: str = ""
    status: ExperimentStatus = ExperimentStatus.DRAFT
    metric_target: str = ""
    control_group: Dict[str, Any] = field(default_factory=dict)
    variant_group: Dict[str, Any] = field(default_factory=dict)
    sample_size: int = 0
    duration_days: int = 0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    results: Dict[str, Any] = field(default_factory=dict)
    statistical_significance: float = 0.0
    conclusion: str = ""
    owner: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GrowthMetric:
    """Represents a growth metric."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    period: str = ""
    value: float = 0.0
    previous_value: float = 0.0
    change_percent: float = 0.0
    trend: MetricTrend = MetricTrend.FLAT
    target: float = 0.0
    variance_to_target: float = 0.0
    segment: str = ""
    recorded_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RevenueMetrics:
    """Revenue department metrics."""

    timestamp: datetime = field(default_factory=_utcnow)
    mrr: float = 0.0
    arr: float = 0.0
    growth_rate: float = 0.0
    net_revenue_retention: float = 0.0
    gross_revenue_retention: float = 0.0
    churn_rate: float = 0.0
    ltv: float = 0.0
    cac: float = 0.0
    ltv_cac_ratio: float = 0.0
    arpu: float = 0.0
    quick_ratio: float = 0.0  # (New + Expansion) / (Churn + Contraction)
    payback_period_months: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# Revenue capabilities
REVENUE_DOMAIN_CAPABILITIES = [
    "revenue_tracking",
    "revenue_forecasting",
    "churn_analysis",
    "retention_analysis",
    "cohort_analysis",
    "conversion_analysis",
    "feature_adoption",
    "growth_experiments",
    "metric_tracking",
    "unit_economics",
]
