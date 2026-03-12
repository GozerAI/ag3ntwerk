"""Tests for cross-agent capability contracts (capability registry)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.core.capability_registry import CapabilityRegistry, get_capability_registry
from ag3ntwerk.core.base import Manager, Task, TaskResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry():
    return CapabilityRegistry()


@pytest.fixture
def handler_ok():
    handler = AsyncMock(return_value={"status": "ok", "data": 42})
    return handler


@pytest.fixture
def handler_error():
    handler = AsyncMock(side_effect=Exception("handler failed"))
    return handler


# ---------------------------------------------------------------------------
# 1. Registration and lookup
# ---------------------------------------------------------------------------


def test_register_and_find_providers(registry):
    """Registering an agent with capabilities makes it discoverable."""
    registry.register("Forge", ["architecture", "code_review"], priority=10)
    providers = registry.find_providers("architecture")
    assert "Forge" in providers


def test_register_multiple_capabilities(registry):
    """An agent can provide multiple capabilities."""
    registry.register("Keystone", ["budgeting", "forecasting", "audit"], priority=5)
    assert "Keystone" in registry.find_providers("budgeting")
    assert "Keystone" in registry.find_providers("forecasting")
    assert "Keystone" in registry.find_providers("audit")


# ---------------------------------------------------------------------------
# 2. Multi-provider ranking by priority
# ---------------------------------------------------------------------------


def test_multi_provider_ranked_by_priority(registry):
    """Higher-priority providers appear first in find_providers."""
    registry.register("Forge", ["architecture"], priority=5)
    registry.register("Foundry", ["architecture"], priority=10)
    registry.register("Index", ["architecture"], priority=1)
    providers = registry.find_providers("architecture")
    assert providers == ["Foundry", "Forge", "Index"]


# ---------------------------------------------------------------------------
# 3. Request routing to handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_routes_to_handler(registry, handler_ok):
    """request() invokes the handler of the highest-priority provider."""
    registry.register("Forge", ["architecture"], handler=handler_ok, priority=10)
    result = await registry.request("architecture", {"depth": "deep"})
    handler_ok.assert_awaited_once_with("architecture", {"depth": "deep"})
    assert result["status"] == "ok"
    assert result["data"] == 42


# ---------------------------------------------------------------------------
# 4. No-provider returns error dict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_no_provider_returns_error(registry):
    """Requesting a capability with no providers yields an error dict."""
    result = await registry.request("unknown_cap", {})
    assert result.get("error") or "error" in result


# ---------------------------------------------------------------------------
# 5. Duplicate registration updates priority
# ---------------------------------------------------------------------------


def test_duplicate_registration_updates_priority(registry):
    """Re-registering the same agent updates its priority."""
    registry.register("Forge", ["architecture"], priority=1)
    registry.register("Forge", ["architecture"], priority=99)
    providers = registry.find_providers("architecture")
    # Forge should still be present (not duplicated) and reflect new priority
    assert providers.count("Forge") == 1
    # If another lower-priority agent exists, Forge should rank above it
    registry.register("Index", ["architecture"], priority=50)
    providers = registry.find_providers("architecture")
    assert providers[0] == "Forge"  # priority 99 > 50


# ---------------------------------------------------------------------------
# 6. Unregister removes agent
# ---------------------------------------------------------------------------


def test_unregister_removes_agent(registry):
    """Unregistering an agent removes it from all capability lookups."""
    registry.register("Forge", ["architecture", "code_review"], priority=10)
    registry.unregister("Forge")
    assert registry.find_providers("architecture") == []
    assert registry.find_providers("code_review") == []


def test_unregister_nonexistent_is_safe(registry):
    """Unregistering an agent that was never registered does not raise."""
    registry.unregister("DOES_NOT_EXIST")  # should not raise


# ---------------------------------------------------------------------------
# 7. list_all_capabilities returns correct mapping
# ---------------------------------------------------------------------------


def test_list_all_capabilities(registry):
    """list_all_capabilities returns {capability: [agents...]} mapping."""
    registry.register("Forge", ["architecture", "code_review"], priority=10)
    registry.register("Keystone", ["budgeting", "architecture"], priority=5)
    mapping = registry.list_all_capabilities()
    assert "architecture" in mapping
    assert "code_review" in mapping
    assert "budgeting" in mapping
    assert set(mapping["architecture"]) == {"Forge", "Keystone"}
    assert mapping["code_review"] == ["Forge"]
    assert mapping["budgeting"] == ["Keystone"]


# ---------------------------------------------------------------------------
# 8. get_agent_capabilities returns correct list
# ---------------------------------------------------------------------------


def test_get_agent_capabilities(registry):
    """get_agent_capabilities returns the list of capabilities for an agent."""
    registry.register("Forge", ["architecture", "code_review"], priority=10)
    caps = registry.get_agent_capabilities("Forge")
    assert set(caps) == {"architecture", "code_review"}


def test_get_agent_capabilities_unknown_agent(registry):
    """get_agent_capabilities returns empty list for unknown agent."""
    caps = registry.get_agent_capabilities("UNKNOWN")
    assert caps == []


# ---------------------------------------------------------------------------
# 9. find_providers returns empty list for unknown capability
# ---------------------------------------------------------------------------


def test_find_providers_unknown_capability(registry):
    """find_providers returns [] when no agent provides the capability."""
    registry.register("Forge", ["architecture"], priority=10)
    assert registry.find_providers("quantum_computing") == []


# ---------------------------------------------------------------------------
# 10. Request falls back to next provider on handler error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_falls_back_on_handler_error(registry, handler_error, handler_ok):
    """If the top-priority handler raises, request falls back to the next."""
    registry.register("Forge", ["architecture"], handler=handler_error, priority=10)
    registry.register("Foundry", ["architecture"], handler=handler_ok, priority=5)
    result = await registry.request("architecture", {"q": "design"})
    # The error handler should have been tried first
    handler_error.assert_awaited_once()
    # Then the fallback handler succeeds
    handler_ok.assert_awaited_once_with("architecture", {"q": "design"})
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_request_all_handlers_fail_returns_error(registry, handler_error):
    """If every provider's handler fails, request returns an error dict."""
    handler_error_2 = AsyncMock(side_effect=Exception("also failed"))
    registry.register("Forge", ["architecture"], handler=handler_error, priority=10)
    registry.register("Foundry", ["architecture"], handler=handler_error_2, priority=5)
    result = await registry.request("architecture", {})
    assert "error" in result


# ---------------------------------------------------------------------------
# 11. Manager.request_from_peer delegates to registry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manager_request_from_peer_delegates(registry, handler_ok):
    """Manager.request_from_peer proxies through the capability registry."""
    registry.register("Keystone", ["budgeting"], handler=handler_ok, priority=10)
    mgr = Manager.__new__(Manager)
    mgr._capability_registry = registry
    result = await mgr.request_from_peer("budgeting", amount=1000)
    handler_ok.assert_awaited_once()
    assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# 12. Manager.request_from_peer without registry returns error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manager_request_from_peer_no_registry():
    """Without a capability registry, request_from_peer returns an error."""
    mgr = Manager.__new__(Manager)
    mgr._capability_registry = None
    result = await mgr.request_from_peer("budgeting", amount=1000)
    assert "error" in result
