"""
Pattern Propagator - Propagates successful patterns across similar agents.

When a pattern proves successful for one agent, it can be propagated to
similar agents that might benefit from the same learning.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from ag3ntwerk.learning.models import (
    LearnedPattern,
    PatternType,
    ScopeLevel,
)

if TYPE_CHECKING:
    from ag3ntwerk.learning.pattern_store import PatternStore
    from ag3ntwerk.learning.outcome_tracker import OutcomeTracker

logger = logging.getLogger(__name__)


class PropagationStatus(Enum):
    """Status of a pattern propagation."""

    PENDING = "pending"
    TESTING = "testing"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    REJECTED = "rejected"


class SimilarityMetric(Enum):
    """Metrics for measuring agent similarity."""

    TASK_TYPE_OVERLAP = "task_type_overlap"
    PERFORMANCE_PROFILE = "performance_profile"
    HIERARCHY_PROXIMITY = "hierarchy_proximity"
    CAPABILITY_OVERLAP = "capability_overlap"


@dataclass
class AgentSimilarity:
    """
    Represents similarity between two agents.
    """

    source_agent: str
    target_agent: str
    similarity_score: float  # 0.0-1.0
    metrics: Dict[str, float] = field(default_factory=dict)
    shared_task_types: List[str] = field(default_factory=list)
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "similarity_score": self.similarity_score,
            "metrics": self.metrics,
            "shared_task_types": self.shared_task_types,
            "computed_at": self.computed_at.isoformat(),
        }


@dataclass
class PropagationRecord:
    """
    Record of a pattern propagation attempt.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_pattern_id: str = ""
    source_agent: str = ""
    target_agent: str = ""
    propagated_pattern_id: Optional[str] = None
    status: PropagationStatus = PropagationStatus.PENDING
    similarity_score: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    test_outcomes: int = 0
    test_successes: int = 0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_pattern_id": self.source_pattern_id,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "propagated_pattern_id": self.propagated_pattern_id,
            "status": self.status.value,
            "similarity_score": self.similarity_score,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "test_outcomes": self.test_outcomes,
            "test_successes": self.test_successes,
            "notes": self.notes,
        }


@dataclass
class PropagationResult:
    """Result of a propagation cycle."""

    patterns_analyzed: int
    propagations_attempted: int
    propagations_successful: int
    propagations_failed: int
    duration_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patterns_analyzed": self.patterns_analyzed,
            "propagations_attempted": self.propagations_attempted,
            "propagations_successful": self.propagations_successful,
            "propagations_failed": self.propagations_failed,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class PatternPropagator:
    """
    Propagates successful patterns across similar agents.

    Analyzes agent similarity and automatically propagates patterns
    that prove successful for one agent to similar agents.
    """

    # Thresholds
    MIN_CONFIDENCE_FOR_PROPAGATION = 0.8  # Pattern must have high confidence
    MIN_APPLICATIONS_FOR_PROPAGATION = 20  # Must be well-tested
    MIN_SUCCESS_RATE_FOR_PROPAGATION = 0.75  # Must be successful
    MIN_SIMILARITY_FOR_PROPAGATION = 0.6  # Agents must be similar enough
    MIN_TEST_OUTCOMES = 10  # Minimum tests before confirming propagation

    def __init__(
        self,
        db: Any,
        pattern_store: "PatternStore",
        outcome_tracker: "OutcomeTracker",
    ):
        """
        Initialize the pattern propagator.

        Args:
            db: Database connection
            pattern_store: PatternStore for pattern access
            outcome_tracker: OutcomeTracker for outcome data
        """
        self._db = db
        self._pattern_store = pattern_store
        self._outcome_tracker = outcome_tracker

        # Caches
        self._similarity_cache: Dict[Tuple[str, str], AgentSimilarity] = {}
        self._propagation_records: Dict[str, PropagationRecord] = {}
        self._agent_task_types: Dict[str, Set[str]] = {}  # agent -> task types

    async def propagate_successful_patterns(
        self,
        window_hours: int = 168,  # 1 week default
    ) -> PropagationResult:
        """
        Propagate successful patterns to similar agents.

        Args:
            window_hours: Time window for pattern analysis

        Returns:
            PropagationResult with statistics
        """
        start_time = datetime.now(timezone.utc)
        propagations_attempted = 0
        propagations_successful = 0
        propagations_failed = 0

        # Step 1: Get high-confidence patterns
        high_confidence = await self._get_high_confidence_patterns(window_hours)
        logger.info(f"Found {len(high_confidence)} high-confidence patterns for propagation")

        # Step 2: For each pattern, find similar agents and propagate
        for pattern in high_confidence:
            # Skip patterns that are already at agent scope (highest level)
            if pattern.scope_level == ScopeLevel.AGENT:
                continue

            # Find similar agents
            similar_agents = await self._find_similar_agents(pattern.scope_code)

            for agent, similarity in similar_agents:
                if similarity.similarity_score < self.MIN_SIMILARITY_FOR_PROPAGATION:
                    continue

                # Check if pattern is applicable to this agent
                if not await self._is_applicable(pattern, agent):
                    continue

                # Check if we've already propagated this pattern to this agent
                if self._has_existing_propagation(pattern.id, agent):
                    continue

                # Attempt propagation
                propagations_attempted += 1
                success = await self._copy_pattern(pattern, agent, similarity)

                if success:
                    propagations_successful += 1
                else:
                    propagations_failed += 1

        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        result = PropagationResult(
            patterns_analyzed=len(high_confidence),
            propagations_attempted=propagations_attempted,
            propagations_successful=propagations_successful,
            propagations_failed=propagations_failed,
            duration_ms=duration_ms,
        )

        logger.info(
            f"Propagation cycle complete: {propagations_successful}/{propagations_attempted} successful"
        )

        return result

    async def _get_high_confidence_patterns(
        self,
        window_hours: int,
    ) -> List[LearnedPattern]:
        """Get patterns that qualify for propagation."""
        all_patterns = await self._pattern_store.get_patterns(is_active=True)

        qualified = []
        for pattern in all_patterns:
            # Check confidence threshold
            if pattern.confidence < self.MIN_CONFIDENCE_FOR_PROPAGATION:
                continue

            # Check application count
            if pattern.application_count < self.MIN_APPLICATIONS_FOR_PROPAGATION:
                continue

            # Check success rate
            if (
                pattern.success_rate is None
                or pattern.success_rate < self.MIN_SUCCESS_RATE_FOR_PROPAGATION
            ):
                continue

            qualified.append(pattern)

        return qualified

    async def _find_similar_agents(
        self,
        agent_code: str,
    ) -> List[Tuple[str, AgentSimilarity]]:
        """
        Find agents similar to the given agent.

        Args:
            agent_code: Source agent code

        Returns:
            List of (agent_code, similarity) tuples
        """
        similar: List[Tuple[str, AgentSimilarity]] = []

        # Get all known agents
        all_agents = await self._get_all_agents()

        for other_agent in all_agents:
            if other_agent == agent_code:
                continue

            # Check cache first
            cache_key = (min(agent_code, other_agent), max(agent_code, other_agent))
            if cache_key in self._similarity_cache:
                similarity = self._similarity_cache[cache_key]
            else:
                similarity = await self._compute_similarity(agent_code, other_agent)
                self._similarity_cache[cache_key] = similarity

            if similarity.similarity_score >= self.MIN_SIMILARITY_FOR_PROPAGATION:
                similar.append((other_agent, similarity))

        # Sort by similarity score
        similar.sort(key=lambda x: x[1].similarity_score, reverse=True)

        return similar

    async def _compute_similarity(
        self,
        agent1: str,
        agent2: str,
    ) -> AgentSimilarity:
        """
        Compute similarity between two agents.

        Args:
            agent1: First agent code
            agent2: Second agent code

        Returns:
            AgentSimilarity with computed scores
        """
        metrics: Dict[str, float] = {}

        # Task type overlap
        types1 = await self._get_agent_task_types(agent1)
        types2 = await self._get_agent_task_types(agent2)

        if types1 and types2:
            overlap = len(types1 & types2)
            union = len(types1 | types2)
            metrics["task_type_overlap"] = overlap / union if union > 0 else 0.0
        else:
            metrics["task_type_overlap"] = 0.0

        # Performance profile similarity
        perf1 = await self._get_performance_profile(agent1)
        perf2 = await self._get_performance_profile(agent2)
        metrics["performance_profile"] = self._compare_profiles(perf1, perf2)

        # Hierarchy proximity
        metrics["hierarchy_proximity"] = self._compute_hierarchy_proximity(agent1, agent2)

        # Weighted average
        weights = {
            "task_type_overlap": 0.5,
            "performance_profile": 0.3,
            "hierarchy_proximity": 0.2,
        }

        total_score = sum(metrics.get(k, 0.0) * w for k, w in weights.items())

        return AgentSimilarity(
            source_agent=agent1,
            target_agent=agent2,
            similarity_score=total_score,
            metrics=metrics,
            shared_task_types=list(types1 & types2) if types1 and types2 else [],
        )

    async def _is_applicable(
        self,
        pattern: LearnedPattern,
        agent_code: str,
    ) -> bool:
        """
        Check if a pattern is applicable to an agent.

        Args:
            pattern: Pattern to check
            agent_code: Target agent

        Returns:
            True if applicable
        """
        # Get agent's task types
        agent_types = await self._get_agent_task_types(agent_code)

        # Pattern must apply to at least one task type the agent handles
        pattern_task_type = self._get_pattern_task_type(pattern)
        if pattern_task_type and pattern_task_type not in agent_types:
            return False

        # Check if agent already has a similar pattern
        existing = await self._pattern_store.get_patterns(
            scope_code=agent_code,
            task_type=pattern_task_type,
            is_active=True,
        )

        for existing_pattern in existing:
            if self._patterns_are_similar(pattern, existing_pattern):
                return False

        return True

    async def _copy_pattern(
        self,
        pattern: LearnedPattern,
        target_agent: str,
        similarity: AgentSimilarity,
    ) -> bool:
        """
        Copy a pattern to a target agent.

        Args:
            pattern: Pattern to copy
            target_agent: Target agent code
            similarity: Similarity between source and target

        Returns:
            True if successful
        """
        # Create propagation record
        record = PropagationRecord(
            source_pattern_id=pattern.id,
            source_agent=pattern.scope_code,
            target_agent=target_agent,
            similarity_score=similarity.similarity_score,
            status=PropagationStatus.TESTING,
        )
        self._propagation_records[record.id] = record

        try:
            # Create new pattern for target agent
            new_pattern = LearnedPattern(
                pattern_type=pattern.pattern_type,
                scope_level=pattern.scope_level,
                scope_code=target_agent,
                condition_json=pattern.condition_json,
                recommendation=f"[Propagated] {pattern.recommendation}",
                confidence=pattern.confidence * similarity.similarity_score,  # Adjusted confidence
                is_active=True,
                success_rate=0.0,  # Will be measured
                application_count=0,
            )

            # Store the pattern
            await self._pattern_store.store_pattern(new_pattern)

            # Update record
            record.propagated_pattern_id = new_pattern.id
            record.status = PropagationStatus.SUCCESSFUL
            record.completed_at = datetime.now(timezone.utc)

            # Persist record
            await self._persist_record(record)

            logger.info(
                f"Propagated pattern {pattern.id} from {pattern.scope_code} "
                f"to {target_agent} (similarity={similarity.similarity_score:.2f})"
            )

            return True

        except Exception as e:
            record.status = PropagationStatus.FAILED
            record.notes = str(e)
            record.completed_at = datetime.now(timezone.utc)
            await self._persist_record(record)

            logger.warning(f"Failed to propagate pattern {pattern.id} to {target_agent}: {e}")
            return False

    def _has_existing_propagation(
        self,
        pattern_id: str,
        target_agent: str,
    ) -> bool:
        """Check if we've already propagated this pattern to this agent."""
        for record in self._propagation_records.values():
            if (
                record.source_pattern_id == pattern_id
                and record.target_agent == target_agent
                and record.status in (PropagationStatus.TESTING, PropagationStatus.SUCCESSFUL)
            ):
                return True
        return False

    def _get_pattern_task_type(self, pattern: LearnedPattern) -> Optional[str]:
        """Extract task_type from pattern's condition_json."""
        try:
            if pattern.condition_json:
                condition = json.loads(pattern.condition_json)
                return condition.get("task_type")
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    def _patterns_are_similar(
        self,
        pattern1: LearnedPattern,
        pattern2: LearnedPattern,
    ) -> bool:
        """Check if two patterns are similar enough to be considered duplicates."""
        # Same type and task type
        if pattern1.pattern_type != pattern2.pattern_type:
            return False
        if self._get_pattern_task_type(pattern1) != self._get_pattern_task_type(pattern2):
            return False

        # Check condition similarity
        try:
            cond1 = json.loads(pattern1.condition_json) if pattern1.condition_json else {}
            cond2 = json.loads(pattern2.condition_json) if pattern2.condition_json else {}

            # Simple comparison - could be more sophisticated
            if cond1 == cond2:
                return True

            # Check key overlap
            keys1 = set(cond1.keys())
            keys2 = set(cond2.keys())
            overlap = len(keys1 & keys2) / len(keys1 | keys2) if (keys1 | keys2) else 0

            return overlap > 0.8

        except (json.JSONDecodeError, TypeError):
            return False

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _get_all_agents(self) -> Set[str]:
        """Get all known agent codes."""
        agents: Set[str] = set()

        try:
            # Get from outcomes
            rows = await self._db.fetch_all(
                """
                SELECT DISTINCT agent_code FROM task_outcomes
                UNION
                SELECT DISTINCT manager_code FROM task_outcomes WHERE manager_code IS NOT NULL
                UNION
                SELECT DISTINCT specialist_code FROM task_outcomes WHERE specialist_code IS NOT NULL
                """
            )
            for row in rows:
                if row[0]:
                    agents.add(row[0])
        except Exception as e:
            logger.warning(f"Failed to get all agents: {e}")

        return agents

    async def _get_agent_task_types(self, agent_code: str) -> Set[str]:
        """Get task types handled by an agent."""
        if agent_code in self._agent_task_types:
            return self._agent_task_types[agent_code]

        task_types: Set[str] = set()

        try:
            rows = await self._db.fetch_all(
                """
                SELECT DISTINCT task_type FROM task_outcomes
                WHERE agent_code = ? OR manager_code = ? OR specialist_code = ?
                """,
                (agent_code, agent_code, agent_code),
            )
            for row in rows:
                if row[0]:
                    task_types.add(row[0])

            self._agent_task_types[agent_code] = task_types

        except Exception as e:
            logger.warning(f"Failed to get task types for {agent_code}: {e}")

        return task_types

    async def _get_performance_profile(
        self,
        agent_code: str,
    ) -> Dict[str, float]:
        """Get performance profile for an agent."""
        try:
            row = await self._db.fetch_one(
                """
                SELECT
                    AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                    AVG(duration_ms) as avg_duration,
                    AVG(COALESCE(effectiveness, 0.0)) as avg_effectiveness
                FROM task_outcomes
                WHERE agent_code = ? OR manager_code = ? OR specialist_code = ?
                """,
                (agent_code, agent_code, agent_code),
            )

            if row:
                return {
                    "success_rate": row[0] or 0.0,
                    "avg_duration": row[1] or 0.0,
                    "avg_effectiveness": row[2] or 0.0,
                }

        except Exception as e:
            logger.warning(f"Failed to get performance profile for {agent_code}: {e}")

        return {"success_rate": 0.0, "avg_duration": 0.0, "avg_effectiveness": 0.0}

    def _compare_profiles(
        self,
        profile1: Dict[str, float],
        profile2: Dict[str, float],
    ) -> float:
        """Compare two performance profiles."""
        if not profile1 or not profile2:
            return 0.0

        # Compare each metric
        similarities = []

        # Success rate comparison
        sr1 = profile1.get("success_rate", 0.0)
        sr2 = profile2.get("success_rate", 0.0)
        if sr1 > 0 and sr2 > 0:
            sr_sim = 1 - abs(sr1 - sr2)
            similarities.append(sr_sim)

        # Effectiveness comparison
        ef1 = profile1.get("avg_effectiveness", 0.0)
        ef2 = profile2.get("avg_effectiveness", 0.0)
        if ef1 > 0 and ef2 > 0:
            ef_sim = 1 - abs(ef1 - ef2)
            similarities.append(ef_sim)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _compute_hierarchy_proximity(
        self,
        agent1: str,
        agent2: str,
    ) -> float:
        """
        Compute hierarchy proximity between two agents.

        Agents in the same agent hierarchy are more similar.
        """
        # Simple heuristic based on agent code prefixes
        # Could be enhanced with actual hierarchy data

        # Same prefix (e.g., both start with "CTO_") = higher similarity
        prefix_len = min(len(agent1), len(agent2)) // 2
        if prefix_len > 0:
            common = sum(1 for a, b in zip(agent1[:prefix_len], agent2[:prefix_len]) if a == b)
            return common / prefix_len

        return 0.0

    # =========================================================================
    # Query Methods
    # =========================================================================

    async def get_propagation_records(
        self,
        pattern_id: Optional[str] = None,
        target_agent: Optional[str] = None,
        status: Optional[PropagationStatus] = None,
    ) -> List[PropagationRecord]:
        """
        Get propagation records.

        Args:
            pattern_id: Filter by source pattern
            target_agent: Filter by target agent
            status: Filter by status

        Returns:
            List of propagation records
        """
        records = []

        for record in self._propagation_records.values():
            if pattern_id and record.source_pattern_id != pattern_id:
                continue
            if target_agent and record.target_agent != target_agent:
                continue
            if status and record.status != status:
                continue
            records.append(record)

        return records

    async def get_propagation_candidates(
        self,
        limit: int = 20,
    ) -> List[Tuple[LearnedPattern, List[str]]]:
        """
        Get patterns that are candidates for propagation along with target agents.

        Args:
            limit: Maximum number of candidates

        Returns:
            List of (pattern, target_agents) tuples
        """
        candidates = []

        high_confidence = await self._get_high_confidence_patterns(168)

        for pattern in high_confidence[:limit]:
            if pattern.scope_level == ScopeLevel.ORGANIZATION:
                continue

            similar_agents = await self._find_similar_agents(pattern.scope_code)
            target_agents = [
                agent
                for agent, sim in similar_agents
                if sim.similarity_score >= self.MIN_SIMILARITY_FOR_PROPAGATION
                and not self._has_existing_propagation(pattern.id, agent)
            ]

            if target_agents:
                candidates.append((pattern, target_agents[:5]))  # Top 5 targets

        return candidates

    async def get_agent_similarity(
        self,
        agent1: str,
        agent2: str,
    ) -> AgentSimilarity:
        """Get similarity between two agents."""
        cache_key = (min(agent1, agent2), max(agent1, agent2))

        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]

        similarity = await self._compute_similarity(agent1, agent2)
        self._similarity_cache[cache_key] = similarity

        return similarity

    # =========================================================================
    # Propagation Testing
    # =========================================================================

    async def record_propagation_outcome(
        self,
        propagation_id: str,
        success: bool,
    ) -> None:
        """
        Record an outcome for a propagated pattern.

        Args:
            propagation_id: Propagation record ID
            success: Whether the outcome was successful
        """
        record = self._propagation_records.get(propagation_id)
        if not record:
            return

        record.test_outcomes += 1
        if success:
            record.test_successes += 1

        # Check if we have enough data to evaluate
        if record.test_outcomes >= self.MIN_TEST_OUTCOMES:
            success_rate = record.test_successes / record.test_outcomes

            if success_rate >= self.MIN_SUCCESS_RATE_FOR_PROPAGATION:
                record.status = PropagationStatus.SUCCESSFUL
                record.notes = f"Confirmed with {success_rate:.1%} success rate"
            else:
                record.status = PropagationStatus.FAILED
                record.notes = f"Failed with {success_rate:.1%} success rate"

                # Deactivate the propagated pattern
                if record.propagated_pattern_id:
                    await self._pattern_store.deactivate_pattern(
                        record.propagated_pattern_id,
                        reason="Propagation failed testing",
                    )

            record.completed_at = datetime.now(timezone.utc)
            await self._persist_record(record)

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Get propagation statistics."""
        status_counts: Dict[str, int] = {}

        for record in self._propagation_records.values():
            status = record.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        total = len(self._propagation_records)
        successful = status_counts.get("successful", 0)

        return {
            "total_propagations": total,
            "by_status": status_counts,
            "success_rate": successful / total if total > 0 else 0.0,
            "similarity_cache_size": len(self._similarity_cache),
            "agents_tracked": len(self._agent_task_types),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    async def _persist_record(self, record: PropagationRecord) -> None:
        """Persist a propagation record to the database."""
        try:
            await self._db.execute(
                """
                INSERT OR REPLACE INTO pattern_propagations (
                    id, source_pattern_id, source_agent, target_agent,
                    propagated_pattern_id, status, similarity_score,
                    created_at, completed_at, test_outcomes, test_successes, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.source_pattern_id,
                    record.source_agent,
                    record.target_agent,
                    record.propagated_pattern_id,
                    record.status.value,
                    record.similarity_score,
                    record.created_at.isoformat(),
                    record.completed_at.isoformat() if record.completed_at else None,
                    record.test_outcomes,
                    record.test_successes,
                    record.notes,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to persist propagation record: {e}")

    async def load_records(self) -> int:
        """Load propagation records from the database."""
        try:
            rows = await self._db.fetch_all("SELECT * FROM pattern_propagations")

            for row in rows:
                record = PropagationRecord(
                    id=row["id"],
                    source_pattern_id=row["source_pattern_id"],
                    source_agent=row["source_agent"],
                    target_agent=row["target_agent"],
                    propagated_pattern_id=row.get("propagated_pattern_id"),
                    status=PropagationStatus(row["status"]),
                    similarity_score=row.get("similarity_score", 0.0),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    completed_at=(
                        datetime.fromisoformat(row["completed_at"])
                        if row.get("completed_at")
                        else None
                    ),
                    test_outcomes=row.get("test_outcomes", 0),
                    test_successes=row.get("test_successes", 0),
                    notes=row.get("notes", ""),
                )
                self._propagation_records[record.id] = record

            return len(rows)

        except Exception as e:
            logger.warning(f"Failed to load propagation records: {e}")
            return 0

    def clear_cache(self) -> None:
        """Clear similarity cache."""
        self._similarity_cache.clear()
        self._agent_task_types.clear()
