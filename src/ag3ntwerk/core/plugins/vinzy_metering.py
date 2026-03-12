"""Vinzy metering plugin — auto-meters agent delegations and tool calls."""

import logging
from typing import Any

from ag3ntwerk.core.plugins.base import Plugin
from ag3ntwerk.core.plugins._utils import hook

logger = logging.getLogger(__name__)


class VinzyMeteringPlugin(Plugin):
    """
    Wires into ag3ntwerk's Manager.delegate() and tool execution hooks
    to auto-meter every agent action via the Vinzy-Engine SDK.
    """

    name = "vinzy-metering"
    version = "1.0.0"
    description = "Auto-meter agent delegations and tool calls via Vinzy-Engine"
    author = "ag3ntwerk"

    def __init__(self, license_key: str, server_url: str = "http://localhost:8080"):
        super().__init__()
        self._license_key = license_key
        self._server_url = server_url
        self._client = None

    def _get_client(self):
        """Lazy-init the Vinzy LicenseClient."""
        if self._client is None:
            from vinzy_engine import LicenseClient

            self._client = LicenseClient(
                server_url=self._server_url,
                license_key=self._license_key,
            )
        return self._client

    # Connection-error codes from the Vinzy SDK indicate the server is
    # unreachable, not that the agent is unentitled.  Graceful degradation:
    # allow execution when Vinzy is down.
    _GRACEFUL_CODES = frozenset(
        {
            "CONNECTION_ERROR",
            "SERVER_ERROR",
            "JSON_ERROR",
        }
    )

    @hook("delegation.pre_execute", priority=10)
    def check_delegation_entitlement(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Block delegation if the delegate agent is not entitled."""
        agent_code = event.get("delegate", "")
        if not agent_code:
            return None
        try:
            result = self._get_client().validate_agent(agent_code)
            if result.valid:
                return None
            if result.code in self._GRACEFUL_CODES:
                logger.warning(
                    "Vinzy entitlement check unavailable for %s (%s); allowing",
                    agent_code,
                    result.code,
                )
                return None
            return {"blocked": True, "reason": result.message or f"Agent {agent_code} not entitled"}
        except Exception as exc:
            logger.warning("Vinzy entitlement check failed for %s: %s; allowing", agent_code, exc)
            return None

    @hook("tool.pre_execute", priority=10)
    def check_tool_entitlement(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Block tool execution if the owning agent is not entitled."""
        agent_code = event.get("agent_code", "")
        if not agent_code:
            return None
        try:
            result = self._get_client().validate_agent(agent_code)
            if result.valid:
                return None
            if result.code in self._GRACEFUL_CODES:
                logger.warning(
                    "Vinzy entitlement check unavailable for %s (%s); allowing",
                    agent_code,
                    result.code,
                )
                return None
            return {"blocked": True, "reason": result.message or f"Agent {agent_code} not entitled"}
        except Exception as exc:
            logger.warning("Vinzy entitlement check failed for %s: %s; allowing", agent_code, exc)
            return None

    @hook("delegation.post_execute", priority=50)
    def meter_delegation(self, event: dict[str, Any]) -> None:
        """Record a delegation event for the delegate agent."""
        agent_code = event.get("delegate", "unknown")
        client = self._get_client()
        client.record_usage(
            metric=f"agent.{agent_code}.delegations",
            value=1.0,
            metadata={
                "task_type": event.get("task_type", ""),
                "manager": event.get("manager", ""),
            },
        )

    @hook("tool.post_execute", priority=50)
    def meter_tool_use(self, event: dict[str, Any]) -> None:
        """Record a tool execution event for the agent."""
        agent_code = event.get("agent_code", "unknown")
        client = self._get_client()
        client.record_usage(
            metric=f"agent.{agent_code}.tool_calls",
            value=1.0,
            metadata={
                "tool_name": event.get("tool_name", ""),
            },
        )
