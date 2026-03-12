"""
Unit tests for Vector (Vector) agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.vector import Vector, Vector
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
from ag3ntwerk.core.base import Task, TaskStatus


class TestCRevOAgent:
    """Tests for Vector agent."""

    @pytest.fixture
    def crevo(self, mock_llm_provider):
        return Vector(llm_provider=mock_llm_provider)

    def test_crevo_creation(self):
        """Test Vector agent creation."""
        crevo = Vector()

        assert crevo.code == "Vector"
        assert crevo.name == "Vector"
        assert crevo.codename == "Vector"
        assert crevo.domain == "Revenue Operations, Growth, Metrics"

    def test_vector_alias(self):
        """Test Vector is an alias for Vector."""
        assert Vector is Vector

        vector = Vector()
        assert vector.code == "Vector"
        assert vector.codename == "Vector"

    def test_crevo_capabilities(self, crevo):
        """Test Vector has expected capabilities."""
        expected_capabilities = [
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

        for cap in expected_capabilities:
            assert cap in crevo.capabilities, f"Missing capability: {cap}"

    def test_can_handle_revenue_tasks(self, crevo):
        """Test Vector can handle revenue-related tasks."""
        revenue_tasks = [
            "revenue_tracking",
            "churn_analysis",
            "feature_adoption_metrics",
            "conversion_analysis",
            "growth_experiment_design",
            "revenue_forecasting",
            "cohort_analysis",
            "mrr_analysis",
        ]

        for task_type in revenue_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert crevo.can_handle(task), f"Vector should handle {task_type}"

    def test_cannot_handle_non_revenue_tasks(self, crevo):
        """Test Vector doesn't handle non-revenue tasks."""
        non_revenue_tasks = [
            "code_review",
            "security_scan",
            "strategic_planning",
            "threat_detection",
            "cost_analysis",
            "data_governance",
        ]

        for task_type in non_revenue_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert not crevo.can_handle(task), f"Vector should not handle {task_type}"

    def test_crevo_subordinate_registration(self, crevo):
        """Test Vector registers managers as subordinates."""
        subordinate_codes = [sub.code for sub in crevo.subordinates]

        assert "RevenueMgr" in subordinate_codes
        assert "MetricsMgr" in subordinate_codes
        assert "GrowthMgr" in subordinate_codes
        assert len(crevo.subordinates) == 3

    def test_crevo_manager_specialist_hierarchy(self, crevo):
        """Test managers have specialists registered."""
        for manager in crevo.subordinates:
            if manager.code == "RevenueMgr":
                sub_codes = [s.code for s in manager.subordinates]
                assert "RevenueAnalyst" in sub_codes
                assert "ChurnAnalyst" in sub_codes
                assert "CohortAnalyst" in sub_codes
            elif manager.code == "MetricsMgr":
                sub_codes = [s.code for s in manager.subordinates]
                assert "AdoptionTracker" in sub_codes
            elif manager.code == "GrowthMgr":
                sub_codes = [s.code for s in manager.subordinates]
                assert "ConversionAnalyst" in sub_codes
                assert "GrowthExperimenter" in sub_codes

    def test_record_revenue(self, crevo):
        """Test recording revenue data."""
        crevo.record_revenue("Q1_2025", {"total": 500000, "mrr": 42000})

        assert "Q1_2025" in crevo._revenue_data
        assert crevo._revenue_data["Q1_2025"]["total"] == 500000
        assert "recorded_at" in crevo._revenue_data["Q1_2025"]

    def test_set_metric(self, crevo):
        """Test setting revenue metrics."""
        crevo.set_metric("mrr", 42000.0)
        crevo.set_metric("arpu", 150.0)

        assert crevo._metrics["mrr"] == 42000.0
        assert crevo._metrics["arpu"] == 150.0

    def test_add_forecast(self, crevo):
        """Test adding revenue forecasts."""
        crevo.add_forecast("Q2_2025", {"base_case": 550000, "best_case": 650000})

        assert "Q2_2025" in crevo._forecasts
        assert crevo._forecasts["Q2_2025"]["base_case"] == 550000
        assert "created_at" in crevo._forecasts["Q2_2025"]

    def test_add_cohort(self, crevo):
        """Test adding cohort data."""
        crevo.add_cohort("jan_2025", {"size": 100, "retention_30d": 0.85})

        assert "jan_2025" in crevo._cohorts
        assert crevo._cohorts["jan_2025"]["size"] == 100

    def test_get_revenue_status(self, crevo):
        """Test getting revenue status."""
        crevo.record_revenue("Q1", {"total": 500000})
        crevo.add_forecast("Q2", {"base": 550000})
        crevo.set_metric("mrr", 42000.0)
        crevo.add_cohort("jan", {"size": 100})

        status = crevo.get_revenue_status()

        assert status["total_periods_tracked"] == 1
        assert status["active_forecasts"] == 1
        assert status["metrics"]["mrr"] == 42000.0
        assert status["cohorts_tracked"] == 1
        assert "capabilities" in status

    def test_crevo_personality_seed(self):
        """Test Vector personality seed traits are defined."""
        from ag3ntwerk.core.personality import PERSONALITY_SEEDS

        assert "Vector" in PERSONALITY_SEEDS
        seed = PERSONALITY_SEEDS["Vector"]
        assert seed["risk"] == 0.6
        assert seed["assertiveness"] == 0.8
        assert seed["decision"] == "decisive"
        assert seed["communication"] == "direct"


class TestCRevOExecute:
    """Tests for Vector task execution."""

    @pytest.mark.asyncio
    async def test_execute_revenue_tracking(self, mock_llm_provider):
        """Test executing revenue tracking task."""
        crevo = Vector(llm_provider=mock_llm_provider)

        task = Task(
            description="Track Q4 revenue performance",
            task_type="revenue_tracking",
            context={
                "revenue_data": {"total": 500000, "mrr": 42000},
                "period": "quarterly",
            },
        )

        result = await crevo.execute(task)

        assert result.success is True
        assert result.output["tracking_type"] == "revenue_tracking"
        assert result.output["period"] == "quarterly"

    @pytest.mark.asyncio
    async def test_execute_churn_analysis(self, mock_llm_provider):
        """Test executing churn analysis task."""
        crevo = Vector(llm_provider=mock_llm_provider)

        task = Task(
            description="Analyze Q1 customer churn",
            task_type="churn_analysis",
            context={
                "churn_data": {"customer_churn_rate": 0.05},
                "period": "quarterly",
            },
        )

        result = await crevo.execute(task)

        assert result.success is True
        assert result.output["analysis_type"] == "churn_analysis"

    @pytest.mark.asyncio
    async def test_execute_feature_adoption(self, mock_llm_provider):
        """Test executing feature adoption metrics task."""
        crevo = Vector(llm_provider=mock_llm_provider)

        task = Task(
            description="Analyze feature adoption for new dashboard",
            task_type="feature_adoption_metrics",
            context={
                "features": ["dashboard", "api", "integrations"],
                "product_id": "platform-v2",
            },
        )

        result = await crevo.execute(task)

        assert result.success is True
        assert result.output["metrics_type"] == "feature_adoption_metrics"

    @pytest.mark.asyncio
    async def test_execute_conversion_analysis(self, mock_llm_provider):
        """Test executing conversion analysis task."""
        crevo = Vector(llm_provider=mock_llm_provider)

        task = Task(
            description="Analyze signup-to-paid conversion funnel",
            task_type="conversion_analysis",
            context={
                "funnel_data": {"visitors": 10000, "signups": 1000, "paid": 100},
                "funnel_type": "signup_to_paid",
            },
        )

        result = await crevo.execute(task)

        assert result.success is True
        assert result.output["analysis_type"] == "conversion_analysis"
        assert result.output["funnel_type"] == "signup_to_paid"

    @pytest.mark.asyncio
    async def test_execute_growth_experiment(self, mock_llm_provider):
        """Test executing growth experiment design task."""
        crevo = Vector(llm_provider=mock_llm_provider)

        task = Task(
            description="Design onboarding optimization experiment",
            task_type="growth_experiment_design",
            context={
                "hypothesis": "Simplified onboarding increases activation by 15%",
                "target_metrics": ["activation_rate", "time_to_first_value"],
            },
        )

        result = await crevo.execute(task)

        assert result.success is True
        assert result.output["experiment_type"] == "growth_experiment_design"

    @pytest.mark.asyncio
    async def test_execute_revenue_forecasting(self, mock_llm_provider):
        """Test executing revenue forecasting task."""
        crevo = Vector(llm_provider=mock_llm_provider)

        task = Task(
            description="Forecast next quarter revenue",
            task_type="revenue_forecasting",
            context={
                "historical_data": {"Q1": 400000, "Q2": 450000, "Q3": 500000},
                "forecast_period": "Q4_2025",
            },
        )

        result = await crevo.execute(task)

        assert result.success is True
        assert result.output["forecast_type"] == "revenue_forecasting"

    @pytest.mark.asyncio
    async def test_execute_cohort_analysis(self, mock_llm_provider):
        """Test executing cohort analysis task."""
        crevo = Vector(llm_provider=mock_llm_provider)

        task = Task(
            description="Analyze acquisition cohorts",
            task_type="cohort_analysis",
            context={
                "cohort_data": {"jan": {"size": 100}, "feb": {"size": 120}},
                "cohort_type": "acquisition",
            },
        )

        result = await crevo.execute(task)

        assert result.success is True
        assert result.output["analysis_type"] == "cohort_analysis"
        assert result.output["cohort_type"] == "acquisition"

    @pytest.mark.asyncio
    async def test_execute_mrr_analysis(self, mock_llm_provider):
        """Test executing MRR analysis task."""
        crevo = Vector(llm_provider=mock_llm_provider)

        task = Task(
            description="Analyze monthly recurring revenue",
            task_type="mrr_analysis",
            context={
                "mrr_data": {"current": 42000, "previous": 40000},
                "period": "monthly",
            },
        )

        result = await crevo.execute(task)

        assert result.success is True
        assert result.output["analysis_type"] == "mrr_analysis"

    @pytest.mark.asyncio
    async def test_execute_with_llm_fallback(self, mock_llm_provider):
        """Test execution falls back to LLM for unhandled capability types."""
        crevo = Vector(llm_provider=mock_llm_provider)

        task = Task(
            description="Calculate unit economics",
            task_type="unit_economics",
            context={"data": {"cac": 500, "ltv": 5000}},
        )

        result = await crevo.execute(task)

        # unit_economics has no specific handler, falls to _handle_with_llm
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_without_provider(self):
        """Test execution without LLM provider."""
        crevo = Vector(llm_provider=None)

        task = Task(
            description="Unknown task",
            task_type="unknown_type",
        )

        result = await crevo.execute(task)

        assert result.success is False
        assert "No LLM provider" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self, mock_llm_provider):
        """Test handling of LLM errors during execution."""
        mock_llm_provider.generate = AsyncMock(side_effect=Exception("LLM Error"))

        crevo = Vector(llm_provider=mock_llm_provider)

        task = Task(
            description="Track revenue",
            task_type="revenue_tracking",
            context={"revenue_data": {}, "period": "monthly"},
        )

        result = await crevo.execute(task)

        assert result.success is False


class TestCRevOManagers:
    """Tests for Vector manager creation and capabilities."""

    def test_revenue_manager(self):
        """Test RevenueManager creation."""
        rm = RevenueManager()

        assert rm.code == "RevenueMgr"
        assert rm.name == "Revenue Manager"
        assert "revenue_tracking" in rm.HANDLED_TASK_TYPES
        assert "revenue_forecasting" in rm.HANDLED_TASK_TYPES

    def test_metrics_manager(self):
        """Test MetricsManager creation."""
        mm = MetricsManager()

        assert mm.code == "MetricsMgr"
        assert mm.name == "Metrics Manager"
        assert "kpi_tracking" in mm.HANDLED_TASK_TYPES
        assert "benchmark_analysis" in mm.HANDLED_TASK_TYPES

    def test_growth_manager(self):
        """Test GrowthManager creation."""
        gm = GrowthManager()

        assert gm.code == "GrowthMgr"
        assert gm.name == "Growth Manager"
        assert "growth_experiment_design" in gm.HANDLED_TASK_TYPES
        assert "conversion_optimization" in gm.HANDLED_TASK_TYPES

    def test_revenue_manager_can_handle(self):
        """Test RevenueManager handles revenue tasks."""
        rm = RevenueManager()

        task = Task(description="Track revenue", task_type="revenue_tracking")
        assert rm.can_handle(task) is True

        task = Task(description="Scan security", task_type="security_scan")
        assert rm.can_handle(task) is False
