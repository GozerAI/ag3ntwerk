"""Tests for VinzyMeteringPlugin — delegation and tool call metering."""

from unittest.mock import MagicMock, patch

from ag3ntwerk.core.plugins.vinzy_metering import VinzyMeteringPlugin


class TestVinzyMeteringPlugin:
    def test_plugin_init(self):
        plugin = VinzyMeteringPlugin(
            license_key="test-key",
            server_url="http://localhost:8080",
        )
        assert plugin.name == "vinzy-metering"
        assert plugin._license_key == "test-key"
        assert plugin._server_url == "http://localhost:8080"
        assert plugin._client is None  # lazy init

    def test_meter_delegation_records_usage(self):
        plugin = VinzyMeteringPlugin(license_key="test-key")
        mock_client = MagicMock()
        plugin._client = mock_client

        event = {
            "delegate": "Forge",
            "task_type": "technical_review",
            "manager": "Overwatch",
        }
        plugin.meter_delegation(event)

        mock_client.record_usage.assert_called_once_with(
            metric="agent.Forge.delegations",
            value=1.0,
            metadata={"task_type": "technical_review", "manager": "Overwatch"},
        )

    def test_meter_tool_use_records_usage(self):
        plugin = VinzyMeteringPlugin(license_key="test-key")
        mock_client = MagicMock()
        plugin._client = mock_client

        event = {
            "agent_code": "Keystone",
            "tool_name": "financial_analysis",
        }
        plugin.meter_tool_use(event)

        mock_client.record_usage.assert_called_once_with(
            metric="agent.Keystone.tool_calls",
            value=1.0,
            metadata={"tool_name": "financial_analysis"},
        )

    def test_metric_format(self):
        """Verify the agent metric format convention."""
        plugin = VinzyMeteringPlugin(license_key="test-key")
        mock_client = MagicMock()
        plugin._client = mock_client

        plugin.meter_delegation({"delegate": "Foundry", "task_type": "", "manager": ""})
        call_args = mock_client.record_usage.call_args
        metric = call_args.kwargs.get("metric") or call_args[1].get("metric")
        assert metric.startswith("agent.")
        assert ".delegations" in metric

        mock_client.reset_mock()
        plugin.meter_tool_use({"agent_code": "Citadel", "tool_name": ""})
        call_args = mock_client.record_usage.call_args
        metric = call_args.kwargs.get("metric") or call_args[1].get("metric")
        assert metric.startswith("agent.")
        assert ".tool_calls" in metric


class TestVinzyEntitlementGating:
    """Tests for pre-execute entitlement checking hooks."""

    def _make_plugin_with_mock(self):
        plugin = VinzyMeteringPlugin(license_key="test-key")
        mock_client = MagicMock()
        plugin._client = mock_client
        return plugin, mock_client

    def test_delegation_entitlement_allowed(self):
        """Valid agent passes entitlement check."""
        plugin, mock_client = self._make_plugin_with_mock()
        mock_client.validate_agent.return_value = MagicMock(valid=True)

        result = plugin.check_delegation_entitlement({"delegate": "Forge"})
        assert result is None
        mock_client.validate_agent.assert_called_once_with("Forge")

    def test_delegation_entitlement_blocked(self):
        """Invalid agent is blocked with reason."""
        plugin, mock_client = self._make_plugin_with_mock()
        mock_client.validate_agent.return_value = MagicMock(
            valid=False,
            code="NOT_ENTITLED",
            message="Agent Forge not licensed",
        )

        result = plugin.check_delegation_entitlement({"delegate": "Forge"})
        assert result is not None
        assert result["blocked"] is True
        assert "not licensed" in result["reason"]

    def test_delegation_entitlement_graceful_on_connection_error(self):
        """Connection errors allow execution (graceful degradation)."""
        plugin, mock_client = self._make_plugin_with_mock()
        mock_client.validate_agent.return_value = MagicMock(
            valid=False,
            code="CONNECTION_ERROR",
            message="Server unreachable",
        )

        result = plugin.check_delegation_entitlement({"delegate": "Forge"})
        assert result is None  # allowed

    def test_delegation_entitlement_graceful_on_server_error(self):
        """Server errors allow execution (graceful degradation)."""
        plugin, mock_client = self._make_plugin_with_mock()
        mock_client.validate_agent.return_value = MagicMock(
            valid=False,
            code="SERVER_ERROR",
            message="500",
        )

        result = plugin.check_delegation_entitlement({"delegate": "Forge"})
        assert result is None

    def test_delegation_entitlement_graceful_on_exception(self):
        """Exceptions allow execution (graceful degradation)."""
        plugin, mock_client = self._make_plugin_with_mock()
        mock_client.validate_agent.side_effect = RuntimeError("Network down")

        result = plugin.check_delegation_entitlement({"delegate": "Forge"})
        assert result is None

    def test_delegation_entitlement_empty_delegate(self):
        """Empty delegate code returns None (skip check)."""
        plugin, mock_client = self._make_plugin_with_mock()

        result = plugin.check_delegation_entitlement({"delegate": ""})
        assert result is None
        mock_client.validate_agent.assert_not_called()

    def test_tool_entitlement_allowed(self):
        """Valid agent passes tool entitlement check."""
        plugin, mock_client = self._make_plugin_with_mock()
        mock_client.validate_agent.return_value = MagicMock(valid=True)

        result = plugin.check_tool_entitlement({"agent_code": "Keystone", "tool_name": "budget"})
        assert result is None
        mock_client.validate_agent.assert_called_once_with("Keystone")

    def test_tool_entitlement_blocked(self):
        """Invalid agent is blocked for tool use."""
        plugin, mock_client = self._make_plugin_with_mock()
        mock_client.validate_agent.return_value = MagicMock(
            valid=False,
            code="NOT_ENTITLED",
            message="Agent Keystone not licensed",
        )

        result = plugin.check_tool_entitlement({"agent_code": "Keystone", "tool_name": "budget"})
        assert result is not None
        assert result["blocked"] is True

    def test_tool_entitlement_graceful_on_connection_error(self):
        """Connection errors allow tool execution."""
        plugin, mock_client = self._make_plugin_with_mock()
        mock_client.validate_agent.return_value = MagicMock(
            valid=False,
            code="JSON_ERROR",
            message="Bad JSON",
        )

        result = plugin.check_tool_entitlement({"agent_code": "Keystone"})
        assert result is None

    def test_tool_entitlement_empty_agent_code(self):
        """Empty agent code returns None (skip check)."""
        plugin, mock_client = self._make_plugin_with_mock()

        result = plugin.check_tool_entitlement({"agent_code": ""})
        assert result is None
        mock_client.validate_agent.assert_not_called()

    def test_hook_priorities(self):
        """Entitlement hooks run before metering hooks."""
        plugin = VinzyMeteringPlugin(license_key="test-key")
        hooks = plugin.get_hooks()

        entitlement_hooks = [h for h in hooks if "entitlement" in h.handler.__name__]
        metering_hooks = [h for h in hooks if "meter" in h.handler.__name__]

        for eh in entitlement_hooks:
            assert eh.priority == 10
        for mh in metering_hooks:
            assert mh.priority == 50

    def test_graceful_codes_set(self):
        """Verify the graceful degradation codes are complete."""
        assert "CONNECTION_ERROR" in VinzyMeteringPlugin._GRACEFUL_CODES
        assert "SERVER_ERROR" in VinzyMeteringPlugin._GRACEFUL_CODES
        assert "JSON_ERROR" in VinzyMeteringPlugin._GRACEFUL_CODES
