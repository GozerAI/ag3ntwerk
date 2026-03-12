"""
Metrics Collection for ag3ntwerk.

Provides business and operational metrics collection:
- Task execution metrics
- Agent agent performance
- Workflow statistics
- LLM usage tracking
- API request metrics

Usage:
    from ag3ntwerk.core.metrics import (
        get_metrics_collector,
        record_task_execution,
        record_llm_request,
    )

    # Record a task execution
    record_task_execution(
        task_type="code_review",
        agent="Forge",
        duration_ms=1500,
        success=True,
    )

    # Get metrics
    metrics = get_metrics_collector()
    summary = metrics.get_summary()
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class Counter:
    """Thread-safe counter."""

    name: str
    value: int = 0
    labels: Dict[str, str] = field(default_factory=dict)

    def inc(self, amount: int = 1) -> None:
        """Increment the counter."""
        self.value += amount

    def get(self) -> int:
        """Get current value."""
        return self.value


@dataclass
class Gauge:
    """Thread-safe gauge (can go up or down)."""

    name: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)

    def set(self, value: float) -> None:
        """Set the gauge value."""
        self.value = value

    def inc(self, amount: float = 1.0) -> None:
        """Increment the gauge."""
        self.value += amount

    def dec(self, amount: float = 1.0) -> None:
        """Decrement the gauge."""
        self.value -= amount

    def get(self) -> float:
        """Get current value."""
        return self.value


@dataclass
class Histogram:
    """Distribution of values with bucketing."""

    name: str
    buckets: List[float] = field(
        default_factory=lambda: [
            0.005,
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
            float("inf"),
        ]
    )
    labels: Dict[str, str] = field(default_factory=dict)

    _count: int = field(default=0, init=False)
    _sum: float = field(default=0.0, init=False)
    _bucket_counts: Dict[float, int] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self._bucket_counts = {b: 0 for b in self.buckets}

    def observe(self, value: float) -> None:
        """Record an observation."""
        self._count += 1
        self._sum += value

        for bucket in self.buckets:
            if value <= bucket:
                self._bucket_counts[bucket] += 1

    @property
    def count(self) -> int:
        return self._count

    @property
    def sum(self) -> float:
        return self._sum

    @property
    def avg(self) -> float:
        if self._count == 0:
            return 0.0
        return self._sum / self._count

    def percentile(self, p: float) -> float:
        """Estimate the p-th percentile (0-100)."""
        if self._count == 0:
            return 0.0

        target = self._count * p / 100

        for i, bucket in enumerate(sorted(self.buckets)):
            if self._bucket_counts[bucket] >= target:
                if i == 0:
                    return bucket
                prev_bucket = sorted(self.buckets)[i - 1]
                # Linear interpolation
                return prev_bucket + (bucket - prev_bucket) * (
                    (target - self._bucket_counts.get(prev_bucket, 0))
                    / max(1, self._bucket_counts[bucket] - self._bucket_counts.get(prev_bucket, 0))
                )

        return self.buckets[-2] if len(self.buckets) > 1 else 0.0

    def get_buckets(self) -> Dict[str, int]:
        """Get bucket counts."""
        return {str(b): c for b, c in self._bucket_counts.items()}


@dataclass
class TaskMetrics:
    """Metrics for task execution."""

    total: Counter = field(default_factory=lambda: Counter("tasks_total"))
    success: Counter = field(default_factory=lambda: Counter("tasks_success"))
    failed: Counter = field(default_factory=lambda: Counter("tasks_failed"))
    duration: Histogram = field(
        default_factory=lambda: Histogram(
            "task_duration_ms",
            buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, float("inf")],
        )
    )
    by_type: Dict[str, Counter] = field(default_factory=dict)
    by_agent: Dict[str, Counter] = field(default_factory=dict)


@dataclass
class LLMMetrics:
    """Metrics for LLM requests."""

    requests_total: Counter = field(default_factory=lambda: Counter("llm_requests_total"))
    tokens_prompt: Counter = field(default_factory=lambda: Counter("llm_tokens_prompt"))
    tokens_completion: Counter = field(default_factory=lambda: Counter("llm_tokens_completion"))
    latency: Histogram = field(
        default_factory=lambda: Histogram(
            "llm_latency_ms",
            buckets=[100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000, float("inf")],
        )
    )
    errors: Counter = field(default_factory=lambda: Counter("llm_errors_total"))
    by_model: Dict[str, Counter] = field(default_factory=dict)
    by_provider: Dict[str, Counter] = field(default_factory=dict)


@dataclass
class WorkflowMetrics:
    """Metrics for workflow execution."""

    total: Counter = field(default_factory=lambda: Counter("workflows_total"))
    success: Counter = field(default_factory=lambda: Counter("workflows_success"))
    failed: Counter = field(default_factory=lambda: Counter("workflows_failed"))
    duration: Histogram = field(
        default_factory=lambda: Histogram(
            "workflow_duration_ms",
            buckets=[1000, 5000, 10000, 30000, 60000, 120000, 300000, float("inf")],
        )
    )
    by_name: Dict[str, Counter] = field(default_factory=dict)
    steps_executed: Counter = field(default_factory=lambda: Counter("workflow_steps_total"))


@dataclass
class APIMetrics:
    """Metrics for API requests."""

    requests_total: Counter = field(default_factory=lambda: Counter("api_requests_total"))
    latency: Histogram = field(
        default_factory=lambda: Histogram(
            "api_latency_ms", buckets=[5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, float("inf")]
        )
    )
    by_endpoint: Dict[str, Counter] = field(default_factory=dict)
    by_status: Dict[int, Counter] = field(default_factory=dict)
    active_requests: Gauge = field(default_factory=lambda: Gauge("api_active_requests"))


@dataclass
class PipelineMetrics:
    """Metrics for the continuous learning pipeline."""

    cycles_total: Counter = field(default_factory=lambda: Counter("pipeline_cycles_total"))
    cycles_success: Counter = field(default_factory=lambda: Counter("pipeline_cycles_success"))
    cycles_failed: Counter = field(default_factory=lambda: Counter("pipeline_cycles_failed"))
    cycle_duration: Histogram = field(
        default_factory=lambda: Histogram(
            "pipeline_cycle_duration_ms",
            buckets=[100, 500, 1000, 5000, 10000, 30000, 60000, 120000, float("inf")],
        )
    )


@dataclass
class AgentActivityMetrics:
    """Metrics for agent activity tracking."""

    active_agents: Gauge = field(default_factory=lambda: Gauge("active_agents"))
    by_agent: Dict[str, Counter] = field(default_factory=dict)


class MetricsCollector:
    """
    Central metrics collector for ag3ntwerk.

    Collects and aggregates metrics from various components.
    """

    def __init__(self):
        self.tasks = TaskMetrics()
        self.llm = LLMMetrics()
        self.workflows = WorkflowMetrics()
        self.api = APIMetrics()
        self.pipeline = PipelineMetrics()
        self.agents = AgentActivityMetrics()
        self._start_time = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()

    def record_task_execution(
        self,
        task_type: str,
        agent: str,
        duration_ms: float,
        success: bool,
        **extra: Any,
    ) -> None:
        """
        Record a task execution.

        Args:
            task_type: Type of task
            agent: Agent that handled the task
            duration_ms: Execution duration in milliseconds
            success: Whether the task succeeded
            **extra: Additional metadata
        """
        self.tasks.total.inc()
        if success:
            self.tasks.success.inc()
        else:
            self.tasks.failed.inc()

        self.tasks.duration.observe(duration_ms)

        # Track by type
        if task_type not in self.tasks.by_type:
            self.tasks.by_type[task_type] = Counter(f"tasks_{task_type}")
        self.tasks.by_type[task_type].inc()

        # Track by agent
        if agent not in self.tasks.by_agent:
            self.tasks.by_agent[agent] = Counter(f"tasks_{agent}")
        self.tasks.by_agent[agent].inc()

        logger.debug(
            "Recorded task metric",
            task_type=task_type,
            agent=agent,
            duration_ms=duration_ms,
            success=success,
        )

    def record_llm_request(
        self,
        provider: str,
        model: str,
        latency_ms: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        success: bool = True,
        **extra: Any,
    ) -> None:
        """
        Record an LLM request.

        Args:
            provider: LLM provider name
            model: Model used
            latency_ms: Request latency in milliseconds
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            success: Whether the request succeeded
            **extra: Additional metadata
        """
        self.llm.requests_total.inc()
        self.llm.tokens_prompt.inc(prompt_tokens)
        self.llm.tokens_completion.inc(completion_tokens)
        self.llm.latency.observe(latency_ms)

        if not success:
            self.llm.errors.inc()

        # Track by model
        if model not in self.llm.by_model:
            self.llm.by_model[model] = Counter(f"llm_{model}")
        self.llm.by_model[model].inc()

        # Track by provider
        if provider not in self.llm.by_provider:
            self.llm.by_provider[provider] = Counter(f"llm_{provider}")
        self.llm.by_provider[provider].inc()

    def record_workflow_execution(
        self,
        workflow_name: str,
        duration_ms: float,
        steps_count: int,
        success: bool,
        **extra: Any,
    ) -> None:
        """
        Record a workflow execution.

        Args:
            workflow_name: Name of the workflow
            duration_ms: Total execution duration
            steps_count: Number of steps executed
            success: Whether the workflow succeeded
            **extra: Additional metadata
        """
        self.workflows.total.inc()
        if success:
            self.workflows.success.inc()
        else:
            self.workflows.failed.inc()

        self.workflows.duration.observe(duration_ms)
        self.workflows.steps_executed.inc(steps_count)

        # Track by name
        if workflow_name not in self.workflows.by_name:
            self.workflows.by_name[workflow_name] = Counter(f"workflow_{workflow_name}")
        self.workflows.by_name[workflow_name].inc()

    def record_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
        **extra: Any,
    ) -> None:
        """
        Record an API request.

        Args:
            endpoint: API endpoint path
            method: HTTP method
            status_code: Response status code
            latency_ms: Request latency
            **extra: Additional metadata
        """
        self.api.requests_total.inc()
        self.api.latency.observe(latency_ms)

        # Track by endpoint
        endpoint_key = f"{method}:{endpoint}"
        if endpoint_key not in self.api.by_endpoint:
            self.api.by_endpoint[endpoint_key] = Counter(f"api_{endpoint_key}")
        self.api.by_endpoint[endpoint_key].inc()

        # Track by status
        if status_code not in self.api.by_status:
            self.api.by_status[status_code] = Counter(f"api_status_{status_code}")
        self.api.by_status[status_code].inc()

    @contextmanager
    def track_api_request(self):
        """Context manager to track active API requests."""
        self.api.active_requests.inc()
        try:
            yield
        finally:
            self.api.active_requests.dec()

    def record_pipeline_cycle(
        self,
        duration_ms: float,
        success: bool,
        **extra: Any,
    ) -> None:
        """
        Record a learning pipeline cycle completion.

        Args:
            duration_ms: Cycle duration in milliseconds
            success: Whether the cycle succeeded
            **extra: Additional metadata
        """
        self.pipeline.cycles_total.inc()
        if success:
            self.pipeline.cycles_success.inc()
        else:
            self.pipeline.cycles_failed.inc()

        self.pipeline.cycle_duration.observe(duration_ms)

    def set_active_agents(self, count: int) -> None:
        """
        Set the number of currently active agents.

        Args:
            count: Number of active agents
        """
        self.agents.active_agents.set(float(count))

    def record_agent_task(self, agent_code: str) -> None:
        """
        Record a task executed by a specific agent.

        Args:
            agent_code: Code of the agent that executed the task
        """
        if agent_code not in self.agents.by_agent:
            self.agents.by_agent[agent_code] = Counter(f"agent_tasks_{agent_code}")
        self.agents.by_agent[agent_code].inc()

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()

        return {
            "uptime_seconds": uptime,
            "tasks": {
                "total": self.tasks.total.get(),
                "success": self.tasks.success.get(),
                "failed": self.tasks.failed.get(),
                "success_rate": self._success_rate(
                    self.tasks.success.get(), self.tasks.total.get()
                ),
                "avg_duration_ms": self.tasks.duration.avg,
                "p50_duration_ms": self.tasks.duration.percentile(50),
                "p95_duration_ms": self.tasks.duration.percentile(95),
                "p99_duration_ms": self.tasks.duration.percentile(99),
                "by_type": {k: v.get() for k, v in self.tasks.by_type.items()},
                "by_agent": {k: v.get() for k, v in self.tasks.by_agent.items()},
            },
            "llm": {
                "requests_total": self.llm.requests_total.get(),
                "tokens_prompt": self.llm.tokens_prompt.get(),
                "tokens_completion": self.llm.tokens_completion.get(),
                "tokens_total": self.llm.tokens_prompt.get() + self.llm.tokens_completion.get(),
                "errors": self.llm.errors.get(),
                "error_rate": self._success_rate(
                    self.llm.errors.get(), self.llm.requests_total.get()
                ),
                "avg_latency_ms": self.llm.latency.avg,
                "p50_latency_ms": self.llm.latency.percentile(50),
                "p95_latency_ms": self.llm.latency.percentile(95),
                "by_model": {k: v.get() for k, v in self.llm.by_model.items()},
                "by_provider": {k: v.get() for k, v in self.llm.by_provider.items()},
            },
            "workflows": {
                "total": self.workflows.total.get(),
                "success": self.workflows.success.get(),
                "failed": self.workflows.failed.get(),
                "success_rate": self._success_rate(
                    self.workflows.success.get(), self.workflows.total.get()
                ),
                "steps_executed": self.workflows.steps_executed.get(),
                "avg_duration_ms": self.workflows.duration.avg,
                "by_name": {k: v.get() for k, v in self.workflows.by_name.items()},
            },
            "api": {
                "requests_total": self.api.requests_total.get(),
                "active_requests": int(self.api.active_requests.get()),
                "avg_latency_ms": self.api.latency.avg,
                "p50_latency_ms": self.api.latency.percentile(50),
                "p95_latency_ms": self.api.latency.percentile(95),
                "by_status": {str(k): v.get() for k, v in self.api.by_status.items()},
            },
            "pipeline": {
                "cycles_total": self.pipeline.cycles_total.get(),
                "cycles_success": self.pipeline.cycles_success.get(),
                "cycles_failed": self.pipeline.cycles_failed.get(),
                "success_rate": self._success_rate(
                    self.pipeline.cycles_success.get(),
                    self.pipeline.cycles_total.get(),
                ),
                "avg_cycle_duration_ms": self.pipeline.cycle_duration.avg,
                "p50_cycle_duration_ms": self.pipeline.cycle_duration.percentile(50),
                "p95_cycle_duration_ms": self.pipeline.cycle_duration.percentile(95),
            },
            "agents": {
                "active_count": int(self.agents.active_agents.get()),
                "by_agent": {k: v.get() for k, v in self.agents.by_agent.items()},
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _success_rate(self, success: int, total: int) -> float:
        """Calculate success rate."""
        if total == 0:
            return 1.0
        return success / total

    def reset(self) -> None:
        """Reset all metrics."""
        self.tasks = TaskMetrics()
        self.llm = LLMMetrics()
        self.workflows = WorkflowMetrics()
        self.api = APIMetrics()
        self.pipeline = PipelineMetrics()
        self.agents = AgentActivityMetrics()
        logger.info("Metrics reset")


# Global metrics collector
_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


# Convenience functions
def record_task_execution(
    task_type: str,
    agent: str,
    duration_ms: float,
    success: bool,
    **extra: Any,
) -> None:
    """Record a task execution metric."""
    get_metrics_collector().record_task_execution(
        task_type, agent, duration_ms, success, **extra
    )


def record_llm_request(
    provider: str,
    model: str,
    latency_ms: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    success: bool = True,
    **extra: Any,
) -> None:
    """Record an LLM request metric."""
    get_metrics_collector().record_llm_request(
        provider, model, latency_ms, prompt_tokens, completion_tokens, success, **extra
    )


def record_workflow_execution(
    workflow_name: str,
    duration_ms: float,
    steps_count: int,
    success: bool,
    **extra: Any,
) -> None:
    """Record a workflow execution metric."""
    get_metrics_collector().record_workflow_execution(
        workflow_name, duration_ms, steps_count, success, **extra
    )


def record_api_request(
    endpoint: str,
    method: str,
    status_code: int,
    latency_ms: float,
    **extra: Any,
) -> None:
    """Record an API request metric."""
    get_metrics_collector().record_api_request(endpoint, method, status_code, latency_ms, **extra)


def record_pipeline_cycle(
    duration_ms: float,
    success: bool,
    **extra: Any,
) -> None:
    """Record a learning pipeline cycle completion."""
    get_metrics_collector().record_pipeline_cycle(duration_ms, success, **extra)


def set_active_agents(count: int) -> None:
    """Set the number of currently active agents."""
    get_metrics_collector().set_active_agents(count)


def record_agent_task(agent_code: str) -> None:
    """Record a task executed by a specific agent."""
    get_metrics_collector().record_agent_task(agent_code)


__all__ = [
    # Classes
    "MetricsCollector",
    "Counter",
    "Gauge",
    "Histogram",
    "TaskMetrics",
    "LLMMetrics",
    "WorkflowMetrics",
    "APIMetrics",
    "PipelineMetrics",
    "AgentActivityMetrics",
    # Functions
    "get_metrics_collector",
    "record_task_execution",
    "record_llm_request",
    "record_workflow_execution",
    "record_api_request",
    "record_pipeline_cycle",
    "set_active_agents",
    "record_agent_task",
]
