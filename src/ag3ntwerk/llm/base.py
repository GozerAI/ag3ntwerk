"""
Base classes for LLM providers.

This module defines the abstract interface that all LLM providers
must implement, ensuring consistent behavior across different backends.
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from typing import Any, Dict, List, Optional
from enum import Enum

import aiohttp

from ag3ntwerk.core.exceptions import (
    LLMRateLimitError,
    LLMResponseError,
)

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model capability tiers for routing decisions."""

    FAST = "fast"  # Quick responses, lower quality
    BALANCED = "balanced"  # Good balance of speed and quality
    POWERFUL = "powerful"  # Best quality, slower
    SPECIALIZED = "specialized"  # Domain-specific models


@dataclass
class ModelInfo:
    """Information about an available model."""

    id: str
    name: str
    tier: ModelTier = ModelTier.BALANCED
    context_length: int = 4096
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tier": self.tier.value,
            "context_length": self.context_length,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
        }


@dataclass
class LLMResponse:
    """Response from an LLM generation request."""

    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    raw_response: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Message:
    """A message in a conversation."""

    role: str  # "system", "user", "assistant"
    content: str
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM backends (GPT4All, Ollama, cloud APIs) must implement
    this interface to work with ag3ntwerk agents.
    """

    def __init__(self, name: str):
        self.name = name
        self._is_connected = False
        self._available_models: List[ModelInfo] = []

    @property
    def is_connected(self) -> bool:
        """Check if provider is connected and ready."""
        return self._is_connected

    @property
    def available_models(self) -> List[ModelInfo]:
        """List available models."""
        return self._available_models

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the LLM backend.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the LLM backend."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion for the given prompt.

        Args:
            prompt: The input prompt
            model: Specific model to use (or default)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            **kwargs: Additional provider-specific options

        Returns:
            LLMResponse with the generated content
        """
        pass

    @abstractmethod
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

        Args:
            messages: Conversation history
            model: Specific model to use (or default)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            **kwargs: Additional provider-specific options

        Returns:
            LLMResponse with the generated content
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """
        Fetch and return available models.

        Returns:
            List of ModelInfo for available models
        """
        pass

    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and responsive.

        Returns:
            True if healthy
        """
        try:
            models = await self.list_models()
            return len(models) > 0
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.debug("Health check failed: %s", e)
            return False

    def get_model_by_tier(self, tier: ModelTier) -> Optional[ModelInfo]:
        """
        Get a model matching the requested tier.

        Args:
            tier: The desired model tier

        Returns:
            ModelInfo or None if no match
        """
        for model in self._available_models:
            if model.tier == tier:
                return model
        return self._available_models[0] if self._available_models else None


class BaseHTTPProvider(LLMProvider):
    """
    Intermediate base class for HTTP-based LLM providers using aiohttp.

    Provides common functionality:
    - Session management (connect/disconnect)
    - Error handling helpers
    - Context manager support
    - Default health check
    - Model selection by task
    - OpenAI-compatible response parsing

    Subclasses should override:
    - _get_headers() for custom authentication
    - list_models() (still abstract)
    - generate() and chat() (still abstract)
    - connect() if using known models instead of API endpoint
    """

    # Override in subclass to enable get_model_for_task()
    TASK_MODEL_PREFERENCES: Dict[str, List[str]] = {}

    def __init__(
        self,
        name: str,
        *,
        api_key: Optional[str] = None,
        env_var: Optional[str] = None,
        base_url: str,
        default_model: str,
        timeout: float = 120.0,
    ):
        """
        Initialize HTTP-based provider.

        Args:
            name: Provider display name
            api_key: API key (or read from env_var)
            env_var: Environment variable for API key
            base_url: Base URL for API requests
            default_model: Default model to use
            timeout: Request timeout in seconds
        """
        super().__init__(name)
        self.api_key = api_key or (os.getenv(env_var) if env_var else None)
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers. Override for custom authentication.

        Default: Bearer token authentication with JSON content type.
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _raise_for_status(self, status: int, error_text: str) -> None:
        """
        Raise appropriate exception for non-200 status.

        Args:
            status: HTTP status code
            error_text: Error response text
        """
        if status == 429:
            raise LLMRateLimitError(self.name)
        if status != 200:
            raise LLMResponseError(self.name, status, error_text)

    async def _ensure_session(self, timeout: Optional[float] = None) -> None:
        """Create session if not exists."""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout or self.timeout),
                headers=self._get_headers(),
            )

    async def connect(self) -> bool:
        """
        Connect to API: check key, create session, list models.

        Override for providers using known models instead of API listing.
        """
        if not self.api_key:
            logger.error(f"{self.name} API key not provided")
            return False

        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self._get_headers(),
            )

            models = await self.list_models()

            if models:
                self._is_connected = True
                self._available_models = models
                logger.info(f"Connected to {self.name} with {len(models)} models")
                return True

            return False

        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.error("Failed to connect to %s: %s", self.name, e, exc_info=True)
            if self._session:
                await self._session.close()
                self._session = None
            return False

    async def disconnect(self) -> None:
        """Disconnect from the API and close session."""
        if self._session:
            await self._session.close()
            self._session = None
        self._is_connected = False

    async def __aenter__(self) -> "BaseHTTPProvider":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def health_check(self) -> bool:
        """
        Default health check: verify connected and has API key.

        Override for HTTP-based health checks to an endpoint.
        """
        return self._is_connected and self.api_key is not None

    def get_model_for_task(self, task_type: str) -> Optional[str]:
        """
        Get best model for a task type using TASK_MODEL_PREFERENCES.

        Args:
            task_type: Type of task (code, analysis, chat, fast, etc.)

        Returns:
            Model ID or default model
        """
        preferred = self.TASK_MODEL_PREFERENCES.get(task_type, [])

        for pref in preferred:
            for model in self._available_models:
                if pref == model.id:
                    return model.id

        return self.default_model

    def _parse_openai_response(
        self,
        data: Dict[str, Any],
        model: str,
        latency_ms: float,
    ) -> LLMResponse:
        """
        Parse OpenAI-compatible chat completion response.

        Works for: OpenAI, OpenRouter, GitHub, Perplexity.
        """
        choices = data.get("choices", [])
        content = choices[0]["message"]["content"] if choices else ""
        finish_reason = choices[0].get("finish_reason") if choices else None

        usage = data.get("usage", {})

        return LLMResponse(
            content=content.strip(),
            model=data.get("model", model),
            finish_reason=finish_reason,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            latency_ms=latency_ms,
            raw_response=data,
        )
