"""Tests for the MetacognitionService."""

import json
import os
import tempfile
import pytest

from ag3ntwerk.modules.metacognition.service import MetacognitionService
from ag3ntwerk.core.personality import (
    PersonalityProfile,
    PERSONALITY_SEEDS,
    MIN_SAMPLES_FOR_EVOLUTION,
    create_seeded_profile,
)


class TestMetacognitionServiceRegistration:
    """Tests for agent registration."""

    def test_register_agent_with_seeds(self):
        svc = MetacognitionService()
        profile = svc.register_agent("Forge")
        assert profile.agent_code == "Forge"
        assert svc.is_registered("Forge")

    def test_register_agent_with_custom_traits(self):
        svc = MetacognitionService()
        profile = svc.register_agent(
            "Forge",
            seed_traits={
                "risk": 0.9,
                "creativity": 0.9,
                "thoroughness": 0.1,
                "assertiveness": 0.5,
                "collaboration": 0.5,
                "adaptability": 0.5,
                "decision": "decisive",
                "communication": "direct",
            },
        )
        assert abs(profile.risk_tolerance.value - 0.9) < 1e-9

    def test_register_multiple_agents(self):
        svc = MetacognitionService()
        for code in ["Forge", "Echo", "Keystone"]:
            svc.register_agent(code)
        assert len(svc.get_all_profiles()) == 3

    def test_is_registered(self):
        svc = MetacognitionService()
        assert svc.is_registered("Forge") is False
        svc.register_agent("Forge")
        assert svc.is_registered("Forge") is True


class TestMetacognitionServiceTaskCompletion:
    """Tests for task completion processing."""

    def test_on_task_completed_success(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        result = svc.on_task_completed(
            agent_code="Forge",
            task_id="task1",
            task_type="code_review",
            success=True,
            duration_ms=100.0,
        )
        assert result is not None
        assert result.success is True
        assert result.agent_code == "Forge"

    def test_on_task_completed_failure(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        result = svc.on_task_completed(
            agent_code="Forge",
            task_id="task1",
            task_type="code_review",
            success=False,
            error="timeout",
        )
        assert result is not None
        assert result.success is False

    def test_on_task_completed_unregistered(self):
        svc = MetacognitionService()
        result = svc.on_task_completed(
            agent_code="UNKNOWN",
            task_id="task1",
            task_type="test",
            success=True,
        )
        assert result is None

    def test_outcomes_buffered(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        for i in range(5):
            svc.on_task_completed("Forge", f"task{i}", "test", True)
        assert svc.task_outcomes_count == 5

    def test_outcomes_capped_at_1000(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        for i in range(1100):
            svc.on_task_completed("Forge", f"task{i}", "test", True)
        assert svc.task_outcomes_count <= 1000


class TestMetacognitionServiceReflection:
    """Tests for system reflection."""

    def test_system_reflect(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.register_agent("Echo")
        reflection = svc.system_reflect(
            agent_health={
                "Forge": {"health_score": 0.9, "success_rate": 0.85, "total_tasks": 50},
                "Echo": {"health_score": 0.7, "success_rate": 0.70, "total_tasks": 30},
            }
        )
        assert 0.0 <= reflection.overall_health_score <= 1.0
        assert svc._system_reflection_count == 1

    def test_system_reflect_without_health(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        reflection = svc.system_reflect()
        assert isinstance(reflection.overall_health_score, float)

    def test_system_reflect_with_compatibility_issues(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.register_agent("Echo")
        issues = [{"description": "Forge-Echo clash", "recommendation": "stagger", "severity": 0.6}]
        reflection = svc.system_reflect(
            agent_health={"Forge": {"health_score": 0.9, "success_rate": 0.85, "total_tasks": 10}},
            compatibility_issues=issues,
        )
        assert isinstance(reflection.overall_health_score, float)
        assert svc._system_reflection_count == 1


class TestMetacognitionServicePersonality:
    """Tests for personality access."""

    def test_get_personality_prompt(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        prompt = svc.get_personality_prompt("Forge")
        assert "Forge" in prompt
        assert len(prompt) > 0

    def test_get_personality_prompt_unregistered(self):
        svc = MetacognitionService()
        prompt = svc.get_personality_prompt("UNKNOWN")
        assert prompt == ""

    def test_get_profile(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        profile = svc.get_profile("Forge")
        assert profile is not None
        assert profile.agent_code == "Forge"

    def test_get_profile_missing(self):
        svc = MetacognitionService()
        assert svc.get_profile("UNKNOWN") is None


class TestMetacognitionServiceHeuristics:
    """Tests for heuristic operations."""

    def test_get_heuristic_actions(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        actions = svc.get_heuristic_actions(
            "Forge",
            context={"consecutive_failures": 5},
        )
        assert isinstance(actions, list)
        assert len(actions) > 0  # failure_recovery should fire

    def test_get_heuristic_actions_unregistered(self):
        svc = MetacognitionService()
        actions = svc.get_heuristic_actions("UNKNOWN")
        assert actions == []

    def test_tune_heuristics_all(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        results = svc.tune_heuristics()
        assert isinstance(results, list)

    def test_tune_heuristics_single(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        results = svc.tune_heuristics("Forge")
        assert isinstance(results, list)

    def test_record_heuristic_outcome(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        actions = svc.get_heuristic_actions("Forge", context={"consecutive_failures": 5})
        if actions:
            svc.record_heuristic_outcome("Forge", actions[0].heuristic_id, True)


class TestMetacognitionServicePersistence:
    """Tests for profile persistence."""

    def test_save_and_load_profiles(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.register_agent("Echo")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            svc.save_profiles(path)

            svc2 = MetacognitionService()
            loaded = svc2.load_profiles(path)
            assert loaded == 2
            assert svc2.is_registered("Forge")
            assert svc2.is_registered("Echo")

            # Verify profile data preserved
            cto = svc2.get_profile("Forge")
            assert cto.agent_code == "Forge"
            assert cto.decision_style == "analytical"
        finally:
            os.unlink(path)

    def test_load_nonexistent_file(self):
        svc = MetacognitionService()
        loaded = svc.load_profiles("/nonexistent/path.json")
        assert loaded == 0

    def test_load_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            path = f.name
        try:
            svc = MetacognitionService()
            loaded = svc.load_profiles(path)
            assert loaded == 0
        finally:
            os.unlink(path)


class TestMetacognitionServiceStats:
    """Tests for statistics."""

    def test_get_stats(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.on_task_completed("Forge", "task1", "test", True)
        stats = svc.get_stats()
        assert "registered_agents" in stats
        assert "Forge" in stats["registered_agents"]
        assert stats["total_reflections"] == 1
        assert "profiles" in stats
        assert "heuristics" in stats

    def test_stats_empty_service(self):
        svc = MetacognitionService()
        stats = svc.get_stats()
        assert stats["registered_agents"] == []
        assert stats["total_reflections"] == 0


class TestMetacognitionServiceIntegration:
    """Integration tests combining multiple components."""

    def test_full_lifecycle(self):
        """Test register -> process tasks -> reflect -> evolve -> stats."""
        svc = MetacognitionService()

        # Register all 16 agents
        for code in PERSONALITY_SEEDS:
            svc.register_agent(code)
        assert len(svc.get_all_profiles()) == 16

        # Process some tasks
        for i in range(10):
            svc.on_task_completed("Forge", f"task{i}", "code_review", i % 3 != 0)
            svc.on_task_completed("Echo", f"task{i}", "campaign", True)

        # System reflection
        reflection = svc.system_reflect(
            agent_health={
                "Forge": {"health_score": 0.8, "success_rate": 0.7, "total_tasks": 10},
                "Echo": {"health_score": 1.0, "success_rate": 1.0, "total_tasks": 10},
            }
        )
        assert reflection.overall_health_score > 0

        # Tune heuristics
        tunings = svc.tune_heuristics()
        assert isinstance(tunings, list)

        # Get stats
        stats = svc.get_stats()
        assert stats["total_reflections"] == 20
        assert "Forge" in stats["profiles"]
        assert "Echo" in stats["profiles"]
