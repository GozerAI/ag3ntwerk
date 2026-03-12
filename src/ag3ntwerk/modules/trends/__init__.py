"""
Trend Intelligence Module.

Provides market trend analysis, niche identification, and opportunity detection
for ag3ntwerk agents. Integrates with external trend sources and provides
autonomous monitoring capabilities.

Primary Owners: Echo (Echo), Blueprint (Visionary)
Secondary Owners: Axiom (Axiom), CEO (Apex)
"""

from ag3ntwerk.modules.trends.core import (
    TrendCategory,
    TrendSource,
    TrendStatus,
    Trend,
    TrendDatabase,
    TrendAnalyzer,
)
from ag3ntwerk.modules.trends.collectors import (
    TrendCollector,
    TrendCollectorManager,
    GoogleTrendsCollector,
    RedditCollector,
    HackerNewsCollector,
    ProductHuntCollector,
    NicheIdentifier,
)
from ag3ntwerk.modules.trends.intelligence import (
    TrendIntelligenceManager,
    TrendCorrelation,
    TrendDriftDetector,
    OpportunityScorer,
)
from ag3ntwerk.modules.trends.service import TrendService

__all__ = [
    # Core
    "TrendCategory",
    "TrendSource",
    "TrendStatus",
    "Trend",
    "TrendDatabase",
    "TrendAnalyzer",
    # Collectors
    "TrendCollector",
    "TrendCollectorManager",
    "GoogleTrendsCollector",
    "RedditCollector",
    "HackerNewsCollector",
    "ProductHuntCollector",
    "NicheIdentifier",
    # Intelligence
    "TrendIntelligenceManager",
    "TrendCorrelation",
    "TrendDriftDetector",
    "OpportunityScorer",
    # Service
    "TrendService",
]
