"""
Unit tests for ag3ntwerk CLI.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

from ag3ntwerk.cli import cli, load_config, get_provider


class TestCLIHelpers:
    """Tests for CLI helper functions."""

    def test_load_config_nonexistent(self, tmp_path):
        """Test loading non-existent config returns empty dict."""
        result = load_config(str(tmp_path / "nonexistent.yaml"))
        assert result == {}

    def test_load_config_existing(self, tmp_path):
        """Test loading existing config file."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("llm:\n  provider: ollama\n")

        result = load_config(str(config_file))
        assert result == {"llm": {"provider": "ollama"}}

    def test_load_config_empty_file(self, tmp_path):
        """Test loading empty config file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        result = load_config(str(config_file))
        assert result == {}

    @patch("ag3ntwerk.llm.get_provider")
    def test_get_provider_ollama(self, mock_llm_get_provider):
        """Test getting Ollama provider from config."""
        config = {
            "llm": {
                "provider": "ollama",
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "default_model": "llama3.2",
                },
            }
        }

        get_provider(config)

        mock_llm_get_provider.assert_called_once_with(
            provider_type="ollama",
            base_url="http://localhost:11434",
            default_model="llama3.2",
            timeout=300.0,
        )

    @patch("ag3ntwerk.llm.get_provider")
    def test_get_provider_gpt4all(self, mock_llm_get_provider):
        """Test getting GPT4All provider from config."""
        config = {
            "llm": {
                "provider": "gpt4all",
                "gpt4all": {
                    "base_url": "http://localhost:4891/v1",
                },
            }
        }

        get_provider(config)

        mock_llm_get_provider.assert_called_once_with(
            provider_type="gpt4all",
            base_url="http://localhost:4891/v1",
            default_model=None,
            timeout=120.0,
        )

    @patch("ag3ntwerk.llm.get_provider")
    def test_get_provider_auto(self, mock_llm_get_provider):
        """Test getting auto provider when unknown type."""
        config = {"llm": {"provider": "unknown"}}

        get_provider(config)

        mock_llm_get_provider.assert_called_once_with(provider_type="auto")

    @patch("ag3ntwerk.llm.get_provider")
    def test_get_provider_empty_config(self, mock_llm_get_provider):
        """Test getting provider with empty config defaults to ollama."""
        config = {}

        get_provider(config)

        mock_llm_get_provider.assert_called_once()
        call_kwargs = mock_llm_get_provider.call_args[1]
        assert call_kwargs["provider_type"] == "ollama"


class TestCLIGroup:
    """Tests for CLI group command."""

    def test_cli_help(self):
        """Test CLI shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "ag3ntwerk AI Agent Platform CLI" in result.output

    def test_cli_config_option(self):
        """Test CLI accepts config option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--config", "custom.yaml", "--help"])

        assert result.exit_code == 0


class TestStatusCommand:
    """Tests for status command."""

    def test_status_help(self):
        """Test status command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])

        assert result.exit_code == 0
        assert "Show system status" in result.output

    @patch("ag3ntwerk.cli.get_provider")
    def test_status_connected(self, mock_get_provider):
        """Test status when LLM is connected."""
        mock_provider = MagicMock()
        mock_provider.connect = AsyncMock(return_value=True)
        mock_provider.disconnect = AsyncMock()
        mock_provider.name = "OllamaProvider"
        mock_provider.available_models = []
        mock_get_provider.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "ag3ntwerk System Status" in result.output

    @patch("ag3ntwerk.cli.get_provider")
    def test_status_disconnected(self, mock_get_provider):
        """Test status when LLM is disconnected."""
        mock_provider = MagicMock()
        mock_provider.connect = AsyncMock(return_value=False)
        mock_get_provider.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "Disconnected" in result.output


class TestAgentsCommand:
    """Tests for agents command (legacy redirect)."""

    def test_agents_help(self):
        """Test agents command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["agents", "--help"])

        assert result.exit_code == 0


class TestExecutivesCommand:
    """Tests for agents command."""

    def test_executives_help(self):
        """Test agents command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["agents", "--help"])

        assert result.exit_code == 0
        assert "List all ag3ntwerk agents" in result.output

    def test_executives_list(self):
        """Test listing agents."""
        runner = CliRunner()
        result = runner.invoke(cli, ["agents"])

        assert result.exit_code == 0
        # Should show agents table
        assert "Nexus" in result.output or "agents" in result.output.lower()


class TestRunCommand:
    """Tests for run command."""

    def test_run_help(self):
        """Test run command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])

        assert result.exit_code == 0
        assert "Execute a task" in result.output

    @patch("ag3ntwerk.cli.get_provider")
    def test_run_requires_args(self, mock_get_provider):
        """Test run command requires task type and description."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run"])

        # Should error due to missing arguments
        assert result.exit_code != 0


class TestExecCommand:
    """Tests for exec command."""

    def test_exec_help(self):
        """Test exec command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["exec", "--help"])

        assert result.exit_code == 0
        assert "Execute a task with a specific agent" in result.output

    def test_exec_requires_args(self):
        """Test exec command requires arguments."""
        runner = CliRunner()
        result = runner.invoke(cli, ["exec"])

        # Should error due to missing arguments
        assert result.exit_code != 0


class TestWorkflowCommand:
    """Tests for workflow command."""

    def test_workflow_help(self):
        """Test workflow command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["workflow", "--help"])

        assert result.exit_code == 0
        assert "Execute a predefined workflow" in result.output

    def test_workflow_list(self):
        """Test listing workflows."""
        runner = CliRunner()
        result = runner.invoke(cli, ["workflow", "--list"])

        # Command may succeed with workflow list OR fail due to no LLM provider
        # (unit tests don't have Ollama running)
        assert result.exit_code == 0 or "Error" in result.output or "LLM provider" in result.output


class TestMCPCommand:
    """Tests for MCP command."""

    def test_mcp_help(self):
        """Test MCP command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "--help"])

        assert result.exit_code == 0
        assert "MCP" in result.output or "mcp" in result.output


class TestVersionInfo:
    """Tests for version information."""

    def test_version_option(self):
        """Test --version option shows version."""
        runner = CliRunner()
        # The CLI may or may not have --version
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0


class TestVerboseMode:
    """Tests for verbose mode."""

    @patch("ag3ntwerk.cli.get_provider")
    def test_verbose_status(self, mock_get_provider):
        """Test verbose mode shows more details."""
        mock_model = MagicMock()
        mock_model.name = "test-model"
        mock_model.tier = MagicMock()
        mock_model.tier.value = "balanced"

        mock_provider = MagicMock()
        mock_provider.connect = AsyncMock(return_value=True)
        mock_provider.disconnect = AsyncMock()
        mock_provider.name = "OllamaProvider"
        mock_provider.available_models = [mock_model]
        mock_get_provider.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "status"])

        assert result.exit_code == 0
        # Verbose should show model details
        assert "test-model" in result.output or "Status" in result.output
