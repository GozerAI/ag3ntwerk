"""
Workbench Bridge - Connects learning system to the Workbench UI.

Provides:
- Learning dashboard data aggregation
- Approval workflow management from UI
- Real-time learning insights
- Pattern and experiment visualization
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ag3ntwerk.learning.orchestrator import LearningOrchestrator

logger = logging.getLogger(__name__)


@dataclass
class LearningDashboard:
    """
    Aggregated learning system data for dashboard display.
    """

    # Pattern statistics
    active_patterns: int = 0
    total_patterns: int = 0
    patterns_by_type: Dict[str, int] = field(default_factory=dict)
    top_performing_patterns: List[Dict[str, Any]] = field(default_factory=list)

    # Experiment statistics
    active_experiments: int = 0
    completed_experiments: int = 0
    recent_experiments: List[Dict[str, Any]] = field(default_factory=list)
    experiment_success_rate: float = 0.0

    # Opportunity feed
    open_opportunities: int = 0
    opportunity_feed: List[Dict[str, Any]] = field(default_factory=list)
    opportunities_by_priority: Dict[str, int] = field(default_factory=dict)

    # Autonomy statistics
    autonomy_stats: Dict[str, Any] = field(default_factory=dict)
    pending_approvals: int = 0
    recent_approvals: List[Dict[str, Any]] = field(default_factory=list)

    # Pipeline status
    pipeline_state: str = "stopped"
    pipeline_stats: Dict[str, Any] = field(default_factory=dict)
    recent_cycles: List[Dict[str, Any]] = field(default_factory=list)

    # Performance overview
    overall_success_rate: float = 0.0
    tasks_today: int = 0
    average_confidence_calibration: float = 0.0

    # Metadata
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data_freshness_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "patterns": {
                "active": self.active_patterns,
                "total": self.total_patterns,
                "by_type": self.patterns_by_type,
                "top_performing": self.top_performing_patterns,
            },
            "experiments": {
                "active": self.active_experiments,
                "completed": self.completed_experiments,
                "recent": self.recent_experiments,
                "success_rate": self.experiment_success_rate,
            },
            "opportunities": {
                "open": self.open_opportunities,
                "feed": self.opportunity_feed,
                "by_priority": self.opportunities_by_priority,
            },
            "autonomy": {
                "stats": self.autonomy_stats,
                "pending_approvals": self.pending_approvals,
                "recent_approvals": self.recent_approvals,
            },
            "pipeline": {
                "state": self.pipeline_state,
                "stats": self.pipeline_stats,
                "recent_cycles": self.recent_cycles,
            },
            "performance": {
                "overall_success_rate": self.overall_success_rate,
                "tasks_today": self.tasks_today,
                "avg_confidence_calibration": self.average_confidence_calibration,
            },
            "metadata": {
                "generated_at": self.generated_at.isoformat(),
                "data_freshness_seconds": self.data_freshness_seconds,
            },
        }


@dataclass
class AgentInsight:
    """Insight about a specific agent's learning performance."""

    agent_code: str
    agent_level: str
    success_rate: float
    task_count: int
    avg_duration_ms: float
    confidence_calibration: float
    active_patterns: int
    performance_trend: str  # "improving", "stable", "declining"
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "agent_level": self.agent_level,
            "success_rate": self.success_rate,
            "task_count": self.task_count,
            "avg_duration_ms": self.avg_duration_ms,
            "confidence_calibration": self.confidence_calibration,
            "active_patterns": self.active_patterns,
            "performance_trend": self.performance_trend,
            "recommendations": self.recommendations,
        }


@dataclass
class ApprovalAction:
    """Result of an approval action."""

    approval_id: str
    action: str  # "approved", "rejected"
    processed_at: datetime
    processed_by: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "action": self.action,
            "processed_at": self.processed_at.isoformat(),
            "processed_by": self.processed_by,
            "notes": self.notes,
        }


class WorkbenchBridge:
    """
    Bridge between the learning system and Workbench UI.

    Provides data aggregation and approval workflow management.
    """

    # Cache TTL for dashboard data (seconds)
    DASHBOARD_CACHE_TTL = 30

    def __init__(self, orchestrator: "LearningOrchestrator"):
        """
        Initialize the workbench bridge.

        Args:
            orchestrator: Learning orchestrator instance
        """
        self._orchestrator = orchestrator
        self._dashboard_cache: Optional[LearningDashboard] = None
        self._cache_updated_at: Optional[datetime] = None

    async def get_learning_dashboard(
        self,
        refresh: bool = False,
    ) -> LearningDashboard:
        """
        Get aggregated learning dashboard data.

        Args:
            refresh: Force refresh even if cache is valid

        Returns:
            LearningDashboard with aggregated data
        """
        now = datetime.now(timezone.utc)

        # Check cache
        if not refresh and self._dashboard_cache and self._cache_updated_at:
            age = (now - self._cache_updated_at).total_seconds()
            if age < self.DASHBOARD_CACHE_TTL:
                self._dashboard_cache.data_freshness_seconds = age
                return self._dashboard_cache

        # Build fresh dashboard
        dashboard = await self._build_dashboard()
        self._dashboard_cache = dashboard
        self._cache_updated_at = now

        return dashboard

    async def _build_dashboard(self) -> LearningDashboard:
        """Build a fresh dashboard from current data."""
        dashboard = LearningDashboard()

        try:
            # Pattern statistics
            await self._populate_pattern_stats(dashboard)
        except Exception as e:
            logger.warning(f"Failed to populate pattern stats: {e}")

        try:
            # Experiment statistics
            await self._populate_experiment_stats(dashboard)
        except Exception as e:
            logger.warning(f"Failed to populate experiment stats: {e}")

        try:
            # Opportunity feed
            await self._populate_opportunity_stats(dashboard)
        except Exception as e:
            logger.warning(f"Failed to populate opportunity stats: {e}")

        try:
            # Autonomy statistics
            await self._populate_autonomy_stats(dashboard)
        except Exception as e:
            logger.warning(f"Failed to populate autonomy stats: {e}")

        try:
            # Pipeline status
            await self._populate_pipeline_stats(dashboard)
        except Exception as e:
            logger.warning(f"Failed to populate pipeline stats: {e}")

        try:
            # Performance overview
            await self._populate_performance_stats(dashboard)
        except Exception as e:
            logger.warning(f"Failed to populate performance stats: {e}")

        return dashboard

    async def _populate_pattern_stats(self, dashboard: LearningDashboard) -> None:
        """Populate pattern statistics."""
        pattern_store = self._orchestrator._pattern_store

        # Get all patterns
        all_patterns = await pattern_store.get_patterns(is_active=None)
        active_patterns = [p for p in all_patterns if p.is_active]

        dashboard.total_patterns = len(all_patterns)
        dashboard.active_patterns = len(active_patterns)

        # Group by type
        type_counts: Dict[str, int] = {}
        for p in active_patterns:
            type_name = p.pattern_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        dashboard.patterns_by_type = type_counts

        # Top performing patterns (by success rate and sample size)
        sorted_patterns = sorted(
            [p for p in active_patterns if p.sample_size >= 10],
            key=lambda p: (p.success_rate or 0, p.sample_size),
            reverse=True,
        )[:5]
        dashboard.top_performing_patterns = [
            {
                "id": p.id,
                "type": p.pattern_type.value,
                "scope": p.scope_code,
                "success_rate": p.success_rate,
                "sample_size": p.sample_size,
                "confidence": p.confidence,
            }
            for p in sorted_patterns
        ]

    async def _populate_experiment_stats(self, dashboard: LearningDashboard) -> None:
        """Populate experiment statistics."""
        experimenter = self._orchestrator._pattern_experimenter
        if not experimenter:
            return

        # Get experiments
        active = await experimenter.get_active_experiments()
        recent_results = await experimenter.get_recent_results(limit=10)

        dashboard.active_experiments = len(active)
        dashboard.completed_experiments = len(recent_results)

        # Success rate
        if recent_results:
            successful = sum(1 for r in recent_results if r.is_positive)
            dashboard.experiment_success_rate = successful / len(recent_results)

        # Recent experiments
        dashboard.recent_experiments = [
            {
                "id": exp.id,
                "pattern_id": exp.pattern_id,
                "status": exp.status.value,
                "started_at": exp.started_at.isoformat() if exp.started_at else None,
            }
            for exp in active[:5]
        ]

    async def _populate_opportunity_stats(self, dashboard: LearningDashboard) -> None:
        """Populate opportunity statistics."""
        detector = self._orchestrator._opportunity_detector
        if not detector:
            return

        # Get open opportunities
        opportunities = await detector.get_open_opportunities(limit=20)
        dashboard.open_opportunities = len(opportunities)

        # Group by priority
        priority_counts: Dict[str, int] = {}
        for opp in opportunities:
            priority = opp.priority.value
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        dashboard.opportunities_by_priority = priority_counts

        # Opportunity feed (top 10)
        dashboard.opportunity_feed = [
            {
                "id": opp.id,
                "type": opp.opportunity_type.value,
                "priority": opp.priority.value,
                "description": opp.description,
                "impact_score": opp.impact_score,
                "created_at": opp.created_at.isoformat(),
            }
            for opp in opportunities[:10]
        ]

    async def _populate_autonomy_stats(self, dashboard: LearningDashboard) -> None:
        """Populate autonomy statistics."""
        controller = self._orchestrator._autonomy_controller
        if not controller:
            return

        # Get stats
        stats = await controller.get_stats()
        dashboard.autonomy_stats = stats

        # Get pending approvals
        pending = await controller.get_pending_approvals()
        dashboard.pending_approvals = len(pending)

        # Recent approvals
        dashboard.recent_approvals = [
            {
                "id": p.id,
                "action": p.action,
                "category": p.category.value,
                "description": p.description,
                "created_at": p.created_at.isoformat(),
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            }
            for p in pending[:5]
        ]

    async def _populate_pipeline_stats(self, dashboard: LearningDashboard) -> None:
        """Populate pipeline statistics."""
        pipeline = self._orchestrator._continuous_pipeline
        if not pipeline:
            return

        # Get state and stats
        dashboard.pipeline_state = pipeline._state.value
        dashboard.pipeline_stats = await pipeline.get_stats()

        # Recent cycles
        history = pipeline.get_cycle_history(limit=5)
        dashboard.recent_cycles = [
            {
                "id": cycle.cycle_id,
                "started_at": cycle.started_at.isoformat(),
                "duration_ms": cycle.duration_ms,
                "success": cycle.success,
                "outcomes_collected": cycle.outcomes_collected,
                "patterns_detected": cycle.patterns_detected,
            }
            for cycle in history
        ]

    async def _populate_performance_stats(self, dashboard: LearningDashboard) -> None:
        """Populate performance overview."""
        stats = await self._orchestrator.get_stats()

        # Overall success rate from outcome tracker
        tracker = self._orchestrator._outcome_tracker
        today_outcomes = await tracker.get_outcomes(
            window_hours=24,
            limit=1000,
        )

        if today_outcomes:
            dashboard.tasks_today = len(today_outcomes)
            successes = sum(1 for o in today_outcomes if o.success)
            dashboard.overall_success_rate = successes / len(today_outcomes)

        # Get average calibration score
        calibrator = self._orchestrator._confidence_calibrator
        if calibrator and calibrator._curves:
            total_score = 0.0
            count = 0
            for curve in calibrator._curves.values():
                if curve.total_predictions >= 10:
                    total_score += curve.calibration_score
                    count += 1
            if count > 0:
                dashboard.average_confidence_calibration = total_score / count

    # =========================================================================
    # Approval Workflow
    # =========================================================================

    async def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """
        Get all pending approval requests.

        Returns:
            List of pending approvals as dictionaries
        """
        controller = self._orchestrator._autonomy_controller
        if not controller:
            return []

        pending = await controller.get_pending_approvals()
        return [
            {
                "id": p.id,
                "action": p.action,
                "category": p.category.value,
                "description": p.description,
                "context": p.context,
                "impact_assessment": p.impact_assessment,
                "recommended_decision": p.recommended_decision,
                "created_at": p.created_at.isoformat(),
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            }
            for p in pending
        ]

    async def approve_action(
        self,
        approval_id: str,
        approved_by: str = "workbench_user",
        notes: Optional[str] = None,
    ) -> ApprovalAction:
        """
        Approve a pending action.

        Args:
            approval_id: ID of the approval to process
            approved_by: Identifier of who approved
            notes: Optional notes

        Returns:
            ApprovalAction result
        """
        controller = self._orchestrator._autonomy_controller
        if not controller:
            raise ValueError("Autonomy controller not available")

        await controller.process_approval(approval_id, approved=True, decided_by=approved_by)

        return ApprovalAction(
            approval_id=approval_id,
            action="approved",
            processed_at=datetime.now(timezone.utc),
            processed_by=approved_by,
            notes=notes,
        )

    async def reject_action(
        self,
        approval_id: str,
        rejected_by: str = "workbench_user",
        notes: Optional[str] = None,
    ) -> ApprovalAction:
        """
        Reject a pending action.

        Args:
            approval_id: ID of the approval to process
            rejected_by: Identifier of who rejected
            notes: Optional notes

        Returns:
            ApprovalAction result
        """
        controller = self._orchestrator._autonomy_controller
        if not controller:
            raise ValueError("Autonomy controller not available")

        await controller.process_approval(approval_id, approved=False, decided_by=rejected_by)

        return ApprovalAction(
            approval_id=approval_id,
            action="rejected",
            processed_at=datetime.now(timezone.utc),
            processed_by=rejected_by,
            notes=notes,
        )

    # =========================================================================
    # Agent Insights
    # =========================================================================

    async def get_agent_insight(self, agent_code: str) -> AgentInsight:
        """
        Get detailed learning insight for an agent.

        Args:
            agent_code: Agent code to get insight for

        Returns:
            AgentInsight with detailed metrics
        """
        # Get outcome stats
        tracker = self._orchestrator._outcome_tracker
        stats = await tracker.get_outcome_stats(agent_code, window_hours=168)  # 7 days

        # Get patterns
        pattern_store = self._orchestrator._pattern_store
        patterns = await pattern_store.get_patterns(
            scope_code=agent_code,
            is_active=True,
        )

        # Get calibration
        calibrator = self._orchestrator._confidence_calibrator
        calibration_summary = await calibrator.get_agent_calibration_summary(agent_code)

        # Determine level
        agent_level = "agent"
        if agent_code in self._orchestrator._manager_loops:
            agent_level = "manager"
        elif agent_code in self._orchestrator._specialist_loops:
            agent_level = "specialist"

        # Determine trend
        trend = "stable"
        # Could compare recent vs historical success rates

        # Generate recommendations
        recommendations = []
        if stats.get("success_rate", 0) < 0.7:
            recommendations.append("Consider reviewing error patterns")
        if calibration_summary.get("tendency") == "over-confident":
            recommendations.append("Agent tends to be over-confident - consider calibration")
        if len(patterns) < 3:
            recommendations.append("Limited learned patterns - more task variety recommended")

        return AgentInsight(
            agent_code=agent_code,
            agent_level=agent_level,
            success_rate=stats.get("success_rate", 0.0),
            task_count=stats.get("total", 0),
            avg_duration_ms=stats.get("avg_duration_ms", 0.0),
            confidence_calibration=calibration_summary.get("calibration_score", 0.5),
            active_patterns=len(patterns),
            performance_trend=trend,
            recommendations=recommendations,
        )

    async def get_all_agent_insights(self) -> List[AgentInsight]:
        """
        Get insights for all registered agents.

        Returns:
            List of AgentInsight for all agents
        """
        insights = []

        # Get all agent codes
        agent_codes = set()
        agent_codes.update(self._orchestrator._agent_loops.keys())
        agent_codes.update(self._orchestrator._manager_loops.keys())
        agent_codes.update(self._orchestrator._specialist_loops.keys())

        for code in agent_codes:
            try:
                insight = await self.get_agent_insight(code)
                insights.append(insight)
            except Exception as e:
                logger.warning(f"Failed to get insight for {code}: {e}")

        return insights

    # =========================================================================
    # Pattern Management
    # =========================================================================

    async def get_pattern_details(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a pattern.

        Args:
            pattern_id: Pattern ID

        Returns:
            Pattern details or None if not found
        """
        pattern_store = self._orchestrator._pattern_store
        pattern = await pattern_store.get_pattern(pattern_id)

        if not pattern:
            return None

        return {
            "id": pattern.id,
            "type": pattern.pattern_type.value,
            "scope_level": pattern.scope_level.value,
            "scope_code": pattern.scope_code,
            "task_type": pattern.task_type,
            "condition": pattern.condition_json,
            "recommendation": pattern.recommendation,
            "confidence": pattern.confidence,
            "sample_size": pattern.sample_size,
            "success_rate": pattern.success_rate,
            "is_active": pattern.is_active,
            "application_count": pattern.application_count,
            "last_applied_at": (
                pattern.last_applied_at.isoformat() if pattern.last_applied_at else None
            ),
            "created_at": pattern.created_at.isoformat(),
        }

    async def deactivate_pattern(self, pattern_id: str, reason: str) -> bool:
        """
        Deactivate a pattern (manual override).

        Args:
            pattern_id: Pattern ID to deactivate
            reason: Reason for deactivation

        Returns:
            True if successful
        """
        pattern_store = self._orchestrator._pattern_store
        pattern = await pattern_store.get_pattern(pattern_id)

        if not pattern:
            return False

        pattern.is_active = False
        await pattern_store.store_pattern(pattern)

        logger.info(f"Pattern {pattern_id} deactivated: {reason}")
        return True

    async def activate_pattern(self, pattern_id: str) -> bool:
        """
        Activate a pattern (manual override).

        Args:
            pattern_id: Pattern ID to activate

        Returns:
            True if successful
        """
        pattern_store = self._orchestrator._pattern_store
        pattern = await pattern_store.get_pattern(pattern_id)

        if not pattern:
            return False

        pattern.is_active = True
        await pattern_store.store_pattern(pattern)

        logger.info(f"Pattern {pattern_id} activated")
        return True

    # =========================================================================
    # Pipeline Control
    # =========================================================================

    async def start_pipeline(self) -> bool:
        """Start the continuous learning pipeline."""
        pipeline = self._orchestrator._continuous_pipeline
        if not pipeline:
            return False

        await pipeline.start()
        return True

    async def stop_pipeline(self) -> bool:
        """Stop the continuous learning pipeline."""
        pipeline = self._orchestrator._continuous_pipeline
        if not pipeline:
            return False

        await pipeline.stop()
        return True

    async def pause_pipeline(self) -> bool:
        """Pause the continuous learning pipeline."""
        pipeline = self._orchestrator._continuous_pipeline
        if not pipeline:
            return False

        await pipeline.pause()
        return True

    async def resume_pipeline(self) -> bool:
        """Resume the continuous learning pipeline."""
        pipeline = self._orchestrator._continuous_pipeline
        if not pipeline:
            return False

        await pipeline.resume()
        return True

    async def trigger_learning_cycle(self) -> Dict[str, Any]:
        """
        Manually trigger a single learning cycle.

        Returns:
            Cycle result
        """
        pipeline = self._orchestrator._continuous_pipeline
        if not pipeline:
            return {"error": "Pipeline not available"}

        result = await pipeline.run_single_cycle()
        return result.to_dict()
