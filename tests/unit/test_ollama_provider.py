"""
Unit tests for Ollama LLM provider.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from ag3ntwerk.llm.ollama_provider import (
    OllamaProvider,
    _infer_model_tier,
    _infer_capabilities,
    _get_context_length,
)
from ag3ntwerk.llm.base import ModelTier, Message
from ag3ntwerk.core.exceptions import (
    LLMConnectionError,
    LLMModelNotFoundError,
    LLMResponseError,
)


class TestModelTierInference:
    """Test model tier inference from names."""

    def test_fast_models(self):
        assert _infer_model_tier("phi3:mini") == ModelTier.FAST
        assert _infer_model_tier("tinyllama") == ModelTier.FAST
        assert _infer_model_tier("gemma:2b") == ModelTier.FAST
        assert _infer_model_tier("qwen2.5:0.5b") == ModelTier.FAST
        assert _infer_model_tier("smollm") == ModelTier.FAST

    def test_balanced_models(self):
        assert _infer_model_tier("llama3.2") == ModelTier.BALANCED
        assert _infer_model_tier("mistral:7b") == ModelTier.BALANCED
        assert _infer_model_tier("gemma2:9b") == ModelTier.BALANCED
        assert _infer_model_tier("qwen2.5:7b") == ModelTier.BALANCED

    def test_powerful_models(self):
        assert _infer_model_tier("llama3.1:70b") == ModelTier.POWERFUL
        assert _infer_model_tier("mixtral:8x7b") == ModelTier.POWERFUL
        assert _infer_model_tier("qwen2.5:72b") == ModelTier.POWERFUL

    def test_specialized_models(self):
        assert _infer_model_tier("codellama") == ModelTier.SPECIALIZED
        assert _infer_model_tier("deepseek-coder") == ModelTier.SPECIALIZED
        assert _infer_model_tier("starcoder2") == ModelTier.SPECIALIZED
        assert _infer_model_tier("sqlcoder") == ModelTier.SPECIALIZED
        assert _infer_model_tier("nomic-embed-text") == ModelTier.SPECIALIZED

    def test_unknown_defaults_balanced(self):
        assert _infer_model_tier("unknown-model") == ModelTier.BALANCED

    def test_size_inference(self):
        # Size indicators should work
        assert _infer_model_tier("custom-70b") == ModelTier.POWERFUL
        assert _infer_model_tier("custom-0.5b") == ModelTier.FAST


class TestCapabilityInference:
    """Test capability inference from model names."""

    def test_chat_models(self):
        caps = _infer_capabilities("llama3.2")
        assert "chat" in caps
        assert "completion" in caps

    def test_code_models(self):
        caps = _infer_capabilities("codellama")
        assert "code" in caps
        assert "code-completion" in caps

    def test_embedding_models(self):
        caps = _infer_capabilities("nomic-embed-text")
        assert "embedding" in caps
        assert "chat" not in caps

    def test_sql_models(self):
        caps = _infer_capabilities("sqlcoder")
        assert "sql" in caps
        assert "database" in caps

    def test_vision_models(self):
        caps = _infer_capabilities("llava")
        assert "vision" in caps


class TestContextLengthInference:
    """Test context length inference."""

    def test_llama3_context(self):
        ctx = _get_context_length("llama3.2", {})
        assert ctx == 8192

    def test_mistral_context(self):
        ctx = _get_context_length("mistral", {})
        assert ctx == 8192

    def test_mixtral_context(self):
        ctx = _get_context_length("mixtral", {})
        assert ctx == 32768

    def test_default_context(self):
        ctx = _get_context_length("unknown", {})
        assert ctx == 4096

    def test_details_override(self):
        details = {"parameters": {"num_ctx": 16384}}
        ctx = _get_context_length("custom", details)
        assert ctx == 16384


class TestOllamaProviderInit:
    """Test OllamaProvider initialization."""

    def test_default_init(self):
        provider = OllamaProvider()
        assert provider.base_url == "http://localhost:11434"
        assert not provider.default_model  # Falsy (None or "")
        assert provider.timeout == 300.0
        assert not provider.is_connected

    def test_custom_init(self):
        provider = OllamaProvider(
            base_url="http://localhost:8080/",
            default_model="mistral",
            timeout=60.0,
        )
        assert provider.base_url == "http://localhost:8080"
        assert provider.default_model == "mistral"
        assert provider.timeout == 60.0


class TestOllamaProviderMocked:
    """Test OllamaProvider with mocked HTTP responses."""

    @pytest.fixture
    def provider(self):
        return OllamaProvider()

    @pytest.fixture
    def mock_models_response(self):
        return {
            "models": [
                {
                    "name": "llama3.2:3b",
                    "size": 2000000000,
                    "digest": "abc123",
                    "modified_at": "2024-01-01T00:00:00Z",
                    "details": {},
                },
                {
                    "name": "mistral:7b",
                    "size": 4000000000,
                    "digest": "def456",
                    "modified_at": "2024-01-01T00:00:00Z",
                    "details": {},
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_list_models_success(self, provider, mock_models_response):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_models_response)

        with patch.object(provider, "_session") as mock_session:
            mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            models = await provider.list_models()

            assert len(models) == 2
            assert models[0].name == "llama3.2:3b"
            assert models[1].name == "mistral:7b"

    @pytest.mark.asyncio
    async def test_list_models_failure(self, provider):
        mock_response = AsyncMock()
        mock_response.status = 500

        with patch.object(provider, "_session") as mock_session:
            mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            models = await provider.list_models()

            assert models == []

    @pytest.mark.asyncio
    async def test_generate_not_connected(self, provider):
        with pytest.raises(LLMConnectionError):
            await provider.generate("Hello")

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        provider._is_connected = True
        provider.default_model = "llama3.2"

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "message": {"content": "Hello! How can I help?"},
                "done_reason": "stop",
                "prompt_eval_count": 10,
                "eval_count": 15,
            }
        )

        with patch.object(provider, "_session") as mock_session:
            mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            response = await provider.generate("Hello")

            assert response.content == "Hello! How can I help?"
            assert response.model == "llama3.2"
            assert response.usage["prompt_tokens"] == 10
            assert response.usage["completion_tokens"] == 15

    @pytest.mark.asyncio
    async def test_chat_success(self, provider):
        provider._is_connected = True
        provider.default_model = "mistral"

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "message": {"content": "I'm doing well, thanks!"},
                "done_reason": "stop",
                "prompt_eval_count": 20,
                "eval_count": 10,
            }
        )

        with patch.object(provider, "_session") as mock_session:
            mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            messages = [
                Message(role="user", content="How are you?"),
            ]
            response = await provider.chat(messages)

            assert response.content == "I'm doing well, thanks!"

    @pytest.mark.asyncio
    async def test_generate_error_response(self, provider):
        provider._is_connected = True
        provider.default_model = "llama3.2"

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal server error")

        with patch.object(provider, "_session") as mock_session:
            mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            with pytest.raises(LLMResponseError) as exc_info:
                await provider.generate("Hello")

            assert exc_info.value.status_code == 500

    def test_get_model_for_task_code(self, provider):
        provider._available_models = [
            MagicMock(id="llama3.2", name="llama3.2"),
            MagicMock(id="deepseek-coder:6.7b", name="deepseek-coder:6.7b"),
        ]

        model = provider.get_model_for_task("code")
        assert model == "deepseek-coder:6.7b"

    def test_get_model_for_task_fast(self, provider):
        provider._available_models = [
            MagicMock(id="llama3.2", name="llama3.2"),
            MagicMock(id="phi3:mini", name="phi3:mini"),
        ]

        model = provider.get_model_for_task("fast")
        assert model == "phi3:mini"

    def test_get_model_for_task_fallback(self, provider):
        provider._available_models = [
            MagicMock(id="llama3.2", name="llama3.2"),
        ]
        provider.default_model = "llama3.2"

        model = provider.get_model_for_task("unknown_task")
        assert model == "llama3.2"


class TestOllamaProviderEmbed:
    """Test embedding functionality."""

    @pytest.mark.asyncio
    async def test_embed_not_connected(self):
        provider = OllamaProvider()
        with pytest.raises(LLMConnectionError):
            await provider.embed("Test text")

    @pytest.mark.asyncio
    async def test_embed_success(self):
        provider = OllamaProvider()
        provider._is_connected = True
        provider.default_model = "nomic-embed-text"
        provider._available_models = [
            MagicMock(id="nomic-embed-text", name="nomic-embed-text"),
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"embedding": [0.1, 0.2, 0.3, 0.4, 0.5]})

        with patch.object(provider, "_session") as mock_session:
            mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
            provider._session = mock_session

            embedding = await provider.embed("Test text", model="nomic-embed-text")

            assert len(embedding) == 5
            assert embedding[0] == 0.1


# =============================================================================
# Helper Classes
# =============================================================================


class AsyncContextManager:
    """Helper class to mock async context managers."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
