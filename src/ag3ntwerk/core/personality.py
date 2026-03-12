"""
Personality Profile System for ag3ntwerk agents.

Provides bounded trait profiles that attach to Agent and influence
LLM prompts, enabling self-differentiation across the 16 agent agents.

Traits evolve slowly based on task outcomes, bounded by stability guarantees:
- MAX_DRIFT_FROM_BASELINE = 0.3
- Momentum decay via STABILITY_DECAY = 0.98
- Confidence-based resistance (more data -> slower changes)
- Minimum sample threshold before any evolution
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================
# Constants
# ============================================================

MAX_DRIFT_FROM_BASELINE = 0.3
EVOLUTION_RATE = 0.05
MIN_SAMPLES_FOR_EVOLUTION = 5
STABILITY_DECAY = 0.98


# ============================================================
# PersonalityTrait
# ============================================================


@dataclass
class PersonalityTrait:
    """
    A single personality trait with bounded evolution.

    Traits live on a 0.0-1.0 scale and cannot drift more than
    MAX_DRIFT_FROM_BASELINE from their initial seed value.
    """

    name: str
    value: float
    baseline: float
    momentum: float = 0.0
    confidence: float = 0.0
    sample_count: int = 0

    def __post_init__(self):
        self.value = max(0.0, min(1.0, self.value))
        self.baseline = max(0.0, min(1.0, self.baseline))

    def evolve(self, delta: float, weight: float = 1.0) -> float:
        """
        Apply a bounded evolution to this trait.

        Args:
            delta: Desired change (-1.0 to 1.0)
            weight: Multiplier for the change (0.0-1.0)

        Returns:
            Actual change applied
        """
        # Scale by evolution rate and weight
        scaled_delta = delta * EVOLUTION_RATE * weight

        # Confidence-based resistance: more samples -> slower change
        if self.sample_count > 0:
            resistance = 1.0 / (1.0 + self.sample_count * 0.01)
            scaled_delta *= resistance

        # Apply momentum decay
        self.momentum = self.momentum * STABILITY_DECAY + scaled_delta

        # Calculate new value
        new_value = self.value + self.momentum

        # Enforce bounds: 0.0-1.0
        new_value = max(0.0, min(1.0, new_value))

        # Enforce drift limit from baseline
        min_allowed = max(0.0, self.baseline - MAX_DRIFT_FROM_BASELINE)
        max_allowed = min(1.0, self.baseline + MAX_DRIFT_FROM_BASELINE)
        new_value = max(min_allowed, min(max_allowed, new_value))

        actual_delta = new_value - self.value
        self.value = new_value
        self.sample_count += 1
        self.confidence = min(1.0, self.sample_count / 100.0)

        return actual_delta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "baseline": self.baseline,
            "momentum": self.momentum,
            "confidence": self.confidence,
            "sample_count": self.sample_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonalityTrait":
        return cls(
            name=data["name"],
            value=data["value"],
            baseline=data["baseline"],
            momentum=data.get("momentum", 0.0),
            confidence=data.get("confidence", 0.0),
            sample_count=data.get("sample_count", 0),
        )


# ============================================================
# PersonalityProfile
# ============================================================


@dataclass
class PersonalityProfile:
    """
    Complete personality profile for a ag3ntwerk agent.

    Contains 6 core traits, decision/communication styles, and
    extensible domain traits. Generates system prompt fragments
    for LLM personality injection.
    """

    agent_code: str
    risk_tolerance: PersonalityTrait = field(
        default_factory=lambda: PersonalityTrait("risk_tolerance", 0.5, 0.5)
    )
    creativity: PersonalityTrait = field(
        default_factory=lambda: PersonalityTrait("creativity", 0.5, 0.5)
    )
    thoroughness: PersonalityTrait = field(
        default_factory=lambda: PersonalityTrait("thoroughness", 0.5, 0.5)
    )
    assertiveness: PersonalityTrait = field(
        default_factory=lambda: PersonalityTrait("assertiveness", 0.5, 0.5)
    )
    collaboration: PersonalityTrait = field(
        default_factory=lambda: PersonalityTrait("collaboration", 0.5, 0.5)
    )
    adaptability: PersonalityTrait = field(
        default_factory=lambda: PersonalityTrait("adaptability", 0.5, 0.5)
    )

    decision_style: str = "balanced"  # analytical, intuitive, balanced, decisive
    communication_style: str = "neutral"  # formal, direct, collaborative, neutral

    domain_traits: Dict[str, PersonalityTrait] = field(default_factory=dict)
    version: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def get_all_traits(self) -> Dict[str, PersonalityTrait]:
        """Get all traits (core + domain) as a dictionary."""
        traits = {
            "risk_tolerance": self.risk_tolerance,
            "creativity": self.creativity,
            "thoroughness": self.thoroughness,
            "assertiveness": self.assertiveness,
            "collaboration": self.collaboration,
            "adaptability": self.adaptability,
        }
        traits.update(self.domain_traits)
        return traits

    def get_trait(self, name: str) -> Optional[PersonalityTrait]:
        """Get a trait by name."""
        return self.get_all_traits().get(name)

    def compute_task_fit(self, task_traits: Dict[str, float]) -> float:
        """
        Compute how well this agent's personality fits the desired task traits.

        Args:
            task_traits: Dict mapping trait names to desired values (0.0-1.0)
                e.g. {"thoroughness": 0.9, "risk_tolerance": 0.2}

        Returns:
            Score from 0.0 (poor fit) to 1.0 (perfect fit)
        """
        if not task_traits:
            return 0.5

        all_traits = self.get_all_traits()
        total_distance = 0.0
        count = 0

        for trait_name, desired_value in task_traits.items():
            trait = all_traits.get(trait_name)
            if trait:
                total_distance += abs(trait.value - desired_value)
                count += 1

        if count == 0:
            return 0.5

        avg_distance = total_distance / count
        return max(0.0, 1.0 - avg_distance)

    def to_system_prompt_fragment(self) -> str:
        """Generate a system prompt fragment describing this personality."""
        lines = [f"Personality Profile ({self.agent_code}):"]

        # Core traits as descriptors
        trait_descriptions = {
            "risk_tolerance": ("cautious", "risk-tolerant"),
            "creativity": ("methodical", "creative"),
            "thoroughness": ("pragmatic", "thorough"),
            "assertiveness": ("reserved", "assertive"),
            "collaboration": ("independent", "collaborative"),
            "adaptability": ("consistent", "adaptive"),
        }

        for trait_name, (low_desc, high_desc) in trait_descriptions.items():
            trait = self.get_trait(trait_name)
            if trait:
                if trait.value < 0.35:
                    lines.append(f"  - Strongly {low_desc}")
                elif trait.value < 0.5:
                    lines.append(f"  - Somewhat {low_desc}")
                elif trait.value > 0.65:
                    lines.append(f"  - Strongly {high_desc}")
                elif trait.value > 0.5:
                    lines.append(f"  - Somewhat {high_desc}")

        # Domain expertise traits
        if self.domain_traits:
            lines.append("  Domain expertise:")
            for name, trait in self.domain_traits.items():
                label = name.replace("_", " ").title()
                if trait.value > 0.65:
                    lines.append(f"  - High {label}")
                elif trait.value < 0.35:
                    lines.append(f"  - Low {label}")

        lines.append(f"  - Decision style: {self.decision_style}")
        lines.append(f"  - Communication style: {self.communication_style}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "risk_tolerance": self.risk_tolerance.to_dict(),
            "creativity": self.creativity.to_dict(),
            "thoroughness": self.thoroughness.to_dict(),
            "assertiveness": self.assertiveness.to_dict(),
            "collaboration": self.collaboration.to_dict(),
            "adaptability": self.adaptability.to_dict(),
            "decision_style": self.decision_style,
            "communication_style": self.communication_style,
            "domain_traits": {k: v.to_dict() for k, v in self.domain_traits.items()},
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonalityProfile":
        profile = cls(
            agent_code=data["agent_code"],
            risk_tolerance=PersonalityTrait.from_dict(data["risk_tolerance"]),
            creativity=PersonalityTrait.from_dict(data["creativity"]),
            thoroughness=PersonalityTrait.from_dict(data["thoroughness"]),
            assertiveness=PersonalityTrait.from_dict(data["assertiveness"]),
            collaboration=PersonalityTrait.from_dict(data["collaboration"]),
            adaptability=PersonalityTrait.from_dict(data["adaptability"]),
            decision_style=data.get("decision_style", "balanced"),
            communication_style=data.get("communication_style", "neutral"),
            domain_traits={
                k: PersonalityTrait.from_dict(v) for k, v in data.get("domain_traits", {}).items()
            },
            version=data.get("version", 0),
        )
        if "created_at" in data:
            try:
                profile.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
        if "updated_at" in data:
            try:
                profile.updated_at = datetime.fromisoformat(data["updated_at"])
            except (ValueError, TypeError):
                pass
        return profile


# ============================================================
# TraitEvolution
# ============================================================


@dataclass
class TraitEvolution:
    """Records a single trait change event."""

    id: str = field(default_factory=lambda: str(uuid4()))
    agent_code: str = ""
    trait_name: str = ""
    old_value: float = 0.0
    new_value: float = 0.0
    delta: float = 0.0
    reason: str = ""
    source_task_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_code": self.agent_code,
            "trait_name": self.trait_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "delta": self.delta,
            "reason": self.reason,
            "source_task_id": self.source_task_id,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================
# PersonalityEvolver
# ============================================================


class PersonalityEvolver:
    """
    Processes task outcomes and reflections to evolve a personality profile.

    Applies bounded, gradual changes based on:
    - Task success/failure patterns
    - Reflection-derived trait signals
    - Stability constraints
    """

    def __init__(self, profile: PersonalityProfile):
        self._profile = profile
        self._evolution_history: List[TraitEvolution] = []

    @property
    def profile(self) -> PersonalityProfile:
        return self._profile

    @property
    def evolution_history(self) -> List[TraitEvolution]:
        return self._evolution_history

    def process_outcome(
        self,
        success: bool,
        task_type: str,
        duration_ms: float = 0.0,
        confidence: Optional[float] = None,
        task_id: Optional[str] = None,
    ) -> List[TraitEvolution]:
        """
        Process a task outcome and evolve traits accordingly.

        Returns list of trait evolutions that occurred.
        """
        evolutions: List[TraitEvolution] = []

        # Need minimum samples before evolving
        min_trait = min(t.sample_count for t in self._profile.get_all_traits().values())
        if min_trait < MIN_SAMPLES_FOR_EVOLUTION:
            # Still count samples even if not evolving
            for trait in self._profile.get_all_traits().values():
                trait.sample_count += 1
            return evolutions

        if success:
            # Successful outcome: reinforce current tendencies slightly
            evolutions.extend(
                self._apply_signals(
                    {"adaptability": 0.02, "thoroughness": 0.01},
                    reason=f"Success on {task_type}",
                    task_id=task_id,
                )
            )
        else:
            # Failure: nudge toward more caution and thoroughness
            evolutions.extend(
                self._apply_signals(
                    {"risk_tolerance": -0.05, "thoroughness": 0.03},
                    reason=f"Failure on {task_type}",
                    task_id=task_id,
                )
            )

        return evolutions

    def process_reflection(
        self,
        trait_signals: Dict[str, float],
        reason: str = "reflection",
        task_id: Optional[str] = None,
    ) -> List[TraitEvolution]:
        """
        Process reflection-derived trait signals.

        Args:
            trait_signals: Dict mapping trait names to deltas (e.g. {"risk_tolerance": -0.1})
            reason: Why these signals were generated
            task_id: Optional source task

        Returns:
            List of trait evolutions applied
        """
        return self._apply_signals(trait_signals, reason=reason, task_id=task_id)

    def _apply_signals(
        self,
        signals: Dict[str, float],
        reason: str = "",
        task_id: Optional[str] = None,
    ) -> List[TraitEvolution]:
        """Apply trait signals with bounds checking."""
        evolutions = []

        for trait_name, delta in signals.items():
            trait = self._profile.get_trait(trait_name)
            if not trait:
                continue

            old_value = trait.value
            actual_delta = trait.evolve(delta)

            if abs(actual_delta) > 1e-6:
                evolution = TraitEvolution(
                    agent_code=self._profile.agent_code,
                    trait_name=trait_name,
                    old_value=old_value,
                    new_value=trait.value,
                    delta=actual_delta,
                    reason=reason,
                    source_task_id=task_id,
                )
                evolutions.append(evolution)
                self._evolution_history.append(evolution)

        if evolutions:
            self._profile.version += 1
            self._profile.updated_at = datetime.now(timezone.utc)

        return evolutions

    def get_stats(self) -> Dict[str, Any]:
        return {
            "agent_code": self._profile.agent_code,
            "profile_version": self._profile.version,
            "total_evolutions": len(self._evolution_history),
            "traits": {
                name: {
                    "value": trait.value,
                    "baseline": trait.baseline,
                    "drift": abs(trait.value - trait.baseline),
                    "sample_count": trait.sample_count,
                }
                for name, trait in self._profile.get_all_traits().items()
            },
        }


# ============================================================
# Personality Seeds
# ============================================================


def _make_profile(
    code: str,
    risk: float,
    creativity: float,
    thoroughness: float,
    assertiveness: float,
    collaboration: float,
    adaptability: float,
    decision: str,
    communication: str,
) -> PersonalityProfile:
    """Helper to create a seeded personality profile."""
    return PersonalityProfile(
        agent_code=code,
        risk_tolerance=PersonalityTrait("risk_tolerance", risk, risk),
        creativity=PersonalityTrait("creativity", creativity, creativity),
        thoroughness=PersonalityTrait("thoroughness", thoroughness, thoroughness),
        assertiveness=PersonalityTrait("assertiveness", assertiveness, assertiveness),
        collaboration=PersonalityTrait("collaboration", collaboration, collaboration),
        adaptability=PersonalityTrait("adaptability", adaptability, adaptability),
        decision_style=decision,
        communication_style=communication,
    )


PERSONALITY_SEEDS: Dict[str, Dict[str, Any]] = {
    "Overwatch": {
        "risk": 0.4,
        "creativity": 0.5,
        "thoroughness": 0.8,
        "assertiveness": 0.6,
        "collaboration": 0.9,
        "adaptability": 0.8,
        "decision": "balanced",
        "communication": "collaborative",
    },
    "Forge": {
        "risk": 0.5,
        "creativity": 0.7,
        "thoroughness": 0.8,
        "assertiveness": 0.7,
        "collaboration": 0.6,
        "adaptability": 0.6,
        "decision": "analytical",
        "communication": "direct",
    },
    "Keystone": {
        "risk": 0.2,
        "creativity": 0.3,
        "thoroughness": 0.9,
        "assertiveness": 0.6,
        "collaboration": 0.5,
        "adaptability": 0.3,
        "decision": "analytical",
        "communication": "formal",
    },
    "Echo": {
        "risk": 0.7,
        "creativity": 0.9,
        "thoroughness": 0.5,
        "assertiveness": 0.7,
        "collaboration": 0.8,
        "adaptability": 0.8,
        "decision": "intuitive",
        "communication": "collaborative",
    },
    "Sentinel": {
        "risk": 0.2,
        "creativity": 0.4,
        "thoroughness": 0.9,
        "assertiveness": 0.5,
        "collaboration": 0.5,
        "adaptability": 0.4,
        "decision": "analytical",
        "communication": "formal",
    },
    "Blueprint": {
        "risk": 0.6,
        "creativity": 0.8,
        "thoroughness": 0.7,
        "assertiveness": 0.6,
        "collaboration": 0.8,
        "adaptability": 0.7,
        "decision": "balanced",
        "communication": "collaborative",
    },
    "Axiom": {
        "risk": 0.5,
        "creativity": 0.6,
        "thoroughness": 0.7,
        "assertiveness": 0.5,
        "collaboration": 0.6,
        "adaptability": 0.6,
        "decision": "analytical",
        "communication": "neutral",
    },
    "Index": {
        "risk": 0.3,
        "creativity": 0.5,
        "thoroughness": 0.9,
        "assertiveness": 0.4,
        "collaboration": 0.5,
        "adaptability": 0.5,
        "decision": "analytical",
        "communication": "formal",
    },
    "Foundry": {
        "risk": 0.4,
        "creativity": 0.6,
        "thoroughness": 0.9,
        "assertiveness": 0.6,
        "collaboration": 0.7,
        "adaptability": 0.5,
        "decision": "analytical",
        "communication": "direct",
    },
    "Citadel": {
        "risk": 0.1,
        "creativity": 0.3,
        "thoroughness": 0.95,
        "assertiveness": 0.7,
        "collaboration": 0.4,
        "adaptability": 0.3,
        "decision": "analytical",
        "communication": "formal",
    },
    "Beacon": {
        "risk": 0.6,
        "creativity": 0.9,
        "thoroughness": 0.6,
        "assertiveness": 0.5,
        "collaboration": 0.8,
        "adaptability": 0.7,
        "decision": "intuitive",
        "communication": "collaborative",
    },
    "Compass": {
        "risk": 0.5,
        "creativity": 0.7,
        "thoroughness": 0.7,
        "assertiveness": 0.7,
        "collaboration": 0.6,
        "adaptability": 0.6,
        "decision": "balanced",
        "communication": "direct",
    },
    "Vector": {
        "risk": 0.6,
        "creativity": 0.6,
        "thoroughness": 0.7,
        "assertiveness": 0.8,
        "collaboration": 0.7,
        "adaptability": 0.6,
        "decision": "decisive",
        "communication": "direct",
    },
    "Aegis": {
        "risk": 0.1,
        "creativity": 0.3,
        "thoroughness": 0.95,
        "assertiveness": 0.6,
        "collaboration": 0.5,
        "adaptability": 0.3,
        "decision": "analytical",
        "communication": "formal",
    },
    "Accord": {
        "risk": 0.5,
        "creativity": 0.7,
        "thoroughness": 0.6,
        "assertiveness": 0.6,
        "collaboration": 0.9,
        "adaptability": 0.7,
        "decision": "balanced",
        "communication": "collaborative",
    },
    "Nexus": {
        "risk": 0.4,
        "creativity": 0.5,
        "thoroughness": 0.8,
        "assertiveness": 0.7,
        "collaboration": 0.8,
        "adaptability": 0.7,
        "decision": "balanced",
        "communication": "direct",
    },
}


# Domain-specific traits for the most differentiated agents
DOMAIN_TRAIT_SEEDS: Dict[str, Dict[str, float]] = {
    "Citadel": {"vigilance": 0.95, "zero_trust_mindset": 0.9, "compliance_rigor": 0.85},
    "Echo": {"audience_empathy": 0.85, "trend_sensitivity": 0.8, "narrative_craft": 0.85},
    "Keystone": {"fiscal_conservatism": 0.85, "regulatory_awareness": 0.8, "margin_sensitivity": 0.9},
    "Forge": {"system_thinking": 0.85, "tech_debt_awareness": 0.8, "scalability_focus": 0.8},
    "Aegis": {"threat_anticipation": 0.9, "scenario_modeling": 0.85, "resilience_focus": 0.8},
}


def create_seeded_profile(agent_code: str) -> PersonalityProfile:
    """Create a personality profile from seeds for a given agent code."""
    seed = PERSONALITY_SEEDS.get(agent_code)
    if not seed:
        # Default neutral profile
        return PersonalityProfile(agent_code=agent_code)

    profile = _make_profile(agent_code, **seed)
    # Add domain traits if available
    for name, value in DOMAIN_TRAIT_SEEDS.get(agent_code, {}).items():
        profile.domain_traits[name] = PersonalityTrait(name=name, value=value, baseline=value)
    return profile
