"""
Tests for the observability module.
"""

import asyncio
import pytest
import time

from ag3ntwerk.observability.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsCollector,
    MetricLabels,
)
from ag3ntwerk.observability.tracing import (
    Span,
    SpanContext,
    SpanKind,
    SpanStatus,
    Tracer,
    ConsoleSpanExporter,
    trace_sync,
    trace_async,
    inject_context,
    extract_context,
)


class TestCounter:
    """Tests for Counter metric."""

    def test_basic_increment(self):
        """Test basic counter increment."""
        counter = Counter("test_counter", "Test counter")

        counter.inc()
        assert counter.get() == 1.0

        counter.inc(5)
        assert counter.get() == 6.0

    def test_increment_with_labels(self):
        """Test counter increment with labels."""
        counter = Counter(
            "test_counter",
            "Test counter",
            labels=["method", "status"],
        )

        counter.inc(method="GET", status="200")
        counter.inc(method="GET", status="200")
        counter.inc(method="POST", status="201")

        assert counter.get(method="GET", status="200") == 2.0
        assert counter.get(method="POST", status="201") == 1.0
        assert counter.get(method="GET", status="404") == 0.0

    def test_negative_increment_raises(self):
        """Test that negative increment raises error."""
        counter = Counter("test_counter", "Test counter")

        with pytest.raises(ValueError):
            counter.inc(-1)

    def test_label_validation(self):
        """Test label validation."""
        counter = Counter(
            "test_counter",
            "Test counter",
            labels=["method"],
        )

        with pytest.raises(ValueError):
            counter.inc(wrong_label="value")

    def test_collect(self):
        """Test collecting counter values."""
        counter = Counter(
            "test_counter",
            "Test counter",
            labels=["type"],
        )

        counter.inc(type="a")
        counter.inc(2, type="b")

        values = counter.collect()
        assert len(values) == 2


class TestGauge:
    """Tests for Gauge metric."""

    def test_set_value(self):
        """Test setting gauge value."""
        gauge = Gauge("test_gauge", "Test gauge")

        gauge.set(42)
        assert gauge.get() == 42

        gauge.set(100)
        assert gauge.get() == 100

    def test_increment_decrement(self):
        """Test gauge increment and decrement."""
        gauge = Gauge("test_gauge", "Test gauge")

        gauge.set(10)
        gauge.inc(5)
        assert gauge.get() == 15

        gauge.dec(3)
        assert gauge.get() == 12

    def test_gauge_with_labels(self):
        """Test gauge with labels."""
        gauge = Gauge(
            "test_gauge",
            "Test gauge",
            labels=["queue"],
        )

        gauge.set(5, queue="tasks")
        gauge.set(10, queue="results")

        assert gauge.get(queue="tasks") == 5
        assert gauge.get(queue="results") == 10


class TestHistogram:
    """Tests for Histogram metric."""

    def test_observe(self):
        """Test observing values."""
        histogram = Histogram(
            "test_histogram",
            "Test histogram",
            buckets=(0.1, 0.5, 1.0, float("inf")),
        )

        histogram.observe(0.05)
        histogram.observe(0.3)
        histogram.observe(0.8)
        histogram.observe(2.0)

        data = histogram.collect()
        assert "default" in data or len(data) == 1

    def test_observe_with_labels(self):
        """Test observing with labels."""
        histogram = Histogram(
            "test_histogram",
            "Test histogram",
            labels=["method"],
        )

        histogram.observe(0.1, method="GET")
        histogram.observe(0.2, method="GET")
        histogram.observe(0.5, method="POST")

        data = histogram.collect()
        assert len(data) == 2

    def test_timer_context_manager(self):
        """Test histogram timer context manager."""
        histogram = Histogram("test_duration", "Test duration")

        with histogram.time():
            time.sleep(0.01)

        data = histogram.collect()
        values = list(data.values())[0]
        assert values["count"] == 1
        assert values["sum"] >= 0.01


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_create_metrics(self):
        """Test creating different metric types."""
        collector = MetricsCollector(namespace="test")

        counter = collector.counter("requests", "Total requests")
        gauge = collector.gauge("queue_size", "Queue size")
        histogram = collector.histogram("duration", "Request duration")

        assert counter.name == "test_requests"
        assert gauge.name == "test_queue_size"
        assert histogram.name == "test_duration"

    def test_metric_reuse(self):
        """Test that same metric is returned on repeated calls."""
        collector = MetricsCollector(namespace="test")

        counter1 = collector.counter("requests", "Total requests")
        counter2 = collector.counter("requests", "Total requests")

        assert counter1 is counter2

    def test_prometheus_export(self):
        """Test Prometheus format export."""
        collector = MetricsCollector(namespace="test")

        counter = collector.counter("requests", "Total requests", labels=["method"])
        counter.inc(method="GET")
        counter.inc(method="POST")

        gauge = collector.gauge("connections", "Active connections")
        gauge.set(5)

        output = collector.export_prometheus()

        assert "# TYPE test_requests counter" in output
        assert 'test_requests{method="GET"} 1' in output
        assert 'test_requests{method="POST"} 1' in output
        assert "# TYPE test_connections gauge" in output
        assert "test_connections 5" in output

    def test_json_export(self):
        """Test JSON format export."""
        collector = MetricsCollector(namespace="test")

        counter = collector.counter("requests", "Total requests")
        counter.inc()

        data = collector.export_json()

        assert "timestamp" in data
        assert "counters" in data
        assert "gauges" in data
        assert "histograms" in data


class TestSpanContext:
    """Tests for SpanContext."""

    def test_generate_root_context(self):
        """Test generating a root span context."""
        context = SpanContext.generate()

        assert context.trace_id is not None
        assert context.span_id is not None
        assert context.parent_span_id is None

    def test_generate_child_context(self):
        """Test generating a child span context."""
        parent = SpanContext.generate()
        child = SpanContext.generate(parent)

        assert child.trace_id == parent.trace_id
        assert child.span_id != parent.span_id
        assert child.parent_span_id == parent.span_id


class TestSpan:
    """Tests for Span."""

    def test_span_creation(self):
        """Test span creation."""
        context = SpanContext.generate()
        span = Span(name="test_span", context=context)

        assert span.name == "test_span"
        assert span.status == SpanStatus.UNSET
        assert span.end_time is None

    def test_span_attributes(self):
        """Test setting span attributes."""
        context = SpanContext.generate()
        span = Span(name="test_span", context=context)

        span.set_attribute("key", "value")
        span.set_attributes({"key2": "value2", "key3": 123})

        assert span.attributes["key"] == "value"
        assert span.attributes["key2"] == "value2"
        assert span.attributes["key3"] == 123

    def test_span_events(self):
        """Test adding span events."""
        context = SpanContext.generate()
        span = Span(name="test_span", context=context)

        span.add_event("event1")
        span.add_event("event2", {"detail": "info"})

        assert len(span.events) == 2
        assert span.events[0].name == "event1"
        assert span.events[1].attributes["detail"] == "info"

    def test_span_exception_recording(self):
        """Test recording exceptions."""
        context = SpanContext.generate()
        span = Span(name="test_span", context=context)

        try:
            raise ValueError("Test error")
        except ValueError as e:
            span.record_exception(e)

        assert span.status == SpanStatus.ERROR
        assert len(span.events) == 1
        assert span.events[0].name == "exception"

    def test_span_end(self):
        """Test ending a span."""
        context = SpanContext.generate()
        span = Span(name="test_span", context=context)

        time.sleep(0.01)
        span.end()

        assert span.end_time is not None
        assert span.status == SpanStatus.OK
        assert span.duration_ms >= 10

    def test_span_to_dict(self):
        """Test span serialization."""
        context = SpanContext.generate()
        span = Span(
            name="test_span",
            context=context,
            kind=SpanKind.SERVER,
        )
        span.set_attribute("test", "value")
        span.add_event("test_event")
        span.end()

        data = span.to_dict()

        assert data["name"] == "test_span"
        assert data["kind"] == "server"
        assert data["status"] == "ok"
        assert "duration_ms" in data
        assert data["attributes"]["test"] == "value"


class TestTracer:
    """Tests for Tracer."""

    def test_start_span(self):
        """Test starting a span with tracer."""
        tracer = Tracer("test")

        with tracer.start_span("test_operation") as span:
            span.set_attribute("key", "value")
            assert span.name == "test_operation"

        # Span should be recorded
        spans = tracer.get_recent_spans()
        assert len(spans) == 1
        assert spans[0].status == SpanStatus.OK

    def test_nested_spans(self):
        """Test nested spans."""
        tracer = Tracer("test")

        with tracer.start_span("parent") as parent_span:
            parent_span.set_attribute("level", "parent")

            with tracer.start_span("child") as child_span:
                child_span.set_attribute("level", "child")
                assert child_span.context.parent_span_id == parent_span.context.span_id

        spans = tracer.get_recent_spans()
        assert len(spans) == 2

    def test_span_with_exception(self):
        """Test span recording exception."""
        tracer = Tracer("test")

        try:
            with tracer.start_span("failing_operation") as span:
                raise ValueError("Test error")
        except ValueError:
            pass

        spans = tracer.get_recent_spans()
        assert len(spans) == 1
        assert spans[0].status == SpanStatus.ERROR


class TestTracingDecorators:
    """Tests for tracing decorators."""

    def test_trace_sync_decorator(self):
        """Test synchronous tracing decorator."""

        @trace_sync()
        def my_function(x: int) -> int:
            return x * 2

        result = my_function(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_trace_async_decorator(self):
        """Test async tracing decorator."""

        @trace_async()
        async def my_async_function(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        result = await my_async_function(5)
        assert result == 10


class TestContextPropagation:
    """Tests for trace context propagation."""

    def test_inject_context(self):
        """Test injecting trace context into carrier."""
        context = SpanContext(
            trace_id="0123456789abcdef0123456789abcdef",
            span_id="0123456789abcdef",
            trace_flags=1,
        )

        carrier = {}
        inject_context(carrier, context)

        assert "traceparent" in carrier
        assert carrier["traceparent"].startswith("00-")

    def test_extract_context(self):
        """Test extracting trace context from carrier."""
        carrier = {"traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"}

        context = extract_context(carrier)

        assert context is not None
        assert context.trace_id == "0123456789abcdef0123456789abcdef"
        assert context.span_id == "0123456789abcdef"
        assert context.trace_flags == 1

    def test_extract_invalid_context(self):
        """Test extracting invalid trace context."""
        carrier = {"traceparent": "invalid"}

        context = extract_context(carrier)
        assert context is None

    def test_extract_missing_context(self):
        """Test extracting from carrier without trace context."""
        carrier = {}

        context = extract_context(carrier)
        assert context is None


class TestMetricLabels:
    """Tests for MetricLabels helper."""

    def test_labels_equality(self):
        """Test label equality."""
        labels1 = MetricLabels({"a": "1", "b": "2"})
        labels2 = MetricLabels({"a": "1", "b": "2"})
        labels3 = MetricLabels({"a": "1", "b": "3"})

        assert labels1 == labels2
        assert labels1 != labels3

    def test_labels_hash(self):
        """Test label hashing for dict keys."""
        labels1 = MetricLabels({"a": "1"})
        labels2 = MetricLabels({"a": "1"})

        d = {labels1: "value"}
        assert d[labels2] == "value"

    def test_prometheus_format(self):
        """Test Prometheus label formatting."""
        labels = MetricLabels({"method": "GET", "status": "200"})

        output = labels.to_prometheus()
        assert output == '{method="GET",status="200"}'

    def test_empty_labels(self):
        """Test empty labels formatting."""
        labels = MetricLabels({})

        assert labels.to_prometheus() == ""
