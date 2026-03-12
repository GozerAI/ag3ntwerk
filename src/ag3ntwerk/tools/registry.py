"""
Tool Registry for ag3ntwerk.

Provides centralized tool discovery, registration, and management.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime

from ag3ntwerk.tools.base import BaseTool, ToolCategory, ToolMetadata, ToolResult

logger = logging.getLogger(__name__)

# Global registry instance
_registry: Optional["ToolRegistry"] = None


def get_registry() -> "ToolRegistry":
    """Get the global tool registry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


@dataclass
class RegisteredTool:
    """A tool registered in the registry."""

    tool: BaseTool
    registered_at: datetime = field(default_factory=datetime.now)
    enabled: bool = True
    usage_count: int = 0
    last_used: Optional[datetime] = None
    error_count: int = 0
    avg_execution_time: float = 0.0

    def update_stats(self, result: ToolResult) -> None:
        """Update usage statistics."""
        self.usage_count += 1
        self.last_used = datetime.now()

        if not result.success:
            self.error_count += 1

        # Update average execution time
        if result.execution_time > 0:
            if self.avg_execution_time == 0:
                self.avg_execution_time = result.execution_time
            else:
                # Exponential moving average
                self.avg_execution_time = (
                    0.9 * self.avg_execution_time + 0.1 * result.execution_time
                )


class ToolRegistry:
    """
    Central registry for all ag3ntwerk tools.

    Provides:
    - Tool registration and discovery
    - Search by name, category, tags
    - Tool execution with tracking
    - Usage statistics

    Example:
        registry = get_registry()

        # Register a tool
        registry.register(SendSlackMessageTool())

        # Find tools
        tools = registry.search("send message")
        tools = registry.get_by_category(ToolCategory.COMMUNICATION)

        # Execute a tool
        result = await registry.execute("send_slack_message", channel="#general", message="Hello")
    """

    def __init__(self):
        """Initialize the registry."""
        self._tools: Dict[str, RegisteredTool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {cat: [] for cat in ToolCategory}
        self._tags: Dict[str, List[str]] = {}
        self._aliases: Dict[str, str] = {}

    def register(
        self,
        tool: BaseTool,
        aliases: Optional[List[str]] = None,
    ) -> None:
        """
        Register a tool.

        Args:
            tool: Tool instance to register
            aliases: Alternative names for the tool
        """
        name = tool.metadata.name

        if name in self._tools:
            logger.warning(f"Tool '{name}' already registered, overwriting")

        self._tools[name] = RegisteredTool(tool=tool)

        # Index by category
        category = tool.metadata.category
        if name not in self._categories[category]:
            self._categories[category].append(name)

        # Index by tags
        for tag in tool.metadata.tags:
            tag_lower = tag.lower()
            if tag_lower not in self._tags:
                self._tags[tag_lower] = []
            if name not in self._tags[tag_lower]:
                self._tags[tag_lower].append(name)

        # Register aliases
        if aliases:
            for alias in aliases:
                self._aliases[alias.lower()] = name

        logger.info(f"Registered tool: {name}")

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Tool name

        Returns:
            True if tool was unregistered
        """
        if name not in self._tools:
            return False

        tool = self._tools[name].tool

        # Remove from category index
        category = tool.metadata.category
        if name in self._categories[category]:
            self._categories[category].remove(name)

        # Remove from tag index
        for tag in tool.metadata.tags:
            tag_lower = tag.lower()
            if tag_lower in self._tags and name in self._tags[tag_lower]:
                self._tags[tag_lower].remove(name)

        # Remove aliases
        self._aliases = {k: v for k, v in self._aliases.items() if v != name}

        del self._tools[name]
        logger.info(f"Unregistered tool: {name}")
        return True

    def get(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.

        Args:
            name: Tool name or alias

        Returns:
            Tool instance or None
        """
        # Check aliases first
        if name.lower() in self._aliases:
            name = self._aliases[name.lower()]

        registered = self._tools.get(name)
        return registered.tool if registered else None

    def get_all(self) -> List[BaseTool]:
        """Get all registered tools."""
        return [rt.tool for rt in self._tools.values() if rt.enabled]

    def get_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """Get tools by category."""
        names = self._categories.get(category, [])
        return [self._tools[name].tool for name in names if self._tools[name].enabled]

    def get_by_tag(self, tag: str) -> List[BaseTool]:
        """Get tools by tag."""
        names = self._tags.get(tag.lower(), [])
        return [self._tools[name].tool for name in names if self._tools[name].enabled]

    def search(
        self,
        query: str,
        category: Optional[ToolCategory] = None,
        limit: int = 10,
    ) -> List[BaseTool]:
        """
        Search for tools matching a query.

        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of matching tools sorted by relevance
        """
        results = []

        for name, registered in self._tools.items():
            if not registered.enabled:
                continue

            tool = registered.tool

            # Category filter
            if category and tool.metadata.category != category:
                continue

            # Calculate relevance score
            score = tool.metadata.matches_query(query)
            if score > 0:
                results.append((score, tool))

        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)

        return [tool for _, tool in results[:limit]]

    def find_tools_for_task(self, task_description: str) -> List[BaseTool]:
        """
        Find tools that could help with a task.

        Uses keyword matching and category inference.

        Args:
            task_description: Description of the task

        Returns:
            List of potentially useful tools
        """
        task_lower = task_description.lower()

        # Keyword to category mapping
        category_keywords = {
            ToolCategory.COMMUNICATION: [
                "send",
                "message",
                "email",
                "slack",
                "discord",
                "notify",
                "chat",
                "post",
                "share",
                "communicate",
            ],
            ToolCategory.DATA: [
                "query",
                "database",
                "sql",
                "data",
                "analyze",
                "chart",
                "graph",
                "visualize",
                "spreadsheet",
                "excel",
            ],
            ToolCategory.DEVOPS: [
                "deploy",
                "docker",
                "container",
                "github",
                "pr",
                "issue",
                "cloud",
                "aws",
                "server",
                "ci",
                "cd",
            ],
            ToolCategory.RESEARCH: [
                "search",
                "find",
                "research",
                "scrape",
                "news",
                "paper",
                "article",
                "web",
                "browse",
            ],
            ToolCategory.BUSINESS: [
                "crm",
                "customer",
                "deal",
                "sales",
                "payment",
                "invoice",
                "project",
                "task",
                "jira",
                "workflow",
            ],
            ToolCategory.DOCUMENTS: [
                "pdf",
                "document",
                "report",
                "ocr",
                "scan",
                "generate",
                "create",
                "template",
            ],
        }

        # Find matching categories
        matching_categories = []
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in task_lower:
                    if category not in matching_categories:
                        matching_categories.append(category)

        # Get tools from matching categories
        tools = []
        for category in matching_categories:
            tools.extend(self.get_by_category(category))

        # Also do keyword search
        search_results = self.search(task_description, limit=5)
        for tool in search_results:
            if tool not in tools:
                tools.append(tool)

        return tools

    async def execute(
        self,
        tool_name: str,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Tool name or alias
            **kwargs: Tool parameters

        Returns:
            ToolResult with execution outcome
        """
        # Resolve alias
        if tool_name.lower() in self._aliases:
            tool_name = self._aliases[tool_name.lower()]

        registered = self._tools.get(tool_name)
        if not registered:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found",
                error_type="ToolNotFoundError",
            )

        if not registered.enabled:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' is disabled",
                error_type="ToolDisabledError",
            )

        # Execute tool
        result = await registered.tool.execute(**kwargs)

        # Update statistics
        registered.update_stats(result)

        return result

    def enable(self, name: str) -> bool:
        """Enable a tool."""
        if name in self._tools:
            self._tools[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a tool."""
        if name in self._tools:
            self._tools[name].enabled = False
            return True
        return False

    def get_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get usage statistics.

        Args:
            name: Specific tool name, or None for all tools

        Returns:
            Statistics dict
        """
        if name:
            registered = self._tools.get(name)
            if not registered:
                return {}

            return {
                "name": name,
                "usage_count": registered.usage_count,
                "error_count": registered.error_count,
                "avg_execution_time": registered.avg_execution_time,
                "last_used": registered.last_used.isoformat() if registered.last_used else None,
                "enabled": registered.enabled,
            }

        # Aggregate stats
        total_usage = sum(rt.usage_count for rt in self._tools.values())
        total_errors = sum(rt.error_count for rt in self._tools.values())

        top_tools = sorted(
            self._tools.items(),
            key=lambda x: x[1].usage_count,
            reverse=True,
        )[:10]

        return {
            "total_tools": len(self._tools),
            "enabled_tools": sum(1 for rt in self._tools.values() if rt.enabled),
            "total_usage": total_usage,
            "total_errors": total_errors,
            "error_rate": total_errors / total_usage if total_usage > 0 else 0,
            "top_tools": [{"name": name, "usage": rt.usage_count} for name, rt in top_tools],
            "by_category": {cat.value: len(names) for cat, names in self._categories.items()},
        }

    def list_tools(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """
        List all tools with metadata.

        Args:
            enabled_only: Only list enabled tools

        Returns:
            List of tool info dicts
        """
        tools = []

        for name, registered in self._tools.items():
            if enabled_only and not registered.enabled:
                continue

            tool = registered.tool
            tools.append(
                {
                    "name": name,
                    "description": tool.metadata.description,
                    "category": tool.metadata.category.value,
                    "tags": tool.metadata.tags,
                    "enabled": registered.enabled,
                    "usage_count": registered.usage_count,
                }
            )

        return tools

    def get_tool_help(self, name: str) -> Optional[str]:
        """Get help text for a tool."""
        tool = self.get(name)
        return tool.get_help() if tool else None

    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for a tool."""
        tool = self.get(name)
        return tool.get_schema() if tool else None

    def export_catalog(self) -> Dict[str, Any]:
        """
        Export the full tool catalog.

        Returns:
            Dict with all tool information
        """
        return {
            "tools": [
                {
                    "name": name,
                    "schema": rt.tool.get_schema(),
                    "enabled": rt.enabled,
                    "stats": {
                        "usage_count": rt.usage_count,
                        "error_count": rt.error_count,
                        "avg_execution_time": rt.avg_execution_time,
                    },
                }
                for name, rt in self._tools.items()
            ],
            "categories": {cat.value: names for cat, names in self._categories.items()},
            "tags": self._tags,
            "aliases": self._aliases,
        }
