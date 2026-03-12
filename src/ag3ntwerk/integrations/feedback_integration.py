"""
Feedback Pipeline Agent Integration.

Routes customer feedback insights to the appropriate ag3ntwerk agents:
- Blueprint (Blueprint): Feature requests, product improvements, roadmap input
- Beacon (Beacon): Customer communication, delivery notifications, loop closing
- Forge (Forge): Bug reports, technical issues, performance problems
- Aegis (Aegis): Churn risk signals, customer health alerts
- Echo (Echo): Competitive intelligence, market positioning

This module bridges the CustomerFeedbackPipeline with the Overwatch routing system.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
from uuid import UUID

from ag3ntwerk.integrations.feedback_pipeline import (
    CustomerFeedbackPipeline,
    FeedbackCategory,
    FeedbackItem,
    InsightPriority,
    ProductInsight,
)

logger = logging.getLogger(__name__)


class AgentTarget(str, Enum):
    """Target agents for feedback routing."""

    Blueprint = "Blueprint"  # Blueprint - Product direction
    Beacon = "Beacon"  # Beacon - Customer relationships
    Forge = "Forge"  # Forge - Technology and bugs
    CRIO = "Aegis"  # Aegis - Risk management
    Echo = "Echo"  # Echo - Marketing and competitive
    COS = "Overwatch"  # Overwatch - General routing


# Routing rules: category -> primary agent (with fallbacks)
CATEGORY_ROUTING: Dict[FeedbackCategory, List[AgentTarget]] = {
    FeedbackCategory.FEATURE_REQUEST: [AgentTarget.Blueprint],
    FeedbackCategory.BUG_REPORT: [AgentTarget.Forge, AgentTarget.Blueprint],
    FeedbackCategory.USABILITY_ISSUE: [AgentTarget.Blueprint, AgentTarget.Forge],
    FeedbackCategory.PERFORMANCE_ISSUE: [AgentTarget.Forge],
    FeedbackCategory.PRAISE: [AgentTarget.Beacon, AgentTarget.Echo],
    FeedbackCategory.CHURN_RISK: [AgentTarget.CRIO, AgentTarget.Beacon],
    FeedbackCategory.SUPPORT_ESCALATION: [AgentTarget.Beacon],
    FeedbackCategory.COMPETITIVE_INTEL: [AgentTarget.Echo, AgentTarget.Blueprint],
    FeedbackCategory.GENERAL: [AgentTarget.COS],
}

# Task type mapping for each agent
AGENT_TASK_TYPES: Dict[AgentTarget, Dict[FeedbackCategory, str]] = {
    AgentTarget.Blueprint: {
        FeedbackCategory.FEATURE_REQUEST: "feature_prioritization",
        FeedbackCategory.BUG_REPORT: "backlog_grooming",
        FeedbackCategory.USABILITY_ISSUE: "requirements_gathering",
        FeedbackCategory.COMPETITIVE_INTEL: "competitive_analysis",
        FeedbackCategory.GENERAL: "product_spec",
    },
    AgentTarget.Forge: {
        FeedbackCategory.BUG_REPORT: "bug_triage",
        FeedbackCategory.PERFORMANCE_ISSUE: "performance_analysis",
        FeedbackCategory.USABILITY_ISSUE: "technical_assessment",
    },
    AgentTarget.Beacon: {
        FeedbackCategory.PRAISE: "customer_advocacy",
        FeedbackCategory.CHURN_RISK: "customer_health_scoring",
        FeedbackCategory.SUPPORT_ESCALATION: "support_escalation",
        FeedbackCategory.GENERAL: "feedback_analysis",
    },
    AgentTarget.CRIO: {
        FeedbackCategory.CHURN_RISK: "risk_assessment",
        FeedbackCategory.SUPPORT_ESCALATION: "risk_assessment",
    },
    AgentTarget.Echo: {
        FeedbackCategory.COMPETITIVE_INTEL: "competitive_analysis",
        FeedbackCategory.PRAISE: "customer_testimonial",
    },
}


@dataclass
class RoutedInsight:
    """An insight routed to an agent."""

    insight: ProductInsight
    target_agent: AgentTarget
    task_type: str
    routed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    task_id: Optional[str] = None


@dataclass
class DeliveryNotification:
    """Notification to Beacon about a delivered feature."""

    insight: ProductInsight
    customer_ids: List[str]
    release_notes: Optional[str]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent: bool = False


# Type alias for async handlers
InsightHandler = Callable[[RoutedInsight], Coroutine[Any, Any, None]]
DeliveryHandler = Callable[[DeliveryNotification], Coroutine[Any, Any, None]]


class FeedbackPipelineIntegration:
    """
    Integrates CustomerFeedbackPipeline with ag3ntwerk agents.

    This class:
    - Monitors the feedback pipeline for new insights
    - Routes insights to appropriate agents based on category
    - Notifies Beacon when features are delivered
    - Tracks routing status and acknowledgments

    Usage:
        from ag3ntwerk.api.state import state

        integration = FeedbackPipelineIntegration(pipeline)
        integration.connect_cos(state.coo)

        # Pipeline generates insights automatically
        # Integration routes them to agents

        # When feature delivered:
        integration.on_feature_delivered(insight_id, "Added dark mode")
    """

    def __init__(
        self,
        pipeline: CustomerFeedbackPipeline,
        auto_route: bool = True,
    ):
        """
        Initialize the integration.

        Args:
            pipeline: The feedback pipeline to integrate
            auto_route: Automatically route new insights
        """
        self._pipeline = pipeline
        self._auto_route = auto_route
        self._cos = None  # Overwatch instance for routing

        # Routed insights tracking
        self._routed_insights: Dict[UUID, RoutedInsight] = {}
        self._pending_deliveries: List[DeliveryNotification] = []

        # Custom handlers
        self._insight_handlers: Dict[AgentTarget, List[InsightHandler]] = {
            target: [] for target in AgentTarget
        }
        self._delivery_handlers: List[DeliveryHandler] = []

        # Statistics
        self._total_routed = 0
        self._total_delivered = 0
        self._routes_by_agent: Dict[str, int] = {}

        logger.info("FeedbackPipelineIntegration initialized")

    @property
    def stats(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "total_routed": self._total_routed,
            "total_delivered": self._total_delivered,
            "routes_by_agent": self._routes_by_agent,
            "pending_deliveries": len(self._pending_deliveries),
            "active_insights": len(
                [r for r in self._routed_insights.values() if not r.acknowledged]
            ),
            "cos_connected": self._cos is not None,
        }

    def connect_cos(self, cos: Any) -> None:
        """
        Connect Overwatch (Overwatch) for task routing.

        Args:
            cos: The Overwatch instance to use for routing tasks
        """
        self._cos = cos
        logger.info("Connected Overwatch (Overwatch) for feedback routing")

    def on_insight(
        self,
        target: AgentTarget,
        handler: InsightHandler,
    ) -> None:
        """
        Register a custom handler for insights routed to an agent.

        Args:
            target: Agent to handle
            handler: Async handler function
        """
        self._insight_handlers[target].append(handler)

    def on_delivery(self, handler: DeliveryHandler) -> None:
        """
        Register a handler for delivery notifications.

        Args:
            handler: Async handler function
        """
        self._delivery_handlers.append(handler)

    async def route_insight(self, insight: ProductInsight) -> List[RoutedInsight]:
        """
        Route an insight to appropriate agents.

        Args:
            insight: The insight to route

        Returns:
            List of routed insights (one per target agent)
        """
        targets = CATEGORY_ROUTING.get(insight.category, [AgentTarget.COS])

        routed = []
        for target in targets:
            task_type = AGENT_TASK_TYPES.get(target, {}).get(
                insight.category, "feedback_review"
            )

            routed_insight = RoutedInsight(
                insight=insight,
                target_agent=target,
                task_type=task_type,
            )

            self._routed_insights[insight.id] = routed_insight
            routed.append(routed_insight)

            # Route via Overwatch if connected
            if self._cos:
                await self._route_via_cos(routed_insight)

            # Call custom handlers
            await self._call_insight_handlers(target, routed_insight)

            # Update stats
            self._total_routed += 1
            self._routes_by_agent[target.value] = (
                self._routes_by_agent.get(target.value, 0) + 1
            )

            logger.info(f"Routed insight {insight.id} to {target.value}: {task_type}")

        return routed

    async def route_all_new_insights(self) -> List[RoutedInsight]:
        """
        Route all new (unrouted) insights from the pipeline.

        Returns:
            List of newly routed insights
        """
        all_routed = []

        for insight in self._pipeline.get_insights(status="new"):
            if insight.id not in self._routed_insights:
                routed = await self.route_insight(insight)
                all_routed.extend(routed)

        return all_routed

    async def on_feature_delivered(
        self,
        insight_id: UUID,
        release_notes: Optional[str] = None,
    ) -> bool:
        """
        Handle feature delivery and notify Beacon.

        Args:
            insight_id: The delivered insight
            release_notes: What was shipped

        Returns:
            True if notification sent
        """
        # Mark delivered in pipeline
        self._pipeline.mark_delivered(insight_id, release_notes)

        insight = self._pipeline.get_insight(insight_id)
        if not insight:
            return False

        # Get customer IDs from source feedback
        customer_ids = []
        for fb in self._pipeline.get_feedback_for_insight(insight_id):
            if fb.customer_id:
                customer_ids.append(fb.customer_id)

        # Create delivery notification
        notification = DeliveryNotification(
            insight=insight,
            customer_ids=list(set(customer_ids)),  # Dedupe
            release_notes=release_notes,
        )

        self._pending_deliveries.append(notification)
        self._total_delivered += 1

        # Notify Beacon
        await self._notify_cco_delivery(notification)

        # Call custom handlers
        await self._call_delivery_handlers(notification)

        logger.info(
            f"Feature delivered: insight {insight_id}, " f"notifying {len(customer_ids)} customers"
        )

        return True

    async def process_feedback_batch(
        self,
        items: List[FeedbackItem],
    ) -> Dict[str, Any]:
        """
        Process a batch of feedback items through the full pipeline.

        Args:
            items: Feedback items to process

        Returns:
            Processing results
        """
        # Add to pipeline
        feedback_ids = self._pipeline.add_feedback_batch(items)

        # Generate insights
        new_insights = self._pipeline.generate_insights()

        # Route insights
        routed = []
        for insight in new_insights:
            routed.extend(await self.route_insight(insight))

        return {
            "feedback_added": len(feedback_ids),
            "insights_generated": len(new_insights),
            "routes_created": len(routed),
            "routes_by_agent": {
                target.value: len([r for r in routed if r.target_agent == target])
                for target in AgentTarget
                if any(r.target_agent == target for r in routed)
            },
        }

    def get_routed_insight(self, insight_id: UUID) -> Optional[RoutedInsight]:
        """Get a routed insight by ID."""
        return self._routed_insights.get(insight_id)

    def get_insights_for_executive(
        self,
        target: AgentTarget,
        acknowledged: Optional[bool] = None,
    ) -> List[RoutedInsight]:
        """Get insights routed to a specific agent."""
        insights = [r for r in self._routed_insights.values() if r.target_agent == target]

        if acknowledged is not None:
            insights = [i for i in insights if i.acknowledged == acknowledged]

        return sorted(insights, key=lambda x: x.routed_at, reverse=True)

    def acknowledge_insight(self, insight_id: UUID, task_id: Optional[str] = None) -> bool:
        """Mark an insight as acknowledged by the target agent."""
        routed = self._routed_insights.get(insight_id)
        if not routed:
            return False

        routed.acknowledged = True
        routed.task_id = task_id

        logger.info(f"Insight {insight_id} acknowledged by {routed.target_agent.value}")
        return True

    # Private methods

    async def _route_via_cos(self, routed_insight: RoutedInsight) -> None:
        """Route insight via Overwatch task routing."""
        if not self._cos:
            return

        try:
            from ag3ntwerk.core.base import Task

            task = Task(
                task_type=routed_insight.task_type,
                description=self._build_task_description(routed_insight),
                context={
                    "insight_id": str(routed_insight.insight.id),
                    "category": routed_insight.insight.category.value,
                    "priority": routed_insight.insight.priority.value,
                    "customer_count": routed_insight.insight.customer_count,
                    "suggested_action": routed_insight.insight.suggested_action,
                    "source": "feedback_pipeline",
                },
                priority=self._priority_to_string(routed_insight.insight.priority),
            )

            result = await self._cos.route_task(task)

            if isinstance(result, dict) and result.get("task_id"):
                routed_insight.task_id = result["task_id"]

            logger.debug(f"Overwatch routed task: {result}")

        except Exception as e:
            logger.warning(f"Failed to route via Overwatch: {e}")

    async def _notify_cco_delivery(self, notification: DeliveryNotification) -> None:
        """Notify Beacon about feature delivery."""
        if not self._cos:
            logger.debug("Beacon notification skipped: Overwatch not connected")
            return

        try:
            from ag3ntwerk.core.base import Task

            task = Task(
                task_type="customer_outreach",
                description=(
                    f"Feature delivered: {notification.insight.title}\n"
                    f"Close the loop with {len(notification.customer_ids)} customers "
                    f"who requested this feature."
                ),
                context={
                    "insight_id": str(notification.insight.id),
                    "customer_ids": notification.customer_ids,
                    "release_notes": notification.release_notes,
                    "customer_count": len(notification.customer_ids),
                    "source": "feedback_pipeline_delivery",
                },
                priority="high",
            )

            result = await self._cos.route_task(task)
            notification.sent = True

            logger.info(f"Beacon notified of delivery: insight {notification.insight.id}")

        except Exception as e:
            logger.warning(f"Failed to notify Beacon: {e}")

    async def _call_insight_handlers(
        self,
        target: AgentTarget,
        routed_insight: RoutedInsight,
    ) -> None:
        """Call registered handlers for insight routing."""
        handlers = self._insight_handlers.get(target, [])
        if not handlers:
            return

        results = await asyncio.gather(
            *[self._safe_call_handler(h, routed_insight) for h in handlers],
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Insight handler error: {result}")

    async def _call_delivery_handlers(
        self,
        notification: DeliveryNotification,
    ) -> None:
        """Call registered handlers for delivery notifications."""
        if not self._delivery_handlers:
            return

        results = await asyncio.gather(
            *[self._safe_call_handler(h, notification) for h in self._delivery_handlers],
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Delivery handler error: {result}")

    async def _safe_call_handler(self, handler: Callable, *args) -> None:
        """Safely call a handler with error handling."""
        try:
            await handler(*args)
        except Exception as e:
            logger.error(f"Handler {handler.__name__} failed: {e}")
            raise

    def _build_task_description(self, routed_insight: RoutedInsight) -> str:
        """Build task description for Overwatch routing."""
        insight = routed_insight.insight

        lines = [
            f"[{insight.priority.value.upper()}] {insight.title}",
            "",
            insight.description,
            "",
            f"Category: {insight.category.value}",
            f"Customer count: {insight.customer_count}",
        ]

        if insight.revenue_impact:
            lines.append(f"Estimated revenue impact: ${insight.revenue_impact:,.0f}")

        if insight.suggested_action:
            lines.append(f"\nSuggested action: {insight.suggested_action}")

        return "\n".join(lines)

    def _priority_to_string(self, priority: InsightPriority) -> str:
        """Convert InsightPriority to task priority string."""
        mapping = {
            InsightPriority.CRITICAL: "critical",
            InsightPriority.HIGH: "high",
            InsightPriority.MEDIUM: "medium",
            InsightPriority.LOW: "low",
        }
        return mapping.get(priority, "medium")


# Convenience functions for common operations


def create_integrated_pipeline(
    cos: Optional[Any] = None,
    max_feedback: int = 10000,
) -> tuple[CustomerFeedbackPipeline, FeedbackPipelineIntegration]:
    """
    Create a feedback pipeline with agent integration.

    Args:
        cos: Optional Overwatch instance for routing
        max_feedback: Maximum feedback items to retain

    Returns:
        Tuple of (pipeline, integration)
    """
    pipeline = CustomerFeedbackPipeline(max_feedback=max_feedback)
    integration = FeedbackPipelineIntegration(pipeline)

    if cos:
        integration.connect_cos(cos)

    return pipeline, integration


async def quick_feedback(
    integration: FeedbackPipelineIntegration,
    content: str,
    category: FeedbackCategory = FeedbackCategory.GENERAL,
    customer_id: Optional[str] = None,
    customer_tier: Optional[str] = None,
    source: str = "direct",
) -> UUID:
    """
    Quickly add feedback and trigger processing.

    Args:
        integration: The integration instance
        content: Feedback content
        category: Feedback category
        customer_id: Optional customer ID
        customer_tier: Optional customer tier
        source: Feedback source

    Returns:
        Feedback ID
    """
    feedback = FeedbackItem(
        content=content,
        category=category,
        customer_id=customer_id,
        customer_tier=customer_tier,
        source=source,
    )

    result = await integration.process_feedback_batch([feedback])
    return feedback.id
