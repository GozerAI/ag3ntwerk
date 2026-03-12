"""
Unit tests for Echo (Echo) agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.echo import Echo, Echo
from ag3ntwerk.agents.echo.managers import CampaignManager, ContentManager, BrandManager
from ag3ntwerk.core.base import Task, TaskStatus


class TestCMOAgent:
    """Tests for Echo agent."""

    def test_cmo_creation(self):
        """Test Echo agent creation."""
        cmo = Echo()

        assert cmo.code == "Echo"
        assert cmo.name == "Echo"
        assert cmo.codename == "Echo"
        assert cmo.domain == "Marketing, Brand, Growth"

    def test_echo_alias(self):
        """Test Echo is an alias for Echo."""
        echo = Echo()

        assert echo.code == "Echo"
        assert echo.codename == "Echo"

    def test_cmo_capabilities(self):
        """Test Echo has expected capabilities."""
        cmo = Echo()

        expected_capabilities = [
            "campaign_creation",
            "campaign_management",
            "brand_strategy",
            "market_analysis",
            "content_marketing",
            "social_media_strategy",
            "marketing_analytics",
            "customer_segmentation",
            "competitive_positioning",
            "go_to_market",
            "demand_generation",
            "marketing_roi",
        ]

        for cap in expected_capabilities:
            assert cap in cmo.capabilities, f"Missing capability: {cap}"

    def test_can_handle_marketing_tasks(self):
        """Test Echo can handle marketing tasks."""
        cmo = Echo()

        marketing_tasks = [
            "campaign_creation",
            "brand_strategy",
            "market_analysis",
            "customer_segmentation",
            "go_to_market",
        ]

        for task_type in marketing_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert cmo.can_handle(task), f"Echo should handle {task_type}"

    def test_cannot_handle_non_marketing_tasks(self):
        """Test Echo doesn't handle non-marketing tasks."""
        cmo = Echo()

        non_marketing_tasks = [
            "code_review",
            "security_scan",
            "cost_analysis",
            "compliance_check",
        ]

        for task_type in non_marketing_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert not cmo.can_handle(task), f"Echo should not handle {task_type}"

    def test_get_marketing_status(self):
        """Test getting marketing status."""
        cmo = Echo()

        # Register some campaigns and segments
        cmo.register_campaign("camp1", {"name": "Q1 Campaign"})
        cmo.register_segment("seg1", {"name": "Enterprise"})

        status = cmo.get_marketing_status()

        assert status["active_campaigns"] == 1
        assert status["defined_segments"] == 1
        assert "capabilities" in status

    def test_campaign_registration(self):
        """Test campaign registration and retrieval."""
        cmo = Echo()

        campaign_data = {
            "name": "Product Launch Q1",
            "budget": 50000,
            "target": "Enterprise",
        }
        cmo.register_campaign("camp1", campaign_data)

        retrieved = cmo.get_campaign("camp1")
        assert retrieved == campaign_data

        # Non-existent campaign
        assert cmo.get_campaign("nonexistent") is None

    def test_segment_registration(self):
        """Test segment registration and retrieval."""
        cmo = Echo()

        segment_data = {
            "name": "SMB",
            "size": 10000,
            "criteria": ["employee_count < 100"],
        }
        cmo.register_segment("smb", segment_data)

        retrieved = cmo.get_segment("smb")
        assert retrieved == segment_data


class TestCMOExecute:
    """Tests for Echo task execution."""

    @pytest.mark.asyncio
    async def test_execute_campaign_creation(self):
        """Test executing campaign creation task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Campaign plan generated")

        cmo = Echo(llm_provider=mock_provider)

        task = Task(
            description="Create Q1 product launch campaign",
            task_type="campaign_creation",
            context={
                "campaign_name": "Q1 Launch",
                "product": "AI Assistant",
                "target_market": "Enterprise",
            },
        )

        result = await cmo.execute(task)

        assert result.success is True
        assert "planning_type" in result.output
        assert result.output["planning_type"] == "campaign_planning"

    @pytest.mark.asyncio
    async def test_execute_brand_strategy(self):
        """Test executing brand strategy task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Brand strategy developed")

        cmo = Echo(llm_provider=mock_provider)

        task = Task(
            description="Develop brand strategy for new product line",
            task_type="brand_strategy",
            context={
                "brand_name": "TechCo",
                "objectives": ["increase awareness", "establish thought leadership"],
            },
        )

        result = await cmo.execute(task)

        assert result.success is True
        assert "identity_type" in result.output
        assert result.output["identity_type"] == "brand_identity"

    @pytest.mark.asyncio
    async def test_execute_market_analysis(self):
        """Test executing market analysis task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Market analysis complete")

        cmo = Echo(llm_provider=mock_provider)

        task = Task(
            description="Analyze enterprise SaaS market",
            task_type="market_analysis",
            context={
                "market": "Enterprise SaaS",
                "segment": "AI/ML Tools",
            },
        )

        result = await cmo.execute(task)

        assert result.success is True
        assert "assessment_type" in result.output
        assert result.output["assessment_type"] == "brand_health"

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self):
        """Test handling of LLM errors during execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=Exception("LLM Error"))

        cmo = Echo(llm_provider=mock_provider)

        task = Task(
            description="Create campaign",
            task_type="campaign_creation",
        )

        result = await cmo.execute(task)

        assert result.success is False
        assert "failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_without_provider(self):
        """Test execution without LLM provider."""
        cmo = Echo(llm_provider=None)

        task = Task(
            description="Create campaign",
            task_type="unknown_type",  # Will fall through to LLM handler
        )

        result = await cmo.execute(task)

        assert result.success is False
        assert "No LLM provider" in result.error


class TestCampaignManager:
    """Tests for CampaignManager."""

    def test_manager_creation(self):
        """Test campaign manager creation."""
        manager = CampaignManager()

        assert manager.code == "CampaignMgr"
        assert manager.name == "Campaign Manager"
        assert manager.domain == "Marketing Campaigns"

    def test_can_handle_campaign_tasks(self):
        """Test manager handles campaign tasks."""
        manager = CampaignManager()

        tasks = [
            "campaign_planning",
            "campaign_execution",
            "ab_testing",
            "campaign_optimization",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task)

    @pytest.mark.asyncio
    async def test_execute_campaign_planning(self):
        """Test campaign planning execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Campaign plan")

        manager = CampaignManager(llm_provider=mock_provider)

        task = Task(
            description="Plan Q1 campaign",
            task_type="campaign_planning",
            context={"campaign_name": "Q1", "budget": {"total": 50000}},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["planning_type"] == "campaign_planning"

    @pytest.mark.asyncio
    async def test_execute_ab_testing(self):
        """Test A/B testing design."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="A/B test design")

        manager = CampaignManager(llm_provider=mock_provider)

        task = Task(
            description="Design A/B test for email subject",
            task_type="ab_testing",
            context={
                "test_name": "Email Subject Test",
                "hypothesis": "Shorter subjects increase open rates",
            },
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["test_type"] == "ab_testing"


class TestContentManager:
    """Tests for ContentManager."""

    def test_manager_creation(self):
        """Test content manager creation."""
        manager = ContentManager()

        assert manager.code == "ContentMgr"
        assert manager.name == "Content Manager"
        assert manager.domain == "Content Marketing"

    def test_can_handle_content_tasks(self):
        """Test manager handles content tasks."""
        manager = ContentManager()

        tasks = [
            "content_strategy",
            "editorial_planning",
            "content_creation",
            "seo_optimization",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task)

    @pytest.mark.asyncio
    async def test_execute_content_strategy(self):
        """Test content strategy execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Content strategy")

        manager = ContentManager(llm_provider=mock_provider)

        task = Task(
            description="Develop content strategy",
            task_type="content_strategy",
            context={"audience": "Developers", "goals": ["awareness", "leads"]},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["strategy_type"] == "content_strategy"


class TestBrandManager:
    """Tests for BrandManager."""

    def test_manager_creation(self):
        """Test brand manager creation."""
        manager = BrandManager()

        assert manager.code == "BrandMgr"
        assert manager.name == "Brand Manager"
        assert manager.domain == "Brand Strategy"

    def test_can_handle_brand_tasks(self):
        """Test manager handles brand tasks."""
        manager = BrandManager()

        tasks = [
            "brand_identity",
            "messaging_framework",
            "brand_guidelines",
            "brand_health",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task)

    @pytest.mark.asyncio
    async def test_execute_brand_identity(self):
        """Test brand identity execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Brand identity")

        manager = BrandManager(llm_provider=mock_provider)

        task = Task(
            description="Develop brand identity",
            task_type="brand_identity",
            context={"brand_name": "TechCo", "values": ["innovation", "trust"]},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["identity_type"] == "brand_identity"
