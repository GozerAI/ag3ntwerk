"""
Base Tool Classes for ag3ntwerk.

Provides the foundation for all tools in the system.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type, Union
from enum import Enum
import json
import traceback

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Categories for organizing tools."""

    COMMUNICATION = "communication"
    DATA = "data"
    DEVOPS = "devops"
    RESEARCH = "research"
    BUSINESS = "business"
    DOCUMENTS = "documents"
    ANALYSIS = "analysis"
    AUTOMATION = "automation"
    GENERAL = "general"


class ParameterType(str, Enum):
    """Types of tool parameters."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    DATE = "date"
    DATETIME = "datetime"
    FILE = "file"
    ANY = "any"


@dataclass
class ToolParameter:
    """Describes a tool parameter."""

    name: str
    description: str
    param_type: ParameterType = ParameterType.STRING
    required: bool = True
    default: Any = None
    choices: Optional[List[Any]] = None
    example: Any = None

    def validate(self, value: Any) -> tuple:
        """
        Validate a parameter value.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None:
            if self.required and self.default is None:
                return False, f"Parameter '{self.name}' is required"
            return True, None

        if self.choices and value not in self.choices:
            return False, f"Parameter '{self.name}' must be one of {self.choices}"

        # Type validation
        type_validators = {
            ParameterType.STRING: lambda v: isinstance(v, str),
            ParameterType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
            ParameterType.FLOAT: lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            ParameterType.BOOLEAN: lambda v: isinstance(v, bool),
            ParameterType.LIST: lambda v: isinstance(v, list),
            ParameterType.DICT: lambda v: isinstance(v, dict),
            ParameterType.ANY: lambda v: True,
        }

        validator = type_validators.get(self.param_type)
        if validator and not validator(value):
            return False, f"Parameter '{self.name}' must be of type {self.param_type.value}"

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.param_type.value,
            "required": self.required,
            "default": self.default,
            "choices": self.choices,
            "example": self.example,
        }


@dataclass
class ToolMetadata:
    """Metadata describing a tool."""

    name: str
    description: str
    category: ToolCategory = ToolCategory.GENERAL
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    requires_auth: bool = False
    auth_type: str = ""  # api_key, oauth, basic, etc.
    rate_limited: bool = False
    rate_limit: int = 0  # requests per minute
    is_async: bool = True
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def matches_query(self, query: str) -> float:
        """
        Check how well this tool matches a search query.

        Returns:
            Score from 0 to 1, higher is better match
        """
        query_lower = query.lower()
        score = 0.0

        # Exact name match
        if query_lower == self.name.lower():
            score += 1.0

        # Name contains query
        if query_lower in self.name.lower():
            score += 0.5

        # Description contains query
        if query_lower in self.description.lower():
            score += 0.3

        # Tag match
        for tag in self.tags:
            if query_lower in tag.lower():
                score += 0.2

        # Category match
        if query_lower in self.category.value:
            score += 0.1

        return min(score, 1.0)


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_type": self.error_type,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def success_result(cls, data: Any, **metadata) -> "ToolResult":
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def error_result(cls, error: str, error_type: str = "Error") -> "ToolResult":
        """Create an error result."""
        return cls(success=False, error=error, error_type=error_type)


class BaseTool(ABC):
    """
    Base class for all ag3ntwerk tools.

    Tools must implement:
    - metadata property: Returns ToolMetadata
    - parameters property: Returns list of ToolParameter
    - _execute method: Performs the tool's action

    Example:
        class SendSlackMessageTool(BaseTool):
            @property
            def metadata(self) -> ToolMetadata:
                return ToolMetadata(
                    name="send_slack_message",
                    description="Send a message to a Slack channel",
                    category=ToolCategory.COMMUNICATION,
                    tags=["slack", "message", "chat"],
                )

            @property
            def parameters(self) -> List[ToolParameter]:
                return [
                    ToolParameter("channel", "Channel to send to", required=True),
                    ToolParameter("message", "Message content", required=True),
                ]

            async def _execute(self, **kwargs) -> ToolResult:
                channel = kwargs["channel"]
                message = kwargs["message"]
                # ... send message ...
                return ToolResult.success_result({"sent": True})
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the tool.

        Args:
            config: Tool configuration (API keys, settings, etc.)
        """
        self.config = config or {}
        self._initialized = False

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Return list of tool parameters."""
        pass

    @abstractmethod
    async def _execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool's action.

        Args:
            **kwargs: Tool parameters

        Returns:
            ToolResult with execution outcome
        """
        pass

    async def initialize(self) -> bool:
        """
        Initialize the tool (connect to services, etc.).

        Override this method to perform setup.

        Returns:
            True if initialization successful
        """
        self._initialized = True
        return True

    async def cleanup(self) -> None:
        """
        Cleanup resources.

        Override this method to perform cleanup.
        """
        self._initialized = False

    def validate_parameters(self, **kwargs) -> tuple:
        """
        Validate all parameters.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check all provided parameters
        param_names = {p.name for p in self.parameters}
        for key in kwargs:
            if key not in param_names:
                errors.append(f"Unknown parameter: {key}")

        # Validate each parameter
        for param in self.parameters:
            value = kwargs.get(param.name, param.default)
            is_valid, error = param.validate(value)
            if not is_valid:
                errors.append(error)

        return len(errors) == 0, errors

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with validation and error handling.

        Args:
            **kwargs: Tool parameters

        Returns:
            ToolResult with execution outcome
        """
        start_time = datetime.now()

        try:
            # Validate parameters
            is_valid, errors = self.validate_parameters(**kwargs)
            if not is_valid:
                return ToolResult(
                    success=False,
                    error="; ".join(errors),
                    error_type="ValidationError",
                )

            # Apply defaults
            for param in self.parameters:
                if param.name not in kwargs and param.default is not None:
                    kwargs[param.name] = param.default

            # Initialize if needed
            if not self._initialized:
                await self.initialize()

            # Execute
            result = await self._execute(**kwargs)

            # Add execution time
            result.execution_time = (datetime.now() - start_time).total_seconds()

            return result

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            logger.debug(traceback.format_exc())

            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                execution_time=(datetime.now() - start_time).total_seconds(),
            )

    def __call__(self, **kwargs) -> ToolResult:
        """Allow calling tool as a function (sync wrapper)."""
        return asyncio.run(self.execute(**kwargs))

    def get_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for the tool.

        Returns:
            Dict representing the tool's schema
        """
        return {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "category": self.metadata.category.value,
            "version": self.metadata.version,
            "parameters": [p.to_dict() for p in self.parameters],
            "tags": self.metadata.tags,
            "requires_auth": self.metadata.requires_auth,
            "examples": self.metadata.examples,
        }

    def get_help(self) -> str:
        """Get human-readable help text."""
        lines = [
            f"# {self.metadata.name}",
            "",
            self.metadata.description,
            "",
            f"Category: {self.metadata.category.value}",
            f"Version: {self.metadata.version}",
            "",
            "## Parameters",
            "",
        ]

        for param in self.parameters:
            required = "(required)" if param.required else "(optional)"
            default = f" [default: {param.default}]" if param.default is not None else ""
            lines.append(f"- **{param.name}** {required}: {param.description}{default}")
            if param.example is not None:
                lines.append(f"  Example: {param.example}")

        if self.metadata.examples:
            lines.extend(
                [
                    "",
                    "## Examples",
                    "",
                ]
            )
            for i, example in enumerate(self.metadata.examples, 1):
                lines.append(f"### Example {i}")
                lines.append(f"```")
                lines.append(json.dumps(example, indent=2))
                lines.append(f"```")

        return "\n".join(lines)


class CompositeTool(BaseTool):
    """
    A tool composed of multiple sub-tools.

    Useful for creating tools that chain multiple operations.
    """

    def __init__(
        self,
        name: str,
        description: str,
        tools: List[BaseTool],
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize composite tool.

        Args:
            name: Tool name
            description: Tool description
            tools: List of sub-tools to compose
            config: Configuration
        """
        super().__init__(config)
        self._name = name
        self._description = description
        self._tools = tools

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self._name,
            description=self._description,
            category=ToolCategory.AUTOMATION,
            tags=["composite", "workflow"],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        # Combine parameters from all tools
        params = []
        seen = set()
        for tool in self._tools:
            for param in tool.parameters:
                if param.name not in seen:
                    params.append(param)
                    seen.add(param.name)
        return params

    async def _execute(self, **kwargs) -> ToolResult:
        """Execute all sub-tools in sequence."""
        results = []
        context = dict(kwargs)

        for tool in self._tools:
            # Filter kwargs to only include this tool's parameters
            tool_params = {p.name for p in tool.parameters}
            tool_kwargs = {k: v for k, v in context.items() if k in tool_params}

            result = await tool.execute(**tool_kwargs)
            results.append(
                {
                    "tool": tool.metadata.name,
                    "result": result.to_dict(),
                }
            )

            if not result.success:
                return ToolResult(
                    success=False,
                    data=results,
                    error=f"Tool '{tool.metadata.name}' failed: {result.error}",
                    error_type="CompositeToolError",
                )

            # Add result data to context for next tool
            if isinstance(result.data, dict):
                context.update(result.data)

        return ToolResult.success_result(results)
