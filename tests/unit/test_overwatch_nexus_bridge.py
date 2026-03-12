"""
Tests for Overwatch NexusBridge integration (Sprint 2.1).

Tests cover:
- Overwatch initialization with NexusBridge
- connect_to_nexus() method
- escalate_to_nexus() method
- report_outcome_to_nexus() method
- sync_context_from_nexus() method
- publish_health_to_nexus() method
- get_nexus_status() method
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from ag3ntwerk.agents.overwatch import Overwatch, NEXUS_BRIDGE_AVAILABLE
from ag3ntwerk.agents.overwatch.models import StrategicContext
from ag3ntwerk.core.base import Task, TaskResult


class TestCoSNexusBridgeInit:
    """Test Overwatch initialization with NexusBridge."""

    def test_cos_init_without_bridge(self):
        """Overwatch should initialize without NexusBridge."""
        cos = Overwatch()
        assert cos._nexus_bridge is None

    def test_cos_init_with_bridge(self):
        """Overwatch should accept NexusBridge in constructor."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = False

        cos = Overwatch(nexus_bridge=mock_bridge)
        assert cos._nexus_bridge is mock_bridge

    def test_cos_has_nexus_methods(self):
        """Overwatch should have all Nexus bridge methods."""
        cos = Overwatch()
        assert hasattr(cos, "connect_to_nexus")
        assert hasattr(cos, "disconnect_from_nexus")
        assert hasattr(cos, "is_nexus_connected")
        assert hasattr(cos, "escalate_to_nexus")
        assert hasattr(cos, "report_outcome_to_nexus")
        assert hasattr(cos, "sync_context_from_nexus")
        assert hasattr(cos, "publish_health_to_nexus")
        assert hasattr(cos, "subscribe_to_nexus_directives")
        assert hasattr(cos, "get_nexus_status")


class TestIsNexusConnected:
    """Test is_nexus_connected() method."""

    def test_not_connected_without_bridge(self):
        """is_nexus_connected should return False without bridge."""
        cos = Overwatch()
        assert cos.is_nexus_connected() is False

    def test_not_connected_with_disconnected_bridge(self):
        """is_nexus_connected should return False with disconnected bridge."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = False

        cos = Overwatch(nexus_bridge=mock_bridge)
        assert cos.is_nexus_connected() is False

    def test_connected_with_connected_bridge(self):
        """is_nexus_connected should return True with connected bridge."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True

        cos = Overwatch(nexus_bridge=mock_bridge)
        assert cos.is_nexus_connected() is True


class TestGetNexusStatus:
    """Test get_nexus_status() method."""

    def test_status_without_bridge(self):
        """get_nexus_status should return availability info without bridge."""
        cos = Overwatch()
        status = cos.get_nexus_status()

        assert status["connected"] is False
        assert "available" in status

    def test_status_with_disconnected_bridge(self):
        """get_nexus_status should show disconnected state."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = False

        cos = Overwatch(nexus_bridge=mock_bridge)
        status = cos.get_nexus_status()

        assert status["connected"] is False
        assert status["available"] is True

    def test_status_with_connected_bridge(self):
        """get_nexus_status should show config when connected."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.config.redis_url = "redis://test:6379"
        mock_bridge.config.channel_prefix = "test:nexus"
        mock_bridge.config.timeout_seconds = 30

        cos = Overwatch(nexus_bridge=mock_bridge)
        status = cos.get_nexus_status()

        assert status["connected"] is True
        assert status["config"]["redis_url"] == "redis://test:6379"


class TestConnectToNexus:
    """Test connect_to_nexus() method."""

    @pytest.mark.asyncio
    async def test_connect_creates_bridge(self):
        """connect_to_nexus should create bridge if not exists."""
        if not NEXUS_BRIDGE_AVAILABLE:
            pytest.skip("NexusBridge not available")

        cos = Overwatch()

        with patch("ag3ntwerk.agents.overwatch.nexus_mixin.NexusBridge") as MockBridge:
            mock_instance = MagicMock()
            mock_instance.connect = AsyncMock(return_value=True)
            mock_instance.sync_context = AsyncMock(return_value=None)
            mock_instance.subscribe_to_execution_requests = AsyncMock()
            mock_instance.is_connected = True
            MockBridge.return_value = mock_instance

            result = await cos.connect_to_nexus("redis://test:6379")

            assert result is True
            MockBridge.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_uses_existing_bridge(self):
        """connect_to_nexus should use existing bridge."""
        mock_bridge = MagicMock()
        mock_bridge.connect = AsyncMock(return_value=True)
        mock_bridge.sync_context = AsyncMock(return_value=None)
        mock_bridge.subscribe_to_execution_requests = AsyncMock()
        mock_bridge.is_connected = True

        cos = Overwatch(nexus_bridge=mock_bridge)
        result = await cos.connect_to_nexus()

        assert result is True
        mock_bridge.connect.assert_called_once()


class TestDisconnectFromNexus:
    """Test disconnect_from_nexus() method."""

    @pytest.mark.asyncio
    async def test_disconnect_calls_bridge(self):
        """disconnect_from_nexus should call bridge disconnect."""
        mock_bridge = MagicMock()
        mock_bridge.disconnect = AsyncMock()

        cos = Overwatch(nexus_bridge=mock_bridge)
        await cos.disconnect_from_nexus()

        mock_bridge.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_without_bridge(self):
        """disconnect_from_nexus should handle no bridge gracefully."""
        cos = Overwatch()
        await cos.disconnect_from_nexus()  # Should not raise


class TestEscalateToNexus:
    """Test escalate_to_nexus() method."""

    @pytest.mark.asyncio
    async def test_escalate_without_connection(self):
        """escalate_to_nexus should return None without connection."""
        cos = Overwatch()
        result = await cos.escalate_to_nexus()
        assert result is None

    @pytest.mark.asyncio
    async def test_escalate_with_disconnected_bridge(self):
        """escalate_to_nexus should return None with disconnected bridge."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = False

        cos = Overwatch(nexus_bridge=mock_bridge)
        result = await cos.escalate_to_nexus()
        assert result is None

    @pytest.mark.asyncio
    async def test_escalate_returns_context(self):
        """escalate_to_nexus should return StrategicContext from Nexus."""
        mock_context = StrategicContext(
            routing_priorities={"urgent": 1.0},
            success_rate_threshold=0.85,
        )

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.request_strategic_guidance = AsyncMock(return_value=mock_context)

        cos = Overwatch(nexus_bridge=mock_bridge)
        result = await cos.escalate_to_nexus()

        assert result is mock_context
        assert cos._metrics["escalations_to_coo"] == 1

    @pytest.mark.asyncio
    async def test_escalate_with_custom_context(self):
        """escalate_to_nexus should use provided drift context."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.request_strategic_guidance = AsyncMock(return_value=None)

        cos = Overwatch(nexus_bridge=mock_bridge)
        custom_context = {"custom": "data", "drift_level": 0.8}

        await cos.escalate_to_nexus(drift_context=custom_context)

        mock_bridge.request_strategic_guidance.assert_called_once_with(custom_context)


class TestReportOutcomeToNexus:
    """Test report_outcome_to_nexus() method."""

    @pytest.mark.asyncio
    async def test_report_without_connection(self):
        """report_outcome_to_nexus should return False without connection."""
        cos = Overwatch()
        result = TaskResult(task_id="test", success=True)

        reported = await cos.report_outcome_to_nexus(result)
        assert reported is False

    @pytest.mark.asyncio
    async def test_report_sends_metrics(self):
        """report_outcome_to_nexus should send task metrics."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.report_outcomes = AsyncMock(return_value=True)

        cos = Overwatch(nexus_bridge=mock_bridge)

        result = TaskResult(
            task_id="test-123",
            success=True,
            metrics={"duration_ms": 150},
        )

        reported = await cos.report_outcome_to_nexus(result)

        assert reported is True
        mock_bridge.report_outcomes.assert_called_once()

        # Check the metrics dict passed
        call_args = mock_bridge.report_outcomes.call_args[0][0]
        assert call_args["task_id"] == "test-123"
        assert call_args["success"] is True
        assert call_args["source"] == "Overwatch"


class TestSyncContextFromNexus:
    """Test sync_context_from_nexus() method."""

    @pytest.mark.asyncio
    async def test_sync_without_connection(self):
        """sync_context_from_nexus should return None without connection."""
        cos = Overwatch()
        result = await cos.sync_context_from_nexus()
        assert result is None

    @pytest.mark.asyncio
    async def test_sync_updates_drift_monitor(self):
        """sync_context_from_nexus should update drift monitor."""
        mock_context = StrategicContext(
            routing_priorities={"high": 1.0},
            success_rate_threshold=0.9,
        )

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.sync_context = AsyncMock(return_value=mock_context)

        cos = Overwatch(nexus_bridge=mock_bridge)
        result = await cos.sync_context_from_nexus()

        assert result is mock_context


class TestPublishHealthToNexus:
    """Test publish_health_to_nexus() method."""

    @pytest.mark.asyncio
    async def test_publish_without_connection(self):
        """publish_health_to_nexus should return False without connection."""
        cos = Overwatch()
        result = await cos.publish_health_to_nexus()
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_sends_health_data(self):
        """publish_health_to_nexus should send comprehensive health data."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_health_status = AsyncMock(return_value=True)

        cos = Overwatch(nexus_bridge=mock_bridge)
        result = await cos.publish_health_to_nexus()

        assert result is True
        mock_bridge.publish_health_status.assert_called_once()

        # Check health data includes required fields
        call_args = mock_bridge.publish_health_status.call_args[0][0]
        assert "cos_metrics" in call_args
        assert "drift_status" in call_args
        assert "agent_health" in call_args
        assert "learning_enabled" in call_args


class TestSubscribeToNexusDirectives:
    """Test subscribe_to_nexus_directives() method."""

    @pytest.mark.asyncio
    async def test_subscribe_without_connection(self):
        """subscribe_to_nexus_directives should handle no connection."""
        cos = Overwatch()

        async def callback(directive):
            pass

        # Should not raise
        await cos.subscribe_to_nexus_directives(callback)

    @pytest.mark.asyncio
    async def test_subscribe_calls_bridge(self):
        """subscribe_to_nexus_directives should call bridge subscribe."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.subscribe_to_directives = AsyncMock()

        cos = Overwatch(nexus_bridge=mock_bridge)

        async def callback(directive):
            pass

        await cos.subscribe_to_nexus_directives(callback)

        mock_bridge.subscribe_to_directives.assert_called_once_with(callback)


class TestNexusBridgeExports:
    """Test that NexusBridge is properly exported from cos package."""

    def test_nexus_bridge_available_exported(self):
        """NEXUS_BRIDGE_AVAILABLE should be exported."""
        from ag3ntwerk.agents.overwatch import NEXUS_BRIDGE_AVAILABLE

        assert isinstance(NEXUS_BRIDGE_AVAILABLE, bool)

    @pytest.mark.skipif(not NEXUS_BRIDGE_AVAILABLE, reason="redis not installed")
    def test_nexus_bridge_exported(self):
        """NexusBridge should be exported when available."""
        from ag3ntwerk.agents.overwatch import NexusBridge, NexusBridgeConfig

        assert NexusBridge is not None
        assert NexusBridgeConfig is not None
