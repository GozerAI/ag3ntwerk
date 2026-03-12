"""
Database management for ag3ntwerk persistence layer.

Supports SQLite (default) and PostgreSQL backends with a unified interface.
Uses Alembic for schema migrations in production.
"""

import asyncio
import os
import sqlite3
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Tuple, Union

from ag3ntwerk.core.logging import get_logger

logger = get_logger(__name__)

# Migration configuration
MIGRATIONS_DIR = Path(__file__).parent / "migrations"
USE_MIGRATIONS = os.getenv("AGENTWERK_USE_MIGRATIONS", "true").lower() == "true"


class DatabaseBackend(Enum):
    """Supported database backends."""

    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


@dataclass
class DatabaseConfig:
    """Database configuration."""

    backend: DatabaseBackend = DatabaseBackend.SQLITE
    # SQLite settings
    sqlite_path: str = "~/.ag3ntwerk/data/ag3ntwerk.db"
    # PostgreSQL settings
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "ag3ntwerk"
    pg_user: str = "ag3ntwerk"
    pg_password: str = ""
    # Common settings
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create config from environment variables."""
        backend_str = os.getenv("DATABASE_BACKEND", "sqlite").lower()
        backend = (
            DatabaseBackend(backend_str)
            if backend_str in ["sqlite", "postgresql"]
            else DatabaseBackend.SQLITE
        )

        return cls(
            backend=backend,
            sqlite_path=os.getenv("DATABASE_PATH", "~/.ag3ntwerk/data/ag3ntwerk.db"),
            pg_host=os.getenv("PG_HOST", "localhost"),
            pg_port=int(os.getenv("PG_PORT", "5432")),
            pg_database=os.getenv("PG_DATABASE", "ag3ntwerk"),
            pg_user=os.getenv("PG_USER", "ag3ntwerk"),
            pg_password=os.getenv("PG_PASSWORD", ""),
            pool_size=int(os.getenv("AGENTWERK_DB_POOL_SIZE", os.getenv("DATABASE_POOL_SIZE", "10"))),
            max_overflow=int(
                os.getenv("AGENTWERK_DB_MAX_OVERFLOW", os.getenv("DATABASE_MAX_OVERFLOW", "20"))
            ),
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
        )

    @property
    def connection_string(self) -> str:
        """Get the connection string for the database."""
        if self.backend == DatabaseBackend.SQLITE:
            path = Path(self.sqlite_path).expanduser().resolve()
            return f"sqlite:///{path}"
        else:
            return f"postgresql://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_database}"

    @property
    def safe_connection_string(self) -> str:
        """Get a connection string with the password masked for logging."""
        if self.backend == DatabaseBackend.SQLITE:
            return self.connection_string
        else:
            masked_password = "***" if self.pg_password else ""
            return f"postgresql://{self.pg_user}:{masked_password}@{self.pg_host}:{self.pg_port}/{self.pg_database}"

    def __repr__(self) -> str:
        """Return a safe representation that never exposes credentials."""
        if self.backend == DatabaseBackend.SQLITE:
            return f"DatabaseConfig(backend=SQLITE, path='{self.sqlite_path}')"
        else:
            return (
                f"DatabaseConfig(backend=POSTGRESQL, "
                f"host='{self.pg_host}', port={self.pg_port}, "
                f"db='{self.pg_database}', user='{self.pg_user}', password='***')"
            )


class DatabaseConnection(ABC):
    """Abstract database connection interface."""

    @abstractmethod
    async def execute(self, query: str, params: Optional[Tuple] = None) -> int:
        """Execute a query and return affected rows."""
        pass

    @abstractmethod
    async def fetch_one(
        self, query: str, params: Optional[Tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single row."""
        pass

    @abstractmethod
    async def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows."""
        pass

    @abstractmethod
    async def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """Execute query with multiple parameter sets."""
        pass


class SQLiteConnection(DatabaseConnection):
    """SQLite connection implementation."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = asyncio.Lock()

    @contextmanager
    def _get_conn(self) -> Iterator[sqlite3.Connection]:
        """Get a SQLite connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    async def execute(self, query: str, params: Optional[Tuple] = None) -> int:
        """Execute a query."""
        loop = asyncio.get_running_loop()

        def _execute():
            with self._get_conn() as conn:
                cursor = conn.execute(query, params or ())
                conn.commit()
                return cursor.rowcount

        async with self._lock:
            return await loop.run_in_executor(None, _execute)

    async def fetch_one(
        self, query: str, params: Optional[Tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch single row."""
        loop = asyncio.get_running_loop()

        def _fetch():
            with self._get_conn() as conn:
                row = conn.execute(query, params or ()).fetchone()
                return dict(row) if row else None

        return await loop.run_in_executor(None, _fetch)

    async def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows."""
        loop = asyncio.get_running_loop()

        def _fetch():
            with self._get_conn() as conn:
                rows = conn.execute(query, params or ()).fetchall()
                return [dict(row) for row in rows]

        return await loop.run_in_executor(None, _fetch)

    async def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """Execute with multiple params."""
        loop = asyncio.get_running_loop()

        def _execute():
            with self._get_conn() as conn:
                cursor = conn.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount

        async with self._lock:
            return await loop.run_in_executor(None, _execute)


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL connection implementation using asyncpg."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool = None

    async def _get_pool(self):
        """Get or create connection pool."""
        if self._pool is None:
            try:
                import asyncpg

                self._pool = await asyncpg.create_pool(
                    host=self.config.pg_host,
                    port=self.config.pg_port,
                    database=self.config.pg_database,
                    user=self.config.pg_user,
                    password=self.config.pg_password,
                    min_size=2,
                    max_size=self.config.pool_size,
                )
            except ImportError:
                raise RuntimeError(
                    "asyncpg is required for PostgreSQL support. Install with: pip install asyncpg"
                )
        return self._pool

    async def execute(self, query: str, params: Optional[Tuple] = None) -> int:
        """Execute a query."""
        pool = await self._get_pool()
        # Convert ? placeholders to $1, $2 for PostgreSQL
        pg_query = self._convert_placeholders(query)
        async with pool.acquire() as conn:
            result = await conn.execute(pg_query, *(params or ()))
            # Parse affected rows from result string
            try:
                return int(result.split()[-1])
            except (ValueError, IndexError):
                return 0

    async def fetch_one(
        self, query: str, params: Optional[Tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch single row."""
        pool = await self._get_pool()
        pg_query = self._convert_placeholders(query)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(pg_query, *(params or ()))
            return dict(row) if row else None

    async def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows."""
        pool = await self._get_pool()
        pg_query = self._convert_placeholders(query)
        async with pool.acquire() as conn:
            rows = await conn.fetch(pg_query, *(params or ()))
            return [dict(row) for row in rows]

    async def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """Execute with multiple params."""
        pool = await self._get_pool()
        pg_query = self._convert_placeholders(query)
        async with pool.acquire() as conn:
            await conn.executemany(pg_query, params_list)
            return len(params_list)

    def _convert_placeholders(self, query: str) -> str:
        """Convert ? placeholders to $1, $2, etc."""
        result = []
        param_num = 0
        for char in query:
            if char == "?":
                param_num += 1
                result.append(f"${param_num}")
            else:
                result.append(char)
        return "".join(result)

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None


class DatabaseManager:
    """
    Database manager providing a unified interface for persistence operations.

    Usage:
        db = DatabaseManager()
        await db.initialize()

        # Execute queries
        await db.execute("INSERT INTO tasks (name) VALUES (?)", ("task1",))
        rows = await db.fetch_all("SELECT * FROM tasks")

        await db.close()
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """Initialize database manager."""
        self.config = config or DatabaseConfig.from_env()
        self._connection: Optional[DatabaseConnection] = None
        self._initialized = False

    async def initialize(self, auto_migrate: bool = False) -> None:
        """
        Initialize the database connection and schema.

        Args:
            auto_migrate: If True, automatically run pending migrations.
                         Defaults to False in production for safety.
        """
        if self._initialized:
            return

        if self.config.backend == DatabaseBackend.SQLITE:
            # Ensure directory exists
            db_path = Path(self.config.sqlite_path).expanduser().resolve()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = SQLiteConnection(db_path)
        else:
            self._connection = PostgreSQLConnection(self.config)

        # Use Alembic migrations if enabled, otherwise fall back to legacy schema init
        if USE_MIGRATIONS:
            try:
                migration_status = self._check_migration_status()
                if migration_status["pending"]:
                    if auto_migrate:
                        logger.info(
                            "Running pending database migrations",
                            component="database",
                            pending_count=len(migration_status["pending"]),
                        )
                        self._run_migrations()
                    else:
                        pending_count = len(migration_status["pending"])
                        logger.warning(
                            "Database has pending migrations. Run 'alembic upgrade head' to apply them.",
                            component="database",
                            pending_count=pending_count,
                        )
                elif not migration_status["up_to_date"] or migration_status["current"] is None:
                    # Fresh database or unknown state - need schema initialization
                    if auto_migrate:
                        logger.info(
                            "Fresh database detected, running migrations", component="database"
                        )
                        self._run_migrations()
                    else:
                        logger.info(
                            "Fresh database detected, initializing schema directly",
                            component="database",
                        )
                        await self._init_schema()
            except Exception as e:  # Intentional catch-all: alembic may not be installed
                logger.warning(
                    "Migration system unavailable, falling back to direct schema init",
                    component="database",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                await self._init_schema()
        else:
            # Legacy: direct schema initialization (for development/testing)
            await self._init_schema()

        self._initialized = True
        logger.info(
            "Database initialized",
            component="database",
            backend=self.config.backend.value,
            connection=self.config.safe_connection_string,
        )

    def _check_migration_status(self) -> Dict[str, Any]:
        """Check the current migration status."""
        try:
            from alembic import command
            from alembic.config import Config
            from alembic.script import ScriptDirectory
            from alembic.runtime.migration import MigrationContext
            from sqlalchemy import create_engine

            # Create Alembic config
            alembic_cfg = Config()
            alembic_cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
            alembic_cfg.set_main_option("sqlalchemy.url", self.config.connection_string)

            # Get script directory
            script = ScriptDirectory.from_config(alembic_cfg)

            # Get current revision from database
            engine = create_engine(self.config.connection_string)
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_rev = context.get_current_revision()

            # Get head revision
            head_rev = script.get_current_head()

            # Get pending revisions
            pending = []
            if current_rev != head_rev:
                for rev in script.iterate_revisions(head_rev, current_rev):
                    if rev.revision != current_rev:
                        pending.append(rev.revision)

            return {
                "current": current_rev,
                "head": head_rev,
                "pending": pending,
                "up_to_date": current_rev == head_rev,
            }
        except Exception as e:  # Intentional catch-all: alembic may not be installed
            logger.warning(
                "Could not check migration status",
                component="database",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            # Return up_to_date=False so the caller knows this is not a healthy state
            return {"current": None, "head": None, "pending": [], "up_to_date": False}

    def _run_migrations(self) -> None:
        """Run all pending migrations."""
        try:
            from alembic import command
            from alembic.config import Config

            alembic_cfg = Config()
            alembic_cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
            alembic_cfg.set_main_option("sqlalchemy.url", self.config.connection_string)

            command.upgrade(alembic_cfg, "head")
            logger.info("Database migrations completed successfully", component="database")
        except Exception as e:  # Intentional catch-all: re-raises after logging
            logger.error(
                "Failed to run migrations",
                component="database",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

    async def _init_schema(self) -> None:
        """Initialize database schema."""
        # Analytics table
        await self.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                dimensions TEXT DEFAULT '{}',
                timestamp TEXT NOT NULL,
                source TEXT DEFAULT 'system'
            )
        """
        )

        # Audit trail table
        await self.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                actor TEXT NOT NULL,
                details TEXT DEFAULT '{}',
                outcome TEXT,
                timestamp TEXT NOT NULL
            )
        """
        )

        # Plugin configuration table
        await self.execute(
            """
            CREATE TABLE IF NOT EXISTS plugin_config (
                plugin_id TEXT PRIMARY KEY,
                config_data TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                version TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        )

        # Decision history table
        await self.execute(
            """
            CREATE TABLE IF NOT EXISTS decision_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT UNIQUE NOT NULL,
                agent_code TEXT NOT NULL,
                task_id TEXT,
                decision_type TEXT NOT NULL,
                input_summary TEXT,
                output_summary TEXT,
                reasoning TEXT,
                confidence REAL,
                alternatives TEXT DEFAULT '[]',
                selected_option TEXT,
                timestamp TEXT NOT NULL
            )
        """
        )

        # Workflow execution table
        await self.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT UNIQUE NOT NULL,
                workflow_name TEXT NOT NULL,
                status TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                error_message TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT
            )
        """
        )

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_analytics_metric ON analytics(metric_name)",
            "CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_trail(entity_type, entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_trail(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_decision_agent ON decision_history(agent_code)",
            "CREATE INDEX IF NOT EXISTS idx_decision_timestamp ON decision_history(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_workflow_status ON workflow_executions(status)",
        ]

        for idx in indexes:
            await self.execute(idx)

    async def execute(self, query: str, params: Optional[Tuple] = None) -> int:
        """Execute a query."""
        if not self._initialized:
            await self.initialize()
        return await self._connection.execute(query, params)

    async def fetch_one(
        self, query: str, params: Optional[Tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch single row."""
        if not self._initialized:
            await self.initialize()
        return await self._connection.fetch_one(query, params)

    async def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows."""
        if not self._initialized:
            await self.initialize()
        return await self._connection.fetch_all(query, params)

    async def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """Execute with multiple params."""
        if not self._initialized:
            await self.initialize()
        return await self._connection.execute_many(query, params_list)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator["DatabaseManager"]:
        """Context manager for transactions (SQLite auto-commits, PG uses explicit)."""
        # For SQLite, transactions are automatic
        # For PostgreSQL, would need to use pool.acquire() + BEGIN/COMMIT
        try:
            yield self
        except Exception:  # Intentional catch-all: transaction rollback + re-raise
            # In a real implementation, rollback here
            raise

    async def close(self) -> None:
        """Close database connection."""
        if hasattr(self._connection, "close"):
            await self._connection.close()
        self._initialized = False

    async def __aenter__(self) -> "DatabaseManager":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


# Global instance
_database: Optional[DatabaseManager] = None


async def get_database() -> DatabaseManager:
    """Get the global database instance."""
    global _database
    if _database is None:
        _database = DatabaseManager()
        await _database.initialize()
    return _database


async def close_database() -> None:
    """Close the global database instance."""
    global _database
    if _database:
        await _database.close()
        _database = None
