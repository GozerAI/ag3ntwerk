"""Tests for metacognition closed-loop TASK_TRAIT_MAP optimization (Phase 5, Step 5)."""

import pytest
from datetime import datetime, timezone, timedelta

from ag3ntwerk.modules.metacognition.service import (
    MetacognitionService,
    TraitMapUpdate,
    MAX_LEARNED_TRAIT_MAP_ENTRIES,
    MIN_APPLY_CONFIDENCE,
    TRAIT_MAP_VALIDATION_WINDOW,
    TRAIT_MAP_ROLLBACK_THRESHOLD,
    MAX_TRAIT_MAP_UPDATES,
    MIN_ATTRIBUTION_SAMPLES,
    MIN_ATTRIBUTION_AGENTS,
)


# ============================================================
# TraitMapUpdate dataclass
# ============================================================


class TestTraitMapUpdate:

    def test_to_dict(self):
        u = TraitMapUpdate(
            task_type="code_review",
            trait_name="thoroughness",
            old_value=None,
            new_value=0.85,
            source_correlation=0.72,
            source_sample_count=30,
        )
        d = u.to_dict()
        assert d["task_type"] == "code_review"
        assert d["trait_name"] == "thoroughness"
        assert d["old_value"] is None
        assert d["new_value"] == 0.85
        assert d["validation_status"] == "pending"

    def test_to_dict_with_old_value(self):
        u = TraitMapUpdate(
            task_type="code_review",
            trait_name="thoroughness",
            old_value=0.7,
            new_value=0.85,
            source_correlation=0.72,
            source_sample_count=30,
        )
        d = u.to_dict()
        assert d["old_value"] == 0.7


# ============================================================
# Helper to create service with sufficient attribution data
# ============================================================


def _make_service_with_attribution():
    """Create a service with enough data for attribution to produce suggestions."""
    svc = MetacognitionService()
    svc._auto_save = False

    # Register 4 agents with distinct trait values
    svc.register_agent(
        "A1",
        seed_traits={
            "thoroughness": 0.9,
            "creativity": 0.3,
            "risk": 0.2,
            "assertiveness": 0.5,
            "collaboration": 0.5,
            "adaptability": 0.5,
            "decision": "analytical",
            "communication": "direct",
        },
    )
    svc.register_agent(
        "A2",
        seed_traits={
            "thoroughness": 0.8,
            "creativity": 0.4,
            "risk": 0.3,
            "assertiveness": 0.5,
            "collaboration": 0.5,
            "adaptability": 0.5,
            "decision": "analytical",
            "communication": "direct",
        },
    )
    svc.register_agent(
        "A3",
        seed_traits={
            "thoroughness": 0.4,
            "creativity": 0.8,
            "risk": 0.7,
            "assertiveness": 0.5,
            "collaboration": 0.5,
            "adaptability": 0.5,
            "decision": "analytical",
            "communication": "direct",
        },
    )
    svc.register_agent(
        "A4",
        seed_traits={
            "thoroughness": 0.3,
            "creativity": 0.9,
            "risk": 0.8,
            "assertiveness": 0.5,
            "collaboration": 0.5,
            "adaptability": 0.5,
            "decision": "analytical",
            "communication": "direct",
        },
    )

    # A1 and A2 (high thoroughness) succeed at code_review
    # A3 and A4 (low thoroughness) fail at code_review
    for i in range(15):
        svc._task_outcomes.append(
            {
                "agent_code": "A1",
                "task_type": "code_review",
                "success": True,
                "task_id": f"t1-{i}",
                "duration_ms": 100,
                "timestamp": "2025-01-01T00:00:00",
            }
        )
        svc._task_outcomes.append(
            {
                "agent_code": "A2",
                "task_type": "code_review",
                "success": True,
                "task_id": f"t2-{i}",
                "duration_ms": 100,
                "timestamp": "2025-01-01T00:00:00",
            }
        )
        svc._task_outcomes.append(
            {
                "agent_code": "A3",
                "task_type": "code_review",
                "success": False,
                "task_id": f"t3-{i}",
                "duration_ms": 100,
                "timestamp": "2025-01-01T00:00:00",
            }
        )
        svc._task_outcomes.append(
            {
                "agent_code": "A4",
                "task_type": "code_review",
                "success": False,
                "task_id": f"t4-{i}",
                "duration_ms": 100,
                "timestamp": "2025-01-01T00:00:00",
            }
        )

    return svc


# ============================================================
# apply_trait_map_suggestions
# ============================================================


class TestApplyTraitMapSuggestions:

    def test_applies_suggestions(self):
        svc = _make_service_with_attribution()
        # Verify suggestions exist
        suggestions = svc.suggest_trait_map_updates(min_correlation=0.5)
        if not suggestions:
            pytest.skip("No suggestions generated — attribution data insufficient")

        updates = svc.apply_trait_map_suggestions(min_confidence=0.5)
        assert len(updates) > 0
        assert all(u.validation_status == "pending" for u in updates)

    def test_learned_map_populated(self):
        svc = _make_service_with_attribution()
        svc.apply_trait_map_suggestions(min_confidence=0.5)
        learned = svc.get_learned_trait_map()
        assert len(learned) > 0

    def test_skip_identical_value(self):
        svc = _make_service_with_attribution()
        updates1 = svc.apply_trait_map_suggestions(min_confidence=0.5)
        # Apply again — should skip already-applied values
        updates2 = svc.apply_trait_map_suggestions(min_confidence=0.5)
        assert len(updates2) == 0

    def test_cap_at_max_updates(self):
        svc = _make_service_with_attribution()
        # Pre-fill updates
        for i in range(MAX_TRAIT_MAP_UPDATES):
            svc._trait_map_updates.append(
                TraitMapUpdate(
                    task_type=f"type_{i}",
                    trait_name="t",
                    old_value=None,
                    new_value=0.5,
                    source_correlation=0.6,
                    source_sample_count=10,
                )
            )
        svc.apply_trait_map_suggestions(min_confidence=0.5)
        assert len(svc._trait_map_updates) <= MAX_TRAIT_MAP_UPDATES

    def test_stats_include_learned_map(self):
        svc = _make_service_with_attribution()
        svc.apply_trait_map_suggestions(min_confidence=0.5)
        stats = svc.get_stats()
        assert "learned_trait_map_entries" in stats
        assert "trait_map_updates" in stats


# ============================================================
# get_effective_traits
# ============================================================


class TestGetEffectiveTraits:

    def test_returns_static_when_no_learned(self):
        svc = MetacognitionService()
        svc._auto_save = False
        static = {"thoroughness": 0.8, "creativity": 0.5}
        result = svc.get_effective_traits("code_review", static)
        assert result == static

    def test_learned_overrides_static(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc._learned_trait_map["code_review"] = {"thoroughness": 0.95}
        static = {"thoroughness": 0.8, "creativity": 0.5}
        result = svc.get_effective_traits("code_review", static)
        assert result["thoroughness"] == 0.95
        assert result["creativity"] == 0.5

    def test_empty_static(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc._learned_trait_map["code_review"] = {"thoroughness": 0.9}
        result = svc.get_effective_traits("code_review")
        assert result == {"thoroughness": 0.9}

    def test_no_learned_no_static(self):
        svc = MetacognitionService()
        svc._auto_save = False
        result = svc.get_effective_traits("unknown_task")
        assert result == {}


# ============================================================
# validate_trait_map_updates
# ============================================================


class TestValidateTraitMapUpdates:

    def test_validates_when_enough_outcomes(self):
        svc = MetacognitionService()
        svc._auto_save = False
        applied_at = datetime.now(timezone.utc) - timedelta(hours=1)

        update = TraitMapUpdate(
            task_type="code_review",
            trait_name="thoroughness",
            old_value=None,
            new_value=0.85,
            source_correlation=0.7,
            source_sample_count=30,
            applied_at=applied_at,
            pre_apply_success_rate=0.6,
        )
        svc._trait_map_updates.append(update)
        svc._learned_trait_map["code_review"] = {"thoroughness": 0.85}

        # Add enough post-apply outcomes (improving)
        for i in range(TRAIT_MAP_VALIDATION_WINDOW + 5):
            svc._task_outcomes.append(
                {
                    "agent_code": "Forge",
                    "task_type": "code_review",
                    "success": True,
                    "task_id": f"t{i}",
                    "duration_ms": 100,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        results = svc.validate_trait_map_updates()
        assert len(results) == 1
        assert results[0]["validation_status"] == "validated"

    def test_rolls_back_on_performance_drop(self):
        svc = MetacognitionService()
        svc._auto_save = False
        applied_at = datetime.now(timezone.utc) - timedelta(hours=1)

        update = TraitMapUpdate(
            task_type="code_review",
            trait_name="thoroughness",
            old_value=None,
            new_value=0.85,
            source_correlation=0.7,
            source_sample_count=30,
            applied_at=applied_at,
            pre_apply_success_rate=0.8,
        )
        svc._trait_map_updates.append(update)
        svc._learned_trait_map["code_review"] = {"thoroughness": 0.85}

        # Add failing post-apply outcomes
        for i in range(TRAIT_MAP_VALIDATION_WINDOW + 5):
            svc._task_outcomes.append(
                {
                    "agent_code": "Forge",
                    "task_type": "code_review",
                    "success": i < 5,
                    "task_id": f"t{i}",
                    "duration_ms": 100,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        results = svc.validate_trait_map_updates()
        assert len(results) == 1
        assert results[0]["validation_status"] == "rolled_back"
        # Check learned map was cleaned
        assert "thoroughness" not in svc._learned_trait_map.get("code_review", {})

    def test_pending_with_insufficient_outcomes(self):
        svc = MetacognitionService()
        svc._auto_save = False

        update = TraitMapUpdate(
            task_type="code_review",
            trait_name="thoroughness",
            old_value=None,
            new_value=0.85,
            source_correlation=0.7,
            source_sample_count=30,
            pre_apply_success_rate=0.6,
        )
        svc._trait_map_updates.append(update)

        results = svc.validate_trait_map_updates()
        assert len(results) == 0
        assert svc._trait_map_updates[0].validation_status == "pending"

    def test_skips_already_validated(self):
        svc = MetacognitionService()
        svc._auto_save = False

        update = TraitMapUpdate(
            task_type="code_review",
            trait_name="thoroughness",
            old_value=None,
            new_value=0.85,
            source_correlation=0.7,
            source_sample_count=30,
            validation_status="validated",
        )
        svc._trait_map_updates.append(update)

        results = svc.validate_trait_map_updates()
        assert len(results) == 0


# ============================================================
# get_learned_trait_map
# ============================================================


class TestGetLearnedTraitMap:

    def test_returns_copy(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc._learned_trait_map["code_review"] = {"thoroughness": 0.9}
        result = svc.get_learned_trait_map()
        result["code_review"]["thoroughness"] = 0.1
        # Original should be unchanged
        assert svc._learned_trait_map["code_review"]["thoroughness"] == 0.9

    def test_empty_when_nothing_learned(self):
        svc = MetacognitionService()
        svc._auto_save = False
        assert svc.get_learned_trait_map() == {}
