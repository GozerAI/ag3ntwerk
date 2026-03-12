"""
Capability Evolver - Enables agents to develop new capabilities based on demand.

Analyzes task demand patterns to identify capability gaps and generates
new capabilities to fill those gaps, enabling emergent agent behavior.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from ag3ntwerk.learning.pattern_store import PatternStore
    from ag3ntwerk.learning.outcome_tracker import OutcomeTracker

logger = logging.getLogger(__name__)


class CapabilityType(Enum):
    """Types of capabilities that can be evolved."""

    TASK_HANDLING = "task_handling"
    ERROR_RECOVERY = "error_recovery"
    OPTIMIZATION = "optimization"
    DELEGATION = "delegation"
    COORDINATION = "coordination"
    SPECIALIZATION = "specialization"


class EvolutionStatus(Enum):
    """Status of a capability evolution."""

    PROPOSED = "proposed"
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


@dataclass
class DemandGap:
    """
    Represents a gap between task demand and agent capabilities.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_code: str = ""
    task_type: str = ""
    volume: int = 0
    failure_rate: float = 0.0
    avg_duration_ms: float = 0.0
    error_patterns: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    severity: float = 0.0  # 0.0-1.0, higher = more urgent

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_code": self.agent_code,
            "task_type": self.task_type,
            "volume": self.volume,
            "failure_rate": self.failure_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "error_patterns": self.error_patterns,
            "detected_at": self.detected_at.isoformat(),
            "severity": self.severity,
        }


@dataclass
class NewCapability:
    """
    A newly evolved capability for an agent.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_code: str = ""
    capability_type: CapabilityType = CapabilityType.TASK_HANDLING
    name: str = ""
    description: str = ""
    task_types: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    status: EvolutionStatus = EvolutionStatus.PROPOSED
    source_gap_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    activated_at: Optional[datetime] = None
    test_results: Dict[str, Any] = field(default_factory=dict)
    success_rate: float = 0.0
    sample_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_code": self.agent_code,
            "capability_type": self.capability_type.value,
            "name": self.name,
            "description": self.description,
            "task_types": self.task_types,
            "configuration": self.configuration,
            "status": self.status.value,
            "source_gap_id": self.source_gap_id,
            "created_at": self.created_at.isoformat(),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "test_results": self.test_results,
            "success_rate": self.success_rate,
            "sample_size": self.sample_size,
        }


@dataclass
class EvolutionResult:
    """Result of a capability evolution cycle."""

    agent_code: str
    gaps_analyzed: int
    capabilities_proposed: int
    capabilities_activated: int
    capabilities_deprecated: int
    duration_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "gaps_analyzed": self.gaps_analyzed,
            "capabilities_proposed": self.capabilities_proposed,
            "capabilities_activated": self.capabilities_activated,
            "capabilities_deprecated": self.capabilities_deprecated,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class CapabilityEvolver:
    """
    Evolves agent capabilities based on demand patterns.

    Analyzes task outcomes to identify capability gaps and generates
    new capabilities to fill those gaps. Capabilities go through a
    lifecycle: proposed -> testing -> active -> deprecated.
    """

    # Thresholds for gap detection
    MIN_VOLUME_FOR_GAP = 50  # Minimum tasks to consider a gap
    MAX_FAILURE_RATE_HEALTHY = 0.3  # Above this = gap detected
    MIN_DURATION_RATIO = 2.0  # If 2x slower than similar, gap detected

    # Thresholds for capability activation
    MIN_TEST_SAMPLES = 20
    MIN_SUCCESS_RATE_FOR_ACTIVATION = 0.7
    ACTIVATION_CONFIDENCE = 0.8

    def __init__(
        self,
        db: Any,
        pattern_store: "PatternStore",
        outcome_tracker: "OutcomeTracker",
    ):
        """
        Initialize the capability evolver.

        Args:
            db: Database connection
            pattern_store: PatternStore for pattern queries
            outcome_tracker: OutcomeTracker for outcome analysis
        """
        self._db = db
        self._pattern_store = pattern_store
        self._outcome_tracker = outcome_tracker

        # In-memory caches
        self._capabilities: Dict[str, NewCapability] = {}  # id -> capability
        self._agent_capabilities: Dict[str, List[str]] = {}  # agent -> capability ids
        self._detected_gaps: Dict[str, DemandGap] = {}  # id -> gap

    async def evolve_capabilities(
        self,
        agent_code: str,
        window_hours: int = 168,  # 1 week default
    ) -> List[NewCapability]:
        """
        Evolve capabilities for an agent based on demand patterns.

        Args:
            agent_code: Agent to evolve capabilities for
            window_hours: Time window for analysis

        Returns:
            List of new or updated capabilities
        """
        start_time = datetime.now(timezone.utc)
        new_capabilities: List[NewCapability] = []

        # Step 1: Analyze demand gaps
        gaps = await self._analyze_demand_gaps(agent_code, window_hours)

        # Step 2: Generate capabilities for significant gaps
        for gap in gaps:
            if (
                gap.volume >= self.MIN_VOLUME_FOR_GAP
                and gap.failure_rate > self.MAX_FAILURE_RATE_HEALTHY
            ):
                capability = await self._generate_capability(gap)
                if capability:
                    await self._register_capability(agent_code, capability)
                    new_capabilities.append(capability)

        # Step 3: Check existing capabilities for promotion/demotion
        await self._evaluate_capability_status(agent_code)

        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        result = EvolutionResult(
            agent_code=agent_code,
            gaps_analyzed=len(gaps),
            capabilities_proposed=len(new_capabilities),
            capabilities_activated=0,  # Updated by _evaluate_capability_status
            capabilities_deprecated=0,
            duration_ms=duration_ms,
        )

        logger.info(
            f"Evolved capabilities for {agent_code}: "
            f"{len(gaps)} gaps analyzed, {len(new_capabilities)} new capabilities"
        )

        return new_capabilities

    async def _analyze_demand_gaps(
        self,
        agent_code: str,
        window_hours: int,
    ) -> List[DemandGap]:
        """
        Analyze demand patterns to identify capability gaps.

        Args:
            agent_code: Agent to analyze
            window_hours: Time window

        Returns:
            List of detected demand gaps
        """
        gaps: List[DemandGap] = []

        # Get outcomes for this agent
        outcomes = await self._outcome_tracker.get_outcomes(
            agent_code=agent_code,
            window_hours=window_hours,
            limit=5000,
        )

        if not outcomes:
            return gaps

        # Group by task type
        by_task_type: Dict[str, List[Any]] = {}
        for outcome in outcomes:
            task_type = outcome.task_type
            if task_type not in by_task_type:
                by_task_type[task_type] = []
            by_task_type[task_type].append(outcome)

        # Analyze each task type for gaps
        for task_type, task_outcomes in by_task_type.items():
            volume = len(task_outcomes)
            if volume < self.MIN_VOLUME_FOR_GAP:
                continue

            failures = [o for o in task_outcomes if not o.success]
            failure_rate = len(failures) / volume
            avg_duration = sum(o.duration_ms for o in task_outcomes) / volume

            # Check for high failure rate
            if failure_rate > self.MAX_FAILURE_RATE_HEALTHY:
                # Collect error patterns
                error_patterns = self._extract_error_patterns(failures)

                gap = DemandGap(
                    agent_code=agent_code,
                    task_type=task_type,
                    volume=volume,
                    failure_rate=failure_rate,
                    avg_duration_ms=avg_duration,
                    error_patterns=error_patterns,
                    severity=self._calculate_gap_severity(volume, failure_rate),
                )
                gaps.append(gap)
                self._detected_gaps[gap.id] = gap

        # Sort by severity
        gaps.sort(key=lambda g: g.severity, reverse=True)

        return gaps

    async def _generate_capability(self, gap: DemandGap) -> Optional[NewCapability]:
        """
        Generate a new capability to address a demand gap.

        Args:
            gap: Demand gap to address

        Returns:
            NewCapability if one can be generated, None otherwise
        """
        # Determine capability type based on gap characteristics
        capability_type = self._determine_capability_type(gap)

        # Generate configuration based on patterns
        configuration = await self._generate_capability_config(gap, capability_type)

        # Create the capability
        capability = NewCapability(
            agent_code=gap.agent_code,
            capability_type=capability_type,
            name=f"{capability_type.value}_{gap.task_type}",
            description=self._generate_capability_description(gap, capability_type),
            task_types=[gap.task_type],
            configuration=configuration,
            status=EvolutionStatus.PROPOSED,
            source_gap_id=gap.id,
        )

        logger.info(
            f"Generated capability {capability.name} for {gap.agent_code} "
            f"to address {gap.task_type} gap (failure_rate={gap.failure_rate:.2%})"
        )

        return capability

    async def _register_capability(
        self,
        agent_code: str,
        capability: NewCapability,
    ) -> None:
        """
        Register a new capability for an agent.

        Args:
            agent_code: Agent to register capability for
            capability: Capability to register
        """
        # Store in memory
        self._capabilities[capability.id] = capability

        if agent_code not in self._agent_capabilities:
            self._agent_capabilities[agent_code] = []
        self._agent_capabilities[agent_code].append(capability.id)

        # Persist to database
        await self._persist_capability(capability)

    async def _evaluate_capability_status(self, agent_code: str) -> None:
        """
        Evaluate and update status of existing capabilities.

        Args:
            agent_code: Agent to evaluate capabilities for
        """
        capability_ids = self._agent_capabilities.get(agent_code, [])

        for cap_id in capability_ids:
            capability = self._capabilities.get(cap_id)
            if not capability:
                continue

            if capability.status == EvolutionStatus.TESTING:
                # Check if ready for activation
                if (
                    capability.sample_size >= self.MIN_TEST_SAMPLES
                    and capability.success_rate >= self.MIN_SUCCESS_RATE_FOR_ACTIVATION
                ):
                    capability.status = EvolutionStatus.ACTIVE
                    capability.activated_at = datetime.now(timezone.utc)
                    await self._persist_capability(capability)
                    logger.info(f"Activated capability {capability.name}")

            elif capability.status == EvolutionStatus.ACTIVE:
                # Check if should be deprecated
                if (
                    capability.sample_size >= self.MIN_TEST_SAMPLES
                    and capability.success_rate < self.MIN_SUCCESS_RATE_FOR_ACTIVATION * 0.7
                ):
                    capability.status = EvolutionStatus.DEPRECATED
                    await self._persist_capability(capability)
                    logger.info(f"Deprecated capability {capability.name}")

    def _determine_capability_type(self, gap: DemandGap) -> CapabilityType:
        """Determine the best capability type for a gap."""
        error_patterns = gap.error_patterns

        # Check for error recovery needs
        if any("timeout" in e.lower() or "error" in e.lower() for e in error_patterns):
            return CapabilityType.ERROR_RECOVERY

        # Check for optimization needs
        if gap.avg_duration_ms > 5000:  # Slow tasks
            return CapabilityType.OPTIMIZATION

        # Check for delegation needs
        if gap.volume > 500 and gap.failure_rate > 0.5:
            return CapabilityType.DELEGATION

        # Default to task handling
        return CapabilityType.TASK_HANDLING

    async def _generate_capability_config(
        self,
        gap: DemandGap,
        capability_type: CapabilityType,
    ) -> Dict[str, Any]:
        """Generate configuration for a new capability."""
        config: Dict[str, Any] = {
            "source_gap_id": gap.id,
            "task_type": gap.task_type,
            "target_failure_rate": gap.failure_rate * 0.5,  # 50% reduction target
        }

        if capability_type == CapabilityType.ERROR_RECOVERY:
            config.update(
                {
                    "retry_count": 3,
                    "retry_delay_ms": 1000,
                    "fallback_enabled": True,
                    "error_patterns_handled": gap.error_patterns[:5],
                }
            )
        elif capability_type == CapabilityType.OPTIMIZATION:
            config.update(
                {
                    "target_duration_ms": gap.avg_duration_ms * 0.7,  # 30% faster
                    "caching_enabled": True,
                    "batch_size": min(10, max(1, gap.volume // 100)),
                }
            )
        elif capability_type == CapabilityType.DELEGATION:
            config.update(
                {
                    "delegation_threshold": 0.5,
                    "preferred_delegates": [],
                    "load_balancing": True,
                }
            )

        return config

    def _generate_capability_description(
        self,
        gap: DemandGap,
        capability_type: CapabilityType,
    ) -> str:
        """Generate a description for a new capability."""
        descriptions = {
            CapabilityType.TASK_HANDLING: (
                f"Enhanced handling for {gap.task_type} tasks to reduce "
                f"failure rate from {gap.failure_rate:.1%}"
            ),
            CapabilityType.ERROR_RECOVERY: (
                f"Error recovery capability for {gap.task_type} addressing "
                f"{len(gap.error_patterns)} common error patterns"
            ),
            CapabilityType.OPTIMIZATION: (
                f"Performance optimization for {gap.task_type} to reduce "
                f"average duration from {gap.avg_duration_ms:.0f}ms"
            ),
            CapabilityType.DELEGATION: (
                f"Intelligent delegation for {gap.task_type} with "
                f"{gap.volume} tasks and {gap.failure_rate:.1%} failure rate"
            ),
            CapabilityType.COORDINATION: (f"Coordination capability for {gap.task_type}"),
            CapabilityType.SPECIALIZATION: (f"Specialized handling for {gap.task_type}"),
        }
        return descriptions.get(capability_type, f"Capability for {gap.task_type}")

    def _extract_error_patterns(self, failures: List[Any]) -> List[str]:
        """Extract common error patterns from failures."""
        error_counts: Dict[str, int] = {}

        for failure in failures:
            error = failure.error_message or "unknown"
            # Normalize error message
            normalized = self._normalize_error(error)
            error_counts[normalized] = error_counts.get(normalized, 0) + 1

        # Return top 10 most common
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [e[0] for e in sorted_errors[:10]]

    def _normalize_error(self, error: str) -> str:
        """Normalize an error message for pattern matching."""
        # Remove specific values like IDs, timestamps
        import re

        normalized = re.sub(r"\b[0-9a-f]{8,}\b", "<ID>", error)
        normalized = re.sub(r"\d{4}-\d{2}-\d{2}", "<DATE>", normalized)
        normalized = re.sub(r"\d+", "<NUM>", normalized)
        return normalized[:100]  # Truncate

    def _calculate_gap_severity(self, volume: int, failure_rate: float) -> float:
        """Calculate the severity of a demand gap."""
        # Combine volume and failure rate
        volume_factor = min(1.0, volume / 1000)  # Caps at 1000 tasks
        severity = (failure_rate * 0.7) + (volume_factor * 0.3)
        return min(1.0, severity)

    # =========================================================================
    # Capability Query Methods
    # =========================================================================

    async def get_agent_capabilities(
        self,
        agent_code: str,
        status: Optional[EvolutionStatus] = None,
    ) -> List[NewCapability]:
        """
        Get capabilities for an agent.

        Args:
            agent_code: Agent to get capabilities for
            status: Optional filter by status

        Returns:
            List of capabilities
        """
        capability_ids = self._agent_capabilities.get(agent_code, [])
        capabilities = []

        for cap_id in capability_ids:
            cap = self._capabilities.get(cap_id)
            if cap and (status is None or cap.status == status):
                capabilities.append(cap)

        return capabilities

    async def get_capability(self, capability_id: str) -> Optional[NewCapability]:
        """Get a specific capability."""
        return self._capabilities.get(capability_id)

    async def get_active_capabilities(
        self,
        agent_code: Optional[str] = None,
    ) -> List[NewCapability]:
        """Get all active capabilities."""
        capabilities = []

        if agent_code:
            return await self.get_agent_capabilities(agent_code, EvolutionStatus.ACTIVE)

        for cap in self._capabilities.values():
            if cap.status == EvolutionStatus.ACTIVE:
                capabilities.append(cap)

        return capabilities

    async def get_detected_gaps(
        self,
        agent_code: Optional[str] = None,
        min_severity: float = 0.0,
    ) -> List[DemandGap]:
        """
        Get detected demand gaps.

        Args:
            agent_code: Optional filter by agent
            min_severity: Minimum severity threshold

        Returns:
            List of demand gaps
        """
        gaps = []

        for gap in self._detected_gaps.values():
            if agent_code and gap.agent_code != agent_code:
                continue
            if gap.severity < min_severity:
                continue
            gaps.append(gap)

        return sorted(gaps, key=lambda g: g.severity, reverse=True)

    # =========================================================================
    # Capability Lifecycle Methods
    # =========================================================================

    async def start_testing(self, capability_id: str) -> bool:
        """
        Start testing a proposed capability.

        Args:
            capability_id: Capability to start testing

        Returns:
            True if testing started
        """
        capability = self._capabilities.get(capability_id)
        if not capability or capability.status != EvolutionStatus.PROPOSED:
            return False

        capability.status = EvolutionStatus.TESTING
        await self._persist_capability(capability)

        logger.info(f"Started testing capability {capability.name}")
        return True

    async def record_capability_usage(
        self,
        capability_id: str,
        success: bool,
        duration_ms: float = 0.0,
    ) -> None:
        """
        Record usage of a capability.

        Args:
            capability_id: Capability that was used
            success: Whether usage was successful
            duration_ms: Duration of the operation
        """
        capability = self._capabilities.get(capability_id)
        if not capability:
            return

        # Update stats
        capability.sample_size += 1
        old_successes = capability.success_rate * (capability.sample_size - 1)
        capability.success_rate = (old_successes + (1 if success else 0)) / capability.sample_size

        # Check for status change
        if capability.status == EvolutionStatus.TESTING:
            await self._evaluate_capability_status(capability.agent_code)

    async def deprecate_capability(
        self,
        capability_id: str,
        reason: str = "",
    ) -> bool:
        """
        Deprecate a capability.

        Args:
            capability_id: Capability to deprecate
            reason: Reason for deprecation

        Returns:
            True if deprecated
        """
        capability = self._capabilities.get(capability_id)
        if not capability:
            return False

        capability.status = EvolutionStatus.DEPRECATED
        capability.test_results["deprecation_reason"] = reason
        await self._persist_capability(capability)

        logger.info(f"Deprecated capability {capability.name}: {reason}")
        return True

    async def reject_capability(
        self,
        capability_id: str,
        reason: str = "",
    ) -> bool:
        """
        Reject a proposed capability.

        Args:
            capability_id: Capability to reject
            reason: Reason for rejection

        Returns:
            True if rejected
        """
        capability = self._capabilities.get(capability_id)
        if not capability or capability.status not in (
            EvolutionStatus.PROPOSED,
            EvolutionStatus.TESTING,
        ):
            return False

        capability.status = EvolutionStatus.REJECTED
        capability.test_results["rejection_reason"] = reason
        await self._persist_capability(capability)

        logger.info(f"Rejected capability {capability.name}: {reason}")
        return True

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(
        self,
        agent_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get capability evolution statistics.

        Args:
            agent_code: Optional filter by agent

        Returns:
            Statistics dictionary
        """
        if agent_code:
            capabilities = await self.get_agent_capabilities(agent_code)
            gaps = await self.get_detected_gaps(agent_code)
        else:
            capabilities = list(self._capabilities.values())
            gaps = list(self._detected_gaps.values())

        status_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}

        for cap in capabilities:
            status = cap.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

            cap_type = cap.capability_type.value
            type_counts[cap_type] = type_counts.get(cap_type, 0) + 1

        return {
            "total_capabilities": len(capabilities),
            "total_gaps": len(gaps),
            "by_status": status_counts,
            "by_type": type_counts,
            "avg_success_rate": (
                sum(c.success_rate for c in capabilities if c.sample_size > 0)
                / max(1, len([c for c in capabilities if c.sample_size > 0]))
            ),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    async def _persist_capability(self, capability: NewCapability) -> None:
        """Persist a capability to the database."""
        try:
            await self._db.execute(
                """
                INSERT OR REPLACE INTO evolved_capabilities (
                    id, agent_code, capability_type, name, description,
                    task_types, configuration, status, source_gap_id,
                    created_at, activated_at, test_results,
                    success_rate, sample_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    capability.id,
                    capability.agent_code,
                    capability.capability_type.value,
                    capability.name,
                    capability.description,
                    json.dumps(capability.task_types),
                    json.dumps(capability.configuration),
                    capability.status.value,
                    capability.source_gap_id,
                    capability.created_at.isoformat(),
                    capability.activated_at.isoformat() if capability.activated_at else None,
                    json.dumps(capability.test_results),
                    capability.success_rate,
                    capability.sample_size,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to persist capability: {e}")

    async def load_capabilities(self, agent_code: Optional[str] = None) -> int:
        """
        Load capabilities from the database.

        Args:
            agent_code: Optional filter by agent

        Returns:
            Number of capabilities loaded
        """
        try:
            if agent_code:
                query = "SELECT * FROM evolved_capabilities WHERE agent_code = ?"
                rows = await self._db.fetch_all(query, (agent_code,))
            else:
                rows = await self._db.fetch_all("SELECT * FROM evolved_capabilities")

            for row in rows:
                capability = self._row_to_capability(row)
                self._capabilities[capability.id] = capability

                if capability.agent_code not in self._agent_capabilities:
                    self._agent_capabilities[capability.agent_code] = []
                if capability.id not in self._agent_capabilities[capability.agent_code]:
                    self._agent_capabilities[capability.agent_code].append(capability.id)

            return len(rows)
        except Exception as e:
            logger.warning(f"Failed to load capabilities: {e}")
            return 0

    def _row_to_capability(self, row: Dict[str, Any]) -> NewCapability:
        """Convert a database row to a NewCapability."""
        return NewCapability(
            id=row["id"],
            agent_code=row["agent_code"],
            capability_type=CapabilityType(row["capability_type"]),
            name=row["name"],
            description=row["description"],
            task_types=json.loads(row.get("task_types", "[]")),
            configuration=json.loads(row.get("configuration", "{}")),
            status=EvolutionStatus(row["status"]),
            source_gap_id=row.get("source_gap_id"),
            created_at=datetime.fromisoformat(row["created_at"]),
            activated_at=(
                datetime.fromisoformat(row["activated_at"]) if row.get("activated_at") else None
            ),
            test_results=json.loads(row.get("test_results", "{}")),
            success_rate=row.get("success_rate", 0.0),
            sample_size=row.get("sample_size", 0),
        )
