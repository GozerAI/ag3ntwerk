"""Tests for Phase 5 GUI panels (TrendPanel, CoherencePanel, TeamLearningPanel, TraitMapPanel)."""

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
# TrendPanel tests
# ============================================================


class TestTrendPanel:

    def test_update_with_agents(self):
        from ag3ntwerk.gui.app import TrendPanel

        panel = TrendPanel()

        trend_data = {
            "total_snapshots": 20,
            "agents": {
                "Forge": {
                    "traits": {
                        "thoroughness": {
                            "classification": "improving",
                            "velocity": 0.02,
                            "current_value": 0.8,
                            "baseline_value": 0.7,
                        }
                    }
                },
                "Keystone": {
                    "traits": {
                        "creativity": {
                            "classification": "declining",
                            "velocity": -0.01,
                            "current_value": 0.4,
                            "baseline_value": 0.5,
                        }
                    }
                },
            },
        }
        panel.update_trends(trend_data)
        assert len(panel._content_widgets) == 4  # 2 agent labels + 2 trait labels

    def test_update_empty_data(self):
        from ag3ntwerk.gui.app import TrendPanel

        panel = TrendPanel()
        panel.update_trends({"agents": {}})
        assert len(panel._content_widgets) == 0

    def test_update_clears_old_widgets(self):
        from ag3ntwerk.gui.app import TrendPanel

        panel = TrendPanel()
        panel.update_trends(
            {
                "agents": {
                    "Forge": {
                        "traits": {"thoroughness": {"classification": "stable", "velocity": 0.0}}
                    }
                }
            }
        )
        assert len(panel._content_widgets) == 2
        panel.update_trends({"agents": {}})
        assert len(panel._content_widgets) == 0


# ============================================================
# CoherencePanel tests
# ============================================================


class TestCoherencePanel:

    def test_update_with_reports(self):
        from ag3ntwerk.gui.app import CoherencePanel

        panel = CoherencePanel()

        reports = [
            {
                "agent_code": "Forge",
                "coherence_score": 0.95,
                "health_classification": "healthy",
                "tensions": [],
            },
            {
                "agent_code": "Keystone",
                "coherence_score": 0.65,
                "health_classification": "drifting",
                "tensions": [
                    {
                        "trait_a": "risk_tolerance",
                        "trait_b": "thoroughness",
                        "description": "risk vs thoroughness tension",
                        "tension_value": 0.3,
                    }
                ],
            },
        ]
        panel.update_coherence(reports)
        # Forge: 1 label, Keystone: 1 label + 1 tension = 3
        assert len(panel._content_widgets) == 3

    def test_no_tensions_shown_for_high_coherence(self):
        from ag3ntwerk.gui.app import CoherencePanel

        panel = CoherencePanel()
        reports = [
            {
                "agent_code": "Forge",
                "coherence_score": 0.95,
                "health_classification": "healthy",
                "tensions": [{"trait_a": "a", "trait_b": "b", "description": "test"}],
            }
        ]
        panel.update_coherence(reports)
        # High coherence (>= 0.8) — tensions not shown
        assert len(panel._content_widgets) == 1

    def test_empty_reports(self):
        from ag3ntwerk.gui.app import CoherencePanel

        panel = CoherencePanel()
        panel.update_coherence([])
        assert len(panel._content_widgets) == 0


# ============================================================
# TeamLearningPanel tests
# ============================================================


class TestTeamLearningPanel:

    def test_update_with_compositions_and_pairs(self):
        from ag3ntwerk.gui.app import TeamLearningPanel

        panel = TeamLearningPanel()

        stats = {
            "total_team_outcomes": 20,
            "compositions": [
                {
                    "team": ["Forge", "Keystone"],
                    "task_type": "code_review",
                    "success_rate": 0.9,
                    "samples": 10,
                },
            ],
        }
        pairs = [
            {"pair": ["Forge", "Keystone"], "success_rate": 0.9, "samples": 10},
        ]
        panel.update_teams(stats, pairs)
        # 1 "Top Compositions" header + 1 comp + 1 "Best Pairs" header + 1 pair = 4
        assert len(panel._content_widgets) == 4

    def test_empty_shows_message(self):
        from ag3ntwerk.gui.app import TeamLearningPanel

        panel = TeamLearningPanel()
        panel.update_teams({"compositions": []}, [])
        # Should show "No team data yet"
        assert len(panel._content_widgets) == 1

    def test_only_compositions(self):
        from ag3ntwerk.gui.app import TeamLearningPanel

        panel = TeamLearningPanel()
        stats = {
            "compositions": [
                {"team": ["Forge", "Keystone"], "task_type": "code_review", "success_rate": 1.0},
            ]
        }
        panel.update_teams(stats, [])
        # 1 header + 1 comp = 2
        assert len(panel._content_widgets) == 2


# ============================================================
# TraitMapPanel tests
# ============================================================


class TestTraitMapPanel:

    def test_update_with_learned_and_updates(self):
        from ag3ntwerk.gui.app import TraitMapPanel

        panel = TraitMapPanel()

        learned = {
            "code_review": {"thoroughness": 0.92},
        }
        updates = [
            {
                "task_type": "code_review",
                "trait_name": "thoroughness",
                "validation_status": "validated",
            },
        ]
        panel.update_trait_map(learned, updates)
        # 1 task_type header + 1 trait = 2
        assert len(panel._content_widgets) == 2

    def test_empty_shows_message(self):
        from ag3ntwerk.gui.app import TraitMapPanel

        panel = TraitMapPanel()
        panel.update_trait_map({}, [])
        assert len(panel._content_widgets) == 1  # "No learned overrides yet"

    def test_multiple_task_types(self):
        from ag3ntwerk.gui.app import TraitMapPanel

        panel = TraitMapPanel()

        learned = {
            "code_review": {"thoroughness": 0.9, "creativity": 0.8},
            "market_research": {"creativity": 0.85},
        }
        panel.update_trait_map(learned, [])
        # 2 headers + 3 traits = 5
        assert len(panel._content_widgets) == 5

    def test_validation_status_lookup(self):
        from ag3ntwerk.gui.app import TraitMapPanel

        panel = TraitMapPanel()

        learned = {"code_review": {"thoroughness": 0.9}}
        updates = [
            {
                "task_type": "code_review",
                "trait_name": "thoroughness",
                "validation_status": "rolled_back",
            },
        ]
        panel.update_trait_map(learned, updates)
        assert len(panel._content_widgets) == 2
