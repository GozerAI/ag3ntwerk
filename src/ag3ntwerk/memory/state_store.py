"""
Persistent state management for ag3ntwerk.

Uses SQLite for simplicity and portability. Provides key-value storage
with namespace isolation, TTL support, and async interface.
"""

import asyncio
import json
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

from ag3ntwerk.core.exceptions import StateCorruptionError, StateNotFoundError, StatePersistenceError

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class StateEntry:
    """Represents a state entry with metadata."""

    key: str
    value: Any
    namespace: str = "default"
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    ttl_seconds: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL."""
        if self.ttl_seconds is None:
            return False
        expiry = self.updated_at + timedelta(seconds=self.ttl_seconds)
        return _utcnow() > expiry

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "key": self.key,
            "value": self.value,
            "namespace": self.namespace,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "metadata": self.metadata,
        }


class StateStore:
    """
    SQLite-backed persistent state store.

    Provides namespaced key-value storage with:
    - Async interface (runs SQLite in thread pool)
    - TTL support for automatic expiration
    - Namespace isolation for multi-tenant usage
    - JSON serialization for complex values

    Example:
        store = StateStore()
        await store.initialize()

        await store.set("user_preferences", {"theme": "dark"}, namespace="user_123")
        prefs = await store.get("user_preferences", namespace="user_123")

        await store.close()
    """

    def __init__(
        self,
        db_path: Union[str, Path] = "~/.ag3ntwerk/state.db",
        pool_size: int = 5,
    ):
        """
        Initialize state store.

        Args:
            db_path: Path to SQLite database file
            pool_size: Number of connections in the pool
        """
        self.db_path = Path(db_path).expanduser().resolve()
        self.pool_size = pool_size
        self._initialized = False
        self._lock = asyncio.Lock()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a database connection with proper handling."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS state (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    ttl_seconds INTEGER,
                    metadata TEXT DEFAULT '{}',
                    PRIMARY KEY (namespace, key)
                );

                CREATE INDEX IF NOT EXISTS idx_state_namespace
                ON state(namespace);

                CREATE INDEX IF NOT EXISTS idx_state_updated
                ON state(updated_at);

                CREATE TABLE IF NOT EXISTS state_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_history_key
                ON state_history(namespace, key);
            """
            )
            conn.commit()

    async def initialize(self) -> None:
        """Initialize the state store."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Initialize schema in thread pool
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._init_schema)

            self._initialized = True
            logger.info(f"StateStore initialized at {self.db_path}")

    async def close(self) -> None:
        """Close the state store."""
        self._initialized = False

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, default=str)

    def _deserialize(self, data: str) -> Any:
        """Deserialize JSON string to value."""
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise StateCorruptionError("unknown", f"Invalid JSON: {e}")

    def _get_sync(self, key: str, namespace: str) -> Optional[StateEntry]:
        """Synchronous get operation."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT key, value, namespace, created_at, updated_at, ttl_seconds, metadata
                FROM state WHERE namespace = ? AND key = ?
                """,
                (namespace, key),
            ).fetchone()

            if not row:
                return None

            entry = StateEntry(
                key=row["key"],
                value=self._deserialize(row["value"]),
                namespace=row["namespace"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                ttl_seconds=row["ttl_seconds"],
                metadata=self._deserialize(row["metadata"]),
            )

            # Check TTL
            if entry.is_expired:
                conn.execute(
                    "DELETE FROM state WHERE namespace = ? AND key = ?",
                    (namespace, key),
                )
                conn.commit()
                return None

            return entry

    async def get(
        self,
        key: str,
        namespace: str = "default",
        default: Any = None,
    ) -> Any:
        """
        Retrieve a value from state.

        Args:
            key: The state key
            namespace: Namespace for isolation
            default: Default value if key not found

        Returns:
            The stored value or default
        """
        if not self._initialized:
            await self.initialize()

        loop = asyncio.get_running_loop()
        entry = await loop.run_in_executor(None, self._get_sync, key, namespace)

        if entry is None:
            return default
        return entry.value

    async def get_entry(
        self,
        key: str,
        namespace: str = "default",
    ) -> Optional[StateEntry]:
        """
        Retrieve a full state entry with metadata.

        Args:
            key: The state key
            namespace: Namespace for isolation

        Returns:
            StateEntry or None if not found
        """
        if not self._initialized:
            await self.initialize()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_sync, key, namespace)

    def _set_sync(
        self,
        key: str,
        value: Any,
        namespace: str,
        ttl_seconds: Optional[int],
        metadata: Dict[str, Any],
    ) -> None:
        """Synchronous set operation."""
        now = _utcnow().isoformat()
        with self._get_connection() as conn:
            # Check if exists for created_at
            existing = conn.execute(
                "SELECT created_at FROM state WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()

            created_at = existing["created_at"] if existing else now

            conn.execute(
                """
                INSERT OR REPLACE INTO state
                (namespace, key, value, created_at, updated_at, ttl_seconds, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    namespace,
                    key,
                    self._serialize(value),
                    created_at,
                    now,
                    ttl_seconds,
                    self._serialize(metadata),
                ),
            )

            # Record history
            conn.execute(
                """
                INSERT INTO state_history (namespace, key, value, operation, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    namespace,
                    key,
                    self._serialize(value),
                    "update" if existing else "create",
                    now,
                ),
            )

            conn.commit()

    async def set(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Store a value in state.

        Args:
            key: The state key
            value: Value to store (must be JSON-serializable)
            namespace: Namespace for isolation
            ttl_seconds: Optional TTL for auto-expiration
            metadata: Optional metadata about the entry
        """
        if not self._initialized:
            await self.initialize()

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self._set_sync,
            key,
            value,
            namespace,
            ttl_seconds,
            metadata or {},
        )

    def _delete_sync(self, key: str, namespace: str) -> bool:
        """Synchronous delete operation."""
        with self._get_connection() as conn:
            # Record deletion in history
            existing = conn.execute(
                "SELECT value FROM state WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()

            if existing:
                conn.execute(
                    """
                    INSERT INTO state_history (namespace, key, value, operation, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        namespace,
                        key,
                        existing["value"],
                        "delete",
                        _utcnow().isoformat(),
                    ),
                )

            result = conn.execute(
                "DELETE FROM state WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            conn.commit()
            return result.rowcount > 0

    async def delete(self, key: str, namespace: str = "default") -> bool:
        """
        Delete a value from state.

        Args:
            key: The state key
            namespace: Namespace for isolation

        Returns:
            True if deleted, False if not found
        """
        if not self._initialized:
            await self.initialize()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._delete_sync, key, namespace)

    def _list_keys_sync(self, namespace: str, pattern: Optional[str]) -> List[str]:
        """Synchronous list keys operation."""
        with self._get_connection() as conn:
            if pattern:
                # Use LIKE for pattern matching
                sql_pattern = pattern.replace("*", "%").replace("?", "_")
                rows = conn.execute(
                    "SELECT key FROM state WHERE namespace = ? AND key LIKE ?",
                    (namespace, sql_pattern),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT key FROM state WHERE namespace = ?",
                    (namespace,),
                ).fetchall()

            return [row["key"] for row in rows]

    async def list_keys(
        self,
        namespace: str = "default",
        pattern: Optional[str] = None,
    ) -> List[str]:
        """
        List keys in a namespace.

        Args:
            namespace: Namespace to list
            pattern: Optional glob pattern (* and ?)

        Returns:
            List of matching keys
        """
        if not self._initialized:
            await self.initialize()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._list_keys_sync, namespace, pattern)

    def _list_namespaces_sync(self) -> List[str]:
        """Synchronous list namespaces operation."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT namespace FROM state ORDER BY namespace"
            ).fetchall()
            return [row["namespace"] for row in rows]

    async def list_namespaces(self) -> List[str]:
        """
        List all namespaces.

        Returns:
            List of namespace names
        """
        if not self._initialized:
            await self.initialize()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._list_namespaces_sync)

    def _clear_namespace_sync(self, namespace: str) -> int:
        """Synchronous clear namespace operation."""
        with self._get_connection() as conn:
            result = conn.execute(
                "DELETE FROM state WHERE namespace = ?",
                (namespace,),
            )
            conn.commit()
            return result.rowcount

    async def clear_namespace(self, namespace: str) -> int:
        """
        Clear all entries in a namespace.

        Args:
            namespace: Namespace to clear

        Returns:
            Number of entries deleted
        """
        if not self._initialized:
            await self.initialize()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._clear_namespace_sync, namespace)

    def _cleanup_expired_sync(self) -> int:
        """Synchronous cleanup of expired entries."""
        with self._get_connection() as conn:
            now = _utcnow()
            # Find and delete expired entries
            rows = conn.execute(
                """
                SELECT namespace, key, updated_at, ttl_seconds
                FROM state WHERE ttl_seconds IS NOT NULL
                """
            ).fetchall()

            deleted = 0
            for row in rows:
                updated = datetime.fromisoformat(row["updated_at"])
                expiry = updated + timedelta(seconds=row["ttl_seconds"])
                if now > expiry:
                    conn.execute(
                        "DELETE FROM state WHERE namespace = ? AND key = ?",
                        (row["namespace"], row["key"]),
                    )
                    deleted += 1

            conn.commit()
            return deleted

    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        if not self._initialized:
            await self.initialize()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._cleanup_expired_sync)

    def _get_history_sync(
        self,
        key: str,
        namespace: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Synchronous get history operation."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT value, operation, timestamp
                FROM state_history
                WHERE namespace = ? AND key = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (namespace, key, limit),
            ).fetchall()

            return [
                {
                    "value": self._deserialize(row["value"]),
                    "operation": row["operation"],
                    "timestamp": row["timestamp"],
                }
                for row in rows
            ]

    async def get_history(
        self,
        key: str,
        namespace: str = "default",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get change history for a key.

        Args:
            key: The state key
            namespace: Namespace for isolation
            limit: Maximum entries to return

        Returns:
            List of history entries (newest first)
        """
        if not self._initialized:
            await self.initialize()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_history_sync, key, namespace, limit)

    async def __aenter__(self) -> "StateStore":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


# Singleton instance for convenience
_default_store: Optional[StateStore] = None


async def get_default_store() -> StateStore:
    """Get the default state store instance."""
    global _default_store
    if _default_store is None:
        _default_store = StateStore()
        await _default_store.initialize()
    return _default_store
