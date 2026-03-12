"""
OpenAI LLM Provider for ag3ntwerk.

Provides access to OpenAI's GPT models including:
- GPT-4o, GPT-4o-mini
- GPT-4 Turbo
- GPT-3.5 Turbo
- Text embedding models

Setup:
    Set environment variable: OPENAI_API_KEY=your-key
    Or pass api_key to constructor
"""

import asyncio
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


# Model configurations
OPENAI_MODELS = {
    # GPT-4o series
    "gpt-4o": ModelTier.POWERFUL,
    "gpt-4o-2024-11-20": ModelTier.POWERFUL,
    "gpt-4o-mini": ModelTier.BALANCED,
    "gpt-4o-mini-2024-07-18": ModelTier.BALANCED,
    # GPT-4 Turbo
    "gpt-4-turbo": ModelTier.POWERFUL,
    "gpt-4-turbo-preview": ModelTier.POWERFUL,
    "gpt-4-1106-preview": ModelTier.POWERFUL,
    # GPT-4
    "gpt-4": ModelTier.POWERFUL,
    "gpt-4-32k": ModelTier.POWERFUL,
    # GPT-3.5
    "gpt-3.5-turbo": ModelTier.FAST,
    "gpt-3.5-turbo-16k": ModelTier.FAST,
    # Embeddings
    "text-embedding-3-large": ModelTier.SPECIALIZED,
    "text-embedding-3-small": ModelTier.SPECIALIZED,
    "text-embedding-ada-002": ModelTier.SPECIALIZED,
}

MODEL_CONTEXT_LENGTHS = {
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4-turbo": 128000,
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-3.5-turbo": 16385,
    "gpt-3.5-turbo-16k": 16385,
}


class OpenAIProvider(BaseHTTPProvider):
    """
    OpenAI LLM provider.

    Provides access to GPT-4o, GPT-4, GPT-3.5 and embedding models.

    Example:
        async with OpenAIProvider() as provider:
            response = await provider.generate("Hello!")
            print(response.content)
    """

    TASK_MODEL_PREFERENCES = {
        "code": ["gpt-4o", "gpt-4-turbo", "gpt-4"],
        "analysis": ["gpt-4o", "gpt-4-turbo"],
        "chat": ["gpt-4o-mini", "gpt-3.5-turbo"],
        "fast": ["gpt-4o-mini", "gpt-3.5-turbo"],
        "embedding": ["text-embedding-3-small", "text-embedding-ada-002"],
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        default_model: str = "gpt-4o-mini",
        timeout: float = 60.0,
        organization: Optional[str] = None,
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            base_url: API base URL
            default_model: Default model to use
            timeout: Request timeout in seconds
            organization: Optional organization ID
        """
        super().__init__(
            "OpenAI",
            api_key=api_key,
            env_var="OPENAI_API_KEY",
            base_url=base_url,
            default_model=default_model,
            timeout=timeout,
        )
        self.organization = organization

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with optional organization."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        return headers

    async def list_models(self) -> List[ModelInfo]:
        """List available models."""
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

                    # Only include GPT and embedding models
                    if not any(x in model_id for x in ["gpt", "embedding"]):
                        continue

                    tier = OPENAI_MODELS.get(model_id, ModelTier.BALANCED)
                    context_length = MODEL_CONTEXT_LENGTHS.get(model_id, 4096)

                    capabilities = ["chat", "completion"]
                    if "embedding" in model_id:
                        capabilities = ["embedding"]

                    models.append(
                        ModelInfo(
                            id=model_id,
                            name=model_id,
                            tier=tier,
                            context_length=context_length,
                            capabilities=capabilities,
                            metadata=model_data,
                        )
                    )

                return models

        except aiohttp.ClientError as e:
            logger.error(f"Error listing OpenAI models: {e}")
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
            raise LLMConnectionError("OpenAI", self.base_url)

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
            raise LLMConnectionError("OpenAI", self.base_url, cause=e)

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
            raise LLMConnectionError("OpenAI", self.base_url)

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
            raise LLMConnectionError("OpenAI", self.base_url, cause=e)

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Generate embeddings."""
        if not self._is_connected:
            raise LLMConnectionError("OpenAI", self.base_url)

        model = model or "text-embedding-3-small"

        payload = {
            "model": model,
            "input": text,
        }

        try:
            async with self._session.post(
                f"{self.base_url}/embeddings",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text)

                data = await response.json()
                return data["data"][0]["embedding"]

        except aiohttp.ClientError as e:
            raise LLMConnectionError("OpenAI", self.base_url, cause=e)

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

        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.debug("OpenAI health check failed: %s", e)
            return False
