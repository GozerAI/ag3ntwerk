"""
Plugin Manager - Central coordinator for the Plugin system.

Delegates to domain-focused facades for actual implementation.
Maintains backward compatibility with existing PluginManager API.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, TYPE_CHECKING

from ag3ntwerk.core.plugins.models import (
    EventFilter,
    HookRegistration,
    PluginContext,
    PluginEvent,
    PluginHealth,
    PluginState,
    SandboxConfig,
)
from ag3ntwerk.core.plugins.facades import (
    RegistryFacade,
    DependencyFacade,
    LifecycleFacade,
    HookFacade,
    HealthFacade,
    EventFacade,
)

if TYPE_CHECKING:
    from ag3ntwerk.core.plugins.base import Plugin

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Central manager for plugins.

    Delegates to domain facades:
    - RegistryFacade: Plugin registration and lookup
    - DependencyFacade: Dependency checking and ordering
    - LifecycleFacade: Startup, shutdown, hot reload
    - HookFacade: Hook dispatch with sandboxing
    - HealthFacade: Health monitoring
    - EventFacade: Event history and listeners

    All existing methods are maintained for backward compatibility.
    """

    def __init__(
        self,
        sandbox_config: Optional[SandboxConfig] = None,
    ):
        """
        Initialize the plugin manager.

        Args:
            sandbox_config: Optional sandbox configuration
        """
        # Shared state
        self._plugins: Dict[str, "Plugin"] = {}
        self._hooks: Dict[str, List[HookRegistration]] = {}
        self._context = PluginContext()
        self._lock = asyncio.Lock()

        # Sandboxing
        self._sandbox = sandbox_config or SandboxConfig()

        # Initialize facades with shared state
        self._registry = RegistryFacade(
            self._plugins,
            self._hooks,
            self._lock,
            self._context,
        )
        self._dependency = DependencyFacade(self._plugins)
        self._lifecycle = LifecycleFacade(self._plugins, self._sandbox)
        self._hook = HookFacade(self._plugins, self._hooks, self._sandbox)
        self._health = HealthFacade(self._plugins)
        self._event = EventFacade()

        # Wire up cross-facade callbacks
        self._hook.set_event_callback(self._event.record_event)
        self._lifecycle.set_reregister_hooks_callback(self._registry.reregister_hooks)

    # ==========================================================================
    # Registration (delegates to RegistryFacade)
    # ==========================================================================

    async def register(
        self,
        plugin: "Plugin",
        config: Optional[Dict[str, Any]] = None,
        event_filter: Optional[EventFilter] = None,
    ) -> bool:
        """
        Register a plugin.

        Args:
            plugin: Plugin instance
            config: Optional configuration
            event_filter: Optional event filter

        Returns:
            True if registered successfully
        """
        return await self._registry.register(
            plugin=plugin,
            config=config,
            event_filter=event_filter,
            check_dependencies=True,
            dependency_checker=self._dependency,
        )

    async def unregister(self, plugin_name: str) -> bool:
        """Unregister a plugin."""
        return await self._registry.unregister(
            plugin_name,
            stop_callback=self._lifecycle.stop_plugin,
        )

    def get_plugin(self, name: str) -> Optional["Plugin"]:
        """Get a plugin by name."""
        return self._registry.get_plugin(name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins."""
        return self._registry.list_plugins()

    def list_hooks(self) -> Dict[str, List[str]]:
        """List all registered hooks."""
        return self._registry.list_hooks()

    # ==========================================================================
    # Lifecycle (delegates to LifecycleFacade)
    # ==========================================================================

    async def startup(self) -> Dict[str, bool]:
        """
        Start all registered plugins.

        Returns:
            Dict mapping plugin names to startup success
        """
        self._context.manager = self
        dependency_order = self._dependency.get_dependency_order()
        return await self._lifecycle.startup_all(dependency_order)

    async def shutdown(self) -> Dict[str, bool]:
        """
        Shutdown all plugins.

        Returns:
            Dict mapping plugin names to shutdown success
        """
        reverse_order = self._dependency.get_reverse_dependency_order()
        return await self._lifecycle.shutdown_all(reverse_order)

    async def reload_plugin(self, plugin_name: str) -> bool:
        """Hot reload a plugin."""
        return await self._lifecycle.reload_plugin(plugin_name, self._lock)

    async def reload_all_plugins(self) -> Dict[str, bool]:
        """Reload all plugins."""
        return await self._lifecycle.reload_all_plugins(self._lock)

    # ==========================================================================
    # Hook Dispatch (delegates to HookFacade)
    # ==========================================================================

    async def dispatch(
        self,
        hook_name: str,
        event: Dict[str, Any],
        stop_on_error: bool = False,
    ) -> List[Any]:
        """
        Dispatch an event to all registered hooks.

        Args:
            hook_name: Name of the hook
            event: Event data
            stop_on_error: Stop if a handler raises an error

        Returns:
            List of results from handlers
        """
        return await self._hook.dispatch(hook_name, event, stop_on_error)

    # ==========================================================================
    # Health Monitoring (delegates to HealthFacade)
    # ==========================================================================

    def get_plugin_health(self, plugin_name: str) -> Optional[PluginHealth]:
        """Get health status for a plugin."""
        return self._health.get_plugin_health(plugin_name)

    def get_all_plugin_health(self) -> List[PluginHealth]:
        """Get health status for all plugins."""
        return self._health.get_all_plugin_health()

    def get_unhealthy_plugins(self) -> List[PluginHealth]:
        """Get list of unhealthy plugins."""
        return self._health.get_unhealthy_plugins()

    def enable_plugin(self, plugin_name: str) -> bool:
        """Re-enable a disabled plugin."""
        return self._health.enable_plugin(plugin_name)

    def disable_plugin(self, plugin_name: str, reason: str = "Manual disable") -> bool:
        """Manually disable a plugin."""
        return self._health.disable_plugin(plugin_name, reason)

    # ==========================================================================
    # Event Listeners (delegates to EventFacade)
    # ==========================================================================

    def add_event_listener(
        self,
        listener: Callable[[PluginEvent], Awaitable[None]],
    ) -> None:
        """Add a listener for plugin events."""
        self._event.add_event_listener(listener)

    def get_event_history(
        self,
        plugin_name: Optional[str] = None,
        hook_name: Optional[str] = None,
        success_only: Optional[bool] = None,
        limit: int = 100,
    ) -> List[PluginEvent]:
        """Get event history with optional filtering."""
        return self._event.get_event_history(
            plugin_name=plugin_name,
            hook_name=hook_name,
            success_only=success_only,
            limit=limit,
        )

    # ==========================================================================
    # Statistics
    # ==========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get plugin manager statistics."""
        return {
            **self._registry.get_stats(),
            **self._lifecycle.get_stats(),
            **self._health.get_stats(),
            **self._event.get_stats(),
            "sandbox_enabled": self._sandbox.enabled,
        }

    # ==========================================================================
    # Direct Facade Access
    # ==========================================================================

    @property
    def registry(self) -> RegistryFacade:
        """Get the registry facade."""
        return self._registry

    @property
    def dependency(self) -> DependencyFacade:
        """Get the dependency facade."""
        return self._dependency

    @property
    def lifecycle(self) -> LifecycleFacade:
        """Get the lifecycle facade."""
        return self._lifecycle

    @property
    def hook(self) -> HookFacade:
        """Get the hook facade."""
        return self._hook

    @property
    def health(self) -> HealthFacade:
        """Get the health facade."""
        return self._health

    @property
    def event(self) -> EventFacade:
        """Get the event facade."""
        return self._event
