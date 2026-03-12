"""Autonomous agenda engine integration mixin for Overwatch."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.core.base import Task, TaskResult

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class AgendaMixin:
    """Agenda engine integration for Overwatch."""

    async def connect_agenda_engine(self, agenda_engine: "AutonomousAgendaEngine") -> None:
        """
        Connect the Autonomous Agenda Engine to the Overwatch.

        This enables:
        - Goal-based agenda generation
        - Obstacle detection and strategy generation
        - Human-in-the-loop checkpoints
        - Agenda-driven suggestions

        Args:
            agenda_engine: The autonomous agenda engine instance
        """
        self._agenda_engine = agenda_engine
        logger.info("Agenda engine connected to Overwatch", component="cos")

    async def disconnect_agenda_engine(self) -> None:
        """Disconnect the agenda engine."""
        self._agenda_engine = None
        logger.info("Agenda engine disconnected from Overwatch", component="cos")

    def is_agenda_enabled(self) -> bool:
        """Check if agenda engine is connected and enabled."""
        return self._agenda_engine is not None

    async def generate_agenda(
        self,
        period_hours: int = 24,
        goals: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate an agenda using the connected agenda engine.

        Args:
            period_hours: Planning period in hours
            goals: Optional list of goals (uses default if not provided)

        Returns:
            Generated agenda dictionary
        """
        if not self.is_agenda_enabled():
            return {"error": "Agenda engine not connected", "agenda": None}

        try:
            agenda = await self._agenda_engine.generate_agenda(
                period_hours=period_hours,
                goals=goals,
            )
            return {
                "agenda_id": agenda.id,
                "period_start": agenda.period_start.isoformat(),
                "period_end": agenda.period_end.isoformat(),
                "total_items": len(agenda.items),
                "goals_addressed": agenda.goals_addressed,
                "obstacles_addressed": agenda.obstacles_addressed,
                "items": [
                    {
                        "id": item.id,
                        "title": item.title,
                        "priority_score": item.priority_score,
                        "estimated_duration_minutes": item.estimated_duration_minutes,
                        "requires_approval": item.requires_approval,
                        "task_type": item.task_type,
                        "recommended_agent": item.recommended_agent,
                    }
                    for item in agenda.items
                ],
            }
        except Exception as e:
            logger.error(f"Failed to generate agenda: {e}", component="cos")
            return {"error": str(e), "agenda": None}

    async def get_agenda_items(
        self,
        count: int = 5,
        include_awaiting_approval: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get executable agenda items.

        Args:
            count: Maximum number of items to return
            include_awaiting_approval: Include items awaiting approval

        Returns:
            List of agenda items
        """
        if not self.is_agenda_enabled():
            return []

        items = self._agenda_engine.get_executable_items(count=count)
        result = []

        for item in items:
            result.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "task_type": item.task_type,
                    "priority_score": item.priority_score,
                    "estimated_duration_minutes": item.estimated_duration_minutes,
                    "requires_approval": item.requires_approval,
                    "approval_status": getattr(item, "approval_status", None),
                    "recommended_agent": item.recommended_agent,
                    "confidence_level": str(getattr(item, "confidence_level", "MEDIUM")),
                    "is_obstacle_resolution": getattr(item, "is_obstacle_resolution", False),
                    "goal_id": item.goal_id,
                    "milestone_id": item.milestone_id,
                }
            )

        if include_awaiting_approval:
            awaiting = self._agenda_engine.get_items_awaiting_approval()
            for item in awaiting:
                if item.id not in [r["id"] for r in result]:
                    result.append(
                        {
                            "id": item.id,
                            "title": item.title,
                            "description": item.description,
                            "task_type": item.task_type,
                            "priority_score": item.priority_score,
                            "estimated_duration_minutes": item.estimated_duration_minutes,
                            "requires_approval": True,
                            "approval_status": "pending",
                            "recommended_agent": item.recommended_agent,
                            "confidence_level": str(getattr(item, "confidence_level", "MEDIUM")),
                            "is_obstacle_resolution": getattr(
                                item, "is_obstacle_resolution", False
                            ),
                            "goal_id": item.goal_id,
                            "milestone_id": item.milestone_id,
                        }
                    )

        return result

    async def execute_agenda_item(self, item_id: str) -> TaskResult:
        """
        Execute a specific agenda item.

        Args:
            item_id: The agenda item ID to execute

        Returns:
            TaskResult from execution
        """
        if not self.is_agenda_enabled():
            return TaskResult(
                task_id=item_id,
                success=False,
                error="Agenda engine not connected",
            )

        # Get the item from current agenda
        item = None
        engine = self._agenda_engine
        if engine._current_agenda and engine._current_agenda.items:
            for candidate in engine._current_agenda.items:
                if candidate.id == item_id:
                    item = candidate
                    break
        if not item:
            return TaskResult(
                task_id=item_id,
                success=False,
                error=f"Agenda item {item_id} not found",
            )

        # Check if approval is required
        if item.requires_approval and item.approval_status != "approved":
            return TaskResult(
                task_id=item_id,
                success=False,
                error="Item requires approval before execution",
            )

        # Create a task from the agenda item
        task = Task(
            description=item.description,
            task_type=item.task_type,
            context={
                "agenda_item_id": item.id,
                "goal_id": item.goal_id,
                "milestone_id": item.milestone_id,
                "workstream_id": item.workstream_id,
                **item.context,
            },
        )

        # Execute via Overwatch
        result = await self.execute(task)

        # Update agenda based on result
        await self._agenda_engine.adapt_agenda(
            {
                "item_id": item.id,
                "success": result.success,
                "output": result.output,
                "error": result.error,
            }
        )

        return result

    async def approve_agenda_item(
        self,
        item_id: str,
        approver: str,
        notes: str = "",
    ) -> bool:
        """
        Approve an agenda item for execution.

        Args:
            item_id: The agenda item ID
            approver: Who is approving
            notes: Optional approval notes

        Returns:
            True if approved successfully
        """
        if not self.is_agenda_enabled():
            return False

        return await self._agenda_engine.approve_item(item_id, approver, notes)

    async def reject_agenda_item(
        self,
        item_id: str,
        rejector: str,
        reason: str,
    ) -> bool:
        """
        Reject an agenda item.

        Args:
            item_id: The agenda item ID
            rejector: Who is rejecting
            reason: Rejection reason

        Returns:
            True if rejected successfully
        """
        if not self.is_agenda_enabled():
            return False

        return await self._agenda_engine.reject_item(item_id, rejector, reason)

    async def get_agenda_status(self) -> Dict[str, Any]:
        """Get the current agenda engine status."""
        if not self.is_agenda_enabled():
            return {"enabled": False}

        engine = self._agenda_engine
        has_agenda = engine._current_agenda is not None
        return {
            "agenda_enabled": True,
            "has_agenda": has_agenda,
            "total_items": len(engine._current_agenda.items) if has_agenda else 0,
            "total_workstreams": len(getattr(engine, "_workstreams", {})),
        }

    async def get_agenda_obstacles(self) -> List[Dict[str, Any]]:
        """Get detected obstacles from the agenda engine."""
        if not self.is_agenda_enabled():
            return []

        return [
            {"id": k, "description": str(v)}
            for k, v in getattr(self._agenda_engine, "_obstacles", {}).items()
        ]

    async def get_agenda_strategies(self) -> List[Dict[str, Any]]:
        """Get generated strategies from the agenda engine."""
        if not self.is_agenda_enabled():
            return []

        return [
            {"id": k, "description": str(v)}
            for k, v in getattr(self._agenda_engine, "_strategies", {}).items()
        ]

    def enrich_context_with_agenda(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a task context with agenda information.

        Args:
            context: Original task context

        Returns:
            Enriched context with agenda data
        """
        if not self.is_agenda_enabled():
            return context

        return self._agenda_engine.feed_to_coo_context(context)
