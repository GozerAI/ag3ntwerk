"""
Module Integration - Wires modules to agent agents.

Provides seamless integration between the autonomous modules
(trends, commerce, brand, scheduler) and their owning agents.
"""

import logging
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ag3ntwerk.core.base import Task, TaskResult, TaskStatus
from ag3ntwerk.modules import MODULE_REGISTRY

if TYPE_CHECKING:
    from ag3ntwerk.modules.trends import TrendService
    from ag3ntwerk.modules.commerce import CommerceService
    from ag3ntwerk.modules.brand import BrandService
    from ag3ntwerk.modules.scheduler import SchedulerService
    from ag3ntwerk.modules.vls import VLSService
    from ag3ntwerk.modules.autonomous_research import AutonomousResearchEngine
    from ag3ntwerk.modules.autonomous_data_harvesting import DataHarvestingEngine
    from ag3ntwerk.modules.autonomous_security import SecurityAutomationEngine
    from ag3ntwerk.modules.workbench import WorkbenchService
    from ag3ntwerk.modules.swarm_bridge.service import SwarmBridgeService
    from ag3ntwerk.modules.distributed.fleet import FleetOrchestrator
    from ag3ntwerk.modules.metacognition.service import MetacognitionService

logger = logging.getLogger(__name__)


class ModuleIntegration:
    """
    Integrates autonomous modules with agent agents.

    Provides a unified interface for agents to access their
    assigned module functionality.

    Example:
        ```python
        integration = ModuleIntegration()

        # Echo can access trends and brand modules
        trend_report = integration.get_module_report("trends", "Echo")
        brand_report = integration.get_module_report("brand", "Echo")

        # Vector can access commerce module
        commerce_report = integration.get_module_report("commerce", "Vector")
        ```
    """

    def __init__(self):
        """Initialize module integration."""
        self._trend_service: Optional["TrendService"] = None
        self._commerce_service: Optional["CommerceService"] = None
        self._brand_service: Optional["BrandService"] = None
        self._scheduler_service: Optional["SchedulerService"] = None
        self._vls_service: Optional["VLSService"] = None
        self._research_engine: Optional["AutonomousResearchEngine"] = None
        self._harvesting_engine: Optional["DataHarvestingEngine"] = None
        self._security_engine: Optional["SecurityAutomationEngine"] = None
        self._workbench_service: Optional["WorkbenchService"] = None
        self._swarm_bridge_service: Optional["SwarmBridgeService"] = None
        self._fleet_orchestrator: Optional["FleetOrchestrator"] = None
        self._metacognition_service: Optional["MetacognitionService"] = None
        self._learning_orchestrator: Optional[Any] = None

    def connect_learning(self, orchestrator) -> None:
        """Connect a learning orchestrator for module feedback recording.

        Args:
            orchestrator: LearningOrchestrator instance
        """
        self._learning_orchestrator = orchestrator

    @property
    def trend_service(self) -> "TrendService":
        """Lazy-load trend service."""
        if self._trend_service is None:
            from ag3ntwerk.modules.trends import TrendService

            self._trend_service = TrendService()
        return self._trend_service

    @property
    def commerce_service(self) -> "CommerceService":
        """Lazy-load commerce service."""
        if self._commerce_service is None:
            from ag3ntwerk.modules.commerce import CommerceService

            self._commerce_service = CommerceService()
        return self._commerce_service

    @property
    def brand_service(self) -> "BrandService":
        """Lazy-load brand service."""
        if self._brand_service is None:
            from ag3ntwerk.modules.brand import BrandService

            self._brand_service = BrandService()
        return self._brand_service

    @property
    def scheduler_service(self) -> "SchedulerService":
        """Lazy-load scheduler service."""
        if self._scheduler_service is None:
            from ag3ntwerk.modules.scheduler import SchedulerService

            self._scheduler_service = SchedulerService()
        return self._scheduler_service

    @property
    def vls_service(self) -> "VLSService":
        """Lazy-load VLS service."""
        if self._vls_service is None:
            from ag3ntwerk.modules.vls import VLSService

            self._vls_service = VLSService()
        return self._vls_service

    @property
    def research_engine(self) -> "AutonomousResearchEngine":
        """Lazy-load autonomous research engine."""
        if self._research_engine is None:
            from ag3ntwerk.modules.autonomous_research import AutonomousResearchEngine

            self._research_engine = AutonomousResearchEngine(integration=self)
        return self._research_engine

    @property
    def harvesting_engine(self) -> "DataHarvestingEngine":
        """Lazy-load data harvesting engine."""
        if self._harvesting_engine is None:
            from ag3ntwerk.modules.autonomous_data_harvesting import DataHarvestingEngine

            self._harvesting_engine = DataHarvestingEngine(integration=self)
        return self._harvesting_engine

    @property
    def security_engine(self) -> "SecurityAutomationEngine":
        """Lazy-load security automation engine."""
        if self._security_engine is None:
            from ag3ntwerk.modules.autonomous_security import SecurityAutomationEngine

            self._security_engine = SecurityAutomationEngine(integration=self)
        return self._security_engine

    @property
    def workbench_service(self) -> "WorkbenchService":
        """Lazy-load workbench service."""
        if self._workbench_service is None:
            from ag3ntwerk.modules.workbench import WorkbenchService

            self._workbench_service = WorkbenchService()
        return self._workbench_service

    @property
    def swarm_bridge_service(self) -> "SwarmBridgeService":
        """Lazy-load swarm bridge service."""
        if self._swarm_bridge_service is None:
            from ag3ntwerk.modules.swarm_bridge.service import SwarmBridgeService

            self._swarm_bridge_service = SwarmBridgeService()
        return self._swarm_bridge_service

    @property
    def fleet_orchestrator(self) -> "FleetOrchestrator":
        """Lazy-load fleet orchestrator."""
        if self._fleet_orchestrator is None:
            from ag3ntwerk.modules.distributed.fleet import FleetOrchestrator

            self._fleet_orchestrator = FleetOrchestrator()
        return self._fleet_orchestrator

    @property
    def metacognition_service(self) -> "MetacognitionService":
        """Lazy-load metacognition service."""
        if self._metacognition_service is None:
            from ag3ntwerk.modules.metacognition.service import MetacognitionService

            self._metacognition_service = MetacognitionService()
        return self._metacognition_service

    def get_modules_for_executive(self, agent_code: str) -> List[str]:
        """Get list of modules available to an agent."""
        from ag3ntwerk.modules import get_modules_for_executive

        return get_modules_for_executive(agent_code)

    async def get_module_report(
        self,
        module_id: str,
        agent_code: str,
    ) -> Dict[str, Any]:
        """
        Get a module report tailored for a specific agent.

        Args:
            module_id: Module identifier (trends, commerce, brand, scheduler)
            agent_code: Agent code requesting the report

        Returns:
            Agent-tailored report from the module
        """
        if module_id == "trends":
            return await self.trend_service.get_agent_report(agent_code)
        elif module_id == "commerce":
            return await self.commerce_service.get_agent_report(agent_code)
        elif module_id == "brand":
            return self.brand_service.get_agent_report(agent_code)
        elif module_id == "scheduler":
            return self.scheduler_service.get_agent_report(agent_code)
        elif module_id == "vls":
            return await self.vls_service.get_agent_report(agent_code)
        elif module_id == "research_automation":
            return self.research_engine.get_research_status()
        elif module_id == "data_harvesting":
            return self.harvesting_engine.get_harvest_status()
        elif module_id == "security_automation":
            return self.security_engine.get_security_posture()
        else:
            return {"error": f"Unknown module: {module_id}"}

    async def get_all_reports_for_executive(
        self,
        agent_code: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all module reports for an agent.

        Args:
            agent_code: Agent code

        Returns:
            Dict mapping module_id to report
        """
        modules = self.get_modules_for_executive(agent_code)
        reports = {}

        for module_id in modules:
            try:
                reports[module_id] = await self.get_module_report(module_id, agent_code)
            except Exception as e:
                reports[module_id] = {"error": str(e)}

        return reports

    async def execute_module_task(
        self,
        module_id: str,
        task_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a task on a specific module.

        Records timing and outcome to the learning system when connected.

        Args:
            module_id: Module identifier
            task_type: Type of task to execute
            params: Task parameters

        Returns:
            Task result
        """
        start = time.perf_counter()
        error_msg: Optional[str] = None
        success = True

        try:
            if module_id == "trends":
                result = await self._execute_trend_task(task_type, params)
            elif module_id == "commerce":
                result = await self._execute_commerce_task(task_type, params)
            elif module_id == "brand":
                result = self._execute_brand_task(task_type, params)
            elif module_id == "scheduler":
                result = await self._execute_scheduler_task(task_type, params)
            elif module_id == "research_automation":
                result = await self._execute_research_task(task_type, params)
            elif module_id == "data_harvesting":
                result = await self._execute_harvesting_task(task_type, params)
            elif module_id == "security_automation":
                result = await self._execute_security_task(task_type, params)
            else:
                result = {"error": f"Unknown module: {module_id}"}

            if isinstance(result, dict) and result.get("error"):
                success = False
                error_msg = result["error"]

            return result

        except Exception as exc:
            success = False
            error_msg = str(exc)
            raise

        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            await self._record_module_outcome(module_id, task_type, success, duration_ms, error_msg)

    async def _record_module_outcome(
        self,
        module_id: str,
        task_type: str,
        success: bool,
        duration_ms: float,
        error: Optional[str],
    ) -> None:
        """Record module execution outcome to learning system (best-effort)."""
        if not self._learning_orchestrator:
            return
        try:
            from ag3ntwerk.learning.models import HierarchyPath

            hierarchy_path = HierarchyPath(
                agent=f"module.{module_id}",
                manager=None,
                specialist=None,
            )
            await self._learning_orchestrator.record_outcome(
                task_id=f"module-{module_id}-{task_type}-{int(time.time())}",
                task_type=f"module.{module_id}.{task_type}",
                hierarchy_path=hierarchy_path,
                success=success,
                duration_ms=duration_ms,
                error=error,
            )
        except Exception as e:
            logger.debug(f"Module learning recording failed: {e}")

    async def _execute_trend_task(
        self,
        task_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a trend module task."""
        if task_type == "run_analysis":
            return await self.trend_service.run_analysis_cycle(
                sources=params.get("sources"),
            )
        elif task_type == "get_trending":
            return self.trend_service.get_trending(
                category=params.get("category"),
                min_score=params.get("min_score", 0),
                limit=params.get("limit", 20),
            )
        elif task_type == "identify_niches":
            return self.trend_service.identify_niches(
                min_opportunity_score=params.get("min_opportunity_score", 50),
            )
        elif task_type == "get_correlations":
            return self.trend_service.get_correlations(
                trend_id=params.get("trend_id"),
            )
        else:
            return {"error": f"Unknown trend task type: {task_type}"}

    async def _execute_commerce_task(
        self,
        task_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a commerce module task."""
        if task_type == "list_storefronts":
            return self.commerce_service.list_storefronts()
        elif task_type == "get_products":
            return await self.commerce_service.get_products(
                storefront_id=params.get("storefront_id", ""),
                collection=params.get("collection"),
                limit=params.get("limit", 50),
            )
        elif task_type == "update_price":
            return await self.commerce_service.update_price(
                storefront_id=params.get("storefront_id", ""),
                product_id=params.get("product_id", ""),
                new_price=params.get("new_price", 0),
            )
        elif task_type == "get_margin_analysis":
            return self.commerce_service.get_margin_analysis(
                storefront_id=params.get("storefront_id"),
            )
        elif task_type == "optimize_pricing":
            return self.commerce_service.optimize_pricing(
                storefront_id=params.get("storefront_id", ""),
                target_margin=params.get("target_margin", 40.0),
                strategy=params.get("strategy", "cost_plus"),
            )
        elif task_type == "get_low_stock":
            return self.commerce_service.get_low_stock_alerts(
                threshold=params.get("threshold", 10),
            )
        else:
            return {"error": f"Unknown commerce task type: {task_type}"}

    def _execute_brand_task(
        self,
        task_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a brand module task."""
        if task_type == "create_identity":
            return self.brand_service.create_identity(
                name=params.get("name", ""),
                tagline=params.get("tagline", ""),
                mission=params.get("mission", ""),
                primary_tone=params.get("primary_tone", "professional"),
                primary_color=params.get("primary_color"),
            )
        elif task_type == "get_identity":
            result = self.brand_service.get_identity()
            return result if result else {"error": "No brand identity created"}
        elif task_type == "validate_content":
            return self.brand_service.validate_content(
                content=params.get("content", ""),
                content_type=params.get("content_type", "website"),
            )
        elif task_type == "check_consistency":
            return self.brand_service.check_consistency(
                content_samples=params.get("samples", []),
            )
        elif task_type == "get_brand_kit":
            return self.brand_service.get_brand_kit()
        elif task_type == "add_guideline":
            guideline_id = self.brand_service.add_guideline(
                category=params.get("category", ""),
                title=params.get("title", ""),
                description=params.get("description", ""),
                rule_type=params.get("rule_type", "guideline"),
            )
            return {"success": True, "guideline_id": guideline_id}
        else:
            return {"error": f"Unknown brand task type: {task_type}"}

    async def _execute_scheduler_task(
        self,
        task_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a scheduler module task."""
        if task_type == "schedule_task":
            task_id = self.scheduler_service.schedule_task(
                name=params.get("name", ""),
                handler_name=params.get("handler_name", ""),
                description=params.get("description", ""),
                frequency=params.get("frequency", "daily"),
                priority=params.get("priority", "normal"),
                owner_executive=params.get("owner_executive", "Nexus"),
            )
            return {"success": True, "task_id": task_id}
        elif task_type == "list_tasks":
            return {
                "tasks": self.scheduler_service.list_tasks(
                    owner_executive=params.get("owner_executive"),
                    category=params.get("category"),
                    status=params.get("status"),
                )
            }
        elif task_type == "run_task":
            return await self.scheduler_service.run_task_now(
                task_id=params.get("task_id", ""),
            )
        elif task_type == "list_workflows":
            return {
                "workflows": self.scheduler_service.list_workflows(
                    owner_executive=params.get("owner_executive"),
                )
            }
        elif task_type == "execute_workflow":
            return await self.scheduler_service.execute_workflow(
                workflow_id=params.get("workflow_id", ""),
                initial_context=params.get("context"),
            )
        elif task_type == "run_autonomous_cycle":
            return await self.scheduler_service.run_autonomous_cycle()
        else:
            return {"error": f"Unknown scheduler task type: {task_type}"}

    async def _execute_research_task(
        self,
        task_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a research automation task."""
        engine = self.research_engine
        if task_type == "run_market_scan":
            result = await engine.run_market_scan(context=params.get("context"))
            return {
                "success": result.success,
                "workflow": result.workflow_name,
                "steps": len(result.steps),
            }
        elif task_type == "run_competitive_analysis":
            result = await engine.run_competitive_analysis(context=params.get("context"))
            return {
                "success": result.success,
                "workflow": result.workflow_name,
                "steps": len(result.steps),
            }
        elif task_type == "run_trend_research":
            result = await engine.run_trend_research(context=params.get("context"))
            return {
                "success": result.success,
                "workflow": result.workflow_name,
                "steps": len(result.steps),
            }
        elif task_type == "run_technology_scan":
            result = await engine.run_technology_scan(context=params.get("context"))
            return {
                "success": result.success,
                "workflow": result.workflow_name,
                "steps": len(result.steps),
            }
        elif task_type == "get_insights_summary":
            return engine.get_insights_summary(
                max_age_hours=params.get("max_age_hours", 24.0),
            )
        elif task_type == "get_research_history":
            return {
                "history": engine.get_research_history(
                    limit=params.get("limit", 20),
                    research_type=params.get("research_type"),
                ),
            }
        else:
            return {"error": f"Unknown research task type: {task_type}"}

    async def _execute_harvesting_task(
        self,
        task_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a data harvesting task."""
        engine = self.harvesting_engine
        if task_type == "register_source":
            from ag3ntwerk.modules.autonomous_data_harvesting import DataSourceType

            source_type = params.get("source_type", "api")
            if isinstance(source_type, str):
                source_type = DataSourceType(source_type)
            return engine.register_source(
                name=params.get("name", ""),
                source_type=source_type,
                config=params.get("config"),
            )
        elif task_type == "remove_source":
            return engine.remove_source(name=params.get("name", ""))
        elif task_type == "list_sources":
            return {"sources": engine.list_sources()}
        elif task_type == "run_harvest_cycle":
            return await engine.run_harvest_cycle(
                source_names=params.get("source_names"),
            )
        elif task_type == "get_data_quality_report":
            return engine.get_data_quality_report()
        elif task_type == "schedule_harvest":
            return engine.schedule_harvest(
                source_name=params.get("source_name", ""),
                interval_hours=params.get("interval_hours", 1.0),
            )
        else:
            return {"error": f"Unknown harvesting task type: {task_type}"}

    async def _execute_security_task(
        self,
        task_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a security automation task."""
        engine = self.security_engine
        if task_type == "run_security_scan":
            result = await engine.run_security_scan(context=params.get("context"))
            return {
                "success": result.success,
                "workflow": result.workflow_name,
                "steps": len(result.steps),
            }
        elif task_type == "run_full_audit":
            results = await engine.run_full_audit(context=params.get("context"))
            return {
                "workflows": {
                    k: {"success": v.success, "steps": len(v.steps)} for k, v in results.items()
                },
            }
        elif task_type == "get_threat_assessment":
            return engine.get_threat_assessment()
        elif task_type == "get_compliance_status":
            return engine.get_compliance_status()
        elif task_type == "get_alert_history":
            return {
                "alerts": engine.get_alert_history(
                    limit=params.get("limit", 20),
                ),
            }
        elif task_type == "acknowledge_alert":
            return engine.acknowledge_alert(
                alert_id=params.get("alert_id", ""),
            )
        elif task_type == "schedule_monitoring":
            return engine.schedule_monitoring(
                interval_minutes=params.get("interval_minutes", 30),
            )
        else:
            return {"error": f"Unknown security task type: {task_type}"}

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from all modules."""
        stats = {}

        try:
            stats["trends"] = self.trend_service.get_stats()
        except Exception as e:
            stats["trends"] = {"error": str(e)}

        try:
            stats["commerce"] = self.commerce_service.get_stats()
        except Exception as e:
            stats["commerce"] = {"error": str(e)}

        try:
            stats["brand"] = self.brand_service.get_stats()
        except Exception as e:
            stats["brand"] = {"error": str(e)}

        try:
            stats["scheduler"] = self.scheduler_service.get_stats()
        except Exception as e:
            stats["scheduler"] = {"error": str(e)}

        try:
            stats["research_automation"] = self.research_engine.get_research_status()
        except Exception as e:
            stats["research_automation"] = {"error": str(e)}

        try:
            stats["data_harvesting"] = self.harvesting_engine.get_harvest_status()
        except Exception as e:
            stats["data_harvesting"] = {"error": str(e)}

        try:
            stats["security_automation"] = self.security_engine.get_security_posture()
        except Exception as e:
            stats["security_automation"] = {"error": str(e)}

        return stats


# Agent-specific module handlers
class EchoModuleHandler:
    """
    Module handler for Echo (Echo).

    Provides Echo-specific access to trends and brand modules.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    async def get_trend_intelligence(self) -> Dict[str, Any]:
        """Get trend intelligence report for Echo."""
        return self._integration.get_module_report("trends", "Echo")

    async def run_trend_analysis(
        self,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run trend analysis cycle."""
        return await self._integration.execute_module_task(
            "trends",
            "run_analysis",
            {"sources": sources},
        )

    def get_brand_report(self) -> Dict[str, Any]:
        """Get brand report for Echo."""
        return self._integration.get_module_report("brand", "Echo")

    def validate_content(
        self,
        content: str,
        content_type: str = "website",
    ) -> Dict[str, Any]:
        """Validate content against brand guidelines."""
        return self._integration._execute_brand_task(
            "validate_content",
            {"content": content, "content_type": content_type},
        )


class VectorModuleHandler:
    """
    Module handler for Vector (Vector).

    Provides Vector-specific access to commerce module.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    def get_commerce_report(self) -> Dict[str, Any]:
        """Get commerce report for Vector."""
        return self._integration.get_module_report("commerce", "Vector")

    async def get_products(
        self,
        storefront_id: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get products from a storefront."""
        return await self._integration.execute_module_task(
            "commerce",
            "get_products",
            {"storefront_id": storefront_id, "limit": limit},
        )

    async def optimize_pricing(
        self,
        storefront_id: str,
        target_margin: float = 40.0,
        strategy: str = "cost_plus",
    ) -> Dict[str, Any]:
        """Optimize pricing for a storefront."""
        return await self._integration.execute_module_task(
            "commerce",
            "optimize_pricing",
            {
                "storefront_id": storefront_id,
                "target_margin": target_margin,
                "strategy": strategy,
            },
        )

    def get_margin_analysis(
        self,
        storefront_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get margin analysis."""
        return self._integration.commerce_service.get_margin_analysis(
            storefront_id=storefront_id,
        )


class NexusModuleHandler:
    """
    Module handler for Nexus (Nexus).

    Provides Nexus-specific access to scheduler module.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    def get_scheduler_report(self) -> Dict[str, Any]:
        """Get scheduler report for Nexus."""
        return self._integration.get_module_report("scheduler", "Nexus")

    def schedule_task(
        self,
        name: str,
        handler_name: str,
        frequency: str = "daily",
        owner_executive: str = "Nexus",
    ) -> str:
        """Schedule a new task."""
        return self._integration.scheduler_service.schedule_task(
            name=name,
            handler_name=handler_name,
            frequency=frequency,
            owner_executive=owner_executive,
        )

    def list_tasks(
        self,
        owner_executive: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all scheduled tasks."""
        return self._integration.scheduler_service.list_tasks(
            owner_executive=owner_executive,
        )

    async def run_autonomous_cycle(self) -> Dict[str, Any]:
        """Run autonomous operational cycle."""
        return await self._integration.scheduler_service.run_autonomous_cycle()

    def get_all_module_stats(self) -> Dict[str, Any]:
        """Get stats from all modules (Nexus has oversight of all)."""
        return self._integration.get_stats()


class CompassModuleHandler:
    """
    Module handler for Compass (Compass).

    Provides Compass-specific access to autonomous research module.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    async def run_market_scan(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run autonomous market intelligence scan."""
        return await self._integration.execute_module_task(
            "research_automation",
            "run_market_scan",
            {"context": context},
        )

    async def run_competitive_analysis(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run competitive analysis."""
        return await self._integration.execute_module_task(
            "research_automation",
            "run_competitive_analysis",
            {"context": context},
        )

    def get_insights_summary(
        self,
        max_age_hours: float = 24.0,
    ) -> Dict[str, Any]:
        """Get aggregated insights from recent research."""
        return self._integration.research_engine.get_insights_summary(
            max_age_hours=max_age_hours,
        )

    def get_research_status(self) -> Dict[str, Any]:
        """Get current research engine status."""
        return self._integration.research_engine.get_research_status()


class IndexModuleHandler:
    """
    Module handler for Index (Index).

    Provides Index-specific access to data harvesting module.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    def register_source(
        self,
        name: str,
        source_type: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Register a new data source for harvesting."""
        from ag3ntwerk.modules.autonomous_data_harvesting import DataSourceType

        return self._integration.harvesting_engine.register_source(
            name=name,
            source_type=DataSourceType(source_type),
            config=config,
        )

    def list_sources(self) -> List[Dict[str, Any]]:
        """List all registered data sources."""
        return self._integration.harvesting_engine.list_sources()

    async def run_harvest_cycle(
        self,
        source_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run a data harvest cycle."""
        return await self._integration.execute_module_task(
            "data_harvesting",
            "run_harvest_cycle",
            {"source_names": source_names},
        )

    def get_data_quality_report(self) -> Dict[str, Any]:
        """Get data quality assessment."""
        return self._integration.harvesting_engine.get_data_quality_report()

    def get_harvest_status(self) -> Dict[str, Any]:
        """Get current harvesting engine status."""
        return self._integration.harvesting_engine.get_harvest_status()


class CitadelModuleHandler:
    """
    Module handler for Citadel (Citadel).

    Provides Citadel-specific access to security automation module.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    async def run_security_scan(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run comprehensive security scan."""
        return await self._integration.execute_module_task(
            "security_automation",
            "run_security_scan",
            {"context": context},
        )

    async def run_full_audit(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run full security audit across all workflows."""
        return await self._integration.execute_module_task(
            "security_automation",
            "run_full_audit",
            {"context": context},
        )

    def get_threat_assessment(self) -> Dict[str, Any]:
        """Get current threat assessment."""
        return self._integration.security_engine.get_threat_assessment()

    def get_security_posture(self) -> Dict[str, Any]:
        """Get overall security posture."""
        return self._integration.security_engine.get_security_posture()

    def acknowledge_alert(self, alert_id: str) -> Dict[str, Any]:
        """Acknowledge a security alert."""
        return self._integration.security_engine.acknowledge_alert(alert_id)


class OverwatchModuleHandler:
    """
    Module handler for Overwatch (Overwatch).

    Provides Overwatch-specific access to metacognition for personality
    oversight, team composition, and cross-agent coordination.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    def get_personality_insights(self) -> Dict[str, Any]:
        """Get personality profile summaries for all registered agents."""
        profiles = self._integration.metacognition_service.get_all_profiles()
        return {
            "agent_count": len(profiles),
            "agents": list(profiles.keys()),
        }

    def get_drift_summary(self) -> Dict[str, Any]:
        """Get personality drift summary across all agents."""
        return self._integration.metacognition_service.get_drift_summary()

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get personality-based routing statistics."""
        return self._integration.metacognition_service.get_routing_stats()

    def suggest_team_for_task(
        self,
        task_traits: Dict[str, float],
        team_size: int = 3,
    ):
        """Suggest optimal team composition for a task."""
        return self._integration.metacognition_service.suggest_team_for_task(
            task_traits,
            team_size,
        )

    def get_all_module_stats(self) -> Dict[str, Any]:
        """Get stats from all modules (Overwatch oversight role)."""
        return self._integration.get_stats()


class ForgeModuleHandler:
    """
    Module handler for Forge (Forge).

    Provides Forge-specific access to workbench, distributed fleet,
    swarm bridge, and research automation modules.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    def get_workbench_status(self) -> Dict[str, Any]:
        """Get development workbench status."""
        return self._integration.workbench_service.get_agent_report("Forge")

    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all development workspaces."""
        return await self._integration.workbench_service.list_workspaces()

    async def delegate_to_swarm(
        self,
        task: str,
        priority: str = "normal",
    ) -> str:
        """Delegate a coding task to the local LLM swarm."""
        return await self._integration.swarm_bridge_service.submit_task(
            prompt=task,
            agent_code="Forge",
            priority=priority,
        )

    async def run_technology_scan(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run autonomous technology radar scan."""
        return await self._integration.execute_module_task(
            "research_automation",
            "run_technology_scan",
            {"context": context},
        )

    def get_distributed_status(self) -> Dict[str, Any]:
        """Get distributed fleet status."""
        return self._integration.fleet_orchestrator.get_fleet_status()


class KeystoneModuleHandler:
    """
    Module handler for Keystone (Keystone).

    Provides Keystone-specific access to commerce module with
    financial focus on margins, revenue, and cost analysis.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    async def get_financial_report(self) -> Dict[str, Any]:
        """Get financial-focused commerce report."""
        return await self._integration.commerce_service.get_agent_report("Keystone")

    async def get_margin_analysis(
        self,
        storefront_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get margin analysis across storefronts."""
        return await self._integration.commerce_service.get_margin_analysis(
            storefront_id=storefront_id,
        )

    def get_revenue_overview(self) -> Dict[str, Any]:
        """Get commerce revenue stats overview."""
        return self._integration.commerce_service.get_stats()


class SentinelModuleHandler:
    """
    Module handler for Sentinel (Sentinel).

    Provides Sentinel-specific IT oversight of security automation
    and distributed infrastructure.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    def get_security_overview(self) -> Dict[str, Any]:
        """Get overall security posture for IT oversight."""
        return self._integration.security_engine.get_security_posture()

    def get_compliance_status(self) -> Dict[str, Any]:
        """Get compliance status across systems."""
        return self._integration.security_engine.get_compliance_status()

    def get_threat_assessment(self) -> Dict[str, Any]:
        """Get current threat assessment."""
        return self._integration.security_engine.get_threat_assessment()

    def get_infrastructure_status(self) -> Dict[str, Any]:
        """Get distributed infrastructure health status."""
        return self._integration.fleet_orchestrator.get_fleet_status()


class BlueprintModuleHandler:
    """
    Module handler for Blueprint (Blueprint).

    Provides Blueprint-specific access to trends module with
    product and innovation focus.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    async def get_product_trends(self) -> Dict[str, Any]:
        """Get product-focused trend intelligence."""
        return await self._integration.trend_service.get_agent_report("Blueprint")

    async def run_trend_analysis(
        self,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run trend analysis cycle for product insights."""
        return await self._integration.execute_module_task(
            "trends",
            "run_analysis",
            {"sources": sources},
        )

    def get_innovation_pipeline(
        self,
        min_opportunity_score: int = 50,
    ) -> Dict[str, Any]:
        """Identify innovation opportunities via niche analysis."""
        return self._integration.trend_service.identify_niches(
            min_opportunity_score=min_opportunity_score,
        )


class AxiomModuleHandler:
    """
    Module handler for Axiom (Axiom).

    Provides Axiom-specific access to trends module with
    research and growth analysis focus.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    async def get_research_trends(self) -> Dict[str, Any]:
        """Get research-focused trend report."""
        return await self._integration.trend_service.get_agent_report("Axiom")

    def get_market_opportunities(
        self,
        min_opportunity_score: int = 50,
    ) -> Dict[str, Any]:
        """Identify market research opportunities."""
        return self._integration.trend_service.identify_niches(
            min_opportunity_score=min_opportunity_score,
        )

    def get_correlations(
        self,
        trend_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get cross-platform trend correlations."""
        return self._integration.trend_service.get_correlations(
            trend_id=trend_id,
        )


class FoundryModuleHandler:
    """
    Module handler for Foundry (Foundry).

    Provides Foundry-specific access to workbench and swarm bridge
    modules for engineering operations.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    def get_workbench_status(self) -> Dict[str, Any]:
        """Get engineering workbench status."""
        return self._integration.workbench_service.get_agent_report("Foundry")

    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all engineering workspaces."""
        return await self._integration.workbench_service.list_workspaces()

    async def delegate_to_swarm(
        self,
        task: str,
        priority: str = "normal",
    ) -> str:
        """Delegate an engineering task to the local LLM swarm."""
        return await self._integration.swarm_bridge_service.submit_task(
            prompt=task,
            agent_code="Foundry",
            priority=priority,
        )

    async def get_swarm_status(self) -> Dict[str, Any]:
        """Get Claude Swarm availability and status."""
        return await self._integration.swarm_bridge_service.get_swarm_status()


class BeaconModuleHandler:
    """
    Module handler for Beacon (Beacon).

    Provides Beacon-specific access to brand module for
    communications and brand consistency.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    def get_brand_report(self) -> Dict[str, Any]:
        """Get brand report for Beacon."""
        return self._integration.brand_service.get_agent_report("Beacon")

    def validate_content(
        self,
        content: str,
        content_type: str = "website",
    ) -> Dict[str, Any]:
        """Validate content against brand guidelines."""
        return self._integration.brand_service.validate_content(
            content,
            content_type,
        )

    def get_brand_kit(self) -> Dict[str, Any]:
        """Get the brand kit."""
        return self._integration.brand_service.get_brand_kit()

    def check_consistency(
        self,
        content_samples: List[str],
    ) -> Dict[str, Any]:
        """Check brand consistency across content samples."""
        return self._integration.brand_service.check_consistency(content_samples)


class AegisModuleHandler:
    """
    Module handler for Aegis (Aegis).

    Provides Aegis-specific access for risk oversight across
    security, VLS, and personality drift monitoring.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    def get_risk_overview(self) -> Dict[str, Any]:
        """Get combined risk overview from security and drift monitoring."""
        security = self._integration.security_engine.get_threat_assessment()
        drift = self._integration.metacognition_service.get_drift_summary()
        return {"security_threats": security, "personality_drift": drift}

    async def get_vls_launches(
        self,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get VLS launches for risk monitoring (stop-loss oversight)."""
        return await self._integration.vls_service.list_launches(status=status)

    def get_compliance_status(self) -> Dict[str, Any]:
        """Get compliance status for risk assessment."""
        return self._integration.security_engine.get_compliance_status()


class AccordModuleHandler:
    """
    Module handler for Accord (Accord).

    Provides Accord-specific access for compliance and
    governance oversight via metacognition and security modules.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or ModuleIntegration()

    def get_governance_report(self) -> Dict[str, Any]:
        """Get governance overview from metacognition."""
        return {
            "drift_summary": self._integration.metacognition_service.get_drift_summary(),
            "routing_stats": self._integration.metacognition_service.get_routing_stats(),
        }

    def get_compliance_status(self) -> Dict[str, Any]:
        """Get compliance status across systems."""
        return self._integration.security_engine.get_compliance_status()

    def get_team_health(self) -> Dict[str, Any]:
        """Get team health and metacognition statistics."""
        return self._integration.metacognition_service.get_stats()


# Singleton integration instance
_integration_instance: Optional[ModuleIntegration] = None


def get_integration() -> ModuleIntegration:
    """Get the shared module integration instance."""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = ModuleIntegration()
    return _integration_instance
