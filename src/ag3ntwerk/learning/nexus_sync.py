"""
Nexus Learning Sync Bridge.

Synchronizes learning outcomes and patterns from ag3ntwerk LearningOrchestrator
to Nexus PersistentLearning system.

Sync Strategy:
- Real-time: Individual outcomes are queued and synced when bridge connected
- Periodic: Aggregated stats are synced on a configurable interval
- On-demand: Full sync can be triggered manually

What gets synced:
- Task outcome summaries (success rate, duration, effectiveness)
- High-confidence patterns (routing recommendations)
- Agent health aggregates (performance trends)
- Failure investigation summaries (root cause patterns)
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from collections import deque

if TYPE_CHECKING:
    from ag3ntwerk.agents.bridges.nexus_bridge import NexusBridge
    from ag3ntwerk.learning.models import TaskOutcomeRecord, LearnedPattern

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class SyncConfig:
    """Configuration for learning sync."""

    # Sync intervals
    aggregate_sync_interval_seconds: int = 3600  # 1 hour
    pattern_sync_interval_seconds: int = 1800  # 30 minutes

    # Thresholds
    min_pattern_confidence: float = 0.7  # Only sync high-confidence patterns
    min_sample_size: int = 10  # Patterns need sufficient data

    # Queue settings
    max_pending_outcomes: int = 1000  # Max outcomes to queue when offline
    batch_size: int = 50  # Send in batches

    # Channel names (relative to bridge prefix)
    learning_sync_channel: str = "learning:sync"
    pattern_sync_channel: str = "learning:patterns"
    aggregate_sync_channel: str = "learning:aggregates"


@dataclass
class OutcomeSummary:
    """Aggregated outcome summary for an agent/task type combination."""

    agent_code: str
    task_type: str
    total_tasks: int = 0
    successful_tasks: int = 0
    avg_duration_ms: float = 0.0
    avg_effectiveness: float = 0.0
    window_start: datetime = field(default_factory=_utcnow)
    window_end: datetime = field(default_factory=_utcnow)

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "task_type": self.task_type,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "avg_effectiveness": self.avg_effectiveness,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
        }


@dataclass
class PatternSyncRecord:
    """Record of a pattern synced to Nexus."""

    pattern_id: str
    synced_at: datetime
    version: int = 1


class NexusSyncBridge:
    """
    Bridge for syncing learning data from ag3ntwerk to Nexus.

    Operates as an observer/forwarder - it doesn't modify ag3ntwerk learning
    data, just forwards relevant information to Nexus for strategic
    decision-making.

    Usage:
        ```python
        sync_bridge = NexusSyncBridge(nexus_bridge)

        # Hook into orchestrator
        orchestrator.set_sync_bridge(sync_bridge)

        # Start periodic sync
        await sync_bridge.start_periodic_sync()

        # Individual outcomes are synced automatically via forward_outcome()
        ```
    """

    def __init__(
        self,
        nexus_bridge: "NexusBridge",
        config: Optional[SyncConfig] = None,
    ):
        """
        Initialize the sync bridge.

        Args:
            nexus_bridge: Connected NexusBridge for communication
            config: Sync configuration
        """
        self._bridge = nexus_bridge
        self._config = config or SyncConfig()

        # Pending outcomes queue (when offline)
        self._pending_outcomes: deque = deque(maxlen=self._config.max_pending_outcomes)

        # Track synced patterns to avoid duplicates
        self._synced_patterns: Dict[str, PatternSyncRecord] = {}

        # Aggregation buffers
        self._outcome_buffer: Dict[str, OutcomeSummary] = {}

        # Background tasks
        self._aggregate_sync_task: Optional[asyncio.Task] = None
        self._pattern_sync_task: Optional[asyncio.Task] = None
        self._running = False

        # Metrics
        self._metrics = {
            "outcomes_synced": 0,
            "outcomes_queued": 0,
            "outcomes_dropped": 0,
            "patterns_synced": 0,
            "aggregate_syncs": 0,
            "sync_errors": 0,
            "last_sync_at": None,
        }

    @property
    def is_connected(self) -> bool:
        """Check if Nexus bridge is connected."""
        return self._bridge and self._bridge.is_connected

    async def start_periodic_sync(self) -> bool:
        """
        Start periodic sync tasks.

        Returns:
            True if started successfully
        """
        if self._running:
            logger.warning("Periodic sync already running")
            return False

        self._running = True

        # Start aggregate sync task
        self._aggregate_sync_task = asyncio.create_task(self._aggregate_sync_loop())

        # Start pattern sync task
        self._pattern_sync_task = asyncio.create_task(self._pattern_sync_loop())

        logger.info("Started periodic learning sync to Nexus")
        return True

    async def stop_periodic_sync(self) -> None:
        """Stop periodic sync tasks."""
        self._running = False

        if self._aggregate_sync_task:
            self._aggregate_sync_task.cancel()
            try:
                await self._aggregate_sync_task
            except asyncio.CancelledError:
                pass

        if self._pattern_sync_task:
            self._pattern_sync_task.cancel()
            try:
                await self._pattern_sync_task
            except asyncio.CancelledError:
                pass

        # Flush any remaining data
        await self._flush_pending()

        logger.info("Stopped periodic learning sync")

    async def forward_outcome(
        self,
        record: "TaskOutcomeRecord",
    ) -> bool:
        """
        Forward a task outcome to Nexus.

        If the bridge is connected, sends immediately.
        If offline, queues for later sync.

        Args:
            record: The outcome record to forward

        Returns:
            True if sent/queued successfully
        """
        # Add to aggregation buffer
        self._update_aggregates(record)

        # Create lightweight summary for sync
        outcome_data = {
            "task_id": record.task_id,
            "task_type": record.task_type,
            "agent": record.agent_code,
            "manager": record.manager_code,
            "specialist": record.specialist_code,
            "success": record.success,
            "duration_ms": record.duration_ms,
            "effectiveness": record.effectiveness,
            "error_category": record.error_category.value if record.error_category else None,
            "timestamp": record.created_at.isoformat(),
        }

        if self.is_connected:
            return await self._send_outcome(outcome_data)
        else:
            # Queue for later
            self._pending_outcomes.append(outcome_data)
            self._metrics["outcomes_queued"] += 1
            return True

    async def forward_pattern(
        self,
        pattern: "LearnedPattern",
    ) -> bool:
        """
        Forward a learned pattern to Nexus.

        Only high-confidence patterns with sufficient sample size
        are forwarded.

        Args:
            pattern: The pattern to forward

        Returns:
            True if sent successfully
        """
        # Check thresholds
        if pattern.confidence < self._config.min_pattern_confidence:
            logger.debug(
                f"Skipping pattern {pattern.id}: confidence {pattern.confidence:.2f} "
                f"< {self._config.min_pattern_confidence}"
            )
            return False

        if pattern.sample_size < self._config.min_sample_size:
            logger.debug(
                f"Skipping pattern {pattern.id}: sample_size {pattern.sample_size} "
                f"< {self._config.min_sample_size}"
            )
            return False

        # Check if already synced (same version)
        if pattern.id in self._synced_patterns:
            # Could add version check here for pattern updates
            return True

        if not self.is_connected:
            logger.debug(f"Cannot sync pattern {pattern.id}: bridge not connected")
            return False

        pattern_data = {
            "id": pattern.id,
            "type": pattern.pattern_type.value,
            "scope_level": pattern.scope_level.value,
            "scope_code": pattern.scope_code,
            "recommendation": pattern.recommendation,
            "confidence": pattern.confidence,
            "sample_size": pattern.sample_size,
            "success_rate": pattern.success_rate,
            "routing_preference": pattern.routing_preference,
            "created_at": pattern.created_at.isoformat(),
        }

        success = await self._send_pattern(pattern_data)

        if success:
            self._synced_patterns[pattern.id] = PatternSyncRecord(
                pattern_id=pattern.id,
                synced_at=_utcnow(),
            )
            self._metrics["patterns_synced"] += 1

        return success

    async def sync_aggregates(
        self,
        force: bool = False,
    ) -> int:
        """
        Sync aggregated outcome summaries to Nexus.

        Args:
            force: If True, sync even if buffer is small

        Returns:
            Number of aggregates synced
        """
        if not self.is_connected:
            logger.debug("Cannot sync aggregates: bridge not connected")
            return 0

        if not self._outcome_buffer and not force:
            return 0

        channel = f"{self._bridge.config.channel_prefix}:{self._config.aggregate_sync_channel}"

        aggregates = [summary.to_dict() for summary in self._outcome_buffer.values()]

        if not aggregates:
            return 0

        try:
            await self._bridge._redis.publish(
                channel,
                json.dumps(
                    {
                        "type": "aggregate_sync",
                        "aggregates": aggregates,
                        "count": len(aggregates),
                        "timestamp": _utcnow().isoformat(),
                    }
                ),
            )

            self._metrics["aggregate_syncs"] += 1
            self._metrics["last_sync_at"] = _utcnow().isoformat()

            # Clear buffer after successful sync
            self._outcome_buffer.clear()

            logger.info(f"Synced {len(aggregates)} aggregate summaries to Nexus")
            return len(aggregates)

        except Exception as e:
            logger.error(f"Failed to sync aggregates: {e}")
            self._metrics["sync_errors"] += 1
            return 0

    async def full_sync(
        self,
        outcome_tracker=None,
        pattern_store=None,
        window_hours: int = 24,
    ) -> Dict[str, int]:
        """
        Perform a full sync of learning data to Nexus.

        Args:
            outcome_tracker: Optional OutcomeTracker for fetching outcomes
            pattern_store: Optional PatternStore for fetching patterns
            window_hours: Time window for outcomes

        Returns:
            Dict with counts of synced items
        """
        results = {
            "outcomes": 0,
            "patterns": 0,
            "aggregates": 0,
        }

        if not self.is_connected:
            logger.warning("Cannot perform full sync: bridge not connected")
            return results

        # Sync pending outcomes first
        await self._flush_pending()

        # Sync aggregates
        results["aggregates"] = await self.sync_aggregates(force=True)

        # Sync patterns if store provided
        if pattern_store:
            try:
                patterns = await pattern_store.get_active_patterns()
                for pattern in patterns:
                    if await self.forward_pattern(pattern):
                        results["patterns"] += 1
            except Exception as e:
                logger.error(f"Error syncing patterns: {e}")

        logger.info(
            f"Full sync complete: {results['outcomes']} outcomes, "
            f"{results['patterns']} patterns, {results['aggregates']} aggregates"
        )

        return results

    def get_metrics(self) -> Dict[str, Any]:
        """Get sync metrics."""
        return {
            **self._metrics,
            "pending_outcomes": len(self._pending_outcomes),
            "buffered_aggregates": len(self._outcome_buffer),
            "synced_patterns": len(self._synced_patterns),
            "is_connected": self.is_connected,
            "is_running": self._running,
        }

    # ==================== Internal Methods ====================

    def _update_aggregates(self, record: "TaskOutcomeRecord") -> None:
        """Update aggregation buffers with a new outcome."""
        key = f"{record.agent_code}:{record.task_type}"

        if key not in self._outcome_buffer:
            self._outcome_buffer[key] = OutcomeSummary(
                agent_code=record.agent_code,
                task_type=record.task_type,
                window_start=record.created_at,
            )

        summary = self._outcome_buffer[key]
        summary.total_tasks += 1

        if record.success:
            summary.successful_tasks += 1

        # Rolling average for duration
        n = summary.total_tasks
        summary.avg_duration_ms = (summary.avg_duration_ms * (n - 1) + record.duration_ms) / n

        # Rolling average for effectiveness
        if record.effectiveness:
            summary.avg_effectiveness = (
                summary.avg_effectiveness * (n - 1) + record.effectiveness
            ) / n

        summary.window_end = record.created_at

    async def _send_outcome(self, outcome_data: Dict[str, Any]) -> bool:
        """Send a single outcome to Nexus."""
        channel = f"{self._bridge.config.channel_prefix}:{self._config.learning_sync_channel}"

        try:
            await self._bridge._redis.publish(
                channel,
                json.dumps(
                    {
                        "type": "outcome_sync",
                        "outcome": outcome_data,
                        "timestamp": _utcnow().isoformat(),
                    }
                ),
            )
            self._metrics["outcomes_synced"] += 1
            return True

        except Exception as e:
            logger.error(f"Failed to send outcome: {e}")
            self._metrics["sync_errors"] += 1
            return False

    async def _send_pattern(self, pattern_data: Dict[str, Any]) -> bool:
        """Send a pattern to Nexus."""
        channel = f"{self._bridge.config.channel_prefix}:{self._config.pattern_sync_channel}"

        try:
            await self._bridge._redis.publish(
                channel,
                json.dumps(
                    {
                        "type": "pattern_sync",
                        "pattern": pattern_data,
                        "timestamp": _utcnow().isoformat(),
                    }
                ),
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send pattern: {e}")
            self._metrics["sync_errors"] += 1
            return False

    async def _flush_pending(self) -> int:
        """Flush pending outcomes queue."""
        if not self.is_connected or not self._pending_outcomes:
            return 0

        count = 0

        while self._pending_outcomes:
            # Process in batches
            batch = []
            for _ in range(min(self._config.batch_size, len(self._pending_outcomes))):
                if self._pending_outcomes:
                    batch.append(self._pending_outcomes.popleft())

            for outcome in batch:
                if await self._send_outcome(outcome):
                    count += 1
                else:
                    # Put back on failure (at the front)
                    self._pending_outcomes.appendleft(outcome)
                    break

        if count > 0:
            logger.info(f"Flushed {count} pending outcomes to Nexus")

        return count

    async def _aggregate_sync_loop(self) -> None:
        """Background task for periodic aggregate sync."""
        while self._running:
            try:
                await asyncio.sleep(self._config.aggregate_sync_interval_seconds)

                if self._running and self.is_connected:
                    await self.sync_aggregates()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in aggregate sync loop: {e}")

    async def _pattern_sync_loop(self) -> None:
        """Background task for periodic pattern check."""
        while self._running:
            try:
                await asyncio.sleep(self._config.pattern_sync_interval_seconds)

                if self._running and self.is_connected:
                    # Flush any pending outcomes first
                    await self._flush_pending()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in pattern sync loop: {e}")


# Convenience function for creating sync bridge
def create_nexus_sync_bridge(
    nexus_bridge: "NexusBridge",
    config: Optional[SyncConfig] = None,
) -> NexusSyncBridge:
    """
    Create a NexusSyncBridge instance.

    Args:
        nexus_bridge: Connected NexusBridge
        config: Optional sync configuration

    Returns:
        Configured NexusSyncBridge
    """
    return NexusSyncBridge(nexus_bridge, config)
