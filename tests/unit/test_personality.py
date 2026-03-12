"""Tests for the personality profile system."""

import json
import random
import pytest

from ag3ntwerk.core.personality import (
    PersonalityTrait,
    PersonalityProfile,
    TraitEvolution,
    PersonalityEvolver,
    PERSONALITY_SEEDS,
    MAX_DRIFT_FROM_BASELINE,
    EVOLUTION_RATE,
    MIN_SAMPLES_FOR_EVOLUTION,
    STABILITY_DECAY,
    create_seeded_profile,
    _make_profile,
)


class TestPersonalityTrait:
    """Tests for PersonalityTrait."""

    def test_trait_creation(self):
        trait = PersonalityTrait("risk_tolerance", 0.5, 0.5)
        assert trait.name == "risk_tolerance"
        assert trait.value == 0.5
        assert trait.baseline == 0.5
        assert trait.momentum == 0.0
        assert trait.sample_count == 0

    def test_trait_bounds_clamped(self):
        trait = PersonalityTrait("test", 1.5, -0.5)
        assert trait.value == 1.0
        assert trait.baseline == 0.0

    def test_evolve_applies_change(self):
        trait = PersonalityTrait("test", 0.5, 0.5)
        delta = trait.evolve(1.0)  # Push up
        assert trait.value > 0.5
        assert trait.sample_count == 1

    def test_evolve_respects_drift_limit(self):
        trait = PersonalityTrait("test", 0.5, 0.5)
        # Apply many large positive pushes
        for _ in range(1000):
            trait.evolve(1.0, weight=10.0)
        # Value should not exceed baseline + MAX_DRIFT
        assert trait.value <= trait.baseline + MAX_DRIFT_FROM_BASELINE + 1e-9
        assert trait.value >= 0.0
        assert trait.value <= 1.0

    def test_evolve_respects_lower_drift_limit(self):
        trait = PersonalityTrait("test", 0.5, 0.5)
        # Apply many large negative pushes
        for _ in range(1000):
            trait.evolve(-1.0, weight=10.0)
        assert trait.value >= trait.baseline - MAX_DRIFT_FROM_BASELINE - 1e-9
        assert trait.value >= 0.0

    def test_evolve_bounds_0_1(self):
        # Trait near 0 — can't go below 0
        trait = PersonalityTrait("test", 0.05, 0.05)
        for _ in range(100):
            trait.evolve(-1.0, weight=10.0)
        assert trait.value >= 0.0

        # Trait near 1 — can't go above 1
        trait2 = PersonalityTrait("test", 0.95, 0.95)
        for _ in range(100):
            trait2.evolve(1.0, weight=10.0)
        assert trait2.value <= 1.0

    def test_trait_serialization_roundtrip(self):
        trait = PersonalityTrait("risk", 0.7, 0.6, momentum=0.01, confidence=0.3, sample_count=15)
        data = trait.to_dict()
        restored = PersonalityTrait.from_dict(data)
        assert restored.name == trait.name
        assert restored.value == trait.value
        assert restored.baseline == trait.baseline
        assert restored.momentum == trait.momentum
        assert restored.sample_count == trait.sample_count

    def test_confidence_increases_with_samples(self):
        trait = PersonalityTrait("test", 0.5, 0.5)
        for _ in range(100):
            trait.evolve(0.1)
        assert trait.confidence > 0.0


class TestPersonalityProfile:
    """Tests for PersonalityProfile."""

    def test_profile_creation(self):
        profile = PersonalityProfile(agent_code="Forge")
        assert profile.agent_code == "Forge"
        assert profile.version == 0

    def test_get_all_traits(self):
        profile = PersonalityProfile(agent_code="Forge")
        traits = profile.get_all_traits()
        assert "risk_tolerance" in traits
        assert "creativity" in traits
        assert "thoroughness" in traits
        assert "assertiveness" in traits
        assert "collaboration" in traits
        assert "adaptability" in traits
        assert len(traits) == 6

    def test_get_all_traits_includes_domain(self):
        profile = PersonalityProfile(agent_code="Forge")
        profile.domain_traits["domain_expertise"] = PersonalityTrait("domain_expertise", 0.8, 0.8)
        traits = profile.get_all_traits()
        assert len(traits) == 7
        assert "domain_expertise" in traits

    def test_get_trait(self):
        profile = PersonalityProfile(agent_code="Forge")
        trait = profile.get_trait("risk_tolerance")
        assert trait is not None
        assert trait.name == "risk_tolerance"

    def test_get_trait_missing(self):
        profile = PersonalityProfile(agent_code="Forge")
        assert profile.get_trait("nonexistent") is None

    def test_to_system_prompt_fragment(self):
        profile = create_seeded_profile("Citadel")  # Very high thoroughness
        fragment = profile.to_system_prompt_fragment()
        assert "Citadel" in fragment
        assert "thorough" in fragment.lower()
        assert "analytical" in fragment.lower()

    def test_serialization_roundtrip(self):
        profile = create_seeded_profile("Forge")
        data = profile.to_dict()
        restored = PersonalityProfile.from_dict(data)
        assert restored.agent_code == "Forge"
        assert restored.decision_style == "analytical"
        assert restored.communication_style == "direct"
        assert abs(restored.risk_tolerance.value - 0.5) < 1e-9
        assert abs(restored.creativity.value - 0.7) < 1e-9

    def test_json_serialization_roundtrip(self):
        profile = create_seeded_profile("Echo")
        json_str = json.dumps(profile.to_dict(), default=str)
        data = json.loads(json_str)
        restored = PersonalityProfile.from_dict(data)
        assert restored.agent_code == "Echo"
        assert restored.decision_style == "intuitive"


class TestPersonalityEvolver:
    """Tests for PersonalityEvolver."""

    def test_evolver_creation(self):
        profile = create_seeded_profile("Forge")
        evolver = PersonalityEvolver(profile)
        assert evolver.profile.agent_code == "Forge"

    def test_process_outcome_needs_min_samples(self):
        profile = create_seeded_profile("Forge")
        evolver = PersonalityEvolver(profile)
        # With no samples, evolve should not produce evolutions
        evolutions = evolver.process_outcome(True, "test_task")
        assert len(evolutions) == 0

    def test_process_outcome_after_min_samples(self):
        profile = create_seeded_profile("Forge")
        evolver = PersonalityEvolver(profile)
        # Build up samples first
        for _ in range(MIN_SAMPLES_FOR_EVOLUTION + 1):
            evolver.process_outcome(True, "test_task")
        # Now we should get evolutions
        evolutions = evolver.process_outcome(False, "test_task")
        assert len(evolutions) > 0

    def test_process_reflection(self):
        profile = create_seeded_profile("Forge")
        evolver = PersonalityEvolver(profile)
        # Need min samples first
        for trait in profile.get_all_traits().values():
            trait.sample_count = MIN_SAMPLES_FOR_EVOLUTION + 1

        evolutions = evolver.process_reflection(
            {"risk_tolerance": -0.1, "thoroughness": 0.1},
            reason="test reflection",
        )
        assert len(evolutions) > 0
        assert profile.version > 0

    def test_evolution_increments_version(self):
        profile = create_seeded_profile("Forge")
        evolver = PersonalityEvolver(profile)
        for trait in profile.get_all_traits().values():
            trait.sample_count = MIN_SAMPLES_FOR_EVOLUTION + 1
        evolver.process_reflection({"risk_tolerance": 0.5})
        assert profile.version >= 1

    def test_get_stats(self):
        profile = create_seeded_profile("Forge")
        evolver = PersonalityEvolver(profile)
        stats = evolver.get_stats()
        assert stats["agent_code"] == "Forge"
        assert "traits" in stats


class TestPersonalitySeeds:
    """Tests for PERSONALITY_SEEDS."""

    def test_all_16_agents_have_seeds(self):
        expected = {
            "Overwatch",
            "Forge",
            "Keystone",
            "Echo",
            "Sentinel",
            "Blueprint",
            "Axiom",
            "Index",
            "Foundry",
            "Citadel",
            "Beacon",
            "Compass",
            "Vector",
            "Aegis",
            "Accord",
            "Nexus",
        }
        assert set(PERSONALITY_SEEDS.keys()) == expected

    def test_seed_values_in_range(self):
        for code, seeds in PERSONALITY_SEEDS.items():
            for key in [
                "risk",
                "creativity",
                "thoroughness",
                "assertiveness",
                "collaboration",
                "adaptability",
            ]:
                value = seeds[key]
                assert 0.0 <= value <= 1.0, f"{code}.{key} = {value} is out of range"

    def test_seed_decision_styles_valid(self):
        valid_styles = {"analytical", "intuitive", "balanced", "decisive"}
        for code, seeds in PERSONALITY_SEEDS.items():
            assert (
                seeds["decision"] in valid_styles
            ), f"{code} has invalid decision style: {seeds['decision']}"

    def test_seed_communication_styles_valid(self):
        valid_styles = {"formal", "direct", "collaborative", "neutral"}
        for code, seeds in PERSONALITY_SEEDS.items():
            assert (
                seeds["communication"] in valid_styles
            ), f"{code} has invalid communication style: {seeds['communication']}"

    def test_create_seeded_profile(self):
        for code in PERSONALITY_SEEDS:
            profile = create_seeded_profile(code)
            assert profile.agent_code == code
            seeds = PERSONALITY_SEEDS[code]
            assert abs(profile.risk_tolerance.value - seeds["risk"]) < 1e-9
            assert abs(profile.creativity.value - seeds["creativity"]) < 1e-9

    def test_create_seeded_profile_unknown_agent(self):
        profile = create_seeded_profile("UNKNOWN")
        assert profile.agent_code == "UNKNOWN"
        # Should get default neutral values
        assert abs(profile.risk_tolerance.value - 0.5) < 1e-9


class TestStabilityBounds:
    """Stability guarantee tests — traits must stay bounded after many random evolutions."""

    def test_1000_random_evolutions_stay_bounded(self):
        """Apply 1000 random evolutions and verify all traits stay within bounds."""
        random.seed(42)
        for code in PERSONALITY_SEEDS:
            profile = create_seeded_profile(code)
            evolver = PersonalityEvolver(profile)

            # Prime samples
            for trait in profile.get_all_traits().values():
                trait.sample_count = MIN_SAMPLES_FOR_EVOLUTION + 1

            for i in range(1000):
                signals = {
                    name: random.uniform(-1.0, 1.0)
                    for name in [
                        "risk_tolerance",
                        "creativity",
                        "thoroughness",
                        "assertiveness",
                        "collaboration",
                        "adaptability",
                    ]
                }
                evolver.process_reflection(signals, reason=f"random_{i}")

            # Verify bounds
            for name, trait in profile.get_all_traits().items():
                assert 0.0 <= trait.value <= 1.0, f"{code}.{name} = {trait.value} is out of [0, 1]"
                drift = abs(trait.value - trait.baseline)
                assert (
                    drift <= MAX_DRIFT_FROM_BASELINE + 1e-6
                ), f"{code}.{name} drift = {drift:.4f} exceeds MAX_DRIFT = {MAX_DRIFT_FROM_BASELINE}"

    def test_momentum_decay(self):
        """Verify momentum decays toward zero over time."""
        trait = PersonalityTrait("test", 0.5, 0.5)
        # Apply one large push
        trait.evolve(1.0, weight=10.0)
        initial_momentum = abs(trait.momentum)

        # Apply many zero-delta evolutions
        for _ in range(50):
            trait.evolve(0.0)

        # Momentum should have decayed
        assert abs(trait.momentum) < initial_momentum


class TestTraitEvolution:
    """Tests for TraitEvolution dataclass."""

    def test_creation(self):
        ev = TraitEvolution(
            agent_code="Forge",
            trait_name="risk_tolerance",
            old_value=0.5,
            new_value=0.48,
            delta=-0.02,
            reason="test",
        )
        assert ev.agent_code == "Forge"
        assert ev.delta == -0.02

    def test_to_dict(self):
        ev = TraitEvolution(agent_code="Forge", trait_name="risk")
        d = ev.to_dict()
        assert "agent_code" in d
        assert "trait_name" in d
        assert "timestamp" in d
