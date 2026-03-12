"""
Metacognition Facade - Learning system integration for metacognition.

11th facade following the existing pattern. Connects the MetacognitionService
to the continuous learning pipeline, providing personality evolution and
reflection as Phase 5.5.
"""

import logging
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies
_MetacognitionService = None


def _get_service_class():
    global _MetacognitionService
    if _MetacognitionService is None:
        from ag3ntwerk.modules.metacognition.service import MetacognitionService

        _MetacognitionService = MetacognitionService
    return _MetacognitionService


class MetacognitionFacade:
    """
    Facade for metacognition operations within the learning system.

    Bridges the MetacognitionService with the continuous learning pipeline.
    Provides reflection, evolution, and heuristic tuning during learning cycles.
    """

    def __init__(self):
        self._service = None
        self._outcomes_buffer: deque[Dict[str, Any]] = deque(maxlen=10000)

    @property
    def outcomes_buffer_count(self) -> int:
        return len(self._outcomes_buffer)

    def connect_service(self, service: Any) -> None:
        """
        Connect a MetacognitionService instance.

        Args:
            service: MetacognitionService instance
        """
        self._service = service
        logger.info("MetacognitionFacade connected to service")

    @property
    def is_connected(self) -> bool:
        """Check if the metacognition service is connected."""
        return self._service is not None

    def process_outcome_with_reflection(
        self,
        agent_code: str,
        task_id: str,
        task_type: str,
        success: bool,
        duration_ms: float = 0.0,
        confidence: Optional[float] = None,
        error: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Process a task outcome with metacognitive reflection.

        Args:
            agent_code: Agent that handled the task
            task_id: Task identifier
            task_type: Type of task
            success: Whether it succeeded
            duration_ms: Execution time
            confidence: Pre-task confidence
            error: Error message if failed

        Returns:
            ReflectionResult dict, or None
        """
        if not self._service:
            return None

        # Buffer for batch processing
        self._outcomes_buffer.append(
            {
                "agent_code": agent_code,
                "task_id": task_id,
                "task_type": task_type,
                "success": success,
                "duration_ms": duration_ms,
                "confidence": confidence,
                "error": error,
            }
        )

        # Process immediately through service
        result = self._service.on_task_completed(
            agent_code=agent_code,
            task_id=task_id,
            task_type=task_type,
            success=success,
            duration_ms=duration_ms,
            confidence=confidence,
            error=error,
        )

        if result:
            return result.to_dict()
        return None

    def run_metacognition_phase(
        self,
        agent_health: Optional[Dict[str, Dict[str, Any]]] = None,
        drift_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the metacognition phase of the learning cycle.

        This is called as Phase 5.5 in the continuous pipeline:
        1. Collect buffered outcomes
        2. Run reflections for all agents
        3. Evolve personalities
        4. Tune heuristics
        5. Optionally run system reflection

        Args:
            agent_health: Per-agent health metrics
            drift_summary: Drift detection summary

        Returns:
            Phase results with metrics
        """
        if not self._service:
            return {"skipped": True, "reason": "service_not_connected"}

        results = {
            "outcomes_processed": len(self._outcomes_buffer),
            "reflections_generated": 0,
            "evolutions_applied": 0,
            "heuristics_tuned": 0,
            "system_reflection": None,
        }

        # Process buffered outcomes (already processed on arrival, just count)
        results["reflections_generated"] = len(self._outcomes_buffer)

        # Tune heuristics across all agents
        tunings = self._service.tune_heuristics()
        results["heuristics_tuned"] = len(tunings)

        # Phase 5: Temporal trait snapshots
        snapshots = self._service.record_trait_snapshot()
        results["trait_snapshots_taken"] = len(snapshots)

        # Phase 5: Cross-agent heuristic sharing
        shares = self._service.auto_share_heuristics()
        results["heuristics_shared"] = len(shares)

        # Phase 5: Closed-loop trait map optimization
        updates = self._service.apply_trait_map_suggestions()
        results["trait_map_updates_applied"] = len(updates)
        validations = self._service.validate_trait_map_updates()
        results["trait_map_validations"] = len(validations)

        # Run system reflection periodically (every 10 calls or if health data available)
        if agent_health or self._service._system_reflection_count % 10 == 0:
            sys_reflection = self._service.system_reflect(
                agent_health=agent_health,
                drift_summary=drift_summary,
            )
            results["system_reflection"] = sys_reflection.to_dict()

        # Clear buffer
        self._outcomes_buffer.clear()

        # Auto-save profiles after metacognition phase
        if hasattr(self._service, "save_if_auto"):
            self._service.save_if_auto()

        return results

    def get_personality_insights(self) -> Dict[str, Any]:
        """Get personality insights for all registered agents."""
        if not self._service:
            return {"connected": False}

        return {
            "connected": True,
            **self._service.get_stats(),
        }

    async def get_stats(self) -> Dict[str, Any]:
        """Get facade statistics."""
        return {
            "connected": self.is_connected,
            "outcomes_buffered": len(self._outcomes_buffer),
            "service_stats": self._service.get_stats() if self._service else {},
        }
