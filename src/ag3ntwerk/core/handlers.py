"""
Base handler infrastructure for ag3ntwerk agents.

This module provides reusable handler patterns to reduce code duplication
across agent implementations. Handlers define how specific task types
are processed using configurable prompts and context extraction.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
import logging

from ag3ntwerk.core.base import Task, TaskResult


logger = logging.getLogger(__name__)


@dataclass
class HandlerConfig:
    """
    Configuration for a task handler.

    Defines how a specific task type should be processed, including
    the prompt template, context extraction, and output formatting.

    Attributes:
        task_type: The task type this handler processes
        prompt_template: Template string for the LLM prompt (uses .format())
        context_fields: Dict mapping context keys to (default_value, prompt_label) tuples
        output_type: Key name for the primary output field
        output_fields: Additional static fields to include in output
    """

    task_type: str
    prompt_template: str
    context_fields: Dict[str, tuple] = field(default_factory=dict)
    output_type: str = "analysis"
    output_fields: Dict[str, str] = field(default_factory=dict)


class HandlerRegistry:
    """
    Registry for task handlers.

    Provides a centralized way to register and retrieve handlers
    for different task types.
    """

    def __init__(self):
        self._handlers: Dict[str, HandlerConfig] = {}
        self._custom_handlers: Dict[str, Callable] = {}

    def register(self, config: HandlerConfig) -> None:
        """Register a handler configuration."""
        self._handlers[config.task_type] = config

    def register_custom(self, task_type: str, handler: Callable) -> None:
        """Register a custom handler function."""
        self._custom_handlers[task_type] = handler

    def get(self, task_type: str) -> Optional[HandlerConfig]:
        """Get handler config for a task type."""
        return self._handlers.get(task_type)

    def get_custom(self, task_type: str) -> Optional[Callable]:
        """Get custom handler for a task type."""
        return self._custom_handlers.get(task_type)

    def has_handler(self, task_type: str) -> bool:
        """Check if a handler exists for the task type."""
        return task_type in self._handlers or task_type in self._custom_handlers

    @property
    def task_types(self) -> List[str]:
        """Get all registered task types."""
        return list(set(self._handlers.keys()) | set(self._custom_handlers.keys()))


class BaseTaskHandler:
    """
    Base class for handling tasks with configurable prompts.

    Provides a standard pattern for:
    1. Extracting context from tasks
    2. Building prompts from templates
    3. Calling LLM for reasoning
    4. Formatting responses as TaskResults

    Example:
        ```python
        class MyAgentHandler(BaseTaskHandler):
            def __init__(self, agent):
                super().__init__(agent.code, agent.name, agent.domain)
                self.agent = agent
                self._register_handlers()

            def _register_handlers(self):
                self.registry.register(HandlerConfig(
                    task_type="cost_analysis",
                    prompt_template='''Perform cost analysis.

                    Period: {period}
                    Category: {category}

                    Provide analysis including:
                    1. Cost breakdown
                    2. Trends
                    3. Recommendations''',
                    context_fields={
                        "period": ("current", "Period"),
                        "category": ("all", "Category"),
                    },
                    output_type="analysis",
                    output_fields={"analysis_type": "cost"},
                ))
        ```
    """

    def __init__(
        self,
        agent_code: str,
        agent_name: str,
        agent_domain: str,
    ):
        self.agent_code = agent_code
        self.agent_name = agent_name
        self.agent_domain = agent_domain
        self.registry = HandlerRegistry()

    def extract_context(
        self,
        task: Task,
        field_configs: Dict[str, tuple],
    ) -> Dict[str, Any]:
        """
        Extract context values from a task.

        Args:
            task: The task to extract context from
            field_configs: Dict mapping field names to (default, label) tuples

        Returns:
            Dict of field names to extracted values
        """
        result = {}
        for field_name, (default, label) in field_configs.items():
            value = task.context.get(field_name, default)
            result[field_name] = value
            result[f"{field_name}_display"] = value if value else f"Define {label.lower()}"
        return result

    def build_prompt(
        self,
        template: str,
        task: Task,
        context_values: Dict[str, Any],
        role_prefix: Optional[str] = None,
    ) -> str:
        """
        Build a prompt from a template.

        Args:
            template: The prompt template with {field} placeholders
            task: The task being handled
            context_values: Extracted context values
            role_prefix: Optional role prefix (defaults to agent role)

        Returns:
            The formatted prompt string
        """
        if role_prefix is None:
            role_prefix = f"As the {self.agent_name}"

        # Add standard fields
        context_values["role_prefix"] = role_prefix
        context_values["description"] = task.description
        context_values["context"] = task.context

        try:
            return template.format(**context_values)
        except KeyError as e:
            logger.warning(f"Missing template field {e} for task {task.task_type}")
            # Fall back to partial formatting
            return template.format_map(SafeDict(context_values))

    async def handle(
        self,
        task: Task,
        reason_func: Callable,
        config: Optional[HandlerConfig] = None,
    ) -> TaskResult:
        """
        Handle a task using the registered configuration.

        Args:
            task: The task to handle
            reason_func: Async function to call LLM (usually agent.reason)
            config: Optional explicit config (otherwise looks up by task_type)

        Returns:
            TaskResult with the handling outcome
        """
        if config is None:
            config = self.registry.get(task.task_type)

        if config is None:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"No handler configured for task type: {task.task_type}",
            )

        # Extract context
        context_values = self.extract_context(task, config.context_fields)

        # Build prompt
        prompt = self.build_prompt(config.prompt_template, task, context_values)

        try:
            response = await reason_func(prompt, task.context)
        except Exception as e:
            logger.exception(f"Handler failed for task {task.id}: {e}")
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"{task.task_type} failed: {e}",
            )

        # Build output
        output = {config.output_type: response}
        output.update(config.output_fields)

        # Add context values that were extracted
        for field_name in config.context_fields:
            if context_values.get(field_name):
                output[field_name] = context_values[field_name]

        return TaskResult(
            task_id=task.id,
            success=True,
            output=output,
        )

    async def handle_with_llm_fallback(
        self,
        task: Task,
        reason_func: Callable,
    ) -> TaskResult:
        """
        Handle a task using generic LLM fallback.

        Used when no specific handler is registered for the task type.

        Args:
            task: The task to handle
            reason_func: Async function to call LLM

        Returns:
            TaskResult with the handling outcome
        """
        prompt = f"""As the {self.agent_name} specializing in {self.agent_domain},
handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough response focused on your domain expertise."""

        try:
            response = await reason_func(prompt, task.context)
        except Exception as e:
            logger.exception(f"LLM fallback failed for task {task.id}: {e}")
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"LLM handling failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )


class SafeDict(dict):
    """Dict that returns the key wrapped in braces for missing keys."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def create_standard_handler(
    task_type: str,
    prompt_intro: str,
    analysis_items: List[str],
    context_fields: Dict[str, tuple],
    output_type: str = "analysis",
    output_fields: Optional[Dict[str, str]] = None,
) -> HandlerConfig:
    """
    Factory function to create standard handler configurations.

    This provides a consistent format for handler prompts across agents.

    Args:
        task_type: The task type identifier
        prompt_intro: Introduction text for the prompt
        analysis_items: List of numbered items to include in response
        context_fields: Dict of (default, label) for context extraction
        output_type: Primary output field name
        output_fields: Additional static output fields

    Returns:
        HandlerConfig ready for registration

    Example:
        ```python
        config = create_standard_handler(
            task_type="cost_analysis",
            prompt_intro="perform cost analysis",
            analysis_items=[
                "Cost breakdown by category",
                "Trends and patterns",
                "Recommendations for optimization",
            ],
            context_fields={
                "period": ("current", "Period"),
                "category": ("all", "Category"),
            },
            output_type="analysis",
            output_fields={"analysis_type": "cost"},
        )
        ```
    """
    # Build the numbered list
    numbered_items = "\n".join(f"{i+1}. {item}" for i, item in enumerate(analysis_items))

    # Build context display section
    context_lines = []
    for field_name, (default, label) in context_fields.items():
        context_lines.append(f"{label}: {{{field_name}_display}}")
    context_section = "\n".join(context_lines)

    template = f"""{{role_prefix}}, {prompt_intro}.

{context_section}
Description: {{description}}
Context: {{context}}

Provide a thorough response including:
{numbered_items}"""

    return HandlerConfig(
        task_type=task_type,
        prompt_template=template,
        context_fields=context_fields,
        output_type=output_type,
        output_fields=output_fields or {},
    )
