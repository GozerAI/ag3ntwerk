"""
Plugin Telemetry Adapter - Tracks outcomes from plugin operations.

Enables plugins to report their outcomes to the learning system,
allowing patterns to be detected across plugin operations.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ag3ntwerk.learning.models import (
    HierarchyPath,
    OutcomeType,
    ErrorCategory,
)

if TYPE_CHECKING:
    from ag3ntwerk.learning.outcome_tracker import OutcomeTracker
    from ag3ntwerk.learning.pattern_store import PatternStore

logger = logging.getLogger(__name__)


@dataclass
class PluginOperation:
    """
    Record of a plugin operation.
    """

    plugin_id: str
    operation: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "operation": self.operation,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
        }


@dataclass
class PluginStats:
    """
    Aggregated statistics for a plugin.
    """

    plugin_id: str
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    avg_duration_ms: float = 0.0
    success_rate: float = 0.0
    operations_by_type: Dict[str, int] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)
    last_operation_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "avg_duration_ms": self.avg_duration_ms,
            "success_rate": self.success_rate,
            "operations_by_type": self.operations_by_type,
            "error_counts": self.error_counts,
            "last_operation_at": (
                self.last_operation_at.isoformat() if self.last_operation_at else None
            ),
        }


class PluginTelemetryAdapter:
    """
    Adapter for tracking plugin operation outcomes.

    Allows plugins to report their outcomes to the learning system
    for pattern detection and analysis.
    """

    # Virtual agent code for plugin operations
    PLUGIN_AGENT = "PLUGIN_SYSTEM"

    # Task type prefix for plugin operations
    TASK_TYPE_PREFIX = "plugin:"

    def __init__(
        self,
        outcome_tracker: "OutcomeTracker",
        pattern_store: Optional["PatternStore"] = None,
    ):
        """
        Initialize the plugin telemetry adapter.

        Args:
            outcome_tracker: OutcomeTracker for recording outcomes
            pattern_store: Optional PatternStore for pattern queries
        """
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store

        # In-memory cache of recent operations (for quick stats)
        self._recent_operations: List[PluginOperation] = []
        self._max_recent_operations = 1000

        # Plugin registration
        self._registered_plugins: Dict[str, Dict[str, Any]] = {}

    def register_plugin(
        self,
        plugin_id: str,
        name: str,
        version: str,
        operations: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a plugin for telemetry tracking.

        Args:
            plugin_id: Unique plugin identifier
            name: Human-readable plugin name
            version: Plugin version
            operations: List of operation names this plugin supports
            metadata: Optional additional metadata
        """
        self._registered_plugins[plugin_id] = {
            "plugin_id": plugin_id,
            "name": name,
            "version": version,
            "operations": operations,
            "metadata": metadata or {},
            "registered_at": datetime.now(timezone.utc),
        }
        logger.info(f"Registered plugin for telemetry: {plugin_id} ({name} v{version})")

    def unregister_plugin(self, plugin_id: str) -> bool:
        """
        Unregister a plugin from telemetry tracking.

        Args:
            plugin_id: Plugin to unregister

        Returns:
            True if plugin was unregistered
        """
        if plugin_id in self._registered_plugins:
            del self._registered_plugins[plugin_id]
            logger.info(f"Unregistered plugin from telemetry: {plugin_id}")
            return True
        return False

    def get_registered_plugins(self) -> List[Dict[str, Any]]:
        """Get list of registered plugins."""
        return list(self._registered_plugins.values())

    async def record_plugin_outcome(
        self,
        plugin_id: str,
        operation: str,
        success: bool,
        duration_ms: float,
        error: Optional[str] = None,
        input_summary: Optional[str] = None,
        output_summary: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record the outcome of a plugin operation.

        Args:
            plugin_id: Plugin that performed the operation
            operation: Operation name (e.g., "analyze", "transform")
            success: Whether the operation succeeded
            duration_ms: Operation duration in milliseconds
            error: Error message if failed
            input_summary: Optional summary of input
            output_summary: Optional summary of output
            context: Additional context

        Returns:
            Outcome record ID
        """
        # Create plugin operation record
        now = datetime.now(timezone.utc)
        operation_record = PluginOperation(
            plugin_id=plugin_id,
            operation=operation,
            started_at=now - timedelta(milliseconds=duration_ms),
            completed_at=now,
            duration_ms=duration_ms,
            success=success,
            error=error,
            input_summary=input_summary,
            output_summary=output_summary,
            context=context or {},
        )

        # Add to recent operations cache
        self._recent_operations.append(operation_record)
        if len(self._recent_operations) > self._max_recent_operations:
            self._recent_operations = self._recent_operations[-self._max_recent_operations :]

        # Create task type for this plugin operation
        task_type = f"{self.TASK_TYPE_PREFIX}{plugin_id}:{operation}"

        # Create hierarchy path (plugins are under the virtual PLUGIN_SYSTEM agent)
        hierarchy_path = HierarchyPath(
            agent=self.PLUGIN_AGENT,
            manager=plugin_id,  # Plugin acts as a "manager"
            specialist=operation,  # Operation acts as a "specialist"
        )

        # Record to the learning system
        outcome_id = await self._outcome_tracker.record_outcome(
            task_id=f"plugin-{plugin_id}-{operation}-{now.timestamp()}",
            task_type=task_type,
            hierarchy_path=hierarchy_path,
            success=success,
            duration_ms=duration_ms,
            error=error,
            output_summary=output_summary,
            context=context,
        )

        logger.debug(
            f"Recorded plugin outcome: {plugin_id}/{operation} "
            f"success={success} duration={duration_ms:.1f}ms"
        )

        return outcome_id

    async def start_operation(
        self,
        plugin_id: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> "OperationContext":
        """
        Start tracking a plugin operation.

        Returns a context manager that automatically records the outcome.

        Args:
            plugin_id: Plugin performing the operation
            operation: Operation name
            context: Additional context

        Returns:
            OperationContext to use with 'async with'
        """
        return OperationContext(
            adapter=self,
            plugin_id=plugin_id,
            operation=operation,
            context=context or {},
        )

    async def get_plugin_stats(
        self,
        plugin_id: str,
        window_hours: int = 24,
    ) -> PluginStats:
        """
        Get aggregated statistics for a plugin.

        Args:
            plugin_id: Plugin to get stats for
            window_hours: Time window in hours

        Returns:
            PluginStats with aggregated metrics
        """
        # Filter recent operations for this plugin
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        plugin_ops = [
            op
            for op in self._recent_operations
            if op.plugin_id == plugin_id and op.started_at >= cutoff
        ]

        if not plugin_ops:
            return PluginStats(plugin_id=plugin_id)

        # Aggregate stats
        total = len(plugin_ops)
        successful = sum(1 for op in plugin_ops if op.success)
        durations = [op.duration_ms for op in plugin_ops]

        # Group by operation type
        ops_by_type: Dict[str, int] = {}
        for op in plugin_ops:
            ops_by_type[op.operation] = ops_by_type.get(op.operation, 0) + 1

        # Count errors
        error_counts: Dict[str, int] = {}
        for op in plugin_ops:
            if op.error:
                error_type = self._categorize_error(op.error)
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return PluginStats(
            plugin_id=plugin_id,
            total_operations=total,
            successful_operations=successful,
            failed_operations=total - successful,
            avg_duration_ms=sum(durations) / len(durations) if durations else 0.0,
            success_rate=successful / total if total > 0 else 0.0,
            operations_by_type=ops_by_type,
            error_counts=error_counts,
            last_operation_at=max(op.completed_at or op.started_at for op in plugin_ops),
        )

    async def get_all_plugin_stats(
        self,
        window_hours: int = 24,
    ) -> List[PluginStats]:
        """
        Get statistics for all plugins.

        Args:
            window_hours: Time window in hours

        Returns:
            List of PluginStats for all active plugins
        """
        # Get unique plugin IDs from recent operations
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        plugin_ids = set(op.plugin_id for op in self._recent_operations if op.started_at >= cutoff)

        # Add registered plugins
        plugin_ids.update(self._registered_plugins.keys())

        # Get stats for each
        stats_list = []
        for plugin_id in plugin_ids:
            stats = await self.get_plugin_stats(plugin_id, window_hours)
            stats_list.append(stats)

        return sorted(stats_list, key=lambda s: s.total_operations, reverse=True)

    async def get_plugin_patterns(
        self,
        plugin_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get learned patterns for a plugin.

        Args:
            plugin_id: Plugin to get patterns for

        Returns:
            List of patterns relevant to this plugin
        """
        if not self._pattern_store:
            return []

        patterns = await self._pattern_store.get_patterns(
            scope_code=plugin_id,
            is_active=True,
        )

        return [
            {
                "id": p.id,
                "type": p.pattern_type.value,
                "task_type": p.task_type,
                "confidence": p.confidence,
                "success_rate": p.success_rate,
                "sample_size": p.sample_size,
            }
            for p in patterns
        ]

    async def get_recent_operations(
        self,
        plugin_id: Optional[str] = None,
        operation: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get recent plugin operations.

        Args:
            plugin_id: Optional filter by plugin
            operation: Optional filter by operation
            limit: Max operations to return

        Returns:
            List of recent operations
        """
        ops = self._recent_operations

        if plugin_id:
            ops = [op for op in ops if op.plugin_id == plugin_id]

        if operation:
            ops = [op for op in ops if op.operation == operation]

        # Sort by most recent first
        ops = sorted(ops, key=lambda op: op.started_at, reverse=True)

        return [op.to_dict() for op in ops[:limit]]

    def _categorize_error(self, error: str) -> str:
        """Categorize an error message for aggregation."""
        error_lower = error.lower()

        if any(kw in error_lower for kw in ["timeout", "timed out"]):
            return "timeout"
        if any(kw in error_lower for kw in ["connection", "network", "unreachable"]):
            return "network"
        if any(kw in error_lower for kw in ["permission", "access denied", "unauthorized"]):
            return "permission"
        if any(kw in error_lower for kw in ["not found", "404", "missing"]):
            return "not_found"
        if any(kw in error_lower for kw in ["invalid", "parse", "format"]):
            return "validation"

        return "other"


class OperationContext:
    """
    Context manager for tracking plugin operations.

    Usage:
        async with adapter.start_operation("my_plugin", "analyze") as ctx:
            result = await do_analysis()
            ctx.set_output(str(result))
    """

    def __init__(
        self,
        adapter: PluginTelemetryAdapter,
        plugin_id: str,
        operation: str,
        context: Dict[str, Any],
    ):
        self._adapter = adapter
        self._plugin_id = plugin_id
        self._operation = operation
        self._context = context
        self._start_time: Optional[datetime] = None
        self._success = True
        self._error: Optional[str] = None
        self._output_summary: Optional[str] = None
        self._input_summary: Optional[str] = None

    def set_input(self, input_summary: str) -> None:
        """Set the input summary."""
        self._input_summary = input_summary

    def set_output(self, output_summary: str) -> None:
        """Set the output summary."""
        self._output_summary = output_summary

    def set_error(self, error: str) -> None:
        """Mark the operation as failed with an error."""
        self._success = False
        self._error = error

    async def __aenter__(self) -> "OperationContext":
        self._start_time = datetime.now(timezone.utc)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        end_time = datetime.now(timezone.utc)
        duration_ms = (end_time - self._start_time).total_seconds() * 1000

        # If an exception occurred, mark as failed
        if exc_type is not None:
            self._success = False
            self._error = str(exc_val)

        # Record the outcome
        await self._adapter.record_plugin_outcome(
            plugin_id=self._plugin_id,
            operation=self._operation,
            success=self._success,
            duration_ms=duration_ms,
            error=self._error,
            input_summary=self._input_summary,
            output_summary=self._output_summary,
            context=self._context,
        )
