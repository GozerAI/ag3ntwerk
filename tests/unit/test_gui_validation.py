"""Tests for GUI panel robustness against malformed/invalid data.

Verifies that all GUI panels handle None, wrong types, empty containers,
and structurally invalid nested data without crashing. Each panel's update
method should either silently ignore bad data or log a warning and continue.
"""

import pytest
from unittest.mock import MagicMock

# Skip all tests if PySide6 is not available
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

# Ensure QApplication exists for widget tests
_app = QApplication.instance()
if _app is None:
    _app = QApplication([])


# ============================================================
# PersonalityPanel malformed data tests
# ============================================================


class TestPersonalityPanelMalformed:
    """PersonalityPanel must not crash on invalid inputs."""

    def test_update_profiles_none(self):
        """Passing None should not crash; panel stays empty."""
        from ag3ntwerk.gui.app import PersonalityPanel

        panel = PersonalityPanel()
        panel.update_profiles(None)
        assert len(panel._trait_widgets) == 0

    def test_update_profiles_wrong_type_string(self):
        """Passing a string instead of dict should not crash."""
        from ag3ntwerk.gui.app import PersonalityPanel

        panel = PersonalityPanel()
        panel.update_profiles("not a dict")
        assert len(panel._trait_widgets) == 0

    def test_update_profiles_agent_value_not_dict(self):
        """Agent entry that is not a dict should be skipped gracefully."""
        from ag3ntwerk.gui.app import PersonalityPanel

        panel = PersonalityPanel()
        panel.update_profiles({"Forge": "not a dict"})
        # Forge entry is invalid, so no widgets should be created
        assert len(panel._trait_widgets) == 0

    def test_update_profiles_empty_dict(self):
        """Empty dict is valid input; panel should remain empty."""
        from ag3ntwerk.gui.app import PersonalityPanel

        panel = PersonalityPanel()
        panel.update_profiles({})
        assert len(panel._trait_widgets) == 0

    def test_update_profiles_trait_info_not_dict(self):
        """Trait info that is not a dict should be skipped without crash."""
        from ag3ntwerk.gui.app import PersonalityPanel

        panel = PersonalityPanel()
        panel.update_profiles(
            {
                "Forge": {
                    "traits": {
                        "risk_tolerance": "bad_value",
                        "creativity": 42,
                    }
                }
            }
        )
        # Agent label is created, but both traits are invalid -> skipped
        assert "Forge_label" in panel._trait_widgets
        assert "Forge_risk_tolerance" not in panel._trait_widgets
        assert "Forge_creativity" not in panel._trait_widgets

    def test_update_profiles_missing_traits_key(self):
        """Agent dict without a 'traits' key should be skipped."""
        from ag3ntwerk.gui.app import PersonalityPanel

        panel = PersonalityPanel()
        panel.update_profiles({"Forge": {"something_else": True}})
        # No traits means nothing rendered for this agent
        assert len(panel._trait_widgets) == 0

    def test_update_profiles_integer_input(self):
        """Passing an integer should not crash."""
        from ag3ntwerk.gui.app import PersonalityPanel

        panel = PersonalityPanel()
        panel.update_profiles(123)
        assert len(panel._trait_widgets) == 0

    def test_update_profiles_list_input(self):
        """Passing a list instead of dict should not crash."""
        from ag3ntwerk.gui.app import PersonalityPanel

        panel = PersonalityPanel()
        panel.update_profiles([{"Forge": {}}])
        assert len(panel._trait_widgets) == 0


# ============================================================
# TrendPanel malformed data tests
# ============================================================


class TestTrendPanelMalformed:
    """TrendPanel must not crash on invalid inputs."""

    def test_update_trends_none(self):
        """Passing None should not crash; panel stays empty."""
        from ag3ntwerk.gui.app import TrendPanel

        panel = TrendPanel()
        panel.update_trends(None)
        assert len(panel._content_widgets) == 0

    def test_update_trends_agents_not_dict(self):
        """agents key containing a non-dict value should be handled."""
        from ag3ntwerk.gui.app import TrendPanel

        panel = TrendPanel()
        panel.update_trends({"agents": "not a dict"})
        assert len(panel._content_widgets) == 0

    def test_update_trends_nested_none_traits(self):
        """Agent with traits set to None should not crash."""
        from ag3ntwerk.gui.app import TrendPanel

        panel = TrendPanel()
        panel.update_trends({"agents": {"Forge": {"traits": None}}})
        # traits is falsy, so agent is skipped
        assert len(panel._content_widgets) == 0

    def test_update_trends_agent_data_not_dict(self):
        """Agent entry that is not a dict should be skipped."""
        from ag3ntwerk.gui.app import TrendPanel

        panel = TrendPanel()
        panel.update_trends({"agents": {"Forge": "invalid"}})
        assert len(panel._content_widgets) == 0

    def test_update_trends_trait_info_not_dict(self):
        """Trait info that is not a dict should be skipped."""
        from ag3ntwerk.gui.app import TrendPanel

        panel = TrendPanel()
        panel.update_trends(
            {
                "agents": {
                    "Forge": {
                        "traits": {
                            "thoroughness": "not a dict",
                        }
                    }
                }
            }
        )
        # Agent label is created, but the trait is invalid
        assert len(panel._content_widgets) == 1  # Only the Forge label

    def test_update_trends_string_input(self):
        """Passing a string should not crash."""
        from ag3ntwerk.gui.app import TrendPanel

        panel = TrendPanel()
        panel.update_trends("bad input")
        assert len(panel._content_widgets) == 0


# ============================================================
# CoherencePanel malformed data tests
# ============================================================


class TestCoherencePanelMalformed:
    """CoherencePanel must not crash on invalid inputs."""

    def test_update_coherence_none(self):
        """Passing None should not crash; panel stays empty."""
        from ag3ntwerk.gui.app import CoherencePanel

        panel = CoherencePanel()
        panel.update_coherence(None)
        assert len(panel._content_widgets) == 0

    def test_update_coherence_mixed_invalid_entries(self):
        """List with None and non-dict entries should skip invalid ones."""
        from ag3ntwerk.gui.app import CoherencePanel

        panel = CoherencePanel()
        panel.update_coherence([None, "not a dict", 42])
        assert len(panel._content_widgets) == 0

    def test_update_coherence_wrong_inner_type_tensions(self):
        """Report where tensions is not a list should handle gracefully."""
        from ag3ntwerk.gui.app import CoherencePanel

        panel = CoherencePanel()
        panel.update_coherence(
            [
                {
                    "agent_code": "Forge",
                    "coherence_score": 0.5,
                    "health_classification": "drifting",
                    "tensions": "not a list",
                }
            ]
        )
        # The agent label is created (score < 0.8 tries to iterate tensions
        # but isinstance check prevents crash)
        assert len(panel._content_widgets) == 1

    def test_update_coherence_string_input(self):
        """Passing a string instead of list should not crash."""
        from ag3ntwerk.gui.app import CoherencePanel

        panel = CoherencePanel()
        panel.update_coherence("bad input")
        assert len(panel._content_widgets) == 0

    def test_update_coherence_tension_entries_not_dicts(self):
        """Tension entries that are not dicts should be skipped."""
        from ag3ntwerk.gui.app import CoherencePanel

        panel = CoherencePanel()
        panel.update_coherence(
            [
                {
                    "agent_code": "Keystone",
                    "coherence_score": 0.4,
                    "health_classification": "degrading",
                    "tensions": [None, "bad", 99],
                }
            ]
        )
        # Agent label is created, but all tension entries are invalid
        assert len(panel._content_widgets) == 1

    def test_update_coherence_missing_keys(self):
        """Report dict missing expected keys uses defaults gracefully."""
        from ag3ntwerk.gui.app import CoherencePanel

        panel = CoherencePanel()
        panel.update_coherence([{}])
        # Uses defaults: agent_code="?", coherence_score=1.0 (>= 0.8 so no tensions)
        assert len(panel._content_widgets) == 1


# ============================================================
# TeamLearningPanel malformed data tests
# ============================================================


class TestTeamLearningPanelMalformed:
    """TeamLearningPanel must not crash on invalid inputs."""

    def test_update_teams_both_none(self):
        """Passing None for both args should not crash."""
        from ag3ntwerk.gui.app import TeamLearningPanel

        panel = TeamLearningPanel()
        panel.update_teams(None, None)
        # Both coerced to empty; shows "No team data yet"
        assert len(panel._content_widgets) == 1

    def test_update_teams_wrong_type_stats(self):
        """Passing wrong type for stats should not crash."""
        from ag3ntwerk.gui.app import TeamLearningPanel

        panel = TeamLearningPanel()
        panel.update_teams("bad", [])
        # stats coerced to {}; no compositions, no pairs => "No team data yet"
        assert len(panel._content_widgets) == 1

    def test_update_teams_wrong_type_pairs(self):
        """Passing wrong type for pairs should not crash."""
        from ag3ntwerk.gui.app import TeamLearningPanel

        panel = TeamLearningPanel()
        panel.update_teams({"compositions": []}, "not a list")
        # pairs coerced to []; no compositions, no pairs => "No team data yet"
        assert len(panel._content_widgets) == 1

    def test_update_teams_compositions_not_list(self):
        """Compositions key that is not a list should be handled."""
        from ag3ntwerk.gui.app import TeamLearningPanel

        panel = TeamLearningPanel()
        panel.update_teams({"compositions": "bad"}, [])
        # compositions coerced to []; shows "No team data yet"
        assert len(panel._content_widgets) == 1

    def test_update_teams_composition_entries_not_dicts(self):
        """Composition entries that are not dicts should be skipped."""
        from ag3ntwerk.gui.app import TeamLearningPanel

        panel = TeamLearningPanel()
        panel.update_teams({"compositions": [None, "bad", 42]}, [])
        # Header is created, but all entries are invalid -> only header
        assert len(panel._content_widgets) == 1

    def test_update_teams_pair_entries_not_dicts(self):
        """Pair entries that are not dicts should be skipped."""
        from ag3ntwerk.gui.app import TeamLearningPanel

        panel = TeamLearningPanel()
        panel.update_teams({"compositions": []}, [None, 123, "bad"])
        # Header for pairs is created, but all entries are invalid -> header only
        assert len(panel._content_widgets) == 1


# ============================================================
# TraitMapPanel malformed data tests
# ============================================================


class TestTraitMapPanelMalformed:
    """TraitMapPanel must not crash on invalid inputs."""

    def test_update_trait_map_none(self):
        """Passing None for learned should not crash."""
        from ag3ntwerk.gui.app import TraitMapPanel

        panel = TraitMapPanel()
        panel.update_trait_map(None, None)
        # learned coerced to {}; shows "No learned overrides yet"
        assert len(panel._content_widgets) == 1

    def test_update_trait_map_wrong_types(self):
        """Passing wrong types for both args should not crash."""
        from ag3ntwerk.gui.app import TraitMapPanel

        panel = TraitMapPanel()
        panel.update_trait_map({"learned": "bad", "updates": 123}, "not a list")
        # learned is a dict (keys: "learned", "updates"), updates coerced to []
        # "learned" key -> traits = "bad" (not a dict) -> skipped with warning
        # "updates" key -> traits = 123 (not a dict) -> skipped with warning
        assert len(panel._content_widgets) == 0

    def test_update_trait_map_traits_not_dict(self):
        """Task type with non-dict traits should be skipped."""
        from ag3ntwerk.gui.app import TraitMapPanel

        panel = TraitMapPanel()
        panel.update_trait_map({"code_review": "not a dict"}, [])
        # "code_review" value is not a dict -> skipped
        assert len(panel._content_widgets) == 0

    def test_update_trait_map_non_numeric_values(self):
        """Trait values that are not numeric should be displayed without crash."""
        from ag3ntwerk.gui.app import TraitMapPanel

        panel = TraitMapPanel()
        panel.update_trait_map(
            {"code_review": {"thoroughness": "not_a_number"}},
            [],
        )
        # Header + trait label (falls back to str representation)
        assert len(panel._content_widgets) == 2

    def test_update_trait_map_updates_entries_not_dicts(self):
        """Update entries that are not dicts should be skipped in validation map."""
        from ag3ntwerk.gui.app import TraitMapPanel

        panel = TraitMapPanel()
        panel.update_trait_map(
            {"code_review": {"thoroughness": 0.9}},
            [None, "bad", 42],
        )
        # Should still render the learned trait map normally
        assert len(panel._content_widgets) == 2


# ============================================================
# DriftAlertBanner malformed data tests
# ============================================================


class TestDriftAlertBannerMalformed:
    """DriftAlertBanner must not crash on invalid inputs."""

    def test_update_alerts_none(self):
        """Passing None should not crash; banner stays hidden."""
        from ag3ntwerk.gui.app import DriftAlertBanner

        banner = DriftAlertBanner()
        banner.update_alerts(None)
        assert not banner.isVisible()

    def test_update_alerts_string(self):
        """Passing a string instead of list should not crash."""
        from ag3ntwerk.gui.app import DriftAlertBanner

        banner = DriftAlertBanner()
        banner.update_alerts("not a list")
        assert not banner.isVisible()

    def test_update_alerts_entries_not_dicts(self):
        """Alert entries that are not dicts should be skipped."""
        from ag3ntwerk.gui.app import DriftAlertBanner

        banner = DriftAlertBanner()
        banner.update_alerts([None, "bad", 42])
        assert not banner.isVisible()

    def test_update_alerts_malformed_critical(self):
        """Critical alert missing required keys should be handled."""
        from ag3ntwerk.gui.app import DriftAlertBanner

        banner = DriftAlertBanner()
        banner.update_alerts(
            [
                {"severity": "critical"},  # Missing agent_code, trait_name, drift
            ]
        )
        # Malformed entry is skipped, no parts -> hidden
        assert not banner.isVisible()
