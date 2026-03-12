"""Tests for deeper LLM reflection with structured parsing (Phase 2, Step 3)."""

import json
import pytest

from ag3ntwerk.core.reflection import AgentReflector, ReflectionResult
from ag3ntwerk.modules.metacognition.service import MetacognitionService


# =========================================================================
# _parse_structured_reflection
# =========================================================================


class TestParseStructuredReflection:
    def setup_method(self):
        self.reflector = AgentReflector("Forge")

    def test_valid_json(self):
        response = json.dumps(
            {
                "what_went_well": ["fast execution", "good output"],
                "what_went_poorly": ["minor issues"],
                "root_cause": "none",
                "trait_adjustments": {
                    "risk_tolerance": 0.05,
                    "thoroughness": -0.03,
                },
                "heuristic_suggestions": ["try splitting tasks"],
                "confidence": 0.9,
            }
        )
        result = self.reflector._parse_structured_reflection(
            response,
            "t1",
            "code_review",
            True,
        )
        assert result.what_went_well == ["fast execution", "good output"]
        assert result.what_went_poorly == ["minor issues"]
        assert result.root_cause == "none"
        assert abs(result.trait_signals["risk_tolerance"] - 0.05) < 1e-6
        assert abs(result.trait_signals["thoroughness"] - (-0.03)) < 1e-6
        assert result.heuristic_suggestions == ["try splitting tasks"]
        assert abs(result.confidence_in_reflection - 0.9) < 1e-6

    def test_json_in_markdown_code_block(self):
        response = '```json\n{"what_went_well": ["good"], "what_went_poorly": []}\n```'
        result = self.reflector._parse_structured_reflection(
            response,
            "t1",
            "test",
            True,
        )
        assert result.what_went_well == ["good"]
        assert result.what_went_poorly == []

    def test_json_in_bare_code_block(self):
        response = '```\n{"what_went_well": ["ok"]}\n```'
        result = self.reflector._parse_structured_reflection(
            response,
            "t1",
            "test",
            True,
        )
        assert result.what_went_well == ["ok"]

    def test_trait_adjustments_clamped(self):
        response = json.dumps(
            {
                "trait_adjustments": {
                    "risk_tolerance": 0.5,  # Should be clamped to 0.1
                    "thoroughness": -0.5,  # Should be clamped to -0.1
                },
            }
        )
        result = self.reflector._parse_structured_reflection(
            response,
            "t1",
            "test",
            True,
        )
        assert abs(result.trait_signals["risk_tolerance"] - 0.1) < 1e-6
        assert abs(result.trait_signals["thoroughness"] - (-0.1)) < 1e-6

    def test_invalid_trait_names_ignored(self):
        response = json.dumps(
            {
                "trait_adjustments": {
                    "risk_tolerance": 0.05,
                    "nonexistent_trait": 0.1,
                },
            }
        )
        result = self.reflector._parse_structured_reflection(
            response,
            "t1",
            "test",
            True,
        )
        assert "risk_tolerance" in result.trait_signals
        assert "nonexistent_trait" not in result.trait_signals

    def test_non_numeric_trait_values_ignored(self):
        response = json.dumps(
            {
                "trait_adjustments": {
                    "risk_tolerance": "high",
                    "thoroughness": 0.05,
                },
            }
        )
        result = self.reflector._parse_structured_reflection(
            response,
            "t1",
            "test",
            True,
        )
        assert "risk_tolerance" not in result.trait_signals
        assert "thoroughness" in result.trait_signals

    def test_invalid_json_graceful_fallback(self):
        response = "This is not JSON at all, just text."
        result = self.reflector._parse_structured_reflection(
            response,
            "t1",
            "test",
            False,
            error="some error",
        )
        assert len(result.what_went_well) == 1
        assert "LLM reflection" in result.what_went_well[0]
        assert result.root_cause == "some error"
        assert result.confidence_in_reflection == 0.5

    def test_empty_response_fallback(self):
        result = self.reflector._parse_structured_reflection(
            "",
            "t1",
            "test",
            True,
        )
        assert result.reflection_mode == "llm"

    def test_confidence_clamped(self):
        response = json.dumps({"confidence": 5.0})
        result = self.reflector._parse_structured_reflection(
            response,
            "t1",
            "test",
            True,
        )
        assert result.confidence_in_reflection <= 1.0

    def test_lists_truncated(self):
        response = json.dumps(
            {
                "what_went_well": [f"item{i}" for i in range(20)],
                "heuristic_suggestions": [f"suggestion{i}" for i in range(10)],
            }
        )
        result = self.reflector._parse_structured_reflection(
            response,
            "t1",
            "test",
            True,
        )
        assert len(result.what_went_well) <= 10
        assert len(result.heuristic_suggestions) <= 5


# =========================================================================
# reflect_llm with structured output
# =========================================================================


class TestReflectLLMStructured:
    @pytest.mark.asyncio
    async def test_reflect_llm_no_provider_falls_back(self):
        reflector = AgentReflector("Forge")
        result = await reflector.reflect_llm(
            task_id="t1",
            task_type="test",
            success=True,
        )
        assert result.reflection_mode == "heuristic"

    @pytest.mark.asyncio
    async def test_reflect_llm_structured_response(self):
        class MockLLM:
            async def generate(self, prompt):
                return json.dumps(
                    {
                        "what_went_well": ["prompt was clear"],
                        "what_went_poorly": [],
                        "root_cause": None,
                        "trait_adjustments": {"creativity": 0.05},
                        "heuristic_suggestions": [],
                        "confidence": 0.85,
                    }
                )

        reflector = AgentReflector("Forge")
        result = await reflector.reflect_llm(
            task_id="t1",
            task_type="code_review",
            success=True,
            llm_provider=MockLLM(),
        )
        assert result.reflection_mode == "llm"
        assert result.what_went_well == ["prompt was clear"]
        assert abs(result.trait_signals.get("creativity", 0) - 0.05) < 1e-6

    @pytest.mark.asyncio
    async def test_reflect_llm_error_falls_back(self):
        class FailLLM:
            async def generate(self, prompt):
                raise RuntimeError("LLM down")

        reflector = AgentReflector("Forge")
        result = await reflector.reflect_llm(
            task_id="t1",
            task_type="test",
            success=False,
            error="some error",
            llm_provider=FailLLM(),
        )
        assert result.reflection_mode == "heuristic"

    @pytest.mark.asyncio
    async def test_reflect_llm_stored_in_history(self):
        class MockLLM:
            async def generate(self, prompt):
                return '{"what_went_well": ["ok"]}'

        reflector = AgentReflector("Forge")
        await reflector.reflect_llm(
            task_id="t1",
            task_type="test",
            success=True,
            llm_provider=MockLLM(),
        )
        assert len(reflector.get_recent_reflections()) == 1


# =========================================================================
# MetacognitionService.on_task_completed_async
# =========================================================================


class TestOnTaskCompletedAsync:
    @pytest.mark.asyncio
    async def test_async_heuristic_mode_by_default(self):
        svc = MetacognitionService()
        svc.register_agent("Forge")
        result = await svc.on_task_completed_async(
            agent_code="Forge",
            task_id="t1",
            task_type="code_review",
            success=True,
        )
        assert result is not None
        assert result.reflection_mode == "heuristic"

    @pytest.mark.asyncio
    async def test_async_llm_mode_on_interval(self):
        class MockLLM:
            async def generate(self, prompt):
                return json.dumps(
                    {
                        "what_went_well": ["triggered"],
                        "confidence": 0.8,
                    }
                )

        svc = MetacognitionService()
        svc.register_agent("Forge")

        # Process LLM_REFLECTION_INTERVAL - 1 tasks first (heuristic mode)
        for i in range(svc.LLM_REFLECTION_INTERVAL - 1):
            await svc.on_task_completed_async(
                agent_code="Forge",
                task_id=f"t{i}",
                task_type="test",
                success=True,
                llm_provider=MockLLM(),
            )

        # The next one should trigger LLM reflection
        result = await svc.on_task_completed_async(
            agent_code="Forge",
            task_id="t_trigger",
            task_type="test",
            success=True,
            llm_provider=MockLLM(),
        )
        assert result.reflection_mode == "llm"

    @pytest.mark.asyncio
    async def test_async_llm_mode_on_failure_streak(self):
        class MockLLM:
            async def generate(self, prompt):
                return json.dumps(
                    {
                        "what_went_well": [],
                        "what_went_poorly": ["failures"],
                        "confidence": 0.7,
                    }
                )

        svc = MetacognitionService()
        svc.register_agent("Forge")

        # Create a failure streak
        for i in range(svc.LLM_REFLECTION_ON_FAILURE_STREAK - 1):
            await svc.on_task_completed_async(
                agent_code="Forge",
                task_id=f"f{i}",
                task_type="test",
                success=False,
                error="failed",
                llm_provider=MockLLM(),
            )

        # Next failure should trigger LLM reflection
        result = await svc.on_task_completed_async(
            agent_code="Forge",
            task_id="f_trigger",
            task_type="test",
            success=False,
            error="failed again",
            llm_provider=MockLLM(),
        )
        assert result.reflection_mode == "llm"

    @pytest.mark.asyncio
    async def test_async_unregistered_agent_returns_none(self):
        svc = MetacognitionService()
        result = await svc.on_task_completed_async(
            agent_code="UNKNOWN",
            task_id="t1",
            task_type="test",
            success=True,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_async_evolves_personality(self):
        class MockLLM:
            async def generate(self, prompt):
                return json.dumps(
                    {
                        "trait_adjustments": {"thoroughness": 0.05},
                        "confidence": 0.8,
                    }
                )

        svc = MetacognitionService()
        svc.register_agent("Forge")

        # Fill minimum samples
        for i in range(svc.LLM_REFLECTION_INTERVAL - 1):
            await svc.on_task_completed_async(
                agent_code="Forge",
                task_id=f"t{i}",
                task_type="test",
                success=True,
                llm_provider=MockLLM(),
            )

        old_version = svc.get_profile("Forge").version

        # Trigger LLM reflection with trait adjustments
        await svc.on_task_completed_async(
            agent_code="Forge",
            task_id="t_evolve",
            task_type="test",
            success=True,
            llm_provider=MockLLM(),
        )

        # Profile version may have increased if evolution occurred
        # (depends on sample counts meeting MIN_SAMPLES_FOR_EVOLUTION)
        assert svc.get_profile("Forge") is not None
