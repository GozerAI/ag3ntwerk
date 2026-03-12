"""
ag3ntwerk Tools System.

Provides a unified tool system for agents with:
- Tool registry for discovery and selection
- Base tool classes with standardized interfaces
- Tool executor with logging and error handling
- Workflow engine for multi-step operations
- Predefined workflows for common agent tasks
- Configuration management
- Integration factory with credential support

Example:
    from ag3ntwerk.tools.bootstrap import initialize

    # Initialize the tools system
    initialize()

    # Or with custom config
    initialize(config_path="config/tools.yaml")

    # Use tools directly
    from ag3ntwerk.tools import get_executor
    executor = get_executor()
    result = await executor.execute("send_slack_message", channel="#general", message="Hello!")

    # Or use workflows
    from ag3ntwerk.tools import get_workflow_registry
    workflow_registry = get_workflow_registry()
    result = await workflow_registry.execute("daily_briefing")

    # Get configured integrations
    from ag3ntwerk.tools.integrations import get_integration
    slack = get_integration("slack")
"""

from ag3ntwerk.tools.base import (
    BaseTool,
    ToolResult,
    ToolParameter,
    ToolCategory,
    ToolMetadata,
    ParameterType,
)
from ag3ntwerk.tools.registry import (
    ToolRegistry,
    RegisteredTool,
    get_registry,
)
from ag3ntwerk.tools.executor import (
    ToolExecutor,
    ExecutionContext,
    ExecutionRecord,
    ExecutionStatus,
    RetryConfig,
    RateLimitConfig,
    get_executor,
)
from ag3ntwerk.tools.workflows import (
    Workflow,
    WorkflowStep,
    ToolStep,
    FunctionStep,
    ParallelStep,
    BranchStep,
    WorkflowContext,
    WorkflowResult,
    WorkflowStatus,
    StepResult,
    StepStatus,
    WorkflowRegistry,
    get_workflow_registry,
)
from ag3ntwerk.tools.config import (
    ToolsConfig,
    IntegrationConfig,
    ExecutorConfig,
    WorkflowConfig,
    ConfigManager,
    get_config_manager,
    get_config,
)
from ag3ntwerk.tools.exceptions import (
    ToolError,
    ToolNotFoundError,
    ToolDisabledError,
    ToolValidationError,
    ToolExecutionError,
    ToolTimeoutError,
    ToolRateLimitError,
    ToolConfigurationError,
    IntegrationError,
    IntegrationNotConfiguredError,
    IntegrationAuthError,
    WorkflowError,
    WorkflowStepError,
    WorkflowNotFoundError,
    WorkflowValidationError,
)

__all__ = [
    # Base
    "BaseTool",
    "ToolResult",
    "ToolParameter",
    "ToolCategory",
    "ToolMetadata",
    "ParameterType",
    # Registry
    "ToolRegistry",
    "RegisteredTool",
    "get_registry",
    # Executor
    "ToolExecutor",
    "ExecutionContext",
    "ExecutionRecord",
    "ExecutionStatus",
    "RetryConfig",
    "RateLimitConfig",
    "get_executor",
    # Workflows
    "Workflow",
    "WorkflowStep",
    "ToolStep",
    "FunctionStep",
    "ParallelStep",
    "BranchStep",
    "WorkflowContext",
    "WorkflowResult",
    "WorkflowStatus",
    "StepResult",
    "StepStatus",
    "WorkflowRegistry",
    "get_workflow_registry",
    # Config
    "ToolsConfig",
    "IntegrationConfig",
    "ExecutorConfig",
    "WorkflowConfig",
    "ConfigManager",
    "get_config_manager",
    "get_config",
    # Exceptions
    "ToolError",
    "ToolNotFoundError",
    "ToolDisabledError",
    "ToolValidationError",
    "ToolExecutionError",
    "ToolTimeoutError",
    "ToolRateLimitError",
    "ToolConfigurationError",
    "IntegrationError",
    "IntegrationNotConfiguredError",
    "IntegrationAuthError",
    "WorkflowError",
    "WorkflowStepError",
    "WorkflowNotFoundError",
    "WorkflowValidationError",
]
