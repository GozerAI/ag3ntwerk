"""
OpenRouter LLM Provider for ag3ntwerk.

OpenRouter provides unified access to 100+ models from:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini, PaLM)
- Meta (Llama)
- Mistral
- And many more

Setup:
    Set environment variable: OPENROUTER_API_KEY=your-key
    Or pass api_key to constructor

Benefits:
- Single API for multiple providers
- Automatic fallback between providers
- Cost-optimized routing
- No need for multiple API keys
"""

import logging
import time
from typing import Any, Dict, List, Optional

import aiohttp

from ag3ntwerk.llm.base import (
    BaseHTTPProvider,
    LLMResponse,
    Message,
    ModelInfo,
    ModelTier,
)
from ag3ntwerk.core.exceptions import LLMConnectionError

logger = logging.getLogger(__name__)


# Popular OpenRouter models with tier mappings
OPENROUTER_MODEL_TIERS = {
    # Top tier models
    "openai/gpt-4o": ModelTier.POWERFUL,
    "openai/gpt-4-turbo": ModelTier.POWERFUL,
    "anthropic/claude-3.5-sonnet": ModelTier.POWERFUL,
    "anthropic/claude-3-opus": ModelTier.POWERFUL,
    "google/gemini-pro-1.5": ModelTier.POWERFUL,
    "meta-llama/llama-3.1-405b-instruct": ModelTier.POWERFUL,
    # Balanced models
    "openai/gpt-4o-mini": ModelTier.BALANCED,
    "anthropic/claude-3.5-haiku": ModelTier.BALANCED,
    "anthropic/claude-3-sonnet": ModelTier.BALANCED,
    "google/gemini-flash-1.5": ModelTier.BALANCED,
    "meta-llama/llama-3.1-70b-instruct": ModelTier.BALANCED,
    "mistralai/mistral-large": ModelTier.BALANCED,
    "mistralai/mixtral-8x22b-instruct": ModelTier.BALANCED,
    # Fast/cheap models
    "openai/gpt-3.5-turbo": ModelTier.FAST,
    "anthropic/claude-3-haiku": ModelTier.FAST,
    "meta-llama/llama-3.1-8b-instruct": ModelTier.FAST,
    "mistralai/mistral-7b-instruct": ModelTier.FAST,
    "google/gemma-2-9b-it": ModelTier.FAST,
    # Code models
    "deepseek/deepseek-coder": ModelTier.SPECIALIZED,
    "codellama/codellama-70b-instruct": ModelTier.SPECIALIZED,
    "phind/phind-codellama-34b": ModelTier.SPECIALIZED,
}


def _infer_tier(model_id: str) -> ModelTier:
    """Infer model tier from model ID."""
    if model_id in OPENROUTER_MODEL_TIERS:
        return OPENROUTER_MODEL_TIERS[model_id]

    model_lower = model_id.lower()

    # Size-based inference
    if any(x in model_lower for x in ["405b", "70b", "opus", "gpt-4o", "gpt-4-turbo"]):
        return ModelTier.POWERFUL
    if any(x in model_lower for x in ["8b", "7b", "mini", "haiku", "flash", "3.5-turbo"]):
        return ModelTier.FAST
    if any(x in model_lower for x in ["code", "coder"]):
        return ModelTier.SPECIALIZED

    return ModelTier.BALANCED


class OpenRouterProvider(BaseHTTPProvider):
    """
    OpenRouter LLM provider.

    Provides unified access to 100+ models from multiple providers.

    Example:
        async with OpenRouterProvider() as provider:
            response = await provider.generate("Hello!")
            print(response.content)
    """

    TASK_MODEL_PREFERENCES = {
        "code": [
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "deepseek/deepseek-coder",
        ],
        "analysis": [
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "google/gemini-pro-1.5",
        ],
        "chat": [
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-haiku",
            "meta-llama/llama-3.1-8b-instruct",
        ],
        "fast": [
            "openai/gpt-3.5-turbo",
            "anthropic/claude-3-haiku",
            "mistralai/mistral-7b-instruct",
        ],
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        default_model: str = "openai/gpt-4o-mini",
        timeout: float = 120.0,
        site_url: Optional[str] = None,
        app_name: str = "ag3ntwerk",
    ):
        """
        Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key (or set OPENROUTER_API_KEY env var)
            base_url: API base URL
            default_model: Default model to use
            timeout: Request timeout in seconds
            site_url: Your site URL (for rankings)
            app_name: Your app name (for rankings)
        """
        super().__init__(
            "OpenRouter",
            api_key=api_key,
            env_var="OPENROUTER_API_KEY",
            base_url=base_url,
            default_model=default_model,
            timeout=timeout,
        )
        self.site_url = site_url
        self.app_name = app_name

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with OpenRouter-specific fields."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url or "https://github.com/ag3ntwerk",
            "X-Title": self.app_name,
        }

    async def list_models(self) -> List[ModelInfo]:
        """List available models from OpenRouter."""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30.0),
                headers=self._get_headers(),
            )

        try:
            async with self._session.get(f"{self.base_url}/models") as response:
                if response.status != 200:
                    return []

                data = await response.json()
                models = []

                for model_data in data.get("data", []):
                    model_id = model_data.get("id", "")
                    context_length = model_data.get("context_length", 4096)

                    models.append(
                        ModelInfo(
                            id=model_id,
                            name=model_data.get("name", model_id),
                            tier=_infer_tier(model_id),
                            context_length=context_length,
                            capabilities=["chat", "completion"],
                            metadata={
                                "pricing": model_data.get("pricing", {}),
                                "top_provider": model_data.get("top_provider", {}),
                            },
                        )
                    )

                return models

        except aiohttp.ClientError as e:
            logger.error(f"Error listing OpenRouter models: {e}")
            return []

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate text completion."""
        if not self._is_connected:
            raise LLMConnectionError("OpenRouter", self.base_url)

        model = model or self.default_model

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        start_time = time.time()

        try:
            async with self._session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status != 200:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text)

                data = await response.json()
                return self._parse_openai_response(data, model, latency_ms)

        except aiohttp.ClientError as e:
            raise LLMConnectionError("OpenRouter", self.base_url, cause=e)

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """Generate chat completion."""
        if not self._is_connected:
            raise LLMConnectionError("OpenRouter", self.base_url)

        model = model or self.default_model

        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        start_time = time.time()

        try:
            async with self._session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status != 200:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text)

                data = await response.json()
                return self._parse_openai_response(data, model, latency_ms)

        except aiohttp.ClientError as e:
            raise LLMConnectionError("OpenRouter", self.base_url, cause=e)

    async def health_check(self) -> bool:
        """Check API health."""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10.0),
                    headers=self._get_headers(),
                )

            async with self._session.get(f"{self.base_url}/models") as response:
                return response.status == 200

        except Exception as e:
            logger.debug(f"OpenRouter health check failed: {e}")
            return False
