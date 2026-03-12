"""Tests for GUI wiring of PersonalityPanel and DriftAlertBanner (Phase 3, Step 6)."""

import pytest
from unittest.mock import MagicMock, patch

# Skip all tests if PySide6 is not available
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

# Ensure QApplication exists for widget tests
_app = QApplication.instance()
if _app is None:
    _app = QApplication([])


class TestDriftAlertBanner:
    """Tests for the DriftAlertBanner widget."""

    def test_hidden_by_default(self):
        from ag3ntwerk.gui.app import DriftAlertBanner

        banner = DriftAlertBanner()
        assert not banner.isVisible()

    def test_shows_on_critical_alerts(self):
        from ag3ntwerk.gui.app import DriftAlertBanner

        banner = DriftAlertBanner()
        alerts = [
            {
                "agent_code": "Forge",
                "trait_name": "risk_tolerance",
                "drift": 0.28,
                "severity": "critical",
            },
        ]
        banner.update_alerts(alerts)
        assert banner.isVisible()
        assert "Forge" in banner._label.text()

    def test_hidden_on_warning_only(self):
        from ag3ntwerk.gui.app import DriftAlertBanner

        banner = DriftAlertBanner()
        alerts = [
            {
                "agent_code": "Forge",
                "trait_name": "risk_tolerance",
                "drift": 0.17,
                "severity": "warning",
            },
        ]
        banner.update_alerts(alerts)
        assert not banner.isVisible()

    def test_hidden_on_empty_alerts(self):
        from ag3ntwerk.gui.app import DriftAlertBanner

        banner = DriftAlertBanner()
        banner.update_alerts([])
        assert not banner.isVisible()

    def test_truncates_many_alerts(self):
        from ag3ntwerk.gui.app import DriftAlertBanner

        banner = DriftAlertBanner()
        alerts = [
            {"agent_code": f"A{i}", "trait_name": f"t{i}", "drift": 0.3, "severity": "critical"}
            for i in range(5)
        ]
        banner.update_alerts(alerts)
        assert banner.isVisible()
        assert "+2 more" in banner._label.text()


class TestPersonalityPanelWiring:
    """Tests for PersonalityPanel update integration."""

    def test_update_profiles_populates_widgets(self):
        from ag3ntwerk.gui.app import PersonalityPanel

        panel = PersonalityPanel()
        profiles = {
            "Forge": {
                "traits": {
                    "risk_tolerance": {"value": 0.5, "baseline": 0.5, "drift": 0.0},
                    "creativity": {"value": 0.7, "baseline": 0.7, "drift": 0.0},
                },
            },
        }
        panel.update_profiles(profiles)
        # Should have created widgets for Forge label + 2 traits
        assert len(panel._trait_widgets) == 3  # CTO_label + 2 traits

    def test_update_profiles_clears_old(self):
        from ag3ntwerk.gui.app import PersonalityPanel

        panel = PersonalityPanel()
        profiles_v1 = {
            "Forge": {"traits": {"risk_tolerance": {"value": 0.5, "baseline": 0.5, "drift": 0.0}}},
        }
        panel.update_profiles(profiles_v1)
        assert len(panel._trait_widgets) == 2  # label + 1 trait

        profiles_v2 = {
            "Keystone": {"traits": {"thoroughness": {"value": 0.9, "baseline": 0.9, "drift": 0.0}}},
        }
        panel.update_profiles(profiles_v2)
        # Old Forge widgets should be gone, new Keystone widgets present
        assert "Keystone_label" in panel._trait_widgets
        assert "Forge_label" not in panel._trait_widgets


class TestBackendSignals:
    """Tests for new backend signals."""

    def test_backend_has_metacognition_signal(self):
        from ag3ntwerk.gui.backend import AgentWerkBackend

        backend = AgentWerkBackend()
        assert hasattr(backend, "metacognition_status")
        assert hasattr(backend, "drift_alerts")
        backend.cleanup()
