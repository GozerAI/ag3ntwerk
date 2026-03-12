"""
LLM Provider module for ag3ntwerk agents.

This module provides a unified interface for multiple LLM backends:

Local Providers:
- Ollama (recommended): Local inference with efficient model management
- GPT4All: Alternative local inference via desktop app

Cloud Providers:
- OpenAI: GPT-4o, GPT-4, GPT-3.5 Turbo
- Anthropic: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- Google: Gemini 2.0, Gemini 1.5 Pro/Flash
- OpenRouter: Unified access to 100+ models
- HuggingFace: Open-source models via Inference API
- GitHub: GitHub Models marketplace
- Perplexity: AI with real-time web search

Usage:
    # Auto-detect provider (tries Ollama first)
    provider = get_provider()
    await provider.connect()

    # Specific local provider
    provider = get_provider("ollama")

    # Cloud provider
    provider = get_provider("openai", api_key="sk-...")
    provider = get_provider("anthropic")  # Uses ANTHROPIC_API_KEY env var

    # Generate response
    response = await provider.generate("Hello!")
    print(response.content)

    await provider.disconnect()
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

from ag3ntwerk.llm.base import (
    BaseHTTPProvider,
    LLMProvider,
    LLMResponse,
    Message,
    ModelInfo,
    ModelTier,
)

from ag3ntwerk.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    CircuitOpenError,
    CircuitState,
    get_circuit_breaker,
    get_circuit_breaker_registry,
    with_circuit_breaker,
)

# Local providers
from ag3ntwerk.llm.ollama_provider import OllamaProvider
from ag3ntwerk.llm.gpt4all_provider import GPT4AllProvider

# Cloud providers
from ag3ntwerk.llm.openai_provider import OpenAIProvider
from ag3ntwerk.llm.anthropic_provider import AnthropicProvider
from ag3ntwerk.llm.google_provider import GoogleProvider
from ag3ntwerk.llm.openrouter_provider import OpenRouterProvider
from ag3ntwerk.llm.huggingface_provider import HuggingFaceProvider
from ag3ntwerk.llm.github_provider import GitHubProvider
from ag3ntwerk.llm.perplexity_provider import PerplexityProvider


# Provider registry
PROVIDERS = {
    # Local
    "ollama": OllamaProvider,
    "gpt4all": GPT4AllProvider,
    # Cloud
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "gemini": GoogleProvider,  # Alias
    "openrouter": OpenRouterProvider,
    "huggingface": HuggingFaceProvider,
    "hf": HuggingFaceProvider,  # Alias
    "github": GitHubProvider,
    "perplexity": PerplexityProvider,
}


def get_provider(
    provider_type: str = "auto",
    **kwargs,
) -> LLMProvider:
    """
    Get an LLM provider instance.

    Args:
        provider_type: Provider type to use:
            Local:
            - "auto": Try Ollama first, fall back to GPT4All
            - "ollama": Ollama local inference
            - "gpt4all": GPT4All local inference

            Cloud:
            - "openai": OpenAI GPT models
            - "anthropic": Anthropic Claude models
            - "google" / "gemini": Google Gemini models
            - "openrouter": OpenRouter unified API
            - "huggingface" / "hf": HuggingFace Inference
            - "github": GitHub Models
            - "perplexity": Perplexity AI with web search

        **kwargs: Provider-specific arguments:
            - api_key: API key (or use environment variable)
            - base_url: Server URL
            - default_model: Default model to use
            - timeout: Request timeout in seconds

    Returns:
        Configured LLMProvider instance

    Examples:
        # Auto-detect local provider
        provider = get_provider()

        # Explicit local provider
        provider = get_provider("ollama", base_url="http://localhost:11434")

        # Cloud providers (API keys from env vars)
        provider = get_provider("openai")  # Uses OPENAI_API_KEY
        provider = get_provider("anthropic")  # Uses ANTHROPIC_API_KEY
        provider = get_provider("google")  # Uses GOOGLE_API_KEY

        # Cloud provider with explicit key
        provider = get_provider("openai", api_key="sk-...")
    """
    if provider_type == "auto":
        # Default to Ollama (preferred) - it will fail gracefully if not available
        return OllamaProvider(**kwargs)

    provider_type_lower = provider_type.lower()

    if provider_type_lower in PROVIDERS:
        return PROVIDERS[provider_type_lower](**kwargs)

    raise ValueError(
        f"Unknown provider type: {provider_type}. "
        f"Supported: {', '.join(sorted(PROVIDERS.keys()))}"
    )


async def auto_connect() -> Optional[LLMProvider]:
    """
    Auto-detect and connect to an available LLM provider.

    Tries providers in order:
    1. Ollama (localhost:11434)
    2. GPT4All (localhost:4891)

    For cloud providers, use get_provider() directly.

    Returns:
        Connected LLMProvider or None if no local provider available

    Example:
        provider = await auto_connect()
        if provider:
            response = await provider.generate("Hello!")
            await provider.disconnect()
    """
    # Try Ollama first
    ollama = OllamaProvider()
    if await ollama.connect():
        return ollama

    # Try GPT4All
    gpt4all = GPT4AllProvider()
    if await gpt4all.connect():
        return gpt4all

    return None


async def auto_connect_cloud(
    preferred: Optional[list[str]] = None,
) -> Optional[LLMProvider]:
    """
    Auto-connect to first available cloud provider.

    Tries providers in order based on environment variable availability.

    Args:
        preferred: Ordered list of preferred providers to try

    Returns:
        Connected LLMProvider or None if no provider available

    Example:
        provider = await auto_connect_cloud(["anthropic", "openai"])
        if provider:
            response = await provider.generate("Hello!")
            await provider.disconnect()
    """
    import os

    # Default order based on common preference
    providers_to_try = preferred or [
        "anthropic",
        "openai",
        "google",
        "openrouter",
        "github",
        "perplexity",
        "huggingface",
    ]

    # Environment variable mapping
    env_vars = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "github": "GITHUB_TOKEN",
        "perplexity": "PERPLEXITY_API_KEY",
        "huggingface": "HUGGINGFACE_API_KEY",
    }

    for provider_name in providers_to_try:
        env_var = env_vars.get(provider_name)
        if env_var and os.getenv(env_var):
            try:
                provider = get_provider(provider_name)
                if await provider.connect():
                    return provider
            except Exception as e:
                logger.debug(f"Failed to connect to {provider_name}: {e}")
                continue

    return None


__all__ = [
    # Base classes
    "BaseHTTPProvider",
    "LLMProvider",
    "LLMResponse",
    "Message",
    "ModelInfo",
    "ModelTier",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    "CircuitBreakerRegistry",
    "CircuitOpenError",
    "CircuitState",
    "get_circuit_breaker",
    "get_circuit_breaker_registry",
    "with_circuit_breaker",
    # Local providers
    "OllamaProvider",
    "GPT4AllProvider",
    # Cloud providers
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "OpenRouterProvider",
    "HuggingFaceProvider",
    "GitHubProvider",
    "PerplexityProvider",
    # Factory functions
    "get_provider",
    "auto_connect",
    "auto_connect_cloud",
    # Registry
    "PROVIDERS",
]
