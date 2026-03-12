"""
Load Balancer - Load-aware task assignment.

Distributes tasks across agents based on:
1. Current queue depth and active tasks
2. Recent performance metrics
3. Agent capacity and health
4. Task-type specific performance

This enables better resource utilization and prevents
overloading individual agents.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from ag3ntwerk.core.queue import TaskQueue

logger = logging.getLogger(__name__)


@dataclass
class AgentLoad:
    """Load metrics for an agent."""

    agent_code: str

    # Queue metrics
    queue_depth: int = 0
    active_tasks: int = 0

    # Capacity
    max_concurrent_tasks: int = 10
    utilization: float = 0.0  # 0.0 to 1.0

    # Performance
    avg_task_duration_ms: float = 0.0
    tasks_completed_last_hour: int = 0
    tasks_failed_last_hour: int = 0

    # Health
    health_score: float = 1.0
    is_available: bool = True

    @property
    def available_capacity(self) -> int:
        """Calculate available capacity for new tasks."""
        if not self.is_available:
            return 0
        return max(0, self.max_concurrent_tasks - self.active_tasks - self.queue_depth)

    @property
    def success_rate_last_hour(self) -> float:
        """Calculate success rate in the last hour."""
        total = self.tasks_completed_last_hour + self.tasks_failed_last_hour
        if total == 0:
            return 1.0  # No data = assume good
        return self.tasks_completed_last_hour / total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "queue_depth": self.queue_depth,
            "active_tasks": self.active_tasks,
            "utilization": self.utilization,
            "available_capacity": self.available_capacity,
            "avg_task_duration_ms": self.avg_task_duration_ms,
            "success_rate_last_hour": self.success_rate_last_hour,
            "health_score": self.health_score,
            "is_available": self.is_available,
        }


@dataclass
class LoadBalanceDecision:
    """Result of a load balancing decision."""

    chosen_agent: str
    score: float
    reasoning: str

    # All candidates with scores
    all_scores: List[Tuple[str, float]] = field(default_factory=list)

    # Load metrics used
    load_metrics: Dict[str, AgentLoad] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chosen_agent": self.chosen_agent,
            "score": self.score,
            "reasoning": self.reasoning,
            "all_scores": self.all_scores,
        }


class LoadBalancer:
    """
    Distributes tasks across agents based on load and performance.

    Scoring factors:
    - Available capacity (higher = better)
    - Recent success rate (higher = better)
    - Task-specific performance (higher = better)
    - Current health (higher = better)
    - Response time (lower = better)
    """

    # Weight configuration
    WEIGHTS = {
        "capacity": 0.30,
        "success_rate": 0.25,
        "task_performance": 0.20,
        "health": 0.15,
        "response_time": 0.10,
    }

    # Thresholds
    OVERLOAD_THRESHOLD = 0.9  # Utilization above this is overloaded
    MIN_CAPACITY_FOR_TASK = 1  # Need at least this much capacity

    def __init__(self, db: Any, task_queue: Optional["TaskQueue"] = None):
        """
        Initialize the load balancer.

        Args:
            db: Database connection
            task_queue: Optional task queue for real-time queue metrics
        """
        self._db = db
        self._task_queue = task_queue

        # Cache for load metrics
        self._load_cache: Dict[str, AgentLoad] = {}
        self._cache_updated_at: Optional[datetime] = None
        self._cache_ttl_seconds = 30  # 30 second cache

    async def get_optimal_agent(
        self,
        task_type: str,
        candidates: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> LoadBalanceDecision:
        """
        Get the optimal agent for a task based on load balancing.

        Args:
            task_type: Type of task
            candidates: List of candidate agent codes
            context: Additional context about the task

        Returns:
            LoadBalanceDecision with chosen agent
        """
        if not candidates:
            return LoadBalanceDecision(
                chosen_agent="",
                score=0.0,
                reasoning="No candidates provided",
            )

        # Get load metrics for all candidates
        load_metrics = await self._get_load_metrics_for_agents(candidates)

        # Get task-specific performance for candidates
        task_performance = await self._get_task_performance(task_type, candidates)

        # Score each candidate
        scores: List[Tuple[str, float]] = []
        for agent_code in candidates:
            load = load_metrics.get(agent_code)
            if not load or not load.is_available:
                scores.append((agent_code, 0.0))
                continue

            score = self._score_agent(
                load=load,
                task_performance=task_performance.get(agent_code, {}),
                context=context,
            )
            scores.append((agent_code, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        if not scores or scores[0][1] == 0:
            # All agents unavailable
            return LoadBalanceDecision(
                chosen_agent=candidates[0] if candidates else "",
                score=0.0,
                reasoning="All agents unavailable or overloaded",
                all_scores=scores,
                load_metrics=load_metrics,
            )

        best_agent, best_score = scores[0]
        best_load = load_metrics.get(best_agent)

        reasoning = self._build_reasoning(best_agent, best_score, best_load)

        return LoadBalanceDecision(
            chosen_agent=best_agent,
            score=best_score,
            reasoning=reasoning,
            all_scores=scores,
            load_metrics=load_metrics,
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
        return await self._get_load_metrics_for_agents(agent_codes)

    async def get_overloaded_agents(
        self,
        agent_codes: Optional[List[str]] = None,
    ) -> List[Tuple[str, AgentLoad]]:
        """
        Find agents that are currently overloaded.

        Args:
            agent_codes: Optional list of agents to check

        Returns:
            List of (agent_code, load) for overloaded agents
        """
        if agent_codes is None:
            # Get all known agents
            rows = await self._db.fetch_all("SELECT DISTINCT agent_code FROM agent_performance")
            agent_codes = [row["agent_code"] for row in rows]

        loads = await self._get_load_metrics_for_agents(agent_codes)

        overloaded = [
            (code, load)
            for code, load in loads.items()
            if load.utilization >= self.OVERLOAD_THRESHOLD
        ]

        # Sort by utilization descending
        overloaded.sort(key=lambda x: x[1].utilization, reverse=True)
        return overloaded

    async def get_idle_agents(
        self,
        agent_codes: Optional[List[str]] = None,
        idle_threshold: float = 0.2,
    ) -> List[Tuple[str, AgentLoad]]:
        """
        Find agents that have low utilization.

        Args:
            agent_codes: Optional list of agents to check
            idle_threshold: Utilization below this is considered idle

        Returns:
            List of (agent_code, load) for idle agents
        """
        if agent_codes is None:
            rows = await self._db.fetch_all("SELECT DISTINCT agent_code FROM agent_performance")
            agent_codes = [row["agent_code"] for row in rows]

        loads = await self._get_load_metrics_for_agents(agent_codes)

        idle = [
            (code, load)
            for code, load in loads.items()
            if load.utilization < idle_threshold and load.is_available
        ]

        # Sort by utilization ascending
        idle.sort(key=lambda x: x[1].utilization)
        return idle

    # Private methods

    async def _get_load_metrics_for_agents(
        self,
        agent_codes: List[str],
    ) -> Dict[str, AgentLoad]:
        """Get load metrics for a list of agents."""
        result = {}

        for agent_code in agent_codes:
            # Check cache first
            if self._is_cache_fresh(agent_code):
                result[agent_code] = self._load_cache[agent_code]
                continue

            load = await self._fetch_agent_load(agent_code)
            self._load_cache[agent_code] = load
            result[agent_code] = load

        self._cache_updated_at = datetime.now(timezone.utc)
        return result

    async def _fetch_agent_load(self, agent_code: str) -> AgentLoad:
        """Fetch load metrics for a single agent from database and queue."""
        load = AgentLoad(agent_code=agent_code)

        try:
            # Get performance metrics from database
            perf_row = await self._db.fetch_one(
                """
                SELECT health_score, circuit_breaker_open, avg_duration_ms,
                       total_tasks, successful_tasks
                FROM agent_performance
                WHERE agent_code = ?
                """,
                (agent_code,),
            )

            if perf_row:
                load.health_score = perf_row["health_score"] or 1.0
                load.is_available = not bool(perf_row["circuit_breaker_open"])
                load.avg_task_duration_ms = perf_row["avg_duration_ms"] or 0.0

            # Get recent task counts from outcomes
            hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            counts_row = await self._db.fetch_one(
                """
                SELECT
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
                FROM learning_outcomes
                WHERE agent_code = ? AND created_at >= ?
                """,
                (agent_code, hour_ago.isoformat()),
            )

            if counts_row:
                load.tasks_completed_last_hour = counts_row["completed"] or 0
                load.tasks_failed_last_hour = counts_row["failed"] or 0

            # Get real-time queue metrics if task queue is available
            if self._task_queue:
                queue_metrics = await self._get_queue_metrics_for_agent(agent_code)
                load.queue_depth = queue_metrics.get("pending", 0)
                load.active_tasks = queue_metrics.get("processing", 0)
                # Calculate utilization from queue state
                total_in_queue = load.queue_depth + load.active_tasks
                load.utilization = min(1.0, total_in_queue / load.max_concurrent_tasks)
            else:
                # Fallback: estimate utilization from recent activity
                total_recent = load.tasks_completed_last_hour + load.tasks_failed_last_hour
                load.utilization = min(1.0, total_recent / 20)  # Assume 20 tasks/hour is full

        except Exception as e:
            logger.warning(f"Failed to fetch load for {agent_code}: {e}")

        return load

    async def _get_queue_metrics_for_agent(self, agent_code: str) -> Dict[str, int]:
        """
        Get queue metrics for a specific agent from the task queue.

        Args:
            agent_code: Agent code to get metrics for

        Returns:
            Dict with pending and processing counts
        """
        if not self._task_queue:
            return {"pending": 0, "processing": 0}

        try:
            # Get queue stats - the task queue tracks by task_type, not agent
            # We need to query tasks that would be routed to this agent
            stats = await self._task_queue.get_stats()

            # For now, we use overall queue stats divided by number of agents
            # In a production system, you'd track agent assignment in the task
            # or have agent-specific queues
            return {
                "pending": stats.pending,
                "processing": stats.processing,
            }
        except Exception as e:
            logger.warning(f"Failed to get queue metrics for {agent_code}: {e}")
            return {"pending": 0, "processing": 0}

    async def _get_task_performance(
        self,
        task_type: str,
        agent_codes: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Get task-type specific performance for agents."""
        result = {}

        try:
            for agent_code in agent_codes:
                row = await self._db.fetch_one(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                        AVG(duration_ms) as avg_duration
                    FROM learning_outcomes
                    WHERE agent_code = ? AND task_type = ?
                    """,
                    (agent_code, task_type),
                )

                if row and row["total"] > 0:
                    result[agent_code] = {
                        "total_tasks": row["total"],
                        "success_rate": row["successful"] / row["total"],
                        "avg_duration_ms": row["avg_duration"] or 0.0,
                    }
                else:
                    result[agent_code] = {
                        "total_tasks": 0,
                        "success_rate": 0.5,  # Unknown
                        "avg_duration_ms": 0.0,
                    }

        except Exception as e:
            logger.warning(f"Failed to get task performance: {e}")

        return result

    def _score_agent(
        self,
        load: AgentLoad,
        task_performance: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> float:
        """Score an agent for load balancing."""
        if not load.is_available:
            return 0.0

        # Capacity score (0-1, higher = more available capacity)
        capacity_score = min(1.0, load.available_capacity / load.max_concurrent_tasks)

        # Success rate score (0-1)
        success_score = load.success_rate_last_hour

        # Task-specific performance score
        task_score = task_performance.get("success_rate", 0.5)

        # Health score (already 0-1)
        health_score = load.health_score

        # Response time score (inverse of duration, normalized)
        # Assume 1000ms is baseline
        avg_duration = task_performance.get("avg_duration_ms", 1000)
        response_score = max(0.0, 1.0 - (avg_duration / 5000))  # 5s = 0 score

        # Weighted sum
        total_score = (
            self.WEIGHTS["capacity"] * capacity_score
            + self.WEIGHTS["success_rate"] * success_score
            + self.WEIGHTS["task_performance"] * task_score
            + self.WEIGHTS["health"] * health_score
            + self.WEIGHTS["response_time"] * response_score
        )

        # Apply overload penalty
        if load.utilization >= self.OVERLOAD_THRESHOLD:
            total_score *= 0.5

        return total_score

    def _build_reasoning(
        self,
        agent_code: str,
        score: float,
        load: Optional[AgentLoad],
    ) -> str:
        """Build human-readable reasoning for the decision."""
        if not load:
            return f"Selected {agent_code} (score: {score:.2f})"

        reasons = [f"Selected {agent_code} (score: {score:.2f})"]

        if load.available_capacity > 5:
            reasons.append("high available capacity")
        if load.success_rate_last_hour > 0.9:
            reasons.append("excellent recent success rate")
        if load.health_score > 0.9:
            reasons.append("healthy")
        if load.utilization < 0.3:
            reasons.append("low utilization")

        return " | ".join(reasons)

    def _is_cache_fresh(self, agent_code: str) -> bool:
        """Check if cached load for an agent is still fresh."""
        if agent_code not in self._load_cache:
            return False
        if not self._cache_updated_at:
            return False
        age = (datetime.now(timezone.utc) - self._cache_updated_at).total_seconds()
        return age < self._cache_ttl_seconds
