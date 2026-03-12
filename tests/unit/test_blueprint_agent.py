"""
Unit tests for Blueprint (Blueprint) agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.blueprint import Blueprint, Blueprint
from ag3ntwerk.agents.blueprint.managers import (
    RoadmapManager,
    FeatureManager,
    RequirementsManager,
)
from ag3ntwerk.agents.blueprint.specialists import (
    RoadmapPlanner,
    FeaturePrioritizer,
    RequirementsWriter,
    BacklogGroomer,
    MarketResearcher,
    SprintPlanner,
)
from ag3ntwerk.core.base import Task, TaskStatus


class TestCPOAgent:
    """Tests for Blueprint agent."""

    def test_cpo_creation(self):
        """Test Blueprint agent creation."""
        cpo = Blueprint()

        assert cpo.code == "Blueprint"
        assert cpo.name == "Blueprint"
        assert cpo.codename == "Blueprint"
        assert cpo.domain == "Product Management, Strategy, Requirements"

    def test_blueprint_alias(self):
        """Test Blueprint is an alias for Blueprint."""
        blueprint = Blueprint()

        assert blueprint.code == "Blueprint"
        assert blueprint.codename == "Blueprint"

    def test_cpo_capabilities(self):
        """Test Blueprint has expected capabilities."""
        cpo = Blueprint()

        expected_capabilities = [
            "feature_prioritization",
            "roadmap_update",
            "requirements_gathering",
            "sprint_planning",
            "backlog_grooming",
            "milestone_tracking",
            "product_spec",
            "user_story",
            "acceptance_criteria",
            "feature_scoping",
            "competitive_analysis",
            "market_research",
        ]

        for cap in expected_capabilities:
            assert cap in cpo.capabilities, f"Missing capability: {cap}"

    def test_can_handle_product_tasks(self):
        """Test Blueprint can handle product management tasks."""
        cpo = Blueprint()

        product_tasks = [
            "feature_prioritization",
            "roadmap_update",
            "requirements_gathering",
            "sprint_planning",
            "backlog_grooming",
            "milestone_tracking",
            "product_spec",
            "user_story",
        ]

        for task_type in product_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert cpo.can_handle(task), f"Blueprint should handle {task_type}"

    def test_cannot_handle_non_product_tasks(self):
        """Test Blueprint doesn't handle non-product tasks."""
        cpo = Blueprint()

        non_product_tasks = [
            "code_review",
            "security_scan",
            "cost_analysis",
            "campaign_creation",
        ]

        for task_type in non_product_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert not cpo.can_handle(task), f"Blueprint should not handle {task_type}"

    def test_feature_management(self):
        """Test adding and tracking features."""
        cpo = Blueprint()

        feature = {
            "id": "feat-auth",
            "name": "OAuth Integration",
            "priority": "P0",
        }
        feature_id = cpo.add_feature("product-1", feature)

        assert feature_id == "feat-auth"
        assert "feat-auth" in cpo._features
        assert cpo._features["feat-auth"]["product_id"] == "product-1"

    def test_roadmap_management(self):
        """Test updating product roadmap."""
        cpo = Blueprint()

        roadmap = {
            "themes": ["AI Integration", "Performance"],
            "milestones": ["M1", "M2"],
        }
        cpo.update_roadmap("product-1", roadmap)

        assert "product-1" in cpo._roadmaps
        assert "updated_at" in cpo._roadmaps["product-1"]

    def test_backlog_management(self):
        """Test adding items to backlog."""
        cpo = Blueprint()

        cpo.add_to_backlog("product-1", ["item-1", "item-2"])
        cpo.add_to_backlog("product-1", ["item-3"])

        assert len(cpo._backlogs["product-1"]) == 3
        assert "item-3" in cpo._backlogs["product-1"]

    def test_milestone_management(self):
        """Test setting milestones."""
        cpo = Blueprint()

        milestone = {
            "id": "ms-q1",
            "name": "Q1 Release",
            "target_date": "2026-03-31",
        }
        ms_id = cpo.set_milestone("product-1", milestone)

        assert ms_id == "ms-q1"
        assert "ms-q1" in cpo._milestones
        assert cpo._milestones["ms-q1"]["product_id"] == "product-1"

    def test_get_product_status(self):
        """Test getting product status summary."""
        cpo = Blueprint()

        cpo.update_roadmap("product-1", {"themes": ["AI"]})
        cpo.add_feature("product-1", {"id": "f1", "name": "Feature 1"})
        cpo.set_milestone("product-1", {"id": "m1", "name": "M1"})

        status = cpo.get_product_status()

        assert status["total_products"] == 1
        assert status["total_features"] == 1
        assert status["total_milestones"] == 1
        assert "capabilities" in status

    def test_get_product_status_for_specific_product(self):
        """Test getting status for a specific product."""
        cpo = Blueprint()

        cpo.update_roadmap("product-1", {"themes": ["AI"]})
        cpo.add_feature("product-1", {"id": "f1", "name": "Feature 1"})
        cpo.add_to_backlog("product-1", ["item-1"])

        status = cpo.get_product_status("product-1")

        assert status["roadmap"] is not None
        assert len(status["features"]) == 1
        assert len(status["backlog"]) == 1

    def test_subordinate_managers_registered(self):
        """Test that managers are registered as subordinates."""
        cpo = Blueprint()

        subordinate_codes = list(cpo._subordinates.keys())

        assert "RoadmapMgr" in subordinate_codes
        assert "FeatureMgr" in subordinate_codes
        assert "RequirementsMgr" in subordinate_codes


class TestCPOExecute:
    """Tests for Blueprint task execution."""

    @pytest.mark.asyncio
    async def test_execute_feature_prioritization(self):
        """Test executing feature prioritization task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Priority matrix complete")

        cpo = Blueprint(llm_provider=mock_provider)

        task = Task(
            description="Prioritize Q1 feature requests",
            task_type="feature_prioritization",
            context={
                "features": ["auth", "search", "notifications"],
                "quarter": "Q1 2026",
            },
        )

        result = await cpo.execute(task)

        assert result.success is True
        assert "prioritization_type" in result.output
        assert result.output["prioritization_type"] == "feature_prioritization"

    @pytest.mark.asyncio
    async def test_execute_roadmap_update(self):
        """Test executing roadmap update task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Roadmap updated")

        cpo = Blueprint(llm_provider=mock_provider)

        task = Task(
            description="Update roadmap for Q2",
            task_type="roadmap_update",
            context={
                "product_id": "main-product",
                "updates": {"add_features": ["AI search"]},
                "timeframe": "Q2 2026",
            },
        )

        result = await cpo.execute(task)

        assert result.success is True
        assert "update_type" in result.output

    @pytest.mark.asyncio
    async def test_execute_requirements_gathering(self):
        """Test executing requirements gathering task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Requirements documented")

        cpo = Blueprint(llm_provider=mock_provider)

        task = Task(
            description="Gather requirements for new search feature",
            task_type="requirements_gathering",
            context={
                "feature": {"name": "Advanced Search"},
                "stakeholders": ["engineering", "product", "sales"],
            },
        )

        result = await cpo.execute(task)

        assert result.success is True
        assert "requirements_type" in result.output
        assert result.output["requirements_type"] == "gathering"

    @pytest.mark.asyncio
    async def test_execute_sprint_planning(self):
        """Test executing sprint planning task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Sprint plan created")

        cpo = Blueprint(llm_provider=mock_provider)

        task = Task(
            description="Plan Sprint 12",
            task_type="sprint_planning",
            context={
                "backlog": ["story-1", "story-2", "story-3"],
                "capacity": {"developers": 5, "points": 40},
                "sprint_length": 2,
            },
        )

        result = await cpo.execute(task)

        assert result.success is True
        assert "planning_type" in result.output
        assert result.output["planning_type"] == "sprint_planning"

    @pytest.mark.asyncio
    async def test_execute_backlog_grooming(self):
        """Test executing backlog grooming task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Backlog groomed")

        cpo = Blueprint(llm_provider=mock_provider)

        task = Task(
            description="Groom product backlog",
            task_type="backlog_grooming",
            context={
                "backlog": ["item-1", "item-2", "item-3", "item-4"],
            },
        )

        result = await cpo.execute(task)

        assert result.success is True
        assert "grooming_type" in result.output
        assert result.output["grooming_type"] == "backlog_grooming"

    @pytest.mark.asyncio
    async def test_execute_milestone_tracking(self):
        """Test executing milestone tracking via direct handler.

        milestone_tracking routes to RoadmapMgr via MANAGER_ROUTING,
        so we test the direct handler by calling it explicitly.
        """
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Milestone status report")

        cpo = Blueprint(llm_provider=mock_provider)

        task = Task(
            description="Track Q1 release milestone",
            task_type="milestone_tracking",
            context={
                "milestone": {"name": "Q1 Release", "target": "2026-03-31"},
                "features": ["auth", "search"],
            },
        )

        # Call the direct handler to bypass manager routing
        result = await cpo._handle_milestone_tracking(task)

        assert result.success is True
        assert "tracking_type" in result.output
        assert result.output["tracking_type"] == "milestone_tracking"

    @pytest.mark.asyncio
    async def test_execute_product_spec(self):
        """Test executing product spec task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="PRD created")

        cpo = Blueprint(llm_provider=mock_provider)

        task = Task(
            description="Create spec for AI-powered search",
            task_type="product_spec",
            context={
                "feature": {"name": "AI Search", "priority": "P0"},
                "requirements": ["fast response", "relevant results"],
            },
        )

        result = await cpo.execute(task)

        assert result.success is True
        assert "spec_type" in result.output
        assert result.output["spec_type"] == "product_spec"

    @pytest.mark.asyncio
    async def test_execute_user_story(self):
        """Test executing user story creation task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="User stories written")

        cpo = Blueprint(llm_provider=mock_provider)

        task = Task(
            description="Write user stories for search feature",
            task_type="user_story",
            context={
                "feature": "Advanced Search",
                "user_types": ["developer", "admin"],
            },
        )

        result = await cpo.execute(task)

        assert result.success is True
        assert "story_type" in result.output
        assert result.output["story_type"] == "user_story"

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self):
        """Test handling of LLM errors during execution.

        Use a non-routed task type to test LLM error handling in the
        direct handler path (sprint_planning has no MANAGER_ROUTING).
        """
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=Exception("LLM Error"))

        cpo = Blueprint(llm_provider=mock_provider)

        task = Task(
            description="Plan next sprint",
            task_type="sprint_planning",
            context={"sprint": "Sprint 12", "capacity": 40},
        )

        result = await cpo.execute(task)

        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_without_provider(self):
        """Test execution without LLM provider."""
        cpo = Blueprint(llm_provider=None)

        task = Task(
            description="Unknown product task",
            task_type="unknown_type",
        )

        result = await cpo.execute(task)

        assert result.success is False
        assert "No LLM provider" in result.error


class TestRoadmapManager:
    """Tests for RoadmapManager."""

    def test_manager_creation(self):
        """Test roadmap manager creation."""
        manager = RoadmapManager()

        assert manager.code == "RoadmapMgr"
        assert manager.name == "Roadmap Manager"
        assert manager.domain == "Product Roadmap and Planning"

    def test_can_handle_roadmap_tasks(self):
        """Test manager handles roadmap-related tasks."""
        manager = RoadmapManager()

        tasks = [
            "roadmap_update",
            "roadmap_review",
            "milestone_planning",
            "timeline_adjustment",
            "dependency_mapping",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"

    @pytest.mark.asyncio
    async def test_execute_roadmap_update(self):
        """Test roadmap update execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Roadmap updated")

        manager = RoadmapManager(llm_provider=mock_provider)

        task = Task(
            description="Update product roadmap",
            task_type="roadmap_update",
            context={"product_id": "main", "updates": {}},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["update_type"] == "roadmap_update"


class TestFeatureManager:
    """Tests for FeatureManager."""

    def test_manager_creation(self):
        """Test feature manager creation."""
        manager = FeatureManager()

        assert manager.code == "FeatureMgr"
        assert manager.name == "Feature Manager"
        assert manager.domain == "Feature Lifecycle Management"

    def test_can_handle_feature_tasks(self):
        """Test manager handles feature-related tasks."""
        manager = FeatureManager()

        tasks = [
            "feature_prioritization",
            "feature_scoping",
            "feature_tracking",
            "feature_spec",
            "impact_analysis",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"

    @pytest.mark.asyncio
    async def test_execute_feature_prioritization(self):
        """Test feature prioritization execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Features prioritized")

        manager = FeatureManager(llm_provider=mock_provider)

        task = Task(
            description="Prioritize features",
            task_type="feature_prioritization",
            context={"features": ["auth", "search"]},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["prioritization_type"] == "feature_prioritization"


class TestRequirementsManager:
    """Tests for RequirementsManager."""

    def test_manager_creation(self):
        """Test requirements manager creation."""
        manager = RequirementsManager()

        assert manager.code == "RequirementsMgr"
        assert manager.name == "Requirements Manager"
        assert manager.domain == "Requirements Engineering"

    def test_can_handle_requirements_tasks(self):
        """Test manager handles requirements-related tasks."""
        manager = RequirementsManager()

        tasks = [
            "requirements_gathering",
            "user_story",
            "acceptance_criteria",
            "spec_review",
            "requirements_validation",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"

    @pytest.mark.asyncio
    async def test_execute_requirements_gathering(self):
        """Test requirements gathering execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Requirements gathered")

        manager = RequirementsManager(llm_provider=mock_provider)

        task = Task(
            description="Gather requirements for auth feature",
            task_type="requirements_gathering",
            context={"feature": {"name": "OAuth"}, "stakeholders": ["eng"]},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["gathering_type"] == "requirements_gathering"
