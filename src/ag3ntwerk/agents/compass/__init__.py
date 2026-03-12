"""Compass (Compass) - Compass Strategy Module."""

from ag3ntwerk.agents.compass.agent import Compass

# Codename alias for product narrative
Compass = Compass

# Managers
from ag3ntwerk.agents.compass.managers import (
    StrategicPlanningManager,
    MarketIntelligenceManager,
    ContentStrategyManager,
    GoToMarketManager,
)

# Specialists
from ag3ntwerk.agents.compass.specialists import (
    StrategyAnalyst,
    MarketResearcher,
    ContentStrategist,
    BrandStrategist,
    GTMSpecialist,
)

# Models
from ag3ntwerk.agents.compass.models import (
    # Enums
    StrategicPriority,
    InitiativeStatus,
    MarketPosition,
    CompetitorThreatLevel,
    ContentType,
    ContentStatus,
    ChannelType,
    AnalysisFramework,
    # Dataclasses
    StrategicPlan,
    StrategicInitiative,
    MarketAnalysis,
    Competitor,
    CompetitiveAnalysis,
    SWOTAnalysis,
    ContentStrategy,
    ContentPiece,
    ContentCalendar,
    ValueProposition,
    GoToMarketPlan,
    MessagingFramework,
    StrategyMetrics,
    # Capabilities
    STRATEGY_DOMAIN_CAPABILITIES,
)

__all__ = [
    # Main agent
    "Compass",
    "Compass",
    # Managers
    "StrategicPlanningManager",
    "MarketIntelligenceManager",
    "ContentStrategyManager",
    "GoToMarketManager",
    # Specialists
    "StrategyAnalyst",
    "MarketResearcher",
    "ContentStrategist",
    "BrandStrategist",
    "GTMSpecialist",
    # Enums
    "StrategicPriority",
    "InitiativeStatus",
    "MarketPosition",
    "CompetitorThreatLevel",
    "ContentType",
    "ContentStatus",
    "ChannelType",
    "AnalysisFramework",
    # Dataclasses
    "StrategicPlan",
    "StrategicInitiative",
    "MarketAnalysis",
    "Competitor",
    "CompetitiveAnalysis",
    "SWOTAnalysis",
    "ContentStrategy",
    "ContentPiece",
    "ContentCalendar",
    "ValueProposition",
    "GoToMarketPlan",
    "MessagingFramework",
    "StrategyMetrics",
    # Capabilities
    "STRATEGY_DOMAIN_CAPABILITIES",
]
