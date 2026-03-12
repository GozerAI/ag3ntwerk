"""
HuggingFace LLM Provider for ag3ntwerk.

Provides access to HuggingFace Inference API and Inference Endpoints:
- Serverless Inference API (free tier available)
- Dedicated Inference Endpoints
- Thousands of open-source models

Setup:
    Set environment variable: HUGGINGFACE_API_KEY=your-key
    Or pass api_key to constructor

Popular Models:
- meta-llama/Llama-3.1-8B-Instruct
- mistralai/Mistral-7B-Instruct-v0.3
- microsoft/Phi-3-mini-4k-instruct
- Qwen/Qwen2.5-72B-Instruct
"""

import logging
import os
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
from ag3ntwerk.core.exceptions import (
    LLMConnectionError,
    LLMResponseError,
)

logger = logging.getLogger(__name__)


# Popular HuggingFace models with tier mappings
HUGGINGFACE_MODEL_TIERS = {
    # Meta Llama
    "meta-llama/Llama-3.1-405B-Instruct": ModelTier.POWERFUL,
    "meta-llama/Llama-3.1-70B-Instruct": ModelTier.POWERFUL,
    "meta-llama/Llama-3.1-8B-Instruct": ModelTier.BALANCED,
    "meta-llama/Llama-3.2-3B-Instruct": ModelTier.FAST,
    "meta-llama/Llama-3.2-1B-Instruct": ModelTier.FAST,
    # Mistral
    "mistralai/Mixtral-8x22B-Instruct-v0.1": ModelTier.POWERFUL,
    "mistralai/Mixtral-8x7B-Instruct-v0.1": ModelTier.BALANCED,
    "mistralai/Mistral-7B-Instruct-v0.3": ModelTier.BALANCED,
    # Microsoft Phi
    "microsoft/Phi-3-medium-128k-instruct": ModelTier.BALANCED,
    "microsoft/Phi-3-mini-4k-instruct": ModelTier.FAST,
    "microsoft/Phi-3.5-mini-instruct": ModelTier.FAST,
    # Qwen
    "Qwen/Qwen2.5-72B-Instruct": ModelTier.POWERFUL,
    "Qwen/Qwen2.5-32B-Instruct": ModelTier.BALANCED,
    "Qwen/Qwen2.5-7B-Instruct": ModelTier.BALANCED,
    "Qwen/Qwen2.5-1.5B-Instruct": ModelTier.FAST,
    # Code models
    "codellama/CodeLlama-70b-Instruct-hf": ModelTier.SPECIALIZED,
    "codellama/CodeLlama-34b-Instruct-hf": ModelTier.SPECIALIZED,
    "bigcode/starcoder2-15b": ModelTier.SPECIALIZED,
    "Qwen/Qwen2.5-Coder-32B-Instruct": ModelTier.SPECIALIZED,
    # Embeddings
    "sentence-transformers/all-MiniLM-L6-v2": ModelTier.SPECIALIZED,
    "BAAI/bge-large-en-v1.5": ModelTier.SPECIALIZED,
    "intfloat/multilingual-e5-large": ModelTier.SPECIALIZED,
}


class HuggingFaceProvider(BaseHTTPProvider):
    """
    HuggingFace Inference API provider.

    Provides access to thousands of open-source models via the Inference API.

    Example:
        async with HuggingFaceProvider() as provider:
            response = await provider.generate("Hello!")
            print(response.content)
    """

    TASK_MODEL_PREFERENCES = {
        "code": [
            "Qwen/Qwen2.5-Coder-32B-Instruct",
            "codellama/CodeLlama-34b-Instruct-hf",
            "bigcode/starcoder2-15b",
        ],
        "analysis": [
            "meta-llama/Llama-3.1-70B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "mistralai/Mixtral-8x22B-Instruct-v0.1",
        ],
        "chat": [
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "microsoft/Phi-3-mini-4k-instruct",
        ],
        "fast": [
            "meta-llama/Llama-3.2-1B-Instruct",
            "microsoft/Phi-3.5-mini-instruct",
            "Qwen/Qwen2.5-1.5B-Instruct",
        ],
        "embedding": [
            "sentence-transformers/all-MiniLM-L6-v2",
            "BAAI/bge-large-en-v1.5",
            "intfloat/multilingual-e5-large",
        ],
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api-inference.huggingface.co",
        default_model: str = "meta-llama/Llama-3.1-8B-Instruct",
        timeout: float = 120.0,
        wait_for_model: bool = True,
    ):
        """
        Initialize HuggingFace provider.

        Args:
            api_key: HuggingFace API key (or set HUGGINGFACE_API_KEY env var)
            base_url: API base URL
            default_model: Default model to use
            timeout: Request timeout in seconds
            wait_for_model: Wait for model to load if not ready
        """
        # Handle multiple env vars
        resolved_key = api_key or os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")

        super().__init__(
            "HuggingFace",
            api_key=resolved_key,
            env_var=None,  # Already resolved
            base_url=base_url,
            default_model=default_model,
            timeout=timeout,
        )
        self.wait_for_model = wait_for_model

    async def connect(self) -> bool:
        """Connect using known models (no models endpoint)."""
        if not self.api_key:
            logger.error("HuggingFace API key not provided")
            return False

        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self._get_headers(),
            )

            # HuggingFace doesn't have a model list endpoint for inference
            # Populate with known popular models
            self._available_models = self._get_known_models()
            self._is_connected = True
            logger.info(f"Connected to HuggingFace with {len(self._available_models)} known models")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to HuggingFace: {e}")
            if self._session:
                await self._session.close()
                self._session = None
            return False

    def _get_known_models(self) -> List[ModelInfo]:
        """Get known HuggingFace models."""
        models = []
        for model_id, tier in HUGGINGFACE_MODEL_TIERS.items():
            capabilities = ["chat", "completion"]
            if "embed" in model_id.lower() or "sentence" in model_id.lower():
                capabilities = ["embedding"]
            elif "code" in model_id.lower():
                capabilities = ["chat", "completion", "code"]

            models.append(
                ModelInfo(
                    id=model_id,
                    name=model_id.split("/")[-1],
                    tier=tier,
                    context_length=4096,  # Varies by model
                    capabilities=capabilities,
                    metadata={"provider": "huggingface"},
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
            raise LLMConnectionError("HuggingFace", self.base_url)

        model = model or self.default_model

        # Format as chat for instruction-tuned models
        if system_prompt:
            full_prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{prompt}\n<|assistant|>\n"
        else:
            full_prompt = f"<|user|>\n{prompt}\n<|assistant|>\n"

        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False,
                **kwargs,
            },
            "options": {
                "wait_for_model": self.wait_for_model,
            },
        }

        start_time = time.time()

        try:
            async with self._session.post(
                f"{self.base_url}/models/{model}",
                json=payload,
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status == 503:
                    # Model is loading
                    data = await response.json()
                    error_msg = data.get("error", "Model is loading")
                    raise LLMResponseError("HuggingFace", response.status, error_msg)

                if response.status != 200:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text)

                data = await response.json()

                # Handle different response formats
                if isinstance(data, list) and len(data) > 0:
                    content = data[0].get("generated_text", "")
                elif isinstance(data, dict):
                    content = data.get("generated_text", "")
                else:
                    content = str(data)

                return LLMResponse(
                    content=content.strip(),
                    model=model,
                    finish_reason="stop",
                    usage={},  # HF doesn't return token counts
                    latency_ms=latency_ms,
                    raw_response=data,
                )

        except aiohttp.ClientError as e:
            raise LLMConnectionError("HuggingFace", self.base_url, cause=e)

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
            raise LLMConnectionError("HuggingFace", self.base_url)

        model = model or self.default_model

        # Convert messages to prompt format
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"<|system|>\n{msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"<|user|>\n{msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"<|assistant|>\n{msg.content}")

        prompt_parts.append("<|assistant|>\n")
        full_prompt = "\n".join(prompt_parts)

        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False,
                **kwargs,
            },
            "options": {
                "wait_for_model": self.wait_for_model,
            },
        }

        start_time = time.time()

        try:
            async with self._session.post(
                f"{self.base_url}/models/{model}",
                json=payload,
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status != 200:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text)

                data = await response.json()

                if isinstance(data, list) and len(data) > 0:
                    content = data[0].get("generated_text", "")
                elif isinstance(data, dict):
                    content = data.get("generated_text", "")
                else:
                    content = str(data)

                return LLMResponse(
                    content=content.strip(),
                    model=model,
                    finish_reason="stop",
                    usage={},
                    latency_ms=latency_ms,
                    raw_response=data,
                )

        except aiohttp.ClientError as e:
            raise LLMConnectionError("HuggingFace", self.base_url, cause=e)

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Generate embeddings."""
        if not self._is_connected:
            raise LLMConnectionError("HuggingFace", self.base_url)

        model = model or "sentence-transformers/all-MiniLM-L6-v2"

        payload = {
            "inputs": text,
            "options": {
                "wait_for_model": self.wait_for_model,
            },
        }

        try:
            async with self._session.post(
                f"{self.base_url}/models/{model}",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text)

                data = await response.json()

                # Handle different embedding response formats
                if isinstance(data, list):
                    if isinstance(data[0], list):
                        return data[0]  # Nested list
                    return data  # Flat list
                return []

        except aiohttp.ClientError as e:
            raise LLMConnectionError("HuggingFace", self.base_url, cause=e)
