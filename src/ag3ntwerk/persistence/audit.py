"""
Decision audit trail for ag3ntwerk.

Provides comprehensive audit logging for agent decisions,
workflow executions, and system actions for compliance and debugging.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from .database import DatabaseManager, get_database

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class AuditAction(Enum):
    """Types of auditable actions."""

    # Task actions
    TASK_CREATED = "task_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"

    # Agent actions
    AGENT_DECISION = "agent_decision"
    AGENT_DELEGATION = "agent_delegation"
    AGENT_ESCALATION = "agent_escalation"

    # Workflow actions
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_STEP_COMPLETED = "workflow_step_completed"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"

    # System actions
    CONFIG_CHANGED = "config_changed"
    PLUGIN_ENABLED = "plugin_enabled"
    PLUGIN_DISABLED = "plugin_disabled"
    USER_ACTION = "user_action"

    # Security actions
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    PERMISSION_DENIED = "permission_denied"


class AuditOutcome(Enum):
    """Outcome of an audited action."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    PENDING = "pending"


@dataclass
class AuditEntry:
    """A single audit trail entry."""

    id: str = field(default_factory=lambda: str(uuid4()))
    action: AuditAction = AuditAction.USER_ACTION
    entity_type: str = "system"
    entity_id: str = ""
    actor: str = "system"
    details: Dict[str, Any] = field(default_factory=dict)
    outcome: AuditOutcome = AuditOutcome.SUCCESS
    timestamp: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "action": self.action.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "actor": self.actor,
            "details": self.details,
            "outcome": self.outcome.value,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class DecisionRecord:
    """Record of an agent decision for audit purposes."""

    decision_id: str = field(default_factory=lambda: str(uuid4()))
    agent_code: str = ""
    task_id: Optional[str] = None
    decision_type: str = "general"
    input_summary: str = ""
    output_summary: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    selected_option: str = ""
    timestamp: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "decision_id": self.decision_id,
            "agent_code": self.agent_code,
            "task_id": self.task_id,
            "decision_type": self.decision_type,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "alternatives": self.alternatives,
            "selected_option": self.selected_option,
            "timestamp": self.timestamp.isoformat(),
        }


class AuditTrail:
    """
    Audit trail for tracking decisions, actions, and system events.

    Features:
    - Comprehensive action logging
    - Decision recording with reasoning
    - Time-based querying
    - Entity-based filtering
    - Compliance reporting

    Usage:
        audit = AuditTrail()

        # Log an action
        await audit.log(
            action=AuditAction.TASK_COMPLETED,
            entity_type="task",
            entity_id="task-123",
            actor="Nexus",
            details={"duration_ms": 1500, "result": "success"},
        )

        # Record a decision
        await audit.record_decision(
            agent_code="Keystone",
            decision_type="budget_approval",
            input_summary="Budget request for $10,000",
            reasoning="Within quarterly allocation, approved based on ROI analysis",
            confidence=0.95,
        )

        # Query audit trail
        entries = await audit.query(
            entity_type="task",
            start_time=datetime.now() - timedelta(hours=24),
        )
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """Initialize audit trail."""
        self._db = db
        self._initialized = False

    async def _get_db(self) -> DatabaseManager:
        """Get database instance."""
        if self._db is None:
            self._db = await get_database()
        return self._db

    async def initialize(self) -> None:
        """Initialize the audit trail."""
        if self._initialized:
            return
        await self._get_db()
        self._initialized = True

    async def log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        actor: str = "system",
        details: Optional[Dict[str, Any]] = None,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        timestamp: Optional[datetime] = None,
    ) -> str:
        """
        Log an audit event.

        Args:
            action: Type of action being logged
            entity_type: Type of entity (task, agent, workflow, etc.)
            entity_id: Unique identifier of the entity
            actor: Who/what performed the action
            details: Additional details about the action
            outcome: Result of the action
            timestamp: When the action occurred

        Returns:
            ID of the audit entry
        """
        db = await self._get_db()

        entry = AuditEntry(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            details=details or {},
            outcome=outcome,
            timestamp=timestamp or _utcnow(),
        )

        await db.execute(
            """
            INSERT INTO audit_trail (action, entity_type, entity_id, actor, details, outcome, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.action.value,
                entry.entity_type,
                entry.entity_id,
                entry.actor,
                json.dumps(entry.details),
                entry.outcome.value,
                entry.timestamp.isoformat(),
            ),
        )

        logger.debug(f"Audit logged: {action.value} on {entity_type}/{entity_id} by {actor}")
        return entry.id

    async def record_decision(
        self,
        agent_code: str,
        decision_type: str,
        input_summary: str = "",
        output_summary: str = "",
        reasoning: str = "",
        confidence: float = 0.0,
        alternatives: Optional[List[Dict[str, Any]]] = None,
        selected_option: str = "",
        task_id: Optional[str] = None,
    ) -> str:
        """
        Record an agent decision for audit purposes.

        Args:
            agent_code: Code of the agent making the decision
            decision_type: Type of decision being made
            input_summary: Summary of input/context
            output_summary: Summary of decision output
            reasoning: Explanation of decision rationale
            confidence: Confidence level (0-1)
            alternatives: Other options considered
            selected_option: Which option was selected
            task_id: Related task ID if applicable

        Returns:
            Decision ID
        """
        db = await self._get_db()

        decision = DecisionRecord(
            agent_code=agent_code,
            task_id=task_id,
            decision_type=decision_type,
            input_summary=input_summary,
            output_summary=output_summary,
            reasoning=reasoning,
            confidence=confidence,
            alternatives=alternatives or [],
            selected_option=selected_option,
        )

        await db.execute(
            """
            INSERT INTO decision_history
            (decision_id, agent_code, task_id, decision_type, input_summary, output_summary,
             reasoning, confidence, alternatives, selected_option, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision.decision_id,
                decision.agent_code,
                decision.task_id,
                decision.decision_type,
                decision.input_summary,
                decision.output_summary,
                decision.reasoning,
                decision.confidence,
                json.dumps(decision.alternatives),
                decision.selected_option,
                decision.timestamp.isoformat(),
            ),
        )

        # Also log to general audit trail
        await self.log(
            action=AuditAction.AGENT_DECISION,
            entity_type="decision",
            entity_id=decision.decision_id,
            actor=agent_code,
            details={
                "decision_type": decision_type,
                "confidence": confidence,
                "task_id": task_id,
            },
        )

        return decision.decision_id

    async def query(
        self,
        action: Optional[AuditAction] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        actor: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        outcome: Optional[AuditOutcome] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEntry]:
        """
        Query audit trail entries.

        Args:
            action: Filter by action type
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            actor: Filter by actor
            start_time: Start of time range
            end_time: End of time range
            outcome: Filter by outcome
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of matching audit entries
        """
        db = await self._get_db()

        conditions = []
        params: List[Any] = []

        if action:
            conditions.append("action = ?")
            params.append(action.value)

        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)

        if entity_id:
            conditions.append("entity_id = ?")
            params.append(entity_id)

        if actor:
            conditions.append("actor = ?")
            params.append(actor)

        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())

        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())

        if outcome:
            conditions.append("outcome = ?")
            params.append(outcome.value)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])

        rows = await db.fetch_all(
            f"""
            SELECT id, action, entity_type, entity_id, actor, details, outcome, timestamp
            FROM audit_trail
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        )

        entries = []
        for row in rows:
            entries.append(
                AuditEntry(
                    id=str(row["id"]),
                    action=AuditAction(row["action"]),
                    entity_type=row["entity_type"],
                    entity_id=row["entity_id"],
                    actor=row["actor"],
                    details=json.loads(row["details"]) if row["details"] else {},
                    outcome=(
                        AuditOutcome(row["outcome"]) if row["outcome"] else AuditOutcome.SUCCESS
                    ),
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
            )

        return entries

    async def get_decision_history(
        self,
        agent_code: Optional[str] = None,
        task_id: Optional[str] = None,
        decision_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[DecisionRecord]:
        """
        Get decision history for analysis.

        Args:
            agent_code: Filter by agent
            task_id: Filter by task
            decision_type: Filter by decision type
            start_time: Start of time range
            limit: Maximum results

        Returns:
            List of decision records
        """
        db = await self._get_db()

        conditions = []
        params: List[Any] = []

        if agent_code:
            conditions.append("agent_code = ?")
            params.append(agent_code)

        if task_id:
            conditions.append("task_id = ?")
            params.append(task_id)

        if decision_type:
            conditions.append("decision_type = ?")
            params.append(decision_type)

        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        rows = await db.fetch_all(
            f"""
            SELECT decision_id, agent_code, task_id, decision_type, input_summary,
                   output_summary, reasoning, confidence, alternatives, selected_option, timestamp
            FROM decision_history
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            tuple(params),
        )

        records = []
        for row in rows:
            records.append(
                DecisionRecord(
                    decision_id=row["decision_id"],
                    agent_code=row["agent_code"],
                    task_id=row["task_id"],
                    decision_type=row["decision_type"],
                    input_summary=row["input_summary"] or "",
                    output_summary=row["output_summary"] or "",
                    reasoning=row["reasoning"] or "",
                    confidence=row["confidence"] or 0.0,
                    alternatives=json.loads(row["alternatives"]) if row["alternatives"] else [],
                    selected_option=row["selected_option"] or "",
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
            )

        return records

    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50,
    ) -> List[AuditEntry]:
        """
        Get complete audit history for a specific entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity identifier
            limit: Maximum results

        Returns:
            List of audit entries for the entity
        """
        return await self.query(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
        )

    async def generate_compliance_report(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Generate a compliance report for a time period.

        Args:
            start_time: Report start time
            end_time: Report end time (defaults to now)

        Returns:
            Compliance report dictionary
        """
        db = await self._get_db()
        end_time = end_time or _utcnow()

        # Get action counts
        action_counts = await db.fetch_all(
            """
            SELECT action, outcome, COUNT(*) as count
            FROM audit_trail
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY action, outcome
            """,
            (start_time.isoformat(), end_time.isoformat()),
        )

        # Get decision statistics
        decision_stats = await db.fetch_one(
            """
            SELECT
                COUNT(*) as total_decisions,
                AVG(confidence) as avg_confidence,
                COUNT(DISTINCT agent_code) as unique_agents
            FROM decision_history
            WHERE timestamp >= ? AND timestamp <= ?
            """,
            (start_time.isoformat(), end_time.isoformat()),
        )

        # Get failure summary
        failures = await db.fetch_all(
            """
            SELECT action, entity_type, COUNT(*) as count
            FROM audit_trail
            WHERE timestamp >= ? AND timestamp <= ? AND outcome = 'failure'
            GROUP BY action, entity_type
            ORDER BY count DESC
            LIMIT 10
            """,
            (start_time.isoformat(), end_time.isoformat()),
        )

        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "action_summary": [
                {"action": row["action"], "outcome": row["outcome"], "count": row["count"]}
                for row in action_counts
            ],
            "decision_statistics": {
                "total_decisions": decision_stats["total_decisions"] if decision_stats else 0,
                "avg_confidence": (
                    round(decision_stats["avg_confidence"] or 0, 3) if decision_stats else 0
                ),
                "unique_agents": decision_stats["unique_agents"] if decision_stats else 0,
            },
            "failure_summary": [
                {"action": row["action"], "entity_type": row["entity_type"], "count": row["count"]}
                for row in failures
            ],
            "generated_at": _utcnow().isoformat(),
        }

    async def cleanup_old_entries(self, retention_days: int = 90) -> int:
        """
        Remove audit entries older than retention period.

        Args:
            retention_days: Days of data to keep

        Returns:
            Number of entries deleted
        """
        db = await self._get_db()
        cutoff = (_utcnow() - timedelta(days=retention_days)).isoformat()

        audit_deleted = await db.execute(
            "DELETE FROM audit_trail WHERE timestamp < ?",
            (cutoff,),
        )

        decision_deleted = await db.execute(
            "DELETE FROM decision_history WHERE timestamp < ?",
            (cutoff,),
        )

        return audit_deleted + decision_deleted


# Convenience functions
async def log_action(
    action: AuditAction,
    entity_type: str,
    entity_id: str,
    actor: str = "system",
    details: Optional[Dict[str, Any]] = None,
) -> str:
    """Log an audit action using the default trail."""
    trail = AuditTrail()
    return await trail.log(action, entity_type, entity_id, actor, details)


async def record_agent_decision(
    agent_code: str,
    decision_type: str,
    reasoning: str,
    confidence: float = 0.0,
    **kwargs,
) -> str:
    """Record an agent decision using the default trail."""
    trail = AuditTrail()
    return await trail.record_decision(
        agent_code=agent_code,
        decision_type=decision_type,
        reasoning=reasoning,
        confidence=confidence,
        **kwargs,
    )
