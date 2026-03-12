"""Tests for the heuristic engine."""

import pytest

from ag3ntwerk.core.heuristics import (
    Heuristic,
    HeuristicAction,
    HeuristicEngine,
    TUNE_STEP,
    MIN_SAMPLES,
    MIN_THRESHOLD,
    MAX_THRESHOLD,
    AUTO_DEACTIVATE_THRESHOLD,
    AUTO_DEACTIVATE_MIN_SAMPLES,
)


class TestHeuristic:
    """Tests for the Heuristic dataclass."""

    def test_creation(self):
        h = Heuristic(name="test", threshold=0.5)
        assert h.name == "test"
        assert h.threshold == 0.5
        assert h.is_active is True
        assert h.times_triggered == 0

    def test_threshold_clamped(self):
        h = Heuristic(threshold=1.5)
        assert h.threshold == MAX_THRESHOLD

        h2 = Heuristic(threshold=-0.5)
        assert h2.threshold == MIN_THRESHOLD

    def test_can_fire_active(self):
        h = Heuristic(threshold=0.5, is_active=True)
        assert h.can_fire(0.6) is True
        assert h.can_fire(0.4) is False

    def test_can_fire_inactive(self):
        h = Heuristic(threshold=0.5, is_active=False)
        assert h.can_fire(0.9) is False

    def test_fire_increments_count(self):
        h = Heuristic()
        h.fire()
        assert h.times_triggered == 1
        h.fire()
        assert h.times_triggered == 2

    def test_cooldown(self):
        import time

        h = Heuristic(threshold=0.1, cooldown_seconds=100.0)
        h.fire()
        # Should be on cooldown
        assert h.can_fire(1.0) is False

    def test_record_outcome_updates_rate(self):
        h = Heuristic()
        for _ in range(8):
            h.record_outcome(True)
        for _ in range(2):
            h.record_outcome(False)
        assert abs(h.success_rate - 0.8) < 1e-9

    def test_tune_no_change_without_samples(self):
        h = Heuristic()
        result = h.tune()
        assert result is None

    def test_tune_raises_threshold_on_low_success(self):
        h = Heuristic(threshold=0.5)
        # Give it poor outcomes
        for _ in range(MIN_SAMPLES + 5):
            h.record_outcome(False)  # 0% success
        result = h.tune()
        assert result is not None
        # Should be deactivated at 0% after enough samples
        # Actually with 15 samples and 0% success, it hits deactivation
        if h.total_outcomes >= AUTO_DEACTIVATE_MIN_SAMPLES:
            assert result["action"] == "deactivated"
        else:
            assert "raised" in result["action"]

    def test_tune_lowers_threshold_on_high_success(self):
        h = Heuristic(threshold=0.5)
        for _ in range(MIN_SAMPLES + 5):
            h.record_outcome(True)  # 100% success
        result = h.tune()
        assert result is not None
        assert result["action"] == "threshold_lowered"
        assert h.threshold < 0.5

    def test_auto_deactivate(self):
        h = Heuristic(threshold=0.5)
        for _ in range(AUTO_DEACTIVATE_MIN_SAMPLES):
            h.record_outcome(False)  # 0% success
        result = h.tune()
        assert h.is_active is False
        assert result["action"] == "deactivated"

    def test_to_dict(self):
        h = Heuristic(name="test", agent_code="Forge")
        d = h.to_dict()
        assert d["name"] == "test"
        assert d["agent_code"] == "Forge"


class TestHeuristicAction:
    """Tests for HeuristicAction."""

    def test_creation(self):
        a = HeuristicAction(
            heuristic_id="h1",
            action="increase_thoroughness",
            weight=1.5,
        )
        assert a.action == "increase_thoroughness"

    def test_to_dict(self):
        a = HeuristicAction(heuristic_id="h1", action="test")
        d = a.to_dict()
        assert "heuristic_id" in d
        assert "action" in d


class TestHeuristicEngine:
    """Tests for HeuristicEngine."""

    def test_creation_with_defaults(self):
        engine = HeuristicEngine("Forge")
        assert engine.agent_code == "Forge"
        stats = engine.get_stats()
        assert stats["total_heuristics"] >= 3  # 3 default heuristics

    def test_add_heuristic(self):
        engine = HeuristicEngine("Forge")
        initial = engine.get_stats()["total_heuristics"]
        engine.add_heuristic(Heuristic(name="custom"))
        assert engine.get_stats()["total_heuristics"] == initial + 1

    def test_remove_heuristic(self):
        engine = HeuristicEngine("Forge")
        h = Heuristic(name="custom")
        engine.add_heuristic(h)
        assert engine.remove_heuristic(h.id) is True
        assert engine.remove_heuristic("nonexistent") is False

    def test_get_heuristic(self):
        engine = HeuristicEngine("Forge")
        h = Heuristic(name="custom")
        engine.add_heuristic(h)
        assert engine.get_heuristic(h.id) is not None
        assert engine.get_heuristic("nonexistent") is None

    def test_evaluate_no_context(self):
        engine = HeuristicEngine("Forge")
        actions = engine.evaluate()
        # With no context, relevance scores should be low/zero
        # May or may not produce actions depending on thresholds
        assert isinstance(actions, list)

    def test_evaluate_with_failures(self):
        engine = HeuristicEngine("Forge")
        # Context with consecutive failures should trigger failure_recovery
        actions = engine.evaluate(context={"consecutive_failures": 5})
        action_names = [a.action for a in actions]
        assert "increase_thoroughness" in action_names

    def test_evaluate_with_high_success(self):
        engine = HeuristicEngine("Forge")
        actions = engine.evaluate(context={"recent_success_rate": 0.95})
        action_names = [a.action for a in actions]
        assert "allow_higher_risk" in action_names

    def test_evaluate_with_complexity(self):
        engine = HeuristicEngine("Forge")
        actions = engine.evaluate(context={"task_complexity": 0.9})
        action_names = [a.action for a in actions]
        assert "request_collaboration" in action_names

    def test_record_outcome(self):
        engine = HeuristicEngine("Forge")
        # Get an ID of one of the default heuristics
        stats = engine.get_stats()
        h_id = stats["heuristics"][0]["id"]
        engine.record_outcome(h_id, True)
        h = engine.get_heuristic(h_id)
        assert h.total_outcomes == 1

    def test_tune(self):
        engine = HeuristicEngine("Forge")
        # Not enough samples, should return empty
        results = engine.tune()
        assert isinstance(results, list)

    def test_tune_with_outcomes(self):
        engine = HeuristicEngine("Forge")
        h = Heuristic(name="test_tune", threshold=0.5)
        engine.add_heuristic(h)
        for _ in range(MIN_SAMPLES + 5):
            engine.record_outcome(h.id, True)
        results = engine.tune()
        # Should have tuned the heuristic with 100% success
        tuned = [r for r in results if r.get("heuristic_id") == h.id]
        assert len(tuned) > 0

    def test_get_stats(self):
        engine = HeuristicEngine("Forge")
        stats = engine.get_stats()
        assert stats["agent_code"] == "Forge"
        assert "total_heuristics" in stats
        assert "active_heuristics" in stats
        assert "heuristics" in stats

    def test_threshold_stays_bounded_after_tuning(self):
        """Verify threshold stays within bounds after many tune cycles."""
        engine = HeuristicEngine("Forge")
        h = Heuristic(name="bound_test", threshold=0.5)
        engine.add_heuristic(h)

        # Give it very high success to lower threshold
        for _ in range(100):
            engine.record_outcome(h.id, True)
            h.tune()

        assert h.threshold >= MIN_THRESHOLD
        assert h.threshold <= MAX_THRESHOLD
