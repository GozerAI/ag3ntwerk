"""
Failure Investigator - Automatic root cause analysis for failures.

Analyzes failure patterns to identify root causes, correlations,
and recommend fixes. Enables the system to learn from failures
and prevent recurrence.
"""

import json
import logging
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from ag3ntwerk.learning.models import (
    TaskOutcomeRecord,
    HierarchyPath,
)

if TYPE_CHECKING:
    from ag3ntwerk.learning.outcome_tracker import OutcomeTracker
    from ag3ntwerk.learning.pattern_store import PatternStore

logger = logging.getLogger(__name__)


class RootCauseType(Enum):
    """Types of root causes."""

    RESOURCE_EXHAUSTION = "resource_exhaustion"
    TIMEOUT = "timeout"
    DEPENDENCY_FAILURE = "dependency_failure"
    CONFIGURATION_ERROR = "configuration_error"
    INPUT_VALIDATION = "input_validation"
    STATE_CORRUPTION = "state_corruption"
    CAPACITY_LIMIT = "capacity_limit"
    EXTERNAL_SERVICE = "external_service"
    RACE_CONDITION = "race_condition"
    UNKNOWN = "unknown"


class CorrelationType(Enum):
    """Types of correlations found."""

    TEMPORAL = "temporal"  # Happens at certain times
    SEQUENTIAL = "sequential"  # Follows certain events
    LOAD_RELATED = "load_related"  # Related to system load
    AGENT_SPECIFIC = "agent_specific"  # Specific to certain agents
    TASK_TYPE_SPECIFIC = "task_type_specific"  # Specific to task types


class InvestigationStatus(Enum):
    """Status of an investigation."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    INCONCLUSIVE = "inconclusive"
    ACTION_REQUIRED = "action_required"


@dataclass
class RootCause:
    """
    An identified root cause for a failure.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cause_type: RootCauseType = RootCauseType.UNKNOWN
    description: str = ""
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    affected_outcomes: int = 0
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cause_type": self.cause_type.value,
            "description": self.description,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "affected_outcomes": self.affected_outcomes,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }


@dataclass
class Correlation:
    """
    A correlation found between failure and some factor.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_type: CorrelationType = CorrelationType.TEMPORAL
    factor: str = ""
    factor_value: Any = None
    correlation_strength: float = 0.0  # 0.0-1.0
    sample_size: int = 0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "correlation_type": self.correlation_type.value,
            "factor": self.factor,
            "factor_value": self.factor_value,
            "correlation_strength": self.correlation_strength,
            "sample_size": self.sample_size,
            "description": self.description,
        }


@dataclass
class RecommendedFix:
    """
    A recommended fix for a root cause.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    root_cause_id: str = ""
    fix_type: str = ""
    description: str = ""
    implementation_steps: List[str] = field(default_factory=list)
    estimated_impact: float = 0.0  # Expected improvement
    priority: int = 0  # 1 = highest
    auto_applicable: bool = False  # Can be applied automatically

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "root_cause_id": self.root_cause_id,
            "fix_type": self.fix_type,
            "description": self.description,
            "implementation_steps": self.implementation_steps,
            "estimated_impact": self.estimated_impact,
            "priority": self.priority,
            "auto_applicable": self.auto_applicable,
        }


@dataclass
class Investigation:
    """
    Complete investigation of a failure.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    outcome_id: str = ""
    task_type: str = ""
    agent_code: str = ""
    status: InvestigationStatus = InvestigationStatus.IN_PROGRESS
    root_causes: List[RootCause] = field(default_factory=list)
    correlations: List[Correlation] = field(default_factory=list)
    recommended_fixes: List[RecommendedFix] = field(default_factory=list)
    similar_failures_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "outcome_id": self.outcome_id,
            "task_type": self.task_type,
            "agent_code": self.agent_code,
            "status": self.status.value,
            "root_causes": [rc.to_dict() for rc in self.root_causes],
            "correlations": [c.to_dict() for c in self.correlations],
            "recommended_fixes": [rf.to_dict() for rf in self.recommended_fixes],
            "similar_failures_count": self.similar_failures_count,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "summary": self.summary,
        }


class FailureInvestigator:
    """
    Automatic root cause analysis for failures.

    Analyzes failure patterns, identifies root causes,
    finds correlations, and suggests fixes.
    """

    # Thresholds
    MIN_SIMILAR_FAILURES = 3  # Min failures to identify pattern
    CORRELATION_THRESHOLD = 0.5  # Min correlation strength
    HIGH_CONFIDENCE_THRESHOLD = 0.7

    # Error pattern keywords
    ERROR_PATTERNS = {
        RootCauseType.TIMEOUT: ["timeout", "timed out", "deadline exceeded", "too slow"],
        RootCauseType.RESOURCE_EXHAUSTION: ["memory", "oom", "out of memory", "heap", "disk full"],
        RootCauseType.DEPENDENCY_FAILURE: [
            "connection",
            "refused",
            "unavailable",
            "unreachable",
            "dns",
        ],
        RootCauseType.CONFIGURATION_ERROR: [
            "config",
            "invalid setting",
            "missing required",
            "malformed",
        ],
        RootCauseType.INPUT_VALIDATION: [
            "invalid input",
            "validation failed",
            "schema",
            "parse error",
        ],
        RootCauseType.CAPACITY_LIMIT: ["rate limit", "quota", "exceeded", "throttle", "max"],
        RootCauseType.EXTERNAL_SERVICE: ["api error", "503", "502", "gateway", "upstream"],
        RootCauseType.STATE_CORRUPTION: ["corrupt", "inconsistent", "integrity", "state error"],
        RootCauseType.RACE_CONDITION: ["concurrent", "race", "deadlock", "lock timeout"],
    }

    def __init__(
        self,
        db: Any,
        outcome_tracker: "OutcomeTracker",
        pattern_store: Optional["PatternStore"] = None,
    ):
        """
        Initialize the failure investigator.

        Args:
            db: Database connection
            outcome_tracker: OutcomeTracker for accessing outcomes
            pattern_store: Optional PatternStore for pattern creation
        """
        self._db = db
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store

        # Caches
        self._investigations: Dict[str, Investigation] = {}
        self._root_cause_cache: Dict[str, List[RootCause]] = {}  # task_type -> causes

    async def investigate_failure(
        self,
        outcome: TaskOutcomeRecord,
    ) -> Investigation:
        """
        Investigate a specific failure.

        Args:
            outcome: The failed outcome to investigate

        Returns:
            Investigation with root causes, correlations, and fixes
        """
        investigation = Investigation(
            outcome_id=outcome.task_id,
            task_type=outcome.task_type,
            agent_code=outcome.agent_code,
        )

        # Step 1: Gather similar failures
        similar_failures = await self._get_similar_failures(outcome)
        investigation.similar_failures_count = len(similar_failures)

        # Step 2: Get context
        agent_state = await self._get_agent_state(outcome.agent_code)
        system_state = await self._get_system_state(outcome.created_at)

        # Step 3: Identify root causes
        root_causes = self._identify_root_causes(outcome, similar_failures)
        investigation.root_causes = root_causes

        # Step 4: Find correlations
        correlations = self._find_correlations(outcome, similar_failures, system_state)
        investigation.correlations = correlations

        # Step 5: Suggest fixes
        fixes = self._suggest_fixes(root_causes, correlations)
        investigation.recommended_fixes = fixes

        # Step 6: Generate summary
        investigation.summary = self._generate_summary(investigation)
        investigation.status = InvestigationStatus.COMPLETED
        investigation.completed_at = datetime.now(timezone.utc)

        # Store investigation
        self._investigations[investigation.id] = investigation
        await self._persist_investigation(investigation)

        logger.info(
            f"Completed investigation {investigation.id}: "
            f"{len(root_causes)} root causes, {len(fixes)} fixes"
        )

        return investigation

    async def investigate_batch(
        self,
        window_hours: int = 24,
        min_failure_rate: float = 0.1,
    ) -> List[Investigation]:
        """
        Investigate failures in batch.

        Args:
            window_hours: Time window to analyze
            min_failure_rate: Minimum failure rate to trigger investigation

        Returns:
            List of investigations
        """
        investigations: List[Investigation] = []

        # Group failures by task type
        failures_by_type = await self._group_failures_by_type(window_hours)

        for task_type, failures in failures_by_type.items():
            if len(failures) < self.MIN_SIMILAR_FAILURES:
                continue

            # Create aggregate investigation
            investigation = await self._investigate_failure_group(task_type, failures)
            if investigation:
                investigations.append(investigation)

        return investigations

    async def _get_similar_failures(
        self,
        outcome: TaskOutcomeRecord,
        window_hours: int = 168,
        limit: int = 100,
    ) -> List[TaskOutcomeRecord]:
        """Get failures similar to the given outcome."""
        try:
            rows = await self._db.fetch_all(
                """
                SELECT * FROM task_outcomes
                WHERE task_type = ?
                  AND success = 0
                  AND created_at >= datetime('now', ?)
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (outcome.task_type, f"-{window_hours} hours", limit),
            )

            failures = []
            for row in rows:
                failures.append(self._row_to_outcome(row))

            return failures

        except Exception as e:
            logger.warning(f"Failed to get similar failures: {e}")
            return []

    async def _get_agent_state(self, agent_code: str) -> Dict[str, Any]:
        """Get the current state of an agent."""
        state: Dict[str, Any] = {
            "agent_code": agent_code,
            "recent_failures": 0,
            "recent_success_rate": 0.0,
            "avg_duration_ms": 0.0,
        }

        try:
            row = await self._db.fetch_one(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failures,
                    AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                    AVG(duration_ms) as avg_duration
                FROM task_outcomes
                WHERE (agent_code = ? OR manager_code = ? OR specialist_code = ?)
                  AND created_at >= datetime('now', '-24 hours')
                """,
                (agent_code, agent_code, agent_code),
            )

            if row:
                state["recent_failures"] = row[1] or 0
                state["recent_success_rate"] = row[2] or 0.0
                state["avg_duration_ms"] = row[3] or 0.0

        except Exception as e:
            logger.warning(f"Failed to get agent state: {e}")

        return state

    async def _get_system_state(
        self,
        at_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get system state at a point in time."""
        state: Dict[str, Any] = {
            "timestamp": (at_time or datetime.now(timezone.utc)).isoformat(),
            "active_tasks": 0,
            "failure_rate_1h": 0.0,
            "avg_queue_time_ms": 0.0,
        }

        try:
            # Get system metrics around the time
            time_str = at_time.isoformat() if at_time else "now"

            row = await self._db.fetch_one(
                """
                SELECT
                    COUNT(*) as total,
                    AVG(CASE WHEN success = 0 THEN 1.0 ELSE 0.0 END) as failure_rate
                FROM task_outcomes
                WHERE created_at BETWEEN datetime(?, '-1 hour') AND datetime(?, '+1 hour')
                """,
                (time_str, time_str),
            )

            if row:
                state["active_tasks"] = row[0] or 0
                state["failure_rate_1h"] = row[1] or 0.0

        except Exception as e:
            logger.warning(f"Failed to get system state: {e}")

        return state

    def _identify_root_causes(
        self,
        outcome: TaskOutcomeRecord,
        similar_failures: List[TaskOutcomeRecord],
    ) -> List[RootCause]:
        """Identify root causes from failure patterns."""
        root_causes: List[RootCause] = []
        error_messages = [outcome.error_message or ""]
        error_messages.extend([f.error_message or "" for f in similar_failures])

        # Analyze error patterns
        cause_counts: Dict[RootCauseType, int] = Counter()
        cause_evidence: Dict[RootCauseType, List[str]] = {}

        for error in error_messages:
            if not error:
                continue

            error_lower = error.lower()

            for cause_type, keywords in self.ERROR_PATTERNS.items():
                if any(kw in error_lower for kw in keywords):
                    cause_counts[cause_type] += 1
                    if cause_type not in cause_evidence:
                        cause_evidence[cause_type] = []
                    if len(cause_evidence[cause_type]) < 5:
                        cause_evidence[cause_type].append(error[:200])

        # Create root cause objects
        total_errors = len([e for e in error_messages if e])

        for cause_type, count in cause_counts.most_common():
            if count >= self.MIN_SIMILAR_FAILURES:
                confidence = min(1.0, count / total_errors) if total_errors > 0 else 0.0

                root_cause = RootCause(
                    cause_type=cause_type,
                    description=self._describe_root_cause(cause_type),
                    confidence=confidence,
                    evidence=cause_evidence.get(cause_type, []),
                    affected_outcomes=count,
                )
                root_causes.append(root_cause)

        # If no patterns found, add UNKNOWN
        if not root_causes:
            root_causes.append(
                RootCause(
                    cause_type=RootCauseType.UNKNOWN,
                    description="Unable to determine specific root cause",
                    confidence=0.3,
                    evidence=error_messages[:3] if error_messages else [],
                    affected_outcomes=len(similar_failures) + 1,
                )
            )

        return root_causes

    def _find_correlations(
        self,
        outcome: TaskOutcomeRecord,
        similar_failures: List[TaskOutcomeRecord],
        system_state: Dict[str, Any],
    ) -> List[Correlation]:
        """Find correlations between failures and various factors."""
        correlations: List[Correlation] = []
        all_failures = [outcome] + similar_failures

        # Temporal correlation - check if failures cluster at certain times
        temporal = self._find_temporal_correlation(all_failures)
        if temporal:
            correlations.append(temporal)

        # Agent-specific correlation
        agent_corr = self._find_agent_correlation(all_failures)
        if agent_corr:
            correlations.append(agent_corr)

        # Load-related correlation
        load_corr = self._find_load_correlation(all_failures, system_state)
        if load_corr:
            correlations.append(load_corr)

        return correlations

    def _find_temporal_correlation(
        self,
        failures: List[TaskOutcomeRecord],
    ) -> Optional[Correlation]:
        """Find temporal patterns in failures."""
        if len(failures) < 3:
            return None

        # Check for hour-of-day pattern
        hour_counts: Dict[int, int] = Counter()
        for f in failures:
            if f.created_at:
                hour_counts[f.created_at.hour] += 1

        if not hour_counts:
            return None

        # Find peak hour
        peak_hour, peak_count = hour_counts.most_common(1)[0]
        total = sum(hour_counts.values())

        # Check if significantly concentrated
        concentration = peak_count / total if total > 0 else 0

        if concentration > 0.3:  # 30% at one hour is significant
            return Correlation(
                correlation_type=CorrelationType.TEMPORAL,
                factor="hour_of_day",
                factor_value=peak_hour,
                correlation_strength=concentration,
                sample_size=total,
                description=f"Failures concentrated at hour {peak_hour:02d}:00",
            )

        return None

    def _find_agent_correlation(
        self,
        failures: List[TaskOutcomeRecord],
    ) -> Optional[Correlation]:
        """Find agent-specific failure patterns."""
        if len(failures) < 3:
            return None

        agent_counts: Dict[str, int] = Counter()
        for f in failures:
            agent = f.specialist_code or f.manager_code or f.agent_code
            if agent:
                agent_counts[agent] += 1

        if not agent_counts:
            return None

        # Find most affected agent
        top_agent, top_count = agent_counts.most_common(1)[0]
        total = sum(agent_counts.values())
        concentration = top_count / total if total > 0 else 0

        if concentration > 0.5:  # 50% from one agent
            return Correlation(
                correlation_type=CorrelationType.AGENT_SPECIFIC,
                factor="agent",
                factor_value=top_agent,
                correlation_strength=concentration,
                sample_size=total,
                description=f"Most failures ({concentration:.0%}) from agent {top_agent}",
            )

        return None

    def _find_load_correlation(
        self,
        failures: List[TaskOutcomeRecord],
        system_state: Dict[str, Any],
    ) -> Optional[Correlation]:
        """Find load-related failure patterns."""
        high_load_threshold = 0.3  # 30% failure rate = high load

        failure_rate = system_state.get("failure_rate_1h", 0.0)

        if failure_rate > high_load_threshold:
            return Correlation(
                correlation_type=CorrelationType.LOAD_RELATED,
                factor="system_failure_rate",
                factor_value=failure_rate,
                correlation_strength=min(1.0, failure_rate / 0.5),
                sample_size=system_state.get("active_tasks", 0),
                description=f"System under high load ({failure_rate:.0%} failure rate)",
            )

        return None

    def _suggest_fixes(
        self,
        root_causes: List[RootCause],
        correlations: List[Correlation],
    ) -> List[RecommendedFix]:
        """Suggest fixes based on root causes and correlations."""
        fixes: List[RecommendedFix] = []

        for i, cause in enumerate(root_causes):
            fix = self._create_fix_for_cause(cause, priority=i + 1)
            if fix:
                fixes.append(fix)

        # Add fixes based on correlations
        for corr in correlations:
            fix = self._create_fix_for_correlation(corr)
            if fix:
                fix.priority = len(root_causes) + 1
                fixes.append(fix)

        return fixes

    def _create_fix_for_cause(
        self,
        cause: RootCause,
        priority: int,
    ) -> Optional[RecommendedFix]:
        """Create a fix recommendation for a root cause."""
        fix_templates: Dict[RootCauseType, Dict[str, Any]] = {
            RootCauseType.TIMEOUT: {
                "fix_type": "configuration",
                "description": "Increase timeout limits or optimize slow operations",
                "steps": [
                    "Review current timeout settings",
                    "Identify slowest operations from logs",
                    "Either increase timeout or optimize the slow operations",
                    "Add timeout-specific retry logic",
                ],
                "impact": 0.7,
                "auto": True,
            },
            RootCauseType.RESOURCE_EXHAUSTION: {
                "fix_type": "scaling",
                "description": "Increase resource allocation or optimize memory usage",
                "steps": [
                    "Monitor memory usage patterns",
                    "Identify memory-intensive operations",
                    "Increase allocation or add cleanup logic",
                    "Consider implementing resource pooling",
                ],
                "impact": 0.8,
                "auto": False,
            },
            RootCauseType.DEPENDENCY_FAILURE: {
                "fix_type": "resilience",
                "description": "Add circuit breaker and fallback mechanisms",
                "steps": [
                    "Identify failing dependencies",
                    "Implement circuit breaker pattern",
                    "Add fallback responses where possible",
                    "Improve connection pool settings",
                ],
                "impact": 0.6,
                "auto": True,
            },
            RootCauseType.CONFIGURATION_ERROR: {
                "fix_type": "validation",
                "description": "Add configuration validation and defaults",
                "steps": [
                    "Review configuration schema",
                    "Add validation at startup",
                    "Provide sensible defaults",
                    "Log configuration issues clearly",
                ],
                "impact": 0.9,
                "auto": True,
            },
            RootCauseType.INPUT_VALIDATION: {
                "fix_type": "validation",
                "description": "Improve input validation and error messages",
                "steps": [
                    "Review input schemas",
                    "Add comprehensive validation",
                    "Provide clear error messages",
                    "Add input sanitization",
                ],
                "impact": 0.8,
                "auto": True,
            },
            RootCauseType.CAPACITY_LIMIT: {
                "fix_type": "rate_limiting",
                "description": "Implement rate limiting and queue management",
                "steps": [
                    "Review current capacity limits",
                    "Implement request queuing",
                    "Add backoff and retry logic",
                    "Consider scaling or quota increases",
                ],
                "impact": 0.7,
                "auto": True,
            },
            RootCauseType.EXTERNAL_SERVICE: {
                "fix_type": "resilience",
                "description": "Add retry logic and fallbacks for external services",
                "steps": [
                    "Implement exponential backoff",
                    "Add circuit breaker",
                    "Cache responses where possible",
                    "Monitor external service health",
                ],
                "impact": 0.6,
                "auto": True,
            },
        }

        template = fix_templates.get(cause.cause_type)
        if not template:
            return None

        return RecommendedFix(
            root_cause_id=cause.id,
            fix_type=template["fix_type"],
            description=template["description"],
            implementation_steps=template["steps"],
            estimated_impact=template["impact"] * cause.confidence,
            priority=priority,
            auto_applicable=template["auto"],
        )

    def _create_fix_for_correlation(
        self,
        correlation: Correlation,
    ) -> Optional[RecommendedFix]:
        """Create a fix recommendation based on a correlation."""
        if correlation.correlation_type == CorrelationType.TEMPORAL:
            return RecommendedFix(
                fix_type="scheduling",
                description=f"Review scheduled tasks around hour {correlation.factor_value}",
                implementation_steps=[
                    f"Check what processes run at hour {correlation.factor_value}",
                    "Consider rescheduling or staggering workloads",
                    "Add monitoring for this time period",
                ],
                estimated_impact=0.5,
                auto_applicable=False,
            )

        if correlation.correlation_type == CorrelationType.AGENT_SPECIFIC:
            return RecommendedFix(
                fix_type="agent_review",
                description=f"Review configuration and health of agent {correlation.factor_value}",
                implementation_steps=[
                    f"Check agent {correlation.factor_value} logs and metrics",
                    "Review agent configuration",
                    "Consider rebalancing load",
                    "Check for agent-specific issues",
                ],
                estimated_impact=0.6,
                auto_applicable=False,
            )

        if correlation.correlation_type == CorrelationType.LOAD_RELATED:
            return RecommendedFix(
                fix_type="scaling",
                description="System appears overloaded - consider scaling",
                implementation_steps=[
                    "Review current capacity",
                    "Identify bottlenecks",
                    "Consider horizontal scaling",
                    "Implement load shedding if needed",
                ],
                estimated_impact=0.7,
                auto_applicable=False,
            )

        return None

    def _describe_root_cause(self, cause_type: RootCauseType) -> str:
        """Generate a description for a root cause type."""
        descriptions = {
            RootCauseType.TIMEOUT: "Operations timing out before completion",
            RootCauseType.RESOURCE_EXHAUSTION: "System running out of memory or other resources",
            RootCauseType.DEPENDENCY_FAILURE: "Dependent services failing or unavailable",
            RootCauseType.CONFIGURATION_ERROR: "Incorrect or missing configuration",
            RootCauseType.INPUT_VALIDATION: "Invalid input data causing failures",
            RootCauseType.CAPACITY_LIMIT: "Rate limits or quotas being exceeded",
            RootCauseType.EXTERNAL_SERVICE: "External API or service errors",
            RootCauseType.STATE_CORRUPTION: "Data or state corruption issues",
            RootCauseType.RACE_CONDITION: "Concurrent access causing conflicts",
            RootCauseType.UNKNOWN: "Root cause not determined",
        }
        return descriptions.get(cause_type, "Unknown cause")

    def _generate_summary(self, investigation: Investigation) -> str:
        """Generate a summary of the investigation."""
        parts = []

        if investigation.root_causes:
            top_cause = investigation.root_causes[0]
            parts.append(
                f"Primary root cause: {top_cause.cause_type.value} "
                f"({top_cause.confidence:.0%} confidence)"
            )

        if investigation.similar_failures_count > 0:
            parts.append(f"Found {investigation.similar_failures_count} similar failures")

        if investigation.recommended_fixes:
            parts.append(
                f"Recommended {len(investigation.recommended_fixes)} fix(es), "
                f"{sum(1 for f in investigation.recommended_fixes if f.auto_applicable)} auto-applicable"
            )

        return ". ".join(parts) if parts else "Investigation complete"

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_outcome(self, row: Dict[str, Any]) -> TaskOutcomeRecord:
        """Convert a database row to TaskOutcomeRecord."""
        return TaskOutcomeRecord(
            task_id=row.get("task_id", ""),
            task_type=row.get("task_type", ""),
            agent_code=row.get("agent_code", ""),
            manager_code=row.get("manager_code"),
            specialist_code=row.get("specialist_code"),
            success=bool(row.get("success", False)),
            effectiveness=row.get("effectiveness"),
            duration_ms=row.get("duration_ms", 0.0),
            error_message=row.get("error"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
        )

    async def _group_failures_by_type(
        self,
        window_hours: int,
    ) -> Dict[str, List[TaskOutcomeRecord]]:
        """Group failures by task type."""
        groups: Dict[str, List[TaskOutcomeRecord]] = {}

        try:
            rows = await self._db.fetch_all(
                """
                SELECT * FROM task_outcomes
                WHERE success = 0
                  AND created_at >= datetime('now', ?)
                ORDER BY task_type, created_at DESC
                """,
                (f"-{window_hours} hours",),
            )

            for row in rows:
                outcome = self._row_to_outcome(row)
                if outcome.task_type not in groups:
                    groups[outcome.task_type] = []
                groups[outcome.task_type].append(outcome)

        except Exception as e:
            logger.warning(f"Failed to group failures: {e}")

        return groups

    async def _investigate_failure_group(
        self,
        task_type: str,
        failures: List[TaskOutcomeRecord],
    ) -> Optional[Investigation]:
        """Investigate a group of failures for a task type."""
        if not failures:
            return None

        # Use first failure as reference
        investigation = Investigation(
            outcome_id=f"group_{task_type}",
            task_type=task_type,
            agent_code=failures[0].agent_code,
            similar_failures_count=len(failures),
        )

        # Analyze the group
        system_state = await self._get_system_state()
        root_causes = self._identify_root_causes(failures[0], failures[1:])
        correlations = self._find_correlations(failures[0], failures[1:], system_state)
        fixes = self._suggest_fixes(root_causes, correlations)

        investigation.root_causes = root_causes
        investigation.correlations = correlations
        investigation.recommended_fixes = fixes
        investigation.summary = self._generate_summary(investigation)
        investigation.status = InvestigationStatus.COMPLETED
        investigation.completed_at = datetime.now(timezone.utc)

        self._investigations[investigation.id] = investigation
        await self._persist_investigation(investigation)

        return investigation

    # =========================================================================
    # Query Methods
    # =========================================================================

    async def get_investigation(
        self,
        investigation_id: str,
    ) -> Optional[Investigation]:
        """Get an investigation by ID."""
        return self._investigations.get(investigation_id)

    async def get_investigations(
        self,
        task_type: Optional[str] = None,
        status: Optional[InvestigationStatus] = None,
        limit: int = 100,
    ) -> List[Investigation]:
        """Get investigations with optional filters."""
        investigations = []

        for inv in self._investigations.values():
            if task_type and inv.task_type != task_type:
                continue
            if status and inv.status != status:
                continue
            investigations.append(inv)

        # Sort by creation time descending
        investigations.sort(key=lambda i: i.created_at, reverse=True)

        return investigations[:limit]

    async def get_common_root_causes(
        self,
        window_hours: int = 168,
        limit: int = 10,
    ) -> List[Tuple[RootCauseType, int, float]]:
        """
        Get the most common root causes.

        Returns:
            List of (cause_type, count, avg_confidence) tuples
        """
        cause_stats: Dict[RootCauseType, Dict[str, Any]] = {}

        for inv in self._investigations.values():
            if (datetime.now(timezone.utc) - inv.created_at).total_seconds() > window_hours * 3600:
                continue

            for cause in inv.root_causes:
                if cause.cause_type not in cause_stats:
                    cause_stats[cause.cause_type] = {"count": 0, "total_confidence": 0.0}

                cause_stats[cause.cause_type]["count"] += 1
                cause_stats[cause.cause_type]["total_confidence"] += cause.confidence

        results = [
            (
                cause_type,
                stats["count"],
                stats["total_confidence"] / stats["count"] if stats["count"] > 0 else 0.0,
            )
            for cause_type, stats in cause_stats.items()
        ]

        results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    async def get_auto_applicable_fixes(self) -> List[RecommendedFix]:
        """Get all auto-applicable fixes from recent investigations."""
        fixes = []

        for inv in self._investigations.values():
            for fix in inv.recommended_fixes:
                if fix.auto_applicable:
                    fixes.append(fix)

        # Sort by estimated impact
        fixes.sort(key=lambda f: f.estimated_impact, reverse=True)

        return fixes

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Get investigator statistics."""
        status_counts: Dict[str, int] = Counter()
        cause_counts: Dict[str, int] = Counter()

        for inv in self._investigations.values():
            status_counts[inv.status.value] += 1
            for cause in inv.root_causes:
                cause_counts[cause.cause_type.value] += 1

        return {
            "total_investigations": len(self._investigations),
            "by_status": dict(status_counts),
            "by_root_cause": dict(cause_counts),
            "auto_applicable_fixes": len(await self.get_auto_applicable_fixes()),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    async def _persist_investigation(self, investigation: Investigation) -> None:
        """Persist an investigation to the database."""
        try:
            await self._db.execute(
                """
                INSERT OR REPLACE INTO failure_investigations (
                    id, outcome_id, task_type, agent_code, status,
                    root_causes, correlations, recommended_fixes,
                    similar_failures_count, created_at, completed_at, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    investigation.id,
                    investigation.outcome_id,
                    investigation.task_type,
                    investigation.agent_code,
                    investigation.status.value,
                    json.dumps([rc.to_dict() for rc in investigation.root_causes]),
                    json.dumps([c.to_dict() for c in investigation.correlations]),
                    json.dumps([rf.to_dict() for rf in investigation.recommended_fixes]),
                    investigation.similar_failures_count,
                    investigation.created_at.isoformat(),
                    investigation.completed_at.isoformat() if investigation.completed_at else None,
                    investigation.summary,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to persist investigation: {e}")

    async def load_investigations(self, limit: int = 100) -> int:
        """Load investigations from the database."""
        try:
            rows = await self._db.fetch_all(
                """
                SELECT * FROM failure_investigations
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )

            for row in rows:
                investigation = Investigation(
                    id=row["id"],
                    outcome_id=row["outcome_id"],
                    task_type=row["task_type"],
                    agent_code=row["agent_code"],
                    status=InvestigationStatus(row["status"]),
                    root_causes=self._parse_root_causes(row.get("root_causes", "[]")),
                    correlations=self._parse_correlations(row.get("correlations", "[]")),
                    recommended_fixes=self._parse_fixes(row.get("recommended_fixes", "[]")),
                    similar_failures_count=row.get("similar_failures_count", 0),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    completed_at=(
                        datetime.fromisoformat(row["completed_at"])
                        if row.get("completed_at")
                        else None
                    ),
                    summary=row.get("summary", ""),
                )
                self._investigations[investigation.id] = investigation

            return len(rows)

        except Exception as e:
            logger.warning(f"Failed to load investigations: {e}")
            return 0

    def _parse_root_causes(self, data: str) -> List[RootCause]:
        """Parse root causes from JSON."""
        try:
            items = json.loads(data)
            return [
                RootCause(
                    id=item.get("id", str(uuid.uuid4())),
                    cause_type=RootCauseType(item.get("cause_type", "unknown")),
                    description=item.get("description", ""),
                    confidence=item.get("confidence", 0.0),
                    evidence=item.get("evidence", []),
                    affected_outcomes=item.get("affected_outcomes", 0),
                )
                for item in items
            ]
        except (json.JSONDecodeError, TypeError):
            return []

    def _parse_correlations(self, data: str) -> List[Correlation]:
        """Parse correlations from JSON."""
        try:
            items = json.loads(data)
            return [
                Correlation(
                    id=item.get("id", str(uuid.uuid4())),
                    correlation_type=CorrelationType(item.get("correlation_type", "temporal")),
                    factor=item.get("factor", ""),
                    factor_value=item.get("factor_value"),
                    correlation_strength=item.get("correlation_strength", 0.0),
                    sample_size=item.get("sample_size", 0),
                    description=item.get("description", ""),
                )
                for item in items
            ]
        except (json.JSONDecodeError, TypeError):
            return []

    def _parse_fixes(self, data: str) -> List[RecommendedFix]:
        """Parse fixes from JSON."""
        try:
            items = json.loads(data)
            return [
                RecommendedFix(
                    id=item.get("id", str(uuid.uuid4())),
                    root_cause_id=item.get("root_cause_id", ""),
                    fix_type=item.get("fix_type", ""),
                    description=item.get("description", ""),
                    implementation_steps=item.get("implementation_steps", []),
                    estimated_impact=item.get("estimated_impact", 0.0),
                    priority=item.get("priority", 0),
                    auto_applicable=item.get("auto_applicable", False),
                )
                for item in items
            ]
        except (json.JSONDecodeError, TypeError):
            return []
