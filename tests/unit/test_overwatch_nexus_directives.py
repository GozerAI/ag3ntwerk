"""
Tests for Overwatch handling of Nexus directives (Sprint 3.3).

Tests cover:
- _handle_nexus_execution_request method
- start_nexus_execution_listener method
- connect_to_nexus starting the listener automatically
- Execution request routing to target agent
- Error handling for failed executions
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from ag3ntwerk.agents.overwatch.agent import Overwatch
from ag3ntwerk.core.base import Task, TaskResult, TaskStatus


class TestHandleNexusExecutionRequest:
    """Test _handle_nexus_execution_request method."""

    @pytest.mark.asyncio
    async def test_handles_basic_execution_request(self):
        """Should handle a basic execution request from Nexus."""
        cos = Overwatch()

        # Mock delegate to return success
        cos.delegate = AsyncMock(
            return_value=TaskResult(
                task_id="test-123",
                success=True,
                output={"result": "done"},
                metrics={"confidence": 0.9},
            )
        )

        # Register a mock agent
        mock_cto = MagicMock()
        mock_cto.code = "Forge"
        mock_cto.is_active = True
        cos._subordinates["Forge"] = mock_cto

        request = {
            "task_id": "test-123",
            "task_type": "code_review",
            "title": "Review auth module",
            "description": "Review security of authentication module",
            "target_agent": "Forge",
            "context": {"priority": "high"},
        }

        result = await cos._handle_nexus_execution_request(request)

        assert result["success"] is True
        assert result["output"] == {"result": "done"}
        assert result["error"] is None
        assert "duration_ms" in result
        cos.delegate.assert_called_once()

    @pytest.mark.asyncio
    async def test_routes_to_target_agent(self):
        """Should route directly to target agent if specified."""
        cos = Overwatch()

        # Track which agent receives the task
        delegated_to = []

        async def mock_delegate(task, target):
            delegated_to.append(target)
            return TaskResult(
                task_id=task.id,
                success=True,
                output={},
            )

        cos.delegate = mock_delegate

        # Register mock agents
        for code in ["Forge", "Echo", "Keystone"]:
            mock_exec = MagicMock()
            mock_exec.code = code
            mock_exec.is_active = True
            cos._subordinates[code] = mock_exec

        request = {
            "task_id": "test-456",
            "task_type": "campaign_creation",
            "description": "Create marketing campaign",
            "target_agent": "Echo",
        }

        result = await cos._handle_nexus_execution_request(request)

        assert result["success"] is True
        assert delegated_to == ["Echo"]

    @pytest.mark.asyncio
    async def test_uses_normal_routing_if_no_target(self):
        """Should use normal routing if no target_agent specified."""
        cos = Overwatch()

        # Mock execute (normal routing path)
        cos.execute = AsyncMock(
            return_value=TaskResult(
                task_id="test-789",
                success=True,
                output={"routed": True},
            )
        )

        request = {
            "task_id": "test-789",
            "task_type": "general",
            "description": "General task",
        }

        result = await cos._handle_nexus_execution_request(request)

        assert result["success"] is True
        cos.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_execution_failure(self):
        """Should handle execution failures gracefully."""
        cos = Overwatch()

        # Mock execute to fail
        cos.execute = AsyncMock(
            return_value=TaskResult(
                task_id="test-fail",
                success=False,
                error="Execution failed",
            )
        )

        request = {
            "task_id": "test-fail",
            "task_type": "code_review",
            "description": "Will fail",
        }

        result = await cos._handle_nexus_execution_request(request)

        assert result["success"] is False
        assert result["error"] == "Execution failed"
        assert result["confidence"] == 0.8  # Default when metrics unavailable

    @pytest.mark.asyncio
    async def test_handles_exception_during_execution(self):
        """Should handle exceptions during execution."""
        cos = Overwatch()

        # Mock execute to raise exception
        cos.execute = AsyncMock(side_effect=Exception("Unexpected error"))

        request = {
            "task_id": "test-exception",
            "task_type": "code_review",
            "description": "Will throw",
        }

        result = await cos._handle_nexus_execution_request(request)

        assert result["success"] is False
        assert "Unexpected error" in result["error"]
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_tracks_duration(self):
        """Should track execution duration in milliseconds."""
        cos = Overwatch()

        import asyncio

        async def slow_execute(task):
            await asyncio.sleep(0.1)  # 100ms delay
            return TaskResult(task_id=task.id, success=True, output={})

        cos.execute = slow_execute

        request = {
            "task_id": "test-duration",
            "task_type": "general",
            "description": "Slow task",
        }

        result = await cos._handle_nexus_execution_request(request)

        assert result["success"] is True
        assert result["duration_ms"] >= 100  # At least 100ms

    @pytest.mark.asyncio
    async def test_publishes_result_to_nexus(self):
        """Should publish execution result back to Nexus if connected."""
        cos = Overwatch()

        # Mock bridge
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_execution_result = AsyncMock(return_value=True)
        cos._nexus_bridge = mock_bridge

        # Mock execute
        cos.execute = AsyncMock(
            return_value=TaskResult(
                task_id="test-publish",
                success=True,
                output={"data": "result"},
            )
        )

        request = {
            "task_id": "test-publish",
            "task_type": "general",
            "description": "Test",
        }

        result = await cos._handle_nexus_execution_request(request)

        mock_bridge.publish_execution_result.assert_called_once()
        call_args = mock_bridge.publish_execution_result.call_args
        assert call_args[0][0] == "test-publish"

    @pytest.mark.asyncio
    async def test_creates_task_with_nexus_context(self):
        """Should create task with Nexus-specific context."""
        cos = Overwatch()

        captured_task = None

        async def capture_execute(task):
            nonlocal captured_task
            captured_task = task
            return TaskResult(task_id=task.id, success=True, output={})

        cos.execute = capture_execute

        request = {
            "task_id": "test-context",
            "task_type": "code_review",
            "title": "Review Code",
            "description": "Full description",
            "target_agent": "Forge",
            "context": {"custom": "data"},
        }

        await cos._handle_nexus_execution_request(request)

        assert captured_task is not None
        assert captured_task.id == "test-context"
        assert captured_task.task_type == "code_review"
        assert captured_task.context["nexus_request"] is True
        assert captured_task.context["target_agent"] == "Forge"
        assert captured_task.context["custom"] == "data"
        assert captured_task.context["original_title"] == "Review Code"


class TestStartNexusExecutionListener:
    """Test start_nexus_execution_listener method."""

    @pytest.mark.asyncio
    async def test_warns_if_not_connected(self):
        """Should warn if bridge not connected."""
        cos = Overwatch()

        with patch("ag3ntwerk.agents.overwatch.nexus_mixin.logger") as mock_logger:
            await cos.start_nexus_execution_listener()
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_starts_listener_task(self):
        """Should start background task for listening."""
        cos = Overwatch()

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.subscribe_to_execution_requests = AsyncMock()
        cos._nexus_bridge = mock_bridge

        await cos.start_nexus_execution_listener()

        # Give the task a moment to start
        import asyncio

        await asyncio.sleep(0.01)

        # The subscription should have been called
        mock_bridge.subscribe_to_execution_requests.assert_called_once()

        # Callback should be the handler
        call_args = mock_bridge.subscribe_to_execution_requests.call_args
        callback = call_args[0][0]
        assert callback == cos._handle_nexus_execution_request


class TestConnectToNexusStartsListener:
    """Test that connect_to_nexus starts the execution listener."""

    @pytest.mark.asyncio
    async def test_connect_starts_execution_listener(self):
        """connect_to_nexus should start execution listener after connecting."""
        cos = Overwatch()

        # Mock NexusBridge
        with patch("ag3ntwerk.agents.overwatch.nexus_mixin.NEXUS_BRIDGE_AVAILABLE", True):
            with patch("ag3ntwerk.agents.overwatch.nexus_mixin.NexusBridge") as MockBridge:
                with patch("ag3ntwerk.agents.overwatch.nexus_mixin.NexusBridgeConfig"):
                    mock_bridge = MagicMock()
                    mock_bridge.connect = AsyncMock(return_value=True)
                    mock_bridge.sync_context = AsyncMock(return_value=None)
                    mock_bridge.is_connected = True
                    mock_bridge.subscribe_to_execution_requests = AsyncMock()
                    MockBridge.return_value = mock_bridge

                    result = await cos.connect_to_nexus("redis://localhost:6379")

                    assert result is True

                    # Give async task a moment to start
                    import asyncio

                    await asyncio.sleep(0.01)

                    # Should have started listening
                    mock_bridge.subscribe_to_execution_requests.assert_called_once()


class TestExecutionRequestIntegration:
    """Integration-style tests for execution request flow."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(self):
        """Test complete execution request -> response flow."""
        cos = Overwatch()

        # Setup mock agents
        mock_cto = MagicMock()
        mock_cto.code = "Forge"
        mock_cto.name = "Forge"
        mock_cto.is_active = True
        mock_cto.can_handle = MagicMock(return_value=True)
        mock_cto.execute = AsyncMock(
            return_value=TaskResult(
                task_id="flow-test",
                success=True,
                output={"review": "Code looks good"},
                metrics={"confidence": 0.95, "handled_by": "Forge"},
            )
        )
        cos._subordinates["Forge"] = mock_cto

        # Setup mock bridge
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_execution_result = AsyncMock(return_value=True)
        cos._nexus_bridge = mock_bridge

        # Mock delegate to use the mock agent
        async def mock_delegate(task, target):
            return await cos._subordinates[target].execute(task)

        cos.delegate = mock_delegate

        # Simulate Nexus request
        request = {
            "task_id": "flow-test",
            "task_type": "code_review",
            "title": "Review auth.py",
            "description": "Check for security issues",
            "target_agent": "Forge",
            "context": {"file": "auth.py"},
        }

        result = await cos._handle_nexus_execution_request(request)

        # Verify result
        assert result["success"] is True
        assert result["output"] == {"review": "Code looks good"}
        assert result["error"] is None
        assert result["duration_ms"] > 0

        # Verify result was published back to Nexus
        mock_bridge.publish_execution_result.assert_called_once_with("flow-test", result)

    @pytest.mark.asyncio
    async def test_fallback_when_target_not_available(self):
        """Should use normal routing when target agent not registered."""
        cos = Overwatch()

        # No agents registered
        cos.execute = AsyncMock(
            return_value=TaskResult(
                task_id="fallback-test",
                success=True,
                output={"handled": "by routing"},
            )
        )

        request = {
            "task_id": "fallback-test",
            "task_type": "code_review",
            "target_agent": "Forge",  # Not registered
        }

        result = await cos._handle_nexus_execution_request(request)

        # Should fall back to normal execute
        assert result["success"] is True
        cos.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_missing_optional_fields(self):
        """Should handle requests with minimal required fields."""
        cos = Overwatch()

        cos.execute = AsyncMock(
            return_value=TaskResult(
                task_id="minimal-test",
                success=True,
                output={},
            )
        )

        # Minimal request - just task_id
        request = {
            "task_id": "minimal-test",
        }

        result = await cos._handle_nexus_execution_request(request)

        assert result["success"] is True
        assert result["duration_ms"] > 0


class TestNexusDirectiveSubscription:
    """Test subscribe_to_nexus_directives method."""

    @pytest.mark.asyncio
    async def test_warns_if_not_connected(self):
        """Should warn if trying to subscribe without connection."""
        cos = Overwatch()

        async def dummy_callback(directive):
            pass

        with patch("ag3ntwerk.agents.overwatch.nexus_mixin.logger") as mock_logger:
            await cos.subscribe_to_nexus_directives(dummy_callback)
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_subscribes_to_directives(self):
        """Should subscribe to directives when connected."""
        cos = Overwatch()

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.subscribe_to_directives = AsyncMock()
        cos._nexus_bridge = mock_bridge

        async def my_callback(directive):
            pass

        await cos.subscribe_to_nexus_directives(my_callback)

        mock_bridge.subscribe_to_directives.assert_called_once_with(my_callback)
