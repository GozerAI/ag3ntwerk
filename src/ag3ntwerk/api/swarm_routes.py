"""
Swarm Bridge API routes for ag3ntwerk.

Provides endpoints for the frontend to:
- Check Swarm health and status
- Submit tasks to the Swarm for execution
- Monitor task progress and results
- View available models, backends, and routing stats
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

swarm_router = APIRouter(prefix="/api/v1/swarm", tags=["Swarm"])


# ── Pydantic models ─────────────────────────────────────────


class SwarmTaskRequest(BaseModel):
    """Request to submit a task to the Swarm."""

    prompt: str = Field(..., description="Task prompt")
    agent_code: str = Field(default="", description="ag3ntwerk agent code (Forge, Foundry, etc.)")
    priority: str = Field(default="normal", description="Priority: low, normal, high, critical")
    wait: bool = Field(default=False, description="Wait for result before responding")
    timeout: int = Field(default=300, description="Timeout in seconds")


class SwarmTaskResponse(BaseModel):
    """Response after submitting a task."""

    task_id: str
    status: str


# ── Service singleton ────────────────────────────────────────

_swarm_service = None
_swarm_facade = None
_init_lock = asyncio.Lock()


async def _get_service():
    """Get or create SwarmBridgeService singleton."""
    global _swarm_service
    if _swarm_service is None:
        async with _init_lock:
            if _swarm_service is None:
                from ag3ntwerk.modules.swarm_bridge import SwarmBridgeService

                _swarm_service = SwarmBridgeService()
    return _swarm_service


async def _get_facade():
    """Get or create SwarmFacade singleton."""
    global _swarm_facade
    if _swarm_facade is None:
        async with _init_lock:
            if _swarm_facade is None:
                from ag3ntwerk.modules.swarm_bridge import SwarmFacade

                _swarm_facade = SwarmFacade()
    return _swarm_facade


# ── Routes ───────────────────────────────────────────────────


@swarm_router.get("/status")
async def swarm_status() -> Dict[str, Any]:
    """Get Swarm health and overall status."""
    try:
        service = await _get_service()
        available = await service.is_swarm_available()
        if not available:
            return {
                "available": False,
                "error": "Swarm is not reachable at http://localhost:8766",
            }
        status = await service.get_swarm_status()
        return {"available": True, **status}
    except Exception as e:
        logger.error("Failed to get swarm status: %s", e)
        return {"available": False, "error": str(e)}


@swarm_router.post("/tasks", response_model=SwarmTaskResponse)
async def submit_task(request: SwarmTaskRequest) -> Dict[str, Any]:
    """Submit a task to the Swarm for execution."""
    try:
        facade = await _get_facade()
        result = await facade.delegate_to_swarm(
            task=request.prompt,
            agent_code=request.agent_code,
            priority=request.priority,
            wait=request.wait,
            timeout=request.timeout,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to submit swarm task: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@swarm_router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> Dict[str, Any]:
    """Get status and result of a specific Swarm task."""
    try:
        service = await _get_service()
        result = await service.get_task_result(task_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task %s: %s", task_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@swarm_router.get("/tasks")
async def list_tasks(status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """List Swarm tasks."""
    try:
        service = await _get_service()
        # Call swarm API directly for task listing
        import aiohttp

        params = {"limit": limit}
        if status:
            params["status"] = status
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{service.swarm_url}/tasks",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return []
                return await resp.json()
    except Exception as e:
        logger.error("Failed to list swarm tasks: %s", e)
        return []


@swarm_router.get("/models")
async def list_models() -> List[Dict[str, Any]]:
    """List available models on the Swarm."""
    try:
        service = await _get_service()
        return await service.get_available_models()
    except Exception as e:
        logger.error("Failed to list swarm models: %s", e)
        return []


@swarm_router.get("/backends")
async def list_backends() -> List[Dict[str, Any]]:
    """List Swarm backend endpoints and their health."""
    try:
        service = await _get_service()
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{service.swarm_url}/backends",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return []
                return await resp.json()
    except Exception as e:
        logger.error("Failed to list swarm backends: %s", e)
        return []


@swarm_router.get("/routing/stats")
async def routing_stats() -> Dict[str, Any]:
    """Get Swarm routing performance statistics."""
    try:
        service = await _get_service()
        return await service.get_routing_insights()
    except Exception as e:
        logger.error("Failed to get routing stats: %s", e)
        return {}
