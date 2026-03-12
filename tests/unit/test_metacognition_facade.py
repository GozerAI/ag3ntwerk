"""Tests for the MetacognitionFacade learning integration."""

import pytest

from ag3ntwerk.learning.facades.metacognition_facade import MetacognitionFacade
from ag3ntwerk.modules.metacognition.service import MetacognitionService


class TestMetacognitionFacade:
    """Tests for MetacognitionFacade."""

    def test_creation(self):
        facade = MetacognitionFacade()
        assert facade.is_connected is False

    def test_connect_service(self):
        facade = MetacognitionFacade()
        svc = MetacognitionService()
        facade.connect_service(svc)
        assert facade.is_connected is True

    def test_process_outcome_without_service(self):
        facade = MetacognitionFacade()
        result = facade.process_outcome_with_reflection(
            "Forge",
            "task1",
            "test",
            True,
        )
        assert result is None

    def test_process_outcome_with_service(self):
        facade = MetacognitionFacade()
        svc = MetacognitionService()
        svc.register_agent("Forge")
        facade.connect_service(svc)

        result = facade.process_outcome_with_reflection(
            agent_code="Forge",
            task_id="task1",
            task_type="code_review",
            success=True,
            duration_ms=100.0,
        )
        assert result is not None
        assert result["agent_code"] == "Forge"
        assert result["success"] is True

    def test_process_outcome_failure(self):
        facade = MetacognitionFacade()
        svc = MetacognitionService()
        svc.register_agent("Forge")
        facade.connect_service(svc)

        result = facade.process_outcome_with_reflection(
            agent_code="Forge",
            task_id="task1",
            task_type="code_review",
            success=False,
            error="timeout",
        )
        assert result is not None
        assert result["success"] is False

    def test_outcomes_buffered(self):
        facade = MetacognitionFacade()
        svc = MetacognitionService()
        svc.register_agent("Forge")
        facade.connect_service(svc)

        for i in range(5):
            facade.process_outcome_with_reflection("Forge", f"task{i}", "test", True)
        assert facade.outcomes_buffer_count == 5

    def test_run_metacognition_phase_not_connected(self):
        facade = MetacognitionFacade()
        result = facade.run_metacognition_phase()
        assert result["skipped"] is True

    def test_run_metacognition_phase_connected(self):
        facade = MetacognitionFacade()
        svc = MetacognitionService()
        svc.register_agent("Forge")
        svc.register_agent("Echo")
        facade.connect_service(svc)

        # Process some outcomes
        for i in range(5):
            facade.process_outcome_with_reflection("Forge", f"task{i}", "test", True)

        result = facade.run_metacognition_phase(
            agent_health={
                "Forge": {"health_score": 0.9, "success_rate": 0.9, "total_tasks": 5},
            }
        )
        assert result["outcomes_processed"] == 5
        assert "heuristics_tuned" in result
        # Buffer should be cleared
        assert facade.outcomes_buffer_count == 0

    def test_run_metacognition_phase_with_system_reflection(self):
        facade = MetacognitionFacade()
        svc = MetacognitionService()
        svc.register_agent("Forge")
        facade.connect_service(svc)

        # Provide agent_health to trigger system reflection
        result = facade.run_metacognition_phase(
            agent_health={"Forge": {"health_score": 0.5, "success_rate": 0.5, "total_tasks": 10}},
        )
        assert result["system_reflection"] is not None

    def test_get_personality_insights_not_connected(self):
        facade = MetacognitionFacade()
        insights = facade.get_personality_insights()
        assert insights["connected"] is False

    def test_get_personality_insights_connected(self):
        facade = MetacognitionFacade()
        svc = MetacognitionService()
        svc.register_agent("Forge")
        facade.connect_service(svc)

        insights = facade.get_personality_insights()
        assert insights["connected"] is True
        assert "registered_agents" in insights

    @pytest.mark.asyncio
    async def test_get_stats(self):
        facade = MetacognitionFacade()
        stats = await facade.get_stats()
        assert "connected" in stats
        assert stats["connected"] is False

    @pytest.mark.asyncio
    async def test_get_stats_connected(self):
        facade = MetacognitionFacade()
        svc = MetacognitionService()
        svc.register_agent("Forge")
        facade.connect_service(svc)

        stats = await facade.get_stats()
        assert stats["connected"] is True
        assert "service_stats" in stats


class TestMetacognitionFacadeIntegration:
    """Integration tests for the facade with multiple agents."""

    def test_multi_agent_workflow(self):
        """Test processing outcomes for multiple agents through the facade."""
        facade = MetacognitionFacade()
        svc = MetacognitionService()

        agents = ["Forge", "Echo", "Keystone", "Sentinel"]
        for code in agents:
            svc.register_agent(code)
        facade.connect_service(svc)

        # Simulate task outcomes
        for i in range(20):
            agent = agents[i % len(agents)]
            facade.process_outcome_with_reflection(
                agent_code=agent,
                task_id=f"task_{i}",
                task_type="general",
                success=i % 5 != 0,
                duration_ms=100.0 + i * 10,
            )

        # Run metacognition phase
        health = {
            code: {"health_score": 0.8, "success_rate": 0.8, "total_tasks": 5} for code in agents
        }
        result = facade.run_metacognition_phase(agent_health=health)

        assert result["outcomes_processed"] == 20
        assert result["system_reflection"] is not None

    def test_repeated_phases(self):
        """Test running multiple metacognition phases."""
        facade = MetacognitionFacade()
        svc = MetacognitionService()
        svc.register_agent("Forge")
        facade.connect_service(svc)

        for phase in range(3):
            for i in range(5):
                facade.process_outcome_with_reflection(
                    "Forge",
                    f"phase{phase}_task{i}",
                    "test",
                    True,
                )
            result = facade.run_metacognition_phase()
            assert result["outcomes_processed"] == 5
            assert facade.outcomes_buffer_count == 0
