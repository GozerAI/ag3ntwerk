"""
Opportunity Detector - Identifies improvement opportunities across the system.

Proactively analyzes the learning system to find:
1. Capability gaps where agents underperform
2. Workflow optimization opportunities
3. Pattern coverage gaps
4. Resource utilization improvements
5. Training needs for agents
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class OpportunityType(Enum):
    """Types of improvement opportunities."""

    CAPABILITY_GAP = "capability_gap"  # Agent underperforms on certain tasks
    WORKFLOW_OPTIMIZATION = "workflow_optimization"  # Process can be improved
    PATTERN_COVERAGE = "pattern_coverage"  # Need more patterns for task type
    RESOURCE_REBALANCING = "resource_rebalancing"  # Uneven load distribution
    TRAINING_NEED = "training_need"  # Agent needs calibration/training
    ERROR_PREVENTION = "error_prevention"  # Recurring errors can be prevented
    HANDLER_OPPORTUNITY = "handler_opportunity"  # Task type could use auto-handler


class OpportunityPriority(Enum):
    """Priority levels for opportunities."""

    CRITICAL = "critical"  # Immediate attention needed
    HIGH = "high"  # Should address soon
    MEDIUM = "medium"  # Address when convenient
    LOW = "low"  # Nice to have


@dataclass
class Opportunity:
    """An improvement opportunity detected by the system."""

    id: str = field(default_factory=lambda: str(uuid4()))
    opportunity_type: OpportunityType = OpportunityType.CAPABILITY_GAP
    priority: OpportunityPriority = OpportunityPriority.MEDIUM

    # Description
    title: str = ""
    description: str = ""
    affected_agent: Optional[str] = None
    affected_task_type: Optional[str] = None

    # Impact assessment
    impact_score: float = 0.0  # 0-1, higher is more impactful
    estimated_improvement: float = 0.0  # Expected success rate improvement
    task_volume_affected: int = 0  # Number of tasks this could affect

    # Evidence
    evidence: Dict[str, Any] = field(default_factory=dict)
    sample_size: int = 0

    # Suggested action
    suggested_action: str = ""
    auto_actionable: bool = False  # Can be addressed automatically

    # Metadata
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    status: str = "open"  # open, acknowledged, addressed, dismissed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "opportunity_type": self.opportunity_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "affected_agent": self.affected_agent,
            "affected_task_type": self.affected_task_type,
            "impact_score": self.impact_score,
            "estimated_improvement": self.estimated_improvement,
            "task_volume_affected": self.task_volume_affected,
            "evidence": self.evidence,
            "sample_size": self.sample_size,
            "suggested_action": self.suggested_action,
            "auto_actionable": self.auto_actionable,
            "detected_at": self.detected_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status,
        }


@dataclass
class CapabilityGap:
    """A detected capability gap for an agent."""

    agent_code: str
    task_type: str
    success_rate: float
    task_volume: int
    avg_success_rate: float  # System average for comparison
    gap_severity: float  # How far below average


@dataclass
class WorkflowAnalysis:
    """Analysis of a workflow/task type performance."""

    task_type: str
    avg_duration_ms: float
    success_rate: float
    task_count: int
    parallelization_opportunity: bool = False
    time_savings_estimate: float = 0.0
    bottleneck_agent: Optional[str] = None


class OpportunityDetector:
    """
    Detects improvement opportunities across the learning system.

    Proactively analyzes patterns, performance, and errors to find
    areas where the system can improve itself.
    """

    # Thresholds for detection
    CAPABILITY_GAP_THRESHOLD = 0.15  # 15% below average
    LOW_SUCCESS_RATE_THRESHOLD = 0.6  # 60% success rate
    HIGH_ERROR_RATE_THRESHOLD = 0.2  # 20% error rate
    MIN_SAMPLES_FOR_DETECTION = 10
    PATTERN_COVERAGE_THRESHOLD = 0.3  # 30% of task types should have patterns

    # Opportunity expiration
    DEFAULT_EXPIRY_HOURS = 168  # 1 week

    def __init__(self, db: Any, pattern_store: Any):
        """
        Initialize the opportunity detector.

        Args:
            db: Database connection
            pattern_store: PatternStore for pattern analysis
        """
        self._db = db
        self._pattern_store = pattern_store

        # Cache of detected opportunities
        self._opportunities: Dict[str, Opportunity] = {}

    async def detect_opportunities(
        self,
        window_hours: int = 168,  # 1 week
    ) -> List[Opportunity]:
        """
        Run a full opportunity detection cycle.

        Args:
            window_hours: Time window for analysis

        Returns:
            List of detected opportunities, sorted by impact
        """
        opportunities = []

        # Detect various types of opportunities
        opportunities.extend(await self._detect_capability_gaps(window_hours))
        opportunities.extend(await self._detect_workflow_optimizations(window_hours))
        opportunities.extend(await self._detect_pattern_coverage_gaps(window_hours))
        opportunities.extend(await self._detect_resource_imbalances(window_hours))
        opportunities.extend(await self._detect_training_needs(window_hours))
        opportunities.extend(await self._detect_error_prevention_opportunities(window_hours))
        opportunities.extend(await self._detect_handler_opportunities(window_hours))

        # Store and sort opportunities
        for opp in opportunities:
            self._opportunities[opp.id] = opp

        # Sort by impact score (highest first)
        opportunities.sort(key=lambda x: x.impact_score, reverse=True)

        logger.info(f"Detected {len(opportunities)} improvement opportunities")

        return opportunities

    async def _detect_capability_gaps(
        self,
        window_hours: int,
    ) -> List[Opportunity]:
        """Detect agents that underperform on specific task types."""
        opportunities = []
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        try:
            # Get per-agent, per-task-type success rates
            rows = await self._db.fetch_all(
                """
                SELECT
                    agent_code as agent_code,
                    task_type,
                    COUNT(*) as task_count,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
                FROM learning_outcomes
                WHERE created_at >= ?
                GROUP BY agent_code, task_type
                HAVING task_count >= ?
                """,
                (window_start.isoformat(), self.MIN_SAMPLES_FOR_DETECTION),
            )

            if not rows:
                return opportunities

            # Calculate average success rate per task type
            task_type_avg: Dict[str, float] = {}
            task_type_counts: Dict[str, List[float]] = {}

            for row in rows:
                task_type = row["task_type"]
                if task_type not in task_type_counts:
                    task_type_counts[task_type] = []
                task_type_counts[task_type].append(row["success_rate"])

            for task_type, rates in task_type_counts.items():
                task_type_avg[task_type] = sum(rates) / len(rates)

            # Find agents below average
            for row in rows:
                agent_code = row["agent_code"]
                task_type = row["task_type"]
                success_rate = row["success_rate"]
                avg_rate = task_type_avg.get(task_type, 0.5)
                gap = avg_rate - success_rate

                if gap >= self.CAPABILITY_GAP_THRESHOLD:
                    impact = gap * row["task_count"] / 100  # Normalize

                    opportunities.append(
                        Opportunity(
                            opportunity_type=OpportunityType.CAPABILITY_GAP,
                            priority=self._calculate_priority(impact),
                            title=f"Capability gap: {agent_code} on {task_type}",
                            description=(
                                f"Agent {agent_code} has {success_rate:.1%} success rate on "
                                f"{task_type} tasks, which is {gap:.1%} below the average "
                                f"of {avg_rate:.1%}."
                            ),
                            affected_agent=agent_code,
                            affected_task_type=task_type,
                            impact_score=min(1.0, impact),
                            estimated_improvement=gap * 0.5,  # Conservative estimate
                            task_volume_affected=row["task_count"],
                            evidence={
                                "success_rate": success_rate,
                                "average_rate": avg_rate,
                                "gap": gap,
                            },
                            sample_size=row["task_count"],
                            suggested_action=(
                                f"Review and improve {agent_code}'s handling of {task_type} tasks. "
                                f"Consider adding specialized patterns or routing to a better agent."
                            ),
                            auto_actionable=True,
                            expires_at=datetime.now(timezone.utc)
                            + timedelta(hours=self.DEFAULT_EXPIRY_HOURS),
                        )
                    )

        except Exception as e:
            logger.warning(f"Failed to detect capability gaps: {e}")

        return opportunities

    async def _detect_workflow_optimizations(
        self,
        window_hours: int,
    ) -> List[Opportunity]:
        """Detect workflows that could be optimized."""
        opportunities = []
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        try:
            # Analyze task type performance
            rows = await self._db.fetch_all(
                """
                SELECT
                    task_type,
                    COUNT(*) as task_count,
                    AVG(duration_ms) as avg_duration,
                    AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                    MAX(duration_ms) as max_duration,
                    MIN(duration_ms) as min_duration
                FROM learning_outcomes
                WHERE created_at >= ? AND duration_ms > 0
                GROUP BY task_type
                HAVING task_count >= ?
                """,
                (window_start.isoformat(), self.MIN_SAMPLES_FOR_DETECTION),
            )

            if not rows:
                return opportunities

            # Find task types with high variance (potential for optimization)
            for row in rows:
                task_type = row["task_type"]
                avg_duration = row["avg_duration"]
                max_duration = row["max_duration"]
                min_duration = row["min_duration"]
                success_rate = row["success_rate"]

                # Calculate duration variance
                duration_range = max_duration - min_duration
                variance_ratio = duration_range / avg_duration if avg_duration > 0 else 0

                # High variance suggests inconsistent processing
                if variance_ratio > 2.0:  # Duration varies by more than 2x
                    time_savings = (
                        (avg_duration - min_duration) * row["task_count"] / 1000
                    )  # seconds
                    impact = min(1.0, time_savings / 3600)  # Normalize by hour

                    opportunities.append(
                        Opportunity(
                            opportunity_type=OpportunityType.WORKFLOW_OPTIMIZATION,
                            priority=self._calculate_priority(impact),
                            title=f"Workflow optimization: {task_type}",
                            description=(
                                f"Task type {task_type} shows high duration variance "
                                f"(range: {min_duration:.0f}ms - {max_duration:.0f}ms, avg: {avg_duration:.0f}ms). "
                                f"Optimizing could save {time_savings/60:.1f} minutes."
                            ),
                            affected_task_type=task_type,
                            impact_score=impact,
                            estimated_improvement=0.1,  # 10% improvement estimate
                            task_volume_affected=row["task_count"],
                            evidence={
                                "avg_duration_ms": avg_duration,
                                "min_duration_ms": min_duration,
                                "max_duration_ms": max_duration,
                                "variance_ratio": variance_ratio,
                                "success_rate": success_rate,
                            },
                            sample_size=row["task_count"],
                            suggested_action=(
                                f"Investigate slow executions of {task_type}. "
                                f"Consider adding timeout handling or parallel processing."
                            ),
                            auto_actionable=False,
                            expires_at=datetime.now(timezone.utc)
                            + timedelta(hours=self.DEFAULT_EXPIRY_HOURS),
                        )
                    )

        except Exception as e:
            logger.warning(f"Failed to detect workflow optimizations: {e}")

        return opportunities

    async def _detect_pattern_coverage_gaps(
        self,
        window_hours: int,
    ) -> List[Opportunity]:
        """Detect task types that lack pattern coverage."""
        opportunities = []
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        try:
            # Get task types with significant volume
            task_types_row = await self._db.fetch_all(
                """
                SELECT
                    task_type,
                    COUNT(*) as task_count,
                    AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
                FROM learning_outcomes
                WHERE created_at >= ?
                GROUP BY task_type
                HAVING task_count >= ?
                """,
                (window_start.isoformat(), self.MIN_SAMPLES_FOR_DETECTION),
            )

            if not task_types_row:
                return opportunities

            # Get patterns by task type
            all_patterns = await self._pattern_store.get_all_active_patterns()
            patterns_by_task_type: Dict[str, int] = {}

            for pattern in all_patterns:
                # Extract task type from pattern condition
                try:
                    import json

                    condition = json.loads(pattern.condition_json)
                    if "task_type" in condition:
                        task_type = condition["task_type"]
                        patterns_by_task_type[task_type] = (
                            patterns_by_task_type.get(task_type, 0) + 1
                        )
                except (json.JSONDecodeError, AttributeError):
                    pass

            # Find task types with no/few patterns
            for row in task_types_row:
                task_type = row["task_type"]
                pattern_count = patterns_by_task_type.get(task_type, 0)
                task_count = row["task_count"]
                success_rate = row["success_rate"]

                # Flag if no patterns and success rate is not perfect
                if pattern_count == 0 and success_rate < 0.95:
                    impact = (1 - success_rate) * (task_count / 100)

                    opportunities.append(
                        Opportunity(
                            opportunity_type=OpportunityType.PATTERN_COVERAGE,
                            priority=self._calculate_priority(impact),
                            title=f"Pattern coverage gap: {task_type}",
                            description=(
                                f"Task type {task_type} has {task_count} executions "
                                f"but no learned patterns. Success rate is {success_rate:.1%}."
                            ),
                            affected_task_type=task_type,
                            impact_score=min(1.0, impact),
                            estimated_improvement=(1 - success_rate) * 0.3,
                            task_volume_affected=task_count,
                            evidence={
                                "pattern_count": pattern_count,
                                "success_rate": success_rate,
                            },
                            sample_size=task_count,
                            suggested_action=(
                                f"Analyze successful executions of {task_type} to extract patterns. "
                                f"Consider running pattern detection for this task type."
                            ),
                            auto_actionable=True,
                            expires_at=datetime.now(timezone.utc)
                            + timedelta(hours=self.DEFAULT_EXPIRY_HOURS),
                        )
                    )

        except Exception as e:
            logger.warning(f"Failed to detect pattern coverage gaps: {e}")

        return opportunities

    async def _detect_resource_imbalances(
        self,
        window_hours: int,
    ) -> List[Opportunity]:
        """Detect uneven load distribution across agents."""
        opportunities = []
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        try:
            # Get task distribution by agent
            rows = await self._db.fetch_all(
                """
                SELECT
                    agent_code as agent_code,
                    COUNT(*) as task_count,
                    AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                    AVG(duration_ms) as avg_duration
                FROM learning_outcomes
                WHERE created_at >= ?
                GROUP BY agent_code
                """,
                (window_start.isoformat(),),
            )

            if len(rows) < 2:
                return opportunities

            # Calculate average load
            total_tasks = sum(row["task_count"] for row in rows)
            avg_tasks = total_tasks / len(rows)

            # Find overloaded agents
            for row in rows:
                agent_code = row["agent_code"]
                task_count = row["task_count"]
                imbalance_ratio = task_count / avg_tasks if avg_tasks > 0 else 1.0

                if imbalance_ratio > 2.0:  # More than 2x average
                    impact = (imbalance_ratio - 1.0) * 0.2

                    opportunities.append(
                        Opportunity(
                            opportunity_type=OpportunityType.RESOURCE_REBALANCING,
                            priority=self._calculate_priority(impact),
                            title=f"Resource imbalance: {agent_code} overloaded",
                            description=(
                                f"Agent {agent_code} handled {task_count} tasks, "
                                f"which is {imbalance_ratio:.1f}x the average of {avg_tasks:.0f}. "
                                f"Consider redistributing load."
                            ),
                            affected_agent=agent_code,
                            impact_score=min(1.0, impact),
                            task_volume_affected=task_count,
                            evidence={
                                "task_count": task_count,
                                "average_tasks": avg_tasks,
                                "imbalance_ratio": imbalance_ratio,
                                "success_rate": row["success_rate"],
                            },
                            sample_size=task_count,
                            suggested_action=(
                                f"Review routing rules for {agent_code}. Consider adjusting "
                                f"load balancer weights or adding routing patterns."
                            ),
                            auto_actionable=True,
                            expires_at=datetime.now(timezone.utc)
                            + timedelta(hours=self.DEFAULT_EXPIRY_HOURS),
                        )
                    )

        except Exception as e:
            logger.warning(f"Failed to detect resource imbalances: {e}")

        return opportunities

    async def _detect_training_needs(
        self,
        window_hours: int,
    ) -> List[Opportunity]:
        """Detect agents that need calibration or training."""
        opportunities = []
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        try:
            # Get agents with poor calibration (confidence vs actual)
            rows = await self._db.fetch_all(
                """
                SELECT
                    agent_code as agent_code,
                    COUNT(*) as task_count,
                    AVG(initial_confidence) as avg_confidence,
                    AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as actual_rate,
                    ABS(AVG(initial_confidence) - AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END)) as calibration_error
                FROM learning_outcomes
                WHERE created_at >= ? AND initial_confidence IS NOT NULL
                GROUP BY agent_code
                HAVING task_count >= ?
                ORDER BY calibration_error DESC
                """,
                (window_start.isoformat(), self.MIN_SAMPLES_FOR_DETECTION),
            )

            for row in rows:
                agent_code = row["agent_code"]
                calibration_error = row["calibration_error"]
                avg_confidence = row["avg_confidence"]
                actual_rate = row["actual_rate"]

                if calibration_error > 0.15:  # More than 15% calibration error
                    impact = calibration_error * 0.5

                    direction = (
                        "overconfident" if avg_confidence > actual_rate else "underconfident"
                    )

                    opportunities.append(
                        Opportunity(
                            opportunity_type=OpportunityType.TRAINING_NEED,
                            priority=self._calculate_priority(impact),
                            title=f"Calibration needed: {agent_code} is {direction}",
                            description=(
                                f"Agent {agent_code} shows {calibration_error:.1%} calibration error. "
                                f"Average confidence: {avg_confidence:.1%}, Actual success: {actual_rate:.1%}."
                            ),
                            affected_agent=agent_code,
                            impact_score=min(1.0, impact),
                            estimated_improvement=calibration_error * 0.5,
                            task_volume_affected=row["task_count"],
                            evidence={
                                "avg_confidence": avg_confidence,
                                "actual_rate": actual_rate,
                                "calibration_error": calibration_error,
                                "direction": direction,
                            },
                            sample_size=row["task_count"],
                            suggested_action=(
                                f"Run confidence calibration for {agent_code}. "
                                f"Adjust confidence parameters to better reflect actual performance."
                            ),
                            auto_actionable=True,
                            expires_at=datetime.now(timezone.utc)
                            + timedelta(hours=self.DEFAULT_EXPIRY_HOURS),
                        )
                    )

        except Exception as e:
            logger.warning(f"Failed to detect training needs: {e}")

        return opportunities

    async def _detect_error_prevention_opportunities(
        self,
        window_hours: int,
    ) -> List[Opportunity]:
        """Detect recurring errors that could be prevented."""
        opportunities = []
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        try:
            # Get error patterns
            rows = await self._db.fetch_all(
                """
                SELECT
                    error_category,
                    task_type,
                    agent_code as agent_code,
                    COUNT(*) as error_count
                FROM learning_outcomes
                WHERE created_at >= ? AND success = 0 AND error_category IS NOT NULL
                GROUP BY error_category, task_type, agent_code
                HAVING error_count >= 5
                ORDER BY error_count DESC
                LIMIT 10
                """,
                (window_start.isoformat(),),
            )

            for row in rows:
                error_category = row["error_category"]
                task_type = row["task_type"]
                agent_code = row["agent_code"]
                error_count = row["error_count"]

                impact = min(1.0, error_count / 20)

                opportunities.append(
                    Opportunity(
                        opportunity_type=OpportunityType.ERROR_PREVENTION,
                        priority=self._calculate_priority(impact),
                        title=f"Recurring {error_category} errors on {task_type}",
                        description=(
                            f"Agent {agent_code} encountered {error_count} {error_category} errors "
                            f"when handling {task_type} tasks. These may be preventable."
                        ),
                        affected_agent=agent_code,
                        affected_task_type=task_type,
                        impact_score=impact,
                        estimated_improvement=0.1,
                        task_volume_affected=error_count,
                        evidence={
                            "error_category": error_category,
                            "error_count": error_count,
                        },
                        sample_size=error_count,
                        suggested_action=(
                            f"Add error handling pattern for {error_category} errors in {task_type}. "
                            f"Consider adding pre-validation or retry logic."
                        ),
                        auto_actionable=True,
                        expires_at=datetime.now(timezone.utc)
                        + timedelta(hours=self.DEFAULT_EXPIRY_HOURS),
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to detect error prevention opportunities: {e}")

        return opportunities

    async def _detect_handler_opportunities(
        self,
        window_hours: int,
    ) -> List[Opportunity]:
        """Detect task types that could benefit from auto-generated handlers."""
        opportunities = []
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        try:
            # Get task types with high volume and good success rate
            rows = await self._db.fetch_all(
                """
                SELECT
                    task_type,
                    COUNT(*) as task_count,
                    AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
                FROM learning_outcomes
                WHERE created_at >= ?
                GROUP BY task_type
                HAVING task_count >= 20 AND success_rate >= 0.7
                ORDER BY task_count DESC
                """,
                (window_start.isoformat(),),
            )

            # Check which don't have handlers
            for row in rows:
                task_type = row["task_type"]
                task_count = row["task_count"]
                success_rate = row["success_rate"]

                # Check if handler exists (would need handler_generator reference)
                # For now, flag all high-volume task types as candidates

                if task_count >= 30 and success_rate >= 0.75:
                    impact = min(1.0, task_count / 100 * success_rate)

                    opportunities.append(
                        Opportunity(
                            opportunity_type=OpportunityType.HANDLER_OPPORTUNITY,
                            priority=OpportunityPriority.MEDIUM,
                            title=f"Handler opportunity: {task_type}",
                            description=(
                                f"Task type {task_type} has {task_count} executions "
                                f"with {success_rate:.1%} success rate. Could benefit from "
                                f"an auto-generated handler."
                            ),
                            affected_task_type=task_type,
                            impact_score=impact,
                            estimated_improvement=0.05,  # 5% improvement
                            task_volume_affected=task_count,
                            evidence={
                                "task_count": task_count,
                                "success_rate": success_rate,
                            },
                            sample_size=task_count,
                            suggested_action=(
                                f"Generate a handler for {task_type} using the HandlerGenerator."
                            ),
                            auto_actionable=True,
                            expires_at=datetime.now(timezone.utc)
                            + timedelta(hours=self.DEFAULT_EXPIRY_HOURS),
                        )
                    )

        except Exception as e:
            logger.warning(f"Failed to detect handler opportunities: {e}")

        return opportunities

    def _calculate_priority(self, impact_score: float) -> OpportunityPriority:
        """Calculate priority based on impact score."""
        if impact_score >= 0.8:
            return OpportunityPriority.CRITICAL
        elif impact_score >= 0.5:
            return OpportunityPriority.HIGH
        elif impact_score >= 0.2:
            return OpportunityPriority.MEDIUM
        else:
            return OpportunityPriority.LOW

    async def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get a specific opportunity by ID."""
        return self._opportunities.get(opportunity_id)

    async def get_opportunities_by_type(
        self,
        opportunity_type: OpportunityType,
    ) -> List[Opportunity]:
        """Get opportunities of a specific type."""
        return [
            opp
            for opp in self._opportunities.values()
            if opp.opportunity_type == opportunity_type and opp.status == "open"
        ]

    async def get_open_opportunities(self) -> List[Opportunity]:
        """Get all open opportunities."""
        now = datetime.now(timezone.utc)
        return [
            opp
            for opp in self._opportunities.values()
            if opp.status == "open" and (opp.expires_at is None or opp.expires_at > now)
        ]

    async def get_actionable_opportunities(self) -> List[Opportunity]:
        """Get opportunities that can be addressed automatically."""
        return [opp for opp in await self.get_open_opportunities() if opp.auto_actionable]

    async def acknowledge_opportunity(
        self,
        opportunity_id: str,
    ) -> bool:
        """Mark an opportunity as acknowledged."""
        opp = self._opportunities.get(opportunity_id)
        if opp:
            opp.status = "acknowledged"
            return True
        return False

    async def address_opportunity(
        self,
        opportunity_id: str,
        resolution: str = "",
    ) -> bool:
        """Mark an opportunity as addressed."""
        opp = self._opportunities.get(opportunity_id)
        if opp:
            opp.status = "addressed"
            return True
        return False

    async def dismiss_opportunity(
        self,
        opportunity_id: str,
        reason: str = "",
    ) -> bool:
        """Dismiss an opportunity."""
        opp = self._opportunities.get(opportunity_id)
        if opp:
            opp.status = "dismissed"
            return True
        return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get opportunity detection statistics."""
        open_opps = await self.get_open_opportunities()

        by_type = {}
        by_priority = {}

        for opp in open_opps:
            type_key = opp.opportunity_type.value
            priority_key = opp.priority.value

            by_type[type_key] = by_type.get(type_key, 0) + 1
            by_priority[priority_key] = by_priority.get(priority_key, 0) + 1

        return {
            "total_opportunities": len(self._opportunities),
            "open_opportunities": len(open_opps),
            "actionable_opportunities": len([o for o in open_opps if o.auto_actionable]),
            "by_type": by_type,
            "by_priority": by_priority,
        }
