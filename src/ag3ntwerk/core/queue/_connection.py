"""
Database Connection Manager - Shared SQLite connection for all facades.

Manages the database connection and schema initialization.
"""

import logging
import sqlite3
from typing import Optional

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages the shared SQLite connection for all queue facades.

    This is a thin wrapper around sqlite3.Connection that:
    - Handles initialization and schema creation
    - Provides thread-safe access
    - Exposes the raw connection for facades
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the connection manager.

        Args:
            db_path: Path to SQLite database (None for in-memory)
        """
        self._db_path = db_path or ":memory:"
        self._connection: Optional[sqlite3.Connection] = None

    async def initialize(self) -> None:
        """Initialize database and create schema."""
        self._connection = sqlite3.connect(self._db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._create_schema()
        logger.info(f"Task queue database initialized: {self._db_path}")

    def _create_schema(self) -> None:
        """Create database schema."""
        if not self._connection:
            raise RuntimeError("Connection not initialized")

        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                state TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                scheduled_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                last_error TEXT,
                next_retry_at TEXT,
                metadata TEXT DEFAULT '{}',
                result TEXT,
                timeout REAL,
                parent_id TEXT,
                group_id TEXT,
                worker_id TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
            CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
            CREATE INDEX IF NOT EXISTS idx_tasks_scheduled ON tasks(scheduled_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_retry ON tasks(next_retry_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type);
            CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_group ON tasks(group_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);

            -- Task dependencies table
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id TEXT NOT NULL,
                depends_on TEXT NOT NULL,
                PRIMARY KEY (task_id, depends_on),
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                FOREIGN KEY (depends_on) REFERENCES tasks(id)
            );

            -- Task events/history table
            CREATE TABLE IF NOT EXISTS task_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT DEFAULT '{}',
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );

            CREATE INDEX IF NOT EXISTS idx_events_task ON task_events(task_id);
            CREATE INDEX IF NOT EXISTS idx_events_type ON task_events(event_type);
        """
        )

        self._connection.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        """
        Get the database connection.

        Raises:
            RuntimeError: If not initialized
        """
        if not self._connection:
            raise RuntimeError("Queue not initialized. Call initialize() first.")
        return self._connection

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor."""
        return self.connection.execute(query, params)

    def commit(self) -> None:
        """Commit current transaction."""
        self.connection.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        self.connection.rollback()

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Task queue database closed")
