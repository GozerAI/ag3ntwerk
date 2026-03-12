"""
Data models for the Autonomous Agenda Engine.

This module defines all enums and dataclasses used throughout the agenda system:
- Obstacle types and detection
- Strategy types and generation
- Workstreams and goal decomposition
- Agenda items and scheduling
- Risk assessment and security
- Human-in-the-loop checkpoints
- Audit trail entries
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


# =============================================================================
# Core Enums
# =============================================================================


class ObstacleType(Enum):
    """Types of obstacles that can block goal progress."""

    CAPABILITY_GAP = "capability_gap"  # Missing tool or skill
    RESOURCE_CONSTRAINT = "resource_constraint"  # Budget, time, concurrency limits
    DEPENDENCY = "dependency"  # Blocked by other work
    FAILURE_PATTERN = "failure_pattern"  # Repeated failures on similar tasks
    INTEGRATION_MISSING = "integration_missing"  # Missing external service/API
    KNOWLEDGE_GAP = "knowledge_gap"  # Missing data or context


class StrategyType(Enum):
    """Types of strategies for overcoming obstacles."""

    INTERNAL_CHANGE = "internal_change"  # Adjust routing, retries, params
    TOOL_INGESTION = "tool_ingestion"  # Add new tool/integration
    GOAL_MODIFICATION = "goal_modification"  # Adjust scope, timeline, criteria
    TASK_GENERATION = "task_generation"  # Create new tasks to address gap


class ConfidenceLevel(Enum):
    """Confidence levels for agenda items."""

    HIGH = "high"  # >0.8 - Ready for autonomous execution
    MEDIUM = "medium"  # 0.5-0.8 - May need supervision
    LOW = "low"  # <0.5 - Requires review/approval
    BLOCKED = "blocked"  # Cannot proceed without intervention


class WorkstreamStatus(Enum):
    """Status of a goal workstream."""

    PENDING = "pending"  # Not yet started
    ACTIVE = "active"  # Currently being worked on
    BLOCKED = "blocked"  # Blocked by obstacles
    COMPLETED = "completed"  # Successfully finished
    DEFERRED = "deferred"  # Postponed for later
    CANCELLED = "cancelled"  # No longer needed


# =============================================================================
# Security & HITL Enums
# =============================================================================


class RiskLevel(Enum):
    """Risk levels for agenda items and strategies."""

    MINIMAL = "minimal"  # Read-only, informational tasks
    LOW = "low"  # Internal changes, no external effects
    MEDIUM = "medium"  # External API calls, resource consumption
    HIGH = "high"  # Financial, data modification, deployments
    CRITICAL = "critical"  # Irreversible actions, security changes, production


class RiskCategory(Enum):
    """Categories of risk for classification."""

    FINANCIAL = "financial"  # Budget, payments, subscriptions
    DATA = "data"  # Data modification, deletion, migration
    SECURITY = "security"  # Access control, credentials, auth
    INFRASTRUCTURE = "infrastructure"  # Deployments, system changes
    EXTERNAL = "external"  # Third-party API calls
    REPUTATION = "reputation"  # Public communications, social media
    LEGAL = "legal"  # Compliance, contracts, regulations


class CheckpointType(Enum):
    """Types of human checkpoints."""

    APPROVAL = "approval"  # Yes/No decision required
    REVIEW = "review"  # Human should review but can auto-proceed
    NOTIFICATION = "notification"  # Inform human, no action needed
    CONFIRMATION = "confirmation"  # Confirm understanding before proceeding


# =============================================================================
# Capability and Requirement Models
# =============================================================================


@dataclass
class CapabilityRequirement:
    """Capability needed to complete a milestone/task."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    task_type: str = ""
    tool_category: Optional[str] = None
    agent_code: Optional[str] = None

    # Availability
    is_available: bool = False
    availability_confidence: float = 0.0
    alternative_approaches: List[str] = field(default_factory=list)

    # Source
    inferred_from: str = ""  # What text/goal this was inferred from

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "tool_category": self.tool_category,
            "agent_code": self.agent_code,
            "is_available": self.is_available,
            "availability_confidence": self.availability_confidence,
            "alternative_approaches": self.alternative_approaches,
            "inferred_from": self.inferred_from,
        }


# =============================================================================
# Obstacle Models
# =============================================================================


@dataclass
class Obstacle:
    """An identified obstacle to goal progress."""

    id: str = field(default_factory=lambda: str(uuid4()))
    obstacle_type: ObstacleType = ObstacleType.CAPABILITY_GAP
    severity: float = 0.5  # 0.0-1.0, higher = more blocking

    # What is blocked
    goal_id: Optional[str] = None
    milestone_id: Optional[str] = None
    workstream_id: Optional[str] = None

    # Description
    title: str = ""
    description: str = ""
    evidence: List[str] = field(default_factory=list)

    # Context
    detected_at: datetime = field(default_factory=datetime.now)
    detected_by: str = ""  # Component that found it
    related_failures: List[str] = field(default_factory=list)
    related_task_types: List[str] = field(default_factory=list)

    # Resolution tracking
    status: str = "active"  # active, resolving, resolved, ignored
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_strategy_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "obstacle_type": self.obstacle_type.value,
            "severity": self.severity,
            "goal_id": self.goal_id,
            "milestone_id": self.milestone_id,
            "workstream_id": self.workstream_id,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "detected_at": self.detected_at.isoformat(),
            "detected_by": self.detected_by,
            "related_failures": self.related_failures,
            "related_task_types": self.related_task_types,
            "status": self.status,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_strategy_id": self.resolution_strategy_id,
        }


# =============================================================================
# Strategy Models
# =============================================================================


@dataclass
class Strategy:
    """Strategy for overcoming an obstacle."""

    id: str = field(default_factory=lambda: str(uuid4()))
    strategy_type: StrategyType = StrategyType.INTERNAL_CHANGE
    obstacle_id: str = ""

    # Description
    title: str = ""
    description: str = ""
    rationale: str = ""

    # Implementation
    implementation_steps: List[str] = field(default_factory=list)
    estimated_effort_hours: float = 0.0
    estimated_cost_usd: float = 0.0

    # Scoring
    confidence: float = 0.5
    impact_score: float = 0.5  # Expected improvement (0-1)
    feasibility_score: float = 0.5  # Likelihood of success (0-1)
    priority_score: float = 0.0  # Computed from impact × feasibility / effort

    # Generated tasks (if strategy_type == TASK_GENERATION)
    generated_task_specs: List[Dict[str, Any]] = field(default_factory=list)

    # Internal change details (if strategy_type == INTERNAL_CHANGE)
    parameter_adjustments: Dict[str, Any] = field(default_factory=dict)
    routing_changes: Dict[str, str] = field(default_factory=dict)
    retry_policy_changes: Dict[str, Any] = field(default_factory=dict)

    # Tool ingestion details (if strategy_type == TOOL_INGESTION)
    proposed_tool: Optional[str] = None
    proposed_integration: Optional[str] = None
    tool_requirements: List[str] = field(default_factory=list)

    # Goal modification details (if strategy_type == GOAL_MODIFICATION)
    scope_changes: Optional[str] = None
    timeline_changes: Optional[str] = None
    success_criteria_changes: Optional[str] = None
    milestone_changes: List[Dict[str, Any]] = field(default_factory=list)

    # Status tracking
    status: str = "proposed"  # proposed, approved, rejected, executing, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    executed_at: Optional[datetime] = None
    outcome: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy_type": self.strategy_type.value,
            "obstacle_id": self.obstacle_id,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "implementation_steps": self.implementation_steps,
            "estimated_effort_hours": self.estimated_effort_hours,
            "estimated_cost_usd": self.estimated_cost_usd,
            "confidence": self.confidence,
            "impact_score": self.impact_score,
            "feasibility_score": self.feasibility_score,
            "priority_score": self.priority_score,
            "generated_task_specs": self.generated_task_specs,
            "parameter_adjustments": self.parameter_adjustments,
            "routing_changes": self.routing_changes,
            "retry_policy_changes": self.retry_policy_changes,
            "proposed_tool": self.proposed_tool,
            "proposed_integration": self.proposed_integration,
            "tool_requirements": self.tool_requirements,
            "scope_changes": self.scope_changes,
            "timeline_changes": self.timeline_changes,
            "success_criteria_changes": self.success_criteria_changes,
            "milestone_changes": self.milestone_changes,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "outcome": self.outcome,
        }


# =============================================================================
# Workstream Models
# =============================================================================


@dataclass
class Workstream:
    """A decomposed workstream from a goal."""

    id: str = field(default_factory=lambda: str(uuid4()))
    goal_id: str = ""
    milestone_id: Optional[str] = None

    # Definition
    title: str = ""
    description: str = ""
    objective: str = ""

    # Requirements
    capability_requirements: List[CapabilityRequirement] = field(default_factory=list)
    executive_mapping: Dict[str, str] = field(default_factory=dict)  # task_type -> agent
    estimated_task_count: int = 0

    # Status
    status: WorkstreamStatus = WorkstreamStatus.PENDING
    progress: float = 0.0  # 0-100

    # Tasks
    task_ids: List[str] = field(default_factory=list)
    completed_task_ids: List[str] = field(default_factory=list)
    failed_task_ids: List[str] = field(default_factory=list)

    # Constraints
    obstacle_ids: List[str] = field(default_factory=list)
    strategy_ids: List[str] = field(default_factory=list)
    dependency_workstream_ids: List[str] = field(default_factory=list)  # Must complete before this

    # Timing
    estimated_duration_hours: float = 0.0
    estimated_completion: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "milestone_id": self.milestone_id,
            "title": self.title,
            "description": self.description,
            "objective": self.objective,
            "capability_requirements": [r.to_dict() for r in self.capability_requirements],
            "executive_mapping": self.executive_mapping,
            "estimated_task_count": self.estimated_task_count,
            "status": self.status.value,
            "progress": self.progress,
            "task_ids": self.task_ids,
            "completed_task_ids": self.completed_task_ids,
            "failed_task_ids": self.failed_task_ids,
            "obstacle_ids": self.obstacle_ids,
            "strategy_ids": self.strategy_ids,
            "dependency_workstream_ids": self.dependency_workstream_ids,
            "estimated_duration_hours": self.estimated_duration_hours,
            "estimated_completion": (
                self.estimated_completion.isoformat() if self.estimated_completion else None
            ),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# =============================================================================
# Risk Assessment Models
# =============================================================================


@dataclass
class RiskAssessment:
    """Assessment of risk for an agenda item or strategy."""

    id: str = field(default_factory=lambda: str(uuid4()))
    item_id: str = ""  # ID of what was assessed
    item_type: str = ""  # "agenda_item", "strategy", "obstacle_resolution"

    # Risk classification
    risk_level: RiskLevel = RiskLevel.LOW
    risk_categories: List[RiskCategory] = field(default_factory=list)
    risk_score: float = 0.0  # 0.0-1.0 composite score

    # Specific risks identified
    risks: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)

    # Human oversight requirements
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    approver_role: Optional[str] = None  # "user", "admin", "agent"

    # Audit trail
    assessed_at: datetime = field(default_factory=datetime.now)
    assessed_by: str = "risk_assessor"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "item_id": self.item_id,
            "item_type": self.item_type,
            "risk_level": self.risk_level.value,
            "risk_categories": [c.value for c in self.risk_categories],
            "risk_score": self.risk_score,
            "risks": self.risks,
            "mitigations": self.mitigations,
            "requires_approval": self.requires_approval,
            "approval_reason": self.approval_reason,
            "approver_role": self.approver_role,
            "assessed_at": self.assessed_at.isoformat(),
            "assessed_by": self.assessed_by,
        }


# =============================================================================
# Checkpoint Models
# =============================================================================


@dataclass
class Checkpoint:
    """A human-in-the-loop checkpoint."""

    id: str = field(default_factory=lambda: str(uuid4()))
    checkpoint_type: CheckpointType = CheckpointType.APPROVAL

    # What triggered the checkpoint
    trigger_reason: str = ""
    risk_assessment: Optional[RiskAssessment] = None

    # What's being checked
    item_id: Optional[str] = None  # AgendaItem ID
    strategy_id: Optional[str] = None  # Strategy ID

    # Context for human
    title: str = ""
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    # Options presented to human
    options: List[str] = field(default_factory=lambda: ["Approve", "Reject", "Defer"])
    default_option: Optional[str] = None

    # Resolution
    status: str = "pending"  # pending, approved, rejected, modified, timeout, escalated
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    selected_option: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    escalated_to: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "checkpoint_type": self.checkpoint_type.value,
            "trigger_reason": self.trigger_reason,
            "risk_assessment": self.risk_assessment.to_dict() if self.risk_assessment else None,
            "item_id": self.item_id,
            "strategy_id": self.strategy_id,
            "title": self.title,
            "description": self.description,
            "context": self.context,
            "options": self.options,
            "default_option": self.default_option,
            "status": self.status,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
            "selected_option": self.selected_option,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "escalated_at": self.escalated_at.isoformat() if self.escalated_at else None,
            "escalated_to": self.escalated_to,
        }


# =============================================================================
# HITL Configuration
# =============================================================================


@dataclass
class HITLConfig:
    """Human-in-the-loop configuration."""

    # Master toggle
    enabled: bool = True

    # Risk-based thresholds (require approval above these levels)
    approval_threshold_risk_level: RiskLevel = RiskLevel.MEDIUM
    approval_threshold_risk_score: float = 0.5

    # Category-specific overrides (always require approval)
    always_approve_categories: List[RiskCategory] = field(
        default_factory=lambda: [
            RiskCategory.FINANCIAL,
            RiskCategory.SECURITY,
            RiskCategory.LEGAL,
        ]
    )

    # Task type overrides (always require approval)
    always_approve_task_types: List[str] = field(
        default_factory=lambda: [
            "deployment",
            "data_migration",
            "credential_rotation",
            "payment_processing",
            "security_scan",
            "production_release",
        ]
    )

    # Strategy type overrides (always require approval)
    always_approve_strategy_types: List[StrategyType] = field(
        default_factory=lambda: [
            StrategyType.TOOL_INGESTION,
            StrategyType.GOAL_MODIFICATION,
        ]
    )

    # Autonomous execution thresholds
    auto_execute_max_risk_level: RiskLevel = RiskLevel.LOW
    auto_execute_max_cost_usd: float = 10.0
    auto_execute_confidence_threshold: float = 0.9

    # Batch approval settings
    allow_batch_approval: bool = True
    max_batch_size: int = 10

    # Timeout settings
    approval_timeout_hours: int = 24
    escalation_after_hours: int = 4

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "approval_threshold_risk_level": self.approval_threshold_risk_level.value,
            "approval_threshold_risk_score": self.approval_threshold_risk_score,
            "always_approve_categories": [c.value for c in self.always_approve_categories],
            "always_approve_task_types": self.always_approve_task_types,
            "always_approve_strategy_types": [s.value for s in self.always_approve_strategy_types],
            "auto_execute_max_risk_level": self.auto_execute_max_risk_level.value,
            "auto_execute_max_cost_usd": self.auto_execute_max_cost_usd,
            "auto_execute_confidence_threshold": self.auto_execute_confidence_threshold,
            "allow_batch_approval": self.allow_batch_approval,
            "max_batch_size": self.max_batch_size,
            "approval_timeout_hours": self.approval_timeout_hours,
            "escalation_after_hours": self.escalation_after_hours,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HITLConfig":
        """Create config from dictionary."""
        config = cls()
        if "enabled" in data:
            config.enabled = data["enabled"]
        if "approval_threshold_risk_level" in data:
            config.approval_threshold_risk_level = RiskLevel(data["approval_threshold_risk_level"])
        if "approval_threshold_risk_score" in data:
            config.approval_threshold_risk_score = data["approval_threshold_risk_score"]
        if "always_approve_categories" in data:
            config.always_approve_categories = [
                RiskCategory(c) for c in data["always_approve_categories"]
            ]
        if "always_approve_task_types" in data:
            config.always_approve_task_types = data["always_approve_task_types"]
        if "always_approve_strategy_types" in data:
            config.always_approve_strategy_types = [
                StrategyType(s) for s in data["always_approve_strategy_types"]
            ]
        if "auto_execute_max_risk_level" in data:
            config.auto_execute_max_risk_level = RiskLevel(data["auto_execute_max_risk_level"])
        if "auto_execute_max_cost_usd" in data:
            config.auto_execute_max_cost_usd = data["auto_execute_max_cost_usd"]
        if "auto_execute_confidence_threshold" in data:
            config.auto_execute_confidence_threshold = data["auto_execute_confidence_threshold"]
        if "allow_batch_approval" in data:
            config.allow_batch_approval = data["allow_batch_approval"]
        if "max_batch_size" in data:
            config.max_batch_size = data["max_batch_size"]
        if "approval_timeout_hours" in data:
            config.approval_timeout_hours = data["approval_timeout_hours"]
        if "escalation_after_hours" in data:
            config.escalation_after_hours = data["escalation_after_hours"]
        return config


# =============================================================================
# Audit Trail Models
# =============================================================================


@dataclass
class AuditEntry:
    """Audit trail entry for security-relevant actions."""

    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    action_type: str = (
        ""  # "approval", "rejection", "execution", "escalation", "checkpoint_created"
    )

    # What was acted upon
    item_id: Optional[str] = None
    strategy_id: Optional[str] = None
    checkpoint_id: Optional[str] = None
    agenda_id: Optional[str] = None

    # Who acted
    actor: str = ""  # "system", "user:xxx", "auto", "escalation"
    actor_role: Optional[str] = None

    # Action details
    risk_level: Optional[RiskLevel] = None
    risk_score: Optional[float] = None
    decision: str = ""
    reason: Optional[str] = None

    # Context
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "action_type": self.action_type,
            "item_id": self.item_id,
            "strategy_id": self.strategy_id,
            "checkpoint_id": self.checkpoint_id,
            "agenda_id": self.agenda_id,
            "actor": self.actor,
            "actor_role": self.actor_role,
            "risk_level": self.risk_level.value if self.risk_level else None,
            "risk_score": self.risk_score,
            "decision": self.decision,
            "reason": self.reason,
            "context": self.context,
        }


# =============================================================================
# Agenda Item Models
# =============================================================================


@dataclass
class AgendaItem:
    """A single item on the generated agenda."""

    id: str = field(default_factory=lambda: str(uuid4()))

    # Source
    goal_id: Optional[str] = None
    workstream_id: Optional[str] = None
    milestone_id: Optional[str] = None
    strategy_id: Optional[str] = None  # If generated from strategy

    # Task specification
    task_type: str = ""
    title: str = ""
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    # Routing
    recommended_agent: Optional[str] = None
    alternative_executives: List[str] = field(default_factory=list)

    # Scoring
    priority_score: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    confidence_score: float = 0.5

    # Constraints
    dependencies: List[str] = field(default_factory=list)  # Other agenda item IDs
    estimated_duration_minutes: float = 15.0
    estimated_cost_usd: float = 0.5

    # Execution hints
    retry_policy: Dict[str, Any] = field(
        default_factory=lambda: {
            "max_retries": 3,
            "backoff_seconds": 5,
        }
    )
    timeout_seconds: int = 300

    # For obstacle resolution
    is_obstacle_resolution: bool = False
    resolves_obstacle_id: Optional[str] = None

    # Security additions
    risk_assessment: Optional[RiskAssessment] = None
    checkpoint: Optional[Checkpoint] = None
    requires_approval: bool = False
    approval_status: str = "not_required"  # not_required, pending, approved, rejected
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    # Execution status
    status: str = "pending"  # pending, ready, executing, completed, failed, skipped
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_result: Optional[Dict[str, Any]] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "workstream_id": self.workstream_id,
            "milestone_id": self.milestone_id,
            "strategy_id": self.strategy_id,
            "task_type": self.task_type,
            "title": self.title,
            "description": self.description,
            "context": self.context,
            "recommended_agent": self.recommended_agent,
            "alternative_executives": self.alternative_executives,
            "priority_score": self.priority_score,
            "confidence_level": self.confidence_level.value,
            "confidence_score": self.confidence_score,
            "dependencies": self.dependencies,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "estimated_cost_usd": self.estimated_cost_usd,
            "retry_policy": self.retry_policy,
            "timeout_seconds": self.timeout_seconds,
            "is_obstacle_resolution": self.is_obstacle_resolution,
            "resolves_obstacle_id": self.resolves_obstacle_id,
            "risk_assessment": self.risk_assessment.to_dict() if self.risk_assessment else None,
            "checkpoint": self.checkpoint.to_dict() if self.checkpoint else None,
            "requires_approval": self.requires_approval,
            "approval_status": self.approval_status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "status": self.status,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_result": self.execution_result,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# Agenda Models
# =============================================================================


@dataclass
class Agenda:
    """Complete agenda for a time period."""

    id: str = field(default_factory=lambda: str(uuid4()))

    # Time period
    period_start: datetime = field(default_factory=datetime.now)
    period_end: datetime = field(default_factory=datetime.now)
    period_type: str = "daily"  # daily, weekly, sprint

    # Items
    items: List[AgendaItem] = field(default_factory=list)
    total_estimated_duration_minutes: float = 0.0
    total_estimated_cost_usd: float = 0.0

    # Coverage
    goals_addressed: List[str] = field(default_factory=list)
    milestones_addressed: List[str] = field(default_factory=list)
    obstacles_addressed: List[str] = field(default_factory=list)
    workstreams_addressed: List[str] = field(default_factory=list)

    # Balance metrics
    executive_distribution: Dict[str, int] = field(default_factory=dict)
    goal_distribution: Dict[str, int] = field(default_factory=dict)
    obstacle_resolution_count: int = 0

    # Status
    status: str = "draft"  # draft, active, completed, archived
    items_completed: int = 0
    items_failed: int = 0
    items_skipped: int = 0
    items_pending_approval: int = 0

    # Generation metadata
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "agenda_engine"
    generation_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "period_type": self.period_type,
            "items": [item.to_dict() for item in self.items],
            "total_estimated_duration_minutes": self.total_estimated_duration_minutes,
            "total_estimated_cost_usd": self.total_estimated_cost_usd,
            "goals_addressed": self.goals_addressed,
            "milestones_addressed": self.milestones_addressed,
            "obstacles_addressed": self.obstacles_addressed,
            "workstreams_addressed": self.workstreams_addressed,
            "executive_distribution": self.executive_distribution,
            "goal_distribution": self.goal_distribution,
            "obstacle_resolution_count": self.obstacle_resolution_count,
            "status": self.status,
            "items_completed": self.items_completed,
            "items_failed": self.items_failed,
            "items_skipped": self.items_skipped,
            "items_pending_approval": self.items_pending_approval,
            "generated_at": self.generated_at.isoformat(),
            "generated_by": self.generated_by,
            "generation_context": self.generation_context,
        }

    def get_executable_items(self) -> List[AgendaItem]:
        """Get items ready for execution (approved or no approval needed)."""
        return [
            item
            for item in self.items
            if item.approval_status in ("not_required", "approved") and item.status == "pending"
        ]

    def get_items_awaiting_approval(self) -> List[AgendaItem]:
        """Get items waiting for human approval."""
        return [item for item in self.items if item.approval_status == "pending"]

    def get_items_by_agent(self, agent_code: str) -> List[AgendaItem]:
        """Get items assigned to a specific agent."""
        return [item for item in self.items if item.recommended_agent == agent_code]

    def get_obstacle_resolution_items(self) -> List[AgendaItem]:
        """Get items that resolve obstacles."""
        return [item for item in self.items if item.is_obstacle_resolution]

    def update_metrics(self) -> None:
        """Update computed metrics based on current items."""
        self.total_estimated_duration_minutes = sum(
            item.estimated_duration_minutes for item in self.items
        )
        self.total_estimated_cost_usd = sum(item.estimated_cost_usd for item in self.items)

        # Agent distribution
        self.executive_distribution = {}
        for item in self.items:
            agent_code = item.recommended_agent or "unassigned"
            self.executive_distribution[agent_code] = (
                self.executive_distribution.get(agent_code, 0) + 1
            )

        # Goal distribution
        self.goal_distribution = {}
        for item in self.items:
            if item.goal_id:
                self.goal_distribution[item.goal_id] = (
                    self.goal_distribution.get(item.goal_id, 0) + 1
                )

        # Obstacle resolution count
        self.obstacle_resolution_count = len(self.get_obstacle_resolution_items())

        # Coverage
        self.goals_addressed = list(set(item.goal_id for item in self.items if item.goal_id))
        self.milestones_addressed = list(
            set(item.milestone_id for item in self.items if item.milestone_id)
        )
        self.workstreams_addressed = list(
            set(item.workstream_id for item in self.items if item.workstream_id)
        )
        self.obstacles_addressed = list(
            set(item.resolves_obstacle_id for item in self.items if item.resolves_obstacle_id)
        )

        # Status counts
        self.items_completed = len([i for i in self.items if i.status == "completed"])
        self.items_failed = len([i for i in self.items if i.status == "failed"])
        self.items_skipped = len([i for i in self.items if i.status == "skipped"])
        self.items_pending_approval = len(self.get_items_awaiting_approval())
