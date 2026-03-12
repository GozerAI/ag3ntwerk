"""
Context Builder Generator.

Automatically generates context builder functions from declarative mappings,
eliminating the need for hand-written lambda functions.
"""

from typing import Any, Callable, Dict, TYPE_CHECKING

from ag3ntwerk.orchestration.factory.definitions import (
    ContextRef,
    StepRef,
    AggregateRef,
    StepDefinition,
)

if TYPE_CHECKING:
    from ag3ntwerk.orchestration.base import WorkflowContext


def generate_context_builder(
    step_def: StepDefinition,
) -> Callable[["WorkflowContext"], Dict[str, Any]]:
    """
    Generate a context builder function from a step definition.

    If the step has a custom_context_builder, it is returned directly.
    Otherwise, a function is generated from the context_mapping.

    Args:
        step_def: Step definition with context_mapping

    Returns:
        Callable that builds context from WorkflowContext
    """
    # Use custom builder if provided
    if step_def.custom_context_builder is not None:
        return step_def.custom_context_builder

    # Empty mapping means use initial params
    if not step_def.context_mapping:
        return lambda ctx: ctx.initial_params.copy()

    # Capture mapping in closure
    mapping = step_def.context_mapping

    def context_builder(ctx: "WorkflowContext") -> Dict[str, Any]:
        """Generated context builder from declarative mapping."""
        result: Dict[str, Any] = {}

        for key, source in mapping.items():
            if isinstance(source, str):
                # Direct parameter lookup
                result[key] = ctx.get(source)
            elif isinstance(source, ContextRef):
                # Parameter with default
                result[key] = ctx.get(source.key, source.default)
            elif isinstance(source, StepRef):
                # Previous step result
                result[key] = ctx.step_results.get(source.step_name)
            elif isinstance(source, AggregateRef):
                # Aggregate multiple step results
                result[key] = {
                    out_key: ctx.step_results.get(step_name)
                    for out_key, step_name in source.steps.items()
                }
            else:
                # Literal value (including None, numbers, etc.)
                result[key] = source

        return result

    return context_builder


# Convenience constructors for context mappings


def param(key: str, default: Any = None) -> ContextRef:
    """
    Reference a workflow parameter with optional default.

    Example:
        context_mapping={
            "budget_limit": param("max_budget", 100000),
            "product_name": param("product_name"),  # No default
        }
    """
    return ContextRef(key=key, default=default)


def step_result(step_name: str, field: Optional[str] = None) -> StepRef:
    """
    Reference a previous step's result or a specific field from it.

    Examples:
        # Reference entire step result
        context_mapping={
            "analysis_result": step_result("analyze_step"),
        }

        # Reference specific field from step result
        context_mapping={
            "niche_candidates": step_result("market_intelligence", "niche_candidates"),
        }
    """
    return StepRef(step_name=step_name, field=field)


def aggregate(**mapping: str) -> AggregateRef:
    """
    Aggregate multiple step results into a dictionary.

    Example:
        context_mapping={
            "all_reviews": aggregate(
                technical="tech_review",
                financial="fin_review",
                legal="legal_review",
            ),
        }
    """
    return AggregateRef(steps=mapping)


def passthrough(*keys: str) -> Dict[str, str]:
    """
    Create a mapping that passes through specified keys unchanged.

    Example:
        context_mapping={
            **passthrough("product_name", "target_date", "budget"),
        }

    Equivalent to:
        context_mapping={
            "product_name": "product_name",
            "target_date": "target_date",
            "budget": "budget",
        }
    """
    return {key: key for key in keys}


def with_step_results(
    base_params: Dict[str, Any],
    **step_refs: str,
) -> Dict[str, Any]:
    """
    Combine base parameter mappings with step result references.

    Example:
        context_mapping=with_step_results(
            {"product_name": "product_name", "budget": "budget"},
            analysis="analyze_step",
            requirements="requirements_step",
        )

    Equivalent to:
        context_mapping={
            "product_name": "product_name",
            "budget": "budget",
            "analysis": step_result("analyze_step"),
            "requirements": step_result("requirements_step"),
        }
    """
    result = dict(base_params)
    for key, step_name in step_refs.items():
        result[key] = step_result(step_name)
    return result
