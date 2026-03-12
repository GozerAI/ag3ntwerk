"""
Prometheus-style metrics collection for ag3ntwerk.

Provides metrics collection compatible with Prometheus exposition format.
Can be used standalone or exported via /metrics endpoint.
"""

import inspect
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class MetricType(Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricLabels:
    """Labels for a metric."""

    labels: Dict[str, str] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.labels.items())))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MetricLabels):
            return False
        return self.labels == other.labels

    def to_prometheus(self) -> str:
        """Convert labels to Prometheus format."""
        if not self.labels:
            return ""
        parts = [f'{k}="{v}"' for k, v in sorted(self.labels.items())]
        return "{" + ",".join(parts) + "}"


class Counter:
    """
    A monotonically increasing counter.

    Counters track things like requests processed, errors encountered, etc.

    Usage:
        counter = Counter(
            name="http_requests_total",
            description="Total HTTP requests",
            labels=["method", "status"],
        )

        # Increment by 1
        counter.inc(method="GET", status="200")

        # Increment by N
        counter.inc(5, method="POST", status="201")
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[MetricLabels, float] = {}
        self._lock = Lock()

    def inc(self, value: float = 1.0, **labels: str) -> None:
        """Increment the counter."""
        if value < 0:
            raise ValueError("Counter can only be incremented")

        self._validate_labels(labels)
        key = MetricLabels(labels)

        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value

    def get(self, **labels: str) -> float:
        """Get the current counter value."""
        key = MetricLabels(labels)
        with self._lock:
            return self._values.get(key, 0.0)

    def _validate_labels(self, labels: Dict[str, str]) -> None:
        """Validate that provided labels match expected labels."""
        provided = set(labels.keys())
        expected = set(self.label_names)
        if provided != expected:
            raise ValueError(f"Labels mismatch: expected {expected}, got {provided}")

    def collect(self) -> List[Tuple[Dict[str, str], float]]:
        """Collect all metric values."""
        with self._lock:
            return [(lbl.labels, val) for lbl, val in self._values.items()]


class Gauge:
    """
    A metric that can go up and down.

    Gauges track things like current queue size, memory usage, etc.

    Usage:
        gauge = Gauge(
            name="queue_size",
            description="Current queue size",
            labels=["queue_name"],
        )

        gauge.set(42, queue_name="tasks")
        gauge.inc(1, queue_name="tasks")
        gauge.dec(1, queue_name="tasks")
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[MetricLabels, float] = {}
        self._lock = Lock()

    def set(self, value: float, **labels: str) -> None:
        """Set the gauge to a specific value."""
        self._validate_labels(labels)
        key = MetricLabels(labels)

        with self._lock:
            self._values[key] = value

    def inc(self, value: float = 1.0, **labels: str) -> None:
        """Increment the gauge."""
        self._validate_labels(labels)
        key = MetricLabels(labels)

        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value

    def dec(self, value: float = 1.0, **labels: str) -> None:
        """Decrement the gauge."""
        self._validate_labels(labels)
        key = MetricLabels(labels)

        with self._lock:
            self._values[key] = self._values.get(key, 0.0) - value

    def get(self, **labels: str) -> float:
        """Get the current gauge value."""
        key = MetricLabels(labels)
        with self._lock:
            return self._values.get(key, 0.0)

    def _validate_labels(self, labels: Dict[str, str]) -> None:
        """Validate that provided labels match expected labels."""
        provided = set(labels.keys())
        expected = set(self.label_names)
        if provided != expected:
            raise ValueError(f"Labels mismatch: expected {expected}, got {provided}")

    def collect(self) -> List[Tuple[Dict[str, str], float]]:
        """Collect all metric values."""
        with self._lock:
            return [(lbl.labels, val) for lbl, val in self._values.items()]


class Histogram:
    """
    A histogram samples observations and counts them in buckets.

    Histograms track things like request durations, response sizes, etc.

    Usage:
        histogram = Histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration",
            labels=["method"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
        )

        histogram.observe(0.123, method="GET")
    """

    # Default buckets following Prometheus conventions
    DEFAULT_BUCKETS = (
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
        float("inf"),
    )

    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        buckets: Optional[Tuple[float, ...]] = None,
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = buckets or self.DEFAULT_BUCKETS

        # Ensure inf bucket exists
        if float("inf") not in self.buckets:
            self.buckets = tuple(self.buckets) + (float("inf"),)

        self._bucket_counts: Dict[MetricLabels, Dict[float, int]] = {}
        self._sums: Dict[MetricLabels, float] = {}
        self._counts: Dict[MetricLabels, int] = {}
        self._lock = Lock()

    def observe(self, value: float, **labels: str) -> None:
        """Observe a value."""
        self._validate_labels(labels)
        key = MetricLabels(labels)

        with self._lock:
            # Initialize if needed
            if key not in self._bucket_counts:
                self._bucket_counts[key] = {b: 0 for b in self.buckets}
                self._sums[key] = 0.0
                self._counts[key] = 0

            # Update buckets
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[key][bucket] += 1

            # Update sum and count
            self._sums[key] += value
            self._counts[key] += 1

    def time(self, **labels: str) -> "HistogramTimer":
        """Return a timer context manager for observing duration."""
        return HistogramTimer(self, labels)

    def _validate_labels(self, labels: Dict[str, str]) -> None:
        """Validate that provided labels match expected labels."""
        provided = set(labels.keys())
        expected = set(self.label_names)
        if provided != expected:
            raise ValueError(f"Labels mismatch: expected {expected}, got {provided}")

    def collect(self) -> Dict[str, Any]:
        """Collect all histogram data."""
        with self._lock:
            result = {}
            for key in self._bucket_counts:
                label_str = str(key.labels) if key.labels else "default"
                result[label_str] = {
                    "buckets": dict(self._bucket_counts[key]),
                    "sum": self._sums.get(key, 0.0),
                    "count": self._counts.get(key, 0),
                }
            return result


class HistogramTimer:
    """Context manager for timing operations with a histogram."""

    def __init__(self, histogram: Histogram, labels: Dict[str, str]):
        self.histogram = histogram
        self.labels = labels
        self.start_time: Optional[float] = None

    def __enter__(self) -> "HistogramTimer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time is not None:
            duration = time.perf_counter() - self.start_time
            self.histogram.observe(duration, **self.labels)


class MetricsCollector:
    """
    Central metrics collection and registry.

    Manages all metrics and provides Prometheus exposition format export.

    Usage:
        collector = MetricsCollector(namespace="ag3ntwerk")

        # Register metrics
        requests = collector.counter(
            "http_requests_total",
            "Total HTTP requests",
            labels=["method", "status"],
        )

        # Use metrics
        requests.inc(method="GET", status="200")

        # Export for Prometheus
        output = collector.export_prometheus()
    """

    def __init__(
        self,
        namespace: str = "ag3ntwerk",
        subsystem: str = "",
    ):
        """
        Initialize metrics collector.

        Args:
            namespace: Prefix for all metric names
            subsystem: Subsystem name (inserted between namespace and name)
        """
        self.namespace = namespace
        self.subsystem = subsystem
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = Lock()

        # Built-in metrics
        self._setup_builtin_metrics()

    def _format_name(self, name: str) -> str:
        """Format metric name with namespace and subsystem."""
        parts = [self.namespace]
        if self.subsystem:
            parts.append(self.subsystem)
        parts.append(name)
        return "_".join(parts)

    def _setup_builtin_metrics(self) -> None:
        """Setup built-in system metrics."""
        # Process info gauge
        self._info_gauge = self.gauge(
            "info",
            "ag3ntwerk process information",
            labels=["version", "python_version"],
        )

        # Uptime gauge
        self._start_time = time.time()
        self._uptime_gauge = self.gauge(
            "uptime_seconds",
            "Process uptime in seconds",
        )

    def counter(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
    ) -> Counter:
        """Create or get a counter metric."""
        full_name = self._format_name(name)

        with self._lock:
            if full_name not in self._counters:
                self._counters[full_name] = Counter(
                    name=full_name,
                    description=description,
                    labels=labels,
                )
            return self._counters[full_name]

    def gauge(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
    ) -> Gauge:
        """Create or get a gauge metric."""
        full_name = self._format_name(name)

        with self._lock:
            if full_name not in self._gauges:
                self._gauges[full_name] = Gauge(
                    name=full_name,
                    description=description,
                    labels=labels,
                )
            return self._gauges[full_name]

    def histogram(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        buckets: Optional[Tuple[float, ...]] = None,
    ) -> Histogram:
        """Create or get a histogram metric."""
        full_name = self._format_name(name)

        with self._lock:
            if full_name not in self._histograms:
                self._histograms[full_name] = Histogram(
                    name=full_name,
                    description=description,
                    labels=labels,
                    buckets=buckets,
                )
            return self._histograms[full_name]

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus exposition format."""
        lines: List[str] = []

        # Update uptime
        self._uptime_gauge.set(time.time() - self._start_time)

        # Export counters
        for name, counter in self._counters.items():
            lines.append(f"# HELP {name} {counter.description}")
            lines.append(f"# TYPE {name} counter")
            for labels, value in counter.collect():
                label_str = MetricLabels(labels).to_prometheus()
                lines.append(f"{name}{label_str} {value}")

        # Export gauges
        for name, gauge in self._gauges.items():
            lines.append(f"# HELP {name} {gauge.description}")
            lines.append(f"# TYPE {name} gauge")
            for labels, value in gauge.collect():
                label_str = MetricLabels(labels).to_prometheus()
                lines.append(f"{name}{label_str} {value}")

        # Export histograms
        for name, histogram in self._histograms.items():
            lines.append(f"# HELP {name} {histogram.description}")
            lines.append(f"# TYPE {name} histogram")

            for label_group, data in histogram.collect().items():
                base_labels = eval(label_group) if label_group != "default" else {}

                # Bucket values
                cumulative = 0
                for bucket, count in sorted(data["buckets"].items()):
                    cumulative = count  # Already cumulative from observe()
                    bucket_labels = {**base_labels, "le": str(bucket)}
                    label_str = MetricLabels(bucket_labels).to_prometheus()
                    lines.append(f"{name}_bucket{label_str} {cumulative}")

                # Sum and count
                base_label_str = MetricLabels(base_labels).to_prometheus()
                lines.append(f"{name}_sum{base_label_str} {data['sum']}")
                lines.append(f"{name}_count{base_label_str} {data['count']}")

        return "\n".join(lines)

    def export_json(self) -> Dict[str, Any]:
        """Export all metrics as JSON."""
        # Update uptime
        self._uptime_gauge.set(time.time() - self._start_time)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "counters": {
                name: {
                    "description": counter.description,
                    "values": [
                        {"labels": labels, "value": value} for labels, value in counter.collect()
                    ],
                }
                for name, counter in self._counters.items()
            },
            "gauges": {
                name: {
                    "description": gauge.description,
                    "values": [
                        {"labels": labels, "value": value} for labels, value in gauge.collect()
                    ],
                }
                for name, gauge in self._gauges.items()
            },
            "histograms": {
                name: {
                    "description": histogram.description,
                    "values": histogram.collect(),
                }
                for name, histogram in self._histograms.items()
            },
        }


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# Convenience decorators


def count_calls(
    counter: Counter,
    labels_fn: Optional[Callable[..., Dict[str, str]]] = None,
) -> Callable[[F], F]:
    """Decorator to count function calls."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            labels = labels_fn(*args, **kwargs) if labels_fn else {}
            counter.inc(**labels)
            return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            labels = labels_fn(*args, **kwargs) if labels_fn else {}
            counter.inc(**labels)
            return await func(*args, **kwargs)

        import asyncio

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore

    return decorator


def time_calls(
    histogram: Histogram,
    labels_fn: Optional[Callable[..., Dict[str, str]]] = None,
) -> Callable[[F], F]:
    """Decorator to time function calls."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            labels = labels_fn(*args, **kwargs) if labels_fn else {}
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                histogram.observe(duration, **labels)

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            labels = labels_fn(*args, **kwargs) if labels_fn else {}
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                histogram.observe(duration, **labels)

        import asyncio

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore

    return decorator
