"""
FastAPI middleware for observability integration.

Provides automatic metrics collection and tracing for API requests.
"""

import logging
import time
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ag3ntwerk.observability.metrics import (
    Counter,
    Histogram,
    MetricsCollector,
    get_metrics_collector,
)
from ag3ntwerk.observability.tracing import (
    SpanKind,
    Tracer,
    extract_context,
    get_tracer,
    inject_context,
)

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting HTTP request metrics.

    Automatically tracks:
    - Request count by method, path, and status
    - Request duration histogram
    - Request size histogram
    - Active requests gauge
    """

    def __init__(
        self,
        app: ASGIApp,
        collector: Optional[MetricsCollector] = None,
        exclude_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.collector = collector or get_metrics_collector()
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/favicon.ico"]

        # Setup metrics
        self.request_counter = self.collector.counter(
            "http_requests_total",
            "Total HTTP requests",
            labels=["method", "path", "status"],
        )

        self.request_duration = self.collector.histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            labels=["method", "path"],
        )

        self.active_requests = self.collector.gauge(
            "http_requests_active",
            "Number of active HTTP requests",
            labels=["method"],
        )

        self.request_size = self.collector.histogram(
            "http_request_size_bytes",
            "HTTP request size in bytes",
            labels=["method"],
        )

        self.response_size = self.collector.histogram(
            "http_response_size_bytes",
            "HTTP response size in bytes",
            labels=["method"],
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(ep) for ep in self.exclude_paths):
            return await call_next(request)

        method = request.method

        # Normalize path to prevent cardinality explosion
        normalized_path = self._normalize_path(path)

        # Track active requests
        self.active_requests.inc(method=method)

        # Track request size
        content_length = request.headers.get("content-length", "0")
        try:
            self.request_size.observe(int(content_length), method=method)
        except ValueError:
            pass

        start_time = time.perf_counter()

        try:
            response = await call_next(request)

            # Record metrics
            duration = time.perf_counter() - start_time
            status = str(response.status_code)

            self.request_counter.inc(
                method=method,
                path=normalized_path,
                status=status,
            )
            self.request_duration.observe(duration, method=method, path=normalized_path)

            # Track response size if available
            response_length = response.headers.get("content-length", "0")
            try:
                self.response_size.observe(int(response_length), method=method)
            except ValueError:
                pass

            return response

        except Exception as e:
            # Record error metrics
            duration = time.perf_counter() - start_time
            self.request_counter.inc(
                method=method,
                path=normalized_path,
                status="500",
            )
            self.request_duration.observe(duration, method=method, path=normalized_path)
            raise

        finally:
            self.active_requests.dec(method=method)

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path to prevent cardinality explosion.

        Replaces dynamic path segments with placeholders.
        """
        # Common patterns to normalize
        import re

        # UUIDs
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{uuid}",
            path,
            flags=re.IGNORECASE,
        )

        # Numeric IDs
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)

        # Task IDs (csk_ prefix)
        path = re.sub(r"/csk_[a-zA-Z0-9]+", "/{task_id}", path)

        return path


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for distributed tracing.

    Automatically creates spans for HTTP requests and propagates
    trace context across services.
    """

    def __init__(
        self,
        app: ASGIApp,
        tracer: Optional[Tracer] = None,
        exclude_paths: Optional[list] = None,
        service_name: str = "ag3ntwerk-api",
    ):
        super().__init__(app)
        self.tracer = tracer or get_tracer(service_name)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/favicon.ico"]
        self.service_name = service_name

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(ep) for ep in self.exclude_paths):
            return await call_next(request)

        method = request.method
        span_name = f"{method} {path}"

        # Extract trace context from incoming request
        parent_context = extract_context(dict(request.headers))

        # Create span
        async with self.tracer.start_span(
            span_name,
            kind=SpanKind.SERVER,
            attributes={
                "http.method": method,
                "http.url": str(request.url),
                "http.scheme": request.url.scheme,
                "http.host": request.url.hostname,
                "http.target": path,
                "http.user_agent": request.headers.get("user-agent", ""),
                "service.name": self.service_name,
            },
        ) as span:
            try:
                response = await call_next(request)

                span.set_attributes(
                    {
                        "http.status_code": response.status_code,
                        "http.response_content_length": response.headers.get("content-length", 0),
                    }
                )

                # Inject trace context into response headers
                response_headers = {}
                inject_context(response_headers, span.context)
                for key, value in response_headers.items():
                    response.headers[key] = value

                return response

            except Exception as e:
                span.record_exception(e)
                raise


def setup_observability(
    app: FastAPI,
    enable_metrics: bool = True,
    enable_tracing: bool = True,
    metrics_path: str = "/metrics",
    exclude_paths: Optional[list] = None,
) -> None:
    """
    Setup observability for a FastAPI application.

    Args:
        app: FastAPI application
        enable_metrics: Enable metrics collection
        enable_tracing: Enable distributed tracing
        metrics_path: Path to expose Prometheus metrics
        exclude_paths: Paths to exclude from metrics/tracing
    """
    exclude = exclude_paths or ["/health", "/metrics", "/favicon.ico"]

    if enable_metrics:
        # Add metrics middleware
        app.add_middleware(
            MetricsMiddleware,
            exclude_paths=exclude,
        )

        # Add metrics endpoint
        collector = get_metrics_collector()

        @app.get(metrics_path, include_in_schema=False)
        async def metrics() -> Response:
            content = collector.export_prometheus()
            return Response(
                content=content,
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )

    if enable_tracing:
        # Add tracing middleware
        app.add_middleware(
            TracingMiddleware,
            exclude_paths=exclude,
        )

    logger.info(f"Observability configured: metrics={enable_metrics}, tracing={enable_tracing}")
