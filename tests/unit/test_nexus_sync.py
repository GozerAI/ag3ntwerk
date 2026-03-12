"""
Tests for NexusSyncBridge (Sprint 4.2).

Tests cover:
- Outcome forwarding
- Pattern syncing
- Aggregate syncing
- Offline queuing
- Metrics tracking
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import json

from ag3ntwerk.learning.nexus_sync import (
    NexusSyncBridge,
    SyncConfig,
    OutcomeSummary,
    PatternSyncRecord,
    create_nexus_sync_bridge,
)
from ag3ntwerk.learning.models import (
    TaskOutcomeRecord,
    LearnedPattern,
    PatternType,
    ScopeLevel,
    ErrorCategory,
)


def _utcnow():
    return datetime.now(timezone.utc)


class TestOutcomeSummary:
    """Test OutcomeSummary dataclass."""

    def test_create_summary(self):
        """Should create a summary with defaults."""
        summary = OutcomeSummary(
            agent_code="Forge",
            task_type="code_review",
        )

        assert summary.agent_code == "Forge"
        assert summary.task_type == "code_review"
        assert summary.total_tasks == 0
        assert summary.success_rate == 0.0

    def test_success_rate_calculation(self):
        """Should calculate success rate correctly."""
        summary = OutcomeSummary(
            agent_code="Forge",
            task_type="code_review",
            total_tasks=10,
            successful_tasks=8,
        )

        assert summary.success_rate == 0.8

    def test_to_dict(self):
        """Should serialize to dict."""
        summary = OutcomeSummary(
            agent_code="Forge",
            task_type="code_review",
            total_tasks=5,
            successful_tasks=4,
            avg_duration_ms=1500.0,
        )

        d = summary.to_dict()

        assert d["agent_code"] == "Forge"
        assert d["task_type"] == "code_review"
        assert d["success_rate"] == 0.8
        assert d["avg_duration_ms"] == 1500.0


class TestNexusSyncBridgeInit:
    """Test NexusSyncBridge initialization."""

    def test_init_with_defaults(self):
        """Should initialize with default config."""
        mock_bridge = MagicMock()
        sync = NexusSyncBridge(mock_bridge)

        assert sync._bridge == mock_bridge
        assert sync._config is not None
        assert sync._running is False
        assert len(sync._pending_outcomes) == 0

    def test_init_with_custom_config(self):
        """Should accept custom config."""
        mock_bridge = MagicMock()
        config = SyncConfig(
            aggregate_sync_interval_seconds=7200,
            min_pattern_confidence=0.8,
        )

        sync = NexusSyncBridge(mock_bridge, config)

        assert sync._config.aggregate_sync_interval_seconds == 7200
        assert sync._config.min_pattern_confidence == 0.8


class TestIsConnected:
    """Test is_connected property."""

    def test_connected_when_bridge_connected(self):
        """Should return True when bridge is connected."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True

        sync = NexusSyncBridge(mock_bridge)

        assert sync.is_connected is True

    def test_not_connected_when_bridge_disconnected(self):
        """Should return False when bridge is disconnected."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = False

        sync = NexusSyncBridge(mock_bridge)

        assert sync.is_connected is False


class TestForwardOutcome:
    """Test forward_outcome method."""

    @pytest.mark.asyncio
    async def test_forward_when_connected(self):
        """Should send outcome when connected."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.config = MagicMock()
        mock_bridge.config.channel_prefix = "ag3ntwerk:nexus"
        mock_bridge._redis = AsyncMock()
        mock_bridge._redis.publish = AsyncMock(return_value=1)

        sync = NexusSyncBridge(mock_bridge)

        record = TaskOutcomeRecord(
            task_id="test-123",
            task_type="code_review",
            agent_code="Forge",
            success=True,
            duration_ms=1500.0,
            effectiveness=0.9,
        )

        result = await sync.forward_outcome(record)

        assert result is True
        assert sync._metrics["outcomes_synced"] == 1
        mock_bridge._redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_queue_when_disconnected(self):
        """Should queue outcome when disconnected."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = False

        sync = NexusSyncBridge(mock_bridge)

        record = TaskOutcomeRecord(
            task_id="test-456",
            task_type="code_review",
            agent_code="Forge",
            success=True,
        )

        result = await sync.forward_outcome(record)

        assert result is True
        assert sync._metrics["outcomes_queued"] == 1
        assert len(sync._pending_outcomes) == 1

    @pytest.mark.asyncio
    async def test_updates_aggregates(self):
        """Should update aggregation buffer."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = False

        sync = NexusSyncBridge(mock_bridge)

        # Send multiple outcomes for same agent/task type
        for i in range(3):
            record = TaskOutcomeRecord(
                task_id=f"test-{i}",
                task_type="code_review",
                agent_code="Forge",
                success=(i % 2 == 0),
                duration_ms=1000.0 + i * 100,
            )
            await sync.forward_outcome(record)

        # Check aggregates
        key = "Forge:code_review"
        assert key in sync._outcome_buffer
        assert sync._outcome_buffer[key].total_tasks == 3
        assert sync._outcome_buffer[key].successful_tasks == 2  # 0 and 2 are even


class TestForwardPattern:
    """Test forward_pattern method."""

    @pytest.mark.asyncio
    async def test_forward_high_confidence_pattern(self):
        """Should forward patterns above confidence threshold."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.config = MagicMock()
        mock_bridge.config.channel_prefix = "ag3ntwerk:nexus"
        mock_bridge._redis = AsyncMock()
        mock_bridge._redis.publish = AsyncMock(return_value=1)

        sync = NexusSyncBridge(mock_bridge)

        pattern = LearnedPattern(
            pattern_type=PatternType.ROUTING,
            scope_level=ScopeLevel.AGENT,
            scope_code="Forge",
            condition_json="{}",
            recommendation="Route code reviews to Forge",
            confidence=0.85,
            sample_size=50,
        )

        result = await sync.forward_pattern(pattern)

        assert result is True
        assert sync._metrics["patterns_synced"] == 1
        assert pattern.id in sync._synced_patterns

    @pytest.mark.asyncio
    async def test_skip_low_confidence_pattern(self):
        """Should skip patterns below confidence threshold."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True

        sync = NexusSyncBridge(mock_bridge)

        pattern = LearnedPattern(
            pattern_type=PatternType.ROUTING,
            scope_level=ScopeLevel.AGENT,
            scope_code="Forge",
            condition_json="{}",
            recommendation="Uncertain recommendation",
            confidence=0.5,  # Below default 0.7 threshold
            sample_size=50,
        )

        result = await sync.forward_pattern(pattern)

        assert result is False
        assert sync._metrics["patterns_synced"] == 0

    @pytest.mark.asyncio
    async def test_skip_small_sample_pattern(self):
        """Should skip patterns with insufficient sample size."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True

        sync = NexusSyncBridge(mock_bridge)

        pattern = LearnedPattern(
            pattern_type=PatternType.ROUTING,
            scope_level=ScopeLevel.AGENT,
            scope_code="Forge",
            condition_json="{}",
            recommendation="Small sample recommendation",
            confidence=0.9,
            sample_size=5,  # Below default 10 threshold
        )

        result = await sync.forward_pattern(pattern)

        assert result is False

    @pytest.mark.asyncio
    async def test_skip_already_synced_pattern(self):
        """Should skip patterns already synced."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.config = MagicMock()
        mock_bridge.config.channel_prefix = "ag3ntwerk:nexus"
        mock_bridge._redis = AsyncMock()
        mock_bridge._redis.publish = AsyncMock(return_value=1)

        sync = NexusSyncBridge(mock_bridge)

        pattern = LearnedPattern(
            pattern_type=PatternType.ROUTING,
            scope_level=ScopeLevel.AGENT,
            scope_code="Forge",
            condition_json="{}",
            recommendation="Route code reviews to Forge",
            confidence=0.85,
            sample_size=50,
        )

        # First sync
        await sync.forward_pattern(pattern)

        # Second sync should be skipped
        result = await sync.forward_pattern(pattern)

        assert result is True  # Returns True because already synced
        assert sync._metrics["patterns_synced"] == 1  # Still 1


class TestSyncAggregates:
    """Test sync_aggregates method."""

    @pytest.mark.asyncio
    async def test_sync_aggregates_sends_data(self):
        """Should sync aggregates to Nexus."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.config = MagicMock()
        mock_bridge.config.channel_prefix = "ag3ntwerk:nexus"
        mock_bridge._redis = AsyncMock()
        mock_bridge._redis.publish = AsyncMock(return_value=1)

        sync = NexusSyncBridge(mock_bridge)

        # Add some aggregates
        sync._outcome_buffer["Forge:code_review"] = OutcomeSummary(
            agent_code="Forge",
            task_type="code_review",
            total_tasks=10,
            successful_tasks=8,
        )

        count = await sync.sync_aggregates()

        assert count == 1
        assert sync._metrics["aggregate_syncs"] == 1
        assert len(sync._outcome_buffer) == 0  # Buffer cleared

    @pytest.mark.asyncio
    async def test_sync_aggregates_empty_buffer(self):
        """Should handle empty buffer gracefully."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True

        sync = NexusSyncBridge(mock_bridge)

        count = await sync.sync_aggregates()

        assert count == 0

    @pytest.mark.asyncio
    async def test_sync_aggregates_when_disconnected(self):
        """Should return 0 when disconnected."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = False

        sync = NexusSyncBridge(mock_bridge)
        sync._outcome_buffer["Forge:code_review"] = OutcomeSummary(
            agent_code="Forge",
            task_type="code_review",
        )

        count = await sync.sync_aggregates()

        assert count == 0


class TestPeriodicSync:
    """Test periodic sync lifecycle."""

    @pytest.mark.asyncio
    async def test_start_periodic_sync(self):
        """Should start background tasks."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True

        sync = NexusSyncBridge(mock_bridge)

        result = await sync.start_periodic_sync()

        assert result is True
        assert sync._running is True
        assert sync._aggregate_sync_task is not None
        assert sync._pattern_sync_task is not None

        # Clean up
        await sync.stop_periodic_sync()

    @pytest.mark.asyncio
    async def test_stop_periodic_sync(self):
        """Should stop background tasks."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.config = MagicMock()
        mock_bridge.config.channel_prefix = "ag3ntwerk:nexus"
        mock_bridge._redis = AsyncMock()
        mock_bridge._redis.publish = AsyncMock(return_value=1)

        sync = NexusSyncBridge(mock_bridge)

        await sync.start_periodic_sync()
        await sync.stop_periodic_sync()

        assert sync._running is False


class TestGetMetrics:
    """Test get_metrics method."""

    def test_get_metrics_returns_all_fields(self):
        """Should return all metric fields."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True

        sync = NexusSyncBridge(mock_bridge)

        metrics = sync.get_metrics()

        assert "outcomes_synced" in metrics
        assert "outcomes_queued" in metrics
        assert "patterns_synced" in metrics
        assert "aggregate_syncs" in metrics
        assert "sync_errors" in metrics
        assert "pending_outcomes" in metrics
        assert "is_connected" in metrics
        assert "is_running" in metrics


class TestCreateNexusSyncBridge:
    """Test factory function."""

    def test_create_with_defaults(self):
        """Should create bridge with defaults."""
        mock_bridge = MagicMock()

        sync = create_nexus_sync_bridge(mock_bridge)

        assert isinstance(sync, NexusSyncBridge)
        assert sync._bridge == mock_bridge

    def test_create_with_custom_config(self):
        """Should create bridge with custom config."""
        mock_bridge = MagicMock()
        config = SyncConfig(batch_size=100)

        sync = create_nexus_sync_bridge(mock_bridge, config)

        assert sync._config.batch_size == 100


class TestFlushPending:
    """Test _flush_pending method."""

    @pytest.mark.asyncio
    async def test_flush_pending_outcomes(self):
        """Should flush pending outcomes when connected."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.config = MagicMock()
        mock_bridge.config.channel_prefix = "ag3ntwerk:nexus"
        mock_bridge._redis = AsyncMock()
        mock_bridge._redis.publish = AsyncMock(return_value=1)

        sync = NexusSyncBridge(mock_bridge)

        # Queue some outcomes while "disconnected"
        sync._pending_outcomes.append({"task_id": "test-1"})
        sync._pending_outcomes.append({"task_id": "test-2"})
        sync._pending_outcomes.append({"task_id": "test-3"})

        count = await sync._flush_pending()

        assert count == 3
        assert len(sync._pending_outcomes) == 0

    @pytest.mark.asyncio
    async def test_flush_noop_when_disconnected(self):
        """Should do nothing when disconnected."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = False

        sync = NexusSyncBridge(mock_bridge)
        sync._pending_outcomes.append({"task_id": "test-1"})

        count = await sync._flush_pending()

        assert count == 0
        assert len(sync._pending_outcomes) == 1


class TestFullSync:
    """Test full_sync method."""

    @pytest.mark.asyncio
    async def test_full_sync_with_pattern_store(self):
        """Should sync patterns from pattern store."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.config = MagicMock()
        mock_bridge.config.channel_prefix = "ag3ntwerk:nexus"
        mock_bridge._redis = AsyncMock()
        mock_bridge._redis.publish = AsyncMock(return_value=1)

        sync = NexusSyncBridge(mock_bridge)

        # Mock pattern store
        mock_pattern_store = AsyncMock()
        mock_pattern_store.get_active_patterns = AsyncMock(
            return_value=[
                LearnedPattern(
                    pattern_type=PatternType.ROUTING,
                    scope_level=ScopeLevel.AGENT,
                    scope_code="Forge",
                    condition_json="{}",
                    recommendation="Test",
                    confidence=0.85,
                    sample_size=50,
                ),
            ]
        )

        results = await sync.full_sync(pattern_store=mock_pattern_store)

        assert results["patterns"] == 1

    @pytest.mark.asyncio
    async def test_full_sync_when_disconnected(self):
        """Should return zeros when disconnected."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = False

        sync = NexusSyncBridge(mock_bridge)

        results = await sync.full_sync()

        assert results["outcomes"] == 0
        assert results["patterns"] == 0
        assert results["aggregates"] == 0
