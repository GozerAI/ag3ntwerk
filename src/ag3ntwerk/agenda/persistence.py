"""
Persistence layer for the Autonomous Agenda Engine.

This module provides SQLite-based storage for:
1. Workstreams - Goal decomposition results
2. Obstacles - Detected constraints and blocks
3. Strategies - Generated resolution plans
4. Agendas - Generated agendas with items
5. Audit Trail - Security-relevant action logs

The persistence layer supports:
- CRUD operations for all entity types
- Querying with filters
- Agenda history tracking
- Audit trail retention
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.agenda.models import (
    Agenda,
    AgendaItem,
    AuditEntry,
    Checkpoint,
    ConfidenceLevel,
    HITLConfig,
    Obstacle,
    ObstacleType,
    RiskAssessment,
    RiskCategory,
    RiskLevel,
    Strategy,
    StrategyType,
    Workstream,
    WorkstreamStatus,
)

logger = get_logger(__name__)


# =============================================================================
# Database Schema
# =============================================================================

SCHEMA = """
-- Workstreams table
CREATE TABLE IF NOT EXISTS workstreams (
    id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL,
    milestone_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    objective TEXT,
    capability_requirements TEXT,  -- JSON
    executive_mapping TEXT,  -- JSON
    estimated_task_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    progress REAL DEFAULT 0.0,
    task_ids TEXT,  -- JSON array
    completed_task_ids TEXT,  -- JSON array
    failed_task_ids TEXT,  -- JSON array
    obstacle_ids TEXT,  -- JSON array
    strategy_ids TEXT,  -- JSON array
    dependency_workstream_ids TEXT,  -- JSON array
    estimated_duration_hours REAL DEFAULT 0.0,
    estimated_completion TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);

-- Obstacles table
CREATE TABLE IF NOT EXISTS obstacles (
    id TEXT PRIMARY KEY,
    obstacle_type TEXT NOT NULL,
    severity REAL DEFAULT 0.5,
    goal_id TEXT,
    milestone_id TEXT,
    workstream_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    evidence TEXT,  -- JSON array
    detected_at TEXT NOT NULL,
    detected_by TEXT,
    related_failures TEXT,  -- JSON array
    related_task_types TEXT,  -- JSON array
    status TEXT DEFAULT 'active',
    resolved_at TEXT,
    resolved_by TEXT,
    resolution_strategy_id TEXT,
    FOREIGN KEY (workstream_id) REFERENCES workstreams(id)
);

-- Strategies table
CREATE TABLE IF NOT EXISTS strategies (
    id TEXT PRIMARY KEY,
    strategy_type TEXT NOT NULL,
    obstacle_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    rationale TEXT,
    implementation_steps TEXT,  -- JSON array
    estimated_effort_hours REAL DEFAULT 0.0,
    estimated_cost_usd REAL DEFAULT 0.0,
    confidence REAL DEFAULT 0.5,
    impact_score REAL DEFAULT 0.5,
    feasibility_score REAL DEFAULT 0.5,
    priority_score REAL DEFAULT 0.0,
    generated_task_specs TEXT,  -- JSON array
    parameter_adjustments TEXT,  -- JSON
    routing_changes TEXT,  -- JSON
    retry_policy_changes TEXT,  -- JSON
    proposed_tool TEXT,
    proposed_integration TEXT,
    tool_requirements TEXT,  -- JSON array
    scope_changes TEXT,
    timeline_changes TEXT,
    success_criteria_changes TEXT,
    milestone_changes TEXT,  -- JSON array
    status TEXT DEFAULT 'proposed',
    created_at TEXT NOT NULL,
    approved_at TEXT,
    approved_by TEXT,
    executed_at TEXT,
    outcome TEXT,
    FOREIGN KEY (obstacle_id) REFERENCES obstacles(id)
);

-- Agendas table
CREATE TABLE IF NOT EXISTS agendas (
    id TEXT PRIMARY KEY,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    period_type TEXT DEFAULT 'daily',
    total_estimated_duration_minutes REAL DEFAULT 0.0,
    total_estimated_cost_usd REAL DEFAULT 0.0,
    goals_addressed TEXT,  -- JSON array
    milestones_addressed TEXT,  -- JSON array
    obstacles_addressed TEXT,  -- JSON array
    workstreams_addressed TEXT,  -- JSON array
    executive_distribution TEXT,  -- JSON
    goal_distribution TEXT,  -- JSON
    obstacle_resolution_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft',
    items_completed INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    items_skipped INTEGER DEFAULT 0,
    items_pending_approval INTEGER DEFAULT 0,
    generated_at TEXT NOT NULL,
    generated_by TEXT DEFAULT 'agenda_engine',
    generation_context TEXT  -- JSON
);

-- Agenda Items table
CREATE TABLE IF NOT EXISTS agenda_items (
    id TEXT PRIMARY KEY,
    agenda_id TEXT NOT NULL,
    goal_id TEXT,
    workstream_id TEXT,
    milestone_id TEXT,
    strategy_id TEXT,
    task_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    context TEXT,  -- JSON
    recommended_agent TEXT,
    alternative_executives TEXT,  -- JSON array
    priority_score REAL DEFAULT 0.0,
    confidence_level TEXT DEFAULT 'medium',
    confidence_score REAL DEFAULT 0.5,
    dependencies TEXT,  -- JSON array
    estimated_duration_minutes REAL DEFAULT 15.0,
    estimated_cost_usd REAL DEFAULT 0.5,
    retry_policy TEXT,  -- JSON
    timeout_seconds INTEGER DEFAULT 300,
    is_obstacle_resolution INTEGER DEFAULT 0,
    resolves_obstacle_id TEXT,
    risk_assessment TEXT,  -- JSON
    checkpoint TEXT,  -- JSON
    requires_approval INTEGER DEFAULT 0,
    approval_status TEXT DEFAULT 'not_required',
    approved_by TEXT,
    approved_at TEXT,
    status TEXT DEFAULT 'pending',
    executed_at TEXT,
    completed_at TEXT,
    execution_result TEXT,  -- JSON
    created_at TEXT NOT NULL,
    FOREIGN KEY (agenda_id) REFERENCES agendas(id),
    FOREIGN KEY (workstream_id) REFERENCES workstreams(id),
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);

-- Audit Trail table
CREATE TABLE IF NOT EXISTS audit_trail (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    action_type TEXT NOT NULL,
    item_id TEXT,
    strategy_id TEXT,
    checkpoint_id TEXT,
    agenda_id TEXT,
    actor TEXT NOT NULL,
    actor_role TEXT,
    risk_level TEXT,
    risk_score REAL,
    decision TEXT,
    reason TEXT,
    context TEXT  -- JSON
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_workstreams_goal ON workstreams(goal_id);
CREATE INDEX IF NOT EXISTS idx_workstreams_status ON workstreams(status);
CREATE INDEX IF NOT EXISTS idx_obstacles_workstream ON obstacles(workstream_id);
CREATE INDEX IF NOT EXISTS idx_obstacles_status ON obstacles(status);
CREATE INDEX IF NOT EXISTS idx_strategies_obstacle ON strategies(obstacle_id);
CREATE INDEX IF NOT EXISTS idx_agenda_items_agenda ON agenda_items(agenda_id);
CREATE INDEX IF NOT EXISTS idx_agenda_items_status ON agenda_items(status);
CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp ON audit_trail(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_trail_action ON audit_trail(action_type);
"""


# =============================================================================
# Agenda Persistence
# =============================================================================


class AgendaPersistence:
    """
    SQLite-based persistence for agenda engine state.

    Stores and retrieves:
    - Workstreams
    - Obstacles
    - Strategies
    - Agendas and agenda items
    - Audit trail entries

    Example:
        persistence = AgendaPersistence("agenda.db")
        await persistence.initialize()

        # Save agenda
        await persistence.save_agenda(agenda)

        # Load agenda
        agenda = await persistence.load_agenda(agenda_id)

        # Query audit trail
        entries = await persistence.get_audit_trail(start_time=yesterday)
    """

    def __init__(self, db_path: str = "agenda.db"):
        """
        Initialize persistence layer.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._initialized = False

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection as context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    async def initialize(self) -> None:
        """Initialize database with schema."""
        if self._initialized:
            return

        with self._get_connection() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

        self._initialized = True
        logger.info(f"Initialized agenda database at {self.db_path}")

    def _ensure_initialized(self) -> None:
        """Ensure database is initialized."""
        if not self._initialized:
            import asyncio

            asyncio.get_event_loop().run_until_complete(self.initialize())

    # =========================================================================
    # Workstream Operations
    # =========================================================================

    async def save_workstream(self, workstream: Workstream) -> None:
        """Save a workstream to the database."""
        self._ensure_initialized()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO workstreams (
                    id, goal_id, milestone_id, title, description, objective,
                    capability_requirements, executive_mapping, estimated_task_count,
                    status, progress, task_ids, completed_task_ids, failed_task_ids,
                    obstacle_ids, strategy_ids, dependency_workstream_ids,
                    estimated_duration_hours, estimated_completion, created_at,
                    started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workstream.id,
                    workstream.goal_id,
                    workstream.milestone_id,
                    workstream.title,
                    workstream.description,
                    workstream.objective,
                    json.dumps([r.to_dict() for r in workstream.capability_requirements]),
                    json.dumps(workstream.executive_mapping),
                    workstream.estimated_task_count,
                    workstream.status.value,
                    workstream.progress,
                    json.dumps(workstream.task_ids),
                    json.dumps(workstream.completed_task_ids),
                    json.dumps(workstream.failed_task_ids),
                    json.dumps(workstream.obstacle_ids),
                    json.dumps(workstream.strategy_ids),
                    json.dumps(workstream.dependency_workstream_ids),
                    workstream.estimated_duration_hours,
                    (
                        workstream.estimated_completion.isoformat()
                        if workstream.estimated_completion
                        else None
                    ),
                    workstream.created_at.isoformat(),
                    workstream.started_at.isoformat() if workstream.started_at else None,
                    workstream.completed_at.isoformat() if workstream.completed_at else None,
                ),
            )
            conn.commit()

    async def load_workstream(self, workstream_id: str) -> Optional[Workstream]:
        """Load a workstream by ID."""
        self._ensure_initialized()

        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM workstreams WHERE id = ?", (workstream_id,)
            ).fetchone()

        if not row:
            return None

        return self._row_to_workstream(row)

    async def list_workstreams(
        self,
        goal_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Workstream]:
        """List workstreams with optional filters."""
        self._ensure_initialized()

        query = "SELECT * FROM workstreams WHERE 1=1"
        params = []

        if goal_id:
            query += " AND goal_id = ?"
            params.append(goal_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_workstream(row) for row in rows]

    def _row_to_workstream(self, row: sqlite3.Row) -> Workstream:
        """Convert database row to Workstream object."""
        from ag3ntwerk.agenda.models import CapabilityRequirement

        cap_reqs_data = json.loads(row["capability_requirements"] or "[]")
        cap_reqs = []
        for data in cap_reqs_data:
            req = CapabilityRequirement(
                id=data.get("id", ""),
                name=data.get("name", ""),
                description=data.get("description", ""),
                task_type=data.get("task_type", ""),
                tool_category=data.get("tool_category"),
                agent_code=data.get("agent_code"),
                is_available=data.get("is_available", False),
                availability_confidence=data.get("availability_confidence", 0.0),
                alternative_approaches=data.get("alternative_approaches", []),
                inferred_from=data.get("inferred_from", ""),
            )
            cap_reqs.append(req)

        return Workstream(
            id=row["id"],
            goal_id=row["goal_id"],
            milestone_id=row["milestone_id"],
            title=row["title"],
            description=row["description"] or "",
            objective=row["objective"] or "",
            capability_requirements=cap_reqs,
            executive_mapping=json.loads(row["executive_mapping"] or "{}"),
            estimated_task_count=row["estimated_task_count"],
            status=WorkstreamStatus(row["status"]),
            progress=row["progress"],
            task_ids=json.loads(row["task_ids"] or "[]"),
            completed_task_ids=json.loads(row["completed_task_ids"] or "[]"),
            failed_task_ids=json.loads(row["failed_task_ids"] or "[]"),
            obstacle_ids=json.loads(row["obstacle_ids"] or "[]"),
            strategy_ids=json.loads(row["strategy_ids"] or "[]"),
            dependency_workstream_ids=json.loads(row["dependency_workstream_ids"] or "[]"),
            estimated_duration_hours=row["estimated_duration_hours"],
            estimated_completion=(
                datetime.fromisoformat(row["estimated_completion"])
                if row["estimated_completion"]
                else None
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=(
                datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
            ),
        )

    # =========================================================================
    # Obstacle Operations
    # =========================================================================

    async def save_obstacle(self, obstacle: Obstacle) -> None:
        """Save an obstacle to the database."""
        self._ensure_initialized()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO obstacles (
                    id, obstacle_type, severity, goal_id, milestone_id, workstream_id,
                    title, description, evidence, detected_at, detected_by,
                    related_failures, related_task_types, status, resolved_at,
                    resolved_by, resolution_strategy_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    obstacle.id,
                    obstacle.obstacle_type.value,
                    obstacle.severity,
                    obstacle.goal_id,
                    obstacle.milestone_id,
                    obstacle.workstream_id,
                    obstacle.title,
                    obstacle.description,
                    json.dumps(obstacle.evidence),
                    obstacle.detected_at.isoformat(),
                    obstacle.detected_by,
                    json.dumps(obstacle.related_failures),
                    json.dumps(obstacle.related_task_types),
                    obstacle.status,
                    obstacle.resolved_at.isoformat() if obstacle.resolved_at else None,
                    obstacle.resolved_by,
                    obstacle.resolution_strategy_id,
                ),
            )
            conn.commit()

    async def load_obstacle(self, obstacle_id: str) -> Optional[Obstacle]:
        """Load an obstacle by ID."""
        self._ensure_initialized()

        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM obstacles WHERE id = ?", (obstacle_id,)).fetchone()

        if not row:
            return None

        return self._row_to_obstacle(row)

    async def list_obstacles(
        self,
        goal_id: Optional[str] = None,
        workstream_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Obstacle]:
        """List obstacles with optional filters."""
        self._ensure_initialized()

        query = "SELECT * FROM obstacles WHERE 1=1"
        params = []

        if goal_id:
            query += " AND goal_id = ?"
            params.append(goal_id)

        if workstream_id:
            query += " AND workstream_id = ?"
            params.append(workstream_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY severity DESC, detected_at DESC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_obstacle(row) for row in rows]

    def _row_to_obstacle(self, row: sqlite3.Row) -> Obstacle:
        """Convert database row to Obstacle object."""
        return Obstacle(
            id=row["id"],
            obstacle_type=ObstacleType(row["obstacle_type"]),
            severity=row["severity"],
            goal_id=row["goal_id"],
            milestone_id=row["milestone_id"],
            workstream_id=row["workstream_id"],
            title=row["title"],
            description=row["description"] or "",
            evidence=json.loads(row["evidence"] or "[]"),
            detected_at=datetime.fromisoformat(row["detected_at"]),
            detected_by=row["detected_by"] or "",
            related_failures=json.loads(row["related_failures"] or "[]"),
            related_task_types=json.loads(row["related_task_types"] or "[]"),
            status=row["status"],
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
            resolved_by=row["resolved_by"],
            resolution_strategy_id=row["resolution_strategy_id"],
        )

    # =========================================================================
    # Strategy Operations
    # =========================================================================

    async def save_strategy(self, strategy: Strategy) -> None:
        """Save a strategy to the database."""
        self._ensure_initialized()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO strategies (
                    id, strategy_type, obstacle_id, title, description, rationale,
                    implementation_steps, estimated_effort_hours, estimated_cost_usd,
                    confidence, impact_score, feasibility_score, priority_score,
                    generated_task_specs, parameter_adjustments, routing_changes,
                    retry_policy_changes, proposed_tool, proposed_integration,
                    tool_requirements, scope_changes, timeline_changes,
                    success_criteria_changes, milestone_changes, status, created_at,
                    approved_at, approved_by, executed_at, outcome
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy.id,
                    strategy.strategy_type.value,
                    strategy.obstacle_id,
                    strategy.title,
                    strategy.description,
                    strategy.rationale,
                    json.dumps(strategy.implementation_steps),
                    strategy.estimated_effort_hours,
                    strategy.estimated_cost_usd,
                    strategy.confidence,
                    strategy.impact_score,
                    strategy.feasibility_score,
                    strategy.priority_score,
                    json.dumps(strategy.generated_task_specs),
                    json.dumps(strategy.parameter_adjustments),
                    json.dumps(strategy.routing_changes),
                    json.dumps(strategy.retry_policy_changes),
                    strategy.proposed_tool,
                    strategy.proposed_integration,
                    json.dumps(strategy.tool_requirements),
                    strategy.scope_changes,
                    strategy.timeline_changes,
                    strategy.success_criteria_changes,
                    json.dumps(strategy.milestone_changes),
                    strategy.status,
                    strategy.created_at.isoformat(),
                    strategy.approved_at.isoformat() if strategy.approved_at else None,
                    strategy.approved_by,
                    strategy.executed_at.isoformat() if strategy.executed_at else None,
                    strategy.outcome,
                ),
            )
            conn.commit()

    async def load_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Load a strategy by ID."""
        self._ensure_initialized()

        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,)).fetchone()

        if not row:
            return None

        return self._row_to_strategy(row)

    async def list_strategies(
        self,
        obstacle_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Strategy]:
        """List strategies with optional filters."""
        self._ensure_initialized()

        query = "SELECT * FROM strategies WHERE 1=1"
        params = []

        if obstacle_id:
            query += " AND obstacle_id = ?"
            params.append(obstacle_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY priority_score DESC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_strategy(row) for row in rows]

    def _row_to_strategy(self, row: sqlite3.Row) -> Strategy:
        """Convert database row to Strategy object."""
        return Strategy(
            id=row["id"],
            strategy_type=StrategyType(row["strategy_type"]),
            obstacle_id=row["obstacle_id"],
            title=row["title"],
            description=row["description"] or "",
            rationale=row["rationale"] or "",
            implementation_steps=json.loads(row["implementation_steps"] or "[]"),
            estimated_effort_hours=row["estimated_effort_hours"],
            estimated_cost_usd=row["estimated_cost_usd"],
            confidence=row["confidence"],
            impact_score=row["impact_score"],
            feasibility_score=row["feasibility_score"],
            priority_score=row["priority_score"],
            generated_task_specs=json.loads(row["generated_task_specs"] or "[]"),
            parameter_adjustments=json.loads(row["parameter_adjustments"] or "{}"),
            routing_changes=json.loads(row["routing_changes"] or "{}"),
            retry_policy_changes=json.loads(row["retry_policy_changes"] or "{}"),
            proposed_tool=row["proposed_tool"],
            proposed_integration=row["proposed_integration"],
            tool_requirements=json.loads(row["tool_requirements"] or "[]"),
            scope_changes=row["scope_changes"],
            timeline_changes=row["timeline_changes"],
            success_criteria_changes=row["success_criteria_changes"],
            milestone_changes=json.loads(row["milestone_changes"] or "[]"),
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            approved_at=datetime.fromisoformat(row["approved_at"]) if row["approved_at"] else None,
            approved_by=row["approved_by"],
            executed_at=datetime.fromisoformat(row["executed_at"]) if row["executed_at"] else None,
            outcome=row["outcome"],
        )

    # =========================================================================
    # Agenda Operations
    # =========================================================================

    async def save_agenda(self, agenda: Agenda) -> None:
        """Save an agenda and its items to the database."""
        self._ensure_initialized()

        with self._get_connection() as conn:
            # Save agenda
            conn.execute(
                """
                INSERT OR REPLACE INTO agendas (
                    id, period_start, period_end, period_type,
                    total_estimated_duration_minutes, total_estimated_cost_usd,
                    goals_addressed, milestones_addressed, obstacles_addressed,
                    workstreams_addressed, executive_distribution, goal_distribution,
                    obstacle_resolution_count, status, items_completed, items_failed,
                    items_skipped, items_pending_approval, generated_at, generated_by,
                    generation_context
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agenda.id,
                    agenda.period_start.isoformat(),
                    agenda.period_end.isoformat(),
                    agenda.period_type,
                    agenda.total_estimated_duration_minutes,
                    agenda.total_estimated_cost_usd,
                    json.dumps(agenda.goals_addressed),
                    json.dumps(agenda.milestones_addressed),
                    json.dumps(agenda.obstacles_addressed),
                    json.dumps(agenda.workstreams_addressed),
                    json.dumps(agenda.executive_distribution),
                    json.dumps(agenda.goal_distribution),
                    agenda.obstacle_resolution_count,
                    agenda.status,
                    agenda.items_completed,
                    agenda.items_failed,
                    agenda.items_skipped,
                    agenda.items_pending_approval,
                    agenda.generated_at.isoformat(),
                    agenda.generated_by,
                    json.dumps(agenda.generation_context),
                ),
            )

            # Save items
            for item in agenda.items:
                await self._save_agenda_item(conn, item, agenda.id)

            conn.commit()

    async def _save_agenda_item(
        self,
        conn: sqlite3.Connection,
        item: AgendaItem,
        agenda_id: str,
    ) -> None:
        """Save an agenda item."""
        conn.execute(
            """
            INSERT OR REPLACE INTO agenda_items (
                id, agenda_id, goal_id, workstream_id, milestone_id, strategy_id,
                task_type, title, description, context, recommended_agent,
                alternative_executives, priority_score, confidence_level,
                confidence_score, dependencies, estimated_duration_minutes,
                estimated_cost_usd, retry_policy, timeout_seconds,
                is_obstacle_resolution, resolves_obstacle_id, risk_assessment,
                checkpoint, requires_approval, approval_status, approved_by,
                approved_at, status, executed_at, completed_at, execution_result,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.id,
                agenda_id,
                item.goal_id,
                item.workstream_id,
                item.milestone_id,
                item.strategy_id,
                item.task_type,
                item.title,
                item.description,
                json.dumps(item.context),
                item.recommended_agent,
                json.dumps(item.alternative_executives),
                item.priority_score,
                item.confidence_level.value,
                item.confidence_score,
                json.dumps(item.dependencies),
                item.estimated_duration_minutes,
                item.estimated_cost_usd,
                json.dumps(item.retry_policy),
                item.timeout_seconds,
                1 if item.is_obstacle_resolution else 0,
                item.resolves_obstacle_id,
                json.dumps(item.risk_assessment.to_dict()) if item.risk_assessment else None,
                json.dumps(item.checkpoint.to_dict()) if item.checkpoint else None,
                1 if item.requires_approval else 0,
                item.approval_status,
                item.approved_by,
                item.approved_at.isoformat() if item.approved_at else None,
                item.status,
                item.executed_at.isoformat() if item.executed_at else None,
                item.completed_at.isoformat() if item.completed_at else None,
                json.dumps(item.execution_result) if item.execution_result else None,
                item.created_at.isoformat(),
            ),
        )

    async def load_agenda(self, agenda_id: str) -> Optional[Agenda]:
        """Load an agenda and its items by ID."""
        self._ensure_initialized()

        with self._get_connection() as conn:
            agenda_row = conn.execute("SELECT * FROM agendas WHERE id = ?", (agenda_id,)).fetchone()

            if not agenda_row:
                return None

            item_rows = conn.execute(
                "SELECT * FROM agenda_items WHERE agenda_id = ? ORDER BY priority_score DESC",
                (agenda_id,),
            ).fetchall()

        items = [self._row_to_agenda_item(row) for row in item_rows]
        return self._row_to_agenda(agenda_row, items)

    async def load_latest_agenda(self) -> Optional[Agenda]:
        """Load the most recently generated agenda."""
        self._ensure_initialized()

        with self._get_connection() as conn:
            agenda_row = conn.execute(
                "SELECT * FROM agendas ORDER BY generated_at DESC LIMIT 1"
            ).fetchone()

            if not agenda_row:
                return None

            item_rows = conn.execute(
                "SELECT * FROM agenda_items WHERE agenda_id = ? ORDER BY priority_score DESC",
                (agenda_row["id"],),
            ).fetchall()

        items = [self._row_to_agenda_item(row) for row in item_rows]
        return self._row_to_agenda(agenda_row, items)

    async def list_agendas(
        self,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> List[Agenda]:
        """List agendas with optional filters."""
        self._ensure_initialized()

        query = "SELECT * FROM agendas WHERE 1=1"
        params: List[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY generated_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            agenda_rows = conn.execute(query, params).fetchall()

            agendas = []
            for agenda_row in agenda_rows:
                item_rows = conn.execute(
                    "SELECT * FROM agenda_items WHERE agenda_id = ?", (agenda_row["id"],)
                ).fetchall()
                items = [self._row_to_agenda_item(row) for row in item_rows]
                agendas.append(self._row_to_agenda(agenda_row, items))

        return agendas

    def _row_to_agenda(
        self,
        row: sqlite3.Row,
        items: List[AgendaItem],
    ) -> Agenda:
        """Convert database row to Agenda object."""
        return Agenda(
            id=row["id"],
            period_start=datetime.fromisoformat(row["period_start"]),
            period_end=datetime.fromisoformat(row["period_end"]),
            period_type=row["period_type"],
            items=items,
            total_estimated_duration_minutes=row["total_estimated_duration_minutes"],
            total_estimated_cost_usd=row["total_estimated_cost_usd"],
            goals_addressed=json.loads(row["goals_addressed"] or "[]"),
            milestones_addressed=json.loads(row["milestones_addressed"] or "[]"),
            obstacles_addressed=json.loads(row["obstacles_addressed"] or "[]"),
            workstreams_addressed=json.loads(row["workstreams_addressed"] or "[]"),
            executive_distribution=json.loads(row["executive_distribution"] or "{}"),
            goal_distribution=json.loads(row["goal_distribution"] or "{}"),
            obstacle_resolution_count=row["obstacle_resolution_count"],
            status=row["status"],
            items_completed=row["items_completed"],
            items_failed=row["items_failed"],
            items_skipped=row["items_skipped"],
            items_pending_approval=row["items_pending_approval"],
            generated_at=datetime.fromisoformat(row["generated_at"]),
            generated_by=row["generated_by"],
            generation_context=json.loads(row["generation_context"] or "{}"),
        )

    def _row_to_agenda_item(self, row: sqlite3.Row) -> AgendaItem:
        """Convert database row to AgendaItem object."""
        risk_assessment = None
        if row["risk_assessment"]:
            ra_data = json.loads(row["risk_assessment"])
            risk_assessment = RiskAssessment(
                id=ra_data.get("id", ""),
                item_id=ra_data.get("item_id", ""),
                item_type=ra_data.get("item_type", ""),
                risk_level=RiskLevel(ra_data.get("risk_level", "low")),
                risk_categories=[RiskCategory(c) for c in ra_data.get("risk_categories", [])],
                risk_score=ra_data.get("risk_score", 0.0),
                risks=ra_data.get("risks", []),
                mitigations=ra_data.get("mitigations", []),
                requires_approval=ra_data.get("requires_approval", False),
                approval_reason=ra_data.get("approval_reason"),
                approver_role=ra_data.get("approver_role"),
            )

        checkpoint = None
        if row["checkpoint"]:
            cp_data = json.loads(row["checkpoint"])
            checkpoint = Checkpoint(
                id=cp_data.get("id", ""),
                checkpoint_type=CheckpointType(cp_data.get("checkpoint_type", "approval")),
                trigger_reason=cp_data.get("trigger_reason", ""),
                item_id=cp_data.get("item_id"),
                strategy_id=cp_data.get("strategy_id"),
                title=cp_data.get("title", ""),
                description=cp_data.get("description", ""),
                context=cp_data.get("context", {}),
                options=cp_data.get("options", []),
                default_option=cp_data.get("default_option"),
                status=cp_data.get("status", "pending"),
            )

        return AgendaItem(
            id=row["id"],
            goal_id=row["goal_id"],
            workstream_id=row["workstream_id"],
            milestone_id=row["milestone_id"],
            strategy_id=row["strategy_id"],
            task_type=row["task_type"],
            title=row["title"],
            description=row["description"] or "",
            context=json.loads(row["context"] or "{}"),
            recommended_agent=row["recommended_agent"],
            alternative_executives=json.loads(row["alternative_executives"] or "[]"),
            priority_score=row["priority_score"],
            confidence_level=ConfidenceLevel(row["confidence_level"]),
            confidence_score=row["confidence_score"],
            dependencies=json.loads(row["dependencies"] or "[]"),
            estimated_duration_minutes=row["estimated_duration_minutes"],
            estimated_cost_usd=row["estimated_cost_usd"],
            retry_policy=json.loads(row["retry_policy"] or "{}"),
            timeout_seconds=row["timeout_seconds"],
            is_obstacle_resolution=bool(row["is_obstacle_resolution"]),
            resolves_obstacle_id=row["resolves_obstacle_id"],
            risk_assessment=risk_assessment,
            checkpoint=checkpoint,
            requires_approval=bool(row["requires_approval"]),
            approval_status=row["approval_status"],
            approved_by=row["approved_by"],
            approved_at=datetime.fromisoformat(row["approved_at"]) if row["approved_at"] else None,
            status=row["status"],
            executed_at=datetime.fromisoformat(row["executed_at"]) if row["executed_at"] else None,
            completed_at=(
                datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
            ),
            execution_result=(
                json.loads(row["execution_result"]) if row["execution_result"] else None
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # =========================================================================
    # Audit Trail Operations
    # =========================================================================

    async def save_audit_entry(self, entry: AuditEntry) -> None:
        """Save an audit entry."""
        self._ensure_initialized()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_trail (
                    id, timestamp, action_type, item_id, strategy_id, checkpoint_id,
                    agenda_id, actor, actor_role, risk_level, risk_score, decision,
                    reason, context
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.timestamp.isoformat(),
                    entry.action_type,
                    entry.item_id,
                    entry.strategy_id,
                    entry.checkpoint_id,
                    entry.agenda_id,
                    entry.actor,
                    entry.actor_role,
                    entry.risk_level.value if entry.risk_level else None,
                    entry.risk_score,
                    entry.decision,
                    entry.reason,
                    json.dumps(entry.context),
                ),
            )
            conn.commit()

    async def get_audit_trail(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        action_types: Optional[List[str]] = None,
        item_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Get audit trail with filters."""
        self._ensure_initialized()

        query = "SELECT * FROM audit_trail WHERE 1=1"
        params: List[Any] = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        if action_types:
            placeholders = ",".join("?" for _ in action_types)
            query += f" AND action_type IN ({placeholders})"
            params.extend(action_types)

        if item_id:
            query += " AND item_id = ?"
            params.append(item_id)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_audit_entry(row) for row in rows]

    def _row_to_audit_entry(self, row: sqlite3.Row) -> AuditEntry:
        """Convert database row to AuditEntry object."""
        return AuditEntry(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            action_type=row["action_type"],
            item_id=row["item_id"],
            strategy_id=row["strategy_id"],
            checkpoint_id=row["checkpoint_id"],
            agenda_id=row["agenda_id"],
            actor=row["actor"],
            actor_role=row["actor_role"],
            risk_level=RiskLevel(row["risk_level"]) if row["risk_level"] else None,
            risk_score=row["risk_score"],
            decision=row["decision"],
            reason=row["reason"],
            context=json.loads(row["context"] or "{}"),
        )

    # =========================================================================
    # Cleanup Operations
    # =========================================================================

    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """
        Clean up data older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Dict with counts of deleted records
        """
        self._ensure_initialized()

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        deleted = {}

        with self._get_connection() as conn:
            # Clean up old agendas (and their items via cascade)
            cursor = conn.execute(
                "DELETE FROM agenda_items WHERE agenda_id IN (SELECT id FROM agendas WHERE generated_at < ?)",
                (cutoff,),
            )
            deleted["agenda_items"] = cursor.rowcount

            cursor = conn.execute("DELETE FROM agendas WHERE generated_at < ?", (cutoff,))
            deleted["agendas"] = cursor.rowcount

            # Clean up old audit trail
            cursor = conn.execute("DELETE FROM audit_trail WHERE timestamp < ?", (cutoff,))
            deleted["audit_entries"] = cursor.rowcount

            # Clean up resolved obstacles older than cutoff
            cursor = conn.execute(
                "DELETE FROM obstacles WHERE status = 'resolved' AND resolved_at < ?", (cutoff,)
            )
            deleted["obstacles"] = cursor.rowcount

            conn.commit()

        logger.info(f"Cleaned up old data: {deleted}")
        return deleted
