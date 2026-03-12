"""
Prediction Facade - Failure prediction, load balancing, and task modification.

This facade manages predictive learning components:
- FailurePredictor: Predicts task failure risks before execution
- LoadBalancer: Load-aware task assignment decisions
- TaskModifier: Proactive task modifications based on predictions
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ag3ntwerk.learning.failure_predictor import FailurePredictor, FailureRisk
from ag3ntwerk.learning.load_balancer import LoadBalancer, LoadBalanceDecision, AgentLoad
from ag3ntwerk.learning.task_modifier import TaskModifier, ModifiedTask

logger = logging.getLogger(__name__)


class PredictionFacade:
    """
    Facade for predictive learning operations.

    Manages failure prediction, load balancing, and proactive
    task modification based on learned patterns.
    """

    def __init__(
        self,
        db: Any,
        task_queue: Optional[Any] = None,
    ):
        """
        Initialize the prediction facade.

        Args:
            db: Database connection
            task_queue: Optional task queue for queue depth metrics
        """
        self._db = db
        self._task_queue = task_queue
        self._failure_predictor = FailurePredictor(db, task_queue)
        self._load_balancer = LoadBalancer(db, task_queue)
        self._task_modifier = TaskModifier(self._failure_predictor, self._load_balancer)

    # --- Failure Prediction ---

    async def predict_failure_risk(
        self,
        task_type: str,
        target_agent: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> FailureRisk:
        """
        Predict the failure risk for a task before execution.

        Uses historical patterns to anticipate problems.

        Args:
            task_type: Type of task
            target_agent: Agent that will handle the task
            context: Additional context about the task

        Returns:
            FailureRisk with score, level, and mitigations
        """
        return await self._failure_predictor.predict_failure_risk(
            task_type=task_type,
            target_agent=target_agent,
            context=context,
        )

    async def get_safest_agent(
        self,
        task_type: str,
        candidates: List[str],
    ) -> Optional[Tuple[str, FailureRisk]]:
        """
        Find the agent with lowest failure risk for a task.

        Args:
            task_type: Type of task
            candidates: List of candidate agent codes

        Returns:
            (agent_code, FailureRisk) for safest agent, or None
        """
        return await self._failure_predictor.get_safest_agent(task_type, candidates)

    async def get_high_risk_agents(
        self,
        task_type: str,
        threshold: float = 0.5,
    ) -> List[Tuple[str, FailureRisk]]:
        """
        Find agents with high failure risk for a task type.

        Args:
            task_type: Type of task
            threshold: Risk score threshold

        Returns:
            List of (agent_code, FailureRisk) tuples
        """
        return await self._failure_predictor.get_high_risk_agents(task_type, threshold)

    # --- Load Balancing ---

    async def get_optimal_agent(
        self,
        task_type: str,
        candidates: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> LoadBalanceDecision:
        """
        Get the optimal agent based on load balancing.

        Considers capacity, performance, and health.

        Args:
            task_type: Type of task
            candidates: List of candidate agent codes
            context: Additional context

        Returns:
            LoadBalanceDecision with chosen agent
        """
        return await self._load_balancer.get_optimal_agent(
            task_type=task_type,
            candidates=candidates,
            context=context,
        )

    async def get_agent_loads(
        self,
        agent_codes: List[str],
    ) -> Dict[str, AgentLoad]:
        """
        Get load metrics for multiple agents.

        Args:
            agent_codes: List of agent codes

        Returns:
            Dict of agent_code -> AgentLoad
        """
        return await self._load_balancer.get_agent_loads(agent_codes)

    async def get_overloaded_agents(
        self,
        agent_codes: Optional[List[str]] = None,
    ) -> List[Tuple[str, AgentLoad]]:
        """
        Find agents that are currently overloaded.

        Args:
            agent_codes: Optional list of agents to check

        Returns:
            List of (agent_code, AgentLoad) for overloaded agents
        """
        return await self._load_balancer.get_overloaded_agents(agent_codes)

    async def get_idle_agents(
        self,
        agent_codes: Optional[List[str]] = None,
        idle_threshold: float = 0.2,
    ) -> List[Tuple[str, AgentLoad]]:
        """
        Find agents with low utilization.

        Args:
            agent_codes: Optional list of agents to check
            idle_threshold: Utilization threshold

        Returns:
            List of (agent_code, AgentLoad) for idle agents
        """
        return await self._load_balancer.get_idle_agents(agent_codes, idle_threshold)

    # --- Task Modification ---

    async def modify_task(
        self,
        task: Dict[str, Any],
        target_agent: str,
        candidates: Optional[List[str]] = None,
    ) -> ModifiedTask:
        """
        Proactively modify a task based on predicted risks.

        Applies mitigations like timeout extension, retries,
        agent reassignment, and priority adjustment.

        Args:
            task: Task dictionary with at least task_type
            target_agent: Initially selected target agent
            candidates: Optional list of alternative agents

        Returns:
            ModifiedTask with modifications applied
        """
        return await self._task_modifier.modify_task(
            task=task,
            target_agent=target_agent,
            candidates=candidates,
        )

    # --- Stats ---

    async def get_stats(self) -> Dict[str, Any]:
        """Get prediction facade statistics."""
        return {
            "failure_predictor": (
                await self._failure_predictor.get_stats()
                if hasattr(self._failure_predictor, "get_stats")
                else {}
            ),
            "load_balancer": (
                await self._load_balancer.get_stats()
                if hasattr(self._load_balancer, "get_stats")
                else {}
            ),
            "task_modifier": (
                await self._task_modifier.get_stats()
                if hasattr(self._task_modifier, "get_stats")
                else {}
            ),
        }

    # --- Accessors for components (used by orchestrator) ---

    @property
    def failure_predictor(self) -> FailurePredictor:
        """Get failure predictor."""
        return self._failure_predictor

    @property
    def load_balancer(self) -> LoadBalancer:
        """Get load balancer."""
        return self._load_balancer

    @property
    def task_modifier(self) -> TaskModifier:
        """Get task modifier."""
        return self._task_modifier
