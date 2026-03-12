"""
Autonomous Workflows - Cross-module automated operations.

Provides pre-defined workflows that coordinate multiple modules
for comprehensive autonomous operations.
"""

import asyncio
import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ag3ntwerk.modules.integration import ModuleIntegration, get_integration

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStepResult:
    """Result from a workflow step."""

    step_name: str
    module: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class AutonomousWorkflowResult:
    """Result from an autonomous workflow execution."""

    workflow_name: str
    success: bool
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    steps: List[WorkflowStepResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "success": self.success,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds() if self.completed_at else None
            ),
            "steps_count": len(self.steps),
            "successful_steps": len([s for s in self.steps if s.success]),
            "failed_steps": len([s for s in self.steps if not s.success]),
            "summary": self.summary,
            "error": self.error,
        }


class AutonomousWorkflow:
    """
    Base class for autonomous cross-module workflows.

    Workflows orchestrate multiple modules to achieve
    comprehensive business objectives.
    """

    name: str = "base_workflow"
    description: str = "Base autonomous workflow"
    owner_executive: str = "Nexus"

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or get_integration()

    async def execute(self, context: Optional[Dict[str, Any]] = None) -> AutonomousWorkflowResult:
        """Execute the workflow."""
        raise NotImplementedError("Subclasses must implement execute()")


class DailyOperationsWorkflow(AutonomousWorkflow):
    """
    Daily Operations Workflow.

    Runs daily autonomous operations including:
    1. Trend analysis scan
    2. Commerce health check
    3. Brand consistency verification
    4. Agent report generation
    """

    name = "daily_operations"
    description = "Complete daily operational analysis and reporting"
    owner_executive = "Nexus"

    async def execute(self, context: Optional[Dict[str, Any]] = None) -> AutonomousWorkflowResult:
        """Execute daily operations workflow."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )

        ctx = context or {}

        # Step 1: Run trend analysis
        step1 = await self._run_step(
            "Trend Analysis Scan",
            "trends",
            self._integration.execute_module_task,
            "trends",
            "run_analysis",
            {"sources": ctx.get("trend_sources")},
        )
        result.steps.append(step1)

        # Step 2: Commerce health check
        step2 = await self._run_step(
            "Commerce Health Check",
            "commerce",
            self._get_commerce_health,
        )
        result.steps.append(step2)

        # Step 3: Brand consistency check
        step3 = await self._run_step(
            "Brand Consistency Check",
            "brand",
            self._get_brand_health,
        )
        result.steps.append(step3)

        # Step 4: Generate agent reports
        step4 = await self._run_step(
            "Agent Report Generation",
            "scheduler",
            self._generate_all_reports,
        )
        result.steps.append(step4)

        # Compile summary
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)
        result.summary = {
            "trends": step1.output if step1.success else step1.error,
            "commerce": step2.output if step2.success else step2.error,
            "brand": step3.output if step3.success else step3.error,
            "reports": step4.output if step4.success else step4.error,
        }

        return result

    async def _run_step(
        self,
        step_name: str,
        module: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> WorkflowStepResult:
        """Run a single workflow step."""
        step_result = WorkflowStepResult(
            step_name=step_name,
            module=module,
            success=False,
            started_at=datetime.now(timezone.utc),
        )

        try:
            if inspect.iscoroutinefunction(func):
                output = await func(*args, **kwargs)
            else:
                output = func(*args, **kwargs)

            step_result.success = True
            step_result.output = output

        except Exception as e:
            step_result.error = str(e)
            logger.error(f"Step {step_name} failed: {e}")

        step_result.completed_at = datetime.now(timezone.utc)
        step_result.duration_seconds = (
            step_result.completed_at - step_result.started_at
        ).total_seconds()

        return step_result

    async def _get_commerce_health(self) -> Dict[str, Any]:
        """Get commerce health status."""
        storefronts = self._integration.commerce_service.list_storefronts()
        low_stock = self._integration.commerce_service.get_low_stock_alerts(threshold=10)

        return {
            "storefronts": storefronts,
            "low_stock_alerts": low_stock,
            "health_status": "healthy" if not low_stock.get("alerts") else "attention_needed",
        }

    async def _get_brand_health(self) -> Dict[str, Any]:
        """Get brand health status."""
        stats = self._integration.brand_service.get_stats()
        return {
            "brand_stats": stats,
            "health_status": "healthy" if stats.get("has_identity") else "needs_setup",
        }

    async def _generate_all_reports(self) -> Dict[str, Any]:
        """Generate reports for all primary agents."""
        agents = ["Nexus", "CEO", "Echo", "Keystone", "Vector"]
        reports = {}

        for agent_code in agents:
            reports[agent_code] = self._integration.get_all_reports_for_executive(agent_code)

        return {
            "generated_for": agents,
            "report_count": len(reports),
        }


class PricingOptimizationWorkflow(AutonomousWorkflow):
    """
    Pricing Optimization Workflow.

    Optimizes pricing across storefronts based on:
    1. Current margin analysis
    2. Trend-informed demand signals
    3. Competitive positioning
    4. Revenue impact projection
    """

    name = "pricing_optimization"
    description = "Analyze and optimize product pricing across storefronts"
    owner_executive = "Vector"

    async def execute(self, context: Optional[Dict[str, Any]] = None) -> AutonomousWorkflowResult:
        """Execute pricing optimization workflow."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )

        ctx = context or {}
        target_margin = ctx.get("target_margin", 40.0)
        strategy = ctx.get("strategy", "cost_plus")

        # Step 1: Get current margin analysis
        step1 = await self._run_step(
            "Margin Analysis",
            "commerce",
            lambda: self._integration.commerce_service.get_margin_analysis(),
        )
        result.steps.append(step1)

        # Step 2: Get trend signals for demand
        step2 = await self._run_step(
            "Trend Demand Signals",
            "trends",
            lambda: self._integration.trend_service.get_trending(
                category="commerce",
                limit=10,
            ),
        )
        result.steps.append(step2)

        # Step 3: Get storefronts and optimize each
        storefronts = self._integration.commerce_service.list_storefronts()
        optimization_results = []

        for sf in storefronts.get("storefronts", []):
            sf_id = sf.get("id", "")
            if sf_id:
                opt_result = self._integration.commerce_service.optimize_pricing(
                    storefront_id=sf_id,
                    target_margin=target_margin,
                    strategy=strategy,
                )
                optimization_results.append(
                    {
                        "storefront": sf_id,
                        "recommendations": opt_result,
                    }
                )

        step3 = WorkflowStepResult(
            step_name="Pricing Recommendations",
            module="commerce",
            success=True,
            output=optimization_results,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        result.steps.append(step3)

        # Compile summary
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)
        result.summary = {
            "storefronts_analyzed": len(optimization_results),
            "target_margin": target_margin,
            "strategy": strategy,
            "margin_analysis": step1.output if step1.success else None,
            "trend_signals": step2.output if step2.success else None,
            "recommendations": optimization_results,
        }

        return result

    async def _run_step(
        self,
        step_name: str,
        module: str,
        func: Callable,
    ) -> WorkflowStepResult:
        """Run a single workflow step."""
        step_result = WorkflowStepResult(
            step_name=step_name,
            module=module,
            success=False,
            started_at=datetime.now(timezone.utc),
        )

        try:
            if inspect.iscoroutinefunction(func):
                output = await func()
            else:
                output = func()

            step_result.success = True
            step_result.output = output

        except Exception as e:
            step_result.error = str(e)
            logger.error(f"Step {step_name} failed: {e}")

        step_result.completed_at = datetime.now(timezone.utc)
        step_result.duration_seconds = (
            step_result.completed_at - step_result.started_at
        ).total_seconds()

        return step_result


class MarketIntelligenceWorkflow(AutonomousWorkflow):
    """
    Market Intelligence Workflow.

    Gathers comprehensive market intelligence:
    1. Trend analysis across sources
    2. Niche opportunity identification
    3. Competitor trend analysis
    4. Strategic recommendations
    """

    name = "market_intelligence"
    description = "Comprehensive market intelligence gathering and analysis"
    owner_executive = "Echo"

    async def execute(self, context: Optional[Dict[str, Any]] = None) -> AutonomousWorkflowResult:
        """Execute market intelligence workflow."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )

        ctx = context or {}

        # Step 1: Run comprehensive trend analysis
        step1_result = await self._integration.execute_module_task(
            "trends",
            "run_analysis",
            {"sources": ["google", "reddit", "hackernews", "producthunt"]},
        )
        step1 = WorkflowStepResult(
            step_name="Comprehensive Trend Scan",
            module="trends",
            success="error" not in step1_result,
            output=step1_result,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        result.steps.append(step1)

        # Step 2: Identify niche opportunities
        step2_result = await self._integration.execute_module_task(
            "trends",
            "identify_niches",
            {"min_opportunity_score": ctx.get("min_opportunity_score", 50)},
        )
        step2 = WorkflowStepResult(
            step_name="Niche Opportunity Analysis",
            module="trends",
            success="error" not in step2_result,
            output=step2_result,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        result.steps.append(step2)

        # Step 3: Get trend correlations
        step3_result = await self._integration.execute_module_task(
            "trends",
            "get_correlations",
            {},
        )
        step3 = WorkflowStepResult(
            step_name="Trend Correlation Analysis",
            module="trends",
            success="error" not in step3_result,
            output=step3_result,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        result.steps.append(step3)

        # Step 4: Generate Echo-focused report
        cmo_report = self._integration.get_module_report("trends", "Echo")
        step4 = WorkflowStepResult(
            step_name="Echo Intelligence Report",
            module="trends",
            success=True,
            output=cmo_report,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        result.steps.append(step4)

        # Compile summary
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)
        result.summary = {
            "trend_scan": step1.output if step1.success else step1.error,
            "niche_opportunities": step2.output if step2.success else step2.error,
            "correlations": step3.output if step3.success else step3.error,
            "executive_report": step4.output if step4.success else step4.error,
        }

        return result


class BrandAuditWorkflow(AutonomousWorkflow):
    """
    Brand Audit Workflow.

    Comprehensive brand consistency audit:
    1. Get brand identity status
    2. Review guidelines compliance
    3. Check content consistency
    4. Generate audit report
    """

    name = "brand_audit"
    description = "Comprehensive brand consistency audit"
    owner_executive = "Echo"

    async def execute(self, context: Optional[Dict[str, Any]] = None) -> AutonomousWorkflowResult:
        """Execute brand audit workflow."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )

        ctx = context or {}

        # Step 1: Get brand identity
        identity = self._integration.brand_service.get_identity()
        step1 = WorkflowStepResult(
            step_name="Brand Identity Review",
            module="brand",
            success=identity is not None,
            output=identity,
            error="No brand identity configured" if not identity else None,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        result.steps.append(step1)

        # Step 2: Get guidelines
        guidelines = self._integration.brand_service.get_guidelines()
        step2 = WorkflowStepResult(
            step_name="Guidelines Review",
            module="brand",
            success=True,
            output={
                "guideline_count": len(guidelines),
                "guidelines": guidelines,
            },
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        result.steps.append(step2)

        # Step 3: Content validation (if samples provided)
        samples = ctx.get("content_samples", [])
        if samples:
            consistency_result = self._integration.brand_service.check_consistency(samples)
            step3 = WorkflowStepResult(
                step_name="Content Consistency Check",
                module="brand",
                success=True,
                output=consistency_result,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
        else:
            step3 = WorkflowStepResult(
                step_name="Content Consistency Check",
                module="brand",
                success=True,
                output={"note": "No content samples provided for consistency check"},
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
        result.steps.append(step3)

        # Step 4: Get brand kit
        brand_kit = self._integration.brand_service.get_brand_kit()
        step4 = WorkflowStepResult(
            step_name="Brand Kit Generation",
            module="brand",
            success="error" not in brand_kit,
            output=brand_kit,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        result.steps.append(step4)

        # Compile summary
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)
        result.summary = {
            "has_identity": identity is not None,
            "guideline_count": len(guidelines),
            "samples_checked": len(samples),
            "audit_complete": result.success,
        }

        return result


class ExecutiveBriefingWorkflow(AutonomousWorkflow):
    """
    Agent Briefing Workflow.

    Generates comprehensive briefings for agents:
    1. Gather all module reports
    2. Synthesize key insights
    3. Generate action items
    4. Compile agent summary
    """

    name = "executive_briefing"
    description = "Generate comprehensive agent briefings from all modules"
    owner_executive = "CEO"

    async def execute(self, context: Optional[Dict[str, Any]] = None) -> AutonomousWorkflowResult:
        """Execute agent briefing workflow."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )

        ctx = context or {}
        target_agent = ctx.get("agent", "CEO")

        # Step 1: Get all module reports for the agent
        all_reports = self._integration.get_all_reports_for_executive(target_agent)
        step1 = WorkflowStepResult(
            step_name="Module Report Collection",
            module="integration",
            success=True,
            output=all_reports,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        result.steps.append(step1)

        # Step 2: Get module stats
        stats = self._integration.get_stats()
        step2 = WorkflowStepResult(
            step_name="System Stats Collection",
            module="integration",
            success=True,
            output=stats,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        result.steps.append(step2)

        # Step 3: Get scheduler status
        scheduler_report = self._integration.get_module_report("scheduler", target_agent)
        step3 = WorkflowStepResult(
            step_name="Operations Status",
            module="scheduler",
            success="error" not in scheduler_report,
            output=scheduler_report,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        result.steps.append(step3)

        # Compile agent briefing
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)
        result.summary = {
            "agent": target_agent,
            "briefing_date": datetime.now(timezone.utc).isoformat(),
            "modules_reported": list(all_reports.keys()),
            "system_health": self._assess_health(stats),
            "action_items": self._generate_action_items(all_reports),
        }

        return result

    def _assess_health(self, stats: Dict[str, Any]) -> str:
        """Assess overall system health."""
        errors = sum(
            1
            for module_stats in stats.values()
            if isinstance(module_stats, dict) and "error" in module_stats
        )

        if errors == 0:
            return "healthy"
        elif errors < len(stats) / 2:
            return "degraded"
        else:
            return "critical"

    def _generate_action_items(self, reports: Dict[str, Any]) -> List[str]:
        """Generate action items from reports."""
        action_items = []

        # Check trends for opportunities
        if "trends" in reports:
            trend_report = reports["trends"]
            if isinstance(trend_report, dict):
                opportunities = trend_report.get("top_opportunities", [])
                if opportunities:
                    action_items.append(f"Review {len(opportunities)} new trend opportunities")

        # Check commerce for low stock
        if "commerce" in reports:
            commerce_report = reports["commerce"]
            if isinstance(commerce_report, dict):
                low_stock = commerce_report.get("low_stock_count", 0)
                if low_stock > 0:
                    action_items.append(f"Address {low_stock} low stock products")

        # Check brand for issues
        if "brand" in reports:
            brand_report = reports["brand"]
            if isinstance(brand_report, dict) and not brand_report.get("has_identity"):
                action_items.append("Set up brand identity")

        if not action_items:
            action_items.append("No urgent action items")

        return action_items


# Workflow registry
AUTONOMOUS_WORKFLOWS = {
    "daily_operations": DailyOperationsWorkflow,
    "pricing_optimization": PricingOptimizationWorkflow,
    "market_intelligence": MarketIntelligenceWorkflow,
    "brand_audit": BrandAuditWorkflow,
    "executive_briefing": ExecutiveBriefingWorkflow,
}


class AutonomousWorkflowRunner:
    """
    Runner for autonomous workflows.

    Provides a unified interface to execute any registered
    autonomous workflow.
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        self._integration = integration or get_integration()
        self._executions: List[AutonomousWorkflowResult] = []

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List available workflows."""
        return [
            {
                "name": name,
                "description": cls.description,
                "owner_executive": cls.owner_executive,
            }
            for name, cls in AUTONOMOUS_WORKFLOWS.items()
        ]

    async def execute(
        self,
        workflow_name: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """
        Execute a workflow by name.

        Args:
            workflow_name: Name of the workflow to execute
            context: Optional context parameters

        Returns:
            Workflow execution result
        """
        if workflow_name not in AUTONOMOUS_WORKFLOWS:
            return AutonomousWorkflowResult(
                workflow_name=workflow_name,
                success=False,
                error=f"Unknown workflow: {workflow_name}",
                completed_at=datetime.now(timezone.utc),
            )

        workflow_class = AUTONOMOUS_WORKFLOWS[workflow_name]
        workflow = workflow_class(self._integration)

        try:
            result = await workflow.execute(context)
            self._executions.append(result)
            return result

        except Exception as e:
            result = AutonomousWorkflowResult(
                workflow_name=workflow_name,
                success=False,
                error=str(e),
                completed_at=datetime.now(timezone.utc),
            )
            self._executions.append(result)
            return result

    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        return [
            ex.to_dict()
            for ex in sorted(
                self._executions,
                key=lambda x: x.started_at,
                reverse=True,
            )[:limit]
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get workflow runner statistics."""
        return {
            "available_workflows": len(AUTONOMOUS_WORKFLOWS),
            "total_executions": len(self._executions),
            "successful_executions": len([e for e in self._executions if e.success]),
            "failed_executions": len([e for e in self._executions if not e.success]),
        }
