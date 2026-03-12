"""
Proactive Facade - Opportunity detection and proactive task generation.

This facade manages proactive behavior components:
- OpportunityDetector: Identifies improvement opportunities
- ProactiveTaskGenerator: Creates tasks to address opportunities
"""

import logging
from typing import Any, Dict, List, Optional

from ag3ntwerk.learning.opportunity_detector import (
    OpportunityDetector,
    Opportunity,
    OpportunityType,
    OpportunityPriority,
)
from ag3ntwerk.learning.pattern_store import PatternStore
from ag3ntwerk.learning.proactive_generator import (
    ProactiveTaskGenerator,
    ProactiveTask,
    ProactiveTaskType,
    TaskPriority,
)

logger = logging.getLogger(__name__)


class ProactiveFacade:
    """
    Facade for proactive behavior operations.

    Manages opportunity detection and proactive task generation
    to enable the learning system to take initiative.
    """

    def __init__(
        self,
        db: Any,
        task_queue: Optional[Any],
        pattern_store: PatternStore,
    ):
        """
        Initialize the proactive facade.

        Args:
            db: Database connection
            task_queue: Optional task queue for task creation
            pattern_store: Shared pattern store instance
        """
        self._db = db
        self._task_queue = task_queue
        self._pattern_store = pattern_store
        self._opportunity_detector = OpportunityDetector(db, pattern_store)
        self._proactive_generator = ProactiveTaskGenerator(
            db, task_queue, self._opportunity_detector
        )

    # --- Opportunity Detection ---

    async def detect_opportunities(
        self,
        window_hours: int = 168,
    ) -> List[Opportunity]:
        """
        Run opportunity detection cycle.

        Args:
            window_hours: Time window for analysis

        Returns:
            List of detected opportunities
        """
        return await self._opportunity_detector.detect_opportunities(window_hours)

    async def get_open_opportunities(self) -> List[Opportunity]:
        """Get all open opportunities."""
        return await self._opportunity_detector.get_open_opportunities()

    async def get_actionable_opportunities(self) -> List[Opportunity]:
        """Get opportunities that can be addressed automatically."""
        return await self._opportunity_detector.get_actionable_opportunities()

    async def get_opportunities_by_type(
        self,
        opportunity_type: OpportunityType,
    ) -> List[Opportunity]:
        """Get opportunities of a specific type."""
        return await self._opportunity_detector.get_opportunities_by_type(opportunity_type)

    async def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get a specific opportunity."""
        return await self._opportunity_detector.get_opportunity(opportunity_id)

    async def acknowledge_opportunity(self, opportunity_id: str) -> bool:
        """Acknowledge an opportunity."""
        return await self._opportunity_detector.acknowledge_opportunity(opportunity_id)

    async def address_opportunity(
        self,
        opportunity_id: str,
        resolution: str = "",
    ) -> bool:
        """Mark an opportunity as addressed."""
        return await self._opportunity_detector.address_opportunity(opportunity_id, resolution)

    async def dismiss_opportunity(
        self,
        opportunity_id: str,
        reason: str = "",
    ) -> bool:
        """Dismiss an opportunity."""
        return await self._opportunity_detector.dismiss_opportunity(opportunity_id, reason)

    async def get_opportunity_stats(self) -> Dict[str, Any]:
        """Get opportunity detection statistics."""
        return await self._opportunity_detector.get_stats()

    # --- Proactive Task Generation ---

    async def generate_proactive_tasks(
        self,
        window_hours: int = 24,
    ) -> List[ProactiveTask]:
        """
        Generate all types of proactive tasks.

        Args:
            window_hours: Time window for analysis

        Returns:
            List of generated tasks
        """
        return await self._proactive_generator.generate_all_tasks(window_hours)

    async def get_pending_proactive_tasks(self) -> List[ProactiveTask]:
        """Get all pending proactive tasks."""
        return await self._proactive_generator.get_pending_tasks()

    async def get_proactive_task(self, task_id: str) -> Optional[ProactiveTask]:
        """Get a specific proactive task."""
        return await self._proactive_generator.get_task(task_id)

    async def get_proactive_tasks_by_type(
        self,
        task_type: ProactiveTaskType,
    ) -> List[ProactiveTask]:
        """Get proactive tasks of a specific type."""
        return await self._proactive_generator.get_tasks_by_type(task_type)

    async def enqueue_proactive_task(self, task: ProactiveTask) -> bool:
        """Enqueue a proactive task to the task queue."""
        return await self._proactive_generator.enqueue_task(task)

    async def enqueue_all_proactive_tasks(self) -> int:
        """Enqueue all pending proactive tasks."""
        return await self._proactive_generator.enqueue_all_pending()

    async def complete_proactive_task(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Mark a proactive task as completed."""
        return await self._proactive_generator.complete_task(task_id, result)

    async def fail_proactive_task(
        self,
        task_id: str,
        error: str = "",
    ) -> bool:
        """Mark a proactive task as failed."""
        return await self._proactive_generator.fail_task(task_id, error)

    async def get_proactive_task_stats(self) -> Dict[str, Any]:
        """Get proactive task generation statistics."""
        return await self._proactive_generator.get_stats()

    # --- Orchestration ---

    async def run_proactive_cycle(
        self,
        window_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Run a full proactive behavior cycle.

        1. Detect opportunities
        2. Generate proactive tasks
        3. Enqueue high-priority tasks

        Args:
            window_hours: Time window for analysis

        Returns:
            Summary of actions taken
        """
        # Detect opportunities
        opportunities = await self.detect_opportunities(window_hours * 7)  # 1 week lookback

        # Generate tasks
        tasks = await self.generate_proactive_tasks(window_hours)

        # Enqueue high-priority tasks automatically
        auto_enqueued = 0
        for task in tasks:
            if task.priority.value <= TaskPriority.MEDIUM.value:
                if await self.enqueue_proactive_task(task):
                    auto_enqueued += 1

        return {
            "opportunities_detected": len(opportunities),
            "tasks_generated": len(tasks),
            "tasks_auto_enqueued": auto_enqueued,
            "high_priority_opportunities": len(
                [
                    o
                    for o in opportunities
                    if o.priority in (OpportunityPriority.CRITICAL, OpportunityPriority.HIGH)
                ]
            ),
        }

    # --- Stats ---

    async def get_stats(self) -> Dict[str, Any]:
        """Get proactive facade statistics."""
        return {
            "opportunity_detector": await self._opportunity_detector.get_stats(),
            "proactive_generator": await self._proactive_generator.get_stats(),
        }

    # --- Accessors for components (used by orchestrator) ---

    @property
    def opportunity_detector(self) -> OpportunityDetector:
        """Get opportunity detector."""
        return self._opportunity_detector

    @property
    def proactive_generator(self) -> ProactiveTaskGenerator:
        """Get proactive task generator."""
        return self._proactive_generator
