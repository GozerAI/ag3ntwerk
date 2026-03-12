"""
Citadel (Citadel) Agent - Citadel.

Codename: Citadel
Core function: Security operations, threat management, and Sentinel platform bridge.

The Citadel bridges ag3ntwerk with the Sentinel security platform:
- Threat detection and response
- Vulnerability management
- Security incident response
- Compliance and governance
- Access reviews and identity governance
- Security automation and orchestration
"""

from ag3ntwerk.agents.citadel.agent import Citadel
from ag3ntwerk.agents.citadel.bridge import SentinelBridge, create_sentinel_bridge
from ag3ntwerk.agents.citadel.managers import (
    ThreatManager,
    VulnerabilityManager,
    ComplianceManager,
    SOCManager,
)
from ag3ntwerk.agents.citadel.specialists import (
    ThreatHunter,
    VulnerabilityAnalyst,
    IncidentResponder,
    ComplianceAnalyst,
    SecurityEngineer,
    AppSecEngineer,
)

# Codename alias
Citadel = Citadel

__all__ = [
    # Agent
    "Citadel",
    "Citadel",
    # Sentinel Integration
    "SentinelBridge",
    "create_sentinel_bridge",
    # Managers
    "ThreatManager",
    "VulnerabilityManager",
    "ComplianceManager",
    "SOCManager",
    # Specialists
    "ThreatHunter",
    "VulnerabilityAnalyst",
    "IncidentResponder",
    "ComplianceAnalyst",
    "SecurityEngineer",
    "AppSecEngineer",
]
