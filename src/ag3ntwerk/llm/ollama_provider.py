"""
Ollama LLM Provider for ag3ntwerk.

Ollama provides local LLM inference with:
- OpenAI-compatible API
- Efficient model management via CLI and API
- GPU acceleration support
- Container-friendly deployment
- Extensive model library

Setup:
    1. Install Ollama: https://ollama.ai
    2. Start server: `ollama serve`
    3. Pull models: `ollama pull llama3.2`

API Endpoints:
    - /api/tags - List models
    - /api/chat - Chat completions
    - /api/generate - Text generation
    - /api/embeddings - Generate embeddings
    - /api/pull - Pull models
    - /api/show - Model information
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
from ag3ntwerk.core.exceptions import (
    LLMConnectionError,
    LLMModelNotFoundError,
    LLMResponseError,
)

logger = logging.getLogger(__name__)


# Model tier mappings for common Ollama models
OLLAMA_MODEL_TIERS = {
    # Fast tier - small, quick models
    "phi": ModelTier.FAST,
    "phi3:mini": ModelTier.FAST,
    "phi3.5": ModelTier.FAST,
    "tinyllama": ModelTier.FAST,
    "gemma:2b": ModelTier.FAST,
    "gemma2:2b": ModelTier.FAST,
    "qwen:0.5b": ModelTier.FAST,
    "qwen2:0.5b": ModelTier.FAST,
    "qwen2.5:0.5b": ModelTier.FAST,
    "qwen2.5:1.5b": ModelTier.FAST,
    "smollm": ModelTier.FAST,
    # Balanced tier - good quality/speed tradeoff
    "llama3": ModelTier.BALANCED,
    "llama3.1": ModelTier.BALANCED,
    "llama3.2": ModelTier.BALANCED,
    "llama3.2:3b": ModelTier.BALANCED,
    "mistral": ModelTier.BALANCED,
    "mistral:7b": ModelTier.BALANCED,
    "gemma": ModelTier.BALANCED,
    "gemma:7b": ModelTier.BALANCED,
    "gemma2": ModelTier.BALANCED,
    "gemma2:9b": ModelTier.BALANCED,
    "qwen": ModelTier.BALANCED,
    "qwen2": ModelTier.BALANCED,
    "qwen2.5": ModelTier.BALANCED,
    "qwen2.5:7b": ModelTier.BALANCED,
    "nous-hermes": ModelTier.BALANCED,
    "neural-chat": ModelTier.BALANCED,
    "starling": ModelTier.BALANCED,
    "zephyr": ModelTier.BALANCED,
    "vicuna": ModelTier.BALANCED,
    "openchat": ModelTier.BALANCED,
    # Powerful tier - large, high-quality models
    "llama3:70b": ModelTier.POWERFUL,
    "llama3.1:70b": ModelTier.POWERFUL,
    "llama3.2:70b": ModelTier.POWERFUL,
    "mixtral": ModelTier.POWERFUL,
    "mixtral:8x7b": ModelTier.POWERFUL,
    "mixtral:8x22b": ModelTier.POWERFUL,
    "command-r": ModelTier.POWERFUL,
    "command-r-plus": ModelTier.POWERFUL,
    "qwen2.5:72b": ModelTier.POWERFUL,
    "deepseek": ModelTier.POWERFUL,
    "yi:34b": ModelTier.POWERFUL,
    # Specialized tier - domain-specific models
    "codellama": ModelTier.SPECIALIZED,
    "deepseek-coder": ModelTier.SPECIALIZED,
    "deepseek-coder-v2": ModelTier.SPECIALIZED,
    "starcoder": ModelTier.SPECIALIZED,
    "starcoder2": ModelTier.SPECIALIZED,
    "codegemma": ModelTier.SPECIALIZED,
    "codestral": ModelTier.SPECIALIZED,
    "sqlcoder": ModelTier.SPECIALIZED,
    "magicoder": ModelTier.SPECIALIZED,
    "wizardcoder": ModelTier.SPECIALIZED,
    "phind-codellama": ModelTier.SPECIALIZED,
    "dolphin-mixtral": ModelTier.SPECIALIZED,
    "meditron": ModelTier.SPECIALIZED,
    "medllama2": ModelTier.SPECIALIZED,
    "llava": ModelTier.SPECIALIZED,  # Vision model
    "bakllava": ModelTier.SPECIALIZED,  # Vision model
    "llava-llama3": ModelTier.SPECIALIZED,  # Vision model
    "nomic-embed-text": ModelTier.SPECIALIZED,  # Embedding model
    "mxbai-embed-large": ModelTier.SPECIALIZED,  # Embedding model
    "all-minilm": ModelTier.SPECIALIZED,  # Embedding model
}


def _infer_model_tier(model_name: str) -> ModelTier:
    """Infer model tier from model name."""
    name_lower = model_name.lower()

    # Direct match
    if name_lower in OLLAMA_MODEL_TIERS:
        return OLLAMA_MODEL_TIERS[name_lower]

    # Partial match
    for key, tier in OLLAMA_MODEL_TIERS.items():
        if key in name_lower:
            return tier

    # Infer from size indicators
    if any(x in name_lower for x in ["70b", "72b", "34b", "8x7b", "8x22b"]):
        return ModelTier.POWERFUL
    if any(x in name_lower for x in ["0.5b", "1b", "2b", "mini", "tiny", "small"]):
        return ModelTier.FAST
    if any(x in name_lower for x in ["code", "coder", "sql", "embed"]):
        return ModelTier.SPECIALIZED

    # Default to balanced
    return ModelTier.BALANCED


def _infer_capabilities(model_name: str) -> List[str]:
    """Infer model capabilities from name."""
    caps = ["chat", "completion"]
    name_lower = model_name.lower()

    if any(x in name_lower for x in ["code", "coder", "starcoder", "codestral", "wizard"]):
        caps.extend(["code", "code-completion", "code-review"])
    if any(x in name_lower for x in ["llava", "vision", "bakllava"]):
        caps.append("vision")
    if any(x in name_lower for x in ["embed", "nomic", "minilm", "mxbai"]):
        caps = ["embedding"]  # Embedding-only models
    if any(x in name_lower for x in ["sql", "sqlcoder"]):
        caps.extend(["sql", "database"])

    return caps


def _get_context_length(model_name: str, details: Dict[str, Any]) -> int:
    """Get context length from model details or infer from name."""
    # Try to get from details
    if "parameters" in details:
        params = details["parameters"]
        if isinstance(params, dict) and "num_ctx" in params:
            return params["num_ctx"]

    # Infer from model name
    name_lower = model_name.lower()

    # Models with known large contexts
    if any(x in name_lower for x in ["128k", "128000"]):
        return 128000
    if any(x in name_lower for x in ["32k", "32000"]):
        return 32768
    if any(x in name_lower for x in ["llama3", "llama-3"]):
        return 8192
    if any(x in name_lower for x in ["mixtral"]):
        return 32768
    if any(x in name_lower for x in ["mistral"]):
        return 8192

    # Default context length
    return 4096


class OllamaProvider(BaseHTTPProvider):
    """
    Ollama LLM provider for local inference.

    Provides access to locally running Ollama models with support for:
    - Chat completions
    - Text generation
    - Embeddings
    - Model management

    Example:
        async with OllamaProvider() as provider:
            response = await provider.generate("Hello, how are you?")
            print(response.content)

    Configuration:
        provider = OllamaProvider(
            base_url="http://localhost:11434",
            default_model="llama3.2",
            timeout=300.0,
        )
    """

    TASK_MODEL_PREFERENCES = {
        "code": [
            "deepseek-coder",
            "codellama",
            "codegemma",
            "codestral",
            "starcoder",
            "wizardcoder",
            "phind-codellama",
            "qwen2.5-coder",
        ],
        "sql": ["sqlcoder", "deepseek-coder", "codellama"],
        "analysis": ["mixtral", "llama3.1:70b", "qwen2.5:72b", "command-r"],
        "chat": ["llama3.2", "llama3.1", "mistral", "gemma2", "qwen2.5"],
        "fast": ["phi3:mini", "gemma:2b", "qwen2.5:0.5b", "tinyllama", "smollm"],
        "embedding": ["nomic-embed-text", "mxbai-embed-large", "all-minilm"],
        "vision": ["llava", "llava-llama3", "bakllava"],
    }

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: Optional[str] = None,
        timeout: float = 300.0,
        **kwargs,  # Accept and ignore api_key and other unused args for interface compatibility
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Base URL for Ollama server
            default_model: Default model to use (auto-selected if not specified)
            timeout: Request timeout in seconds (longer for local inference)
            **kwargs: Ignored - allows uniform interface with API-key-based providers
        """
        # Ollama doesn't use API keys, but we accept the parameter for interface compatibility
        super().__init__(
            "Ollama",
            api_key=None,  # Ollama doesn't require API key
            env_var=None,
            base_url=base_url,
            default_model=default_model or "",  # Will be auto-selected
            timeout=timeout,
        )

    def _get_headers(self) -> Dict[str, str]:
        """No auth headers needed for Ollama."""
        return {"Content-Type": "application/json"}

    async def connect(self) -> bool:
        """Connect to Ollama server and fetch available models."""
        try:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))

            # Test connection and get models
            models = await self.list_models()

            if models:
                self._is_connected = True
                self._available_models = models

                # Auto-select default model if not specified
                if not self.default_model and models:
                    # Prefer common models in order
                    preferred = [
                        "llama3.2",
                        "llama3.1",
                        "llama3",
                        "mistral",
                        "gemma2",
                        "gemma",
                        "phi3",
                        "qwen2.5",
                        "qwen2",
                    ]
                    for pref in preferred:
                        for model in models:
                            if pref in model.name.lower():
                                self.default_model = model.id
                                logger.info(f"Auto-selected model: {self.default_model}")
                                break
                        if self.default_model:
                            break

                    # Fall back to first model
                    if not self.default_model:
                        self.default_model = models[0].id
                        logger.info(f"Using first available model: {self.default_model}")

                logger.info(
                    f"Connected to Ollama at {self.base_url} "
                    f"with {len(models)} models available"
                )
                return True
            else:
                logger.warning("Ollama connected but no models available")
                await self.disconnect()
                return False

        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            if self._session:
                await self._session.close()
                self._session = None
            return False

    async def list_models(self) -> List[ModelInfo]:
        """Fetch available models from Ollama."""
        if not self._session:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30.0))

        try:
            async with self._session.get(f"{self.base_url}/api/tags") as response:
                if response.status != 200:
                    return []

                data = await response.json()
                models = []

                for model_data in data.get("models", []):
                    name = model_data.get("name", "")
                    details = model_data.get("details", {})

                    model_info = ModelInfo(
                        id=name,
                        name=name,
                        tier=_infer_model_tier(name),
                        context_length=_get_context_length(name, details),
                        capabilities=_infer_capabilities(name),
                        metadata={
                            "size": model_data.get("size", 0),
                            "digest": model_data.get("digest", ""),
                            "modified_at": model_data.get("modified_at", ""),
                            "details": details,
                        },
                    )
                    models.append(model_info)

                return models

        except aiohttp.ClientError as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []

    def _parse_ollama_response(
        self,
        data: Dict[str, Any],
        model: str,
        latency_ms: float,
    ) -> LLMResponse:
        """Parse Ollama's chat response format."""
        message = data.get("message", {})
        content = message.get("content", "")

        usage = {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        }

        return LLMResponse(
            content=content.strip(),
            model=model,
            finish_reason=data.get("done_reason", "stop"),
            usage=usage,
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
            raise LLMConnectionError("Ollama", self.base_url)

        model = model or self.default_model
        if not model:
            raise LLMModelNotFoundError("Ollama", "none", [m.id for m in self._available_models])

        # Use chat API with single message for generation
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **kwargs.get("options", {}),
            },
        }

        start_time = time.time()

        try:
            async with self._session.post(
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status != 200:
                    error_text = await response.text()
                    raise LLMResponseError("Ollama", response.status, error_text)

                data = await response.json()
                return self._parse_ollama_response(data, model, latency_ms)

        except aiohttp.ClientError as e:
            raise LLMConnectionError("Ollama", self.base_url, cause=e)

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
            raise LLMConnectionError("Ollama", self.base_url)

        model = model or self.default_model
        if not model:
            raise LLMModelNotFoundError("Ollama", "none", [m.id for m in self._available_models])

        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **kwargs.get("options", {}),
            },
        }

        start_time = time.time()

        try:
            async with self._session.post(
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status != 200:
                    error_text = await response.text()
                    raise LLMResponseError("Ollama", response.status, error_text)

                data = await response.json()
                return self._parse_ollama_response(data, model, latency_ms)

        except aiohttp.ClientError as e:
            raise LLMConnectionError("Ollama", self.base_url, cause=e)

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Generate embeddings for text."""
        if not self._is_connected:
            raise LLMConnectionError("Ollama", self.base_url)

        # Find embedding model
        embed_model = model
        if not embed_model:
            for m in self._available_models:
                if "embed" in m.name.lower():
                    embed_model = m.id
                    break
            # Fall back to default model (may not work well)
            embed_model = embed_model or self.default_model

        if not embed_model:
            raise LLMModelNotFoundError(
                "Ollama",
                "embedding model",
                [m.id for m in self._available_models],
            )

        payload = {
            "model": embed_model,
            "prompt": text,
        }

        try:
            async with self._session.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LLMResponseError("Ollama", response.status, error_text)

                data = await response.json()
                return data.get("embedding", [])

        except aiohttp.ClientError as e:
            raise LLMConnectionError("Ollama", self.base_url, cause=e)

    async def health_check(self) -> bool:
        """Check if Ollama server is responsive."""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5.0))

            async with self._session.get(f"{self.base_url}/api/tags") as response:
                return response.status == 200

        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.debug("Ollama health check failed: %s", e)
            return False

    def get_model_for_task(self, task_type: str) -> Optional[str]:
        """
        Get the best model for a specific task type.

        Uses partial matching (`in`) instead of exact match for flexibility
        with Ollama's model naming conventions.
        """
        preferred = self.TASK_MODEL_PREFERENCES.get(task_type, [])

        for model in self._available_models:
            model_lower = model.id.lower()
            for pref in preferred:
                if pref in model_lower:
                    return model.id

        return self.default_model

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama library."""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=3600.0)  # 1 hour for large models
            )

        try:
            async with self._session.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": False},
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully pulled model: {model_name}")
                    # Refresh model list
                    self._available_models = await self.list_models()
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to pull model {model_name}: {error_text}")
                    return False

        except aiohttp.ClientError as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False

    async def show_model(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a model."""
        if not self._session:
            raise LLMConnectionError("Ollama", self.base_url)

        try:
            async with self._session.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}

        except aiohttp.ClientError:
            return {}


# Convenience function for quick usage
async def get_ollama_response(
    prompt: str,
    model: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Quick helper to get a response from Ollama.

    Usage:
        response = await get_ollama_response("What is Python?")
        print(response)
    """
    async with OllamaProvider() as provider:
        result = await provider.generate(prompt, model=model, **kwargs)
        return result.content
