"""
Product Lifecycle Management Module.

Provides models, abstractions, and telemetry for managing products
within the ag3ntwerk framework. Used by agents to build, deploy,
and operate software products like the GozerAI portfolio.

Key Components:
- Product models: Product, Release, Feature, Milestone, Roadmap
- Repository abstraction: Git operations for release management
- Telemetry: Metrics collection for product health tracking
"""

from ag3ntwerk.products.base import (
    # Enums
    EffortSize,
    FeatureStatus,
    Priority,
    ProductStatus,
    ReleaseStatus,
    ReleaseType,
    # Models
    CustomerFeedback,
    Feature,
    Milestone,
    Product,
    Release,
    Roadmap,
    # Constants
    PRODUCT_CAPABILITIES,
    PRODUCT_TASK_TYPES,
)
from ag3ntwerk.products.repository import (
    BranchInfo,
    CommitInfo,
    GitError,
    PullRequest,
    RepositoryManager,
    RepositoryStats,
    TagInfo,
)
from ag3ntwerk.products.telemetry import (
    # Enums
    MetricType,
    TimeGranularity,
    # Models
    CostMetrics,
    CustomerMetrics,
    DevelopmentMetrics,
    MetricPoint,
    ProductMetric,
    ProductTelemetry,
    RevenueMetrics,
    UsageMetrics,
    # Collector
    TelemetryCollector,
    # Constants
    STANDARD_METRICS,
)

__all__ = [
    # Enums
    "ProductStatus",
    "ReleaseStatus",
    "ReleaseType",
    "FeatureStatus",
    "EffortSize",
    "Priority",
    "MetricType",
    "TimeGranularity",
    # Product Models
    "Product",
    "Release",
    "Feature",
    "Milestone",
    "Roadmap",
    "CustomerFeedback",
    # Repository
    "RepositoryManager",
    "CommitInfo",
    "BranchInfo",
    "TagInfo",
    "PullRequest",
    "RepositoryStats",
    "GitError",
    # Telemetry
    "ProductMetric",
    "MetricPoint",
    "UsageMetrics",
    "RevenueMetrics",
    "CustomerMetrics",
    "DevelopmentMetrics",
    "CostMetrics",
    "ProductTelemetry",
    "TelemetryCollector",
    # Constants
    "PRODUCT_TASK_TYPES",
    "PRODUCT_CAPABILITIES",
    "STANDARD_METRICS",
]
