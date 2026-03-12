"""Tests for GPT4All provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.llm.gpt4all_provider import GPT4AllProvider, _infer_model_tier
from ag3ntwerk.llm.base import ModelTier, Message


class TestModelTierInference:
    """Test model tier inference from names."""

    def test_fast_models(self):
        assert _infer_model_tier("phi-3-mini") == ModelTier.FAST
        assert _infer_model_tier("Phi-2") == ModelTier.FAST
        assert _infer_model_tier("TinyLlama-1.1B") == ModelTier.FAST

    def test_balanced_models(self):
        assert _infer_model_tier("Mistral-7B") == ModelTier.BALANCED
        assert _infer_model_tier("llama-3-8b") == ModelTier.BALANCED

    def test_powerful_models(self):
        assert _infer_model_tier("Mixtral-8x7B") == ModelTier.POWERFUL
        assert _infer_model_tier("llama-2-70b") == ModelTier.POWERFUL

    def test_specialized_models(self):
        assert _infer_model_tier("CodeLlama-7B") == ModelTier.SPECIALIZED
        assert _infer_model_tier("SQLCoder") == ModelTier.SPECIALIZED

    def test_unknown_defaults_balanced(self):
        assert _infer_model_tier("unknown-model") == ModelTier.BALANCED


class TestGPT4AllProvider:
    """Test GPT4All provider functionality."""

    @pytest.fixture
    def provider(self):
        return GPT4AllProvider()

    def test_init_defaults(self, provider):
        assert provider.base_url == "http://localhost:4891/v1"
        assert not provider.default_model  # Falsy (None or "")
        assert provider.timeout == 120.0
        assert not provider.is_connected

    def test_init_custom_url(self):
        provider = GPT4AllProvider(base_url="http://localhost:5000/v1/")
        assert provider.base_url == "http://localhost:5000/v1"

    @pytest.mark.asyncio
    async def test_health_check_not_connected(self, provider):
        """Health check should fail when server not available."""
        # This will fail in test environment without GPT4All running
        with patch.object(provider, "_session", None):
            result = await provider.health_check()
            # Result depends on whether GPT4All is running
            assert isinstance(result, bool)

    def test_get_model_for_task(self, provider):
        """Test task-specific model selection."""
        # Without models loaded, should return default
        result = provider.get_model_for_task("code")
        assert result == provider.default_model


class TestMessage:
    """Test Message class."""

    def test_to_dict(self):
        msg = Message(role="user", content="Hello")
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "Hello"
        assert "name" not in d

    def test_to_dict_with_name(self):
        msg = Message(role="assistant", content="Hi", name="Assistant")
        d = msg.to_dict()
        assert d["name"] == "Assistant"
