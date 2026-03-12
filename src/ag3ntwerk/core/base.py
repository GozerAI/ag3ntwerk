"""
Base classes for ag3ntwerk agents.

This module provides the foundational abstractions for building
hierarchical AI agent systems with specialized roles.
"""

from abc import ABC, abstractmethod
import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from ag3ntwerk.core.exceptions import (
    AgentUnavailableError,
    AgentCapabilityError,
    TaskExecutionError,
    TaskTimeoutError,
)
from ag3ntwerk.core.identity import normalize_key
from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.core.metrics import record_task_execution, record_agent_task

logger = get_logger(__name__)


class TaskStatus(Enum):
    """Status of a task in the system."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    DELEGATED = "delegated"


class TaskPriority(Enum):
    """Priority levels for tasks."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class Task:
    """Represents a unit of work in the system."""

    description: str
    task_type: str
    priority: TaskPriority = TaskPriority.MEDIUM
    id: str = field(default_factory=lambda: str(uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    parent_task_id: Optional[str] = None
    assigned_to: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            "id": self.id,
            "description": self.description,
            "task_type": self.task_type,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "context": self.context,
            "parent_task_id": self.parent_task_id,
            "assigned_to": self.assigned_to,
            "metadata": self.metadata,
        }


@dataclass
class TaskResult:
    """Result of executing a task."""

    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    completed_at: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)
    subtask_results: List["TaskResult"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "completed_at": self.completed_at.isoformat(),
            "metrics": self.metrics,
            "subtask_results": [r.to_dict() for r in self.subtask_results],
        }


class Agent(ABC):
    """
    Base class for all ag3ntwerk agents.

    Each agent has:
    - A unique code (e.g., "Nexus", "Sentinel", "Forge")
    - A domain of expertise
    - The ability to execute tasks
    - Access to an LLM provider for reasoning
    """

    def __init__(
        self,
        code: str,
        name: str,
        domain: str,
        llm_provider: Optional[Any] = None,
    ):
        self.code = code
        self.name = name
        self.domain = domain
        self.llm_provider = llm_provider
        self._active = True
        self._task_history: deque[TaskResult] = deque(maxlen=1000)
        self.capabilities: List[str] = []

        # Metacognition (optional, attached by MetacognitionService)
        self.personality: Optional[Any] = None  # PersonalityProfile
        self._reflector: Optional[Any] = None  # AgentReflector
        self._heuristic_engine: Optional[Any] = None  # HeuristicEngine

        # Strategic context (propagated from Nexus via Overwatch)
        self._strategic_context: Dict[str, Any] = {}

    def receive_strategic_context(self, context: Dict[str, Any]) -> None:
        """Receive strategic context from Nexus (propagated via Overwatch).

        Args:
            context: Strategic context dictionary with priorities, goals, etc.
        """
        self._strategic_context = context

    def attach_metacognition(self, personality=None, heuristic_engine=None, reflector=None):
        """Attach metacognition components (personality, heuristic engine, reflector)."""
        if personality is not None:
            self.personality = personality
        if heuristic_engine is not None:
            self._heuristic_engine = heuristic_engine
        if reflector is not None:
            self._reflector = reflector

    @property
    def is_active(self) -> bool:
        """Check if agent is active and ready to receive tasks."""
        return self._active

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """
        Execute a task within this agent's domain.

        Args:
            task: The task to execute

        Returns:
            TaskResult with the outcome
        """
        pass

    @abstractmethod
    def can_handle(self, task: Task) -> bool:
        """
        Determine if this agent can handle the given task.

        Args:
            task: The task to evaluate

        Returns:
            True if this agent can handle the task
        """
        pass

    def _build_capability_context(self) -> str:
        """Build a capability and module summary for LLM context."""
        parts = []

        if self.capabilities:
            # Group capabilities for readability (show all, they're short strings)
            parts.append(f"Capabilities: {', '.join(self.capabilities)}")

        # Lazy import to avoid circular dependency
        try:
            from ag3ntwerk.modules import get_modules_for_executive, get_module_info

            module_ids = get_modules_for_executive(self.code)
            if module_ids:
                module_lines = []
                for mid in module_ids:
                    info = get_module_info(mid)
                    if info:
                        ownership = (
                            "primary"
                            if self.code in info.get("primary_owners", [])
                            else "secondary"
                        )
                        module_lines.append(
                            f"  - {info['name']} ({ownership}): {info['description']}"
                        )
                if module_lines:
                    parts.append("Modules:\n" + "\n".join(module_lines))
        except ImportError:
            logger.debug("Module registry not available for capability context")

        return "\n".join(parts)

    async def reason(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Use LLM to reason about a problem.

        If ``_conversation_history`` is present in *context*, delegates to
        :meth:`_reason_multi_turn` which builds a proper multi-turn message
        list and calls ``llm_provider.chat()``.  Otherwise falls back to the
        existing single-shot ``llm_provider.generate()`` path.

        Args:
            prompt: The reasoning prompt
            context: Additional context for reasoning

        Returns:
            The LLM's response
        """
        if not self.llm_provider:
            raise RuntimeError(f"Agent {self.code} has no LLM provider configured")

        # Multi-turn path — trigger when history key is present (even if empty list)
        if context and context.get("_conversation_history") is not None:
            return await self._reason_multi_turn(prompt, context)

        # Single-turn path (unchanged)
        full_prompt = f"[{self.code} - {self.name}]\nDomain: {self.domain}\n"

        # Inject capability and module context
        capability_ctx = self._build_capability_context()
        if capability_ctx:
            full_prompt += f"\n{capability_ctx}\n"

        if self.personality:
            try:
                full_prompt += f"\n{self.personality.to_system_prompt_fragment()}\n"
            except Exception as e:
                logger.debug("Personality injection failed for agent %s: %s", self.code, e)

        # Inject heuristic context into LLM prompts
        if context:
            if context.get("_thoroughness_boost"):
                full_prompt += "\n[HEURISTIC: Be extra thorough. Double-check assumptions.]"
            if context.get("_risk_allowance"):
                full_prompt += "\n[HEURISTIC: Prioritize bold approaches and speed.]"
            if context.get("_collaboration_suggested"):
                full_prompt += "\n[HEURISTIC: Consider consulting other agents.]"

        full_prompt += f"\n{prompt}"
        if context:
            filtered = {k: v for k, v in context.items() if not k.startswith("_")}
            if filtered:
                full_prompt += f"\n\nContext: {filtered}"

        return await self.llm_provider.generate(full_prompt)

    async def _reason_multi_turn(
        self,
        prompt: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Multi-turn reasoning via ``llm_provider.chat(messages)``.

        Builds a message list consisting of:
        1. A system message with identity, capabilities, personality, heuristics
        2. Prior conversation history messages
        3. The current user prompt
        """
        from ag3ntwerk.llm.base import Message

        # --- system message ---
        codename = getattr(self, "codename", None)
        org_ctx = context.get("_organizational_context")

        if codename and org_ctx is not None:
            # Rich framing for chat callers that provide org context
            system_parts = [
                f"You are {codename} — the {self.name} ({self.code}) of ag3ntwerk, "
                "an AI agent team that collaboratively manages strategy, "
                "technology, finance, operations, security, compliance, and more.",
                f"\nYour domain: {self.domain}",
            ]
        else:
            # Lean framing for non-chat callers (backward compatible)
            system_parts = [f"You are {self.name} ({self.code}), domain: {self.domain}."]

        capability_ctx = self._build_capability_context()
        if capability_ctx:
            system_parts.append(f"\n{capability_ctx}")

        if self.personality:
            try:
                system_parts.append(f"\n{self.personality.to_system_prompt_fragment()}")
            except Exception as e:
                logger.debug("Personality injection failed for agent %s: %s", self.code, e)

        # Organizational context sections (only when provided by ChatService)
        if org_ctx:
            system_state = org_ctx.get("system_state")
            if system_state:
                system_parts.append("\nSystem state:")
                for s in system_state:
                    system_parts.append(f"- {s}")

            peers = org_ctx.get("peers")
            if peers:
                system_parts.append("\nYour peer agents:")
                for p in peers:
                    system_parts.append(f"- {p}")

            goals = org_ctx.get("goals")
            if goals:
                system_parts.append("\nCurrent organizational focus:")
                for g in goals:
                    system_parts.append(f"- {g}")

        if context.get("_thoroughness_boost"):
            system_parts.append("\n[HEURISTIC: Be extra thorough. Double-check assumptions.]")
        if context.get("_risk_allowance"):
            system_parts.append("\n[HEURISTIC: Prioritize bold approaches and speed.]")
        if context.get("_collaboration_suggested"):
            system_parts.append("\n[HEURISTIC: Consider consulting other agents.]")

        # Behavioral instruction (only for rich framing)
        if codename and org_ctx is not None:
            system_parts.append(
                "\nRespond conversationally as this agent. Draw on your domain "
                "expertise and reference your capabilities when relevant. If a question "
                "falls outside your domain, suggest which peer agent would be better suited."
            )

        messages = [Message(role="system", content="\n".join(system_parts))]

        # --- history ---
        history = context["_conversation_history"]
        for msg in history:
            messages.append(Message(role=msg["role"], content=msg["content"]))

        # --- current user prompt ---
        messages.append(Message(role="user", content=prompt))

        response = await self.llm_provider.chat(messages)
        # chat() returns an LLMResponse; extract .content
        if hasattr(response, "content"):
            return response.content
        return str(response)

    async def use_tool(self, tool_name: str, timeout: Optional[float] = None, **kwargs) -> Any:
        """Execute a tool via the global executor with plugin dispatch.

        Args:
            tool_name: Name of the registered tool
            timeout: Optional timeout in seconds
            **kwargs: Tool parameters

        Returns:
            ToolResult from the executor
        """
        try:
            from ag3ntwerk.tools.executor import get_executor, ExecutionContext

            executor = get_executor()
            context = ExecutionContext(
                execution_id=executor._generate_execution_id(),
                tool_name=tool_name,
                parameters=kwargs,
                metadata={"agent_code": self.code},
            )
            result = await executor.execute(tool_name, context=context, timeout=timeout, **kwargs)
            return result
        except Exception as e:
            logger.debug("Tool execution failed for agent %s: %s", self.code, e)
            # Return a ToolResult-like dict so callers have a consistent shape
            try:
                from ag3ntwerk.tools.base import ToolResult as TR

                return TR(success=False, error=str(e), error_type=type(e).__name__)
            except ImportError:
                return {"success": False, "error": str(e)}

    def record_result(self, result: TaskResult) -> None:
        """Record a task result in history."""
        self._task_history.append(result)

    def get_history(self, limit: int = 10) -> List[TaskResult]:
        """Get recent task history."""
        history = list(self._task_history)
        return history[-limit:]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} code={self.code} name={self.name}>"


class Manager(Agent):
    """
    A ag3ntwerk agent that manages other agents.

    Managers can delegate tasks to their subordinates and
    coordinate complex workflows across multiple agents.
    """

    def __init__(
        self,
        code: str,
        name: str,
        domain: str,
        llm_provider: Optional[Any] = None,
    ):
        super().__init__(code, name, domain, llm_provider)
        self._subordinates: Dict[str, Agent] = {}
        self._subordinate_lookup: Dict[str, str] = {}  # normalized_key -> canonical_code
        self._metacognition_service: Optional[Any] = None  # Set by connect_metacognition()
        self._learning_orchestrator: Optional[Any] = None  # Set by connect_learning_orchestrator()
        self._capability_registry: Optional[Any] = None  # Set externally

    async def execute(self, task: Task) -> TaskResult:
        """
        Execute a task by finding the best subordinate and delegating.

        Args:
            task: The task to execute

        Returns:
            TaskResult from the subordinate, or error if none found
        """
        best_code = await self.find_best_agent(task)
        if best_code is None:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=(
                    f"Manager {self.code} has no subordinate capable of "
                    f"handling task type '{task.task_type}'"
                ),
            )
        return await self.delegate(task, best_code)

    def can_handle(self, task: Task) -> bool:
        """
        Check if any subordinate can handle the task.

        Args:
            task: The task to evaluate

        Returns:
            True if at least one active subordinate can handle the task
        """
        return any(
            agent.can_handle(task) and agent.is_active for agent in self._subordinates.values()
        )

    def connect_metacognition_service(self, service) -> None:
        """Connect a metacognition service to this manager."""
        self._metacognition_service = service

    def connect_learning_orchestrator(self, orchestrator) -> None:
        """Connect a learning orchestrator to this manager for delegation recording."""
        self._learning_orchestrator = orchestrator

    async def request_from_peer(self, capability: str, **params) -> Dict[str, Any]:
        """Request work from a peer agent via the capability registry.

        Args:
            capability: Capability string to request
            **params: Parameters for the request

        Returns:
            Result dict from the capability provider, or error dict
        """
        if not self._capability_registry:
            return {"error": "No capability registry connected"}
        try:
            return await self._capability_registry.request(capability, params)
        except Exception as e:
            logger.debug("Peer request failed for %s: %s", capability, e)
            return {"error": str(e)}

    def register_subordinate(self, agent: Agent) -> None:
        """Register an agent as a subordinate."""
        self._subordinates[agent.code] = agent
        self._subordinate_lookup[normalize_key(agent.code)] = agent.code

    def unregister_subordinate(self, agent_code: str) -> None:
        """Remove a subordinate agent."""
        canonical = self._subordinate_lookup.pop(normalize_key(agent_code), None)
        if canonical:
            self._subordinates.pop(canonical, None)

    def get_subordinate(self, agent_code: str) -> Optional[Agent]:
        """Get a subordinate by code (case-insensitive)."""
        # First try direct lookup
        if agent_code in self._subordinates:
            return self._subordinates[agent_code]
        # Then try normalized lookup
        canonical = self._subordinate_lookup.get(normalize_key(agent_code))
        if canonical:
            return self._subordinates.get(canonical)
        return None

    @property
    def subordinates(self) -> List[Agent]:
        """List all subordinate agents."""
        return list(self._subordinates.values())

    def _build_heuristic_context(self, task: Task) -> Dict[str, Any]:
        """
        Compute heuristic context from task history for the heuristic engine.

        Returns dict with consecutive_failures, recent_success_rate, task_complexity.
        """
        recent = list(self._task_history)[-20:]
        consecutive_failures = 0
        for r in reversed(recent):
            if not r.success:
                consecutive_failures += 1
            else:
                break

        success_count = sum(1 for r in recent if r.success)
        recent_success_rate = success_count / len(recent) if recent else 0.5

        # Estimate task complexity from context
        task_complexity = 0.0
        if task.context:
            task_complexity = task.context.get("complexity", 0.0)
        if task.priority.value <= 2:  # CRITICAL or HIGH
            task_complexity = max(task_complexity, 0.5)

        return {
            "consecutive_failures": consecutive_failures,
            "recent_success_rate": recent_success_rate,
            "task_complexity": task_complexity,
        }

    def _apply_heuristic_actions(self, task: Task) -> List:
        """
        Evaluate heuristic engine for context-aware actions and apply them
        as prompt-level modifications to the task context.

        Returns list of HeuristicAction objects that fired.
        """
        if not self._heuristic_engine:
            return []

        heuristic_context = self._build_heuristic_context(task)
        actions = self._heuristic_engine.evaluate(task=task, context=heuristic_context)

        if not actions:
            return []

        task.context = task.context or {}
        action_keys = [a.action for a in actions]
        task.context["_heuristic_actions"] = action_keys

        # Set flags based on fired actions
        for action in actions:
            if action.action == "increase_thoroughness":
                task.context["_thoroughness_boost"] = True
            elif action.action == "allow_higher_risk":
                task.context["_risk_allowance"] = True
            elif action.action == "request_collaboration":
                task.context["_collaboration_suggested"] = True

            # Merge any context modifications from the heuristic
            if action.context_modifications:
                task.context.update(action.context_modifications)

        return actions

    def _record_heuristic_outcomes(self, actions: List, success: bool) -> None:
        """
        Feed success/failure back to the heuristic engine for each fired action.
        """
        if not self._heuristic_engine:
            return

        for action in actions:
            self._heuristic_engine.record_outcome(action.heuristic_id, success)

    async def delegate(self, task: Task, agent_code: str) -> TaskResult:
        """
        Delegate a task to a subordinate agent (case-insensitive).

        Args:
            task: The task to delegate
            agent_code: The code of the subordinate to delegate to

        Returns:
            TaskResult from the subordinate
        """
        # Resolve to canonical code
        canonical = self._subordinate_lookup.get(normalize_key(agent_code))
        agent = self._subordinates.get(canonical) if canonical else None
        if not agent:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"No subordinate with code {agent_code}",
            )

        if not agent.can_handle(task):
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Agent {agent_code} cannot handle task type {task.task_type}",
            )

        task.status = TaskStatus.DELEGATED
        task.assigned_to = agent_code

        # Apply heuristic actions before delegation
        fired_actions = self._apply_heuristic_actions(task)

        # Dispatch plugin pre-delegation event
        try:
            from ag3ntwerk.core.plugins import dispatch_plugin_event

            pre_results = await dispatch_plugin_event(
                "delegation.pre_execute",
                {
                    "task": task.description if hasattr(task, "description") else str(task),
                    "task_type": task.task_type,
                    "target": agent_code,
                    "agent_code": self.code,
                },
            )
            for r in pre_results or []:
                if isinstance(r, dict) and r.get("blocked"):
                    return TaskResult(
                        task_id=task.id,
                        success=False,
                        error=r.get("reason", "Blocked by plugin"),
                    )
        except Exception as e:
            logger.debug(f"Plugin pre-delegation dispatch failed: {e}")

        start_time = datetime.now()
        result = await agent.execute(task)

        # Record heuristic outcomes after delegation
        if fired_actions:
            self._record_heuristic_outcomes(fired_actions, result.success)

        # Record internal delegation outcome to metacognition
        self._record_delegation_to_metacognition(agent_code, task, result, start_time)

        # Record delegation outcome to learning system
        await self._record_delegation_to_learning(task, result, start_time)

        # Dispatch plugin post-delegation event
        try:
            from ag3ntwerk.core.plugins import dispatch_plugin_event

            await dispatch_plugin_event(
                "delegation.post_execute",
                {
                    "task": task.description if hasattr(task, "description") else str(task),
                    "task_type": task.task_type,
                    "target": agent_code,
                    "agent_code": self.code,
                    "success": result.success,
                },
            )
        except Exception as e:
            logger.debug(f"Plugin post-delegation dispatch failed: {e}")

        return result

    def _record_delegation_to_metacognition(
        self,
        delegate_code: str,
        task: Task,
        result: TaskResult,
        start_time: datetime,
    ) -> None:
        """Record delegation outcome to metacognition (best-effort, no-op without service)."""
        if not self._metacognition_service:
            return
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        try:
            self._metacognition_service.on_task_completed(
                agent_code=delegate_code,
                task_id=task.id,
                task_type=task.task_type,
                success=result.success,
                duration_ms=duration_ms,
                error=result.error,
            )
        except Exception as e:
            logger.debug(
                "Metacognition task-completion recording failed",
                agent=delegate_code,
                error=str(e),
                error_type=type(e).__name__,
            )

    async def _record_delegation_to_learning(
        self,
        task: Task,
        result: TaskResult,
        start_time: datetime,
    ) -> None:
        """Record delegation outcome to learning system (best-effort, no-op without orchestrator)."""
        if not self._learning_orchestrator:
            return
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        try:
            from ag3ntwerk.learning.models import HierarchyPath

            hierarchy_path = HierarchyPath(
                agent=self.code,
                manager=task.assigned_to,
                specialist=None,
            )
            await self._learning_orchestrator.record_outcome(
                task_id=task.id,
                task_type=task.task_type,
                hierarchy_path=hierarchy_path,
                success=result.success,
                duration_ms=duration_ms,
                error=result.error,
            )
        except Exception as e:
            logger.debug(
                "Learning outcome recording failed",
                agent=self.code,
                error=str(e),
                error_type=type(e).__name__,
            )

    async def delegate_with_retry(
        self,
        task: Task,
        agent_code: str,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        timeout_seconds: Optional[float] = None,
    ) -> TaskResult:
        """
        Delegate a task with exponential backoff retry.

        Args:
            task: The task to delegate
            agent_code: The code of the subordinate to delegate to
            max_retries: Maximum number of retry attempts
            backoff_factor: Multiplier for exponential backoff
            timeout_seconds: Optional timeout for each attempt

        Returns:
            TaskResult from the subordinate

        Raises:
            AgentUnavailableError: If agent is not found after retries
            AgentCapabilityError: If agent cannot handle the task type
            TaskTimeoutError: If all attempts timeout
            TaskExecutionError: If execution fails after all retries
        """
        # Resolve to canonical code
        canonical = self._subordinate_lookup.get(normalize_key(agent_code))
        agent = self._subordinates.get(canonical) if canonical else None
        if not agent:
            raise AgentUnavailableError(agent_code, "not registered as subordinate")

        if not agent.can_handle(task):
            raise AgentCapabilityError(agent_code, task.task_type)

        task.status = TaskStatus.DELEGATED
        task.assigned_to = agent_code

        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                logger.debug(
                    "Delegating task",
                    task_id=task.id,
                    agent=agent_code,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )

                if timeout_seconds:
                    result = await asyncio.wait_for(
                        agent.execute(task),
                        timeout=timeout_seconds,
                    )
                else:
                    result = await agent.execute(task)

                if result.success:
                    return result

                # Task completed but failed - check if recoverable
                if attempt < max_retries - 1:
                    wait_time = backoff_factor**attempt
                    logger.warning(
                        "Task failed, retrying",
                        task_id=task.id,
                        agent=agent_code,
                        wait_seconds=round(wait_time, 1),
                        error=result.error,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(wait_time)
                    last_error = TaskExecutionError(
                        task.id, agent_code, result.error or "Unknown error"
                    )
                else:
                    return result

            except asyncio.TimeoutError:
                last_error = TaskTimeoutError(task.id, agent_code, timeout_seconds or 0)
                if attempt < max_retries - 1:
                    wait_time = backoff_factor**attempt
                    logger.warning(
                        "Task timed out, retrying",
                        task_id=task.id,
                        agent=agent_code,
                        wait_seconds=round(wait_time, 1),
                        timeout_seconds=timeout_seconds,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise last_error

            except Exception as e:  # Intentional catch-all: generic retry for any execution error
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = backoff_factor**attempt
                    logger.warning(
                        "Task execution error, retrying",
                        task_id=task.id,
                        agent=agent_code,
                        wait_seconds=round(wait_time, 1),
                        error=str(e),
                        error_type=type(e).__name__,
                        attempt=attempt + 1,
                        exc_info=True,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise TaskExecutionError(
                        task.id, agent_code, str(e), recoverable=False, cause=e
                    )

        # Should not reach here, but handle edge case
        if last_error:
            raise last_error
        return TaskResult(
            task_id=task.id,
            success=False,
            error="Delegation failed after all retries",
        )

    async def find_best_agent(self, task: Task) -> Optional[str]:
        """
        Find the best subordinate to handle a task.

        Args:
            task: The task to assign

        Returns:
            Agent code of the best match, or None
        """
        capable_agents = [
            agent
            for agent in self._subordinates.values()
            if agent.can_handle(task) and agent.is_active
        ]

        if not capable_agents:
            return None

        # Use LLM to pick the best agent if multiple can handle it
        if len(capable_agents) == 1:
            return capable_agents[0].code

        if self.llm_provider:
            agent_descriptions = "\n".join(
                [f"- {a.code}: {a.name} - {a.domain}" for a in capable_agents]
            )

            prompt = f"""Given this task: {task.description}

Which agent should handle it? Available agents:
{agent_descriptions}

Respond with just the agent code (e.g., Sentinel, Forge)."""

            response = await self.reason(prompt)
            chosen_raw = (response or "").strip()

            # Resolve to canonical code case-insensitively
            canonical = self._subordinate_lookup.get(normalize_key(chosen_raw))
            if canonical and canonical in self._subordinates:
                return canonical

        # Fallback: return first capable agent
        return capable_agents[0].code

    async def execute_with_learning(
        self,
        task: Task,
        initial_confidence: Optional[float] = None,
        learning_context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """
        Execute a task with learning system integration.

        This wrapper method:
        - Records initial confidence before execution
        - Passes learning context and hints to the execution
        - Annotates the result with metrics for the learning system

        Args:
            task: The task to execute
            initial_confidence: Optional confidence estimate (0.0-1.0) before execution
            learning_context: Optional additional context from learning system

        Returns:
            TaskResult with learning-related metrics populated
        """
        start_time = datetime.now()

        # Merge learning context into task context
        if learning_context:
            task.context = task.context or {}
            task.context["learning_context"] = learning_context

        # Store initial confidence in task context
        if initial_confidence is not None:
            task.context = task.context or {}
            task.context["initial_confidence"] = initial_confidence

        try:
            # Execute the task
            result = await self.execute(task)

            # Calculate duration
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Ensure metrics dict exists
            if result.metrics is None:
                result.metrics = {}

            # Add learning-related metrics
            result.metrics["duration_ms"] = duration_ms
            result.metrics["manager_code"] = self.code

            if initial_confidence is not None:
                result.metrics["initial_confidence"] = initial_confidence

            # Try to extract effectiveness from result if not already set
            if "effectiveness" not in result.metrics and result.success:
                # Default effectiveness based on success
                result.metrics["effectiveness"] = 1.0 if result.success else 0.0

            # Record task metrics
            try:
                record_task_execution(
                    task_type=task.task_type,
                    agent=self.code,
                    duration_ms=duration_ms,
                    success=result.success,
                )
                record_agent_task(self.code)
            except Exception:  # Metrics recording must never break execution
                pass

            return result

        except Exception as e:  # Intentional catch-all: convert any failure to TaskResult
            # Calculate duration even on failure
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Record task metrics for failures too
            try:
                record_task_execution(
                    task_type=task.task_type,
                    agent=self.code,
                    duration_ms=duration_ms,
                    success=False,
                )
                record_agent_task(self.code)
            except Exception:  # Metrics recording must never break execution
                pass

            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                metrics={
                    "duration_ms": duration_ms,
                    "manager_code": self.code,
                    "initial_confidence": initial_confidence,
                    "effectiveness": 0.0,
                },
            )

    def estimate_confidence(self, task: Task) -> float:
        """
        Estimate confidence for handling a task.

        Override this method in subclasses to provide more accurate
        confidence estimates based on agent-specific factors.

        Args:
            task: The task to estimate confidence for

        Returns:
            Confidence value between 0.0 and 1.0
        """
        # Default: base confidence on task history
        if not self._task_history:
            return 0.5  # Unknown - neutral confidence

        # Calculate recent success rate for this task type
        recent = list(self._task_history)[-20:]
        relevant_history = [
            r for r in recent if r.metrics and r.metrics.get("task_type") == task.task_type
        ]

        if not relevant_history:
            return 0.5

        success_rate = sum(1 for r in relevant_history if r.success) / len(relevant_history)
        return success_rate


class Specialist(Agent):
    """
    A ag3ntwerk agent that specializes in specific tasks.

    Specialists are the workers that perform actual operations.
    They typically don't have subordinates and focus on execution.
    """

    def __init__(
        self,
        code: str,
        name: str,
        domain: str,
        capabilities: List[str],
        llm_provider: Optional[Any] = None,
    ):
        super().__init__(code, name, domain, llm_provider)
        self.capabilities = capabilities

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist can handle the task based on capabilities."""
        return task.task_type in self.capabilities

    def add_capability(self, capability: str) -> None:
        """Add a new capability."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)

    def remove_capability(self, capability: str) -> None:
        """Remove a capability."""
        if capability in self.capabilities:
            self.capabilities.remove(capability)
