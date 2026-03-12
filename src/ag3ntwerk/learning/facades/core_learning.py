"""
Core Learning Facade - Outcome tracking, pattern storage, and learning loops.

This facade manages the foundational learning components:
- OutcomeTracker: Records task outcomes
- PatternStore: Stores and retrieves learned patterns
- IssueManager: Creates and tracks learning issues
- Learning Loops: Agent, Manager, and Specialist loops
"""

import logging
from typing import Any, Dict, List, Optional

from datetime import datetime, timezone

from ag3ntwerk.learning.issue_manager import IssueManager
from ag3ntwerk.learning.models import (
    HierarchyPath,
    LearnedPattern,
    LearningAdjustment,
    LearningIssue,
    ScopeLevel,
    TaskOutcomeRecord,
)
from ag3ntwerk.learning.outcome_tracker import OutcomeTracker
from ag3ntwerk.learning.pattern_store import PatternStore
from ag3ntwerk.learning.loops.agent_loop import ExecutiveLearningLoop
from ag3ntwerk.learning.loops.manager_loop import ManagerLearningLoop
from ag3ntwerk.learning.loops.specialist_loop import SpecialistLearningLoop

logger = logging.getLogger(__name__)


class CoreLearningFacade:
    """
    Facade for core learning operations.

    Manages outcome tracking, pattern storage, issue management,
    and the hierarchy of learning loops.
    """

    def __init__(
        self,
        db: Any,
        task_queue: Optional[Any],
        outcome_tracker: OutcomeTracker,
        pattern_store: PatternStore,
    ):
        """
        Initialize the core learning facade.

        Args:
            db: Database connection
            task_queue: Optional task queue for issue task creation
            outcome_tracker: Shared outcome tracker instance
            pattern_store: Shared pattern store instance
        """
        self._db = db
        self._task_queue = task_queue
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store
        self._issue_manager = IssueManager(db, task_queue)

        # Learning loops by agent code
        self._agent_loops: Dict[str, ExecutiveLearningLoop] = {}
        self._manager_loops: Dict[str, ManagerLearningLoop] = {}
        self._specialist_loops: Dict[str, SpecialistLearningLoop] = {}

    # --- Registration methods ---

    def register_executive(
        self,
        agent_code: str,
        managers: List[str],
    ) -> None:
        """
        Register an agent and create its learning loop.

        Args:
            agent_code: Agent agent code (e.g., "Forge")
            managers: List of manager codes under this agent
        """
        loop = ExecutiveLearningLoop(
            agent_code=agent_code,
            managers=managers,
            pattern_store=self._pattern_store,
            db=self._db,
        )
        self._agent_loops[agent_code] = loop
        logger.info(f"Registered agent learning loop: {agent_code}")

    def register_manager(
        self,
        manager_code: str,
        agent_code: str,
        specialists: List[str],
    ) -> None:
        """
        Register a manager and create its learning loop.

        Args:
            manager_code: Manager agent code (e.g., "AM")
            agent_code: Parent agent code
            specialists: List of specialist codes under this manager
        """
        loop = ManagerLearningLoop(
            manager_code=manager_code,
            agent_code=agent_code,
            specialists=specialists,
            pattern_store=self._pattern_store,
            db=self._db,
        )
        self._manager_loops[manager_code] = loop
        logger.info(f"Registered manager learning loop: {manager_code}")

    def register_specialist(
        self,
        specialist_code: str,
        manager_code: str,
        capabilities: Optional[List[str]] = None,
    ) -> None:
        """
        Register a specialist and create its learning loop.

        Args:
            specialist_code: Specialist agent code (e.g., "SD")
            manager_code: Parent manager code
            capabilities: List of capabilities this specialist has
        """
        loop = SpecialistLearningLoop(
            specialist_code=specialist_code,
            manager_code=manager_code,
            capabilities=capabilities or [],
            pattern_store=self._pattern_store,
            db=self._db,
        )
        self._specialist_loops[specialist_code] = loop
        logger.info(f"Registered specialist learning loop: {specialist_code}")

    # --- Outcome recording ---

    async def record_outcome(
        self,
        task_id: str,
        task_type: str,
        hierarchy_path: HierarchyPath,
        success: bool,
        duration_ms: float = 0.0,
        effectiveness: Optional[float] = None,
        confidence: Optional[float] = None,
        actual_accuracy: Optional[float] = None,
        error: Optional[str] = None,
        output_summary: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        applied_pattern_ids: Optional[List[str]] = None,
        was_routing_influenced: bool = False,
        was_confidence_calibrated: bool = False,
    ) -> str:
        """
        Record a task outcome.

        This is the main entry point called after every task execution.

        Args:
            task_id: ID of the executed task
            task_type: Type of task
            hierarchy_path: Path through hierarchy
            success: Whether task succeeded
            duration_ms: Execution duration
            effectiveness: Effectiveness score (0-1)
            confidence: Initial confidence
            actual_accuracy: Post-hoc accuracy
            error: Error message if failed
            output_summary: Summary of output
            context: Additional context
            applied_pattern_ids: IDs of patterns that influenced this task
            was_routing_influenced: Whether routing was influenced by patterns
            was_confidence_calibrated: Whether confidence was calibrated

        Returns:
            Outcome record ID
        """
        outcome_id = await self._outcome_tracker.record_outcome(
            task_id=task_id,
            task_type=task_type,
            hierarchy_path=hierarchy_path,
            success=success,
            duration_ms=duration_ms,
            effectiveness=effectiveness,
            confidence=confidence,
            actual_accuracy=actual_accuracy,
            error=error,
            output_summary=output_summary,
            context=context,
            applied_pattern_ids=applied_pattern_ids,
            was_routing_influenced=was_routing_influenced,
            was_confidence_calibrated=was_confidence_calibrated,
        )

        # Update performance metrics for each agent in the hierarchy
        outcome = TaskOutcomeRecord(
            task_id=task_id,
            task_type=task_type,
            agent_code=hierarchy_path.agent,
            manager_code=hierarchy_path.manager,
            specialist_code=hierarchy_path.specialist,
            success=success,
            effectiveness=effectiveness or (1.0 if success else 0.0),
            duration_ms=duration_ms,
            initial_confidence=confidence,
            actual_accuracy=actual_accuracy,
            applied_pattern_ids=applied_pattern_ids or [],
            was_routing_influenced=was_routing_influenced,
            was_confidence_calibrated=was_confidence_calibrated,
        )

        # Update agent metrics
        if hierarchy_path.agent in self._agent_loops:
            await self._agent_loops[hierarchy_path.agent].update_performance_metrics(
                outcome
            )

        # Update manager metrics
        if hierarchy_path.manager and hierarchy_path.manager in self._manager_loops:
            await self._manager_loops[hierarchy_path.manager].update_performance_metrics(outcome)

        # Update specialist metrics
        if hierarchy_path.specialist and hierarchy_path.specialist in self._specialist_loops:
            await self._specialist_loops[hierarchy_path.specialist].update_performance_metrics(
                outcome
            )

        return outcome_id

    # --- Task adjustments ---

    async def get_task_adjustments(
        self,
        task_type: str,
        target_agent: str,
    ) -> LearningAdjustment:
        """
        Get learning-based adjustments for a task before execution.

        Called by Nexus/managers before delegating a task.

        Args:
            task_type: Type of task
            target_agent: Agent code that will handle the task

        Returns:
            Adjustments to apply
        """
        adjustments = LearningAdjustment()

        # Check agent loop
        if target_agent in self._agent_loops:
            loop = self._agent_loops[target_agent]
            patterns = await loop.get_applicable_patterns(task_type)
            exec_adj = await loop.apply_learning(task_type, patterns)
            adjustments.merge(exec_adj)

            # Track pattern application
            for pattern_id in exec_adj.applied_pattern_ids:
                await self._pattern_store.update_pattern_stats(pattern_id, applied=True)

        # Check manager loop
        elif target_agent in self._manager_loops:
            loop = self._manager_loops[target_agent]
            patterns = await loop.get_applicable_patterns(task_type)
            mgr_adj = await loop.apply_learning(task_type, patterns)
            adjustments.merge(mgr_adj)

            for pattern_id in mgr_adj.applied_pattern_ids:
                await self._pattern_store.update_pattern_stats(pattern_id, applied=True)

        # Check specialist loop
        elif target_agent in self._specialist_loops:
            loop = self._specialist_loops[target_agent]
            patterns = await loop.get_applicable_patterns(task_type)
            spec_adj = await loop.apply_learning(task_type, patterns)
            adjustments.merge(spec_adj)

            for pattern_id in spec_adj.applied_pattern_ids:
                await self._pattern_store.update_pattern_stats(pattern_id, applied=True)

        return adjustments

    # --- Pattern queries ---

    async def get_patterns(
        self,
        scope: Optional[ScopeLevel] = None,
        pattern_type: Optional[str] = None,
        agent_code: Optional[str] = None,
        min_effectiveness: Optional[float] = None,
    ) -> List[LearnedPattern]:
        """
        Get patterns matching criteria.

        Args:
            scope: Scope level filter
            pattern_type: Pattern type filter
            agent_code: Agent code filter
            min_effectiveness: Minimum effectiveness filter

        Returns:
            List of matching patterns
        """
        return await self._pattern_store.get_patterns(
            scope=scope,
            pattern_type=pattern_type,
            agent_code=agent_code,
            min_effectiveness=min_effectiveness,
        )

    async def get_open_issues(
        self,
        agent_code: Optional[str] = None,
    ) -> List[LearningIssue]:
        """
        Get open issues, optionally filtered by agent.

        Args:
            agent_code: Optional agent code filter

        Returns:
            List of open issues
        """
        return await self._issue_manager.get_open_issues(agent_code=agent_code)

    # --- Analysis ---

    async def run_analysis_cycle(self) -> Dict[str, Any]:
        """
        Run one analysis cycle across all loops.

        Returns:
            Analysis results summary
        """
        results = {
            "executive_results": {},
            "manager_results": {},
            "specialist_results": {},
            "new_patterns": 0,
            "updated_patterns": 0,
            "new_issues": 0,
        }

        # Get outcomes grouped by hierarchy level
        outcomes_by_hierarchy = await self._outcome_tracker.get_outcomes_by_hierarchy(
            window_hours=24
        )

        # Analyze agent loops
        executive_outcomes = outcomes_by_hierarchy.get("agent", {})
        for code, loop in self._agent_loops.items():
            agent_outcomes = executive_outcomes.get(code, [])
            patterns = await loop.analyze_outcomes(agent_outcomes)
            results["executive_results"][code] = {
                "patterns_detected": len(patterns),
                "outcomes_analyzed": len(agent_outcomes),
            }
            # Store detected patterns
            for pattern in patterns:
                await self._pattern_store.store_pattern(pattern)
                results["new_patterns"] += 1

        # Analyze manager loops
        manager_outcomes = outcomes_by_hierarchy.get("manager", {})
        for code, loop in self._manager_loops.items():
            agent_outcomes = manager_outcomes.get(code, [])
            patterns = await loop.analyze_outcomes(agent_outcomes)
            results["manager_results"][code] = {
                "patterns_detected": len(patterns),
                "outcomes_analyzed": len(agent_outcomes),
            }
            for pattern in patterns:
                await self._pattern_store.store_pattern(pattern)
                results["new_patterns"] += 1

        # Analyze specialist loops
        specialist_outcomes = outcomes_by_hierarchy.get("specialist", {})
        for code, loop in self._specialist_loops.items():
            agent_outcomes = specialist_outcomes.get(code, [])
            patterns = await loop.analyze_outcomes(agent_outcomes)
            results["specialist_results"][code] = {
                "patterns_detected": len(patterns),
                "outcomes_analyzed": len(agent_outcomes),
            }
            for pattern in patterns:
                await self._pattern_store.store_pattern(pattern)
                results["new_patterns"] += 1

        # Detect issues (delegated to individual loops during analysis)
        # No centralized issue detection - each loop detects its own issues
        results["new_issues"] = 0

        # Add legacy/expected fields for backward compatibility
        results["timestamp"] = datetime.now(timezone.utc).isoformat()
        results["patterns_detected"] = results["new_patterns"]
        results["issues_detected"] = results["new_issues"]

        return results

    # --- Stats ---

    async def get_stats(self) -> Dict[str, Any]:
        """Get core learning statistics."""
        stats = {
            "agent_loops": len(self._agent_loops),
            "manager_loops": len(self._manager_loops),
            "specialist_loops": len(self._specialist_loops),
        }

        # Outcome tracker stats - get outcomes by hierarchy for summary
        try:
            outcomes_by_hierarchy = await self._outcome_tracker.get_outcomes_by_hierarchy(
                window_hours=24
            )
            total_outcomes = sum(
                len(outcomes)
                for level_outcomes in outcomes_by_hierarchy.values()
                for outcomes in level_outcomes.values()
            )
            stats["outcome_stats"] = {
                "total_outcomes_24h": total_outcomes,
                "agents": len(outcomes_by_hierarchy.get("agent", {})),
                "managers": len(outcomes_by_hierarchy.get("manager", {})),
                "specialists": len(outcomes_by_hierarchy.get("specialist", {})),
            }
        except Exception as e:
            logger.debug("Failed to collect outcome stats: %s", e)
            stats["outcome_stats"] = {}

        # Pattern store stats - count patterns
        try:
            patterns = await self._pattern_store.get_patterns()
            stats["pattern_stats"] = {
                "total_patterns": len(patterns),
            }
        except Exception as e:
            logger.debug("Failed to collect pattern stats: %s", e)
            stats["pattern_stats"] = {}

        # Issue manager stats
        try:
            if hasattr(self._issue_manager, "get_issue_stats"):
                stats["issue_stats"] = await self._issue_manager.get_issue_stats()
            else:
                open_issues = await self._issue_manager.get_open_issues()
                stats["issue_stats"] = {"open_issues": len(open_issues)}
        except Exception as e:
            logger.debug("Failed to collect issue stats: %s", e)
            stats["issue_stats"] = {}

        return stats

    # --- Accessors for loops (used by orchestrator) ---

    @property
    def agent_loops(self) -> Dict[str, ExecutiveLearningLoop]:
        """Get agent loops dictionary."""
        return self._agent_loops

    @property
    def manager_loops(self) -> Dict[str, ManagerLearningLoop]:
        """Get manager loops dictionary."""
        return self._manager_loops

    @property
    def specialist_loops(self) -> Dict[str, SpecialistLearningLoop]:
        """Get specialist loops dictionary."""
        return self._specialist_loops

    @property
    def issue_manager(self) -> IssueManager:
        """Get issue manager."""
        return self._issue_manager
