"""
Unit tests for Compass (Compass) agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.compass import Compass, Compass
from ag3ntwerk.agents.compass.managers import (
    StrategicPlanningManager,
    MarketIntelligenceManager,
    ContentStrategyManager,
    GoToMarketManager,
)
from ag3ntwerk.agents.compass.specialists import (
    StrategyAnalyst,
    MarketResearcher,
    ContentStrategist,
    BrandStrategist,
    GTMSpecialist,
)
from ag3ntwerk.core.base import Task, TaskStatus


class TestCSOAgent:
    """Tests for Compass agent."""

    @pytest.fixture
    def cso(self, mock_llm_provider):
        return Compass(llm_provider=mock_llm_provider)

    def test_cso_creation(self):
        """Test Compass agent creation."""
        cso = Compass()

        assert cso.code == "Compass"
        assert cso.name == "Compass"
        assert cso.codename == "Compass"
        assert cso.domain == "Strategy, Content, Market Analysis"

    def test_compass_alias(self):
        """Test Compass is an alias for Compass."""
        assert Compass is Compass

        compass = Compass()
        assert compass.code == "Compass"
        assert compass.codename == "Compass"

    def test_cso_capabilities(self, cso):
        """Test Compass has expected capabilities."""
        expected_capabilities = [
            "market_analysis",
            "competitive_analysis",
            "strategic_planning",
            "content_strategy",
            "content_creation",
            "brand_positioning",
            "go_to_market",
            "trend_analysis",
            "swot_analysis",
            "opportunity_assessment",
            "messaging_framework",
            "value_proposition",
        ]

        for cap in expected_capabilities:
            assert cap in cso.capabilities, f"Missing capability: {cap}"

    def test_can_handle_strategy_tasks(self, cso):
        """Test Compass can handle strategy-related tasks."""
        strategy_tasks = [
            "market_analysis",
            "competitive_analysis",
            "strategic_planning",
            "content_strategy",
            "content_creation",
            "brand_positioning",
            "go_to_market",
            "trend_analysis",
            "swot_analysis",
            "opportunity_assessment",
            "messaging_framework",
            "value_proposition",
        ]

        for task_type in strategy_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert cso.can_handle(task), f"Compass should handle {task_type}"

    def test_cannot_handle_non_strategy_tasks(self, cso):
        """Test Compass doesn't handle non-strategy tasks."""
        non_strategy_tasks = [
            "code_review",
            "security_scan",
            "cost_analysis",
            "vulnerability_assessment",
            "revenue_tracking",
            "incident_response",
        ]

        for task_type in non_strategy_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert not cso.can_handle(task), f"Compass should not handle {task_type}"

    def test_cso_subordinate_registration(self, cso):
        """Test Compass registers managers as subordinates."""
        subordinate_codes = [sub.code for sub in cso.subordinates]

        assert "SPM" in subordinate_codes  # StrategicPlanningManager
        assert "MIM" in subordinate_codes  # MarketIntelligenceManager
        assert "CSM" in subordinate_codes  # ContentStrategyManager
        assert "GTMM" in subordinate_codes  # GoToMarketManager
        assert len(cso.subordinates) == 4

    def test_cso_manager_specialist_hierarchy(self, cso):
        """Test managers have specialists registered."""
        for manager in cso.subordinates:
            if manager.code == "SPM":
                sub_codes = [s.code for s in manager.subordinates]
                assert "SA" in sub_codes  # StrategyAnalyst
            elif manager.code == "MIM":
                sub_codes = [s.code for s in manager.subordinates]
                assert "MR" in sub_codes  # MarketResearcher
            elif manager.code == "CSM":
                sub_codes = [s.code for s in manager.subordinates]
                assert "CS" in sub_codes  # ContentStrategist
                assert "BS" in sub_codes  # BrandStrategist
            elif manager.code == "GTMM":
                sub_codes = [s.code for s in manager.subordinates]
                assert "GTMS" in sub_codes  # GTMSpecialist

    def test_add_market_insight(self, cso):
        """Test adding market insights."""
        cso.add_market_insight("ai_market", {"size": "1.5T", "growth": "15%"})

        assert "ai_market" in cso._market_insights
        assert cso._market_insights["ai_market"]["size"] == "1.5T"

    def test_get_strategy_status(self, cso):
        """Test getting strategy status."""
        cso.add_market_insight("key1", "value1")
        cso.add_market_insight("key2", "value2")

        status = cso.get_strategy_status()

        assert status["market_insights"] == 2
        assert status["content_calendar_items"] == 0
        assert status["strategic_initiatives"] == 0
        assert "capabilities" in status

    def test_cso_personality_seed(self):
        """Test Compass personality seed traits are defined."""
        from ag3ntwerk.core.personality import PERSONALITY_SEEDS

        assert "Compass" in PERSONALITY_SEEDS
        seed = PERSONALITY_SEEDS["Compass"]
        assert seed["risk"] == 0.5
        assert seed["creativity"] == 0.7
        assert seed["decision"] == "balanced"
        assert seed["communication"] == "direct"


class TestCSOExecute:
    """Tests for Compass task execution."""

    @pytest.mark.asyncio
    async def test_execute_market_analysis(self, mock_llm_provider):
        """Test executing market analysis task."""
        cso = Compass(llm_provider=mock_llm_provider)

        task = Task(
            description="Analyze the AI developer tools market",
            task_type="market_analysis",
            context={"market": "AI/ML developer tools", "scope": "comprehensive"},
        )

        result = await cso.execute(task)

        assert result.success is True
        assert result.output["analysis_type"] == "market"
        assert result.output["market"] == "AI/ML developer tools"

    @pytest.mark.asyncio
    async def test_execute_competitive_analysis(self, mock_llm_provider):
        """Test executing competitive analysis task."""
        cso = Compass(llm_provider=mock_llm_provider)

        task = Task(
            description="Analyze competitors in AI assistant space",
            task_type="competitive_analysis",
            context={
                "industry": "AI Assistants",
                "competitors": ["CompA", "CompB"],
            },
        )

        result = await cso.execute(task)

        assert result.success is True
        assert result.output["analysis_type"] == "competitive"
        assert result.output["industry"] == "AI Assistants"

    @pytest.mark.asyncio
    async def test_execute_strategic_planning(self, mock_llm_provider):
        """Test executing strategic planning task."""
        cso = Compass(llm_provider=mock_llm_provider)

        task = Task(
            description="Create 3-year strategic plan for platform growth",
            task_type="strategic_planning",
            context={
                "timeframe": "3 years",
                "focus_areas": ["expansion", "retention", "innovation"],
            },
        )

        result = await cso.execute(task)

        assert result.success is True
        assert result.output["plan_type"] == "strategic"
        assert result.output["timeframe"] == "3 years"

    @pytest.mark.asyncio
    async def test_execute_content_strategy(self, mock_llm_provider):
        """Test executing content strategy task."""
        cso = Compass(llm_provider=mock_llm_provider)

        task = Task(
            description="Develop content strategy for developer audience",
            task_type="content_strategy",
            context={
                "audience": "developers",
                "channels": ["blog", "youtube", "twitter"],
            },
        )

        result = await cso.execute(task)

        assert result.success is True
        assert result.output["strategy_type"] == "content"
        assert result.output["audience"] == "developers"

    @pytest.mark.asyncio
    async def test_execute_content_creation(self, mock_llm_provider):
        """Test executing content creation task."""
        cso = Compass(llm_provider=mock_llm_provider)

        task = Task(
            description="Create blog post about AI best practices",
            task_type="content_creation",
            context={
                "content_type": "blog_post",
                "tone": "technical",
            },
        )

        result = await cso.execute(task)

        assert result.success is True
        assert result.output["content_type"] == "blog_post"

    @pytest.mark.asyncio
    async def test_execute_swot_analysis(self, mock_llm_provider):
        """Test executing SWOT analysis task."""
        cso = Compass(llm_provider=mock_llm_provider)

        task = Task(
            description="SWOT analysis for enterprise product line",
            task_type="swot_analysis",
            context={"subject": "Enterprise AI Platform"},
        )

        result = await cso.execute(task)

        assert result.success is True
        assert result.output["analysis_type"] == "swot"
        assert result.output["subject"] == "Enterprise AI Platform"

    @pytest.mark.asyncio
    async def test_execute_with_llm_fallback(self, mock_llm_provider):
        """Test execution falls back to LLM for unhandled capability types."""
        cso = Compass(llm_provider=mock_llm_provider)

        task = Task(
            description="Assess new market opportunity",
            task_type="opportunity_assessment",
            context={"opportunity": "Southeast Asia market"},
        )

        result = await cso.execute(task)

        # opportunity_assessment has no specific handler, falls to _handle_with_llm
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_without_provider(self):
        """Test execution without LLM provider."""
        cso = Compass(llm_provider=None)

        task = Task(
            description="Unknown task",
            task_type="unknown_type",
        )

        result = await cso.execute(task)

        assert result.success is False
        assert "No LLM provider" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self, mock_llm_provider):
        """Test handling of LLM errors during execution."""
        mock_llm_provider.generate = AsyncMock(side_effect=Exception("LLM Error"))

        cso = Compass(llm_provider=mock_llm_provider)

        task = Task(
            description="Analyze market",
            task_type="market_analysis",
            context={"market": "test"},
        )

        result = await cso.execute(task)

        assert result.success is False
        assert "failed" in result.error.lower()


class TestCSOManagers:
    """Tests for Compass manager creation and capabilities."""

    def test_strategic_planning_manager(self):
        """Test StrategicPlanningManager creation."""
        spm = StrategicPlanningManager()

        assert spm.code == "SPM"
        assert spm.name == "Strategic Planning Manager"
        assert "strategic_planning" in spm.capabilities
        assert "roadmap_creation" in spm.capabilities

    def test_market_intelligence_manager(self):
        """Test MarketIntelligenceManager creation."""
        mim = MarketIntelligenceManager()

        assert mim.code == "MIM"
        assert mim.name == "Market Intelligence Manager"
        assert "market_analysis" in mim.capabilities
        assert "competitive_analysis" in mim.capabilities

    def test_content_strategy_manager(self):
        """Test ContentStrategyManager creation."""
        csm = ContentStrategyManager()

        assert csm.code == "CSM"
        assert csm.name == "Content Strategy Manager"
        assert "content_strategy" in csm.capabilities
        assert "content_creation" in csm.capabilities

    def test_go_to_market_manager(self):
        """Test GoToMarketManager creation."""
        gtmm = GoToMarketManager()

        assert gtmm.code == "GTMM"
        assert gtmm.name == "Go-to-Market Manager"
        assert "go_to_market" in gtmm.capabilities
        assert "value_proposition" in gtmm.capabilities
