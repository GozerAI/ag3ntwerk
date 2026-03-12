"""
Plugin Base Class - Abstract base class for plugins.

Contains the Plugin ABC and built-in plugin implementations.
"""

import logging
from abc import ABC
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.plugins.models import (
    EventFilter,
    HookRegistration,
    PluginContext,
    PluginHealth,
    PluginMetadata,
    PluginState,
    VersionRequirement,
)
from ag3ntwerk.core.plugins._utils import hook

logger = logging.getLogger(__name__)


class Plugin(ABC):
    """
    Base class for ag3ntwerk plugins.

    Subclass this to create custom plugins with lifecycle hooks
    and event handlers.
    """

    # Override these in subclasses
    name: str = "unnamed-plugin"
    version: str = "0.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = []
    version_requirements: List[VersionRequirement] = []

    def __init__(self):
        self._state = PluginState.REGISTERED
        self._config: Dict[str, Any] = {}
        self._context: Optional[PluginContext] = None
        self._started_at: Optional[datetime] = None
        self._error: Optional[str] = None

        # Health tracking
        self._error_count: int = 0
        self._last_error_time: Optional[datetime] = None
        self._hooks_executed: int = 0
        self._hooks_failed: int = 0
        self._total_hook_duration_ms: float = 0.0

        # Event filtering
        self._event_filter: Optional[EventFilter] = None

        # Disabled by sandbox
        self._disabled: bool = False
        self._disabled_reason: Optional[str] = None

    @property
    def state(self) -> PluginState:
        """Current plugin state."""
        return self._state

    @property
    def config(self) -> Dict[str, Any]:
        """Plugin configuration."""
        return self._config

    @property
    def context(self) -> Optional[PluginContext]:
        """Plugin context (available after startup)."""
        return self._context

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the plugin.

        Called before startup with plugin-specific configuration.

        Args:
            config: Configuration dictionary
        """
        self._config = config

    async def on_startup(self) -> None:
        """
        Called when the plugin starts up.

        Override to perform initialization.
        """
        pass

    async def on_shutdown(self) -> None:
        """
        Called when the plugin shuts down.

        Override to perform cleanup.
        """
        pass

    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            dependencies=self.dependencies,
        )

    def get_hooks(self) -> List[HookRegistration]:
        """
        Get all hook registrations for this plugin.

        Returns:
            List of HookRegistration
        """
        hooks = []

        for name in dir(self):
            if name.startswith("_"):
                continue

            method = getattr(self, name)
            if callable(method) and hasattr(method, "_hook_event"):
                hooks.append(
                    HookRegistration(
                        hook_name=method._hook_event,
                        handler=method,
                        plugin_name=self.name,
                        priority=getattr(method, "_hook_priority", 50),
                    )
                )

        return hooks

    def set_event_filter(self, event_filter: EventFilter) -> None:
        """Set event filter for this plugin."""
        self._event_filter = event_filter

    def accepts_event(self, hook_name: str) -> bool:
        """Check if plugin accepts this event."""
        if self._event_filter is None:
            return True
        return self._event_filter.matches(hook_name)

    def get_health(self) -> PluginHealth:
        """Get plugin health status."""
        uptime = 0.0
        if self._started_at:
            uptime = (datetime.now(timezone.utc) - self._started_at).total_seconds()

        avg_duration = 0.0
        if self._hooks_executed > 0:
            avg_duration = self._total_hook_duration_ms / self._hooks_executed

        return PluginHealth(
            plugin_name=self.name,
            state=self._state,
            healthy=not self._disabled and self._state == PluginState.ACTIVE,
            error_count=self._error_count,
            last_error=self._error,
            last_error_time=self._last_error_time,
            uptime_seconds=uptime,
            hooks_executed=self._hooks_executed,
            hooks_failed=self._hooks_failed,
            avg_hook_duration_ms=avg_duration,
        )

    def record_hook_execution(
        self, duration_ms: float, success: bool, error: Optional[str] = None
    ) -> None:
        """Record a hook execution for health tracking."""
        self._hooks_executed += 1
        self._total_hook_duration_ms += duration_ms

        if not success:
            self._hooks_failed += 1
            self._error_count += 1
            self._last_error_time = datetime.now(timezone.utc)
            self._error = error

    def reset_error_count(self) -> None:
        """Reset error count (called periodically by sandbox)."""
        self._error_count = 0

    def disable(self, reason: str) -> None:
        """Disable plugin (called by sandbox)."""
        self._disabled = True
        self._disabled_reason = reason
        logger.warning(f"Plugin {self.name} disabled: {reason}")

    def enable(self) -> None:
        """Re-enable plugin."""
        self._disabled = False
        self._disabled_reason = None
        self._error_count = 0
        logger.info(f"Plugin {self.name} re-enabled")

    @property
    def is_disabled(self) -> bool:
        """Check if plugin is disabled."""
        return self._disabled

    async def on_reload(self) -> None:
        """
        Called when the plugin is being hot reloaded.

        Override to handle reload (e.g., save state).
        """
        pass

    async def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate plugin configuration.

        Override to add custom validation.

        Args:
            config: Configuration to validate

        Returns:
            List of validation errors (empty if valid)
        """
        return []


# =============================================================================
# Built-in Plugins
# =============================================================================


class LoggingPlugin(Plugin):
    """Built-in plugin that logs all events."""

    name = "logging"
    version = "1.0.0"
    description = "Logs all events for debugging"

    @hook("*", priority=100)
    async def log_event(self, event: Dict[str, Any]) -> None:
        """Log all events."""
        logger.debug(f"Event: {event}")


class MetricsPlugin(Plugin):
    """Built-in plugin that tracks event metrics."""

    name = "metrics"
    version = "1.0.0"
    description = "Tracks event counts and timing"

    def __init__(self):
        super().__init__()
        self._event_counts: Dict[str, int] = {}

    @hook("*", priority=99)
    async def count_event(self, event: Dict[str, Any]) -> None:
        """Count events by type."""
        event_type = event.get("type", "unknown")
        self._event_counts[event_type] = self._event_counts.get(event_type, 0) + 1

    def get_counts(self) -> Dict[str, int]:
        """Get event counts."""
        return dict(self._event_counts)
