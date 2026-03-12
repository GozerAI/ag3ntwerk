"""Tests for inter-agent personality dynamics (Phase 2, Step 4)."""

import pytest

from ag3ntwerk.core.personality import (
    PersonalityProfile,
    PersonalityTrait,
    create_seeded_profile,
)
from ag3ntwerk.core.personality_dynamics import (
    PersonalityDynamicsEngine,
    CompatibilityResult,
    ConflictDetection,
    TeamSuggestion,
    CONFLICT_PAIRS,
)
from ag3ntwerk.core.reflection import SystemReflector
from ag3ntwerk.modules.metacognition.service import MetacognitionService


# =========================================================================
# CompatibilityResult
# =========================================================================


class TestCompatibilityResult:
    def test_to_dict(self):
        result = CompatibilityResult(
            agent_a="Forge",
            agent_b="Echo",
            overall_score=0.75,
            trait_scores={"creativity": 0.8},
            synergies=["Both creative"],
        )
        d = result.to_dict()
        assert d["agent_a"] == "Forge"
        assert d["overall_score"] == 0.75
        assert "creativity" in d["trait_scores"]


# =========================================================================
# PersonalityDynamicsEngine.compute_compatibility
# =========================================================================


class TestComputeCompatibility:
    def setup_method(self):
        self.engine = PersonalityDynamicsEngine()

    def test_identical_profiles_perfect_compatibility(self):
        p1 = create_seeded_profile("Forge")
        p2 = create_seeded_profile("Forge")
        p2.agent_code = "CTO2"
        result = self.engine.compute_compatibility(p1, p2)
        assert abs(result.overall_score - 1.0) < 1e-6
        assert result.friction_points == []

    def test_opposing_profiles_low_compatibility(self):
        p1 = PersonalityProfile(
            agent_code="A",
            risk_tolerance=PersonalityTrait("risk_tolerance", 1.0, 1.0),
            thoroughness=PersonalityTrait("thoroughness", 0.0, 0.0),
            creativity=PersonalityTrait("creativity", 1.0, 1.0),
            assertiveness=PersonalityTrait("assertiveness", 0.0, 0.0),
            collaboration=PersonalityTrait("collaboration", 1.0, 1.0),
            adaptability=PersonalityTrait("adaptability", 0.0, 0.0),
        )
        p2 = PersonalityProfile(
            agent_code="B",
            risk_tolerance=PersonalityTrait("risk_tolerance", 0.0, 0.0),
            thoroughness=PersonalityTrait("thoroughness", 1.0, 1.0),
            creativity=PersonalityTrait("creativity", 0.0, 0.0),
            assertiveness=PersonalityTrait("assertiveness", 1.0, 1.0),
            collaboration=PersonalityTrait("collaboration", 0.0, 0.0),
            adaptability=PersonalityTrait("adaptability", 1.0, 1.0),
        )
        result = self.engine.compute_compatibility(p1, p2)
        assert result.overall_score < 0.3
        assert len(result.friction_points) > 0

    def test_synergies_detected(self):
        p1 = PersonalityProfile(
            agent_code="A",
            creativity=PersonalityTrait("creativity", 0.9, 0.9),
        )
        p2 = PersonalityProfile(
            agent_code="B",
            creativity=PersonalityTrait("creativity", 0.8, 0.8),
        )
        result = self.engine.compute_compatibility(p1, p2)
        synergy_creativity = [s for s in result.synergies if "creativity" in s]
        assert len(synergy_creativity) > 0

    def test_seeded_profiles_compatibility(self):
        cto = create_seeded_profile("Forge")
        cmo = create_seeded_profile("Echo")
        result = self.engine.compute_compatibility(cto, cmo)
        assert 0.0 <= result.overall_score <= 1.0
        assert result.agent_a == "Forge"
        assert result.agent_b == "Echo"


# =========================================================================
# PersonalityDynamicsEngine.detect_conflicts
# =========================================================================


class TestDetectConflicts:
    def setup_method(self):
        self.engine = PersonalityDynamicsEngine()

    def test_no_conflicts_with_similar_profiles(self):
        profiles = {
            "A": create_seeded_profile("Forge"),
            "B": create_seeded_profile("Forge"),
        }
        profiles["B"].agent_code = "B"
        conflicts = self.engine.detect_conflicts(profiles)
        assert len(conflicts) == 0

    def test_conflicts_with_opposing_traits(self):
        profiles = {
            "A": PersonalityProfile(
                agent_code="A",
                risk_tolerance=PersonalityTrait("risk_tolerance", 0.9, 0.9),
                thoroughness=PersonalityTrait("thoroughness", 0.2, 0.2),
                assertiveness=PersonalityTrait("assertiveness", 0.9, 0.9),
                collaboration=PersonalityTrait("collaboration", 0.2, 0.2),
            ),
            "B": PersonalityProfile(
                agent_code="B",
                risk_tolerance=PersonalityTrait("risk_tolerance", 0.2, 0.2),
                thoroughness=PersonalityTrait("thoroughness", 0.9, 0.9),
                assertiveness=PersonalityTrait("assertiveness", 0.2, 0.2),
                collaboration=PersonalityTrait("collaboration", 0.9, 0.9),
            ),
        }
        conflicts = self.engine.detect_conflicts(profiles)
        assert len(conflicts) >= 1
        assert conflicts[0].severity > 0.3

    def test_working_together_filters(self):
        profiles = {
            "A": create_seeded_profile("Forge"),
            "B": create_seeded_profile("Echo"),
            "C": create_seeded_profile("Keystone"),
        }
        # Only check A and B
        conflicts = self.engine.detect_conflicts(profiles, working_together=["A", "B"])
        # Should not include C
        for c in conflicts:
            assert "C" not in c.agents_involved

    def test_conflict_has_recommendation(self):
        profiles = {
            "A": PersonalityProfile(
                agent_code="A",
                risk_tolerance=PersonalityTrait("risk_tolerance", 0.9, 0.9),
                thoroughness=PersonalityTrait("thoroughness", 0.1, 0.1),
            ),
            "B": PersonalityProfile(
                agent_code="B",
                risk_tolerance=PersonalityTrait("risk_tolerance", 0.1, 0.1),
                thoroughness=PersonalityTrait("thoroughness", 0.9, 0.9),
            ),
        }
        conflicts = self.engine.detect_conflicts(profiles)
        if conflicts:
            assert conflicts[0].recommendation != ""
            assert conflicts[0].conflict_type != ""


# =========================================================================
# PersonalityDynamicsEngine.suggest_team
# =========================================================================


class TestSuggestTeam:
    def setup_method(self):
        self.engine = PersonalityDynamicsEngine()

    def test_suggest_team_returns_correct_size(self):
        profiles = {
            code: create_seeded_profile(code) for code in ["Forge", "Echo", "Keystone", "Sentinel", "Blueprint"]
        }
        suggestion = self.engine.suggest_team(
            profiles,
            {"thoroughness": 0.9, "risk_tolerance": 0.2},
            team_size=3,
        )
        assert len(suggestion.suggested_agents) == 3

    def test_suggest_team_picks_best_fit(self):
        profiles = {code: create_seeded_profile(code) for code in ["Forge", "Echo", "Keystone", "Citadel"]}
        suggestion = self.engine.suggest_team(
            profiles,
            {"thoroughness": 0.95, "risk_tolerance": 0.1},
            team_size=2,
        )
        # Citadel and Keystone should be top picks for high thoroughness / low risk
        assert "Citadel" in suggestion.suggested_agents or "Keystone" in suggestion.suggested_agents

    def test_suggest_team_empty_profiles(self):
        suggestion = self.engine.suggest_team({}, {"creativity": 0.9}, team_size=3)
        assert suggestion.suggested_agents == []

    def test_suggest_team_has_scores(self):
        profiles = {code: create_seeded_profile(code) for code in ["Forge", "Echo"]}
        suggestion = self.engine.suggest_team(
            profiles,
            {"creativity": 0.9},
            team_size=2,
        )
        assert len(suggestion.scores) == 2
        for score in suggestion.scores.values():
            assert 0.0 <= score <= 1.0


# =========================================================================
# PersonalityDynamicsEngine.get_compatibility_matrix
# =========================================================================


class TestCompatibilityMatrix:
    def test_matrix_symmetric(self):
        engine = PersonalityDynamicsEngine()
        profiles = {code: create_seeded_profile(code) for code in ["Forge", "Echo", "Keystone"]}
        matrix = engine.get_compatibility_matrix(profiles)
        assert matrix["Forge"]["Echo"] == matrix["Echo"]["Forge"]
        assert matrix["Forge"]["Keystone"] == matrix["Keystone"]["Forge"]

    def test_matrix_diagonal_is_one(self):
        engine = PersonalityDynamicsEngine()
        profiles = {code: create_seeded_profile(code) for code in ["Forge", "Echo"]}
        matrix = engine.get_compatibility_matrix(profiles)
        assert matrix["Forge"]["Forge"] == 1.0
        assert matrix["Echo"]["Echo"] == 1.0

    def test_matrix_values_bounded(self):
        engine = PersonalityDynamicsEngine()
        profiles = {code: create_seeded_profile(code) for code in ["Forge", "Echo", "Keystone", "Sentinel"]}
        matrix = engine.get_compatibility_matrix(profiles)
        for code_a in matrix:
            for code_b in matrix[code_a]:
                assert 0.0 <= matrix[code_a][code_b] <= 1.0


# =========================================================================
# MetacognitionService dynamics integration
# =========================================================================


class TestServiceDynamics:
    def test_get_compatibility(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.register_agent("Echo")
        result = svc.get_compatibility("Forge", "Echo")
        assert result is not None
        assert 0.0 <= result.overall_score <= 1.0

    def test_get_compatibility_unknown_agent(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        result = svc.get_compatibility("Forge", "UNKNOWN")
        assert result is None

    def test_detect_team_conflicts(self):
        svc = MetacognitionService()
        for code in ["Forge", "Echo", "Keystone"]:
            svc.register_agent(code)
        conflicts = svc.detect_team_conflicts()
        assert isinstance(conflicts, list)

    def test_suggest_team_for_task(self):
        svc = MetacognitionService()
        for code in ["Forge", "Echo", "Keystone", "Sentinel"]:
            svc.register_agent(code)
        suggestion = svc.suggest_team_for_task(
            {"thoroughness": 0.9, "risk_tolerance": 0.2},
            team_size=2,
        )
        assert len(suggestion.suggested_agents) == 2

    def test_get_compatibility_matrix(self):
        svc = MetacognitionService()
        for code in ["Forge", "Echo"]:
            svc.register_agent(code)
        matrix = svc.get_compatibility_matrix()
        assert "Forge" in matrix
        assert "Echo" in matrix["Forge"]


# =========================================================================
# SystemReflector compatibility issues integration
# =========================================================================


class TestSystemReflectorCompatibility:
    def test_reflect_with_compatibility_issues(self):
        reflector = SystemReflector()
        issues = [
            {
                "description": "Forge and Keystone have opposing styles",
                "recommendation": "Use mediator",
                "severity": 0.7,
            }
        ]
        result = reflector.reflect(
            agent_health={},
            compatibility_issues=issues,
        )
        assert result.collaboration_effectiveness < 1.0
        assert any("conflict" in r.lower() for r in result.personality_recommendations)

    def test_reflect_without_issues(self):
        reflector = SystemReflector()
        result = reflector.reflect(agent_health={}, compatibility_issues=[])
        assert result.collaboration_effectiveness == 1.0

    def test_reflect_low_severity_not_included(self):
        reflector = SystemReflector()
        issues = [
            {
                "description": "Minor difference",
                "recommendation": "",
                "severity": 0.3,
            }
        ]
        result = reflector.reflect(agent_health={}, compatibility_issues=issues)
        assert result.collaboration_effectiveness == 1.0
