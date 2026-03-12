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
    Overwatch   CoS      Internal Coordinator
    Nexus       COO      Strategic Intelligence (deprecated shim)
    Forge       CTO      Technical Foundation
    Keystone    CFO      Financial Health
    Echo        CMO      Marketing & Growth
    Sentinel    CIO      Information Governance
    Blueprint   CPO      Product Direction
    Axiom       CRO      Research & Insights
    Compass     CSO      Strategic Direction
    Index       CDO      Data Governance & Knowledge
    Foundry     CEngO    Engineering Execution
    Citadel     CSecO    Security Operations
    Beacon      CCO      Customer Relations
    Vector      CRevO    Revenue Operations
    Aegis       CRiO     Risk Management
    Accord      CComO    Compliance
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
# Legacy aliases -- old executive codes map to codenames (backward compat)
# ---------------------------------------------------------------------------

CoS = Overwatch
COO = Nexus  # deprecated shim; prefer Overwatch directly
CTO = Forge
CFO = Keystone
CMO = Echo
CIO = Sentinel
CPO = Blueprint
CRO = Axiom
CSO = Compass
CDO = Index
CEngO = Foundry
CSecO = Citadel
CCO = Beacon
CRevO = Vector
CRiO = Aegis
CComO = Accord

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
    "CoS",
    "COO",
    "CTO",
    "CFO",
    "CMO",
    "CIO",
    "CPO",
    "CRO",
    "CSO",
    "CDO",
    "CEngO",
    "CSecO",
    "CCO",
    "CRevO",
    "CRiO",
    "CComO",
]
