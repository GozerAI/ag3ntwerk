"""Tests for metacognition routing feedback loop (Phase 4, Step 1)."""

import pytest

from ag3ntwerk.modules.metacognition.service import (
    MetacognitionService,
    MIN_ROUTING_SAMPLES,
    MAX_ROUTING_BONUS,
    MAX_ROUTING_OUTCOMES,
)


class TestRecordRoutingOutcome:
    """Tests for record_routing_outcome."""

    def test_basic_recording(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.record_routing_outcome("Forge", "code_review", 0.8, True)
        assert len(svc._routing_outcomes) == 1
        assert svc._routing_outcomes[0]["agent_code"] == "Forge"
        assert svc._routing_outcomes[0]["task_type"] == "code_review"
        assert svc._routing_outcomes[0]["success"] is True

    def test_multiple_recordings(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        for i in range(10):
            svc.record_routing_outcome("Forge", "code_review", 0.8, i % 2 == 0)
        assert len(svc._routing_outcomes) == 10

    def test_capped_at_max(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        for i in range(MAX_ROUTING_OUTCOMES + 100):
            svc.record_routing_outcome("Forge", "test", 0.5, True)
        assert len(svc._routing_outcomes) <= MAX_ROUTING_OUTCOMES

    def test_outcome_has_timestamp(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.record_routing_outcome("Forge", "code_review", 0.8, True)
        assert "timestamp" in svc._routing_outcomes[0]


class TestComputeRoutingBonus:
    """Tests for compute_routing_bonus."""

    def test_returns_zero_below_min_samples(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        for i in range(MIN_ROUTING_SAMPLES - 1):
            svc.record_routing_outcome("Forge", "code_review", 0.8, True)
        assert svc.compute_routing_bonus("Forge", "code_review") == 0.0

    def test_returns_zero_no_data(self):
        svc = MetacognitionService()
        assert svc.compute_routing_bonus("Forge", "code_review") == 0.0

    def test_perfect_success_gives_max_bonus(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        for _ in range(MIN_ROUTING_SAMPLES):
            svc.record_routing_outcome("Forge", "code_review", 0.8, True)
        bonus = svc.compute_routing_bonus("Forge", "code_review")
        assert abs(bonus - MAX_ROUTING_BONUS) < 1e-9

    def test_total_failure_gives_negative_max(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        for _ in range(MIN_ROUTING_SAMPLES):
            svc.record_routing_outcome("Forge", "code_review", 0.8, False)
        bonus = svc.compute_routing_bonus("Forge", "code_review")
        assert abs(bonus - (-MAX_ROUTING_BONUS)) < 1e-9

    def test_fifty_percent_gives_zero(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        for i in range(MIN_ROUTING_SAMPLES * 2):
            svc.record_routing_outcome("Forge", "code_review", 0.8, i % 2 == 0)
        bonus = svc.compute_routing_bonus("Forge", "code_review")
        assert abs(bonus) < 1e-9

    def test_bonus_bounded(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        for _ in range(100):
            svc.record_routing_outcome("Forge", "code_review", 0.8, True)
        bonus = svc.compute_routing_bonus("Forge", "code_review")
        assert -MAX_ROUTING_BONUS <= bonus <= MAX_ROUTING_BONUS

    def test_different_task_types_independent(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        for _ in range(MIN_ROUTING_SAMPLES):
            svc.record_routing_outcome("Forge", "code_review", 0.8, True)
            svc.record_routing_outcome("Forge", "deploy", 0.8, False)
        bonus_review = svc.compute_routing_bonus("Forge", "code_review")
        bonus_deploy = svc.compute_routing_bonus("Forge", "deploy")
        assert bonus_review > 0
        assert bonus_deploy < 0


class TestScoreAgentsWithRouting:
    """Tests for score_agents_for_task with routing bonus."""

    def test_backward_compatible_no_task_type(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.register_agent("Echo")
        scores = svc.score_agents_for_task(
            {"risk_tolerance": 0.8},
            ["Forge", "Echo"],
        )
        assert len(scores) == 2
        assert all(isinstance(s, tuple) for s in scores)

    def test_task_type_includes_bonus(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.register_agent("Echo")
        # Give Forge a strong routing history for code_review
        for _ in range(MIN_ROUTING_SAMPLES):
            svc.record_routing_outcome("Forge", "code_review", 0.8, True)
            svc.record_routing_outcome("Echo", "code_review", 0.8, False)
        scores_with = svc.score_agents_for_task(
            {"risk_tolerance": 0.8},
            ["Forge", "Echo"],
            task_type="code_review",
        )
        scores_without = svc.score_agents_for_task(
            {"risk_tolerance": 0.8},
            ["Forge", "Echo"],
        )
        # Forge should rank higher with routing history considered
        cto_with = next(s for c, s in scores_with if c == "Forge")
        cto_without = next(s for c, s in scores_without if c == "Forge")
        assert cto_with > cto_without


class TestGetRoutingStats:
    """Tests for get_routing_stats."""

    def test_empty_stats(self):
        svc = MetacognitionService()
        stats = svc.get_routing_stats()
        assert stats["total_routing_outcomes"] == 0
        assert stats["agents"] == {}

    def test_stats_structure(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        for _ in range(MIN_ROUTING_SAMPLES):
            svc.record_routing_outcome("Forge", "code_review", 0.8, True)
        stats = svc.get_routing_stats()
        assert stats["total_routing_outcomes"] == MIN_ROUTING_SAMPLES
        assert "Forge" in stats["agents"]
        assert "code_review" in stats["agents"]["Forge"]
        cr = stats["agents"]["Forge"]["code_review"]
        assert "samples" in cr
        assert "success_rate" in cr
        assert "routing_bonus" in cr

    def test_stats_in_get_stats(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.record_routing_outcome("Forge", "code_review", 0.8, True)
        stats = svc.get_stats()
        assert "total_routing_outcomes" in stats
        assert stats["total_routing_outcomes"] == 1
