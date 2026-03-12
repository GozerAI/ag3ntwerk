"""
Keystone (Keystone) Agent - Keystone.

Codename: Keystone
Core function: Protect and grow financial health; allocate resources intelligently.

The Keystone handles all financial and resource management tasks:
- Cost analysis and optimization
- Budget planning and forecasting
- Resource allocation
- ROI calculations
- Financial modeling
- Usage tracking and billing

Sphere of influence: Budgeting/forecasting, unit economics, pricing support,
cash/treasury, reporting, controls, capital planning, financial risk.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Manager,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider
from ag3ntwerk.agents.keystone.managers import (
    CostManager,
    PricingManager,
    BudgetManager,
)
from ag3ntwerk.agents.keystone.specialists import (
    FinancialAnalyst,
    CostAccountant,
    BudgetAnalyst,
    InvestmentAnalyst,
    PricingAnalyst,
    TreasuryAnalyst,
    ComplianceAccountant,
)


# Financial task types this agent can handle
FINANCIAL_CAPABILITIES = [
    "cost_analysis",
    "budget_planning",
    "resource_allocation",
    "roi_calculation",
    "financial_modeling",
    "usage_tracking",
    "cost_optimization",
    "pricing_analysis",
    "investment_analysis",
    "break_even_analysis",
    "variance_analysis",
    "forecast",
    # Manager-level task types
    "development_cost_analysis",
    "infrastructure_cost_tracking",
    "cost_attribution",
    "cost_forecasting",
    "vendor_cost_analysis",
    "pricing_strategy",
    "margin_analysis",
    "competitive_pricing",
    "pricing_experiment",
    "price_optimization",
    "discount_analysis",
    "budget_variance",
    "financial_forecast",
    "spend_tracking",
    "budget_reallocation",
    # Specialist-level task types
    "financial_modeling",
    "scenario_analysis",
    "sensitivity_analysis",
    "valuation_analysis",
    "financial_projections",
    "cost_accounting",
    "cost_allocation",
    "activity_based_costing",
    "overhead_analysis",
    "cost_variance",
    "budget_creation",
    "budget_monitoring",
    "budget_variance_analysis",
    "budget_forecasting",
    "rolling_forecast",
    "investment_evaluation",
    "capital_allocation",
    "roi_analysis",
    "npv_calculation",
    "irr_analysis",
    "payback_analysis",
    "price_analysis",
    "margin_calculation",
    "price_elasticity",
    "competitive_pricing_analysis",
    "discount_impact",
    "cash_flow_analysis",
    "liquidity_management",
    "working_capital_analysis",
    "cash_forecasting",
    "funding_analysis",
    "compliance_review",
    "control_testing",
    "audit_preparation",
    "policy_compliance",
    "regulatory_reporting",
]

# Routing from task types to managers
MANAGER_ROUTING = {
    # CostManager tasks
    "development_cost_analysis": "CostMgr",
    "infrastructure_cost_tracking": "CostMgr",
    "cost_attribution": "CostMgr",
    "cost_optimization": "CostMgr",
    "cost_forecasting": "CostMgr",
    "vendor_cost_analysis": "CostMgr",
    "cost_analysis": "CostMgr",
    # PricingManager tasks
    "pricing_strategy": "PricingMgr",
    "margin_analysis": "PricingMgr",
    "competitive_pricing": "PricingMgr",
    "pricing_experiment": "PricingMgr",
    "price_optimization": "PricingMgr",
    "discount_analysis": "PricingMgr",
    "pricing_analysis": "PricingMgr",
    # BudgetManager tasks
    "budget_planning": "BudgetMgr",
    "budget_variance": "BudgetMgr",
    "financial_forecast": "BudgetMgr",
    "spend_tracking": "BudgetMgr",
    "budget_reallocation": "BudgetMgr",
    "forecast": "BudgetMgr",
    "variance_analysis": "BudgetMgr",
}


class Keystone(Manager):
    """
    Keystone - Keystone.

    The Keystone is responsible for all financial planning and resource
    management within the ag3ntwerk system.

    Codename: Keystone

    Core Responsibilities:
    - Cost analysis and optimization
    - Budget planning and forecasting
    - Resource allocation and utilization
    - ROI calculations and financial modeling
    - Usage tracking and billing optimization

    Example:
        ```python
        cfo = Keystone(llm_provider=llm)

        task = Task(
            description="Analyze cloud infrastructure costs for Q1",
            task_type="cost_analysis",
            context={"period": "Q1 2024", "category": "cloud"},
        )
        result = await cfo.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__(
            code="Keystone",
            name="Keystone",
            domain="Finance, Budgeting, Resource Management",
            llm_provider=llm_provider,
        )
        self.codename = "Keystone"

        self.capabilities = FINANCIAL_CAPABILITIES

        # Financial-specific state
        self._budgets: Dict[str, float] = {}
        self._cost_tracking: Dict[str, List[Dict[str, Any]]] = {}
        self._resource_allocation: Dict[str, Any] = {}

        # Initialize and register managers with their specialists
        self._init_managers()

    def can_handle(self, task: Task) -> bool:
        """Check if this is a financial-related task."""
        return task.task_type in self.capabilities

    def _init_managers(self) -> None:
        """Initialize and register managers with their specialists."""
        # Create managers
        cost_mgr = CostManager(llm_provider=self.llm_provider)
        pricing_mgr = PricingManager(llm_provider=self.llm_provider)
        budget_mgr = BudgetManager(llm_provider=self.llm_provider)

        # Create specialists
        financial_analyst = FinancialAnalyst(llm_provider=self.llm_provider)
        cost_accountant = CostAccountant(llm_provider=self.llm_provider)
        budget_analyst = BudgetAnalyst(llm_provider=self.llm_provider)
        investment_analyst = InvestmentAnalyst(llm_provider=self.llm_provider)
        pricing_analyst = PricingAnalyst(llm_provider=self.llm_provider)
        treasury_analyst = TreasuryAnalyst(llm_provider=self.llm_provider)
        compliance_accountant = ComplianceAccountant(llm_provider=self.llm_provider)

        # Register specialists with appropriate managers
        cost_mgr.register_subordinate(cost_accountant)
        cost_mgr.register_subordinate(treasury_analyst)
        pricing_mgr.register_subordinate(pricing_analyst)
        budget_mgr.register_subordinate(budget_analyst)
        budget_mgr.register_subordinate(financial_analyst)
        budget_mgr.register_subordinate(investment_analyst)
        budget_mgr.register_subordinate(compliance_accountant)

        # Register managers with Keystone
        self.register_subordinate(cost_mgr)
        self.register_subordinate(pricing_mgr)
        self.register_subordinate(budget_mgr)

    def _route_to_manager(self, task_type: str) -> Optional[str]:
        """Route task to appropriate manager."""
        return MANAGER_ROUTING.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute a financial task, routing through managers when appropriate."""
        task.status = TaskStatus.IN_PROGRESS

        # First, try to route through a manager
        manager_code = self._route_to_manager(task.task_type)
        if manager_code and manager_code in self._subordinates:
            return await self.delegate(task, manager_code)

        # Fall back to direct handlers
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            "cost_analysis": self._handle_cost_analysis,
            "budget_planning": self._handle_budget_planning,
            "resource_allocation": self._handle_resource_allocation,
            "roi_calculation": self._handle_roi_calculation,
            "cost_optimization": self._handle_cost_optimization,
            "forecast": self._handle_forecast,
            "break_even_analysis": self._handle_break_even_analysis,
            # VLS handlers
            "vls_validation_economics": self._handle_vls_validation_economics,
        }
        return handlers.get(task_type)

    async def _handle_cost_analysis(self, task: Task) -> TaskResult:
        """Analyze costs."""
        period = task.context.get("period", "current")
        category = task.context.get("category", "all")
        data = task.context.get("cost_data", {})

        prompt = f"""As the Keystone, perform cost analysis.

Period: {period}
Category: {category}
Cost Data: {data if data else 'Provide general cost analysis framework'}
Description: {task.description}
Context: {task.context}

Provide a cost analysis including:
1. Cost breakdown by category
2. Trends and patterns
3. Cost drivers identification
4. Comparison to benchmarks
5. Anomalies or areas of concern
6. Cost per unit/transaction metrics
7. Recommendations for optimization
8. Projected future costs"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "cost",
                "period": period,
                "category": category,
                "analysis": response,
            },
        )

    async def _handle_budget_planning(self, task: Task) -> TaskResult:
        """Plan budget."""
        period = task.context.get("period", "annual")
        departments = task.context.get("departments", [])
        constraints = task.context.get("constraints", {})

        prompt = f"""As the Keystone, create a budget plan.

Planning Period: {period}
Departments: {departments if departments else 'All departments'}
Constraints: {constraints if constraints else 'Standard constraints'}
Description: {task.description}
Context: {task.context}

Create a budget plan including:
1. Revenue projections
2. Expense categories and allocations
3. Capital expenditure plans
4. Departmental budgets
5. Contingency reserves
6. Key assumptions
7. Approval workflow
8. Monitoring and variance tracking plan"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "plan_type": "budget",
                "period": period,
                "plan": response,
            },
        )

    async def _handle_resource_allocation(self, task: Task) -> TaskResult:
        """Allocate resources."""
        resources = task.context.get("resources", [])
        projects = task.context.get("projects", [])
        priorities = task.context.get("priorities", {})

        prompt = f"""As the Keystone, plan resource allocation.

Available Resources: {resources if resources else 'Assess required resources'}
Projects/Initiatives: {projects if projects else 'List current initiatives'}
Priorities: {priorities if priorities else 'Define priority criteria'}
Description: {task.description}
Context: {task.context}

Create a resource allocation plan including:
1. Resource inventory and availability
2. Project requirements analysis
3. Priority-based allocation matrix
4. Utilization optimization
5. Gap analysis
6. Contingency planning
7. Monitoring metrics
8. Reallocation triggers"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "plan_type": "resource_allocation",
                "plan": response,
            },
        )

    async def _handle_roi_calculation(self, task: Task) -> TaskResult:
        """Calculate ROI."""
        investment = task.context.get("investment", {})
        benefits = task.context.get("benefits", {})
        timeframe = task.context.get("timeframe", "3 years")

        prompt = f"""As the Keystone, calculate ROI.

Investment Details: {investment if investment else 'Define investment parameters'}
Expected Benefits: {benefits if benefits else 'Identify benefit categories'}
Analysis Timeframe: {timeframe}
Description: {task.description}
Context: {task.context}

Provide ROI analysis including:
1. Total investment costs (initial + ongoing)
2. Quantified benefits (tangible + intangible)
3. ROI calculation and percentage
4. Payback period
5. Net Present Value (NPV)
6. Internal Rate of Return (IRR)
7. Sensitivity analysis
8. Risk-adjusted returns
9. Recommendation"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "roi",
                "timeframe": timeframe,
                "analysis": response,
            },
        )

    async def _handle_cost_optimization(self, task: Task) -> TaskResult:
        """Optimize costs."""
        area = task.context.get("area", "general")
        current_costs = task.context.get("current_costs", {})
        target_reduction = task.context.get("target_reduction", "10-20%")

        prompt = f"""As the Keystone, develop cost optimization plan.

Area: {area}
Current Costs: {current_costs if current_costs else 'Analyze current cost structure'}
Target Reduction: {target_reduction}
Description: {task.description}
Context: {task.context}

Develop a cost optimization plan including:
1. Current state assessment
2. Cost reduction opportunities
3. Quick wins vs long-term initiatives
4. Implementation roadmap
5. Expected savings per initiative
6. Risk assessment for each change
7. Success metrics
8. Monitoring and sustainability plan"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "plan_type": "cost_optimization",
                "area": area,
                "target": target_reduction,
                "plan": response,
            },
        )

    async def _handle_forecast(self, task: Task) -> TaskResult:
        """Create financial forecast."""
        forecast_type = task.context.get("forecast_type", "revenue")
        horizon = task.context.get("horizon", "12 months")
        historical_data = task.context.get("historical_data", {})

        prompt = f"""As the Keystone, create a financial forecast.

Forecast Type: {forecast_type}
Forecast Horizon: {horizon}
Historical Data: {historical_data if historical_data else 'Use reasonable assumptions'}
Description: {task.description}
Context: {task.context}

Create a forecast including:
1. Methodology and assumptions
2. Historical trend analysis
3. Baseline forecast
4. Scenario analysis (optimistic/pessimistic/realistic)
5. Key drivers and sensitivities
6. Confidence intervals
7. Risk factors
8. Recommended actions based on forecast"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "forecast_type": forecast_type,
                "horizon": horizon,
                "forecast": response,
            },
        )

    async def _handle_break_even_analysis(self, task: Task) -> TaskResult:
        """Perform break-even analysis."""
        fixed_costs = task.context.get("fixed_costs", 0)
        variable_costs = task.context.get("variable_costs", 0)
        price = task.context.get("price", 0)

        prompt = f"""As the Keystone, perform break-even analysis.

Fixed Costs: {fixed_costs if fixed_costs else 'Define fixed cost structure'}
Variable Costs: {variable_costs if variable_costs else 'Define variable costs per unit'}
Price: {price if price else 'Define pricing model'}
Description: {task.description}
Context: {task.context}

Provide break-even analysis including:
1. Cost structure breakdown
2. Break-even point (units and revenue)
3. Contribution margin analysis
4. Margin of safety
5. Operating leverage
6. Sensitivity analysis
7. What-if scenarios
8. Recommendations for improving break-even"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "break_even",
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

        prompt = f"""As the Keystone (Keystone) specializing in finance and resources,
handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough finance-focused response."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )

    def set_budget(self, category: str, amount: float) -> None:
        """Set a budget for a category."""
        self._budgets[category] = amount

    def track_cost(self, category: str, amount: float, description: str) -> None:
        """Track a cost entry."""
        if category not in self._cost_tracking:
            self._cost_tracking[category] = []
        self._cost_tracking[category].append(
            {
                "amount": amount,
                "description": description,
            }
        )

    async def _handle_vls_validation_economics(self, task: Task) -> TaskResult:
        """Execute VLS Stage 2: Validation & Economics."""
        from ag3ntwerk.modules.vls.stages import execute_validation_economics

        try:
            result = await execute_validation_economics(task.context)

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
                error=f"VLS Validation & Economics failed: {e}",
            )

    def get_financial_status(self) -> Dict[str, Any]:
        """Get current financial status."""
        total_budget = sum(self._budgets.values())
        total_costs = sum(
            sum(entry["amount"] for entry in entries) for entries in self._cost_tracking.values()
        )

        return {
            "total_budget": total_budget,
            "total_tracked_costs": total_costs,
            "budget_categories": len(self._budgets),
            "cost_categories": len(self._cost_tracking),
            "capabilities": self.capabilities,
        }
