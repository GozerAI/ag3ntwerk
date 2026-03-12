"""
Persistence layer for Workbench Service.

Provides SQLite-based storage for workspaces, ensuring data survives
restarts and system failures. The persistence layer handles:
1. Workspace metadata storage
2. Run history tracking
3. Port allocation state
4. Recovery of existing Docker containers on startup
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.modules.workbench.schemas import (
    Workspace,
    WorkspaceStatus,
    RuntimeType,
    RunResult,
    RunStatus,
    PortExposeResult,
    PortProtocol,
)

logger = get_logger(__name__)


# =============================================================================
# Database Schema
# =============================================================================

SCHEMA = """
-- Workspaces table
CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    runtime TEXT NOT NULL,
    status TEXT DEFAULT 'stopped',
    container_id TEXT,
    metadata TEXT,  -- JSON
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Run history table
CREATE TABLE IF NOT EXISTS run_history (
    run_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    cmd TEXT NOT NULL,  -- JSON array
    status TEXT NOT NULL,
    exit_code INTEGER,
    stdout TEXT,
    stderr TEXT,
    started_at TEXT,
    ended_at TEXT,
    duration_seconds REAL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
);

-- Exposed ports table
CREATE TABLE IF NOT EXISTS exposed_ports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT NOT NULL,
    container_port INTEGER NOT NULL,
    host_port INTEGER NOT NULL,
    protocol TEXT DEFAULT 'http',
    label TEXT,
    preview_url TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    UNIQUE(workspace_id, container_port)
);

-- Port allocations table (tracks which host ports are in use)
CREATE TABLE IF NOT EXISTS port_allocations (
    host_port INTEGER PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    allocated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_workspaces_status ON workspaces(status);
CREATE INDEX IF NOT EXISTS idx_workspaces_runtime ON workspaces(runtime);
CREATE INDEX IF NOT EXISTS idx_run_history_workspace ON run_history(workspace_id);
CREATE INDEX IF NOT EXISTS idx_exposed_ports_workspace ON exposed_ports(workspace_id);
"""


class WorkbenchPersistence:
    """
    SQLite persistence layer for Workbench data.

    Ensures workspaces and their metadata survive restarts.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the persistence layer.

        Args:
            db_path: Path to SQLite database. Defaults to data/workbench.db
        """
        if db_path is None:
            # Default to data directory in project root
            db_path = Path(__file__).parent.parent.parent.parent.parent / "data" / "workbench.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialized = False

    def initialize(self) -> None:
        """Initialize the database schema."""
        if self._initialized:
            return

        with self._get_connection() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

        self._initialized = True
        logger.info(f"Workbench persistence initialized at {self.db_path}")

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # =========================================================================
    # Workspace Operations
    # =========================================================================

    def save_workspace(self, workspace: Workspace, container_id: Optional[str] = None) -> None:
        """
        Save or update a workspace.

        Args:
            workspace: The workspace to save.
            container_id: Optional Docker container ID.
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO workspaces
                (id, name, path, runtime, status, container_id, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workspace.id,
                    workspace.name,
                    workspace.path,
                    workspace.runtime.value,
                    workspace.status.value,
                    container_id,
                    json.dumps(workspace.metadata),
                    workspace.created_at.isoformat(),
                    workspace.updated_at.isoformat(),
                ),
            )
            conn.commit()

        logger.debug(f"Saved workspace {workspace.id}")

    def load_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """
        Load a workspace by ID.

        Args:
            workspace_id: The workspace ID.

        Returns:
            The Workspace or None if not found.
        """
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()

        if not row:
            return None

        return self._row_to_workspace(row)

    def load_all_workspaces(self) -> List[Workspace]:
        """
        Load all workspaces.

        Returns:
            List of all workspaces.
        """
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM workspaces").fetchall()

        return [self._row_to_workspace(row) for row in rows]

    def delete_workspace(self, workspace_id: str) -> None:
        """
        Delete a workspace and all related data.

        Args:
            workspace_id: The workspace ID.
        """
        with self._get_connection() as conn:
            # Delete related data first
            conn.execute("DELETE FROM run_history WHERE workspace_id = ?", (workspace_id,))
            conn.execute("DELETE FROM exposed_ports WHERE workspace_id = ?", (workspace_id,))
            conn.execute("DELETE FROM port_allocations WHERE workspace_id = ?", (workspace_id,))

            # Delete workspace
            conn.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))
            conn.commit()

        logger.debug(f"Deleted workspace {workspace_id}")

    def update_workspace_status(
        self,
        workspace_id: str,
        status: WorkspaceStatus,
        container_id: Optional[str] = None,
    ) -> None:
        """
        Update workspace status.

        Args:
            workspace_id: The workspace ID.
            status: New status.
            container_id: Optional container ID to update.
        """
        with self._get_connection() as conn:
            if container_id is not None:
                conn.execute(
                    """
                    UPDATE workspaces
                    SET status = ?, container_id = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        status.value,
                        container_id,
                        datetime.now(timezone.utc).isoformat(),
                        workspace_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE workspaces
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status.value, datetime.now(timezone.utc).isoformat(), workspace_id),
                )
            conn.commit()

    def get_container_id(self, workspace_id: str) -> Optional[str]:
        """
        Get the Docker container ID for a workspace.

        Args:
            workspace_id: The workspace ID.

        Returns:
            Container ID or None.
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT container_id FROM workspaces WHERE id = ?", (workspace_id,)
            ).fetchone()

        return row["container_id"] if row else None

    def _row_to_workspace(self, row: sqlite3.Row) -> Workspace:
        """Convert a database row to a Workspace object."""
        return Workspace(
            id=row["id"],
            name=row["name"],
            path=row["path"],
            runtime=RuntimeType(row["runtime"]),
            status=WorkspaceStatus(row["status"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # =========================================================================
    # Run History Operations
    # =========================================================================

    def save_run(self, run: RunResult) -> None:
        """
        Save a run result.

        Args:
            run: The run result to save.
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO run_history
                (run_id, workspace_id, cmd, status, exit_code, stdout, stderr,
                 started_at, ended_at, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.workspace_id,
                    json.dumps(run.cmd),
                    run.status.value,
                    run.exit_code,
                    run.stdout,
                    run.stderr,
                    run.started_at.isoformat() if run.started_at else None,
                    run.ended_at.isoformat() if run.ended_at else None,
                    run.duration_seconds,
                ),
            )
            conn.commit()

    def load_runs_for_workspace(
        self,
        workspace_id: str,
        limit: int = 100,
    ) -> List[RunResult]:
        """
        Load run history for a workspace.

        Args:
            workspace_id: The workspace ID.
            limit: Maximum number of runs to return.

        Returns:
            List of run results, most recent first.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM run_history
                WHERE workspace_id = ?
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (workspace_id, limit),
            ).fetchall()

        return [self._row_to_run(row) for row in rows]

    def _row_to_run(self, row: sqlite3.Row) -> RunResult:
        """Convert a database row to a RunResult object."""
        return RunResult(
            run_id=row["run_id"],
            workspace_id=row["workspace_id"],
            cmd=json.loads(row["cmd"]),
            status=RunStatus(row["status"]),
            exit_code=row["exit_code"],
            stdout=row["stdout"],
            stderr=row["stderr"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            duration_seconds=row["duration_seconds"],
        )

    # =========================================================================
    # Port Operations
    # =========================================================================

    def save_exposed_port(self, port_result: PortExposeResult) -> None:
        """
        Save an exposed port.

        Args:
            port_result: The port expose result to save.
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO exposed_ports
                (workspace_id, container_port, host_port, protocol, label, preview_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    port_result.workspace_id,
                    port_result.port,
                    port_result.host_port,
                    port_result.proto.value,
                    port_result.label,
                    port_result.preview_url,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

            # Also track allocation
            conn.execute(
                """
                INSERT OR REPLACE INTO port_allocations
                (host_port, workspace_id, allocated_at)
                VALUES (?, ?, ?)
                """,
                (
                    port_result.host_port,
                    port_result.workspace_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def load_exposed_ports(self, workspace_id: str) -> List[PortExposeResult]:
        """
        Load exposed ports for a workspace.

        Args:
            workspace_id: The workspace ID.

        Returns:
            List of exposed ports.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM exposed_ports WHERE workspace_id = ?", (workspace_id,)
            ).fetchall()

        return [
            PortExposeResult(
                workspace_id=row["workspace_id"],
                port=row["container_port"],
                host_port=row["host_port"],
                proto=PortProtocol(row["protocol"]),
                label=row["label"],
                preview_url=row["preview_url"],
            )
            for row in rows
        ]

    def load_all_port_allocations(self) -> Dict[int, str]:
        """
        Load all port allocations.

        Returns:
            Dict mapping host_port to workspace_id.
        """
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM port_allocations").fetchall()

        return {row["host_port"]: row["workspace_id"] for row in rows}

    def release_port(self, host_port: int) -> None:
        """
        Release a port allocation.

        Args:
            host_port: The host port to release.
        """
        with self._get_connection() as conn:
            conn.execute("DELETE FROM port_allocations WHERE host_port = ?", (host_port,))
            conn.execute("DELETE FROM exposed_ports WHERE host_port = ?", (host_port,))
            conn.commit()

    def release_workspace_ports(self, workspace_id: str) -> None:
        """
        Release all ports for a workspace.

        Args:
            workspace_id: The workspace ID.
        """
        with self._get_connection() as conn:
            conn.execute("DELETE FROM port_allocations WHERE workspace_id = ?", (workspace_id,))
            conn.execute("DELETE FROM exposed_ports WHERE workspace_id = ?", (workspace_id,))
            conn.commit()

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def get_all_container_mappings(self) -> Dict[str, str]:
        """
        Get all workspace -> container_id mappings.

        Returns:
            Dict mapping workspace_id to container_id.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, container_id FROM workspaces WHERE container_id IS NOT NULL"
            ).fetchall()

        return {row["id"]: row["container_id"] for row in rows}

    def get_stats(self) -> Dict[str, Any]:
        """
        Get persistence statistics.

        Returns:
            Stats dictionary.
        """
        with self._get_connection() as conn:
            workspace_count = conn.execute("SELECT COUNT(*) FROM workspaces").fetchone()[0]
            run_count = conn.execute("SELECT COUNT(*) FROM run_history").fetchone()[0]
            port_count = conn.execute("SELECT COUNT(*) FROM port_allocations").fetchone()[0]

        return {
            "total_workspaces": workspace_count,
            "total_runs": run_count,
            "allocated_ports": port_count,
            "db_path": str(self.db_path),
        }


# =============================================================================
# Singleton
# =============================================================================

_persistence: Optional[WorkbenchPersistence] = None


def get_workbench_persistence() -> WorkbenchPersistence:
    """Get or create the global persistence instance."""
    global _persistence
    if _persistence is None:
        _persistence = WorkbenchPersistence()
        _persistence.initialize()
    return _persistence
