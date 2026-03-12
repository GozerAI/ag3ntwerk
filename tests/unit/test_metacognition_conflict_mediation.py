"""Tests for conflict mediation in system reflection (Phase 3, Step 7)."""

import pytest
from unittest.mock import MagicMock, patch, call

from ag3ntwerk.core.base import Task
from ag3ntwerk.core.personality_dynamics import ConflictDetection
from ag3ntwerk.core.reflection import SystemReflection


def _make_cos():
    from ag3ntwerk.agents.overwatch.agent import Overwatch

    return Overwatch(llm_provider=None, enable_health_routing=False)


class FakeAgent:
    def __init__(self, code):
        self.code = code
        self.name = code
        self.domain = "test"
        self.personality = None
        self._reflector = None
        self._heuristic_engine = None
        self._metacognition_service = None
        self._subordinates = {}
        self._active = True

    @property
    def is_active(self):
        return self._active

    def can_handle(self, task):
        return True


class TestConflictMediation:
    """Tests for trigger_system_reflection() with conflict detection."""

    def test_returns_none_without_service(self):
        cos = _make_cos()
        assert cos.trigger_system_reflection() is None

    def test_includes_conflicts_in_result(self):
        cos = _make_cos()
        svc = MagicMock()
        cos._metacognition_service = svc
        cos._subordinates = {"Forge": FakeAgent("Forge"), "Keystone": FakeAgent("Keystone")}

        svc.detect_team_conflicts.return_value = [
            ConflictDetection(
                agents_involved=["Forge", "Keystone"],
                severity=0.6,
                conflict_type="style",
                description="Forge/Keystone style clash",
                recommendation="assign different tracks",
            ),
        ]
        svc.system_reflect.return_value = SystemReflection()
        svc.save_if_auto = MagicMock()

        result = cos.trigger_system_reflection()
        assert result is not None
        assert "conflicts" in result
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["agents_involved"] == ["Forge", "Keystone"]

    def test_stores_active_conflicts(self):
        cos = _make_cos()
        svc = MagicMock()
        cos._metacognition_service = svc
        cos._subordinates = {"Forge": FakeAgent("Forge")}

        conflicts = [
            ConflictDetection(
                agents_involved=["Forge"],
                severity=0.3,
                conflict_type="minor",
                description="minor",
                recommendation="none",
            ),
        ]
        svc.detect_team_conflicts.return_value = conflicts
        svc.system_reflect.return_value = SystemReflection()
        svc.save_if_auto = MagicMock()

        cos.trigger_system_reflection()
        assert cos._active_conflicts == conflicts

    def test_auto_saves_profiles(self):
        cos = _make_cos()
        svc = MagicMock()
        cos._metacognition_service = svc
        cos._subordinates = {}

        svc.detect_team_conflicts.return_value = []
        svc.system_reflect.return_value = SystemReflection()

        cos.trigger_system_reflection()
        svc.save_if_auto.assert_called_once()

    def test_passes_compatibility_issues_to_system_reflect(self):
        cos = _make_cos()
        svc = MagicMock()
        cos._metacognition_service = svc
        cos._subordinates = {"Forge": FakeAgent("Forge"), "Echo": FakeAgent("Echo")}

        svc.detect_team_conflicts.return_value = [
            ConflictDetection(
                agents_involved=["Forge", "Echo"],
                severity=0.6,
                conflict_type="approach",
                description="clash",
                recommendation="mediate",
            ),
        ]
        svc.system_reflect.return_value = SystemReflection()
        svc.save_if_auto = MagicMock()

        cos.trigger_system_reflection()

        # Verify compatibility_issues was passed
        call_kwargs = svc.system_reflect.call_args[1]
        assert "compatibility_issues" in call_kwargs
        issues = call_kwargs["compatibility_issues"]
        assert len(issues) == 1
        assert issues[0]["severity"] == 0.6
