"""
Customer Feedback Pipeline - Beacon to Blueprint integration.

This module provides a bidirectional pipeline between the Chief Customer
Officer (Beacon/Beacon) and Blueprint (Blueprint/Blueprint) for:

- Routing customer feedback to product planning
- Translating customer pain points to feature requests
- Prioritizing features based on customer impact
- Closing the loop on delivered features

The pipeline ensures voice-of-customer data flows into product decisions.
"""

import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class FeedbackCategory(Enum):
    """Categories of customer feedback."""

    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    USABILITY_ISSUE = "usability_issue"
    PERFORMANCE_ISSUE = "performance_issue"
    PRAISE = "praise"
    CHURN_RISK = "churn_risk"
    SUPPORT_ESCALATION = "support_escalation"
    COMPETITIVE_INTEL = "competitive_intel"
    GENERAL = "general"


class InsightPriority(Enum):
    """Priority levels for product insights."""

    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Address in current sprint/cycle
    MEDIUM = "medium"  # Include in near-term planning
    LOW = "low"  # Nice to have / future consideration


@dataclass
class FeedbackItem:
    """A single piece of customer feedback."""

    id: UUID = field(default_factory=uuid4)
    source: str = "unknown"  # support, survey, social, direct, etc.
    customer_id: Optional[str] = None
    customer_tier: Optional[str] = None  # enterprise, pro, free, etc.
    category: FeedbackCategory = FeedbackCategory.GENERAL
    content: str = ""
    sentiment_score: float = 0.5  # 0-1, where 1 is positive
    urgency: int = 5  # 1-10, where 10 is most urgent
    product_area: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "source": self.source,
            "customer_id": self.customer_id,
            "customer_tier": self.customer_tier,
            "category": self.category.value,
            "content": self.content,
            "sentiment_score": self.sentiment_score,
            "urgency": self.urgency,
            "product_area": self.product_area,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ProductInsight:
    """An actionable insight derived from customer feedback."""

    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    priority: InsightPriority = InsightPriority.MEDIUM
    category: FeedbackCategory = FeedbackCategory.FEATURE_REQUEST
    source_feedback_ids: List[UUID] = field(default_factory=list)
    customer_count: int = 0
    revenue_impact: Optional[float] = None  # Estimated impact
    product_area: Optional[str] = None
    suggested_action: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "new"  # new, acknowledged, planned, in_progress, delivered
    cpo_notes: Optional[str] = None
    delivered_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "category": self.category.value,
            "source_feedback_ids": [str(fid) for fid in self.source_feedback_ids],
            "customer_count": self.customer_count,
            "revenue_impact": self.revenue_impact,
            "product_area": self.product_area,
            "suggested_action": self.suggested_action,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "cpo_notes": self.cpo_notes,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
        }


class CustomerFeedbackPipeline:
    """
    Pipeline for routing customer feedback from Beacon to Blueprint.

    Features:
    - Aggregate and categorize feedback from Beacon
    - Generate actionable product insights
    - Route insights to Blueprint for product planning
    - Track insight status through product lifecycle
    - Close the loop when features are delivered

    Usage:
        pipeline = CustomerFeedbackPipeline()

        # Beacon adds feedback
        pipeline.add_feedback(FeedbackItem(
            source="support",
            category=FeedbackCategory.FEATURE_REQUEST,
            content="Need dark mode support",
            customer_tier="enterprise",
        ))

        # Generate insights for Blueprint
        insights = pipeline.generate_insights()

        # Blueprint acknowledges and plans
        pipeline.acknowledge_insight(insight_id, "Planned for Q2")

        # When delivered, close the loop
        pipeline.mark_delivered(insight_id)
    """

    # Threshold for creating insights from feedback
    MIN_FEEDBACK_FOR_INSIGHT = 3

    # Weight multipliers for customer tiers
    TIER_WEIGHTS = {
        "enterprise": 3.0,
        "pro": 2.0,
        "business": 1.5,
        "starter": 1.0,
        "free": 0.5,
    }

    # Category to priority mapping defaults
    CATEGORY_PRIORITY_MAP = {
        FeedbackCategory.BUG_REPORT: InsightPriority.HIGH,
        FeedbackCategory.PERFORMANCE_ISSUE: InsightPriority.HIGH,
        FeedbackCategory.CHURN_RISK: InsightPriority.CRITICAL,
        FeedbackCategory.SUPPORT_ESCALATION: InsightPriority.HIGH,
        FeedbackCategory.FEATURE_REQUEST: InsightPriority.MEDIUM,
        FeedbackCategory.USABILITY_ISSUE: InsightPriority.MEDIUM,
        FeedbackCategory.COMPETITIVE_INTEL: InsightPriority.LOW,
        FeedbackCategory.PRAISE: InsightPriority.LOW,
        FeedbackCategory.GENERAL: InsightPriority.LOW,
    }

    def __init__(
        self,
        cco: Optional[Any] = None,
        cpo: Optional[Any] = None,
        max_feedback: int = 10000,
        auto_generate_threshold: int = 10,
    ):
        """
        Initialize the feedback pipeline.

        Args:
            cco: Optional Beacon instance for callbacks
            cpo: Optional Blueprint instance for callbacks
            max_feedback: Maximum feedback items to retain
            auto_generate_threshold: Generate insights after this many new items
        """
        self._cco = cco
        self._cpo = cpo
        self._max_feedback = max_feedback
        self._auto_generate_threshold = auto_generate_threshold

        # Feedback storage (OrderedDict for LRU-like behavior)
        self._feedback: OrderedDict[UUID, FeedbackItem] = OrderedDict()

        # Generated insights
        self._insights: Dict[UUID, ProductInsight] = {}

        # Tracking
        self._feedback_since_generate = 0
        self._total_feedback_processed = 0
        self._total_insights_generated = 0

        logger.info("CustomerFeedbackPipeline initialized")

    @property
    def feedback_count(self) -> int:
        """Get total feedback items."""
        return len(self._feedback)

    @property
    def insight_count(self) -> int:
        """Get total insights."""
        return len(self._insights)

    @property
    def stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        insights_by_status = {}
        insights_by_priority = {}
        for insight in self._insights.values():
            insights_by_status[insight.status] = insights_by_status.get(insight.status, 0) + 1
            insights_by_priority[insight.priority.value] = (
                insights_by_priority.get(insight.priority.value, 0) + 1
            )

        return {
            "feedback_count": len(self._feedback),
            "insight_count": len(self._insights),
            "total_feedback_processed": self._total_feedback_processed,
            "total_insights_generated": self._total_insights_generated,
            "feedback_since_generate": self._feedback_since_generate,
            "insights_by_status": insights_by_status,
            "insights_by_priority": insights_by_priority,
            "cco_connected": self._cco is not None,
            "cpo_connected": self._cpo is not None,
        }

    def connect_executives(self, cco: Any = None, cpo: Any = None) -> None:
        """Connect Beacon and/or Blueprint for callbacks."""
        if cco:
            self._cco = cco
            logger.info("Connected Beacon (Beacon) to feedback pipeline")
        if cpo:
            self._cpo = cpo
            logger.info("Connected Blueprint (Blueprint) to feedback pipeline")

    def add_feedback(self, feedback: FeedbackItem) -> UUID:
        """
        Add feedback to the pipeline.

        Args:
            feedback: Feedback item to add

        Returns:
            Feedback ID
        """
        # Enforce max size
        while len(self._feedback) >= self._max_feedback:
            self._feedback.popitem(last=False)

        self._feedback[feedback.id] = feedback
        self._feedback_since_generate += 1
        self._total_feedback_processed += 1

        logger.debug(
            f"Added feedback {feedback.id}: "
            f"category={feedback.category.value}, source={feedback.source}"
        )

        # Auto-generate insights if threshold reached
        if self._feedback_since_generate >= self._auto_generate_threshold:
            self.generate_insights()

        return feedback.id

    def add_feedback_batch(self, items: List[FeedbackItem]) -> List[UUID]:
        """Add multiple feedback items."""
        ids = []
        for item in items:
            ids.append(self.add_feedback(item))
        return ids

    def get_feedback(self, feedback_id: UUID) -> Optional[FeedbackItem]:
        """Get a specific feedback item."""
        return self._feedback.get(feedback_id)

    def get_recent_feedback(
        self,
        limit: int = 100,
        category: Optional[FeedbackCategory] = None,
        product_area: Optional[str] = None,
    ) -> List[FeedbackItem]:
        """Get recent feedback items with optional filtering."""
        items = list(reversed(self._feedback.values()))

        if category:
            items = [f for f in items if f.category == category]

        if product_area:
            items = [f for f in items if f.product_area == product_area]

        return items[:limit]

    def generate_insights(self) -> List[ProductInsight]:
        """
        Analyze feedback and generate product insights.

        Groups similar feedback and creates actionable insights
        for the Blueprint to review and prioritize.

        Returns:
            List of newly generated insights
        """
        if not self._feedback:
            return []

        new_insights = []

        # Group feedback by category and product area
        groups: Dict[str, List[FeedbackItem]] = {}
        for fb in self._feedback.values():
            key = f"{fb.category.value}:{fb.product_area or 'general'}"
            if key not in groups:
                groups[key] = []
            groups[key].append(fb)

        # Generate insights for groups meeting threshold
        for key, items in groups.items():
            if len(items) < self.MIN_FEEDBACK_FOR_INSIGHT:
                continue

            # Skip if we already have an open insight for this group
            existing = self._find_open_insight_for_group(key)
            if existing:
                # Update existing insight with new feedback
                self._update_insight_with_feedback(existing, items)
                continue

            # Calculate priority based on feedback characteristics
            priority = self._calculate_priority(items)

            # Calculate weighted customer count
            weighted_count = sum(
                self.TIER_WEIGHTS.get(f.customer_tier or "free", 0.5) for f in items
            )

            # Estimate revenue impact if tier data available
            revenue_impact = self._estimate_revenue_impact(items)

            # Create insight
            category_str, product_area = key.split(":", 1)
            category = FeedbackCategory(category_str)

            insight = ProductInsight(
                title=self._generate_insight_title(items),
                description=self._generate_insight_description(items),
                priority=priority,
                category=category,
                source_feedback_ids=[f.id for f in items],
                customer_count=len(items),
                revenue_impact=revenue_impact,
                product_area=product_area if product_area != "general" else None,
                suggested_action=self._suggest_action(items),
            )

            self._insights[insight.id] = insight
            new_insights.append(insight)
            self._total_insights_generated += 1

            logger.info(
                f"Generated insight: {insight.title} "
                f"(priority={insight.priority.value}, customers={insight.customer_count})"
            )

        self._feedback_since_generate = 0

        # Notify Blueprint if connected
        if self._cpo and new_insights:
            self._notify_cpo(new_insights)

        return new_insights

    def get_insight(self, insight_id: UUID) -> Optional[ProductInsight]:
        """Get a specific insight."""
        return self._insights.get(insight_id)

    def get_insights(
        self,
        status: Optional[str] = None,
        priority: Optional[InsightPriority] = None,
        limit: int = 50,
    ) -> List[ProductInsight]:
        """Get insights with optional filtering."""
        insights = list(self._insights.values())

        if status:
            insights = [i for i in insights if i.status == status]

        if priority:
            insights = [i for i in insights if i.priority == priority]

        # Sort by priority (critical first) then by customer count
        priority_order = {
            InsightPriority.CRITICAL: 0,
            InsightPriority.HIGH: 1,
            InsightPriority.MEDIUM: 2,
            InsightPriority.LOW: 3,
        }
        insights.sort(key=lambda i: (priority_order.get(i.priority, 99), -i.customer_count))

        return insights[:limit]

    def get_insights_for_cpo(self) -> Dict[str, Any]:
        """
        Get insights formatted for Blueprint consumption.

        Returns a structured report suitable for product planning.
        """
        insights = self.get_insights()

        by_priority = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }
        for insight in insights:
            by_priority[insight.priority.value].append(insight.to_dict())

        by_status = {}
        for insight in insights:
            if insight.status not in by_status:
                by_status[insight.status] = []
            by_status[insight.status].append(insight.to_dict())

        return {
            "summary": {
                "total_insights": len(insights),
                "critical_count": len(by_priority["critical"]),
                "high_count": len(by_priority["high"]),
                "actionable_count": len([i for i in insights if i.status == "new"]),
            },
            "by_priority": by_priority,
            "by_status": by_status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def acknowledge_insight(
        self,
        insight_id: UUID,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Blueprint acknowledges an insight for planning.

        Args:
            insight_id: Insight to acknowledge
            notes: Optional notes from Blueprint

        Returns:
            True if acknowledged
        """
        insight = self._insights.get(insight_id)
        if not insight:
            return False

        insight.status = "acknowledged"
        if notes:
            insight.cpo_notes = notes

        logger.info(f"Insight {insight_id} acknowledged by Blueprint")
        return True

    def plan_insight(
        self,
        insight_id: UUID,
        milestone: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Mark insight as planned for a milestone.

        Args:
            insight_id: Insight to plan
            milestone: Target milestone/sprint
            notes: Planning notes

        Returns:
            True if updated
        """
        insight = self._insights.get(insight_id)
        if not insight:
            return False

        insight.status = "planned"
        if notes:
            insight.cpo_notes = f"{insight.cpo_notes or ''}\n[Planned] {notes}".strip()
        if milestone:
            insight.metadata = insight.metadata or {}
            insight.metadata["milestone"] = milestone

        logger.info(f"Insight {insight_id} planned for {milestone or 'future'}")
        return True

    def mark_in_progress(self, insight_id: UUID) -> bool:
        """Mark insight as in progress."""
        insight = self._insights.get(insight_id)
        if not insight:
            return False

        insight.status = "in_progress"
        logger.info(f"Insight {insight_id} now in progress")
        return True

    def mark_delivered(
        self,
        insight_id: UUID,
        release_notes: Optional[str] = None,
    ) -> bool:
        """
        Mark insight as delivered.

        This closes the feedback loop - customers who provided
        feedback can be notified of the improvement.

        Args:
            insight_id: Insight that was delivered
            release_notes: What was shipped

        Returns:
            True if marked delivered
        """
        insight = self._insights.get(insight_id)
        if not insight:
            return False

        insight.status = "delivered"
        insight.delivered_at = datetime.now(timezone.utc)
        if release_notes:
            insight.cpo_notes = f"{insight.cpo_notes or ''}\n[Delivered] {release_notes}".strip()

        logger.info(f"Insight {insight_id} delivered")

        # Notify Beacon to close the loop with customers
        if self._cco:
            self._notify_cco_of_delivery(insight)

        return True

    def get_feedback_for_insight(self, insight_id: UUID) -> List[FeedbackItem]:
        """Get all feedback items that contributed to an insight."""
        insight = self._insights.get(insight_id)
        if not insight:
            return []

        return [self._feedback[fid] for fid in insight.source_feedback_ids if fid in self._feedback]

    def get_customer_impact_report(self) -> Dict[str, Any]:
        """
        Get report of customer impact from delivered insights.

        Useful for showing ROI of customer feedback program.
        """
        delivered = [i for i in self._insights.values() if i.status == "delivered"]

        total_customers = sum(i.customer_count for i in delivered)
        total_revenue_impact = sum(i.revenue_impact or 0 for i in delivered)

        by_category = {}
        for insight in delivered:
            cat = insight.category.value
            if cat not in by_category:
                by_category[cat] = {"count": 0, "customers": 0}
            by_category[cat]["count"] += 1
            by_category[cat]["customers"] += insight.customer_count

        return {
            "delivered_insights": len(delivered),
            "customers_impacted": total_customers,
            "estimated_revenue_impact": total_revenue_impact,
            "by_category": by_category,
            "average_time_to_delivery": self._calculate_avg_delivery_time(delivered),
        }

    # Private helper methods

    def _find_open_insight_for_group(self, group_key: str) -> Optional[ProductInsight]:
        """Find existing open insight for a feedback group."""
        category_str, product_area = group_key.split(":", 1)
        category = FeedbackCategory(category_str)

        for insight in self._insights.values():
            if insight.status in ("delivered",):
                continue
            if insight.category != category:
                continue
            if (insight.product_area or "general") != product_area:
                continue
            return insight
        return None

    def _update_insight_with_feedback(
        self,
        insight: ProductInsight,
        items: List[FeedbackItem],
    ) -> None:
        """Update existing insight with new feedback."""
        new_ids = {f.id for f in items} - set(insight.source_feedback_ids)
        if new_ids:
            insight.source_feedback_ids.extend(new_ids)
            insight.customer_count = len(insight.source_feedback_ids)
            # Recalculate priority with new data
            insight.priority = self._calculate_priority(items)

    def _calculate_priority(self, items: List[FeedbackItem]) -> InsightPriority:
        """Calculate insight priority from feedback characteristics."""
        if not items:
            return InsightPriority.LOW

        # Get base priority from category
        category = items[0].category
        base_priority = self.CATEGORY_PRIORITY_MAP.get(category, InsightPriority.MEDIUM)

        # Escalate based on urgency
        avg_urgency = sum(f.urgency for f in items) / len(items)
        if avg_urgency >= 8:
            if base_priority == InsightPriority.MEDIUM:
                return InsightPriority.HIGH
            elif base_priority == InsightPriority.LOW:
                return InsightPriority.MEDIUM

        # Escalate based on volume
        if len(items) >= 10:
            if base_priority == InsightPriority.LOW:
                return InsightPriority.MEDIUM

        # Escalate based on customer tier
        enterprise_count = sum(1 for f in items if f.customer_tier == "enterprise")
        if enterprise_count >= 3:
            if base_priority != InsightPriority.CRITICAL:
                return InsightPriority.HIGH

        return base_priority

    def _estimate_revenue_impact(self, items: List[FeedbackItem]) -> Optional[float]:
        """Estimate revenue impact from feedback."""
        # Simple model: count by tier with estimated ARR
        tier_arr = {
            "enterprise": 50000,
            "pro": 5000,
            "business": 1000,
            "starter": 100,
            "free": 0,
        }

        total = 0.0
        for item in items:
            tier = item.customer_tier or "free"
            # Assume 10% churn risk impact
            total += tier_arr.get(tier, 0) * 0.1

        return total if total > 0 else None

    def _generate_insight_title(self, items: List[FeedbackItem]) -> str:
        """Generate a title for an insight."""
        category = items[0].category
        product_area = items[0].product_area or "product"
        count = len(items)

        titles = {
            FeedbackCategory.FEATURE_REQUEST: f"Feature request: {product_area} ({count} customers)",
            FeedbackCategory.BUG_REPORT: f"Bug reports in {product_area} ({count} reports)",
            FeedbackCategory.USABILITY_ISSUE: f"Usability issues: {product_area} ({count} reports)",
            FeedbackCategory.PERFORMANCE_ISSUE: f"Performance issues: {product_area} ({count} reports)",
            FeedbackCategory.CHURN_RISK: f"Churn risk signal ({count} customers)",
            FeedbackCategory.SUPPORT_ESCALATION: f"Support escalations: {product_area} ({count} tickets)",
            FeedbackCategory.COMPETITIVE_INTEL: f"Competitive insight ({count} mentions)",
        }

        return titles.get(category, f"Customer feedback: {product_area} ({count} items)")

    def _generate_insight_description(self, items: List[FeedbackItem]) -> str:
        """Generate a description for an insight."""
        # Summarize feedback content
        contents = [f.content for f in items[:5] if f.content]
        summary = "; ".join(contents[:3]) if contents else "Multiple customer reports"

        # Add tier breakdown
        tier_counts = {}
        for item in items:
            tier = item.customer_tier or "unknown"
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        tier_summary = ", ".join(f"{v} {k}" for k, v in tier_counts.items())

        return f"{summary}\n\nCustomer breakdown: {tier_summary}"

    def _suggest_action(self, items: List[FeedbackItem]) -> str:
        """Suggest an action based on feedback category."""
        category = items[0].category
        actions = {
            FeedbackCategory.FEATURE_REQUEST: "Consider for roadmap planning",
            FeedbackCategory.BUG_REPORT: "Prioritize for bug triage",
            FeedbackCategory.USABILITY_ISSUE: "Schedule UX review",
            FeedbackCategory.PERFORMANCE_ISSUE: "Performance investigation needed",
            FeedbackCategory.CHURN_RISK: "Immediate customer success outreach",
            FeedbackCategory.SUPPORT_ESCALATION: "Review support escalation patterns",
            FeedbackCategory.COMPETITIVE_INTEL: "Share with product strategy",
        }
        return actions.get(category, "Review and prioritize")

    def _calculate_avg_delivery_time(
        self,
        delivered: List[ProductInsight],
    ) -> Optional[float]:
        """Calculate average time from insight creation to delivery."""
        times = []
        for insight in delivered:
            if insight.delivered_at:
                delta = insight.delivered_at - insight.created_at
                times.append(delta.total_seconds() / 86400)  # Days

        return sum(times) / len(times) if times else None

    def _notify_cpo(self, insights: List[ProductInsight]) -> None:
        """
        Notify Blueprint of new insights.

        If using FeedbackPipelineIntegration, this is handled automatically
        via Overwatch routing. This method provides basic logging when the
        integration is not connected.
        """
        logger.info(f"Notifying Blueprint of {len(insights)} new insights")

        # If Blueprint is connected directly, call its feedback handler
        if self._cpo and hasattr(self._cpo, "handle_feedback_insights"):
            try:
                self._cpo.handle_feedback_insights(insights)
            except Exception as e:
                logger.warning(f"Blueprint notification failed: {e}")

    def _notify_cco_of_delivery(self, insight: ProductInsight) -> None:
        """
        Notify Beacon that an insight was delivered.

        If using FeedbackPipelineIntegration, this is handled automatically
        via Overwatch routing to create a customer outreach task. This method
        provides basic logging when the integration is not connected.
        """
        logger.info(
            f"Notifying Beacon to close loop on insight {insight.id} "
            f"({insight.customer_count} customers)"
        )

        # If Beacon is connected directly, call its delivery handler
        if self._cco and hasattr(self._cco, "handle_delivery_notification"):
            try:
                feedback_items = [
                    self._feedback[fid]
                    for fid in insight.source_feedback_ids
                    if fid in self._feedback
                ]
                customer_ids = [f.customer_id for f in feedback_items if f.customer_id]
                self._cco.handle_delivery_notification(insight, customer_ids)
            except Exception as e:
                logger.warning(f"Beacon notification failed: {e}")
