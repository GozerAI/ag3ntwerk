"""Tests for drift alerting (Phase 3, Step 4)."""

import pytest

from ag3ntwerk.core.personality import PersonalityTrait
from ag3ntwerk.modules.metacognition.service import (
    MetacognitionService,
    DriftAlert,
    DRIFT_WARNING_THRESHOLD,
    DRIFT_CRITICAL_THRESHOLD,
)


@pytest.fixture
def service(tmp_path):
    svc = MetacognitionService(profile_path=str(tmp_path / "test_drift_profiles.json"))
    svc._auto_save = False
    return svc


class TestDriftAlert:
    """Tests for the DriftAlert dataclass."""

    def test_to_dict(self):
        alert = DriftAlert(
            agent_code="Forge",
            trait_name="risk_tolerance",
            current_value=0.8,
            baseline_value=0.5,
            drift=0.3,
            severity="critical",
        )
        d = alert.to_dict()
        assert d["agent_code"] == "Forge"
        assert d["drift"] == 0.3
        assert d["severity"] == "critical"
        assert "timestamp" in d

    def test_thresholds(self):
        assert DRIFT_WARNING_THRESHOLD == 0.15
        assert DRIFT_CRITICAL_THRESHOLD == 0.25


class TestCheckDriftAlerts:
    """Tests for MetacognitionService.check_drift_alerts()."""

    def test_no_alerts_on_fresh_profiles(self, service):
        service.register_agent("Forge")
        alerts = service.check_drift_alerts()
        assert len(alerts) == 0

    def test_warning_alert_on_moderate_drift(self, service):
        service.register_agent("Forge")
        profile = service.get_profile("Forge")
        # Manually push a trait to trigger warning
        profile.risk_tolerance.value = profile.risk_tolerance.baseline + 0.16
        alerts = service.check_drift_alerts()
        warning_alerts = [a for a in alerts if a.severity == "warning"]
        assert len(warning_alerts) >= 1
        assert any(a.trait_name == "risk_tolerance" for a in warning_alerts)

    def test_critical_alert_on_large_drift(self, service):
        service.register_agent("Forge")
        profile = service.get_profile("Forge")
        profile.creativity.value = profile.creativity.baseline + 0.26
        alerts = service.check_drift_alerts()
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        assert len(critical_alerts) >= 1
        assert any(a.trait_name == "creativity" for a in critical_alerts)

    def test_alerts_sorted_by_drift_descending(self, service):
        service.register_agent("Forge")
        profile = service.get_profile("Forge")
        profile.risk_tolerance.value = profile.risk_tolerance.baseline + 0.16  # warning
        profile.creativity.value = profile.creativity.baseline + 0.26  # critical
        alerts = service.check_drift_alerts()
        assert len(alerts) >= 2
        drifts = [a.drift for a in alerts]
        assert drifts == sorted(drifts, reverse=True)

    def test_filter_by_agent_code(self, service):
        service.register_agent("Forge")
        service.register_agent("Keystone")
        profile_cto = service.get_profile("Forge")
        profile_cto.risk_tolerance.value = profile_cto.risk_tolerance.baseline + 0.2
        alerts = service.check_drift_alerts("Forge")
        assert all(a.agent_code == "Forge" for a in alerts)
        assert len(alerts) >= 1

    def test_domain_traits_checked_for_drift(self, service):
        service.register_agent("Citadel")
        profile = service.get_profile("Citadel")
        # Citadel has domain traits from DOMAIN_TRAIT_SEEDS
        if "vigilance" in profile.domain_traits:
            profile.domain_traits["vigilance"].value = (
                profile.domain_traits["vigilance"].baseline - 0.26
            )
            alerts = service.check_drift_alerts("Citadel")
            vigilance_alerts = [a for a in alerts if a.trait_name == "vigilance"]
            assert len(vigilance_alerts) == 1
            assert vigilance_alerts[0].severity == "critical"


class TestGetDriftSummary:
    """Tests for MetacognitionService.get_drift_summary()."""

    def test_empty_summary_on_fresh_profiles(self, service):
        service.register_agent("Forge")
        summary = service.get_drift_summary()
        assert summary["total_alerts"] == 0
        assert summary["critical_count"] == 0
        assert summary["warning_count"] == 0
        assert summary["alerts"] == []

    def test_summary_counts_correct(self, service):
        service.register_agent("Forge")
        profile = service.get_profile("Forge")
        profile.risk_tolerance.value = profile.risk_tolerance.baseline + 0.16  # warning
        profile.creativity.value = profile.creativity.baseline + 0.26  # critical
        summary = service.get_drift_summary()
        assert summary["total_alerts"] >= 2
        assert summary["critical_count"] >= 1
        assert summary["warning_count"] >= 1
        assert len(summary["alerts"]) == summary["total_alerts"]
