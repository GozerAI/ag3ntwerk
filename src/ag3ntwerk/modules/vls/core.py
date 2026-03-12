"""
VLS Core Data Models.

Defines the fundamental data structures for the Vertical Launch System.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# Enumerations
# =============================================================================


class LaunchStatus(Enum):
    """Status of a vertical launch."""

    PENDING = "pending"
    STAGE_1_INTELLIGENCE = "stage_1_intelligence"
    STAGE_2_VALIDATION = "stage_2_validation"
    STAGE_3_BLUEPRINT = "stage_3_blueprint"
    STAGE_4_BUILD = "stage_4_build"
    STAGE_5_INTAKE = "stage_5_intake"
    STAGE_6_ACQUISITION = "stage_6_acquisition"
    STAGE_7_ROUTING = "stage_7_routing"
    STAGE_8_BILLING = "stage_8_billing"
    STAGE_9_MONITORING = "stage_9_monitoring"
    STAGE_10_KNOWLEDGE = "stage_10_knowledge"
    LIVE = "live"
    PAUSED = "paused"
    STOPPED = "stopped"
    FAILED = "failed"
    ARCHIVED = "archived"


class StageStatus(Enum):
    """Status of a single stage in the pipeline."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class GateStatus(Enum):
    """Gate validation status."""

    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL_PASS = "conditional_pass"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class VerticalStatus(Enum):
    """Operational status of a deployed vertical."""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    ARCHIVED = "archived"


# =============================================================================
# Stage 1: Market Intelligence
# =============================================================================


@dataclass
class NicheCandidate:
    """Candidate niche identified during market intelligence stage."""

    niche_id: str
    name: str
    description: str

    # Market signals
    search_volume: int
    trend_score: float  # 0.0 to 100.0
    competition_level: str  # "low", "medium", "high"

    # Viability indicators
    confidence_score: float  # 0.0 to 1.0
    estimated_market_size: Optional[int] = None
    growth_rate: Optional[float] = None

    # Supporting evidence
    evidence_sources: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    related_niches: List[str] = field(default_factory=list)

    # Metadata
    identified_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Stage 2: Validation & Economics
# =============================================================================


@dataclass
class EconomicsModel:
    """Unit economics and financial projections for a vertical."""

    vertical_name: str

    # Cost structure
    cost_per_lead: float  # CPL
    acquisition_cost: float  # CAC for buyer
    operational_cost_monthly: float
    infrastructure_cost_monthly: float

    # Revenue structure
    price_per_lead: float
    estimated_monthly_volume: int
    gross_margin: float  # As percentage

    # Key metrics
    cac_ltv_ratio: float  # Should be < 3.0
    expected_margin: float  # As percentage
    break_even_months: int

    # Projections
    month_1_revenue: float
    month_3_revenue: float
    month_6_revenue: float
    month_12_revenue: float

    # Risk assessment
    confidence_level: float  # 0.0 to 1.0
    assumptions: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    validated_by: Optional[str] = None  # Agent code


# =============================================================================
# Stage 3: Blueprint Definition
# =============================================================================


@dataclass
class VerticalBlueprint:
    """Formal executable specification for a vertical launch."""

    blueprint_id: str
    vertical_name: str
    vertical_key: str  # URL-safe identifier

    # Market positioning
    niche: NicheCandidate
    icp_definition: Dict[str, Any]  # Ideal Customer Profile
    value_proposition: str
    positioning_statement: str

    # Economics reference
    economics: EconomicsModel

    # Operational specification
    lead_sources: List[str]
    lead_qualification_criteria: Dict[str, Any]
    buyer_qualification_criteria: Dict[str, Any]
    pricing_tiers: List[Dict[str, Any]]

    # Infrastructure requirements
    required_integrations: List[str]
    tech_stack: Dict[str, str]
    deployment_targets: List[str]

    # Monitoring & stop-loss
    success_metrics: Dict[str, float]
    stop_loss_thresholds: Dict[str, float]
    monitoring_frequency: str  # "hourly", "daily", etc.

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None  # Agent code
    approved_by: Optional[str] = None  # CEO approval
    version: str = "1.0"


# =============================================================================
# Stage 5: Lead Intake
# =============================================================================


@dataclass
class LeadRecord:
    """Individual lead captured through the vertical."""

    lead_id: str
    vertical_key: str

    # Lead data
    contact_info: Dict[str, Any]
    qualification_data: Dict[str, Any]
    lead_score: float  # 0.0 to 100.0

    # Classification
    qualified: bool
    rejection_reason: Optional[str] = None
    assigned_tier: Optional[str] = None

    # Routing
    routed_to_buyer: Optional[str] = None  # Buyer ID
    routed_at: Optional[datetime] = None
    delivery_status: str = "pending"  # "pending", "delivered", "failed"

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Stage 6: Buyer Acquisition
# =============================================================================


@dataclass
class BuyerProfile:
    """Profile of a lead buyer in the vertical."""

    buyer_id: str
    vertical_key: str

    # Buyer information
    company_name: str
    contact_name: str
    contact_email: str

    # Business details
    geographic_coverage: List[str]  # Metro areas, states, etc.
    capacity_daily: int  # Max leads per day
    capacity_monthly: int  # Max leads per month

    # Preferences
    lead_preferences: Dict[str, Any]
    pricing_tier: str
    price_per_lead: float

    # Optional fields (must come after required fields)
    contact_phone: Optional[str] = None

    # Performance tracking
    leads_delivered: int = 0
    acceptance_rate: float = 0.0  # Percentage
    average_response_time_hours: float = 0.0
    lifetime_value: float = 0.0

    # Status
    status: str = "active"  # "active", "paused", "churned"
    onboarded_at: datetime = field(default_factory=datetime.utcnow)
    last_purchase_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Helper Functions
# =============================================================================


def stage_number_from_status(status: LaunchStatus) -> int:
    """Convert launch status to stage number."""
    stage_map = {
        LaunchStatus.PENDING: 0,
        LaunchStatus.STAGE_1_INTELLIGENCE: 1,
        LaunchStatus.STAGE_2_VALIDATION: 2,
        LaunchStatus.STAGE_3_BLUEPRINT: 3,
        LaunchStatus.STAGE_4_BUILD: 4,
        LaunchStatus.STAGE_5_INTAKE: 5,
        LaunchStatus.STAGE_6_ACQUISITION: 6,
        LaunchStatus.STAGE_7_ROUTING: 7,
        LaunchStatus.STAGE_8_BILLING: 8,
        LaunchStatus.STAGE_9_MONITORING: 9,
        LaunchStatus.STAGE_10_KNOWLEDGE: 10,
        LaunchStatus.LIVE: 11,
    }
    return stage_map.get(status, 0)


def status_from_stage_number(stage: int) -> LaunchStatus:
    """Convert stage number to launch status."""
    status_map = {
        0: LaunchStatus.PENDING,
        1: LaunchStatus.STAGE_1_INTELLIGENCE,
        2: LaunchStatus.STAGE_2_VALIDATION,
        3: LaunchStatus.STAGE_3_BLUEPRINT,
        4: LaunchStatus.STAGE_4_BUILD,
        5: LaunchStatus.STAGE_5_INTAKE,
        6: LaunchStatus.STAGE_6_ACQUISITION,
        7: LaunchStatus.STAGE_7_ROUTING,
        8: LaunchStatus.STAGE_8_BILLING,
        9: LaunchStatus.STAGE_9_MONITORING,
        10: LaunchStatus.STAGE_10_KNOWLEDGE,
        11: LaunchStatus.LIVE,
    }
    return status_map.get(stage, LaunchStatus.PENDING)
