"""
Bootstrap Module for ag3ntwerk Tools.

Provides initialization and setup for the tools system.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ag3ntwerk.tools.config import ConfigManager, get_config_manager, ToolsConfig
from ag3ntwerk.tools.registry import get_registry, ToolRegistry
from ag3ntwerk.tools.executor import get_executor, ToolExecutor, RetryConfig, RateLimitConfig
from ag3ntwerk.tools.workflows import get_workflow_registry, WorkflowRegistry
from ag3ntwerk.tools.integrations import get_integration_factory

logger = logging.getLogger(__name__)


class ToolsBootstrap:
    """
    Bootstraps the ag3ntwerk tools system.

    Handles:
    - Configuration loading
    - Tool registration
    - Workflow registration
    - Integration setup

    Example:
        # Simple initialization
        bootstrap = ToolsBootstrap()
        bootstrap.initialize()

        # With custom config
        bootstrap = ToolsBootstrap(config_path="config/tools.yaml")
        bootstrap.initialize()

        # Or step by step
        bootstrap = ToolsBootstrap()
        bootstrap.load_config("config/tools.yaml")
        bootstrap.register_tools()
        bootstrap.register_workflows()
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        auto_discover: bool = True,
    ):
        """
        Initialize the bootstrap.

        Args:
            config_path: Path to configuration file
            auto_discover: Auto-discover config files
        """
        self.config_path = config_path
        self.auto_discover = auto_discover
        self._initialized = False

    def initialize(
        self,
        register_tools: bool = True,
        register_workflows: bool = True,
    ) -> None:
        """
        Initialize the tools system.

        Args:
            register_tools: Whether to register tools
            register_workflows: Whether to register predefined workflows
        """
        if self._initialized:
            logger.warning("Tools system already initialized")
            return

        logger.info("Initializing ag3ntwerk tools system...")

        # Load configuration
        self._load_configuration()

        # Configure executor
        self._configure_executor()

        # Register tools
        if register_tools:
            self.register_tools()

        # Register workflows
        if register_workflows:
            self.register_workflows()

        self._initialized = True
        logger.info("ag3ntwerk tools system initialized successfully")

    def _load_configuration(self) -> None:
        """Load configuration from various sources."""
        config_manager = get_config_manager()

        # Load from environment first
        config_manager.load_from_env()

        # Load from config file if provided
        if self.config_path:
            config_manager.load_from_yaml(self.config_path)
        elif self.auto_discover:
            # Try to find config file
            possible_paths = [
                "tools_config.yaml",
                "config/tools.yaml",
                "config/tools_config.yaml",
                Path.home() / ".ag3ntwerk" / "tools.yaml",
            ]

            for path in possible_paths:
                if Path(path).exists():
                    logger.info(f"Found config file: {path}")
                    config_manager.load_from_yaml(str(path))
                    break

        logger.debug(f"Configuration loaded: {config_manager.config}")

    def _configure_executor(self) -> None:
        """Configure the executor with loaded config."""
        config_manager = get_config_manager()
        executor_config = config_manager.get_executor_config()

        # Get the executor and configure it
        executor = get_executor()
        executor.retry_config = RetryConfig(
            max_attempts=executor_config.max_retries,
            initial_delay=executor_config.initial_retry_delay,
            max_delay=executor_config.max_retry_delay,
            exponential_base=executor_config.exponential_base,
        )
        executor.default_timeout = executor_config.default_timeout
        executor.max_history = executor_config.max_history

        # Configure rate limiter
        executor.rate_limiter.config.requests_per_minute = executor_config.requests_per_minute
        executor.rate_limiter.config.burst_size = executor_config.burst_size

    def register_tools(self, tools: Optional[List[str]] = None) -> int:
        """
        Register tools with the registry.

        Args:
            tools: Specific tools to register (all if None)

        Returns:
            Number of tools registered
        """
        from ag3ntwerk.tools.definitions import ALL_TOOLS

        registry = get_registry()
        config_manager = get_config_manager()
        registered = 0

        for tool_class in ALL_TOOLS:
            try:
                tool = tool_class()
                tool_name = tool.metadata.name

                # Check if specific tools requested
                if tools and tool_name not in tools:
                    continue

                # Check if tool is enabled in config
                if not config_manager.is_tool_enabled(tool_name):
                    logger.debug(f"Tool '{tool_name}' is disabled in config")
                    continue

                registry.register(tool)
                registered += 1

            except Exception as e:
                logger.warning(f"Failed to register tool {tool_class.__name__}: {e}")

        logger.info(f"Registered {registered} tools")
        return registered

    def register_workflows(self, workflows: Optional[List[str]] = None) -> int:
        """
        Register predefined workflows.

        Args:
            workflows: Specific workflows to register (all if None)

        Returns:
            Number of workflows registered
        """
        from ag3ntwerk.tools.predefined_workflows import get_workflow_builders

        workflow_registry = get_workflow_registry()
        registered = 0

        builders = get_workflow_builders()

        for name, builder in builders.items():
            if workflows and name not in workflows:
                continue

            try:
                workflow = builder()
                workflow_registry.register(workflow)
                registered += 1
            except Exception as e:
                logger.warning(f"Failed to register workflow '{name}': {e}")

        logger.info(f"Registered {registered} workflows")
        return registered

    def verify_integrations(self) -> Dict[str, bool]:
        """
        Verify that integrations are properly configured.

        Returns:
            Dict mapping integration name to availability status
        """
        from ag3ntwerk.tools.integrations import get_integration_factory
        from ag3ntwerk.tools.exceptions import IntegrationNotConfiguredError

        factory = get_integration_factory()
        results = {}

        integrations = [
            "slack",
            "discord",
            "email",
            "calendar",
            "notion",
            "sql",
            "dataframes",
            "visualization",
            "spreadsheets",
            "github",
            "docker",
            "cloud",
            "scraping",
            "news",
            "papers",
            "crm",
            "payments",
            "projects",
            "workflows",
            "pdf",
            "ocr",
            "generator",
        ]

        for name in integrations:
            try:
                factory.get(name, cached=False)
                results[name] = True
            except IntegrationNotConfiguredError:
                results[name] = False
            except Exception as e:
                logger.debug(f"Integration '{name}' check failed: {e}")
                results[name] = False

        return results

    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the tools system.

        Returns:
            Dict with status information
        """
        registry = get_registry()
        workflow_registry = get_workflow_registry()
        executor = get_executor()

        return {
            "initialized": self._initialized,
            "tools": {
                "total": len(registry.list_tools(enabled_only=False)),
                "enabled": len(registry.list_tools(enabled_only=True)),
            },
            "workflows": {
                "total": len(workflow_registry.list()),
            },
            "executor": {
                "history_size": len(executor._history),
                "stats": executor.get_stats(),
            },
            "integrations": self.verify_integrations(),
        }


# Global bootstrap instance
_bootstrap: Optional[ToolsBootstrap] = None


def get_bootstrap() -> ToolsBootstrap:
    """Get the global bootstrap instance."""
    global _bootstrap
    if _bootstrap is None:
        _bootstrap = ToolsBootstrap()
    return _bootstrap


def initialize(
    config_path: Optional[str] = None,
    register_tools: bool = True,
    register_workflows: bool = True,
) -> None:
    """
    Initialize the ag3ntwerk tools system.

    This is the main entry point for initializing the tools system.

    Example:
        from ag3ntwerk.tools.bootstrap import initialize

        # Basic initialization
        initialize()

        # With custom config
        initialize(config_path="config/tools.yaml")
    """
    global _bootstrap
    _bootstrap = ToolsBootstrap(config_path=config_path)
    _bootstrap.initialize(
        register_tools=register_tools,
        register_workflows=register_workflows,
    )


def get_status() -> Dict[str, Any]:
    """Get the current status of the tools system."""
    return get_bootstrap().get_status()


def verify_setup() -> bool:
    """
    Verify that the tools system is properly set up.

    Returns:
        True if the system is properly initialized
    """
    bootstrap = get_bootstrap()

    if not bootstrap._initialized:
        logger.error("Tools system not initialized")
        return False

    registry = get_registry()
    if len(registry.list_tools()) == 0:
        logger.error("No tools registered")
        return False

    return True
