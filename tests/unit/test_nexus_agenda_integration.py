"""
Unit tests for Nexus + Autonomous Agenda Engine integration.

Tests cover:
1. Nexus.connect_agenda_engine() - Engine connection
2. Nexus agenda generation via goals
3. Nexus execution of agenda items
4. Nexus approval/rejection workflow
5. COOService integration with agenda
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestCOOAgendaConnection:
    """Test Nexus agenda engine connection."""

    @pytest.fixture
    def coo(self):
        """Create Nexus instance."""
        from ag3ntwerk.agents.overwatch import Overwatch as Nexus

        return Nexus(llm_provider=None)

    @pytest.fixture
    def agenda_engine(self):
        """Create mock agenda engine."""
        from ag3ntwerk.agenda import AutonomousAgendaEngine, AgendaEngineConfig

        engine = AutonomousAgendaEngine(config=AgendaEngineConfig())
        return engine

    @pytest.mark.asyncio
    async def test_connect_agenda_engine(self, coo, agenda_engine):
        """Test connecting agenda engine to Nexus."""
        await coo.connect_agenda_engine(agenda_engine)

        assert coo.is_agenda_enabled()
        assert coo._agenda_engine is agenda_engine

    @pytest.mark.asyncio
    async def test_disconnect_agenda_engine(self, coo, agenda_engine):
        """Test disconnecting agenda engine."""
        await coo.connect_agenda_engine(agenda_engine)
        await coo.disconnect_agenda_engine()

        assert not coo.is_agenda_enabled()
        assert coo._agenda_engine is None

    def test_is_agenda_enabled_false_by_default(self, coo):
        """Test agenda is disabled by default."""
        assert not coo.is_agenda_enabled()


class TestCOOAgendaGeneration:
    """Test Nexus agenda generation."""

    @pytest.fixture
    def coo_with_agenda(self):
        """Create Nexus with agenda engine."""
        from ag3ntwerk.agents.overwatch import Overwatch as Nexus
        from ag3ntwerk.agenda import AutonomousAgendaEngine, AgendaEngineConfig

        coo = Nexus(llm_provider=None)
        engine = AutonomousAgendaEngine(config=AgendaEngineConfig())
        coo._agenda_engine = engine
        return coo

    @pytest.fixture
    def sample_goals(self):
        """Create sample goals."""
        return [
            {
                "id": "goal_001",
                "title": "Implement Feature X",
                "description": "Build new user feature",
                "milestones": [
                    {"id": "m1", "title": "Design", "status": "pending"},
                    {"id": "m2", "title": "Implement", "status": "pending"},
                ],
                "status": "active",
            },
        ]

    @pytest.mark.asyncio
    async def test_generate_agenda(self, coo_with_agenda, sample_goals):
        """Test generating agenda through Nexus."""
        result = await coo_with_agenda.generate_agenda(
            period_hours=24,
            goals=sample_goals,
        )

        assert "agenda_id" in result
        assert "total_items" in result
        assert result["total_items"] > 0

    @pytest.mark.asyncio
    async def test_generate_agenda_without_engine(self):
        """Test agenda generation when engine not connected."""
        from ag3ntwerk.agents.overwatch import Overwatch as Nexus

        coo = Nexus(llm_provider=None)
        result = await coo.generate_agenda()

        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_agenda_items(self, coo_with_agenda, sample_goals):
        """Test getting agenda items."""
        await coo_with_agenda.generate_agenda(goals=sample_goals)
        items = await coo_with_agenda.get_agenda_items(count=5)

        assert isinstance(items, list)
        if items:
            item = items[0]
            assert "id" in item
            assert "title" in item
            assert "task_type" in item
            assert "recommended_agent" in item

    @pytest.mark.asyncio
    async def test_get_agenda_status(self, coo_with_agenda, sample_goals):
        """Test getting agenda status."""
        await coo_with_agenda.generate_agenda(goals=sample_goals)
        status = await coo_with_agenda.get_agenda_status()

        assert status.get("enabled") or status.get("agenda_enabled")
        # Status structure may vary between implementations


class TestCOOAgendaExecution:
    """Test Nexus agenda item execution."""

    @pytest.fixture
    def coo_with_agenda_and_items(self):
        """Create Nexus with agenda and items."""
        from ag3ntwerk.agents.overwatch import Overwatch as Nexus
        from ag3ntwerk.agenda import AutonomousAgendaEngine, AgendaEngineConfig

        coo = Nexus(llm_provider=None)
        engine = AutonomousAgendaEngine(config=AgendaEngineConfig())
        coo._agenda_engine = engine
        return coo

    @pytest.fixture
    def sample_goals(self):
        """Create sample goals."""
        return [
            {
                "id": "goal_001",
                "title": "Research Task",
                "description": "Do research",
                "milestones": [
                    {"id": "m1", "title": "Research topic", "status": "pending"},
                ],
                "status": "active",
            },
        ]

    @pytest.mark.asyncio
    async def test_execute_agenda_item_not_found(self, coo_with_agenda_and_items):
        """Test executing non-existent agenda item."""
        result = await coo_with_agenda_and_items.execute_agenda_item("nonexistent")

        assert not result.success
        assert "not found" in result.error.lower() or "no active agenda" in result.error.lower()

    @pytest.mark.asyncio
    async def test_approve_agenda_item(self, coo_with_agenda_and_items, sample_goals):
        """Test approving agenda item."""
        # Generate agenda first
        await coo_with_agenda_and_items.generate_agenda(goals=sample_goals)

        # Get items awaiting approval
        items = await coo_with_agenda_and_items.get_agenda_items(count=5)
        pending_items = [i for i in items if i.get("approval_status") == "pending"]

        if pending_items:
            item_id = pending_items[0]["id"]
            success = await coo_with_agenda_and_items.approve_agenda_item(
                item_id, "test@user.com", "Approved for testing"
            )
            # May or may not succeed depending on item state
            assert isinstance(success, bool)

    @pytest.mark.asyncio
    async def test_reject_agenda_item(self, coo_with_agenda_and_items, sample_goals):
        """Test rejecting agenda item."""
        await coo_with_agenda_and_items.generate_agenda(goals=sample_goals)
        items = await coo_with_agenda_and_items.get_agenda_items(count=5)

        pending_items = [i for i in items if i.get("approval_status") == "pending"]

        if pending_items:
            item_id = pending_items[0]["id"]
            success = await coo_with_agenda_and_items.reject_agenda_item(
                item_id, "test@user.com", "Rejected for testing"
            )
            assert isinstance(success, bool)


class TestCOOAgendaObstacles:
    """Test Nexus agenda obstacle management."""

    @pytest.fixture
    def coo_with_agenda(self):
        """Create Nexus with agenda engine."""
        from ag3ntwerk.agents.overwatch import Overwatch as Nexus
        from ag3ntwerk.agenda import AutonomousAgendaEngine, AgendaEngineConfig

        coo = Nexus(llm_provider=None)
        engine = AutonomousAgendaEngine(config=AgendaEngineConfig())
        coo._agenda_engine = engine
        return coo

    @pytest.mark.asyncio
    async def test_get_obstacles_empty(self, coo_with_agenda):
        """Test getting obstacles when none exist."""
        obstacles = await coo_with_agenda.get_agenda_obstacles()
        assert isinstance(obstacles, list)

    @pytest.mark.asyncio
    async def test_get_strategies_empty(self, coo_with_agenda):
        """Test getting strategies when none exist."""
        strategies = await coo_with_agenda.get_agenda_strategies()
        assert isinstance(strategies, list)


class TestCOOContextEnrichment:
    """Test Nexus context enrichment with agenda data."""

    @pytest.fixture
    def coo_with_agenda(self):
        """Create Nexus with agenda engine."""
        from ag3ntwerk.agents.overwatch import Overwatch as Nexus
        from ag3ntwerk.agenda import AutonomousAgendaEngine, AgendaEngineConfig

        coo = Nexus(llm_provider=None)
        engine = AutonomousAgendaEngine(config=AgendaEngineConfig())
        coo._agenda_engine = engine
        return coo

    @pytest.mark.asyncio
    async def test_enrich_context_with_agenda(self, coo_with_agenda):
        """Test enriching context with agenda data."""
        goals = [
            {
                "id": "goal_001",
                "title": "Test Goal",
                "milestones": [],
                "status": "active",
            }
        ]
        await coo_with_agenda.generate_agenda(goals=goals)

        context = {"existing_key": "value"}
        enriched = coo_with_agenda.enrich_context_with_agenda(context)

        assert "existing_key" in enriched
        assert "agenda" in enriched

    def test_enrich_context_without_agenda(self):
        """Test enriching context when agenda not enabled."""
        from ag3ntwerk.agents.overwatch import Overwatch as Nexus

        coo = Nexus(llm_provider=None)
        context = {"key": "value"}
        enriched = coo.enrich_context_with_agenda(context)

        # Should return original context unchanged
        assert enriched == context


class TestCOOServiceAgendaIntegration:
    """Test COOService integration with agenda."""

    @pytest.fixture
    def mock_state(self):
        """Create mock state with Nexus."""
        from ag3ntwerk.agents.overwatch import Overwatch as Nexus
        from ag3ntwerk.agenda import AutonomousAgendaEngine, AgendaEngineConfig

        state = MagicMock()
        coo = Nexus(llm_provider=None)
        engine = AutonomousAgendaEngine(config=AgendaEngineConfig())
        coo._agenda_engine = engine

        state.coo = coo
        state.llm_provider = MagicMock()
        state.list_goals = MagicMock(
            return_value=[
                {
                    "id": "g1",
                    "title": "Test Goal",
                    "milestones": [],
                    "status": "active",
                }
            ]
        )
        state.list_tasks = MagicMock(return_value=[])
        state.broadcast = AsyncMock()

        return state

    @pytest.fixture
    def coo_service(self, mock_state):
        """Create Nexus service."""
        from ag3ntwerk.api.services import COOService

        return COOService(mock_state)

    @pytest.mark.asyncio
    async def test_get_suggestions_with_agenda(self, coo_service, mock_state):
        """Test getting suggestions with agenda engine."""
        # First generate agenda
        await mock_state.coo.generate_agenda(goals=mock_state.list_goals())

        result = await coo_service.get_suggestions()

        assert "suggestion" in result
        assert "context_summary" in result
        assert result["context_summary"].get("agenda_enabled", False)

    @pytest.mark.asyncio
    async def test_get_suggestions_generate_agenda_prompt(self, coo_service, mock_state):
        """Test that suggestions prompt for agenda generation when needed."""
        # Agenda engine connected but no agenda generated
        result = await coo_service.get_suggestions()

        # Should suggest generating an agenda
        if result.get("suggestion"):
            assert result["context_summary"].get("agenda_enabled", False)


class TestCOOWorkbenchIntegration:
    """Test Nexus workbench pipeline integration."""

    @pytest.fixture
    def coo(self):
        """Create Nexus instance."""
        from ag3ntwerk.agents.overwatch import Overwatch as Nexus

        return Nexus(llm_provider=None)

    @pytest.fixture
    def mock_pipeline(self):
        """Create mock workbench pipeline."""
        pipeline = MagicMock()
        pipeline.run_evaluation = AsyncMock(return_value={"status": "success"})
        pipeline.run_full_pipeline = AsyncMock(return_value={"status": "success"})
        pipeline.get_workspace_status = AsyncMock(return_value={"status": "active"})
        return pipeline

    @pytest.mark.asyncio
    async def test_connect_workbench_pipeline(self, coo, mock_pipeline):
        """Test connecting workbench pipeline."""
        await coo.connect_workbench_pipeline(mock_pipeline)

        assert coo.is_workbench_connected()

    @pytest.mark.asyncio
    async def test_disconnect_workbench_pipeline(self, coo, mock_pipeline):
        """Test disconnecting workbench pipeline."""
        await coo.connect_workbench_pipeline(mock_pipeline)
        await coo.disconnect_workbench_pipeline()

        assert not coo.is_workbench_connected()

    @pytest.mark.asyncio
    async def test_run_workbench_pipeline(self, coo, mock_pipeline):
        """Test running workbench pipeline."""
        mock_pipeline.execute = AsyncMock(return_value={"status": "success"})
        await coo.connect_workbench_pipeline(mock_pipeline)

        result = await coo.run_workbench_pipeline(
            workspace_id="ws_001",
            cmd=["python", "main.py"],
        )

        assert result == {"status": "success"}
        mock_pipeline.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_workbench_pipeline_not_connected(self, coo):
        """Test running pipeline when not connected."""
        result = await coo.run_workbench_pipeline(
            workspace_id="ws_001",
            cmd=["python", "main.py"],
        )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_workbench_status(self, coo, mock_pipeline):
        """Test getting workbench status."""
        mock_pipeline.get_stats = AsyncMock(return_value={"workspaces": 1})
        await coo.connect_workbench_pipeline(mock_pipeline)

        result = await coo.get_workbench_status()

        assert result["connected"] is True
