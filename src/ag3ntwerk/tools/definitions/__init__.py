"""
Tool Definitions for ag3ntwerk.

This module provides concrete tool implementations that wrap integrations.
Each tool follows the BaseTool interface for consistent usage.
"""

from ag3ntwerk.tools.definitions.communication import (
    SendSlackMessageTool,
    SendEmailTool,
    CreateCalendarEventTool,
    SendDiscordMessageTool,
    CreateNotionPageTool,
)
from ag3ntwerk.tools.definitions.data import (
    RunSQLQueryTool,
    AnalyzeDataFrameTool,
    CreateVisualizationTool,
    ReadSpreadsheetTool,
)
from ag3ntwerk.tools.definitions.devops import (
    CreateGitHubIssueTool,
    CreatePullRequestTool,
    RunDockerContainerTool,
)
from ag3ntwerk.tools.definitions.research import (
    WebScrapeTool,
    SearchNewsTool,
    SearchPapersTool,
)
from ag3ntwerk.tools.definitions.business import (
    CreateCRMContactTool,
    ProcessPaymentTool,
    CreateProjectTaskTool,
    TriggerWorkflowTool,
)
from ag3ntwerk.tools.definitions.documents import (
    ExtractPDFTextTool,
    OCRImageTool,
    GenerateDocumentTool,
)
from ag3ntwerk.tools.definitions.swarm import (
    SwarmExecuteTool,
    SwarmStatusTool,
)

# All available tools
ALL_TOOLS = [
    # Communication
    SendSlackMessageTool,
    SendEmailTool,
    CreateCalendarEventTool,
    SendDiscordMessageTool,
    CreateNotionPageTool,
    # Data
    RunSQLQueryTool,
    AnalyzeDataFrameTool,
    CreateVisualizationTool,
    ReadSpreadsheetTool,
    # DevOps
    CreateGitHubIssueTool,
    CreatePullRequestTool,
    RunDockerContainerTool,
    # Research
    WebScrapeTool,
    SearchNewsTool,
    SearchPapersTool,
    # Business
    CreateCRMContactTool,
    ProcessPaymentTool,
    CreateProjectTaskTool,
    TriggerWorkflowTool,
    # Documents
    ExtractPDFTextTool,
    OCRImageTool,
    GenerateDocumentTool,
    # Swarm
    SwarmExecuteTool,
    SwarmStatusTool,
]


def register_all_tools():
    """Register all tools with the global registry."""
    from ag3ntwerk.tools.registry import get_registry

    registry = get_registry()

    for tool_class in ALL_TOOLS:
        try:
            tool = tool_class()
            registry.register(tool)
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to register tool {tool_class.__name__}: {e}"
            )

    return registry


__all__ = [
    "SendSlackMessageTool",
    "SendEmailTool",
    "CreateCalendarEventTool",
    "SendDiscordMessageTool",
    "CreateNotionPageTool",
    "RunSQLQueryTool",
    "AnalyzeDataFrameTool",
    "CreateVisualizationTool",
    "ReadSpreadsheetTool",
    "CreateGitHubIssueTool",
    "CreatePullRequestTool",
    "RunDockerContainerTool",
    "WebScrapeTool",
    "SearchNewsTool",
    "SearchPapersTool",
    "CreateCRMContactTool",
    "ProcessPaymentTool",
    "CreateProjectTaskTool",
    "TriggerWorkflowTool",
    "ExtractPDFTextTool",
    "OCRImageTool",
    "GenerateDocumentTool",
    "SwarmExecuteTool",
    "SwarmStatusTool",
    "ALL_TOOLS",
    "register_all_tools",
]
