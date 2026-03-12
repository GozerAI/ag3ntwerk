"""
Integration tests for Nexus <-> ag3ntwerk communication.

Requires Redis running on localhost:6379
Skip with: pytest -m "not redis"

These tests verify end-to-end communication between:
- ag3ntwerk Overwatch (operational coordinator)
- Nexus AutonomousCOO (strategic brain)

via Redis pub/sub messaging.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
import os
import sys
import importlib.util

# Add nexus to path for imports
_nexus_src_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "src", "nexus", "src")
)


def _import_from_path(module_name: str, file_path: str):
    """Import a module from a specific file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Import Nexus modules directly to avoid conflicts
_csuite_bridge_path = os.path.join(_nexus_src_path, "nexus", "coo", "csuite_bridge.py")

if os.path.exists(_csuite_bridge_path):
    _csuite_bridge_module = _import_from_path("test_int_csuite_bridge", _csuite_bridge_path)
    CSuiteBridgeListener = _csuite_bridge_module.CSuiteBridgeListener
    CSuiteBridgeConfig = _csuite_bridge_module.CSuiteBridgeConfig
    NEXUS_BRIDGE_AVAILABLE = True
else:
    NEXUS_BRIDGE_AVAILABLE = False
    CSuiteBridgeListener = None
    CSuiteBridgeConfig = None

# Import ag3ntwerk modules
try:
    from ag3ntwerk.agents.bridges.nexus_bridge import NexusBridge, NexusBridgeConfig

    AGENTWERK_BRIDGE_AVAILABLE = True
except ImportError:
    AGENTWERK_BRIDGE_AVAILABLE = False
    NexusBridge = None
    NexusBridgeConfig = None


# Mark all tests in this module as requiring Redis
pytestmark = [
    pytest.mark.redis,
    pytest.mark.integration,
    pytest.mark.skipif(
        not NEXUS_BRIDGE_AVAILABLE or not AGENTWERK_BRIDGE_AVAILABLE,
        reason="Bridge modules not available",
    ),
]


class TestBridgeConnectionHandshake:
    """Test connection establishment between bridges."""

    @pytest.mark.asyncio
    async def test_nexus_bridge_connects(self, redis_client, redis_channel_prefix):
        """Nexus CSuiteBridgeListener should connect to Redis."""
        mock_coo = MagicMock()
        config = CSuiteBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        listener = CSuiteBridgeListener(mock_coo, config)

        connected = await listener.connect()

        assert connected is True
        assert listener.is_connected is True

        await listener.disconnect()
        assert listener.is_connected is False

    @pytest.mark.asyncio
    async def test_csuite_bridge_connects(self, redis_client, redis_channel_prefix):
        """ag3ntwerk NexusBridge should connect to Redis."""
        config = NexusBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        bridge = NexusBridge(config)

        connected = await bridge.connect()

        assert connected is True
        assert bridge.is_connected is True

        await bridge.disconnect()
        assert bridge.is_connected is False

    @pytest.mark.asyncio
    async def test_both_bridges_can_connect_simultaneously(
        self, redis_client, redis_channel_prefix
    ):
        """Both bridges should be able to connect to the same Redis."""
        # Nexus side
        mock_coo = MagicMock()
        nexus_config = CSuiteBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        nexus_listener = CSuiteBridgeListener(mock_coo, nexus_config)

        # ag3ntwerk side
        csuite_config = NexusBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        csuite_bridge = NexusBridge(csuite_config)

        try:
            # Both connect
            nexus_connected = await nexus_listener.connect()
            csuite_connected = await csuite_bridge.connect()

            assert nexus_connected is True
            assert csuite_connected is True
            assert nexus_listener.is_connected is True
            assert csuite_bridge.is_connected is True
        finally:
            await nexus_listener.disconnect()
            await csuite_bridge.disconnect()


class TestGuidanceRequestFlow:
    """Test guidance request from Overwatch to Nexus."""

    @pytest.mark.asyncio
    async def test_cos_sends_guidance_request_nexus_receives(
        self, redis_client, redis_channel_prefix
    ):
        """Overwatch should be able to send guidance request that Nexus receives."""
        # Setup Nexus listener
        mock_coo = MagicMock()
        mock_coo.get_status.return_value = MagicMock(mode=MagicMock(value="supervised"))
        mock_coo.config = MagicMock(
            max_concurrent_executions=3,
            auto_execute_confidence=0.9,
        )

        nexus_config = CSuiteBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        nexus_listener = CSuiteBridgeListener(mock_coo, nexus_config)

        # Setup ag3ntwerk bridge
        csuite_config = NexusBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        csuite_bridge = NexusBridge(csuite_config)

        try:
            # Connect both
            await nexus_listener.connect()
            await csuite_bridge.connect()

            # Start Nexus listening
            await nexus_listener.start_listening()

            # Give the listener time to start
            await asyncio.sleep(0.1)

            # Overwatch sends guidance request
            drift_context = {
                "drift_type": "performance",
                "drift_level": 0.6,
                "metrics": {"latency": 500, "error_rate": 0.05},
            }

            # Publish directly to the channel (simulating Overwatch request)
            channel = f"{redis_channel_prefix}:guidance:request"
            await redis_client.publish(
                channel,
                json.dumps(
                    {
                        "type": "guidance_request",
                        "drift_context": drift_context,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ),
            )

            # Give time for message to be processed
            await asyncio.sleep(0.2)

            # Check that Nexus received it
            assert nexus_listener._guidance_requests_received >= 1

        finally:
            await nexus_listener.stop_listening()
            await nexus_listener.disconnect()
            await csuite_bridge.disconnect()

    @pytest.mark.asyncio
    async def test_nexus_sends_guidance_response(self, redis_client, redis_channel_prefix):
        """Nexus should send guidance response after processing request."""
        # Setup Nexus listener
        mock_coo = MagicMock()
        mock_coo.get_status.return_value = MagicMock(mode=MagicMock(value="supervised"))
        mock_coo.config = MagicMock(
            max_concurrent_executions=3,
            auto_execute_confidence=0.9,
        )

        nexus_config = CSuiteBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        nexus_listener = CSuiteBridgeListener(mock_coo, nexus_config)

        received_responses = []

        async def response_handler():
            """Listen for guidance responses."""
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(f"{redis_channel_prefix}:guidance:response")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    received_responses.append(json.loads(message["data"]))
                    break  # Got one response, done

            await pubsub.unsubscribe()
            await pubsub.close()

        try:
            await nexus_listener.connect()
            await nexus_listener.start_listening()

            # Start response listener
            response_task = asyncio.create_task(response_handler())

            await asyncio.sleep(0.1)

            # Send guidance request
            channel = f"{redis_channel_prefix}:guidance:request"
            await redis_client.publish(
                channel,
                json.dumps(
                    {
                        "type": "guidance_request",
                        "drift_context": {"drift_type": "accuracy", "drift_level": 0.5},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ),
            )

            # Wait for response
            try:
                await asyncio.wait_for(response_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass  # May timeout, check what we got

            # Should have sent a response
            assert nexus_listener._guidance_responses_sent >= 1
            assert len(received_responses) >= 1

            if received_responses:
                response = received_responses[0]
                assert "type" in response
                assert response["type"] == "guidance_response"
                assert "guidance" in response

        finally:
            await nexus_listener.stop_listening()
            await nexus_listener.disconnect()


class TestOutcomeReportingFlow:
    """Test outcome reporting from Overwatch to Nexus."""

    @pytest.mark.asyncio
    async def test_cos_reports_outcome_nexus_receives(self, redis_client, redis_channel_prefix):
        """Overwatch outcome reports should be received by Nexus."""
        # Setup Nexus listener
        mock_coo = MagicMock()
        mock_coo._learning = None  # No learning system

        nexus_config = CSuiteBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        nexus_listener = CSuiteBridgeListener(mock_coo, nexus_config)

        try:
            await nexus_listener.connect()
            await nexus_listener.start_listening()

            await asyncio.sleep(0.1)

            # Overwatch reports outcome
            outcome_report = {
                "type": "outcome_report",
                "metrics": {
                    "task_id": "test-task-123",
                    "success": True,
                    "duration_ms": 150,
                    "agent": "Forge",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            channel = f"{redis_channel_prefix}:outcomes"
            await redis_client.publish(channel, json.dumps(outcome_report))

            await asyncio.sleep(0.2)

            # Check that Nexus received it
            assert nexus_listener._outcomes_received >= 1

        finally:
            await nexus_listener.stop_listening()
            await nexus_listener.disconnect()

    @pytest.mark.asyncio
    async def test_outcome_forwarded_to_learning_system(self, redis_client, redis_channel_prefix):
        """Outcome should be forwarded to Nexus learning system if available."""
        # Setup mock learning system
        mock_learning = MagicMock()
        mock_learning.record_external_outcome = AsyncMock()

        mock_coo = MagicMock()
        mock_coo._learning = mock_learning

        nexus_config = CSuiteBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        nexus_listener = CSuiteBridgeListener(mock_coo, nexus_config)

        try:
            await nexus_listener.connect()
            await nexus_listener.start_listening()

            await asyncio.sleep(0.1)

            # Send outcome
            outcome_report = {
                "type": "outcome_report",
                "metrics": {
                    "task_id": "test-task-456",
                    "success": False,
                    "error": "Timeout",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            channel = f"{redis_channel_prefix}:outcomes"
            await redis_client.publish(channel, json.dumps(outcome_report))

            await asyncio.sleep(0.2)

            # Check that learning system was called
            mock_learning.record_external_outcome.assert_called()

        finally:
            await nexus_listener.stop_listening()
            await nexus_listener.disconnect()


class TestHealthStatusFlow:
    """Test health status updates from Overwatch to Nexus."""

    @pytest.mark.asyncio
    async def test_cos_publishes_health_nexus_receives(self, redis_client, redis_channel_prefix):
        """Overwatch health status should be received by Nexus."""
        mock_coo = MagicMock()

        nexus_config = CSuiteBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        nexus_listener = CSuiteBridgeListener(mock_coo, nexus_config)

        try:
            await nexus_listener.connect()
            await nexus_listener.start_listening()

            await asyncio.sleep(0.1)

            # Overwatch publishes health
            health_data = {
                "type": "health_status",
                "source": "Overwatch",
                "data": {
                    "cos_metrics": {
                        "tasks_completed": 50,
                        "success_rate": 0.95,
                        "avg_latency_ms": 120,
                    },
                    "drift_status": {
                        "is_drifting": False,
                        "drift_level": 0.1,
                    },
                    "agent_health": {
                        "Forge": "healthy",
                        "Echo": "healthy",
                        "Keystone": "degraded",
                    },
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            channel = f"{redis_channel_prefix}:health"
            await redis_client.publish(channel, json.dumps(health_data))

            await asyncio.sleep(0.2)

            # Check that Nexus received it
            assert nexus_listener._health_updates_received >= 1
            assert nexus_listener.get_csuite_health() is not None

            health = nexus_listener.get_csuite_health()
            assert health["cos_metrics"]["tasks_completed"] == 50

        finally:
            await nexus_listener.stop_listening()
            await nexus_listener.disconnect()


class TestDirectiveFlow:
    """Test directives from Nexus to Overwatch."""

    @pytest.mark.asyncio
    async def test_nexus_publishes_directive(self, redis_client, redis_channel_prefix):
        """Nexus should be able to publish directives to Overwatch."""
        mock_coo = MagicMock()

        nexus_config = CSuiteBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        nexus_listener = CSuiteBridgeListener(mock_coo, nexus_config)

        received_directives = []

        async def directive_handler():
            """Listen for directives."""
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(f"{redis_channel_prefix}:directives")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    received_directives.append(json.loads(message["data"]))
                    break

            await pubsub.unsubscribe()
            await pubsub.close()

        try:
            await nexus_listener.connect()

            # Start directive listener
            listener_task = asyncio.create_task(directive_handler())
            await asyncio.sleep(0.1)

            # Publish directive
            directive = {
                "type": "update_priorities",
                "priorities": {
                    "urgent": 1.0,
                    "high": 0.7,
                    "medium": 0.4,
                    "low": 0.1,
                },
            }

            result = await nexus_listener.publish_directive(directive)

            assert result is True
            assert nexus_listener._directives_sent >= 1

            # Wait for directive to be received
            try:
                await asyncio.wait_for(listener_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass

            assert len(received_directives) >= 1

            if received_directives:
                received = received_directives[0]
                assert received["type"] == "directive"
                assert received["directive"]["type"] == "update_priorities"

        finally:
            await nexus_listener.disconnect()


class TestConnectionFailureHandling:
    """Test graceful handling of connection failures."""

    @pytest.mark.asyncio
    async def test_nexus_bridge_handles_bad_redis_url(self):
        """Nexus bridge should handle connection failure gracefully."""
        mock_coo = MagicMock()
        config = CSuiteBridgeConfig(
            redis_url="redis://nonexistent:9999",
            channel_prefix="test:fail",
        )
        listener = CSuiteBridgeListener(mock_coo, config)

        connected = await listener.connect()

        assert connected is False
        assert listener.is_connected is False

    @pytest.mark.asyncio
    async def test_csuite_bridge_handles_bad_redis_url(self):
        """ag3ntwerk bridge should handle connection failure gracefully."""
        config = NexusBridgeConfig(
            redis_url="redis://nonexistent:9999",
            channel_prefix="test:fail",
        )
        bridge = NexusBridge(config)

        connected = await bridge.connect()

        assert connected is False
        assert bridge.is_connected is False

    @pytest.mark.asyncio
    async def test_publish_directive_fails_when_not_connected(self):
        """Publishing should fail gracefully when not connected."""
        mock_coo = MagicMock()
        config = CSuiteBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix="test:noconnect",
        )
        listener = CSuiteBridgeListener(mock_coo, config)
        # Don't connect

        result = await listener.publish_directive({"type": "test"})

        assert result is False


class TestBridgeStatus:
    """Test bridge status reporting."""

    @pytest.mark.asyncio
    async def test_nexus_bridge_status(self, redis_client, redis_channel_prefix):
        """Nexus bridge should report comprehensive status."""
        mock_coo = MagicMock()
        config = CSuiteBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        listener = CSuiteBridgeListener(mock_coo, config)

        try:
            await listener.connect()
            await listener.start_listening()

            status = listener.get_status()

            assert status["connected"] is True
            assert status["listening"] is True
            assert "metrics" in status
            assert "config" in status
            assert status["config"]["redis_url"] == "redis://localhost:6379"
            assert status["config"]["channel_prefix"] == redis_channel_prefix

        finally:
            await listener.stop_listening()
            await listener.disconnect()


class TestMessageSerialization:
    """Test message serialization and deserialization."""

    @pytest.mark.asyncio
    async def test_complex_drift_context_serialization(self, redis_client, redis_channel_prefix):
        """Complex drift context should be properly serialized/deserialized."""
        mock_coo = MagicMock()
        mock_coo.get_status.return_value = MagicMock(mode=MagicMock(value="supervised"))
        mock_coo.config = MagicMock(
            max_concurrent_executions=3,
            auto_execute_confidence=0.9,
        )

        nexus_config = CSuiteBridgeConfig(
            redis_url="redis://localhost:6379",
            channel_prefix=redis_channel_prefix,
        )
        nexus_listener = CSuiteBridgeListener(mock_coo, nexus_config)

        try:
            await nexus_listener.connect()
            await nexus_listener.start_listening()
            await asyncio.sleep(0.1)

            # Send complex drift context
            complex_context = {
                "drift_type": "composite",
                "drift_level": 0.75,
                "nested": {
                    "metrics": {
                        "latency": [100, 150, 200, 180],
                        "throughput": 1000,
                    },
                    "timestamps": [
                        datetime.now(timezone.utc).isoformat(),
                    ],
                },
                "array_data": [1, 2, 3, 4, 5],
                "unicode": "Test with unicode: \u00e9\u00e8\u00ea",
            }

            channel = f"{redis_channel_prefix}:guidance:request"
            await redis_client.publish(
                channel,
                json.dumps(
                    {
                        "type": "guidance_request",
                        "drift_context": complex_context,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ),
            )

            await asyncio.sleep(0.2)

            # Should have processed without error
            assert nexus_listener._guidance_requests_received >= 1

        finally:
            await nexus_listener.stop_listening()
            await nexus_listener.disconnect()
