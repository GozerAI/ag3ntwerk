"""Tests for metacognition drift auto-response (Phase 4, Step 2)."""

import pytest

from ag3ntwerk.modules.metacognition.service import (
    MetacognitionService,
    DriftResponse,
    DRIFT_CRITICAL_THRESHOLD,
    DRIFT_WARNING_THRESHOLD,
    DRIFT_STABILIZATION_BOOST,
    DRIFT_NUDGE_DELTA,
    MAX_DRIFT_RESPONSES,
)
from ag3ntwerk.core.personality import PersonalityTrait


def _make_service_with_critical_drift():
    """Create a service with an agent whose trait has critical drift."""
    svc = MetacognitionService()
    svc.register_agent("Forge")
    profile = svc.get_profile("Forge")
    # Force critical drift on risk_tolerance
    trait = profile.risk_tolerance
    trait.value = trait.baseline + DRIFT_CRITICAL_THRESHOLD + 0.05
    trait.value = min(1.0, trait.value)
    return svc


def _make_service_with_warning_only():
    """Create a service where drift is warning-level only (not critical)."""
    svc = MetacognitionService()
    svc.register_agent("Forge")
    profile = svc.get_profile("Forge")
    trait = profile.risk_tolerance
    trait.value = trait.baseline + DRIFT_WARNING_THRESHOLD + 0.01
    # Make sure it's below critical
    if abs(trait.value - trait.baseline) >= DRIFT_CRITICAL_THRESHOLD:
        trait.value = trait.baseline + DRIFT_WARNING_THRESHOLD + 0.01
    return svc


class TestRespondToDrift:
    """Tests for respond_to_drift."""

    def test_responds_to_critical_drift(self):
        svc = _make_service_with_critical_drift()
        responses = svc.respond_to_drift()
        assert len(responses) >= 2  # stabilization + nudge_back per trait
        actions = {r.action for r in responses}
        assert "stabilization" in actions
        assert "nudge_back" in actions

    def test_ignores_warning_drift(self):
        svc = _make_service_with_warning_only()
        responses = svc.respond_to_drift()
        assert len(responses) == 0

    def test_no_drift_no_response(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        responses = svc.respond_to_drift()
        assert responses == []

    def test_stabilization_boosts_sample_count(self):
        svc = _make_service_with_critical_drift()
        profile = svc.get_profile("Forge")
        trait = profile.risk_tolerance
        old_count = trait.sample_count
        svc.respond_to_drift()
        # sample_count should have increased by at least DRIFT_STABILIZATION_BOOST
        assert trait.sample_count >= old_count + DRIFT_STABILIZATION_BOOST

    def test_nudge_moves_toward_baseline(self):
        svc = _make_service_with_critical_drift()
        profile = svc.get_profile("Forge")
        trait = profile.risk_tolerance
        old_distance = abs(trait.value - trait.baseline)
        svc.respond_to_drift()
        # After nudge, distance should be same or smaller
        new_distance = abs(trait.value - trait.baseline)
        assert new_distance <= old_distance + 0.001  # allow float tolerance

    def test_agent_code_filter(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.register_agent("Echo")
        # Force critical drift on both
        for code in ["Forge", "Echo"]:
            profile = svc.get_profile(code)
            trait = profile.risk_tolerance
            trait.value = min(1.0, trait.baseline + DRIFT_CRITICAL_THRESHOLD + 0.05)

        cto_only = svc.respond_to_drift(agent_code="Forge")
        assert all(r.agent_code == "Forge" for r in cto_only)

    def test_responses_recorded(self):
        svc = _make_service_with_critical_drift()
        svc.respond_to_drift()
        assert len(svc._drift_responses) >= 2

    def test_responses_capped(self):
        svc = _make_service_with_critical_drift()
        # Pre-fill with fake responses
        for i in range(MAX_DRIFT_RESPONSES):
            svc._drift_responses.append(
                DriftResponse(
                    agent_code="Forge",
                    trait_name="risk_tolerance",
                    action="stabilization",
                    old_value=0.5,
                    new_value=0.5,
                    sample_count_before=0,
                    sample_count_after=50,
                )
            )
        svc.respond_to_drift()
        assert len(svc._drift_responses) <= MAX_DRIFT_RESPONSES

    def test_unregistered_agent_no_crash(self):
        svc = MetacognitionService()
        responses = svc.respond_to_drift(agent_code="NONEXISTENT")
        assert responses == []


class TestDriftResponseDataclass:
    """Tests for the DriftResponse dataclass."""

    def test_to_dict(self):
        r = DriftResponse(
            agent_code="Forge",
            trait_name="risk_tolerance",
            action="stabilization",
            old_value=0.75,
            new_value=0.75,
            sample_count_before=10,
            sample_count_after=60,
        )
        d = r.to_dict()
        assert d["agent_code"] == "Forge"
        assert d["action"] == "stabilization"
        assert d["sample_count_before"] == 10
        assert d["sample_count_after"] == 60
        assert "timestamp" in d

    def test_to_dict_rounds_values(self):
        r = DriftResponse(
            agent_code="Forge",
            trait_name="risk_tolerance",
            action="nudge_back",
            old_value=0.12345678,
            new_value=0.12340000,
            sample_count_before=0,
            sample_count_after=1,
        )
        d = r.to_dict()
        assert d["old_value"] == 0.1235
        assert d["new_value"] == 0.1234


class TestGetDriftResponses:
    """Tests for get_drift_responses."""

    def test_empty_history(self):
        svc = MetacognitionService()
        assert svc.get_drift_responses() == []

    def test_returns_most_recent_first(self):
        svc = _make_service_with_critical_drift()
        svc.respond_to_drift()
        # Force another critical drift and respond again
        profile = svc.get_profile("Forge")
        trait = profile.risk_tolerance
        trait.value = min(1.0, trait.baseline + DRIFT_CRITICAL_THRESHOLD + 0.05)
        svc.respond_to_drift()
        results = svc.get_drift_responses()
        assert len(results) >= 2
        # Most recent should be first
        assert results[0]["timestamp"] >= results[-1]["timestamp"]

    def test_filter_by_agent(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.register_agent("Echo")
        for code in ["Forge", "Echo"]:
            profile = svc.get_profile(code)
            trait = profile.risk_tolerance
            trait.value = min(1.0, trait.baseline + DRIFT_CRITICAL_THRESHOLD + 0.05)
        svc.respond_to_drift()
        cto_only = svc.get_drift_responses(agent_code="Forge")
        assert all(r["agent_code"] == "Forge" for r in cto_only)

    def test_limit_respected(self):
        svc = _make_service_with_critical_drift()
        svc.respond_to_drift()
        results = svc.get_drift_responses(limit=1)
        assert len(results) <= 1

    def test_stats_include_drift_responses(self):
        svc = _make_service_with_critical_drift()
        svc.respond_to_drift()
        stats = svc.get_stats()
        assert "total_drift_responses" in stats
        assert stats["total_drift_responses"] >= 2
