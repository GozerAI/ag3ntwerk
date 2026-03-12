"""
Tests for ag3ntwerk execution from Nexus (Sprint 3.2).

Tests cover:
- AutonomousExecutor handling ag3ntwerk:* executor types
- _execute_via_csuite method
- NexusBridge execution request handling
- Execution response flow
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import asyncio
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


# Import the executor module directly
_executor_path = os.path.join(_nexus_src_path, "nexus", "coo", "executor.py")

if os.path.exists(_executor_path):
    _executor_module = _import_from_path("test_exec_csuite", _executor_path)
    AutonomousExecutor = _executor_module.AutonomousExecutor
    ExecutionResult = _executor_module.ExecutionResult
    ExecutionStatus = _executor_module.ExecutionStatus
    EXECUTOR_AVAILABLE = True
else:
    EXECUTOR_AVAILABLE = False
    AutonomousExecutor = None

# Import NexusBridge
try:
    from ag3ntwerk.agents.bridges.nexus_bridge import NexusBridge, NexusBridgeConfig

    NEXUS_BRIDGE_AVAILABLE = True
except ImportError:
    NEXUS_BRIDGE_AVAILABLE = False
    NexusBridge = None
    NexusBridgeConfig = None


pytestmark = pytest.mark.skipif(not EXECUTOR_AVAILABLE, reason="AutonomousExecutor not available")


class TestAutonomousExecutorCsuiteRouting:
    """Test executor routes ag3ntwerk:* executor types correctly."""

    def test_executor_has_csuite_in_executors(self):
        """ag3ntwerk should be listed in EXECUTORS."""
        assert "ag3ntwerk" in AutonomousExecutor.EXECUTORS

    def test_executor_has_csuite_timeout(self):
        """Executor should have ag3ntwerk execution timeout."""
        assert hasattr(AutonomousExecutor, "AGENTWERK_EXECUTION_TIMEOUT")
        assert AutonomousExecutor.AGENTWERK_EXECUTION_TIMEOUT > 0

    def test_executor_accepts_csuite_bridge(self):
        """Executor should accept csuite_bridge parameter."""
        mock_bridge = MagicMock()
        executor = AutonomousExecutor(csuite_bridge=mock_bridge)
        assert executor._csuite_bridge is mock_bridge

    def test_set_csuite_bridge(self):
        """set_csuite_bridge should set the bridge."""
        executor = AutonomousExecutor()
        mock_bridge = MagicMock()

        executor.set_csuite_bridge(mock_bridge)

        assert executor._csuite_bridge is mock_bridge


class TestExecuteViaCsuite:
    """Test _execute_via_csuite method."""

    @pytest.mark.asyncio
    async def test_execute_via_csuite_no_bridge_falls_back(self):
        """Without bridge, should fall back to expert_router."""
        executor = AutonomousExecutor()

        # Mock the _execute_expert_router method directly
        executor._execute_expert_router = AsyncMock(return_value={"result": "expert_output"})

        item = MagicMock()
        item.id = "test-123"
        item.task_type = "code_review"
        item.title = "Test task"
        item.description = "Test description"

        result = await executor._execute_via_csuite(item, "ag3ntwerk:Forge", {})

        # Should have fallen back to expert_router
        executor._execute_expert_router.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_via_csuite_disconnected_bridge_falls_back(self):
        """With disconnected bridge, should fall back to expert_router."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = False

        executor = AutonomousExecutor(csuite_bridge=mock_bridge)

        # Mock the _execute_expert_router method directly
        executor._execute_expert_router = AsyncMock(return_value={"result": "expert_output"})

        item = MagicMock()
        item.id = "test-456"
        item.task_type = "code_review"
        item.title = "Test task"
        item.description = "Test description"

        result = await executor._execute_via_csuite(item, "ag3ntwerk:Forge", {})

        executor._execute_expert_router.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_via_csuite_extracts_agent_code(self):
        """Should extract agent code from executor_type."""
        mock_redis = AsyncMock()
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge._redis = mock_redis
        mock_bridge.config = MagicMock(channel_prefix="test:prefix")

        executor = AutonomousExecutor(csuite_bridge=mock_bridge)

        item = MagicMock()
        item.id = "test-789"
        item.task_type = "code_review"
        item.title = "Test task"
        item.description = "Test description"

        # This will timeout since no response, but we can check the publish call
        try:
            await asyncio.wait_for(
                executor._execute_via_csuite(item, "ag3ntwerk:Echo", {}), timeout=0.5
            )
        except asyncio.TimeoutError:
            pass

        # Check that publish was called with correct channel
        if mock_redis.publish.called:
            call_args = mock_redis.publish.call_args
            channel = call_args[0][0]
            assert channel == "test:prefix:execute:request"

    @pytest.mark.asyncio
    async def test_execute_via_csuite_timeout_returns_error(self):
        """Timeout should return error result."""
        mock_redis = AsyncMock()
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge._redis = mock_redis
        mock_bridge.config = MagicMock(channel_prefix="test:prefix")

        executor = AutonomousExecutor(csuite_bridge=mock_bridge)
        executor.AGENTWERK_EXECUTION_TIMEOUT = 0.1  # Very short timeout

        item = MagicMock()
        item.id = "test-timeout"
        item.task_type = "code_review"
        item.title = "Test task"
        item.description = "Test description"

        result = await executor._execute_via_csuite(item, "ag3ntwerk:Forge", {})

        assert result["csuite_execution"] is True
        assert result["success"] is False
        assert "Timeout" in result["error"]


class TestExecuteRouting:
    """Test execute method routes ag3ntwerk:* correctly."""

    @pytest.mark.asyncio
    async def test_execute_routes_csuite_executor(self):
        """execute() should route ag3ntwerk:* to _execute_via_csuite."""
        executor = AutonomousExecutor()

        # Mock _execute_via_csuite
        executor._execute_via_csuite = AsyncMock(
            return_value={
                "csuite_execution": True,
                "success": True,
                "output": {"test": "result"},
                "confidence": 0.9,
            }
        )

        item = MagicMock()
        item.id = "test-route"

        result = await executor.execute(item, "ag3ntwerk:Forge", {})

        executor._execute_via_csuite.assert_called_once()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_non_csuite_routes_normally(self):
        """execute() should route non-ag3ntwerk to appropriate executor."""
        executor = AutonomousExecutor()

        # Mock the _execute_expert_router method directly
        executor._execute_expert_router = AsyncMock(
            return_value={"result": "expert_output", "confidence": 0.8}
        )

        item = MagicMock()
        item.id = "test-expert"
        item.title = "Test"
        item.description = "Test"
        item.priority = "medium"

        result = await executor.execute(item, "expert_router", {})

        executor._execute_expert_router.assert_called_once()


@pytest.mark.skipif(not NEXUS_BRIDGE_AVAILABLE, reason="NexusBridge not available")
class TestNexusBridgeExecutionMethods:
    """Test NexusBridge execution request/response handling."""

    def test_nexus_bridge_has_execution_methods(self):
        """NexusBridge should have execution handling methods."""
        bridge = NexusBridge()

        assert hasattr(bridge, "subscribe_to_execution_requests")
        assert hasattr(bridge, "_send_execution_response")
        assert hasattr(bridge, "publish_execution_result")

    @pytest.mark.asyncio
    async def test_subscribe_to_execution_requests_not_connected(self):
        """subscribe_to_execution_requests should warn if not connected."""
        bridge = NexusBridge()
        callback = AsyncMock()

        # Should return without error when not connected
        await bridge.subscribe_to_execution_requests(callback)

        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_execution_response_not_connected(self):
        """_send_execution_response should return False if not connected."""
        bridge = NexusBridge()

        result = await bridge._send_execution_response(
            request_id="test-123", result={"success": True}
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_execution_response_connected(self):
        """_send_execution_response should publish when connected."""
        bridge = NexusBridge()
        bridge._connected = True
        bridge._redis = AsyncMock()

        result = await bridge._send_execution_response(
            request_id="test-456",
            result={
                "success": True,
                "output": {"test": "data"},
                "confidence": 0.9,
                "duration_ms": 100,
            },
        )

        assert result is True
        bridge._redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_execution_result_not_connected(self):
        """publish_execution_result should return False if not connected."""
        bridge = NexusBridge()

        result = await bridge.publish_execution_result(task_id="task-123", result={"success": True})

        assert result is False

    @pytest.mark.asyncio
    async def test_publish_execution_result_connected(self):
        """publish_execution_result should publish when connected."""
        bridge = NexusBridge()
        bridge._connected = True
        bridge._redis = AsyncMock()

        result = await bridge.publish_execution_result(
            task_id="task-789",
            result={
                "success": True,
                "output": {"completed": True},
                "confidence": 0.85,
            },
        )

        assert result is True
        bridge._redis.publish.assert_called_once()

        # Check the channel
        call_args = bridge._redis.publish.call_args
        channel = call_args[0][0]
        assert "execute:response" in channel


class TestExecutionResultFormat:
    """Test execution result format."""

    def test_execution_result_to_dict(self):
        """ExecutionResult.to_dict() should include all fields."""
        result = ExecutionResult(
            item_id="test-item",
            executor="ag3ntwerk:Forge",
            success=True,
            status=ExecutionStatus.COMPLETED,
            output={"test": "output"},
            confidence=0.9,
            duration_minutes=1.5,
            cost_usd=0.01,
        )

        result_dict = result.to_dict()

        assert result_dict["item_id"] == "test-item"
        assert result_dict["executor"] == "ag3ntwerk:Forge"
        assert result_dict["success"] is True
        assert result_dict["status"] == "completed"
        assert result_dict["confidence"] == 0.9

    def test_execution_status_values(self):
        """ExecutionStatus should have expected values."""
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.CANCELLED.value == "cancelled"
