"""
Business-logic services extracted from route handlers.

Each service encapsulates the domain logic for a group of related
API endpoints, keeping the route handlers thin.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from ag3ntwerk.core.logging import get_logger

logger = get_logger(__name__)


class TaskService:
    """Handles task creation and execution via the Nexus."""

    def __init__(self, state):
        self._state = state

    async def create_and_execute(
        self,
        description: str,
        task_type: str,
        priority: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a task and optionally execute it via the Nexus."""
        new_task = self._state.create_task(
            description=description,
            task_type=task_type,
            priority=priority,
            context=context,
        )
        await self._state.broadcast("task_created", new_task)

        if self._state.coo and self._state.llm_provider:
            await self._execute_via_coo(new_task, description, task_type, priority, context)

        return new_task

    async def _execute_via_coo(
        self,
        task_dict: Dict[str, Any],
        description: str,
        task_type: str,
        priority: str,
        context: Dict[str, Any],
    ):
        from ag3ntwerk.core.base import Task as AgentTask, TaskPriority

        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL,
        }

        try:
            agent_task = AgentTask(
                description=description,
                task_type=task_type,
                priority=priority_map.get(priority.lower(), TaskPriority.MEDIUM),
                context=context,
            )

            task_dict["status"] = "running"
            await self._state.broadcast("task_updated", task_dict)

            result = await self._state.coo.execute(agent_task)

            task_dict["status"] = "completed" if result.success else "failed"
            output = result.output
            if isinstance(output, dict) and "content" in output:
                task_dict["result"] = output["content"]
            else:
                task_dict["result"] = str(output) if output else "Task completed"
            await self._state.broadcast("task_completed", task_dict)

        except Exception as e:
            logger.error(
                "Task execution failed",
                task_id=task_dict["id"],
                task_type=task_type,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            task_dict["status"] = "failed"
            task_dict["result"] = "Task execution failed. Check server logs for details."


class ChatService:
    """Handles chat interactions with agents."""

    def __init__(self, state):
        self._state = state
        self._conversation_store: Optional[Any] = None

    async def _get_store(self):
        if self._conversation_store is None:
            from ag3ntwerk.api.conversation_store import ConversationStore

            self._conversation_store = ConversationStore()
        return self._conversation_store

    async def chat(
        self,
        message: str,
        agent_code: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message to an agent and return the response."""
        if not self._state.llm_provider:
            return {"content": "LLM not connected. Please ensure Ollama is running.", "error": True}

        try:
            store = await self._get_store()

            # Create or load conversation
            if conversation_id:
                conv = await store.get(conversation_id)
                if conv is None:
                    conversation_id = await store.create(agent_code.upper())
            else:
                conversation_id = await store.create(agent_code.upper())

            # Save user message
            await store.add_message(conversation_id, "user", message)

            # Load windowed history (exclude the message we just added)
            recent = await store.get_recent_messages(conversation_id, limit=21)
            # Drop the last entry (our just-saved user message) so the
            # current prompt is passed separately via task.description.
            history = recent[:-1] if recent else []

            agent = (
                self._state.registry.get(agent_code.upper()) if self._state.registry else None
            )
            if not agent:
                llm_resp = await self._state.llm_provider.generate(prompt=message)
                content = llm_resp.content
                await store.add_message(conversation_id, "assistant", content)
                return {
                    "content": content,
                    "agent": "LLM",
                    "conversation_id": conversation_id,
                }

            from ag3ntwerk.core.base import Task as AgentTask, TaskPriority

            context: Dict[str, Any] = {}
            context["_conversation_history"] = history

            context["_organizational_context"] = self._build_org_context(agent_code.upper())

            task = AgentTask(
                description=message,
                task_type="chat",
                priority=TaskPriority.MEDIUM,
                context=context,
            )
            result = await agent.execute(task)

            # Extract string content from the output
            output = result.output
            if hasattr(output, "content"):
                content = output.content
            elif isinstance(output, dict) and "content" in output:
                content = output["content"]
            elif isinstance(output, str):
                content = output
            else:
                content = str(output) if output else "No response generated."

            # Save assistant response
            await store.add_message(conversation_id, "assistant", content)

            return {
                "content": content,
                "agent": agent_code.upper(),
                "success": result.success,
                "conversation_id": conversation_id,
            }

        except Exception as e:
            logger.error(
                "Chat endpoint error",
                agent=agent_code.upper(),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return {"content": "An error occurred processing your request.", "error": True}

    def _build_org_context(self, agent_code: str) -> Dict[str, Any]:
        """Build organizational context (peers, goals, system state) for LLM system prompt."""
        result: Dict[str, Any] = {}

        # Peer agents from registry
        registry = self._state.registry if self._state else None
        if registry:
            try:
                from ag3ntwerk.orchestration.registry import STANDARD_AGENTS

                peers = []
                for codename, (_, _) in STANDARD_AGENTS.items():
                    if codename == agent_code:
                        continue
                    agent = registry.get(codename)
                    domain = agent.domain if agent else "unknown"
                    peers.append(f"{codename}: {domain}")
                result["peers"] = peers
            except Exception as e:
                logger.debug("Failed to build peer list: %s", e)

        # Active goals (capped at 6)
        try:
            goals = self._state.list_goals()
            active = [g for g in goals if g.get("status") == "active"][:6]
            if active:
                goal_lines = []
                for g in active:
                    progress = g.get("progress", 0)
                    goal_lines.append(f"{g['title']} ({progress}%)")
                result["goals"] = goal_lines
        except Exception as e:
            logger.debug("Failed to build goals list: %s", e)

        # System state snapshot
        state_lines = []
        try:
            llm = self._state.llm_provider
            if llm:
                model = getattr(llm, "default_model", None) or "unknown"
                provider = getattr(llm, "name", None) or "unknown"
                state_lines.append(f"LLM: {provider} ({model})")
            else:
                state_lines.append("LLM: not connected")

            tasks = self._state.list_tasks()
            if tasks:
                completed = sum(1 for t in tasks if t["status"] == "completed")
                pending = sum(1 for t in tasks if t["status"] == "pending")
                failed = sum(1 for t in tasks if t["status"] == "failed")
                state_lines.append(
                    f"Tasks: {len(tasks)} total ({completed} completed, "
                    f"{pending} pending, {failed} failed)"
                )

            # Active modules
            try:
                from ag3ntwerk.modules import MODULE_REGISTRY

                module_names = [MODULE_REGISTRY[mid]["name"] for mid in MODULE_REGISTRY]
                state_lines.append(f"Modules: {', '.join(module_names)}")
            except Exception:
                pass

            # Connected services
            services = []
            if self._state.coo:
                services.append("Overwatch (Overwatch)")
            if getattr(self._state, "database", None):
                services.append("Database")
            if getattr(self._state, "task_queue", None):
                services.append("Task Queue")
            if getattr(self._state, "agenda_engine", None):
                services.append("Agenda Engine")
            if getattr(self._state, "ollama_manager", None):
                services.append("Ollama Manager")
            if services:
                state_lines.append(f"Services: {', '.join(services)}")

            coo_mode = getattr(self._state, "_coo_mode", None)
            if coo_mode:
                state_lines.append(f"Operating mode: {coo_mode}")

        except Exception as e:
            logger.debug("Failed to build system state: %s", e)

        if state_lines:
            result["system_state"] = state_lines

        return result

    async def list_conversations(self, limit: int = 50) -> Dict[str, Any]:
        """List recent conversations."""
        store = await self._get_store()
        conversations = await store.list_conversations(limit=limit)
        return {"conversations": conversations, "count": len(conversations)}

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a full conversation with messages."""
        store = await self._get_store()
        return await store.get(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        store = await self._get_store()
        return await store.delete(conversation_id)


class WorkflowService:
    """Handles workflow execution and history."""

    def __init__(self, state, *, is_production: bool = False):
        self._state = state
        self._is_production = is_production

    async def execute(self, workflow_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow and broadcast lifecycle events."""
        await self._state.broadcast(
            "workflow_started",
            {
                "workflow_name": workflow_name,
                "params": params,
                "timestamp": datetime.now().isoformat(),
            },
        )

        try:
            result = await self._state.orchestrator.execute(workflow_name, **params)

            self._state._workflow_executions[result.workflow_id] = result.to_dict()

            await self._state.broadcast(
                "workflow_completed",
                {
                    "workflow_id": result.workflow_id,
                    "workflow_name": workflow_name,
                    "status": result.status.value,
                    "success": result.success,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return result.to_dict()

        except Exception as e:
            logger.error(
                "Workflow execution failed",
                workflow_name=workflow_name,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            await self._state.broadcast(
                "workflow_failed",
                {
                    "workflow_name": workflow_name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
            )
            if self._is_production:
                detail = "Workflow execution failed. Check server logs for details."
            else:
                detail = f"Workflow execution failed: {e}"
            from fastapi import HTTPException

            raise HTTPException(status_code=500, detail=detail)


class GoalService:
    """Handles goal creation, updates, and milestone management."""

    def __init__(self, state):
        self._state = state

    async def list_goals(self) -> Dict[str, Any]:
        """List all goals."""
        goals = self._state.list_goals()
        return {"goals": goals, "count": len(goals)}

    async def create_goal(
        self, title: str, description: Optional[str], milestones: list
    ) -> Dict[str, Any]:
        """Create a new goal."""
        milestone_dicts = [{"title": m.title} for m in milestones] if milestones else []
        goal = self._state.create_goal(
            title=title,
            description=description,
            milestones=milestone_dicts,
        )
        await self._state.broadcast("goal_created", goal)
        return goal

    async def update_goal(self, goal_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a goal."""
        goal = self._state.update_goal(goal_id, updates)
        if not goal:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")
        await self._state.broadcast("goal_updated", goal)
        return goal

    async def add_milestone(self, goal_id: str, title: str) -> Dict[str, Any]:
        """Add a milestone to a goal."""
        milestone = self._state.add_milestone(goal_id, title)
        if not milestone:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")
        goal = self._state.get_goal(goal_id)
        await self._state.broadcast("milestone_added", {"goal_id": goal_id, "milestone": milestone})
        return {"milestone": milestone, "goal": goal}

    async def update_milestone(
        self, goal_id: str, milestone_id: str, status: str
    ) -> Dict[str, Any]:
        """Update a milestone status."""
        milestone = self._state.update_milestone(goal_id, milestone_id, status)
        if not milestone:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail=f"Milestone not found: {milestone_id}")
        goal = self._state.get_goal(goal_id)
        await self._state.broadcast(
            "milestone_updated", {"goal_id": goal_id, "milestone": milestone}
        )
        return {"milestone": milestone, "goal": goal}


class MemoryService:
    """Handles memory search and knowledge base operations."""

    def __init__(self, state):
        self._state = state

    async def search(
        self, query: str, n_results: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search the memory/knowledge base."""
        # In a full implementation, this would use the vector store
        # For now, return empty results to allow the UI to function
        results = []

        # Try to use the integrated memory system if available
        if self._state.coo and hasattr(self._state.coo, "memory"):
            try:
                memory = self._state.coo.memory
                if hasattr(memory, "search"):
                    raw_results = await memory.search(query, n_results=n_results)
                    for item in raw_results:
                        results.append(
                            {
                                "content": item.get("content", str(item)),
                                "score": item.get("score", 0.5),
                                "metadata": item.get("metadata", {}),
                            }
                        )
            except Exception as e:
                logger.warning("Memory search failed", error=str(e))

        return {
            "results": results,
            "query": query,
            "count": len(results),
        }

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory/knowledge statistics."""
        # Return basic stats - in full implementation, query actual stores
        return {
            "memory": {"total_chunks": 0},
            "knowledge": {"total_entities": 0, "total_facts": 0},
            "decisions": {"total": 0},
        }


class COOService:
    """Handles Nexus autonomous operations, suggestions, and mode management."""

    def __init__(self, state):
        self._state = state

    async def get_status(self) -> Dict[str, Any]:
        """Get detailed Nexus status."""
        from datetime import datetime as dt

        tasks = self._state.list_tasks()
        completed_tasks = len([t for t in tasks if t["status"] == "completed"])
        failed_tasks = len([t for t in tasks if t["status"] == "failed"])

        uptime = 0.0
        if self._state._coo_start_time:
            uptime = (dt.now() - self._state._coo_start_time).total_seconds()

        return {
            "state": "running" if self._state.coo else "not_available",
            "mode": self._state._coo_mode,
            "codename": "Nexus",
            "total_tasks_executed": completed_tasks + failed_tasks,
            "uptime_seconds": uptime,
            "successful_executions": completed_tasks,
            "failed_executions": failed_tasks,
            "daily_spend_usd": 0.0,  # Would be tracked in production
            "pending_approvals": 0,
        }

    async def set_mode(self, mode: str) -> Dict[str, Any]:
        """Set the Nexus operating mode."""
        self._state._coo_mode = mode
        await self._state.broadcast("coo_mode_changed", {"mode": mode})
        return {"success": True, "mode": mode}

    async def get_suggestions(self) -> Dict[str, Any]:
        """Get the next suggested action from Nexus.

        Uses the Autonomous Agenda Engine if connected, otherwise falls back
        to simple pending task suggestions.
        """
        if not self._state.coo:
            return {
                "suggestion": None,
                "reason": "Nexus is not running. Start the Nexus to receive suggestions.",
            }

        # Check if agenda engine is available
        if self._state.coo.is_agenda_enabled():
            return await self._get_agenda_suggestions()

        # Fallback to legacy suggestion system
        return await self._get_legacy_suggestions()

    async def _get_agenda_suggestions(self) -> Dict[str, Any]:
        """Get suggestions from the Autonomous Agenda Engine."""
        goals = self._state.list_goals()
        tasks = self._state.list_tasks()
        pending_tasks = [t for t in tasks if t["status"] == "pending"]

        # Get agenda status
        agenda_status = await self._state.coo.get_agenda_status()

        context_summary = {
            "active_goals": len([g for g in goals if g["status"] == "active"]),
            "pending_tasks": len(pending_tasks),
            "blockers": agenda_status.get("active_obstacles", 0),
            "agenda_enabled": True,
            "total_workstreams": agenda_status.get("total_workstreams", 0),
            "pending_approvals": (
                len(self._state.coo.checkpoint_manager.get_pending_checkpoints())
                if hasattr(self._state.coo, "checkpoint_manager")
                else 0
            ),
        }

        # Get next agenda items
        agenda_items = await self._state.coo.get_agenda_items(count=5)

        if not agenda_items:
            # No agenda items - try to generate agenda if we have goals
            if goals:
                active_goals = [g for g in goals if g["status"] == "active"]
                if active_goals:
                    return {
                        "suggestion": {
                            "id": "generate_agenda",
                            "item": {
                                "id": "generate_agenda",
                                "title": "Generate Autonomous Agenda",
                                "type": "agenda_generation",
                            },
                            "action": "generate_agenda",
                        },
                        "decision": {
                            "executor": "Nexus",
                            "confidence": 0.9,
                            "reason": f"You have {len(active_goals)} active goal(s) but no agenda. Generate an agenda to get started.",
                        },
                        "context_summary": context_summary,
                    }

            return {
                "suggestion": None,
                "context_summary": context_summary,
                "reason": "No agenda items available. Create goals and generate an agenda to get started.",
            }

        # Return the highest priority agenda item
        item = agenda_items[0]

        # Format suggestion based on approval status
        action = "execute" if item["approval_status"] != "pending" else "approve"

        return {
            "suggestion": {
                "id": item["id"],
                "item": {
                    "id": item["id"],
                    "title": item["title"],
                    "type": item["task_type"],
                    "description": item.get("description", ""),
                },
                "action": action,
                "requires_approval": item["requires_approval"],
                "is_obstacle_resolution": item.get("is_obstacle_resolution", False),
                "risk_level": item.get("risk_level"),
            },
            "decision": {
                "executor": item["recommended_agent"],
                "confidence": item["priority_score"],
                "confidence_level": item["confidence_level"],
                "reason": f"Agenda item: {item['title'][:80]}",
            },
            "context_summary": context_summary,
            "agenda_items_available": len(agenda_items),
        }

    async def _get_legacy_suggestions(self) -> Dict[str, Any]:
        """Legacy suggestion system when agenda engine is not available."""
        goals = self._state.list_goals()
        tasks = self._state.list_tasks()
        pending_tasks = [t for t in tasks if t["status"] == "pending"]

        context_summary = {
            "active_goals": len([g for g in goals if g["status"] == "active"]),
            "pending_tasks": len(pending_tasks),
            "blockers": 0,
            "agenda_enabled": False,
        }

        if not pending_tasks and not goals:
            return {
                "suggestion": None,
                "context_summary": context_summary,
                "reason": "No pending tasks or goals. Create a goal or task to get started.",
            }

        # Return the first pending task as a suggestion
        if pending_tasks:
            task = pending_tasks[0]
            return {
                "suggestion": {
                    "id": task["id"],  # Include ID at suggestion level for frontend
                    "item": {
                        "id": task["id"],
                        "title": task["description"],
                        "type": task["task_type"],
                    },
                    "action": "execute",
                },
                "decision": {
                    "executor": task.get("routed_to", "Nexus"),
                    "confidence": 0.85,
                    "reason": f"Task '{task['description'][:50]}...' is pending and ready for execution.",
                },
                "context_summary": context_summary,
            }

        return {
            "suggestion": None,
            "context_summary": context_summary,
            "reason": "No actionable items at this time.",
        }

    async def approve_suggestion(
        self,
        suggestion_id: str,
        approver: str = "user",
        notes: str = "",
    ) -> Dict[str, Any]:
        """Approve and execute a suggestion.

        Handles both agenda items and legacy tasks.
        """
        await self._state.broadcast("suggestion_approved", {"suggestion_id": suggestion_id})

        if not self._state.coo or not self._state.llm_provider:
            return {"success": False, "suggestion_id": suggestion_id, "status": "coo_not_available"}

        # Check if this is an agenda item
        if self._state.coo.is_agenda_enabled():
            # Handle special agenda actions
            if suggestion_id == "generate_agenda":
                result = await self._state.coo.generate_agenda()
                return {
                    "success": "error" not in result,
                    "suggestion_id": suggestion_id,
                    "status": "agenda_generated" if "error" not in result else "failed",
                    "result": result,
                }

            # Try to approve/execute as agenda item
            agenda_result = await self._execute_agenda_item(suggestion_id, approver, notes)
            if agenda_result["status"] != "not_found":
                return agenda_result

        # Fallback to legacy task execution
        tasks = self._state.list_tasks()
        task = next((t for t in tasks if t["id"] == suggestion_id), None)

        if not task:
            return {"success": False, "suggestion_id": suggestion_id, "status": "not_found"}

        # Execute the task via TaskService
        task_service = TaskService(self._state)
        await task_service._execute_via_coo(
            task,
            task["description"],
            task["task_type"],
            task.get("priority", "medium"),
            task.get("context", {}),
        )

        return {"success": True, "suggestion_id": suggestion_id, "status": "executed"}

    async def _execute_agenda_item(
        self,
        item_id: str,
        approver: str,
        notes: str,
    ) -> Dict[str, Any]:
        """Execute an agenda item, approving first if needed."""
        # Get the agenda item
        agenda_items = await self._state.coo.get_agenda_items(count=50)
        item = next((i for i in agenda_items if i["id"] == item_id), None)

        if not item:
            return {"success": False, "suggestion_id": item_id, "status": "not_found"}

        # Approve if pending
        if item.get("requires_approval") and item.get("approval_status") == "pending":
            approved = await self._state.coo.approve_agenda_item(item_id, approver, notes)
            if not approved:
                return {
                    "success": False,
                    "suggestion_id": item_id,
                    "status": "approval_failed",
                }

        # Execute the agenda item
        result = await self._state.coo.execute_agenda_item(item_id)

        return {
            "success": result.success,
            "suggestion_id": item_id,
            "status": "executed" if result.success else "failed",
            "result": result.output if result.success else result.error,
            "executor": item.get("recommended_agent"),
        }

    async def reject_suggestion(
        self,
        suggestion_id: str,
        approver: str = "user",
        reason: str = "",
    ) -> Dict[str, Any]:
        """Reject a suggestion.

        Handles both agenda items and legacy tasks.
        """
        await self._state.broadcast("suggestion_rejected", {"suggestion_id": suggestion_id})

        # Check if this is an agenda item
        if self._state.coo and self._state.coo.is_agenda_enabled():
            rejected = await self._state.coo.reject_agenda_item(
                suggestion_id, approver, reason or "Rejected by user"
            )
            if rejected:
                return {
                    "success": True,
                    "suggestion_id": suggestion_id,
                    "status": "rejected",
                    "reason": reason,
                }

        return {"success": True, "suggestion_id": suggestion_id, "status": "rejected"}
