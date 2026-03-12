"""
Unit tests for Keystone (Keystone) agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.keystone import Keystone, Keystone
from ag3ntwerk.agents.keystone.managers import CostManager, PricingManager, BudgetManager
from ag3ntwerk.core.base import Task, TaskStatus


class TestCFOAgent:
    """Tests for Keystone agent."""

    def test_cfo_creation(self):
        """Test Keystone agent creation."""
        cfo = Keystone()

        assert cfo.code == "Keystone"
        assert cfo.name == "Keystone"
        assert cfo.codename == "Keystone"
        assert cfo.domain == "Finance, Budgeting, Resource Management"

    def test_keystone_alias(self):
        """Test Keystone is an alias for Keystone."""
        keystone = Keystone()

        assert keystone.code == "Keystone"
        assert keystone.codename == "Keystone"

    def test_cfo_capabilities(self):
        """Test Keystone has expected capabilities."""
        cfo = Keystone()

        expected_capabilities = [
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
        ]

        for cap in expected_capabilities:
            assert cap in cfo.capabilities, f"Missing capability: {cap}"

    def test_can_handle_financial_tasks(self):
        """Test Keystone can handle financial tasks."""
        cfo = Keystone()

        financial_tasks = [
            "cost_analysis",
            "budget_planning",
            "resource_allocation",
            "roi_calculation",
            "cost_optimization",
            "forecast",
        ]

        for task_type in financial_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert cfo.can_handle(task), f"Keystone should handle {task_type}"

    def test_cannot_handle_non_financial_tasks(self):
        """Test Keystone doesn't handle non-financial tasks."""
        cfo = Keystone()

        non_financial_tasks = [
            "code_review",
            "campaign_creation",
            "security_scan",
            "architecture_design",
        ]

        for task_type in non_financial_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert not cfo.can_handle(task), f"Keystone should not handle {task_type}"

    def test_get_financial_status(self):
        """Test getting financial status."""
        cfo = Keystone()

        # Set up some budgets and costs
        cfo.set_budget("engineering", 100000)
        cfo.set_budget("marketing", 50000)
        cfo.track_cost("engineering", 25000, "Q1 salaries")
        cfo.track_cost("engineering", 5000, "Tools")

        status = cfo.get_financial_status()

        assert status["total_budget"] == 150000
        assert status["total_tracked_costs"] == 30000
        assert status["budget_categories"] == 2
        assert status["cost_categories"] == 1
        assert "capabilities" in status

    def test_budget_management(self):
        """Test budget setting and retrieval."""
        cfo = Keystone()

        cfo.set_budget("infrastructure", 75000)
        assert cfo._budgets["infrastructure"] == 75000

        cfo.set_budget("infrastructure", 80000)  # Update
        assert cfo._budgets["infrastructure"] == 80000

    def test_cost_tracking(self):
        """Test cost tracking."""
        cfo = Keystone()

        cfo.track_cost("cloud", 1000, "AWS compute")
        cfo.track_cost("cloud", 500, "AWS storage")
        cfo.track_cost("licenses", 2000, "Software licenses")

        assert len(cfo._cost_tracking["cloud"]) == 2
        assert len(cfo._cost_tracking["licenses"]) == 1
        assert cfo._cost_tracking["cloud"][0]["amount"] == 1000
        assert cfo._cost_tracking["cloud"][0]["description"] == "AWS compute"


class TestCFOExecute:
    """Tests for Keystone task execution."""

    @pytest.mark.asyncio
    async def test_execute_cost_analysis(self):
        """Test executing cost analysis task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Cost analysis complete")

        cfo = Keystone(llm_provider=mock_provider)

        task = Task(
            description="Analyze Q1 cloud infrastructure costs",
            task_type="cost_analysis",
            context={
                "period": "Q1 2024",
                "category": "cloud",
            },
        )

        result = await cfo.execute(task)

        assert result.success is True
        assert "analysis_type" in result.output
        assert result.output["analysis_type"] == "cost"

    @pytest.mark.asyncio
    async def test_execute_budget_planning(self):
        """Test executing budget planning task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Budget plan created")

        cfo = Keystone(llm_provider=mock_provider)

        task = Task(
            description="Create annual budget plan",
            task_type="budget_planning",
            context={
                "period": "FY2024",
                "departments": ["engineering", "marketing", "sales"],
            },
        )

        result = await cfo.execute(task)

        assert result.success is True
        assert "planning_type" in result.output
        assert result.output["planning_type"] == "budget_planning"

    @pytest.mark.asyncio
    async def test_execute_roi_calculation(self):
        """Test executing ROI calculation task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="ROI analysis complete")

        cfo = Keystone(llm_provider=mock_provider)

        task = Task(
            description="Calculate ROI for new AI platform",
            task_type="roi_calculation",
            context={
                "investment": {"initial": 500000, "ongoing": 50000},
                "benefits": {"revenue": 1000000, "cost_savings": 200000},
                "timeframe": "3 years",
            },
        )

        result = await cfo.execute(task)

        assert result.success is True
        assert "analysis_type" in result.output
        assert result.output["analysis_type"] == "roi"

    @pytest.mark.asyncio
    async def test_execute_forecast(self):
        """Test executing forecast task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Forecast generated")

        cfo = Keystone(llm_provider=mock_provider)

        task = Task(
            description="Generate revenue forecast for next quarter",
            task_type="forecast",
            context={
                "forecast_type": "revenue",
                "horizon": "Q2 2024",
            },
        )

        result = await cfo.execute(task)

        assert result.success is True
        assert "forecast_type" in result.output

    @pytest.mark.asyncio
    async def test_execute_resource_allocation(self):
        """Test executing resource allocation task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Allocation plan created")

        cfo = Keystone(llm_provider=mock_provider)

        task = Task(
            description="Allocate resources for Q2 projects",
            task_type="resource_allocation",
            context={
                "resources": ["engineering team", "budget", "infrastructure"],
                "projects": ["Project Alpha", "Project Beta"],
            },
        )

        result = await cfo.execute(task)

        assert result.success is True
        assert "plan_type" in result.output
        assert result.output["plan_type"] == "resource_allocation"

    @pytest.mark.asyncio
    async def test_execute_break_even_analysis(self):
        """Test executing break-even analysis task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Break-even analysis complete")

        cfo = Keystone(llm_provider=mock_provider)

        task = Task(
            description="Calculate break-even point for new product",
            task_type="break_even_analysis",
            context={
                "fixed_costs": 100000,
                "variable_costs": 50,
                "price": 150,
            },
        )

        result = await cfo.execute(task)

        assert result.success is True
        assert "analysis_type" in result.output
        assert result.output["analysis_type"] == "break_even"

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self):
        """Test handling of LLM errors during execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=Exception("LLM Error"))

        cfo = Keystone(llm_provider=mock_provider)

        task = Task(
            description="Analyze costs",
            task_type="cost_analysis",
        )

        result = await cfo.execute(task)

        assert result.success is False
        assert "failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_without_provider(self):
        """Test execution without LLM provider."""
        cfo = Keystone(llm_provider=None)

        task = Task(
            description="Unknown financial task",
            task_type="unknown_type",  # Will fall through to LLM handler
        )

        result = await cfo.execute(task)

        assert result.success is False
        assert "No LLM provider" in result.error


class TestCostManager:
    """Tests for CostManager."""

    def test_manager_creation(self):
        """Test cost manager creation."""
        manager = CostManager()

        assert manager.code == "CostMgr"
        assert manager.name == "Cost Manager"
        assert manager.domain == "Cost Analysis and Optimization"

    def test_can_handle_cost_tasks(self):
        """Test manager handles cost-related tasks."""
        manager = CostManager()

        tasks = [
            "development_cost_analysis",
            "infrastructure_cost_tracking",
            "cost_attribution",
            "cost_forecasting",
            "vendor_cost_analysis",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task)

    @pytest.mark.asyncio
    async def test_execute_infrastructure_cost_tracking(self):
        """Test infrastructure cost tracking execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Cost tracking report")

        manager = CostManager(llm_provider=mock_provider)

        task = Task(
            description="Track infrastructure costs",
            task_type="infrastructure_cost_tracking",
            context={"infrastructure_type": "cloud", "period": "monthly"},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["tracking_type"] == "infrastructure_cost_tracking"


class TestPricingManager:
    """Tests for PricingManager."""

    def test_manager_creation(self):
        """Test pricing manager creation."""
        manager = PricingManager()

        assert manager.code == "PricingMgr"
        assert manager.name == "Pricing Manager"
        assert manager.domain == "Pricing Strategy and Analysis"

    def test_can_handle_pricing_tasks(self):
        """Test manager handles pricing-related tasks."""
        manager = PricingManager()

        tasks = [
            "pricing_strategy",
            "margin_analysis",
            "competitive_pricing",
            "pricing_experiment",
            "price_optimization",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task)

    @pytest.mark.asyncio
    async def test_execute_pricing_strategy(self):
        """Test pricing strategy execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Pricing strategy developed")

        manager = PricingManager(llm_provider=mock_provider)

        task = Task(
            description="Develop pricing strategy for new product",
            task_type="pricing_strategy",
            context={"product": "AI Platform", "target_market": "Enterprise"},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["strategy_type"] == "pricing_strategy"


class TestBudgetManager:
    """Tests for BudgetManager."""

    def test_manager_creation(self):
        """Test budget manager creation."""
        manager = BudgetManager()

        assert manager.code == "BudgetMgr"
        assert manager.name == "Budget Manager"
        assert manager.domain == "Budgeting and Forecasting"

    def test_can_handle_budget_tasks(self):
        """Test manager handles budget-related tasks."""
        manager = BudgetManager()

        tasks = [
            "budget_variance",
            "financial_forecast",
            "spend_tracking",
            "budget_reallocation",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task)

    @pytest.mark.asyncio
    async def test_execute_budget_variance(self):
        """Test budget variance analysis execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Variance analysis complete")

        manager = BudgetManager(llm_provider=mock_provider)

        task = Task(
            description="Analyze Q1 budget variance",
            task_type="budget_variance",
            context={"period": "Q1 2024", "budget": 500000, "actual": 525000},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["analysis_type"] == "budget_variance"
