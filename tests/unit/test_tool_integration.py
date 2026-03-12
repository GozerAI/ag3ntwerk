"""Tests for Tool System Integration (Item 3).

Covers:
- Tool execution returns ToolResult
- Plugin dispatch fires (pre/post/error)
- Unknown tool returns error ToolResult
- Agent code is passed in ExecutionContext metadata
- Timeout parameter is forwarded
- use_tool works without orchestrator (graceful)
- use_tool handles ImportError gracefully (returns error ToolResult or dict)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ag3ntwerk.core.base import Agent, Task, TaskResult
from ag3ntwerk.tools.base import ToolResult


# ---------------------------------------------------------------------------
# Concrete agent subclass (Agent is abstract)
# Prefixed with '_' to prevent pytest from collecting it as a test class.
# ---------------------------------------------------------------------------
class _StubAgent(Agent):
    """Minimal concrete agent for testing use_tool."""

    async def execute(self, task: Task) -> TaskResult:
        return TaskResult(task_id=task.id, success=True)

    def can_handle(self, task: Task) -> bool:
        return True


def _make_agent(code: str = "TEST") -> _StubAgent:
    return _StubAgent(code=code, name="StubAgent", domain="testing")


# ---------------------------------------------------------------------------
# 1. Tool execution returns ToolResult
# ---------------------------------------------------------------------------
class TestToolExecutionReturnsToolResult:
    """Verify that use_tool returns a ToolResult on success."""

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_use_tool_returns_tool_result(self, mock_get_exec):
        expected = ToolResult(success=True, data={"answer": 42})
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=expected)
        executor._generate_execution_id = MagicMock(return_value="exec-1")
        mock_get_exec.return_value = executor

        agent = _make_agent()
        result = await agent.use_tool("some_tool", param="value")

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.data == {"answer": 42}

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_use_tool_returns_tool_result_with_data(self, mock_get_exec):
        expected = ToolResult(success=True, data={"key": "val"})
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=expected)
        executor._generate_execution_id = MagicMock(return_value="exec-2")
        mock_get_exec.return_value = executor

        agent = _make_agent()
        result = await agent.use_tool("lookup", query="test")

        assert result.success is True
        assert result.data["key"] == "val"


# ---------------------------------------------------------------------------
# 2. Plugin dispatch fires (pre / post / error)
# ---------------------------------------------------------------------------
class TestPluginDispatch:
    """Verify that the executor is invoked (which fires plugin hooks internally)."""

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_executor_execute_is_called(self, mock_get_exec):
        expected = ToolResult(success=True, data={})
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=expected)
        executor._generate_execution_id = MagicMock(return_value="exec-3")
        mock_get_exec.return_value = executor

        agent = _make_agent()
        result = await agent.use_tool("my_tool")

        executor.execute.assert_awaited_once()
        assert result.success is True

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_executor_called_once_per_use_tool(self, mock_get_exec):
        expected = ToolResult(success=True, data={"done": True})
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=expected)
        executor._generate_execution_id = MagicMock(return_value="exec-4")
        mock_get_exec.return_value = executor

        agent = _make_agent()
        result = await agent.use_tool("my_tool")

        assert result.success is True
        assert executor.execute.await_count == 1

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_error_in_executor_returns_failed_result(self, mock_get_exec):
        """When executor.execute raises, use_tool catches and returns error ToolResult."""
        executor = MagicMock()
        executor.execute = AsyncMock(side_effect=RuntimeError("boom"))
        executor._generate_execution_id = MagicMock(return_value="exec-5")
        mock_get_exec.return_value = executor

        agent = _make_agent()
        result = await agent.use_tool("bad_tool")

        # use_tool wraps exceptions into a ToolResult with success=False
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "boom" in (result.error or "")
        assert result.error_type == "RuntimeError"


# ---------------------------------------------------------------------------
# 3. Unknown tool returns error ToolResult
# ---------------------------------------------------------------------------
class TestUnknownToolError:
    """Unknown tool names should yield an error ToolResult, not raise."""

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_unknown_tool_returns_error(self, mock_get_exec):
        error_result = ToolResult(
            success=False,
            error="Tool not found: nonexistent_tool",
            error_type="ToolNotFoundError",
        )
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=error_result)
        executor._generate_execution_id = MagicMock(return_value="exec-6")
        mock_get_exec.return_value = executor

        agent = _make_agent()
        result = await agent.use_tool("nonexistent_tool")

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "not found" in (result.error or "").lower()

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_unknown_tool_has_error_type(self, mock_get_exec):
        error_result = ToolResult(
            success=False,
            error="Unknown tool",
            error_type="ToolNotFoundError",
        )
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=error_result)
        executor._generate_execution_id = MagicMock(return_value="exec-7")
        mock_get_exec.return_value = executor

        agent = _make_agent()
        result = await agent.use_tool("ghost_tool")

        assert result.error_type is not None


# ---------------------------------------------------------------------------
# 4. Agent code is passed in ExecutionContext metadata
# ---------------------------------------------------------------------------
class TestExecutionContextMetadata:
    """The agent's code must appear in the ExecutionContext passed to the executor."""

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_agent_code_in_context_CFO(self, mock_get_exec):
        expected = ToolResult(success=True, data={})
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=expected)
        executor._generate_execution_id = MagicMock(return_value="exec-8")
        mock_get_exec.return_value = executor

        agent = _make_agent(code="Keystone")
        await agent.use_tool("finance_tool", amount=100)

        call_kwargs = executor.execute.call_args.kwargs
        ctx = call_kwargs.get("context")
        assert ctx is not None, "ExecutionContext must be passed to executor"
        assert ctx.metadata.get("agent_code") == "Keystone"

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_agent_code_in_context_CTO(self, mock_get_exec):
        expected = ToolResult(success=True, data={})
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=expected)
        executor._generate_execution_id = MagicMock(return_value="exec-9")
        mock_get_exec.return_value = executor

        agent = _make_agent(code="Forge")
        await agent.use_tool("tech_tool")

        call_kwargs = executor.execute.call_args.kwargs
        ctx = call_kwargs.get("context")
        assert ctx is not None
        assert ctx.metadata.get("agent_code") == "Forge"

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_context_tool_name_matches(self, mock_get_exec):
        expected = ToolResult(success=True, data={})
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=expected)
        executor._generate_execution_id = MagicMock(return_value="exec-10")
        mock_get_exec.return_value = executor

        agent = _make_agent(code="Sentinel")
        await agent.use_tool("data_tool", source="db")

        call_kwargs = executor.execute.call_args.kwargs
        ctx = call_kwargs.get("context")
        assert ctx.tool_name == "data_tool"


# ---------------------------------------------------------------------------
# 5. Timeout parameter is forwarded
# ---------------------------------------------------------------------------
class TestTimeoutForwarding:
    """Verify that the timeout kwarg reaches the executor."""

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_timeout_is_forwarded(self, mock_get_exec):
        expected = ToolResult(success=True, data={})
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=expected)
        executor._generate_execution_id = MagicMock(return_value="exec-11")
        mock_get_exec.return_value = executor

        agent = _make_agent()
        await agent.use_tool("slow_tool", timeout=30)

        call_kwargs = executor.execute.call_args.kwargs
        assert call_kwargs.get("timeout") == 30

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_no_timeout_passes_none(self, mock_get_exec):
        expected = ToolResult(success=True, data={})
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=expected)
        executor._generate_execution_id = MagicMock(return_value="exec-12")
        mock_get_exec.return_value = executor

        agent = _make_agent()
        await agent.use_tool("fast_tool")

        call_kwargs = executor.execute.call_args.kwargs
        # timeout should be None when not specified
        assert call_kwargs.get("timeout") is None


# ---------------------------------------------------------------------------
# 6. use_tool works without orchestrator (graceful)
# ---------------------------------------------------------------------------
class TestUseToolWithoutOrchestrator:
    """Agents without an orchestrator should still call use_tool without error."""

    @patch("ag3ntwerk.tools.executor.get_executor")
    async def test_no_orchestrator_still_works(self, mock_get_exec):
        expected = ToolResult(success=True, data={"ok": True})
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=expected)
        executor._generate_execution_id = MagicMock(return_value="exec-13")
        mock_get_exec.return_value = executor

        agent = _make_agent()
        # Ensure no orchestrator is attached
        if hasattr(agent, "orchestrator"):
            agent.orchestrator = None

        result = await agent.use_tool("standalone_tool")

        assert isinstance(result, ToolResult)
        assert result.success is True


# ---------------------------------------------------------------------------
# 7. use_tool handles ImportError gracefully (returns error ToolResult or dict)
# ---------------------------------------------------------------------------
class TestImportErrorHandling:
    """If the tools package cannot be imported, use_tool should not raise."""

    async def test_import_error_returns_error_result(self):
        """Simulate ImportError by patching the import inside use_tool."""
        agent = _make_agent()

        # Patch the import of ag3ntwerk.tools.executor so it raises ImportError
        original_import = (
            __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
        )

        def _failing_import(name, *args, **kwargs):
            if name == "ag3ntwerk.tools.executor":
                raise ImportError("tools not installed")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_failing_import):
            result = await agent.use_tool("any_tool")

        # The outer except in use_tool catches ImportError and tries to import ToolResult
        # If that also fails, it returns a plain dict
        if isinstance(result, ToolResult):
            assert result.success is False
            assert result.error is not None
        elif isinstance(result, dict):
            assert result.get("success") is False
            assert "error" in result

    @patch("ag3ntwerk.tools.executor.get_executor", side_effect=ImportError("no tools"))
    async def test_get_executor_import_error_caught(self, mock_get_exec):
        """When get_executor itself raises ImportError, use_tool catches it."""
        agent = _make_agent()
        result = await agent.use_tool("missing_tool")

        # use_tool catches Exception (ImportError is a subclass)
        # and returns ToolResult(success=False, ...)
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "no tools" in (result.error or "")
        assert result.error_type == "ImportError"

    @patch("ag3ntwerk.tools.executor.get_executor", side_effect=ImportError("unavailable"))
    async def test_import_error_contains_error_type(self, mock_get_exec):
        agent = _make_agent()
        result = await agent.use_tool("whatever")

        assert isinstance(result, ToolResult)
        assert result.error_type == "ImportError"
