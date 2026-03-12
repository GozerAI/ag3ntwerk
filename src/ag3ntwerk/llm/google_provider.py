"""
Google AI (Gemini) LLM Provider for ag3ntwerk.

Provides access to Google's Gemini models:
- Gemini 2.0 Flash
- Gemini 1.5 Pro
- Gemini 1.5 Flash
- Text embedding models

Setup:
    Set environment variable: GOOGLE_API_KEY=your-key
    Or pass api_key to constructor

Note: This uses the Google AI Studio API (generativelanguage.googleapis.com)
      For Vertex AI, use a separate provider.
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


# Gemini model configurations
GEMINI_MODELS = {
    # Gemini 2.0
    "gemini-2.0-flash-exp": ModelTier.POWERFUL,
    "gemini-2.0-flash-thinking-exp": ModelTier.POWERFUL,
    # Gemini 1.5
    "gemini-1.5-pro": ModelTier.POWERFUL,
    "gemini-1.5-pro-latest": ModelTier.POWERFUL,
    "gemini-1.5-flash": ModelTier.BALANCED,
    "gemini-1.5-flash-latest": ModelTier.BALANCED,
    "gemini-1.5-flash-8b": ModelTier.FAST,
    # Gemini 1.0
    "gemini-1.0-pro": ModelTier.BALANCED,
    "gemini-pro": ModelTier.BALANCED,
    # Embeddings
    "text-embedding-004": ModelTier.SPECIALIZED,
    "embedding-001": ModelTier.SPECIALIZED,
}

MODEL_CONTEXT_LENGTHS = {
    "gemini-2.0-flash-exp": 1000000,
    "gemini-1.5-pro": 2000000,
    "gemini-1.5-flash": 1000000,
    "gemini-1.5-flash-8b": 1000000,
    "gemini-1.0-pro": 32768,
    "gemini-pro": 32768,
}


class GoogleProvider(BaseHTTPProvider):
    """
    Google AI (Gemini) LLM provider.

    Provides access to Gemini models via Google AI Studio API.

    Example:
        async with GoogleProvider() as provider:
            response = await provider.generate("Hello!")
            print(response.content)
    """

    TASK_MODEL_PREFERENCES = {
        "code": ["gemini-1.5-pro", "gemini-2.0-flash-exp"],
        "analysis": ["gemini-1.5-pro", "gemini-2.0-flash-exp"],
        "chat": ["gemini-1.5-flash", "gemini-1.5-flash-8b"],
        "fast": ["gemini-1.5-flash-8b", "gemini-1.5-flash"],
        "embedding": ["text-embedding-004", "embedding-001"],
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        default_model: str = "gemini-1.5-flash",
        timeout: float = 120.0,
    ):
        """
        Initialize Google AI provider.

        Args:
            api_key: Google AI API key (or set GOOGLE_API_KEY env var)
            base_url: API base URL
            default_model: Default model to use
            timeout: Request timeout in seconds
        """
        super().__init__(
            "Google",
            api_key=api_key,
            env_var="GOOGLE_API_KEY",
            base_url=base_url,
            default_model=default_model,
            timeout=timeout,
        )

    def _get_headers(self) -> Dict[str, str]:
        """Google uses API key in URL, not in headers."""
        return {"Content-Type": "application/json"}

    async def connect(self) -> bool:
        """Connect to Google AI API."""
        if not self.api_key:
            logger.error("Google API key not provided")
            return False

        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )

            models = await self.list_models()

            if models:
                self._is_connected = True
                self._available_models = models
                logger.info(f"Connected to Google AI with {len(models)} models")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to connect to Google AI: {e}")
            if self._session:
                await self._session.close()
                self._session = None
            return False

    async def list_models(self) -> List[ModelInfo]:
        """List available models."""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30.0),
            )

        try:
            async with self._session.get(f"{self.base_url}/models?key={self.api_key}") as response:
                if response.status != 200:
                    return []

                data = await response.json()
                models = []

                for model_data in data.get("models", []):
                    # Extract model name (e.g., "models/gemini-1.5-pro" -> "gemini-1.5-pro")
                    full_name = model_data.get("name", "")
                    model_id = full_name.replace("models/", "")

                    # Skip non-generative models
                    if "generateContent" not in model_data.get("supportedGenerationMethods", []):
                        continue

                    tier = GEMINI_MODELS.get(model_id, ModelTier.BALANCED)
                    context_length = MODEL_CONTEXT_LENGTHS.get(model_id, 32768)

                    capabilities = ["chat", "completion"]
                    if "embed" in model_id.lower():
                        capabilities = ["embedding"]

                    models.append(
                        ModelInfo(
                            id=model_id,
                            name=model_data.get("displayName", model_id),
                            tier=tier,
                            context_length=context_length,
                            capabilities=capabilities,
                            metadata=model_data,
                        )
                    )

                return models

        except aiohttp.ClientError as e:
            logger.error(f"Error listing Google AI models: {e}")
            return []

    def _parse_gemini_response(
        self,
        data: Dict[str, Any],
        model: str,
        latency_ms: float,
    ) -> LLMResponse:
        """Parse Gemini's candidates/parts response format."""
        candidates = data.get("candidates", [])
        content = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)

        finish_reason = candidates[0].get("finishReason") if candidates else None
        usage_metadata = data.get("usageMetadata", {})

        return LLMResponse(
            content=content.strip(),
            model=model,
            finish_reason=finish_reason,
            usage={
                "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                "total_tokens": usage_metadata.get("totalTokenCount", 0),
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
            raise LLMConnectionError("Google", self.base_url)

        model = model or self.default_model

        # Build contents array
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System: {system_prompt}"}]})
            contents.append(
                {
                    "role": "model",
                    "parts": [{"text": "Understood. I will follow these instructions."}],
                }
            )

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        start_time = time.time()

        try:
            async with self._session.post(
                f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
                json=payload,
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status != 200:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text)

                data = await response.json()
                return self._parse_gemini_response(data, model, latency_ms)

        except aiohttp.ClientError as e:
            raise LLMConnectionError("Google", self.base_url, cause=e)

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
            raise LLMConnectionError("Google", self.base_url)

        model = model or self.default_model

        # Convert messages to Gemini format
        contents = []
        system_instruction = None

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            else:
                role = "model" if msg.role == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": msg.content}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        start_time = time.time()

        try:
            async with self._session.post(
                f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
                json=payload,
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status != 200:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text)

                data = await response.json()
                return self._parse_gemini_response(data, model, latency_ms)

        except aiohttp.ClientError as e:
            raise LLMConnectionError("Google", self.base_url, cause=e)

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Generate embeddings."""
        if not self._is_connected:
            raise LLMConnectionError("Google", self.base_url)

        model = model or "text-embedding-004"

        payload = {"model": f"models/{model}", "content": {"parts": [{"text": text}]}}

        try:
            async with self._session.post(
                f"{self.base_url}/models/{model}:embedContent?key={self.api_key}",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text)

                data = await response.json()
                return data.get("embedding", {}).get("values", [])

        except aiohttp.ClientError as e:
            raise LLMConnectionError("Google", self.base_url, cause=e)

    async def health_check(self) -> bool:
        """Check API health."""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10.0),
                )

            async with self._session.get(f"{self.base_url}/models?key={self.api_key}") as response:
                return response.status == 200

        except Exception as e:
            logger.debug(f"Google health check failed: {e}")
            return False
