"""
Keystone (Keystone) Agent - Keystone.

Codename: Keystone
Core function: Protect and grow financial health; allocate resources intelligently.

The Keystone handles all financial and resource management tasks:
- Cost analysis and optimization
- Budget planning and forecasting
- Pricing strategy and margin analysis
- Resource allocation
- ROI calculations
"""

from ag3ntwerk.agents.keystone.agent import Keystone
from ag3ntwerk.agents.keystone.managers import (
    BudgetManager,
    CostManager,
    PricingManager,
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
from ag3ntwerk.agents.keystone.models import (
    # Enums
    BudgetStatus,
    ExpenseCategory,
    CostType,
    ForecastType,
    InvestmentStatus,
    RiskLevel,
    ApprovalStatus,
    # Dataclasses
    Budget,
    BudgetLineItem,
    CostAnalysis,
    CostOptimization,
    Forecast,
    ROIAnalysis,
    Investment,
    ResourceAllocation,
    BreakEvenAnalysis,
    VarianceAnalysis,
    PricingAnalysis,
    FinancialMetrics,
    # Capabilities
    FINANCIAL_DOMAIN_CAPABILITIES,
)

# Codename alias
Keystone = Keystone

__all__ = [
    # Agent
    "Keystone",
    "Keystone",
    # Managers
    "BudgetManager",
    "CostManager",
    "PricingManager",
    # Specialists
    "FinancialAnalyst",
    "CostAccountant",
    "BudgetAnalyst",
    "InvestmentAnalyst",
    "PricingAnalyst",
    "TreasuryAnalyst",
    "ComplianceAccountant",
    # Enums
    "BudgetStatus",
    "ExpenseCategory",
    "CostType",
    "ForecastType",
    "InvestmentStatus",
    "RiskLevel",
    "ApprovalStatus",
    # Dataclasses
    "Budget",
    "BudgetLineItem",
    "CostAnalysis",
    "CostOptimization",
    "Forecast",
    "ROIAnalysis",
    "Investment",
    "ResourceAllocation",
    "BreakEvenAnalysis",
    "VarianceAnalysis",
    "PricingAnalysis",
    "FinancialMetrics",
    # Capabilities
    "FINANCIAL_DOMAIN_CAPABILITIES",
]
