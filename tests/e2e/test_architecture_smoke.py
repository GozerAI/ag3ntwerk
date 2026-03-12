"""
Architecture smoke test for the federated ag3ntwerk architecture.

Tests the new Overwatch (Overwatch) coordination layer and verifies
that the service bridges can be instantiated.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestCoSInitialization:
    """Test Overwatch initializes correctly."""

    def test_cos_initialization(self):
        """Test Overwatch initializes correctly."""
        from ag3ntwerk.agents.overwatch import Overwatch

        cos = Overwatch()
        assert cos.code == "Overwatch"
        assert cos.codename == "Overwatch"

    def test_cos_is_overwatch(self):
        """Test Overwatch alias."""
        from ag3ntwerk.agents.overwatch import Overwatch, Overwatch

        assert Overwatch is Overwatch

    def test_cos_has_managers(self):
        """Test Overwatch has required managers."""
        from ag3ntwerk.agents.overwatch import (
            WorkflowManager,
            TaskRoutingManager,
            ProcessManager,
            CoordinationManager,
        )

        # These should all be importable
        assert WorkflowManager is not None
        assert TaskRoutingManager is not None
        assert ProcessManager is not None
        assert CoordinationManager is not None

    def test_cos_has_specialists(self):
        """Test Overwatch has required specialists."""
        from ag3ntwerk.agents.overwatch import (
            WorkflowDesigner,
            TaskAnalyst,
            MetricsAnalyst,
            ProcessEngineer,
            OKRCoordinator,
        )

        # These should all be importable
        assert WorkflowDesigner is not None
        assert TaskAnalyst is not None
        assert MetricsAnalyst is not None
        assert ProcessEngineer is not None
        assert OKRCoordinator is not None


class TestDriftDetection:
    """Test drift detection works."""

    def test_drift_models_exist(self):
        """Test drift detection models exist."""
        from ag3ntwerk.agents.overwatch.models import (
            DriftType,
            DriftSignal,
            StrategicContext,
        )

        assert DriftType is not None
        assert DriftSignal is not None
        assert StrategicContext is not None

    def test_drift_signal_creation(self):
        """Test drift signal can be created."""
        from ag3ntwerk.agents.overwatch.models import DriftType, DriftSignal

        signal = DriftSignal(
            drift_type=DriftType.PERFORMANCE,
            severity=0.8,
            description="Test drift",
        )

        assert signal.drift_type == DriftType.PERFORMANCE
        assert signal.severity == 0.8
        assert signal.exceeds_tolerance is True

    def test_strategic_context_defaults(self):
        """Test strategic context has sensible defaults."""
        from ag3ntwerk.agents.overwatch.models import StrategicContext

        context = StrategicContext()

        assert context.success_rate_threshold == 0.7
        assert context.latency_slo_ms == 5000.0
        assert context.auto_escalation_enabled is True


class TestServiceBridges:
    """Test service bridges can be instantiated."""

    def test_nexus_bridge_instantiation(self):
        """Test NexusBridge can be instantiated."""
        from ag3ntwerk.agents.bridges import NexusBridge, NexusBridgeConfig

        config = NexusBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix="ag3ntwerk:nexus",
        )
        bridge = NexusBridge(config=config)

        assert bridge is not None
        assert bridge.config.redis_url == "redis://localhost:6379"
        assert bridge.is_connected is False

    def test_forge_bridge_instantiation(self):
        """Test ForgeBridge can be instantiated."""
        from ag3ntwerk.agents.bridges import ForgeBridge, ForgeBridgeConfig

        config = ForgeBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix="ag3ntwerk:forge",
        )
        bridge = ForgeBridge(config=config)

        assert bridge is not None
        assert bridge.config.timeout_seconds == 300  # Dev tasks are slow

    def test_sentinel_bridge_instantiation(self):
        """Test SentinelBridge can be instantiated."""
        from ag3ntwerk.agents.bridges import SentinelBridge, SentinelBridgeConfig

        config = SentinelBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix="ag3ntwerk:sentinel",
        )
        bridge = SentinelBridge(config=config)

        assert bridge is not None
        assert bridge.config.timeout_seconds == 60


class TestBackwardCompatibility:
    """Test backward compatibility with old Nexus imports."""

    def test_coo_import_works(self):
        """Test Nexus can still be imported."""
        from ag3ntwerk.agents.nexus import Nexus

        coo = Nexus()
        assert coo.code == "Nexus"
        assert coo.codename == "Nexus"

    def test_nexus_alias_works(self):
        """Test Nexus alias works."""
        from ag3ntwerk.agents import Nexus

        # Should be an alias for Nexus
        nexus = Nexus()
        assert nexus.code == "Nexus"


class TestRegistryIntegration:
    """Test AgentRegistry includes Overwatch."""

    def test_registry_has_cos(self):
        """Test registry includes Overwatch."""
        from ag3ntwerk.orchestration.registry import AgentRegistry

        registry = AgentRegistry(auto_register=True)

        assert "Overwatch" in registry.STANDARD_AGENTS

    def test_registry_can_get_cos(self):
        """Test registry can get Overwatch."""
        from ag3ntwerk.orchestration.registry import AgentRegistry

        registry = AgentRegistry(auto_register=True)
        cos = registry.get("Overwatch")

        assert cos is not None
        assert cos.code == "Overwatch"
        assert cos.codename == "Overwatch"


class TestInitializationFactory:
    """Test initialization factory updates."""

    def test_agent_system_has_cos(self):
        """Test AgentSystem has cos attribute."""
        from ag3ntwerk.initialization import AgentSystem
        from ag3ntwerk.agents.overwatch import Overwatch

        cos = Overwatch()
        system = AgentSystem(cos=cos)

        assert system.cos is cos
        assert system.coo is cos  # backward compat

    def test_create_overwatch_with_agents(self):
        """Test create_overwatch_with_agents function."""
        from ag3ntwerk.initialization import create_overwatch_with_agents

        # Should not raise
        assert create_overwatch_with_agents is not None


class TestAgentPackageExports:
    """Test agents package exports new components."""

    def test_cos_exported(self):
        """Test Overwatch is exported from agents package."""
        from ag3ntwerk.agents import Overwatch, Overwatch

        assert Overwatch is not None
        assert Overwatch is not None
        assert Overwatch is Overwatch

    def test_all_standard_agents_importable(self):
        """Test all standard agents can be imported."""
        from ag3ntwerk.agents import (
            Overwatch,
            Nexus,
            Sentinel,
            Forge,
            Compass,
            Axiom,
            Keystone,
            Index,
            Aegis,
            Accord,
        )

        # All should be importable
        assert Overwatch is not None
        assert Nexus is not None
        assert Sentinel is not None
        assert Forge is not None
