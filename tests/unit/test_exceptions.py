"""
Unit tests for ag3ntwerk exception classes.
"""

import pytest

from ag3ntwerk.core.exceptions import (
    AgentWerkError,
    TaskExecutionError,
    TaskTimeoutError,
    TaskCancelledError,
    TaskValidationError,
    AgentError,
    AgentUnavailableError,
    AgentBusyError,
    AgentCapabilityError,
    AgentInitializationError,
    LLMError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMModelNotFoundError,
    LLMRateLimitError,
    LLMResponseError,
    CommunicationError,
    MessageDeliveryError,
    MessageTimeoutError,
    StateError,
    StateNotFoundError,
    StateCorruptionError,
    StatePersistenceError,
    ConfigurationError,
    is_recoverable,
)


class TestAgentError:
    """Test base AgentWerkError class."""

    def test_basic_error(self):
        error = AgentWerkError("Test error")
        assert str(error) == "Test error"
        assert error.recoverable is True

    def test_non_recoverable_error(self):
        error = AgentWerkError("Fatal error", recoverable=False)
        assert error.recoverable is False


class TestTaskExecutionError:
    """Test task execution errors."""

    def test_task_execution_error(self):
        error = TaskExecutionError(
            task_id="task-123",
            agent="Forge",
            message="Processing failed",
        )
        assert error.task_id == "task-123"
        assert error.agent == "Forge"
        assert "task-123" in str(error)
        assert "Forge" in str(error)
        assert error.recoverable is True

    def test_task_timeout_error(self):
        error = TaskTimeoutError(
            task_id="task-456",
            agent="Sentinel",
            timeout_seconds=30.0,
        )
        assert error.timeout_seconds == 30.0
        assert "30" in str(error)
        assert error.recoverable is True

    def test_task_cancelled_error(self):
        error = TaskCancelledError(
            task_id="task-789",
            agent="Nexus",
            reason="User cancelled",
        )
        assert "cancelled" in str(error).lower()
        assert "User cancelled" in str(error)
        assert error.recoverable is False

    def test_task_validation_error(self):
        error = TaskValidationError(
            task_id="task-abc",
            message="Missing required field",
        )
        assert "Validation" in str(error)
        assert error.recoverable is False


class TestAgentErrors:
    """Test agent-related errors."""

    def test_agent_unavailable_error(self):
        error = AgentUnavailableError("Forge", "offline")
        assert error.agent_code == "Forge"
        assert "Forge" in str(error)
        assert "offline" in str(error)
        assert error.recoverable is True

    def test_agent_busy_error(self):
        error = AgentBusyError("Sentinel", current_task_id="task-123")
        assert "busy" in str(error).lower()
        assert "task-123" in str(error)
        assert error.recoverable is True

    def test_agent_capability_error(self):
        error = AgentCapabilityError("Keystone", "security_scan")
        assert "security_scan" in str(error)
        assert error.recoverable is False

    def test_agent_initialization_error(self):
        error = AgentInitializationError("Nexus", "Config missing")
        assert "Initialization" in str(error)
        assert error.recoverable is False


class TestLLMErrors:
    """Test LLM provider errors."""

    def test_llm_connection_error(self):
        error = LLMConnectionError(
            provider="Ollama",
            url="http://localhost:11434",
        )
        assert error.provider == "Ollama"
        assert error.url == "http://localhost:11434"
        assert error.recoverable is True

    def test_llm_timeout_error(self):
        error = LLMTimeoutError("GPT4All", timeout_seconds=60.0)
        assert error.timeout_seconds == 60.0
        assert "60" in str(error)
        assert error.recoverable is True

    def test_llm_model_not_found_error(self):
        error = LLMModelNotFoundError(
            provider="Ollama",
            model="llama3",
            available_models=["mistral", "phi"],
        )
        assert error.model == "llama3"
        assert "llama3" in str(error)
        assert error.recoverable is False

    def test_llm_rate_limit_error(self):
        error = LLMRateLimitError("OpenAI", retry_after=30.0)
        assert error.retry_after == 30.0
        assert "30" in str(error)
        assert error.recoverable is True

    def test_llm_response_error(self):
        error = LLMResponseError(
            provider="Ollama",
            status_code=500,
            response_text="Internal server error",
        )
        assert error.status_code == 500
        assert "500" in str(error)
        assert error.recoverable is True  # 5xx are recoverable

    def test_llm_response_error_client_error(self):
        error = LLMResponseError(
            provider="Ollama",
            status_code=400,
            response_text="Bad request",
        )
        assert error.recoverable is False  # 4xx are not recoverable


class TestCommunicationErrors:
    """Test communication errors."""

    def test_message_delivery_error(self):
        error = MessageDeliveryError(
            target="Forge",
            message_type="task",
        )
        assert error.target == "Forge"
        assert "task" in str(error)
        assert error.recoverable is True

    def test_message_timeout_error(self):
        error = MessageTimeoutError("Sentinel", timeout_seconds=10.0)
        assert error.timeout_seconds == 10.0
        assert "10" in str(error)
        assert error.recoverable is True


class TestStateErrors:
    """Test state/memory errors."""

    def test_state_not_found_error(self):
        error = StateNotFoundError("user_prefs", "users")
        assert error.key == "user_prefs"
        assert error.namespace == "users"
        assert error.recoverable is False

    def test_state_corruption_error(self):
        error = StateCorruptionError("config", "Invalid JSON")
        assert error.key == "config"
        assert "Invalid JSON" in str(error)
        assert error.recoverable is False

    def test_state_persistence_error(self):
        error = StatePersistenceError("write")
        assert "write" in str(error)
        assert error.recoverable is True


class TestConfigurationError:
    """Test configuration errors."""

    def test_configuration_error(self):
        error = ConfigurationError("llm.provider", "Invalid provider type")
        assert error.key == "llm.provider"
        assert "Invalid provider" in str(error)
        assert error.recoverable is False


class TestIsRecoverable:
    """Test is_recoverable utility function."""

    def test_agent_error_recoverable(self):
        error = AgentWerkError("Recoverable", recoverable=True)
        assert is_recoverable(error) is True

    def test_agent_error_not_recoverable(self):
        error = AgentWerkError("Not recoverable", recoverable=False)
        assert is_recoverable(error) is False

    def test_timeout_error(self):
        error = TimeoutError("Connection timed out")
        assert is_recoverable(error) is True

    def test_connection_error(self):
        error = ConnectionError("Connection refused")
        assert is_recoverable(error) is True

    def test_value_error(self):
        error = ValueError("Invalid value")
        assert is_recoverable(error) is False

    def test_runtime_error(self):
        error = RuntimeError("Unexpected error")
        assert is_recoverable(error) is False
