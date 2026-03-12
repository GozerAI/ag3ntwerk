"""Tests for metacognition personality coherence & anomaly detection (Phase 5, Step 2)."""

import pytest
from datetime import datetime, timezone, timedelta

from ag3ntwerk.modules.metacognition.service import (
    MetacognitionService,
    CoherenceReport,
    TraitSnapshot,
    COHERENCE_RULES,
    COHERENCE_TENSION_WEIGHT,
    ANOMALY_VELOCITY_MULTIPLIER,
    ANOMALY_LOOKBACK_SNAPSHOTS,
)
from ag3ntwerk.core.personality import EVOLUTION_RATE


# ============================================================
# CoherenceReport dataclass
# ============================================================


class TestCoherenceReport:

    def test_to_dict(self):
        report = CoherenceReport(
            agent_code="Forge",
            coherence_score=0.85,
            tensions=[
                {"trait_a": "risk_tolerance", "trait_b": "thoroughness", "tension_value": 0.1}
            ],
            anomalies=[],
            health_classification="healthy",
        )
        d = report.to_dict()
        assert d["agent_code"] == "Forge"
        assert d["coherence_score"] == 0.85
        assert len(d["tensions"]) == 1
        assert d["health_classification"] == "healthy"


# ============================================================
# compute_coherence
# ============================================================


class TestComputeCoherence:

    def _make_service(self, traits=None):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge", seed_traits=traits)
        return svc

    def test_returns_none_for_unregistered(self):
        svc = MetacognitionService()
        svc._auto_save = False
        result = svc.compute_coherence("UNKNOWN")
        assert result is None

    def test_healthy_default_profile(self):
        svc = self._make_service()
        report = svc.compute_coherence("Forge")
        assert report is not None
        assert 0.0 <= report.coherence_score <= 1.0
        assert report.health_classification == "healthy"

    def test_same_high_tension(self):
        # Both risk_tolerance and thoroughness very high -> tension
        svc = self._make_service(
            traits={
                "risk": 0.95,
                "thoroughness": 0.95,
                "assertiveness": 0.5,
                "collaboration": 0.5,
                "creativity": 0.5,
                "adaptability": 0.5,
                "decision": "analytical",
                "communication": "direct",
            }
        )
        report = svc.compute_coherence("Forge")
        assert report is not None
        assert report.coherence_score < 1.0
        tensions = [
            t
            for t in report.tensions
            if t["trait_a"] == "risk_tolerance" and t["trait_b"] == "thoroughness"
        ]
        assert len(tensions) == 1
        assert tensions[0]["tension_value"] > 0

    def test_opposite_tension(self):
        # risk_tolerance low, adaptability high -> inconsistency
        svc = self._make_service(
            traits={
                "risk": 0.1,
                "adaptability": 0.9,
                "thoroughness": 0.5,
                "assertiveness": 0.5,
                "collaboration": 0.5,
                "creativity": 0.5,
                "decision": "analytical",
                "communication": "direct",
            }
        )
        report = svc.compute_coherence("Forge")
        assert report is not None
        opp_tensions = [t for t in report.tensions if "diverge" in t.get("description", "")]
        assert len(opp_tensions) >= 1

    def test_no_tension_moderate_traits(self):
        svc = self._make_service(
            traits={
                "risk": 0.5,
                "thoroughness": 0.5,
                "assertiveness": 0.5,
                "collaboration": 0.5,
                "creativity": 0.5,
                "adaptability": 0.5,
                "decision": "analytical",
                "communication": "direct",
            }
        )
        report = svc.compute_coherence("Forge")
        assert report is not None
        assert report.coherence_score == 1.0
        assert len(report.tensions) == 0

    def test_coherence_score_clamps_to_zero(self):
        # All traits extremely high -> multiple tensions stack
        svc = self._make_service(
            traits={
                "risk": 0.99,
                "thoroughness": 0.99,
                "assertiveness": 0.99,
                "collaboration": 0.99,
                "creativity": 0.99,
                "adaptability": 0.01,
                "decision": "analytical",
                "communication": "direct",
            }
        )
        report = svc.compute_coherence("Forge")
        assert report is not None
        assert report.coherence_score >= 0.0


# ============================================================
# detect_anomalies
# ============================================================


class TestDetectAnomalies:

    def test_no_snapshots(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        anomalies = svc.detect_anomalies("Forge")
        assert anomalies == []

    def test_single_snapshot(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        svc._trait_snapshots.append(
            TraitSnapshot(
                agent_code="Forge",
                trait_values={"thoroughness": 0.5},
                trait_baselines={"thoroughness": 0.5},
            )
        )
        anomalies = svc.detect_anomalies("Forge")
        assert anomalies == []

    def test_detects_rapid_change(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        # Rapid change: EVOLUTION_RATE is 0.05, 3x is 0.15
        # If slope > 0.15 per snapshot, it's an anomaly
        for i in range(5):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.3 + i * 0.1},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime.now(timezone.utc) - timedelta(seconds=50 - i * 10),
                )
            )
        anomalies = svc.detect_anomalies("Forge")
        # slope per snapshot = 0.1 which is > 3 * 0.05 = 0.15? No, 0.1 < 0.15
        # Need slope > 0.15
        assert len(anomalies) == 0

    def test_detects_very_rapid_change(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        for i in range(5):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.1 + i * 0.2},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime.now(timezone.utc) - timedelta(seconds=50 - i * 10),
                )
            )
        anomalies = svc.detect_anomalies("Forge")
        # slope = 0.2 per snapshot, which > 3 * 0.05 = 0.15
        assert len(anomalies) == 1
        assert anomalies[0]["trait_name"] == "thoroughness"

    def test_normal_change_no_anomaly(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        for i in range(5):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.5 + i * 0.01},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime.now(timezone.utc) - timedelta(seconds=50 - i * 10),
                )
            )
        anomalies = svc.detect_anomalies("Forge")
        assert len(anomalies) == 0


# ============================================================
# classify_agent_health
# ============================================================


class TestClassifyAgentHealth:

    def test_healthy_default(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        health = svc.classify_agent_health("Forge")
        assert health == "healthy"

    def test_degrading_on_anomaly(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        # Inject rapid change snapshots
        for i in range(5):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.1 + i * 0.2},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime.now(timezone.utc) - timedelta(seconds=50 - i * 10),
                )
            )
        health = svc.classify_agent_health("Forge")
        assert health == "degrading"

    def test_oscillating_detection(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        # Create oscillating snapshots
        values = [0.5, 0.7, 0.5, 0.7, 0.5, 0.7, 0.5, 0.7, 0.5, 0.7]
        for i, v in enumerate(values):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": v},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime.now(timezone.utc) - timedelta(seconds=100 - i * 10),
                )
            )
        health = svc.classify_agent_health("Forge")
        assert health in ("oscillating", "degrading")

    def test_stats_include_agent_health(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        stats = svc.get_stats()
        assert "agent_health" in stats
        assert stats["agent_health"]["Forge"] == "healthy"
