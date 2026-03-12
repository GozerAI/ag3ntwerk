"""
Workflow Factory.

Provides the factory for creating workflow instances from definitions,
and the DynamicWorkflow class that replaces boilerplate workflow classes.
"""

from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

from ag3ntwerk.orchestration.base import Workflow, WorkflowStep
from ag3ntwerk.orchestration.factory.definitions import WorkflowDefinition, StepDefinition
from ag3ntwerk.orchestration.factory.context_builders import generate_context_builder

if TYPE_CHECKING:
    from ag3ntwerk.orchestration.registry import AgentRegistry


class DynamicWorkflow(Workflow):
    """
    Dynamic workflow created from a WorkflowDefinition.

    This single class replaces all boilerplate workflow classes.
    It implements the Workflow interface by delegating to a definition.
    """

    def __init__(
        self,
        registry: "AgentRegistry",
        definition: WorkflowDefinition,
    ):
        """
        Initialize dynamic workflow.

        Args:
            registry: Agent registry for workflow execution
            definition: Workflow definition containing steps
        """
        super().__init__(registry)
        self._definition = definition

    @property
    def name(self) -> str:
        """Workflow name from definition."""
        return self._definition.name

    @property
    def description(self) -> str:
        """Workflow description from definition."""
        return self._definition.description

    def define_steps(self) -> List[WorkflowStep]:
        """
        Generate WorkflowStep instances from step definitions.

        Returns:
            List of WorkflowStep objects
        """
        steps = []
        for step_def in self._definition.steps:
            step = WorkflowStep(
                name=step_def.name,
                agent=step_def.agent,
                task_type=step_def.task_type,
                description=step_def.description,
                depends_on=list(step_def.depends_on),
                required=step_def.required,
                context_builder=generate_context_builder(step_def),
            )
            steps.append(step)
        return steps


class WorkflowFactory:
    """
    Singleton factory for creating workflow instances.

    Supports both definition-based and legacy class-based workflows.

    Usage:
        ```python
        factory = WorkflowFactory.get_instance()

        # Register definition-based workflow
        factory.register(MY_WORKFLOW_DEFINITION)

        # Register legacy class-based workflow
        factory.register_class(MyLegacyWorkflow)

        # Create workflow instance
        workflow = factory.create("my_workflow", registry)

        # List all workflows
        workflows = factory.list_workflows()
        ```
    """

    _instance: Optional["WorkflowFactory"] = None

    def __init__(self) -> None:
        """Initialize factory (use get_instance() instead)."""
        self._definitions: Dict[str, WorkflowDefinition] = {}
        self._classes: Dict[str, Type[Workflow]] = {}

    @classmethod
    def get_instance(cls) -> "WorkflowFactory":
        """Get or create the singleton factory instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    def register(self, definition: WorkflowDefinition) -> None:
        """
        Register a workflow definition.

        Args:
            definition: Workflow definition to register
        """
        self._definitions[definition.name] = definition

    def register_class(self, workflow_class: Type[Workflow], registry: "AgentRegistry") -> None:
        """
        Register a legacy class-based workflow.

        Args:
            workflow_class: Workflow class to register
            registry: Registry for temporary instantiation to get name
        """
        # Create temporary instance to get name
        temp = workflow_class(registry)
        self._classes[temp.name] = workflow_class

    def unregister(self, name: str) -> bool:
        """
        Unregister a workflow by name.

        Args:
            name: Workflow name to unregister

        Returns:
            True if found and removed, False otherwise
        """
        if name in self._definitions:
            del self._definitions[name]
            return True
        if name in self._classes:
            del self._classes[name]
            return True
        return False

    def create(self, name: str, registry: "AgentRegistry") -> Workflow:
        """
        Create a workflow instance by name.

        Args:
            name: Workflow name
            registry: Agent registry for workflow

        Returns:
            Workflow instance

        Raises:
            ValueError: If workflow not found
        """
        # Check definitions first (preferred)
        if name in self._definitions:
            return DynamicWorkflow(registry, self._definitions[name])

        # Fall back to legacy classes
        if name in self._classes:
            return self._classes[name](registry)

        raise ValueError(f"Unknown workflow: {name}")

    def has_workflow(self, name: str) -> bool:
        """Check if a workflow is registered."""
        return name in self._definitions or name in self._classes

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all registered workflows.

        Returns:
            List of workflow info dictionaries
        """
        result = []

        # Definition-based workflows
        for name, definition in self._definitions.items():
            result.append(
                {
                    "name": name,
                    "description": definition.description,
                    "category": definition.category,
                    "tags": list(definition.tags),
                    "step_count": len(definition.steps),
                    "source": "definition",
                }
            )

        # Legacy class-based workflows
        for name, cls in self._classes.items():
            result.append(
                {
                    "name": name,
                    "description": f"{name} workflow",  # Can't get description without registry
                    "category": "legacy",
                    "tags": [],
                    "step_count": 0,  # Can't get steps without registry
                    "source": "class",
                }
            )

        return result

    def get_definition(self, name: str) -> Optional[WorkflowDefinition]:
        """
        Get workflow definition by name.

        Args:
            name: Workflow name

        Returns:
            WorkflowDefinition or None if not found
        """
        return self._definitions.get(name)

    def get_workflows_by_category(self, category: str) -> List[str]:
        """
        Get workflow names by category.

        Args:
            category: Category to filter by

        Returns:
            List of workflow names
        """
        return [
            name
            for name, definition in self._definitions.items()
            if definition.category == category
        ]

    def get_workflows_by_tag(self, tag: str) -> List[str]:
        """
        Get workflow names that have a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of workflow names
        """
        return [name for name, definition in self._definitions.items() if tag in definition.tags]


# Module-level convenience functions


def get_workflow_factory() -> WorkflowFactory:
    """Get the singleton WorkflowFactory instance."""
    return WorkflowFactory.get_instance()


def create_workflow(name: str, registry: "AgentRegistry") -> Workflow:
    """
    Create a workflow by name using the global factory.

    Args:
        name: Workflow name
        registry: Agent registry

    Returns:
        Workflow instance
    """
    return get_workflow_factory().create(name, registry)
