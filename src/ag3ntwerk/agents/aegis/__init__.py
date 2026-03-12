"""
Aegis (Aegis) Agent - Aegis.

Codename: Aegis
Core function: Enterprise risk management and threat mitigation.

The Aegis handles all risk-related tasks:
- Enterprise risk assessment
- Risk quantification and scoring
- Risk mitigation planning
- Threat modeling
- Business continuity planning
- Insurance and hedging strategies
"""

from ag3ntwerk.agents.aegis.agent import Aegis
from ag3ntwerk.agents.aegis.managers import (
    RiskAssessmentManager,
    ThreatModelingManager,
    BCPManager,
    IncidentManager,
)
from ag3ntwerk.agents.aegis.specialists import (
    RiskAnalyst,
    ThreatAnalyst,
    ControlsAnalyst,
    IncidentAnalyst,
)

# Codename alias
Aegis = Aegis

__all__ = [
    # Agent
    "Aegis",
    "Aegis",
    # Managers
    "RiskAssessmentManager",
    "ThreatModelingManager",
    "BCPManager",
    "IncidentManager",
    # Specialists
    "RiskAnalyst",
    "ThreatAnalyst",
    "ControlsAnalyst",
    "IncidentAnalyst",
]
