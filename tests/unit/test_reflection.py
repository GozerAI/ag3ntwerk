"""Tests for the reflection system."""

import pytest

from ag3ntwerk.core.reflection import (
    ReflectionResult,
    SystemReflection,
    AgentReflector,
    SystemReflector,
)


class TestReflectionResult:
    """Tests for ReflectionResult."""

    def test_creation(self):
        r = ReflectionResult(agent_code="Forge", task_type="code_review", success=True)
        assert r.agent_code == "Forge"
        assert r.success is True
        assert r.reflection_mode == "heuristic"

    def test_to_dict(self):
        r = ReflectionResult(agent_code="Forge", task_type="test")
        d = r.to_dict()
        assert d["agent_code"] == "Forge"
        assert "what_went_well" in d
        assert "trait_signals" in d


class TestSystemReflection:
    """Tests for SystemReflection."""

    def test_creation(self):
        sr = SystemReflection()
        assert sr.overall_health_score == 1.0
        assert len(sr.system_recommendations) == 0

    def test_to_dict(self):
        sr = SystemReflection(overall_health_score=0.8)
        d = sr.to_dict()
        assert d["overall_health_score"] == 0.8


class TestAgentReflector:
    """Tests for AgentReflector."""

    def test_creation(self):
        r = AgentReflector("Forge")
        assert r.agent_code == "Forge"
        assert r.reflection_count == 0

    def test_heuristic_reflection_success(self):
        r = AgentReflector("Forge")
        result = r.reflect_heuristic(
            task_id="task1",
            task_type="code_review",
            success=True,
            duration_ms=100.0,
        )
        assert result.success is True
        assert result.reflection_mode == "heuristic"
        assert result.agent_code == "Forge"
        assert len(result.what_went_well) > 0
        assert r.reflection_count == 1

    def test_heuristic_reflection_failure(self):
        r = AgentReflector("Forge")
        result = r.reflect_heuristic(
            task_id="task1",
            task_type="code_review",
            success=False,
            error="timeout",
        )
        assert result.success is False
        assert len(result.what_went_poorly) > 0
        assert result.root_cause == "timeout"
        # Should have negative risk_tolerance signal
        assert result.trait_signals.get("risk_tolerance", 0) < 0

    def test_consecutive_success_signals(self):
        r = AgentReflector("Forge")
        for i in range(6):
            result = r.reflect_heuristic(
                task_id=f"task{i}",
                task_type="test",
                success=True,
            )
        # After 5+ consecutive successes, should see risk_tolerance boost
        assert result.trait_signals.get("risk_tolerance", 0) > 0

    def test_consecutive_failure_signals(self):
        r = AgentReflector("Forge")
        for i in range(4):
            result = r.reflect_heuristic(
                task_id=f"task{i}",
                task_type="test",
                success=False,
                error="failed",
            )
        # After 3+ failures, should see collaboration boost
        assert result.trait_signals.get("collaboration", 0) > 0
        assert len(result.heuristic_suggestions) > 0

    def test_confidence_analysis_overconfidence(self):
        r = AgentReflector("Forge")
        result = r.reflect_heuristic(
            task_id="task1",
            task_type="test",
            success=False,
            confidence=0.9,
        )
        # High confidence + failure = overconfidence
        assert "overconfidence" in " ".join(result.what_went_poorly).lower()

    def test_confidence_analysis_underconfidence(self):
        r = AgentReflector("Forge")
        result = r.reflect_heuristic(
            task_id="task1",
            task_type="test",
            success=True,
            confidence=0.2,
        )
        # Low confidence + success = underestimating
        assert "underestimating" in " ".join(result.what_went_well).lower()

    def test_duration_analysis_fast(self):
        r = AgentReflector("Forge")
        # First task sets the baseline
        r.reflect_heuristic("task0", "test", True, duration_ms=1000.0)
        r.reflect_heuristic("task1", "test", True, duration_ms=1000.0)
        # Now a very fast task
        result = r.reflect_heuristic("task2", "test", True, duration_ms=100.0)
        assert any("faster" in w.lower() for w in result.what_went_well)

    def test_duration_analysis_slow(self):
        r = AgentReflector("Forge")
        r.reflect_heuristic("task0", "test", True, duration_ms=100.0)
        r.reflect_heuristic("task1", "test", True, duration_ms=100.0)
        result = r.reflect_heuristic("task2", "test", True, duration_ms=500.0)
        assert any("longer" in w.lower() for w in result.what_went_poorly)

    def test_update_personality_context(self):
        r = AgentReflector("Forge")
        r.update_personality_context("New context")
        assert r._personality_context == "New context"

    def test_get_recent_reflections(self):
        r = AgentReflector("Forge")
        for i in range(5):
            r.reflect_heuristic(f"task{i}", "test", True)
        recent = r.get_recent_reflections(limit=3)
        assert len(recent) == 3

    def test_get_stats(self):
        r = AgentReflector("Forge")
        r.reflect_heuristic("task1", "test", True)
        stats = r.get_stats()
        assert stats["agent_code"] == "Forge"
        assert stats["total_reflections"] == 1

    @pytest.mark.asyncio
    async def test_llm_reflection_fallback(self):
        """LLM reflection should fall back to heuristic when no LLM available."""
        r = AgentReflector("Forge")
        result = await r.reflect_llm(
            task_id="task1",
            task_type="test",
            success=True,
            llm_provider=None,
        )
        assert result.reflection_mode == "heuristic"


class TestSystemReflector:
    """Tests for SystemReflector."""

    def test_creation(self):
        sr = SystemReflector()
        assert sr.reflection_count == 0

    def test_basic_reflection(self):
        sr = SystemReflector()
        reflection = sr.reflect(agent_health={})
        assert isinstance(reflection, SystemReflection)
        assert sr.reflection_count == 1

    def test_reflection_with_health(self):
        sr = SystemReflector()
        health = {
            "Forge": {"health_score": 0.9, "success_rate": 0.85, "total_tasks": 50},
            "Echo": {"health_score": 0.6, "success_rate": 0.70, "total_tasks": 30},
        }
        reflection = sr.reflect(agent_health=health)
        assert 0.0 <= reflection.overall_health_score <= 1.0
        assert "Forge" in reflection.agent_performance_summary
        assert "Echo" in reflection.agent_performance_summary

    def test_low_health_generates_recommendation(self):
        sr = SystemReflector()
        health = {
            "Forge": {"health_score": 0.3, "success_rate": 0.3, "total_tasks": 100},
            "Echo": {"health_score": 0.4, "success_rate": 0.4, "total_tasks": 100},
        }
        reflection = sr.reflect(agent_health=health)
        assert reflection.overall_health_score < 0.7
        assert len(reflection.system_recommendations) > 0

    def test_workload_balance(self):
        sr = SystemReflector()
        # Very unbalanced workload
        health = {
            "Forge": {"health_score": 1.0, "success_rate": 1.0, "total_tasks": 100},
            "Echo": {"health_score": 1.0, "success_rate": 1.0, "total_tasks": 1},
        }
        reflection = sr.reflect(agent_health=health)
        assert reflection.workload_balance_score < 1.0

    def test_routing_optimality_from_drift(self):
        sr = SystemReflector()
        drift = {"unresolved_count": 5}
        reflection = sr.reflect(
            agent_health={},
            drift_summary=drift,
        )
        assert reflection.routing_optimality < 1.0

    def test_personality_coherence(self):
        sr = SystemReflector()
        profiles = {
            "Forge": {"traits": {"risk_tolerance": {"drift": 0.28}}},
            "Echo": {"traits": {"creativity": {"drift": 0.01}}},
        }
        reflection = sr.reflect(
            agent_health={},
            agent_profiles=profiles,
        )
        # High drift on Forge should lower coherence
        assert reflection.personality_coherence < 1.0
        assert any("Forge" in r for r in reflection.personality_recommendations)

    def test_get_recent_reflections(self):
        sr = SystemReflector()
        for _ in range(3):
            sr.reflect(agent_health={})
        recent = sr.get_recent_reflections(limit=2)
        assert len(recent) == 2

    def test_get_stats(self):
        sr = SystemReflector()
        sr.reflect(
            agent_health={"Forge": {"health_score": 0.9, "total_tasks": 10, "success_rate": 0.9}}
        )
        stats = sr.get_stats()
        assert stats["total_reflections"] == 1
        assert stats["last_health_score"] is not None
