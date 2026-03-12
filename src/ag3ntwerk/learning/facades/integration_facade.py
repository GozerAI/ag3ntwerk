"""
Integration Facade - Workbench, plugin, and service integrations.

This facade manages external integration components:
- WorkbenchBridge: UI integration for learning dashboards
- PluginTelemetryAdapter: Plugin telemetry tracking
- ServiceAdapter: Service configuration adaptation
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ag3ntwerk.learning.outcome_tracker import OutcomeTracker
from ag3ntwerk.learning.pattern_store import PatternStore
from ag3ntwerk.learning.plugin_telemetry import PluginTelemetryAdapter, PluginStats
from ag3ntwerk.learning.service_adapter import ServiceAdapter, ConfigRecommendation
from ag3ntwerk.learning.workbench_bridge import WorkbenchBridge, LearningDashboard

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class IntegrationFacade:
    """
    Facade for external integration operations.

    Manages workbench UI integration, plugin telemetry,
    and service configuration adaptation.
    """

    def __init__(
        self,
        db: Any,
        outcome_tracker: OutcomeTracker,
        pattern_store: PatternStore,
    ):
        """
        Initialize the integration facade.

        Args:
            db: Database connection
            outcome_tracker: Shared outcome tracker instance
            pattern_store: Shared pattern store instance
        """
        self._db = db
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store

        # Plugin and service components
        self._plugin_telemetry = PluginTelemetryAdapter(outcome_tracker, pattern_store)
        self._service_adapter = ServiceAdapter(db, pattern_store, outcome_tracker)

        # Workbench bridge is lazy-initialized
        self._workbench_bridge: Optional[WorkbenchBridge] = None
        self._orchestrator = None  # Set via set_orchestrator()

    def set_orchestrator(self, orchestrator: Any) -> None:
        """
        Set the orchestrator reference for workbench bridge.

        Args:
            orchestrator: Parent orchestrator instance
        """
        self._orchestrator = orchestrator

    # --- Workbench Bridge ---

    def get_workbench_bridge(self) -> WorkbenchBridge:
        """
        Get the Workbench bridge for UI integration.

        Lazy-initializes if not already created.

        Returns:
            WorkbenchBridge instance
        """
        if self._workbench_bridge is None:
            if self._orchestrator is None:
                raise RuntimeError("Orchestrator not set. Call set_orchestrator() first.")
            self._workbench_bridge = WorkbenchBridge(self._orchestrator)
        return self._workbench_bridge

    async def get_learning_dashboard(
        self,
        refresh: bool = False,
    ) -> LearningDashboard:
        """
        Get the learning dashboard data.

        Args:
            refresh: Force refresh even if cache is valid

        Returns:
            LearningDashboard with aggregated data
        """
        bridge = self.get_workbench_bridge()
        return await bridge.get_learning_dashboard(refresh)

    async def get_workbench_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get pending approvals for Workbench display."""
        bridge = self.get_workbench_bridge()
        return await bridge.get_pending_approvals()

    async def workbench_approve_action(
        self,
        approval_id: str,
        approved_by: str = "workbench_user",
        notes: Optional[str] = None,
    ) -> Any:
        """Approve an action from Workbench."""
        bridge = self.get_workbench_bridge()
        return await bridge.approve_action(approval_id, approved_by, notes)

    async def workbench_reject_action(
        self,
        approval_id: str,
        rejected_by: str = "workbench_user",
        notes: Optional[str] = None,
    ) -> Any:
        """Reject an action from Workbench."""
        bridge = self.get_workbench_bridge()
        return await bridge.reject_action(approval_id, rejected_by, notes)

    async def get_agent_insight(self, agent_code: str) -> Any:
        """Get learning insight for an agent."""
        bridge = self.get_workbench_bridge()
        return await bridge.get_agent_insight(agent_code)

    async def get_all_agent_insights(self) -> List[Any]:
        """Get learning insights for all agents."""
        bridge = self.get_workbench_bridge()
        return await bridge.get_all_agent_insights()

    # --- Plugin Telemetry ---

    def get_plugin_telemetry(self) -> PluginTelemetryAdapter:
        """Get the plugin telemetry adapter."""
        return self._plugin_telemetry

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
            name: Human-readable name
            version: Plugin version
            operations: Supported operations
            metadata: Optional metadata
        """
        self._plugin_telemetry.register_plugin(
            plugin_id=plugin_id,
            name=name,
            version=version,
            operations=operations,
            metadata=metadata,
        )

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
        Record a plugin operation outcome.

        Args:
            plugin_id: Plugin that performed the operation
            operation: Operation name
            success: Whether it succeeded
            duration_ms: Duration in milliseconds
            error: Error message if failed
            input_summary: Input summary
            output_summary: Output summary
            context: Additional context

        Returns:
            Outcome record ID
        """
        return await self._plugin_telemetry.record_plugin_outcome(
            plugin_id=plugin_id,
            operation=operation,
            success=success,
            duration_ms=duration_ms,
            error=error,
            input_summary=input_summary,
            output_summary=output_summary,
            context=context,
        )

    async def start_plugin_operation(
        self,
        plugin_id: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Start tracking a plugin operation.

        Returns a context manager for automatic outcome recording.

        Args:
            plugin_id: Plugin ID
            operation: Operation name
            context: Additional context

        Returns:
            OperationContext for use with 'async with'
        """
        return await self._plugin_telemetry.start_operation(
            plugin_id=plugin_id,
            operation=operation,
            context=context,
        )

    async def get_plugin_stats(
        self,
        plugin_id: str,
        window_hours: int = 24,
    ) -> PluginStats:
        """
        Get statistics for a plugin.

        Args:
            plugin_id: Plugin to get stats for
            window_hours: Time window in hours

        Returns:
            PluginStats with aggregated metrics
        """
        return await self._plugin_telemetry.get_plugin_stats(
            plugin_id=plugin_id,
            window_hours=window_hours,
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
            List of PluginStats
        """
        return await self._plugin_telemetry.get_all_plugin_stats(window_hours)

    # --- Service Adapter ---

    def get_service_adapter(self) -> ServiceAdapter:
        """Get the service adapter."""
        return self._service_adapter

    async def register_service(
        self,
        service_id: str,
        initial_config: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Register a service for adaptation tracking.

        Args:
            service_id: Unique service identifier
            initial_config: Current service configuration
            metadata: Optional metadata

        Returns:
            ServiceConfig for the service
        """
        return await self._service_adapter.register_service(
            service_id=service_id,
            initial_config=initial_config,
            metadata=metadata,
        )

    async def get_service_config(self, service_id: str) -> Optional[Any]:
        """Get current configuration for a service."""
        return await self._service_adapter.get_service_config(service_id)

    async def get_config_recommendations(
        self,
        service_id: str,
        min_confidence: float = 0.6,
    ) -> List[ConfigRecommendation]:
        """
        Get configuration recommendations for a service.

        Args:
            service_id: Service to get recommendations for
            min_confidence: Minimum confidence threshold

        Returns:
            List of ConfigRecommendation
        """
        return await self._service_adapter.get_config_recommendations(
            service_id=service_id,
            min_confidence=min_confidence,
        )

    async def apply_config_recommendation(
        self,
        service_id: str,
        recommendation: ConfigRecommendation,
    ) -> Any:
        """
        Apply a configuration recommendation.

        Args:
            service_id: Service to update
            recommendation: Recommendation to apply

        Returns:
            ConfigChange record
        """
        return await self._service_adapter.apply_recommendation(
            service_id=service_id,
            recommendation=recommendation,
        )

    async def get_service_adaptation_stats(
        self,
        service_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get adaptation statistics.

        Args:
            service_id: Optional filter by service

        Returns:
            Statistics dictionary
        """
        return await self._service_adapter.get_adaptation_stats(service_id)

    # --- Stats ---

    async def get_stats(self) -> Dict[str, Any]:
        """Get integration facade statistics."""
        return {
            "plugin_telemetry": (
                await self._plugin_telemetry.get_stats()
                if hasattr(self._plugin_telemetry, "get_stats")
                else {}
            ),
            "service_adapter": await self._service_adapter.get_adaptation_stats(),
        }

    # --- Accessors for components (used by orchestrator) ---

    @property
    def workbench_bridge(self) -> Optional[WorkbenchBridge]:
        """Get workbench bridge (may be None if not initialized)."""
        return self._workbench_bridge

    @property
    def plugin_telemetry(self) -> PluginTelemetryAdapter:
        """Get plugin telemetry adapter."""
        return self._plugin_telemetry

    @property
    def service_adapter(self) -> ServiceAdapter:
        """Get service adapter."""
        return self._service_adapter
