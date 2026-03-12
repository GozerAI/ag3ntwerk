"""
Handler Generator - Auto-generates task handlers from successful patterns.

Analyzes successful task executions to:
1. Extract common prompt patterns and structures
2. Identify effective parameter configurations
3. Generate new handler templates
4. Track handler performance over time
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4
from enum import Enum

logger = logging.getLogger(__name__)


class HandlerStatus(Enum):
    """Status of a generated handler."""

    DRAFT = "draft"  # Newly generated, not yet tested
    TESTING = "testing"  # Being tested in production
    ACTIVE = "active"  # Approved and in use
    DEPRECATED = "deprecated"  # No longer used


@dataclass
class GeneratedHandler:
    """A handler generated from successful patterns."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    task_type: str = ""
    description: str = ""

    # Handler configuration
    prompt_template: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_context: List[str] = field(default_factory=list)
    output_format: str = ""

    # Source information
    source_patterns: List[str] = field(default_factory=list)
    source_outcomes: List[str] = field(default_factory=list)
    sample_size: int = 0

    # Performance tracking
    status: HandlerStatus = HandlerStatus.DRAFT
    confidence: float = 0.5
    times_used: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_duration_ms: float = 0.0

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "auto"  # "auto" for generated, agent code for manual

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total

    def record_usage(
        self,
        success: bool,
        duration_ms: float = 0.0,
    ) -> None:
        """Record a usage of this handler."""
        self.times_used += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        # Update average duration
        if self.times_used == 1:
            self.avg_duration_ms = duration_ms
        else:
            # Running average
            self.avg_duration_ms = (
                self.avg_duration_ms * (self.times_used - 1) + duration_ms
            ) / self.times_used

        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "description": self.description,
            "prompt_template": self.prompt_template,
            "parameters": self.parameters,
            "required_context": self.required_context,
            "output_format": self.output_format,
            "source_patterns": self.source_patterns,
            "sample_size": self.sample_size,
            "status": self.status.value,
            "confidence": self.confidence,
            "times_used": self.times_used,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class HandlerCandidate:
    """A candidate for handler generation."""

    task_type: str
    common_patterns: List[str] = field(default_factory=list)
    parameter_ranges: Dict[str, Any] = field(default_factory=dict)
    context_keys: Set[str] = field(default_factory=set)
    sample_outputs: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    sample_count: int = 0


class HandlerGenerator:
    """
    Generates task handlers from successful execution patterns.

    Analyzes outcomes to identify:
    - Common prompt structures that lead to success
    - Effective parameter configurations
    - Required context fields
    - Output format patterns
    """

    # Minimum samples before considering handler generation
    MIN_SAMPLES_FOR_GENERATION = 20

    # Minimum success rate to consider a pattern
    MIN_SUCCESS_RATE = 0.7

    # Confidence threshold for auto-activation
    AUTO_ACTIVATE_CONFIDENCE = 0.8

    # Performance threshold for deprecation
    DEPRECATION_THRESHOLD = 0.5

    def __init__(self, db: Any, pattern_store: Any):
        """
        Initialize the handler generator.

        Args:
            db: Database connection
            pattern_store: PatternStore for accessing learned patterns
        """
        self._db = db
        self._pattern_store = pattern_store

        # Generated handlers
        self._handlers: Dict[str, GeneratedHandler] = {}

    async def analyze_task_type(
        self,
        task_type: str,
        window_hours: int = 168,  # 1 week
    ) -> Optional[HandlerCandidate]:
        """
        Analyze a task type for potential handler generation.

        Args:
            task_type: Type of task to analyze
            window_hours: Time window for analysis

        Returns:
            HandlerCandidate if generation is viable, None otherwise
        """
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        try:
            # Get successful outcomes for this task type
            rows = await self._db.fetch_all(
                """
                SELECT task_id, context_snapshot, output_summary, duration_ms
                FROM learning_outcomes
                WHERE task_type = ? AND success = 1 AND created_at >= ?
                ORDER BY effectiveness DESC
                LIMIT 100
                """,
                (task_type, window_start.isoformat()),
            )

            if len(rows) < self.MIN_SAMPLES_FOR_GENERATION:
                return None

            # Get overall stats
            stats_row = await self._db.fetch_one(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                FROM learning_outcomes
                WHERE task_type = ? AND created_at >= ?
                """,
                (task_type, window_start.isoformat()),
            )

            if not stats_row or stats_row["total"] == 0:
                return None

            success_rate = stats_row["successful"] / stats_row["total"]

            if success_rate < self.MIN_SUCCESS_RATE:
                return None

            # Analyze patterns
            candidate = HandlerCandidate(
                task_type=task_type,
                success_rate=success_rate,
                sample_count=len(rows),
            )

            # Extract common context keys
            context_keys: Set[str] = set()
            for row in rows:
                if row["context_snapshot"]:
                    import json

                    try:
                        context = json.loads(row["context_snapshot"])
                        context_keys.update(context.keys())
                    except (json.JSONDecodeError, TypeError):
                        pass

            candidate.context_keys = context_keys

            # Extract output samples
            for row in rows[:5]:  # Top 5 successful outputs
                if row["output_summary"]:
                    candidate.sample_outputs.append(row["output_summary"])

            # Analyze parameter patterns from context
            candidate.parameter_ranges = self._analyze_parameter_ranges(rows)

            # Extract common patterns from outputs
            candidate.common_patterns = self._extract_common_patterns(
                [row["output_summary"] for row in rows if row["output_summary"]]
            )

            return candidate

        except Exception as e:
            logger.warning(f"Failed to analyze task type {task_type}: {e}")
            return None

    async def generate_handler(
        self,
        candidate: HandlerCandidate,
    ) -> Optional[GeneratedHandler]:
        """
        Generate a handler from a candidate.

        Args:
            candidate: Handler candidate with analysis results

        Returns:
            Generated handler or None
        """
        if candidate.sample_count < self.MIN_SAMPLES_FOR_GENERATION:
            return None

        # Build prompt template from patterns
        prompt_template = self._build_prompt_template(candidate)

        # Determine optimal parameters
        parameters = self._determine_parameters(candidate)

        # Create handler
        handler = GeneratedHandler(
            name=f"auto_{candidate.task_type}",
            task_type=candidate.task_type,
            description=f"Auto-generated handler for {candidate.task_type} based on {candidate.sample_count} successful executions",
            prompt_template=prompt_template,
            parameters=parameters,
            required_context=list(candidate.context_keys),
            output_format=self._infer_output_format(candidate.sample_outputs),
            sample_size=candidate.sample_count,
            confidence=min(0.9, candidate.success_rate),
            status=HandlerStatus.DRAFT,
        )

        # Get related patterns
        patterns = await self._pattern_store.get_patterns(
            task_type=candidate.task_type,
            is_active=True,
        )
        handler.source_patterns = [p.id for p in patterns[:5]]

        # Store handler
        self._handlers[handler.id] = handler
        await self._save_handler(handler)

        logger.info(
            f"Generated handler {handler.name} for {candidate.task_type} "
            f"(confidence: {handler.confidence:.2f})"
        )

        return handler

    async def get_handler_for_task(
        self,
        task_type: str,
    ) -> Optional[GeneratedHandler]:
        """
        Get an active handler for a task type.

        Args:
            task_type: Type of task

        Returns:
            Active handler if available
        """
        for handler in self._handlers.values():
            if handler.task_type == task_type and handler.status in (
                HandlerStatus.ACTIVE,
                HandlerStatus.TESTING,
            ):
                return handler
        return None

    async def record_handler_usage(
        self,
        handler_id: str,
        success: bool,
        duration_ms: float = 0.0,
    ) -> None:
        """
        Record usage of a handler.

        Args:
            handler_id: ID of the handler
            success: Whether execution succeeded
            duration_ms: Execution duration
        """
        handler = self._handlers.get(handler_id)
        if not handler:
            return

        handler.record_usage(success, duration_ms)

        # Check for status transitions
        if handler.status == HandlerStatus.TESTING:
            if handler.times_used >= 50:  # Enough test data
                if handler.success_rate >= self.AUTO_ACTIVATE_CONFIDENCE:
                    handler.status = HandlerStatus.ACTIVE
                    logger.info(
                        f"Handler {handler.name} promoted to ACTIVE "
                        f"(success rate: {handler.success_rate:.1%})"
                    )
                elif handler.success_rate < self.DEPRECATION_THRESHOLD:
                    handler.status = HandlerStatus.DEPRECATED
                    logger.info(
                        f"Handler {handler.name} DEPRECATED "
                        f"(success rate: {handler.success_rate:.1%})"
                    )

        elif handler.status == HandlerStatus.ACTIVE:
            # Check for performance degradation
            if handler.times_used > 100 and handler.success_rate < self.DEPRECATION_THRESHOLD:
                handler.status = HandlerStatus.DEPRECATED
                logger.warning(
                    f"Handler {handler.name} degraded and DEPRECATED "
                    f"(success rate: {handler.success_rate:.1%})"
                )

        await self._save_handler(handler)

    async def activate_handler(self, handler_id: str) -> bool:
        """
        Manually activate a handler for testing.

        Args:
            handler_id: ID of the handler

        Returns:
            True if activated
        """
        handler = self._handlers.get(handler_id)
        if not handler:
            return False

        if handler.status == HandlerStatus.DRAFT:
            handler.status = HandlerStatus.TESTING
            handler.updated_at = datetime.now(timezone.utc)
            await self._save_handler(handler)
            logger.info(f"Handler {handler.name} activated for TESTING")
            return True

        return False

    async def deprecate_handler(
        self,
        handler_id: str,
        reason: str = "",
    ) -> bool:
        """
        Manually deprecate a handler.

        Args:
            handler_id: ID of the handler
            reason: Reason for deprecation

        Returns:
            True if deprecated
        """
        handler = self._handlers.get(handler_id)
        if not handler:
            return False

        handler.status = HandlerStatus.DEPRECATED
        handler.updated_at = datetime.now(timezone.utc)
        await self._save_handler(handler)
        logger.info(f"Handler {handler.name} DEPRECATED: {reason}")
        return True

    async def get_handlers_by_status(
        self,
        status: HandlerStatus,
    ) -> List[GeneratedHandler]:
        """Get handlers with a specific status."""
        return [h for h in self._handlers.values() if h.status == status]

    async def get_all_handlers(self) -> List[GeneratedHandler]:
        """Get all generated handlers."""
        return list(self._handlers.values())

    async def get_handler(self, handler_id: str) -> Optional[GeneratedHandler]:
        """Get a specific handler by ID."""
        return self._handlers.get(handler_id)

    async def find_generation_candidates(
        self,
        min_samples: int = 20,
        min_success_rate: float = 0.7,
    ) -> List[str]:
        """
        Find task types that are candidates for handler generation.

        Args:
            min_samples: Minimum number of samples
            min_success_rate: Minimum success rate

        Returns:
            List of task types that could have handlers generated
        """
        try:
            rows = await self._db.fetch_all(
                """
                SELECT
                    task_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                FROM learning_outcomes
                WHERE created_at >= ?
                GROUP BY task_type
                HAVING total >= ?
                """,
                (
                    (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
                    min_samples,
                ),
            )

            candidates = []
            for row in rows:
                success_rate = row["successful"] / row["total"]
                if success_rate >= min_success_rate:
                    # Check if handler already exists
                    has_handler = any(
                        h.task_type == row["task_type"] and h.status != HandlerStatus.DEPRECATED
                        for h in self._handlers.values()
                    )
                    if not has_handler:
                        candidates.append(row["task_type"])

            return candidates

        except Exception as e:
            logger.warning(f"Failed to find generation candidates: {e}")
            return []

    def _analyze_parameter_ranges(
        self,
        rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analyze parameter ranges from successful outcomes."""
        import json

        ranges: Dict[str, List[Any]] = {}

        for row in rows:
            if row["context_snapshot"]:
                try:
                    context = json.loads(row["context_snapshot"])
                    for key, value in context.items():
                        if key not in ranges:
                            ranges[key] = []
                        ranges[key].append(value)
                except (json.JSONDecodeError, TypeError):
                    pass

        # Analyze ranges
        result = {}
        for key, values in ranges.items():
            if not values:
                continue

            # Check if numeric
            numeric_values = [v for v in values if isinstance(v, (int, float))]
            if len(numeric_values) > len(values) * 0.8:
                result[key] = {
                    "type": "numeric",
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                    "avg": sum(numeric_values) / len(numeric_values),
                }
            else:
                # Categorical
                unique = list(set(str(v) for v in values))
                if len(unique) <= 10:
                    result[key] = {
                        "type": "categorical",
                        "values": unique,
                    }

        return result

    def _extract_common_patterns(
        self,
        outputs: List[str],
    ) -> List[str]:
        """Extract common patterns from outputs."""
        if not outputs:
            return []

        patterns = []

        # Find common prefixes
        prefixes: Dict[str, int] = {}
        for output in outputs:
            words = output.split()[:5]  # First 5 words
            if words:
                prefix = " ".join(words)
                prefixes[prefix] = prefixes.get(prefix, 0) + 1

        # Keep patterns that appear in >30% of outputs
        threshold = len(outputs) * 0.3
        for prefix, count in sorted(prefixes.items(), key=lambda x: -x[1]):
            if count >= threshold:
                patterns.append(f"Common start: {prefix}...")

        # Find structural patterns (bullet points, numbered lists, etc.)
        bullet_count = sum(1 for o in outputs if "•" in o or "- " in o)
        numbered_count = sum(1 for o in outputs if re.search(r"^\d+\.", o, re.MULTILINE))

        if bullet_count > len(outputs) * 0.5:
            patterns.append("Uses bullet points")
        if numbered_count > len(outputs) * 0.5:
            patterns.append("Uses numbered lists")

        return patterns[:5]  # Top 5 patterns

    def _build_prompt_template(
        self,
        candidate: HandlerCandidate,
    ) -> str:
        """Build a prompt template from candidate analysis."""
        template_parts = [
            f"Task: {candidate.task_type}",
            "",
            "Context:",
        ]

        # Add required context fields
        for key in sorted(candidate.context_keys):
            template_parts.append(f"  - {key}: {{{key}}}")

        template_parts.append("")
        template_parts.append("Instructions:")
        template_parts.append(
            f"  Process the {candidate.task_type} task using the provided context."
        )

        # Add pattern-based instructions
        for pattern in candidate.common_patterns[:3]:
            template_parts.append(f"  - {pattern}")

        template_parts.append("")
        template_parts.append("Output:")
        template_parts.append("  Provide a structured response.")

        return "\n".join(template_parts)

    def _determine_parameters(
        self,
        candidate: HandlerCandidate,
    ) -> Dict[str, Any]:
        """Determine optimal parameters from analysis."""
        params = {}

        for key, range_info in candidate.parameter_ranges.items():
            if range_info["type"] == "numeric":
                # Use average as default
                params[key] = {
                    "default": range_info["avg"],
                    "min": range_info["min"],
                    "max": range_info["max"],
                }
            elif range_info["type"] == "categorical":
                # Use most common value (first in list)
                params[key] = {
                    "default": range_info["values"][0] if range_info["values"] else None,
                    "allowed": range_info["values"],
                }

        return params

    def _infer_output_format(
        self,
        sample_outputs: List[str],
    ) -> str:
        """Infer the expected output format from samples."""
        if not sample_outputs:
            return "text"

        # Check for JSON
        json_count = 0
        for output in sample_outputs:
            if output.strip().startswith("{") or output.strip().startswith("["):
                json_count += 1

        if json_count > len(sample_outputs) * 0.5:
            return "json"

        # Check for markdown
        md_count = sum(1 for o in sample_outputs if "##" in o or "```" in o)
        if md_count > len(sample_outputs) * 0.5:
            return "markdown"

        return "text"

    async def _save_handler(self, handler: GeneratedHandler) -> None:
        """Save handler to database."""
        import json

        try:
            await self._db.execute(
                """
                INSERT OR REPLACE INTO generated_handlers (
                    id, name, task_type, description,
                    prompt_template, parameters_json, required_context_json,
                    output_format, source_patterns_json, sample_size,
                    status, confidence, times_used, success_count, failure_count,
                    avg_duration_ms, created_at, updated_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    handler.id,
                    handler.name,
                    handler.task_type,
                    handler.description,
                    handler.prompt_template,
                    json.dumps(handler.parameters),
                    json.dumps(handler.required_context),
                    handler.output_format,
                    json.dumps(handler.source_patterns),
                    handler.sample_size,
                    handler.status.value,
                    handler.confidence,
                    handler.times_used,
                    handler.success_count,
                    handler.failure_count,
                    handler.avg_duration_ms,
                    handler.created_at.isoformat(),
                    handler.updated_at.isoformat(),
                    handler.created_by,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to save handler: {e}")

    async def load_handlers(self) -> int:
        """
        Load handlers from database.

        Returns:
            Number of handlers loaded
        """
        import json

        try:
            rows = await self._db.fetch_all(
                """
                SELECT * FROM generated_handlers
                WHERE status != 'deprecated'
                """
            )

            self._handlers.clear()

            for row in rows:
                handler = GeneratedHandler(
                    id=row["id"],
                    name=row["name"],
                    task_type=row["task_type"],
                    description=row["description"],
                    prompt_template=row["prompt_template"],
                    parameters=json.loads(row["parameters_json"]) if row["parameters_json"] else {},
                    required_context=(
                        json.loads(row["required_context_json"])
                        if row["required_context_json"]
                        else []
                    ),
                    output_format=row["output_format"],
                    source_patterns=(
                        json.loads(row["source_patterns_json"])
                        if row["source_patterns_json"]
                        else []
                    ),
                    sample_size=row["sample_size"],
                    status=HandlerStatus(row["status"]),
                    confidence=row["confidence"],
                    times_used=row["times_used"],
                    success_count=row["success_count"],
                    failure_count=row["failure_count"],
                    avg_duration_ms=row["avg_duration_ms"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    created_by=row["created_by"],
                )
                self._handlers[handler.id] = handler

            logger.info(f"Loaded {len(self._handlers)} generated handlers")
            return len(self._handlers)

        except Exception as e:
            logger.warning(f"Failed to load handlers: {e}")
            return 0
