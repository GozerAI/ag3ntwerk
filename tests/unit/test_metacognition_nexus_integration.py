"""Tests for metacognition + Nexus bridge integration (Phase 5 insights)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.agents.overwatch.agent import Overwatch
from ag3ntwerk.modules.metacognition.service import MetacognitionService


def _make_cos_with_metacognition():
    """Create a Overwatch with metacognition service connected."""
    cos = Overwatch.__new__(Overwatch)
    cos._subordinates = {}
    cos._active_conflicts = []
    cos._nexus_bridge = None
    cos._health_router = None
    cos._drift_monitor = MagicMock()
    cos._drift_monitor.get_drift_summary.return_value = {}
    cos._learning_orchestrator = None
    cos._execution_hooks = []

    svc = MetacognitionService()
    svc._auto_save = False
    svc.register_agent(
        "Forge",
        seed_traits={
            "thoroughness": 0.9,
            "creativity": 0.4,
            "risk": 0.3,
            "assertiveness": 0.5,
            "collaboration": 0.5,
            "adaptability": 0.5,
            "decision": "analytical",
            "communication": "direct",
        },
    )
    svc.register_agent(
        "Keystone",
        seed_traits={
            "thoroughness": 0.7,
            "creativity": 0.5,
            "risk": 0.4,
            "assertiveness": 0.5,
            "collaboration": 0.5,
            "adaptability": 0.5,
            "decision": "analytical",
            "communication": "direct",
        },
    )
    cos._metacognition_service = svc
    return cos, svc


class TestGetMetacognitionInsights:

    def test_without_service(self):
        cos = Overwatch.__new__(Overwatch)
        cos._metacognition_service = None
        insights = cos._get_metacognition_insights()
        assert insights == {}

    def test_with_service(self):
        cos, svc = _make_cos_with_metacognition()
        insights = cos._get_metacognition_insights()
        assert "agent_health" in insights
        assert "trend_summary" in insights
        assert "team_stats" in insights
        assert "learned_trait_map" in insights
        assert "total_trait_snapshots" in insights
        assert "total_peer_recommendations" in insights

    def test_includes_agent_health(self):
        cos, svc = _make_cos_with_metacognition()
        insights = cos._get_metacognition_insights()
        assert "Forge" in insights["agent_health"]
        assert "Keystone" in insights["agent_health"]
        assert insights["agent_health"]["Forge"] == "healthy"

    def test_includes_learned_trait_map(self):
        cos, svc = _make_cos_with_metacognition()
        svc._learned_trait_map["code_review"] = {"thoroughness": 0.92}
        insights = cos._get_metacognition_insights()
        assert "code_review" in insights["learned_trait_map"]
        assert insights["learned_trait_map"]["code_review"]["thoroughness"] == 0.92


class TestSystemReflectionIncludesInsights:

    def test_reflection_result_has_insights(self):
        cos, svc = _make_cos_with_metacognition()
        result = cos.trigger_system_reflection()
        assert result is not None
        assert "metacognition_insights" in result
        assert "agent_health" in result["metacognition_insights"]


class TestPublishHealthIncludesInsights:

    @pytest.mark.asyncio
    async def test_health_data_includes_insights(self):
        cos, svc = _make_cos_with_metacognition()
        mock_bridge = AsyncMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_health_status = AsyncMock(return_value=True)
        cos._nexus_bridge = mock_bridge

        # Mock the methods that health publishing calls
        cos.get_metrics = MagicMock(return_value={})
        cos.get_drift_status = MagicMock(return_value={})
        cos.get_agent_health = MagicMock(return_value={})
        cos.is_learning_enabled = MagicMock(return_value=True)

        await cos.publish_health_to_nexus()

        mock_bridge.publish_health_status.assert_called_once()
        health_data = mock_bridge.publish_health_status.call_args[0][0]
        assert "metacognition_insights" in health_data
        assert "agent_health" in health_data["metacognition_insights"]
