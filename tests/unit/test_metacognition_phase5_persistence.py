"""Tests for Phase 5 state persistence (save/load of snapshots, teams, learned map, etc.)."""

import json
import os
import pytest
from datetime import datetime, timezone, timedelta

from ag3ntwerk.modules.metacognition.service import (
    MetacognitionService,
    TraitSnapshot,
    TeamOutcome,
    TraitMapUpdate,
    PeerRecommendation,
    MAX_TRAIT_SNAPSHOTS,
    MAX_TEAM_OUTCOMES,
    MAX_LEARNED_TRAIT_MAP_ENTRIES,
    MAX_TRAIT_MAP_UPDATES,
    MAX_PEER_RECOMMENDATIONS,
)


# ============================================================
# save_phase5_state
# ============================================================


class TestSavePhase5State:

    def test_creates_file(self, tmp_path):
        svc = MetacognitionService()
        svc._auto_save = False
        path = str(tmp_path / "phase5_state.json")
        svc.save_phase5_state(path)
        assert os.path.exists(path)

    def test_saves_snapshots(self, tmp_path):
        svc = MetacognitionService()
        svc._auto_save = False
        svc._trait_snapshots.append(
            TraitSnapshot(
                agent_code="Forge",
                trait_values={"thoroughness": 0.8},
                trait_baselines={"thoroughness": 0.7},
            )
        )
        path = str(tmp_path / "phase5_state.json")
        svc.save_phase5_state(path)
        with open(path) as f:
            data = json.load(f)
        assert len(data["trait_snapshots"]) == 1
        assert data["trait_snapshots"][0]["agent_code"] == "Forge"

    def test_saves_team_outcomes(self, tmp_path):
        svc = MetacognitionService()
        svc._auto_save = False
        svc._team_outcomes.append(
            TeamOutcome(
                team=["Forge", "Keystone"],
                task_type="code_review",
                success=True,
                task_id="t1",
            )
        )
        path = str(tmp_path / "phase5_state.json")
        svc.save_phase5_state(path)
        with open(path) as f:
            data = json.load(f)
        assert len(data["team_outcomes"]) == 1

    def test_saves_learned_trait_map(self, tmp_path):
        svc = MetacognitionService()
        svc._auto_save = False
        svc._learned_trait_map["code_review"] = {"thoroughness": 0.9}
        path = str(tmp_path / "phase5_state.json")
        svc.save_phase5_state(path)
        with open(path) as f:
            data = json.load(f)
        assert data["learned_trait_map"]["code_review"]["thoroughness"] == 0.9

    def test_caps_snapshots_at_max(self, tmp_path):
        svc = MetacognitionService()
        svc._auto_save = False
        for i in range(MAX_TRAIT_SNAPSHOTS + 100):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.5},
                    trait_baselines={"thoroughness": 0.5},
                )
            )
        path = str(tmp_path / "phase5_state.json")
        svc.save_phase5_state(path)
        with open(path) as f:
            data = json.load(f)
        assert len(data["trait_snapshots"]) == MAX_TRAIT_SNAPSHOTS

    def test_caps_peer_recs_at_100(self, tmp_path):
        svc = MetacognitionService()
        svc._auto_save = False
        for i in range(150):
            svc._peer_recommendations.append(
                PeerRecommendation(
                    target_agent="Keystone",
                    source_agent="Forge",
                    task_type="code_review",
                    recommendation_type="trait_adjustment",
                    trait_name="thoroughness",
                    source_value=0.9,
                    target_value=0.5,
                    suggested_value=0.9,
                    source_success_rate=0.9,
                    target_success_rate=0.5,
                    confidence=0.5,
                )
            )
        path = str(tmp_path / "phase5_state.json")
        svc.save_phase5_state(path)
        with open(path) as f:
            data = json.load(f)
        assert len(data["peer_recommendations"]) == 100


# ============================================================
# load_phase5_state
# ============================================================


class TestLoadPhase5State:

    def test_missing_file_returns_zeros(self, tmp_path):
        svc = MetacognitionService()
        svc._auto_save = False
        path = str(tmp_path / "nonexistent.json")
        counts = svc.load_phase5_state(path)
        assert counts["snapshots"] == 0
        assert counts["team_outcomes"] == 0
        assert counts["learned_map_entries"] == 0

    def test_bad_json_returns_zeros(self, tmp_path):
        path = str(tmp_path / "bad.json")
        with open(path, "w") as f:
            f.write("not valid json{{{")
        svc = MetacognitionService()
        svc._auto_save = False
        counts = svc.load_phase5_state(path)
        assert counts["snapshots"] == 0

    def test_round_trip_snapshots(self, tmp_path):
        svc1 = MetacognitionService()
        svc1._auto_save = False
        ts = datetime.now(timezone.utc) - timedelta(hours=1)
        svc1._trait_snapshots.append(
            TraitSnapshot(
                agent_code="Forge",
                trait_values={"thoroughness": 0.8, "creativity": 0.6},
                trait_baselines={"thoroughness": 0.7, "creativity": 0.5},
                timestamp=ts,
            )
        )
        path = str(tmp_path / "state.json")
        svc1.save_phase5_state(path)

        svc2 = MetacognitionService()
        svc2._auto_save = False
        counts = svc2.load_phase5_state(path)
        assert counts["snapshots"] == 1
        assert len(svc2.trait_snapshots) == 1
        assert svc2.trait_snapshots[0].agent_code == "Forge"
        assert svc2.trait_snapshots[0].trait_values["thoroughness"] == 0.8

    def test_round_trip_team_outcomes(self, tmp_path):
        svc1 = MetacognitionService()
        svc1._auto_save = False
        svc1._team_outcomes.append(
            TeamOutcome(
                team=["Keystone", "Forge"],
                task_type="code_review",
                success=True,
                task_id="t42",
                compatibility_score=0.85,
            )
        )
        path = str(tmp_path / "state.json")
        svc1.save_phase5_state(path)

        svc2 = MetacognitionService()
        svc2._auto_save = False
        counts = svc2.load_phase5_state(path)
        assert counts["team_outcomes"] == 1
        assert svc2.team_outcomes[0].team == ["Keystone", "Forge"]
        assert svc2.team_outcomes[0].success is True

    def test_round_trip_learned_trait_map(self, tmp_path):
        svc1 = MetacognitionService()
        svc1._auto_save = False
        svc1._learned_trait_map["code_review"] = {"thoroughness": 0.92}
        svc1._learned_trait_map["market_research"] = {"creativity": 0.88}
        path = str(tmp_path / "state.json")
        svc1.save_phase5_state(path)

        svc2 = MetacognitionService()
        svc2._auto_save = False
        counts = svc2.load_phase5_state(path)
        assert counts["learned_map_entries"] == 2
        assert svc2.learned_trait_map["code_review"]["thoroughness"] == 0.92

    def test_round_trip_trait_map_updates(self, tmp_path):
        svc1 = MetacognitionService()
        svc1._auto_save = False
        svc1._trait_map_updates.append(
            TraitMapUpdate(
                task_type="code_review",
                trait_name="thoroughness",
                old_value=None,
                new_value=0.85,
                source_correlation=0.72,
                source_sample_count=30,
                validation_status="validated",
                pre_apply_success_rate=0.6,
            )
        )
        path = str(tmp_path / "state.json")
        svc1.save_phase5_state(path)

        svc2 = MetacognitionService()
        svc2._auto_save = False
        counts = svc2.load_phase5_state(path)
        assert counts["trait_map_updates"] == 1
        assert svc2.trait_map_updates[0].validation_status == "validated"
        assert svc2.trait_map_updates[0].new_value == 0.85

    def test_round_trip_peer_recommendations(self, tmp_path):
        svc1 = MetacognitionService()
        svc1._auto_save = False
        svc1._peer_recommendations.append(
            PeerRecommendation(
                target_agent="Keystone",
                source_agent="Forge",
                task_type="code_review",
                recommendation_type="trait_adjustment",
                trait_name="thoroughness",
                source_value=0.9,
                target_value=0.5,
                suggested_value=0.85,
                source_success_rate=0.95,
                target_success_rate=0.4,
                confidence=0.7,
            )
        )
        path = str(tmp_path / "state.json")
        svc1.save_phase5_state(path)

        svc2 = MetacognitionService()
        svc2._auto_save = False
        counts = svc2.load_phase5_state(path)
        assert counts["peer_recommendations"] == 1
        assert svc2.peer_recommendations[0].target_agent == "Keystone"
        assert svc2.peer_recommendations[0].confidence == 0.7

    def test_caps_enforced_on_load(self, tmp_path):
        """Verify that loading respects max caps."""
        svc1 = MetacognitionService()
        svc1._auto_save = False
        # Add more than MAX_TRAIT_MAP_UPDATES
        for i in range(MAX_TRAIT_MAP_UPDATES + 50):
            svc1._trait_map_updates.append(
                TraitMapUpdate(
                    task_type=f"type_{i}",
                    trait_name="t",
                    old_value=None,
                    new_value=0.5,
                    source_correlation=0.6,
                    source_sample_count=10,
                )
            )
        path = str(tmp_path / "state.json")
        svc1.save_phase5_state(path)

        svc2 = MetacognitionService()
        svc2._auto_save = False
        svc2.load_phase5_state(path)
        assert len(svc2.trait_map_updates) <= MAX_TRAIT_MAP_UPDATES


# ============================================================
# save_if_auto / load_on_startup integration
# ============================================================


class TestAutoSaveLoadIntegration:

    def test_save_if_auto_saves_phase5(self, tmp_path):
        svc = MetacognitionService()
        svc._profile_path = str(tmp_path / "profiles.json")
        svc._phase5_state_path = str(tmp_path / "phase5_state.json")
        svc._auto_save = True
        svc._trait_snapshots.append(
            TraitSnapshot(
                agent_code="Forge",
                trait_values={"thoroughness": 0.8},
                trait_baselines={"thoroughness": 0.7},
            )
        )
        svc.save_if_auto()
        assert os.path.exists(str(tmp_path / "phase5_state.json"))

    def test_load_on_startup_loads_phase5(self, tmp_path):
        # Save state
        svc1 = MetacognitionService()
        svc1._auto_save = False
        svc1._learned_trait_map["code_review"] = {"thoroughness": 0.9}
        svc1.save_phase5_state(str(tmp_path / "phase5_state.json"))

        # Load on startup
        svc2 = MetacognitionService()
        svc2._auto_save = False
        svc2._profile_path = str(tmp_path / "profiles.json")
        svc2._phase5_state_path = str(tmp_path / "phase5_state.json")
        svc2.load_on_startup()
        assert svc2.learned_trait_map["code_review"]["thoroughness"] == 0.9

    def test_no_save_when_auto_disabled(self, tmp_path):
        svc = MetacognitionService()
        svc._profile_path = str(tmp_path / "profiles.json")
        svc._phase5_state_path = str(tmp_path / "phase5_state.json")
        svc._auto_save = False
        svc._trait_snapshots.append(
            TraitSnapshot(
                agent_code="Forge",
                trait_values={"thoroughness": 0.8},
                trait_baselines={"thoroughness": 0.7},
            )
        )
        svc.save_if_auto()
        assert not os.path.exists(str(tmp_path / "phase5_state.json"))
