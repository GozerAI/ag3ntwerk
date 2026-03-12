"""
Unit tests for Phase 7 Learning System components.

Tests:
- WorkbenchBridge: Learning dashboard integration
- PluginTelemetryAdapter: Plugin outcome tracking
- ServiceAdapter: Service configuration adaptation
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.learning.workbench_bridge import (
    WorkbenchBridge,
    LearningDashboard,
    AgentInsight,
    ApprovalAction,
)
from ag3ntwerk.learning.plugin_telemetry import (
    PluginTelemetryAdapter,
    PluginOperation,
    PluginStats,
    OperationContext,
)
from ag3ntwerk.learning.service_adapter import (
    ServiceAdapter,
    ConfigChangeType,
    AdaptationStrategy,
    ConfigRecommendation,
    ServiceConfig,
    ConfigChange,
)
from ag3ntwerk.learning.models import (
    HierarchyPath,
    LearnedPattern,
    PatternType,
    ScopeLevel,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    db.fetch_one = AsyncMock(return_value=None)
    db.fetch_all = AsyncMock(return_value=[])
    return db


@pytest.fixture
def mock_outcome_tracker():
    """Create a mock outcome tracker."""
    tracker = AsyncMock()
    tracker.record_outcome = AsyncMock(return_value="outcome-123")
    tracker.get_outcomes = AsyncMock(return_value=[])
    tracker.get_outcome_stats = AsyncMock(
        return_value={
            "total": 100,
            "success_rate": 0.85,
            "avg_duration_ms": 150.0,
        }
    )
    return tracker


@pytest.fixture
def mock_pattern_store():
    """Create a mock pattern store."""
    store = AsyncMock()
    store.get_patterns = AsyncMock(return_value=[])
    store.get_pattern = AsyncMock(return_value=None)
    store.store_pattern = AsyncMock()
    store.count_active = AsyncMock(return_value=5)
    return store


@pytest.fixture
def mock_orchestrator(mock_outcome_tracker, mock_pattern_store):
    """Create a mock learning orchestrator."""
    orchestrator = MagicMock()
    orchestrator._outcome_tracker = mock_outcome_tracker
    orchestrator._pattern_store = mock_pattern_store
    orchestrator._pattern_experimenter = AsyncMock()
    orchestrator._pattern_experimenter.get_active_experiments = AsyncMock(return_value=[])
    orchestrator._pattern_experimenter.get_recent_results = AsyncMock(return_value=[])
    orchestrator._opportunity_detector = AsyncMock()
    orchestrator._opportunity_detector.get_open_opportunities = AsyncMock(return_value=[])
    orchestrator._autonomy_controller = AsyncMock()
    orchestrator._autonomy_controller.get_stats = AsyncMock(return_value={})
    orchestrator._autonomy_controller.get_pending_approvals = AsyncMock(return_value=[])
    orchestrator._autonomy_controller.process_approval = AsyncMock()
    orchestrator._continuous_pipeline = None
    orchestrator._agent_loops = {}
    orchestrator._manager_loops = {}
    orchestrator._specialist_loops = {}
    orchestrator._confidence_calibrator = MagicMock()
    orchestrator._confidence_calibrator._curves = {}
    orchestrator._confidence_calibrator.get_agent_calibration_summary = AsyncMock(
        return_value={"calibration_score": 0.8, "tendency": "balanced"}
    )
    orchestrator.get_stats = AsyncMock(return_value={})
    return orchestrator


# =============================================================================
# WorkbenchBridge Tests
# =============================================================================


class TestWorkbenchBridge:
    """Tests for WorkbenchBridge."""

    @pytest.fixture
    def bridge(self, mock_orchestrator):
        """Create a WorkbenchBridge instance."""
        return WorkbenchBridge(mock_orchestrator)

    @pytest.mark.asyncio
    async def test_get_learning_dashboard(self, bridge):
        """Test getting the learning dashboard."""
        dashboard = await bridge.get_learning_dashboard()

        assert isinstance(dashboard, LearningDashboard)
        assert dashboard.generated_at is not None

    @pytest.mark.asyncio
    async def test_dashboard_caching(self, bridge):
        """Test dashboard caching behavior."""
        # First call builds dashboard
        dashboard1 = await bridge.get_learning_dashboard()
        generated_at_1 = dashboard1.generated_at

        # Second call should return cached
        dashboard2 = await bridge.get_learning_dashboard(refresh=False)
        assert dashboard2.generated_at == generated_at_1

        # Force refresh should rebuild
        dashboard3 = await bridge.get_learning_dashboard(refresh=True)
        # May or may not be different depending on timing

    @pytest.mark.asyncio
    async def test_dashboard_to_dict(self, bridge):
        """Test dashboard serialization."""
        dashboard = await bridge.get_learning_dashboard()
        data = dashboard.to_dict()

        assert "patterns" in data
        assert "experiments" in data
        assert "opportunities" in data
        assert "autonomy" in data
        assert "pipeline" in data
        assert "performance" in data
        assert "metadata" in data

    @pytest.mark.asyncio
    async def test_get_pending_approvals(self, bridge, mock_orchestrator):
        """Test getting pending approvals."""
        approvals = await bridge.get_pending_approvals()
        assert isinstance(approvals, list)

    @pytest.mark.asyncio
    async def test_approve_action(self, bridge, mock_orchestrator):
        """Test approving an action."""
        result = await bridge.approve_action(
            approval_id="approval-123",
            approved_by="test_user",
            notes="Test approval",
        )

        assert isinstance(result, ApprovalAction)
        assert result.approval_id == "approval-123"
        assert result.action == "approved"
        assert result.processed_by == "test_user"
        mock_orchestrator._autonomy_controller.process_approval.assert_called()

    @pytest.mark.asyncio
    async def test_reject_action(self, bridge, mock_orchestrator):
        """Test rejecting an action."""
        result = await bridge.reject_action(
            approval_id="approval-456",
            rejected_by="test_user",
            notes="Test rejection",
        )

        assert isinstance(result, ApprovalAction)
        assert result.approval_id == "approval-456"
        assert result.action == "rejected"
        mock_orchestrator._autonomy_controller.process_approval.assert_called()

    @pytest.mark.asyncio
    async def test_get_agent_insight(self, bridge, mock_orchestrator):
        """Test getting agent insight."""
        # Register an agent loop for testing
        mock_orchestrator._agent_loops = {"Forge": MagicMock()}

        insight = await bridge.get_agent_insight("Forge")

        assert isinstance(insight, AgentInsight)
        assert insight.agent_code == "Forge"
        assert insight.agent_level == "agent"

    @pytest.mark.asyncio
    async def test_agent_insight_to_dict(self, bridge, mock_orchestrator):
        """Test agent insight serialization."""
        mock_orchestrator._agent_loops = {"Forge": MagicMock()}

        insight = await bridge.get_agent_insight("Forge")
        data = insight.to_dict()

        assert data["agent_code"] == "Forge"
        assert "success_rate" in data
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_start_pipeline(self, bridge, mock_orchestrator):
        """Test starting the pipeline."""
        # Without pipeline
        result = await bridge.start_pipeline()
        assert result is False

        # With pipeline
        mock_orchestrator._continuous_pipeline = AsyncMock()
        mock_orchestrator._continuous_pipeline.start = AsyncMock()
        result = await bridge.start_pipeline()
        assert result is True

    @pytest.mark.asyncio
    async def test_stop_pipeline(self, bridge, mock_orchestrator):
        """Test stopping the pipeline."""
        # Without pipeline
        result = await bridge.stop_pipeline()
        assert result is False

        # With pipeline
        mock_orchestrator._continuous_pipeline = AsyncMock()
        mock_orchestrator._continuous_pipeline.stop = AsyncMock()
        result = await bridge.stop_pipeline()
        assert result is True


# =============================================================================
# PluginTelemetryAdapter Tests
# =============================================================================


class TestPluginTelemetryAdapter:
    """Tests for PluginTelemetryAdapter."""

    @pytest.fixture
    def adapter(self, mock_outcome_tracker, mock_pattern_store):
        """Create a PluginTelemetryAdapter instance."""
        return PluginTelemetryAdapter(mock_outcome_tracker, mock_pattern_store)

    def test_register_plugin(self, adapter):
        """Test registering a plugin."""
        adapter.register_plugin(
            plugin_id="test-plugin",
            name="Test Plugin",
            version="1.0.0",
            operations=["analyze", "transform"],
            metadata={"author": "test"},
        )

        plugins = adapter.get_registered_plugins()
        assert len(plugins) == 1
        assert plugins[0]["plugin_id"] == "test-plugin"
        assert plugins[0]["name"] == "Test Plugin"
        assert plugins[0]["version"] == "1.0.0"
        assert "analyze" in plugins[0]["operations"]

    def test_unregister_plugin(self, adapter):
        """Test unregistering a plugin."""
        adapter.register_plugin(
            plugin_id="test-plugin",
            name="Test Plugin",
            version="1.0.0",
            operations=["analyze"],
        )

        assert adapter.unregister_plugin("test-plugin") is True
        assert adapter.unregister_plugin("nonexistent") is False
        assert len(adapter.get_registered_plugins()) == 0

    @pytest.mark.asyncio
    async def test_record_plugin_outcome(self, adapter, mock_outcome_tracker):
        """Test recording a plugin outcome."""
        outcome_id = await adapter.record_plugin_outcome(
            plugin_id="test-plugin",
            operation="analyze",
            success=True,
            duration_ms=100.0,
            output_summary="Analysis complete",
        )

        assert outcome_id == "outcome-123"
        mock_outcome_tracker.record_outcome.assert_called()

    @pytest.mark.asyncio
    async def test_record_plugin_outcome_with_error(self, adapter, mock_outcome_tracker):
        """Test recording a failed plugin outcome."""
        outcome_id = await adapter.record_plugin_outcome(
            plugin_id="test-plugin",
            operation="transform",
            success=False,
            duration_ms=50.0,
            error="Transform failed: invalid input",
        )

        assert outcome_id == "outcome-123"
        call_args = mock_outcome_tracker.record_outcome.call_args
        assert call_args.kwargs.get("success") is False

    @pytest.mark.asyncio
    async def test_start_operation_context(self, adapter):
        """Test operation context manager."""
        context = await adapter.start_operation(
            plugin_id="test-plugin",
            operation="analyze",
            context={"file": "test.txt"},
        )

        assert isinstance(context, OperationContext)

    @pytest.mark.asyncio
    async def test_operation_context_success(self, adapter, mock_outcome_tracker):
        """Test successful operation with context manager."""
        async with await adapter.start_operation(
            plugin_id="test-plugin",
            operation="analyze",
        ) as ctx:
            ctx.set_input("test input")
            ctx.set_output("test output")

        # Should record successful outcome
        mock_outcome_tracker.record_outcome.assert_called()
        call_args = mock_outcome_tracker.record_outcome.call_args
        assert call_args.kwargs.get("success") is True

    @pytest.mark.asyncio
    async def test_operation_context_failure(self, adapter, mock_outcome_tracker):
        """Test failed operation with context manager."""
        try:
            async with await adapter.start_operation(
                plugin_id="test-plugin",
                operation="analyze",
            ):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should record failed outcome
        mock_outcome_tracker.record_outcome.assert_called()
        call_args = mock_outcome_tracker.record_outcome.call_args
        assert call_args.kwargs.get("success") is False

    @pytest.mark.asyncio
    async def test_get_plugin_stats_empty(self, adapter):
        """Test getting stats with no operations."""
        stats = await adapter.get_plugin_stats("nonexistent")

        assert isinstance(stats, PluginStats)
        assert stats.total_operations == 0
        assert stats.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_get_plugin_stats(self, adapter, mock_outcome_tracker):
        """Test getting plugin stats with operations."""
        # Record some operations
        for i in range(5):
            await adapter.record_plugin_outcome(
                plugin_id="test-plugin",
                operation="analyze" if i % 2 == 0 else "transform",
                success=i < 4,  # 4 successful, 1 failed
                duration_ms=100.0 + i * 10,
            )

        stats = await adapter.get_plugin_stats("test-plugin", window_hours=24)

        assert stats.total_operations == 5
        assert stats.successful_operations == 4
        assert stats.failed_operations == 1
        assert stats.success_rate == 0.8

    @pytest.mark.asyncio
    async def test_get_all_plugin_stats(self, adapter, mock_outcome_tracker):
        """Test getting all plugin stats."""
        adapter.register_plugin(
            plugin_id="plugin-1",
            name="Plugin 1",
            version="1.0",
            operations=["op1"],
        )
        adapter.register_plugin(
            plugin_id="plugin-2",
            name="Plugin 2",
            version="1.0",
            operations=["op2"],
        )

        stats_list = await adapter.get_all_plugin_stats()

        assert len(stats_list) >= 2

    @pytest.mark.asyncio
    async def test_get_recent_operations(self, adapter, mock_outcome_tracker):
        """Test getting recent operations."""
        await adapter.record_plugin_outcome(
            plugin_id="test-plugin",
            operation="analyze",
            success=True,
            duration_ms=100.0,
        )

        operations = await adapter.get_recent_operations()
        assert len(operations) == 1
        assert operations[0]["plugin_id"] == "test-plugin"

    def test_error_categorization(self, adapter):
        """Test error message categorization."""
        assert adapter._categorize_error("Connection timeout") == "timeout"
        assert adapter._categorize_error("Network unreachable") == "network"
        assert adapter._categorize_error("Permission denied") == "permission"
        assert adapter._categorize_error("File not found") == "not_found"
        assert adapter._categorize_error("Invalid JSON format") == "validation"
        assert adapter._categorize_error("Unknown error") == "other"


# =============================================================================
# ServiceAdapter Tests
# =============================================================================


class TestServiceAdapter:
    """Tests for ServiceAdapter."""

    @pytest.fixture
    def adapter(self, mock_db, mock_pattern_store, mock_outcome_tracker):
        """Create a ServiceAdapter instance."""
        return ServiceAdapter(mock_db, mock_pattern_store, mock_outcome_tracker)

    @pytest.mark.asyncio
    async def test_register_service(self, adapter):
        """Test registering a service."""
        config = await adapter.register_service(
            service_id="test-service",
            initial_config={"timeout": 30, "retries": 3},
            metadata={"version": "1.0"},
        )

        assert isinstance(config, ServiceConfig)
        assert config.service_id == "test-service"
        assert config.parameters["timeout"] == 30
        assert config.parameters["retries"] == 3
        assert config.version == 1

    @pytest.mark.asyncio
    async def test_get_service_config(self, adapter):
        """Test getting service configuration."""
        await adapter.register_service(
            service_id="test-service",
            initial_config={"timeout": 30},
        )

        config = await adapter.get_service_config("test-service")
        assert config is not None
        assert config.service_id == "test-service"

        # Nonexistent service
        config = await adapter.get_service_config("nonexistent")
        assert config is None

    @pytest.mark.asyncio
    async def test_update_service_config(self, adapter):
        """Test updating service configuration."""
        await adapter.register_service(
            service_id="test-service",
            initial_config={"timeout": 30},
        )

        config = await adapter.update_service_config(
            service_id="test-service",
            updates={"timeout": 60, "new_param": "value"},
        )

        assert config.parameters["timeout"] == 60
        assert config.parameters["new_param"] == "value"
        assert config.version == 2

    @pytest.mark.asyncio
    async def test_get_config_recommendations_empty(self, adapter, mock_pattern_store):
        """Test getting recommendations when none available."""
        await adapter.register_service(
            service_id="test-service",
            initial_config={"timeout": 30},
        )

        recommendations = await adapter.get_config_recommendations("test-service")
        assert recommendations == []

    @pytest.mark.asyncio
    async def test_apply_recommendation(self, adapter, mock_db):
        """Test applying a configuration recommendation."""
        await adapter.register_service(
            service_id="test-service",
            initial_config={"timeout": 30},
        )

        recommendation = ConfigRecommendation(
            service_id="test-service",
            parameter="timeout",
            current_value=30,
            recommended_value=60,
            change_type=ConfigChangeType.THRESHOLD_ADJUSTMENT,
            confidence=0.85,
            reasoning="Historical data shows better performance with higher timeout",
            expected_improvement=0.15,
        )

        change = await adapter.apply_recommendation(
            service_id="test-service",
            recommendation=recommendation,
        )

        assert isinstance(change, ConfigChange)
        assert change.parameter == "timeout"
        assert change.old_value == 30
        assert change.new_value == 60
        mock_db.execute.assert_called()

        # Verify config was updated
        config = await adapter.get_service_config("test-service")
        assert config.parameters["timeout"] == 60

    @pytest.mark.asyncio
    async def test_apply_recommendation_gradual(self, adapter, mock_db):
        """Test applying a recommendation with gradual strategy."""
        await adapter.register_service(
            service_id="test-service",
            initial_config={"timeout": 30},
        )

        recommendation = ConfigRecommendation(
            service_id="test-service",
            parameter="timeout",
            current_value=30,
            recommended_value=60,
            change_type=ConfigChangeType.THRESHOLD_ADJUSTMENT,
            confidence=0.7,
            reasoning="Test",
            expected_improvement=0.1,
        )

        change = await adapter.apply_recommendation(
            service_id="test-service",
            recommendation=recommendation,
            strategy=AdaptationStrategy.GRADUAL,
        )

        assert change is not None
        # Config should NOT be immediately updated with gradual strategy
        config = await adapter.get_service_config("test-service")
        assert config.parameters["timeout"] == 30

    @pytest.mark.asyncio
    async def test_record_change_outcome(self, adapter, mock_db):
        """Test recording the outcome of a configuration change."""
        await adapter.register_service(
            service_id="test-service",
            initial_config={"timeout": 30},
        )

        recommendation = ConfigRecommendation(
            service_id="test-service",
            parameter="timeout",
            current_value=30,
            recommended_value=60,
            change_type=ConfigChangeType.THRESHOLD_ADJUSTMENT,
            confidence=0.85,
            reasoning="Test",
            expected_improvement=0.15,
        )

        change = await adapter.apply_recommendation(
            service_id="test-service",
            recommendation=recommendation,
        )

        await adapter.record_change_outcome(
            change_id=change.id,
            success=True,
            metrics={"latency_reduction": 0.12},
        )

        # Find the change in history
        history = await adapter.get_change_history("test-service")
        assert len(history) == 1
        assert history[0].success is True
        assert history[0].outcome_metrics["latency_reduction"] == 0.12

    @pytest.mark.asyncio
    async def test_get_change_history(self, adapter, mock_db):
        """Test getting change history."""
        await adapter.register_service(
            service_id="test-service",
            initial_config={"param1": 1, "param2": 2},
        )

        # Apply multiple changes
        for i, param in enumerate(["param1", "param2"]):
            recommendation = ConfigRecommendation(
                service_id="test-service",
                parameter=param,
                current_value=i + 1,
                recommended_value=(i + 1) * 10,
                change_type=ConfigChangeType.PARAMETER_UPDATE,
                confidence=0.8,
                reasoning="Test",
                expected_improvement=0.1,
            )
            await adapter.apply_recommendation("test-service", recommendation)

        history = await adapter.get_change_history("test-service")
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_adaptation_stats(self, adapter, mock_db):
        """Test getting adaptation statistics."""
        await adapter.register_service(
            service_id="test-service",
            initial_config={"timeout": 30},
        )

        recommendation = ConfigRecommendation(
            service_id="test-service",
            parameter="timeout",
            current_value=30,
            recommended_value=60,
            change_type=ConfigChangeType.THRESHOLD_ADJUSTMENT,
            confidence=0.85,
            reasoning="Test",
            expected_improvement=0.15,
        )

        change = await adapter.apply_recommendation("test-service", recommendation)
        await adapter.record_change_outcome(change.id, success=True)

        stats = await adapter.get_adaptation_stats("test-service")

        assert stats["total_changes"] == 1
        assert stats["successful_changes"] == 1
        assert stats["failed_changes"] == 0

    @pytest.mark.asyncio
    async def test_rollback_change(self, adapter, mock_db):
        """Test rolling back a configuration change."""
        await adapter.register_service(
            service_id="test-service",
            initial_config={"timeout": 30},
        )

        recommendation = ConfigRecommendation(
            service_id="test-service",
            parameter="timeout",
            current_value=30,
            recommended_value=60,
            change_type=ConfigChangeType.THRESHOLD_ADJUSTMENT,
            confidence=0.85,
            reasoning="Test",
            expected_improvement=0.15,
        )

        change = await adapter.apply_recommendation("test-service", recommendation)

        # Verify change was applied
        config = await adapter.get_service_config("test-service")
        assert config.parameters["timeout"] == 60

        # Rollback
        rollback = await adapter.rollback_change(change.id, reason="Performance degradation")

        assert rollback is not None
        assert rollback.old_value == 60
        assert rollback.new_value == 30

        # Verify rollback was applied
        config = await adapter.get_service_config("test-service")
        assert config.parameters["timeout"] == 30

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_change(self, adapter):
        """Test rolling back a nonexistent change."""
        rollback = await adapter.rollback_change("nonexistent", reason="Test")
        assert rollback is None

    def test_config_change_types(self):
        """Test ConfigChangeType enum values."""
        assert ConfigChangeType.PARAMETER_UPDATE.value == "parameter_update"
        assert ConfigChangeType.FEATURE_TOGGLE.value == "feature_toggle"
        assert ConfigChangeType.THRESHOLD_ADJUSTMENT.value == "threshold_adjustment"
        assert ConfigChangeType.RESOURCE_SCALING.value == "resource_scaling"
        assert ConfigChangeType.BEHAVIOR_MODIFICATION.value == "behavior_modification"

    def test_adaptation_strategies(self):
        """Test AdaptationStrategy enum values."""
        assert AdaptationStrategy.IMMEDIATE.value == "immediate"
        assert AdaptationStrategy.GRADUAL.value == "gradual"
        assert AdaptationStrategy.EXPERIMENT.value == "experiment"
        assert AdaptationStrategy.MANUAL.value == "manual"

    def test_config_recommendation_to_dict(self):
        """Test ConfigRecommendation serialization."""
        rec = ConfigRecommendation(
            service_id="test",
            parameter="timeout",
            current_value=30,
            recommended_value=60,
            change_type=ConfigChangeType.THRESHOLD_ADJUSTMENT,
            confidence=0.85,
            reasoning="Test reasoning",
            expected_improvement=0.15,
            patterns_used=["pattern-1"],
        )

        data = rec.to_dict()
        assert data["service_id"] == "test"
        assert data["parameter"] == "timeout"
        assert data["change_type"] == "threshold_adjustment"
        assert data["patterns_used"] == ["pattern-1"]

    def test_service_config_to_dict(self):
        """Test ServiceConfig serialization."""
        config = ServiceConfig(
            service_id="test",
            parameters={"timeout": 30},
            version=2,
        )

        data = config.to_dict()
        assert data["service_id"] == "test"
        assert data["parameters"]["timeout"] == 30
        assert data["version"] == 2

    def test_config_change_to_dict(self):
        """Test ConfigChange serialization."""
        change = ConfigChange(
            id="change-123",
            service_id="test",
            parameter="timeout",
            old_value=30,
            new_value=60,
            change_type=ConfigChangeType.THRESHOLD_ADJUSTMENT,
            reason="Test",
            applied_at=datetime.now(timezone.utc),
        )

        data = change.to_dict()
        assert data["id"] == "change-123"
        assert data["parameter"] == "timeout"
        assert data["old_value"] == 30
        assert data["new_value"] == 60


# =============================================================================
# Integration Tests
# =============================================================================


class TestPhase7Integration:
    """Integration tests for Phase 7 components working together."""

    @pytest.mark.asyncio
    async def test_dashboard_includes_plugin_data(self, mock_orchestrator, mock_outcome_tracker):
        """Test that dashboard can include plugin telemetry data."""
        bridge = WorkbenchBridge(mock_orchestrator)

        # Dashboard should build without errors even with no data
        dashboard = await bridge.get_learning_dashboard()
        assert dashboard is not None

    @pytest.mark.asyncio
    async def test_plugin_telemetry_feeds_learning(self, mock_outcome_tracker, mock_pattern_store):
        """Test that plugin telemetry feeds into the learning system."""
        adapter = PluginTelemetryAdapter(mock_outcome_tracker, mock_pattern_store)

        # Register plugin
        adapter.register_plugin(
            plugin_id="analytics",
            name="Analytics Plugin",
            version="2.0.0",
            operations=["aggregate", "report"],
        )

        # Record operations
        await adapter.record_plugin_outcome(
            plugin_id="analytics",
            operation="aggregate",
            success=True,
            duration_ms=500.0,
        )

        # Should have recorded to outcome tracker
        mock_outcome_tracker.record_outcome.assert_called()

        # Task type should include plugin prefix
        call_args = mock_outcome_tracker.record_outcome.call_args
        assert "plugin:" in call_args.kwargs.get("task_type", "")

    @pytest.mark.asyncio
    async def test_service_adapter_uses_patterns(
        self, mock_db, mock_pattern_store, mock_outcome_tracker
    ):
        """Test that service adapter uses patterns for recommendations."""
        adapter = ServiceAdapter(mock_db, mock_pattern_store, mock_outcome_tracker)

        await adapter.register_service(
            service_id="api-gateway",
            initial_config={"timeout": 30, "max_connections": 100},
        )

        # Get recommendations (will be empty without matching patterns)
        recommendations = await adapter.get_config_recommendations("api-gateway")

        # Pattern store should have been queried
        mock_pattern_store.get_patterns.assert_called()

    @pytest.mark.asyncio
    async def test_full_adaptation_workflow(
        self, mock_db, mock_pattern_store, mock_outcome_tracker
    ):
        """Test complete service adaptation workflow."""
        adapter = ServiceAdapter(mock_db, mock_pattern_store, mock_outcome_tracker)

        # 1. Register service
        config = await adapter.register_service(
            service_id="worker",
            initial_config={"batch_size": 100},
        )
        assert config.version == 1

        # 2. Create and apply recommendation
        rec = ConfigRecommendation(
            service_id="worker",
            parameter="batch_size",
            current_value=100,
            recommended_value=200,
            change_type=ConfigChangeType.RESOURCE_SCALING,
            confidence=0.9,
            reasoning="Higher batch size improves throughput",
            expected_improvement=0.25,
        )
        change = await adapter.apply_recommendation("worker", rec)

        # 3. Record outcome
        await adapter.record_change_outcome(change.id, success=True)

        # 4. Check stats
        stats = await adapter.get_adaptation_stats("worker")
        assert stats["successful_changes"] == 1

    @pytest.mark.asyncio
    async def test_plugin_operation_context_integration(
        self, mock_outcome_tracker, mock_pattern_store
    ):
        """Test plugin operation context manager in integration scenario."""
        adapter = PluginTelemetryAdapter(mock_outcome_tracker, mock_pattern_store)

        adapter.register_plugin(
            plugin_id="processor",
            name="Data Processor",
            version="1.0.0",
            operations=["process", "validate"],
        )

        # Use context manager for operation
        async with await adapter.start_operation(
            plugin_id="processor",
            operation="process",
            context={"input_count": 100},
        ) as ctx:
            ctx.set_input("100 records")
            # Simulate processing
            ctx.set_output("100 records processed")

        # Get stats
        stats = await adapter.get_plugin_stats("processor")
        assert stats.total_operations == 1
        assert stats.successful_operations == 1
