"""
Module API Routes - FastAPI routes for autonomous modules.

Provides REST API access to trends, commerce, brand, and scheduler
module functionality.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ag3ntwerk.modules.trends import TrendService
from ag3ntwerk.modules.commerce import CommerceService
from ag3ntwerk.modules.brand import BrandService
from ag3ntwerk.modules.scheduler import SchedulerService

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================


class TrendAnalysisRequest(BaseModel):
    sources: Optional[List[str]] = None


class TrendFilterRequest(BaseModel):
    category: Optional[str] = None
    min_score: float = 0
    limit: int = 20


class ExecutiveReportRequest(BaseModel):
    agent_code: str = "Echo"


class BrandIdentityCreate(BaseModel):
    name: str
    tagline: str = ""
    mission: str = ""
    primary_tone: str = "professional"
    primary_color: Optional[str] = None


class BrandGuidelineCreate(BaseModel):
    category: str
    title: str
    description: str
    rule_type: str = "guideline"


class ContentValidationRequest(BaseModel):
    content: str
    content_type: str = "website"


class ConsistencyCheckRequest(BaseModel):
    samples: List[Dict[str, str]]


class ScheduleTaskRequest(BaseModel):
    name: str
    handler_name: str
    description: str = ""
    frequency: str = "daily"
    priority: str = "normal"
    owner_executive: str = "Nexus"
    hour: int = 0
    minute: int = 0


class WorkflowExecuteRequest(BaseModel):
    context: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Service Singletons (double-checked locking)
# =============================================================================

_trend_service: Optional[TrendService] = None
_trend_init_lock = asyncio.Lock()
_commerce_service: Optional[CommerceService] = None
_commerce_init_lock = asyncio.Lock()
_brand_service: Optional[BrandService] = None
_brand_init_lock = asyncio.Lock()
_scheduler_service: Optional[SchedulerService] = None
_scheduler_init_lock = asyncio.Lock()


def get_trend_service() -> TrendService:
    """Get or create TrendService singleton (sync fast-path)."""
    global _trend_service
    if _trend_service is None:
        _trend_service = TrendService()
    return _trend_service


async def _get_trend_service_async() -> TrendService:
    """Get or create TrendService singleton with async lock."""
    global _trend_service
    if _trend_service is None:
        async with _trend_init_lock:
            if _trend_service is None:
                _trend_service = TrendService()
    return _trend_service


def get_commerce_service() -> CommerceService:
    """Get or create CommerceService singleton (sync fast-path)."""
    global _commerce_service
    if _commerce_service is None:
        _commerce_service = CommerceService()
    return _commerce_service


async def _get_commerce_service_async() -> CommerceService:
    """Get or create CommerceService singleton with async lock."""
    global _commerce_service
    if _commerce_service is None:
        async with _commerce_init_lock:
            if _commerce_service is None:
                _commerce_service = CommerceService()
    return _commerce_service


def get_brand_service() -> BrandService:
    """Get or create BrandService singleton (sync fast-path)."""
    global _brand_service
    if _brand_service is None:
        _brand_service = BrandService()
    return _brand_service


async def _get_brand_service_async() -> BrandService:
    """Get or create BrandService singleton with async lock."""
    global _brand_service
    if _brand_service is None:
        async with _brand_init_lock:
            if _brand_service is None:
                _brand_service = BrandService()
    return _brand_service


def get_scheduler_service() -> SchedulerService:
    """Get or create SchedulerService singleton (sync fast-path)."""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service


async def _get_scheduler_service_async() -> SchedulerService:
    """Get or create SchedulerService singleton with async lock."""
    global _scheduler_service
    if _scheduler_service is None:
        async with _scheduler_init_lock:
            if _scheduler_service is None:
                _scheduler_service = SchedulerService()
    return _scheduler_service


# =============================================================================
# Trends Router
# =============================================================================

trends_router = APIRouter(prefix="/api/v1/modules/trends", tags=["Trends"])


@trends_router.get("/")
async def trends_overview():
    """Get trends module overview."""
    service = await _get_trend_service_async()
    return {
        "module": "trends",
        "primary_owner": "Echo",
        "stats": await service.get_stats(),
    }


@trends_router.post("/analyze")
async def run_trend_analysis(request: TrendAnalysisRequest):
    """Run trend analysis cycle."""
    try:
        service = await _get_trend_service_async()
        result = await service.run_analysis_cycle(sources=request.sources)
        return result
    except Exception as e:
        logger.error(f"Trend analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trends_router.get("/trending")
async def get_trending(
    category: Optional[str] = None,
    min_score: float = 0,
    limit: int = 20,
):
    """Get trending topics."""
    try:
        service = await _get_trend_service_async()
        result = await service.get_trending(
            category=category,
            min_score=min_score,
            limit=limit,
        )
        return {"trends": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Get trending failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trends_router.get("/opportunities")
async def get_opportunities(min_score: float = 50, limit: int = 10):
    """Get niche opportunities."""
    try:
        service = await _get_trend_service_async()
        result = await service.find_opportunities(min_score=min_score, limit=limit)
        return {"opportunities": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Get opportunities failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trends_router.get("/correlations")
async def get_correlations(trend_id: Optional[str] = None, min_correlation: float = 0.3):
    """Get trend correlations."""
    try:
        service = await _get_trend_service_async()
        result = await service.get_correlations(trend_id=trend_id, min_correlation=min_correlation)
        return {"correlations": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Get correlations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trends_router.get("/report/{agent_code}")
async def get_trends_executive_report(agent_code: str):
    """Get agent-tailored trend report."""
    try:
        service = await _get_trend_service_async()
        result = await service.get_agent_report(agent_code.upper())
        return result
    except Exception as e:
        logger.error(f"Get trend report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Commerce Router
# =============================================================================

commerce_router = APIRouter(prefix="/api/v1/modules/commerce", tags=["Commerce"])


@commerce_router.get("/")
async def commerce_overview():
    """Get commerce module overview."""
    service = await _get_commerce_service_async()
    return {
        "module": "commerce",
        "primary_owner": "Vector",
        "stats": service.get_stats(),
    }


@commerce_router.get("/storefronts")
async def list_storefronts():
    """List all storefronts."""
    try:
        service = await _get_commerce_service_async()
        storefronts = service.list_storefronts()
        return {"storefronts": storefronts, "count": len(storefronts)}
    except Exception as e:
        logger.error(f"List storefronts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@commerce_router.get("/storefronts/{storefront_id}")
async def get_storefront(storefront_id: str):
    """Get storefront details."""
    try:
        service = await _get_commerce_service_async()
        result = service.get_storefront(storefront_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Storefront not found: {storefront_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get storefront failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@commerce_router.get("/storefronts/{storefront_id}/products")
async def get_storefront_products(storefront_id: str, limit: int = 50):
    """Get products from a storefront."""
    try:
        service = await _get_commerce_service_async()
        products = await service.get_products(storefront_key=storefront_id, limit=limit)
        return {"products": products, "count": len(products)}
    except Exception as e:
        logger.error(f"Get products failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@commerce_router.get("/analytics")
async def get_commerce_analytics():
    """Get analytics across all storefronts."""
    try:
        service = await _get_commerce_service_async()
        result = await service.get_all_analytics()
        return result
    except Exception as e:
        logger.error(f"Get analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@commerce_router.get("/margins")
async def get_margin_analysis(storefront_id: Optional[str] = None):
    """Get margin analysis."""
    try:
        service = await _get_commerce_service_async()
        result = await service.get_margin_analysis(storefront_key=storefront_id)
        return result
    except Exception as e:
        logger.error(f"Get margin analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@commerce_router.get("/inventory/alerts")
async def get_inventory_alerts(threshold: int = 10):
    """Get inventory alerts."""
    try:
        service = await _get_commerce_service_async()
        result = await service.get_inventory_alerts(low_stock_threshold=threshold)
        return result
    except Exception as e:
        logger.error(f"Get inventory alerts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@commerce_router.post("/pricing/optimize/{storefront_id}")
async def optimize_pricing(
    storefront_id: str,
    target_margin: float = 40.0,
    strategy: str = "cost_plus",
):
    """Get pricing optimization recommendations."""
    try:
        service = await _get_commerce_service_async()
        result = await service.optimize_pricing(
            storefront_key=storefront_id,
            target_margin=target_margin,
            strategy=strategy,
        )
        return result
    except Exception as e:
        logger.error(f"Optimize pricing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@commerce_router.get("/report/{agent_code}")
async def get_commerce_executive_report(agent_code: str):
    """Get agent-tailored commerce report."""
    try:
        service = await _get_commerce_service_async()
        result = await service.get_agent_report(agent_code.upper())
        return result
    except Exception as e:
        logger.error(f"Get commerce report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Brand Router
# =============================================================================

brand_router = APIRouter(prefix="/api/v1/modules/brand", tags=["Brand"])


@brand_router.get("/")
async def brand_overview():
    """Get brand module overview."""
    service = await _get_brand_service_async()
    return {
        "module": "brand",
        "primary_owner": "Echo",
        "stats": service.get_stats(),
    }


@brand_router.get("/identity")
async def get_brand_identity():
    """Get current brand identity."""
    try:
        service = await _get_brand_service_async()
        result = service.get_identity()
        if result is None:
            return {"message": "No brand identity created yet"}
        return result
    except Exception as e:
        logger.error(f"Get identity failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@brand_router.post("/identity")
async def create_brand_identity(request: BrandIdentityCreate):
    """Create brand identity."""
    try:
        service = await _get_brand_service_async()
        result = service.create_identity(
            name=request.name,
            tagline=request.tagline,
            mission=request.mission,
            primary_tone=request.primary_tone,
            primary_color=request.primary_color,
        )
        return result
    except Exception as e:
        logger.error(f"Create identity failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@brand_router.post("/validate")
async def validate_content(request: ContentValidationRequest):
    """Validate content against brand guidelines."""
    try:
        service = await _get_brand_service_async()
        result = service.validate_content(
            content=request.content,
            content_type=request.content_type,
        )
        return result
    except Exception as e:
        logger.error(f"Validate content failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@brand_router.post("/consistency")
async def check_consistency(request: ConsistencyCheckRequest):
    """Check brand consistency across content samples."""
    try:
        service = await _get_brand_service_async()
        result = service.check_consistency(request.samples)
        return result
    except Exception as e:
        logger.error(f"Check consistency failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@brand_router.get("/guidelines")
async def get_guidelines(category: Optional[str] = None):
    """Get brand guidelines."""
    try:
        service = await _get_brand_service_async()
        result = service.get_guidelines(category=category)
        return {"guidelines": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Get guidelines failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@brand_router.post("/guidelines")
async def add_guideline(request: BrandGuidelineCreate):
    """Add a brand guideline."""
    try:
        service = await _get_brand_service_async()
        guideline_id = service.add_guideline(
            category=request.category,
            title=request.title,
            description=request.description,
            rule_type=request.rule_type,
        )
        return {"success": True, "guideline_id": guideline_id}
    except Exception as e:
        logger.error(f"Add guideline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@brand_router.get("/kit")
async def get_brand_kit():
    """Get complete brand kit."""
    try:
        service = await _get_brand_service_async()
        result = service.get_brand_kit()
        return result
    except Exception as e:
        logger.error(f"Get brand kit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@brand_router.get("/report/{agent_code}")
async def get_brand_executive_report(agent_code: str):
    """Get agent-tailored brand report."""
    try:
        service = await _get_brand_service_async()
        result = service.get_agent_report(agent_code.upper())
        return result
    except Exception as e:
        logger.error(f"Get brand report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Scheduler Router
# =============================================================================

scheduler_router = APIRouter(prefix="/api/v1/modules/scheduler", tags=["Scheduler"])


@scheduler_router.get("/")
async def scheduler_overview():
    """Get scheduler module overview."""
    service = await _get_scheduler_service_async()
    return {
        "module": "scheduler",
        "primary_owner": "Nexus",
        "stats": service.get_stats(),
    }


@scheduler_router.get("/tasks")
async def list_scheduled_tasks(
    owner_executive: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
):
    """List scheduled tasks."""
    try:
        service = await _get_scheduler_service_async()
        result = service.list_tasks(
            owner_executive=owner_executive,
            category=category,
            status=status,
        )
        return {"tasks": result, "count": len(result)}
    except Exception as e:
        logger.error(f"List tasks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@scheduler_router.post("/tasks")
async def schedule_task(request: ScheduleTaskRequest):
    """Schedule a new task."""
    try:
        service = await _get_scheduler_service_async()
        task_id = service.schedule_task(
            name=request.name,
            handler_name=request.handler_name,
            description=request.description,
            frequency=request.frequency,
            priority=request.priority,
            owner_executive=request.owner_executive,
            hour=request.hour,
            minute=request.minute,
        )
        return {"success": True, "task_id": task_id}
    except Exception as e:
        logger.error(f"Schedule task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@scheduler_router.post("/tasks/template/{template_name}")
async def schedule_from_template(template_name: str):
    """Schedule a task from a template."""
    try:
        service = await _get_scheduler_service_async()
        task_id = service.schedule_from_template(template_name)
        return {"success": True, "task_id": task_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Schedule from template failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@scheduler_router.post("/tasks/{task_id}/run")
async def run_task_now(task_id: str):
    """Run a task immediately."""
    try:
        service = await _get_scheduler_service_async()
        result = await service.run_task_now(task_id)
        return result
    except Exception as e:
        logger.error(f"Run task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@scheduler_router.post("/tasks/{task_id}/enable")
async def enable_task(task_id: str):
    """Enable a paused task."""
    try:
        service = await _get_scheduler_service_async()
        success = service.enable_task(task_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Enable task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@scheduler_router.post("/tasks/{task_id}/disable")
async def disable_task(task_id: str):
    """Disable a task."""
    try:
        service = await _get_scheduler_service_async()
        success = service.disable_task(task_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Disable task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@scheduler_router.get("/workflows")
async def list_workflows(owner_executive: Optional[str] = None):
    """List available workflows."""
    try:
        service = await _get_scheduler_service_async()
        result = service.list_workflows(owner_executive=owner_executive)
        return {"workflows": result, "count": len(result)}
    except Exception as e:
        logger.error(f"List workflows failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@scheduler_router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, request: WorkflowExecuteRequest):
    """Execute a workflow."""
    try:
        service = await _get_scheduler_service_async()
        result = await service.execute_workflow(
            workflow_id=workflow_id,
            initial_context=request.context,
        )
        return result
    except Exception as e:
        logger.error(f"Execute workflow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@scheduler_router.post("/autonomous-cycle")
async def run_autonomous_cycle():
    """Run autonomous operational cycle."""
    try:
        service = await _get_scheduler_service_async()
        result = await service.run_autonomous_cycle()
        return result
    except Exception as e:
        logger.error(f"Autonomous cycle failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@scheduler_router.get("/report/{agent_code}")
async def get_scheduler_executive_report(agent_code: str):
    """Get agent-tailored scheduler report."""
    try:
        service = await _get_scheduler_service_async()
        result = service.get_agent_report(agent_code.upper())
        return result
    except Exception as e:
        logger.error(f"Get scheduler report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Modules Overview Router
# =============================================================================

modules_router = APIRouter(prefix="/api/v1/modules", tags=["Modules"])


@modules_router.get("/")
async def modules_overview():
    """Get overview of all autonomous modules."""
    from ag3ntwerk.modules import MODULE_REGISTRY

    modules = []
    for name, info in MODULE_REGISTRY.items():
        modules.append(
            {
                "name": name,
                "description": info["description"],
                "primary_owners": info["primary_owners"],
                "secondary_owners": info["secondary_owners"],
                "capabilities": info["capabilities"],
            }
        )

    return {
        "modules": modules,
        "count": len(modules),
        "timestamp": datetime.now().isoformat(),
    }


@modules_router.get("/status")
async def modules_status():
    """Get status of all module services."""
    status = {
        "trends": {
            "initialized": _trend_service is not None,
            "stats": (
                (await (await _get_trend_service_async()).get_stats()) if _trend_service else None
            ),
        },
        "commerce": {
            "initialized": _commerce_service is not None,
            "stats": (
                (await _get_commerce_service_async()).get_stats() if _commerce_service else None
            ),
        },
        "brand": {
            "initialized": _brand_service is not None,
            "stats": (await _get_brand_service_async()).get_stats() if _brand_service else None,
        },
        "scheduler": {
            "initialized": _scheduler_service is not None,
            "stats": (
                (await _get_scheduler_service_async()).get_stats() if _scheduler_service else None
            ),
        },
    }

    return {
        "modules": status,
        "timestamp": datetime.now().isoformat(),
    }
