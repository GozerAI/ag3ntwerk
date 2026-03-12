"""
Tests for ContentDistributionPipelineWorkflow.

Phase 6: End-to-end content distribution pipeline tests.
"""

import pytest
from unittest.mock import MagicMock

from ag3ntwerk.orchestration.workflows import ContentDistributionPipelineWorkflow
from ag3ntwerk.orchestration.base import WorkflowStep, WorkflowContext


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_registry():
    """Create a mock AgentRegistry."""
    registry = MagicMock()
    return registry


@pytest.fixture
def pipeline(mock_registry):
    """Create a ContentDistributionPipelineWorkflow instance."""
    return ContentDistributionPipelineWorkflow(mock_registry)


# =============================================================================
# Workflow Definition Tests
# =============================================================================


class TestContentDistributionPipelineDefinition:
    """Test workflow definition and structure."""

    def test_workflow_name(self, pipeline):
        """Test workflow has correct name."""
        assert pipeline.name == "content_distribution_pipeline"

    def test_workflow_description(self, pipeline):
        """Test workflow has a description."""
        desc = pipeline.description.lower()
        assert "content" in desc
        assert "social" in desc

    def test_defines_three_steps(self, pipeline):
        """Test workflow defines exactly 3 steps."""
        steps = pipeline.define_steps()
        assert len(steps) == 3

    def test_step_names(self, pipeline):
        """Test step names are correct."""
        steps = pipeline.define_steps()
        names = [s.name for s in steps]
        assert names == ["content_creation", "social_distribution", "revenue_tracking"]

    def test_step_executives(self, pipeline):
        """Test steps target correct agents."""
        steps = pipeline.define_steps()
        assert steps[0].agent == "Echo"
        assert steps[1].agent == "Echo"
        assert steps[2].agent == "Vector"

    def test_step_task_types(self, pipeline):
        """Test steps use correct task types."""
        steps = pipeline.define_steps()
        assert steps[0].task_type == "content_creation"
        assert steps[1].task_type == "social_distribute"
        assert steps[2].task_type == "revenue_tracking"

    def test_dependency_chain(self, pipeline):
        """Test dependency chain is correct."""
        steps = pipeline.define_steps()
        # Step 1: no dependencies
        assert steps[0].depends_on == []
        # Step 2: depends on content_creation
        assert steps[1].depends_on == ["content_creation"]
        # Step 3: depends on social_distribution
        assert steps[2].depends_on == ["social_distribution"]

    def test_revenue_tracking_is_optional(self, pipeline):
        """Test revenue tracking step is not required."""
        steps = pipeline.define_steps()
        revenue_step = steps[2]
        assert revenue_step.required is False

    def test_content_creation_is_required(self, pipeline):
        """Test content creation step is required by default."""
        steps = pipeline.define_steps()
        assert steps[0].required is True

    def test_social_distribution_is_required(self, pipeline):
        """Test social distribution step is required by default."""
        steps = pipeline.define_steps()
        assert steps[1].required is True


# =============================================================================
# Context Builder Tests
# =============================================================================


class TestContextBuilders:
    """Test that context builders produce correct task contexts."""

    def test_content_creation_context(self, pipeline):
        """Test content_creation step context builder."""
        steps = pipeline.define_steps()
        ctx = WorkflowContext(
            workflow_id="test-wf",
            workflow_name="content_distribution_pipeline",
            initial_params={
                "content_topic": "AI for Solo Devs",
                "content_type": "blog_post",
                "target_audience": "indie developers",
                "tone": "conversational",
                "keywords": ["AI", "indie"],
            },
        )

        builder = steps[0].context_builder
        assert builder is not None
        result = builder(ctx)

        assert result["topic"] == "AI for Solo Devs"
        assert result["content_type"] == "blog_post"
        assert result["audience"] == "indie developers"
        assert result["tone"] == "conversational"
        assert result["keywords"] == ["AI", "indie"]

    def test_content_creation_defaults(self, pipeline):
        """Test content_creation context builder with empty params."""
        steps = pipeline.define_steps()
        ctx = WorkflowContext(
            workflow_id="test-wf",
            workflow_name="content_distribution_pipeline",
            initial_params={},
        )

        builder = steps[0].context_builder
        result = builder(ctx)

        assert result["topic"] == ""
        assert result["content_type"] == "blog_post"
        assert result["audience"] == ""
        assert result["tone"] == "professional"
        assert result["keywords"] == []

    def test_social_distribution_context(self, pipeline):
        """Test social_distribution step context builder."""
        steps = pipeline.define_steps()
        ctx = WorkflowContext(
            workflow_id="test-wf",
            workflow_name="content_distribution_pipeline",
            initial_params={
                "platforms": ["linkedin", "twitter"],
                "hashtags": ["#AI", "#dev"],
            },
        )
        # Simulate content_creation step result
        ctx.set_step_result("content_creation", {"title": "AI Guide", "body": "..."})

        builder = steps[1].context_builder
        result = builder(ctx)

        assert result["content"] == {"title": "AI Guide", "body": "..."}
        assert result["platforms"] == ["linkedin", "twitter"]
        assert result["hashtags"] == ["#AI", "#dev"]

    def test_social_distribution_defaults(self, pipeline):
        """Test social_distribution context builder with defaults."""
        steps = pipeline.define_steps()
        ctx = WorkflowContext(
            workflow_id="test-wf",
            workflow_name="content_distribution_pipeline",
            initial_params={},
        )

        builder = steps[1].context_builder
        result = builder(ctx)

        assert result["platforms"] == ["linkedin", "twitter"]
        assert result["hashtags"] == []
        assert result["schedule_time"] is None

    def test_revenue_tracking_context(self, pipeline):
        """Test revenue_tracking step context builder."""
        steps = pipeline.define_steps()
        ctx = WorkflowContext(
            workflow_id="test-wf",
            workflow_name="content_distribution_pipeline",
            initial_params={
                "tracking_period": "daily",
                "revenue_data": {"source": "gumroad"},
            },
        )
        ctx.set_step_result("content_creation", {"title": "Guide"})
        ctx.set_step_result("social_distribution", {"published": True})

        builder = steps[2].context_builder
        result = builder(ctx)

        assert result["content_result"] == {"title": "Guide"}
        assert result["distribution_result"] == {"published": True}
        assert result["period"] == "daily"
        assert result["revenue_data"] == {"source": "gumroad"}

    def test_revenue_tracking_defaults(self, pipeline):
        """Test revenue_tracking context builder with defaults."""
        steps = pipeline.define_steps()
        ctx = WorkflowContext(
            workflow_id="test-wf",
            workflow_name="content_distribution_pipeline",
            initial_params={},
        )

        builder = steps[2].context_builder
        result = builder(ctx)

        assert result["period"] == "weekly"
        assert result["revenue_data"] == {}


# =============================================================================
# Package Import Tests
# =============================================================================


class TestPipelineImports:
    """Test that the pipeline is properly exported."""

    def test_import_from_orchestration(self):
        """Test importing from orchestration package."""
        from ag3ntwerk.orchestration import ContentDistributionPipelineWorkflow

        assert ContentDistributionPipelineWorkflow is not None

    def test_import_from_workflows_module(self):
        """Test importing from workflows module."""
        from ag3ntwerk.orchestration.workflows import ContentDistributionPipelineWorkflow

        assert ContentDistributionPipelineWorkflow is not None

    def test_in_all_list(self):
        """Test that the workflow is in __all__."""
        import ag3ntwerk.orchestration as orch

        assert "ContentDistributionPipelineWorkflow" in orch.__all__
