"""
GPT4All LLM Provider for ag3ntwerk.

This module provides integration with GPT4All's local API server,
enabling private, local LLM inference for all ag3ntwerk agents.

GPT4All API Server:
- Default URL: http://localhost:4891/v1
- OpenAI-compatible API
- Enable in GPT4All Desktop: Settings > Application > Advanced > Enable Local API Server
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

logger = logging.getLogger(__name__)


# Default model tier mappings based on common GPT4All models
MODEL_TIER_MAPPINGS = {
    # Fast/Small models
    "phi": ModelTier.FAST,
    "phi-2": ModelTier.FAST,
    "phi-3-mini": ModelTier.FAST,
    "tinyllama": ModelTier.FAST,
    "orca-mini": ModelTier.FAST,
    # Balanced models
    "mistral": ModelTier.BALANCED,
    "llama-2-7b": ModelTier.BALANCED,
    "llama-3": ModelTier.BALANCED,
    "nous-hermes": ModelTier.BALANCED,
    "wizardlm": ModelTier.BALANCED,
    # Powerful models
    "llama-2-13b": ModelTier.POWERFUL,
    "llama-2-70b": ModelTier.POWERFUL,
    "mixtral": ModelTier.POWERFUL,
    "falcon": ModelTier.POWERFUL,
    # Specialized models
    "codellama": ModelTier.SPECIALIZED,
    "starcoder": ModelTier.SPECIALIZED,
    "sqlcoder": ModelTier.SPECIALIZED,
}


def _infer_model_tier(model_name: str) -> ModelTier:
    """Infer model tier from model name."""
    name_lower = model_name.lower()
    for key, tier in MODEL_TIER_MAPPINGS.items():
        if key in name_lower:
            return tier
    return ModelTier.BALANCED


class GPT4AllProvider(BaseHTTPProvider):
    """
    LLM Provider for GPT4All local API server.

    GPT4All provides a local, private LLM inference server with an
    OpenAI-compatible API. This provider connects to the local server
    and routes requests to the appropriate models.

    Usage:
        provider = GPT4AllProvider()
        await provider.connect()

        response = await provider.generate("Hello, world!")
        print(response.content)

    Configuration:
        - Ensure GPT4All Desktop is running
        - Enable API server in Settings > Application > Advanced
        - Default port is 4891
    """

    TASK_MODEL_PREFERENCES = {
        "code": ["codellama", "starcoder", "wizardcoder"],
        "sql": ["sqlcoder", "codellama"],
        "analysis": ["mixtral", "llama-2-13b", "mistral"],
        "chat": ["nous-hermes", "mistral", "llama-3"],
        "fast": ["phi-3-mini", "phi-2", "tinyllama"],
    }

    def __init__(
        self,
        base_url: str = "http://localhost:4891/v1",
        default_model: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize GPT4All provider.

        Args:
            base_url: Base URL for the GPT4All API server
            default_model: Default model to use (or first available)
            timeout: Request timeout in seconds
        """
        super().__init__(
            "GPT4All",
            api_key=None,
            env_var=None,
            base_url=base_url,
            default_model=default_model or "",
            timeout=timeout,
        )

    def _get_headers(self) -> Dict[str, str]:
        """No auth headers needed for local server."""
        return {"Content-Type": "application/json"}

    async def connect(self) -> bool:
        """Connect to the GPT4All API server."""
        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self._get_headers(),
            )

            models = await self.list_models()

            if models:
                self._is_connected = True
                self._available_models = models

                # Set default model if not specified
                if not self.default_model and models:
                    self.default_model = models[0].id

                logger.info(f"Connected to GPT4All with {len(models)} models")
                return True
            else:
                await self.disconnect()
                return False

        except Exception as e:
            logger.error(f"Failed to connect to GPT4All: {e}")
            if self._session:
                await self._session.close()
                self._session = None
            return False

    async def list_models(self) -> List[ModelInfo]:
        """Fetch available models from GPT4All server."""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
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
                    model_name = model_data.get("name", model_id)

                    models.append(
                        ModelInfo(
                            id=model_id,
                            name=model_name,
                            tier=_infer_model_tier(model_name),
                            context_length=model_data.get("context_length", 4096),
                            capabilities=["text-generation", "chat"],
                            metadata=model_data,
                        )
                    )

                return models

        except aiohttp.ClientError as e:
            logger.error(f"Error listing models: {e}")
            return []

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a text completion.

        Uses the /v1/completions endpoint.
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to GPT4All server")

        model = model or self.default_model
        if not model:
            raise ValueError("No model specified and no default model available")

        payload = {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        start_time = time.time()

        try:
            async with self._session.post(
                f"{self.base_url}/completions",
                json=payload,
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"GPT4All API error: {error_text}")

                data = await response.json()

                # Extract response content (completions format uses "text" not "message")
                choices = data.get("choices", [])
                content = choices[0].get("text", "") if choices else ""
                finish_reason = choices[0].get("finish_reason") if choices else None

                usage = data.get("usage", {})

                return LLMResponse(
                    content=content.strip(),
                    model=model,
                    finish_reason=finish_reason,
                    usage={
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                    latency_ms=latency_ms,
                    raw_response=data,
                )

        except aiohttp.ClientError as e:
            raise RuntimeError(f"Request failed: {e}")

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a chat completion.

        Uses the /v1/chat/completions endpoint.
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to GPT4All server")

        model = model or self.default_model
        if not model:
            raise ValueError("No model specified and no default model available")

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
                    raise RuntimeError(f"GPT4All API error: {error_text}")

                data = await response.json()

                # Extract response content
                choices = data.get("choices", [])
                message = choices[0].get("message", {}) if choices else {}
                content = message.get("content", "")
                finish_reason = choices[0].get("finish_reason") if choices else None

                usage = data.get("usage", {})

                # Check for LocalDocs references
                references = choices[0].get("references", []) if choices else []

                return LLMResponse(
                    content=content.strip(),
                    model=model,
                    finish_reason=finish_reason,
                    usage={
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                    latency_ms=latency_ms,
                    raw_response={**data, "references": references},
                )

        except aiohttp.ClientError as e:
            raise RuntimeError(f"Request failed: {e}")

    async def health_check(self) -> bool:
        """Check if GPT4All server is responsive."""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=5.0),
                    headers=self._get_headers(),
                )

            async with self._session.get(f"{self.base_url}/models") as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"GPT4All health check failed: {e}")
            return False

    def get_model_for_task(self, task_type: str) -> Optional[str]:
        """
        Get the best model for a specific task type.

        Uses partial matching for model names (e.g., "codellama" matches "CodeLlama-7B").

        Args:
            task_type: Type of task (e.g., "code", "analysis", "chat")

        Returns:
            Model ID or None
        """
        preferred = self.TASK_MODEL_PREFERENCES.get(task_type, [])

        for model in self._available_models:
            model_lower = model.id.lower()
            for pref in preferred:
                if pref in model_lower:
                    return model.id

        return self.default_model


# Convenience function for quick usage
async def get_gpt4all_response(
    prompt: str,
    model: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Quick helper to get a response from GPT4All.

    Usage:
        response = await get_gpt4all_response("What is Python?")
        print(response)
    """
    async with GPT4AllProvider() as provider:
        result = await provider.generate(prompt, model=model, **kwargs)
        return result.content
