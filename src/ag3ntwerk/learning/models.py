"""
Data models for the ag3ntwerk Learning System.

Defines all data structures used for outcome tracking, pattern storage,
issue management, and learning adjustments.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class OutcomeType(Enum):
    """Types of task outcomes."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


class ErrorCategory(Enum):
    """Categories of errors for pattern analysis."""

    TIMEOUT = "timeout"  # Task exceeded time limit
    CAPABILITY = "capability"  # Agent couldn't handle task
    RESOURCE = "resource"  # Memory, CPU, or other resource issues
    LOGIC = "logic"  # Bug or logic error in handling
    EXTERNAL = "external"  # LLM provider or external service failure
    UNKNOWN = "unknown"  # Uncategorized errors


class PatternType(Enum):
    """Types of learned patterns."""

    ROUTING = "routing"  # Which agent handles task type best
    CONFIDENCE = "confidence"  # Confidence calibration adjustments
    CAPABILITY = "capability"  # Capability-specific performance
    ERROR = "error"  # Recurring error patterns


class ScopeLevel(Enum):
    """Hierarchy levels for pattern scope."""

    AGENT = "agent"
    MANAGER = "manager"
    SPECIALIST = "specialist"


class IssueSeverity(Enum):
    """Severity levels for detected issues."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueType(Enum):
    """Types of detected issues."""

    ANOMALY = "anomaly"  # Unexpected behavior detected
    PATTERN_DECLINE = "pattern_decline"  # Performance declining over time
    ERROR_SPIKE = "error_spike"  # Sudden increase in errors
    CONFIDENCE_DRIFT = "confidence_drift"  # Confidence no longer calibrated
    CAPABILITY_GAP = "capability_gap"  # Missing or failing capability


class IssueStatus(Enum):
    """Status of a learning issue."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class PerformanceTrend(Enum):
    """Performance trend direction."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


@dataclass
class HierarchyPath:
    """
    Path through the agent hierarchy for a task execution.

    Tracks which agent, manager, and specialist handled the task.
    """

    agent: str
    manager: Optional[str] = None
    specialist: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "agent": self.agent,
            "manager": self.manager,
            "specialist": self.specialist,
        }


@dataclass
class TaskOutcomeRecord:
    """
    Complete record of a task outcome.

    Captures all information needed for learning analysis.
    """

    task_id: str
    task_type: str

    # Hierarchy
    agent_code: str
    manager_code: Optional[str] = None
    specialist_code: Optional[str] = None

    # Outcome
    outcome_type: OutcomeType = OutcomeType.SUCCESS
    success: bool = True
    effectiveness: float = 0.0  # 0.0 to 1.0
    duration_ms: float = 0.0

    # Confidence tracking
    initial_confidence: Optional[float] = None
    actual_accuracy: Optional[float] = None

    # Error details (if failed)
    error_category: Optional[ErrorCategory] = None
    error_message: Optional[str] = None
    is_recoverable: bool = True

    # Context
    input_hash: Optional[str] = None
    output_summary: Optional[str] = None
    context_snapshot: Dict[str, Any] = field(default_factory=dict)

    # Pattern attribution (for measuring pattern effectiveness)
    applied_pattern_ids: List[str] = field(default_factory=list)
    was_routing_influenced: bool = False  # Was routing decision influenced by patterns?
    was_confidence_calibrated: bool = False  # Was confidence adjusted by calibration?

    # Metadata
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def confidence_delta(self) -> Optional[float]:
        """Calculate difference between predicted and actual accuracy."""
        if self.initial_confidence is not None and self.actual_accuracy is not None:
            return self.actual_accuracy - self.initial_confidence
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "agent_code": self.agent_code,
            "manager_code": self.manager_code,
            "specialist_code": self.specialist_code,
            "outcome_type": self.outcome_type.value,
            "success": self.success,
            "effectiveness": self.effectiveness,
            "duration_ms": self.duration_ms,
            "initial_confidence": self.initial_confidence,
            "actual_accuracy": self.actual_accuracy,
            "error_category": self.error_category.value if self.error_category else None,
            "error_message": self.error_message,
            "is_recoverable": self.is_recoverable,
            "input_hash": self.input_hash,
            "context_snapshot": self.context_snapshot,
            "applied_pattern_ids": self.applied_pattern_ids,
            "was_routing_influenced": self.was_routing_influenced,
            "was_confidence_calibrated": self.was_confidence_calibrated,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class LearnedPattern:
    """
    A learned pattern that should influence future behavior.

    Patterns are detected from outcome analysis and applied during
    task routing and execution.
    """

    pattern_type: PatternType
    scope_level: ScopeLevel
    scope_code: str  # Agent code (Forge, AM, SD, etc.)

    # Pattern definition
    condition_json: str  # JSON conditions when pattern applies
    recommendation: str

    # Metrics
    confidence: float = 0.5
    sample_size: int = 0
    success_rate: Optional[float] = None
    avg_improvement: Optional[float] = None

    # Adjustments to apply
    confidence_adjustment: float = 0.0
    priority_adjustment: int = 0
    routing_preference: Optional[str] = None  # Preferred agent code

    # Lifecycle
    is_active: bool = True
    last_applied_at: Optional[datetime] = None
    application_count: int = 0
    expires_at: Optional[datetime] = None

    # Validation
    validated_by: Optional[str] = None  # "human", "automated", or None
    validation_score: Optional[float] = None

    # Metadata
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pattern_type": self.pattern_type.value,
            "scope_level": self.scope_level.value,
            "scope_code": self.scope_code,
            "condition_json": self.condition_json,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "sample_size": self.sample_size,
            "success_rate": self.success_rate,
            "confidence_adjustment": self.confidence_adjustment,
            "priority_adjustment": self.priority_adjustment,
            "routing_preference": self.routing_preference,
            "is_active": self.is_active,
            "last_applied_at": self.last_applied_at.isoformat() if self.last_applied_at else None,
            "application_count": self.application_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class LearningIssue:
    """
    A detected issue that needs investigation or action.

    Issues are automatically created when the learning system detects
    problems like declining performance or error spikes.
    """

    issue_type: IssueType
    severity: IssueSeverity
    priority: int  # 1-10, for task queue (1 = highest)

    # Source
    source_agent_code: str
    source_level: ScopeLevel
    detected_pattern_id: Optional[str] = None

    # Issue details
    title: str = ""
    description: str = ""
    evidence_json: Optional[str] = None  # JSON array of evidence
    suggested_action: Optional[str] = None

    # Task queue integration
    task_id: Optional[str] = None  # Created task ID
    task_created_at: Optional[datetime] = None

    # Lifecycle
    status: IssueStatus = IssueStatus.OPEN
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

    # Metadata
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "priority": self.priority,
            "source_agent_code": self.source_agent_code,
            "source_level": self.source_level.value,
            "detected_pattern_id": self.detected_pattern_id,
            "title": self.title,
            "description": self.description,
            "evidence_json": self.evidence_json,
            "suggested_action": self.suggested_action,
            "task_id": self.task_id,
            "status": self.status.value,
            "resolution": self.resolution,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AgentPerformance:
    """
    Rolling performance metrics for an agent.

    Tracks aggregate performance over a sliding window.
    """

    agent_code: str
    agent_level: ScopeLevel
    parent_code: Optional[str] = None

    # Performance metrics
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_duration_ms: float = 0.0

    # Task type success rates (JSON: {task_type: rate})
    task_type_success_rates: Dict[str, float] = field(default_factory=dict)

    # Confidence calibration
    avg_confidence: float = 0.5
    avg_actual_accuracy: float = 0.5
    confidence_calibration_score: float = 0.0

    # Trend
    performance_trend: PerformanceTrend = PerformanceTrend.STABLE
    trend_magnitude: float = 0.0

    # Health
    health_score: float = 1.0
    consecutive_failures: int = 0
    last_failure_at: Optional[datetime] = None
    circuit_breaker_open: bool = False

    # Window
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "agent_level": self.agent_level.value,
            "parent_code": self.parent_code,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "avg_confidence": self.avg_confidence,
            "avg_actual_accuracy": self.avg_actual_accuracy,
            "performance_trend": self.performance_trend.value,
            "health_score": self.health_score,
            "consecutive_failures": self.consecutive_failures,
            "circuit_breaker_open": self.circuit_breaker_open,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class LearningAdjustment:
    """
    Adjustments to apply based on learned patterns.

    Returned by learning loops to influence task routing and execution.
    """

    # Routing adjustments
    preferred_route: Optional[str] = None
    routing_confidence: float = 0.0
    avoid_routes: List[str] = field(default_factory=list)

    # Confidence adjustments
    confidence_adjustment: float = 0.0

    # Priority adjustments
    priority_adjustment: int = 0

    # Hints and warnings
    effectiveness_hints: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Applied patterns (for tracking)
    applied_pattern_ids: List[str] = field(default_factory=list)

    def merge(self, other: "LearningAdjustment") -> None:
        """Merge another adjustment into this one."""
        # Take preferred route if more confident
        if other.routing_confidence > self.routing_confidence:
            self.preferred_route = other.preferred_route
            self.routing_confidence = other.routing_confidence

        # Accumulate adjustments
        self.confidence_adjustment += other.confidence_adjustment
        self.priority_adjustment += other.priority_adjustment

        # Merge lists
        self.avoid_routes.extend(other.avoid_routes)
        self.effectiveness_hints.extend(other.effectiveness_hints)
        self.warnings.extend(other.warnings)
        self.applied_pattern_ids.extend(other.applied_pattern_ids)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        if warning not in self.warnings:
            self.warnings.append(warning)

    def clamp(self) -> None:
        """Clamp adjustments to reasonable bounds."""
        self.confidence_adjustment = max(-0.3, min(0.3, self.confidence_adjustment))
        self.priority_adjustment = max(-3, min(3, self.priority_adjustment))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preferred_route": self.preferred_route,
            "routing_confidence": self.routing_confidence,
            "avoid_routes": self.avoid_routes,
            "confidence_adjustment": self.confidence_adjustment,
            "priority_adjustment": self.priority_adjustment,
            "effectiveness_hints": self.effectiveness_hints,
            "warnings": self.warnings,
            "applied_pattern_ids": self.applied_pattern_ids,
        }
