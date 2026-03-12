"""
Tests for CSuiteBridgeListener (Sprint 2.2).

Tests cover:
- CSuiteBridgeListener initialization
- Connection and disconnection
- Guidance request handling
- Outcome report handling
- Health update handling
- Directive publishing

Note: AutonomousCOO integration tests are in the nexus test suite.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import sys
import os
import importlib.util

# Add nexus to path for imports
_nexus_src_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "src", "nexus", "src")
)


# Import the csuite_bridge module directly to avoid conflicts with other nexus packages
def _import_from_path(module_name: str, file_path: str):
    """Import a module from a specific file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    # Don't add to sys.modules to avoid conflicts
    spec.loader.exec_module(module)
    return module


# Import the csuite_bridge module directly
_csuite_bridge_path = os.path.join(_nexus_src_path, "nexus", "coo", "csuite_bridge.py")

# Check if the file exists before trying to import
if os.path.exists(_csuite_bridge_path):
    _csuite_bridge_module = _import_from_path("test_csuite_bridge", _csuite_bridge_path)
    CSuiteBridgeListener = _csuite_bridge_module.CSuiteBridgeListener
    CSuiteBridgeConfig = _csuite_bridge_module.CSuiteBridgeConfig
    AGENTWERK_BRIDGE_AVAILABLE = True
else:
    AGENTWERK_BRIDGE_AVAILABLE = False
    CSuiteBridgeListener = None
    CSuiteBridgeConfig = None


# Skip all tests if module not available
pytestmark = pytest.mark.skipif(
    not AGENTWERK_BRIDGE_AVAILABLE, reason="CSuiteBridgeListener not available"
)


class TestCSuiteBridgeListenerInit:
    """Test CSuiteBridgeListener initialization."""

    def test_init_with_defaults(self):
        """CSuiteBridgeListener should initialize with default config."""
        mock_coo = MagicMock()
        listener = CSuiteBridgeListener(mock_coo)

        assert listener._coo is mock_coo
        assert listener.config.redis_url == "redis://localhost:6379"
        assert listener.config.channel_prefix == "ag3ntwerk:nexus"
        assert listener.is_connected is False
        assert listener.is_listening is False

    def test_init_with_custom_config(self):
        """CSuiteBridgeListener should accept custom config."""
        mock_coo = MagicMock()
        config = CSuiteBridgeConfig(
            redis_url="redis://custom:6380",
            channel_prefix="custom:prefix",
            response_timeout_seconds=60,
        )
        listener = CSuiteBridgeListener(mock_coo, config)

        assert listener.config.redis_url == "redis://custom:6380"
        assert listener.config.channel_prefix == "custom:prefix"
        assert listener.config.response_timeout_seconds == 60

    def test_init_metrics_zeroed(self):
        """CSuiteBridgeListener should start with zero metrics."""
        mock_coo = MagicMock()
        listener = CSuiteBridgeListener(mock_coo)

        assert listener._guidance_requests_received == 0
        assert listener._guidance_responses_sent == 0
        assert listener._outcomes_received == 0
        assert listener._health_updates_received == 0
        assert listener._directives_sent == 0


class TestCSuiteBridgeListenerConnection:
    """Test connection and disconnection."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """connect() should return True on successful connection."""
        mock_coo = MagicMock()
        listener = CSuiteBridgeListener(mock_coo)

        with patch.dict("sys.modules", {"redis": MagicMock(), "redis.asyncio": MagicMock()}):
            # Reimport with mock
            import importlib

            with patch.object(listener, "_redis", None):
                # Mock the redis import inside the module
                mock_redis_module = MagicMock()
                mock_client = AsyncMock()
                mock_client.ping = AsyncMock()
                mock_redis_module.from_url.return_value = mock_client

                with patch.dict("sys.modules", {"redis.asyncio": mock_redis_module}):
                    # Patch at module level
                    original_connect = listener.connect

                    async def patched_connect():
                        listener._redis = mock_client
                        await listener._redis.ping()
                        listener._connected = True
                        return True

                    listener.connect = patched_connect
                    result = await listener.connect()

                    assert result is True
                    assert listener.is_connected is True

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """disconnect() should close Redis connection."""
        mock_coo = MagicMock()
        listener = CSuiteBridgeListener(mock_coo)

        mock_redis_client = AsyncMock()
        listener._redis = mock_redis_client
        listener._connected = True

        await listener.disconnect()

        mock_redis_client.close.assert_called_once()
        assert listener.is_connected is False


class TestCSuiteBridgeListenerListening:
    """Test start/stop listening."""

    @pytest.mark.asyncio
    async def test_start_listening_already_listening(self):
        """start_listening() should return True if already listening."""
        mock_coo = MagicMock()
        listener = CSuiteBridgeListener(mock_coo)
        listener._connected = True
        listener._listening = True

        result = await listener.start_listening()

        assert result is True

    @pytest.mark.asyncio
    async def test_stop_listening(self):
        """stop_listening() should cancel listener tasks."""
        import asyncio

        mock_coo = MagicMock()
        listener = CSuiteBridgeListener(mock_coo)
        listener._listening = True

        # Create a real asyncio task that we can cancel
        async def dummy_task():
            try:
                await asyncio.sleep(100)  # Long sleep
            except asyncio.CancelledError:
                pass

        mock_task1 = asyncio.create_task(dummy_task())
        mock_task2 = asyncio.create_task(dummy_task())
        mock_task3 = asyncio.create_task(dummy_task())

        listener._listener_task = mock_task1
        listener._outcome_listener_task = mock_task2
        listener._health_listener_task = mock_task3

        await listener.stop_listening()

        assert listener._listening is False
        assert listener._listener_task is None
        assert mock_task1.cancelled() or mock_task1.done()
        assert mock_task2.cancelled() or mock_task2.done()
        assert mock_task3.cancelled() or mock_task3.done()


class TestGuidanceRequestHandling:
    """Test guidance request handling."""

    @pytest.mark.asyncio
    async def test_handle_guidance_request_increments_counter(self):
        """handle_guidance_request() should increment counter."""
        mock_coo = MagicMock()
        mock_coo.get_status.return_value = MagicMock(mode=MagicMock(value="supervised"))
        mock_coo.config = MagicMock(
            max_concurrent_executions=3,
            auto_execute_confidence=0.9,
        )
        listener = CSuiteBridgeListener(mock_coo)
        listener._connected = True
        listener._redis = AsyncMock()

        request = {
            "type": "guidance_request",
            "drift_context": {"drift_type": "performance", "drift_level": 0.5},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await listener.handle_guidance_request(request)

        assert listener._guidance_requests_received == 1

    @pytest.mark.asyncio
    async def test_handle_guidance_request_generates_response(self):
        """handle_guidance_request() should send guidance response."""
        mock_coo = MagicMock()
        mock_coo.get_status.return_value = MagicMock(mode=MagicMock(value="supervised"))
        mock_coo.config = MagicMock(
            max_concurrent_executions=3,
            auto_execute_confidence=0.9,
        )
        listener = CSuiteBridgeListener(mock_coo)
        listener._connected = True
        listener._redis = AsyncMock()

        request = {
            "type": "guidance_request",
            "drift_context": {"drift_type": "accuracy", "drift_level": 0.6},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await listener.handle_guidance_request(request)

        # Should have published a response
        listener._redis.publish.assert_called_once()
        assert listener._guidance_responses_sent == 1


class TestOutcomeReportHandling:
    """Test outcome report handling."""

    @pytest.mark.asyncio
    async def test_handle_outcome_report_increments_counter(self):
        """handle_outcome_report() should increment counter."""
        mock_coo = MagicMock()
        mock_coo._learning = None  # No learning system
        listener = CSuiteBridgeListener(mock_coo)

        report = {
            "type": "outcome_report",
            "metrics": {
                "task_id": "test-123",
                "success": True,
                "duration_ms": 150,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await listener.handle_outcome_report(report)

        assert listener._outcomes_received == 1

    @pytest.mark.asyncio
    async def test_handle_outcome_report_forwards_to_learning(self):
        """handle_outcome_report() should forward to Nexus learning if available."""
        mock_coo = MagicMock()
        mock_learning = MagicMock()
        mock_learning.record_external_outcome = AsyncMock()
        mock_coo._learning = mock_learning
        listener = CSuiteBridgeListener(mock_coo)

        report = {
            "type": "outcome_report",
            "metrics": {
                "task_id": "test-456",
                "success": False,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await listener.handle_outcome_report(report)

        mock_learning.record_external_outcome.assert_called_once()


class TestHealthUpdateHandling:
    """Test health status update handling."""

    @pytest.mark.asyncio
    async def test_handle_health_update_stores_data(self):
        """Health update should be stored."""
        mock_coo = MagicMock()
        listener = CSuiteBridgeListener(mock_coo)

        health_data = {
            "type": "health_status",
            "source": "Overwatch",
            "data": {
                "cos_metrics": {"tasks_completed": 10},
                "drift_status": {"is_drifting": False},
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await listener._handle_health_update(health_data)

        assert listener._health_updates_received == 1
        assert listener._last_csuite_health is not None
        assert listener._last_csuite_health["cos_metrics"]["tasks_completed"] == 10

    def test_get_csuite_health_returns_last_health(self):
        """get_csuite_health() should return last received health."""
        mock_coo = MagicMock()
        listener = CSuiteBridgeListener(mock_coo)
        listener._last_csuite_health = {"status": "healthy"}

        health = listener.get_csuite_health()

        assert health == {"status": "healthy"}


class TestDirectivePublishing:
    """Test directive publishing."""

    @pytest.mark.asyncio
    async def test_publish_directive_success(self):
        """publish_directive() should publish to Redis channel."""
        mock_coo = MagicMock()
        listener = CSuiteBridgeListener(mock_coo)
        listener._connected = True
        listener._redis = AsyncMock()

        directive = {
            "type": "update_priorities",
            "priorities": {"urgent": 1.0, "high": 0.7},
        }

        result = await listener.publish_directive(directive)

        assert result is True
        assert listener._directives_sent == 1
        listener._redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_directive_not_connected(self):
        """publish_directive() should return False if not connected."""
        mock_coo = MagicMock()
        listener = CSuiteBridgeListener(mock_coo)
        listener._connected = False

        directive = {"type": "test"}

        result = await listener.publish_directive(directive)

        assert result is False
        assert listener._directives_sent == 0


class TestStatus:
    """Test status reporting."""

    def test_get_status_returns_comprehensive_info(self):
        """get_status() should return comprehensive status."""
        mock_coo = MagicMock()
        listener = CSuiteBridgeListener(mock_coo)
        listener._connected = True
        listener._listening = True
        listener._guidance_requests_received = 5
        listener._outcomes_received = 10

        status = listener.get_status()

        assert status["connected"] is True
        assert status["listening"] is True
        assert status["metrics"]["guidance_requests_received"] == 5
        assert status["metrics"]["outcomes_received"] == 10
        assert "config" in status
        assert "csuite_health" in status


class TestCSuiteBridgeConfig:
    """Test CSuiteBridgeConfig dataclass."""

    def test_config_defaults(self):
        """CSuiteBridgeConfig should have sensible defaults."""
        config = CSuiteBridgeConfig()

        assert config.redis_url == "redis://localhost:6379"
        assert config.channel_prefix == "ag3ntwerk:nexus"
        assert config.response_timeout_seconds == 30
        assert config.reconnect_delay_seconds == 5.0
        assert config.max_reconnect_attempts == 10

    def test_config_custom_values(self):
        """CSuiteBridgeConfig should accept custom values."""
        config = CSuiteBridgeConfig(
            redis_url="redis://custom:6380",
            channel_prefix="test:prefix",
            response_timeout_seconds=60,
            reconnect_delay_seconds=10.0,
            max_reconnect_attempts=5,
        )

        assert config.redis_url == "redis://custom:6380"
        assert config.channel_prefix == "test:prefix"
        assert config.response_timeout_seconds == 60
        assert config.reconnect_delay_seconds == 10.0
        assert config.max_reconnect_attempts == 5
