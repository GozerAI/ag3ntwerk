"""
Agent Dashboard API - Unified dashboard endpoints for ag3ntwerk agents.

Provides aggregated views of all module data tailored for each agent role.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.modules import (
    get_modules_for_executive,
    get_integration,
    ModuleIntegration,
)
from ag3ntwerk.modules.autonomous_workflows import AutonomousWorkflowRunner

logger = logging.getLogger(__name__)


@dataclass
class DashboardWidget:
    """A widget for the agent dashboard."""

    id: str
    title: str
    widget_type: str  # metric, chart, table, alert, status
    data: Any
    priority: int = 0
    module: str = ""
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.widget_type,
            "data": self.data,
            "priority": self.priority,
            "module": self.module,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ExecutiveDashboard:
    """Complete dashboard for an agent."""

    agent_code: str
    executive_name: str
    generated_at: datetime
    widgets: List[DashboardWidget] = field(default_factory=list)
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    quick_actions: List[Dict[str, Any]] = field(default_factory=list)
    modules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "executive_name": self.executive_name,
            "generated_at": self.generated_at.isoformat(),
            "widgets": [w.to_dict() for w in self.widgets],
            "alerts": self.alerts,
            "quick_actions": self.quick_actions,
            "modules": self.modules,
            "widget_count": len(self.widgets),
            "alert_count": len(self.alerts),
        }


class DashboardService:
    """
    Service for generating agent dashboards.

    Aggregates data from all modules and creates unified
    dashboard views for each agent.

    Example:
        ```python
        service = DashboardService()

        # Get Echo dashboard
        dashboard = await service.get_dashboard("Echo")
        print(dashboard.to_dict())

        # Get specific widgets
        widgets = await service.get_widgets("Keystone", module="commerce")
        ```
    """

    # Agent metadata
    AGENTS = {
        "CEO": {"name": "Chief Agent Officer", "codename": "Apex"},
        "Nexus": {"name": "Nexus", "codename": "Nexus"},
        "Keystone": {"name": "Keystone", "codename": "Keystone"},
        "Forge": {"name": "Forge", "codename": "Forge"},
        "Echo": {"name": "Echo", "codename": "Echo"},
        "Blueprint": {"name": "Blueprint", "codename": "Blueprint"},
        "Beacon": {"name": "Beacon", "codename": "Beacon"},
        "Index": {"name": "Index", "codename": "Index"},
        "Vector": {"name": "Vector", "codename": "Vector"},
        "Axiom": {"name": "Axiom", "codename": "Axiom"},
        "Compass": {"name": "Compass", "codename": "Compass"},
    }

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or get_integration()
        self._workflow_runner = AutonomousWorkflowRunner(self._integration)

    async def get_dashboard(
        self,
        agent_code: str,
    ) -> ExecutiveDashboard:
        """
        Generate a complete dashboard for an agent.

        Args:
            agent_code: The agent code (CEO, Echo, Keystone, etc.)

        Returns:
            Complete agent dashboard
        """
        exec_info = self.AGENTS.get(agent_code, {})

        dashboard = ExecutiveDashboard(
            agent_code=agent_code,
            executive_name=exec_info.get("name", agent_code),
            generated_at=datetime.now(timezone.utc),
            modules=get_modules_for_executive(agent_code),
        )

        # Get widgets based on agent role
        dashboard.widgets = await self._get_widgets_for_executive(agent_code)

        # Get alerts
        dashboard.alerts = await self._get_alerts_for_executive(agent_code)

        # Get quick actions
        dashboard.quick_actions = self._get_quick_actions_for_executive(agent_code)

        return dashboard

    async def _get_widgets_for_executive(
        self,
        agent_code: str,
    ) -> List[DashboardWidget]:
        """Get widgets for an agent."""
        widgets = []
        modules = get_modules_for_executive(agent_code)

        # Module-specific widgets
        if "trends" in modules:
            widgets.extend(await self._get_trend_widgets(agent_code))

        if "commerce" in modules:
            widgets.extend(await self._get_commerce_widgets(agent_code))

        if "brand" in modules:
            widgets.extend(await self._get_brand_widgets(agent_code))

        if "scheduler" in modules:
            widgets.extend(await self._get_scheduler_widgets(agent_code))

        # Role-specific widgets
        if agent_code == "CEO":
            widgets.extend(await self._get_ceo_widgets())
        elif agent_code == "Nexus":
            widgets.extend(await self._get_coo_widgets())

        # Workflow Library widgets for Nexus, Forge, CEO
        if agent_code in ("Nexus", "Forge", "CEO"):
            widgets.extend(await self._get_workflow_library_widgets())

        # Sort by priority
        widgets.sort(key=lambda w: w.priority, reverse=True)

        return widgets

    async def _get_trend_widgets(
        self,
        agent_code: str,
    ) -> List[DashboardWidget]:
        """Get trend-related widgets."""
        widgets = []

        try:
            report = self._integration.get_module_report("trends", agent_code)

            # Top trends widget
            widgets.append(
                DashboardWidget(
                    id="trend_top",
                    title="Top Trends",
                    widget_type="table",
                    data=report.get("top_trends", [])[:5],
                    priority=80,
                    module="trends",
                )
            )

            # Trend stats
            stats = self._integration.trend_service.get_stats()
            widgets.append(
                DashboardWidget(
                    id="trend_stats",
                    title="Trend Intelligence",
                    widget_type="metric",
                    data={
                        "total_trends": stats.get("total_trends", 0),
                        "sources_active": stats.get("sources_active", 0),
                    },
                    priority=70,
                    module="trends",
                )
            )

        except Exception as e:
            logger.warning(f"Failed to get trend widgets: {e}")

        return widgets

    async def _get_commerce_widgets(
        self,
        agent_code: str,
    ) -> List[DashboardWidget]:
        """Get commerce-related widgets."""
        widgets = []

        try:
            report = self._integration.get_module_report("commerce", agent_code)

            # Storefront overview
            storefronts = self._integration.commerce_service.list_storefronts()
            widgets.append(
                DashboardWidget(
                    id="commerce_storefronts",
                    title="Storefronts",
                    widget_type="metric",
                    data={
                        "total": storefronts.get("total", 0),
                        "active": len(
                            [
                                s
                                for s in storefronts.get("storefronts", [])
                                if s.get("status") == "active"
                            ]
                        ),
                    },
                    priority=75,
                    module="commerce",
                )
            )

            # Low stock alerts
            low_stock = self._integration.commerce_service.get_low_stock_alerts(threshold=10)
            if low_stock.get("alerts") or low_stock.get("products"):
                widgets.append(
                    DashboardWidget(
                        id="commerce_low_stock",
                        title="Low Stock Alerts",
                        widget_type="alert",
                        data=low_stock,
                        priority=90,
                        module="commerce",
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to get commerce widgets: {e}")

        return widgets

    async def _get_brand_widgets(
        self,
        agent_code: str,
    ) -> List[DashboardWidget]:
        """Get brand-related widgets."""
        widgets = []

        try:
            stats = self._integration.brand_service.get_stats()

            # Brand health
            widgets.append(
                DashboardWidget(
                    id="brand_health",
                    title="Brand Health",
                    widget_type="status",
                    data={
                        "has_identity": stats.get("has_identity", False),
                        "guidelines_count": stats.get("guidelines", {}).get("total", 0),
                        "assets_count": stats.get("assets", {}).get("total", 0),
                    },
                    priority=65,
                    module="brand",
                )
            )

            # Guidelines summary
            guidelines = stats.get("guidelines", {})
            if guidelines.get("total", 0) > 0:
                widgets.append(
                    DashboardWidget(
                        id="brand_guidelines",
                        title="Brand Guidelines",
                        widget_type="metric",
                        data=guidelines,
                        priority=60,
                        module="brand",
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to get brand widgets: {e}")

        return widgets

    async def _get_scheduler_widgets(
        self,
        agent_code: str,
    ) -> List[DashboardWidget]:
        """Get scheduler-related widgets."""
        widgets = []

        try:
            stats = self._integration.scheduler_service.get_stats()

            # Scheduler status
            widgets.append(
                DashboardWidget(
                    id="scheduler_status",
                    title="Scheduler Status",
                    widget_type="status",
                    data={
                        "running": stats.get("scheduler_running", False),
                        "total_tasks": stats.get("engine", {}).get("total_tasks", 0),
                        "active_tasks": stats.get("engine", {}).get("active_tasks", 0),
                    },
                    priority=85,
                    module="scheduler",
                )
            )

            # Workflow stats
            workflow_stats = stats.get("workflows", {})
            if workflow_stats.get("registered_workflows", 0) > 0:
                widgets.append(
                    DashboardWidget(
                        id="scheduler_workflows",
                        title="Workflows",
                        widget_type="metric",
                        data=workflow_stats,
                        priority=70,
                        module="scheduler",
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to get scheduler widgets: {e}")

        return widgets

    async def _get_ceo_widgets(self) -> List[DashboardWidget]:
        """Get CEO-specific widgets."""
        widgets = []

        try:
            # System overview
            all_stats = self._integration.get_stats()
            widgets.append(
                DashboardWidget(
                    id="ceo_system_overview",
                    title="System Overview",
                    widget_type="status",
                    data={
                        "modules_active": len(
                            [
                                k
                                for k, v in all_stats.items()
                                if isinstance(v, dict) and "error" not in v
                            ]
                        ),
                        "total_modules": len(all_stats),
                    },
                    priority=100,
                    module="system",
                )
            )

            # Workflow summary
            workflow_stats = self._workflow_runner.get_stats()
            widgets.append(
                DashboardWidget(
                    id="ceo_workflows",
                    title="Autonomous Operations",
                    widget_type="metric",
                    data={
                        "available_workflows": workflow_stats.get("available_workflows", 0),
                        "total_executions": workflow_stats.get("total_executions", 0),
                        "success_rate": (
                            workflow_stats.get("successful_executions", 0)
                            / max(workflow_stats.get("total_executions", 1), 1)
                            * 100
                        ),
                    },
                    priority=95,
                    module="system",
                )
            )

        except Exception as e:
            logger.warning(f"Failed to get CEO widgets: {e}")

        return widgets

    async def _get_coo_widgets(self) -> List[DashboardWidget]:
        """Get Nexus-specific widgets."""
        widgets = []

        try:
            # All module stats
            all_stats = self._integration.get_stats()
            widgets.append(
                DashboardWidget(
                    id="coo_module_health",
                    title="Module Health",
                    widget_type="table",
                    data=[
                        {
                            "module": k,
                            "status": "healthy" if "error" not in v else "error",
                            "error": v.get("error") if isinstance(v, dict) else None,
                        }
                        for k, v in all_stats.items()
                    ],
                    priority=100,
                    module="system",
                )
            )

            # Operations queue
            scheduler_stats = self._integration.scheduler_service.get_stats()
            widgets.append(
                DashboardWidget(
                    id="coo_operations_queue",
                    title="Operations Queue",
                    widget_type="metric",
                    data={
                        "queue_size": scheduler_stats.get("engine", {}).get("queue_size", 0),
                        "pending_tasks": scheduler_stats.get("engine", {}).get("total_tasks", 0),
                    },
                    priority=95,
                    module="scheduler",
                )
            )

        except Exception as e:
            logger.warning(f"Failed to get Nexus widgets: {e}")

        return widgets

    async def _get_workflow_library_widgets(self) -> List[DashboardWidget]:
        """Get workflow library widgets for Nexus, Forge, CEO dashboards."""
        widgets = []

        try:
            from ag3ntwerk.core.plugins import get_plugin_manager

            manager = get_plugin_manager()
            plugin = manager.get_plugin("workflow-library")
            if not plugin or not plugin._pool:
                return widgets

            async with plugin._pool.acquire() as conn:
                # Overview metric
                total = await conn.fetchval("SELECT COUNT(*) FROM workflows")
                tool_types = await conn.fetchval("SELECT COUNT(DISTINCT tool_type) FROM workflows")
                categories = await conn.fetchval(
                    "SELECT COUNT(DISTINCT primary_category) FROM workflows WHERE primary_category IS NOT NULL"
                )
                embedded = await conn.fetchval(
                    "SELECT COUNT(*) FROM workflows WHERE embedded_at IS NOT NULL"
                )

                widgets.append(
                    DashboardWidget(
                        id="wf_library_overview",
                        title="Workflow Library",
                        widget_type="metric",
                        data={
                            "total_workflows": total,
                            "tool_types": tool_types,
                            "categories": categories,
                            "embedded": embedded,
                        },
                        priority=70,
                        module="workflow-library",
                    )
                )

                # Quality distribution chart
                quality_dist = await conn.fetch(
                    """SELECT
                        CASE
                            WHEN quality_score >= 80 THEN 'excellent'
                            WHEN quality_score >= 60 THEN 'good'
                            WHEN quality_score >= 40 THEN 'fair'
                            ELSE 'low'
                        END as tier,
                        COUNT(*) as count
                    FROM workflows
                    WHERE quality_score > 0
                    GROUP BY tier
                    ORDER BY count DESC"""
                )

                if quality_dist:
                    widgets.append(
                        DashboardWidget(
                            id="wf_quality_dist",
                            title="Workflow Quality Distribution",
                            widget_type="chart",
                            data=[dict(r) for r in quality_dist],
                            priority=60,
                            module="workflow-library",
                        )
                    )

                # Deployment stats (if table exists)
                has_deployments = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'workflow_deployments')"
                )
                if has_deployments:
                    deploy_stats = await conn.fetchrow(
                        """SELECT COUNT(*) as total,
                                  COALESCE(SUM(execution_count), 0) as executions,
                                  COUNT(*) FILTER (WHERE last_status = 'success') as successful
                           FROM workflow_deployments"""
                    )
                    if deploy_stats and deploy_stats["total"] > 0:
                        widgets.append(
                            DashboardWidget(
                                id="wf_deployments",
                                title="Workflow Deployments",
                                widget_type="metric",
                                data={
                                    "total_deployments": deploy_stats["total"],
                                    "total_executions": deploy_stats["executions"],
                                    "success_rate": round(
                                        deploy_stats["successful"]
                                        / max(deploy_stats["total"], 1)
                                        * 100,
                                        1,
                                    ),
                                },
                                priority=65,
                                module="workflow-library",
                            )
                        )

                # Top 5 most popular workflows
                top_workflows = await conn.fetch(
                    """SELECT workflow_name, tool_type, quality_score
                       FROM workflows
                       WHERE quality_score > 0
                       ORDER BY quality_score DESC
                       LIMIT 5"""
                )
                if top_workflows:
                    widgets.append(
                        DashboardWidget(
                            id="wf_popular",
                            title="Top Workflows",
                            widget_type="table",
                            data=[dict(r) for r in top_workflows],
                            priority=55,
                            module="workflow-library",
                        )
                    )

        except ImportError:
            logger.debug("Workflow library plugin not available for dashboard")
        except Exception as e:
            logger.warning(f"Failed to get workflow library widgets: {e}")

        return widgets

    async def _get_alerts_for_executive(
        self,
        agent_code: str,
    ) -> List[Dict[str, Any]]:
        """Get alerts for an agent."""
        alerts = []
        modules = get_modules_for_executive(agent_code)

        try:
            # Commerce alerts
            if "commerce" in modules:
                low_stock = self._integration.commerce_service.get_low_stock_alerts(threshold=5)
                if low_stock.get("alerts") or low_stock.get("products"):
                    alerts.append(
                        {
                            "type": "warning",
                            "module": "commerce",
                            "title": "Low Stock Alert",
                            "message": "Some products are running low on inventory",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

            # Brand alerts
            if "brand" in modules:
                identity = self._integration.brand_service.get_identity()
                if not identity:
                    alerts.append(
                        {
                            "type": "info",
                            "module": "brand",
                            "title": "Brand Setup Required",
                            "message": "No brand identity has been configured",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

            # Scheduler alerts
            if "scheduler" in modules:
                stats = self._integration.scheduler_service.get_stats()
                if not stats.get("scheduler_running"):
                    alerts.append(
                        {
                            "type": "info",
                            "module": "scheduler",
                            "title": "Scheduler Not Running",
                            "message": "The scheduler engine is not currently running",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

        except Exception as e:
            logger.warning(f"Failed to get alerts: {e}")

        return alerts

    def _get_quick_actions_for_executive(
        self,
        agent_code: str,
    ) -> List[Dict[str, Any]]:
        """Get quick actions for an agent."""
        actions = []
        modules = get_modules_for_executive(agent_code)

        if "trends" in modules:
            actions.append(
                {
                    "id": "run_trend_analysis",
                    "title": "Run Trend Analysis",
                    "module": "trends",
                    "action_type": "execute_module_task",
                    "params": {
                        "module_id": "trends",
                        "task_type": "run_analysis",
                    },
                }
            )

        if "commerce" in modules:
            actions.append(
                {
                    "id": "optimize_pricing",
                    "title": "Optimize Pricing",
                    "module": "commerce",
                    "action_type": "execute_module_task",
                    "params": {
                        "module_id": "commerce",
                        "task_type": "optimize_pricing",
                    },
                }
            )

        if "brand" in modules:
            actions.append(
                {
                    "id": "run_brand_audit",
                    "title": "Run Brand Audit",
                    "module": "brand",
                    "action_type": "execute_workflow",
                    "params": {
                        "workflow_name": "brand_audit",
                    },
                }
            )

        if "scheduler" in modules:
            actions.append(
                {
                    "id": "run_daily_operations",
                    "title": "Run Daily Operations",
                    "module": "scheduler",
                    "action_type": "execute_workflow",
                    "params": {
                        "workflow_name": "daily_operations",
                    },
                }
            )

        # Add agent briefing for all
        actions.append(
            {
                "id": "get_briefing",
                "title": "Get Agent Briefing",
                "module": "system",
                "action_type": "execute_workflow",
                "params": {
                    "workflow_name": "executive_briefing",
                    "context": {"agent": agent_code},
                },
            }
        )

        return actions

    async def execute_quick_action(
        self,
        action_id: str,
        agent_code: str,
    ) -> Dict[str, Any]:
        """
        Execute a quick action.

        Args:
            action_id: The action ID
            agent_code: The agent executing the action

        Returns:
            Action result
        """
        actions = self._get_quick_actions_for_executive(agent_code)
        action = next((a for a in actions if a["id"] == action_id), None)

        if not action:
            return {"error": f"Action not found: {action_id}"}

        action_type = action.get("action_type")
        params = action.get("params", {})

        try:
            if action_type == "execute_module_task":
                result = await self._integration.execute_module_task(
                    params.get("module_id", ""),
                    params.get("task_type", ""),
                    params,
                )
            elif action_type == "execute_workflow":
                result = await self._workflow_runner.execute(
                    params.get("workflow_name", ""),
                    params.get("context"),
                )
                result = result.to_dict()
            else:
                result = {"error": f"Unknown action type: {action_type}"}

            return {
                "success": True,
                "action_id": action_id,
                "result": result,
            }

        except Exception as e:
            return {
                "success": False,
                "action_id": action_id,
                "error": str(e),
            }

    def get_available_executives(self) -> List[Dict[str, Any]]:
        """Get list of available agents with their modules."""
        agents = []
        for code, info in self.AGENTS.items():
            agents.append(
                {
                    "code": code,
                    "name": info["name"],
                    "codename": info["codename"],
                    "modules": get_modules_for_executive(code),
                }
            )
        return agents
