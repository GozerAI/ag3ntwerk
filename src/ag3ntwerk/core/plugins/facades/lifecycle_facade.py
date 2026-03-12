"""
Lifecycle Facade - Plugin startup, shutdown, and hot reload.

This facade handles:
- Plugin startup with timeout
- Plugin shutdown with timeout
- State transitions
- Hot reload support
- Error reset loop management
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from ag3ntwerk.core.plugins.models import PluginState, SandboxConfig

if TYPE_CHECKING:
    from ag3ntwerk.core.plugins.base import Plugin

logger = logging.getLogger(__name__)


class LifecycleFacade:
    """
    Facade for plugin lifecycle operations.

    Manages startup, shutdown, and hot reload.
    """

    def __init__(
        self,
        plugins: Dict[str, "Plugin"],
        sandbox: SandboxConfig,
    ):
        """
        Initialize the lifecycle facade.

        Args:
            plugins: Shared plugins dictionary
            sandbox: Sandbox configuration
        """
        self._plugins = plugins
        self._sandbox = sandbox
        self._error_reset_task: Optional[asyncio.Task] = None
        self._started = False

        # Callback for hook re-registration during hot reload
        self._reregister_hooks_callback: Optional[Callable[["Plugin"], None]] = None

    def set_reregister_hooks_callback(
        self,
        callback: Callable[["Plugin"], None],
    ) -> None:
        """
        Set callback for hook re-registration during reload.

        Args:
            callback: Function that takes a plugin and re-registers its hooks
        """
        self._reregister_hooks_callback = callback

    async def startup_all(
        self,
        dependency_order: List[str],
    ) -> Dict[str, bool]:
        """
        Start all registered plugins in dependency order.

        Args:
            dependency_order: Plugin names in startup order

        Returns:
            Dict mapping plugin names to startup success
        """
        results = {}

        for plugin_name in dependency_order:
            plugin = self._plugins.get(plugin_name)
            if plugin:
                success = await self.start_plugin(plugin)
                results[plugin_name] = success

        self._started = True

        # Start error reset task
        if self._sandbox.enabled:
            self._error_reset_task = asyncio.create_task(self._error_reset_loop())

        logger.info(f"Started {sum(results.values())}/{len(results)} plugins")
        return results

    async def shutdown_all(
        self,
        reverse_order: List[str],
    ) -> Dict[str, bool]:
        """
        Shutdown all plugins in reverse dependency order.

        Args:
            reverse_order: Plugin names in shutdown order

        Returns:
            Dict mapping plugin names to shutdown success
        """
        # Cancel error reset task
        if self._error_reset_task:
            self._error_reset_task.cancel()
            try:
                await self._error_reset_task
            except asyncio.CancelledError:
                pass
            self._error_reset_task = None

        results = {}

        for plugin_name in reverse_order:
            plugin = self._plugins.get(plugin_name)
            if plugin and plugin.state == PluginState.ACTIVE:
                success = await self.stop_plugin(plugin)
                results[plugin_name] = success

        self._started = False
        logger.info(f"Stopped {sum(results.values())}/{len(results)} plugins")
        return results

    async def start_plugin(self, plugin: "Plugin") -> bool:
        """
        Start a single plugin with sandboxed execution.

        Args:
            plugin: Plugin to start

        Returns:
            True if started successfully
        """
        try:
            plugin._state = PluginState.INITIALIZING

            if self._sandbox.enabled:
                # Execute with timeout
                await asyncio.wait_for(
                    plugin.on_startup(), timeout=self._sandbox.startup_timeout_seconds
                )
            else:
                await plugin.on_startup()

            plugin._state = PluginState.ACTIVE
            plugin._started_at = datetime.now(timezone.utc)
            plugin._error = None

            logger.info(f"Started plugin: {plugin.name}")
            return True

        except asyncio.TimeoutError:
            plugin._state = PluginState.ERROR
            plugin._error = f"Startup timeout ({self._sandbox.startup_timeout_seconds}s)"
            logger.error(f"Plugin {plugin.name} startup timed out")
            return False

        except Exception as e:
            plugin._state = PluginState.ERROR
            plugin._error = str(e)
            logger.exception(f"Failed to start plugin: {plugin.name}")
            return False

    async def stop_plugin(self, plugin: "Plugin") -> bool:
        """
        Stop a single plugin with sandboxed execution.

        Args:
            plugin: Plugin to stop

        Returns:
            True if stopped successfully
        """
        try:
            plugin._state = PluginState.STOPPING

            if self._sandbox.enabled:
                await asyncio.wait_for(
                    plugin.on_shutdown(), timeout=self._sandbox.shutdown_timeout_seconds
                )
            else:
                await plugin.on_shutdown()

            plugin._state = PluginState.STOPPED
            logger.info(f"Stopped plugin: {plugin.name}")
            return True

        except asyncio.TimeoutError:
            plugin._state = PluginState.STOPPED
            logger.warning(f"Plugin {plugin.name} shutdown timed out, forcing stop")
            return True

        except Exception as e:
            plugin._state = PluginState.ERROR
            plugin._error = str(e)
            logger.exception(f"Error stopping plugin: {plugin.name}")
            return False

    async def reload_plugin(
        self,
        plugin_name: str,
        lock: asyncio.Lock,
    ) -> bool:
        """
        Hot reload a plugin.

        Re-registers hooks after reload to pick up any changes.

        Args:
            plugin_name: Plugin to reload
            lock: Lock for thread safety

        Returns:
            True if successful
        """
        async with lock:
            plugin = self._plugins.get(plugin_name)
            if not plugin:
                logger.error(f"Plugin not found: {plugin_name}")
                return False

            try:
                # Call reload hook
                await plugin.on_reload()

                # Stop plugin
                if plugin.state == PluginState.ACTIVE:
                    await self.stop_plugin(plugin)

                # Reset plugin state
                plugin._error_count = 0
                plugin._disabled = False
                plugin._disabled_reason = None

                # Re-register hooks (may have changed during reload)
                if self._reregister_hooks_callback:
                    self._reregister_hooks_callback(plugin)

                # Restart plugin
                success = await self.start_plugin(plugin)

                if success:
                    logger.info(f"Reloaded plugin: {plugin_name}")
                else:
                    logger.error(f"Failed to reload plugin: {plugin_name}")

                return success

            except Exception as e:
                logger.exception(f"Error reloading plugin: {plugin_name}")
                plugin._error = str(e)
                return False

    async def reload_all_plugins(self, lock: asyncio.Lock) -> Dict[str, bool]:
        """
        Reload all plugins.

        Args:
            lock: Lock for thread safety

        Returns:
            Dict mapping plugin names to reload success
        """
        results = {}
        for name in list(self._plugins.keys()):
            results[name] = await self.reload_plugin(name, lock)
        return results

    async def _error_reset_loop(self) -> None:
        """Periodically reset error counts for plugins."""
        interval = self._sandbox.error_reset_interval_seconds
        while True:
            try:
                await asyncio.sleep(interval)
                for plugin in self._plugins.values():
                    plugin.reset_error_count()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in reset loop: {e}")

    @property
    def is_started(self) -> bool:
        """Check if lifecycle has started."""
        return self._started

    def get_stats(self) -> Dict[str, Any]:
        """Get lifecycle statistics."""
        return {
            "started": self._started,
            "active_plugins": sum(
                1 for p in self._plugins.values() if p.state == PluginState.ACTIVE
            ),
        }
