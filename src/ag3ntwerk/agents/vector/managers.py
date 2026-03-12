"""
Vector (Vector) Manager Classes.

Middle-management layer for revenue operations.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Manager,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class RevenueManager(Manager):
    """
    Manages revenue tracking and forecasting.

    Handles MRR, ARR, and revenue analytics.
    Reports to Vector (Vector).

    When a GumroadClient is provided, revenue_tracking tasks
    will query live Gumroad sales data and feed it into the
    LLM-based analysis.
    """

    HANDLED_TASK_TYPES = [
        "revenue_tracking",
        "revenue_forecasting",
        "mrr_analysis",
        "arr_calculation",
        "revenue_attribution",
        "revenue_summary",
    ]

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        gumroad_client=None,
    ):
        super().__init__(
            code="RevenueMgr",
            name="Revenue Manager",
            domain="Revenue Tracking",
            llm_provider=llm_provider,
        )
        self._revenue_records: Dict[str, Any] = {}
        self._gumroad = gumroad_client

    @property
    def gumroad_client(self):
        """Access the Gumroad client."""
        return self._gumroad

    @gumroad_client.setter
    def gumroad_client(self, value):
        """Set the Gumroad client."""
        self._gumroad = value

    def can_handle(self, task: Task) -> bool:
        """Check if this manager handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute revenue management task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "revenue_tracking": self._handle_tracking,
            "revenue_forecasting": self._handle_forecasting,
            "mrr_analysis": self._handle_mrr,
            "revenue_summary": self._handle_revenue_summary,
        }

        handler = handlers.get(task.task_type)
        if handler:
            return await handler(task)

        return await self._execute_with_llm(task)

    async def _handle_tracking(self, task: Task) -> TaskResult:
        """Track revenue metrics, injecting live Gumroad data when available."""
        revenue_data = task.context.get("revenue_data", {})
        period = task.context.get("period", "monthly")
        period_days = task.context.get("period_days", 30)

        # Inject live Gumroad data if client is configured
        live_data = {}
        if self._gumroad:
            try:
                live_data = await self._gumroad.get_revenue_summary(period_days=period_days)
                logger.info("Fetched live Gumroad revenue data")
            except Exception as e:
                logger.warning("Failed to fetch Gumroad data: %s", e)

        combined_data = {**revenue_data, "gumroad_live": live_data} if live_data else revenue_data

        prompt = f"""As the Revenue Manager, track revenue.

Revenue Data: {combined_data}
Period: {period}
Context: {task.description}

Provide:
1. Revenue summary (total, MRR, ARR)
2. Period-over-period comparison
3. Revenue breakdown by source
4. Key trends
5. Variance analysis"""

        response = await self.reason(prompt, task.context)

        output = {
            "tracking_type": "revenue_tracking",
            "period": period,
            "analysis": response,
        }
        if live_data:
            output["live_data"] = live_data

        return TaskResult(
            task_id=task.id,
            success=True,
            output=output,
        )

    async def _handle_forecasting(self, task: Task) -> TaskResult:
        """Forecast revenue."""
        historical = task.context.get("historical_data", {})
        horizon = task.context.get("forecast_horizon", "quarter")

        prompt = f"""As the Revenue Manager, create forecast.

Historical Data: {historical}
Forecast Horizon: {horizon}
Context: {task.description}

Provide:
1. Base case forecast
2. Best/worst case scenarios
3. Assumptions
4. Risk factors
5. Confidence level"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "forecast_type": "revenue_forecasting",
                "horizon": horizon,
                "forecast": response,
            },
        )

    async def _handle_mrr(self, task: Task) -> TaskResult:
        """Analyze MRR movements."""
        mrr_data = task.context.get("mrr_data", {})

        prompt = f"""As the Revenue Manager, analyze MRR.

MRR Data: {mrr_data}
Context: {task.description}

Provide:
1. MRR summary
2. Movement analysis (new, expansion, contraction, churn)
3. Quick ratio
4. Growth trajectory
5. Recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "mrr_analysis",
                "analysis": response,
            },
        )

    async def _handle_revenue_summary(self, task: Task) -> TaskResult:
        """Get revenue summary directly from Gumroad (no LLM needed)."""
        if not self._gumroad:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="GumroadClient not configured",
            )

        period_days = task.context.get("period_days", 30)

        try:
            summary = await self._gumroad.get_revenue_summary(period_days=period_days)
            return TaskResult(
                task_id=task.id,
                success=True,
                output={
                    "summary_type": "revenue_summary",
                    "period_days": period_days,
                    "summary": summary,
                },
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Revenue summary failed: {e}",
            )

    async def _execute_with_llm(self, task: Task) -> TaskResult:
        """Execute task using LLM."""
        prompt = f"""As the Revenue Manager, handle this task:

Task: {task.description}
Type: {task.task_type}
Context: {task.context}

Provide revenue-focused analysis."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )


class MetricsManager(Manager):
    """
    Manages business metrics and KPIs.

    Handles dashboards, reporting, and metric tracking.
    Reports to Vector (Vector).
    """

    HANDLED_TASK_TYPES = [
        "kpi_tracking",
        "dashboard_update",
        "metric_definition",
        "performance_reporting",
        "benchmark_analysis",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="MetricsMgr",
            name="Metrics Manager",
            domain="Business Metrics",
            llm_provider=llm_provider,
        )
        self._metrics: Dict[str, Any] = {}

    def can_handle(self, task: Task) -> bool:
        """Check if this manager handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute metrics management task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "kpi_tracking": self._handle_kpi_tracking,
            "benchmark_analysis": self._handle_benchmark,
        }

        handler = handlers.get(task.task_type)
        if handler:
            return await handler(task)

        return await self._execute_with_llm(task)

    async def _handle_kpi_tracking(self, task: Task) -> TaskResult:
        """Track KPIs."""
        kpis = task.context.get("kpis", [])
        period = task.context.get("period", "weekly")

        prompt = f"""As the Metrics Manager, track KPIs.

KPIs: {kpis}
Period: {period}
Context: {task.description}

Provide:
1. KPI dashboard summary
2. Performance vs targets
3. Trend analysis
4. Areas of concern
5. Recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "tracking_type": "kpi_tracking",
                "period": period,
                "dashboard": response,
            },
        )

    async def _handle_benchmark(self, task: Task) -> TaskResult:
        """Benchmark against industry."""
        metrics = task.context.get("metrics", {})
        industry = task.context.get("industry", "SaaS")

        prompt = f"""As the Metrics Manager, perform benchmark analysis.

Our Metrics: {metrics}
Industry: {industry}
Context: {task.description}

Provide:
1. Benchmark comparison
2. Where we excel
3. Where we lag
4. Industry best practices
5. Improvement priorities"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "benchmark_analysis",
                "industry": industry,
                "analysis": response,
            },
        )

    async def _execute_with_llm(self, task: Task) -> TaskResult:
        """Execute task using LLM."""
        prompt = f"""As the Metrics Manager, handle this task:

Task: {task.description}
Type: {task.task_type}
Context: {task.context}

Provide metrics-focused analysis."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )


class GrowthManager(Manager):
    """
    Manages growth initiatives and experiments.

    Handles growth strategy, experiments, and optimization.
    Reports to Vector (Vector).
    """

    HANDLED_TASK_TYPES = [
        "growth_experiment_design",
        "growth_analysis",
        "conversion_optimization",
        "expansion_strategy",
        "acquisition_analysis",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="GrowthMgr",
            name="Growth Manager",
            domain="Growth Strategy",
            llm_provider=llm_provider,
        )
        self._experiments: Dict[str, Any] = {}

    def can_handle(self, task: Task) -> bool:
        """Check if this manager handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute growth management task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "growth_experiment_design": self._handle_experiment_design,
            "growth_analysis": self._handle_growth_analysis,
            "conversion_optimization": self._handle_conversion,
        }

        handler = handlers.get(task.task_type)
        if handler:
            return await handler(task)

        return await self._execute_with_llm(task)

    async def _handle_experiment_design(self, task: Task) -> TaskResult:
        """Design growth experiment."""
        hypothesis = task.context.get("hypothesis", "")
        target_metric = task.context.get("target_metric", "")

        prompt = f"""As the Growth Manager, design an experiment.

Hypothesis: {hypothesis}
Target Metric: {target_metric}
Context: {task.description}

Provide experiment design:
1. Experiment setup
2. Control vs treatment
3. Sample size
4. Duration
5. Success criteria
6. Analysis plan"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "design_type": "growth_experiment_design",
                "hypothesis": hypothesis,
                "design": response,
            },
        )

    async def _handle_growth_analysis(self, task: Task) -> TaskResult:
        """Analyze growth metrics."""
        growth_data = task.context.get("growth_data", {})

        prompt = f"""As the Growth Manager, analyze growth.

Growth Data: {growth_data}
Context: {task.description}

Provide:
1. Growth rate analysis
2. Growth drivers
3. Growth headwinds
4. Opportunity areas
5. Strategic recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "growth_analysis",
                "analysis": response,
            },
        )

    async def _handle_conversion(self, task: Task) -> TaskResult:
        """Optimize conversion."""
        funnel_data = task.context.get("funnel_data", {})
        target_stage = task.context.get("target_stage", "")

        prompt = f"""As the Growth Manager, optimize conversion.

Funnel Data: {funnel_data}
Target Stage: {target_stage}
Context: {task.description}

Provide:
1. Current conversion rates
2. Bottleneck identification
3. Optimization opportunities
4. Recommended tests
5. Expected impact"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "optimization_type": "conversion_optimization",
                "target_stage": target_stage,
                "recommendations": response,
            },
        )

    async def _execute_with_llm(self, task: Task) -> TaskResult:
        """Execute task using LLM."""
        prompt = f"""As the Growth Manager, handle this task:

Task: {task.description}
Type: {task.task_type}
Context: {task.context}

Provide growth-focused analysis."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )
