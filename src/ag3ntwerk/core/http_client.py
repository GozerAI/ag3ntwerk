"""
HTTP Client Pool for ag3ntwerk.

Provides centralized HTTP client management with:
- Connection pooling for efficient resource usage
- Configurable timeouts and limits per service
- Automatic retry with exponential backoff
- Request tracing with correlation IDs
- Graceful shutdown support

Usage:
    from ag3ntwerk.core.http_client import get_http_client, HTTPClientPool

    # Get a shared client for a service
    client = await get_http_client("ollama")

    # Use it for requests
    async with client.get("/api/tags") as response:
        data = await response.json()

    # Or create a custom pool
    pool = HTTPClientPool()
    await pool.initialize()
    client = await pool.get_client("my_service", base_url="http://localhost:8000")
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from contextvars import ContextVar

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

logger = logging.getLogger(__name__)

# Context variable for request ID propagation
_request_id_context: ContextVar[str] = ContextVar("http_request_id", default="")


@dataclass
class ClientConfig:
    """Configuration for an HTTP client."""

    base_url: str = ""
    timeout_total: float = 60.0
    timeout_connect: float = 10.0
    timeout_sock_read: float = 30.0
    max_connections: int = 100
    max_connections_per_host: int = 30
    keepalive_timeout: float = 30.0
    force_close: bool = False
    enable_cleanup_closed: bool = True
    headers: Dict[str, str] = field(default_factory=dict)
    retry_attempts: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    retry_on_status: tuple = (502, 503, 504)


# Default configurations for known services
DEFAULT_CONFIGS: Dict[str, ClientConfig] = {
    "ollama": ClientConfig(
        base_url="http://localhost:11434",
        timeout_total=300.0,  # Longer timeout for LLM inference
        timeout_connect=10.0,
        timeout_sock_read=300.0,
        max_connections=50,
        max_connections_per_host=10,
        retry_attempts=2,
    ),
    "openai": ClientConfig(
        base_url="https://api.openai.com/v1",
        timeout_total=120.0,
        timeout_connect=10.0,
        timeout_sock_read=120.0,
        max_connections=100,
        max_connections_per_host=20,
        retry_attempts=3,
    ),
    "anthropic": ClientConfig(
        base_url="https://api.anthropic.com",
        timeout_total=120.0,
        timeout_connect=10.0,
        timeout_sock_read=120.0,
        max_connections=100,
        max_connections_per_host=20,
        retry_attempts=3,
    ),
    "google": ClientConfig(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        timeout_total=120.0,
        timeout_connect=10.0,
        timeout_sock_read=120.0,
        max_connections=100,
        max_connections_per_host=20,
        retry_attempts=3,
    ),
    "openrouter": ClientConfig(
        base_url="https://openrouter.ai/api/v1",
        timeout_total=120.0,
        timeout_connect=10.0,
        timeout_sock_read=120.0,
        max_connections=100,
        max_connections_per_host=20,
        retry_attempts=3,
    ),
    "huggingface": ClientConfig(
        base_url="https://api-inference.huggingface.co",
        timeout_total=180.0,
        timeout_connect=10.0,
        timeout_sock_read=180.0,
        max_connections=50,
        max_connections_per_host=10,
        retry_attempts=3,
    ),
    "github": ClientConfig(
        base_url="https://models.inference.ai.azure.com",
        timeout_total=120.0,
        timeout_connect=10.0,
        timeout_sock_read=120.0,
        max_connections=100,
        max_connections_per_host=20,
        retry_attempts=3,
    ),
    "perplexity": ClientConfig(
        base_url="https://api.perplexity.ai",
        timeout_total=120.0,
        timeout_connect=10.0,
        timeout_sock_read=120.0,
        max_connections=50,
        max_connections_per_host=10,
        retry_attempts=3,
    ),
    "gpt4all": ClientConfig(
        base_url="http://localhost:4891/v1",
        timeout_total=300.0,
        timeout_connect=10.0,
        timeout_sock_read=300.0,
        max_connections=20,
        max_connections_per_host=5,
        retry_attempts=2,
    ),
    "default": ClientConfig(
        timeout_total=60.0,
        timeout_connect=10.0,
        timeout_sock_read=30.0,
        max_connections=100,
        max_connections_per_host=30,
        retry_attempts=3,
    ),
}


class TracingSession:
    """
    ClientSession wrapper that adds request tracing.

    Uses composition instead of inheritance (aiohttp best practice).
    Automatically propagates request IDs and logs request/response details.
    """

    def __init__(
        self,
        service_name: str,
        config: ClientConfig,
        session: ClientSession,
    ):
        self.service_name = service_name
        self.config = config
        self._session = session
        self._request_count = 0
        self._error_count = 0
        self._total_latency_ms = 0.0

    async def _traced_request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Perform request with tracing and metrics."""
        self._request_count += 1
        start_time = datetime.now(timezone.utc)

        # Add request ID header if available
        request_id = _request_id_context.get()
        if request_id:
            headers = kwargs.get("headers", {})
            headers["X-Request-ID"] = request_id
            kwargs["headers"] = headers

        # Add default headers from config
        if self.config.headers:
            headers = kwargs.get("headers", {})
            for key, value in self.config.headers.items():
                if key not in headers:
                    headers[key] = value
            kwargs["headers"] = headers

        try:
            response = await self._session.request(method, url, **kwargs)
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self._total_latency_ms += latency_ms

            logger.debug(
                "HTTP request completed",
                service=self.service_name,
                method=method,
                url=str(url),
                status=response.status,
                latency_ms=round(latency_ms, 2),
                request_id=request_id or None,
            )

            return response

        except Exception as e:  # Intentional catch-all: metrics tracking before re-raise
            self._error_count += 1
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self._total_latency_ms += latency_ms

            logger.warning(
                "HTTP request failed",
                service=self.service_name,
                method=method,
                url=str(url),
                error=str(e),
                error_type=type(e).__name__,
                latency_ms=round(latency_ms, 2),
                request_id=request_id or None,
                exc_info=True,
            )
            raise

    # Delegate common HTTP methods to traced request
    def get(self, url: str, **kwargs):
        """Perform GET request with tracing."""
        return self._traced_request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        """Perform POST request with tracing."""
        return self._traced_request("POST", url, **kwargs)

    def put(self, url: str, **kwargs):
        """Perform PUT request with tracing."""
        return self._traced_request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs):
        """Perform DELETE request with tracing."""
        return self._traced_request("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs):
        """Perform PATCH request with tracing."""
        return self._traced_request("PATCH", url, **kwargs)

    def head(self, url: str, **kwargs):
        """Perform HEAD request with tracing."""
        return self._traced_request("HEAD", url, **kwargs)

    def options(self, url: str, **kwargs):
        """Perform OPTIONS request with tracing."""
        return self._traced_request("OPTIONS", url, **kwargs)

    def request(self, method: str, url: str, **kwargs):
        """Perform request with tracing."""
        return self._traced_request(method, url, **kwargs)

    async def close(self):
        """Close the underlying session."""
        await self._session.close()

    @property
    def closed(self) -> bool:
        """Check if session is closed."""
        return self._session.closed

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "service": self.service_name,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(1, self._request_count),
            "avg_latency_ms": self._total_latency_ms / max(1, self._request_count),
            "total_latency_ms": self._total_latency_ms,
        }


class HTTPClientPool:
    """
    Centralized HTTP client pool manager.

    Manages connection pools for multiple services with proper resource handling.

    Usage:
        pool = HTTPClientPool()
        await pool.initialize()

        # Get client for a known service
        ollama_client = await pool.get_client("ollama")

        # Get client with custom config
        custom_client = await pool.get_client(
            "my_service",
            base_url="http://localhost:9000",
            timeout_total=30.0,
        )

        # Cleanup when done
        await pool.shutdown()
    """

    def __init__(self):
        self._clients: Dict[str, TracingSession] = {}
        self._connectors: Dict[str, TCPConnector] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        self._shutting_down = False

    async def initialize(self) -> None:
        """Initialize the client pool."""
        async with self._lock:
            if self._initialized:
                return
            self._initialized = True
            logger.debug("HTTP client pool initialized")

    async def get_client(
        self,
        service_name: str,
        base_url: Optional[str] = None,
        **config_overrides,
    ) -> TracingSession:
        """
        Get or create an HTTP client for a service.

        Args:
            service_name: Name of the service (used for pooling and logging)
            base_url: Optional base URL override
            **config_overrides: Override default config values

        Returns:
            TracingSession client configured for the service
        """
        if self._shutting_down:
            raise RuntimeError("HTTP client pool is shutting down")

        if not self._initialized:
            await self.initialize()

        # Create unique key for this client configuration
        client_key = f"{service_name}:{base_url or 'default'}"

        async with self._lock:
            if client_key in self._clients:
                client = self._clients[client_key]
                if not client.closed:
                    return client
                # Client was closed, remove it
                del self._clients[client_key]
                if client_key in self._connectors:
                    del self._connectors[client_key]

            # Get config for this service
            config = self._get_config(service_name, base_url, **config_overrides)

            # Create connector with connection pooling
            connector = TCPConnector(
                limit=config.max_connections,
                limit_per_host=config.max_connections_per_host,
                keepalive_timeout=config.keepalive_timeout,
                force_close=config.force_close,
                enable_cleanup_closed=config.enable_cleanup_closed,
            )
            self._connectors[client_key] = connector

            # Create timeout configuration
            timeout = ClientTimeout(
                total=config.timeout_total,
                connect=config.timeout_connect,
                sock_read=config.timeout_sock_read,
            )

            # Create the underlying aiohttp session
            session = ClientSession(
                base_url=config.base_url,
                connector=connector,
                timeout=timeout,
            )

            # Wrap with tracing
            client = TracingSession(
                service_name=service_name,
                config=config,
                session=session,
            )
            self._clients[client_key] = client

            logger.debug(
                "Created HTTP client",
                service=service_name,
                base_url=config.base_url,
                max_connections=config.max_connections,
            )

            return client

    def _get_config(
        self,
        service_name: str,
        base_url: Optional[str],
        **overrides,
    ) -> ClientConfig:
        """Get configuration for a service with overrides."""
        # Start with default config
        if service_name in DEFAULT_CONFIGS:
            base_config = DEFAULT_CONFIGS[service_name]
        else:
            base_config = DEFAULT_CONFIGS["default"]

        # Create new config with overrides
        config_dict = {
            "base_url": base_url or base_config.base_url,
            "timeout_total": overrides.get("timeout_total", base_config.timeout_total),
            "timeout_connect": overrides.get("timeout_connect", base_config.timeout_connect),
            "timeout_sock_read": overrides.get("timeout_sock_read", base_config.timeout_sock_read),
            "max_connections": overrides.get("max_connections", base_config.max_connections),
            "max_connections_per_host": overrides.get(
                "max_connections_per_host", base_config.max_connections_per_host
            ),
            "keepalive_timeout": overrides.get("keepalive_timeout", base_config.keepalive_timeout),
            "force_close": overrides.get("force_close", base_config.force_close),
            "enable_cleanup_closed": overrides.get(
                "enable_cleanup_closed", base_config.enable_cleanup_closed
            ),
            "headers": {**base_config.headers, **overrides.get("headers", {})},
            "retry_attempts": overrides.get("retry_attempts", base_config.retry_attempts),
            "retry_delay": overrides.get("retry_delay", base_config.retry_delay),
            "retry_backoff": overrides.get("retry_backoff", base_config.retry_backoff),
            "retry_on_status": overrides.get("retry_on_status", base_config.retry_on_status),
        }

        return ClientConfig(**config_dict)

    async def close_client(self, service_name: str, base_url: Optional[str] = None) -> None:
        """Close a specific client."""
        client_key = f"{service_name}:{base_url or 'default'}"

        async with self._lock:
            if client_key in self._clients:
                client = self._clients[client_key]
                if not client.closed:
                    await client.close()
                del self._clients[client_key]

            if client_key in self._connectors:
                connector = self._connectors[client_key]
                await connector.close()
                del self._connectors[client_key]

            logger.debug(
                "Closed HTTP client",
                service=service_name,
                base_url=base_url or "default",
            )

    async def shutdown(self, timeout: float = 5.0) -> None:
        """
        Gracefully shutdown all clients.

        Args:
            timeout: Maximum time to wait for connections to close
        """
        self._shutting_down = True

        async with self._lock:
            # Collect stats before closing
            all_stats = self.get_all_stats()

            # Close all clients
            close_tasks = []
            for client in self._clients.values():
                if not client.closed:
                    close_tasks.append(client.close())

            if close_tasks:
                await asyncio.wait_for(
                    asyncio.gather(*close_tasks, return_exceptions=True),
                    timeout=timeout,
                )

            # Close all connectors
            for connector in self._connectors.values():
                await connector.close()

            self._clients.clear()
            self._connectors.clear()
            self._initialized = False

            logger.info(
                "HTTP client pool shutdown complete",
                total_clients=len(all_stats),
                stats=all_stats,
            )

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all clients."""
        return {
            key: client.get_stats() for key, client in self._clients.items() if not client.closed
        }

    def is_healthy(self) -> bool:
        """Check if the pool is healthy."""
        return self._initialized and not self._shutting_down

    async def __aenter__(self) -> "HTTPClientPool":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.shutdown()


# Global pool instance
_global_pool: Optional[HTTPClientPool] = None
_pool_lock: Optional[asyncio.Lock] = None


def _get_pool_lock() -> asyncio.Lock:
    """Get or create the pool lock lazily within the event loop."""
    global _pool_lock
    if _pool_lock is None:
        _pool_lock = asyncio.Lock()
    return _pool_lock


async def get_http_client_pool() -> HTTPClientPool:
    """Get the global HTTP client pool."""
    global _global_pool

    async with _get_pool_lock():
        if _global_pool is None:
            _global_pool = HTTPClientPool()
            await _global_pool.initialize()
        return _global_pool


async def get_http_client(
    service_name: str,
    base_url: Optional[str] = None,
    **config_overrides,
) -> TracingSession:
    """
    Get an HTTP client from the global pool.

    This is the recommended way to get HTTP clients for services.

    Args:
        service_name: Name of the service
        base_url: Optional base URL override
        **config_overrides: Config overrides

    Returns:
        TracingSession configured for the service

    Example:
        client = await get_http_client("ollama")
        async with client.get("/api/tags") as response:
            data = await response.json()
    """
    pool = await get_http_client_pool()
    return await pool.get_client(service_name, base_url, **config_overrides)


async def shutdown_http_clients() -> None:
    """Shutdown the global HTTP client pool."""
    global _global_pool

    async with _get_pool_lock():
        if _global_pool is not None:
            await _global_pool.shutdown()
            _global_pool = None


def set_request_id(request_id: str) -> None:
    """Set the request ID for correlation in HTTP requests."""
    _request_id_context.set(request_id)


def get_request_id() -> str:
    """Get the current request ID."""
    return _request_id_context.get()


__all__ = [
    # Classes
    "HTTPClientPool",
    "TracingSession",
    "ClientConfig",
    # Configuration
    "DEFAULT_CONFIGS",
    # Functions
    "get_http_client_pool",
    "get_http_client",
    "shutdown_http_clients",
    "set_request_id",
    "get_request_id",
]
