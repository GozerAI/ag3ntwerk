"""
Sentinel (Sentinel) Information Governance Domain Models.

Data models for information governance, security alignment, and IT systems.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class InformationClassification(Enum):
    """Information classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


class SystemStatus(Enum):
    """IT system status."""

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    DECOMMISSIONED = "decommissioned"


class DataQualityLevel(Enum):
    """Data quality assessment levels."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


class VerificationStatus(Enum):
    """Truth/verification workflow status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    REJECTED = "rejected"


class AccessLevel(Enum):
    """Access control levels."""

    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SUPERUSER = "superuser"


class IncidentSeverity(Enum):
    """Information security incident severity."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class IncidentStatus(Enum):
    """Incident status."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    CLOSED = "closed"


class GovernanceStatus(Enum):
    """Data governance status."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNDER_REVIEW = "under_review"
    EXEMPT = "exempt"


@dataclass
class InformationAsset:
    """Represents an information asset."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    classification: InformationClassification = InformationClassification.INTERNAL
    owner: str = ""
    custodian: str = ""
    location: str = ""  # System/database where stored
    data_types: List[str] = field(default_factory=list)
    retention_period_days: int = 365
    quality_level: DataQualityLevel = DataQualityLevel.ACCEPTABLE
    created_at: datetime = field(default_factory=_utcnow)
    last_reviewed: Optional[datetime] = None
    review_frequency_days: int = 90
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ITSystem:
    """Represents an IT system or application."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: SystemStatus = SystemStatus.OPERATIONAL
    system_type: str = ""  # application, database, infrastructure, etc.
    owner: str = ""
    vendor: Optional[str] = None
    version: str = ""
    environment: str = "production"
    criticality: str = "medium"  # low, medium, high, critical
    data_classification: InformationClassification = InformationClassification.INTERNAL
    integrations: List[str] = field(default_factory=list)
    uptime_sla: float = 99.9
    last_health_check: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataGovernancePolicy:
    """Represents a data governance policy."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    policy_type: str = ""  # retention, access, quality, privacy, etc.
    scope: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    owner: str = ""
    status: GovernanceStatus = GovernanceStatus.COMPLIANT
    effective_date: Optional[datetime] = None
    review_date: Optional[datetime] = None
    version: str = "1.0"
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessControl:
    """Represents access control configuration."""

    id: str = field(default_factory=lambda: str(uuid4()))
    resource: str = ""
    resource_type: str = ""  # system, data, application
    principal: str = ""  # user, group, service account
    principal_type: str = "user"
    access_level: AccessLevel = AccessLevel.READ
    conditions: Dict[str, Any] = field(default_factory=dict)
    granted_by: str = ""
    granted_at: datetime = field(default_factory=_utcnow)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    justification: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityIncident:
    """Represents a security incident."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    status: IncidentStatus = IncidentStatus.OPEN
    category: str = ""  # data_breach, unauthorized_access, malware, etc.
    affected_systems: List[str] = field(default_factory=list)
    affected_data: List[str] = field(default_factory=list)
    reported_by: str = ""
    assigned_to: Optional[str] = None
    reported_at: datetime = field(default_factory=_utcnow)
    contained_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    root_cause: Optional[str] = None
    remediation_steps: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationWorkflow:
    """Represents a truth/verification workflow."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    claim: str = ""  # The statement/data being verified
    source: str = ""
    status: VerificationStatus = VerificationStatus.PENDING
    verification_method: str = ""
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    verifiers: List[str] = field(default_factory=list)
    confidence_score: Optional[float] = None  # 0-100
    created_at: datetime = field(default_factory=_utcnow)
    verified_at: Optional[datetime] = None
    verdict: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeArticle:
    """Represents a knowledge management article."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    content: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)
    author: str = ""
    status: str = "draft"  # draft, published, archived
    classification: InformationClassification = InformationClassification.INTERNAL
    version: str = "1.0"
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    views: int = 0
    helpful_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataQualityCheck:
    """Represents a data quality check."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    target_asset: str = ""
    check_type: str = ""  # completeness, accuracy, consistency, timeliness
    rule: str = ""
    threshold: float = 0.0
    result: Optional[float] = None
    passed: Optional[bool] = None
    executed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    issues_found: int = 0
    issues_detail: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemIntegration:
    """Represents an integration between systems."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    source_system: str = ""
    target_system: str = ""
    integration_type: str = ""  # api, file, database, messaging
    protocol: str = ""
    data_flow: str = "bidirectional"  # unidirectional, bidirectional
    frequency: str = "real-time"  # real-time, batch, on-demand
    data_classification: InformationClassification = InformationClassification.INTERNAL
    status: SystemStatus = SystemStatus.OPERATIONAL
    owner: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    last_sync: Optional[datetime] = None
    error_count_24h: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InformationMetrics:
    """Information governance metrics."""

    timestamp: datetime = field(default_factory=_utcnow)

    # Asset metrics
    total_information_assets: int = 0
    classified_assets: int = 0
    unclassified_assets: int = 0

    # Quality metrics
    data_quality_score: float = 0.0
    quality_checks_passed: int = 0
    quality_checks_failed: int = 0

    # System metrics
    total_systems: int = 0
    systems_operational: int = 0
    systems_degraded: int = 0

    # Security metrics
    open_incidents: int = 0
    incidents_24h: int = 0
    mean_time_to_resolve_hours: float = 0.0

    # Access metrics
    access_reviews_pending: int = 0
    access_reviews_completed: int = 0

    # Knowledge metrics
    knowledge_articles: int = 0
    article_views_30d: int = 0

    metadata: Dict[str, Any] = field(default_factory=dict)


# Information governance capabilities
INFORMATION_GOVERNANCE_CAPABILITIES = [
    # Security
    "security_scan",
    "vulnerability_check",
    "threat_analysis",
    "access_audit",
    "compliance_check",
    "incident_response",
    "security_review",
    "penetration_test",
    "risk_assessment",
    # Data Governance
    "data_classification",
    "data_quality_check",
    "data_lineage",
    "data_catalog",
    "retention_management",
    # Knowledge Management
    "knowledge_creation",
    "knowledge_retrieval",
    "knowledge_curation",
    # IT Systems
    "system_inventory",
    "integration_management",
    "health_monitoring",
    # Verification
    "truth_verification",
    "claim_validation",
    "evidence_collection",
]
