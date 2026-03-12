"""
Tests for Overwatch (Overwatch) routing rules additions.

Phase 5: Verifies that new social and revenue task types
are correctly routed to Echo and Vector respectively.
"""

import pytest

from ag3ntwerk.agents.overwatch.agent import ROUTING_RULES, HealthAwareRouter


# =============================================================================
# ROUTING_RULES Tests
# =============================================================================


class TestRoutingRulesAdditions:
    """Test that new task types are registered in ROUTING_RULES."""

    # Social distribution -> Echo
    @pytest.mark.parametrize(
        "task_type",
        [
            "social_distribute",
            "social_publish",
            "social_schedule",
            "social_analytics",
            "social_metrics",
        ],
    )
    def test_social_tasks_route_to_cmo(self, task_type):
        """Social distribution tasks should route to Echo."""
        assert task_type in ROUTING_RULES
        assert ROUTING_RULES[task_type] == "Echo"

    # Revenue tasks -> Vector
    @pytest.mark.parametrize(
        "task_type",
        [
            "revenue_summary",
            "revenue_tracking",
        ],
    )
    def test_revenue_tasks_route_to_crevo(self, task_type):
        """Revenue tasks should route to Vector."""
        assert task_type in ROUTING_RULES
        assert ROUTING_RULES[task_type] == "Vector"

    # Existing routes should still be present
    def test_existing_cmo_routes_intact(self):
        """Existing Echo routes should still work."""
        assert ROUTING_RULES["campaign_creation"] == "Echo"
        assert ROUTING_RULES["content_strategy"] == "Compass"  # Strategic content routes to Compass
        assert ROUTING_RULES["brand_analysis"] == "Echo"

    def test_existing_crevo_routes_intact(self):
        """Existing Vector routes should still work."""
        assert ROUTING_RULES["revenue_optimization"] == "Vector"
        assert ROUTING_RULES["sales_strategy"] == "Vector"

    def test_other_routes_not_affected(self):
        """Other routing rules should be unchanged."""
        assert ROUTING_RULES["code_review"] == "Forge"
        assert ROUTING_RULES["security_scan"] == "Citadel"
        assert ROUTING_RULES["budget_analysis"] == "Keystone"
        assert ROUTING_RULES["strategic_analysis"] == "Compass"
        assert ROUTING_RULES["product_strategy"] == "Blueprint"


# =============================================================================
# HealthAwareRouter Tests with New Routes
# =============================================================================


class TestHealthAwareRouterWithNewRoutes:
    """Test that HealthAwareRouter picks up new routing rules."""

    def test_router_uses_routing_rules(self):
        """HealthAwareRouter should reference the updated ROUTING_RULES."""
        router = HealthAwareRouter()
        # The router stores a reference to the module-level ROUTING_RULES
        assert "social_distribute" in router._routing_rules
        assert "revenue_summary" in router._routing_rules

    def test_router_returns_cmo_for_social(self):
        """Router should return Echo for social task types when Echo is available."""
        router = HealthAwareRouter()
        # Simulate Echo being available
        mock_cmo = type(
            "MockAgent", (), {"code": "Echo", "can_handle": lambda s, t: True, "is_active": True}
        )()
        agents = {"Echo": mock_cmo}

        result = router.get_best_agent("social_distribute", agents)
        assert result is not None
        agent_code, score = result
        assert agent_code == "Echo"

    def test_router_returns_crevo_for_revenue_summary(self):
        """Router should return Vector for revenue_summary."""
        router = HealthAwareRouter()
        mock_crevo = type(
            "MockAgent", (), {"code": "Vector", "can_handle": lambda s, t: True, "is_active": True}
        )()
        agents = {"Vector": mock_crevo}

        result = router.get_best_agent("revenue_summary", agents)
        assert result is not None
        agent_code, score = result
        assert agent_code == "Vector"

    def test_router_returns_none_when_no_agent(self):
        """Router should return None when target agent not available."""
        router = HealthAwareRouter()
        result = router.get_best_agent("social_distribute", {})
        assert result is None
