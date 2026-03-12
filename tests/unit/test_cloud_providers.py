"""
Unit tests for cloud LLM providers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from ag3ntwerk.llm import (
    get_provider,
    PROVIDERS,
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    OpenRouterProvider,
    HuggingFaceProvider,
    GitHubProvider,
    PerplexityProvider,
)
from ag3ntwerk.llm.base import ModelTier, Message
from ag3ntwerk.core.exceptions import (
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
)


class AsyncContextManager:
    """Helper class to mock async context managers."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# =============================================================================
# Provider Registry Tests
# =============================================================================


class TestProviderRegistry:
    """Test the provider registry and factory function."""

    def test_all_providers_registered(self):
        """Verify all providers are in registry."""
        expected = [
            "ollama",
            "gpt4all",  # Local
            "openai",
            "anthropic",
            "google",
            "gemini",  # Major cloud
            "openrouter",
            "huggingface",
            "hf",
            "github",
            "perplexity",  # Others
        ]
        for name in expected:
            assert name in PROVIDERS, f"Provider {name} not in registry"

    def test_get_provider_openai(self):
        """Test getting OpenAI provider."""
        provider = get_provider("openai", api_key="test-key")
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "test-key"

    def test_get_provider_anthropic(self):
        """Test getting Anthropic provider."""
        provider = get_provider("anthropic", api_key="test-key")
        assert isinstance(provider, AnthropicProvider)
        assert provider.api_key == "test-key"

    def test_get_provider_google(self):
        """Test getting Google provider."""
        provider = get_provider("google", api_key="test-key")
        assert isinstance(provider, GoogleProvider)

    def test_get_provider_gemini_alias(self):
        """Test gemini alias for Google provider."""
        provider = get_provider("gemini", api_key="test-key")
        assert isinstance(provider, GoogleProvider)

    def test_get_provider_openrouter(self):
        """Test getting OpenRouter provider."""
        provider = get_provider("openrouter", api_key="test-key")
        assert isinstance(provider, OpenRouterProvider)

    def test_get_provider_huggingface(self):
        """Test getting HuggingFace provider."""
        provider = get_provider("huggingface", api_key="test-key")
        assert isinstance(provider, HuggingFaceProvider)

    def test_get_provider_hf_alias(self):
        """Test hf alias for HuggingFace provider."""
        provider = get_provider("hf", api_key="test-key")
        assert isinstance(provider, HuggingFaceProvider)

    def test_get_provider_github(self):
        """Test getting GitHub provider."""
        provider = get_provider("github", api_key="test-key")
        assert isinstance(provider, GitHubProvider)

    def test_get_provider_perplexity(self):
        """Test getting Perplexity provider."""
        provider = get_provider("perplexity", api_key="test-key")
        assert isinstance(provider, PerplexityProvider)

    def test_get_provider_case_insensitive(self):
        """Test provider names are case insensitive."""
        provider1 = get_provider("OpenAI", api_key="test")
        provider2 = get_provider("OPENAI", api_key="test")
        provider3 = get_provider("openai", api_key="test")
        assert all(isinstance(p, OpenAIProvider) for p in [provider1, provider2, provider3])

    def test_get_provider_invalid(self):
        """Test invalid provider type."""
        with pytest.raises(ValueError) as exc_info:
            get_provider("invalid_provider")
        assert "Unknown provider type" in str(exc_info.value)


# =============================================================================
# OpenAI Provider Tests
# =============================================================================


class TestOpenAIProvider:
    """Test OpenAI provider."""

    @pytest.fixture
    def provider(self):
        return OpenAIProvider(api_key="test-key")

    def test_init_defaults(self):
        """Test default initialization."""
        provider = OpenAIProvider(api_key="test-key")
        assert provider.base_url == "https://api.openai.com/v1"
        assert provider.default_model == "gpt-4o-mini"
        assert provider.timeout == 60.0

    def test_init_custom(self):
        """Test custom initialization."""
        provider = OpenAIProvider(
            api_key="test-key",
            base_url="https://custom.api/",
            default_model="gpt-4o",
            timeout=120.0,
        )
        assert provider.base_url == "https://custom.api"
        assert provider.default_model == "gpt-4o"
        assert provider.timeout == 120.0

    @pytest.mark.asyncio
    async def test_generate_not_connected(self, provider):
        """Test generate fails when not connected."""
        with pytest.raises(LLMConnectionError):
            await provider.generate("Hello")

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        provider._is_connected = True

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "choices": [{"message": {"content": "Hello!"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            }
        )

        with patch.object(provider, "_session") as mock_session:
            mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            response = await provider.generate("Hi")

            assert response.content == "Hello!"
            assert response.usage["total_tokens"] == 8

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, provider):
        """Test rate limit handling."""
        provider._is_connected = True

        mock_response = AsyncMock()
        mock_response.status = 429

        with patch.object(provider, "_session") as mock_session:
            mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            with pytest.raises(LLMRateLimitError):
                await provider.generate("Hi")


# =============================================================================
# Anthropic Provider Tests
# =============================================================================


class TestAnthropicProvider:
    """Test Anthropic provider."""

    @pytest.fixture
    def provider(self):
        return AnthropicProvider(api_key="test-key")

    def test_init_defaults(self):
        """Test default initialization."""
        provider = AnthropicProvider(api_key="test-key")
        assert provider.base_url == "https://api.anthropic.com"
        assert provider.default_model == "claude-3-5-sonnet-latest"

    @pytest.mark.asyncio
    async def test_connect_success(self, provider):
        """Test successful connection."""
        provider._session = MagicMock()

        connected = await provider.connect()

        assert connected
        assert provider._is_connected
        assert len(provider._available_models) > 0

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        provider._is_connected = True

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "content": [{"type": "text", "text": "Hello from Claude!"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }
        )

        with patch.object(provider, "_session") as mock_session:
            mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            response = await provider.generate("Hi")

            assert response.content == "Hello from Claude!"
            assert response.usage["prompt_tokens"] == 10


# =============================================================================
# Google Provider Tests
# =============================================================================


class TestGoogleProvider:
    """Test Google Gemini provider."""

    @pytest.fixture
    def provider(self):
        return GoogleProvider(api_key="test-key")

    def test_init_defaults(self):
        """Test default initialization."""
        provider = GoogleProvider(api_key="test-key")
        assert "generativelanguage.googleapis.com" in provider.base_url
        assert provider.default_model == "gemini-1.5-flash"

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        provider._is_connected = True
        provider._session = MagicMock()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "Hello from Gemini!"}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 5,
                    "candidatesTokenCount": 4,
                    "totalTokenCount": 9,
                },
            }
        )

        with patch.object(provider, "_session") as mock_session:
            mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            response = await provider.generate("Hi")

            assert response.content == "Hello from Gemini!"


# =============================================================================
# OpenRouter Provider Tests
# =============================================================================


class TestOpenRouterProvider:
    """Test OpenRouter provider."""

    @pytest.fixture
    def provider(self):
        return OpenRouterProvider(api_key="test-key")

    def test_init_defaults(self):
        """Test default initialization."""
        provider = OpenRouterProvider(api_key="test-key")
        assert provider.base_url == "https://openrouter.ai/api/v1"
        assert provider.default_model == "openai/gpt-4o-mini"
        assert provider.app_name == "ag3ntwerk"

    @pytest.mark.asyncio
    async def test_list_models_success(self, provider):
        """Test listing models."""
        provider._session = MagicMock()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "data": [
                    {"id": "openai/gpt-4o", "name": "GPT-4o", "context_length": 128000},
                    {
                        "id": "anthropic/claude-3.5-sonnet",
                        "name": "Claude 3.5",
                        "context_length": 200000,
                    },
                ]
            }
        )

        with patch.object(provider, "_session") as mock_session:
            mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            models = await provider.list_models()

            assert len(models) == 2
            assert models[0].id == "openai/gpt-4o"


# =============================================================================
# HuggingFace Provider Tests
# =============================================================================


class TestHuggingFaceProvider:
    """Test HuggingFace provider."""

    @pytest.fixture
    def provider(self):
        return HuggingFaceProvider(api_key="test-key")

    def test_init_defaults(self):
        """Test default initialization."""
        provider = HuggingFaceProvider(api_key="test-key")
        assert "huggingface.co" in provider.base_url
        assert "Llama" in provider.default_model

    def test_known_models(self, provider):
        """Test known models list."""
        models = provider._get_known_models()
        assert len(models) > 0
        assert any("llama" in m.id.lower() for m in models)

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        provider._is_connected = True

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[{"generated_text": "Hello from HuggingFace!"}])

        with patch.object(provider, "_session") as mock_session:
            mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            response = await provider.generate("Hi")

            assert response.content == "Hello from HuggingFace!"


# =============================================================================
# GitHub Provider Tests
# =============================================================================


class TestGitHubProvider:
    """Test GitHub Models provider."""

    @pytest.fixture
    def provider(self):
        return GitHubProvider(api_key="test-key")

    def test_init_defaults(self):
        """Test default initialization."""
        provider = GitHubProvider(api_key="test-key")
        assert "azure.com" in provider.base_url
        assert provider.default_model == "gpt-4o-mini"

    def test_known_models(self, provider):
        """Test known models list."""
        models = provider._get_known_models()
        assert len(models) > 0
        assert any("gpt" in m.id.lower() for m in models)

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        provider._is_connected = True

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "choices": [
                    {"message": {"content": "Hello from GitHub!"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            }
        )

        with patch.object(provider, "_session") as mock_session:
            mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            response = await provider.generate("Hi")

            assert response.content == "Hello from GitHub!"


# =============================================================================
# Perplexity Provider Tests
# =============================================================================


class TestPerplexityProvider:
    """Test Perplexity provider."""

    @pytest.fixture
    def provider(self):
        return PerplexityProvider(api_key="test-key")

    def test_init_defaults(self):
        """Test default initialization."""
        provider = PerplexityProvider(api_key="test-key")
        assert provider.base_url == "https://api.perplexity.ai"
        assert provider.default_model == "sonar"

    def test_known_models(self, provider):
        """Test known models have web search capability."""
        models = provider._get_known_models()
        sonar_models = [m for m in models if "sonar" in m.id]
        assert all("web-search" in m.capabilities for m in sonar_models)

    @pytest.mark.asyncio
    async def test_generate_with_citations(self, provider):
        """Test generation with citations."""
        provider._is_connected = True

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "choices": [
                    {
                        "message": {"content": "Python is a programming language."},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
                "citations": ["https://python.org", "https://wikipedia.org/wiki/Python"],
            }
        )

        with patch.object(provider, "_session") as mock_session:
            mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            response = await provider.generate("What is Python?")

            assert "Python" in response.content
            assert "citations" in response.raw_response
            assert len(response.raw_response["citations"]) == 2

    @pytest.mark.asyncio
    async def test_search_method(self, provider):
        """Test search convenience method."""
        provider._is_connected = True

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "choices": [{"message": {"content": "Latest news..."}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
                "citations": ["https://news.com"],
                "images": [],
            }
        )

        with patch.object(provider, "_session") as mock_session:
            mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            result = await provider.search("Latest tech news")

            assert "content" in result
            assert "citations" in result
            assert "images" in result


# =============================================================================
# Model Tier Tests
# =============================================================================


class TestModelTiers:
    """Test model tier assignments."""

    def test_openai_tiers(self):
        """Test OpenAI model tiers."""
        from ag3ntwerk.llm.openai_provider import OPENAI_MODELS

        assert OPENAI_MODELS["gpt-4o"] == ModelTier.POWERFUL
        assert OPENAI_MODELS["gpt-4o-mini"] == ModelTier.BALANCED
        assert OPENAI_MODELS["gpt-3.5-turbo"] == ModelTier.FAST

    def test_anthropic_tiers(self):
        """Test Anthropic model tiers."""
        from ag3ntwerk.llm.anthropic_provider import ANTHROPIC_MODELS

        assert ANTHROPIC_MODELS["claude-3-opus-20240229"] == ModelTier.POWERFUL
        assert ANTHROPIC_MODELS["claude-3-5-sonnet-20241022"] == ModelTier.POWERFUL
        assert ANTHROPIC_MODELS["claude-3-haiku-20240307"] == ModelTier.FAST

    def test_google_tiers(self):
        """Test Google model tiers."""
        from ag3ntwerk.llm.google_provider import GEMINI_MODELS

        assert GEMINI_MODELS["gemini-1.5-pro"] == ModelTier.POWERFUL
        assert GEMINI_MODELS["gemini-1.5-flash"] == ModelTier.BALANCED
        assert GEMINI_MODELS["gemini-1.5-flash-8b"] == ModelTier.FAST


# =============================================================================
# Task-Based Model Selection Tests
# =============================================================================


class TestTaskBasedSelection:
    """Test task-based model selection."""

    def test_openai_task_selection(self):
        """Test OpenAI task-based selection."""
        provider = OpenAIProvider(api_key="test")
        provider._available_models = []  # Empty list, will fall back to default

        # Should return default model when no models available
        model = provider.get_model_for_task("code")
        assert model == provider.default_model

    def test_anthropic_task_selection(self):
        """Test Anthropic task-based selection."""
        provider = AnthropicProvider(api_key="test")
        provider._available_models = provider._get_known_models()

        model = provider.get_model_for_task("code")
        assert "sonnet" in model or "opus" in model

    def test_perplexity_task_selection(self):
        """Test Perplexity task-based selection."""
        provider = PerplexityProvider(api_key="test")
        provider._available_models = provider._get_known_models()

        # Search tasks should prefer sonar
        model = provider.get_model_for_task("search")
        assert "sonar" in model
