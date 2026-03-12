"""
Tests for the consolidated Overwatch (Overwatch) after Nexus merge.

Sprint 1.3: Verify the merged Overwatch has all capabilities from both
the original Overwatch and the deprecated Nexus.

Tests cover:
- Health-aware routing (from Nexus)
- Learning system integration (from Nexus)
- Drift detection (from Overwatch)
- Dynamic routing phases
- Deprecation warning for Nexus imports
"""

import pytest
import warnings
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from ag3ntwerk.agents.overwatch import Overwatch, Overwatch
from ag3ntwerk.agents.overwatch.agent import ROUTING_RULES, HealthAwareRouter, LEARNING_AVAILABLE
from ag3ntwerk.agents.overwatch.models import (
    DriftType,
    DriftSignal,
    StrategicContext,
    ORCHESTRATION_CAPABILITIES,
)
from ag3ntwerk.core.base import Task, TaskResult


class TestCoSConsolidatedCapabilities:
    """Test that Overwatch has all capabilities from both Nexus and original Overwatch."""

    def test_cos_has_health_routing(self):
        """Overwatch should have health-aware routing enabled by default."""
        cos = Overwatch()
        assert cos._health_routing_enabled is True
        assert cos._health_router is not None
        assert isinstance(cos._health_router, HealthAwareRouter)

    def test_cos_has_drift_monitor(self):
        """Overwatch should have drift detection (original Overwatch feature)."""
        cos = Overwatch()
        assert cos._drift_monitor is not None
        assert hasattr(cos._drift_monitor, "should_escalate")
        assert hasattr(cos._drift_monitor, "record_task_outcome")

    def test_cos_has_learning_orchestrator_slot(self):
        """Overwatch should have a slot for learning orchestrator."""
        cos = Overwatch()
        assert hasattr(cos, "_learning_orchestrator")
        assert cos._learning_orchestrator is None  # Not connected by default

    def test_cos_has_dynamic_routing_metric(self):
        """Overwatch should track dynamically routed tasks."""
        cos = Overwatch()
        assert "tasks_dynamically_routed" in cos._metrics

    def test_cos_has_managers(self):
        """Overwatch should have internal managers (from both Nexus and Overwatch)."""
        cos = Overwatch()
        assert hasattr(cos, "_cos_managers")
        assert "WFM" in cos._cos_managers  # WorkflowManager
        assert "TRM" in cos._cos_managers  # TaskRoutingManager
        assert "PRM" in cos._cos_managers  # ProcessManager
        assert "CORM" in cos._cos_managers  # CoordinationManager

    def test_cos_has_orchestration_capabilities(self):
        """Overwatch should expose ORCHESTRATION_CAPABILITIES."""
        cos = Overwatch()
        assert hasattr(cos, "capabilities")
        assert cos.capabilities == ORCHESTRATION_CAPABILITIES


class TestCoSHealthRoutingMethods:
    """Test health routing methods merged from Nexus."""

    def test_get_agent_health_no_router(self):
        """get_agent_health should handle disabled health routing."""
        cos = Overwatch(enable_health_routing=False)
        result = cos.get_agent_health()
        assert result == {"health_routing_enabled": False}

    def test_get_agent_health_all_agents(self):
        """get_agent_health should return all agents when no code specified."""
        cos = Overwatch()
        result = cos.get_agent_health()
        assert result["health_routing_enabled"] is True
        assert "agents" in result

    def test_get_agent_health_specific_agent(self):
        """get_agent_health should return specific agent health."""
        cos = Overwatch()
        result = cos.get_agent_health("Forge")
        assert result["agent_code"] == "Forge"
        assert "is_healthy" in result
        assert "health_score" in result
        assert "success_rate" in result

    def test_reset_agent_health_method_exists(self):
        """reset_agent_health method should exist and work."""
        cos = Overwatch()
        assert hasattr(cos, "reset_agent_health")
        result = cos.reset_agent_health("Forge")
        assert result is True

    def test_reset_agent_health_disabled(self):
        """reset_agent_health should return False when routing disabled."""
        cos = Overwatch(enable_health_routing=False)
        result = cos.reset_agent_health()
        assert result is False

    def test_add_fallback_route_method_exists(self):
        """add_fallback_route method should exist and work."""
        cos = Overwatch()
        assert hasattr(cos, "add_fallback_route")
        result = cos.add_fallback_route("code_review", ["Forge", "Sentinel"])
        assert result is True

    def test_set_health_routing_enabled(self):
        """set_health_routing_enabled should toggle health routing."""
        cos = Overwatch(enable_health_routing=False)
        assert cos._health_routing_enabled is False

        cos.set_health_routing_enabled(True)
        assert cos._health_routing_enabled is True
        assert cos._health_router is not None


class TestCoSLearningMethods:
    """Test learning system methods merged from Nexus."""

    def test_is_learning_enabled_without_orchestrator(self):
        """is_learning_enabled should return False without orchestrator."""
        cos = Overwatch()
        assert cos.is_learning_enabled() is False

    def test_disconnect_learning_system(self):
        """disconnect_learning_system should clear orchestrator."""
        cos = Overwatch()
        cos._learning_orchestrator = MagicMock()
        cos.disconnect_learning_system()
        assert cos._learning_orchestrator is None

    @pytest.mark.asyncio
    async def test_get_learning_stats_not_connected(self):
        """get_learning_stats should return error when not connected."""
        cos = Overwatch()
        result = await cos.get_learning_stats()
        assert result["learning_enabled"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_learned_patterns_not_connected(self):
        """get_learned_patterns should return empty list when not connected."""
        cos = Overwatch()
        result = await cos.get_learned_patterns()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_open_learning_issues_not_connected(self):
        """get_open_learning_issues should return empty list when not connected."""
        cos = Overwatch()
        result = await cos.get_open_learning_issues()
        assert result == []

    @pytest.mark.asyncio
    async def test_trigger_learning_analysis_not_connected(self):
        """trigger_learning_analysis should return error when not connected."""
        cos = Overwatch()
        result = await cos.trigger_learning_analysis()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_learning_insights_not_connected(self):
        """get_learning_insights should return error when not connected."""
        cos = Overwatch()
        result = await cos.get_learning_insights()
        assert "error" in result


class TestCoSDriftDetection:
    """Test drift detection (original Overwatch feature preserved)."""

    def test_get_drift_status(self):
        """get_drift_status should return drift summary."""
        cos = Overwatch()
        status = cos.get_drift_status()
        assert "total_signals" in status
        assert "unresolved_count" in status
        assert "should_escalate" in status

    def test_update_strategic_context(self):
        """update_strategic_context should update drift monitor."""
        cos = Overwatch()
        context = StrategicContext(
            routing_priorities={"priority1": 1.0},
            success_rate_threshold=0.9,
        )
        cos.update_strategic_context(context)
        # Should not raise


class TestCoSRoutingPhases:
    """Test the 5-phase routing strategy."""

    def test_routing_rules_exist(self):
        """ROUTING_RULES should be available."""
        assert ROUTING_RULES is not None
        assert isinstance(ROUTING_RULES, dict)
        assert len(ROUTING_RULES) > 0

    def test_routing_rules_cover_major_task_types(self):
        """ROUTING_RULES should cover major task types."""
        assert "code_review" in ROUTING_RULES
        assert "security_scan" in ROUTING_RULES
        assert "financial_report" in ROUTING_RULES
        assert "campaign_creation" in ROUTING_RULES  # Echo task type

    @pytest.mark.asyncio
    async def test_route_task_static_fallback(self):
        """_route_task should fall back to static routing."""
        cos = Overwatch()

        # Create a mock subordinate
        mock_cto = MagicMock()
        mock_cto.code = "Forge"
        mock_cto.can_handle = MagicMock(return_value=True)
        mock_cto.is_active = True
        cos._subordinates["Forge"] = mock_cto

        task = Task(
            description="Review code",
            task_type="code_review",
        )

        result = await cos._route_task(task)
        assert result == "Forge"

    @pytest.mark.asyncio
    async def test_route_task_unknown_type_records_drift(self):
        """_route_task should record unknown task types for drift."""
        cos = Overwatch()

        task = Task(
            description="Unknown task",
            task_type="completely_unknown_task_type_xyz",
        )

        await cos._route_task(task)

        # Should have recorded the unknown task type
        assert "completely_unknown_task_type_xyz" in cos._drift_monitor._unknown_task_types


class TestCoSExecutionIntegration:
    """Test execute method with merged capabilities."""

    @pytest.mark.asyncio
    async def test_execute_tracks_timing(self):
        """execute should track task timing for latency."""
        cos = Overwatch()

        task = Task(
            description="Test task",
            task_type="test",
        )

        # Execute without LLM provider - will fail but timing should be tracked
        result = await cos.execute(task)

        # Task should have been tracked
        assert cos._metrics["tasks_received"] >= 1

    @pytest.mark.asyncio
    async def test_execute_records_health_on_failure(self):
        """execute should record health metrics on failure."""
        cos = Overwatch()

        # Create mock subordinate that fails
        mock_cto = MagicMock()
        mock_cto.code = "Forge"
        mock_cto.can_handle = MagicMock(return_value=True)
        mock_cto.is_active = True
        mock_cto.execute = AsyncMock(
            return_value=TaskResult(
                task_id="test",
                success=False,
                error="Test failure",
            )
        )
        cos._subordinates["Forge"] = mock_cto

        task = Task(
            description="Review code",
            task_type="code_review",
        )

        result = await cos.execute(task)

        assert result.success is False
        # Health should have recorded the failure
        health = cos.get_agent_health("Forge")
        assert health["total_tasks"] >= 1


class TestCOODeprecationWarning:
    """Test that importing Nexus shows deprecation warning."""

    def test_coo_import_shows_warning(self):
        """Importing from ag3ntwerk.agents.nexus should show DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Force reimport by removing from cache
            import sys

            modules_to_remove = [k for k in sys.modules if "ag3ntwerk.agents.nexus" in k]
            for mod in modules_to_remove:
                del sys.modules[mod]

            # Import Nexus
            from ag3ntwerk.agents.nexus import Nexus

            # Check for deprecation warning
            deprecation_warnings = [
                warning for warning in w if issubclass(warning.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) >= 1
            assert "deprecated" in str(deprecation_warnings[0].message).lower()

    def test_coo_still_functional(self):
        """Nexus should still work for backward compatibility (returns Overwatch)."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from ag3ntwerk.agents.nexus import Nexus, Nexus

            coo = Nexus()
            # Nexus is now an alias for Overwatch
            assert coo.code == "Overwatch"
            assert coo.codename == "Overwatch"

            # Nexus alias should also be Overwatch
            assert Nexus is Nexus


class TestOverwatchAlias:
    """Test Overwatch alias for Overwatch."""

    def test_overwatch_is_cos(self):
        """Overwatch should be an alias for Overwatch."""
        assert Overwatch is Overwatch

    def test_overwatch_instantiation(self):
        """Should be able to instantiate via Overwatch."""
        overwatch = Overwatch()
        assert overwatch.code == "Overwatch"
        assert overwatch.codename == "Overwatch"


class TestCoSDocstring:
    """Test that Overwatch has proper documentation."""

    def test_cos_has_docstring(self):
        """Overwatch should have a comprehensive docstring."""
        assert Overwatch.__doc__ is not None
        assert "Overwatch" in Overwatch.__doc__
        assert "Overwatch" in Overwatch.__doc__

    def test_cos_module_docstring(self):
        """Overwatch module should have updated docstring."""
        from ag3ntwerk.agents.overwatch import agent

        assert agent.__doc__ is not None
        assert "operational coordinator" in agent.__doc__
        assert "NOT the Nexus" in agent.__doc__
