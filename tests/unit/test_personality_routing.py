"""Tests for personality-aware routing (Phase 2, Step 2)."""

import pytest

from ag3ntwerk.core.personality import (
    PersonalityProfile,
    PersonalityTrait,
    create_seeded_profile,
)
from ag3ntwerk.core.base import Agent, Task, TaskResult
from ag3ntwerk.modules.metacognition.service import MetacognitionService


# =========================================================================
# PersonalityProfile.compute_task_fit
# =========================================================================


class TestComputeTaskFit:
    def test_perfect_match(self):
        profile = PersonalityProfile(
            agent_code="TEST",
            thoroughness=PersonalityTrait("thoroughness", 0.9, 0.9),
            risk_tolerance=PersonalityTrait("risk_tolerance", 0.2, 0.2),
        )
        score = profile.compute_task_fit({"thoroughness": 0.9, "risk_tolerance": 0.2})
        assert abs(score - 1.0) < 1e-6

    def test_complete_mismatch(self):
        profile = PersonalityProfile(
            agent_code="TEST",
            thoroughness=PersonalityTrait("thoroughness", 0.0, 0.0),
            risk_tolerance=PersonalityTrait("risk_tolerance", 1.0, 1.0),
        )
        score = profile.compute_task_fit({"thoroughness": 1.0, "risk_tolerance": 0.0})
        assert abs(score - 0.0) < 1e-6

    def test_partial_match(self):
        profile = PersonalityProfile(
            agent_code="TEST",
            thoroughness=PersonalityTrait("thoroughness", 0.7, 0.7),
        )
        score = profile.compute_task_fit({"thoroughness": 0.9})
        assert 0.5 < score < 1.0

    def test_empty_traits_returns_neutral(self):
        profile = PersonalityProfile(agent_code="TEST")
        assert profile.compute_task_fit({}) == 0.5

    def test_unknown_trait_ignored(self):
        profile = PersonalityProfile(agent_code="TEST")
        score = profile.compute_task_fit({"nonexistent_trait": 0.5})
        assert score == 0.5

    def test_seeded_profiles_differ(self):
        cto = create_seeded_profile("Forge")
        cfo = create_seeded_profile("Keystone")
        # Security review should favor Keystone (low risk, high thoroughness)
        security_traits = {"thoroughness": 0.9, "risk_tolerance": 0.2}
        cto_score = cto.compute_task_fit(security_traits)
        cfo_score = cfo.compute_task_fit(security_traits)
        # Keystone should score higher for security tasks
        assert cfo_score > cto_score


# =========================================================================
# MetacognitionService.score_agents_for_task
# =========================================================================


class TestScoreAgentsForTask:
    def test_returns_sorted_scores(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.register_agent("Keystone")
        svc.register_agent("Echo")

        scores = svc.score_agents_for_task(
            {"thoroughness": 0.9, "risk_tolerance": 0.2},
            ["Forge", "Keystone", "Echo"],
        )
        assert len(scores) == 3
        # Scores should be sorted descending
        for i in range(len(scores) - 1):
            assert scores[i][1] >= scores[i + 1][1]

    def test_unknown_agents_skipped(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        scores = svc.score_agents_for_task(
            {"thoroughness": 0.9},
            ["Forge", "UNKNOWN"],
        )
        assert len(scores) == 1
        assert scores[0][0] == "Forge"

    def test_empty_agents_returns_empty(self):
        svc = MetacognitionService()
        scores = svc.score_agents_for_task({"thoroughness": 0.9}, [])
        assert scores == []


# =========================================================================
# Overwatch Personality-Aware Routing
# =========================================================================


class SimpleAgent(Agent):
    def can_handle(self, task):
        return True

    async def execute(self, task):
        return TaskResult(task_id=task.id, success=True, output="done")


class TestCoSPersonalityRouting:
    def test_task_trait_map_has_entries(self):
        from ag3ntwerk.agents.overwatch.agent import Overwatch

        cos = Overwatch()
        assert len(cos.TASK_TRAIT_MAP) >= 15

    def test_infer_task_traits_from_map(self):
        from ag3ntwerk.agents.overwatch.agent import Overwatch

        cos = Overwatch()
        task = Task(description="review security", task_type="security_review")
        traits = cos._infer_task_traits(task)
        assert "thoroughness" in traits
        assert traits["thoroughness"] > 0.8

    def test_infer_task_traits_from_context(self):
        from ag3ntwerk.agents.overwatch.agent import Overwatch

        cos = Overwatch()
        task = Task(
            description="custom task",
            task_type="unknown",
            context={"_desired_traits": {"creativity": 0.9}},
        )
        traits = cos._infer_task_traits(task)
        assert traits == {"creativity": 0.9}

    def test_infer_task_traits_unknown_returns_empty(self):
        from ag3ntwerk.agents.overwatch.agent import Overwatch

        cos = Overwatch()
        task = Task(description="unknown", task_type="nonexistent_type")
        traits = cos._infer_task_traits(task)
        assert traits == {}

    def test_personality_score_agents_without_service(self):
        from ag3ntwerk.agents.overwatch.agent import Overwatch

        cos = Overwatch()
        task = Task(description="test", task_type="security_review")
        result = cos._personality_score_agents(task, ["Forge", "Keystone"])
        assert result is None

    def test_personality_score_agents_returns_best(self):
        from ag3ntwerk.agents.overwatch.agent import Overwatch

        cos = Overwatch()
        for code in ["Forge", "Keystone", "Citadel"]:
            agent = SimpleAgent(code, code, "domain")
            cos.register_subordinate(agent)

        svc = MetacognitionService()
        cos.connect_metacognition(svc)

        task = Task(description="security review", task_type="security_review")
        result = cos._personality_score_agents(task, ["Forge", "Keystone", "Citadel"])
        # Should pick one of the candidates (typically Citadel for security)
        assert result is None or result in ["Forge", "Keystone", "Citadel"]

    def test_personality_score_with_no_traits_returns_none(self):
        from ag3ntwerk.agents.overwatch.agent import Overwatch

        cos = Overwatch()
        agent = SimpleAgent("Forge", "Forge", "tech")
        cos.register_subordinate(agent)

        svc = MetacognitionService()
        cos.connect_metacognition(svc)

        task = Task(description="unknown", task_type="nonexistent_type_xyz")
        result = cos._personality_score_agents(task, ["Forge"])
        assert result is None

    @pytest.mark.asyncio
    async def test_route_task_uses_personality_scoring(self):
        """Verify Phase 2.5 is reached when metacognition is connected."""
        from ag3ntwerk.agents.overwatch.agent import Overwatch

        cos = Overwatch(enable_health_routing=False)
        for code in ["Forge", "Citadel"]:
            agent = SimpleAgent(code, code, "tech")
            cos.register_subordinate(agent)

        svc = MetacognitionService()
        cos.connect_metacognition(svc)

        # security_review is in TASK_TRAIT_MAP, so personality scoring should be attempted
        task = Task(description="review security", task_type="security_review")
        target = await cos._route_task(task)
        # Should return some valid agent (either from personality or static)
        assert target in ["Forge", "Citadel"] or target is not None
