"""
Custom exceptions for ag3ntwerk.

This module provides a comprehensive exception hierarchy for error handling
across the ag3ntwerk platform, enabling proper error recovery and reporting.
"""

from typing import Optional


class AgentWerkError(Exception):
    """Base exception for all ag3ntwerk errors."""

    def __init__(self, message: str, recoverable: bool = True):
        self.message = message
        self.recoverable = recoverable
        super().__init__(message)


# =============================================================================
# Task Execution Errors
# =============================================================================


class TaskExecutionError(AgentWerkError):
    """Raised when task execution fails."""

    def __init__(
        self,
        task_id: str,
        agent: str,
        message: str,
        recoverable: bool = True,
        cause: Optional[Exception] = None,
    ):
        self.task_id = task_id
        self.agent = agent
        self.cause = cause
        super().__init__(
            f"Task {task_id} failed on {agent}: {message}",
            recoverable=recoverable,
        )


class TaskTimeoutError(TaskExecutionError):
    """Raised when task execution exceeds timeout."""

    def __init__(
        self,
        task_id: str,
        agent: str,
        timeout_seconds: float,
    ):
        self.timeout_seconds = timeout_seconds
        super().__init__(
            task_id=task_id,
            agent=agent,
            message=f"Execution timed out after {timeout_seconds}s",
            recoverable=True,
        )


class TaskCancelledError(TaskExecutionError):
    """Raised when a task is cancelled."""

    def __init__(self, task_id: str, agent: str, reason: str = ""):
        super().__init__(
            task_id=task_id,
            agent=agent,
            message=f"Task cancelled{': ' + reason if reason else ''}",
            recoverable=False,
        )


class TaskValidationError(TaskExecutionError):
    """Raised when task validation fails."""

    def __init__(self, task_id: str, message: str):
        super().__init__(
            task_id=task_id,
            agent="validator",
            message=f"Validation failed: {message}",
            recoverable=False,
        )


# =============================================================================
# Agent Errors
# =============================================================================


class AgentError(AgentWerkError):
    """Base class for agent-related errors."""

    def __init__(self, agent_code: str, message: str, recoverable: bool = True):
        self.agent_code = agent_code
        super().__init__(f"Agent {agent_code}: {message}", recoverable=recoverable)


class AgentUnavailableError(AgentError):
    """Raised when target agent is not available."""

    def __init__(self, agent_code: str, reason: str = "not found"):
        super().__init__(
            agent_code=agent_code,
            message=f"Agent unavailable: {reason}",
            recoverable=True,
        )


class AgentBusyError(AgentError):
    """Raised when agent is busy and cannot accept new tasks."""

    def __init__(self, agent_code: str, current_task_id: Optional[str] = None):
        msg = "Agent is busy"
        if current_task_id:
            msg += f" (processing task {current_task_id})"
        super().__init__(agent_code=agent_code, message=msg, recoverable=True)


class AgentCapabilityError(AgentError):
    """Raised when agent lacks required capability."""

    def __init__(self, agent_code: str, task_type: str):
        super().__init__(
            agent_code=agent_code,
            message=f"Cannot handle task type '{task_type}'",
            recoverable=False,
        )


class AgentInitializationError(AgentError):
    """Raised when agent fails to initialize."""

    def __init__(self, agent_code: str, reason: str):
        super().__init__(
            agent_code=agent_code,
            message=f"Initialization failed: {reason}",
            recoverable=False,
        )


# =============================================================================
# LLM Provider Errors
# =============================================================================


class LLMError(AgentWerkError):
    """Base class for LLM-related errors."""

    def __init__(self, provider: str, message: str, recoverable: bool = True):
        self.provider = provider
        super().__init__(f"LLM ({provider}): {message}", recoverable=recoverable)


class LLMConnectionError(LLMError):
    """Raised when connection to LLM provider fails."""

    def __init__(self, provider: str, url: str, cause: Optional[Exception] = None):
        self.url = url
        self.cause = cause
        super().__init__(
            provider=provider,
            message=f"Failed to connect to {url}",
            recoverable=True,
        )


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""

    def __init__(self, provider: str, timeout_seconds: float):
        self.timeout_seconds = timeout_seconds
        super().__init__(
            provider=provider,
            message=f"Request timed out after {timeout_seconds}s",
            recoverable=True,
        )


class LLMModelNotFoundError(LLMError):
    """Raised when requested model is not available."""

    def __init__(self, provider: str, model: str, available_models: list[str]):
        self.model = model
        self.available_models = available_models
        super().__init__(
            provider=provider,
            message=f"Model '{model}' not found. Available: {available_models}",
            recoverable=False,
        )


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: Optional[float] = None):
        self.retry_after = retry_after
        msg = "Rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after}s"
        super().__init__(provider=provider, message=msg, recoverable=True)


class LLMResponseError(LLMError):
    """Raised when LLM returns an invalid or error response."""

    def __init__(self, provider: str, status_code: int, response_text: str):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(
            provider=provider,
            message=f"Error response ({status_code}): {response_text[:200]}",
            recoverable=status_code >= 500,  # Server errors are recoverable
        )


# =============================================================================
# Communication Errors
# =============================================================================


class CommunicationError(AgentWerkError):
    """Base class for communication-related errors."""

    pass


class MessageDeliveryError(CommunicationError):
    """Raised when message delivery fails."""

    def __init__(self, target: str, message_type: str, cause: Optional[Exception] = None):
        self.target = target
        self.message_type = message_type
        self.cause = cause
        super().__init__(
            f"Failed to deliver {message_type} to {target}",
            recoverable=True,
        )


class MessageTimeoutError(CommunicationError):
    """Raised when waiting for message response times out."""

    def __init__(self, target: str, timeout_seconds: float):
        self.target = target
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Timeout waiting for response from {target} after {timeout_seconds}s",
            recoverable=True,
        )


# =============================================================================
# State/Memory Errors
# =============================================================================


class StateError(AgentWerkError):
    """Base class for state management errors."""

    pass


class StateNotFoundError(StateError):
    """Raised when requested state key is not found."""

    def __init__(self, key: str, namespace: str = "default"):
        self.key = key
        self.namespace = namespace
        super().__init__(
            f"State key '{key}' not found in namespace '{namespace}'",
            recoverable=False,
        )


class StateCorruptionError(StateError):
    """Raised when state data is corrupted."""

    def __init__(self, key: str, reason: str):
        self.key = key
        super().__init__(
            f"State corruption for key '{key}': {reason}",
            recoverable=False,
        )


class StatePersistenceError(StateError):
    """Raised when state persistence fails."""

    def __init__(self, operation: str, cause: Optional[Exception] = None):
        self.operation = operation
        self.cause = cause
        super().__init__(
            f"State persistence failed during {operation}",
            recoverable=True,
        )


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(AgentWerkError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, key: str, message: str):
        self.key = key
        super().__init__(f"Configuration error for '{key}': {message}", recoverable=False)


# =============================================================================
# Retry Helper
# =============================================================================


def is_recoverable(error: Exception) -> bool:
    """Check if an error is recoverable and can be retried."""
    if isinstance(error, AgentWerkError):
        return error.recoverable
    # For non-CSuite errors, assume transient errors are recoverable
    transient_errors = (
        TimeoutError,
        ConnectionError,
        ConnectionResetError,
        ConnectionRefusedError,
    )
    return isinstance(error, transient_errors)
