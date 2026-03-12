"""
ag3ntwerk Agent implementations.

Architecture:
- Overwatch: Internal coordination layer - manages workflows and routing
- Nexus: Deprecated shim (routes to Overwatch internally)
- Forge: Technical execution service
- Sentinel: Security and information governance service
- And 12 additional domain agents (see below)

Each agent has an official codename (primary API) and a legacy code
(backward-compatible alias):

    Codename    Legacy   Domain
    ---------   ------   ------
    Overwatch   Overwatch      Internal Coordinator
    Nexus       Nexus      Strategic Intelligence (deprecated shim)
    Forge       Forge      Technical Foundation
    Keystone    Keystone      Financial Health
    Echo        Echo      Marketing & Growth
    Sentinel    Sentinel      Information Governance
    Blueprint   Blueprint      Product Direction
    Axiom       Axiom      Research & Insights
    Compass     Compass      Strategic Direction
    Index       Index      Data Governance & Knowledge
    Foundry     Foundry    Engineering Execution
    Citadel     Citadel    Security Operations
    Beacon      Beacon      Customer Relations
    Vector      Vector    Revenue Operations
    Aegis       Aegis     Risk Management
    Accord      Accord    Compliance
"""

# ---------------------------------------------------------------------------
# Primary imports -- codenames are the public API
# ---------------------------------------------------------------------------

# Coordination layer
from ag3ntwerk.agents.overwatch import Overwatch

# Nexus (deprecated compatibility shim -> Overwatch)
from ag3ntwerk.agents.nexus import Nexus

# Domain agents
from ag3ntwerk.agents.forge import Forge
from ag3ntwerk.agents.keystone import Keystone
from ag3ntwerk.agents.echo import Echo
from ag3ntwerk.agents.sentinel import Sentinel
from ag3ntwerk.agents.blueprint import Blueprint
from ag3ntwerk.agents.axiom import Axiom
from ag3ntwerk.agents.compass import Compass
from ag3ntwerk.agents.index_agent import Index
from ag3ntwerk.agents.foundry import Foundry
from ag3ntwerk.agents.citadel import Citadel
from ag3ntwerk.agents.beacon import Beacon
from ag3ntwerk.agents.vector import Vector
from ag3ntwerk.agents.aegis import Aegis
from ag3ntwerk.agents.accord import Accord

# ---------------------------------------------------------------------------
# Legacy aliases -- old agent codes map to codenames (backward compat)
# ---------------------------------------------------------------------------

Overwatch = Overwatch
Nexus = Nexus  # deprecated shim; prefer Overwatch directly
Forge = Forge
Keystone = Keystone
Echo = Echo
Sentinel = Sentinel
Blueprint = Blueprint
Axiom = Axiom
Compass = Compass
Index = Index
Foundry = Foundry
Citadel = Citadel
Beacon = Beacon
Vector = Vector
Aegis = Aegis
Accord = Accord

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Codenames (primary)
    "Overwatch",
    "Nexus",
    "Forge",
    "Keystone",
    "Echo",
    "Sentinel",
    "Blueprint",
    "Axiom",
    "Compass",
    "Index",
    "Foundry",
    "Citadel",
    "Beacon",
    "Vector",
    "Aegis",
    "Accord",
    # Legacy codes (backward compat)
    "Overwatch",
    "Nexus",
    "Forge",
    "Keystone",
    "Echo",
    "Sentinel",
    "Blueprint",
    "Axiom",
    "Compass",
    "Index",
    "Foundry",
    "Citadel",
    "Beacon",
    "Vector",
    "Aegis",
    "Accord",
]
