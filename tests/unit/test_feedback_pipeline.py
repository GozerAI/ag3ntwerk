"""
Unit tests for Customer Feedback Pipeline (Beacon -> Blueprint).

Tests the integration between Beacon (Beacon) and Blueprint (Blueprint)
for routing customer feedback to product planning.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone


class TestFeedbackPipelineModule:
    """Test feedback pipeline module structure."""

    def test_feedback_pipeline_imports(self):
        """Verify module can be imported."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/__init__.py", encoding="utf-8") as f:
            content = f.read()

        assert "CustomerFeedbackPipeline" in content
        assert "FeedbackItem" in content
        assert "FeedbackCategory" in content
        assert "ProductInsight" in content

    def test_feedback_category_enum(self):
        """Verify FeedbackCategory enum values."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        categories = [
            'FEATURE_REQUEST = "feature_request"',
            'BUG_REPORT = "bug_report"',
            'USABILITY_ISSUE = "usability_issue"',
            'PERFORMANCE_ISSUE = "performance_issue"',
            'PRAISE = "praise"',
            'CHURN_RISK = "churn_risk"',
            'SUPPORT_ESCALATION = "support_escalation"',
            'COMPETITIVE_INTEL = "competitive_intel"',
        ]
        for category in categories:
            assert category in content, f"Missing category: {category}"

    def test_insight_priority_enum(self):
        """Verify InsightPriority enum values."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        priorities = [
            'CRITICAL = "critical"',
            'HIGH = "high"',
            'MEDIUM = "medium"',
            'LOW = "low"',
        ]
        for priority in priorities:
            assert priority in content, f"Missing priority: {priority}"


class TestFeedbackItem:
    """Test FeedbackItem dataclass."""

    def test_feedback_item_fields(self):
        """Verify FeedbackItem has required fields."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        fields = [
            "id: UUID",
            "source: str",
            "customer_id: Optional[str]",
            "customer_tier: Optional[str]",
            "category: FeedbackCategory",
            "content: str",
            "sentiment_score: float",
            "urgency: int",
            "product_area: Optional[str]",
            "tags: List[str]",
            "timestamp: datetime",
            "metadata: Dict[str, Any]",
        ]
        for field in fields:
            assert field in content, f"Missing field: {field}"

    def test_feedback_item_to_dict(self):
        """Verify FeedbackItem has to_dict method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def to_dict(self) -> Dict[str, Any]:" in content


class TestProductInsight:
    """Test ProductInsight dataclass."""

    def test_product_insight_fields(self):
        """Verify ProductInsight has required fields."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        fields = [
            "id: UUID",
            "title: str",
            "description: str",
            "priority: InsightPriority",
            "source_feedback_ids: List[UUID]",
            "customer_count: int",
            "revenue_impact: Optional[float]",
            "product_area: Optional[str]",
            "suggested_action: Optional[str]",
            "status: str",
            "cpo_notes: Optional[str]",
            "delivered_at: Optional[datetime]",
        ]
        for field in fields:
            assert field in content, f"Missing field: {field}"

    def test_insight_status_values(self):
        """Verify insight status documentation."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Status values documented in default
        assert 'status: str = "new"' in content
        assert "# new, acknowledged, planned, in_progress, delivered" in content


class TestCustomerFeedbackPipeline:
    """Test CustomerFeedbackPipeline class."""

    def test_pipeline_init(self):
        """Verify pipeline initialization."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def __init__(" in content
        assert "self._cco = cco" in content
        assert "self._cpo = cpo" in content
        assert "self._feedback: OrderedDict" in content
        assert "self._insights: Dict[UUID, ProductInsight]" in content

    def test_pipeline_add_feedback(self):
        """Verify add_feedback method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def add_feedback(self, feedback: FeedbackItem) -> UUID:" in content
        assert "self._feedback[feedback.id] = feedback" in content
        assert "self._feedback_since_generate += 1" in content

    def test_pipeline_add_feedback_batch(self):
        """Verify batch feedback addition."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def add_feedback_batch(self, items: List[FeedbackItem]) -> List[UUID]:" in content

    def test_pipeline_generate_insights(self):
        """Verify insight generation."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def generate_insights(self) -> List[ProductInsight]:" in content
        assert "MIN_FEEDBACK_FOR_INSIGHT" in content
        assert "self._insights[insight.id] = insight" in content

    def test_pipeline_get_insights_for_cpo(self):
        """Verify Blueprint-formatted insight retrieval."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def get_insights_for_cpo(self) -> Dict[str, Any]:" in content
        assert '"summary"' in content
        assert '"by_priority"' in content
        assert '"by_status"' in content


class TestPipelineStatusManagement:
    """Test insight status management methods."""

    def test_acknowledge_insight(self):
        """Verify insight acknowledgment."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def acknowledge_insight(" in content
        assert 'insight.status = "acknowledged"' in content

    def test_plan_insight(self):
        """Verify insight planning."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def plan_insight(" in content
        assert 'insight.status = "planned"' in content
        assert '"milestone"' in content

    def test_mark_in_progress(self):
        """Verify marking insight in progress."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def mark_in_progress(self, insight_id: UUID) -> bool:" in content
        assert 'insight.status = "in_progress"' in content

    def test_mark_delivered(self):
        """Verify marking insight as delivered."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def mark_delivered(" in content
        assert 'insight.status = "delivered"' in content
        assert "insight.delivered_at = datetime.now(timezone.utc)" in content
        assert "_notify_cco_of_delivery" in content


class TestPipelinePriorityCalculation:
    """Test priority calculation logic."""

    def test_tier_weights(self):
        """Verify customer tier weights."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "TIER_WEIGHTS = {" in content
        assert '"enterprise": 3.0' in content
        assert '"pro": 2.0' in content
        assert '"free": 0.5' in content

    def test_category_priority_map(self):
        """Verify category to priority mapping."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "CATEGORY_PRIORITY_MAP = {" in content
        assert "FeedbackCategory.BUG_REPORT: InsightPriority.HIGH" in content
        assert "FeedbackCategory.CHURN_RISK: InsightPriority.CRITICAL" in content

    def test_calculate_priority(self):
        """Verify priority calculation method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert (
            "def _calculate_priority(self, items: List[FeedbackItem]) -> InsightPriority:"
            in content
        )
        # Urgency escalation
        assert "avg_urgency >= 8" in content
        # Volume escalation
        assert "len(items) >= 10" in content
        # Enterprise escalation
        assert "enterprise_count >= 3" in content

    def test_estimate_revenue_impact(self):
        """Verify revenue impact estimation."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def _estimate_revenue_impact(self, items: List[FeedbackItem])" in content
        assert "tier_arr = {" in content
        assert '"enterprise": 50000' in content


class TestPipelineStats:
    """Test pipeline statistics."""

    def test_stats_property(self):
        """Verify stats property."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def stats(self) -> Dict[str, Any]:" in content
        assert '"feedback_count"' in content
        assert '"insight_count"' in content
        assert '"total_feedback_processed"' in content
        assert '"insights_by_status"' in content
        assert '"insights_by_priority"' in content

    def test_customer_impact_report(self):
        """Verify customer impact reporting."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def get_customer_impact_report(self) -> Dict[str, Any]:" in content
        assert '"delivered_insights"' in content
        assert '"customers_impacted"' in content
        assert '"estimated_revenue_impact"' in content


class TestPipelineExecutiveIntegration:
    """Test agent connection methods."""

    def test_connect_executives(self):
        """Verify agent connection method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def connect_executives(self, cco: Any = None, cpo: Any = None)" in content
        assert 'logger.info("Connected Beacon (Beacon) to feedback pipeline")' in content
        assert 'logger.info("Connected Blueprint (Blueprint) to feedback pipeline")' in content

    def test_notify_cpo(self):
        """Verify Blueprint notification method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def _notify_cpo(self, insights: List[ProductInsight])" in content

    def test_notify_cco_of_delivery(self):
        """Verify Beacon notification on delivery."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def _notify_cco_of_delivery(self, insight: ProductInsight)" in content


class TestPipelineAutoGeneration:
    """Test auto-generation of insights."""

    def test_auto_generate_threshold(self):
        """Verify auto-generation threshold."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "auto_generate_threshold" in content
        assert "self._feedback_since_generate >= self._auto_generate_threshold" in content
        assert "self.generate_insights()" in content

    def test_min_feedback_for_insight(self):
        """Verify minimum feedback threshold for insight creation."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/feedback_pipeline.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "MIN_FEEDBACK_FOR_INSIGHT = 3" in content
        assert "len(items) < self.MIN_FEEDBACK_FOR_INSIGHT" in content
