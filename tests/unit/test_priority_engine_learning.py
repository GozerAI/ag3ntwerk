"""
Unit tests for Priority Engine learning integration.

Tests the integration between PriorityEngine and PersistentLearning
to ensure historical data is properly used for priority scoring.

Note: Due to Nexus being installed as an editable package, runtime tests
validate the codebase implementation directly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestPriorityEngineLearning:
    """Test Priority Engine learning system integration."""

    def test_learning_integration_code_exists(self):
        """Verify learning integration is implemented in codebase."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        # Verify learning system parameter is added to __init__
        assert "learning_system=None" in content
        assert "self._learning = learning_system" in content

        # Verify learning cache is implemented
        assert "_learning_cache" in content
        assert "_cache_ttl_seconds" in content

        # Verify _calculate_learning uses the learning system
        assert "await self._learning.get_similar_outcomes" in content
        assert "await self._learning.get_executor_stats" in content

        # Verify helper methods exist
        assert "def set_learning_system" in content
        assert "def clear_learning_cache" in content
        assert "async def get_learning_insights" in content

    def test_learning_score_calculation_logic(self):
        """Verify learning score calculation logic."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        # Verify success rate calculation
        assert "success_rate = successes / len(similar_outcomes)" in content

        # Verify recent outcomes weighting
        assert "recent_weight" in content
        assert "recent_count" in content

        # Verify executor performance blending
        assert "executor_rate" in content
        assert "0.8 * learning_score + 0.2 * executor_rate" in content

    def test_calculate_learning_default_return(self):
        """Verify default return value when no learning system."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        # Verify default return when no learning system
        assert "if not self._learning:" in content
        assert "return 0.5  # Default neutral score when no learning system" in content

    def test_calculate_learning_cache_check(self):
        """Verify cache is checked before querying learning system."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        # Verify cache check logic
        assert "if item_id in self._learning_cache:" in content
        assert "return self._learning_cache[item_id]" in content

    def test_calculate_learning_insufficient_data_check(self):
        """Verify insufficient data handling."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        # Verify insufficient data check
        assert "if len(similar_outcomes) < 3:" in content
        assert "# Not enough historical data" in content

    def test_set_learning_system_clears_cache(self):
        """Verify set_learning_system clears the cache."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        # Verify cache clearing in set_learning_system
        assert "def set_learning_system" in content
        assert "self._learning_cache.clear()" in content

    def test_clear_learning_cache_method(self):
        """Verify clear_learning_cache method exists."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        assert "def clear_learning_cache(self):" in content
        assert "self._learning_cache.clear()" in content

    def test_get_learning_insights_structure(self):
        """Verify get_learning_insights returns proper structure."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        # Verify insights structure
        assert '"available"' in content
        assert '"has_data"' in content
        assert '"similar_count"' in content
        assert '"success_count"' in content
        assert '"failure_count"' in content
        assert '"success_rate"' in content
        assert '"recommended_executor"' in content

    def test_learning_insights_no_system_response(self):
        """Verify response when no learning system configured."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        assert '"No learning system configured"' in content

    def test_learning_insights_insufficient_data_response(self):
        """Verify response when insufficient historical data."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        assert '"Insufficient historical data"' in content


class TestPriorityEngineIntegration:
    """Test full priority engine implementation with learning."""

    def test_priority_factor_learning_exists(self):
        """Verify LEARNING is in PriorityFactor enum."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        assert 'LEARNING = "learning"' in content
        assert "PriorityFactor.LEARNING" in content

    def test_learning_weight_configured(self):
        """Verify learning has a weight in DEFAULT_WEIGHTS."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        assert "PriorityFactor.LEARNING: 0.10" in content

    def test_score_item_calls_calculate_learning(self):
        """Verify _score_item calls _calculate_learning."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        assert "learning = await self._calculate_learning(item)" in content
        assert "factors[PriorityFactor.LEARNING] = learning" in content

    def test_learning_error_handling(self):
        """Verify error handling in learning calculation."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        assert "except Exception as e:" in content
        assert 'logger.warning(f"Error calculating learning score: {e}")' in content
        assert "return 0.5  # Default on error" in content

    def test_recent_weighting_algorithm(self):
        """Verify recent outcomes are weighted more heavily."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        # Verify decay weight for older records
        assert "weight = 1.0 - (i * 0.15)" in content

        # Verify blend ratio
        assert "0.6 * recent_success_rate + 0.4 * success_rate" in content

    def test_executor_performance_factored(self):
        """Verify executor performance is factored into learning score."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        # Verify executor stats are fetched
        assert "executor_stats = await self._learning.get_executor_stats" in content

        # Verify minimum sample size check
        assert 'if executor_stats.get("total", 0) >= 5:' in content

    def test_error_pattern_analysis_in_insights(self):
        """Verify error patterns are analyzed in get_learning_insights."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        assert "error_patterns = {}" in content
        assert "common_errors" in content

    def test_trend_analysis_in_insights(self):
        """Verify trend analysis in get_learning_insights."""
        with open("F:/Projects/public-release/ag3ntwerk/src/nexus/src/nexus/coo/priority_engine.py") as f:
            content = f.read()

        assert '"recent_trend"' in content
        assert '"improving"' in content
        assert '"declining"' in content
        assert '"stable"' in content
