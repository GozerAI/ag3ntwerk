"""
Data models for the Accord (Accord) agent.

This module defines the core data structures for regulatory compliance,
policy management, and audit coordination.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ComplianceStatus(Enum):
    """Compliance status levels."""

    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"
    UNDER_REVIEW = "under_review"
    PENDING = "pending"


class RegulatoryFramework(Enum):
    """Common regulatory frameworks."""

    GDPR = "gdpr"  # EU General Data Protection Regulation
    CCPA = "ccpa"  # California Consumer Privacy Act
    HIPAA = "hipaa"  # Health Insurance Portability
    SOX = "sox"  # Sarbanes-Oxley
    PCI_DSS = "pci_dss"  # Payment Card Industry
    ISO_27001 = "iso_27001"  # Information Security Management
    SOC2 = "soc2"  # Service Organization Control
    NIST = "nist"  # NIST Cybersecurity Framework
    FERPA = "ferpa"  # Family Educational Rights
    GLBA = "glba"  # Gramm-Leach-Bliley Act
    FTC = "ftc"  # FTC Regulations
    SEC = "sec"  # SEC Regulations
    FINRA = "finra"  # Financial Industry Regulatory
    FDA = "fda"  # FDA Regulations
    OSHA = "osha"  # Occupational Safety
    AML = "aml"  # Anti-Money Laundering
    CUSTOM = "custom"  # Custom/Internal


class PolicyStatus(Enum):
    """Policy lifecycle status."""

    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class AuditType(Enum):
    """Types of audits."""

    INTERNAL = "internal"
    EXTERNAL = "external"
    REGULATORY = "regulatory"
    CERTIFICATION = "certification"
    SOC = "soc"
    PENETRATION_TEST = "penetration_test"
    COMPLIANCE_REVIEW = "compliance_review"


class AuditStatus(Enum):
    """Audit lifecycle status."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    FIELDWORK_COMPLETE = "fieldwork_complete"
    DRAFT_REPORT = "draft_report"
    FINAL_REPORT = "final_report"
    REMEDIATION = "remediation"
    CLOSED = "closed"


class FindingSeverity(Enum):
    """Audit finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class FindingStatus(Enum):
    """Audit finding remediation status."""

    OPEN = "open"
    IN_REMEDIATION = "in_remediation"
    PENDING_VALIDATION = "pending_validation"
    CLOSED = "closed"
    ACCEPTED = "accepted"  # Risk accepted


@dataclass
class Regulation:
    """Represents a regulatory requirement."""

    id: str
    name: str
    description: str = ""
    framework: RegulatoryFramework = RegulatoryFramework.CUSTOM
    jurisdiction: str = ""  # Geographic jurisdiction
    effective_date: Optional[datetime] = None
    requirements: List[str] = field(default_factory=list)
    penalties: str = ""  # Description of penalties
    regulatory_body: str = ""
    documentation_url: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "framework": self.framework.value,
            "jurisdiction": self.jurisdiction,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "requirements": self.requirements,
            "penalties": self.penalties,
            "regulatory_body": self.regulatory_body,
            "documentation_url": self.documentation_url,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class ComplianceRequirement:
    """A specific compliance requirement to track."""

    id: str
    name: str
    description: str = ""
    regulation_id: str = ""
    framework: RegulatoryFramework = RegulatoryFramework.CUSTOM
    control_reference: str = ""  # e.g., "GDPR Art. 17"
    status: ComplianceStatus = ComplianceStatus.PENDING
    owner: str = ""
    due_date: Optional[datetime] = None
    evidence_required: List[str] = field(default_factory=list)
    evidence_collected: List[str] = field(default_factory=list)
    controls: List[str] = field(default_factory=list)
    last_assessed: Optional[datetime] = None
    next_review: Optional[datetime] = None
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_overdue(self) -> bool:
        """Check if requirement is overdue."""
        if self.due_date and self.status not in (
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.NOT_APPLICABLE,
        ):
            return _utcnow() > self.due_date
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "regulation_id": self.regulation_id,
            "framework": self.framework.value,
            "control_reference": self.control_reference,
            "status": self.status.value,
            "owner": self.owner,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "is_overdue": self.is_overdue,
            "evidence_required": self.evidence_required,
            "evidence_collected": self.evidence_collected,
            "controls": self.controls,
            "last_assessed": self.last_assessed.isoformat() if self.last_assessed else None,
            "next_review": self.next_review.isoformat() if self.next_review else None,
            "notes": self.notes,
            "metadata": self.metadata,
        }


@dataclass
class Policy:
    """Represents an organizational policy."""

    id: str
    name: str
    description: str = ""
    policy_type: str = "general"  # security, privacy, hr, etc.
    version: str = "1.0"
    status: PolicyStatus = PolicyStatus.DRAFT
    owner: str = ""
    approver: str = ""
    content: str = ""  # Policy content or document reference
    effective_date: Optional[datetime] = None
    review_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    applicable_to: List[str] = field(default_factory=list)  # Departments, roles
    related_regulations: List[str] = field(default_factory=list)
    parent_policy: Optional[str] = None
    child_policies: List[str] = field(default_factory=list)
    acknowledgment_required: bool = False
    training_required: bool = False
    exceptions: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def needs_review(self) -> bool:
        """Check if policy needs review."""
        if self.review_date:
            return _utcnow() >= self.review_date
        return False

    @property
    def is_expired(self) -> bool:
        """Check if policy is expired."""
        if self.expiration_date:
            return _utcnow() > self.expiration_date
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "policy_type": self.policy_type,
            "version": self.version,
            "status": self.status.value,
            "owner": self.owner,
            "approver": self.approver,
            "content": self.content,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "needs_review": self.needs_review,
            "is_expired": self.is_expired,
            "applicable_to": self.applicable_to,
            "related_regulations": self.related_regulations,
            "parent_policy": self.parent_policy,
            "child_policies": self.child_policies,
            "acknowledgment_required": self.acknowledgment_required,
            "training_required": self.training_required,
            "exceptions": self.exceptions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class AuditFinding:
    """An audit finding or observation."""

    id: str
    audit_id: str
    title: str
    description: str = ""
    severity: FindingSeverity = FindingSeverity.MEDIUM
    status: FindingStatus = FindingStatus.OPEN
    category: str = ""
    control_reference: str = ""
    root_cause: str = ""
    recommendation: str = ""
    management_response: str = ""
    owner: str = ""
    due_date: Optional[datetime] = None
    remediation_plan: str = ""
    evidence: List[str] = field(default_factory=list)
    identified_at: datetime = field(default_factory=_utcnow)
    closed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_overdue(self) -> bool:
        """Check if finding remediation is overdue."""
        if self.due_date and self.status in (FindingStatus.OPEN, FindingStatus.IN_REMEDIATION):
            return _utcnow() > self.due_date
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "audit_id": self.audit_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "category": self.category,
            "control_reference": self.control_reference,
            "root_cause": self.root_cause,
            "recommendation": self.recommendation,
            "management_response": self.management_response,
            "owner": self.owner,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "is_overdue": self.is_overdue,
            "remediation_plan": self.remediation_plan,
            "evidence": self.evidence,
            "identified_at": self.identified_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "metadata": self.metadata,
        }


@dataclass
class Audit:
    """Represents an audit engagement."""

    id: str
    name: str
    description: str = ""
    audit_type: AuditType = AuditType.INTERNAL
    status: AuditStatus = AuditStatus.PLANNED
    scope: str = ""
    objectives: List[str] = field(default_factory=list)
    framework: Optional[RegulatoryFramework] = None
    auditor: str = ""  # Internal or external auditor
    audit_firm: str = ""  # External audit firm
    lead_auditor: str = ""
    auditee_contact: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    report_date: Optional[datetime] = None
    findings: List[str] = field(default_factory=list)  # Finding IDs
    areas_covered: List[str] = field(default_factory=list)
    documents_requested: List[str] = field(default_factory=list)
    documents_provided: List[str] = field(default_factory=list)
    opinion: str = ""  # Audit opinion
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "audit_type": self.audit_type.value,
            "status": self.status.value,
            "scope": self.scope,
            "objectives": self.objectives,
            "framework": self.framework.value if self.framework else None,
            "auditor": self.auditor,
            "audit_firm": self.audit_firm,
            "lead_auditor": self.lead_auditor,
            "auditee_contact": self.auditee_contact,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "findings": self.findings,
            "areas_covered": self.areas_covered,
            "documents_requested": self.documents_requested,
            "documents_provided": self.documents_provided,
            "opinion": self.opinion,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class License:
    """A license or certification to track."""

    id: str
    name: str
    description: str = ""
    license_type: str = ""  # software, professional, regulatory
    issuing_authority: str = ""
    holder: str = ""  # Organization or individual
    license_number: str = ""
    issued_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    renewal_lead_days: int = 90  # Days before expiration to start renewal
    status: str = "active"  # active, expired, pending_renewal, suspended
    cost: float = 0.0
    renewal_cost: float = 0.0
    requirements: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    documentation: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if license is expired."""
        if self.expiration_date:
            return _utcnow() > self.expiration_date
        return False

    @property
    def needs_renewal(self) -> bool:
        """Check if license needs renewal soon."""
        if self.expiration_date:
            from datetime import timedelta

            renewal_threshold = self.expiration_date - timedelta(days=self.renewal_lead_days)
            return _utcnow() >= renewal_threshold
        return False

    @property
    def days_until_expiration(self) -> Optional[int]:
        """Get days until expiration."""
        if self.expiration_date:
            delta = self.expiration_date - _utcnow()
            return delta.days
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "license_type": self.license_type,
            "issuing_authority": self.issuing_authority,
            "holder": self.holder,
            "license_number": self.license_number,
            "issued_date": self.issued_date.isoformat() if self.issued_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "days_until_expiration": self.days_until_expiration,
            "renewal_lead_days": self.renewal_lead_days,
            "status": self.status,
            "is_expired": self.is_expired,
            "needs_renewal": self.needs_renewal,
            "cost": self.cost,
            "renewal_cost": self.renewal_cost,
            "requirements": self.requirements,
            "conditions": self.conditions,
            "documentation": self.documentation,
            "metadata": self.metadata,
        }


@dataclass
class ComplianceAssessment:
    """A compliance assessment result."""

    id: str
    name: str
    framework: RegulatoryFramework
    assessment_date: datetime = field(default_factory=_utcnow)
    assessor: str = ""
    scope: str = ""
    overall_status: ComplianceStatus = ComplianceStatus.PENDING
    requirements_assessed: int = 0
    requirements_compliant: int = 0
    requirements_partial: int = 0
    requirements_non_compliant: int = 0
    requirements_na: int = 0
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    next_assessment: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def compliance_score(self) -> float:
        """Calculate compliance score as percentage."""
        total = self.requirements_assessed - self.requirements_na
        if total == 0:
            return 100.0
        compliant = self.requirements_compliant + (self.requirements_partial * 0.5)
        return (compliant / total) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "framework": self.framework.value,
            "assessment_date": self.assessment_date.isoformat(),
            "assessor": self.assessor,
            "scope": self.scope,
            "overall_status": self.overall_status.value,
            "compliance_score": self.compliance_score,
            "requirements_assessed": self.requirements_assessed,
            "requirements_compliant": self.requirements_compliant,
            "requirements_partial": self.requirements_partial,
            "requirements_non_compliant": self.requirements_non_compliant,
            "requirements_na": self.requirements_na,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "next_assessment": self.next_assessment.isoformat() if self.next_assessment else None,
            "metadata": self.metadata,
        }


@dataclass
class EthicsCase:
    """An ethics or conduct case."""

    id: str
    title: str
    description: str = ""
    case_type: str = ""  # conflict_of_interest, harassment, fraud, etc.
    status: str = "open"  # open, investigating, resolved, closed
    reporter: str = ""  # Anonymous if not provided
    is_anonymous: bool = False
    reported_at: datetime = field(default_factory=_utcnow)
    severity: str = "medium"
    assigned_to: str = ""
    involved_parties: List[str] = field(default_factory=list)
    investigation_notes: List[str] = field(default_factory=list)
    resolution: str = ""
    actions_taken: List[str] = field(default_factory=list)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "case_type": self.case_type,
            "status": self.status,
            "reporter": "Anonymous" if self.is_anonymous else self.reporter,
            "is_anonymous": self.is_anonymous,
            "reported_at": self.reported_at.isoformat(),
            "severity": self.severity,
            "assigned_to": self.assigned_to,
            "involved_parties": self.involved_parties,
            "investigation_notes": self.investigation_notes,
            "resolution": self.resolution,
            "actions_taken": self.actions_taken,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata,
        }
