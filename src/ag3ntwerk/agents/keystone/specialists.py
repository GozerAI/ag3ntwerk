"""
Keystone (Keystone) Specialist Classes.

Individual contributor specialists for financial operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ag3ntwerk.core.base import (
    Specialist,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class FinancialAnalyst(Specialist):
    """
    Specialist for financial analysis.

    Performs detailed financial modeling and analysis.
    """

    HANDLED_TASK_TYPES = [
        "financial_modeling",
        "scenario_analysis",
        "sensitivity_analysis",
        "valuation_analysis",
        "financial_projections",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="FinAnalyst",
            name="Financial Analyst",
            domain="Financial Analysis",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute financial analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        data = task.context.get("financial_data", {})
        assumptions = task.context.get("assumptions", {})

        prompt = f"""As a Financial Analyst specialist:

Task Type: {task.task_type}
Description: {task.description}
Financial Data: {data}
Assumptions: {assumptions}

Provide financial analysis:
1. Model structure and methodology
2. Key assumptions and inputs
3. Base case projections
4. Scenario variations
5. Sensitivity analysis
6. Key findings
7. Limitations and caveats
8. Recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": task.task_type,
                "analysis": response,
                "analyzed_at": _utcnow().isoformat(),
            },
        )


class CostAccountant(Specialist):
    """
    Specialist for cost accounting.

    Tracks, allocates, and analyzes costs across the organization.
    """

    HANDLED_TASK_TYPES = [
        "cost_accounting",
        "cost_allocation",
        "activity_based_costing",
        "overhead_analysis",
        "cost_variance",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="CostAccountant",
            name="Cost Accountant",
            domain="Cost Accounting",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute cost accounting task."""
        task.status = TaskStatus.IN_PROGRESS

        cost_data = task.context.get("cost_data", {})
        allocation_basis = task.context.get("allocation_basis", "activity")

        prompt = f"""As a Cost Accountant specialist:

Task Type: {task.task_type}
Description: {task.description}
Cost Data: {cost_data}
Allocation Basis: {allocation_basis}

Provide cost accounting analysis:
1. Cost classification (direct/indirect)
2. Cost allocation methodology
3. Activity drivers identification
4. Cost pool analysis
5. Unit cost calculations
6. Variance analysis
7. Cost optimization opportunities
8. Reporting recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "accounting_type": task.task_type,
                "allocation_basis": allocation_basis,
                "analysis": response,
            },
        )


class BudgetAnalyst(Specialist):
    """
    Specialist for budget analysis.

    Creates, monitors, and analyzes budgets.
    """

    HANDLED_TASK_TYPES = [
        "budget_creation",
        "budget_monitoring",
        "budget_variance_analysis",
        "budget_forecasting",
        "rolling_forecast",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="BudgetAnalyst",
            name="Budget Analyst",
            domain="Budget Analysis",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute budget analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        budget_data = task.context.get("budget_data", {})
        period = task.context.get("period", "quarterly")

        prompt = f"""As a Budget Analyst specialist:

Task Type: {task.task_type}
Description: {task.description}
Budget Data: {budget_data}
Period: {period}

Provide budget analysis:
1. Budget structure review
2. Historical trend analysis
3. Variance identification
4. Root cause analysis
5. Forecast adjustments
6. Risk factors
7. Corrective actions
8. Reporting summary"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "budget_type": task.task_type,
                "period": period,
                "analysis": response,
            },
        )


class InvestmentAnalyst(Specialist):
    """
    Specialist for investment analysis.

    Evaluates investment opportunities and capital allocation.
    """

    HANDLED_TASK_TYPES = [
        "investment_evaluation",
        "capital_allocation",
        "roi_analysis",
        "npv_calculation",
        "irr_analysis",
        "payback_analysis",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="InvestAnalyst",
            name="Investment Analyst",
            domain="Investment Analysis",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute investment analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        investment = task.context.get("investment", {})
        cash_flows = task.context.get("cash_flows", [])
        discount_rate = task.context.get("discount_rate", 0.10)

        prompt = f"""As an Investment Analyst specialist:

Task Type: {task.task_type}
Description: {task.description}
Investment: {investment}
Cash Flows: {cash_flows}
Discount Rate: {discount_rate}

Provide investment analysis:
1. Investment summary
2. Cash flow projections
3. NPV calculation
4. IRR calculation
5. Payback period
6. Risk assessment
7. Sensitivity analysis
8. Investment recommendation"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "investment_type": task.task_type,
                "discount_rate": discount_rate,
                "analysis": response,
            },
        )


class PricingAnalyst(Specialist):
    """
    Specialist for pricing analysis.

    Analyzes pricing strategies and their financial impact.
    """

    HANDLED_TASK_TYPES = [
        "price_analysis",
        "margin_calculation",
        "price_elasticity",
        "competitive_pricing_analysis",
        "discount_impact",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="PricingAnalyst",
            name="Pricing Analyst",
            domain="Pricing Analysis",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute pricing analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        pricing_data = task.context.get("pricing_data", {})
        cost_data = task.context.get("cost_data", {})

        prompt = f"""As a Pricing Analyst specialist:

Task Type: {task.task_type}
Description: {task.description}
Pricing Data: {pricing_data}
Cost Data: {cost_data}

Provide pricing analysis:
1. Current price structure
2. Cost-plus analysis
3. Margin analysis by product/segment
4. Price elasticity assessment
5. Competitive positioning
6. Discount impact analysis
7. Optimization opportunities
8. Pricing recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "pricing_type": task.task_type,
                "analysis": response,
            },
        )


class TreasuryAnalyst(Specialist):
    """
    Specialist for treasury and cash management.

    Manages cash flow, liquidity, and working capital.
    """

    HANDLED_TASK_TYPES = [
        "cash_flow_analysis",
        "liquidity_management",
        "working_capital_analysis",
        "cash_forecasting",
        "funding_analysis",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="TreasuryAnalyst",
            name="Treasury Analyst",
            domain="Treasury Management",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute treasury analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        cash_data = task.context.get("cash_data", {})
        forecast_horizon = task.context.get("horizon", "13 weeks")

        prompt = f"""As a Treasury Analyst specialist:

Task Type: {task.task_type}
Description: {task.description}
Cash Data: {cash_data}
Forecast Horizon: {forecast_horizon}

Provide treasury analysis:
1. Current cash position
2. Cash flow forecast
3. Liquidity ratios
4. Working capital metrics
5. Funding requirements
6. Investment opportunities
7. Risk exposures
8. Recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "treasury_type": task.task_type,
                "horizon": forecast_horizon,
                "analysis": response,
            },
        )


class ComplianceAccountant(Specialist):
    """
    Specialist for financial compliance.

    Ensures financial reporting compliance and controls.
    """

    HANDLED_TASK_TYPES = [
        "compliance_review",
        "control_testing",
        "audit_preparation",
        "policy_compliance",
        "regulatory_reporting",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="ComplianceAcct",
            name="Compliance Accountant",
            domain="Financial Compliance",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute compliance task."""
        task.status = TaskStatus.IN_PROGRESS

        compliance_area = task.context.get("compliance_area", "general")
        regulations = task.context.get("regulations", [])

        prompt = f"""As a Compliance Accountant specialist:

Task Type: {task.task_type}
Description: {task.description}
Compliance Area: {compliance_area}
Regulations: {regulations}

Provide compliance analysis:
1. Regulatory requirements
2. Current compliance status
3. Gap identification
4. Control effectiveness
5. Remediation needs
6. Documentation requirements
7. Timeline for compliance
8. Recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "compliance_type": task.task_type,
                "compliance_area": compliance_area,
                "analysis": response,
            },
        )
