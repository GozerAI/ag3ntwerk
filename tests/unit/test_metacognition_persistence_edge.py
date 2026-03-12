"""
Edge-case tests for Phase 5 persistence (save/load of phase5_state.json).

Covers corruption recovery, save edge cases, and round-trip data integrity
for special values, datetime boundaries, and unusual agent codes.
"""

import json
import os
from datetime import datetime, timezone, timedelta

from ag3ntwerk.modules.metacognition.service import (
    MAX_LEARNED_TRAIT_MAP_ENTRIES,
    MAX_TEAM_OUTCOMES,
    MAX_TRAIT_SNAPSHOTS,
    MetacognitionService,
    PeerRecommendation,
    TeamOutcome,
    TraitMapUpdate,
    TraitSnapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_service() -> MetacognitionService:
    svc = MetacognitionService()
    svc._auto_save = False
    return svc


# ============================================================
# 1. Corruption Recovery
# ============================================================


class TestCorruptionRecovery:
    """Verify graceful handling of corrupt or malformed state files."""

    def test_load_empty_file(self, tmp_path):
        """An empty file should be treated as invalid JSON and return zeros."""
        path = str(tmp_path / "empty.json")
        with open(path, "w") as f:
            f.write("")
        svc = _empty_service()
        counts = svc.load_phase5_state(path)
        assert counts["snapshots"] == 0
        assert counts["team_outcomes"] == 0
        assert counts["learned_map_entries"] == 0
        assert counts["trait_map_updates"] == 0
        assert counts["peer_recommendations"] == 0

    def test_load_invalid_json(self, tmp_path):
        """A file with broken JSON should return zeros without raising."""
        path = str(tmp_path / "broken.json")
        with open(path, "w") as f:
            f.write("{not json at all!!![}}}}")
        svc = _empty_service()
        counts = svc.load_phase5_state(path)
        assert counts["snapshots"] == 0

    def test_load_valid_json_missing_keys(self, tmp_path):
        """Valid JSON that lacks the expected top-level keys should use
        defaults (empty collections) instead of crashing."""
        path = str(tmp_path / "partial.json")
        with open(path, "w") as f:
            json.dump({"schema_version": 1, "extra_field": 42}, f)
        svc = _empty_service()
        counts = svc.load_phase5_state(path)
        assert counts["snapshots"] == 0
        assert counts["team_outcomes"] == 0
        assert counts["learned_map_entries"] == 0
        assert counts["trait_map_updates"] == 0
        assert counts["peer_recommendations"] == 0

    def test_load_learned_trait_map_wrong_type(self, tmp_path):
        """When learned_trait_map is not a dict, it should be safely ignored.
        The service guards this with ``isinstance(learned, dict)``."""
        path = str(tmp_path / "wrong_map.json")
        data = {
            "schema_version": 1,
            "trait_snapshots": [],
            "team_outcomes": [],
            "learned_trait_map": "not_a_dict",
            "trait_map_updates": [],
            "peer_recommendations": [],
        }
        with open(path, "w") as f:
            json.dump(data, f)
        svc = _empty_service()
        counts = svc.load_phase5_state(path)
        assert counts["learned_map_entries"] == 0
        assert svc.learned_trait_map == {}

    def test_load_learned_trait_map_nested_wrong_types(self, tmp_path):
        """When the inner values of learned_trait_map contain non-numeric values,
        they should be filtered out by the ``isinstance(v, (int, float))`` check."""
        path = str(tmp_path / "wrong_nested.json")
        data = {
            "schema_version": 1,
            "trait_snapshots": [],
            "team_outcomes": [],
            "learned_trait_map": {
                "code_review": {
                    "good_trait": 0.85,
                    "bad_trait": "not_a_number",
                    "also_bad": None,
                },
            },
            "trait_map_updates": [],
            "peer_recommendations": [],
        }
        with open(path, "w") as f:
            json.dump(data, f)
        svc = _empty_service()
        counts = svc.load_phase5_state(path)
        # Only the valid numeric entry should load
        assert "good_trait" in svc.learned_trait_map.get("code_review", {})
        assert "bad_trait" not in svc.learned_trait_map.get("code_review", {})
        assert "also_bad" not in svc.learned_trait_map.get("code_review", {})

    def test_load_snapshot_with_missing_subfields(self, tmp_path):
        """A snapshot entry missing required sub-keys (agent_code, trait_values)
        should be skipped without aborting the entire load."""
        path = str(tmp_path / "bad_snapshot.json")
        data = {
            "schema_version": 1,
            "trait_snapshots": [
                {"agent_code": "Forge"},  # missing trait_values / trait_baselines
                {
                    "agent_code": "Keystone",
                    "trait_values": {"thoroughness": 0.8},
                    "trait_baselines": {"thoroughness": 0.7},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "team_outcomes": [],
            "learned_trait_map": {},
            "trait_map_updates": [],
            "peer_recommendations": [],
        }
        with open(path, "w") as f:
            json.dump(data, f)
        svc = _empty_service()
        counts = svc.load_phase5_state(path)
        # Only the valid snapshot should load
        assert counts["snapshots"] == 1
        assert svc.trait_snapshots[0].agent_code == "Keystone"


# ============================================================
# 2. Save Edge Cases
# ============================================================


class TestSaveEdgeCases:
    """Edge cases for save_phase5_state()."""

    def test_save_empty_state(self, tmp_path):
        """Saving with completely empty collections should produce a valid
        JSON file with empty arrays/objects."""
        path = str(tmp_path / "empty_state.json")
        svc = _empty_service()
        svc.save_phase5_state(path)

        with open(path) as f:
            data = json.load(f)
        assert data["trait_snapshots"] == []
        assert data["team_outcomes"] == []
        assert data["learned_trait_map"] == {}
        assert data["trait_map_updates"] == []
        assert data["peer_recommendations"] == []

    def test_save_with_maximum_capacity_snapshots(self, tmp_path):
        """Saving at exactly MAX_TRAIT_SNAPSHOTS should not lose entries."""
        svc = _empty_service()
        for i in range(MAX_TRAIT_SNAPSHOTS):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code=f"A{i % 50}",
                    trait_values={"t": float(i) / MAX_TRAIT_SNAPSHOTS},
                    trait_baselines={"t": 0.5},
                    timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=i),
                )
            )
        path = str(tmp_path / "max_cap.json")
        svc.save_phase5_state(path)

        with open(path) as f:
            data = json.load(f)
        assert len(data["trait_snapshots"]) == MAX_TRAIT_SNAPSHOTS

    def test_save_with_maximum_capacity_team_outcomes(self, tmp_path):
        """Saving at exactly MAX_TEAM_OUTCOMES should write them all."""
        svc = _empty_service()
        for i in range(MAX_TEAM_OUTCOMES):
            svc._team_outcomes.append(
                TeamOutcome(
                    team=["A", "B"],
                    task_type="stress",
                    success=(i % 2 == 0),
                    task_id=f"t{i}",
                )
            )
        path = str(tmp_path / "max_teams.json")
        svc.save_phase5_state(path)

        with open(path) as f:
            data = json.load(f)
        assert len(data["team_outcomes"]) == MAX_TEAM_OUTCOMES

    def test_save_creates_missing_directory(self, tmp_path):
        """If the target directory does not exist, save should create it
        (the _atomic_write_json helper calls mkdir(parents=True))."""
        path = str(tmp_path / "nested" / "deep" / "phase5.json")
        svc = _empty_service()
        svc.save_phase5_state(path)
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["schema_version"] == 1


# ============================================================
# 3. Round-Trip Integrity
# ============================================================


class TestRoundTripIntegrity:
    """Save then load should reproduce all data fields exactly."""

    def test_full_round_trip_all_fields(self, tmp_path):
        """Save a service with data in every collection, load into a fresh
        service, and verify all fields match."""
        svc1 = _empty_service()
        ts = datetime(2025, 6, 15, 12, 30, 0, tzinfo=timezone.utc)

        svc1._trait_snapshots.append(
            TraitSnapshot(
                agent_code="Forge",
                trait_values={"thoroughness": 0.85, "creativity": 0.6},
                trait_baselines={"thoroughness": 0.7, "creativity": 0.5},
                timestamp=ts,
            )
        )
        svc1._team_outcomes.append(
            TeamOutcome(
                team=["Forge", "Keystone"],
                task_type="code_review",
                success=True,
                task_id="task_42",
                compatibility_score=0.92,
            )
        )
        svc1._learned_trait_map["code_review"] = {"thoroughness": 0.88}
        svc1._trait_map_updates.append(
            TraitMapUpdate(
                task_type="code_review",
                trait_name="thoroughness",
                old_value=None,
                new_value=0.88,
                source_correlation=0.75,
                source_sample_count=40,
                validation_status="validated",
                pre_apply_success_rate=0.65,
            )
        )
        svc1._peer_recommendations.append(
            PeerRecommendation(
                target_agent="Keystone",
                source_agent="Forge",
                task_type="code_review",
                recommendation_type="trait_adjustment",
                trait_name="thoroughness",
                source_value=0.85,
                target_value=0.5,
                suggested_value=0.85,
                source_success_rate=0.92,
                target_success_rate=0.45,
                confidence=0.78,
            )
        )

        path = str(tmp_path / "roundtrip.json")
        svc1.save_phase5_state(path)

        svc2 = _empty_service()
        counts = svc2.load_phase5_state(path)

        assert counts["snapshots"] == 1
        assert counts["team_outcomes"] == 1
        assert counts["learned_map_entries"] == 1
        assert counts["trait_map_updates"] == 1
        assert counts["peer_recommendations"] == 1

        snap = svc2.trait_snapshots[0]
        assert snap.agent_code == "Forge"
        assert snap.trait_values["thoroughness"] == 0.85
        assert snap.trait_values["creativity"] == 0.6
        assert snap.trait_baselines["thoroughness"] == 0.7

        team = svc2.team_outcomes[0]
        assert team.team == ["Forge", "Keystone"]
        assert team.success is True
        assert team.task_id == "task_42"

        assert svc2.learned_trait_map["code_review"]["thoroughness"] == 0.88

        update = svc2.trait_map_updates[0]
        assert update.validation_status == "validated"
        assert update.new_value == 0.88

        rec = svc2.peer_recommendations[0]
        assert rec.target_agent == "Keystone"
        assert rec.confidence == 0.78

    def test_round_trip_special_characters_in_agent_codes(self, tmp_path):
        """Agent codes with special characters should survive save/load."""
        svc1 = _empty_service()
        special_codes = ["C-TO", "CFO_v2", "agent/slash", "agent.dot", "agent+plus"]
        for code in special_codes:
            svc1._trait_snapshots.append(
                TraitSnapshot(
                    agent_code=code,
                    trait_values={"risk_tolerance": 0.7},
                    trait_baselines={"risk_tolerance": 0.6},
                )
            )
            svc1._team_outcomes.append(
                TeamOutcome(
                    team=[code, "partner"],
                    task_type="special",
                    success=True,
                )
            )

        path = str(tmp_path / "special.json")
        svc1.save_phase5_state(path)

        svc2 = _empty_service()
        counts = svc2.load_phase5_state(path)
        assert counts["snapshots"] == len(special_codes)
        assert counts["team_outcomes"] == len(special_codes)

        loaded_codes = [s.agent_code for s in svc2.trait_snapshots]
        for code in special_codes:
            assert code in loaded_codes, f"Agent code '{code}' was lost on round-trip"

    def test_round_trip_midnight_utc_datetime(self, tmp_path):
        """Timestamp at midnight UTC should survive serialization exactly."""
        svc1 = _empty_service()
        midnight = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        svc1._trait_snapshots.append(
            TraitSnapshot(
                agent_code="Forge",
                trait_values={"thoroughness": 0.5},
                trait_baselines={"thoroughness": 0.5},
                timestamp=midnight,
            )
        )
        path = str(tmp_path / "midnight.json")
        svc1.save_phase5_state(path)

        svc2 = _empty_service()
        svc2.load_phase5_state(path)
        loaded_ts = svc2.trait_snapshots[0].timestamp
        # Should round-trip to the same point in time
        assert loaded_ts.year == 2025
        assert loaded_ts.month == 1
        assert loaded_ts.day == 1
        assert loaded_ts.hour == 0
        assert loaded_ts.minute == 0

    def test_round_trip_far_future_datetime(self, tmp_path):
        """A far-future timestamp should survive serialization."""
        svc1 = _empty_service()
        future = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        svc1._trait_snapshots.append(
            TraitSnapshot(
                agent_code="FUTURE",
                trait_values={"adaptability": 0.99},
                trait_baselines={"adaptability": 0.5},
                timestamp=future,
            )
        )
        path = str(tmp_path / "future.json")
        svc1.save_phase5_state(path)

        svc2 = _empty_service()
        svc2.load_phase5_state(path)
        loaded = svc2.trait_snapshots[0]
        assert loaded.timestamp.year == 2099

    def test_round_trip_negative_offset_timezone(self, tmp_path):
        """Timestamps with non-UTC timezone offsets should still parse
        correctly on load."""
        svc1 = _empty_service()
        est = timezone(timedelta(hours=-5))
        ts_est = datetime(2025, 7, 4, 20, 0, 0, tzinfo=est)
        svc1._trait_snapshots.append(
            TraitSnapshot(
                agent_code="TZ",
                trait_values={"risk_tolerance": 0.3},
                trait_baselines={"risk_tolerance": 0.5},
                timestamp=ts_est,
            )
        )
        path = str(tmp_path / "tz.json")
        svc1.save_phase5_state(path)

        svc2 = _empty_service()
        svc2.load_phase5_state(path)
        loaded = svc2.trait_snapshots[0]
        # The loaded timestamp may be in UTC or the original offset, but the
        # absolute point in time should match
        assert abs((loaded.timestamp - ts_est).total_seconds()) < 2

    def test_round_trip_many_learned_map_entries(self, tmp_path):
        """Round-trip with exactly MAX_LEARNED_TRAIT_MAP_ENTRIES entries."""
        svc1 = _empty_service()
        for i in range(MAX_LEARNED_TRAIT_MAP_ENTRIES):
            svc1._learned_trait_map[f"task_{i}"] = {"t": float(i) / 100}
        path = str(tmp_path / "big_map.json")
        svc1.save_phase5_state(path)

        svc2 = _empty_service()
        counts = svc2.load_phase5_state(path)
        total = sum(len(v) for v in svc2.learned_trait_map.values())
        assert total <= MAX_LEARNED_TRAIT_MAP_ENTRIES

    def test_round_trip_trait_map_update_with_none_old_value(self, tmp_path):
        """TraitMapUpdate where old_value is None should survive round-trip."""
        svc1 = _empty_service()
        svc1._trait_map_updates.append(
            TraitMapUpdate(
                task_type="new_task",
                trait_name="creativity",
                old_value=None,
                new_value=0.77,
                source_correlation=0.65,
                source_sample_count=25,
                validation_status="pending",
                pre_apply_success_rate=None,
            )
        )
        path = str(tmp_path / "none_old.json")
        svc1.save_phase5_state(path)

        svc2 = _empty_service()
        svc2.load_phase5_state(path)
        update = svc2.trait_map_updates[0]
        assert update.old_value is None
        assert update.new_value == 0.77
        assert update.pre_apply_success_rate is None
        assert update.validation_status == "pending"

    def test_round_trip_float_precision(self, tmp_path):
        """Trait values should maintain at least 4 decimal places of
        precision through save/load."""
        svc1 = _empty_service()
        val = 0.123456789
        svc1._trait_snapshots.append(
            TraitSnapshot(
                agent_code="PREC",
                trait_values={"fine_trait": val},
                trait_baselines={"fine_trait": 0.5},
            )
        )
        path = str(tmp_path / "precision.json")
        svc1.save_phase5_state(path)

        svc2 = _empty_service()
        svc2.load_phase5_state(path)
        loaded_val = svc2.trait_snapshots[0].trait_values["fine_trait"]
        # to_dict rounds to 4 places => 0.1235
        assert abs(loaded_val - round(val, 4)) < 1e-6
