"""
Structured logging module for ag3ntwerk.

Provides JSON-formatted logging with request correlation, context propagation,
and standardized log fields for improved observability and log aggregation.

Usage:
    from ag3ntwerk.core.logging import get_logger, configure_logging, LogContext

    # Configure at application startup
    configure_logging(level="INFO", json_output=True)

    # Get a logger for your module
    logger = get_logger(__name__)

    # Log with automatic request ID correlation
    logger.info("Processing task", task_id="task-123", agent="Forge")

    # Use context manager for additional context
    with LogContext(user_id="user-456", session_id="sess-789"):
        logger.info("User action logged")  # Includes user_id and session_id
"""

import inspect
import json
import logging
import sys
import traceback
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Optional

# Context variables for log correlation
_log_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})


# Standard log fields
@dataclass
class LogFields:
    """Standard fields included in all log records."""

    timestamp: str = ""
    level: str = ""
    logger: str = ""
    message: str = ""
    request_id: str = ""
    # Optional fields
    agent: Optional[str] = None
    task_id: Optional[str] = None
    task_type: Optional[str] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


class StructuredLogFormatter(logging.Formatter):
    """
    Formatter that outputs logs as JSON with standardized fields.

    Integrates with request ID tracking from the API middleware.
    """

    def __init__(
        self,
        include_stack_info: bool = True,
        indent: Optional[int] = None,
    ):
        """
        Initialize the formatter.

        Args:
            include_stack_info: Include stack traces for errors
            indent: JSON indent level (None for compact)
        """
        super().__init__()
        self.include_stack_info = include_stack_info
        self.indent = indent

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        # Get request ID from context variable if available
        request_id = self._get_request_id()

        # Get additional context from context variable
        context = _log_context.get()

        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request ID if available
        if request_id:
            log_data["request_id"] = request_id

        # Add context from ContextVar
        if context:
            log_data.update(context)

        # Add extra fields from the log record
        extra_fields = self._extract_extra_fields(record)
        if extra_fields:
            log_data.update(extra_fields)

        # Add exception info if present
        if record.exc_info and self.include_stack_info:
            log_data["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            log_data["error"] = str(record.exc_info[1]) if record.exc_info[1] else None
            log_data["stack_trace"] = self._format_exception(record.exc_info)

        # Add location info for debug level
        if record.levelno <= logging.DEBUG:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_data, default=str, indent=self.indent)

    def _get_request_id(self) -> str:
        """Get request ID from the API context variable."""
        try:
            # Import here to avoid circular imports
            from ag3ntwerk.api.app import get_request_id

            return get_request_id()
        except (ImportError, AttributeError):
            return ""

    def _extract_extra_fields(self, record: logging.LogRecord) -> dict[str, Any]:
        """Extract custom fields added to the log record."""
        # Standard LogRecord attributes to exclude
        standard_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "message",
            "taskName",
        }

        extra = {}
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                extra[key] = value

        return extra

    def _format_exception(self, exc_info) -> str:
        """Format exception information."""
        if exc_info:
            return "".join(traceback.format_exception(*exc_info))
        return ""


class ConsoleLogFormatter(logging.Formatter):
    """
    Human-readable formatter for console output with colors.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record for console output."""
        # Get request ID
        request_id = self._get_request_id()

        # Build the log line
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level = record.levelname

        if self.use_colors:
            color = self.COLORS.get(level, "")
            level_str = f"{color}{level:8}{self.RESET}"
        else:
            level_str = f"{level:8}"

        # Build prefix with request ID if available
        prefix = f"{timestamp} | {level_str} | {record.name}"
        if request_id:
            prefix += f" | req:{request_id[:8]}"

        # Extract extra fields
        extra = self._extract_extra_fields(record)
        extra_str = ""
        if extra:
            extra_str = " | " + " ".join(f"{k}={v}" for k, v in extra.items())

        message = f"{prefix} | {record.getMessage()}{extra_str}"

        # Add exception info if present
        if record.exc_info:
            message += "\n" + self._format_exception(record.exc_info)

        return message

    def _get_request_id(self) -> str:
        """Get request ID from the API context variable."""
        try:
            from ag3ntwerk.api.app import get_request_id

            return get_request_id()
        except (ImportError, AttributeError):
            return ""

    def _extract_extra_fields(self, record: logging.LogRecord) -> dict[str, Any]:
        """Extract custom fields added to the log record."""
        standard_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "message",
            "taskName",
        }

        extra = {}
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                extra[key] = value

        return extra

    def _format_exception(self, exc_info) -> str:
        """Format exception information."""
        if exc_info:
            return "".join(traceback.format_exception(*exc_info))
        return ""


class StructuredLogger(logging.Logger):
    """
    Logger that supports structured logging with extra fields.
    """

    def _log_with_extra(
        self,
        level: int,
        msg: str,
        args: tuple = (),
        exc_info: Any = None,
        **kwargs: Any,
    ) -> None:
        """Log with extra keyword arguments as structured fields."""
        if self.isEnabledFor(level):
            extra = kwargs
            self._log(level, msg, args, exc_info=exc_info, extra=extra)

    def debug(self, msg: str, *args, **kwargs) -> None:
        self._log_with_extra(logging.DEBUG, msg, args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._log_with_extra(logging.INFO, msg, args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._log_with_extra(logging.WARNING, msg, args, **kwargs)

    def error(self, msg: str, *args, exc_info: Any = None, **kwargs) -> None:
        self._log_with_extra(logging.ERROR, msg, args, exc_info=exc_info, **kwargs)

    def critical(self, msg: str, *args, exc_info: Any = None, **kwargs) -> None:
        self._log_with_extra(logging.CRITICAL, msg, args, exc_info=exc_info, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        """Log an exception with traceback."""
        kwargs["exc_info"] = True
        self.error(msg, *args, **kwargs)


class LogContext:
    """
    Context manager for adding temporary context to all logs within a block.

    Usage:
        with LogContext(user_id="123", operation="process_task"):
            logger.info("Starting")  # Includes user_id and operation
            logger.info("Done")      # Includes user_id and operation
        # Context is removed after exiting the block
    """

    def __init__(self, **kwargs: Any):
        """
        Initialize with context fields.

        Args:
            **kwargs: Fields to add to all logs within this context
        """
        self.new_context = kwargs
        self.previous_context: dict[str, Any] = {}
        self.token = None

    def __enter__(self) -> "LogContext":
        """Enter the context, adding fields to the log context."""
        self.previous_context = _log_context.get().copy()
        merged_context = {**self.previous_context, **self.new_context}
        self.token = _log_context.set(merged_context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context, restoring previous context."""
        _log_context.set(self.previous_context)
        return None


def set_log_context(**kwargs: Any) -> None:
    """
    Set persistent context fields for the current async context.

    Unlike LogContext, this doesn't automatically clean up.
    Use for request-scoped context set at the start of a request.

    Args:
        **kwargs: Fields to add to the log context
    """
    current = _log_context.get().copy()
    current.update(kwargs)
    _log_context.set(current)


def clear_log_context() -> None:
    """Clear all context fields."""
    _log_context.set({})


def get_log_context() -> dict[str, Any]:
    """Get the current log context."""
    return _log_context.get().copy()


# Logger factory with caching
_loggers: dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured StructuredLogger instance
    """
    if name not in _loggers:
        # Set the logger class temporarily
        old_class = logging.getLoggerClass()
        logging.setLoggerClass(StructuredLogger)
        logger = logging.getLogger(name)
        logging.setLoggerClass(old_class)
        _loggers[name] = logger
    return _loggers[name]


def configure_logging(
    level: str = "INFO",
    json_output: bool = False,
    include_stack_info: bool = True,
    log_file: Optional[str] = None,
    use_colors: bool = True,
) -> None:
    """
    Configure logging for the application.

    Should be called once at application startup.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Use JSON format for logs (recommended for production)
        include_stack_info: Include stack traces in error logs
        log_file: Optional file path to write logs
        use_colors: Use colors in console output (ignored if json_output=True)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    if json_output:
        console_handler.setFormatter(StructuredLogFormatter(include_stack_info=include_stack_info))
    else:
        console_handler.setFormatter(ConsoleLogFormatter(use_colors=use_colors))

    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        # Always use JSON format for file logs
        file_handler.setFormatter(StructuredLogFormatter(include_stack_info=include_stack_info))
        root_logger.addHandler(file_handler)

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def log_execution_time(
    logger: Optional[StructuredLogger] = None,
    level: int = logging.INFO,
    message: str = "Execution completed",
) -> Callable:
    """
    Decorator to log execution time of a function.

    Args:
        logger: Logger to use (defaults to function's module logger)
        level: Log level to use
        message: Base message for the log

    Usage:
        @log_execution_time()
        def my_function():
            ...

        @log_execution_time(message="Task processed")
        async def process_task():
            ...
    """

    def decorator(func: Callable) -> Callable:
        func_logger = logger or get_logger(func.__module__)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            try:
                result = await func(*args, **kwargs)
                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                func_logger._log_with_extra(
                    level,
                    message,
                    function=func.__name__,
                    duration_ms=round(duration_ms, 2),
                    status="success",
                )
                return result
            except Exception as e:
                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                func_logger._log_with_extra(
                    logging.ERROR,
                    f"{message} - failed",
                    function=func.__name__,
                    duration_ms=round(duration_ms, 2),
                    status="error",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            try:
                result = func(*args, **kwargs)
                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                func_logger._log_with_extra(
                    level,
                    message,
                    function=func.__name__,
                    duration_ms=round(duration_ms, 2),
                    status="success",
                )
                return result
            except Exception as e:
                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                func_logger._log_with_extra(
                    logging.ERROR,
                    f"{message} - failed",
                    function=func.__name__,
                    duration_ms=round(duration_ms, 2),
                    status="error",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                raise

        import asyncio

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Convenience function for logging agent actions
def log_agent_action(
    logger: StructuredLogger,
    action: str,
    agent: str,
    task_id: Optional[str] = None,
    task_type: Optional[str] = None,
    **extra: Any,
) -> None:
    """
    Log an agent action with standard fields.

    Args:
        logger: Logger to use
        action: Action being performed
        agent: Agent code/name
        task_id: Optional task identifier
        task_type: Optional task type
        **extra: Additional fields to include
    """
    logger.info(
        action,
        agent=agent,
        task_id=task_id,
        task_type=task_type,
        **extra,
    )


__all__ = [
    # Formatters
    "StructuredLogFormatter",
    "ConsoleLogFormatter",
    # Logger
    "StructuredLogger",
    "get_logger",
    # Configuration
    "configure_logging",
    # Context
    "LogContext",
    "set_log_context",
    "clear_log_context",
    "get_log_context",
    # Decorators
    "log_execution_time",
    # Utilities
    "log_agent_action",
    "LogFields",
]
