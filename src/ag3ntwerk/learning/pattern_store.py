"""
Pattern Store - Persistence and retrieval of learned patterns.

Manages the storage and querying of patterns learned from outcome analysis.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.learning.models import (
    LearnedPattern,
    PatternType,
    ScopeLevel,
)

logger = logging.getLogger(__name__)


class PatternStore:
    """
    Manages persistence and retrieval of learned patterns.

    Patterns are stored in the database and cached in memory for
    fast access during task routing.
    """

    def __init__(self, db: Any):
        """
        Initialize the pattern store.

        Args:
            db: Database connection (DatabaseManager or similar)
        """
        self._db = db
        self._cache: Dict[str, List[LearnedPattern]] = {}
        self._cache_loaded = False

    async def load_patterns(self) -> int:
        """
        Load all active patterns into memory cache.

        Returns:
            Number of patterns loaded
        """
        rows = await self._db.fetch_all(
            """
            SELECT * FROM learned_patterns
            WHERE is_active = 1
            ORDER BY confidence DESC
            """
        )

        self._cache.clear()
        count = 0

        for row in rows:
            pattern = self._row_to_pattern(row)
            cache_key = f"{pattern.scope_level.value}:{pattern.scope_code}"

            if cache_key not in self._cache:
                self._cache[cache_key] = []
            self._cache[cache_key].append(pattern)
            count += 1

        self._cache_loaded = True
        logger.info(f"Loaded {count} patterns into cache")
        return count

    async def store_pattern(self, pattern: LearnedPattern) -> str:
        """
        Store a new pattern or update existing one.

        If a pattern with the same type, scope, and conditions exists,
        it will be updated. Otherwise, a new pattern is created.

        Args:
            pattern: The pattern to store

        Returns:
            Pattern ID
        """
        # Check for existing pattern with same signature
        existing = await self._find_matching_pattern(pattern)

        if existing:
            # Update existing pattern
            await self._update_pattern(existing.id, pattern)
            pattern.id = existing.id
            logger.debug(f"Updated existing pattern {pattern.id}")
        else:
            # Insert new pattern
            await self._insert_pattern(pattern)
            logger.info(f"Created new pattern {pattern.id}: {pattern.recommendation}")

        # Update cache
        await self._update_cache(pattern)

        return pattern.id

    async def get_patterns(
        self,
        scope_level: Optional[ScopeLevel] = None,
        scope_code: Optional[str] = None,
        pattern_type: Optional[PatternType] = None,
        task_type: Optional[str] = None,
        is_active: bool = True,
    ) -> List[LearnedPattern]:
        """
        Get patterns matching the specified criteria.

        Args:
            scope_level: Filter by agent/manager/specialist
            scope_code: Filter by agent code
            pattern_type: Filter by pattern type
            task_type: Filter by task type in condition
            is_active: Only return active patterns

        Returns:
            List of matching patterns
        """
        # Try cache first for common queries
        if scope_level and scope_code and is_active and self._cache_loaded:
            cache_key = f"{scope_level.value}:{scope_code}"
            if cache_key in self._cache:
                patterns = self._cache[cache_key]

                # Apply additional filters
                if pattern_type:
                    patterns = [p for p in patterns if p.pattern_type == pattern_type]
                if task_type:
                    patterns = [
                        p for p in patterns if self._pattern_matches_task_type(p, task_type)
                    ]

                return patterns

        # Fall back to database query
        return await self._query_patterns(
            scope_level=scope_level,
            scope_code=scope_code,
            pattern_type=pattern_type,
            task_type=task_type,
            is_active=is_active,
        )

    async def update_pattern_stats(
        self,
        pattern_id: str,
        applied: bool = True,
        success: bool = True,
    ) -> None:
        """
        Update pattern application statistics.

        Args:
            pattern_id: Pattern ID
            applied: Whether the pattern was applied
            success: Whether application was successful
        """
        now = datetime.now(timezone.utc).isoformat()

        if applied:
            await self._db.execute(
                """
                UPDATE learned_patterns
                SET application_count = application_count + 1,
                    last_applied_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, now, pattern_id),
            )

        # Recalculate success rate if we have enough data
        if success is not None:
            # This would need a separate tracking table for full implementation
            # For now, we just track application count
            pass

    async def deactivate_pattern(
        self,
        pattern_id: str,
        reason: Optional[str] = None,
    ) -> None:
        """
        Deactivate a pattern.

        Args:
            pattern_id: Pattern to deactivate
            reason: Reason for deactivation
        """
        now = datetime.now(timezone.utc).isoformat()

        await self._db.execute(
            """
            UPDATE learned_patterns
            SET is_active = 0,
                updated_at = ?
            WHERE id = ?
            """,
            (now, pattern_id),
        )

        # Remove from cache
        for patterns in self._cache.values():
            patterns[:] = [p for p in patterns if p.id != pattern_id]

        logger.info(f"Deactivated pattern {pattern_id}: {reason}")

    async def get_all_active_patterns(self) -> List[LearnedPattern]:
        """
        Get all active patterns from the database.

        Returns:
            List of all active LearnedPattern objects
        """
        rows = await self._db.fetch_all(
            """
            SELECT * FROM learned_patterns
            WHERE is_active = 1
            ORDER BY confidence DESC
            """
        )

        return [self._row_to_pattern(row) for row in rows]

    async def activate_pattern(
        self,
        pattern_id: str,
        reason: Optional[str] = None,
    ) -> None:
        """
        Activate a pattern.

        Args:
            pattern_id: Pattern to activate
            reason: Reason for activation
        """
        now = datetime.now(timezone.utc).isoformat()

        await self._db.execute(
            """
            UPDATE learned_patterns
            SET is_active = 1,
                updated_at = ?
            WHERE id = ?
            """,
            (now, pattern_id),
        )

        # Update cache - reload the pattern and add it
        row = await self._db.fetch_one(
            "SELECT * FROM learned_patterns WHERE id = ?",
            (pattern_id,),
        )
        if row:
            pattern = self._row_to_pattern(row)
            await self._update_cache(pattern)

        logger.info(f"Activated pattern {pattern_id}: {reason}")

    async def get_pattern_by_id(self, pattern_id: str) -> Optional[LearnedPattern]:
        """Get a specific pattern by ID."""
        row = await self._db.fetch_one(
            "SELECT * FROM learned_patterns WHERE id = ?",
            (pattern_id,),
        )
        return self._row_to_pattern(row) if row else None

    # Private methods

    async def _find_matching_pattern(
        self,
        pattern: LearnedPattern,
    ) -> Optional[LearnedPattern]:
        """Find an existing pattern with the same signature."""
        row = await self._db.fetch_one(
            """
            SELECT * FROM learned_patterns
            WHERE pattern_type = ?
            AND scope_level = ?
            AND scope_code = ?
            AND condition_json = ?
            AND is_active = 1
            """,
            (
                pattern.pattern_type.value,
                pattern.scope_level.value,
                pattern.scope_code,
                pattern.condition_json,
            ),
        )
        return self._row_to_pattern(row) if row else None

    async def _insert_pattern(self, pattern: LearnedPattern) -> None:
        """Insert a new pattern into the database."""
        await self._db.execute(
            """
            INSERT INTO learned_patterns (
                id, pattern_type, scope_level, scope_code,
                condition_json, recommendation,
                confidence, sample_size, success_rate, avg_improvement,
                confidence_adjustment, priority_adjustment, routing_preference,
                is_active, last_applied_at, application_count, expires_at,
                validated_by, validation_score,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pattern.id,
                pattern.pattern_type.value,
                pattern.scope_level.value,
                pattern.scope_code,
                pattern.condition_json,
                pattern.recommendation,
                pattern.confidence,
                pattern.sample_size,
                pattern.success_rate,
                pattern.avg_improvement,
                pattern.confidence_adjustment,
                pattern.priority_adjustment,
                pattern.routing_preference,
                1 if pattern.is_active else 0,
                pattern.last_applied_at.isoformat() if pattern.last_applied_at else None,
                pattern.application_count,
                pattern.expires_at.isoformat() if pattern.expires_at else None,
                pattern.validated_by,
                pattern.validation_score,
                pattern.created_at.isoformat(),
                pattern.updated_at.isoformat(),
            ),
        )

    async def _update_pattern(
        self,
        pattern_id: str,
        pattern: LearnedPattern,
    ) -> None:
        """Update an existing pattern."""
        now = datetime.now(timezone.utc).isoformat()

        await self._db.execute(
            """
            UPDATE learned_patterns
            SET recommendation = ?,
                confidence = ?,
                sample_size = ?,
                success_rate = ?,
                avg_improvement = ?,
                confidence_adjustment = ?,
                priority_adjustment = ?,
                routing_preference = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                pattern.recommendation,
                pattern.confidence,
                pattern.sample_size,
                pattern.success_rate,
                pattern.avg_improvement,
                pattern.confidence_adjustment,
                pattern.priority_adjustment,
                pattern.routing_preference,
                now,
                pattern_id,
            ),
        )

    async def _update_cache(self, pattern: LearnedPattern) -> None:
        """Update the in-memory cache with a pattern."""
        if not self._cache_loaded:
            return

        cache_key = f"{pattern.scope_level.value}:{pattern.scope_code}"

        if cache_key not in self._cache:
            self._cache[cache_key] = []

        # Remove existing pattern with same ID
        self._cache[cache_key] = [p for p in self._cache[cache_key] if p.id != pattern.id]

        # Add updated pattern if active
        if pattern.is_active:
            self._cache[cache_key].append(pattern)

            # Re-sort by confidence
            self._cache[cache_key].sort(key=lambda p: p.confidence, reverse=True)

    async def _query_patterns(
        self,
        scope_level: Optional[ScopeLevel] = None,
        scope_code: Optional[str] = None,
        pattern_type: Optional[PatternType] = None,
        task_type: Optional[str] = None,
        is_active: bool = True,
    ) -> List[LearnedPattern]:
        """Query patterns from database."""
        conditions = []
        params = []

        if scope_level:
            conditions.append("scope_level = ?")
            params.append(scope_level.value)

        if scope_code:
            conditions.append("scope_code = ?")
            params.append(scope_code)

        if pattern_type:
            conditions.append("pattern_type = ?")
            params.append(pattern_type.value)

        if is_active:
            conditions.append("is_active = 1")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT * FROM learned_patterns
            WHERE {where_clause}
            ORDER BY confidence DESC
        """

        rows = await self._db.fetch_all(query, tuple(params))
        patterns = [self._row_to_pattern(row) for row in rows]

        # Filter by task type if specified
        if task_type:
            patterns = [p for p in patterns if self._pattern_matches_task_type(p, task_type)]

        return patterns

    def _pattern_matches_task_type(
        self,
        pattern: LearnedPattern,
        task_type: str,
    ) -> bool:
        """Check if a pattern's condition matches a task type."""
        try:
            condition = json.loads(pattern.condition_json)
            pattern_task_type = condition.get("task_type")

            if pattern_task_type is None:
                return True  # Pattern applies to all task types

            if isinstance(pattern_task_type, list):
                return task_type in pattern_task_type

            return pattern_task_type == task_type

        except (json.JSONDecodeError, TypeError):
            return False

    def _row_to_pattern(self, row: Dict[str, Any]) -> LearnedPattern:
        """Convert a database row to a LearnedPattern object."""
        return LearnedPattern(
            id=row["id"],
            pattern_type=PatternType(row["pattern_type"]),
            scope_level=ScopeLevel(row["scope_level"]),
            scope_code=row["scope_code"],
            condition_json=row["condition_json"],
            recommendation=row["recommendation"],
            confidence=row["confidence"] or 0.5,
            sample_size=row["sample_size"] or 0,
            success_rate=row["success_rate"],
            avg_improvement=row["avg_improvement"],
            confidence_adjustment=row["confidence_adjustment"] or 0.0,
            priority_adjustment=row["priority_adjustment"] or 0,
            routing_preference=row["routing_preference"],
            is_active=bool(row["is_active"]),
            last_applied_at=(
                datetime.fromisoformat(row["last_applied_at"]) if row["last_applied_at"] else None
            ),
            application_count=row["application_count"] or 0,
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            validated_by=row["validated_by"],
            validation_score=row["validation_score"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
