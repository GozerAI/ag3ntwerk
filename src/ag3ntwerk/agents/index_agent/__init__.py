"""
Index (Index) Agent - Index.

Codename: Index
Core function: Govern data assets, ensure quality, and manage knowledge.

The Index handles all data governance, quality, and knowledge management:
- Data governance and stewardship
- Data quality monitoring and enforcement
- Schema management and validation
- Data lineage tracking
- Knowledge management (merged from CKO)
- Analytics coordination
"""

from ag3ntwerk.agents.index_agent.agent import Index
from ag3ntwerk.agents.index_agent.managers import (
    DataGovernanceManager,
    AnalyticsManager,
    KnowledgeManager,
)
from ag3ntwerk.agents.index_agent.specialists import (
    DataSteward,
    SchemaAnalyst,
    QualityAnalyst,
    KnowledgeCurator,
)

# Codename alias
Index = Index

__all__ = [
    # Agent
    "Index",
    "Index",
    # Managers
    "DataGovernanceManager",
    "AnalyticsManager",
    "KnowledgeManager",
    # Specialists
    "DataSteward",
    "SchemaAnalyst",
    "QualityAnalyst",
    "KnowledgeCurator",
]
