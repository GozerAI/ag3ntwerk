"""
Workflow Factory - Declarative workflow creation infrastructure.

This module provides a factory pattern for creating workflows from
declarative definitions, eliminating boilerplate class definitions.

Usage:
    ```python
    from ag3ntwerk.orchestration.factory import (
        WorkflowFactory,
        WorkflowDefinition,
        StepDefinition,
        param,
        step_result,
        aggregate,
    )

    # Define a workflow declaratively
    MY_WORKFLOW = WorkflowDefinition(
        name="my_workflow",
        description="My workflow description",
        steps=[
            StepDefinition(
                name="step1",
                agent="Forge",
                task_type="analysis",
                description="Analyze requirements",
                context_mapping={"input": "input_data"},
            ),
            StepDefinition(
                name="step2",
                agent="Keystone",
                task_type="budget",
                description="Plan budget",
                depends_on=["step1"],
                context_mapping={
                    "analysis": step_result("step1"),
                    "budget_limit": param("budget_limit", 100000),
                },
            ),
        ],
    )

    # Create workflow instance
    factory = WorkflowFactory.get_instance()
    factory.register(MY_WORKFLOW)
    workflow = factory.create("my_workflow", registry)
    ```
"""

from ag3ntwerk.orchestration.factory.definitions import (
    ContextRef,
    StepRef,
    AggregateRef,
    StepDefinition,
    WorkflowDefinition,
)
from ag3ntwerk.orchestration.factory.context_builders import (
    generate_context_builder,
    param,
    step_result,
    aggregate,
)
from ag3ntwerk.orchestration.factory.factory import (
    DynamicWorkflow,
    WorkflowFactory,
    get_workflow_factory,
    create_workflow,
)

__all__ = [
    # Definitions
    "ContextRef",
    "StepRef",
    "AggregateRef",
    "StepDefinition",
    "WorkflowDefinition",
    # Context builders
    "generate_context_builder",
    "param",
    "step_result",
    "aggregate",
    # Factory
    "DynamicWorkflow",
    "WorkflowFactory",
    "get_workflow_factory",
    "create_workflow",
]
