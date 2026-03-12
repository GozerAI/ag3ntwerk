"""
Tests for Swarm Bridge Facade — domain-aware routing.

Verifies that all 16 agents map to correct task tags,
domain models, and that metadata is properly constructed.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.modules.swarm_bridge.facade import (
    SwarmFacade,
    _AGENT_TASK_MAP,
    _AGENT_DOMAIN_MODEL,
    _TRAIT_ROUTING,
)


# =============================================================================
# Agent Mapping Coverage
# =============================================================================


ALL_EXECUTIVES = [
    "Overwatch",
    "Nexus",
    "Forge",
    "Keystone",
    "Echo",
    "Sentinel",
    "Blueprint",
    "Axiom",
    "Index",
    "Foundry",
    "Citadel",
    "Beacon",
    "Compass",
    "Vector",
    "Aegis",
    "Accord",
]


class TestAgentTaskMap:
    """Verify _AGENT_TASK_MAP covers all 16 agents."""

    def test_all_16_executives_present(self):
        for code in ALL_EXECUTIVES:
            assert code in _AGENT_TASK_MAP, f"{code} missing from _AGENT_TASK_MAP"

    def test_no_empty_tag_lists(self):
        for code, tags in _AGENT_TASK_MAP.items():
            assert len(tags) > 0, f"{code} has empty task tags"

    def test_technical_cluster_tags(self):
        for code in ["Forge", "Foundry", "Sentinel", "Citadel"]:
            tags = _AGENT_TASK_MAP[code]
            # Technical agents should have at least one technical tag
            tech_tags = {"code_review", "debugging", "security_audit", "architecture", "testing"}
            assert tech_tags & set(tags), f"{code} missing technical tags"

    def test_business_cluster_tags(self):
        for code in ["Keystone", "Vector", "Compass", "Blueprint"]:
            tags = _AGENT_TASK_MAP[code]
            biz_tags = {
                "cost_analysis",
                "revenue_analysis",
                "strategic_planning",
                "product_planning",
            }
            assert biz_tags & set(tags), f"{code} missing business tags"

    def test_operations_cluster_tags(self):
        for code in ["Overwatch", "Nexus", "Index", "Axiom"]:
            tags = _AGENT_TASK_MAP[code]
            ops_tags = {"task_routing", "data_governance", "research", "operational_planning"}
            assert ops_tags & set(tags), f"{code} missing operations tags"

    def test_governance_cluster_tags(self):
        for code in ["Accord", "Aegis", "Beacon", "Echo"]:
            tags = _AGENT_TASK_MAP[code]
            gov_tags = {"compliance", "risk_assessment", "customer_success", "marketing"}
            assert gov_tags & set(tags), f"{code} missing governance tags"


class TestAgentDomainModel:
    """Verify _AGENT_DOMAIN_MODEL maps all 16 agents to correct domain models."""

    def test_all_16_executives_present(self):
        for code in ALL_EXECUTIVES:
            assert code in _AGENT_DOMAIN_MODEL, f"{code} missing from _AGENT_DOMAIN_MODEL"

    def test_technical_cluster(self):
        for code in ["Forge", "Foundry", "Sentinel", "Citadel"]:
            assert _AGENT_DOMAIN_MODEL[code] == "ag3ntwerk-technical"

    def test_business_cluster(self):
        for code in ["Keystone", "Vector", "Compass", "Blueprint"]:
            assert _AGENT_DOMAIN_MODEL[code] == "ag3ntwerk-business"

    def test_operations_cluster(self):
        for code in ["Overwatch", "Nexus", "Index", "Axiom"]:
            assert _AGENT_DOMAIN_MODEL[code] == "ag3ntwerk-operations"

    def test_governance_cluster(self):
        for code in ["Accord", "Aegis", "Beacon", "Echo"]:
            assert _AGENT_DOMAIN_MODEL[code] == "ag3ntwerk-governance"

    def test_maps_are_consistent(self):
        """Both maps should have the exact same set of keys."""
        assert set(_AGENT_TASK_MAP.keys()) == set(_AGENT_DOMAIN_MODEL.keys())


# =============================================================================
# SwarmFacade Delegation
# =============================================================================


class TestSwarmFacadeDelegation:
    """Test that delegate_to_swarm passes correct metadata."""

    @pytest.fixture
    def facade(self):
        service = MagicMock()
        service.submit_task = AsyncMock(return_value="task-123")
        service.wait_for_task = AsyncMock(return_value={"status": "completed", "result": "ok"})
        return SwarmFacade(service)

    @pytest.mark.asyncio
    async def test_cto_sends_technical_model(self, facade):
        result = await facade.delegate_to_swarm("Review code", agent_code="Forge")
        call_kwargs = facade._service.submit_task.call_args
        metadata = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        assert metadata["preferred_model"] == "ag3ntwerk-technical"
        assert metadata["ag3ntwerk_agent"] == "Forge"
        assert "code_review" in metadata["task_tags"]

    @pytest.mark.asyncio
    async def test_cfo_sends_business_model(self, facade):
        result = await facade.delegate_to_swarm("Analyze costs", agent_code="Keystone")
        call_kwargs = facade._service.submit_task.call_args
        metadata = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        assert metadata["preferred_model"] == "ag3ntwerk-business"
        assert "cost_analysis" in metadata["task_tags"]

    @pytest.mark.asyncio
    async def test_cos_sends_operations_model(self, facade):
        result = await facade.delegate_to_swarm("Route this task", agent_code="Overwatch")
        call_kwargs = facade._service.submit_task.call_args
        metadata = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        assert metadata["preferred_model"] == "ag3ntwerk-operations"

    @pytest.mark.asyncio
    async def test_ccomo_sends_governance_model(self, facade):
        result = await facade.delegate_to_swarm("Compliance check", agent_code="Accord")
        call_kwargs = facade._service.submit_task.call_args
        metadata = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        assert metadata["preferred_model"] == "ag3ntwerk-governance"

    @pytest.mark.asyncio
    async def test_unknown_agent_falls_back_to_generalist(self, facade):
        result = await facade.delegate_to_swarm("General task", agent_code="UNKNOWN")
        call_kwargs = facade._service.submit_task.call_args
        metadata = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        assert metadata["preferred_model"] == "ag3ntwerk-model"
        assert metadata["task_tags"] == []

    @pytest.mark.asyncio
    async def test_wait_returns_result(self, facade):
        result = await facade.delegate_to_swarm("Test", agent_code="Forge", wait=True)
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_no_wait_returns_task_id(self, facade):
        result = await facade.delegate_to_swarm("Test", agent_code="Forge", wait=False)
        assert result["task_id"] == "task-123"
        assert result["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_high_urgency_boosts_priority(self, facade):
        context = {"traits": {"urgency": 0.9}}
        await facade.delegate_to_swarm("Urgent", agent_code="Forge", agent_context=context)
        call_kwargs = facade._service.submit_task.call_args
        assert (
            call_kwargs.kwargs.get("priority") == "high" or call_kwargs[1].get("priority") == "high"
        )


# =============================================================================
# Trait Routing
# =============================================================================


class TestTraitRouting:
    def test_analytical_prefers_quality(self):
        assert _TRAIT_ROUTING["analytical"]["prefer_speed"] is False

    def test_decisive_prefers_speed(self):
        assert _TRAIT_ROUTING["decisive"]["prefer_speed"] is True

    def test_cautious_prefers_quality(self):
        assert _TRAIT_ROUTING["cautious"]["prefer_speed"] is False
