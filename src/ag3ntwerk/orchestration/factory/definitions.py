"""
Workflow Definition Dataclasses.

Provides immutable data structures for declarative workflow definitions.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ag3ntwerk.orchestration.base import WorkflowContext


@dataclass(frozen=True)
class ContextRef:
    """
    Reference to a workflow parameter with optional default.

    Used in context_mapping to indicate a value should come from
    the workflow's initial parameters.

    Example:
        context_mapping={
            "budget": ContextRef("budget_limit", default=100000),
        }
    """

    key: str
    default: Any = None


@dataclass(frozen=True)
class StepRef:
    """
    Reference to a previous step's result or a specific field from it.

    Used in context_mapping to indicate a value should come from
    a prior step's output.

    Examples:
        # Reference entire step result
        context_mapping={
            "analysis": StepRef("analyze_step"),
        }

        # Reference specific field from step result
        context_mapping={
            "niche_candidates": StepRef("market_intelligence", "niche_candidates"),
        }
    """

    step_name: str
    field: Optional[str] = None


@dataclass(frozen=True)
class AggregateRef:
    """
    Aggregate multiple step results into a dictionary.

    Used in context_mapping to combine outputs from multiple steps.

    Example:
        context_mapping={
            "all_results": AggregateRef({
                "analysis": "analyze_step",
                "budget": "budget_step",
                "risk": "risk_step",
            }),
        }
    """

    steps: Dict[str, str]  # output_key -> step_name

    def __hash__(self) -> int:
        """Make hashable for frozen dataclass."""
        return hash(tuple(sorted(self.steps.items())))


@dataclass(frozen=True)
class StepDefinition:
    """
    Declarative definition of a workflow step.

    Attributes:
        name: Step identifier (must be unique within workflow)
        agent: Agent code to handle this step (e.g., "Blueprint", "Keystone")
        task_type: Task type to execute
        description: Human-readable description of what this step does
        depends_on: List of step names this step depends on
        required: Whether this step must succeed for workflow to continue
        context_mapping: Declarative mapping of context keys to values
        custom_context_builder: Optional custom function for complex context building

    Context Mapping:
        The context_mapping dict supports several value types:
        - str: Direct parameter key lookup (e.g., "product_name" -> ctx.get("product_name"))
        - ContextRef: Parameter with default (e.g., ContextRef("limit", 100))
        - StepRef: Previous step result (e.g., StepRef("analyze"))
        - AggregateRef: Multiple step results (e.g., AggregateRef({"a": "step1", "b": "step2"}))
        - Any other value: Used as literal value
    """

    name: str
    agent: str
    task_type: str
    description: str
    depends_on: tuple = field(default_factory=tuple)  # Use tuple for frozen
    required: bool = True
    context_mapping: Dict[str, Any] = field(default_factory=dict)
    custom_context_builder: Optional[Callable[["WorkflowContext"], Dict[str, Any]]] = None

    def __hash__(self) -> int:
        """Make hashable for frozen dataclass."""
        # Exclude mutable fields from hash
        return hash(
            (
                self.name,
                self.agent,
                self.task_type,
                self.description,
                self.depends_on,
                self.required,
            )
        )


@dataclass(frozen=True)
class WorkflowDefinition:
    """
    Declarative definition of a complete workflow.

    Attributes:
        name: Workflow identifier (used for registration and lookup)
        description: Human-readable workflow description
        steps: Ordered list of step definitions
        category: Optional category for grouping (e.g., "cross_functional", "specialist")
        tags: Optional tags for filtering and discovery
    """

    name: str
    description: str
    steps: tuple  # Use tuple for frozen; accepts List in practice
    category: str = "general"
    tags: tuple = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Convert steps list to tuple if needed."""
        if isinstance(self.steps, list):
            object.__setattr__(self, "steps", tuple(self.steps))
        if isinstance(self.tags, list):
            object.__setattr__(self, "tags", tuple(self.tags))

    def __hash__(self) -> int:
        """Make hashable for frozen dataclass."""
        return hash((self.name, self.description, self.category))


def step(
    name: str,
    agent: str,
    task_type: str,
    description: str,
    depends_on: Optional[List[str]] = None,
    required: bool = True,
    context_mapping: Optional[Dict[str, Any]] = None,
    custom_context_builder: Optional[Callable[["WorkflowContext"], Dict[str, Any]]] = None,
) -> StepDefinition:
    """
    Convenience function to create a StepDefinition.

    Example:
        step(
            name="analyze",
            agent="Forge",
            task_type="technical_analysis",
            description="Analyze technical requirements",
            depends_on=["requirements"],
            context_mapping={"input": "requirements_doc"},
        )
    """
    return StepDefinition(
        name=name,
        agent=agent,
        task_type=task_type,
        description=description,
        depends_on=tuple(depends_on or []),
        required=required,
        context_mapping=context_mapping or {},
        custom_context_builder=custom_context_builder,
    )


def workflow(
    name: str,
    description: str,
    steps: List[StepDefinition],
    category: str = "general",
    tags: Optional[List[str]] = None,
) -> WorkflowDefinition:
    """
    Convenience function to create a WorkflowDefinition.

    Example:
        workflow(
            name="product_launch",
            description="End-to-end product launch coordination",
            category="cross_functional",
            steps=[
                step(...),
                step(...),
            ],
        )
    """
    return WorkflowDefinition(
        name=name,
        description=description,
        steps=tuple(steps),
        category=category,
        tags=tuple(tags or []),
    )
