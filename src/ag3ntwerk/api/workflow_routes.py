"""
Workflow Library API Routes - REST endpoints for workflow analytics.

Provides aggregate statistics, quality trends, deployment metrics,
and harvest run history for the workflow library.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["workflow-library"])

# Plugin reference - set during app startup
_plugin = None
_plugin_init_lock = asyncio.Lock()


def set_workflow_plugin(plugin) -> None:
    """Set the workflow library plugin for API routes."""
    global _plugin
    _plugin = plugin


def _get_plugin():
    """Get the plugin, attempting lazy-load from registry if needed (sync fast-path)."""
    global _plugin
    if _plugin is not None:
        return _plugin
    try:
        from ag3ntwerk.core.plugins import get_plugin_manager

        manager = get_plugin_manager()
        _plugin = manager.get_plugin("workflow-library")
    except Exception as e:
        logger.debug("Workflow library plugin lazy-load failed: %s", e)
    return _plugin


async def _get_plugin_async():
    """Get the plugin with async lock to prevent concurrent lazy-load."""
    global _plugin
    if _plugin is not None:
        return _plugin
    async with _plugin_init_lock:
        if _plugin is not None:
            return _plugin
        try:
            from ag3ntwerk.core.plugins import get_plugin_manager

            manager = get_plugin_manager()
            _plugin = manager.get_plugin("workflow-library")
        except Exception as e:
            logger.debug("Workflow library plugin lazy-load failed: %s", e)
    return _plugin


# =============================================================================
# Routes
# =============================================================================


@router.get("/stats")
async def get_workflow_stats():
    """Get aggregate library statistics."""
    plugin = await _get_plugin_async()
    if not plugin:
        raise HTTPException(status_code=503, detail="Workflow library not available")

    stats = await plugin.get_stats()
    return {"success": True, "statistics": stats}


@router.get("/stats/by-tool")
async def get_stats_by_tool():
    """Get workflow breakdown by tool type."""
    plugin = await _get_plugin_async()
    if not plugin or not plugin._pool:
        raise HTTPException(status_code=503, detail="Workflow library not available")

    async with plugin._pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT tool_type, COUNT(*) as total,
                      COUNT(*) FILTER (WHERE quality_score >= 70) as high_quality,
                      ROUND(AVG(quality_score)) as avg_quality,
                      COUNT(*) FILTER (WHERE embedded_at IS NOT NULL) as embedded
               FROM workflows
               GROUP BY tool_type
               ORDER BY total DESC"""
        )

    return {
        "success": True,
        "by_tool": [dict(r) for r in rows],
    }


@router.get("/stats/quality-trends")
async def get_quality_trends():
    """Get quality score trends over time (by month discovered)."""
    plugin = await _get_plugin_async()
    if not plugin or not plugin._pool:
        raise HTTPException(status_code=503, detail="Workflow library not available")

    async with plugin._pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT
                 date_trunc('month', discovered_at) as month,
                 COUNT(*) as total,
                 ROUND(AVG(quality_score)) as avg_quality,
                 COUNT(*) FILTER (WHERE quality_score >= 70) as high_quality,
                 COUNT(DISTINCT tool_type) as tool_types
               FROM workflows
               WHERE discovered_at IS NOT NULL
               GROUP BY month
               ORDER BY month DESC
               LIMIT 12"""
        )

    return {
        "success": True,
        "trends": [
            {
                "month": str(r["month"].date()) if r["month"] else None,
                "total": r["total"],
                "avg_quality": int(r["avg_quality"]) if r["avg_quality"] else 0,
                "high_quality": r["high_quality"],
                "tool_types": r["tool_types"],
            }
            for r in rows
        ],
    }


@router.get("/stats/deployments")
async def get_deployment_stats():
    """Get deployment counts, success rates, and execution totals."""
    plugin = await _get_plugin_async()
    if not plugin or not plugin._pool:
        raise HTTPException(status_code=503, detail="Workflow library not available")

    async with plugin._pool.acquire() as conn:
        # Check if deployment table exists
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'workflow_deployments')"
        )

        if not table_exists:
            return {
                "success": True,
                "deployments": {"total": 0, "message": "No deployment table yet"},
            }

        stats = await conn.fetchrow(
            """SELECT
                 COUNT(*) as total_deployments,
                 COUNT(*) FILTER (WHERE activated = true) as active_deployments,
                 COALESCE(SUM(execution_count), 0) as total_executions,
                 COUNT(*) FILTER (WHERE last_status = 'success') as successful,
                 COUNT(*) FILTER (WHERE last_status = 'error') as failed,
                 COUNT(DISTINCT workflow_id) as unique_workflows
               FROM workflow_deployments"""
        )

    total = stats["total_deployments"] or 0
    successful = stats["successful"] or 0
    failed = stats["failed"] or 0

    return {
        "success": True,
        "deployments": {
            "total_deployments": total,
            "active_deployments": stats["active_deployments"] or 0,
            "total_executions": stats["total_executions"] or 0,
            "unique_workflows": stats["unique_workflows"] or 0,
            "success_rate": round(successful / max(successful + failed, 1) * 100, 1),
        },
    }


@router.get("/stats/popular")
async def get_popular_workflows(
    limit: int = Query(default=10, le=50),
):
    """Get most deployed/recommended workflows."""
    plugin = await _get_plugin_async()
    if not plugin or not plugin._pool:
        raise HTTPException(status_code=503, detail="Workflow library not available")

    async with plugin._pool.acquire() as conn:
        # Check if deployment table exists
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'workflow_deployments')"
        )

        if table_exists:
            rows = await conn.fetch(
                """SELECT w.id, w.workflow_name, w.tool_type, w.primary_category,
                          w.quality_score, d.deployment_count, d.total_executions
                   FROM workflows w
                   JOIN (
                       SELECT workflow_id,
                              COUNT(*) as deployment_count,
                              COALESCE(SUM(execution_count), 0) as total_executions
                       FROM workflow_deployments
                       GROUP BY workflow_id
                   ) d ON d.workflow_id = w.id
                   ORDER BY d.total_executions DESC, d.deployment_count DESC
                   LIMIT $1""",
                limit,
            )
        else:
            # Fall back to quality-based ranking
            rows = await conn.fetch(
                """SELECT id, workflow_name, tool_type, primary_category,
                          quality_score, 0 as deployment_count, 0 as total_executions
                   FROM workflows
                   WHERE quality_score > 0
                   ORDER BY quality_score DESC
                   LIMIT $1""",
                limit,
            )

    return {
        "success": True,
        "popular": [
            {
                "id": str(r["id"]),
                "name": r["workflow_name"],
                "tool_type": r["tool_type"],
                "category": r["primary_category"],
                "quality_score": r["quality_score"],
                "deployments": r["deployment_count"],
                "executions": r["total_executions"],
            }
            for r in rows
        ],
    }


@router.get("/stats/recommendations")
async def get_recommendation_stats():
    """Get recommendation effectiveness from learning outcomes."""
    plugin = await _get_plugin_async()
    if not plugin:
        raise HTTPException(status_code=503, detail="Workflow library not available")

    try:
        from ag3ntwerk.learning.orchestrator import get_learning_orchestrator

        orchestrator = get_learning_orchestrator()

        # Get recent workflow-related outcomes
        outcomes = await orchestrator.get_recent_outcomes(
            task_type="workflow_selection",
            limit=100,
        )

        if not outcomes:
            return {
                "success": True,
                "recommendations": {
                    "total_selections": 0,
                    "message": "No recommendation data yet",
                },
            }

        avg_effectiveness = sum(o.get("effectiveness", 0) for o in outcomes) / len(outcomes)

        return {
            "success": True,
            "recommendations": {
                "total_selections": len(outcomes),
                "avg_effectiveness": round(avg_effectiveness, 3),
                "avg_position": round(
                    sum(o.get("context", {}).get("recommendation_position", 0) for o in outcomes)
                    / len(outcomes),
                    1,
                ),
            },
        }

    except (ImportError, AttributeError):
        return {
            "success": True,
            "recommendations": {
                "total_selections": 0,
                "message": "Learning system not available",
            },
        }
    except Exception as e:
        logger.warning(f"Failed to get recommendation stats: {e}")
        return {
            "success": True,
            "recommendations": {"total_selections": 0, "error": str(e)},
        }


@router.get("/stats/harvest-runs")
async def get_harvest_runs(
    limit: int = Query(default=20, le=100),
):
    """Get recent harvest run history."""
    plugin = await _get_plugin_async()
    if not plugin or not plugin._pool:
        raise HTTPException(status_code=503, detail="Workflow library not available")

    async with plugin._pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT source, status, items_discovered, items_new,
                      items_duplicate, items_invalid, error_message,
                      started_at, completed_at
               FROM harvest_runs
               ORDER BY started_at DESC
               LIMIT $1""",
            limit,
        )

    return {
        "success": True,
        "harvest_runs": [
            {
                "source": r["source"],
                "status": r["status"],
                "discovered": r["items_discovered"],
                "new": r["items_new"],
                "duplicate": r["items_duplicate"],
                "invalid": r["items_invalid"],
                "error": r["error_message"],
                "started_at": str(r["started_at"]) if r["started_at"] else None,
                "completed_at": str(r["completed_at"]) if r["completed_at"] else None,
            }
            for r in rows
        ],
    }


@router.get("/{workflow_id}/similar")
async def get_similar_workflows(
    workflow_id: str,
    limit: int = Query(default=10, le=50),
    tool_type: Optional[str] = Query(default=None),
):
    """Find workflows similar to a given workflow by vector embedding distance."""
    plugin = await _get_plugin_async()
    if not plugin:
        raise HTTPException(status_code=503, detail="Workflow library not available")

    results = await plugin.find_similar(
        workflow_id=workflow_id,
        limit=limit,
        tool_type=tool_type,
    )

    return {
        "success": True,
        "workflow_id": workflow_id,
        "count": len(results),
        "similar": results,
    }
