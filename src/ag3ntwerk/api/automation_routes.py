"""
Automation API Routes - FastAPI routes for autonomous automation modules.

Provides REST API access to research automation, data harvesting,
and security automation functionality.
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


class ResearchRequest(BaseModel):
    context: Dict[str, Any] = Field(default_factory=dict)


class ScheduleResearchRequest(BaseModel):
    research_type: str
    interval_hours: float = 24.0


class DataSourceRegisterRequest(BaseModel):
    name: str
    source_type: str
    config: Dict[str, Any] = Field(default_factory=dict)


class ScheduleHarvestRequest(BaseModel):
    source_name: str
    interval_hours: float = 12.0


class HarvestCycleRequest(BaseModel):
    source_names: Optional[List[str]] = None


class SecurityScanRequest(BaseModel):
    context: Dict[str, Any] = Field(default_factory=dict)


class AcknowledgeAlertRequest(BaseModel):
    alert_id: str


class IncidentResponseRequest(BaseModel):
    incident_id: str
    severity: str = "medium"
    context: Dict[str, Any] = Field(default_factory=dict)


class ScheduleMonitoringRequest(BaseModel):
    interval_minutes: int = 30


# =============================================================================
# Engine Singletons (double-checked locking)
# =============================================================================

_research_engine = None
_research_init_lock = asyncio.Lock()
_harvesting_engine = None
_harvesting_init_lock = asyncio.Lock()
_security_engine = None
_security_init_lock = asyncio.Lock()


def get_research_engine():
    """Get or create AutonomousResearchEngine singleton (sync fast-path)."""
    global _research_engine
    if _research_engine is None:
        from ag3ntwerk.modules.autonomous_research import AutonomousResearchEngine

        _research_engine = AutonomousResearchEngine()
    return _research_engine


async def _get_research_engine_async():
    """Get or create AutonomousResearchEngine singleton with async lock."""
    global _research_engine
    if _research_engine is None:
        async with _research_init_lock:
            if _research_engine is None:
                from ag3ntwerk.modules.autonomous_research import AutonomousResearchEngine

                _research_engine = AutonomousResearchEngine()
    return _research_engine


def get_harvesting_engine():
    """Get or create DataHarvestingEngine singleton (sync fast-path)."""
    global _harvesting_engine
    if _harvesting_engine is None:
        from ag3ntwerk.modules.autonomous_data_harvesting import DataHarvestingEngine

        _harvesting_engine = DataHarvestingEngine()
    return _harvesting_engine


async def _get_harvesting_engine_async():
    """Get or create DataHarvestingEngine singleton with async lock."""
    global _harvesting_engine
    if _harvesting_engine is None:
        async with _harvesting_init_lock:
            if _harvesting_engine is None:
                from ag3ntwerk.modules.autonomous_data_harvesting import DataHarvestingEngine

                _harvesting_engine = DataHarvestingEngine()
    return _harvesting_engine


def get_security_engine():
    """Get or create SecurityAutomationEngine singleton (sync fast-path)."""
    global _security_engine
    if _security_engine is None:
        from ag3ntwerk.modules.autonomous_security import SecurityAutomationEngine

        _security_engine = SecurityAutomationEngine()
    return _security_engine


async def _get_security_engine_async():
    """Get or create SecurityAutomationEngine singleton with async lock."""
    global _security_engine
    if _security_engine is None:
        async with _security_init_lock:
            if _security_engine is None:
                from ag3ntwerk.modules.autonomous_security import SecurityAutomationEngine

                _security_engine = SecurityAutomationEngine()
    return _security_engine


# =============================================================================
# Research Automation Router
# =============================================================================

research_router = APIRouter(
    prefix="/api/v1/automation/research",
    tags=["Research Automation"],
)


@research_router.get("/")
async def research_overview():
    """Get research automation module overview and status."""
    engine = await _get_research_engine_async()
    return {
        "module": "research_automation",
        "primary_owner": "Axiom",
        "status": engine.get_research_status(),
    }


@research_router.post("/market-scan")
async def run_market_scan(request: ResearchRequest):
    """Execute an autonomous market intelligence scan."""
    engine = await _get_research_engine_async()
    try:
        result = await engine.run_market_scan(request.context or None)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Market scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Market scan failed: {e}")


@research_router.post("/competitive-analysis")
async def run_competitive_analysis(request: ResearchRequest):
    """Execute an autonomous competitive intelligence analysis."""
    engine = await _get_research_engine_async()
    try:
        result = await engine.run_competitive_analysis(request.context or None)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Competitive analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Competitive analysis failed: {e}")


@research_router.post("/trend-research")
async def run_trend_research(request: ResearchRequest):
    """Execute autonomous trend deep research."""
    engine = await _get_research_engine_async()
    try:
        result = await engine.run_trend_research(request.context or None)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Trend research failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trend research failed: {e}")


@research_router.post("/technology-scan")
async def run_technology_scan(request: ResearchRequest):
    """Execute an autonomous technology radar scan."""
    engine = await _get_research_engine_async()
    try:
        result = await engine.run_technology_scan(request.context or None)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Technology scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Technology scan failed: {e}")


@research_router.get("/history")
async def get_research_history(
    limit: int = Query(20, ge=1, le=100),
    research_type: Optional[str] = Query(None),
):
    """Get research execution history."""
    engine = await _get_research_engine_async()
    return engine.get_research_history(limit=limit, research_type=research_type)


@research_router.get("/insights")
async def get_research_insights(
    max_age_hours: float = Query(72.0, ge=1.0, le=720.0),
):
    """Get aggregated insights from recent research."""
    engine = await _get_research_engine_async()
    return engine.get_insights_summary(max_age_hours=max_age_hours)


@research_router.post("/schedule")
async def schedule_recurring_research(request: ScheduleResearchRequest):
    """Schedule recurring research of a specific type."""
    engine = await _get_research_engine_async()
    try:
        engine.schedule_recurring_research(request.research_type, request.interval_hours)
        return {
            "success": True,
            "research_type": request.research_type,
            "interval_hours": request.interval_hours,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@research_router.post("/run-recurring")
async def run_due_recurring_research():
    """Execute all recurring research that is currently due."""
    engine = await _get_research_engine_async()
    results = await engine.run_due_recurring_research()
    return {
        "executed": len(results),
        "results": [r.to_dict() for r in results],
    }


# =============================================================================
# Data Harvesting Router
# =============================================================================

harvesting_router = APIRouter(
    prefix="/api/v1/automation/harvesting",
    tags=["Data Harvesting"],
)


@harvesting_router.get("/")
async def harvesting_overview():
    """Get data harvesting module overview and status."""
    engine = await _get_harvesting_engine_async()
    return {
        "module": "data_harvesting",
        "primary_owner": "Index",
        "status": engine.get_harvest_status(),
    }


@harvesting_router.post("/sources")
async def register_data_source(request: DataSourceRegisterRequest):
    """Register a new data source for harvesting."""
    engine = await _get_harvesting_engine_async()
    try:
        engine.register_source(request.name, request.source_type, request.config)
        return {
            "success": True,
            "source": request.name,
            "type": request.source_type,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@harvesting_router.delete("/sources/{source_name}")
async def remove_data_source(source_name: str):
    """Remove a registered data source."""
    engine = await _get_harvesting_engine_async()
    try:
        engine.remove_source(source_name)
        return {"success": True, "removed": source_name}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Source not found: {source_name}")


@harvesting_router.get("/sources")
async def list_data_sources():
    """List all registered data sources."""
    engine = await _get_harvesting_engine_async()
    return {"sources": engine.list_sources()}


@harvesting_router.post("/harvest")
async def run_harvest_cycle(request: HarvestCycleRequest):
    """Execute a data harvesting cycle."""
    engine = await _get_harvesting_engine_async()
    try:
        result = await engine.run_harvest_cycle(request.source_names)
        return result
    except Exception as e:
        logger.error(f"Harvest cycle failed: {e}")
        raise HTTPException(status_code=500, detail=f"Harvest cycle failed: {e}")


@harvesting_router.get("/history")
async def get_harvest_history(
    limit: int = Query(20, ge=1, le=100),
):
    """Get data harvesting execution history."""
    engine = await _get_harvesting_engine_async()
    return {"history": engine.get_harvest_history(limit=limit)}


@harvesting_router.get("/quality")
async def get_data_quality_report():
    """Get data quality metrics across all sources."""
    engine = await _get_harvesting_engine_async()
    return engine.get_data_quality_report()


@harvesting_router.post("/schedule")
async def schedule_harvest(request: ScheduleHarvestRequest):
    """Schedule recurring data harvesting for a source."""
    engine = await _get_harvesting_engine_async()
    try:
        engine.schedule_harvest(request.source_name, request.interval_hours)
        return {
            "success": True,
            "source": request.source_name,
            "interval_hours": request.interval_hours,
        }
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Security Automation Router
# =============================================================================

security_router = APIRouter(
    prefix="/api/v1/automation/security",
    tags=["Security Automation"],
)


@security_router.get("/")
async def security_overview():
    """Get security automation module overview and posture."""
    engine = await _get_security_engine_async()
    return {
        "module": "security_automation",
        "primary_owner": "Sentinel",
        "posture": engine.get_security_posture(),
    }


@security_router.post("/scan")
async def run_security_scan(request: SecurityScanRequest):
    """Execute an autonomous security scan."""
    engine = await _get_security_engine_async()
    try:
        result = await engine.run_security_scan()
        return result.to_dict()
    except Exception as e:
        logger.error(f"Security scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Security scan failed: {e}")


@security_router.get("/threat-assessment")
async def get_threat_assessment():
    """Get current threat assessment based on tracked events."""
    engine = await _get_security_engine_async()
    return engine.get_threat_assessment()


@security_router.get("/posture")
async def get_security_posture():
    """Get detailed security posture report."""
    engine = await _get_security_engine_async()
    return engine.get_security_posture()


@security_router.get("/alerts")
async def get_security_alerts(
    limit: int = Query(50, ge=1, le=200),
):
    """Get security alert history."""
    engine = await _get_security_engine_async()
    return {"alerts": engine.get_alert_history(limit=limit)}


@security_router.post("/alerts/acknowledge")
async def acknowledge_security_alert(request: AcknowledgeAlertRequest):
    """Acknowledge and resolve a security alert."""
    engine = await _get_security_engine_async()
    success = engine.acknowledge_alert(request.alert_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert not found: {request.alert_id}")
    return {"success": True, "alert_id": request.alert_id, "status": "resolved"}


@security_router.get("/compliance")
async def get_compliance_status():
    """Get compliance audit status and results."""
    engine = await _get_security_engine_async()
    return engine.get_compliance_status()


@security_router.post("/full-audit")
async def run_full_security_audit():
    """Execute a comprehensive security audit across all domains."""
    engine = await _get_security_engine_async()
    try:
        results = await engine.run_full_audit()
        return {
            "audit_type": "full",
            "workflows_executed": len(results),
            "results": [r.to_dict() for r in results],
        }
    except Exception as e:
        logger.error(f"Full audit failed: {e}")
        raise HTTPException(status_code=500, detail=f"Full audit failed: {e}")


@security_router.post("/incident-response")
async def trigger_incident_response(request: IncidentResponseRequest):
    """Trigger automated incident response workflow."""
    engine = await _get_security_engine_async()
    try:
        from ag3ntwerk.modules.autonomous_security import IncidentResponseWorkflow

        workflow = IncidentResponseWorkflow()
        result = await workflow.execute(
            context={
                "incident_id": request.incident_id,
                "severity": request.severity,
                **request.context,
            }
        )
        return result.to_dict()
    except Exception as e:
        logger.error(f"Incident response failed: {e}")
        raise HTTPException(status_code=500, detail=f"Incident response failed: {e}")


@security_router.post("/access-review")
async def run_access_review():
    """Execute automated access review and privilege audit."""
    engine = await _get_security_engine_async()
    try:
        from ag3ntwerk.modules.autonomous_security import AccessReviewWorkflow

        workflow = AccessReviewWorkflow()
        result = await workflow.execute()
        return result.to_dict()
    except Exception as e:
        logger.error(f"Access review failed: {e}")
        raise HTTPException(status_code=500, detail=f"Access review failed: {e}")


@security_router.post("/monitoring/schedule")
async def schedule_security_monitoring(request: ScheduleMonitoringRequest):
    """Configure continuous security monitoring schedule."""
    engine = await _get_security_engine_async()
    engine.schedule_monitoring(request.interval_minutes)
    return {
        "success": True,
        "interval_minutes": request.interval_minutes,
    }
