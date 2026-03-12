"""Tests for metacognition performance attribution (Phase 4, Step 3)."""

import math
import pytest

from ag3ntwerk.modules.metacognition.service import (
    MetacognitionService,
    TraitAttribution,
    _pearson_correlation,
    MIN_ATTRIBUTION_SAMPLES,
    MIN_ATTRIBUTION_AGENTS,
    MIN_SUGGESTION_CORRELATION,
)


# ============================================================
# Pearson Correlation Helper
# ============================================================


class TestPearsonCorrelation:
    """Tests for the pure-Python Pearson helper."""

    def test_perfect_positive(self):
        r = _pearson_correlation([1, 2, 3, 4], [10, 20, 30, 40])
        assert abs(r - 1.0) < 1e-9

    def test_perfect_negative(self):
        r = _pearson_correlation([1, 2, 3, 4], [40, 30, 20, 10])
        assert abs(r - (-1.0)) < 1e-9

    def test_no_correlation(self):
        r = _pearson_correlation([1, 2, 3, 4], [1, 1, 1, 1])
        assert abs(r) < 1e-9  # constant y -> zero std -> 0.0

    def test_returns_zero_for_single_element(self):
        assert _pearson_correlation([1], [1]) == 0.0

    def test_returns_zero_for_empty(self):
        assert _pearson_correlation([], []) == 0.0

    def test_returns_zero_for_mismatched_lengths(self):
        assert _pearson_correlation([1, 2], [1]) == 0.0

    def test_moderate_correlation(self):
        r = _pearson_correlation([1, 2, 3, 4, 5], [2, 4, 5, 4, 5])
        assert 0.5 < r < 1.0


# ============================================================
# TraitAttribution dataclass
# ============================================================


class TestTraitAttribution:
    """Tests for the TraitAttribution dataclass."""

    def test_to_dict(self):
        a = TraitAttribution(
            task_type="code_review",
            trait_name="risk_tolerance",
            correlation=0.72345,
            sample_count=50,
            suggested_value=0.81234,
        )
        d = a.to_dict()
        assert d["task_type"] == "code_review"
        assert d["trait_name"] == "risk_tolerance"
        assert d["correlation"] == 0.7235
        assert d["sample_count"] == 50
        assert d["suggested_value"] == 0.8123

    def test_negative_correlation(self):
        a = TraitAttribution(
            task_type="deploy",
            trait_name="creativity",
            correlation=-0.6,
            sample_count=30,
            suggested_value=0.3,
        )
        d = a.to_dict()
        assert d["correlation"] == -0.6


# ============================================================
# Helpers
# ============================================================


def _build_attribution_service(
    agents=("Forge", "Echo", "Keystone", "Index"),
    task_type="code_review",
    outcomes_per_agent=15,
    success_pattern=None,
):
    """
    Build a service with enough data for attribution.
    success_pattern: dict of agent_code -> success_rate (0.0-1.0)
    """
    svc = MetacognitionService()
    for code in agents:
        svc.register_agent(code)

    if success_pattern is None:
        # Default: Forge=90%, Echo=70%, Keystone=50%, Index=30%
        success_pattern = {}
        rates = [0.9, 0.7, 0.5, 0.3]
        for i, code in enumerate(agents):
            success_pattern[code] = rates[i] if i < len(rates) else 0.5

    for code in agents:
        rate = success_pattern.get(code, 0.5)
        for j in range(outcomes_per_agent):
            success = (j / outcomes_per_agent) < rate
            svc.on_task_completed(code, f"{code}-{task_type}-{j}", task_type, success)

    return svc


# ============================================================
# compute_attribution
# ============================================================


class TestComputeAttribution:
    """Tests for compute_attribution."""

    def test_returns_empty_with_no_data(self):
        svc = MetacognitionService()
        assert svc.compute_attribution() == []

    def test_returns_empty_below_min_agents(self):
        svc = MetacognitionService()
        # Only 2 agents (below MIN_ATTRIBUTION_AGENTS=3)
        for code in ["Forge", "Echo"]:
            svc.register_agent(code)
            for i in range(MIN_ATTRIBUTION_SAMPLES):
                svc.on_task_completed(code, f"{code}-t{i}", "test", True)
        assert svc.compute_attribution() == []

    def test_returns_empty_below_min_samples(self):
        svc = MetacognitionService()
        for code in ["Forge", "Echo", "Keystone"]:
            svc.register_agent(code)
            for i in range(MIN_ATTRIBUTION_SAMPLES - 1):
                svc.on_task_completed(code, f"{code}-t{i}", "test", True)
        assert svc.compute_attribution() == []

    def test_returns_attributions_with_sufficient_data(self):
        svc = _build_attribution_service()
        result = svc.compute_attribution()
        assert len(result) > 0
        assert all(isinstance(a, TraitAttribution) for a in result)

    def test_sorted_by_abs_correlation(self):
        svc = _build_attribution_service()
        result = svc.compute_attribution()
        if len(result) > 1:
            for i in range(len(result) - 1):
                assert abs(result[i].correlation) >= abs(result[i + 1].correlation)

    def test_filter_by_task_type(self):
        svc = _build_attribution_service(task_type="code_review")
        # Add a second task type
        for code in ["Forge", "Echo", "Keystone", "Index"]:
            for i in range(15):
                svc.on_task_completed(code, f"{code}-deploy-{i}", "deploy", True)

        review_only = svc.compute_attribution(task_type="code_review")
        assert all(a.task_type == "code_review" for a in review_only)

    def test_custom_min_samples(self):
        svc = _build_attribution_service(outcomes_per_agent=8)
        # With default min_samples=10, should be empty
        assert svc.compute_attribution(min_samples=10) == []
        # With lower min_samples, should work
        result = svc.compute_attribution(min_samples=5)
        assert len(result) > 0

    def test_correlation_range(self):
        svc = _build_attribution_service()
        for a in svc.compute_attribution():
            assert -1.0 <= a.correlation <= 1.0

    def test_sample_count_correct(self):
        agents = ("Forge", "Echo", "Keystone", "Index")
        n = 15
        svc = _build_attribution_service(agents=agents, outcomes_per_agent=n)
        for a in svc.compute_attribution():
            assert a.sample_count == len(agents) * n

    def test_suggested_value_in_range(self):
        svc = _build_attribution_service()
        for a in svc.compute_attribution():
            assert 0.0 <= a.suggested_value <= 1.0


# ============================================================
# suggest_trait_map_updates
# ============================================================


class TestSuggestTraitMapUpdates:
    """Tests for suggest_trait_map_updates."""

    def test_empty_with_no_data(self):
        svc = MetacognitionService()
        assert svc.suggest_trait_map_updates() == {}

    def test_returns_dict_structure(self):
        svc = _build_attribution_service()
        result = svc.suggest_trait_map_updates(min_correlation=0.0)
        assert isinstance(result, dict)
        for tt, traits in result.items():
            assert isinstance(tt, str)
            assert isinstance(traits, dict)
            for name, value in traits.items():
                assert isinstance(name, str)
                assert isinstance(value, float)

    def test_respects_min_correlation(self):
        svc = _build_attribution_service()
        # Very high threshold -> likely empty
        strict = svc.suggest_trait_map_updates(min_correlation=0.99)
        # Very low threshold -> more results
        lenient = svc.suggest_trait_map_updates(min_correlation=0.0)
        total_strict = sum(len(v) for v in strict.values())
        total_lenient = sum(len(v) for v in lenient.values())
        assert total_lenient >= total_strict

    def test_values_are_valid_floats(self):
        svc = _build_attribution_service()
        result = svc.suggest_trait_map_updates(min_correlation=0.0)
        for traits in result.values():
            for v in traits.values():
                assert 0.0 <= v <= 1.0
                assert not math.isnan(v)

    def test_custom_min_samples(self):
        svc = _build_attribution_service(outcomes_per_agent=8)
        assert svc.suggest_trait_map_updates(min_samples=10) == {}
        # Lower threshold should work
        result = svc.suggest_trait_map_updates(min_correlation=0.0, min_samples=5)
        # May or may not have results depending on correlation


# ============================================================
# Integration
# ============================================================


class TestAttributionIntegration:
    """Integration tests combining attribution with other metacognition."""

    def test_attribution_uses_task_outcomes_from_on_task_completed(self):
        svc = MetacognitionService()
        for code in ["Forge", "Echo", "Keystone"]:
            svc.register_agent(code)
        # Feed outcomes
        for i in range(MIN_ATTRIBUTION_SAMPLES):
            svc.on_task_completed("Forge", f"t{i}", "test", True)
            svc.on_task_completed("Echo", f"t{i}", "test", i % 2 == 0)
            svc.on_task_completed("Keystone", f"t{i}", "test", False)
        result = svc.compute_attribution(task_type="test")
        assert len(result) > 0

    def test_to_dict_serializable(self):
        """Ensure attribution results are JSON-serializable."""
        import json

        svc = _build_attribution_service()
        result = svc.compute_attribution()
        dicts = [a.to_dict() for a in result]
        serialized = json.dumps(dicts)
        assert len(serialized) > 2
