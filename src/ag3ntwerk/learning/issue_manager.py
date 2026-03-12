"""
Issue Manager - Converts detected issues into priority tasks.

Manages the issue lifecycle and integrates with the task queue
to automatically create fix tasks for detected problems.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.learning.models import (
    IssueSeverity,
    IssueStatus,
    IssueType,
    LearningIssue,
    ScopeLevel,
)

logger = logging.getLogger(__name__)


class IssueManager:
    """
    Manages the issue lifecycle and task queue integration.

    Converts learning issues into actionable tasks that are
    automatically added to the priority queue.
    """

    # Issue type to task type mapping
    ISSUE_TASK_MAPPING: Dict[IssueType, str] = {
        IssueType.ANOMALY: "anomaly_investigation",
        IssueType.PATTERN_DECLINE: "performance_optimization",
        IssueType.ERROR_SPIKE: "error_investigation",
        IssueType.CONFIDENCE_DRIFT: "calibration_review",
        IssueType.CAPABILITY_GAP: "capability_assessment",
    }

    # Severity to priority mapping (lower = higher priority)
    SEVERITY_PRIORITY: Dict[IssueSeverity, int] = {
        IssueSeverity.CRITICAL: 1,
        IssueSeverity.HIGH: 3,
        IssueSeverity.MEDIUM: 5,
        IssueSeverity.LOW: 7,
    }

    def __init__(
        self,
        db: Any,
        task_queue: Optional[Any] = None,
    ):
        """
        Initialize the issue manager.

        Args:
            db: Database connection
            task_queue: Optional task queue for automatic task creation
        """
        self._db = db
        self._task_queue = task_queue
        self._deduplication_window_hours = 24

    async def create_issue(
        self,
        issue: LearningIssue,
        create_task: bool = True,
    ) -> Optional[str]:
        """
        Create a new issue and optionally enqueue a task.

        Args:
            issue: The issue to create
            create_task: Whether to create a task for this issue

        Returns:
            Issue ID if created, None if duplicate
        """
        # Check for duplicate
        if await self._is_duplicate_issue(issue):
            logger.debug(
                f"Skipping duplicate issue: {issue.title} " f"for {issue.source_agent_code}"
            )
            return None

        # Persist the issue
        await self._persist_issue(issue)
        logger.info(f"Created issue {issue.id}: {issue.title}")

        # Create task if requested and queue is available
        if create_task and self._task_queue:
            task_id = await self._create_issue_task(issue)
            if task_id:
                issue.task_id = task_id
                issue.task_created_at = datetime.now(timezone.utc)
                await self._update_issue_task(issue.id, task_id)

        return issue.id

    async def create_issues_batch(
        self,
        issues: List[LearningIssue],
        create_tasks: bool = True,
    ) -> List[str]:
        """
        Create multiple issues in batch.

        Args:
            issues: List of issues to create
            create_tasks: Whether to create tasks

        Returns:
            List of created issue IDs
        """
        created_ids = []

        for issue in issues:
            issue_id = await self.create_issue(issue, create_task=create_tasks)
            if issue_id:
                created_ids.append(issue_id)

        return created_ids

    async def get_open_issues(
        self,
        agent_code: Optional[str] = None,
        severity: Optional[IssueSeverity] = None,
        limit: int = 100,
    ) -> List[LearningIssue]:
        """
        Get open issues matching criteria.

        Args:
            agent_code: Filter by source agent
            severity: Filter by severity
            limit: Maximum number of issues

        Returns:
            List of matching issues
        """
        conditions = ["status = 'open'"]
        params: List[Any] = []

        if agent_code:
            conditions.append("source_agent_code = ?")
            params.append(agent_code)

        if severity:
            conditions.append("severity = ?")
            params.append(severity.value)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT * FROM learning_issues
            WHERE {where_clause}
            ORDER BY priority ASC, created_at DESC
            LIMIT ?
        """
        params.append(limit)

        rows = await self._db.fetch_all(query, tuple(params))
        return [self._row_to_issue(row) for row in rows]

    async def get_issue(self, issue_id: str) -> Optional[LearningIssue]:
        """Get a specific issue by ID."""
        row = await self._db.fetch_one(
            "SELECT * FROM learning_issues WHERE id = ?",
            (issue_id,),
        )
        return self._row_to_issue(row) if row else None

    async def resolve_issue(
        self,
        issue_id: str,
        resolution: str,
        resolved_by: str = "system",
    ) -> None:
        """
        Mark an issue as resolved.

        Args:
            issue_id: Issue to resolve
            resolution: Description of how it was resolved
            resolved_by: Who/what resolved it
        """
        now = datetime.now(timezone.utc).isoformat()

        await self._db.execute(
            """
            UPDATE learning_issues
            SET status = 'resolved',
                resolution = ?,
                resolved_by = ?,
                resolved_at = ?
            WHERE id = ?
            """,
            (resolution, resolved_by, now, issue_id),
        )

        logger.info(f"Resolved issue {issue_id}: {resolution}")

    async def dismiss_issue(
        self,
        issue_id: str,
        reason: str,
    ) -> None:
        """
        Dismiss an issue without resolving it.

        Args:
            issue_id: Issue to dismiss
            reason: Reason for dismissal
        """
        now = datetime.now(timezone.utc).isoformat()

        await self._db.execute(
            """
            UPDATE learning_issues
            SET status = 'dismissed',
                resolution = ?,
                resolved_at = ?
            WHERE id = ?
            """,
            (f"Dismissed: {reason}", now, issue_id),
        )

        logger.info(f"Dismissed issue {issue_id}: {reason}")

    async def start_investigation(self, issue_id: str) -> None:
        """Mark an issue as being investigated."""
        await self._db.execute(
            """
            UPDATE learning_issues
            SET status = 'investigating'
            WHERE id = ?
            """,
            (issue_id,),
        )

    async def get_issue_stats(
        self,
        window_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get statistics about issues.

        Returns:
            Dictionary with issue counts and breakdowns
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).isoformat()

        # Total counts by status
        status_counts = await self._db.fetch_all(
            """
            SELECT status, COUNT(*) as count
            FROM learning_issues
            WHERE created_at >= ?
            GROUP BY status
            """,
            (cutoff,),
        )

        # Counts by severity
        severity_counts = await self._db.fetch_all(
            """
            SELECT severity, COUNT(*) as count
            FROM learning_issues
            WHERE created_at >= ? AND status = 'open'
            GROUP BY severity
            """,
            (cutoff,),
        )

        # Counts by type
        type_counts = await self._db.fetch_all(
            """
            SELECT issue_type, COUNT(*) as count
            FROM learning_issues
            WHERE created_at >= ?
            GROUP BY issue_type
            """,
            (cutoff,),
        )

        return {
            "window_hours": window_hours,
            "by_status": {row["status"]: row["count"] for row in status_counts},
            "open_by_severity": {row["severity"]: row["count"] for row in severity_counts},
            "by_type": {row["issue_type"]: row["count"] for row in type_counts},
        }

    # Private methods

    async def _is_duplicate_issue(self, issue: LearningIssue) -> bool:
        """Check if a similar issue already exists and is open."""
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=self._deduplication_window_hours)
        ).isoformat()

        result = await self._db.fetch_one(
            """
            SELECT id FROM learning_issues
            WHERE source_agent_code = ?
            AND issue_type = ?
            AND status IN ('open', 'investigating')
            AND created_at > ?
            """,
            (issue.source_agent_code, issue.issue_type.value, cutoff),
        )

        return result is not None

    async def _persist_issue(self, issue: LearningIssue) -> None:
        """Persist an issue to the database."""
        await self._db.execute(
            """
            INSERT INTO learning_issues (
                id, issue_type, severity, priority,
                source_agent_code, source_level, detected_pattern_id,
                title, description, evidence_json, suggested_action,
                task_id, task_created_at,
                status, resolution, resolved_at, resolved_by,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                issue.id,
                issue.issue_type.value,
                issue.severity.value,
                issue.priority,
                issue.source_agent_code,
                issue.source_level.value,
                issue.detected_pattern_id,
                issue.title,
                issue.description,
                issue.evidence_json,
                issue.suggested_action,
                issue.task_id,
                issue.task_created_at.isoformat() if issue.task_created_at else None,
                issue.status.value,
                issue.resolution,
                issue.resolved_at.isoformat() if issue.resolved_at else None,
                issue.resolved_by,
                issue.created_at.isoformat(),
            ),
        )

    async def _create_issue_task(self, issue: LearningIssue) -> Optional[str]:
        """Create a task for an issue and enqueue it."""
        if not self._task_queue:
            return None

        # Determine task type
        task_type = self.ISSUE_TASK_MAPPING.get(
            issue.issue_type,
            "general_investigation",
        )

        # Create task payload
        payload = {
            "issue_id": issue.id,
            "issue_type": issue.issue_type.value,
            "source_agent": issue.source_agent_code,
            "source_level": issue.source_level.value,
            "title": issue.title,
            "description": issue.description,
            "evidence": issue.evidence_json,
            "suggested_action": issue.suggested_action,
        }

        try:
            # Enqueue the task
            task_id = await self._task_queue.enqueue(
                task_type=task_type,
                payload=payload,
                priority=issue.priority,
                metadata={
                    "source": "learning_system",
                    "issue_severity": issue.severity.value,
                },
            )

            logger.info(f"Created task {task_id} for issue {issue.id}: {issue.title}")
            return task_id

        except Exception as e:
            logger.error(f"Failed to create task for issue {issue.id}: {e}")
            return None

    async def _update_issue_task(
        self,
        issue_id: str,
        task_id: str,
    ) -> None:
        """Update an issue with its created task ID."""
        now = datetime.now(timezone.utc).isoformat()

        await self._db.execute(
            """
            UPDATE learning_issues
            SET task_id = ?,
                task_created_at = ?
            WHERE id = ?
            """,
            (task_id, now, issue_id),
        )

    def _row_to_issue(self, row: Dict[str, Any]) -> LearningIssue:
        """Convert a database row to a LearningIssue."""
        return LearningIssue(
            id=row["id"],
            issue_type=IssueType(row["issue_type"]),
            severity=IssueSeverity(row["severity"]),
            priority=row["priority"],
            source_agent_code=row["source_agent_code"],
            source_level=ScopeLevel(row["source_level"]),
            detected_pattern_id=row["detected_pattern_id"],
            title=row["title"],
            description=row["description"],
            evidence_json=row["evidence_json"],
            suggested_action=row["suggested_action"],
            task_id=row["task_id"],
            task_created_at=(
                datetime.fromisoformat(row["task_created_at"]) if row["task_created_at"] else None
            ),
            status=IssueStatus(row["status"]),
            resolution=row["resolution"],
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
            resolved_by=row["resolved_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
