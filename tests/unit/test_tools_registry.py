"""
Tests for ag3ntwerk Tools Registry Module.

Tests ToolRegistry and tool discovery functionality.
"""

import pytest
from typing import List

from ag3ntwerk.tools.base import (
    BaseTool,
    ToolParameter,
    ToolMetadata,
    ToolResult,
    ToolCategory,
    ParameterType,
)
from ag3ntwerk.tools.registry import ToolRegistry, RegisteredTool


class MockCommunicationTool(BaseTool):
    """Mock communication tool."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mock_slack",
            description="Send messages to Slack",
            category=ToolCategory.COMMUNICATION,
            tags=["slack", "message", "chat"],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="channel",
                description="Channel",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="message",
                description="Message",
                param_type=ParameterType.STRING,
                required=True,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"sent": True})


class MockDataTool(BaseTool):
    """Mock data tool."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mock_sql",
            description="Run SQL queries",
            category=ToolCategory.DATA,
            tags=["sql", "database", "query"],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                description="SQL query",
                param_type=ParameterType.STRING,
                required=True,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"rows": []})


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = MockCommunicationTool()

        registry.register(tool)

        assert registry.get("mock_slack") is not None
        assert registry.get("mock_slack") == tool

    def test_register_with_alias(self):
        """Test registering a tool with aliases."""
        registry = ToolRegistry()
        tool = MockCommunicationTool()

        registry.register(tool, aliases=["slack", "send_slack"])

        assert registry.get("mock_slack") == tool
        assert registry.get("slack") == tool
        assert registry.get("send_slack") == tool

    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = ToolRegistry()
        tool = MockCommunicationTool()
        registry.register(tool)

        result = registry.unregister("mock_slack")

        assert result is True
        assert registry.get("mock_slack") is None

    def test_unregister_nonexistent_tool(self):
        """Test unregistering a tool that doesn't exist."""
        registry = ToolRegistry()

        result = registry.unregister("nonexistent")

        assert result is False

    def test_get_nonexistent_tool(self):
        """Test getting a tool that doesn't exist."""
        registry = ToolRegistry()

        tool = registry.get("nonexistent")

        assert tool is None

    def test_get_all_tools(self):
        """Test getting all registered tools."""
        registry = ToolRegistry()
        tool1 = MockCommunicationTool()
        tool2 = MockDataTool()

        registry.register(tool1)
        registry.register(tool2)

        all_tools = registry.get_all()

        assert len(all_tools) == 2
        assert tool1 in all_tools
        assert tool2 in all_tools

    def test_get_by_category(self):
        """Test getting tools by category."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())
        registry.register(MockDataTool())

        comm_tools = registry.get_by_category(ToolCategory.COMMUNICATION)
        data_tools = registry.get_by_category(ToolCategory.DATA)

        assert len(comm_tools) == 1
        assert comm_tools[0].metadata.name == "mock_slack"
        assert len(data_tools) == 1
        assert data_tools[0].metadata.name == "mock_sql"

    def test_get_by_tag(self):
        """Test getting tools by tag."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())
        registry.register(MockDataTool())

        slack_tools = registry.get_by_tag("slack")
        sql_tools = registry.get_by_tag("sql")

        assert len(slack_tools) == 1
        assert len(sql_tools) == 1

    def test_search_by_name(self):
        """Test searching tools by name."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())
        registry.register(MockDataTool())

        results = registry.search("slack")

        assert len(results) >= 1
        assert any(t.metadata.name == "mock_slack" for t in results)

    def test_search_by_description(self):
        """Test searching tools by description."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())
        registry.register(MockDataTool())

        results = registry.search("SQL queries")

        assert len(results) >= 1
        assert any(t.metadata.name == "mock_sql" for t in results)

    def test_search_with_category_filter(self):
        """Test searching with category filter."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())
        registry.register(MockDataTool())

        results = registry.search("query", category=ToolCategory.DATA)

        # Should only return data tools
        for tool in results:
            assert tool.metadata.category == ToolCategory.DATA

    def test_search_with_limit(self):
        """Test search respects limit."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())
        registry.register(MockDataTool())

        results = registry.search("mock", limit=1)

        assert len(results) <= 1

    def test_find_tools_for_task(self):
        """Test finding tools for a task description."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())
        registry.register(MockDataTool())

        # Should find communication tools
        tools = registry.find_tools_for_task("send a message to the team")
        assert any(t.metadata.category == ToolCategory.COMMUNICATION for t in tools)

        # Should find data tools
        tools = registry.find_tools_for_task("query the database")
        assert any(t.metadata.category == ToolCategory.DATA for t in tools)

    def test_enable_disable_tool(self):
        """Test enabling and disabling tools."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())

        # Disable
        registry.disable("mock_slack")
        # get() still returns the tool (for inspection), but get_all() excludes disabled
        assert registry.get("mock_slack") is not None
        assert len(registry.get_all()) == 0  # get_all() excludes disabled

        # Enable
        registry.enable("mock_slack")
        assert registry.get("mock_slack") is not None
        assert len(registry.get_all()) == 1

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test executing a tool through registry."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())

        result = await registry.execute("mock_slack", channel="#general", message="Hello")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        """Test executing a tool that doesn't exist."""
        registry = ToolRegistry()

        result = await registry.execute("nonexistent", arg="value")

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_disabled_tool(self):
        """Test executing a disabled tool."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())
        registry.disable("mock_slack")

        result = await registry.execute("mock_slack", channel="#general", message="Hello")

        assert result.success is False
        assert "disabled" in result.error.lower()

    def test_get_stats(self):
        """Test getting usage statistics."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())
        registry.register(MockDataTool())

        stats = registry.get_stats()

        assert stats["total_tools"] == 2
        assert stats["enabled_tools"] == 2
        assert stats["total_usage"] == 0

    def test_list_tools(self):
        """Test listing all tools."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())
        registry.register(MockDataTool())

        tools_list = registry.list_tools()

        assert len(tools_list) == 2
        assert all("name" in t for t in tools_list)
        assert all("description" in t for t in tools_list)
        assert all("category" in t for t in tools_list)

    def test_get_tool_help(self):
        """Test getting help for a tool."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())

        help_text = registry.get_tool_help("mock_slack")

        assert help_text is not None
        assert "mock_slack" in help_text

    def test_get_tool_schema(self):
        """Test getting schema for a tool."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())

        schema = registry.get_tool_schema("mock_slack")

        assert schema is not None
        assert schema["name"] == "mock_slack"

    def test_export_catalog(self):
        """Test exporting tool catalog."""
        registry = ToolRegistry()
        registry.register(MockCommunicationTool())

        catalog = registry.export_catalog()

        assert "tools" in catalog
        assert "categories" in catalog
        assert len(catalog["tools"]) == 1


class TestRegisteredTool:
    """Tests for RegisteredTool dataclass."""

    @pytest.mark.asyncio
    async def test_update_stats_success(self):
        """Test updating stats for successful execution."""
        tool = MockCommunicationTool()
        registered = RegisteredTool(tool=tool)

        result = ToolResult(success=True, execution_time=0.5)
        registered.update_stats(result)

        assert registered.usage_count == 1
        assert registered.error_count == 0
        assert registered.last_used is not None
        assert registered.avg_execution_time > 0

    @pytest.mark.asyncio
    async def test_update_stats_failure(self):
        """Test updating stats for failed execution."""
        tool = MockCommunicationTool()
        registered = RegisteredTool(tool=tool)

        result = ToolResult(success=False, error="Test error")
        registered.update_stats(result)

        assert registered.usage_count == 1
        assert registered.error_count == 1
