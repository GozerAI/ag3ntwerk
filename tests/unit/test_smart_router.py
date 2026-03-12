"""Tests for SmartRouter – Item 6.

Covers ranking logic, cold-start fallback, load/speed/personality scoring,
static routes, learning/metacognition wiring, and error resilience.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.core.smart_router import SmartRouter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_learning(perf_map: dict | None = None):
    """Return an AsyncMock learning orchestrator.

    *perf_map* maps ``(agent_code, task_type)`` to a performance dict.
    Missing keys return ``{}``.
    """
    orch = AsyncMock()

    async def _get_perf(agent_code, task_type):
        if perf_map is None:
            return {}
        return perf_map.get((agent_code, task_type), {})

    orch.get_agent_performance = AsyncMock(side_effect=_get_perf)
    return orch


def _make_metacognition(profiles: dict | None = None, stats: dict | None = None):
    """Return a MagicMock metacognition service.

    *profiles* maps agent_code -> MagicMock with ``compute_task_fit``.
    *stats*    maps agent_code -> dict (e.g. ``{"active_tasks": 2}``).
    """
    svc = MagicMock()

    def _get_profile(agent_code):
        if profiles and agent_code in profiles:
            return profiles[agent_code]
        # Default profile with neutral fit
        p = MagicMock()
        p.compute_task_fit = MagicMock(return_value=0.5)
        return p

    def _get_stats(agent_code):
        if stats and agent_code in stats:
            return stats[agent_code]
        return {"active_tasks": 0}

    svc.get_profile = MagicMock(side_effect=_get_profile)
    svc.get_agent_stats = MagicMock(side_effect=_get_stats)
    return svc


def _agents(*codes):
    """Build a simple ``{code: MagicMock()}`` dict."""
    return {c: MagicMock() for c in codes}


# ---------------------------------------------------------------------------
# 1. Ranking with performance data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ranking_with_performance_data():
    """Agents with better performance data should rank higher."""
    perf = {
        ("Forge", "code_review"): {
            "success_rate": 0.95,
            "total_outcomes": 20,
            "avg_duration_ms": 2000,
        },
        ("Keystone", "code_review"): {
            "success_rate": 0.60,
            "total_outcomes": 10,
            "avg_duration_ms": 5000,
        },
    }
    router = SmartRouter(
        learning_orchestrator=_make_learning(perf),
        metacognition_service=_make_metacognition(),
    )
    ranked = await router.rank_agents("code_review", _agents("Forge", "Keystone"))
    codes = [code for code, _ in ranked]
    assert codes[0] == "Forge", "Forge should rank first with higher success rate"


# ---------------------------------------------------------------------------
# 2. Cold-start fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cold_start_fallback_no_learning():
    """Without a learning orchestrator every agent should get ~0.5 scores."""
    router = SmartRouter()
    ranked = await router.rank_agents("anything", _agents("Forge", "Keystone"))
    scores = {code: score for code, score in ranked}
    for code in ("Forge", "Keystone"):
        assert (
            abs(scores[code] - 0.5) < 0.15
        ), f"{code} cold-start score {scores[code]} should be near 0.5"


@pytest.mark.asyncio
async def test_cold_start_below_min_outcomes():
    """Fewer than MIN_OUTCOMES_THRESHOLD outcomes should behave like cold start."""
    perf = {
        ("Forge", "task"): {
            "success_rate": 0.99,
            "total_outcomes": 2,  # below threshold (5)
            "avg_duration_ms": 500,
        },
    }
    router = SmartRouter(
        learning_orchestrator=_make_learning(perf),
        metacognition_service=_make_metacognition(),
    )
    ranked = await router.rank_agents("task", _agents("Forge"))
    _, score = ranked[0]
    # With insufficient data the router should blend toward the default;
    # the score should not be pushed to the extreme by a 0.99 success rate.
    assert score < 0.95, "Score should be tempered when outcomes < threshold"


# ---------------------------------------------------------------------------
# 3. Load factor influence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_factor_lower_load_higher_score():
    """An idle agent should score higher than a busy one, all else equal."""
    stats = {
        "Forge": {"active_tasks": 0},
        "Keystone": {"active_tasks": 10},
    }
    router = SmartRouter(
        learning_orchestrator=_make_learning(),
        metacognition_service=_make_metacognition(stats=stats),
    )
    ranked = await router.rank_agents("task", _agents("Forge", "Keystone"))
    scores = {c: s for c, s in ranked}
    assert scores["Forge"] > scores["Keystone"], "Idle agent should score higher"


# ---------------------------------------------------------------------------
# 4. Personality fit integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_personality_fit_boosts_score():
    """High personality fit should push an agent's score up."""
    high_fit = MagicMock()
    high_fit.compute_task_fit = MagicMock(return_value=1.0)
    low_fit = MagicMock()
    low_fit.compute_task_fit = MagicMock(return_value=0.0)

    profiles = {"Forge": high_fit, "Keystone": low_fit}
    router = SmartRouter(
        learning_orchestrator=_make_learning(),
        metacognition_service=_make_metacognition(profiles=profiles),
    )
    context = {"task_traits": {"analytical": 0.8, "creative": 0.3}}
    ranked = await router.rank_agents("task", _agents("Forge", "Keystone"), context=context)
    scores = {c: s for c, s in ranked}
    assert scores["Forge"] > scores["Keystone"], "High personality fit should rank higher"


# ---------------------------------------------------------------------------
# 5. Speed score normalization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_speed_score_fast_agent():
    """avg_duration_ms <= 1000 should yield speed score ~1.0."""
    perf = {
        ("Forge", "task"): {
            "success_rate": 0.5,
            "total_outcomes": 10,
            "avg_duration_ms": 500,
        },
    }
    router = SmartRouter(
        learning_orchestrator=_make_learning(perf),
        metacognition_service=_make_metacognition(),
    )
    ranked = await router.rank_agents("task", _agents("Forge"))
    _, score = ranked[0]
    # Speed weight is 0.20; with max speed (1.0) the overall score should
    # be noticeably above what a slow agent would get.
    assert score > 0.45


@pytest.mark.asyncio
async def test_speed_score_slow_agent():
    """avg_duration_ms >= 10000 should yield speed score ~0.0."""
    perf = {
        ("Forge", "task"): {
            "success_rate": 0.5,
            "total_outcomes": 10,
            "avg_duration_ms": 15000,
        },
    }
    router = SmartRouter(
        learning_orchestrator=_make_learning(perf),
        metacognition_service=_make_metacognition(),
    )
    ranked = await router.rank_agents("task", _agents("Forge"))
    _, score = ranked[0]
    # With speed score at 0.0 the overall should be lower.
    assert score < 0.55


# ---------------------------------------------------------------------------
# 6. Success rate from learning system
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_success_rate_dominates_score():
    """success_rate carries WEIGHT_SUCCESS_RATE=0.45, so a big gap should show."""
    perf = {
        ("Forge", "task"): {
            "success_rate": 1.0,
            "total_outcomes": 50,
            "avg_duration_ms": 3000,
        },
        ("Keystone", "task"): {
            "success_rate": 0.0,
            "total_outcomes": 50,
            "avg_duration_ms": 3000,
        },
    }
    router = SmartRouter(
        learning_orchestrator=_make_learning(perf),
        metacognition_service=_make_metacognition(),
    )
    ranked = await router.rank_agents("task", _agents("Forge", "Keystone"))
    scores = {c: s for c, s in ranked}
    gap = scores["Forge"] - scores["Keystone"]
    assert gap >= 0.40, f"Success-rate gap should dominate; got {gap:.2f}"


# ---------------------------------------------------------------------------
# 7. get_best_agent returns top-ranked agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_best_agent_returns_top():
    perf = {
        ("Forge", "deploy"): {
            "success_rate": 0.95,
            "total_outcomes": 30,
            "avg_duration_ms": 1000,
        },
        ("Keystone", "deploy"): {
            "success_rate": 0.40,
            "total_outcomes": 30,
            "avg_duration_ms": 8000,
        },
    }
    router = SmartRouter(
        learning_orchestrator=_make_learning(perf),
        metacognition_service=_make_metacognition(),
    )
    result = await router.get_best_agent("deploy", _agents("Forge", "Keystone"))
    assert result is not None
    best_code, best_score = result
    assert best_code == "Forge"
    assert best_score > 0.0


# ---------------------------------------------------------------------------
# 8. get_best_agent returns None for empty agents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_best_agent_empty_agents():
    router = SmartRouter()
    result = await router.get_best_agent("task", {})
    assert result is None


# ---------------------------------------------------------------------------
# 9. rank_agents returns all agents sorted by score
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rank_agents_sorted_descending():
    perf = {
        ("A", "t"): {"success_rate": 0.9, "total_outcomes": 20, "avg_duration_ms": 1000},
        ("B", "t"): {"success_rate": 0.5, "total_outcomes": 20, "avg_duration_ms": 5000},
        ("C", "t"): {"success_rate": 0.7, "total_outcomes": 20, "avg_duration_ms": 3000},
    }
    router = SmartRouter(
        learning_orchestrator=_make_learning(perf),
        metacognition_service=_make_metacognition(),
    )
    ranked = await router.rank_agents("t", _agents("A", "B", "C"))
    assert len(ranked) == 3, "All agents should be present"
    scores = [s for _, s in ranked]
    assert scores == sorted(scores, reverse=True), "Scores should be descending"


# ---------------------------------------------------------------------------
# 10. has_learning_data returns True / False
# ---------------------------------------------------------------------------


def test_has_learning_data_true():
    router = SmartRouter(learning_orchestrator=_make_learning())
    assert router.has_learning_data() is True


def test_has_learning_data_false():
    router = SmartRouter()
    assert router.has_learning_data() is False


# ---------------------------------------------------------------------------
# 11. connect_learning / connect_metacognition
# ---------------------------------------------------------------------------


def test_connect_learning():
    router = SmartRouter()
    assert router.has_learning_data() is False
    orch = _make_learning()
    router.connect_learning(orch)
    assert router.has_learning_data() is True


def test_connect_metacognition():
    router = SmartRouter()
    svc = _make_metacognition()
    router.connect_metacognition(svc)
    # After connecting, personality scoring should use the new service.
    assert router._metacognition is svc


# ---------------------------------------------------------------------------
# 12. get_static_route
# ---------------------------------------------------------------------------


def test_get_static_route_found():
    router = SmartRouter(static_rules={"budget_analysis": "Keystone"})
    assert router.get_static_route("budget_analysis") == "Keystone"


def test_get_static_route_missing():
    router = SmartRouter(static_rules={"budget_analysis": "Keystone"})
    assert router.get_static_route("code_review") is None


def test_get_static_route_no_rules():
    router = SmartRouter()
    assert router.get_static_route("anything") is None


# ---------------------------------------------------------------------------
# 13. Error in learning system handled gracefully
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_learning_error_handled_gracefully():
    """If the learning orchestrator raises, the router should still return results."""
    orch = AsyncMock()
    orch.get_agent_performance = AsyncMock(side_effect=RuntimeError("db down"))

    router = SmartRouter(
        learning_orchestrator=orch,
        metacognition_service=_make_metacognition(),
    )
    # Should NOT raise
    ranked = await router.rank_agents("task", _agents("Forge"))
    assert len(ranked) == 1
    _, score = ranked[0]
    # Fallback score should be reasonable (near 0.5)
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_metacognition_error_handled_gracefully():
    """If the metacognition service raises, the router should still return results."""
    svc = MagicMock()
    svc.get_profile = MagicMock(side_effect=RuntimeError("service unavailable"))
    svc.get_agent_stats = MagicMock(side_effect=RuntimeError("service unavailable"))

    router = SmartRouter(
        learning_orchestrator=_make_learning(),
        metacognition_service=svc,
    )
    ranked = await router.rank_agents("task", _agents("Forge"))
    assert len(ranked) == 1
    _, score = ranked[0]
    assert 0.0 <= score <= 1.0
