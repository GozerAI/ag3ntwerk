"""
Evolution Facade - Capability evolution, pattern propagation, and failure investigation.

This facade manages advanced feedback loop components:
- CapabilityEvolver: Evolves agent capabilities based on demand
- PatternPropagator: Propagates successful patterns to similar agents
- FailureInvestigator: Investigates failures and recommends fixes
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.learning.capability_evolver import (
    CapabilityEvolver,
    NewCapability,
    DemandGap,
    EvolutionStatus,
)
from ag3ntwerk.learning.failure_investigator import (
    FailureInvestigator,
    Investigation,
    RootCause,
    RecommendedFix,
)
from ag3ntwerk.learning.models import TaskOutcomeRecord
from ag3ntwerk.learning.outcome_tracker import OutcomeTracker
from ag3ntwerk.learning.pattern_propagator import (
    PatternPropagator,
    PropagationRecord,
    PropagationResult,
    AgentSimilarity,
)
from ag3ntwerk.learning.pattern_store import PatternStore

logger = logging.getLogger(__name__)


class EvolutionFacade:
    """
    Facade for advanced feedback loop operations.

    Manages capability evolution, pattern propagation,
    and failure investigation.
    """

    def __init__(
        self,
        db: Any,
        outcome_tracker: OutcomeTracker,
        pattern_store: PatternStore,
    ):
        """
        Initialize the evolution facade.

        Args:
            db: Database connection
            outcome_tracker: Shared outcome tracker instance
            pattern_store: Shared pattern store instance
        """
        self._db = db
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store
        self._capability_evolver = CapabilityEvolver(db, pattern_store, outcome_tracker)
        self._pattern_propagator = PatternPropagator(db, pattern_store, outcome_tracker)
        self._failure_investigator = FailureInvestigator(db, outcome_tracker, pattern_store)

    # --- Capability Evolution ---

    def get_capability_evolver(self) -> CapabilityEvolver:
        """Get the capability evolver."""
        return self._capability_evolver

    async def evolve_capabilities(
        self,
        agent_code: str,
        window_hours: int = 168,
    ) -> List[NewCapability]:
        """
        Evolve capabilities for an agent based on demand patterns.

        Args:
            agent_code: Agent to evolve capabilities for
            window_hours: Time window for analysis

        Returns:
            List of new or updated capabilities
        """
        return await self._capability_evolver.evolve_capabilities(
            agent_code=agent_code,
            window_hours=window_hours,
        )

    async def get_agent_capabilities(
        self,
        agent_code: str,
        status: Optional[EvolutionStatus] = None,
    ) -> List[NewCapability]:
        """Get capabilities for an agent."""
        return await self._capability_evolver.get_agent_capabilities(agent_code, status)

    async def get_active_capabilities(
        self,
        agent_code: Optional[str] = None,
    ) -> List[NewCapability]:
        """Get all active capabilities."""
        return await self._capability_evolver.get_active_capabilities(agent_code)

    async def get_demand_gaps(
        self,
        agent_code: Optional[str] = None,
        min_severity: float = 0.0,
    ) -> List[DemandGap]:
        """Get detected demand gaps."""
        return await self._capability_evolver.get_detected_gaps(agent_code, min_severity)

    async def start_capability_testing(self, capability_id: str) -> bool:
        """Start testing a proposed capability."""
        return await self._capability_evolver.start_testing(capability_id)

    async def record_capability_usage(
        self,
        capability_id: str,
        success: bool,
        duration_ms: float = 0.0,
    ) -> None:
        """Record usage of a capability."""
        await self._capability_evolver.record_capability_usage(
            capability_id=capability_id,
            success=success,
            duration_ms=duration_ms,
        )

    # --- Pattern Propagation ---

    def get_pattern_propagator(self) -> PatternPropagator:
        """Get the pattern propagator."""
        return self._pattern_propagator

    async def propagate_patterns(
        self,
        window_hours: int = 168,
    ) -> PropagationResult:
        """
        Propagate successful patterns to similar agents.

        Args:
            window_hours: Time window for pattern analysis

        Returns:
            PropagationResult with statistics
        """
        return await self._pattern_propagator.propagate_successful_patterns(window_hours)

    async def get_propagation_candidates(
        self,
        limit: int = 20,
    ) -> List[tuple]:
        """Get patterns that are candidates for propagation."""
        return await self._pattern_propagator.get_propagation_candidates(limit)

    async def get_agent_similarity(
        self,
        agent1: str,
        agent2: str,
    ) -> AgentSimilarity:
        """Get similarity between two agents."""
        return await self._pattern_propagator.get_agent_similarity(agent1, agent2)

    async def get_propagation_records(
        self,
        pattern_id: Optional[str] = None,
        target_agent: Optional[str] = None,
    ) -> List[PropagationRecord]:
        """Get propagation records."""
        return await self._pattern_propagator.get_propagation_records(
            pattern_id=pattern_id,
            target_agent=target_agent,
        )

    # --- Failure Investigation ---

    def get_failure_investigator(self) -> FailureInvestigator:
        """Get the failure investigator."""
        return self._failure_investigator

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
        return await self._failure_investigator.investigate_failure(outcome)

    async def investigate_failures_batch(
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
        return await self._failure_investigator.investigate_batch(
            window_hours=window_hours,
            min_failure_rate=min_failure_rate,
        )

    async def get_investigation(
        self,
        investigation_id: str,
    ) -> Optional[Investigation]:
        """Get an investigation by ID."""
        return await self._failure_investigator.get_investigation(investigation_id)

    async def get_investigations(
        self,
        task_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Investigation]:
        """Get investigations with optional filters."""
        return await self._failure_investigator.get_investigations(
            task_type=task_type,
            limit=limit,
        )

    async def get_common_root_causes(
        self,
        window_hours: int = 168,
        limit: int = 10,
    ) -> List[tuple]:
        """Get the most common root causes."""
        return await self._failure_investigator.get_common_root_causes(
            window_hours=window_hours,
            limit=limit,
        )

    async def get_auto_applicable_fixes(self) -> List[RecommendedFix]:
        """Get all auto-applicable fixes from recent investigations."""
        return await self._failure_investigator.get_auto_applicable_fixes()

    # --- Orchestration ---

    async def run_feedback_cycle(
        self,
        window_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Run a complete feedback cycle (Phase 8).

        Includes capability evolution, pattern propagation, and failure investigation.

        Args:
            window_hours: Time window for analysis

        Returns:
            Summary of actions taken
        """
        results: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capabilities": {},
            "propagation": {},
            "investigations": {},
        }

        # Run pattern propagation
        propagation_result = await self.propagate_patterns(window_hours * 7)
        results["propagation"] = propagation_result.to_dict()

        # Run batch failure investigation
        investigations = await self.investigate_failures_batch(window_hours)
        results["investigations"] = {
            "count": len(investigations),
            "auto_fixes_available": len(await self.get_auto_applicable_fixes()),
        }

        # Get capability stats (evolution runs per-agent, not globally)
        evolver_stats = await self._capability_evolver.get_stats()
        results["capabilities"] = evolver_stats

        return results

    # --- Stats ---

    async def get_stats(self) -> Dict[str, Any]:
        """Get evolution facade statistics."""
        return {
            "capability_evolver": await self._capability_evolver.get_stats(),
            "pattern_propagator": (
                await self._pattern_propagator.get_stats()
                if hasattr(self._pattern_propagator, "get_stats")
                else {}
            ),
            "failure_investigator": (
                await self._failure_investigator.get_stats()
                if hasattr(self._failure_investigator, "get_stats")
                else {}
            ),
        }

    # --- Accessors for components (used by orchestrator) ---

    @property
    def capability_evolver(self) -> CapabilityEvolver:
        """Get capability evolver."""
        return self._capability_evolver

    @property
    def pattern_propagator(self) -> PatternPropagator:
        """Get pattern propagator."""
        return self._pattern_propagator

    @property
    def failure_investigator(self) -> FailureInvestigator:
        """Get failure investigator."""
        return self._failure_investigator
