"""
Workflow Definitions - Declarative workflow specifications.

This module contains all workflow definitions organized by category.
Definitions are automatically registered with the WorkflowFactory.

Categories:
- cross_functional: Multi-agent workflows that coordinate across functions
- single_agent: Workflows that primarily use one agent
- specialist: Single-step specialist task workflows
- aggregation: Multi-step workflows for a single agent
- pipelines: Complex multi-stage pipeline workflows
"""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ag3ntwerk.orchestration.factory import WorkflowDefinition


def get_all_definitions() -> List["WorkflowDefinition"]:
    """Get all workflow definitions."""
    # Import modules lazily to avoid circular imports
    from ag3ntwerk.orchestration.definitions import (
        cross_functional,
        single_agent,
        specialist,
        aggregation,
        pipelines,
    )

    return [
        *cross_functional.ALL_DEFINITIONS,
        *single_agent.ALL_DEFINITIONS,
        *specialist.ALL_DEFINITIONS,
        *aggregation.ALL_DEFINITIONS,
        *pipelines.ALL_DEFINITIONS,
    ]


def register_all_definitions() -> None:
    """Register all workflow definitions with the factory."""
    from ag3ntwerk.orchestration.factory import WorkflowFactory

    factory = WorkflowFactory.get_instance()
    for definition in get_all_definitions():
        factory.register(definition)


__all__ = [
    "get_all_definitions",
    "register_all_definitions",
]
