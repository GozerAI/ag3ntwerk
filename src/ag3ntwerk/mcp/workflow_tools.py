"""
MCP Workflow Library Tools - Exposes workflow library via MCP.

Provides search, recommendation, retrieval, and statistics for the
multi-tool automation workflow library (n8n, Zapier, Make, LangChain,
CrewAI, AutoGen, IFTTT).

The workflow library is populated by the Harvester service and stored
in a shared PostgreSQL database.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.types import Tool

logger = logging.getLogger(__name__)


def _error_response(error: Exception, context: str = "") -> str:
    """Create a standardized error response."""
    error_type = type(error).__name__
    error_msg = str(error)

    response = {
        "success": False,
        "error": {
            "type": error_type,
            "message": error_msg,
            "context": context,
        },
    }

    logger.error(f"MCP Handler Error [{context}]: {error_type}: {error_msg}")

    return json.dumps(response, indent=2)


# =============================================================================
# Tool Definitions
# =============================================================================

WORKFLOW_LIBRARY_TOOLS = [
    Tool(
        name="workflow_search",
        description=(
            "Search the automation workflow library across all tools and frameworks. "
            "Finds workflows by keyword matching against names, descriptions, and tags. "
            "Supports filtering by tool type, category, minimum quality score, "
            "and optional semantic (vector similarity) search for better results."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'email automation', 'lead generation', 'AI agent')",
                },
                "tool_type": {
                    "type": "string",
                    "description": "Filter by automation tool",
                    "enum": [
                        "n8n",
                        "zapier",
                        "make",
                        "langchain",
                        "crewai",
                        "autogen",
                        "ifttt",
                        "activepieces",
                        "windmill",
                        "temporal",
                        "airflow",
                        "node-red",
                        "prefect",
                        "dagster",
                        "langgraph",
                    ],
                },
                "category": {
                    "type": "string",
                    "description": (
                        "Filter by category: lead-gen-crm, content-marketing, data-processing, "
                        "devops-monitoring, general-productivity, ai-agent, multi-step-automation, "
                        "integration-pipeline, orchestration, data-pipeline"
                    ),
                },
                "min_score": {
                    "type": "integer",
                    "description": "Minimum quality score (0-100). Higher values return only well-documented workflows.",
                    "default": 0,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (max 50)",
                    "default": 10,
                },
                "semantic": {
                    "type": "boolean",
                    "description": "Enable semantic vector search for better conceptual matching (slower but more accurate)",
                    "default": False,
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="workflow_get",
        description=(
            "Get full details for a specific workflow by its ID. "
            "Returns complete workflow data including the JSON definition/source code, "
            "metadata, quality score, node types, credentials required, and author info."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {
                    "type": "string",
                    "description": "UUID of the workflow to retrieve",
                },
            },
            "required": ["workflow_id"],
        },
    ),
    Tool(
        name="workflow_recommend",
        description=(
            "Get workflow recommendations for a given task description. "
            "Uses hybrid ranking: text relevance (35%), semantic vector similarity (35%), "
            "quality score (20%), and historical success rate (10%). "
            "Ideal for finding the best automation solution for a specific use case."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": (
                        "Natural language description of the task to automate "
                        "(e.g., 'send Slack notifications when new leads arrive in HubSpot')"
                    ),
                },
                "tool_type": {
                    "type": "string",
                    "description": "Optional: prefer a specific tool type",
                    "enum": [
                        "n8n",
                        "zapier",
                        "make",
                        "langchain",
                        "crewai",
                        "autogen",
                        "ifttt",
                        "activepieces",
                        "windmill",
                        "temporal",
                        "airflow",
                        "node-red",
                        "prefect",
                        "dagster",
                        "langgraph",
                    ],
                },
                "agent_code": {
                    "type": "string",
                    "description": "Agent code for personalized learning-based recommendations",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of recommendations (max 20)",
                    "default": 5,
                },
            },
            "required": ["task_description"],
        },
    ),
    Tool(
        name="workflow_stats",
        description=(
            "Get aggregate statistics about the workflow library. "
            "Returns total counts, breakdown by tool type, category distribution, "
            "source distribution, and quality tier distribution."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="workflow_deploy",
        description=(
            "Deploy an n8n workflow from the library to a running n8n instance. "
            "Fetches the workflow definition, pushes it to n8n via API, and records "
            "the deployment for tracking. Only works with tool_type='n8n' workflows."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {
                    "type": "string",
                    "description": "UUID of the workflow in the library to deploy",
                },
                "activate": {
                    "type": "boolean",
                    "description": "Whether to activate the workflow immediately after deployment",
                    "default": False,
                },
                "deployed_by": {
                    "type": "string",
                    "description": "Agent code or identifier of who is deploying",
                },
            },
            "required": ["workflow_id"],
        },
    ),
    Tool(
        name="workflow_execute",
        description=(
            "Execute a deployed workflow on n8n. Triggers the workflow with optional "
            "input data and returns the execution result. Also records the outcome "
            "for the learning system."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "n8n_workflow_id": {
                    "type": "string",
                    "description": "The n8n workflow ID (returned from workflow_deploy)",
                },
                "data": {
                    "type": "object",
                    "description": "Optional input data to pass to the workflow",
                },
                "library_workflow_id": {
                    "type": "string",
                    "description": "Optional library UUID for tracking and learning",
                },
            },
            "required": ["n8n_workflow_id"],
        },
    ),
    Tool(
        name="workflow_executions",
        description=(
            "List recent executions for a deployed workflow. Shows execution history "
            "including status, timing, and results."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "n8n_workflow_id": {
                    "type": "string",
                    "description": "The n8n workflow ID",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by execution status (success, error, running)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of executions to return",
                    "default": 10,
                },
            },
            "required": ["n8n_workflow_id"],
        },
    ),
    Tool(
        name="workflow_similar",
        description=(
            "Find workflows similar to a given workflow or text description. "
            "Uses pgvector embedding similarity (cosine distance) to find workflows "
            "that are conceptually related. Provide either a workflow_id to find "
            "workflows similar to an existing one, or text to find workflows "
            "matching a description."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {
                    "type": "string",
                    "description": "UUID of an existing workflow to find similar workflows for",
                },
                "text": {
                    "type": "string",
                    "description": (
                        "Text description to find similar workflows for "
                        "(e.g., 'email notification when new lead arrives'). "
                        "Use this when you don't have a specific workflow_id."
                    ),
                },
                "tool_type": {
                    "type": "string",
                    "description": "Optional: filter results to a specific tool type",
                    "enum": [
                        "n8n",
                        "zapier",
                        "make",
                        "langchain",
                        "crewai",
                        "autogen",
                        "ifttt",
                        "activepieces",
                        "windmill",
                        "temporal",
                        "airflow",
                        "node-red",
                        "prefect",
                        "dagster",
                        "langgraph",
                    ],
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of similar workflows to return (max 50)",
                    "default": 10,
                },
            },
            "required": [],
        },
    ),
]


# =============================================================================
# Tool Handler
# =============================================================================


class WorkflowLibraryToolHandler:
    """
    Handles MCP tool calls for the Workflow Library.

    Delegates to the WorkflowLibraryPlugin for database access.
    The plugin must be initialized and connected before tools can be used.
    """

    def __init__(self, plugin=None):
        """
        Initialize the handler.

        Args:
            plugin: WorkflowLibraryPlugin instance. If None, will attempt
                    lazy loading from the plugin registry.
        """
        self._plugin = plugin

    @property
    def plugin(self):
        """Get the workflow library plugin, lazy-loading if needed."""
        if self._plugin is None:
            try:
                from ag3ntwerk.core.plugins import get_plugin_manager

                manager = get_plugin_manager()
                self._plugin = manager.get_plugin("workflow-library")
            except Exception as e:
                logger.warning("WorkflowLibraryPlugin not available: %s", e)
        return self._plugin

    def get_handler(self, tool_name: str):
        """Get handler function for a tool name."""
        handlers = {
            "workflow_search": self._handle_workflow_search,
            "workflow_get": self._handle_workflow_get,
            "workflow_recommend": self._handle_workflow_recommend,
            "workflow_stats": self._handle_workflow_stats,
            "workflow_deploy": self._handle_workflow_deploy,
            "workflow_execute": self._handle_workflow_execute,
            "workflow_executions": self._handle_workflow_executions,
            "workflow_similar": self._handle_workflow_similar,
        }
        return handlers.get(tool_name)

    # ─── Handler Methods ─────────────────────────────────────────────────

    async def _handle_workflow_search(self, args: Dict[str, Any]) -> str:
        """Search the workflow library."""
        try:
            if not self.plugin:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Workflow library plugin is not available. Ensure it is configured and the database is running.",
                    }
                )

            query = args.get("query", "")
            if not query:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Search query is required.",
                    }
                )

            results = await self.plugin.search(
                query=query,
                tool_type=args.get("tool_type"),
                category=args.get("category"),
                min_score=args.get("min_score", 0),
                limit=args.get("limit", 10),
                semantic=args.get("semantic", False),
            )

            return json.dumps(
                {
                    "success": True,
                    "query": query,
                    "filters": {
                        k: v
                        for k, v in {
                            "tool_type": args.get("tool_type"),
                            "category": args.get("category"),
                            "min_score": args.get("min_score"),
                        }.items()
                        if v is not None
                    },
                    "count": len(results),
                    "workflows": results,
                },
                indent=2,
                default=str,
            )

        except Exception as e:
            return _error_response(e, "workflow_search")

    async def _handle_workflow_get(self, args: Dict[str, Any]) -> str:
        """Get a specific workflow by ID."""
        try:
            if not self.plugin:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Workflow library plugin is not available.",
                    }
                )

            workflow_id = args.get("workflow_id", "")
            if not workflow_id:
                return json.dumps(
                    {
                        "success": False,
                        "error": "workflow_id is required.",
                    }
                )

            result = await self.plugin.get_workflow(workflow_id)

            if result is None:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Workflow not found: {workflow_id}",
                    }
                )

            return json.dumps(
                {
                    "success": True,
                    "workflow": result,
                },
                indent=2,
                default=str,
            )

        except Exception as e:
            return _error_response(e, "workflow_get")

    async def _handle_workflow_recommend(self, args: Dict[str, Any]) -> str:
        """Get workflow recommendations for a task."""
        try:
            if not self.plugin:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Workflow library plugin is not available.",
                    }
                )

            task_description = args.get("task_description", "")
            if not task_description:
                return json.dumps(
                    {
                        "success": False,
                        "error": "task_description is required.",
                    }
                )

            results = await self.plugin.recommend(
                task_description=task_description,
                tool_type=args.get("tool_type"),
                agent_code=args.get("agent_code"),
                limit=args.get("limit", 5),
            )

            return json.dumps(
                {
                    "success": True,
                    "task_description": task_description,
                    "tool_type_filter": args.get("tool_type"),
                    "count": len(results),
                    "recommendations": results,
                },
                indent=2,
                default=str,
            )

        except Exception as e:
            return _error_response(e, "workflow_recommend")

    async def _handle_workflow_stats(self, args: Dict[str, Any]) -> str:
        """Get workflow library statistics."""
        try:
            if not self.plugin:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Workflow library plugin is not available.",
                    }
                )

            stats = await self.plugin.get_stats()

            return json.dumps(
                {
                    "success": True,
                    "statistics": stats,
                },
                indent=2,
                default=str,
            )

        except Exception as e:
            return _error_response(e, "workflow_stats")

    async def _handle_workflow_deploy(self, args: Dict[str, Any]) -> str:
        """Deploy a workflow to n8n."""
        try:
            if not self.plugin:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Workflow library plugin is not available.",
                    }
                )

            workflow_id = args.get("workflow_id", "")
            if not workflow_id:
                return json.dumps(
                    {
                        "success": False,
                        "error": "workflow_id is required.",
                    }
                )

            result = await self.plugin.deploy_workflow(
                workflow_id=workflow_id,
                activate=args.get("activate", False),
                deployed_by=args.get("deployed_by"),
            )

            return json.dumps(
                {
                    "success": True,
                    "deployment": result,
                },
                indent=2,
                default=str,
            )

        except ValueError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )
        except Exception as e:
            return _error_response(e, "workflow_deploy")

    async def _handle_workflow_execute(self, args: Dict[str, Any]) -> str:
        """Execute a deployed workflow."""
        try:
            if not self.plugin:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Workflow library plugin is not available.",
                    }
                )

            n8n_workflow_id = args.get("n8n_workflow_id", "")
            if not n8n_workflow_id:
                return json.dumps(
                    {
                        "success": False,
                        "error": "n8n_workflow_id is required.",
                    }
                )

            result = await self.plugin.execute_deployed(
                n8n_workflow_id=n8n_workflow_id,
                data=args.get("data"),
                library_workflow_id=args.get("library_workflow_id"),
            )

            return json.dumps(
                {
                    "success": True,
                    "execution": result,
                },
                indent=2,
                default=str,
            )

        except Exception as e:
            return _error_response(e, "workflow_execute")

    async def _handle_workflow_executions(self, args: Dict[str, Any]) -> str:
        """List executions for a deployed workflow."""
        try:
            if not self.plugin:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Workflow library plugin is not available.",
                    }
                )

            n8n_workflow_id = args.get("n8n_workflow_id", "")
            if not n8n_workflow_id:
                return json.dumps(
                    {
                        "success": False,
                        "error": "n8n_workflow_id is required.",
                    }
                )

            results = await self.plugin.list_executions(
                n8n_workflow_id=n8n_workflow_id,
                status=args.get("status"),
                limit=args.get("limit", 10),
            )

            return json.dumps(
                {
                    "success": True,
                    "n8n_workflow_id": n8n_workflow_id,
                    "count": len(results),
                    "executions": results,
                },
                indent=2,
                default=str,
            )

        except Exception as e:
            return _error_response(e, "workflow_executions")

    async def _handle_workflow_similar(self, args: Dict[str, Any]) -> str:
        """Find workflows similar to a given workflow or text description."""
        try:
            if not self.plugin:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Workflow library plugin is not available.",
                    }
                )

            workflow_id = args.get("workflow_id", "")
            text = args.get("text", "")

            if not workflow_id and not text:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Either workflow_id or text is required.",
                    }
                )

            if workflow_id and text:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Provide either workflow_id or text, not both.",
                    }
                )

            tool_type = args.get("tool_type")
            limit = args.get("limit", 10)

            if workflow_id:
                results = await self.plugin.find_similar(
                    workflow_id=workflow_id,
                    limit=limit,
                    tool_type=tool_type,
                )
                return json.dumps(
                    {
                        "success": True,
                        "reference_workflow_id": workflow_id,
                        "count": len(results),
                        "similar": results,
                    },
                    indent=2,
                    default=str,
                )
            else:
                results = await self.plugin.find_similar_by_text(
                    text=text,
                    limit=limit,
                    tool_type=tool_type,
                )
                return json.dumps(
                    {
                        "success": True,
                        "reference_text": text,
                        "count": len(results),
                        "similar": results,
                    },
                    indent=2,
                    default=str,
                )

        except Exception as e:
            return _error_response(e, "workflow_similar")
