"""
Blueprint (Blueprint) Agent - Blueprint.

Codename: Blueprint
Core function: Product direction, roadmap, and feature lifecycle.

The Blueprint handles all product management tasks:
- Feature prioritization and lifecycle
- Roadmap planning and updates
- Requirements gathering and specification
- Sprint planning and backlog grooming
- Milestone tracking and release planning
"""

from ag3ntwerk.agents.blueprint.agent import Blueprint
from ag3ntwerk.agents.blueprint.managers import (
    FeatureManager,
    RequirementsManager,
    RoadmapManager,
)
from ag3ntwerk.agents.blueprint.specialists import (
    BacklogGroomer,
    FeaturePrioritizer,
    MarketResearcher,
    RequirementsWriter,
    RoadmapPlanner,
    SprintPlanner,
)
from ag3ntwerk.agents.blueprint.models import (
    # Enums
    FeatureStatus,
    FeaturePriority,
    RequirementType,
    RequirementStatus,
    RoadmapHorizon,
    SprintStatus,
    # Dataclasses
    Feature,
    Requirement,
    Roadmap,
    Sprint,
    BacklogItem,
    Release,
    ProductMetrics,
    # Capabilities
    PRODUCT_DOMAIN_CAPABILITIES,
)

# Codename alias
Blueprint = Blueprint

__all__ = [
    # Agent
    "Blueprint",
    "Blueprint",
    # Managers
    "RoadmapManager",
    "FeatureManager",
    "RequirementsManager",
    # Specialists
    "RoadmapPlanner",
    "FeaturePrioritizer",
    "RequirementsWriter",
    "BacklogGroomer",
    "MarketResearcher",
    "SprintPlanner",
    # Enums
    "FeatureStatus",
    "FeaturePriority",
    "RequirementType",
    "RequirementStatus",
    "RoadmapHorizon",
    "SprintStatus",
    # Dataclasses
    "Feature",
    "Requirement",
    "Roadmap",
    "Sprint",
    "BacklogItem",
    "Release",
    "ProductMetrics",
    # Capabilities
    "PRODUCT_DOMAIN_CAPABILITIES",
]
