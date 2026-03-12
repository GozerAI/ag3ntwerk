"""
Personality Dynamics Engine for ag3ntwerk agents.

Computes inter-agent compatibility, detects conflicts from trait
mismatches, and suggests team compositions for task types.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ag3ntwerk.core.personality import PersonalityProfile

logger = logging.getLogger(__name__)


# Trait pairs that create friction when both are extreme in opposing directions
CONFLICT_PAIRS: List[Tuple[str, str]] = [
    ("risk_tolerance", "thoroughness"),
    ("assertiveness", "collaboration"),
]


@dataclass
class CompatibilityResult:
    """Per-pair compatibility assessment."""

    agent_a: str
    agent_b: str
    overall_score: float = 0.5
    trait_scores: Dict[str, float] = field(default_factory=dict)
    synergies: List[str] = field(default_factory=list)
    friction_points: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "overall_score": round(self.overall_score, 3),
            "trait_scores": {k: round(v, 3) for k, v in self.trait_scores.items()},
            "synergies": self.synergies,
            "friction_points": self.friction_points,
        }


@dataclass
class ConflictDetection:
    """Detected conflict between agents working together."""

    agents_involved: List[str] = field(default_factory=list)
    severity: float = 0.0
    conflict_type: str = ""
    description: str = ""
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agents_involved": self.agents_involved,
            "severity": round(self.severity, 3),
            "conflict_type": self.conflict_type,
            "description": self.description,
            "recommendation": self.recommendation,
        }


@dataclass
class TeamSuggestion:
    """Suggested team for a task based on personality traits."""

    suggested_agents: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggested_agents": self.suggested_agents,
            "scores": {k: round(v, 3) for k, v in self.scores.items()},
            "reasoning": self.reasoning,
        }


class PersonalityDynamicsEngine:
    """
    Computes compatibility, detects conflicts, and suggests teams.
    """

    def compute_compatibility(
        self,
        profile_a: PersonalityProfile,
        profile_b: PersonalityProfile,
    ) -> CompatibilityResult:
        """
        Compute compatibility between two agents.

        Scores each trait pair and identifies synergies and friction.

        Returns CompatibilityResult with 0.0-1.0 score (higher = more compatible).
        """
        result = CompatibilityResult(
            agent_a=profile_a.agent_code,
            agent_b=profile_b.agent_code,
        )

        traits_a = profile_a.get_all_traits()
        traits_b = profile_b.get_all_traits()

        total_score = 0.0
        count = 0

        for name in traits_a:
            if name in traits_b:
                val_a = traits_a[name].value
                val_b = traits_b[name].value
                distance = abs(val_a - val_b)

                # Complementary traits (moderate difference) can be positive
                # Identical traits score well for alignment
                trait_compat = 1.0 - distance
                result.trait_scores[name] = trait_compat
                total_score += trait_compat
                count += 1

                # Identify synergies (both strong in same trait)
                if val_a > 0.7 and val_b > 0.7:
                    result.synergies.append(f"Both strong in {name} ({val_a:.2f}, {val_b:.2f})")

                # Identify friction (very different values)
                if distance > 0.5:
                    result.friction_points.append(
                        f"Opposing {name}: {profile_a.agent_code}={val_a:.2f}, "
                        f"{profile_b.agent_code}={val_b:.2f}"
                    )

        result.overall_score = total_score / max(1, count)
        return result

    def detect_conflicts(
        self,
        profiles: Dict[str, PersonalityProfile],
        working_together: Optional[List[str]] = None,
    ) -> List[ConflictDetection]:
        """
        Detect personality conflicts among agents working together.

        If working_together is None, checks all pairs.
        """
        codes = working_together or list(profiles.keys())
        conflicts = []

        for i, code_a in enumerate(codes):
            for code_b in codes[i + 1 :]:
                profile_a = profiles.get(code_a)
                profile_b = profiles.get(code_b)
                if not profile_a or not profile_b:
                    continue

                traits_a = profile_a.get_all_traits()
                traits_b = profile_b.get_all_traits()

                for trait_x, trait_y in CONFLICT_PAIRS:
                    tx_a = traits_a.get(trait_x)
                    ty_a = traits_a.get(trait_y)
                    tx_b = traits_b.get(trait_x)
                    ty_b = traits_b.get(trait_y)

                    if not (tx_a and ty_a and tx_b and ty_b):
                        continue

                    # Conflict: A is high-X/low-Y, B is low-X/high-Y
                    a_divergence = tx_a.value - ty_a.value
                    b_divergence = tx_b.value - ty_b.value

                    if a_divergence * b_divergence < -0.1:
                        severity = abs(a_divergence - b_divergence) / 2.0
                        if severity > 0.3:
                            conflicts.append(
                                ConflictDetection(
                                    agents_involved=[code_a, code_b],
                                    severity=min(1.0, severity),
                                    conflict_type=f"{trait_x}_vs_{trait_y}",
                                    description=(
                                        f"{code_a} favors {trait_x} over {trait_y}, "
                                        f"while {code_b} favors {trait_y} over {trait_x}"
                                    ),
                                    recommendation=(
                                        f"Use a mediator or clear roles when "
                                        f"{code_a} and {code_b} collaborate on tasks "
                                        f"involving {trait_x}/{trait_y} trade-offs"
                                    ),
                                )
                            )

        return conflicts

    def suggest_team(
        self,
        profiles: Dict[str, PersonalityProfile],
        task_traits: Dict[str, float],
        team_size: int = 3,
    ) -> TeamSuggestion:
        """
        Suggest a team for a task based on personality fit.

        Selects agents with best task fit, then checks for compatibility.
        """
        # Score all agents for task fit
        scores = {}
        for code, profile in profiles.items():
            scores[code] = profile.compute_task_fit(task_traits)

        # Sort by score descending
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Take top candidates
        team = [code for code, _ in sorted_agents[:team_size]]

        return TeamSuggestion(
            suggested_agents=team,
            scores={code: scores[code] for code in team},
            reasoning=(
                f"Selected top {len(team)} agents by task fit. "
                f"Best: {team[0]} ({scores[team[0]]:.2f})"
                if team
                else "No agents available"
            ),
        )

    def get_compatibility_matrix(
        self,
        profiles: Dict[str, PersonalityProfile],
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute full compatibility matrix for all agent pairs.

        Returns dict of {agent_a: {agent_b: score}}.
        """
        codes = list(profiles.keys())
        matrix: Dict[str, Dict[str, float]] = {}

        for code in codes:
            matrix[code] = {}

        for i, code_a in enumerate(codes):
            matrix[code_a][code_a] = 1.0
            for code_b in codes[i + 1 :]:
                profile_a = profiles[code_a]
                profile_b = profiles[code_b]
                result = self.compute_compatibility(profile_a, profile_b)
                matrix[code_a][code_b] = result.overall_score
                matrix[code_b][code_a] = result.overall_score

        return matrix
