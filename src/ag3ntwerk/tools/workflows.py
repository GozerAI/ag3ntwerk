"""
Workflow Engine for ag3ntwerk.

Provides multi-step workflow execution with:
- Sequential and parallel execution
- Conditional branching
- Variable passing between steps
- Error handling and rollback
- Workflow persistence
"""

import asyncio
import inspect
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum
from abc import ABC, abstractmethod

from ag3ntwerk.tools.base import BaseTool, ToolResult
from ag3ntwerk.tools.executor import get_executor, ExecutionContext

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class StepResult:
    """Result of a workflow step execution."""

    step_id: str
    step_name: str
    status: StepStatus
    output: Any = None
    error: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: float = 0


@dataclass
class WorkflowContext:
    """Context passed through workflow execution."""

    workflow_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        """Set a variable."""
        self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a variable."""
        return self.variables.get(key, default)

    def get_step_output(self, step_name: str) -> Any:
        """Get output from a previous step."""
        result = self.step_results.get(step_name)
        return result.output if result else None


class WorkflowStep(ABC):
    """Base class for workflow steps."""

    def __init__(
        self,
        name: str,
        description: str = "",
        condition: Optional[Callable[[WorkflowContext], bool]] = None,
        on_error: str = "fail",  # fail, skip, retry
        max_retries: int = 3,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.description = description
        self.condition = condition
        self.on_error = on_error
        self.max_retries = max_retries

    def should_execute(self, context: WorkflowContext) -> bool:
        """Check if step should execute."""
        if self.condition is None:
            return True
        return self.condition(context)

    @abstractmethod
    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute the step."""
        pass


class ToolStep(WorkflowStep):
    """Step that executes a tool."""

    def __init__(
        self,
        name: str,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        parameter_mapping: Optional[Dict[str, str]] = None,
        output_key: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize a tool step.

        Args:
            name: Step name
            tool_name: Name of the tool to execute
            parameters: Static parameters
            parameter_mapping: Map parameter names to context variables
            output_key: Key to store output in context
        """
        super().__init__(name, **kwargs)
        self.tool_name = tool_name
        self.parameters = parameters or {}
        self.parameter_mapping = parameter_mapping or {}
        self.output_key = output_key

    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute the tool."""
        started_at = datetime.now()

        try:
            # Build parameters
            params = dict(self.parameters)

            # Apply parameter mapping from context
            for param_name, context_key in self.parameter_mapping.items():
                if context_key.startswith("$step."):
                    # Get from step output
                    step_name = context_key[6:]
                    params[param_name] = context.get_step_output(step_name)
                else:
                    # Get from variables
                    params[param_name] = context.get(context_key)

            # Execute tool
            executor = get_executor()
            exec_context = ExecutionContext(
                execution_id=f"{context.workflow_id}-{self.id}",
                tool_name=self.tool_name,
                parameters=params,
                metadata={"workflow_id": context.workflow_id, "step": self.name},
            )

            result = await executor.execute(
                self.tool_name,
                context=exec_context,
                **params,
            )

            finished_at = datetime.now()

            # Store output in context
            if self.output_key and result.success:
                context.set(self.output_key, result.data)

            step_result = StepResult(
                step_id=self.id,
                step_name=self.name,
                status=StepStatus.SUCCESS if result.success else StepStatus.FAILED,
                output=result.data if result.success else None,
                error=result.error or "",
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=(finished_at - started_at).total_seconds() * 1000,
            )

            context.step_results[self.name] = step_result
            return step_result

        except Exception as e:
            finished_at = datetime.now()
            step_result = StepResult(
                step_id=self.id,
                step_name=self.name,
                status=StepStatus.FAILED,
                error=str(e),
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=(finished_at - started_at).total_seconds() * 1000,
            )
            context.step_results[self.name] = step_result
            return step_result


class FunctionStep(WorkflowStep):
    """Step that executes a Python function."""

    def __init__(
        self,
        name: str,
        func: Callable[[WorkflowContext], Any],
        output_key: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(name, **kwargs)
        self.func = func
        self.output_key = output_key

    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute the function."""
        started_at = datetime.now()

        try:
            if inspect.iscoroutinefunction(self.func):
                output = await self.func(context)
            else:
                output = self.func(context)

            finished_at = datetime.now()

            if self.output_key:
                context.set(self.output_key, output)

            step_result = StepResult(
                step_id=self.id,
                step_name=self.name,
                status=StepStatus.SUCCESS,
                output=output,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=(finished_at - started_at).total_seconds() * 1000,
            )

            context.step_results[self.name] = step_result
            return step_result

        except Exception as e:
            finished_at = datetime.now()
            step_result = StepResult(
                step_id=self.id,
                step_name=self.name,
                status=StepStatus.FAILED,
                error=str(e),
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=(finished_at - started_at).total_seconds() * 1000,
            )
            context.step_results[self.name] = step_result
            return step_result


class ParallelStep(WorkflowStep):
    """Step that executes multiple steps in parallel."""

    def __init__(
        self,
        name: str,
        steps: List[WorkflowStep],
        **kwargs,
    ):
        super().__init__(name, **kwargs)
        self.steps = steps

    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute steps in parallel."""
        started_at = datetime.now()

        try:
            # Execute all steps in parallel
            results = await asyncio.gather(
                *[step.execute(context) for step in self.steps if step.should_execute(context)]
            )

            finished_at = datetime.now()

            # Check if all succeeded
            all_success = all(r.status == StepStatus.SUCCESS for r in results)

            step_result = StepResult(
                step_id=self.id,
                step_name=self.name,
                status=StepStatus.SUCCESS if all_success else StepStatus.FAILED,
                output={r.step_name: r.output for r in results},
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=(finished_at - started_at).total_seconds() * 1000,
            )

            context.step_results[self.name] = step_result
            return step_result

        except Exception as e:
            finished_at = datetime.now()
            step_result = StepResult(
                step_id=self.id,
                step_name=self.name,
                status=StepStatus.FAILED,
                error=str(e),
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=(finished_at - started_at).total_seconds() * 1000,
            )
            context.step_results[self.name] = step_result
            return step_result


class BranchStep(WorkflowStep):
    """Step that branches based on conditions."""

    def __init__(
        self,
        name: str,
        branches: Dict[str, WorkflowStep],
        selector: Callable[[WorkflowContext], str],
        **kwargs,
    ):
        """
        Initialize a branch step.

        Args:
            name: Step name
            branches: Dict mapping branch names to steps
            selector: Function that returns branch name to execute
        """
        super().__init__(name, **kwargs)
        self.branches = branches
        self.selector = selector

    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute the selected branch."""
        started_at = datetime.now()

        try:
            branch_name = self.selector(context)
            step = self.branches.get(branch_name)

            if not step:
                raise ValueError(f"Unknown branch: {branch_name}")

            result = await step.execute(context)

            finished_at = datetime.now()

            step_result = StepResult(
                step_id=self.id,
                step_name=self.name,
                status=result.status,
                output={"branch": branch_name, "result": result.output},
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=(finished_at - started_at).total_seconds() * 1000,
            )

            context.step_results[self.name] = step_result
            return step_result

        except Exception as e:
            finished_at = datetime.now()
            step_result = StepResult(
                step_id=self.id,
                step_name=self.name,
                status=StepStatus.FAILED,
                error=str(e),
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=(finished_at - started_at).total_seconds() * 1000,
            )
            context.step_results[self.name] = step_result
            return step_result


@dataclass
class WorkflowResult:
    """Result of workflow execution."""

    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    steps: List[StepResult]
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: float = 0
    error: str = ""
    output: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "steps": [
                {
                    "name": s.step_name,
                    "status": s.status.value,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                }
                for s in self.steps
            ],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class Workflow:
    """
    Represents a multi-step workflow.

    Example:
        # Create a workflow
        workflow = Workflow(
            name="onboard_customer",
            description="Onboard a new customer",
        )

        # Add steps
        workflow.add_step(ToolStep(
            name="create_contact",
            tool_name="create_crm_contact",
            parameters={"email": "user@example.com"},
            output_key="contact",
        ))

        workflow.add_step(ToolStep(
            name="send_welcome",
            tool_name="send_email",
            parameter_mapping={
                "to": "contact.email",
            },
            parameters={"subject": "Welcome!"},
        ))

        # Execute
        result = await workflow.execute(variables={"user_name": "John"})
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        on_error: str = "fail",  # fail, continue
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.on_error = on_error
        self.steps: List[WorkflowStep] = []

    def add_step(self, step: WorkflowStep) -> "Workflow":
        """Add a step to the workflow."""
        self.steps.append(step)
        return self

    def add_tool_step(
        self,
        name: str,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        parameter_mapping: Optional[Dict[str, str]] = None,
        output_key: Optional[str] = None,
        **kwargs,
    ) -> "Workflow":
        """Add a tool step."""
        step = ToolStep(
            name=name,
            tool_name=tool_name,
            parameters=parameters,
            parameter_mapping=parameter_mapping,
            output_key=output_key,
            **kwargs,
        )
        return self.add_step(step)

    def add_function_step(
        self,
        name: str,
        func: Callable[[WorkflowContext], Any],
        output_key: Optional[str] = None,
        **kwargs,
    ) -> "Workflow":
        """Add a function step."""
        step = FunctionStep(
            name=name,
            func=func,
            output_key=output_key,
            **kwargs,
        )
        return self.add_step(step)

    def add_parallel_steps(
        self,
        name: str,
        steps: List[WorkflowStep],
        **kwargs,
    ) -> "Workflow":
        """Add parallel steps."""
        step = ParallelStep(name=name, steps=steps, **kwargs)
        return self.add_step(step)

    def add_branch(
        self,
        name: str,
        branches: Dict[str, WorkflowStep],
        selector: Callable[[WorkflowContext], str],
        **kwargs,
    ) -> "Workflow":
        """Add a branching step."""
        step = BranchStep(name=name, branches=branches, selector=selector, **kwargs)
        return self.add_step(step)

    async def execute(
        self,
        variables: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """
        Execute the workflow.

        Args:
            variables: Initial variables
            metadata: Execution metadata

        Returns:
            WorkflowResult with execution outcome
        """
        workflow_id = f"{self.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        context = WorkflowContext(
            workflow_id=workflow_id,
            variables=variables or {},
            metadata=metadata or {},
        )

        started_at = datetime.now()
        step_results = []
        status = WorkflowStatus.RUNNING
        error = ""

        logger.info(f"Starting workflow: {self.name} ({workflow_id})")

        try:
            for step in self.steps:
                # Check condition
                if not step.should_execute(context):
                    result = StepResult(
                        step_id=step.id,
                        step_name=step.name,
                        status=StepStatus.SKIPPED,
                    )
                    step_results.append(result)
                    continue

                logger.info(f"Executing step: {step.name}")

                # Execute step
                result = await step.execute(context)
                step_results.append(result)

                # Handle errors
                if result.status == StepStatus.FAILED:
                    if self.on_error == "fail":
                        status = WorkflowStatus.FAILED
                        error = f"Step '{step.name}' failed: {result.error}"
                        break
                    # continue mode - keep going

            if status == WorkflowStatus.RUNNING:
                status = WorkflowStatus.SUCCESS

        except Exception as e:
            status = WorkflowStatus.FAILED
            error = str(e)
            logger.error(f"Workflow failed: {e}")

        finished_at = datetime.now()

        result = WorkflowResult(
            workflow_id=workflow_id,
            workflow_name=self.name,
            status=status,
            steps=step_results,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=(finished_at - started_at).total_seconds() * 1000,
            error=error,
            output=context.variables,
        )

        logger.info(
            f"Workflow completed: {self.name} - {status.value} " f"({result.duration_ms:.1f}ms)"
        )

        return result


class WorkflowRegistry:
    """Registry for workflow definitions."""

    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}

    def register(self, workflow: Workflow) -> None:
        """Register a workflow."""
        self._workflows[workflow.name] = workflow
        logger.info(f"Registered workflow: {workflow.name}")

    def get(self, name: str) -> Optional[Workflow]:
        """Get a workflow by name."""
        return self._workflows.get(name)

    def list(self) -> List[Dict[str, str]]:
        """List all workflows."""
        return [{"name": w.name, "description": w.description} for w in self._workflows.values()]

    async def execute(
        self,
        name: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """Execute a workflow by name."""
        workflow = self.get(name)
        if not workflow:
            return WorkflowResult(
                workflow_id="",
                workflow_name=name,
                status=WorkflowStatus.FAILED,
                steps=[],
                error=f"Workflow '{name}' not found",
            )

        return await workflow.execute(variables)


# Global workflow registry
_workflow_registry: Optional[WorkflowRegistry] = None


def get_workflow_registry() -> WorkflowRegistry:
    """Get the global workflow registry."""
    global _workflow_registry
    if _workflow_registry is None:
        _workflow_registry = WorkflowRegistry()
    return _workflow_registry
