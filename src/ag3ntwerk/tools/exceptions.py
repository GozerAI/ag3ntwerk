"""
Tool Exceptions for ag3ntwerk.

Provides specific exception types for tool operations.
"""

from typing import Any, Dict, List, Optional


class ToolError(Exception):
    """Base exception for all tool errors."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "tool_name": self.tool_name,
            "details": self.details,
        }


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not registered."""

    def __init__(self, tool_name: str):
        super().__init__(
            message=f"Tool '{tool_name}' not found in registry",
            tool_name=tool_name,
        )


class ToolDisabledError(ToolError):
    """Raised when attempting to use a disabled tool."""

    def __init__(self, tool_name: str):
        super().__init__(
            message=f"Tool '{tool_name}' is disabled",
            tool_name=tool_name,
        )


class ToolValidationError(ToolError):
    """Raised when tool parameters fail validation."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        parameter_name: Optional[str] = None,
        expected_type: Optional[str] = None,
        actual_value: Any = None,
        validation_errors: Optional[List[str]] = None,
    ):
        details = {}
        if parameter_name:
            details["parameter"] = parameter_name
        if expected_type:
            details["expected_type"] = expected_type
        if actual_value is not None:
            details["actual_value"] = str(actual_value)[:100]
        if validation_errors:
            details["validation_errors"] = validation_errors

        super().__init__(
            message=message,
            tool_name=tool_name,
            details=details,
        )
        self.parameter_name = parameter_name
        self.validation_errors = validation_errors or []


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        execution_id: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        details = {}
        if execution_id:
            details["execution_id"] = execution_id
        if cause:
            details["cause_type"] = type(cause).__name__
            details["cause_message"] = str(cause)

        super().__init__(
            message=message,
            tool_name=tool_name,
            details=details,
        )
        self.execution_id = execution_id
        self.cause = cause


class ToolTimeoutError(ToolExecutionError):
    """Raised when tool execution times out."""

    def __init__(
        self,
        tool_name: str,
        timeout_seconds: float,
        execution_id: Optional[str] = None,
    ):
        super().__init__(
            message=f"Tool '{tool_name}' timed out after {timeout_seconds}s",
            tool_name=tool_name,
            execution_id=execution_id,
        )
        self.timeout_seconds = timeout_seconds
        self.details["timeout_seconds"] = timeout_seconds


class ToolRateLimitError(ToolExecutionError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        tool_name: str,
        retry_after: Optional[float] = None,
    ):
        message = f"Rate limit exceeded for tool '{tool_name}'"
        if retry_after:
            message += f", retry after {retry_after}s"

        super().__init__(
            message=message,
            tool_name=tool_name,
        )
        self.retry_after = retry_after
        if retry_after:
            self.details["retry_after"] = retry_after


class ToolConfigurationError(ToolError):
    """Raised when tool configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        missing_config: Optional[List[str]] = None,
    ):
        details = {}
        if missing_config:
            details["missing_config"] = missing_config

        super().__init__(
            message=message,
            tool_name=tool_name,
            details=details,
        )
        self.missing_config = missing_config or []


class IntegrationError(ToolError):
    """Raised when an integration fails."""

    def __init__(
        self,
        message: str,
        integration_name: str,
        tool_name: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        details = {"integration": integration_name}
        if cause:
            details["cause_type"] = type(cause).__name__
            details["cause_message"] = str(cause)

        super().__init__(
            message=message,
            tool_name=tool_name,
            details=details,
        )
        self.integration_name = integration_name
        self.cause = cause


class IntegrationNotConfiguredError(IntegrationError):
    """Raised when integration is not configured."""

    def __init__(
        self,
        integration_name: str,
        tool_name: Optional[str] = None,
        required_config: Optional[List[str]] = None,
    ):
        message = f"Integration '{integration_name}' is not configured"
        if required_config:
            message += f". Required: {', '.join(required_config)}"

        super().__init__(
            message=message,
            integration_name=integration_name,
            tool_name=tool_name,
        )
        self.required_config = required_config or []
        if required_config:
            self.details["required_config"] = required_config


class IntegrationAuthError(IntegrationError):
    """Raised when integration authentication fails."""

    def __init__(
        self,
        integration_name: str,
        tool_name: Optional[str] = None,
        auth_type: Optional[str] = None,
    ):
        super().__init__(
            message=f"Authentication failed for integration '{integration_name}'",
            integration_name=integration_name,
            tool_name=tool_name,
        )
        self.auth_type = auth_type
        if auth_type:
            self.details["auth_type"] = auth_type


class WorkflowError(ToolError):
    """Base exception for workflow errors."""

    def __init__(
        self,
        message: str,
        workflow_name: Optional[str] = None,
        workflow_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if workflow_id:
            full_details["workflow_id"] = workflow_id

        super().__init__(
            message=message,
            tool_name=workflow_name,
            details=full_details,
        )
        self.workflow_name = workflow_name
        self.workflow_id = workflow_id


class WorkflowStepError(WorkflowError):
    """Raised when a workflow step fails."""

    def __init__(
        self,
        message: str,
        workflow_name: Optional[str] = None,
        step_name: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        details = {}
        if step_name:
            details["step_name"] = step_name
        if cause:
            details["cause_type"] = type(cause).__name__
            details["cause_message"] = str(cause)

        super().__init__(
            message=message,
            workflow_name=workflow_name,
            details=details,
        )
        self.step_name = step_name
        self.cause = cause


class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow is not found."""

    def __init__(self, workflow_name: str):
        super().__init__(
            message=f"Workflow '{workflow_name}' not found",
            workflow_name=workflow_name,
        )


class WorkflowValidationError(WorkflowError):
    """Raised when workflow validation fails."""

    def __init__(
        self,
        message: str,
        workflow_name: Optional[str] = None,
        missing_variables: Optional[List[str]] = None,
    ):
        details = {}
        if missing_variables:
            details["missing_variables"] = missing_variables

        super().__init__(
            message=message,
            workflow_name=workflow_name,
            details=details,
        )
        self.missing_variables = missing_variables or []
