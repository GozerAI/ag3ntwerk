"""
Observability infrastructure for ag3ntwerk.

This package provides:
- Prometheus metrics collection and export
- OpenTelemetry tracing integration
- Structured logging with correlation
- Performance monitoring
"""

from ag3ntwerk.observability.metrics import (
    MetricsCollector,
    Counter,
    Gauge,
    Histogram,
    get_metrics_collector,
)
from ag3ntwerk.observability.tracing import (
    TracingManager,
    get_tracer,
    trace_async,
    trace_sync,
)

__all__ = [
    # Metrics
    "MetricsCollector",
    "Counter",
    "Gauge",
    "Histogram",
    "get_metrics_collector",
    # Tracing
    "TracingManager",
    "get_tracer",
    "trace_async",
    "trace_sync",
]
