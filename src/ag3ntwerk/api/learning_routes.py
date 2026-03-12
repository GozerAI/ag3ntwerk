"""
Learning API Routes - FastAPI routes for the learning system.

Provides REST API access to:
- Learning dashboard
- Pattern management
- Approval workflow
- Pipeline control
- Agent insights
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================


class ApprovalRequest(BaseModel):
    """Request to approve or reject an action."""

    approved_by: str = Field(default="api_user", description="User making the decision")
    notes: Optional[str] = Field(default=None, description="Optional notes")


class PatternActionRequest(BaseModel):
    """Request to activate/deactivate a pattern."""

    reason: Optional[str] = Field(default=None, description="Reason for the action")


class PipelineConfigUpdate(BaseModel):
    """Request to update pipeline configuration."""

    cycle_interval_seconds: Optional[int] = None
    enable_pattern_detection: Optional[bool] = None
    enable_experiments: Optional[bool] = None
    enable_opportunity_detection: Optional[bool] = None
    enable_task_generation: Optional[bool] = None
    enable_cleanup: Optional[bool] = None


# =============================================================================
# Service Access (async-safe setters and getters)
# =============================================================================

# Learning orchestrator and bridge are injected at startup
_orchestrator = None
_orchestrator_init_lock = asyncio.Lock()
_workbench_bridge = None
_bridge_init_lock = asyncio.Lock()


def set_learning_orchestrator(orchestrator) -> None:
    """Set the learning orchestrator for API routes.

    This is a simple assignment -- safe to call from sync context.
    The lock-protected variant ``set_learning_orchestrator_async`` is
    available for concurrent async callers.
    """
    global _orchestrator
    _orchestrator = orchestrator


async def set_learning_orchestrator_async(orchestrator) -> None:
    """Set the learning orchestrator for API routes (async-safe)."""
    global _orchestrator
    async with _orchestrator_init_lock:
        _orchestrator = orchestrator


def set_workbench_bridge(bridge) -> None:
    """Set the workbench bridge for API routes.

    This is a simple assignment -- safe to call from sync context.
    """
    global _workbench_bridge
    _workbench_bridge = bridge


async def set_workbench_bridge_async(bridge) -> None:
    """Set the workbench bridge for API routes (async-safe)."""
    global _workbench_bridge
    async with _bridge_init_lock:
        _workbench_bridge = bridge


def get_orchestrator():
    """Get the learning orchestrator.

    The orchestrator is set once during startup via ``set_learning_orchestrator``,
    so reads after that point are safe without a lock.
    """
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Learning system not initialized")
    return _orchestrator


def get_bridge():
    """Get the workbench bridge.

    The bridge is set once during startup via ``set_workbench_bridge``,
    so reads after that point are safe without a lock.
    """
    if _workbench_bridge is None:
        raise HTTPException(status_code=503, detail="Workbench bridge not initialized")
    return _workbench_bridge


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/learning", tags=["learning"])


# =============================================================================
# Dashboard Endpoints
# =============================================================================


@router.get("/dashboard")
async def get_dashboard(
    refresh: bool = Query(default=False, description="Force refresh cache"),
) -> Dict[str, Any]:
    """
    Get the learning dashboard data.

    Returns aggregated learning system statistics including:
    - Pattern counts and top performers
    - Experiment status
    - Opportunity feed
    - Autonomy stats and pending approvals
    - Pipeline status
    - Performance overview
    """
    bridge = get_bridge()
    dashboard = await bridge.get_learning_dashboard(refresh=refresh)
    return dashboard.to_dict()


@router.get("/stats")
async def get_learning_stats() -> Dict[str, Any]:
    """
    Get detailed learning system statistics.

    Returns lower-level stats from the orchestrator.
    """
    orchestrator = get_orchestrator()
    return await orchestrator.get_stats()


# =============================================================================
# Pattern Endpoints
# =============================================================================


@router.get("/patterns")
async def list_patterns(
    pattern_type: Optional[str] = Query(default=None, description="Filter by pattern type"),
    scope_code: Optional[str] = Query(default=None, description="Filter by scope code"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max patterns to return"),
) -> List[Dict[str, Any]]:
    """
    List learned patterns.

    Patterns influence routing decisions, confidence calibration,
    and other runtime behavior.
    """
    orchestrator = get_orchestrator()
    pattern_store = orchestrator._pattern_store

    patterns = await pattern_store.get_patterns(
        pattern_type=pattern_type,
        scope_code=scope_code,
        is_active=is_active,
    )

    return [
        {
            "id": p.id,
            "type": p.pattern_type.value,
            "scope_level": p.scope_level.value,
            "scope_code": p.scope_code,
            "task_type": p.task_type,
            "recommendation": p.recommendation,
            "confidence": p.confidence,
            "sample_size": p.sample_size,
            "success_rate": p.success_rate,
            "is_active": p.is_active,
            "application_count": p.application_count,
            "created_at": p.created_at.isoformat(),
        }
        for p in patterns[:limit]
    ]


@router.get("/patterns/{pattern_id}")
async def get_pattern(pattern_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific pattern."""
    bridge = get_bridge()
    details = await bridge.get_pattern_details(pattern_id)

    if not details:
        raise HTTPException(status_code=404, detail="Pattern not found")

    return details


@router.post("/patterns/{pattern_id}/activate")
async def activate_pattern(pattern_id: str) -> Dict[str, Any]:
    """Activate a pattern (manual override)."""
    bridge = get_bridge()
    success = await bridge.activate_pattern(pattern_id)

    if not success:
        raise HTTPException(status_code=404, detail="Pattern not found")

    return {"status": "activated", "pattern_id": pattern_id}


@router.post("/patterns/{pattern_id}/deactivate")
async def deactivate_pattern(
    pattern_id: str,
    request: PatternActionRequest,
) -> Dict[str, Any]:
    """Deactivate a pattern (manual override)."""
    bridge = get_bridge()
    success = await bridge.deactivate_pattern(
        pattern_id, reason=request.reason or "Manual deactivation via API"
    )

    if not success:
        raise HTTPException(status_code=404, detail="Pattern not found")

    return {"status": "deactivated", "pattern_id": pattern_id}


# =============================================================================
# Approval Endpoints
# =============================================================================


@router.get("/approvals")
async def list_pending_approvals() -> List[Dict[str, Any]]:
    """
    List pending approval requests.

    These are actions that require human approval before execution.
    """
    bridge = get_bridge()
    return await bridge.get_pending_approvals()


@router.post("/approvals/{approval_id}/approve")
async def approve_action(
    approval_id: str,
    request: ApprovalRequest,
) -> Dict[str, Any]:
    """Approve a pending action."""
    bridge = get_bridge()

    try:
        result = await bridge.approve_action(
            approval_id=approval_id,
            approved_by=request.approved_by,
            notes=request.notes,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/approvals/{approval_id}/reject")
async def reject_action(
    approval_id: str,
    request: ApprovalRequest,
) -> Dict[str, Any]:
    """Reject a pending action."""
    bridge = get_bridge()

    try:
        result = await bridge.reject_action(
            approval_id=approval_id,
            rejected_by=request.approved_by,
            notes=request.notes,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Agent Insight Endpoints
# =============================================================================


@router.get("/agents")
async def list_agent_insights() -> List[Dict[str, Any]]:
    """
    Get learning insights for all registered agents.

    Returns performance metrics, calibration data, and recommendations.
    """
    bridge = get_bridge()
    insights = await bridge.get_all_agent_insights()
    return [i.to_dict() for i in insights]


@router.get("/agents/{agent_code}")
async def get_agent_insight(agent_code: str) -> Dict[str, Any]:
    """Get detailed learning insight for a specific agent."""
    bridge = get_bridge()

    try:
        insight = await bridge.get_agent_insight(agent_code)
        return insight.to_dict()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Agent not found: {e}")


@router.get("/agents/{agent_code}/calibration")
async def get_agent_calibration(agent_code: str) -> Dict[str, Any]:
    """Get calibration data for an agent."""
    orchestrator = get_orchestrator()
    return await orchestrator.get_agent_calibration_summary(agent_code)


# =============================================================================
# Pipeline Control Endpoints
# =============================================================================


@router.get("/pipeline/status")
async def get_pipeline_status() -> Dict[str, Any]:
    """Get the current pipeline status."""
    orchestrator = get_orchestrator()
    pipeline = orchestrator._continuous_pipeline

    if not pipeline:
        return {"status": "not_configured"}

    stats = await pipeline.get_stats()
    health = await pipeline.health_check()

    return {
        "state": pipeline._state.value,
        "healthy": health.get("healthy", False),
        "stats": stats,
        "health": health,
    }


@router.post("/pipeline/start")
async def start_pipeline() -> Dict[str, Any]:
    """Start the continuous learning pipeline."""
    bridge = get_bridge()
    success = await bridge.start_pipeline()

    if not success:
        raise HTTPException(status_code=503, detail="Pipeline not configured")

    return {"status": "started"}


@router.post("/pipeline/stop")
async def stop_pipeline() -> Dict[str, Any]:
    """Stop the continuous learning pipeline."""
    bridge = get_bridge()
    success = await bridge.stop_pipeline()

    if not success:
        raise HTTPException(status_code=503, detail="Pipeline not configured")

    return {"status": "stopped"}


@router.post("/pipeline/pause")
async def pause_pipeline() -> Dict[str, Any]:
    """Pause the continuous learning pipeline."""
    bridge = get_bridge()
    success = await bridge.pause_pipeline()

    if not success:
        raise HTTPException(status_code=503, detail="Pipeline not configured")

    return {"status": "paused"}


@router.post("/pipeline/resume")
async def resume_pipeline() -> Dict[str, Any]:
    """Resume the continuous learning pipeline."""
    bridge = get_bridge()
    success = await bridge.resume_pipeline()

    if not success:
        raise HTTPException(status_code=503, detail="Pipeline not configured")

    return {"status": "resumed"}


@router.post("/pipeline/trigger")
async def trigger_learning_cycle() -> Dict[str, Any]:
    """Manually trigger a single learning cycle."""
    bridge = get_bridge()
    result = await bridge.trigger_learning_cycle()
    return result


@router.get("/pipeline/history")
async def get_pipeline_history(
    limit: int = Query(default=20, ge=1, le=100, description="Max cycles to return"),
) -> List[Dict[str, Any]]:
    """Get recent pipeline cycle history."""
    orchestrator = get_orchestrator()
    pipeline = orchestrator._continuous_pipeline

    if not pipeline:
        return []

    history = pipeline.get_cycle_history(limit=limit)
    return [
        {
            "id": cycle.cycle_id,
            "started_at": cycle.started_at.isoformat(),
            "completed_at": cycle.completed_at.isoformat() if cycle.completed_at else None,
            "duration_ms": cycle.duration_ms,
            "success": cycle.success,
            "error": cycle.error,
            "outcomes_collected": cycle.outcomes_collected,
            "patterns_detected": cycle.patterns_detected,
            "experiments_started": cycle.experiments_started,
            "experiments_concluded": cycle.experiments_concluded,
            "patterns_activated": cycle.patterns_activated,
            "patterns_deactivated": cycle.patterns_deactivated,
            "parameters_tuned": cycle.parameters_tuned,
            "opportunities_detected": cycle.opportunities_detected,
            "tasks_generated": cycle.tasks_generated,
        }
        for cycle in history
    ]


# =============================================================================
# Experiment Endpoints
# =============================================================================


@router.get("/experiments")
async def list_experiments(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=200, description="Max experiments"),
) -> List[Dict[str, Any]]:
    """List pattern experiments."""
    orchestrator = get_orchestrator()
    experimenter = orchestrator._pattern_experimenter

    if not experimenter:
        return []

    if status == "active":
        experiments = await experimenter.get_active_experiments()
    else:
        experiments = await experimenter.get_active_experiments()

    return [
        {
            "id": exp.id,
            "pattern_id": exp.pattern_id,
            "status": exp.status.value,
            "control_size": exp.control_count,
            "treatment_size": exp.treatment_count,
            "started_at": exp.started_at.isoformat() if exp.started_at else None,
        }
        for exp in experiments[:limit]
    ]


@router.get("/experiments/results")
async def get_experiment_results(
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
) -> List[Dict[str, Any]]:
    """Get recent experiment results."""
    orchestrator = get_orchestrator()
    experimenter = orchestrator._pattern_experimenter

    if not experimenter:
        return []

    results = await experimenter.get_recent_results(limit=limit)

    return [
        {
            "experiment_id": r.experiment_id,
            "pattern_id": r.pattern_id,
            "conclusion": r.conclusion.value if r.conclusion else None,
            "is_positive": r.is_positive,
            "control_success_rate": r.control_success_rate,
            "treatment_success_rate": r.treatment_success_rate,
            "effect_size": r.effect_size,
            "statistical_significance": r.statistical_significance,
            "concluded_at": r.concluded_at.isoformat() if r.concluded_at else None,
        }
        for r in results
    ]


# =============================================================================
# Opportunity Endpoints
# =============================================================================


@router.get("/opportunities")
async def list_opportunities(
    priority: Optional[str] = Query(default=None, description="Filter by priority"),
    limit: int = Query(default=50, ge=1, le=200, description="Max opportunities"),
) -> List[Dict[str, Any]]:
    """List detected improvement opportunities."""
    orchestrator = get_orchestrator()
    detector = orchestrator._opportunity_detector

    if not detector:
        return []

    opportunities = await detector.get_open_opportunities(limit=limit)

    if priority:
        opportunities = [o for o in opportunities if o.priority.value == priority]

    return [
        {
            "id": opp.id,
            "type": opp.opportunity_type.value,
            "priority": opp.priority.value,
            "description": opp.description,
            "impact_score": opp.impact_score,
            "source_agent": opp.source_agent,
            "task_type": opp.task_type,
            "evidence": opp.evidence,
            "recommended_action": opp.recommended_action,
            "created_at": opp.created_at.isoformat(),
        }
        for opp in opportunities
    ]


# =============================================================================
# Routing Decision Endpoints
# =============================================================================


@router.get("/routing/decisions")
async def get_recent_routing_decisions(
    limit: int = Query(default=50, ge=1, le=200, description="Max decisions"),
) -> List[Dict[str, Any]]:
    """Get recent routing decisions."""
    orchestrator = get_orchestrator()
    # Access routing history if available
    router = orchestrator._dynamic_router

    # This would need to be implemented in DynamicRouter
    # For now, return empty list
    return []


@router.post("/routing/simulate")
async def simulate_routing(
    task_type: str = Query(description="Task type to simulate"),
) -> Dict[str, Any]:
    """
    Simulate a routing decision without executing.

    Useful for understanding how the learning system would route a task.
    """
    orchestrator = get_orchestrator()

    # Get available agents (would need access to Nexus)
    # For now, return a placeholder
    return {
        "task_type": task_type,
        "message": "Routing simulation requires Nexus integration",
    }
