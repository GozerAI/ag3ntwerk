"""Tests for metacognition team composition learning (Phase 5, Step 4)."""

import pytest

from ag3ntwerk.modules.metacognition.service import (
    MetacognitionService,
    TeamOutcome,
    MAX_TEAM_OUTCOMES,
    MIN_TEAM_SAMPLES,
    MIN_PAIR_SAMPLES,
)


# ============================================================
# TeamOutcome dataclass
# ============================================================


class TestTeamOutcome:

    def test_to_dict(self):
        to = TeamOutcome(
            team=["Forge", "Keystone"],
            task_type="code_review",
            success=True,
            task_id="t1",
            compatibility_score=0.85,
        )
        d = to.to_dict()
        assert d["team"] == ["Forge", "Keystone"]
        assert d["success"] is True
        assert d["compatibility_score"] == 0.85


# ============================================================
# record_team_outcome
# ============================================================


class TestRecordTeamOutcome:

    def test_records_sorted_team(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.record_team_outcome(["Keystone", "Forge"], "code_review", True)
        assert len(svc._team_outcomes) == 1
        assert svc._team_outcomes[0].team == ["Forge", "Keystone"]

    def test_empty_team_noop(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.record_team_outcome([], "code_review", True)
        assert len(svc._team_outcomes) == 0

    def test_cap_at_max(self):
        svc = MetacognitionService()
        svc._auto_save = False
        for i in range(MAX_TEAM_OUTCOMES + 10):
            svc.record_team_outcome(["Forge", "Keystone"], "code_review", True, task_id=f"t{i}")
        assert len(svc._team_outcomes) <= MAX_TEAM_OUTCOMES

    def test_stats_include_team_outcomes(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        svc.record_team_outcome(["Forge"], "code_review", True)
        stats = svc.get_stats()
        assert stats["total_team_outcomes"] == 1


# ============================================================
# get_team_stats
# ============================================================


class TestGetTeamStats:

    def _make_service(self):
        svc = MetacognitionService()
        svc._auto_save = False
        # Record enough outcomes for a team
        for i in range(10):
            svc.record_team_outcome(
                ["Forge", "Keystone"],
                "code_review",
                success=i < 8,
                task_id=f"t{i}",
            )
        return svc

    def test_returns_compositions(self):
        svc = self._make_service()
        stats = svc.get_team_stats()
        assert stats["total_team_outcomes"] == 10
        assert len(stats["compositions"]) == 1
        assert stats["compositions"][0]["success_rate"] == 0.8

    def test_filter_by_task_type(self):
        svc = self._make_service()
        # Add outcomes for different task type
        for i in range(10):
            svc.record_team_outcome(["Forge", "Echo"], "market_research", success=True)

        stats = svc.get_team_stats(task_type="market_research")
        assert all(c["task_type"] == "market_research" for c in stats["compositions"])

    def test_minimum_samples_required(self):
        svc = MetacognitionService()
        svc._auto_save = False
        # Only 2 outcomes, below MIN_TEAM_SAMPLES
        svc.record_team_outcome(["Forge", "Keystone"], "code_review", True)
        svc.record_team_outcome(["Forge", "Keystone"], "code_review", True)
        stats = svc.get_team_stats()
        assert len(stats["compositions"]) == 0


# ============================================================
# recommend_learned_team
# ============================================================


class TestRecommendLearnedTeam:

    def _make_service_with_teams(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        svc.register_agent("Keystone")
        svc.register_agent("Echo")

        # Record successful team
        for i in range(10):
            svc.record_team_outcome(
                ["Keystone", "Echo", "Forge"],
                "code_review",
                success=True,
                task_id=f"t{i}",
            )
        return svc

    def test_returns_learned_team(self):
        svc = self._make_service_with_teams()
        result = svc.recommend_learned_team("code_review", team_size=3)
        assert result["source"] == "learned"
        assert result["fallback_used"] is False
        assert len(result["team"]) == 3
        assert result["success_rate"] == 1.0

    def test_fallback_when_no_data(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        svc.register_agent("Keystone")
        svc.register_agent("Echo")
        result = svc.recommend_learned_team("unknown_task", team_size=3)
        assert result["fallback_used"] is True
        assert result["source"] == "personality_fit"

    def test_wrong_team_size_fallback(self):
        svc = self._make_service_with_teams()
        # We have data for team_size=3 but not 2
        result = svc.recommend_learned_team("code_review", team_size=2)
        assert result["fallback_used"] is True

    def test_samples_field(self):
        svc = self._make_service_with_teams()
        result = svc.recommend_learned_team("code_review", team_size=3)
        assert result["samples"] == 10


# ============================================================
# get_best_pairs
# ============================================================


class TestGetBestPairs:

    def _make_service(self):
        svc = MetacognitionService()
        svc._auto_save = False
        # Forge+Keystone team with high success
        for i in range(10):
            svc.record_team_outcome(["Forge", "Keystone"], "code_review", success=True)
        # Forge+Echo team with lower success
        for i in range(10):
            svc.record_team_outcome(["Forge", "Echo"], "code_review", success=i < 5)
        return svc

    def test_returns_sorted_pairs(self):
        svc = self._make_service()
        pairs = svc.get_best_pairs()
        assert len(pairs) >= 2
        assert pairs[0]["success_rate"] >= pairs[1]["success_rate"]

    def test_filter_by_task_type(self):
        svc = self._make_service()
        svc.record_team_outcome(["Keystone", "Echo"], "market_research", success=True)
        svc.record_team_outcome(["Keystone", "Echo"], "market_research", success=True)
        svc.record_team_outcome(["Keystone", "Echo"], "market_research", success=True)
        pairs = svc.get_best_pairs(task_type="market_research")
        assert len(pairs) == 1
        assert pairs[0]["pair"] == ["Echo", "Keystone"]

    def test_limit(self):
        svc = self._make_service()
        pairs = svc.get_best_pairs(limit=1)
        assert len(pairs) == 1

    def test_minimum_pair_samples(self):
        svc = MetacognitionService()
        svc._auto_save = False
        # Only 1 outcome — below MIN_PAIR_SAMPLES
        svc.record_team_outcome(["Forge", "Keystone"], "code_review", success=True)
        pairs = svc.get_best_pairs()
        assert len(pairs) == 0

    def test_three_agent_team_extracts_pairs(self):
        svc = MetacognitionService()
        svc._auto_save = False
        for i in range(5):
            svc.record_team_outcome(["Forge", "Keystone", "Echo"], "code_review", success=True)
        pairs = svc.get_best_pairs()
        # Should extract 3 pairs: Forge-Keystone, Forge-Echo, Keystone-Echo
        assert len(pairs) == 3
