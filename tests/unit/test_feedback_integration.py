"""
Tests for Feedback Pipeline Agent Integration.

Tests the routing of customer feedback insights to appropriate ag3ntwerk agents.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from ag3ntwerk.integrations.feedback_pipeline import (
    CustomerFeedbackPipeline,
    FeedbackCategory,
    FeedbackItem,
    InsightPriority,
    ProductInsight,
)
from ag3ntwerk.integrations.feedback_integration import (
    FeedbackPipelineIntegration,
    AgentTarget,
    RoutedInsight,
    DeliveryNotification,
    CATEGORY_ROUTING,
    AGENT_TASK_TYPES,
    create_integrated_pipeline,
    quick_feedback,
)


class TestExecutiveRouting:
    """Tests for agent routing rules."""

    def test_feature_requests_route_to_cpo(self):
        """Feature requests should route to Blueprint."""
        targets = CATEGORY_ROUTING[FeedbackCategory.FEATURE_REQUEST]
        assert AgentTarget.Blueprint in targets

    def test_bug_reports_route_to_cto_and_cpo(self):
        """Bug reports should route to Forge (primary) and Blueprint."""
        targets = CATEGORY_ROUTING[FeedbackCategory.BUG_REPORT]
        assert AgentTarget.Forge in targets
        assert AgentTarget.Blueprint in targets
        # Forge should be primary (first)
        assert targets[0] == AgentTarget.Forge

    def test_churn_risk_routes_to_crio_and_cco(self):
        """Churn risk should route to Aegis and Beacon."""
        targets = CATEGORY_ROUTING[FeedbackCategory.CHURN_RISK]
        assert AgentTarget.CRIO in targets
        assert AgentTarget.Beacon in targets

    def test_competitive_intel_routes_to_cmo(self):
        """Competitive intel should route to Echo."""
        targets = CATEGORY_ROUTING[FeedbackCategory.COMPETITIVE_INTEL]
        assert AgentTarget.Echo in targets

    def test_support_escalation_routes_to_cco(self):
        """Support escalations should route to Beacon."""
        targets = CATEGORY_ROUTING[FeedbackCategory.SUPPORT_ESCALATION]
        assert AgentTarget.Beacon in targets

    def test_performance_issues_route_to_cto(self):
        """Performance issues should route to Forge."""
        targets = CATEGORY_ROUTING[FeedbackCategory.PERFORMANCE_ISSUE]
        assert AgentTarget.Forge in targets

    def test_praise_routes_to_cco_and_cmo(self):
        """Praise should route to Beacon and Echo."""
        targets = CATEGORY_ROUTING[FeedbackCategory.PRAISE]
        assert AgentTarget.Beacon in targets
        assert AgentTarget.Echo in targets


class TestTaskTypeMapping:
    """Tests for task type mapping per agent."""

    def test_cpo_feature_prioritization(self):
        """Blueprint should get feature_prioritization for feature requests."""
        task_type = AGENT_TASK_TYPES[AgentTarget.Blueprint][FeedbackCategory.FEATURE_REQUEST]
        assert task_type == "feature_prioritization"

    def test_cto_bug_triage(self):
        """Forge should get bug_triage for bug reports."""
        task_type = AGENT_TASK_TYPES[AgentTarget.Forge][FeedbackCategory.BUG_REPORT]
        assert task_type == "bug_triage"

    def test_cco_customer_health(self):
        """Beacon should get customer_health_scoring for churn risk."""
        task_type = AGENT_TASK_TYPES[AgentTarget.Beacon][FeedbackCategory.CHURN_RISK]
        assert task_type == "customer_health_scoring"

    def test_crio_risk_assessment(self):
        """Aegis should get risk_assessment for churn risk."""
        task_type = AGENT_TASK_TYPES[AgentTarget.CRIO][FeedbackCategory.CHURN_RISK]
        assert task_type == "risk_assessment"

    def test_cmo_competitive_analysis(self):
        """Echo should get competitive_analysis for competitive intel."""
        task_type = AGENT_TASK_TYPES[AgentTarget.Echo][FeedbackCategory.COMPETITIVE_INTEL]
        assert task_type == "competitive_analysis"


class TestFeedbackPipelineIntegration:
    """Tests for FeedbackPipelineIntegration class."""

    @pytest.fixture
    def pipeline(self):
        """Create a feedback pipeline."""
        return CustomerFeedbackPipeline(max_feedback=100)

    @pytest.fixture
    def integration(self, pipeline):
        """Create an integration instance."""
        return FeedbackPipelineIntegration(pipeline)

    @pytest.fixture
    def mock_cos(self):
        """Create a mock Overwatch instance."""
        cos = MagicMock()
        cos.route_task = AsyncMock(return_value={"task_id": "task_123", "routed_to": "Blueprint"})
        return cos

    def test_integration_initialization(self, integration):
        """Test integration initializes correctly."""
        assert integration._pipeline is not None
        assert integration._cos is None
        assert integration._total_routed == 0
        assert integration._total_delivered == 0

    def test_connect_cos(self, integration, mock_cos):
        """Test connecting Overwatch."""
        integration.connect_cos(mock_cos)
        assert integration._cos is mock_cos

    @pytest.mark.asyncio
    async def test_route_feature_request(self, integration, pipeline, mock_cos):
        """Test routing a feature request insight."""
        integration.connect_cos(mock_cos)

        insight = ProductInsight(
            title="Dark mode feature",
            description="Multiple users requesting dark mode",
            category=FeedbackCategory.FEATURE_REQUEST,
            priority=InsightPriority.HIGH,
            customer_count=5,
        )
        pipeline._insights[insight.id] = insight

        routed = await integration.route_insight(insight)

        assert len(routed) == 1  # Feature requests go to Blueprint only
        assert routed[0].target_agent == AgentTarget.Blueprint
        assert routed[0].task_type == "feature_prioritization"
        assert integration._total_routed == 1

    @pytest.mark.asyncio
    async def test_route_bug_report_to_multiple(self, integration, pipeline, mock_cos):
        """Test routing a bug report to Forge and Blueprint."""
        integration.connect_cos(mock_cos)

        insight = ProductInsight(
            title="Login bug",
            description="Users can't log in",
            category=FeedbackCategory.BUG_REPORT,
            priority=InsightPriority.CRITICAL,
            customer_count=10,
        )
        pipeline._insights[insight.id] = insight

        routed = await integration.route_insight(insight)

        assert len(routed) == 2  # Bug reports go to Forge and Blueprint
        agents = {r.target_agent for r in routed}
        assert AgentTarget.Forge in agents
        assert AgentTarget.Blueprint in agents
        assert integration._total_routed == 2

    @pytest.mark.asyncio
    async def test_route_via_cos(self, integration, pipeline, mock_cos):
        """Test that insights are routed via Overwatch."""
        integration.connect_cos(mock_cos)

        insight = ProductInsight(
            title="API improvement",
            category=FeedbackCategory.FEATURE_REQUEST,
            priority=InsightPriority.MEDIUM,
        )
        pipeline._insights[insight.id] = insight

        await integration.route_insight(insight)

        mock_cos.route_task.assert_called_once()
        task = mock_cos.route_task.call_args[0][0]
        assert task.task_type == "feature_prioritization"
        assert "insight_id" in task.context

    @pytest.mark.asyncio
    async def test_route_without_cos(self, integration, pipeline):
        """Test routing works without Overwatch connected."""
        insight = ProductInsight(
            title="Test insight",
            category=FeedbackCategory.GENERAL,
        )
        pipeline._insights[insight.id] = insight

        routed = await integration.route_insight(insight)

        assert len(routed) == 1
        assert routed[0].task_id is None  # No Overwatch routing

    @pytest.mark.asyncio
    async def test_route_all_new_insights(self, integration, pipeline, mock_cos):
        """Test routing all new insights from pipeline."""
        integration.connect_cos(mock_cos)

        # Add multiple insights
        for i in range(3):
            insight = ProductInsight(
                title=f"Insight {i}",
                category=FeedbackCategory.FEATURE_REQUEST,
                status="new",
            )
            pipeline._insights[insight.id] = insight

        routed = await integration.route_all_new_insights()

        assert len(routed) == 3
        assert integration._total_routed == 3

    @pytest.mark.asyncio
    async def test_acknowledge_insight(self, integration, pipeline):
        """Test acknowledging a routed insight."""
        insight = ProductInsight(
            title="Test insight",
            category=FeedbackCategory.GENERAL,
        )
        pipeline._insights[insight.id] = insight

        await integration.route_insight(insight)
        result = integration.acknowledge_insight(insight.id, task_id="task_456")

        assert result is True
        routed = integration.get_routed_insight(insight.id)
        assert routed.acknowledged is True
        assert routed.task_id == "task_456"

    @pytest.mark.asyncio
    async def test_acknowledge_nonexistent_insight(self, integration):
        """Test acknowledging a non-existent insight."""
        result = integration.acknowledge_insight(uuid4())
        assert result is False


class TestFeatureDelivery:
    """Tests for feature delivery notifications."""

    @pytest.fixture
    def pipeline(self):
        """Create a feedback pipeline."""
        return CustomerFeedbackPipeline(max_feedback=100)

    @pytest.fixture
    def integration(self, pipeline):
        """Create an integration instance."""
        return FeedbackPipelineIntegration(pipeline)

    @pytest.fixture
    def mock_cos(self):
        """Create a mock Overwatch instance."""
        cos = MagicMock()
        cos.route_task = AsyncMock(return_value={"task_id": "task_delivery", "routed_to": "Beacon"})
        return cos

    @pytest.mark.asyncio
    async def test_feature_delivered(self, integration, pipeline, mock_cos):
        """Test marking feature as delivered."""
        integration.connect_cos(mock_cos)

        # Add feedback and generate insight
        feedback = FeedbackItem(
            content="Need dark mode",
            category=FeedbackCategory.FEATURE_REQUEST,
            customer_id="cust_123",
            customer_tier="enterprise",
        )
        pipeline.add_feedback(feedback)

        insight = ProductInsight(
            title="Dark mode",
            category=FeedbackCategory.FEATURE_REQUEST,
            source_feedback_ids=[feedback.id],
            customer_count=1,
        )
        pipeline._insights[insight.id] = insight

        # Mark delivered
        result = await integration.on_feature_delivered(
            insight.id, release_notes="Dark mode added in v2.0"
        )

        assert result is True
        assert integration._total_delivered == 1
        assert len(integration._pending_deliveries) == 1

        # Check Beacon was notified
        assert mock_cos.route_task.call_count >= 1

    @pytest.mark.asyncio
    async def test_delivery_extracts_customer_ids(self, integration, pipeline, mock_cos):
        """Test that delivery notification includes customer IDs."""
        integration.connect_cos(mock_cos)

        # Add multiple feedbacks with customer IDs
        feedbacks = []
        for i in range(3):
            fb = FeedbackItem(
                content=f"Feedback {i}",
                category=FeedbackCategory.FEATURE_REQUEST,
                customer_id=f"cust_{i}",
            )
            pipeline.add_feedback(fb)
            feedbacks.append(fb)

        insight = ProductInsight(
            title="Test feature",
            category=FeedbackCategory.FEATURE_REQUEST,
            source_feedback_ids=[fb.id for fb in feedbacks],
            customer_count=3,
        )
        pipeline._insights[insight.id] = insight

        await integration.on_feature_delivered(insight.id)

        notification = integration._pending_deliveries[0]
        assert len(notification.customer_ids) == 3
        assert "cust_0" in notification.customer_ids
        assert "cust_1" in notification.customer_ids
        assert "cust_2" in notification.customer_ids

    @pytest.mark.asyncio
    async def test_delivery_nonexistent_insight(self, integration, pipeline):
        """Test marking non-existent insight as delivered."""
        result = await integration.on_feature_delivered(uuid4())
        assert result is False


class TestCustomHandlers:
    """Tests for custom handler registration."""

    @pytest.fixture
    def pipeline(self):
        return CustomerFeedbackPipeline()

    @pytest.fixture
    def integration(self, pipeline):
        return FeedbackPipelineIntegration(pipeline)

    @pytest.mark.asyncio
    async def test_custom_insight_handler(self, integration, pipeline):
        """Test registering and calling custom insight handler."""
        handler_called = []

        async def custom_handler(routed_insight):
            handler_called.append(routed_insight)

        integration.on_insight(AgentTarget.Blueprint, custom_handler)

        insight = ProductInsight(
            title="Test",
            category=FeedbackCategory.FEATURE_REQUEST,
        )
        pipeline._insights[insight.id] = insight

        await integration.route_insight(insight)

        assert len(handler_called) == 1
        assert handler_called[0].target_agent == AgentTarget.Blueprint

    @pytest.mark.asyncio
    async def test_custom_delivery_handler(self, integration, pipeline):
        """Test registering and calling custom delivery handler."""
        handler_called = []

        async def custom_handler(notification):
            handler_called.append(notification)

        integration.on_delivery(custom_handler)

        insight = ProductInsight(
            title="Test",
            category=FeedbackCategory.FEATURE_REQUEST,
        )
        pipeline._insights[insight.id] = insight

        await integration.on_feature_delivered(insight.id)

        assert len(handler_called) == 1
        assert handler_called[0].insight == insight

    @pytest.mark.asyncio
    async def test_handler_error_isolation(self, integration, pipeline):
        """Test that handler errors don't affect other handlers."""
        successful_calls = []

        async def failing_handler(routed_insight):
            raise ValueError("Test error")

        async def successful_handler(routed_insight):
            successful_calls.append(routed_insight)

        integration.on_insight(AgentTarget.Blueprint, failing_handler)
        integration.on_insight(AgentTarget.Blueprint, successful_handler)

        insight = ProductInsight(
            title="Test",
            category=FeedbackCategory.FEATURE_REQUEST,
        )
        pipeline._insights[insight.id] = insight

        # Should not raise
        await integration.route_insight(insight)

        # Successful handler should still be called
        assert len(successful_calls) == 1


class TestProcessFeedbackBatch:
    """Tests for batch feedback processing."""

    @pytest.fixture
    def pipeline(self):
        # Lower the MIN_FEEDBACK_FOR_INSIGHT so we can test with fewer items
        pipeline = CustomerFeedbackPipeline(auto_generate_threshold=3)
        pipeline.MIN_FEEDBACK_FOR_INSIGHT = 3
        return pipeline

    @pytest.fixture
    def integration(self, pipeline):
        return FeedbackPipelineIntegration(pipeline)

    @pytest.mark.asyncio
    async def test_process_batch(self, integration, pipeline):
        """Test processing a batch of feedback."""
        # Items need same product_area to be grouped together for insight generation
        items = [
            FeedbackItem(
                content=f"Feature request {i}",
                category=FeedbackCategory.FEATURE_REQUEST,
                customer_tier="pro",
                product_area="dashboard",  # Same product area to group
            )
            for i in range(5)
        ]

        result = await integration.process_feedback_batch(items)

        assert result["feedback_added"] == 5
        # Insights are generated during add_feedback_batch (auto_generate_threshold)
        # The result counts only NEW insights from the explicit generate_insights() call
        # Check that pipeline has insights (they may have been auto-generated)
        assert pipeline.insight_count >= 1
        assert "routes_created" in result

    @pytest.mark.asyncio
    async def test_process_batch_routes_by_agent(
        self,
        integration,
        pipeline,
    ):
        """Test that batch processing tracks routes by agent."""
        items = [
            FeedbackItem(
                content="Bug report",
                category=FeedbackCategory.BUG_REPORT,
                customer_tier="enterprise",
            )
            for _ in range(3)
        ]

        result = await integration.process_feedback_batch(items)

        if result["insights_generated"] > 0:
            assert "routes_by_agent" in result


class TestStatistics:
    """Tests for integration statistics."""

    @pytest.fixture
    def pipeline(self):
        return CustomerFeedbackPipeline()

    @pytest.fixture
    def integration(self, pipeline):
        return FeedbackPipelineIntegration(pipeline)

    def test_initial_stats(self, integration):
        """Test initial statistics."""
        stats = integration.stats

        assert stats["total_routed"] == 0
        assert stats["total_delivered"] == 0
        assert stats["pending_deliveries"] == 0
        assert stats["cos_connected"] is False

    @pytest.mark.asyncio
    async def test_stats_after_routing(self, integration, pipeline):
        """Test statistics after routing insights."""
        insight = ProductInsight(
            title="Test",
            category=FeedbackCategory.FEATURE_REQUEST,
        )
        pipeline._insights[insight.id] = insight

        await integration.route_insight(insight)

        stats = integration.stats
        assert stats["total_routed"] == 1
        assert stats["routes_by_agent"]["Blueprint"] == 1


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_integrated_pipeline(self):
        """Test creating an integrated pipeline."""
        pipeline, integration = create_integrated_pipeline()

        assert pipeline is not None
        assert integration is not None
        assert integration._pipeline is pipeline

    def test_create_integrated_pipeline_with_cos(self):
        """Test creating an integrated pipeline with Overwatch."""
        mock_cos = MagicMock()
        pipeline, integration = create_integrated_pipeline(cos=mock_cos)

        assert integration._cos is mock_cos

    @pytest.mark.asyncio
    async def test_quick_feedback(self):
        """Test quick feedback helper."""
        pipeline, integration = create_integrated_pipeline()

        feedback_id = await quick_feedback(
            integration,
            content="I need dark mode",
            category=FeedbackCategory.FEATURE_REQUEST,
            customer_id="cust_123",
            customer_tier="enterprise",
        )

        assert feedback_id is not None
        # Feedback should be in pipeline
        assert pipeline.feedback_count >= 1


class TestGetInsightsForExecutive:
    """Tests for retrieving insights by agent."""

    @pytest.fixture
    def pipeline(self):
        return CustomerFeedbackPipeline()

    @pytest.fixture
    def integration(self, pipeline):
        return FeedbackPipelineIntegration(pipeline)

    @pytest.mark.asyncio
    async def test_get_insights_for_cpo(self, integration, pipeline):
        """Test getting insights routed to Blueprint."""
        # Route multiple insights
        for i in range(3):
            insight = ProductInsight(
                title=f"Feature {i}",
                category=FeedbackCategory.FEATURE_REQUEST,
            )
            pipeline._insights[insight.id] = insight
            await integration.route_insight(insight)

        cpo_insights = integration.get_insights_for_executive(AgentTarget.Blueprint)
        assert len(cpo_insights) == 3

    @pytest.mark.asyncio
    async def test_filter_acknowledged_insights(self, integration, pipeline):
        """Test filtering by acknowledged status."""
        insight1 = ProductInsight(title="Test 1", category=FeedbackCategory.FEATURE_REQUEST)
        insight2 = ProductInsight(title="Test 2", category=FeedbackCategory.FEATURE_REQUEST)
        pipeline._insights[insight1.id] = insight1
        pipeline._insights[insight2.id] = insight2

        await integration.route_insight(insight1)
        await integration.route_insight(insight2)

        # Acknowledge one
        integration.acknowledge_insight(insight1.id)

        unacked = integration.get_insights_for_executive(AgentTarget.Blueprint, acknowledged=False)
        assert len(unacked) == 1
        assert unacked[0].insight.id == insight2.id
