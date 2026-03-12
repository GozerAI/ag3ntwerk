"""Tests for metacognition temporal trait tracking and trend analysis (Phase 5, Step 1)."""

import pytest
from datetime import datetime, timezone, timedelta

from ag3ntwerk.modules.metacognition.service import (
    MetacognitionService,
    TraitSnapshot,
    TraitTrend,
    _linear_slope,
    MAX_TRAIT_SNAPSHOTS,
    SNAPSHOT_MIN_INTERVAL_SECONDS,
    TREND_WINDOW_SIZE,
    TREND_IMPROVING_THRESHOLD,
    TREND_DECLINING_THRESHOLD,
    TREND_OSCILLATION_REVERSALS,
)


# ============================================================
# _linear_slope helper
# ============================================================


class TestLinearSlope:
    """Tests for the pure-Python least-squares slope helper."""

    def test_returns_zero_for_empty(self):
        assert _linear_slope([]) == 0.0

    def test_returns_zero_for_single_value(self):
        assert _linear_slope([5.0]) == 0.0

    def test_positive_slope(self):
        slope = _linear_slope([1.0, 2.0, 3.0, 4.0])
        assert abs(slope - 1.0) < 1e-9

    def test_negative_slope(self):
        slope = _linear_slope([4.0, 3.0, 2.0, 1.0])
        assert abs(slope - (-1.0)) < 1e-9

    def test_flat_slope(self):
        slope = _linear_slope([3.0, 3.0, 3.0, 3.0])
        assert abs(slope) < 1e-9

    def test_noisy_positive(self):
        slope = _linear_slope([1.0, 1.5, 1.2, 2.0, 2.5])
        assert slope > 0


# ============================================================
# TraitSnapshot dataclass
# ============================================================


class TestTraitSnapshot:

    def test_to_dict(self):
        ts = TraitSnapshot(
            agent_code="Forge",
            trait_values={"thoroughness": 0.75},
            trait_baselines={"thoroughness": 0.70},
        )
        d = ts.to_dict()
        assert d["agent_code"] == "Forge"
        assert d["trait_values"]["thoroughness"] == 0.75
        assert d["trait_baselines"]["thoroughness"] == 0.70
        assert "timestamp" in d


# ============================================================
# TraitTrend dataclass
# ============================================================


class TestTraitTrend:

    def test_to_dict(self):
        trend = TraitTrend(
            agent_code="Forge",
            trait_name="thoroughness",
            classification="improving",
            velocity=0.02,
            direction_toward_baseline=True,
            sample_count=20,
            current_value=0.8,
            baseline_value=0.7,
        )
        d = trend.to_dict()
        assert d["classification"] == "improving"
        assert d["velocity"] == 0.02
        assert d["direction_toward_baseline"] is True


# ============================================================
# record_trait_snapshot
# ============================================================


class TestRecordTraitSnapshot:

    def _make_service(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        svc.register_agent("Keystone")
        return svc

    def test_snapshots_all_agents(self):
        svc = self._make_service()
        snaps = svc.record_trait_snapshot()
        assert len(snaps) == 2
        codes = {s.agent_code for s in snaps}
        assert codes == {"Forge", "Keystone"}

    def test_snapshot_single_agent(self):
        svc = self._make_service()
        snaps = svc.record_trait_snapshot("Forge")
        assert len(snaps) == 1
        assert snaps[0].agent_code == "Forge"

    def test_interval_enforcement(self):
        svc = self._make_service()
        svc.record_trait_snapshot("Forge")
        # Second immediate call should be skipped
        snaps2 = svc.record_trait_snapshot("Forge")
        assert len(snaps2) == 0

    def test_interval_allows_after_time(self):
        svc = self._make_service()
        svc.record_trait_snapshot("Forge")
        # Backdate the snapshot
        svc._trait_snapshots[-1].timestamp = datetime.now(timezone.utc) - timedelta(
            seconds=SNAPSHOT_MIN_INTERVAL_SECONDS + 1
        )
        snaps2 = svc.record_trait_snapshot("Forge")
        assert len(snaps2) == 1

    def test_cap_at_max(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        # Inject many snapshots
        for i in range(MAX_TRAIT_SNAPSHOTS + 10):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.5},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime.now(timezone.utc)
                    - timedelta(seconds=MAX_TRAIT_SNAPSHOTS + 10 - i),
                )
            )
        svc.record_trait_snapshot("Forge")
        assert len(svc._trait_snapshots) <= MAX_TRAIT_SNAPSHOTS

    def test_stats_include_snapshot_count(self):
        svc = self._make_service()
        svc.record_trait_snapshot()
        stats = svc.get_stats()
        assert stats["total_trait_snapshots"] == 2


# ============================================================
# get_trait_history
# ============================================================


class TestGetTraitHistory:

    def test_returns_newest_first(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        # Add snapshots manually
        for i in range(5):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.5 + i * 0.01},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime.now(timezone.utc) - timedelta(seconds=50 - i * 10),
                )
            )
        history = svc.get_trait_history("Forge")
        assert len(history) == 5
        # newest first
        assert (
            history[0]["trait_values"]["thoroughness"] > history[-1]["trait_values"]["thoroughness"]
        )

    def test_filter_by_trait_name(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        svc._trait_snapshots.append(
            TraitSnapshot(
                agent_code="Forge",
                trait_values={"thoroughness": 0.8, "creativity": 0.6},
                trait_baselines={"thoroughness": 0.7, "creativity": 0.5},
            )
        )
        history = svc.get_trait_history("Forge", trait_name="thoroughness")
        assert len(history) == 1
        assert "value" in history[0]
        assert history[0]["value"] == 0.8

    def test_limit(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        for i in range(20):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.5},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime.now(timezone.utc) - timedelta(seconds=200 - i * 10),
                )
            )
        history = svc.get_trait_history("Forge", limit=5)
        assert len(history) == 5


# ============================================================
# classify_trait_trend
# ============================================================


class TestClassifyTraitTrend:

    def _make_svc_with_snapshots(self, values):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        for i, v in enumerate(values):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": v},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime.now(timezone.utc)
                    - timedelta(seconds=len(values) * 10 - i * 10),
                )
            )
        return svc

    def test_returns_none_with_insufficient_data(self):
        svc = self._make_svc_with_snapshots([0.5, 0.6])
        result = svc.classify_trait_trend("Forge", "thoroughness")
        assert result is None

    def test_improving(self):
        svc = self._make_svc_with_snapshots([0.5, 0.52, 0.54, 0.56, 0.58])
        trend = svc.classify_trait_trend("Forge", "thoroughness")
        assert trend is not None
        assert trend.classification == "improving"
        assert trend.velocity > 0

    def test_declining(self):
        svc = self._make_svc_with_snapshots([0.58, 0.56, 0.54, 0.52, 0.50])
        trend = svc.classify_trait_trend("Forge", "thoroughness")
        assert trend is not None
        assert trend.classification == "declining"
        assert trend.velocity < 0

    def test_stable(self):
        svc = self._make_svc_with_snapshots([0.50, 0.50, 0.50, 0.50, 0.50])
        trend = svc.classify_trait_trend("Forge", "thoroughness")
        assert trend is not None
        assert trend.classification == "stable"

    def test_oscillating(self):
        # Values alternating up/down to create many reversals
        values = [0.5, 0.6, 0.5, 0.6, 0.5, 0.6, 0.5, 0.6, 0.5, 0.6]
        svc = self._make_svc_with_snapshots(values)
        trend = svc.classify_trait_trend("Forge", "thoroughness")
        assert trend is not None
        assert trend.classification == "oscillating"

    def test_direction_toward_baseline(self):
        # Moving from 0.7 toward baseline of 0.5
        svc = self._make_svc_with_snapshots([0.7, 0.65, 0.60, 0.55])
        trend = svc.classify_trait_trend("Forge", "thoroughness")
        assert trend is not None
        assert trend.direction_toward_baseline is True


# ============================================================
# get_trend_summary
# ============================================================


class TestGetTrendSummary:

    def test_summary_structure(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        # Add enough snapshots
        for i in range(5):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.5 + i * 0.02},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime.now(timezone.utc) - timedelta(seconds=50 - i * 10),
                )
            )
        summary = svc.get_trend_summary()
        assert "agents" in summary
        assert "total_snapshots" in summary
        assert "Forge" in summary["agents"]
        assert "traits" in summary["agents"]["Forge"]

    def test_filter_by_agent(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        svc.register_agent("Keystone")
        summary = svc.get_trend_summary("Forge")
        assert "Forge" in summary["agents"]
        assert "Keystone" not in summary["agents"]
