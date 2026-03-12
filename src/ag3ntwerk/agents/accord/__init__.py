"""
Accord (Accord) Agent - Accord.

Codename: Accord
Core function: Regulatory compliance and policy enforcement.

The Accord handles all compliance-related tasks:
- Regulatory compliance monitoring
- Policy management and enforcement
- Audit coordination
- License and certification tracking
- Ethics and conduct oversight
- Regulatory reporting
"""

from ag3ntwerk.agents.accord.agent import Accord
from ag3ntwerk.agents.accord.managers import (
    ComplianceManager,
    PolicyManager,
    AuditManager,
    EthicsManager,
    LicenseManager,
)
from ag3ntwerk.agents.accord.specialists import (
    ComplianceAnalyst,
    PolicyAnalyst,
    AuditCoordinator,
    EthicsOfficer,
    TrainingCoordinator,
)

# Codename alias
Accord = Accord

__all__ = [
    # Agent
    "Accord",
    "Accord",
    # Managers
    "ComplianceManager",
    "PolicyManager",
    "AuditManager",
    "EthicsManager",
    "LicenseManager",
    # Specialists
    "ComplianceAnalyst",
    "PolicyAnalyst",
    "AuditCoordinator",
    "EthicsOfficer",
    "TrainingCoordinator",
]
