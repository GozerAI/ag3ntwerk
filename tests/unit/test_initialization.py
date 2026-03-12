"""
Unit tests for the ag3ntwerk Initialization Factory.

Tests:
- create_overwatch_with_agents() function
- initialize_system() async function
- AgentSystem container
- Agent wiring logic
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.initialization import (
    AgentSystem,
    SKIP_AGENTS,
    ACTIVE_AGENTS,
    create_overwatch_with_agents,
    initialize_system,
)


class TestConstants:
    """Test module-level constants."""

    def test_skip_executives(self):
        """Nexus and Overwatch should be skipped."""
        assert "Nexus" in SKIP_AGENTS
        assert "Overwatch" in SKIP_AGENTS
        assert len(SKIP_AGENTS) == 2

    def test_active_executives_count(self):
        """Should have 14 active agents."""
        assert len(ACTIVE_AGENTS) == 14

    def test_active_executives_includes_expected(self):
        """Should include all expected agents."""
        expected = {
            "Beacon",
            "Forge",
            "Keystone",
            "Sentinel",
            "Compass",
            "Index",
            "Blueprint",
            "Echo",
            "Citadel",
            "Accord",
            "Foundry",
            "Aegis",
            "Axiom",
            "Vector",
        }
        assert ACTIVE_AGENTS == expected

    def test_skip_and_active_are_disjoint(self):
        """Skip and active sets should not overlap."""
        assert SKIP_AGENTS.isdisjoint(ACTIVE_AGENTS)


class TestAgentSystem:
    """Test AgentSystem container."""

    def test_system_creation(self):
        """Test basic system creation."""
        mock_cos = MagicMock()
        system = AgentSystem(
            cos=mock_cos,
            registered_executives=["Forge", "Keystone"],
        )

        assert system.cos == mock_cos
        assert system.coo == mock_cos  # backward compat property
        assert system.executive_count == 2
        assert system.learning_enabled is False
        assert system.learning_orchestrator is None

    def test_system_with_learning(self):
        """Test system with learning enabled."""
        mock_cos = MagicMock()
        mock_orchestrator = MagicMock()

        system = AgentSystem(
            cos=mock_cos,
            learning_orchestrator=mock_orchestrator,
            registered_executives=["Forge", "Keystone", "Sentinel"],
            learning_enabled=True,
        )

        assert system.learning_enabled is True
        assert system.learning_orchestrator == mock_orchestrator
        assert system.executive_count == 3

    def test_get_status(self):
        """Test status reporting."""
        mock_cos = MagicMock()
        system = AgentSystem(
            cos=mock_cos,
            registered_executives=["Forge", "Keystone"],
            learning_enabled=False,
        )

        status = system.get_status()

        assert status["cos_ready"] is True
        assert status["coo_ready"] is True  # backward compat
        assert status["executives_registered"] == 2
        assert status["agent_codes"] == ["Forge", "Keystone"]
        assert status["learning_enabled"] is False
        assert status["learning_orchestrator_ready"] is False


class TestCreateCosWithExecutives:
    """Test create_overwatch_with_agents function."""

    def test_creates_cos(self):
        """Test that Overwatch is created."""
        mock_provider = MagicMock()

        # Patch the Overwatch agent and registry at their import locations
        with (
            patch("ag3ntwerk.agents.overwatch.Overwatch") as MockCoS,
            patch("ag3ntwerk.orchestration.registry.AgentRegistry") as MockRegistry,
        ):

            mock_cos = MagicMock()
            mock_cos.subordinates = []
            MockCoS.return_value = mock_cos

            mock_registry = MagicMock()
            mock_registry.get_available_codes.return_value = ["Nexus", "Overwatch", "Forge", "Keystone"]
            mock_registry.get.return_value = MagicMock()
            MockRegistry.return_value = mock_registry

            result = create_overwatch_with_agents(mock_provider)

            MockCoS.assert_called_once_with(llm_provider=mock_provider)
            assert result == mock_cos

    def test_skips_coo_and_cos(self):
        """Test that Nexus and Overwatch are not registered as subordinates."""
        mock_provider = MagicMock()

        with (
            patch("ag3ntwerk.agents.overwatch.Overwatch") as MockCoS,
            patch("ag3ntwerk.orchestration.registry.AgentRegistry") as MockRegistry,
        ):

            mock_cos = MagicMock()
            mock_cos.subordinates = []
            MockCoS.return_value = mock_cos

            mock_registry = MagicMock()
            mock_registry.get_available_codes.return_value = ["Nexus", "Overwatch", "Forge", "Keystone"]

            mock_executive = MagicMock()
            mock_registry.get.return_value = mock_executive
            MockRegistry.return_value = mock_registry

            create_overwatch_with_agents(mock_provider)

            # Should only register Forge and Keystone (not Nexus or Overwatch)
            assert mock_cos.register_subordinate.call_count == 2

    def test_respects_enabled_agents(self):
        """Test that only enabled agents are registered."""
        mock_provider = MagicMock()

        with (
            patch("ag3ntwerk.agents.overwatch.Overwatch") as MockCoS,
            patch("ag3ntwerk.orchestration.registry.AgentRegistry") as MockRegistry,
        ):

            mock_cos = MagicMock()
            mock_cos.subordinates = []
            MockCoS.return_value = mock_cos

            mock_registry = MagicMock()
            mock_registry.get_available_codes.return_value = ["Nexus", "Overwatch", "Forge", "Keystone", "Sentinel"]
            mock_registry.get.return_value = MagicMock()
            MockRegistry.return_value = mock_registry

            create_overwatch_with_agents(
                mock_provider,
                enabled_agents={"Forge"},  # Only Forge
            )

            # Should only register Forge
            assert mock_cos.register_subordinate.call_count == 1

    def test_handles_registration_errors(self):
        """Test that registration errors are logged but don't fail."""
        mock_provider = MagicMock()

        with (
            patch("ag3ntwerk.agents.overwatch.Overwatch") as MockCoS,
            patch("ag3ntwerk.orchestration.registry.AgentRegistry") as MockRegistry,
        ):

            mock_cos = MagicMock()
            mock_cos.subordinates = []
            MockCoS.return_value = mock_cos

            mock_registry = MagicMock()
            mock_registry.get_available_codes.return_value = ["Nexus", "Overwatch", "Forge", "Keystone"]

            # First call succeeds, second fails
            mock_registry.get.side_effect = [
                MagicMock(),  # Forge success
                Exception("Failed to load Keystone"),  # Keystone fails
            ]
            MockRegistry.return_value = mock_registry

            # Should not raise
            result = create_overwatch_with_agents(mock_provider)

            # Should still return the Overwatch
            assert result == mock_cos
            # Should have registered Forge but not Keystone
            assert mock_cos.register_subordinate.call_count == 1


class TestInitializeSystem:
    """Test initialize_system async function."""

    @pytest.mark.asyncio
    async def test_basic_initialization(self):
        """Test basic initialization without learning."""
        mock_provider = MagicMock()

        with (
            patch("ag3ntwerk.agents.overwatch.Overwatch") as MockCoS,
            patch("ag3ntwerk.orchestration.registry.AgentRegistry") as MockRegistry,
        ):

            mock_cos = MagicMock()
            mock_cos.subordinates = []
            MockCoS.return_value = mock_cos

            mock_registry = MagicMock()
            mock_registry.get_available_codes.return_value = ["Nexus", "Overwatch", "Forge", "Keystone"]
            mock_registry.get.return_value = MagicMock()
            MockRegistry.return_value = mock_registry

            result = await initialize_system(
                llm_provider=mock_provider,
                enable_learning=False,
            )

            assert isinstance(result, AgentSystem)
            assert result.cos == mock_cos
            assert result.learning_enabled is False
            assert len(result.registered_executives) == 2  # Forge, Keystone

    @pytest.mark.asyncio
    async def test_learning_disabled_without_db(self):
        """Test that learning is disabled if db not provided."""
        mock_provider = MagicMock()

        with (
            patch("ag3ntwerk.agents.overwatch.Overwatch") as MockCoS,
            patch("ag3ntwerk.orchestration.registry.AgentRegistry") as MockRegistry,
        ):

            mock_cos = MagicMock()
            mock_cos.subordinates = []
            MockCoS.return_value = mock_cos

            mock_registry = MagicMock()
            mock_registry.get_available_codes.return_value = ["Nexus", "Overwatch"]
            MockRegistry.return_value = mock_registry

            result = await initialize_system(
                llm_provider=mock_provider,
                enable_learning=True,  # Requested but no db
                db=None,
                task_queue=None,
            )

            # Learning should be disabled due to missing db
            assert result.learning_enabled is False

    @pytest.mark.asyncio
    async def test_custom_config(self):
        """Test initialization with custom config."""
        mock_provider = MagicMock()

        with (
            patch("ag3ntwerk.agents.overwatch.Overwatch") as MockCoS,
            patch("ag3ntwerk.orchestration.registry.AgentRegistry") as MockRegistry,
        ):

            mock_cos = MagicMock()
            mock_cos.subordinates = []
            MockCoS.return_value = mock_cos

            mock_registry = MagicMock()
            mock_registry.get_available_codes.return_value = ["Nexus", "Overwatch", "Forge", "Keystone", "Sentinel"]
            mock_registry.get.return_value = MagicMock()
            MockRegistry.return_value = mock_registry

            result = await initialize_system(
                llm_provider=mock_provider,
                enable_learning=False,
                config={
                    "enabled_agents": {"Forge", "Sentinel"},  # Only these two
                },
            )

            # Should only register Forge and Sentinel
            assert len(result.registered_executives) == 2
            assert "Forge" in result.registered_executives
            assert "Sentinel" in result.registered_executives
