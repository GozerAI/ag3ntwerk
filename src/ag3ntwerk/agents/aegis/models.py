"""
Data models for the Aegis (Aegis) agent.

This module defines the core data structures for enterprise risk management,
threat modeling, and business continuity planning.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class RiskCategory(Enum):
    """Categories of enterprise risk."""

    STRATEGIC = "strategic"  # Market, competitive, regulatory
    OPERATIONAL = "operational"  # Process, people, systems
    FINANCIAL = "financial"  # Credit, liquidity, market
    COMPLIANCE = "compliance"  # Legal, regulatory, policy
    TECHNOLOGY = "technology"  # Cyber, infrastructure, data
    REPUTATIONAL = "reputational"  # Brand, public relations
    ENVIRONMENTAL = "environmental"  # Climate, sustainability
    THIRD_PARTY = "third_party"  # Vendor, supply chain


class RiskSeverity(Enum):
    """Risk severity levels."""

    CRITICAL = "critical"  # Existential threat
    HIGH = "high"  # Significant impact
    MEDIUM = "medium"  # Moderate impact
    LOW = "low"  # Minor impact
    MINIMAL = "minimal"  # Negligible impact


class RiskLikelihood(Enum):
    """Risk likelihood levels."""

    ALMOST_CERTAIN = "almost_certain"  # >90% probability
    LIKELY = "likely"  # 60-90% probability
    POSSIBLE = "possible"  # 30-60% probability
    UNLIKELY = "unlikely"  # 10-30% probability
    RARE = "rare"  # <10% probability


class RiskStatus(Enum):
    """Risk management status."""

    IDENTIFIED = "identified"  # Newly identified
    ASSESSED = "assessed"  # Analyzed and scored
    MITIGATING = "mitigating"  # Mitigation in progress
    ACCEPTED = "accepted"  # Risk accepted
    TRANSFERRED = "transferred"  # Risk transferred (insurance)
    AVOIDED = "avoided"  # Risk avoided
    CLOSED = "closed"  # No longer applicable


class MitigationStrategy(Enum):
    """Risk mitigation strategies."""

    AVOID = "avoid"  # Eliminate the risk
    MITIGATE = "mitigate"  # Reduce likelihood or impact
    TRANSFER = "transfer"  # Insurance or contractual transfer
    ACCEPT = "accept"  # Accept the risk
    SHARE = "share"  # Share with partners


class ThreatType(Enum):
    """Types of threats for threat modeling."""

    SPOOFING = "spoofing"  # Identity spoofing
    TAMPERING = "tampering"  # Data tampering
    REPUDIATION = "repudiation"  # Denying actions
    INFORMATION_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"
    # Additional threat types
    INSIDER_THREAT = "insider_threat"
    SUPPLY_CHAIN = "supply_chain"
    SOCIAL_ENGINEERING = "social_engineering"
    PHYSICAL = "physical"


@dataclass
class RiskScore:
    """Quantified risk score."""

    likelihood_score: float  # 1-5 scale
    impact_score: float  # 1-5 scale
    velocity_score: float = 3.0  # How fast risk can materialize (1-5)
    detection_score: float = 3.0  # How easy to detect (1-5, higher = easier)

    @property
    def inherent_score(self) -> float:
        """Calculate inherent risk score (before controls)."""
        return self.likelihood_score * self.impact_score

    @property
    def risk_level(self) -> RiskSeverity:
        """Determine risk level from score."""
        score = self.inherent_score
        if score >= 20:
            return RiskSeverity.CRITICAL
        elif score >= 12:
            return RiskSeverity.HIGH
        elif score >= 6:
            return RiskSeverity.MEDIUM
        elif score >= 3:
            return RiskSeverity.LOW
        else:
            return RiskSeverity.MINIMAL

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "likelihood_score": self.likelihood_score,
            "impact_score": self.impact_score,
            "velocity_score": self.velocity_score,
            "detection_score": self.detection_score,
            "inherent_score": self.inherent_score,
            "risk_level": self.risk_level.value,
        }


@dataclass
class Control:
    """A risk control or mitigation measure."""

    id: str
    name: str
    description: str = ""
    control_type: str = "preventive"  # preventive, detective, corrective
    effectiveness: float = 0.5  # 0-1, reduction in risk
    cost: float = 0.0
    owner: str = ""
    status: str = "proposed"  # proposed, implemented, validated
    implementation_date: Optional[datetime] = None
    last_tested: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "control_type": self.control_type,
            "effectiveness": self.effectiveness,
            "cost": self.cost,
            "owner": self.owner,
            "status": self.status,
            "implementation_date": (
                self.implementation_date.isoformat() if self.implementation_date else None
            ),
            "last_tested": self.last_tested.isoformat() if self.last_tested else None,
            "metadata": self.metadata,
        }


@dataclass
class Risk:
    """Represents an enterprise risk."""

    id: str
    name: str
    description: str = ""
    category: RiskCategory = RiskCategory.OPERATIONAL
    status: RiskStatus = RiskStatus.IDENTIFIED
    owner: str = ""
    inherent_score: Optional[RiskScore] = None
    residual_score: Optional[RiskScore] = None
    controls: List[str] = field(default_factory=list)  # Control IDs
    mitigation_strategy: MitigationStrategy = MitigationStrategy.MITIGATE
    potential_impact: str = ""  # Description of potential impact
    financial_exposure: float = 0.0  # Estimated financial exposure
    affected_assets: List[str] = field(default_factory=list)
    related_risks: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    review_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_residual_risk(self, controls: List[Control]) -> RiskScore:
        """Calculate residual risk after controls."""
        if not self.inherent_score:
            return RiskScore(likelihood_score=3.0, impact_score=3.0)

        total_effectiveness = sum(c.effectiveness for c in controls)
        # Cap effectiveness at 90%
        reduction = min(0.9, total_effectiveness)

        return RiskScore(
            likelihood_score=self.inherent_score.likelihood_score * (1 - reduction),
            impact_score=self.inherent_score.impact_score,
            velocity_score=self.inherent_score.velocity_score,
            detection_score=self.inherent_score.detection_score + (reduction * 2),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "status": self.status.value,
            "owner": self.owner,
            "inherent_score": self.inherent_score.to_dict() if self.inherent_score else None,
            "residual_score": self.residual_score.to_dict() if self.residual_score else None,
            "controls": self.controls,
            "mitigation_strategy": self.mitigation_strategy.value,
            "potential_impact": self.potential_impact,
            "financial_exposure": self.financial_exposure,
            "affected_assets": self.affected_assets,
            "related_risks": self.related_risks,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "metadata": self.metadata,
        }


@dataclass
class Threat:
    """A threat in the threat model."""

    id: str
    name: str
    description: str = ""
    threat_type: ThreatType = ThreatType.TAMPERING
    target: str = ""  # What the threat targets
    threat_actor: str = ""  # Who poses the threat
    attack_vector: str = ""  # How the threat manifests
    severity: RiskSeverity = RiskSeverity.MEDIUM
    likelihood: RiskLikelihood = RiskLikelihood.POSSIBLE
    mitigations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "threat_type": self.threat_type.value,
            "target": self.target,
            "threat_actor": self.threat_actor,
            "attack_vector": self.attack_vector,
            "severity": self.severity.value,
            "likelihood": self.likelihood.value,
            "mitigations": self.mitigations,
            "metadata": self.metadata,
        }


@dataclass
class ThreatModel:
    """A complete threat model for a system or component."""

    id: str
    name: str
    description: str = ""
    scope: str = ""  # What is being modeled
    threats: List[Threat] = field(default_factory=list)
    assets: List[str] = field(default_factory=list)  # Assets in scope
    data_flows: List[Dict[str, Any]] = field(default_factory=list)
    trust_boundaries: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    version: str = "1.0"
    status: str = "draft"  # draft, reviewed, approved
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_threat(self, threat: Threat) -> None:
        """Add a threat to the model."""
        self.threats.append(threat)
        self.updated_at = _utcnow()

    def get_threats_by_type(self, threat_type: ThreatType) -> List[Threat]:
        """Get all threats of a specific type."""
        return [t for t in self.threats if t.threat_type == threat_type]

    def get_high_severity_threats(self) -> List[Threat]:
        """Get all high and critical severity threats."""
        return [t for t in self.threats if t.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "scope": self.scope,
            "threats": [t.to_dict() for t in self.threats],
            "assets": self.assets,
            "data_flows": self.data_flows,
            "trust_boundaries": self.trust_boundaries,
            "assumptions": self.assumptions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class RiskAppetite:
    """Organization's risk appetite settings."""

    id: str
    name: str = "Default Risk Appetite"
    description: str = ""
    # Tolerance thresholds by category
    tolerances: Dict[str, RiskSeverity] = field(default_factory=dict)
    # Maximum acceptable financial exposure
    max_financial_exposure: float = 0.0
    # Categories with zero tolerance
    zero_tolerance_categories: List[RiskCategory] = field(default_factory=list)
    approved_by: str = ""
    approved_at: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    review_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_within_appetite(self, risk: Risk) -> bool:
        """Check if a risk is within appetite."""
        if risk.category in self.zero_tolerance_categories:
            return False

        if risk.financial_exposure > self.max_financial_exposure:
            return False

        category_key = risk.category.value
        if category_key in self.tolerances:
            tolerance = self.tolerances[category_key]
            if risk.inherent_score:
                risk_level = risk.inherent_score.risk_level
                severity_order = [
                    RiskSeverity.MINIMAL,
                    RiskSeverity.LOW,
                    RiskSeverity.MEDIUM,
                    RiskSeverity.HIGH,
                    RiskSeverity.CRITICAL,
                ]
                return severity_order.index(risk_level) <= severity_order.index(tolerance)

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tolerances": {k: v.value for k, v in self.tolerances.items()},
            "max_financial_exposure": self.max_financial_exposure,
            "zero_tolerance_categories": [c.value for c in self.zero_tolerance_categories],
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "metadata": self.metadata,
        }


@dataclass
class BusinessContinuityPlan:
    """Business continuity and disaster recovery plan."""

    id: str
    name: str
    description: str = ""
    scope: str = ""
    # Recovery objectives
    rto_hours: float = 24.0  # Recovery Time Objective
    rpo_hours: float = 4.0  # Recovery Point Objective
    mtpd_hours: float = 72.0  # Maximum Tolerable Period of Disruption
    # Plan components
    critical_functions: List[str] = field(default_factory=list)
    recovery_procedures: List[Dict[str, Any]] = field(default_factory=list)
    communication_plan: Dict[str, Any] = field(default_factory=dict)
    resource_requirements: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    # Status
    status: str = "draft"  # draft, approved, tested
    last_tested: Optional[datetime] = None
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    owner: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "scope": self.scope,
            "rto_hours": self.rto_hours,
            "rpo_hours": self.rpo_hours,
            "mtpd_hours": self.mtpd_hours,
            "critical_functions": self.critical_functions,
            "recovery_procedures": self.recovery_procedures,
            "communication_plan": self.communication_plan,
            "resource_requirements": self.resource_requirements,
            "dependencies": self.dependencies,
            "status": self.status,
            "last_tested": self.last_tested.isoformat() if self.last_tested else None,
            "test_results": self.test_results,
            "owner": self.owner,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class RiskIncident:
    """A realized risk or incident."""

    id: str
    name: str
    description: str = ""
    related_risk_id: Optional[str] = None
    category: RiskCategory = RiskCategory.OPERATIONAL
    severity: RiskSeverity = RiskSeverity.MEDIUM
    status: str = "open"  # open, investigating, resolved, closed
    detected_at: datetime = field(default_factory=_utcnow)
    resolved_at: Optional[datetime] = None
    root_cause: str = ""
    impact_description: str = ""
    financial_impact: float = 0.0
    affected_systems: List[str] = field(default_factory=list)
    response_actions: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    owner: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def resolution_time_hours(self) -> Optional[float]:
        """Calculate time to resolution in hours."""
        if self.resolved_at:
            delta = self.resolved_at - self.detected_at
            return delta.total_seconds() / 3600
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "related_risk_id": self.related_risk_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "status": self.status,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_time_hours": self.resolution_time_hours,
            "root_cause": self.root_cause,
            "impact_description": self.impact_description,
            "financial_impact": self.financial_impact,
            "affected_systems": self.affected_systems,
            "response_actions": self.response_actions,
            "lessons_learned": self.lessons_learned,
            "owner": self.owner,
            "metadata": self.metadata,
        }
