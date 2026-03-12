"""Tests for metacognition cross-agent learning (Phase 5, Step 3)."""

import pytest
from uuid import uuid4

from ag3ntwerk.modules.metacognition.service import (
    MetacognitionService,
    PeerRecommendation,
    MIN_TOP_PERFORMER_SAMPLES,
    TOP_PERFORMER_PERCENTILE,
    MAX_PEER_RECOMMENDATIONS,
    HEURISTIC_SHARE_MIN_SUCCESS_RATE,
    HEURISTIC_SHARE_MIN_SAMPLES,
)
from ag3ntwerk.core.heuristics import Heuristic


# ============================================================
# PeerRecommendation dataclass
# ============================================================


class TestPeerRecommendation:

    def test_to_dict(self):
        rec = PeerRecommendation(
            target_agent="Keystone",
            source_agent="Forge",
            task_type="code_review",
            recommendation_type="trait_adjustment",
            trait_name="thoroughness",
            source_value=0.85,
            target_value=0.60,
            suggested_value=0.85,
            source_success_rate=0.90,
            target_success_rate=0.60,
            confidence=0.30,
        )
        d = rec.to_dict()
        assert d["target_agent"] == "Keystone"
        assert d["source_agent"] == "Forge"
        assert d["recommendation_type"] == "trait_adjustment"
        assert d["trait_name"] == "thoroughness"
        assert d["confidence"] == 0.30


# ============================================================
# extract_top_performer_patterns
# ============================================================


class TestExtractTopPerformerPatterns:

    def _make_service_with_outcomes(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent(
            "Forge",
            seed_traits={
                "thoroughness": 0.9,
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
            "Keystone",
            seed_traits={
                "thoroughness": 0.5,
                "creativity": 0.5,
                "risk": 0.5,
                "assertiveness": 0.5,
                "collaboration": 0.5,
                "adaptability": 0.5,
                "decision": "analytical",
                "communication": "direct",
            },
        )
        svc.register_agent(
            "Echo",
            seed_traits={
                "thoroughness": 0.3,
                "creativity": 0.9,
                "risk": 0.7,
                "assertiveness": 0.5,
                "collaboration": 0.5,
                "adaptability": 0.5,
                "decision": "analytical",
                "communication": "direct",
            },
        )

        # Forge high performer on code_review
        for i in range(15):
            svc._task_outcomes.append(
                {
                    "agent_code": "Forge",
                    "task_type": "code_review",
                    "success": True,
                    "task_id": f"t{i}",
                    "duration_ms": 100,
                    "timestamp": "2025-01-01T00:00:00",
                }
            )

        # Keystone low performer
        for i in range(15):
            svc._task_outcomes.append(
                {
                    "agent_code": "Keystone",
                    "task_type": "code_review",
                    "success": i < 5,
                    "task_id": f"t{100+i}",
                    "duration_ms": 100,
                    "timestamp": "2025-01-01T00:00:00",
                }
            )

        # Echo medium performer
        for i in range(15):
            svc._task_outcomes.append(
                {
                    "agent_code": "Echo",
                    "task_type": "code_review",
                    "success": i < 10,
                    "task_id": f"t{200+i}",
                    "duration_ms": 100,
                    "timestamp": "2025-01-01T00:00:00",
                }
            )

        return svc

    def test_identifies_top_performers(self):
        svc = self._make_service_with_outcomes()
        patterns = svc.extract_top_performer_patterns("code_review")
        assert "Forge" in patterns
        assert patterns["Forge"]["success_rate"] == 1.0

    def test_excludes_low_performers(self):
        svc = self._make_service_with_outcomes()
        patterns = svc.extract_top_performer_patterns("code_review")
        assert "Keystone" not in patterns  # 5/15 = 0.333 < 0.75

    def test_no_results_for_unknown_task(self):
        svc = self._make_service_with_outcomes()
        patterns = svc.extract_top_performer_patterns("unknown_task")
        assert patterns == {}

    def test_insufficient_samples(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        # Only 3 outcomes, not enough
        for i in range(3):
            svc._task_outcomes.append(
                {
                    "agent_code": "Forge",
                    "task_type": "code_review",
                    "success": True,
                    "task_id": f"t{i}",
                    "duration_ms": 100,
                    "timestamp": "2025-01-01T00:00:00",
                }
            )
        patterns = svc.extract_top_performer_patterns("code_review")
        assert patterns == {}


# ============================================================
# generate_peer_recommendations
# ============================================================


class TestGeneratePeerRecommendations:

    def _make_service(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent(
            "Forge",
            seed_traits={
                "thoroughness": 0.9,
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
            "Keystone",
            seed_traits={
                "thoroughness": 0.5,
                "creativity": 0.5,
                "risk": 0.5,
                "assertiveness": 0.5,
                "collaboration": 0.5,
                "adaptability": 0.5,
                "decision": "analytical",
                "communication": "direct",
            },
        )

        # Forge top performer
        for i in range(15):
            svc._task_outcomes.append(
                {
                    "agent_code": "Forge",
                    "task_type": "code_review",
                    "success": True,
                    "task_id": f"t{i}",
                    "duration_ms": 100,
                    "timestamp": "2025-01-01T00:00:00",
                }
            )
        # Keystone low performer
        for i in range(15):
            svc._task_outcomes.append(
                {
                    "agent_code": "Keystone",
                    "task_type": "code_review",
                    "success": i < 5,
                    "task_id": f"t{100+i}",
                    "duration_ms": 100,
                    "timestamp": "2025-01-01T00:00:00",
                }
            )
        return svc

    def test_generates_recommendations(self):
        svc = self._make_service()
        recs = svc.generate_peer_recommendations("Keystone")
        assert len(recs) > 0
        assert all(r.target_agent == "Keystone" for r in recs)

    def test_no_recs_for_top_performer(self):
        svc = self._make_service()
        recs = svc.generate_peer_recommendations("Forge")
        assert len(recs) == 0

    def test_no_recs_for_unregistered(self):
        svc = self._make_service()
        recs = svc.generate_peer_recommendations("UNKNOWN")
        assert recs == []

    def test_filter_by_task_type(self):
        svc = self._make_service()
        recs = svc.generate_peer_recommendations("Keystone", task_type="unknown_task")
        assert len(recs) == 0

    def test_stats_include_peer_recommendations(self):
        svc = self._make_service()
        svc.generate_peer_recommendations("Keystone")
        stats = svc.get_stats()
        assert stats["total_peer_recommendations"] > 0


# ============================================================
# share_heuristic
# ============================================================


class TestShareHeuristic:

    def _make_service_with_heuristic(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        svc.register_agent("Keystone")

        # Add a high-performing heuristic to Forge
        h = Heuristic(
            id="h1",
            name="test_heuristic",
            agent_code="Forge",
            condition="test",
            action="test_action",
            success_rate=0.85,
        )
        h._successes = 17
        h._failures = 3  # 20 total, 0.85 rate
        svc._heuristic_engines["Forge"].add_heuristic(h)
        return svc, h

    def test_successful_share(self):
        svc, h = self._make_service_with_heuristic()
        result = svc.share_heuristic("Forge", "Keystone", "h1")
        assert result is not None
        assert result["source_agent"] == "Forge"
        assert result["target_agent"] == "Keystone"
        assert "(from Forge)" in result["name"]

    def test_share_fails_low_success_rate(self):
        svc, h = self._make_service_with_heuristic()
        h.success_rate = 0.5
        result = svc.share_heuristic("Forge", "Keystone", "h1")
        assert result is None

    def test_share_fails_insufficient_samples(self):
        svc, h = self._make_service_with_heuristic()
        h._successes = 5
        h._failures = 2  # Only 7 total
        result = svc.share_heuristic("Forge", "Keystone", "h1")
        assert result is None

    def test_share_fails_unknown_heuristic(self):
        svc, _ = self._make_service_with_heuristic()
        result = svc.share_heuristic("Forge", "Keystone", "nonexistent")
        assert result is None

    def test_share_fails_unknown_agent(self):
        svc, _ = self._make_service_with_heuristic()
        result = svc.share_heuristic("Forge", "UNKNOWN", "h1")
        assert result is None


# ============================================================
# auto_share_heuristics
# ============================================================


class TestAutoShareHeuristics:

    def test_auto_shares(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        svc.register_agent("Keystone")

        h = Heuristic(
            id="h1",
            name="proven_strategy",
            agent_code="Forge",
            condition="test",
            action="test_action",
            success_rate=0.9,
        )
        h._successes = 18
        h._failures = 2
        svc._heuristic_engines["Forge"].add_heuristic(h)

        shares = svc.auto_share_heuristics()
        assert len(shares) >= 1
        assert shares[0]["target_agent"] == "Keystone"

    def test_no_duplicate_shares(self):
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")
        svc.register_agent("Keystone")

        h = Heuristic(
            id="h1",
            name="proven_strategy",
            agent_code="Forge",
            condition="test",
            action="test_action",
            success_rate=0.9,
        )
        h._successes = 18
        h._failures = 2
        svc._heuristic_engines["Forge"].add_heuristic(h)

        # First share
        svc.auto_share_heuristics()
        # Second share should not duplicate
        shares2 = svc.auto_share_heuristics()
        assert len(shares2) == 0
