"""
Perplexity LLM Provider for ag3ntwerk.

Provides access to Perplexity's AI models with real-time web search:
- Sonar models (with web search)
- Llama models (offline)

Key Features:
- Real-time web search integration
- Citations and sources
- Up-to-date information

Setup:
    Set environment variable: PERPLEXITY_API_KEY=your-key
    Or pass api_key to constructor
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


# Perplexity models
PERPLEXITY_MODELS = {
    # Sonar models (with web search)
    "sonar": ModelTier.BALANCED,
    "sonar-pro": ModelTier.POWERFUL,
    "sonar-reasoning": ModelTier.POWERFUL,
    # Llama-based models (offline)
    "llama-3.1-sonar-small-128k-online": ModelTier.FAST,
    "llama-3.1-sonar-large-128k-online": ModelTier.BALANCED,
    "llama-3.1-sonar-huge-128k-online": ModelTier.POWERFUL,
    # Offline models
    "llama-3.1-8b-instruct": ModelTier.FAST,
    "llama-3.1-70b-instruct": ModelTier.BALANCED,
}

MODEL_CONTEXT_LENGTHS = {
    "sonar": 127072,
    "sonar-pro": 127072,
    "sonar-reasoning": 127072,
    "llama-3.1-sonar-small-128k-online": 127072,
    "llama-3.1-sonar-large-128k-online": 127072,
    "llama-3.1-sonar-huge-128k-online": 127072,
    "llama-3.1-8b-instruct": 131072,
    "llama-3.1-70b-instruct": 131072,
}


class PerplexityProvider(BaseHTTPProvider):
    """
    Perplexity AI LLM provider.

    Provides access to Perplexity's models with optional web search.

    Example:
        async with PerplexityProvider() as provider:
            response = await provider.generate("What is the latest news?")
            print(response.content)
            print(response.raw_response.get("citations", []))
    """

    TASK_MODEL_PREFERENCES = {
        "search": ["sonar-pro", "sonar"],
        "research": ["sonar-pro", "sonar-reasoning"],
        "analysis": ["sonar-pro", "llama-3.1-70b-instruct"],
        "chat": ["sonar", "llama-3.1-8b-instruct"],
        "fast": ["llama-3.1-8b-instruct", "llama-3.1-sonar-small-128k-online"],
        "reasoning": ["sonar-reasoning", "sonar-pro"],
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.perplexity.ai",
        default_model: str = "sonar",
        timeout: float = 120.0,
    ):
        """
        Initialize Perplexity provider.

        Args:
            api_key: Perplexity API key (or set PERPLEXITY_API_KEY env var)
            base_url: API base URL
            default_model: Default model to use
            timeout: Request timeout in seconds
        """
        super().__init__(
            "Perplexity",
            api_key=api_key,
            env_var="PERPLEXITY_API_KEY",
            base_url=base_url,
            default_model=default_model,
            timeout=timeout,
        )

    async def connect(self) -> bool:
        """Connect using known models (no models endpoint)."""
        if not self.api_key:
            logger.error("Perplexity API key not provided")
            return False

        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self._get_headers(),
            )

            # Populate with known models
            self._available_models = self._get_known_models()
            self._is_connected = True
            logger.info(f"Connected to Perplexity with {len(self._available_models)} models")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Perplexity: {e}")
            if self._session:
                await self._session.close()
                self._session = None
            return False

    def _get_known_models(self) -> List[ModelInfo]:
        """Get known Perplexity models."""
        models = []
        for model_id, tier in PERPLEXITY_MODELS.items():
            context_length = MODEL_CONTEXT_LENGTHS.get(model_id, 127072)

            capabilities = ["chat", "completion"]
            if "sonar" in model_id or "online" in model_id:
                capabilities.append("web-search")

            models.append(
                ModelInfo(
                    id=model_id,
                    name=model_id,
                    tier=tier,
                    context_length=context_length,
                    capabilities=capabilities,
                    metadata={"provider": "perplexity"},
                )
            )
        return models

    async def list_models(self) -> List[ModelInfo]:
        """List available models."""
        return self._get_known_models()

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        search_domain_filter: Optional[List[str]] = None,
        return_citations: bool = True,
        return_images: bool = False,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text completion with optional web search.

        Args:
            prompt: Input prompt
            model: Model to use
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            system_prompt: System prompt
            search_domain_filter: Limit search to specific domains
            return_citations: Include source citations
            return_images: Include images in response
        """
        if not self._is_connected:
            raise LLMConnectionError("Perplexity", self.base_url)

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
            "return_citations": return_citations,
            "return_images": return_images,
        }

        if search_domain_filter:
            payload["search_domain_filter"] = search_domain_filter

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

                # Use base parsing and augment with citations/images
                llm_response = self._parse_openai_response(data, model, latency_ms)

                # Augment raw_response with citations and images
                llm_response.raw_response["citations"] = data.get("citations", [])
                llm_response.raw_response["images"] = data.get("images", [])

                return llm_response

        except aiohttp.ClientError as e:
            raise LLMConnectionError("Perplexity", self.base_url, cause=e)

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        return_citations: bool = True,
        **kwargs,
    ) -> LLMResponse:
        """Generate chat completion with web search."""
        if not self._is_connected:
            raise LLMConnectionError("Perplexity", self.base_url)

        model = model or self.default_model

        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "return_citations": return_citations,
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

                # Use base parsing and augment with citations
                llm_response = self._parse_openai_response(data, model, latency_ms)
                llm_response.raw_response["citations"] = data.get("citations", [])

                return llm_response

        except aiohttp.ClientError as e:
            raise LLMConnectionError("Perplexity", self.base_url, cause=e)

    async def search(
        self,
        query: str,
        model: str = "sonar",
        max_tokens: int = 1024,
        search_domain_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Perform a web search query.

        Args:
            query: Search query
            model: Model to use (sonar recommended)
            max_tokens: Maximum response tokens
            search_domain_filter: Limit to specific domains

        Returns:
            Dict with 'content', 'citations', and 'images'
        """
        response = await self.generate(
            prompt=query,
            model=model,
            max_tokens=max_tokens,
            search_domain_filter=search_domain_filter,
            return_citations=True,
            return_images=True,
        )

        return {
            "content": response.content,
            "citations": response.raw_response.get("citations", []),
            "images": response.raw_response.get("images", []),
        }
