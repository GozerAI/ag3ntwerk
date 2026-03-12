"""
Tests for ag3ntwerk Tools Configuration Module.

Tests ToolsConfig, ConfigManager, and configuration loading.
"""

import os
import pytest
from unittest.mock import patch

from ag3ntwerk.tools.config import (
    ToolsConfig,
    IntegrationConfig,
    ExecutorConfig,
    WorkflowConfig,
    ConfigManager,
    get_config_manager,
    get_config,
)


class TestIntegrationConfig:
    """Tests for IntegrationConfig class."""

    def test_create_config(self):
        """Test creating integration config."""
        config = IntegrationConfig(
            name="slack",
            enabled=True,
            credentials={"bot_token": "xoxb-123"},
            settings={"channel": "#general"},
        )

        assert config.name == "slack"
        assert config.enabled is True
        assert config.credentials["bot_token"] == "xoxb-123"

    def test_get_credential_direct(self):
        """Test getting a direct credential value."""
        config = IntegrationConfig(
            name="test",
            credentials={"api_key": "secret123"},
        )

        value = config.get_credential("api_key")

        assert value == "secret123"

    def test_get_credential_from_env(self):
        """Test getting a credential from environment variable."""
        config = IntegrationConfig(
            name="test",
            credentials={"api_key": "${TEST_API_KEY}"},
        )

        with patch.dict(os.environ, {"TEST_API_KEY": "env_secret"}):
            value = config.get_credential("api_key")

        assert value == "env_secret"

    def test_get_credential_default(self):
        """Test getting a credential with default value."""
        config = IntegrationConfig(name="test")

        value = config.get_credential("missing", "default_value")

        assert value == "default_value"

    def test_get_setting(self):
        """Test getting a setting value."""
        config = IntegrationConfig(
            name="test",
            settings={"timeout": 30, "retries": 3},
        )

        assert config.get_setting("timeout") == 30
        assert config.get_setting("retries") == 3
        assert config.get_setting("missing", 5) == 5


class TestExecutorConfig:
    """Tests for ExecutorConfig class."""

    def test_default_values(self):
        """Test default executor configuration values."""
        config = ExecutorConfig()

        assert config.default_timeout == 300.0
        assert config.max_retries == 3
        assert config.requests_per_minute == 60

    def test_custom_values(self):
        """Test custom executor configuration values."""
        config = ExecutorConfig(
            default_timeout=60.0,
            max_retries=5,
            requests_per_minute=120,
        )

        assert config.default_timeout == 60.0
        assert config.max_retries == 5
        assert config.requests_per_minute == 120


class TestWorkflowConfig:
    """Tests for WorkflowConfig class."""

    def test_default_values(self):
        """Test default workflow configuration values."""
        config = WorkflowConfig()

        assert config.default_on_error == "fail"
        assert config.max_parallel_steps == 10

    def test_custom_values(self):
        """Test custom workflow configuration values."""
        config = WorkflowConfig(
            default_on_error="continue",
            max_parallel_steps=5,
        )

        assert config.default_on_error == "continue"
        assert config.max_parallel_steps == 5


class TestToolsConfig:
    """Tests for ToolsConfig class."""

    def test_is_tool_enabled_all_enabled(self):
        """Test tool enabled check when all tools are enabled."""
        config = ToolsConfig()

        assert config.is_tool_enabled("any_tool") is True

    def test_is_tool_enabled_in_enabled_list(self):
        """Test tool enabled check with enabled list."""
        config = ToolsConfig(enabled_tools=["tool_a", "tool_b"])

        assert config.is_tool_enabled("tool_a") is True
        assert config.is_tool_enabled("tool_c") is False

    def test_is_tool_disabled(self):
        """Test tool enabled check with disabled list."""
        config = ToolsConfig(disabled_tools=["disabled_tool"])

        assert config.is_tool_enabled("normal_tool") is True
        assert config.is_tool_enabled("disabled_tool") is False

    def test_get_integration_config(self):
        """Test getting integration configuration."""
        config = ToolsConfig(
            integrations={
                "slack": IntegrationConfig(name="slack", credentials={"token": "abc"}),
            }
        )

        slack_config = config.get_integration_config("slack")

        assert slack_config is not None
        assert slack_config.credentials["token"] == "abc"

    def test_get_integration_config_missing(self):
        """Test getting missing integration configuration."""
        config = ToolsConfig()

        result = config.get_integration_config("nonexistent")

        assert result is None

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "enabled_tools": ["tool_a", "tool_b"],
            "disabled_tools": ["tool_c"],
            "executor": {
                "default_timeout": 120.0,
                "max_retries": 5,
            },
            "workflow": {
                "default_on_error": "continue",
            },
            "integrations": {
                "slack": {
                    "enabled": True,
                    "credentials": {"bot_token": "xoxb-123"},
                    "settings": {"default_channel": "#general"},
                },
            },
        }

        config = ToolsConfig.from_dict(data)

        assert "tool_a" in config.enabled_tools
        assert config.executor.default_timeout == 120.0
        assert config.workflow.default_on_error == "continue"
        assert config.integrations["slack"].credentials["bot_token"] == "xoxb-123"

    def test_from_env(self):
        """Test creating config from environment variables."""
        env_vars = {
            "AGENTWERK_TOOL_TIMEOUT": "60",
            "AGENTWERK_TOOL_MAX_RETRIES": "5",
            "AGENTWERK_INTEGRATION_SLACK_BOT_TOKEN": "xoxb-env",
            "AGENTWERK_INTEGRATION_GITHUB_TOKEN": "ghp-env",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = ToolsConfig.from_env()

        assert config.executor.default_timeout == 60.0
        assert config.executor.max_retries == 5
        assert "slack" in config.integrations
        assert "github" in config.integrations


class TestConfigManager:
    """Tests for ConfigManager class."""

    def test_singleton(self):
        """Test ConfigManager is a singleton."""
        manager1 = ConfigManager.get_instance()
        manager2 = ConfigManager.get_instance()

        # Reset for other tests
        ConfigManager._instance = None

        assert manager1 is manager2

    def test_load_from_dict(self):
        """Test loading configuration from dictionary."""
        manager = ConfigManager()

        manager.load_from_dict(
            {
                "executor": {"default_timeout": 60.0},
            }
        )

        assert manager.config.executor.default_timeout == 60.0

    def test_load_from_env(self):
        """Test loading configuration from environment."""
        manager = ConfigManager()

        with patch.dict(os.environ, {"AGENTWERK_TOOL_TIMEOUT": "45"}, clear=False):
            manager.load_from_env()

        assert manager.config.executor.default_timeout == 45.0

    def test_merge_config(self):
        """Test configuration merging."""
        manager = ConfigManager()

        # Load first config
        manager.load_from_dict(
            {
                "executor": {"default_timeout": 60.0},
                "integrations": {
                    "slack": {"credentials": {"token": "first"}},
                },
            }
        )

        # Load second config (should merge)
        manager.load_from_dict(
            {
                "executor": {"max_retries": 10},
                "integrations": {
                    "slack": {"credentials": {"secret": "second"}},
                    "github": {"credentials": {"token": "gh-token"}},
                },
            }
        )

        # Check merged values
        assert manager.config.executor.default_timeout == 60.0  # From first
        assert manager.config.executor.max_retries == 10  # From second
        assert manager.config.integrations["slack"].credentials["token"] == "first"
        assert manager.config.integrations["slack"].credentials["secret"] == "second"
        assert "github" in manager.config.integrations

    def test_get_integration(self):
        """Test getting integration configuration."""
        manager = ConfigManager()
        manager.load_from_dict(
            {
                "integrations": {
                    "slack": {"credentials": {"token": "xoxb-123"}},
                },
            }
        )

        integration = manager.get_integration("slack")

        assert integration is not None
        assert integration.credentials["token"] == "xoxb-123"

    def test_is_tool_enabled(self):
        """Test checking if tool is enabled."""
        manager = ConfigManager()
        manager.load_from_dict(
            {
                "disabled_tools": ["disabled_tool"],
            }
        )

        assert manager.is_tool_enabled("normal_tool") is True
        assert manager.is_tool_enabled("disabled_tool") is False

    def test_set_integration_credential(self):
        """Test setting integration credential at runtime."""
        manager = ConfigManager()

        manager.set_integration_credential("slack", "bot_token", "xoxb-runtime")

        integration = manager.get_integration("slack")
        assert integration.credentials["bot_token"] == "xoxb-runtime"


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_config_manager(self):
        """Test get_config_manager returns singleton."""
        ConfigManager._instance = None

        manager = get_config_manager()

        assert manager is not None
        assert isinstance(manager, ConfigManager)

        ConfigManager._instance = None

    def test_get_config(self):
        """Test get_config returns current configuration."""
        ConfigManager._instance = None

        config = get_config()

        assert config is not None
        assert isinstance(config, ToolsConfig)

        ConfigManager._instance = None
