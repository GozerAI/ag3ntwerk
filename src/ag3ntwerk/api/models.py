"""
Pydantic request/response models and validation constants for the ag3ntwerk API.
"""

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from ag3ntwerk.core.identity import AgentRegistry

# ============================================================
# Input Validation Constants
# ============================================================

VALID_PRIORITIES = {"low", "medium", "high", "critical"}

# Canonical agent codes — the registry handles case-insensitive resolution
CANONICAL_AGENTS = {
    "Overwatch",  # Overwatch (Overwatch) — internal coordination layer
    "Nexus",
    "Forge",
    "Keystone",
    "Echo",
    "Blueprint",
    "Beacon",
    "Sentinel",
    "Axiom",
    "Compass",
    "Index",
    "Vector",
    "Accord",
    "Aegis",
    "Foundry",
    "Citadel",
}
AGENT_REGISTRY = AgentRegistry.from_codes(CANONICAL_AGENTS)

MAX_DESCRIPTION_LENGTH = 10000
MAX_MESSAGE_LENGTH = 10000
MAX_TASK_TYPE_LENGTH = 100
MAX_WORKFLOW_NAME_LENGTH = 100
MAX_CONTEXT_DEPTH = 10
MAX_CONTEXT_SIZE = 100000  # 100KB serialized


# ============================================================
# Request Models
# ============================================================


class TaskCreate(BaseModel):
    """Request model for creating a new task."""

    description: str = Field(
        ...,
        min_length=1,
        max_length=MAX_DESCRIPTION_LENGTH,
        description="Task description",
        examples=["Analyze Q1 sales data and provide insights"],
    )
    task_type: str = Field(
        default="general",
        min_length=1,
        max_length=MAX_TASK_TYPE_LENGTH,
        description="Type of task to execute",
        examples=["general", "code_review", "cost_analysis"],
    )
    priority: str = Field(
        default="medium",
        description="Task priority level",
        examples=["low", "medium", "high", "critical"],
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the task",
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate and sanitize task description."""
        v = v.strip()
        if not v:
            raise ValueError("Description cannot be empty or whitespace only")
        return v

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, v: str) -> str:
        """Validate task type format."""
        v = v.strip().lower()
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                "Task type must start with a letter and contain only "
                "lowercase letters, numbers, and underscores"
            )
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate priority is a valid value."""
        v = v.strip().lower()
        if v not in VALID_PRIORITIES:
            raise ValueError(f"Priority must be one of: {', '.join(sorted(VALID_PRIORITIES))}")
        return v

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate context size and depth."""
        import json

        def check_depth(obj: Any, depth: int = 0) -> int:
            if depth > MAX_CONTEXT_DEPTH:
                raise ValueError(f"Context nesting depth exceeds maximum of {MAX_CONTEXT_DEPTH}")
            if isinstance(obj, dict):
                if not obj:
                    return depth
                return max(check_depth(val, depth + 1) for val in obj.values())
            elif isinstance(obj, list):
                if not obj:
                    return depth
                return max(check_depth(item, depth + 1) for item in obj)
            return depth

        check_depth(v)

        try:
            serialized = json.dumps(v)
            if len(serialized) > MAX_CONTEXT_SIZE:
                raise ValueError(f"Context size exceeds maximum of {MAX_CONTEXT_SIZE // 1024}KB")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Context must be JSON-serializable: {e}")

        return v


class ChatMessage(BaseModel):
    """Request model for chat messages."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MESSAGE_LENGTH,
        description="Message to send to the agent",
        examples=["What are the current project priorities?"],
    )
    agent: str = Field(
        default="Nexus",
        description="Agent code to chat with",
        examples=["Nexus", "Forge", "Keystone"],
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Conversation ID for multi-turn chat continuity",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty or whitespace only")
        return v

    @field_validator("agent")
    @classmethod
    def validate_executive(cls, v: str) -> str:
        resolved = AGENT_REGISTRY.resolve(v.strip())
        if not resolved:
            raise ValueError(f"Agent must be one of: {', '.join(sorted(CANONICAL_AGENTS))}")
        return resolved

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith("conv_"):
            raise ValueError("conversation_id must start with 'conv_'")
        return v


class WorkflowExecute(BaseModel):
    """Request model for executing workflows."""

    workflow_name: str = Field(
        ...,
        min_length=1,
        max_length=MAX_WORKFLOW_NAME_LENGTH,
        description="Name of the workflow to execute",
        examples=["product_launch", "incident_response"],
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the workflow",
    )

    @field_validator("workflow_name")
    @classmethod
    def validate_workflow_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Workflow name cannot be empty")
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "Workflow name must start with a letter and contain only "
                "letters, numbers, underscores, and hyphens"
            )
        return v

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        import json

        try:
            serialized = json.dumps(v)
            if len(serialized) > MAX_CONTEXT_SIZE:
                raise ValueError(f"Params size exceeds maximum of {MAX_CONTEXT_SIZE // 1024}KB")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Params must be JSON-serializable: {e}")

        return v


# ============================================================
# Response Models
# ============================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    llm_connected: bool
    coo_ready: bool
    timestamp: str


class ExecutiveInfo(BaseModel):
    """Information about an agent."""

    code: str
    codename: str
    available: bool


class ExecutivesResponse(BaseModel):
    """Response for listing agents."""

    agents: List[ExecutiveInfo]
    count: int


class TaskResponse(BaseModel):
    """Response for task operations."""

    id: str
    description: str
    task_type: str
    priority: str
    status: str
    context: Dict[str, Any]
    result: Optional[Any] = None
    routed_to: Optional[str] = None
    created_at: str


class TasksResponse(BaseModel):
    """Response for listing tasks."""

    tasks: List[TaskResponse]
    count: int


# ============================================================
# Goal Models
# ============================================================

VALID_GOAL_STATUSES = {"active", "completed", "abandoned", "paused"}


class MilestoneCreate(BaseModel):
    """Request model for creating a milestone."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Milestone title",
    )


class GoalCreate(BaseModel):
    """Request model for creating a goal."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Goal title",
        examples=["Increase monthly revenue by 20%"],
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Goal description",
    )
    milestones: List[MilestoneCreate] = Field(
        default_factory=list,
        description="Initial milestones",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty or whitespace only")
        return v


class GoalUpdate(BaseModel):
    """Request model for updating a goal."""

    title: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[str] = Field(default=None)
    progress: Optional[float] = Field(default=None, ge=0, le=100)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_GOAL_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(sorted(VALID_GOAL_STATUSES))}")
        return v


class MilestoneResponse(BaseModel):
    """Response model for a milestone."""

    id: str
    title: str
    status: str


class GoalResponse(BaseModel):
    """Response model for a goal."""

    id: str
    title: str
    description: Optional[str]
    status: str
    progress: float
    milestones: List[MilestoneResponse]
    created_at: str


class GoalsResponse(BaseModel):
    """Response for listing goals."""

    goals: List[GoalResponse]
    count: int


# ============================================================
# Memory/Search Models
# ============================================================


class SearchResult(BaseModel):
    """A single search result."""

    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class MemorySearchResponse(BaseModel):
    """Response for memory search."""

    results: List[SearchResult]
    query: str
    count: int


# ============================================================
# Nexus Models
# ============================================================

VALID_COO_MODES = {"autonomous", "supervised", "approval", "observe", "paused"}


class COOModeUpdate(BaseModel):
    """Request model for updating Nexus mode."""

    mode: str = Field(
        ...,
        description="Operating mode for the Nexus",
        examples=["supervised", "autonomous", "approval"],
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_COO_MODES:
            raise ValueError(f"Mode must be one of: {', '.join(sorted(VALID_COO_MODES))}")
        return v


class COOStatusResponse(BaseModel):
    """Response for Nexus status."""

    state: str
    mode: str
    codename: str
    total_tasks_executed: int
    uptime_seconds: float = 0
    successful_executions: int = 0
    failed_executions: int = 0
    daily_spend_usd: float = 0
    pending_approvals: int = 0


class SuggestionResponse(BaseModel):
    """Response for Nexus suggestion."""

    suggestion: Optional[Dict[str, Any]] = None
    decision: Optional[Dict[str, Any]] = None
    context_summary: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
