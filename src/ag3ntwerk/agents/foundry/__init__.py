"""
Foundry (Foundry) Agent - Foundry.

Codename: Foundry
Core function: Engineering execution, delivery process, and quality assurance.

The Foundry handles all engineering execution tasks:
- Sprint planning and velocity tracking
- Release coordination and delivery
- Quality gates and test automation
- CI/CD pipelines and deployment
- Infrastructure and DevOps operations
- Engineering metrics and productivity
"""

from ag3ntwerk.agents.foundry.agent import Foundry
from ag3ntwerk.agents.foundry.managers import (
    DeliveryManager,
    DevOpsManager,
    QualityManager,
    ReleaseManager,
)
from ag3ntwerk.agents.foundry.specialists import (
    SprintCoordinator,
    ReleaseEngineer,
    QAEngineer,
    QAAutomationEngineer,
    BuildEngineer,
    DeploymentEngineer,
)

# Codename alias
Foundry = Foundry

__all__ = [
    # Agent
    "Foundry",
    "Foundry",
    # Managers
    "DeliveryManager",
    "DevOpsManager",
    "QualityManager",
    "ReleaseManager",
    # Specialists
    "SprintCoordinator",
    "ReleaseEngineer",
    "QAEngineer",
    "QAAutomationEngineer",
    "BuildEngineer",
    "DeploymentEngineer",
]
