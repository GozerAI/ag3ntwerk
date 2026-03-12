"""
Keystone (Keystone) Financial Domain Models.

Data models for financial planning, budgeting, cost analysis, and resource allocation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class BudgetStatus(Enum):
    """Budget status."""

    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    ACTIVE = "active"
    CLOSED = "closed"
    REVISED = "revised"


class ExpenseCategory(Enum):
    """Expense categories."""

    PERSONNEL = "personnel"
    INFRASTRUCTURE = "infrastructure"
    SOFTWARE = "software"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    RESEARCH = "research"
    TRAVEL = "travel"
    PROFESSIONAL_SERVICES = "professional_services"
    OTHER = "other"


class CostType(Enum):
    """Cost classification types."""

    FIXED = "fixed"
    VARIABLE = "variable"
    SEMI_VARIABLE = "semi_variable"
    CAPITAL = "capital"
    OPERATING = "operating"


class ForecastType(Enum):
    """Financial forecast types."""

    REVENUE = "revenue"
    EXPENSE = "expense"
    CASH_FLOW = "cash_flow"
    PROFIT = "profit"
    HEADCOUNT = "headcount"


class InvestmentStatus(Enum):
    """Investment status."""

    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class RiskLevel(Enum):
    """Financial risk levels."""

    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class ApprovalStatus(Enum):
    """Approval workflow status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


@dataclass
class Budget:
    """Represents a budget."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    period: str = ""  # e.g., "FY2024", "Q1 2024"
    status: BudgetStatus = BudgetStatus.DRAFT
    total_amount: float = 0.0
    allocated_amount: float = 0.0
    spent_amount: float = 0.0
    categories: Dict[str, float] = field(default_factory=dict)
    owner: str = ""
    approver: Optional[str] = None
    department: str = ""
    assumptions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    approved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetLineItem:
    """Represents a budget line item."""

    id: str = field(default_factory=lambda: str(uuid4()))
    budget_id: str = ""
    name: str = ""
    description: str = ""
    category: ExpenseCategory = ExpenseCategory.OTHER
    cost_type: CostType = CostType.OPERATING
    amount: float = 0.0
    actual_amount: float = 0.0
    variance: float = 0.0
    variance_percent: float = 0.0
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostAnalysis:
    """Represents a cost analysis."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    period: str = ""
    scope: str = ""  # department, project, category
    total_costs: float = 0.0
    cost_breakdown: Dict[str, float] = field(default_factory=dict)
    cost_drivers: List[Dict[str, Any]] = field(default_factory=list)
    trends: List[Dict[str, Any]] = field(default_factory=list)
    benchmarks: Dict[str, Any] = field(default_factory=dict)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    analyst: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostOptimization:
    """Represents a cost optimization initiative."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    area: str = ""
    current_cost: float = 0.0
    target_cost: float = 0.0
    savings_target: float = 0.0
    savings_achieved: float = 0.0
    initiatives: List[Dict[str, Any]] = field(default_factory=list)
    quick_wins: List[str] = field(default_factory=list)
    long_term_initiatives: List[str] = field(default_factory=list)
    risks: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "planned"  # planned, in_progress, completed
    owner: str = ""
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Forecast:
    """Represents a financial forecast."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    forecast_type: ForecastType = ForecastType.REVENUE
    horizon: str = ""  # e.g., "12 months"
    base_period: str = ""
    methodology: str = ""
    assumptions: List[str] = field(default_factory=list)
    baseline_forecast: Dict[str, float] = field(default_factory=dict)
    optimistic_forecast: Dict[str, float] = field(default_factory=dict)
    pessimistic_forecast: Dict[str, float] = field(default_factory=dict)
    key_drivers: List[Dict[str, Any]] = field(default_factory=list)
    confidence_level: str = "medium"
    risk_factors: List[str] = field(default_factory=list)
    analyst: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    valid_until: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ROIAnalysis:
    """Represents an ROI analysis."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    investment_id: Optional[str] = None
    total_investment: float = 0.0
    initial_investment: float = 0.0
    ongoing_costs: float = 0.0
    total_benefits: float = 0.0
    tangible_benefits: float = 0.0
    intangible_benefits: List[str] = field(default_factory=list)
    roi_percent: float = 0.0
    payback_period_months: float = 0.0
    npv: float = 0.0
    irr: float = 0.0
    discount_rate: float = 0.0
    timeframe_years: int = 3
    sensitivity_analysis: Dict[str, Any] = field(default_factory=dict)
    risk_adjusted_roi: Optional[float] = None
    recommendation: str = ""
    analyst: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Investment:
    """Represents an investment proposal."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    investment_type: str = ""  # capex, opex, strategic
    amount: float = 0.0
    status: InvestmentStatus = InvestmentStatus.PROPOSED
    sponsor: str = ""
    department: str = ""
    business_case: str = ""
    expected_benefits: List[str] = field(default_factory=list)
    roi_analysis_id: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risks: List[Dict[str, Any]] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approvers: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    approved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceAllocation:
    """Represents a resource allocation plan."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    period: str = ""
    total_resources: Dict[str, Any] = field(default_factory=dict)  # {type: amount}
    allocations: List[Dict[str, Any]] = field(
        default_factory=list
    )  # {project, resource_type, amount}
    utilization_rate: float = 0.0
    gaps: List[Dict[str, Any]] = field(default_factory=list)
    priorities: Dict[str, int] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    owner: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BreakEvenAnalysis:
    """Represents a break-even analysis."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    product_service: str = ""
    fixed_costs: float = 0.0
    variable_cost_per_unit: float = 0.0
    price_per_unit: float = 0.0
    break_even_units: float = 0.0
    break_even_revenue: float = 0.0
    contribution_margin: float = 0.0
    contribution_margin_ratio: float = 0.0
    margin_of_safety: float = 0.0
    operating_leverage: float = 0.0
    scenarios: List[Dict[str, Any]] = field(default_factory=list)
    analyst: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VarianceAnalysis:
    """Represents a variance analysis."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    period: str = ""
    budget_id: Optional[str] = None
    budgeted_amount: float = 0.0
    actual_amount: float = 0.0
    variance: float = 0.0
    variance_percent: float = 0.0
    favorable: bool = True
    variance_by_category: Dict[str, float] = field(default_factory=dict)
    root_causes: List[str] = field(default_factory=list)
    corrective_actions: List[str] = field(default_factory=list)
    analyst: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PricingAnalysis:
    """Represents a pricing analysis."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    product_service: str = ""
    cost_basis: float = 0.0
    target_margin: float = 0.0
    recommended_price: float = 0.0
    competitive_prices: Dict[str, float] = field(default_factory=dict)
    price_elasticity: Optional[float] = None
    pricing_strategy: str = ""  # cost_plus, value_based, competitive, penetration
    tiers: List[Dict[str, Any]] = field(default_factory=list)
    discounts: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    analyst: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FinancialMetrics:
    """Financial department metrics."""

    timestamp: datetime = field(default_factory=_utcnow)

    # Budget metrics
    total_budget: float = 0.0
    total_spent: float = 0.0
    budget_utilization: float = 0.0
    variance_to_budget: float = 0.0

    # Cost metrics
    total_costs: float = 0.0
    cost_reduction_achieved: float = 0.0
    cost_per_unit: float = 0.0

    # Investment metrics
    total_investments: int = 0
    approved_investments: int = 0
    average_roi: float = 0.0
    average_payback_months: float = 0.0

    # Forecast accuracy
    forecast_accuracy: float = 0.0

    # Resource metrics
    resource_utilization: float = 0.0

    metadata: Dict[str, Any] = field(default_factory=dict)


# Financial capabilities
FINANCIAL_DOMAIN_CAPABILITIES = [
    # Budgeting
    "budget_planning",
    "budget_tracking",
    "variance_analysis",
    # Cost Management
    "cost_analysis",
    "cost_optimization",
    "break_even_analysis",
    # Investment
    "roi_calculation",
    "investment_analysis",
    "financial_modeling",
    # Forecasting
    "forecast",
    "scenario_planning",
    # Resource Management
    "resource_allocation",
    "capacity_planning",
    # Pricing
    "pricing_analysis",
    "margin_analysis",
    # Reporting
    "financial_reporting",
    "usage_tracking",
]
