"""
Cascade prediction for the ag3ntwerk learning system.

Predicts downstream effects of routing decisions to enable
better decision-making and risk assessment.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .models import TaskOutcomeRecord
from .outcome_tracker import OutcomeTracker
from .pattern_store import PatternStore


class RiskLevel(str, Enum):
    """Risk levels for cascade effects."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactType(str, Enum):
    """Types of downstream impact."""

    LOAD_INCREASE = "load_increase"
    DELAY_PROPAGATION = "delay_propagation"
    FAILURE_CASCADE = "failure_cascade"
    RESOURCE_CONTENTION = "resource_contention"
    BOTTLENECK = "bottleneck"


@dataclass
class AgentLoad:
    """Current and projected load for an agent."""

    agent_code: str
    current_load: float
    projected_load: float
    capacity: float
    utilization: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "current_load": self.current_load,
            "projected_load": self.projected_load,
            "capacity": self.capacity,
            "utilization": self.utilization,
        }


@dataclass
class DownstreamAgent:
    """An agent that will be affected downstream."""

    agent_code: str
    probability: float
    expected_tasks: int
    impact_type: ImpactType
    estimated_delay_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "probability": self.probability,
            "expected_tasks": self.expected_tasks,
            "impact_type": self.impact_type.value,
            "estimated_delay_ms": self.estimated_delay_ms,
        }


@dataclass
class CascadeRisk:
    """Risk assessment for a cascade effect."""

    risk_level: RiskLevel
    risk_score: float
    risk_factors: List[str]
    mitigation_suggestions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "risk_factors": self.risk_factors,
            "mitigation_suggestions": self.mitigation_suggestions,
        }


@dataclass
class RoutingDecision:
    """A routing decision to analyze."""

    task_type: str
    selected_agent: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    estimated_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "selected_agent": self.selected_agent,
            "context": self.context,
            "priority": self.priority,
            "estimated_duration_ms": self.estimated_duration_ms,
        }


@dataclass
class CascadeEffect:
    """Complete cascade effect prediction."""

    prediction_id: str
    created_at: datetime
    decision: RoutingDecision
    primary_agent_load: AgentLoad
    downstream_agents: List[DownstreamAgent]
    expected_duration: float
    risk: CascadeRisk
    alternative_routes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "created_at": self.created_at.isoformat(),
            "decision": self.decision.to_dict(),
            "primary_agent_load": self.primary_agent_load.to_dict(),
            "downstream_agents": [d.to_dict() for d in self.downstream_agents],
            "expected_duration": self.expected_duration,
            "risk": self.risk.to_dict(),
            "alternative_routes": self.alternative_routes,
        }


@dataclass
class CascadeHistoryEntry:
    """Historical cascade record for learning."""

    decision_id: str
    task_type: str
    selected_agent: str
    downstream_agents: List[str]
    actual_duration_ms: float
    predicted_duration_ms: float
    had_failures: bool
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "task_type": self.task_type,
            "selected_agent": self.selected_agent,
            "downstream_agents": self.downstream_agents,
            "actual_duration_ms": self.actual_duration_ms,
            "predicted_duration_ms": self.predicted_duration_ms,
            "had_failures": self.had_failures,
            "created_at": self.created_at.isoformat(),
        }


class CascadePredictor:
    """
    Predicts downstream effects of routing decisions.

    Analyzes historical task flows to understand how decisions
    cascade through the agent hierarchy, enabling:
    - Load estimation for downstream agents
    - Duration prediction for task chains
    - Risk assessment for routing decisions
    - Alternative route suggestions
    """

    # Default capacity per agent
    DEFAULT_CAPACITY = 100.0

    # Load threshold for high utilization
    HIGH_UTILIZATION_THRESHOLD = 0.8

    # History window for pattern analysis
    HISTORY_WINDOW_HOURS = 168

    def __init__(
        self,
        db: Any,
        outcome_tracker: OutcomeTracker,
        pattern_store: PatternStore,
    ):
        self._db = db
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store
        self._agent_capacities: Dict[str, float] = {}

    async def predict_cascade(
        self,
        decision: RoutingDecision,
    ) -> CascadeEffect:
        """
        Predict cascade effects of a routing decision.

        Args:
            decision: The routing decision to analyze

        Returns:
            Complete cascade effect prediction
        """
        import uuid

        # Get similar historical decisions
        similar_decisions = await self._get_similar_decisions(decision)

        # Trace downstream effects
        downstream_outcomes = await self._trace_downstream(similar_decisions)

        # Estimate primary agent load
        primary_load = await self._estimate_load(decision.selected_agent)

        # Identify downstream agents
        downstream_agents = self._identify_downstream(similar_decisions, downstream_outcomes)

        # Estimate total duration
        expected_duration = self._estimate_total_duration(decision, downstream_outcomes)

        # Calculate cascade risk
        risk = self._calculate_cascade_risk(primary_load, downstream_agents, downstream_outcomes)

        # Find alternative routes
        alternatives = await self._find_alternative_routes(decision, primary_load, risk)

        return CascadeEffect(
            prediction_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            decision=decision,
            primary_agent_load=primary_load,
            downstream_agents=downstream_agents,
            expected_duration=expected_duration,
            risk=risk,
            alternative_routes=alternatives,
        )

    async def _get_similar_decisions(
        self,
        decision: RoutingDecision,
    ) -> List[Dict[str, Any]]:
        """Get historically similar routing decisions."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.HISTORY_WINDOW_HOURS)

        query = """
            SELECT
                rd.id,
                rd.task_type,
                rd.selected_agent,
                rd.context,
                rd.created_at,
                lo.success,
                lo.duration_ms
            FROM routing_decisions rd
            LEFT JOIN learning_outcomes lo ON rd.task_id = lo.task_id
            WHERE rd.task_type = ?
            AND rd.created_at >= ?
            ORDER BY rd.created_at DESC
            LIMIT 100
        """

        rows = await self._db.fetch_all(query, [decision.task_type, cutoff.isoformat()])

        return [
            {
                "id": row["id"],
                "task_type": row["task_type"],
                "selected_agent": row["selected_agent"],
                "context": json.loads(row["context"]) if row["context"] else {},
                "created_at": row["created_at"],
                "success": row["success"],
                "duration_ms": row["duration_ms"],
            }
            for row in rows
        ]

    async def _trace_downstream(
        self,
        similar_decisions: List[Dict[str, Any]],
    ) -> List[TaskOutcomeRecord]:
        """Trace downstream effects of similar decisions."""
        if not similar_decisions:
            return []

        # Get agent codes that handled similar tasks
        agents = set(d["selected_agent"] for d in similar_decisions)

        # Find tasks that followed (were delegated by) these agents
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.HISTORY_WINDOW_HOURS)

        placeholders = ",".join("?" * len(agents))
        query = f"""
            SELECT *
            FROM learning_outcomes
            WHERE agent_code IN ({placeholders})
            AND created_at >= ?
            ORDER BY created_at DESC
            LIMIT 500
        """

        params = list(agents) + [cutoff.isoformat()]
        rows = await self._db.fetch_all(query, params)

        outcomes = []
        for row in rows:
            outcomes.append(
                TaskOutcomeRecord(
                    id=row["id"],
                    task_id=row["task_id"],
                    task_type=row["task_type"],
                    agent_code=row["agent_code"],
                    manager_code=row.get("manager_code"),
                    specialist_code=row.get("specialist_code"),
                    success=bool(row["success"]),
                    duration_ms=row.get("duration_ms", 0.0),
                    error_message=row.get("error_message"),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )

        return outcomes

    async def _estimate_load(self, agent_code: str) -> AgentLoad:
        """Estimate current and projected load for an agent."""
        # Get recent task count
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

        query = """
            SELECT COUNT(*) as count
            FROM learning_outcomes
            WHERE agent_code = ?
            AND created_at >= ?
        """

        row = await self._db.fetch_one(query, [agent_code, cutoff.isoformat()])
        current_load = float(row["count"]) if row else 0.0

        # Get capacity (use cached or default)
        capacity = self._agent_capacities.get(agent_code, self.DEFAULT_CAPACITY)

        # Project load (assume 10% increase for new task)
        projected_load = current_load + 1

        utilization = current_load / capacity if capacity > 0 else 0.0

        return AgentLoad(
            agent_code=agent_code,
            current_load=current_load,
            projected_load=projected_load,
            capacity=capacity,
            utilization=min(1.0, utilization),
        )

    def _identify_downstream(
        self,
        similar_decisions: List[Dict[str, Any]],
        downstream_outcomes: List[TaskOutcomeRecord],
    ) -> List[DownstreamAgent]:
        """Identify agents that will be affected downstream."""
        if not downstream_outcomes:
            return []

        # Count downstream agents and their characteristics
        agent_stats: Dict[str, Dict[str, Any]] = {}

        for outcome in downstream_outcomes:
            # Track manager as downstream
            if outcome.manager_code:
                if outcome.manager_code not in agent_stats:
                    agent_stats[outcome.manager_code] = {
                        "count": 0,
                        "durations": [],
                        "failures": 0,
                    }
                agent_stats[outcome.manager_code]["count"] += 1
                agent_stats[outcome.manager_code]["durations"].append(outcome.duration_ms)
                if not outcome.success:
                    agent_stats[outcome.manager_code]["failures"] += 1

            # Track specialist as downstream
            if outcome.specialist_code:
                if outcome.specialist_code not in agent_stats:
                    agent_stats[outcome.specialist_code] = {
                        "count": 0,
                        "durations": [],
                        "failures": 0,
                    }
                agent_stats[outcome.specialist_code]["count"] += 1
                agent_stats[outcome.specialist_code]["durations"].append(outcome.duration_ms)
                if not outcome.success:
                    agent_stats[outcome.specialist_code]["failures"] += 1

        total = len(downstream_outcomes)
        downstream_agents = []

        for agent_code, stats in agent_stats.items():
            probability = stats["count"] / total if total > 0 else 0.0
            avg_duration = (
                sum(stats["durations"]) / len(stats["durations"]) if stats["durations"] else 0.0
            )
            failure_rate = stats["failures"] / stats["count"] if stats["count"] > 0 else 0.0

            # Determine impact type
            if failure_rate > 0.3:
                impact_type = ImpactType.FAILURE_CASCADE
            elif probability > 0.8:
                impact_type = ImpactType.BOTTLENECK
            elif avg_duration > 5000:
                impact_type = ImpactType.DELAY_PROPAGATION
            else:
                impact_type = ImpactType.LOAD_INCREASE

            downstream_agents.append(
                DownstreamAgent(
                    agent_code=agent_code,
                    probability=probability,
                    expected_tasks=stats["count"],
                    impact_type=impact_type,
                    estimated_delay_ms=avg_duration,
                )
            )

        # Sort by probability
        downstream_agents.sort(key=lambda x: x.probability, reverse=True)
        return downstream_agents[:10]  # Top 10

    def _estimate_total_duration(
        self,
        decision: RoutingDecision,
        downstream_outcomes: List[TaskOutcomeRecord],
    ) -> float:
        """Estimate total duration including cascade effects."""
        if not downstream_outcomes:
            return decision.estimated_duration_ms or 1000.0

        # Calculate average duration from similar outcomes
        durations = [o.duration_ms for o in downstream_outcomes if o.duration_ms > 0]

        if not durations:
            return decision.estimated_duration_ms or 1000.0

        import statistics

        avg_duration = statistics.mean(durations)

        # Add buffer for cascade effects
        cascade_factor = 1.2  # 20% overhead for coordination
        return avg_duration * cascade_factor

    def _calculate_cascade_risk(
        self,
        primary_load: AgentLoad,
        downstream_agents: List[DownstreamAgent],
        downstream_outcomes: List[TaskOutcomeRecord],
    ) -> CascadeRisk:
        """Calculate risk level for the cascade."""
        risk_factors = []
        risk_score = 0.0

        # Check primary agent utilization
        if primary_load.utilization > self.HIGH_UTILIZATION_THRESHOLD:
            risk_factors.append(
                f"Primary agent {primary_load.agent_code} at "
                f"{primary_load.utilization:.0%} utilization"
            )
            risk_score += 0.3

        # Check for failure cascade risk
        failure_agents = [
            a for a in downstream_agents if a.impact_type == ImpactType.FAILURE_CASCADE
        ]
        if failure_agents:
            risk_factors.append(f"{len(failure_agents)} downstream agents with high failure rates")
            risk_score += 0.3

        # Check for bottlenecks
        bottleneck_agents = [a for a in downstream_agents if a.impact_type == ImpactType.BOTTLENECK]
        if bottleneck_agents:
            risk_factors.append(f"{len(bottleneck_agents)} potential bottleneck agents")
            risk_score += 0.2

        # Check historical failure rate
        if downstream_outcomes:
            failures = sum(1 for o in downstream_outcomes if not o.success)
            failure_rate = failures / len(downstream_outcomes)
            if failure_rate > 0.2:
                risk_factors.append(f"Historical failure rate: {failure_rate:.0%}")
                risk_score += 0.2

        # Determine risk level
        if risk_score >= 0.7:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 0.5:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 0.3:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Generate mitigation suggestions
        mitigation_suggestions = self._generate_mitigations(
            risk_factors, primary_load, downstream_agents
        )

        return CascadeRisk(
            risk_level=risk_level,
            risk_score=min(1.0, risk_score),
            risk_factors=risk_factors,
            mitigation_suggestions=mitigation_suggestions,
        )

    def _generate_mitigations(
        self,
        risk_factors: List[str],
        primary_load: AgentLoad,
        downstream_agents: List[DownstreamAgent],
    ) -> List[str]:
        """Generate risk mitigation suggestions."""
        suggestions = []

        if primary_load.utilization > self.HIGH_UTILIZATION_THRESHOLD:
            suggestions.append(
                f"Consider routing to alternative agent to reduce "
                f"{primary_load.agent_code} load"
            )

        failure_agents = [
            a for a in downstream_agents if a.impact_type == ImpactType.FAILURE_CASCADE
        ]
        if failure_agents:
            suggestions.append("Implement retry logic or circuit breaker for failure-prone paths")

        bottleneck_agents = [a for a in downstream_agents if a.impact_type == ImpactType.BOTTLENECK]
        if bottleneck_agents:
            suggestions.append("Consider parallel processing or load distribution")

        if not suggestions:
            suggestions.append("No immediate mitigation required")

        return suggestions

    async def _find_alternative_routes(
        self,
        decision: RoutingDecision,
        primary_load: AgentLoad,
        risk: CascadeRisk,
    ) -> List[Dict[str, Any]]:
        """Find alternative routing options."""
        if risk.risk_level == RiskLevel.LOW:
            return []

        # Get other agents that handle this task type
        query = """
            SELECT DISTINCT agent_code, COUNT(*) as count,
                   AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate,
                   AVG(duration_ms) as avg_duration
            FROM learning_outcomes
            WHERE task_type = ?
            AND agent_code != ?
            GROUP BY agent_code
            HAVING count >= 5
            ORDER BY success_rate DESC, avg_duration ASC
            LIMIT 3
        """

        rows = await self._db.fetch_all(query, [decision.task_type, decision.selected_agent])

        alternatives = []
        for row in rows:
            alternatives.append(
                {
                    "agent_code": row["agent_code"],
                    "success_rate": row["success_rate"],
                    "avg_duration_ms": row["avg_duration"],
                    "sample_size": row["count"],
                }
            )

        return alternatives

    async def record_cascade_outcome(
        self,
        prediction_id: str,
        actual_duration_ms: float,
        had_failures: bool,
        downstream_agents_used: List[str],
    ) -> None:
        """Record actual cascade outcome for learning."""
        await self._db.execute(
            """
            INSERT INTO cascade_outcomes (
                prediction_id, actual_duration_ms, had_failures,
                downstream_agents, recorded_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                prediction_id,
                actual_duration_ms,
                had_failures,
                json.dumps(downstream_agents_used),
                datetime.now(timezone.utc).isoformat(),
            ],
        )

    async def get_cascade_accuracy(
        self,
        window_hours: int = 168,
    ) -> Dict[str, Any]:
        """Calculate prediction accuracy over time window."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        query = """
            SELECT
                AVG(ABS(actual_duration_ms - predicted_duration_ms) /
                    NULLIF(actual_duration_ms, 0)) as duration_error,
                AVG(CASE WHEN predicted_failures = had_failures THEN 1 ELSE 0 END)
                    as failure_accuracy,
                COUNT(*) as sample_size
            FROM cascade_outcomes
            WHERE recorded_at >= ?
        """

        row = await self._db.fetch_one(query, [cutoff.isoformat()])

        if not row or row["sample_size"] == 0:
            return {
                "duration_error": None,
                "failure_accuracy": None,
                "sample_size": 0,
            }

        return {
            "duration_error": row["duration_error"],
            "failure_accuracy": row["failure_accuracy"],
            "sample_size": row["sample_size"],
        }

    def set_agent_capacity(self, agent_code: str, capacity: float) -> None:
        """Set capacity for an agent."""
        self._agent_capacities[agent_code] = capacity

    async def save_prediction(self, prediction: CascadeEffect) -> None:
        """Save cascade prediction for tracking."""
        await self._db.execute(
            """
            INSERT INTO cascade_predictions (
                id, created_at, task_type, selected_agent,
                expected_duration, risk_level, risk_score,
                downstream_agents_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                prediction.prediction_id,
                prediction.created_at.isoformat(),
                prediction.decision.task_type,
                prediction.decision.selected_agent,
                prediction.expected_duration,
                prediction.risk.risk_level.value,
                prediction.risk.risk_score,
                json.dumps([d.to_dict() for d in prediction.downstream_agents]),
            ],
        )
