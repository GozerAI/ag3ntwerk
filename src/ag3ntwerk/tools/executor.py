"""
Tool Executor for ag3ntwerk.

Provides execution management with:
- Logging and tracing
- Error handling and retries
- Rate limiting
- Timeout management
- Execution history
"""

import asyncio
import inspect
import logging
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type
from enum import Enum
from functools import wraps

from ag3ntwerk.tools.base import BaseTool, ToolResult
from ag3ntwerk.tools.registry import get_registry

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Status of tool execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class ExecutionContext:
    """Context for tool execution."""

    execution_id: str
    tool_name: str
    parameters: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    parent_execution_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionRecord:
    """Record of a tool execution."""

    execution_id: str
    tool_name: str
    status: ExecutionStatus
    parameters: Dict[str, Any]
    result: Optional[ToolResult] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: float = 0
    attempt: int = 1
    error: str = ""
    traceback: str = ""
    context: Optional[ExecutionContext] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "parameters": self.parameters,
            "result": self.result.to_dict() if self.result else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "attempt": self.attempt,
            "error": self.error,
        }


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    retry_on: List[Type[Exception]] = field(default_factory=lambda: [Exception])

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.initial_delay * (self.exponential_base ** (attempt - 1))
        return min(delay, self.max_delay)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    burst_size: int = 10


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = config.burst_size
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update

            # Refill tokens
            refill_rate = self.config.requests_per_minute / 60.0
            self.tokens = min(self.config.burst_size, self.tokens + elapsed * refill_rate)
            self.last_update = now

            if self.tokens < 1:
                # Wait for token
                wait_time = (1 - self.tokens) / refill_rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class ExecutionHooks:
    """Hooks for execution lifecycle events."""

    def __init__(self):
        self._before_execute: List[Callable] = []
        self._after_execute: List[Callable] = []
        self._on_error: List[Callable] = []
        self._on_retry: List[Callable] = []

    def before_execute(self, func: Callable) -> Callable:
        """Register a before-execute hook."""
        self._before_execute.append(func)
        return func

    def after_execute(self, func: Callable) -> Callable:
        """Register an after-execute hook."""
        self._after_execute.append(func)
        return func

    def on_error(self, func: Callable) -> Callable:
        """Register an error hook."""
        self._on_error.append(func)
        return func

    def on_retry(self, func: Callable) -> Callable:
        """Register a retry hook."""
        self._on_retry.append(func)
        return func

    async def run_before(self, context: ExecutionContext) -> None:
        """Run before-execute hooks."""
        for hook in self._before_execute:
            try:
                if inspect.iscoroutinefunction(hook):
                    await hook(context)
                else:
                    hook(context)
            except Exception as e:
                logger.warning(f"Before-execute hook failed: {e}")

    async def run_after(self, record: ExecutionRecord) -> None:
        """Run after-execute hooks."""
        for hook in self._after_execute:
            try:
                if inspect.iscoroutinefunction(hook):
                    await hook(record)
                else:
                    hook(record)
            except Exception as e:
                logger.warning(f"After-execute hook failed: {e}")

    async def run_error(self, context: ExecutionContext, error: Exception) -> None:
        """Run error hooks."""
        for hook in self._on_error:
            try:
                if inspect.iscoroutinefunction(hook):
                    await hook(context, error)
                else:
                    hook(context, error)
            except Exception as e:
                logger.warning(f"Error hook failed: {e}")

    async def run_retry(self, context: ExecutionContext, attempt: int) -> None:
        """Run retry hooks."""
        for hook in self._on_retry:
            try:
                if inspect.iscoroutinefunction(hook):
                    await hook(context, attempt)
                else:
                    hook(context, attempt)
            except Exception as e:
                logger.warning(f"Retry hook failed: {e}")


class ToolExecutor:
    """
    Manages tool execution with logging, retries, and rate limiting.

    Example:
        executor = ToolExecutor()

        # Execute a tool
        result = await executor.execute(
            "send_slack_message",
            channel="#general",
            message="Hello!",
        )

        # With context
        result = await executor.execute(
            "send_email",
            context=ExecutionContext(
                execution_id="exec-123",
                tool_name="send_email",
                parameters={},
                user_id="user-1",
            ),
            to="user@example.com",
            subject="Hello",
        )

        # Get execution history
        history = executor.get_history(limit=10)
    """

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
        default_timeout: float = 300.0,  # 5 minutes
        max_history: int = 1000,
    ):
        """Initialize the executor."""
        self.retry_config = retry_config or RetryConfig()
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())
        self.default_timeout = default_timeout
        self.max_history = max_history

        self._history: List[ExecutionRecord] = []
        self._execution_count = 0
        self.hooks = ExecutionHooks()

    def _generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        self._execution_count += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"exec-{timestamp}-{self._execution_count:06d}"

    async def execute(
        self,
        tool_name: str,
        context: Optional[ExecutionContext] = None,
        timeout: Optional[float] = None,
        retry: bool = True,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a tool with full lifecycle management.

        Args:
            tool_name: Name of the tool to execute
            context: Execution context
            timeout: Timeout in seconds
            retry: Whether to retry on failure
            **kwargs: Tool parameters

        Returns:
            ToolResult with execution outcome
        """
        # Create context if not provided
        if context is None:
            context = ExecutionContext(
                execution_id=self._generate_execution_id(),
                tool_name=tool_name,
                parameters=kwargs,
            )

        # Get registry
        registry = get_registry()
        tool = registry.get(tool_name)

        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found",
                error_type="ToolNotFoundError",
            )

        # Apply rate limiting
        await self.rate_limiter.acquire()

        # Dispatch plugin pre-execute event
        try:
            from ag3ntwerk.core.plugins import dispatch_plugin_event

            pre_results = await dispatch_plugin_event(
                "tool.pre_execute",
                {
                    "tool_name": tool_name,
                    "parameters": kwargs,
                    "agent_code": context.metadata.get("agent_code", ""),
                    "tool_category": (
                        getattr(tool.metadata, "category", {}).value
                        if hasattr(tool, "metadata")
                        and hasattr(getattr(tool, "metadata", None), "category")
                        else "general"
                    ),
                },
            )
            for r in pre_results or []:
                if isinstance(r, dict) and r.get("blocked"):
                    return ToolResult(
                        success=False,
                        error=r.get("reason", "Blocked by plugin"),
                        error_type="PluginBlockedError",
                    )
        except Exception as e:
            logger.debug(f"Plugin pre-execute dispatch failed: {e}")

        # Run before hooks
        await self.hooks.run_before(context)

        # Execute with retries
        timeout_val = timeout or self.default_timeout
        attempt = 0
        last_error: Optional[Exception] = None

        while attempt < (self.retry_config.max_attempts if retry else 1):
            attempt += 1

            record = ExecutionRecord(
                execution_id=context.execution_id,
                tool_name=tool_name,
                status=ExecutionStatus.RUNNING,
                parameters=kwargs,
                started_at=datetime.now(),
                attempt=attempt,
                context=context,
            )

            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    tool.execute(**kwargs),
                    timeout=timeout_val,
                )

                # Update record
                record.status = (
                    ExecutionStatus.SUCCESS if result.success else ExecutionStatus.FAILED
                )
                record.result = result
                record.finished_at = datetime.now()
                record.duration_ms = (record.finished_at - record.started_at).total_seconds() * 1000

                if not result.success:
                    record.error = result.error or "Unknown error"

                # Store in history
                self._add_to_history(record)

                # Dispatch plugin post-execute event
                try:
                    from ag3ntwerk.core.plugins import dispatch_plugin_event

                    await dispatch_plugin_event(
                        "tool.post_execute",
                        {
                            "tool_name": tool_name,
                            "result": result.data if result else None,
                            "agent_code": context.metadata.get("agent_code", ""),
                            "success": result.success if result else False,
                        },
                    )
                except Exception as e:
                    logger.debug(f"Plugin post-execute dispatch failed: {e}")

                # Run after hooks
                await self.hooks.run_after(record)

                # Log execution
                self._log_execution(record)

                return result

            except asyncio.TimeoutError:
                record.status = ExecutionStatus.TIMEOUT
                record.finished_at = datetime.now()
                record.duration_ms = timeout_val * 1000
                record.error = f"Execution timed out after {timeout_val}s"
                last_error = asyncio.TimeoutError(record.error)

                self._add_to_history(record)
                await self.hooks.run_error(context, last_error)

                # Don't retry timeouts
                break

            except Exception as e:
                record.status = ExecutionStatus.FAILED
                record.finished_at = datetime.now()
                record.duration_ms = (record.finished_at - record.started_at).total_seconds() * 1000
                record.error = str(e)
                record.traceback = traceback.format_exc()
                last_error = e

                self._add_to_history(record)

                # Dispatch plugin error event
                try:
                    from ag3ntwerk.core.plugins import dispatch_plugin_event

                    await dispatch_plugin_event(
                        "tool.error",
                        {
                            "tool_name": tool_name,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "agent_code": context.metadata.get("agent_code", ""),
                        },
                    )
                except Exception as plugin_err:
                    logger.debug(f"Plugin error dispatch failed: {plugin_err}")

                await self.hooks.run_error(context, e)

                # Check if we should retry
                should_retry = (
                    retry
                    and attempt < self.retry_config.max_attempts
                    and any(isinstance(e, exc_type) for exc_type in self.retry_config.retry_on)
                )

                if should_retry:
                    record.status = ExecutionStatus.RETRYING
                    delay = self.retry_config.get_delay(attempt)
                    logger.warning(
                        f"Tool '{tool_name}' failed (attempt {attempt}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    await self.hooks.run_retry(context, attempt)
                    await asyncio.sleep(delay)
                else:
                    break

        # All retries exhausted
        self._log_execution(record)

        return ToolResult(
            success=False,
            error=str(last_error) if last_error else "Execution failed",
            error_type=type(last_error).__name__ if last_error else "ExecutionError",
        )

    async def execute_batch(
        self,
        executions: List[Dict[str, Any]],
        concurrency: int = 5,
    ) -> List[ToolResult]:
        """
        Execute multiple tools in parallel.

        Args:
            executions: List of dicts with 'tool_name' and params
            concurrency: Maximum concurrent executions

        Returns:
            List of ToolResults
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def execute_one(exec_spec: Dict[str, Any]) -> ToolResult:
            async with semaphore:
                tool_name = exec_spec.pop("tool_name")
                return await self.execute(tool_name, **exec_spec)

        return await asyncio.gather(*[execute_one(exec_spec.copy()) for exec_spec in executions])

    def _add_to_history(self, record: ExecutionRecord) -> None:
        """Add record to history, maintaining max size."""
        self._history.append(record)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]

    def _log_execution(self, record: ExecutionRecord) -> None:
        """Log execution record."""
        if record.status == ExecutionStatus.SUCCESS:
            logger.info(
                f"Tool '{record.tool_name}' executed successfully " f"in {record.duration_ms:.1f}ms"
            )
        elif record.status == ExecutionStatus.TIMEOUT:
            logger.error(f"Tool '{record.tool_name}' timed out after {record.duration_ms:.1f}ms")
        else:
            logger.error(f"Tool '{record.tool_name}' failed: {record.error}")

    def get_history(
        self,
        tool_name: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100,
    ) -> List[ExecutionRecord]:
        """
        Get execution history.

        Args:
            tool_name: Filter by tool name
            status: Filter by status
            limit: Maximum records

        Returns:
            List of ExecutionRecords
        """
        records = self._history

        if tool_name:
            records = [r for r in records if r.tool_name == tool_name]

        if status:
            records = [r for r in records if r.status == status]

        return records[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        if not self._history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
            }

        total = len(self._history)
        successes = sum(1 for r in self._history if r.status == ExecutionStatus.SUCCESS)
        durations = [r.duration_ms for r in self._history if r.duration_ms > 0]

        by_tool = {}
        for record in self._history:
            if record.tool_name not in by_tool:
                by_tool[record.tool_name] = {"total": 0, "success": 0, "durations": []}
            by_tool[record.tool_name]["total"] += 1
            if record.status == ExecutionStatus.SUCCESS:
                by_tool[record.tool_name]["success"] += 1
            if record.duration_ms > 0:
                by_tool[record.tool_name]["durations"].append(record.duration_ms)

        return {
            "total_executions": total,
            "success_rate": successes / total if total > 0 else 0.0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0.0,
            "by_status": {
                status.value: sum(1 for r in self._history if r.status == status)
                for status in ExecutionStatus
            },
            "by_tool": {
                name: {
                    "total": data["total"],
                    "success_rate": data["success"] / data["total"] if data["total"] > 0 else 0.0,
                    "avg_duration_ms": (
                        sum(data["durations"]) / len(data["durations"])
                        if data["durations"]
                        else 0.0
                    ),
                }
                for name, data in by_tool.items()
            },
        }

    def clear_history(self) -> None:
        """Clear execution history."""
        self._history = []


# Global executor instance
_executor: Optional[ToolExecutor] = None


def get_executor() -> ToolExecutor:
    """Get the global tool executor instance."""
    global _executor
    if _executor is None:
        _executor = ToolExecutor()
    return _executor
