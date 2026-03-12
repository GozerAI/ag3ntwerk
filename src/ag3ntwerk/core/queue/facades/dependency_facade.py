"""
Dependency Facade - Task dependency management.

This facade handles:
- Creating task dependencies
- Querying dependencies
- Checking dependency status
"""

import logging
from typing import Dict, Any, List

from ag3ntwerk.core.queue._connection import ConnectionManager

logger = logging.getLogger(__name__)


class DependencyFacade:
    """
    Facade for task dependency operations.

    Manages relationships between tasks.
    """

    def __init__(self, connection: ConnectionManager):
        """
        Initialize the dependency facade.

        Args:
            connection: Shared connection manager
        """
        self._connection = connection

    async def add_dependency(self, task_id: str, depends_on: str) -> None:
        """
        Add a dependency between tasks.

        Args:
            task_id: Task that depends on another
            depends_on: Task ID that must complete first
        """
        self._connection.execute(
            """
            INSERT OR IGNORE INTO task_dependencies (task_id, depends_on)
            VALUES (?, ?)
            """,
            (task_id, depends_on),
        )
        self._connection.commit()

    async def get_dependencies(self, task_id: str) -> List[str]:
        """
        Get task IDs that this task depends on.

        Args:
            task_id: Task ID

        Returns:
            List of dependency task IDs
        """
        cursor = self._connection.execute(
            """
            SELECT depends_on FROM task_dependencies WHERE task_id = ?
            """,
            (task_id,),
        )
        return [row["depends_on"] for row in cursor.fetchall()]

    async def get_dependents(self, task_id: str) -> List[str]:
        """
        Get task IDs that depend on this task.

        Args:
            task_id: Task ID

        Returns:
            List of dependent task IDs
        """
        cursor = self._connection.execute(
            """
            SELECT task_id FROM task_dependencies WHERE depends_on = ?
            """,
            (task_id,),
        )
        return [row["task_id"] for row in cursor.fetchall()]

    async def are_dependencies_met(self, task_id: str) -> bool:
        """
        Check if all dependencies are completed.

        Args:
            task_id: Task ID

        Returns:
            True if all dependencies are completed
        """
        cursor = self._connection.execute(
            """
            SELECT COUNT(*) as count
            FROM task_dependencies td
            JOIN tasks t ON td.depends_on = t.id
            WHERE td.task_id = ? AND t.state != 'completed'
            """,
            (task_id,),
        )
        return cursor.fetchone()["count"] == 0

    async def remove_dependency(self, task_id: str, depends_on: str) -> bool:
        """
        Remove a dependency between tasks.

        Args:
            task_id: Task ID
            depends_on: Dependency to remove

        Returns:
            True if removed
        """
        cursor = self._connection.execute(
            """
            DELETE FROM task_dependencies
            WHERE task_id = ? AND depends_on = ?
            """,
            (task_id, depends_on),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        """Get dependency facade statistics."""
        cursor = self._connection.execute("SELECT COUNT(*) as count FROM task_dependencies")
        total_dependencies = cursor.fetchone()["count"]

        return {
            "total_dependencies": total_dependencies,
        }
