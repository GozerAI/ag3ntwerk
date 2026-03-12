"""
Anthropic LLM Provider for ag3ntwerk.

Provides access to Anthropic's Claude models:
- Claude 3.5 Sonnet
- Claude 3.5 Haiku
- Claude 3 Opus
- Claude 3 Sonnet
- Claude 3 Haiku

Setup:
    Set environment variable: ANTHROPIC_API_KEY=your-key
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


# Claude model configurations
ANTHROPIC_MODELS = {
    # Claude 3.5 series
    "claude-3-5-sonnet-20241022": ModelTier.POWERFUL,
    "claude-3-5-sonnet-latest": ModelTier.POWERFUL,
    "claude-3-5-haiku-20241022": ModelTier.BALANCED,
    "claude-3-5-haiku-latest": ModelTier.BALANCED,
    # Claude 3 series
    "claude-3-opus-20240229": ModelTier.POWERFUL,
    "claude-3-opus-latest": ModelTier.POWERFUL,
    "claude-3-sonnet-20240229": ModelTier.BALANCED,
    "claude-3-haiku-20240307": ModelTier.FAST,
    # Legacy
    "claude-2.1": ModelTier.BALANCED,
    "claude-2.0": ModelTier.BALANCED,
    "claude-instant-1.2": ModelTier.FAST,
}

MODEL_CONTEXT_LENGTHS = {
    "claude-3-5-sonnet-20241022": 200000,
    "claude-3-5-haiku-20241022": 200000,
    "claude-3-opus-20240229": 200000,
    "claude-3-sonnet-20240229": 200000,
    "claude-3-haiku-20240307": 200000,
    "claude-2.1": 200000,
    "claude-2.0": 100000,
    "claude-instant-1.2": 100000,
}


class AnthropicProvider(BaseHTTPProvider):
    """
    Anthropic Claude LLM provider.

    Provides access to Claude 3.5, Claude 3, and legacy Claude models.

    Example:
        async with AnthropicProvider() as provider:
            response = await provider.generate("Hello!")
            print(response.content)
    """

    TASK_MODEL_PREFERENCES = {
        "code": ["claude-3-5-sonnet-latest", "claude-3-opus-latest"],
        "analysis": ["claude-3-5-sonnet-latest", "claude-3-opus-latest"],
        "chat": ["claude-3-5-haiku-latest", "claude-3-haiku-20240307"],
        "fast": ["claude-3-5-haiku-latest", "claude-3-haiku-20240307"],
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com",
        default_model: str = "claude-3-5-sonnet-latest",
        timeout: float = 120.0,
        api_version: str = "2023-06-01",
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            base_url: API base URL
            default_model: Default model to use
            timeout: Request timeout in seconds
            api_version: Anthropic API version
        """
        super().__init__(
            "Anthropic",
            api_key=api_key,
            env_var="ANTHROPIC_API_KEY",
            base_url=base_url,
            default_model=default_model,
            timeout=timeout,
        )
        self.api_version = api_version

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with x-api-key auth (not Bearer)."""
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "Content-Type": "application/json",
        }

    async def connect(self) -> bool:
        """Connect using known models (no models endpoint)."""
        if not self.api_key:
            logger.error("Anthropic API key not provided")
            return False

        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self._get_headers(),
            )

            # Populate with known models
            self._available_models = self._get_known_models()
            self._is_connected = True
            logger.info(f"Connected to Anthropic with {len(self._available_models)} models")
            return True

        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.error("Failed to connect to Anthropic: %s", e, exc_info=True)
            if self._session:
                await self._session.close()
                self._session = None
            return False

    def _get_known_models(self) -> List[ModelInfo]:
        """Get known Anthropic models."""
        models = []
        for model_id, tier in ANTHROPIC_MODELS.items():
            context_length = MODEL_CONTEXT_LENGTHS.get(model_id, 200000)
            models.append(
                ModelInfo(
                    id=model_id,
                    name=model_id,
                    tier=tier,
                    context_length=context_length,
                    capabilities=["chat", "completion", "analysis"],
                    metadata={"provider": "anthropic"},
                )
            )
        return models

    async def list_models(self) -> List[ModelInfo]:
        """List available models."""
        return self._get_known_models()

    def _parse_anthropic_response(
        self,
        data: Dict[str, Any],
        model: str,
        latency_ms: float,
    ) -> LLMResponse:
        """Parse Anthropic's content blocks response format."""
        content_blocks = data.get("content", [])
        content = ""
        for block in content_blocks:
            if block.get("type") == "text":
                content += block.get("text", "")

        usage = data.get("usage", {})

        return LLMResponse(
            content=content.strip(),
            model=model,
            finish_reason=data.get("stop_reason"),
            usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            },
            latency_ms=latency_ms,
            raw_response=data,
        )

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
            raise LLMConnectionError("Anthropic", self.base_url)

        model = model or self.default_model

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            payload["system"] = system_prompt

        start_time = time.time()

        try:
            async with self._session.post(
                f"{self.base_url}/v1/messages",
                json=payload,
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status != 200:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text)

                data = await response.json()
                return self._parse_anthropic_response(data, model, latency_ms)

        except aiohttp.ClientError as e:
            raise LLMConnectionError("Anthropic", self.base_url, cause=e)

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
            raise LLMConnectionError("Anthropic", self.base_url)

        model = model or self.default_model

        # Convert messages to Anthropic format
        anthropic_messages = []
        system_prompt = None

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                anthropic_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anthropic_messages,
        }

        if system_prompt:
            payload["system"] = system_prompt

        start_time = time.time()

        try:
            async with self._session.post(
                f"{self.base_url}/v1/messages",
                json=payload,
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status != 200:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text)

                data = await response.json()
                return self._parse_anthropic_response(data, model, latency_ms)

        except aiohttp.ClientError as e:
            raise LLMConnectionError("Anthropic", self.base_url, cause=e)
