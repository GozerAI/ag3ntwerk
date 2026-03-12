"""
Vector (Vector) Agent - Vector.

Codename: Vector
Core function: Revenue operations, growth metrics, and business performance.

The Vector handles all revenue-related tasks:
- Revenue tracking and forecasting
- Growth metrics and KPIs
- Churn and retention analysis
- Feature adoption metrics
- Conversion funnel analysis
"""

from ag3ntwerk.agents.vector.agent import Vector
from ag3ntwerk.agents.vector.managers import (
    GrowthManager,
    MetricsManager,
    RevenueManager,
)
from ag3ntwerk.agents.vector.specialists import (
    AdoptionTracker,
    ChurnAnalyst,
    CohortAnalyst,
    ConversionAnalyst,
    GrowthExperimenter,
    RevenueAnalyst,
)
from ag3ntwerk.agents.vector.models import (
    # Enums
    RevenueType,
    ChurnType,
    GrowthStage,
    FunnelStage,
    MetricTrend,
    ExperimentStatus,
    # Dataclasses
    Revenue,
    RevenueforecastForecast,
    ChurnAnalysis,
    Cohort,
    ConversionFunnel,
    FeatureAdoption,
    GrowthExperiment,
    GrowthMetric,
    RevenueMetrics,
    # Capabilities
    REVENUE_DOMAIN_CAPABILITIES,
)

# Codename alias
Vector = Vector

__all__ = [
    # Agent
    "Vector",
    "Vector",
    # Managers
    "RevenueManager",
    "MetricsManager",
    "GrowthManager",
    # Specialists
    "RevenueAnalyst",
    "ChurnAnalyst",
    "AdoptionTracker",
    "ConversionAnalyst",
    "GrowthExperimenter",
    "CohortAnalyst",
    # Enums
    "RevenueType",
    "ChurnType",
    "GrowthStage",
    "FunnelStage",
    "MetricTrend",
    "ExperimentStatus",
    # Dataclasses
    "Revenue",
    "RevenueforecastForecast",
    "ChurnAnalysis",
    "Cohort",
    "ConversionFunnel",
    "FeatureAdoption",
    "GrowthExperiment",
    "GrowthMetric",
    "RevenueMetrics",
    # Capabilities
    "REVENUE_DOMAIN_CAPABILITIES",
]
