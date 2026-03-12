"""Tests for domain trait specialization (Phase 3, Step 3)."""

import pytest

from ag3ntwerk.core.personality import (
    PersonalityTrait,
    PersonalityProfile,
    PERSONALITY_SEEDS,
    DOMAIN_TRAIT_SEEDS,
    create_seeded_profile,
)


class TestDomainTraitSeeds:
    """Tests for DOMAIN_TRAIT_SEEDS configuration."""

    def test_domain_seeds_exist_for_five_executives(self):
        assert len(DOMAIN_TRAIT_SEEDS) == 5
        expected = {"Citadel", "Echo", "Keystone", "Forge", "Aegis"}
        assert set(DOMAIN_TRAIT_SEEDS.keys()) == expected

    def test_domain_seed_values_in_range(self):
        for code, traits in DOMAIN_TRAIT_SEEDS.items():
            for name, value in traits.items():
                assert 0.0 <= value <= 1.0, f"{code}.{name} = {value} out of range"

    def test_each_executive_has_three_domain_traits(self):
        for code, traits in DOMAIN_TRAIT_SEEDS.items():
            assert len(traits) == 3, f"{code} has {len(traits)} domain traits, expected 3"


class TestCreateSeededProfileWithDomainTraits:
    """Tests for create_seeded_profile() domain trait integration."""

    def test_cseco_gets_domain_traits(self):
        profile = create_seeded_profile("Citadel")
        assert "vigilance" in profile.domain_traits
        assert "zero_trust_mindset" in profile.domain_traits
        assert "compliance_rigor" in profile.domain_traits
        assert profile.domain_traits["vigilance"].value == 0.95

    def test_cmo_gets_domain_traits(self):
        profile = create_seeded_profile("Echo")
        assert "audience_empathy" in profile.domain_traits
        assert "trend_sensitivity" in profile.domain_traits
        assert "narrative_craft" in profile.domain_traits

    def test_cfo_gets_domain_traits(self):
        profile = create_seeded_profile("Keystone")
        assert "fiscal_conservatism" in profile.domain_traits
        assert profile.domain_traits["margin_sensitivity"].value == 0.9

    def test_agent_without_domain_seeds_has_empty_domain_traits(self):
        profile = create_seeded_profile("Overwatch")
        assert profile.domain_traits == {}

    def test_domain_trait_baseline_matches_value(self):
        profile = create_seeded_profile("Forge")
        for name, trait in profile.domain_traits.items():
            assert trait.value == trait.baseline, f"{name}: value != baseline"

    def test_domain_traits_included_in_get_all_traits(self):
        profile = create_seeded_profile("Citadel")
        all_traits = profile.get_all_traits()
        assert "vigilance" in all_traits
        assert "risk_tolerance" in all_traits  # core trait still present

    def test_domain_traits_affect_task_fit(self):
        profile = create_seeded_profile("Citadel")
        # Task requiring high vigilance should fit Citadel well
        fit = profile.compute_task_fit({"vigilance": 0.9, "thoroughness": 0.9})
        assert fit > 0.8

        # Task requiring low vigilance should fit poorly
        fit_low = profile.compute_task_fit({"vigilance": 0.1})
        assert fit_low < fit


class TestSystemPromptWithDomainTraits:
    """Tests for to_system_prompt_fragment() domain trait inclusion."""

    def test_prompt_includes_domain_expertise_section(self):
        profile = create_seeded_profile("Citadel")
        fragment = profile.to_system_prompt_fragment()
        assert "Domain expertise:" in fragment
        assert "Vigilance" in fragment

    def test_prompt_omits_domain_section_when_no_domain_traits(self):
        profile = create_seeded_profile("Overwatch")
        fragment = profile.to_system_prompt_fragment()
        assert "Domain expertise:" not in fragment

    def test_high_domain_trait_shows_high_label(self):
        profile = create_seeded_profile("Echo")
        fragment = profile.to_system_prompt_fragment()
        assert "High Audience Empathy" in fragment
        assert "High Narrative Craft" in fragment

    def test_low_domain_trait_shows_low_label(self):
        profile = create_seeded_profile("Citadel")
        # Manually set a domain trait low
        profile.domain_traits["test_low"] = PersonalityTrait(
            name="test_low",
            value=0.2,
            baseline=0.2,
        )
        fragment = profile.to_system_prompt_fragment()
        assert "Low Test Low" in fragment
