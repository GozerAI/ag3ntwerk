"""Sentinel (Sentinel) - Sentinel Security Module."""

from ag3ntwerk.agents.sentinel.agent import Sentinel

# Codename alias for product narrative
Sentinel = Sentinel

# Managers
from ag3ntwerk.agents.sentinel.managers import (
    DataGovernanceManager,
    ITSystemsManager,
    KnowledgeManager,
    VerificationManager,
)

# Specialists
from ag3ntwerk.agents.sentinel.specialists import (
    DataSteward,
    CloudComplianceAnalyst,
    PrivacyGovernanceOfficer,
    SecurityAnalyst,
    KnowledgeSpecialist,
    SystemsAnalyst,
)

# Models
from ag3ntwerk.agents.sentinel.models import (
    # Enums
    InformationClassification,
    SystemStatus,
    DataQualityLevel,
    VerificationStatus,
    AccessLevel,
    IncidentSeverity,
    IncidentStatus,
    GovernanceStatus,
    # Dataclasses
    InformationAsset,
    ITSystem,
    DataGovernancePolicy,
    AccessControl,
    SecurityIncident,
    VerificationWorkflow,
    KnowledgeArticle,
    DataQualityCheck,
    SystemIntegration,
    InformationMetrics,
    # Capabilities
    INFORMATION_GOVERNANCE_CAPABILITIES,
)

__all__ = [
    # Main agent
    "Sentinel",
    "Sentinel",
    # Managers
    "DataGovernanceManager",
    "ITSystemsManager",
    "KnowledgeManager",
    "VerificationManager",
    # Specialists
    "DataSteward",
    "CloudComplianceAnalyst",
    "PrivacyGovernanceOfficer",
    "SecurityAnalyst",
    "KnowledgeSpecialist",
    "SystemsAnalyst",
    # Enums
    "InformationClassification",
    "SystemStatus",
    "DataQualityLevel",
    "VerificationStatus",
    "AccessLevel",
    "IncidentSeverity",
    "IncidentStatus",
    "GovernanceStatus",
    # Dataclasses
    "InformationAsset",
    "ITSystem",
    "DataGovernancePolicy",
    "AccessControl",
    "SecurityIncident",
    "VerificationWorkflow",
    "KnowledgeArticle",
    "DataQualityCheck",
    "SystemIntegration",
    "InformationMetrics",
    # Capabilities
    "INFORMATION_GOVERNANCE_CAPABILITIES",
]
