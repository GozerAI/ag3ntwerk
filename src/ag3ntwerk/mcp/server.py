"""
MCP Server for ag3ntwerk Agent Platform.

Exposes ag3ntwerk agents via Model Context Protocol (MCP).
Includes tools for agents, workflows, and module functionality.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from ag3ntwerk.orchestration.registry import AgentRegistry
from ag3ntwerk.orchestration.base import Orchestrator
from ag3ntwerk.orchestration.workflows import (
    ProductLaunchWorkflow,
    IncidentResponseWorkflow,
    BudgetApprovalWorkflow,
    FeatureReleaseWorkflow,
)
from ag3ntwerk.core.base import Task, TaskPriority
from ag3ntwerk.llm.base import LLMProvider
from ag3ntwerk.mcp.module_tools import MODULE_TOOLS, ModuleToolHandler
from ag3ntwerk.mcp.workflow_tools import WORKFLOW_LIBRARY_TOOLS, WorkflowLibraryToolHandler


class AgentWerkMCPServer:
    """
    MCP Server exposing ag3ntwerk agents.

    Security: This server communicates via stdio (stdin/stdout) only,
    so it is not exposed over the network. If you add an HTTP/SSE
    transport in the future, ensure it binds to 127.0.0.1 only and
    requires an API key via AGENTWERK_MCP_KEY.

    Provides tools for:
    - Executing tasks via specific agents
    - Listing available agents and their capabilities
    - Routing tasks through Nexus
    - Running predefined workflows
    - Managing trends, commerce, brand, and scheduler modules

    Example:
        ```python
        from ag3ntwerk.mcp import AgentWerkMCPServer
        from ag3ntwerk.llm import OllamaProvider

        provider = OllamaProvider()
        await provider.connect()

        server = AgentWerkMCPServer(llm_provider=provider)
        await server.run()
        ```
    """

    # Tool definitions
    TOOLS = [
        Tool(
            name="ag3ntwerk_list_agents",
            description="List all available ag3ntwerk agents with their codes, codenames, and availability status.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="ag3ntwerk_get_agent",
            description="Get detailed information about a specific agent including capabilities.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Agent code (e.g., 'Blueprint', 'Keystone', 'Echo')",
                    },
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="agentwerk_find_agent_for_task",
            description="Find agents that can handle a specific task type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "description": "The type of task (e.g., 'cost_analysis', 'campaign_creation')",
                    },
                },
                "required": ["task_type"],
            },
        ),
        Tool(
            name="agentwerk_execute_task",
            description="Execute a task with a specific agent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_code": {
                        "type": "string",
                        "description": "Agent to use (e.g., 'Blueprint', 'Keystone', 'Echo')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Task description",
                    },
                    "task_type": {
                        "type": "string",
                        "description": "Type of task (e.g., 'cost_analysis', 'campaign_creation')",
                    },
                    "context": {
                        "type": "string",
                        "description": "JSON string with additional context",
                        "default": "{}",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Task priority (low, medium, high, critical)",
                        "default": "medium",
                    },
                },
                "required": ["agent_code", "description", "task_type"],
            },
        ),
        Tool(
            name="agentwerk_route_task",
            description="Route a task through Nexus for automatic agent assignment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Task description",
                    },
                    "task_type": {
                        "type": "string",
                        "description": "Type of task",
                    },
                    "context": {
                        "type": "string",
                        "description": "JSON string with additional context",
                        "default": "{}",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Task priority (low, medium, high, critical)",
                        "default": "medium",
                    },
                },
                "required": ["description", "task_type"],
            },
        ),
        Tool(
            name="agentwerk_list_workflows",
            description="List all available workflows.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="agentwerk_run_workflow",
            description="Execute a predefined workflow.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_name": {
                        "type": "string",
                        "description": "Name of workflow (product_launch, incident_response, budget_approval, feature_release)",
                    },
                    "params": {
                        "type": "string",
                        "description": "JSON string with workflow parameters",
                        "default": "{}",
                    },
                },
                "required": ["workflow_name"],
            },
        ),
        Tool(
            name="agentwerk_system_status",
            description="Get overall ag3ntwerk system status.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="agentwerk_agent_capabilities",
            description="Get capabilities of one or all agents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_code": {
                        "type": "string",
                        "description": "Optional agent code. If not provided, returns all.",
                    },
                },
                "required": [],
            },
        ),
    ]

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        registry: Optional[AgentRegistry] = None,
        include_module_tools: bool = True,
        include_workflow_tools: bool = True,
    ):
        """
        Initialize the MCP server.

        Args:
            llm_provider: LLM provider for agents
            registry: Optional pre-configured registry
            include_module_tools: Include module tools (trends, commerce, brand, scheduler)
            include_workflow_tools: Include workflow library tools (search, recommend, stats)
        """
        self.llm_provider = llm_provider
        self.registry = registry or AgentRegistry(llm_provider=llm_provider)
        self.orchestrator = Orchestrator(self.registry)
        self.include_module_tools = include_module_tools
        self.include_workflow_tools = include_workflow_tools

        # Register standard workflows
        self.orchestrator.register_workflow(ProductLaunchWorkflow)
        self.orchestrator.register_workflow(IncidentResponseWorkflow)
        self.orchestrator.register_workflow(BudgetApprovalWorkflow)
        self.orchestrator.register_workflow(FeatureReleaseWorkflow)

        # Initialize module handler if needed
        self.module_handler = ModuleToolHandler() if include_module_tools else None

        # Initialize workflow library handler if needed
        self.workflow_handler = WorkflowLibraryToolHandler() if include_workflow_tools else None

        self.server = Server("ag3ntwerk-agents")
        self._register_handlers()

    def _register_handlers(self):
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """Return list of available tools."""
            tools = list(self.TOOLS)
            if self.include_module_tools:
                tools.extend(MODULE_TOOLS)
            if self.include_workflow_tools:
                tools.extend(WORKFLOW_LIBRARY_TOOLS)
            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
            """Handle tool calls."""
            # Check agent tools first
            handler = self._get_handler(name)
            if handler:
                result = await handler(arguments)
                return [TextContent(type="text", text=result)]

            # Check module tools if enabled
            if self.include_module_tools and self.module_handler:
                module_handler = self.module_handler.get_handler(name)
                if module_handler:
                    result = await module_handler(arguments)
                    return [TextContent(type="text", text=result)]

            # Check workflow library tools if enabled
            if self.include_workflow_tools and self.workflow_handler:
                workflow_handler = self.workflow_handler.get_handler(name)
                if workflow_handler:
                    result = await workflow_handler(arguments)
                    return [TextContent(type="text", text=result)]

            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    def _get_handler(self, tool_name: str):
        """Get handler for a tool."""
        handlers = {
            "ag3ntwerk_list_agents": self._handle_list_agents,
            "ag3ntwerk_get_agent": self._handle_get_agent,
            "agentwerk_find_agent_for_task": self._handle_find_executive,
            "agentwerk_execute_task": self._handle_execute_task,
            "agentwerk_route_task": self._handle_route_task,
            "agentwerk_list_workflows": self._handle_list_workflows,
            "agentwerk_run_workflow": self._handle_run_workflow,
            "agentwerk_system_status": self._handle_system_status,
            "agentwerk_agent_capabilities": self._handle_capabilities,
        }
        return handlers.get(tool_name)

    async def _handle_list_agents(self, args: Dict[str, Any]) -> str:
        """List all agents."""
        agents = self.registry.list_agents()
        return json.dumps(agents, indent=2)

    async def _handle_get_agent(self, args: Dict[str, Any]) -> str:
        """Get agent details."""
        code = args.get("code", "")
        agent = self.registry.get(code)

        if not agent:
            return json.dumps(
                {
                    "error": f"Agent not found: {code}",
                    "available_codes": self.registry.get_available_codes(),
                }
            )

        capabilities = getattr(agent, "capabilities", [])
        return json.dumps(
            {
                "code": agent.code,
                "name": agent.name,
                "domain": getattr(agent, "domain", ""),
                "codename": getattr(agent, "codename", ""),
                "capabilities": capabilities,
                "is_active": agent.is_active,
            }
        )

    async def _handle_find_executive(self, args: Dict[str, Any]) -> str:
        """Find agents for task type."""
        task_type = args.get("task_type", "")
        agents = self.registry.get_by_capability(task_type)

        return json.dumps(
            [
                {
                    "code": e.code,
                    "name": e.name,
                    "codename": getattr(e, "codename", ""),
                }
                for e in agents
            ]
        )

    async def _handle_execute_task(self, args: Dict[str, Any]) -> str:
        """Execute task with specific agent."""
        agent_code = args.get("agent_code", "")
        description = args.get("description", "")
        task_type = args.get("task_type", "")
        context_str = args.get("context", "{}")
        priority = args.get("priority", "medium")

        agent = self.registry.get(agent_code)
        if not agent:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Agent not found: {agent_code}",
                }
            )

        # Parse context
        try:
            ctx = json.loads(context_str) if context_str else {}
        except json.JSONDecodeError:
            ctx = {}

        # Create task
        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL,
        }

        task = Task(
            description=description,
            task_type=task_type,
            context=ctx,
            priority=priority_map.get(priority, TaskPriority.MEDIUM),
        )

        try:
            result = await agent.execute(task)
            return json.dumps(
                {
                    "success": result.success,
                    "task_id": result.task_id,
                    "output": result.output,
                    "error": result.error,
                    "agent": agent_code,
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                    "agent": agent_code,
                }
            )

    async def _handle_route_task(self, args: Dict[str, Any]) -> str:
        """Route task through Nexus."""
        description = args.get("description", "")
        task_type = args.get("task_type", "")
        context_str = args.get("context", "{}")
        priority = args.get("priority", "medium")

        coo = self.registry.get("Nexus")
        if not coo:
            return json.dumps(
                {
                    "success": False,
                    "error": "Nexus not available for routing",
                }
            )

        # Parse context
        try:
            ctx = json.loads(context_str) if context_str else {}
        except json.JSONDecodeError:
            ctx = {}

        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL,
        }

        task = Task(
            description=description,
            task_type=task_type,
            context=ctx,
            priority=priority_map.get(priority, TaskPriority.MEDIUM),
        )

        try:
            result = await coo.execute(task)
            return json.dumps(
                {
                    "success": result.success,
                    "task_id": result.task_id,
                    "output": result.output,
                    "error": result.error,
                    "routed_via": "Nexus",
                    "handled_by": result.metrics.get("handled_by") if result.metrics else None,
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    async def _handle_list_workflows(self, args: Dict[str, Any]) -> str:
        """List available workflows."""
        workflows = self.orchestrator.list_workflows()
        return json.dumps(workflows, indent=2)

    async def _handle_run_workflow(self, args: Dict[str, Any]) -> str:
        """Run workflow."""
        workflow_name = args.get("workflow_name", "")
        params_str = args.get("params", "{}")

        try:
            workflow_params = json.loads(params_str) if params_str else {}
        except json.JSONDecodeError:
            return json.dumps(
                {
                    "success": False,
                    "error": "Invalid JSON in params",
                }
            )

        try:
            result = await self.orchestrator.execute(workflow_name, **workflow_params)
            return json.dumps(result.to_dict(), indent=2)
        except ValueError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                    "available_workflows": [w["name"] for w in self.orchestrator.list_workflows()],
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    async def _handle_system_status(self, args: Dict[str, Any]) -> str:
        """Get system status."""
        agents = self.registry.list_agents()
        available = [e for e in agents if e.get("available")]
        instantiated = [e for e in agents if e.get("instantiated")]

        status = {
            "total_executives": len(agents),
            "available_executives": len(available),
            "instantiated_executives": len(instantiated),
            "llm_provider": self.llm_provider.__class__.__name__ if self.llm_provider else None,
            "llm_connected": self.llm_provider.is_connected if self.llm_provider else False,
            "registered_workflows": len(self.orchestrator.list_workflows()),
            "agents": agents,
            "modules_enabled": self.include_module_tools,
            "available_modules": (
                ["trends", "commerce", "brand", "scheduler"] if self.include_module_tools else []
            ),
            "workflow_library_enabled": self.include_workflow_tools,
        }

        return json.dumps(status, indent=2)

    async def _handle_capabilities(self, args: Dict[str, Any]) -> str:
        """Get agent capabilities."""
        agent_code = args.get("agent_code")

        if agent_code:
            agent = self.registry.get(agent_code)
            if not agent:
                return json.dumps(
                    {
                        "error": f"Agent not found: {agent_code}",
                    }
                )
            return json.dumps(
                {
                    agent_code: getattr(agent, "capabilities", []),
                }
            )

        # Get all capabilities
        capabilities = {}
        for code in self.registry.get_available_codes():
            agent = self.registry.get(code)
            if agent:
                capabilities[code] = getattr(agent, "capabilities", [])

        return json.dumps(capabilities, indent=2)

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)


async def main():
    """Entry point for running ag3ntwerk MCP server."""
    from ag3ntwerk.llm import auto_connect

    # Try to auto-connect to LLM provider
    provider = await auto_connect()

    server = AgentWerkMCPServer(llm_provider=provider)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
