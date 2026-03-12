"""
Orchestration Base Classes.

Provides the foundation for workflow orchestration across agents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from ag3ntwerk.orchestration.registry import AgentRegistry


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class WorkflowStatus(Enum):
    """Status of a workflow execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(Enum):
    """Status of an individual workflow step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """
    A single step in a workflow.

    Attributes:
        name: Human-readable step name
        agent: Agent code to handle this step (e.g., "Blueprint", "Keystone")
        task_type: Task type to execute
        description: Description of what this step does
        context_builder: Optional function to build task context from workflow context
        required: Whether this step must succeed for workflow to continue
        depends_on: List of step names this step depends on
    """

    name: str
    agent: str
    task_type: str
    description: str
    context_builder: Optional[Callable[["WorkflowContext"], Dict[str, Any]]] = None
    required: bool = True
    depends_on: List[str] = field(default_factory=list)

    # Runtime state
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary."""
        return {
            "name": self.name,
            "agent": self.agent,
            "task_type": self.task_type,
            "description": self.description,
            "required": self.required,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class WorkflowContext:
    """
    Context passed through a workflow.

    Accumulates data from each step and provides it to subsequent steps.
    """

    workflow_id: str
    workflow_name: str
    initial_params: Dict[str, Any]
    step_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=_utcnow)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from initial params or step results."""
        if key in self.step_results:
            return self.step_results[key]
        return self.initial_params.get(key, default)

    def set_step_result(self, step_name: str, result: Any) -> None:
        """Store result from a completed step."""
        self.step_results[step_name] = result

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "initial_params": self.initial_params,
            "step_results": self.step_results,
            "metadata": self.metadata,
            "started_at": self.started_at.isoformat(),
        }


@dataclass
class WorkflowResult:
    """
    Result of a workflow execution.

    Attributes:
        workflow_id: Unique identifier for this execution
        workflow_name: Name of the workflow
        status: Final status of the workflow
        steps: List of step results
        output: Combined output from all steps
        error: Error message if workflow failed
        started_at: When workflow started
        completed_at: When workflow completed
        duration_seconds: Total execution time
    """

    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    steps: List[Dict[str, Any]]
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def success(self) -> bool:
        """Whether workflow completed successfully."""
        return self.status == WorkflowStatus.COMPLETED

    @property
    def duration_seconds(self) -> Optional[float]:
        """Total execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "success": self.success,
            "steps": self.steps,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


class Workflow(ABC):
    """
    Base class for multi-agent workflows.

    Workflows define a series of steps that coordinate multiple agents
    to accomplish complex cross-functional tasks.

    Subclasses must implement:
    - name: Property returning workflow name
    - define_steps: Method returning list of workflow steps

    Example:
        ```python
        class MyWorkflow(Workflow):
            @property
            def name(self) -> str:
                return "my_workflow"

            def define_steps(self) -> List[WorkflowStep]:
                return [
                    WorkflowStep(
                        name="analyze",
                        agent="Forge",
                        task_type="technical_analysis",
                        description="Analyze technical requirements",
                    ),
                    WorkflowStep(
                        name="budget",
                        agent="Keystone",
                        task_type="budget_planning",
                        description="Plan budget",
                        depends_on=["analyze"],
                    ),
                ]
        ```
    """

    def __init__(self, registry: "AgentRegistry"):
        """
        Initialize workflow with agent registry.

        Args:
            registry: Registry containing all agents
        """
        self.registry = registry
        self._steps: List[WorkflowStep] = []
        self._context: Optional[WorkflowContext] = None
        self._status = WorkflowStatus.PENDING

    @property
    @abstractmethod
    def name(self) -> str:
        """Workflow name identifier."""
        pass

    @property
    def description(self) -> str:
        """Human-readable workflow description."""
        return f"{self.name} workflow"

    @abstractmethod
    def define_steps(self) -> List[WorkflowStep]:
        """
        Define the steps in this workflow.

        Returns:
            List of WorkflowStep objects defining the workflow
        """
        pass

    async def execute(self, **params: Any) -> WorkflowResult:
        """
        Execute the workflow with given parameters.

        Args:
            **params: Parameters to pass to workflow steps

        Returns:
            WorkflowResult containing execution results
        """
        workflow_id = str(uuid4())
        started_at = _utcnow()

        # Initialize context
        self._context = WorkflowContext(
            workflow_id=workflow_id,
            workflow_name=self.name,
            initial_params=params,
            started_at=started_at,
        )

        # Get steps
        self._steps = self.define_steps()
        self._status = WorkflowStatus.IN_PROGRESS

        completed_steps: List[str] = []
        error_message: Optional[str] = None

        try:
            # Execute steps in dependency order
            for step in self._get_execution_order():
                # Check dependencies
                if not self._dependencies_met(step, completed_steps):
                    step.status = StepStatus.SKIPPED
                    step.error = "Dependencies not met"
                    continue

                # Execute step
                step.status = StepStatus.IN_PROGRESS
                step.started_at = _utcnow()

                try:
                    result = await self._execute_step(step)
                    step.status = StepStatus.COMPLETED
                    step.result = result
                    step.completed_at = _utcnow()

                    # Store result in context
                    self._context.set_step_result(step.name, result)
                    completed_steps.append(step.name)

                except Exception as e:
                    step.status = StepStatus.FAILED
                    step.error = str(e)
                    step.completed_at = _utcnow()

                    if step.required:
                        error_message = f"Required step '{step.name}' failed: {e}"
                        self._status = WorkflowStatus.FAILED
                        break

            # Determine final status
            if self._status != WorkflowStatus.FAILED:
                self._status = WorkflowStatus.COMPLETED

        except Exception as e:
            self._status = WorkflowStatus.FAILED
            error_message = f"Workflow execution failed: {e}"

        completed_at = _utcnow()

        # Build output from step results
        output = self._build_output()

        return WorkflowResult(
            workflow_id=workflow_id,
            workflow_name=self.name,
            status=self._status,
            steps=[step.to_dict() for step in self._steps],
            output=output,
            error=error_message,
            started_at=started_at,
            completed_at=completed_at,
        )

    async def _execute_step(self, step: WorkflowStep) -> Any:
        """
        Execute a single workflow step.

        Args:
            step: Step to execute

        Returns:
            Result from step execution

        Raises:
            ValueError: If agent not found or context invalid
            Exception: If step execution fails
        """
        # Validate context exists
        if not self._context:
            raise ValueError("Workflow context not initialized")

        # Get agent with validation
        if not step.agent:
            raise ValueError(f"Step '{step.name}' has no agent assigned")

        try:
            agent = self.registry.get(step.agent)
        except Exception as e:
            raise ValueError(f"Failed to get agent '{step.agent}': {e}")

        if not agent:
            raise ValueError(f"Agent not found: {step.agent}")

        # Build task context safely
        task_context: Dict[str, Any] = {}
        if step.context_builder:
            try:
                task_context = step.context_builder(self._context)
            except Exception as e:
                raise ValueError(f"Context builder failed for step '{step.name}': {e}")
        else:
            task_context = self._context.initial_params.copy()

        # Ensure task_context is a dict
        if not isinstance(task_context, dict):
            task_context = {}

        # Add workflow metadata to context
        task_context["_workflow_id"] = self._context.workflow_id
        task_context["_workflow_name"] = self.name
        task_context["_step_name"] = step.name

        # Import Task here to avoid circular imports
        from ag3ntwerk.core.base import Task

        # Create and execute task
        task = Task(
            description=step.description,
            task_type=step.task_type,
            context=task_context,
        )

        try:
            result = await agent.execute(task)
        except Exception as e:
            raise Exception(f"Agent execution failed for step '{step.name}': {e}")

        if not result.success:
            raise Exception(result.error or "Step execution failed")

        return result.output

    def _get_execution_order(self) -> List[WorkflowStep]:
        """
        Get steps in dependency-respecting execution order.

        Uses topological sort to order steps.
        """
        # Build dependency graph
        remaining = {step.name: step for step in self._steps}
        ordered: List[WorkflowStep] = []

        while remaining:
            # Find steps with no unmet dependencies
            ready = [
                name
                for name, step in remaining.items()
                if all(dep not in remaining for dep in step.depends_on)
            ]

            if not ready:
                # Circular dependency detected
                raise ValueError(f"Circular dependency detected among: {list(remaining.keys())}")

            # Add ready steps to order
            for name in ready:
                ordered.append(remaining.pop(name))

        return ordered

    def _dependencies_met(self, step: WorkflowStep, completed: List[str]) -> bool:
        """Check if all dependencies for a step are met."""
        return all(dep in completed for dep in step.depends_on)

    def _build_output(self) -> Dict[str, Any]:
        """Build combined output from all step results."""
        if not self._context:
            return {}

        return {
            "workflow": self.name,
            "params": self._context.initial_params,
            "results": self._context.step_results,
        }


class Orchestrator:
    """
    Central orchestrator for managing workflow execution.

    The Orchestrator provides a high-level interface for executing
    workflows and coordinating between agents.

    Example:
        ```python
        orchestrator = Orchestrator(registry)

        # Register workflows
        orchestrator.register_workflow(ProductLaunchWorkflow)
        orchestrator.register_workflow(IncidentResponseWorkflow)

        # Execute workflow
        result = await orchestrator.execute(
            "product_launch",
            product_name="GozerAI",
            features=["chat", "code"],
        )
        ```
    """

    def __init__(self, registry: "AgentRegistry"):
        """
        Initialize orchestrator.

        Args:
            registry: Agent registry for workflow access
        """
        self.registry = registry
        self._workflows: Dict[str, type] = {}
        self._execution_history: List[WorkflowResult] = []

    def register_workflow(self, workflow_class: type) -> None:
        """
        Register a workflow class.

        Args:
            workflow_class: Workflow class to register
        """
        # Create temporary instance to get name
        temp = workflow_class(self.registry)
        self._workflows[temp.name] = workflow_class

    def list_workflows(self) -> List[Dict[str, str]]:
        """List all registered workflows."""
        result = []
        for name, cls in self._workflows.items():
            temp = cls(self.registry)
            result.append(
                {
                    "name": name,
                    "description": temp.description,
                    "class": cls.__name__,
                }
            )
        return result

    async def execute(self, workflow_name: str, **params: Any) -> WorkflowResult:
        """
        Execute a registered workflow.

        Args:
            workflow_name: Name of workflow to execute
            **params: Parameters to pass to workflow

        Returns:
            WorkflowResult from execution
        """
        if workflow_name not in self._workflows:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        workflow_class = self._workflows[workflow_name]
        workflow = workflow_class(self.registry)

        result = await workflow.execute(**params)
        self._execution_history.append(result)

        return result

    def get_history(self, limit: int = 10) -> List[WorkflowResult]:
        """Get recent workflow execution history."""
        return self._execution_history[-limit:]
