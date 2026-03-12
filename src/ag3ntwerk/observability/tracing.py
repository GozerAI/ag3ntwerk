"""
OpenTelemetry-compatible tracing for ag3ntwerk.

Provides distributed tracing capabilities for tracking request flow
across agents and services.
"""

import asyncio
import functools
import logging
import os
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class SpanKind(Enum):
    """Type of span."""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(Enum):
    """Status of a span."""

    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    """Context for a span, enabling distributed tracing."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 1  # 1 = sampled
    trace_state: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def generate(cls, parent: Optional["SpanContext"] = None) -> "SpanContext":
        """Generate a new span context."""
        trace_id = parent.trace_id if parent else uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        parent_span_id = parent.span_id if parent else None

        return cls(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_flags": self.trace_flags,
        }


@dataclass
class SpanEvent:
    """An event that occurred during a span."""

    name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """
    A span represents a single operation within a trace.

    Spans can be nested to represent hierarchical operations.
    """

    name: str
    context: SpanContext
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanContext] = field(default_factory=list)

    _start_perf: float = field(default_factory=time.perf_counter, repr=False)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the span."""
        self.attributes[key] = value

    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        """Set multiple attributes."""
        self.attributes.update(attributes)

    def add_event(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an event to the span."""
        self.events.append(
            SpanEvent(
                name=name,
                attributes=attributes or {},
            )
        )

    def set_status(self, status: SpanStatus, description: str = "") -> None:
        """Set the span status."""
        self.status = status
        if description:
            self.attributes["status.description"] = description

    def record_exception(self, exception: Exception) -> None:
        """Record an exception on the span."""
        self.set_status(SpanStatus.ERROR, str(exception))
        self.add_event(
            "exception",
            attributes={
                "exception.type": type(exception).__name__,
                "exception.message": str(exception),
            },
        )

    def end(self, end_time: Optional[datetime] = None) -> None:
        """End the span."""
        self.end_time = end_time or datetime.now(timezone.utc)

        if self.status == SpanStatus.UNSET:
            self.status = SpanStatus.OK

    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        if self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return (time.perf_counter() - self._start_perf) * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for export."""
        return {
            "name": self.name,
            "context": self.context.to_dict(),
            "kind": self.kind.value,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": [
                {
                    "name": e.name,
                    "timestamp": e.timestamp.isoformat(),
                    "attributes": e.attributes,
                }
                for e in self.events
            ],
            "links": [link.to_dict() for link in self.links],
        }


# Context variable for current span
_current_span: ContextVar[Optional[Span]] = ContextVar("current_span", default=None)


class Tracer:
    """
    Creates and manages spans for a named instrumentation scope.

    Usage:
        tracer = Tracer("ag3ntwerk.agents")

        with tracer.start_span("process_task") as span:
            span.set_attribute("task.type", "analysis")
            # Do work...
    """

    def __init__(
        self,
        name: str,
        version: str = "0.1.0",
        exporter: Optional["SpanExporter"] = None,
    ):
        """
        Initialize tracer.

        Args:
            name: Instrumentation scope name
            version: Version of the instrumentation
            exporter: Optional span exporter
        """
        self.name = name
        self.version = version
        self.exporter = exporter
        self._spans: List[Span] = []

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        links: Optional[List[SpanContext]] = None,
    ) -> "SpanContextManager":
        """Start a new span."""
        parent = _current_span.get()
        parent_context = parent.context if parent else None

        context = SpanContext.generate(parent_context)

        span = Span(
            name=name,
            context=context,
            kind=kind,
            attributes=attributes or {},
            links=links or [],
        )

        # Add instrumentation info
        span.set_attributes(
            {
                "otel.library.name": self.name,
                "otel.library.version": self.version,
            }
        )

        return SpanContextManager(self, span)

    def _record_span(self, span: Span) -> None:
        """Record a completed span."""
        self._spans.append(span)

        if self.exporter:
            self.exporter.export([span])

    def get_recent_spans(self, limit: int = 100) -> List[Span]:
        """Get recent spans."""
        return self._spans[-limit:]

    def clear_spans(self) -> None:
        """Clear recorded spans."""
        self._spans.clear()


class SpanContextManager:
    """Context manager for spans."""

    def __init__(self, tracer: Tracer, span: Span):
        self.tracer = tracer
        self.span = span
        self._token: Optional[Any] = None

    def __enter__(self) -> Span:
        self._token = _current_span.set(self.span)
        return self.span

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Any,
    ) -> None:
        if exc_val:
            self.span.record_exception(exc_val)

        self.span.end()
        self.tracer._record_span(self.span)

        if self._token:
            _current_span.reset(self._token)

    async def __aenter__(self) -> Span:
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Any,
    ) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)


class SpanExporter:
    """Base class for span exporters."""

    def export(self, spans: List[Span]) -> None:
        """Export spans."""
        raise NotImplementedError

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        pass


class ConsoleSpanExporter(SpanExporter):
    """Exports spans to console for debugging."""

    def export(self, spans: List[Span]) -> None:
        """Export spans to console."""
        for span in spans:
            duration = span.duration_ms
            status = span.status.value
            logger.info(
                f"[TRACE] {span.name} ({status}) - {duration:.2f}ms "
                f"[trace_id={span.context.trace_id[:8]}]"
            )


class JSONFileSpanExporter(SpanExporter):
    """Exports spans to a JSON file."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

    def export(self, spans: List[Span]) -> None:
        """Export spans to JSON file."""
        import json

        with open(self.file_path, "a") as f:
            for span in spans:
                f.write(json.dumps(span.to_dict()) + "\n")


class TracingManager:
    """
    Central tracing management.

    Provides a singleton interface for tracing across the application.

    Usage:
        manager = TracingManager()
        manager.configure(
            service_name="ag3ntwerk",
            exporter=ConsoleSpanExporter(),
        )

        tracer = manager.get_tracer("ag3ntwerk.api")

        with tracer.start_span("handle_request") as span:
            # Process request
            pass
    """

    def __init__(self):
        self._tracers: Dict[str, Tracer] = {}
        self._exporter: Optional[SpanExporter] = None
        self._service_name: str = "ag3ntwerk"
        self._enabled: bool = True

    def configure(
        self,
        service_name: str = "ag3ntwerk",
        exporter: Optional[SpanExporter] = None,
        enabled: bool = True,
    ) -> None:
        """
        Configure the tracing manager.

        Args:
            service_name: Name of the service for tracing
            exporter: Span exporter to use
            enabled: Whether tracing is enabled
        """
        self._service_name = service_name
        self._exporter = exporter
        self._enabled = enabled

    def get_tracer(self, name: str, version: str = "0.1.0") -> Tracer:
        """Get or create a tracer."""
        if name not in self._tracers:
            self._tracers[name] = Tracer(
                name=name,
                version=version,
                exporter=self._exporter if self._enabled else None,
            )
        return self._tracers[name]

    def get_current_span(self) -> Optional[Span]:
        """Get the current active span."""
        return _current_span.get()

    def shutdown(self) -> None:
        """Shutdown all tracers and exporters."""
        if self._exporter:
            self._exporter.shutdown()


# Global tracing manager
_tracing_manager: Optional[TracingManager] = None


def get_tracing_manager() -> TracingManager:
    """Get the global tracing manager."""
    global _tracing_manager
    if _tracing_manager is None:
        _tracing_manager = TracingManager()
    return _tracing_manager


def get_tracer(name: str, version: str = "0.1.0") -> Tracer:
    """Get a tracer from the global manager."""
    return get_tracing_manager().get_tracer(name, version)


# Decorators for tracing


def trace_sync(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """Decorator to trace synchronous functions."""

    def decorator(func: F) -> F:
        span_name = name or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer(func.__module__)

            with tracer.start_span(span_name, kind=kind, attributes=attributes) as span:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    raise

        return wrapper  # type: ignore

    return decorator


def trace_async(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """Decorator to trace async functions."""

    def decorator(func: F) -> F:
        span_name = name or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer(func.__module__)

            async with tracer.start_span(span_name, kind=kind, attributes=attributes) as span:
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    raise

        return wrapper  # type: ignore

    return decorator


# OpenTelemetry context propagation (W3C Trace Context format)


def inject_context(
    carrier: Dict[str, str],
    context: Optional[SpanContext] = None,
) -> None:
    """Inject trace context into a carrier (e.g., HTTP headers)."""
    if context is None:
        span = _current_span.get()
        if span:
            context = span.context

    if context:
        # W3C Trace Context format
        traceparent = f"00-{context.trace_id}-{context.span_id}-" f"{context.trace_flags:02x}"
        carrier["traceparent"] = traceparent


def extract_context(carrier: Dict[str, str]) -> Optional[SpanContext]:
    """Extract trace context from a carrier (e.g., HTTP headers)."""
    traceparent = carrier.get("traceparent")

    if not traceparent:
        return None

    try:
        # Parse W3C Trace Context format: 00-traceid-spanid-flags
        parts = traceparent.split("-")
        if len(parts) != 4:
            return None

        version, trace_id, span_id, flags = parts

        return SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=int(flags, 16),
        )
    except (ValueError, IndexError):
        logger.warning("Failed to parse traceparent: %s", traceparent)
        return None
