"""
Citadel (Citadel) Security Domain Models.

Data models for security operations, threat management, and Sentinel integration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ThreatSeverity(Enum):
    """Threat severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ThreatStatus(Enum):
    """Threat status."""

    DETECTED = "detected"
    ANALYZING = "analyzing"
    CONFIRMED = "confirmed"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class VulnerabilityStatus(Enum):
    """Vulnerability status."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    REMEDIATED = "remediated"
    ACCEPTED = "accepted"
    FALSE_POSITIVE = "false_positive"


class ScanType(Enum):
    """Security scan types."""

    VULNERABILITY = "vulnerability"
    PENETRATION = "penetration"
    CONFIGURATION = "configuration"
    COMPLIANCE = "compliance"
    CODE_ANALYSIS = "code_analysis"
    DEPENDENCY = "dependency"


class ScanStatus(Enum):
    """Scan status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IncidentSeverity(Enum):
    """Security incident severity."""

    P1_CRITICAL = "p1_critical"
    P2_HIGH = "p2_high"
    P3_MEDIUM = "p3_medium"
    P4_LOW = "p4_low"


class IncidentStatus(Enum):
    """Incident status."""

    DETECTED = "detected"
    TRIAGING = "triaging"
    INVESTIGATING = "investigating"
    CONTAINING = "containing"
    ERADICATING = "eradicating"
    RECOVERING = "recovering"
    POST_INCIDENT = "post_incident"
    CLOSED = "closed"


class ComplianceStatus(Enum):
    """Compliance status."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class PolicyType(Enum):
    """Security policy types."""

    ACCESS_CONTROL = "access_control"
    NETWORK = "network"
    DATA_PROTECTION = "data_protection"
    ENCRYPTION = "encryption"
    AUTHENTICATION = "authentication"
    LOGGING = "logging"
    INCIDENT_RESPONSE = "incident_response"


@dataclass
class Threat:
    """Represents a detected threat."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    severity: ThreatSeverity = ThreatSeverity.MEDIUM
    status: ThreatStatus = ThreatStatus.DETECTED
    source: str = ""
    target: str = ""
    attack_vector: str = ""
    indicators: List[str] = field(default_factory=list)
    mitre_tactics: List[str] = field(default_factory=list)
    mitre_techniques: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=_utcnow)
    resolved_at: Optional[datetime] = None
    analyst: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Vulnerability:
    """Represents a security vulnerability."""

    id: str = field(default_factory=lambda: str(uuid4()))
    cve_id: Optional[str] = None
    title: str = ""
    description: str = ""
    severity: ThreatSeverity = ThreatSeverity.MEDIUM
    cvss_score: Optional[float] = None
    cvss_vector: Optional[str] = None
    status: VulnerabilityStatus = VulnerabilityStatus.OPEN
    affected_asset: str = ""
    affected_component: str = ""
    remediation: str = ""
    workaround: Optional[str] = None
    discovered_at: datetime = field(default_factory=_utcnow)
    due_date: Optional[datetime] = None
    remediated_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityScan:
    """Represents a security scan."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    scan_type: ScanType = ScanType.VULNERABILITY
    status: ScanStatus = ScanStatus.PENDING
    target: str = ""
    scope: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    findings_critical: int = 0
    findings_high: int = 0
    findings_medium: int = 0
    findings_low: int = 0
    findings_info: int = 0
    vulnerabilities: List[str] = field(default_factory=list)  # Vulnerability IDs
    configuration: Dict[str, Any] = field(default_factory=dict)
    report_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityIncident:
    """Represents a security incident."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    severity: IncidentSeverity = IncidentSeverity.P3_MEDIUM
    status: IncidentStatus = IncidentStatus.DETECTED
    category: str = ""  # malware, phishing, data_breach, etc.
    affected_systems: List[str] = field(default_factory=list)
    affected_users: List[str] = field(default_factory=list)
    threat_ids: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=_utcnow)
    acknowledged_at: Optional[datetime] = None
    contained_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    incident_commander: Optional[str] = None
    responders: List[str] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    root_cause: Optional[str] = None
    lessons_learned: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityPolicy:
    """Represents a security policy."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    policy_type: PolicyType = PolicyType.ACCESS_CONTROL
    version: str = "1.0"
    enabled: bool = True
    rules: List[Dict[str, Any]] = field(default_factory=list)
    scope: List[str] = field(default_factory=list)  # systems, networks, users
    exceptions: List[str] = field(default_factory=list)
    enforcement_mode: str = "enforce"  # enforce, audit, disabled
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    owner: Optional[str] = None
    compliance_frameworks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceControl:
    """Represents a compliance control."""

    id: str = field(default_factory=lambda: str(uuid4()))
    control_id: str = ""  # e.g., "CIS-1.1", "NIST-AC-1"
    framework: str = ""  # CIS, NIST, SOC2, etc.
    title: str = ""
    description: str = ""
    status: ComplianceStatus = ComplianceStatus.UNKNOWN
    implementation: str = ""
    evidence: List[str] = field(default_factory=list)
    last_assessed: Optional[datetime] = None
    next_assessment: Optional[datetime] = None
    owner: Optional[str] = None
    related_policies: List[str] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessReview:
    """Represents an access review."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    review_type: str = ""  # user, service_account, privilege, etc.
    scope: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed
    started_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    reviewer: Optional[str] = None
    total_items: int = 0
    reviewed_items: int = 0
    approved: int = 0
    revoked: int = 0
    flagged: int = 0
    findings: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SentinelAgentMapping:
    """Maps ag3ntwerk task types to Sentinel agents."""

    task_type: str
    sentinel_agent: str
    priority: int = 1
    fallback_agent: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityMetrics:
    """Security metrics and KPIs."""

    timestamp: datetime = field(default_factory=_utcnow)

    # Vulnerability metrics
    open_vulnerabilities: int = 0
    critical_vulnerabilities: int = 0
    high_vulnerabilities: int = 0
    mttr_vulnerabilities_hours: float = 0.0  # Mean time to remediate

    # Threat metrics
    active_threats: int = 0
    threats_detected_24h: int = 0
    threats_mitigated_24h: int = 0
    mttd_hours: float = 0.0  # Mean time to detect
    mttm_hours: float = 0.0  # Mean time to mitigate

    # Incident metrics
    open_incidents: int = 0
    incidents_24h: int = 0
    mttr_incidents_hours: float = 0.0  # Mean time to resolve

    # Compliance metrics
    compliance_score: float = 0.0  # 0-100
    controls_compliant: int = 0
    controls_non_compliant: int = 0

    # Security posture
    security_score: float = 0.0  # 0-100
    risk_score: float = 0.0  # 0-100

    metadata: Dict[str, Any] = field(default_factory=dict)


# Security capabilities
SECURITY_CAPABILITIES = [
    # Threat Management
    "threat_detection",
    "threat_analysis",
    "threat_hunting",
    "threat_mitigation",
    # Vulnerability Management
    "vulnerability_scanning",
    "vulnerability_assessment",
    "vulnerability_remediation",
    "patch_management",
    # Incident Response
    "incident_detection",
    "incident_triage",
    "incident_response",
    "incident_investigation",
    "forensics",
    # Compliance
    "compliance_assessment",
    "compliance_monitoring",
    "audit_support",
    "policy_management",
    # Access Management
    "access_review",
    "privilege_management",
    "identity_governance",
    # Security Operations
    "security_monitoring",
    "siem_operations",
    "security_automation",
    # AppSec
    "code_review",
    "sast_scanning",
    "dast_scanning",
    "dependency_scanning",
    # Sentinel Integration
    "sentinel_bridge",
    "sentinel_orchestration",
]
