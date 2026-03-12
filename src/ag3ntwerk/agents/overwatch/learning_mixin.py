"""Learning system integration mixin for Overwatch."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.core.base import Manager, Specialist

if TYPE_CHECKING:
    from ag3ntwerk.learning.orchestrator import LearningOrchestrator

# Learning system integration (optional, imported lazily)
try:
    from ag3ntwerk.learning.models import HierarchyPath

    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False
    HierarchyPath = None

logger = get_logger(__name__)


class LearningMixin:
    """Learning system integration for Overwatch."""

    async def connect_learning_system(
        self,
        orchestrator: "LearningOrchestrator",
    ) -> None:
        """
        Connect the learning orchestrator to the Overwatch.

        This enables:
        - Outcome recording after each task execution
        - Learning-based routing adjustments
        - Pattern detection and issue creation
        - Confidence calibration

        Args:
            orchestrator: The learning orchestrator instance
        """
        if not LEARNING_AVAILABLE:
            logger.warning("Learning system not available - imports failed")
            return

        self._learning_orchestrator = orchestrator

        # Register all subordinate agents with the learning system
        for agent_code, exec_agent in self._subordinates.items():
            managers = []
            if isinstance(exec_agent, Manager):
                managers = list(exec_agent._subordinates.keys())

            orchestrator.register_executive(agent_code, managers)

            # Register managers and their specialists
            if isinstance(exec_agent, Manager):
                for mgr_code, mgr_agent in exec_agent._subordinates.items():
                    specialists = []
                    if isinstance(mgr_agent, Manager):
                        specialists = list(mgr_agent._subordinates.keys())

                    orchestrator.register_manager(mgr_code, agent_code, specialists)

                    # Register specialists
                    if isinstance(mgr_agent, Manager):
                        for spec_code, spec_agent in mgr_agent._subordinates.items():
                            capabilities = []
                            if isinstance(spec_agent, Specialist):
                                capabilities = spec_agent.capabilities

                            orchestrator.register_specialist(spec_code, mgr_code, capabilities)

        # Propagate orchestrator to all managers so every delegate() records outcomes
        for agent_code, exec_agent in self._subordinates.items():
            if isinstance(exec_agent, Manager):
                exec_agent.connect_learning_orchestrator(orchestrator)
                # Also propagate to sub-managers
                for mgr_code, mgr_agent in exec_agent._subordinates.items():
                    if isinstance(mgr_agent, Manager):
                        mgr_agent.connect_learning_orchestrator(orchestrator)

        logger.info(f"Connected learning system with {len(self._subordinates)} agents")

    def disconnect_learning_system(self) -> None:
        """Disconnect the learning system."""
        self._learning_orchestrator = None
        logger.info("Disconnected learning system")

    def is_learning_enabled(self) -> bool:
        """Check if learning system is connected and available."""
        return LEARNING_AVAILABLE and self._learning_orchestrator is not None

    async def get_learning_insights(self) -> Dict[str, Any]:
        """Get learning insights from the connected learning system."""
        if not self._learning_orchestrator:
            return {"error": "Learning system not connected"}
        try:
            return await self._learning_orchestrator.get_insights()
        except Exception as e:
            return {"error": str(e)}

    async def get_learning_stats(self) -> Dict[str, Any]:
        """
        Get learning system statistics.

        Returns:
            Dictionary with learning stats or error if not connected
        """
        if not self._learning_orchestrator:
            return {"learning_enabled": False, "error": "Learning system not connected"}

        try:
            stats = await self._learning_orchestrator.get_stats()
            return {
                "learning_enabled": True,
                **stats,
            }
        except Exception as e:
            return {"learning_enabled": True, "error": str(e)}

    async def get_learned_patterns(
        self,
        agent_code: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get learned patterns from the learning system.

        Args:
            agent_code: Filter by agent code
            task_type: Filter by task type

        Returns:
            List of patterns as dictionaries
        """
        if not self._learning_orchestrator:
            return []

        try:
            patterns = await self._learning_orchestrator.get_patterns(
                scope_code=agent_code,
                task_type=task_type,
            )
            return [
                {
                    "id": p.id,
                    "pattern_type": p.pattern_type.value,
                    "scope_level": p.scope_level.value,
                    "scope_code": p.scope_code,
                    "recommendation": p.recommendation,
                    "confidence": p.confidence,
                    "sample_size": p.sample_size,
                    "success_rate": p.success_rate,
                    "is_active": p.is_active,
                }
                for p in patterns
            ]
        except Exception as e:
            logger.error(f"Failed to get learned patterns: {e}")
            return []

    async def get_open_learning_issues(
        self,
        agent_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get open issues from the learning system.

        Args:
            agent_code: Filter by agent code

        Returns:
            List of issues as dictionaries
        """
        if not self._learning_orchestrator:
            return []

        try:
            issues = await self._learning_orchestrator.get_open_issues(agent_code)
            return [
                {
                    "id": i.id,
                    "issue_type": i.issue_type.value,
                    "severity": i.severity.value,
                    "priority": i.priority,
                    "source_agent": i.source_agent_code,
                    "title": i.title,
                    "description": i.description,
                    "suggested_action": i.suggested_action,
                    "status": i.status.value,
                    "created_at": i.created_at.isoformat(),
                }
                for i in issues
            ]
        except Exception as e:
            logger.error(f"Failed to get open issues: {e}")
            return []

    async def trigger_learning_analysis(self) -> Dict[str, Any]:
        """
        Manually trigger a learning analysis cycle.

        Returns:
            Analysis results
        """
        if not self._learning_orchestrator:
            return {"error": "Learning system not connected"}

        try:
            return await self._learning_orchestrator.trigger_analysis()
        except Exception as e:
            logger.error(f"Failed to trigger learning analysis: {e}")
            return {"error": str(e)}
