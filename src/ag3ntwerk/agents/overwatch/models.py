"""
Overwatch (Overwatch) Operations Domain Models.

Data models for orchestration, workflow management, operational metrics,
and drift detection for Nexus escalation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class WorkflowStatus(Enum):
    """Workflow execution status."""

    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class TaskRoutingStrategy(Enum):
    """Task routing strategies."""

    RULE_BASED = "rule_based"
    CAPABILITY_MATCH = "capability_match"
    LOAD_BALANCED = "load_balanced"
    ROUND_ROBIN = "round_robin"
    AI_DECISION = "ai_decision"
    PRIORITY_BASED = "priority_based"


class ExecutionMode(Enum):
    """Workflow execution modes."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"
    CONDITIONAL = "conditional"


class OperationalHealth(Enum):
    """Operational health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ProcessStatus(Enum):
    """Business process status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    UNDER_REVIEW = "under_review"
    DEPRECATED = "deprecated"


class OKRStatus(Enum):
    """OKR tracking status."""

    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    OFF_TRACK = "off_track"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class EfficiencyLevel(Enum):
    """Efficiency rating levels."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"


class DelegationResult(Enum):
    """Task delegation result."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


# =============================================================================
# Drift Detection Models (for Nexus escalation)
# =============================================================================


class DriftType(Enum):
    """Types of drift that trigger Nexus escalation."""

    PERFORMANCE = "performance"  # Success rate drops below threshold
    ROUTING = "routing"  # Task types appearing without defined routes
    LOAD = "load"  # Sustained imbalance across agents
    CONFLICT = "conflict"  # Agents returning contradictory results
    CONTEXT = "context"  # Task context assumptions no longer valid
    RESOURCE = "resource"  # Resource exhaustion or capacity issues
    LATENCY = "latency"  # Response times exceeding SLOs


@dataclass
class DriftSignal:
    """A detected drift signal that may require Nexus escalation."""

    id: str = field(default_factory=lambda: str(uuid4()))
    drift_type: DriftType = DriftType.PERFORMANCE
    severity: float = 0.0  # 0.0 to 1.0, where 1.0 is critical
    description: str = ""
    detected_at: datetime = field(default_factory=_utcnow)

    # Context about the drift
    affected_executive: Optional[str] = None
    affected_task_type: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    baseline_value: Optional[float] = None

    # Resolution
    escalated: bool = False
    escalated_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_action: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def exceeds_tolerance(self) -> bool:
        """Check if drift exceeds tolerance threshold."""
        # Default tolerance: severity > 0.5 requires escalation
        return self.severity > 0.5


@dataclass
class StrategicContext:
    """Strategic context provided by Nexus (Nexus) for Overwatch operations.

    This is the "standing orders" that Overwatch operates under until drift
    triggers a request for updated guidance.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    received_at: datetime = field(default_factory=_utcnow)
    valid_until: Optional[datetime] = None

    # Routing configuration
    routing_rules: Dict[str, str] = field(default_factory=dict)
    routing_priorities: Dict[str, int] = field(default_factory=dict)

    # Performance thresholds
    success_rate_threshold: float = 0.7  # Below this triggers drift
    latency_slo_ms: float = 5000.0  # Above this triggers drift

    # Load balancing
    max_agent_load: float = 0.9  # 90% capacity max
    load_rebalance_threshold: float = 0.3  # Rebalance if imbalance > 30%

    # Escalation configuration
    drift_tolerance: float = 0.5  # Drift severity threshold
    auto_escalation_enabled: bool = True
    escalation_cooldown_seconds: int = 300  # 5 minutes between escalations

    # Active workflows
    active_workflow_definitions: List[str] = field(default_factory=list)

    # Notes from Nexus
    strategic_notes: str = ""

    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Core Workflow Models
# =============================================================================


@dataclass
class WorkflowStep:
    """Represents a step in a workflow."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    agent: str = ""  # Target agent code (e.g., "Forge", "Keystone")
    task_type: str = ""
    depends_on: List[str] = field(default_factory=list)  # Step IDs
    status: WorkflowStatus = WorkflowStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    optional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Workflow:
    """Represents a multi-step workflow."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    steps: List[WorkflowStep] = field(default_factory=list)
    current_step: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    priority: int = 5  # 1-10, 1 being highest
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskDelegation:
    """Represents a task delegation to an agent."""

    id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    task_type: str = ""
    description: str = ""
    source_executive: str = "Overwatch"  # Changed from Nexus
    target_agent: str = ""
    routing_strategy: TaskRoutingStrategy = TaskRoutingStrategy.RULE_BASED
    result: DelegationResult = DelegationResult.SUCCESS
    created_at: datetime = field(default_factory=_utcnow)
    delegated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    response_time_ms: Optional[int] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingRule:
    """Represents a task routing rule."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    task_types: List[str] = field(default_factory=list)
    target_agent: str = ""
    priority: int = 1  # Higher priority rules checked first
    conditions: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    hit_count: int = 0
    last_used: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationalMetrics:
    """Operational metrics for system health."""

    timestamp: datetime = field(default_factory=_utcnow)

    # Task metrics
    tasks_received: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_delegated: int = 0
    tasks_in_progress: int = 0

    # Performance metrics
    avg_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0

    # Throughput metrics
    tasks_per_minute: float = 0.0
    workflows_per_hour: float = 0.0

    # Success metrics
    success_rate: float = 0.0
    delegation_success_rate: float = 0.0

    # Resource metrics
    active_executives: int = 0
    queue_depth: int = 0

    # Health
    overall_health: OperationalHealth = OperationalHealth.HEALTHY

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutiveStatus:
    """Status of a ag3ntwerk agent."""

    code: str = ""
    name: str = ""
    codename: str = ""
    is_active: bool = True
    is_healthy: bool = True
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_response_time_ms: float = 0.0
    capabilities: List[str] = field(default_factory=list)
    last_activity: Optional[datetime] = None
    current_task: Optional[str] = None
    queue_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BusinessProcess:
    """Represents a business process."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: ProcessStatus = ProcessStatus.ACTIVE
    owner: str = ""  # Agent code responsible
    stakeholders: List[str] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    sla_hours: Optional[float] = None
    efficiency_score: Optional[float] = None
    automation_level: float = 0.0  # 0-100%
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OKR:
    """Represents an Objective and Key Result."""

    id: str = field(default_factory=lambda: str(uuid4()))
    objective: str = ""
    description: str = ""
    owner: str = ""  # Agent code responsible
    status: OKRStatus = OKRStatus.ON_TRACK
    key_results: List[Dict[str, Any]] = field(default_factory=list)
    progress: float = 0.0  # 0-100%
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    related_workflows: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossFunctionalProject:
    """Represents a cross-functional project involving multiple agents."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    lead_executive: str = ""
    participating_executives: List[str] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    target_end_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    progress: float = 0.0
    risks: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperatingCadence:
    """Represents an operating cadence or recurring process."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    frequency: str = "weekly"  # daily, weekly, monthly, quarterly
    participants: List[str] = field(default_factory=list)
    agenda_template: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)
    next_occurrence: Optional[datetime] = None
    last_occurrence: Optional[datetime] = None
    enabled: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VendorOperation:
    """Represents a vendor operation or integration."""

    id: str = field(default_factory=lambda: str(uuid4()))
    vendor_name: str = ""
    service_type: str = ""
    status: str = "active"
    owner: str = ""  # Agent code responsible
    contract_start: Optional[datetime] = None
    contract_end: Optional[datetime] = None
    sla_metrics: Dict[str, Any] = field(default_factory=dict)
    integration_points: List[str] = field(default_factory=list)
    cost_monthly: Optional[float] = None
    health_score: float = 100.0
    last_review: Optional[datetime] = None
    issues: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeliveryReliability:
    """Metrics for delivery reliability."""

    timestamp: datetime = field(default_factory=_utcnow)
    period: str = "daily"  # daily, weekly, monthly

    # On-time delivery
    deliveries_total: int = 0
    deliveries_on_time: int = 0
    on_time_rate: float = 0.0

    # Quality metrics
    defect_rate: float = 0.0
    rework_rate: float = 0.0

    # Prediction accuracy
    estimated_vs_actual_ratio: float = 1.0

    # Throughput
    velocity: float = 0.0
    capacity_utilization: float = 0.0

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealthCheck:
    """System health check results."""

    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=_utcnow)
    overall_status: OperationalHealth = OperationalHealth.HEALTHY

    # Component health
    llm_provider_healthy: bool = True
    executives_healthy: bool = True
    communication_healthy: bool = True
    queue_healthy: bool = True

    # Details
    agent_statuses: List[ExecutiveStatus] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Metrics at check time
    metrics: Optional[OperationalMetrics] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


# Orchestration capabilities list
ORCHESTRATION_CAPABILITIES = [
    # Task Management
    "task_routing",
    "task_delegation",
    "task_prioritization",
    "task_scheduling",
    # Workflow Management
    "workflow_creation",
    "workflow_execution",
    "workflow_monitoring",
    "workflow_optimization",
    # Coordination
    "cross_functional_coordination",
    "executive_communication",
    "resource_allocation",
    "conflict_resolution",
    # Monitoring
    "system_monitoring",
    "health_checking",
    "metrics_collection",
    "alerting",
    # Process Management
    "process_design",
    "process_optimization",
    "sla_management",
    "vendor_management",
    # Strategic
    "okr_tracking",
    "cadence_management",
    "delivery_tracking",
    "efficiency_analysis",
    # Drift Detection (new)
    "drift_detection",
    "coo_escalation",
    "context_synchronization",
]
