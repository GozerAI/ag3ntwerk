"""
Tests for ag3ntwerk Tools Workflow Module.

Tests Workflow, WorkflowStep, and workflow execution.
"""

import asyncio
import pytest
from typing import List

from ag3ntwerk.tools.base import (
    BaseTool,
    ToolParameter,
    ToolMetadata,
    ToolResult,
    ToolCategory,
    ParameterType,
)
from ag3ntwerk.tools.workflows import (
    Workflow,
    WorkflowStep,
    ToolStep,
    FunctionStep,
    ParallelStep,
    BranchStep,
    WorkflowContext,
    WorkflowResult,
    WorkflowStatus,
    StepStatus,
    StepResult,
    WorkflowRegistry,
)


class TestWorkflowContext:
    """Tests for WorkflowContext class."""

    def test_set_and_get_variable(self):
        """Test setting and getting variables."""
        context = WorkflowContext(workflow_id="test-001")

        context.set("key", "value")
        result = context.get("key")

        assert result == "value"

    def test_get_default_value(self):
        """Test getting with default value."""
        context = WorkflowContext(workflow_id="test-001")

        result = context.get("nonexistent", "default")

        assert result == "default"

    def test_get_step_output(self):
        """Test getting step output."""
        context = WorkflowContext(workflow_id="test-001")
        context.step_results["step1"] = StepResult(
            step_id="1",
            step_name="step1",
            status=StepStatus.SUCCESS,
            output={"data": 42},
        )

        output = context.get_step_output("step1")

        assert output == {"data": 42}

    def test_get_step_output_missing(self):
        """Test getting output from missing step."""
        context = WorkflowContext(workflow_id="test-001")

        output = context.get_step_output("nonexistent")

        assert output is None


class TestFunctionStep:
    """Tests for FunctionStep class."""

    @pytest.mark.asyncio
    async def test_execute_sync_function(self):
        """Test executing a synchronous function."""

        def my_func(ctx):
            return ctx.get("input", 0) * 2

        step = FunctionStep(name="double", func=my_func, output_key="result")
        context = WorkflowContext(workflow_id="test-001", variables={"input": 21})

        result = await step.execute(context)

        assert result.status == StepStatus.SUCCESS
        assert result.output == 42
        assert context.get("result") == 42

    @pytest.mark.asyncio
    async def test_execute_async_function(self):
        """Test executing an async function."""

        async def my_async_func(ctx):
            await asyncio.sleep(0.01)
            return "async result"

        step = FunctionStep(name="async_step", func=my_async_func, output_key="result")
        context = WorkflowContext(workflow_id="test-001")

        result = await step.execute(context)

        assert result.status == StepStatus.SUCCESS
        assert result.output == "async result"

    @pytest.mark.asyncio
    async def test_execute_function_error(self):
        """Test handling function errors."""

        def failing_func(ctx):
            raise ValueError("Test error")

        step = FunctionStep(name="failing", func=failing_func)
        context = WorkflowContext(workflow_id="test-001")

        result = await step.execute(context)

        assert result.status == StepStatus.FAILED
        assert "Test error" in result.error

    def test_should_execute_with_condition(self):
        """Test conditional execution."""
        step = FunctionStep(
            name="conditional",
            func=lambda ctx: "result",
            condition=lambda ctx: ctx.get("should_run", False),
        )

        context1 = WorkflowContext(workflow_id="test", variables={"should_run": True})
        context2 = WorkflowContext(workflow_id="test", variables={"should_run": False})

        assert step.should_execute(context1) is True
        assert step.should_execute(context2) is False


class TestParallelStep:
    """Tests for ParallelStep class."""

    @pytest.mark.asyncio
    async def test_execute_parallel_steps(self):
        """Test executing steps in parallel."""
        steps = [
            FunctionStep(name="step1", func=lambda ctx: "result1", output_key="out1"),
            FunctionStep(name="step2", func=lambda ctx: "result2", output_key="out2"),
            FunctionStep(name="step3", func=lambda ctx: "result3", output_key="out3"),
        ]

        parallel = ParallelStep(name="parallel", steps=steps)
        context = WorkflowContext(workflow_id="test-001")

        result = await parallel.execute(context)

        assert result.status == StepStatus.SUCCESS
        assert context.get("out1") == "result1"
        assert context.get("out2") == "result2"
        assert context.get("out3") == "result3"

    @pytest.mark.asyncio
    async def test_parallel_with_failure(self):
        """Test parallel execution with one failing step."""
        steps = [
            FunctionStep(name="success", func=lambda ctx: "ok"),
            FunctionStep(name="failure", func=lambda ctx: 1 / 0),  # Will fail
        ]

        parallel = ParallelStep(name="parallel", steps=steps)
        context = WorkflowContext(workflow_id="test-001")

        result = await parallel.execute(context)

        assert result.status == StepStatus.FAILED


class TestBranchStep:
    """Tests for BranchStep class."""

    @pytest.mark.asyncio
    async def test_execute_branch(self):
        """Test branching based on selector."""
        branches = {
            "a": FunctionStep(name="branch_a", func=lambda ctx: "result_a", output_key="out"),
            "b": FunctionStep(name="branch_b", func=lambda ctx: "result_b", output_key="out"),
        }

        branch = BranchStep(
            name="branch",
            branches=branches,
            selector=lambda ctx: ctx.get("choice"),
        )

        context = WorkflowContext(workflow_id="test", variables={"choice": "a"})
        result = await branch.execute(context)

        assert result.status == StepStatus.SUCCESS
        assert context.get("out") == "result_a"

    @pytest.mark.asyncio
    async def test_execute_unknown_branch(self):
        """Test branching with unknown branch name."""
        branches = {
            "a": FunctionStep(name="branch_a", func=lambda ctx: "result_a"),
        }

        branch = BranchStep(
            name="branch",
            branches=branches,
            selector=lambda ctx: "unknown",
        )

        context = WorkflowContext(workflow_id="test")
        result = await branch.execute(context)

        assert result.status == StepStatus.FAILED
        assert "unknown" in result.error.lower()


class TestWorkflow:
    """Tests for Workflow class."""

    @pytest.mark.asyncio
    async def test_simple_workflow(self):
        """Test a simple sequential workflow."""
        workflow = Workflow(name="simple_workflow")

        workflow.add_function_step(
            name="step1",
            func=lambda ctx: ctx.set("value", 1),
        )
        workflow.add_function_step(
            name="step2",
            func=lambda ctx: ctx.set("value", ctx.get("value") + 1),
        )
        workflow.add_function_step(
            name="step3",
            func=lambda ctx: ctx.get("value") + 1,
            output_key="final",
        )

        result = await workflow.execute()

        assert result.status == WorkflowStatus.SUCCESS
        assert len(result.steps) == 3
        assert result.output.get("final") == 3

    @pytest.mark.asyncio
    async def test_workflow_with_initial_variables(self):
        """Test workflow with initial variables."""
        workflow = Workflow(name="test_workflow")

        workflow.add_function_step(
            name="compute",
            func=lambda ctx: ctx.get("x") * ctx.get("y"),
            output_key="result",
        )

        result = await workflow.execute(variables={"x": 6, "y": 7})

        assert result.status == WorkflowStatus.SUCCESS
        assert result.output.get("result") == 42

    @pytest.mark.asyncio
    async def test_workflow_step_failure_stops(self):
        """Test workflow stops on step failure with on_error=fail."""
        workflow = Workflow(name="test", on_error="fail")

        workflow.add_function_step(name="step1", func=lambda ctx: "ok")
        workflow.add_function_step(name="step2", func=lambda ctx: 1 / 0)  # Fails
        workflow.add_function_step(name="step3", func=lambda ctx: "never reached")

        result = await workflow.execute()

        assert result.status == WorkflowStatus.FAILED
        assert len(result.steps) == 2  # Only 2 steps executed

    @pytest.mark.asyncio
    async def test_workflow_step_failure_continues(self):
        """Test workflow continues on step failure with on_error=continue."""
        workflow = Workflow(name="test", on_error="continue")

        workflow.add_function_step(name="step1", func=lambda ctx: "ok", output_key="out1")
        workflow.add_function_step(name="step2", func=lambda ctx: 1 / 0)  # Fails
        workflow.add_function_step(name="step3", func=lambda ctx: "ok", output_key="out3")

        result = await workflow.execute()

        assert result.status == WorkflowStatus.SUCCESS
        assert len(result.steps) == 3
        assert result.output.get("out1") == "ok"
        assert result.output.get("out3") == "ok"

    @pytest.mark.asyncio
    async def test_workflow_conditional_step(self):
        """Test workflow with conditional steps."""
        workflow = Workflow(name="conditional")

        workflow.add_function_step(
            name="always",
            func=lambda ctx: ctx.set("ran_always", True),
        )
        workflow.add_function_step(
            name="conditional",
            func=lambda ctx: ctx.set("ran_conditional", True),
            condition=lambda ctx: ctx.get("run_conditional", False),
        )

        # Without condition met
        result1 = await workflow.execute(variables={"run_conditional": False})
        assert result1.output.get("ran_always") is True
        assert result1.output.get("ran_conditional") is None

        # With condition met
        result2 = await workflow.execute(variables={"run_conditional": True})
        assert result2.output.get("ran_conditional") is True

    @pytest.mark.asyncio
    async def test_workflow_with_parallel_steps(self):
        """Test workflow with parallel steps."""
        workflow = Workflow(name="parallel_test")

        workflow.add_parallel_steps(
            name="parallel",
            steps=[
                FunctionStep(name="p1", func=lambda ctx: 1, output_key="v1"),
                FunctionStep(name="p2", func=lambda ctx: 2, output_key="v2"),
            ],
        )
        workflow.add_function_step(
            name="combine",
            func=lambda ctx: ctx.get("v1") + ctx.get("v2"),
            output_key="sum",
        )

        result = await workflow.execute()

        assert result.status == WorkflowStatus.SUCCESS
        assert result.output.get("sum") == 3

    @pytest.mark.asyncio
    async def test_workflow_with_branch(self):
        """Test workflow with branching."""
        workflow = Workflow(name="branch_test")

        workflow.add_branch(
            name="decision",
            branches={
                "high": FunctionStep(
                    name="high", func=lambda ctx: "priority high", output_key="msg"
                ),
                "low": FunctionStep(name="low", func=lambda ctx: "priority low", output_key="msg"),
            },
            selector=lambda ctx: ctx.get("priority"),
        )

        result = await workflow.execute(variables={"priority": "high"})

        assert result.status == WorkflowStatus.SUCCESS
        assert result.output.get("msg") == "priority high"

    def test_workflow_chaining(self):
        """Test fluent workflow building."""
        workflow = (
            Workflow(name="chained")
            .add_function_step(name="s1", func=lambda ctx: None)
            .add_function_step(name="s2", func=lambda ctx: None)
            .add_function_step(name="s3", func=lambda ctx: None)
        )

        assert len(workflow.steps) == 3


class TestWorkflowResult:
    """Tests for WorkflowResult class."""

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = WorkflowResult(
            workflow_id="wf-001",
            workflow_name="test_workflow",
            status=WorkflowStatus.SUCCESS,
            steps=[
                StepResult(step_id="1", step_name="step1", status=StepStatus.SUCCESS),
            ],
            duration_ms=150.5,
        )

        d = result.to_dict()

        assert d["workflow_id"] == "wf-001"
        assert d["status"] == "success"
        assert len(d["steps"]) == 1


class TestWorkflowRegistry:
    """Tests for WorkflowRegistry class."""

    def test_register_workflow(self):
        """Test registering a workflow."""
        registry = WorkflowRegistry()
        workflow = Workflow(name="test_workflow", description="A test workflow")

        registry.register(workflow)

        assert registry.get("test_workflow") is not None

    def test_get_nonexistent_workflow(self):
        """Test getting a workflow that doesn't exist."""
        registry = WorkflowRegistry()

        workflow = registry.get("nonexistent")

        assert workflow is None

    def test_list_workflows(self):
        """Test listing all workflows."""
        registry = WorkflowRegistry()
        registry.register(Workflow(name="wf1", description="First"))
        registry.register(Workflow(name="wf2", description="Second"))

        workflows = registry.list()

        assert len(workflows) == 2
        assert any(w["name"] == "wf1" for w in workflows)
        assert any(w["name"] == "wf2" for w in workflows)

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        """Test executing a workflow from registry."""
        registry = WorkflowRegistry()

        workflow = Workflow(name="test")
        workflow.add_function_step(
            name="compute",
            func=lambda ctx: ctx.get("x") * 2,
            output_key="result",
        )
        registry.register(workflow)

        result = await registry.execute("test", variables={"x": 21})

        assert result.status == WorkflowStatus.SUCCESS
        assert result.output.get("result") == 42

    @pytest.mark.asyncio
    async def test_execute_nonexistent_workflow(self):
        """Test executing a workflow that doesn't exist."""
        registry = WorkflowRegistry()

        result = await registry.execute("nonexistent")

        assert result.status == WorkflowStatus.FAILED
        assert "not found" in result.error.lower()
