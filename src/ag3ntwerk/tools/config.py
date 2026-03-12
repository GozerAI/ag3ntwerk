"""
Tool Configuration for ag3ntwerk.

Provides configuration management for tools and integrations.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class IntegrationConfig:
    """Configuration for a specific integration."""

    name: str
    enabled: bool = True
    credentials: Dict[str, str] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)

    def get_credential(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a credential value, checking env vars first."""
        # First check if it's an env var reference
        value = self.credentials.get(key, default)
        if value and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var)
        return value

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)


@dataclass
class ExecutorConfig:
    """Configuration for the tool executor."""

    default_timeout: float = 300.0
    max_retries: int = 3
    initial_retry_delay: float = 1.0
    max_retry_delay: float = 30.0
    exponential_base: float = 2.0
    requests_per_minute: int = 60
    burst_size: int = 10
    max_history: int = 1000


@dataclass
class WorkflowConfig:
    """Configuration for the workflow engine."""

    default_on_error: str = "fail"  # fail, continue
    max_parallel_steps: int = 10
    step_timeout: float = 600.0


@dataclass
class ToolsConfig:
    """Main configuration for the tools system."""

    enabled_tools: List[str] = field(default_factory=list)  # Empty = all enabled
    disabled_tools: List[str] = field(default_factory=list)
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    integrations: Dict[str, IntegrationConfig] = field(default_factory=dict)

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a tool is enabled."""
        if tool_name in self.disabled_tools:
            return False
        if self.enabled_tools and tool_name not in self.enabled_tools:
            return False
        return True

    def get_integration_config(self, name: str) -> Optional[IntegrationConfig]:
        """Get configuration for an integration."""
        return self.integrations.get(name)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolsConfig":
        """Create config from dictionary."""
        executor_data = data.get("executor", {})
        workflow_data = data.get("workflow", {})
        integrations_data = data.get("integrations", {})

        integrations = {}
        for name, config in integrations_data.items():
            integrations[name] = IntegrationConfig(
                name=name,
                enabled=config.get("enabled", True),
                credentials=config.get("credentials", {}),
                settings=config.get("settings", {}),
            )

        return cls(
            enabled_tools=data.get("enabled_tools", []),
            disabled_tools=data.get("disabled_tools", []),
            executor=ExecutorConfig(**executor_data) if executor_data else ExecutorConfig(),
            workflow=WorkflowConfig(**workflow_data) if workflow_data else WorkflowConfig(),
            integrations=integrations,
        )

    @classmethod
    def from_yaml(cls, path: str) -> "ToolsConfig":
        """Load config from YAML file."""
        try:
            import yaml

            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
            return cls.from_dict(data.get("tools", data))
        except ImportError:
            logger.warning("PyYAML not installed, using default config")
            return cls()
        except FileNotFoundError:
            logger.warning(f"Config file not found: {path}")
            return cls()

    @classmethod
    def from_env(cls) -> "ToolsConfig":
        """Create config from environment variables."""
        config = cls()

        # Executor settings
        if os.environ.get("AGENTWERK_TOOL_TIMEOUT"):
            config.executor.default_timeout = float(os.environ["AGENTWERK_TOOL_TIMEOUT"])
        if os.environ.get("AGENTWERK_TOOL_MAX_RETRIES"):
            config.executor.max_retries = int(os.environ["AGENTWERK_TOOL_MAX_RETRIES"])
        if os.environ.get("AGENTWERK_TOOL_RATE_LIMIT"):
            config.executor.requests_per_minute = int(os.environ["AGENTWERK_TOOL_RATE_LIMIT"])

        # Auto-detect integration configs from env vars
        # Format: AGENTWERK_INTEGRATION_{NAME}_{KEY}
        prefix = "AGENTWERK_INTEGRATION_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix) :].split("_", 1)
                if len(parts) == 2:
                    integration_name = parts[0].lower()
                    credential_key = parts[1].lower()

                    if integration_name not in config.integrations:
                        config.integrations[integration_name] = IntegrationConfig(
                            name=integration_name
                        )
                    config.integrations[integration_name].credentials[credential_key] = value

        return config


class ConfigManager:
    """
    Manages tool configuration with multiple sources.

    Configuration priority (highest to lowest):
    1. Environment variables
    2. Config file
    3. Defaults

    Example:
        manager = ConfigManager()
        manager.load_from_yaml("config/tools.yaml")

        # Get integration config
        slack_config = manager.get_integration("slack")
        token = slack_config.get_credential("bot_token")
    """

    _instance: Optional["ConfigManager"] = None

    def __init__(self):
        self._config = ToolsConfig()
        self._loaded = False

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_from_yaml(self, path: str) -> None:
        """Load configuration from YAML file."""
        file_config = ToolsConfig.from_yaml(path)
        self._merge_config(file_config)
        self._loaded = True

    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """Load configuration from dictionary."""
        dict_config = ToolsConfig.from_dict(data)
        self._merge_config(dict_config)
        self._loaded = True

    def load_from_env(self) -> None:
        """Load configuration from environment."""
        env_config = ToolsConfig.from_env()
        self._merge_config(env_config)
        self._loaded = True

    def _merge_config(self, new_config: ToolsConfig) -> None:
        """Merge new config into existing config."""
        # Merge lists
        if new_config.enabled_tools:
            self._config.enabled_tools = new_config.enabled_tools
        if new_config.disabled_tools:
            self._config.disabled_tools.extend(new_config.disabled_tools)

        # Merge executor config (non-default values override)
        default_executor = ExecutorConfig()
        for field_name in [
            "default_timeout",
            "max_retries",
            "initial_retry_delay",
            "max_retry_delay",
            "exponential_base",
            "requests_per_minute",
            "burst_size",
            "max_history",
        ]:
            new_value = getattr(new_config.executor, field_name)
            default_value = getattr(default_executor, field_name)
            if new_value != default_value:
                setattr(self._config.executor, field_name, new_value)

        # Merge workflow config
        default_workflow = WorkflowConfig()
        for field_name in ["default_on_error", "max_parallel_steps", "step_timeout"]:
            new_value = getattr(new_config.workflow, field_name)
            default_value = getattr(default_workflow, field_name)
            if new_value != default_value:
                setattr(self._config.workflow, field_name, new_value)

        # Merge integrations
        for name, integration in new_config.integrations.items():
            if name in self._config.integrations:
                # Merge credentials and settings
                self._config.integrations[name].credentials.update(integration.credentials)
                self._config.integrations[name].settings.update(integration.settings)
                if not integration.enabled:
                    self._config.integrations[name].enabled = False
            else:
                self._config.integrations[name] = integration

    @property
    def config(self) -> ToolsConfig:
        """Get the current configuration."""
        return self._config

    def get_integration(self, name: str) -> Optional[IntegrationConfig]:
        """Get configuration for an integration."""
        return self._config.get_integration_config(name)

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a tool is enabled."""
        return self._config.is_tool_enabled(tool_name)

    def get_executor_config(self) -> ExecutorConfig:
        """Get executor configuration."""
        return self._config.executor

    def get_workflow_config(self) -> WorkflowConfig:
        """Get workflow configuration."""
        return self._config.workflow

    def set_integration_credential(
        self,
        integration_name: str,
        key: str,
        value: str,
    ) -> None:
        """Set a credential for an integration at runtime."""
        if integration_name not in self._config.integrations:
            self._config.integrations[integration_name] = IntegrationConfig(name=integration_name)
        self._config.integrations[integration_name].credentials[key] = value


def get_config_manager() -> ConfigManager:
    """Get the global config manager instance."""
    return ConfigManager.get_instance()


def get_config() -> ToolsConfig:
    """Get the current tools configuration."""
    return get_config_manager().config
