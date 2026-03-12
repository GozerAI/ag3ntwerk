"""
Registry Facade - Plugin registration and lookup.

This facade handles:
- Plugin registration and unregistration
- Plugin lookup
- Hook registration tracking
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ag3ntwerk.core.plugins.models import (
    EventFilter,
    HookRegistration,
    PluginContext,
    PluginState,
)

if TYPE_CHECKING:
    from ag3ntwerk.core.plugins.base import Plugin

logger = logging.getLogger(__name__)


class RegistryFacade:
    """
    Facade for plugin registration operations.

    Manages plugin registration and hook tracking.
    """

    def __init__(
        self,
        plugins: Dict[str, "Plugin"],
        hooks: Dict[str, List[HookRegistration]],
        lock: asyncio.Lock,
        context: PluginContext,
    ):
        """
        Initialize the registry facade.

        Args:
            plugins: Shared plugins dictionary
            hooks: Shared hooks dictionary
            lock: Shared lock for thread safety
            context: Plugin context
        """
        self._plugins = plugins
        self._hooks = hooks
        self._lock = lock
        self._context = context

    async def register(
        self,
        plugin: "Plugin",
        config: Optional[Dict[str, Any]] = None,
        event_filter: Optional[EventFilter] = None,
        check_dependencies: bool = True,
        dependency_checker: Optional[Any] = None,
    ) -> bool:
        """
        Register a plugin.

        Args:
            plugin: Plugin instance
            config: Optional configuration
            event_filter: Optional event filter
            check_dependencies: Whether to check dependencies
            dependency_checker: DependencyFacade for dependency checking

        Returns:
            True if registered successfully
        """
        async with self._lock:
            if plugin.name in self._plugins:
                logger.warning(f"Plugin already registered: {plugin.name}")
                return False

            # Check dependencies if requested
            if check_dependencies and dependency_checker:
                missing = dependency_checker.check_dependencies(plugin)
                if missing:
                    logger.error(f"Plugin {plugin.name} has missing dependencies: {missing}")
                    return False

                version_errors = dependency_checker.check_version_requirements(plugin)
                if version_errors:
                    logger.error(
                        f"Plugin {plugin.name} has version requirement errors: {version_errors}"
                    )
                    return False

            # Validate config
            if config:
                validation_errors = await plugin.validate_config(config)
                if validation_errors:
                    logger.error(
                        f"Plugin {plugin.name} config validation failed: {validation_errors}"
                    )
                    return False
                plugin.configure(config)

            # Set event filter
            if event_filter:
                plugin.set_event_filter(event_filter)

            # Register
            self._plugins[plugin.name] = plugin
            plugin._context = self._context

            # Register hooks
            for hook_reg in plugin.get_hooks():
                if hook_reg.hook_name not in self._hooks:
                    self._hooks[hook_reg.hook_name] = []
                self._hooks[hook_reg.hook_name].append(hook_reg)
                # Sort by priority
                self._hooks[hook_reg.hook_name].sort(key=lambda h: h.priority)

            logger.info(f"Registered plugin: {plugin.name} v{plugin.version}")
            return True

    async def unregister(
        self,
        plugin_name: str,
        stop_callback: Optional[Any] = None,
    ) -> bool:
        """
        Unregister a plugin.

        Args:
            plugin_name: Name of plugin to remove
            stop_callback: Optional callback to stop the plugin first

        Returns:
            True if removed
        """
        async with self._lock:
            plugin = self._plugins.get(plugin_name)
            if not plugin:
                return False

            # Stop if running
            if plugin.state == PluginState.ACTIVE and stop_callback:
                await stop_callback(plugin)

            # Remove hooks
            for hook_name in list(self._hooks.keys()):
                self._hooks[hook_name] = [
                    h for h in self._hooks[hook_name] if h.plugin_name != plugin_name
                ]
                if not self._hooks[hook_name]:
                    del self._hooks[hook_name]

            # Remove plugin
            del self._plugins[plugin_name]
            logger.info(f"Unregistered plugin: {plugin_name}")
            return True

    def get_plugin(self, name: str) -> Optional["Plugin"]:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins."""
        return [
            {
                "name": p.name,
                "version": p.version,
                "state": p.state.value,
                "description": p.description,
                "dependencies": p.dependencies,
                "started_at": p._started_at.isoformat() if p._started_at else None,
                "error": p._error,
            }
            for p in self._plugins.values()
        ]

    def list_hooks(self) -> Dict[str, List[str]]:
        """List all registered hooks."""
        return {
            hook_name: [h.plugin_name for h in handlers]
            for hook_name, handlers in self._hooks.items()
        }

    def reregister_hooks(self, plugin: "Plugin") -> None:
        """
        Re-register hooks for a plugin (used during hot reload).

        Removes old hooks and registers new ones from the plugin.

        Args:
            plugin: Plugin to re-register hooks for
        """
        # Remove existing hooks for this plugin
        for hook_name in list(self._hooks.keys()):
            self._hooks[hook_name] = [
                h for h in self._hooks[hook_name] if h.plugin_name != plugin.name
            ]
            if not self._hooks[hook_name]:
                del self._hooks[hook_name]

        # Re-register hooks from plugin
        for hook_reg in plugin.get_hooks():
            if hook_reg.hook_name not in self._hooks:
                self._hooks[hook_reg.hook_name] = []
            self._hooks[hook_reg.hook_name].append(hook_reg)
            # Sort by priority
            self._hooks[hook_reg.hook_name].sort(key=lambda h: h.priority)

        logger.debug(f"Re-registered hooks for plugin: {plugin.name}")

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_plugins": len(self._plugins),
            "total_hooks": sum(len(h) for h in self._hooks.values()),
        }
