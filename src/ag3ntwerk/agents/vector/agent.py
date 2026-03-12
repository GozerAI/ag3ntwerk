"""
Vector (Vector) Agent - Vector.

Codename: Vector
Core function: Revenue operations, growth metrics, and business performance.

The Vector handles all revenue-related tasks:
- Revenue tracking and forecasting
- Growth metrics and KPIs
- Churn and retention analysis
- Feature adoption metrics
- Conversion funnel analysis

Sphere of influence: Revenue growth, pricing strategy, market expansion,
sales enablement, revenue forecasting, unit economics.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Manager,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider
from ag3ntwerk.agents.vector.managers import (
    RevenueManager,
    MetricsManager,
    GrowthManager,
)
from ag3ntwerk.agents.vector.specialists import (
    RevenueAnalyst,
    ChurnAnalyst,
    AdoptionTracker,
    ConversionAnalyst,
    GrowthExperimenter,
    CohortAnalyst,
)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


# Revenue management task types
REVENUE_CAPABILITIES = [
    "revenue_tracking",
    "churn_analysis",
    "feature_adoption_metrics",
    "conversion_analysis",
    "growth_experiment_design",
    "revenue_forecasting",
    "pricing_analysis",
    "unit_economics",
    "cohort_analysis",
    "ltv_calculation",
    "mrr_analysis",
    "expansion_revenue",
    "revenue_summary",
]


class Vector(Manager):
    """
    Vector - Vector.

    The Vector is responsible for revenue operations and growth
    within the ag3ntwerk system. It tracks revenue metrics,
    analyzes growth patterns, and optimizes monetization.

    Codename: Vector

    Core Responsibilities:
    - Revenue tracking and forecasting
    - Growth metrics and KPI monitoring
    - Churn and retention analysis
    - Feature adoption tracking
    - Conversion funnel optimization

    Example:
        ```python
        crevo = Vector(llm_provider=llm)

        task = Task(
            description="Analyze Q4 revenue performance",
            task_type="revenue_tracking",
            context={"revenue_data": data, "quarter": "Q4 2025"},
        )
        result = await crevo.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__(
            code="Vector",
            name="Vector",
            domain="Revenue Operations, Growth, Metrics",
            llm_provider=llm_provider,
        )
        self.codename = "Vector"

        self.capabilities = REVENUE_CAPABILITIES

        # Revenue-specific state
        self._revenue_data: Dict[str, Any] = {}
        self._forecasts: Dict[str, Any] = {}
        self._metrics: Dict[str, float] = {}
        self._cohorts: Dict[str, Any] = {}

        # Initialize and register managers with their specialists
        self._init_managers()

    def _init_managers(self, gumroad_client=None) -> None:
        """Initialize and register managers with their specialists."""
        # Create managers
        rev_mgr = RevenueManager(
            llm_provider=self.llm_provider,
            gumroad_client=gumroad_client,
        )
        metrics_mgr = MetricsManager(llm_provider=self.llm_provider)
        growth_mgr = GrowthManager(llm_provider=self.llm_provider)

        # Create specialists
        revenue_analyst = RevenueAnalyst(llm_provider=self.llm_provider)
        churn_analyst = ChurnAnalyst(llm_provider=self.llm_provider)
        adoption_tracker = AdoptionTracker(llm_provider=self.llm_provider)
        conversion_analyst = ConversionAnalyst(llm_provider=self.llm_provider)
        growth_experimenter = GrowthExperimenter(llm_provider=self.llm_provider)
        cohort_analyst = CohortAnalyst(llm_provider=self.llm_provider)

        # Register specialists with appropriate managers
        rev_mgr.register_subordinate(revenue_analyst)
        rev_mgr.register_subordinate(churn_analyst)
        rev_mgr.register_subordinate(cohort_analyst)
        metrics_mgr.register_subordinate(adoption_tracker)
        growth_mgr.register_subordinate(conversion_analyst)
        growth_mgr.register_subordinate(growth_experimenter)

        # Register managers with Vector
        self.register_subordinate(rev_mgr)
        self.register_subordinate(metrics_mgr)
        self.register_subordinate(growth_mgr)

        # Keep reference for external configuration
        self._revenue_mgr = rev_mgr

    def can_handle(self, task: Task) -> bool:
        """Check if this is a revenue-related task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute a revenue management task."""
        task.status = TaskStatus.IN_PROGRESS

        # Route to appropriate handler
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        # Fallback to LLM-based handling
        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            "revenue_tracking": self._handle_revenue_tracking,
            "churn_analysis": self._handle_churn_analysis,
            "feature_adoption_metrics": self._handle_feature_adoption,
            "conversion_analysis": self._handle_conversion_analysis,
            "growth_experiment_design": self._handle_growth_experiment,
            "revenue_forecasting": self._handle_revenue_forecasting,
            "cohort_analysis": self._handle_cohort_analysis,
            "mrr_analysis": self._handle_mrr_analysis,
            # VLS handlers
            "vls_buyer_acquisition": self._handle_vls_buyer_acquisition,
            "vls_billing_revenue": self._handle_vls_billing_revenue,
        }
        return handlers.get(task_type)

    async def _handle_revenue_tracking(self, task: Task) -> TaskResult:
        """Track revenue metrics and performance."""
        revenue_data = task.context.get("revenue_data", {})
        period = task.context.get("period", "monthly")
        product_id = task.context.get("product_id", "")

        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider for revenue analysis",
            )

        prompt = f"""As the Vector (Vector), analyze revenue performance.

Revenue Data:
{revenue_data}

Period: {period}
Product: {product_id}
Context: {task.description}

Provide comprehensive revenue analysis:

1. REVENUE SUMMARY
   - Total Revenue: $X
   - MRR: $X
   - ARR: $X
   - Growth Rate: X%

2. REVENUE BREAKDOWN
   - By product/tier
   - By customer segment
   - New vs expansion vs contraction

3. PERFORMANCE VS TARGETS
   - Target: $X
   - Actual: $X
   - Variance: X%
   - Trend analysis

4. KEY METRICS
   - ARPU: $X
   - LTV: $X
   - CAC Payback: X months
   - Net Revenue Retention: X%

5. REVENUE DRIVERS
   - Top performing segments
   - Growth drivers
   - Headwinds

6. RECOMMENDATIONS
   - Revenue optimization opportunities
   - Risk mitigation
   - Investment priorities

7. FORECAST IMPLICATIONS
   - Impact on quarterly forecast
   - Year-end projection"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Revenue tracking failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "tracking_type": "revenue_tracking",
                "period": period,
                "product_id": product_id,
                "analysis": response,
                "tracked_at": _utcnow().isoformat(),
            },
            metrics={"task_type": "revenue_tracking"},
        )

    async def _handle_churn_analysis(self, task: Task) -> TaskResult:
        """Analyze customer and revenue churn."""
        churn_data = task.context.get("churn_data", {})
        period = task.context.get("period", "quarterly")

        prompt = f"""As the Vector (Vector), analyze churn.

Churn Data:
{churn_data}

Period: {period}
Context: {task.description}

Provide churn analysis:

1. CHURN METRICS
   - Customer Churn Rate: X%
   - Revenue Churn Rate: X%
   - Net Revenue Retention: X%
   - Gross Revenue Retention: X%

2. CHURN BREAKDOWN
   - By customer segment
   - By tenure
   - By product tier
   - By reason

3. COHORT ANALYSIS
   - Churn by acquisition cohort
   - Retention curves
   - Best/worst performing cohorts

4. REVENUE IMPACT
   - Lost MRR: $X
   - Recoverable revenue
   - Lifetime value lost

5. CHURN DRIVERS
   - Primary reasons
   - Leading indicators
   - Correlation analysis

6. PREVENTION STRATEGIES
   - High-risk accounts to save
   - Intervention playbooks
   - Early warning triggers

7. BENCHMARK COMPARISON
   - vs industry benchmarks
   - vs historical performance
   - vs targets"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Churn analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "churn_analysis",
                "period": period,
                "analysis": response,
            },
        )

    async def _handle_feature_adoption(self, task: Task) -> TaskResult:
        """Analyze feature adoption metrics."""
        adoption_data = task.context.get("adoption_data", {})
        features = task.context.get("features", [])
        product_id = task.context.get("product_id", "")

        prompt = f"""As the Vector (Vector), analyze feature adoption.

Adoption Data:
{adoption_data}

Features: {features}
Product: {product_id}
Context: {task.description}

Provide adoption analysis:

1. ADOPTION OVERVIEW
   - Total features tracked
   - Average adoption rate
   - Adoption trend

2. FEATURE RANKINGS
   - Most adopted features
   - Least adopted features
   - Fastest growing features

3. ADOPTION BY SEGMENT
   - By customer tier
   - By use case
   - By tenure

4. REVENUE CORRELATION
   - Features correlated with retention
   - Features correlated with expansion
   - Features correlated with churn

5. TIME-TO-ADOPTION
   - Average time to first use
   - Adoption velocity by feature
   - Onboarding impact

6. ENGAGEMENT DEPTH
   - Power users vs casual users
   - Feature stickiness
   - Usage frequency

7. RECOMMENDATIONS
   - Features to promote
   - Features to improve
   - Features to sunset
   - Product feedback for Blueprint (Blueprint)"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Feature adoption analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "metrics_type": "feature_adoption_metrics",
                "product_id": product_id,
                "analysis": response,
            },
        )

    async def _handle_conversion_analysis(self, task: Task) -> TaskResult:
        """Analyze conversion funnel."""
        funnel_data = task.context.get("funnel_data", {})
        funnel_type = task.context.get("funnel_type", "signup_to_paid")

        prompt = f"""As the Vector (Vector), analyze conversion funnel.

Funnel Data:
{funnel_data}

Funnel Type: {funnel_type}
Context: {task.description}

Provide conversion analysis:

1. FUNNEL OVERVIEW
   - Total funnel volume
   - Overall conversion rate
   - Trend vs previous period

2. STAGE-BY-STAGE ANALYSIS
   For each stage:
   - Volume entering
   - Conversion rate
   - Drop-off rate
   - Bottleneck assessment

3. CONVERSION DRIVERS
   - What drives conversion
   - What causes drop-off
   - Correlation with behavior

4. SEGMENT PERFORMANCE
   - Best converting segments
   - Worst converting segments
   - Opportunity segments

5. TIME ANALYSIS
   - Time in each stage
   - Conversion velocity
   - Optimal timing

6. A/B TEST INSIGHTS
   - Active experiments
   - Results and learnings
   - Recommended changes

7. OPTIMIZATION RECOMMENDATIONS
   - Quick wins
   - High-impact changes
   - Long-term improvements

8. REVENUE IMPACT
   - Revenue per conversion
   - Opportunity cost of drop-offs
   - Expected lift from improvements"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Conversion analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "conversion_analysis",
                "funnel_type": funnel_type,
                "analysis": response,
            },
        )

    async def _handle_growth_experiment(self, task: Task) -> TaskResult:
        """Design growth experiments."""
        hypothesis = task.context.get("hypothesis", "")
        metrics = task.context.get("target_metrics", [])
        constraints = task.context.get("constraints", {})

        prompt = f"""As the Vector (Vector), design a growth experiment.

Hypothesis: {hypothesis}
Target Metrics: {metrics}
Constraints: {constraints}
Context: {task.description}

Design experiment:

1. EXPERIMENT OVERVIEW
   - Name
   - Hypothesis statement
   - Expected impact

2. EXPERIMENT DESIGN
   - Control group
   - Treatment group(s)
   - Sample size calculation
   - Duration

3. SUCCESS METRICS
   - Primary metric
   - Secondary metrics
   - Guardrail metrics

4. IMPLEMENTATION
   - Technical requirements
   - Rollout plan
   - Risk mitigation

5. ANALYSIS PLAN
   - Statistical methodology
   - Segmentation
   - Sensitivity analysis

6. DECISION FRAMEWORK
   - Success criteria
   - Failure criteria
   - Edge cases

7. TIMELINE
   - Setup phase
   - Running phase
   - Analysis phase
   - Decision date

8. STAKEHOLDERS
   - DRI (Directly Responsible Individual)
   - Approvers
   - Informed parties"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Growth experiment design failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "experiment_type": "growth_experiment_design",
                "hypothesis": hypothesis,
                "design": response,
            },
        )

    async def _handle_revenue_forecasting(self, task: Task) -> TaskResult:
        """Forecast revenue."""
        historical_data = task.context.get("historical_data", {})
        forecast_period = task.context.get("forecast_period", "quarter")
        assumptions = task.context.get("assumptions", {})

        prompt = f"""As the Vector (Vector), create revenue forecast.

Historical Data:
{historical_data}

Forecast Period: {forecast_period}
Assumptions: {assumptions}
Context: {task.description}

Provide revenue forecast:

1. FORECAST SUMMARY
   - Forecast period: {forecast_period}
   - Base case: $X
   - Best case: $X
   - Worst case: $X

2. METHODOLOGY
   - Model used
   - Key assumptions
   - Confidence level

3. REVENUE COMPONENTS
   - New business: $X
   - Expansion: $X
   - Contraction: $X
   - Churn: $X
   - Net new: $X

4. GROWTH DRIVERS
   - Volume growth
   - Price growth
   - Mix shift

5. RISK FACTORS
   - Upside risks
   - Downside risks
   - Sensitivity analysis

6. MONTHLY BREAKDOWN
   Month-by-month projection with:
   - MRR
   - Growth rate
   - Cumulative

7. COMPARISON TO TARGETS
   - vs plan
   - vs previous period
   - Gap analysis

8. RECOMMENDATIONS
   - To hit target
   - Contingency plans"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Revenue forecasting failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "forecast_type": "revenue_forecasting",
                "period": forecast_period,
                "forecast": response,
                "created_at": _utcnow().isoformat(),
            },
        )

    async def _handle_cohort_analysis(self, task: Task) -> TaskResult:
        """Perform cohort analysis."""
        cohort_data = task.context.get("cohort_data", {})
        cohort_type = task.context.get("cohort_type", "acquisition")

        prompt = f"""As the Vector (Vector), perform cohort analysis.

Cohort Data:
{cohort_data}

Cohort Type: {cohort_type}
Context: {task.description}

Provide cohort analysis:

1. COHORT OVERVIEW
   - Cohort definition: {cohort_type}
   - Number of cohorts
   - Total customers analyzed

2. RETENTION MATRIX
   - Month-over-month retention by cohort
   - Retention curve shape
   - Stabilization point

3. REVENUE BY COHORT
   - Initial ARPU by cohort
   - ARPU evolution
   - Expansion patterns

4. BEST/WORST COHORTS
   - Top performing cohorts
   - Underperforming cohorts
   - Common characteristics

5. TREND ANALYSIS
   - Are newer cohorts better/worse?
   - Seasonal patterns
   - Product/pricing impact

6. LTV CALCULATION
   - By cohort
   - Payback period
   - Long-term value

7. ACTIONABLE INSIGHTS
   - Acquisition channel implications
   - Product improvements
   - Pricing considerations"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Cohort analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "cohort_analysis",
                "cohort_type": cohort_type,
                "analysis": response,
            },
        )

    async def _handle_mrr_analysis(self, task: Task) -> TaskResult:
        """Analyze Monthly Recurring Revenue."""
        mrr_data = task.context.get("mrr_data", {})
        period = task.context.get("period", "monthly")

        prompt = f"""As the Vector (Vector), analyze MRR.

MRR Data:
{mrr_data}

Period: {period}
Context: {task.description}

Provide MRR analysis:

1. MRR SUMMARY
   - Current MRR: $X
   - Previous MRR: $X
   - Net Change: $X (X%)
   - ARR Equivalent: $X

2. MRR MOVEMENTS
   - New MRR: +$X
   - Expansion MRR: +$X
   - Contraction MRR: -$X
   - Churn MRR: -$X
   - Reactivation MRR: +$X

3. GROWTH ANALYSIS
   - MRR Growth Rate: X%
   - Quick Ratio: X
   - Net MRR Growth: X%

4. CUSTOMER MOVEMENTS
   - New customers
   - Upgrades
   - Downgrades
   - Churned customers

5. SEGMENT BREAKDOWN
   - By tier/plan
   - By industry
   - By size

6. TREND ANALYSIS
   - 3-month trend
   - 12-month trend
   - Seasonality

7. HEALTH INDICATORS
   - Quick ratio trend
   - Expansion vs churn
   - Customer concentration

8. FORECAST IMPLICATIONS
   - Run rate
   - Growth trajectory
   - Risk to plan"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"MRR analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "mrr_analysis",
                "period": period,
                "analysis": response,
            },
        )

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM when no specific handler exists."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider and no handler for task type",
            )

        prompt = f"""As the Vector (Vector) - Vector, specializing in
revenue operations and growth, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough revenue-focused response with data-driven insights."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"LLM handling failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )

    # State management methods

    def record_revenue(self, period: str, data: Dict[str, Any]) -> None:
        """Record revenue data for a period."""
        self._revenue_data[period] = {
            **data,
            "recorded_at": _utcnow().isoformat(),
        }

    def set_metric(self, name: str, value: float) -> None:
        """Set a revenue metric."""
        self._metrics[name] = value

    def add_forecast(self, period: str, forecast: Dict[str, Any]) -> None:
        """Add a revenue forecast."""
        self._forecasts[period] = {
            **forecast,
            "created_at": _utcnow().isoformat(),
        }

    def add_cohort(self, cohort_id: str, data: Dict[str, Any]) -> None:
        """Add cohort data."""
        self._cohorts[cohort_id] = data

    async def _handle_vls_buyer_acquisition(self, task: Task) -> TaskResult:
        """Execute VLS Stage: Buyer Acquisition."""
        from ag3ntwerk.modules.vls.stages import execute_buyer_acquisition

        try:
            result = await execute_buyer_acquisition(task.context)

            return TaskResult(
                task_id=task.id,
                success=result.get("success", False),
                output=result,
                error=result.get("error"),
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"VLS Buyer Acquisition failed: {e}",
            )

    async def _handle_vls_billing_revenue(self, task: Task) -> TaskResult:
        """Execute VLS Stage: Billing & Revenue."""
        from ag3ntwerk.modules.vls.stages import execute_billing_revenue

        try:
            result = await execute_billing_revenue(task.context)

            return TaskResult(
                task_id=task.id,
                success=result.get("success", False),
                output=result,
                error=result.get("error"),
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"VLS Billing & Revenue failed: {e}",
            )

    def get_revenue_status(self) -> Dict[str, Any]:
        """Get current revenue status."""
        return {
            "total_periods_tracked": len(self._revenue_data),
            "active_forecasts": len(self._forecasts),
            "metrics": self._metrics,
            "cohorts_tracked": len(self._cohorts),
            "capabilities": self.capabilities,
        }
