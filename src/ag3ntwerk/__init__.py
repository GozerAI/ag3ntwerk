"""
ag3ntwerk: Unified AI Agent Platform
===================================

A hierarchical AI agent orchestration platform using a corporate
agent metaphor for task routing and execution.

Architecture:
- Coordination Layer (Overwatch/Overwatch): Internal workflow and task routing
- Strategic Intelligence (Nexus): External Nexus service for strategic guidance
- Technical Execution (Forge): External Forge service for development tasks
- Security Operations (Sentinel): External Sentinel/Citadel for security tasks

Components:
- Overwatch (Overwatch): Internal coordination and drift detection
- Operations Stack: Sentinel (Sentinel), Keystone (Keystone), Index (Index)
- Technology Stack: Forge (Forge), Foundry (Foundry), Citadel (Citadel)
- Strategy Stack: Compass (Compass), Axiom (Axiom)
- Service Bridges: Nexus, Forge, Sentinel for external services
- LLM Providers: Ollama (recommended), GPT4All

Quick Start:
    from ag3ntwerk import Task, TaskPriority
    from ag3ntwerk.llm import get_provider, OllamaProvider
    from ag3ntwerk.agents.overwatch import Overwatch

    # Initialize LLM provider
    provider = OllamaProvider()
    await provider.connect()

    # Create Overwatch (internal coordinator) and execute task
    cos = Overwatch(llm_provider=provider)
    task = Task(
        description="Analyze security posture",
        task_type="security_scan",
        priority=TaskPriority.HIGH,
    )
    result = await cos.execute(task)

    # For backward compatibility, Nexus still works:
    from ag3ntwerk.agents.nexus import Nexus
    coo = Nexus(llm_provider=provider)
    result = await coo.execute(task)
"""

__version__ = "0.1.0"
__author__ = "GozerAI"

# Core classes
from ag3ntwerk.core.base import (
    Agent,
    Manager,
    Specialist,
    Task,
    TaskResult,
    TaskStatus,
    TaskPriority,
)

# Exceptions
from ag3ntwerk.core.exceptions import (
    AgentWerkError,
    TaskExecutionError,
    AgentError,
    LLMError,
)

# LLM Providers
from ag3ntwerk.llm import (
    get_provider,
    auto_connect,
    OllamaProvider,
    GPT4AllProvider,
    LLMProvider,
    ModelTier,
)

# Memory/State
from ag3ntwerk.memory import (
    StateStore,
    get_default_store,
)

# Orchestration
from ag3ntwerk.orchestration import (
    AgentRegistry,
    Orchestrator,
    Workflow,
    WorkflowResult,
    WorkflowStatus,
)


# MCP Server - lazy import to avoid circular dependency
# Use: from ag3ntwerk.mcp import AgentWerkMCPServer
def get_mcp_server():
    """Get the MCP server class (lazy import to avoid circular dependency)."""
    from ag3ntwerk.mcp import AgentWerkMCPServer

    return AgentWerkMCPServer


__all__ = [
    # Version
    "__version__",
    "__author__",
    # Core classes
    "Agent",
    "Manager",
    "Specialist",
    "Task",
    "TaskResult",
    "TaskStatus",
    "TaskPriority",
    # Exceptions
    "AgentWerkError",
    "TaskExecutionError",
    "AgentError",
    "LLMError",
    # LLM
    "get_provider",
    "auto_connect",
    "OllamaProvider",
    "GPT4AllProvider",
    "LLMProvider",
    "ModelTier",
    # Memory
    "StateStore",
    "get_default_store",
    # Orchestration
    "AgentRegistry",
    "Orchestrator",
    "Workflow",
    "WorkflowResult",
    "WorkflowStatus",
    # MCP
    "get_mcp_server",
]
