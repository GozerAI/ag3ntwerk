"""
ag3ntwerk MCP Server.

Exposes ag3ntwerk agents via Model Context Protocol (MCP) for integration
with LLM-based tools and workflows.

Includes module tools for:
- Trends: Market trend analysis and niche identification
- Commerce: Storefront management (Shopify/Medusa)
- Brand: Brand identity and guideline management
- Scheduler: Task scheduling and workflow orchestration
- Workflow Library: Search, recommend, and manage automation workflows
"""

from ag3ntwerk.mcp.server import AgentWerkMCPServer
from ag3ntwerk.mcp.module_tools import (
    MODULE_TOOLS,
    ModuleToolHandler,
    TREND_TOOLS,
    COMMERCE_TOOLS,
    BRAND_TOOLS,
    SCHEDULER_TOOLS,
)
from ag3ntwerk.mcp.workflow_tools import (
    WORKFLOW_LIBRARY_TOOLS,
    WorkflowLibraryToolHandler,
)

__all__ = [
    "AgentWerkMCPServer",
    "MODULE_TOOLS",
    "ModuleToolHandler",
    "TREND_TOOLS",
    "COMMERCE_TOOLS",
    "BRAND_TOOLS",
    "SCHEDULER_TOOLS",
    "WORKFLOW_LIBRARY_TOOLS",
    "WorkflowLibraryToolHandler",
]
