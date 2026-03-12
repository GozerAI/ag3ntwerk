"""
Health Facade - Plugin health monitoring.

This facade handles:
- Plugin health status queries
- Enable/disable plugins
- Unhealthy plugin detection
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ag3ntwerk.core.plugins.models import PluginHealth, PluginState

if TYPE_CHECKING:
    from ag3ntwerk.core.plugins.base import Plugin

logger = logging.getLogger(__name__)


class HealthFacade:
    """
    Facade for plugin health operations.

    Manages health monitoring and plugin enable/disable.
    """

    def __init__(self, plugins: Dict[str, "Plugin"]):
        """
        Initialize the health facade.

        Args:
            plugins: Shared plugins dictionary
        """
        self._plugins = plugins

    def get_plugin_health(self, plugin_name: str) -> Optional[PluginHealth]:
        """
        Get health status for a plugin.

        Args:
            plugin_name: Plugin name

        Returns:
            PluginHealth or None if not found
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return None
        return plugin.get_health()

    def get_all_plugin_health(self) -> List[PluginHealth]:
        """
        Get health status for all plugins.

        Returns:
            List of PluginHealth
        """
        return [p.get_health() for p in self._plugins.values()]

    def get_unhealthy_plugins(self) -> List[PluginHealth]:
        """
        Get list of unhealthy plugins.

        Returns:
            List of unhealthy PluginHealth
        """
        return [h for h in self.get_all_plugin_health() if not h.healthy]

    def enable_plugin(self, plugin_name: str) -> bool:
        """
        Re-enable a disabled plugin.

        Args:
            plugin_name: Plugin name

        Returns:
            True if enabled
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return False
        plugin.enable()
        return True

    def disable_plugin(self, plugin_name: str, reason: str = "Manual disable") -> bool:
        """
        Manually disable a plugin.

        Args:
            plugin_name: Plugin name
            reason: Reason for disabling

        Returns:
            True if disabled
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return False
        plugin.disable(reason)
        return True

    def get_active_count(self) -> int:
        """Get count of active plugins."""
        return sum(1 for p in self._plugins.values() if p.state == PluginState.ACTIVE)

    def get_disabled_count(self) -> int:
        """Get count of disabled plugins."""
        return sum(1 for p in self._plugins.values() if p.is_disabled)

    def get_stats(self) -> Dict[str, Any]:
        """Get health statistics."""
        health_list = self.get_all_plugin_health()

        return {
            "active_plugins": self.get_active_count(),
            "disabled_plugins": self.get_disabled_count(),
            "unhealthy_plugins": len(self.get_unhealthy_plugins()),
            "total_hooks_executed": sum(h.hooks_executed for h in health_list),
            "total_hooks_failed": sum(h.hooks_failed for h in health_list),
        }
