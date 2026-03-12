"""
Metacognition API routes.

REST endpoints for metacognition data: profiles, reflections,
heuristics, compatibility, and system reflection triggers.
"""

import asyncio
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path

router = APIRouter(prefix="/metacognition", tags=["metacognition"])

_metacognition_service = None
_metacognition_init_lock = asyncio.Lock()


def set_metacognition_service(service) -> None:
    """Set the metacognition service at startup.

    This is a simple assignment -- safe to call from sync context.
    The lock-protected variant ``set_metacognition_service_async`` is
    available for concurrent async callers.
    """
    global _metacognition_service
    _metacognition_service = service


async def set_metacognition_service_async(service) -> None:
    """Set the metacognition service at startup (async-safe)."""
    global _metacognition_service
    async with _metacognition_init_lock:
        _metacognition_service = service


def _get_service():
    """Get the metacognition service or raise 503.

    The service is set once during startup via ``set_metacognition_service``,
    so reads after that point are safe without a lock.
    """
    if _metacognition_service is None:
        raise HTTPException(
            status_code=503,
            detail="Metacognition service not initialized",
        )
    return _metacognition_service


# ============================================================
# Status
# ============================================================


@router.get("/status")
async def get_metacognition_status() -> Dict[str, Any]:
    """Get full metacognition statistics."""
    service = _get_service()
    return service.get_stats()


# ============================================================
# Profiles
# ============================================================


@router.get("/profiles")
async def get_all_profiles() -> Dict[str, Any]:
    """Get all personality profiles."""
    service = _get_service()
    profiles = service.get_all_profiles()
    return {code: profile.to_dict() for code, profile in profiles.items()}


@router.get("/profiles/{agent_code}")
async def get_profile(
    agent_code: str = Path(..., min_length=1, max_length=20),
) -> Dict[str, Any]:
    """Get a single agent's personality profile."""
    service = _get_service()
    profile = service.get_profile(agent_code)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_code} not registered",
        )
    return profile.to_dict()


# ============================================================
# Reflection
# ============================================================


@router.post("/reflect")
async def trigger_system_reflection() -> Dict[str, Any]:
    """Trigger a system-level metacognition reflection."""
    service = _get_service()
    reflection = service.system_reflect()
    return reflection.to_dict()


@router.get("/reflections/{agent_code}")
async def get_reflections(
    agent_code: str = Path(..., min_length=1, max_length=20),
    limit: int = Query(10, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Get recent reflections for an agent."""
    service = _get_service()
    reflector = service._reflectors.get(agent_code)
    if not reflector:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_code} not registered",
        )
    reflections = reflector.get_recent_reflections(limit)
    return [r.to_dict() for r in reflections]


# ============================================================
# Heuristics
# ============================================================


@router.get("/heuristics/{agent_code}")
async def get_heuristic_stats(
    agent_code: str = Path(..., min_length=1, max_length=20),
) -> Dict[str, Any]:
    """Get heuristic engine stats for an agent."""
    service = _get_service()
    engine = service._heuristic_engines.get(agent_code)
    if not engine:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_code} not registered",
        )
    return engine.get_stats()


# ============================================================
# Compatibility
# ============================================================


@router.get("/compatibility")
async def get_compatibility_matrix() -> Dict[str, Dict[str, float]]:
    """Get full compatibility matrix for all agents."""
    service = _get_service()
    return service.get_compatibility_matrix()


# ============================================================
# Drift Alerting
# ============================================================


@router.get("/drift")
async def get_drift_summary() -> Dict[str, Any]:
    """Get full drift alert summary across all agents."""
    service = _get_service()
    return service.get_drift_summary()


@router.get("/drift/{agent_code}")
async def get_agent_drift_alerts(
    agent_code: str = Path(..., min_length=1, max_length=20),
) -> Dict[str, Any]:
    """Get drift alerts for a specific agent."""
    service = _get_service()
    if not service.is_registered(agent_code):
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_code} not registered",
        )
    alerts = service.check_drift_alerts(agent_code)
    return {
        "agent_code": agent_code,
        "total_alerts": len(alerts),
        "alerts": [a.to_dict() for a in alerts],
    }


# ============================================================
# Drift Auto-Response
# ============================================================


@router.get("/drift-responses")
async def get_drift_responses(
    agent_code: Optional[str] = Query(None, min_length=1, max_length=20),
    limit: int = Query(50, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """Get history of drift auto-responses."""
    service = _get_service()
    return service.get_drift_responses(agent_code=agent_code, limit=limit)


@router.post("/drift-respond")
async def trigger_drift_response(
    agent_code: Optional[str] = Query(None, min_length=1, max_length=20),
) -> Dict[str, Any]:
    """Manually trigger drift auto-response."""
    service = _get_service()
    responses = service.respond_to_drift(agent_code=agent_code)
    return {
        "responses_taken": len(responses),
        "responses": [r.to_dict() for r in responses],
    }


# ============================================================
# Routing Feedback
# ============================================================


@router.get("/routing-stats")
async def get_routing_stats() -> Dict[str, Any]:
    """Get routing feedback statistics."""
    service = _get_service()
    return service.get_routing_stats()


# ============================================================
# Performance Attribution
# ============================================================


@router.get("/attribution/suggestions")
async def get_attribution_suggestions(
    min_correlation: float = Query(0.5, ge=0.0, le=1.0),
    min_samples: int = Query(10, ge=1, le=1000),
) -> Dict[str, Dict[str, float]]:
    """Get suggested TASK_TRAIT_MAP updates based on attribution analysis."""
    service = _get_service()
    return service.suggest_trait_map_updates(
        min_correlation=min_correlation,
        min_samples=min_samples,
    )


@router.get("/attribution/{task_type}")
async def get_task_type_attribution(
    task_type: str = Path(..., min_length=1, max_length=50),
    min_samples: int = Query(10, ge=1, le=1000),
) -> List[Dict[str, Any]]:
    """Get attribution analysis for a specific task type."""
    service = _get_service()
    attributions = service.compute_attribution(
        task_type=task_type,
        min_samples=min_samples,
    )
    return [a.to_dict() for a in attributions]


@router.get("/attribution")
async def get_full_attribution(
    min_samples: int = Query(10, ge=1, le=1000),
) -> List[Dict[str, Any]]:
    """Get full attribution analysis across all task types."""
    service = _get_service()
    attributions = service.compute_attribution(min_samples=min_samples)
    return [a.to_dict() for a in attributions]


# ============================================================
# Temporal Trends (Phase 5)
# ============================================================


@router.get("/trends")
async def get_trend_summary() -> Dict[str, Any]:
    """Get full trend summary for all agents."""
    service = _get_service()
    return service.get_trend_summary()


@router.get("/trends/{agent_code}")
async def get_agent_trends(
    agent_code: str = Path(..., min_length=1, max_length=20),
    trait_name: Optional[str] = Query(None, min_length=1, max_length=50),
) -> Dict[str, Any]:
    """Get trends for a specific agent, optionally filtered by trait."""
    service = _get_service()
    if not service.is_registered(agent_code):
        raise HTTPException(status_code=404, detail=f"Agent {agent_code} not registered")
    if trait_name:
        trend = service.classify_trait_trend(agent_code, trait_name)
        return (
            trend.to_dict()
            if trend
            else {"agent_code": agent_code, "trait_name": trait_name, "classification": None}
        )
    return service.get_trend_summary(agent_code)


# ============================================================
# Coherence (Phase 5)
# ============================================================


@router.get("/coherence")
async def get_all_coherence() -> List[Dict[str, Any]]:
    """Get coherence reports for all agents."""
    service = _get_service()
    reports = []
    for code in service.get_all_profiles():
        report = service.compute_coherence(code)
        if report:
            reports.append(report.to_dict())
    return reports


@router.get("/coherence/{agent_code}")
async def get_agent_coherence(
    agent_code: str = Path(..., min_length=1, max_length=20),
) -> Dict[str, Any]:
    """Get coherence report for a specific agent."""
    service = _get_service()
    report = service.compute_coherence(agent_code)
    if not report:
        raise HTTPException(status_code=404, detail=f"Agent {agent_code} not registered")
    return report.to_dict()


# ============================================================
# Cross-Agent Learning (Phase 5)
# ============================================================


@router.get("/peer-recommendations/{agent_code}")
async def get_peer_recommendations(
    agent_code: str = Path(..., min_length=1, max_length=20),
    task_type: Optional[str] = Query(None, min_length=1, max_length=50),
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Get peer recommendations for an agent."""
    service = _get_service()
    if not service.is_registered(agent_code):
        raise HTTPException(status_code=404, detail=f"Agent {agent_code} not registered")
    recs = service.generate_peer_recommendations(agent_code, task_type=task_type)
    return [r.to_dict() for r in recs[:limit]]


@router.post("/heuristic-sharing")
async def share_heuristic(
    source_agent: str = Query(..., min_length=1, max_length=20),
    target_agent: str = Query(..., min_length=1, max_length=20),
    heuristic_id: str = Query(..., min_length=1),
) -> Dict[str, Any]:
    """Manually share a heuristic between agents."""
    service = _get_service()
    result = service.share_heuristic(source_agent, target_agent, heuristic_id)
    if not result:
        raise HTTPException(
            status_code=400, detail="Sharing failed: check agents, heuristic, and thresholds"
        )
    return result


# ============================================================
# Team Learning (Phase 5)
# ============================================================


@router.get("/team-stats")
async def get_team_stats(
    task_type: Optional[str] = Query(None, min_length=1, max_length=50),
) -> Dict[str, Any]:
    """Get team composition statistics."""
    service = _get_service()
    return service.get_team_stats(task_type=task_type)


@router.get("/team-recommendations/{task_type}")
async def get_team_recommendations(
    task_type: str = Path(..., min_length=1, max_length=50),
    team_size: int = Query(3, ge=2, le=10),
) -> Dict[str, Any]:
    """Get team recommendation for a task type."""
    service = _get_service()
    return service.recommend_learned_team(task_type, team_size=team_size)


@router.get("/team-pairs")
async def get_team_pairs(
    task_type: Optional[str] = Query(None, min_length=1, max_length=50),
    limit: int = Query(10, ge=1, le=50),
) -> List[Dict[str, Any]]:
    """Get best agent pairs by co-occurrence success rate."""
    service = _get_service()
    return service.get_best_pairs(task_type=task_type, limit=limit)


# ============================================================
# Trait Map Optimization (Phase 5)
# ============================================================


@router.post("/trait-map/apply")
async def apply_trait_map(
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
) -> Dict[str, Any]:
    """Apply high-confidence trait map suggestions."""
    service = _get_service()
    updates = service.apply_trait_map_suggestions(min_confidence=min_confidence)
    return {
        "updates_applied": len(updates),
        "updates": [u.to_dict() for u in updates],
    }


@router.get("/trait-map/learned")
async def get_learned_trait_map() -> Dict[str, Dict[str, float]]:
    """Get the current learned trait map overlay."""
    service = _get_service()
    return service.get_learned_trait_map()


@router.get("/trait-map/validation")
async def get_trait_map_validation() -> List[Dict[str, Any]]:
    """Get trait map update history with validation status."""
    service = _get_service()
    return [u.to_dict() for u in service._trait_map_updates]


@router.get("/compatibility/{agent_a}/{agent_b}")
async def get_pairwise_compatibility(
    agent_a: str = Path(..., min_length=1, max_length=20),
    agent_b: str = Path(..., min_length=1, max_length=20),
) -> Dict[str, Any]:
    """Get compatibility score between two agents."""
    service = _get_service()
    result = service.get_compatibility(agent_a, agent_b)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"One or both agents not registered: {agent_a}, {agent_b}",
        )
    return result.to_dict()
