"""
GitHub Models LLM Provider for ag3ntwerk.

Provides access to models via GitHub's AI model marketplace:
- OpenAI models (GPT-4o, GPT-4o-mini)
- Meta Llama models
- Mistral models
- Cohere models
- And more

Setup:
    Set environment variable: GITHUB_TOKEN=your-token
    Or pass api_key to constructor

Note: Requires GitHub account with access to GitHub Models (in preview)
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


# GitHub Models available
GITHUB_MODELS = {
    # OpenAI
    "gpt-4o": ModelTier.POWERFUL,
    "gpt-4o-mini": ModelTier.BALANCED,
    # Meta Llama
    "Meta-Llama-3.1-405B-Instruct": ModelTier.POWERFUL,
    "Meta-Llama-3.1-70B-Instruct": ModelTier.POWERFUL,
    "Meta-Llama-3.1-8B-Instruct": ModelTier.BALANCED,
    "Llama-3.2-90B-Vision-Instruct": ModelTier.POWERFUL,
    "Llama-3.2-11B-Vision-Instruct": ModelTier.BALANCED,
    # Mistral
    "Mistral-large-2407": ModelTier.POWERFUL,
    "Mistral-small": ModelTier.BALANCED,
    "Mistral-Nemo": ModelTier.FAST,
    # Cohere
    "Cohere-command-r-plus": ModelTier.POWERFUL,
    "Cohere-command-r": ModelTier.BALANCED,
    # AI21
    "AI21-Jamba-1.5-Large": ModelTier.POWERFUL,
    "AI21-Jamba-1.5-Mini": ModelTier.FAST,
    # Microsoft Phi
    "Phi-3.5-MoE-instruct": ModelTier.BALANCED,
    "Phi-3.5-mini-instruct": ModelTier.FAST,
    "Phi-3.5-vision-instruct": ModelTier.BALANCED,
}

MODEL_CONTEXT_LENGTHS = {
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "Meta-Llama-3.1-405B-Instruct": 128000,
    "Meta-Llama-3.1-70B-Instruct": 128000,
    "Meta-Llama-3.1-8B-Instruct": 128000,
    "Mistral-large-2407": 128000,
    "Cohere-command-r-plus": 128000,
}


class GitHubProvider(BaseHTTPProvider):
    """
    GitHub Models LLM provider.

    Provides access to various models via GitHub's model marketplace.

    Example:
        async with GitHubProvider() as provider:
            response = await provider.generate("Hello!")
            print(response.content)
    """

    TASK_MODEL_PREFERENCES = {
        "code": ["gpt-4o", "Meta-Llama-3.1-70B-Instruct", "Mistral-large-2407"],
        "analysis": ["gpt-4o", "Meta-Llama-3.1-405B-Instruct", "Cohere-command-r-plus"],
        "chat": ["gpt-4o-mini", "Meta-Llama-3.1-8B-Instruct", "Mistral-Nemo"],
        "fast": ["gpt-4o-mini", "Phi-3.5-mini-instruct", "AI21-Jamba-1.5-Mini"],
        "vision": ["Llama-3.2-90B-Vision-Instruct", "Phi-3.5-vision-instruct"],
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://models.inference.ai.azure.com",
        default_model: str = "gpt-4o-mini",
        timeout: float = 120.0,
    ):
        """
        Initialize GitHub Models provider.

        Args:
            api_key: GitHub token (or set GITHUB_TOKEN env var)
            base_url: API base URL
            default_model: Default model to use
            timeout: Request timeout in seconds
        """
        super().__init__(
            "GitHub",
            api_key=api_key,
            env_var="GITHUB_TOKEN",
            base_url=base_url,
            default_model=default_model,
            timeout=timeout,
        )

    async def connect(self) -> bool:
        """Connect using known models (no models endpoint)."""
        if not self.api_key:
            logger.error("GitHub token not provided")
            return False

        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self._get_headers(),
            )

            # Populate with known models
            self._available_models = self._get_known_models()
            self._is_connected = True
            logger.info(f"Connected to GitHub Models with {len(self._available_models)} models")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to GitHub Models: {e}")
            if self._session:
                await self._session.close()
                self._session = None
            return False

    def _get_known_models(self) -> List[ModelInfo]:
        """Get known GitHub Models."""
        models = []
        for model_id, tier in GITHUB_MODELS.items():
            context_length = MODEL_CONTEXT_LENGTHS.get(model_id, 32768)

            capabilities = ["chat", "completion"]
            if "vision" in model_id.lower():
                capabilities.append("vision")

            models.append(
                ModelInfo(
                    id=model_id,
                    name=model_id,
                    tier=tier,
                    context_length=context_length,
                    capabilities=capabilities,
                    metadata={"provider": "github"},
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
        **kwargs,
    ) -> LLMResponse:
        """Generate text completion."""
        if not self._is_connected:
            raise LLMConnectionError("GitHub", self.base_url)

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
            raise LLMConnectionError("GitHub", self.base_url, cause=e)

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
            raise LLMConnectionError("GitHub", self.base_url)

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
            raise LLMConnectionError("GitHub", self.base_url, cause=e)

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Generate embeddings."""
        if not self._is_connected:
            raise LLMConnectionError("GitHub", self.base_url)

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
            raise LLMConnectionError("GitHub", self.base_url, cause=e)
