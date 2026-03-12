"""Tests for team formation and conflict-aware routing (Phase 3, Step 5)."""

import pytest
from unittest.mock import MagicMock, patch

from ag3ntwerk.core.base import Task, TaskResult, TaskStatus
from ag3ntwerk.core.personality_dynamics import ConflictDetection, TeamSuggestion


def _make_cos(**kwargs):
    """Create a Overwatch with minimal dependencies for testing."""
    from ag3ntwerk.agents.overwatch.agent import Overwatch

    return Overwatch(llm_provider=None, enable_health_routing=False, **kwargs)


def _make_task(task_type="general", desc="test"):
    return Task(description=desc, task_type=task_type)


class FakeAgent:
    """Minimal stub for a subordinate agent."""

    def __init__(self, code):
        self.code = code
        self.name = code
        self.domain = "test"
        self.personality = None
        self._reflector = None
        self._heuristic_engine = None
        self._active = True

    @property
    def is_active(self):
        return self._active

    def can_handle(self, task):
        return True


class TestFilterConflictingAgents:
    """Tests for Overwatch._filter_conflicting_agents()."""

    def test_returns_candidates_when_no_service(self):
        cos = _make_cos()
        cos._metacognition_service = None
        candidates = ["Forge", "Keystone"]
        result = cos._filter_conflicting_agents(_make_task(), candidates)
        assert result == candidates

    def test_returns_candidates_when_single(self):
        cos = _make_cos()
        cos._metacognition_service = MagicMock()
        result = cos._filter_conflicting_agents(_make_task(), ["Forge"])
        assert result == ["Forge"]

    def test_returns_all_when_no_active_tasks(self):
        cos = _make_cos()
        cos._metacognition_service = MagicMock()
        cos._active_tasks = {}
        result = cos._filter_conflicting_agents(_make_task(), ["Forge", "Keystone"])
        assert result == ["Forge", "Keystone"]

    def test_filters_high_severity_conflict(self):
        cos = _make_cos()
        svc = MagicMock()
        cos._metacognition_service = svc

        # Set up active task assigned to Echo
        active_task = _make_task()
        active_task.assigned_to = "Echo"
        cos._active_tasks = {"t1": active_task}
        cos._subordinates["Echo"] = FakeAgent("Echo")
        cos._subordinates["Forge"] = FakeAgent("Forge")
        cos._subordinates["Keystone"] = FakeAgent("Keystone")

        # Forge has high conflict with Echo, Keystone doesn't
        def detect_conflicts(agents):
            if "Forge" in agents:
                return [
                    ConflictDetection(
                        agents_involved=["Echo", "Forge"],
                        severity=0.7,
                        conflict_type="style",
                        description="test conflict",
                        recommendation="avoid",
                    )
                ]
            return []

        svc.detect_team_conflicts.side_effect = detect_conflicts
        result = cos._filter_conflicting_agents(_make_task(), ["Forge", "Keystone"])
        assert "Keystone" in result
        assert "Forge" not in result

    def test_never_filters_to_zero(self):
        cos = _make_cos()
        svc = MagicMock()
        cos._metacognition_service = svc

        active_task = _make_task()
        active_task.assigned_to = "Echo"
        cos._active_tasks = {"t1": active_task}
        cos._subordinates["Echo"] = FakeAgent("Echo")
        cos._subordinates["Forge"] = FakeAgent("Forge")

        # All candidates conflict
        svc.detect_team_conflicts.return_value = [
            ConflictDetection(
                agents_involved=["Echo", "Forge"],
                severity=0.8,
                conflict_type="style",
                description="conflict",
                recommendation="avoid",
            ),
        ]
        result = cos._filter_conflicting_agents(_make_task(), ["Forge"])
        assert len(result) >= 1  # Never empty


class TestRouteCollaborativeTask:
    """Tests for Overwatch._route_collaborative_task()."""

    async def test_falls_back_to_route_task_without_service(self):
        cos = _make_cos()
        cos._metacognition_service = None

        # Patch _route_task to return a known agent
        with patch.object(cos, "_route_task", return_value="Forge"):
            team = await cos._route_collaborative_task(_make_task(), team_size=2)
        assert team == ["Forge"]

    async def test_suggests_team_with_service(self):
        cos = _make_cos()
        svc = MagicMock()
        cos._metacognition_service = svc
        cos._subordinates["Forge"] = FakeAgent("Forge")
        cos._subordinates["Keystone"] = FakeAgent("Keystone")

        svc.suggest_team_for_task.return_value = TeamSuggestion(
            suggested_agents=["Forge", "Keystone"],
            scores={"Forge": 0.9, "Keystone": 0.85},
            reasoning="good team",
        )
        svc.detect_team_conflicts.return_value = []

        team = await cos._route_collaborative_task(_make_task(), team_size=2)
        assert set(team) == {"Forge", "Keystone"}

    async def test_attaches_conflict_warnings_to_task(self):
        cos = _make_cos()
        svc = MagicMock()
        cos._metacognition_service = svc
        cos._subordinates["Forge"] = FakeAgent("Forge")
        cos._subordinates["Echo"] = FakeAgent("Echo")

        svc.suggest_team_for_task.return_value = TeamSuggestion(
            suggested_agents=["Forge", "Echo"],
            scores={"Forge": 0.9, "Echo": 0.8},
        )
        svc.detect_team_conflicts.return_value = [
            ConflictDetection(
                agents_involved=["Forge", "Echo"],
                severity=0.7,
                conflict_type="approach",
                description="Forge/Echo conflict",
                recommendation="mediate",
            ),
        ]

        task = _make_task()
        team = await cos._route_collaborative_task(task, team_size=2)
        assert len(team) == 2
        assert "_team_conflicts" in task.context
        assert len(task.context["_team_conflicts"]) == 1
