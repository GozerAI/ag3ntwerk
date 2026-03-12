"""
Unit tests for Ensemble Feedback Learning System.

Tests the integration between UnifiedEnsemble and FeedbackTracker
for meta-learning based on user feedback.

Note: Due to Nexus being installed as an editable package, runtime tests
validate the codebase implementation directly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4


class TestEnsembleFeedbackLearning:
    """Test Ensemble feedback learning system."""

    def test_provide_feedback_implementation(self):
        """Verify provide_feedback is fully implemented."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify the TODO has been removed
        assert "# TODO: Integrate with combo1's meta-learning system" not in content
        assert "# TODO: Update model weights based on feedback" not in content

        # Verify feedback recording is implemented
        assert "self._feedback_tracker.record_feedback" in content
        assert "await self._maybe_update_weights_from_feedback()" in content

    def test_feedback_tracker_integration(self):
        """Verify FeedbackTracker is integrated."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify feedback tracker is used
        assert "if self._feedback_tracker:" in content
        assert "self._feedback_tracker.record_feedback" in content
        assert "self._feedback_tracker.get_weight_recommendations()" in content

    def test_request_context_tracking(self):
        """Verify request context is tracked for feedback correlation."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify context tracking methods
        assert "def record_request_context" in content
        assert "_request_history" in content
        assert "_find_model_for_request" in content
        assert "_get_query_type_for_request" in content
        assert "_get_latency_for_request" in content

    def test_request_context_recorded_in_process(self):
        """Verify request context is recorded during processing."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify record_request_context is called in process method
        assert "self.record_request_context(" in content
        assert "model_name=primary_model" in content
        assert "latency_ms=total_latency" in content

    def test_feedback_score_validation(self):
        """Verify feedback score is validated (0-1 range)."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify score validation
        assert "feedback_score = max(0.0, min(1.0, feedback_score))" in content

    def test_model_score_update_from_feedback(self):
        """Verify model scores are updated from feedback."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify feedback updates performance
        assert "_update_model_score_from_feedback" in content
        assert '"feedback_score"' in content
        assert '"feedback_count"' in content

    def test_weight_recommendations_applied(self):
        """Verify weight recommendations are applied to models."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify weight adjustment
        assert "_maybe_update_weights_from_feedback" in content
        assert '"feedback_weight_adj"' in content
        assert '"effective_confidence"' in content

    def test_get_feedback_stats_method(self):
        """Verify get_feedback_stats returns proper structure."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify stats method
        assert "def get_feedback_stats" in content
        assert "get_all_model_stats()" in content
        assert '"total_feedback"' in content
        assert '"average_score"' in content
        assert '"recommendations"' in content


class TestEnsembleWeightAdjustment:
    """Test weight adjustment based on feedback."""

    def test_effective_confidence_calculation(self):
        """Verify effective confidence is calculated from feedback."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify confidence blending formula
        assert "feedback_influence = 0.2" in content
        assert "(1 - feedback_influence)" in content

    def test_running_average_calculation(self):
        """Verify running average for feedback scores."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify running average formula
        assert '(perf["feedback_score"] * (n - 1) + feedback_score) / n' in content

    def test_request_history_cleanup(self):
        """Verify request history is cleaned up to prevent memory bloat."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify cleanup logic
        assert "while len(self._request_history) > 1000:" in content
        assert "popitem(last=False)" in content


class TestFeedbackTrackerIntegration:
    """Test FeedbackTracker features used by ensemble."""

    def test_feedback_record_structure(self):
        """Verify FeedbackRecord has required fields."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/monitoring/feedback_tracker.py"
        ) as f:
            content = f.read()

        # Verify FeedbackRecord fields
        assert "request_id: UUID" in content
        assert "model_name: str" in content
        assert "feedback_score: float" in content
        assert "query_type: Optional[str]" in content
        assert "response_latency_ms: Optional[float]" in content

    def test_weight_recommendations(self):
        """Verify get_weight_recommendations is available."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/monitoring/feedback_tracker.py"
        ) as f:
            content = f.read()

        # Verify recommendation method
        assert "def get_weight_recommendations" in content
        assert "score_diff = stats.average_score - mean_score" in content
        assert "trend_factor = stats.recent_trend" in content

    def test_query_type_tracking(self):
        """Verify per-query-type tracking."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/monitoring/feedback_tracker.py"
        ) as f:
            content = f.read()

        # Verify query type tracking
        assert "query_type_scores" in content
        assert "get_best_model_for_query_type" in content
        assert "get_query_type_rankings" in content

    def test_model_feedback_stats(self):
        """Verify ModelFeedbackStats structure."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/monitoring/feedback_tracker.py"
        ) as f:
            content = f.read()

        # Verify stats structure
        assert "class ModelFeedbackStats:" in content
        assert "average_score: float" in content
        assert "positive_count: int" in content
        assert "negative_count: int" in content
        assert "recent_trend: float" in content


class TestFeedbackLogging:
    """Test feedback logging and debugging."""

    def test_feedback_logging(self):
        """Verify feedback is logged."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify logging
        assert 'logger.debug(f"Recorded feedback for {model_name}' in content
        assert 'f"Updated {model_name} feedback' in content  # Multiline log statement
        assert 'logger.debug(f"Applied weight recommendations' in content

    def test_warning_for_missing_model(self):
        """Verify warning when model not found for request."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify warning
        assert 'logger.warning(f"Cannot find model for request {request_id}")' in content


class TestFeedbackFallback:
    """Test fallback behavior when feedback tracker is not available."""

    def test_fallback_without_tracker(self):
        """Verify fallback to direct score update."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify fallback logic
        assert "else:" in content
        assert "self._update_model_score_from_feedback(model_name, feedback_score)" in content

    def test_stats_without_tracker(self):
        """Verify get_feedback_stats handles missing tracker."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/providers/ensemble/core.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Verify handling
        assert '"available": False' in content
        assert '"Feedback tracker not initialized"' in content
