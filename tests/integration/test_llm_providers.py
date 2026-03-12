"""
Integration tests for LLM providers.

These tests require actual LLM servers running:
- Ollama: http://localhost:11434
- GPT4All: http://localhost:4891

Skip these tests in CI by using: pytest -m "not integration"
"""

import pytest
from ag3ntwerk.llm import get_provider, auto_connect, OllamaProvider, GPT4AllProvider
from ag3ntwerk.llm.base import Message


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestOllamaIntegration:
    """Integration tests for Ollama provider."""

    @pytest.mark.asyncio
    async def test_connect_and_list_models(self):
        """Test connection and model listing."""
        provider = OllamaProvider()

        try:
            connected = await provider.connect()

            if connected:
                assert len(provider.available_models) > 0
                assert provider.default_model is not None
            else:
                pytest.skip("Ollama not available")

        finally:
            await provider.disconnect()

    @pytest.mark.asyncio
    async def test_generate_simple(self):
        """Test simple text generation."""
        async with OllamaProvider() as provider:
            if not provider.is_connected:
                pytest.skip("Ollama not available")

            response = await provider.generate(
                "What is 2 + 2? Answer with just the number.",
                max_tokens=10,
                temperature=0.1,
            )

            assert response.content is not None
            assert len(response.content) > 0
            assert "4" in response.content

    @pytest.mark.asyncio
    async def test_chat_completion(self):
        """Test chat completion."""
        async with OllamaProvider() as provider:
            if not provider.is_connected:
                pytest.skip("Ollama not available")

            messages = [
                Message(role="system", content="You are a helpful assistant."),
                Message(role="user", content="Say hello in one word."),
            ]

            response = await provider.chat(
                messages,
                max_tokens=20,
                temperature=0.1,
            )

            assert response.content is not None
            assert len(response.content) > 0

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        provider = OllamaProvider()

        try:
            healthy = await provider.health_check()
            # Result depends on whether Ollama is running
            assert isinstance(healthy, bool)
        finally:
            await provider.disconnect()


class TestGPT4AllIntegration:
    """Integration tests for GPT4All provider."""

    @pytest.mark.asyncio
    async def test_connect_and_list_models(self):
        """Test connection and model listing."""
        provider = GPT4AllProvider()

        try:
            connected = await provider.connect()

            if connected:
                assert len(provider.available_models) > 0
                assert provider.default_model is not None
            else:
                pytest.skip("GPT4All not available")

        finally:
            await provider.disconnect()

    @pytest.mark.asyncio
    async def test_generate_simple(self):
        """Test simple text generation."""
        async with GPT4AllProvider() as provider:
            if not provider.is_connected:
                pytest.skip("GPT4All not available")

            response = await provider.generate(
                "What is the capital of France? Answer in one word.",
                max_tokens=10,
                temperature=0.1,
            )

            assert response.content is not None
            assert len(response.content) > 0


class TestAutoConnect:
    """Test auto-connection functionality."""

    @pytest.mark.asyncio
    async def test_auto_connect(self):
        """Test auto-connect finds an available provider."""
        provider = await auto_connect()

        if provider is None:
            pytest.skip("No LLM provider available")

        try:
            assert provider.is_connected
            assert provider.name in ["Ollama", "GPT4All"]
        finally:
            await provider.disconnect()


class TestGetProvider:
    """Test get_provider factory function."""

    def test_get_ollama_provider(self):
        """Test getting Ollama provider."""
        provider = get_provider("ollama")
        assert isinstance(provider, OllamaProvider)

    def test_get_gpt4all_provider(self):
        """Test getting GPT4All provider."""
        provider = get_provider("gpt4all")
        assert isinstance(provider, GPT4AllProvider)

    def test_get_auto_provider(self):
        """Test getting auto provider (defaults to Ollama)."""
        provider = get_provider("auto")
        assert isinstance(provider, OllamaProvider)

    def test_get_invalid_provider(self):
        """Test invalid provider type."""
        with pytest.raises(ValueError):
            get_provider("invalid_provider")

    def test_get_provider_with_kwargs(self):
        """Test provider with custom arguments."""
        provider = get_provider(
            "ollama",
            base_url="http://custom:11434",
            timeout=120.0,
        )
        assert provider.base_url == "http://custom:11434"
        assert provider.timeout == 120.0
