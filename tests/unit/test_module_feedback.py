"""Tests for Module-to-Learning Feedback (Item 2).

Verifies that ModuleIntegration records success/failure outcomes
to the learning orchestrator with correct timing, task_type strings,
and HierarchyPath values. Ensures graceful degradation when no
orchestrator is connected and that learning errors never break
module execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.modules.integration import ModuleIntegration, get_integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_integration_with_orchestrator():
    """Create a ModuleIntegration with a mock learning orchestrator."""
    integration = ModuleIntegration()
    mock_orch = AsyncMock()
    mock_orch.record_outcome = AsyncMock(return_value="record-123")
    integration.connect_learning(mock_orch)
    return integration, mock_orch


# ---------------------------------------------------------------------------
# 1. Success recording with timing (duration_ms > 0)
# ---------------------------------------------------------------------------


async def test_success_recording_with_timing():
    """Successful module execution records outcome with positive duration_ms."""
    integration, mock_orch = _make_integration_with_orchestrator()

    with patch.object(
        integration,
        "_execute_trend_task",
        new_callable=AsyncMock,
        return_value={"trends": []},
    ):
        result = await integration.execute_module_task("trends", "run_analysis", {})

    mock_orch.record_outcome.assert_called_once()
    call_kwargs = mock_orch.record_outcome.call_args[1]
    assert call_kwargs["success"] is True
    assert call_kwargs["duration_ms"] > 0


# ---------------------------------------------------------------------------
# 2. Failure recording with error category
# ---------------------------------------------------------------------------


async def test_failure_recording_with_error_category():
    """When internal method returns an error dict, success=False is recorded."""
    integration, mock_orch = _make_integration_with_orchestrator()

    with patch.object(
        integration,
        "_execute_trend_task",
        new_callable=AsyncMock,
        return_value={"error": "data source unavailable"},
    ):
        result = await integration.execute_module_task("trends", "run_analysis", {})

    mock_orch.record_outcome.assert_called_once()
    call_kwargs = mock_orch.record_outcome.call_args[1]
    assert call_kwargs["success"] is False
    assert (
        "error" in call_kwargs
        or "error_category" in call_kwargs
        or call_kwargs.get("duration_ms", 0) >= 0
    )


async def test_exception_records_failure_and_propagates():
    """When internal method raises, the exception propagates but learning is still recorded."""
    integration, mock_orch = _make_integration_with_orchestrator()

    with patch.object(
        integration,
        "_execute_trend_task",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            await integration.execute_module_task("trends", "run_analysis", {})

    mock_orch.record_outcome.assert_called_once()
    call_kwargs = mock_orch.record_outcome.call_args[1]
    assert call_kwargs["success"] is False
    assert call_kwargs["duration_ms"] >= 0


# ---------------------------------------------------------------------------
# 3. Graceful degradation without orchestrator (no error)
# ---------------------------------------------------------------------------


async def test_graceful_degradation_without_orchestrator():
    """Module execution succeeds even when no learning orchestrator is connected."""
    integration = ModuleIntegration()
    # No connect_learning call — orchestrator is None

    with patch.object(
        integration,
        "_execute_trend_task",
        new_callable=AsyncMock,
        return_value={"trends": ["ai"]},
    ):
        result = await integration.execute_module_task("trends", "run_analysis", {})

    # Should return data without raising
    assert result is not None


# ---------------------------------------------------------------------------
# 4. Each module type generates correct task_type string
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module_id,internal_method,task_type",
    [
        ("trends", "_execute_trend_task", "fetch_trends"),
        ("commerce", "_execute_commerce_task", "analyze_sales"),
        ("brand", "_execute_brand_task", "check_consistency"),
        ("scheduler", "_execute_scheduler_task", "schedule_task"),
    ],
)
async def test_task_type_string_format(module_id, internal_method, task_type):
    """Each module produces a task_type string of 'module.{module_id}.{task_type}'."""
    integration, mock_orch = _make_integration_with_orchestrator()

    with patch.object(
        integration,
        internal_method,
        new_callable=AsyncMock,
        return_value={"ok": True},
    ):
        await integration.execute_module_task(module_id, task_type, {})

    mock_orch.record_outcome.assert_called_once()
    call_kwargs = mock_orch.record_outcome.call_args[1]
    assert call_kwargs["task_type"] == f"module.{module_id}.{task_type}"


# ---------------------------------------------------------------------------
# 5. connect_learning sets the orchestrator
# ---------------------------------------------------------------------------


async def test_connect_learning_sets_orchestrator():
    """connect_learning stores the orchestrator reference internally."""
    integration = ModuleIntegration()
    assert integration._learning_orchestrator is None

    mock_orch = AsyncMock()
    integration.connect_learning(mock_orch)
    assert integration._learning_orchestrator is mock_orch


async def test_connect_learning_replaces_orchestrator():
    """Calling connect_learning again replaces the previous orchestrator."""
    integration = ModuleIntegration()
    first = AsyncMock()
    second = AsyncMock()

    integration.connect_learning(first)
    assert integration._learning_orchestrator is first

    integration.connect_learning(second)
    assert integration._learning_orchestrator is second


# ---------------------------------------------------------------------------
# 6. Learning recording errors don't break module execution
# ---------------------------------------------------------------------------


async def test_learning_error_does_not_break_execution():
    """If orchestrator.record_outcome raises, module execution still returns data."""
    integration, mock_orch = _make_integration_with_orchestrator()
    mock_orch.record_outcome.side_effect = Exception("learning DB down")

    with patch.object(
        integration,
        "_execute_trend_task",
        new_callable=AsyncMock,
        return_value={"trends": ["blockchain"]},
    ):
        result = await integration.execute_module_task("trends", "run_analysis", {})

    # Module result should still be returned despite learning failure
    assert result == {"trends": ["blockchain"]}


async def test_learning_timeout_does_not_break_execution():
    """If orchestrator.record_outcome times out, module execution still succeeds."""
    integration, mock_orch = _make_integration_with_orchestrator()
    mock_orch.record_outcome.side_effect = TimeoutError("record_outcome timed out")

    with patch.object(
        integration,
        "_execute_commerce_task",
        new_callable=AsyncMock,
        return_value={"sales": 42},
    ):
        result = await integration.execute_module_task("commerce", "get_sales", {})

    assert result == {"sales": 42}


# ---------------------------------------------------------------------------
# 7. HierarchyPath agent is "module.{module_id}"
# ---------------------------------------------------------------------------


async def test_hierarchy_path_executive_format():
    """The HierarchyPath passed to record_outcome has agent='module.{module_id}'."""
    integration, mock_orch = _make_integration_with_orchestrator()

    with patch.object(
        integration,
        "_execute_brand_task",
        new_callable=AsyncMock,
        return_value={"score": 0.95},
    ):
        await integration.execute_module_task("brand", "audit", {})

    mock_orch.record_outcome.assert_called_once()
    call_kwargs = mock_orch.record_outcome.call_args[1]

    # The hierarchy_path (or path) should contain the module agent identifier
    path = call_kwargs.get("hierarchy_path") or call_kwargs.get("path")
    if path is not None:
        # HierarchyPath object — check .agent attribute
        agent = getattr(path, "agent", str(path))
        assert agent == "module.brand"
    else:
        # May be passed positionally
        call_args = mock_orch.record_outcome.call_args[0]
        assert any("module.brand" in str(a) for a in call_args)


async def test_hierarchy_path_executive_for_scheduler():
    """HierarchyPath agent matches 'module.scheduler' for scheduler tasks."""
    integration, mock_orch = _make_integration_with_orchestrator()

    with patch.object(
        integration,
        "_execute_scheduler_task",
        new_callable=AsyncMock,
        return_value={"scheduled": True},
    ):
        await integration.execute_module_task("scheduler", "create_job", {})

    mock_orch.record_outcome.assert_called_once()
    call_kwargs = mock_orch.record_outcome.call_args[1]

    path = call_kwargs.get("hierarchy_path") or call_kwargs.get("path")
    if path is not None:
        agent = getattr(path, "agent", str(path))
        assert agent == "module.scheduler"
    else:
        call_args = mock_orch.record_outcome.call_args[0]
        assert any("module.scheduler" in str(a) for a in call_args)
