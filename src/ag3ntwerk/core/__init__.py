"""
Core module for ag3ntwerk agent framework.

Provides the foundational abstractions:
- Task: Unit of work with priority and context
- TaskResult: Outcome of task execution
- Agent: Base class for all agents
- Manager: Agent that delegates to subordinates
- Specialist: Agent that executes specific tasks

Also provides exception classes for error handling.
"""

from ag3ntwerk.core.base import (
    Task,
    TaskResult,
    TaskStatus,
    TaskPriority,
    Agent,
    Manager,
    Specialist,
)

from ag3ntwerk.core.handlers import (
    HandlerConfig,
    HandlerRegistry,
    BaseTaskHandler,
    create_standard_handler,
)

from ag3ntwerk.core.logging import (
    StructuredLogFormatter,
    ConsoleLogFormatter,
    StructuredLogger,
    get_logger,
    configure_logging,
    LogContext,
    set_log_context,
    clear_log_context,
    get_log_context,
    log_execution_time,
    log_agent_action,
    LogFields,
)

from ag3ntwerk.core.async_utils import (
    run_sync,
)

from ag3ntwerk.core.http_client import (
    HTTPClientPool,
    TracingSession,
    ClientConfig,
    DEFAULT_CONFIGS,
    get_http_client_pool,
    get_http_client,
    shutdown_http_clients,
)

from ag3ntwerk.core.health import (
    HealthStatus,
    CheckStatus,
    HealthCheckResult,
    AggregatedHealth,
    HealthCheck,
    HealthAggregator,
    get_health_aggregator,
    register_health_check,
    get_aggregated_health,
    check_readiness,
    check_liveness,
)

from ag3ntwerk.core.shutdown import (
    ShutdownManager,
    ShutdownState,
    ShutdownHook,
    TaskInfo,
    get_shutdown_manager,
    register_shutdown_hook,
    setup_signal_handlers,
)

from ag3ntwerk.core.config import (
    Environment,
    Config,
    LLMConfig,
    ServerConfig,
    RateLimitConfig,
    ShutdownConfig,
    HealthConfig,
    get_config,
    set_config,
    validate_config,
    validate_config_or_raise,
    log_config_summary,
)

from ag3ntwerk.core.resources import (
    AsyncResource,
    ResourcePool,
    ResourceStats,
    ResourceManager,
    get_resource_manager,
    cleanup_all_resources,
    managed_resource,
)

from ag3ntwerk.core.metrics import (
    MetricsCollector,
    Counter,
    Gauge,
    Histogram,
    TaskMetrics,
    LLMMetrics,
    WorkflowMetrics,
    APIMetrics,
    get_metrics_collector,
    record_task_execution,
    record_llm_request,
    record_workflow_execution,
    record_api_request,
)

from ag3ntwerk.core.errors import (
    ErrorResponse,
    ErrorDetail,
    ErrorCode,
    ERROR_STATUS_CODES,
    create_error_response,
    create_json_response,
    exception_to_error_response,
    get_error_code_for_exception,
    get_request_info,
    register_exception_mapping,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

from ag3ntwerk.core.webhooks import (
    WebhookEventType,
    DeliveryStatus,
    WebhookEvent,
    DeliveryAttempt,
    DeliveryRecord,
    Webhook,
    WebhookManager,
    get_webhook_manager,
    dispatch_event,
    shutdown_webhooks,
)

from ag3ntwerk.core.queue import (
    TaskState,
    QueuedTask,
    QueueStats,
    TaskQueue,
    get_task_queue,
    enqueue_task,
    shutdown_queue,
)

from ag3ntwerk.core.analytics import (
    TimeRange,
    AlertSeverity,
    TaskRecord,
    ExecutivePerformance,
    TaskTypeAnalytics,
    DashboardSummary,
    Alert,
    AlertRule,
    CacheEntry,
    AnalyticsDashboard,
    get_analytics_dashboard,
    record_task_analytics,
)

from ag3ntwerk.core.plugins import (
    PluginState,
    PluginMetadata,
    HookRegistration,
    SandboxConfig,
    VersionRequirement,
    PluginHealth,
    PluginEvent,
    EventFilter,
    PluginContext,
    hook,
    Plugin,
    PluginManager,
    get_plugin_manager,
    LoggingPlugin,
    MetricsPlugin,
    dispatch_plugin_event,
    shutdown_plugins,
)

from ag3ntwerk.core.decisions import (
    DecisionState,
    VoteWeight,
    DecisionPriority,
    AuditAction,
    Vote,
    ImpactAssessment,
    DecisionOutcome,
    Decision,
    AuditEntry,
    EscalationRule,
    Escalation,
    DecisionTemplate,
    Notification,
    Delegation,
    Comment,
    DecisionManager,
    get_decision_manager,
    propose_decision,
)

from ag3ntwerk.core.exceptions import (
    # Base
    AgentWerkError,
    # Task errors
    TaskExecutionError,
    TaskTimeoutError,
    TaskCancelledError,
    TaskValidationError,
    # Agent errors
    AgentError,
    AgentUnavailableError,
    AgentBusyError,
    AgentCapabilityError,
    AgentInitializationError,
    # LLM errors
    LLMError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMModelNotFoundError,
    LLMRateLimitError,
    LLMResponseError,
    # Communication errors
    CommunicationError,
    MessageDeliveryError,
    MessageTimeoutError,
    # State errors
    StateError,
    StateNotFoundError,
    StateCorruptionError,
    StatePersistenceError,
    # Configuration errors
    ConfigurationError,
    # Utilities
    is_recoverable,
)

__all__ = [
    # Base classes
    "Task",
    "TaskResult",
    "TaskStatus",
    "TaskPriority",
    "Agent",
    "Manager",
    "Specialist",
    # Async utilities
    "run_sync",
    # Handlers
    "HandlerConfig",
    "HandlerRegistry",
    "BaseTaskHandler",
    "create_standard_handler",
    # Exceptions
    "AgentWerkError",
    "TaskExecutionError",
    "TaskTimeoutError",
    "TaskCancelledError",
    "TaskValidationError",
    "AgentError",
    "AgentUnavailableError",
    "AgentBusyError",
    "AgentCapabilityError",
    "AgentInitializationError",
    "LLMError",
    "LLMConnectionError",
    "LLMTimeoutError",
    "LLMModelNotFoundError",
    "LLMRateLimitError",
    "LLMResponseError",
    "CommunicationError",
    "MessageDeliveryError",
    "MessageTimeoutError",
    "StateError",
    "StateNotFoundError",
    "StateCorruptionError",
    "StatePersistenceError",
    "ConfigurationError",
    "is_recoverable",
    # Logging
    "StructuredLogFormatter",
    "ConsoleLogFormatter",
    "StructuredLogger",
    "get_logger",
    "configure_logging",
    "LogContext",
    "set_log_context",
    "clear_log_context",
    "get_log_context",
    "log_execution_time",
    "log_agent_action",
    "LogFields",
    # HTTP Client Pool
    "HTTPClientPool",
    "TracingSession",
    "ClientConfig",
    "DEFAULT_CONFIGS",
    "get_http_client_pool",
    "get_http_client",
    "shutdown_http_clients",
    # Health Check
    "HealthStatus",
    "CheckStatus",
    "HealthCheckResult",
    "AggregatedHealth",
    "HealthCheck",
    "HealthAggregator",
    "get_health_aggregator",
    "register_health_check",
    "get_aggregated_health",
    "check_readiness",
    "check_liveness",
    # Graceful Shutdown
    "ShutdownManager",
    "ShutdownState",
    "ShutdownHook",
    "TaskInfo",
    "get_shutdown_manager",
    "register_shutdown_hook",
    "setup_signal_handlers",
    # Configuration
    "Environment",
    "Config",
    "LLMConfig",
    "ServerConfig",
    "RateLimitConfig",
    "ShutdownConfig",
    "HealthConfig",
    "get_config",
    "set_config",
    "validate_config",
    "validate_config_or_raise",
    "log_config_summary",
    # Resource Management
    "AsyncResource",
    "ResourcePool",
    "ResourceStats",
    "ResourceManager",
    "get_resource_manager",
    "cleanup_all_resources",
    "managed_resource",
    # Metrics
    "MetricsCollector",
    "Counter",
    "Gauge",
    "Histogram",
    "TaskMetrics",
    "LLMMetrics",
    "WorkflowMetrics",
    "APIMetrics",
    "get_metrics_collector",
    "record_task_execution",
    "record_llm_request",
    "record_workflow_execution",
    "record_api_request",
    # Error Responses
    "ErrorResponse",
    "ErrorDetail",
    "ErrorCode",
    "ERROR_STATUS_CODES",
    "create_error_response",
    "create_json_response",
    "exception_to_error_response",
    "get_error_code_for_exception",
    "get_request_info",
    "register_exception_mapping",
    "generic_exception_handler",
    "http_exception_handler",
    "validation_exception_handler",
    # Webhooks
    "WebhookEventType",
    "DeliveryStatus",
    "WebhookEvent",
    "DeliveryAttempt",
    "DeliveryRecord",
    "Webhook",
    "WebhookManager",
    "get_webhook_manager",
    "dispatch_event",
    "shutdown_webhooks",
    # Task Queue
    "TaskState",
    "QueuedTask",
    "QueueStats",
    "TaskQueue",
    "get_task_queue",
    "enqueue_task",
    "shutdown_queue",
    # Analytics
    "TimeRange",
    "AlertSeverity",
    "TaskRecord",
    "ExecutivePerformance",
    "TaskTypeAnalytics",
    "DashboardSummary",
    "Alert",
    "AlertRule",
    "CacheEntry",
    "AnalyticsDashboard",
    "get_analytics_dashboard",
    "record_task_analytics",
    # Plugins
    "PluginState",
    "PluginMetadata",
    "HookRegistration",
    "SandboxConfig",
    "VersionRequirement",
    "PluginHealth",
    "PluginEvent",
    "EventFilter",
    "PluginContext",
    "hook",
    "Plugin",
    "PluginManager",
    "get_plugin_manager",
    "LoggingPlugin",
    "MetricsPlugin",
    "dispatch_plugin_event",
    "shutdown_plugins",
    # Decisions
    "DecisionState",
    "VoteWeight",
    "DecisionPriority",
    "AuditAction",
    "Vote",
    "ImpactAssessment",
    "DecisionOutcome",
    "Decision",
    "AuditEntry",
    "EscalationRule",
    "Escalation",
    "DecisionTemplate",
    "Notification",
    "Delegation",
    "Comment",
    "DecisionManager",
    "get_decision_manager",
    "propose_decision",
]
