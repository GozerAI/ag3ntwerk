"""
Plugin/Extension System for ag3ntwerk.

Provides a modular extension mechanism:
- Plugin discovery and loading
- Lifecycle hooks (startup, shutdown)
- Event subscriptions
- Dependency injection
- Configuration management
- Sandboxed execution with timeouts
- Hot reload support
- Version compatibility checking

Usage:
    from ag3ntwerk.core.plugins import (
        Plugin,
        PluginManager,
        get_plugin_manager,
        hook,
    )

    # Define a plugin
    class MyPlugin(Plugin):
        name = "my-plugin"
        version = "1.0.0"

        async def on_startup(self):
            print("Plugin started!")

        @hook("task.completed")
        async def on_task_completed(self, event):
            print(f"Task completed: {event['task_id']}")

    # Register and load
    manager = get_plugin_manager()
    await manager.register(MyPlugin())
    await manager.startup()
"""

from typing import Any, Dict, List, Optional

# Models
from ag3ntwerk.core.plugins.models import (
    PluginState,
    PluginMetadata,
    HookRegistration,
    SandboxConfig,
    VersionRequirement,
    PluginHealth,
    PluginEvent,
    EventFilter,
    PluginContext,
)

# Base classes and decorator
from ag3ntwerk.core.plugins.base import (
    Plugin,
    LoggingPlugin,
    MetricsPlugin,
)
from ag3ntwerk.core.plugins._utils import hook

# Manager
from ag3ntwerk.core.plugins.manager import PluginManager

# Facades (for direct access)
from ag3ntwerk.core.plugins.facades import (
    RegistryFacade,
    DependencyFacade,
    LifecycleFacade,
    HookFacade,
    HealthFacade,
    EventFacade,
)


# Global plugin manager
_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager."""
    global _manager
    if _manager is None:
        _manager = PluginManager()
    return _manager


async def dispatch_plugin_event(
    hook_name: str,
    event: Dict[str, Any],
) -> List[Any]:
    """
    Dispatch an event to plugins.

    Args:
        hook_name: Name of the hook
        event: Event data

    Returns:
        List of handler results
    """
    manager = get_plugin_manager()
    return await manager.dispatch(hook_name, event)


async def shutdown_plugins() -> None:
    """Shutdown the plugin system."""
    global _manager
    if _manager:
        await _manager.shutdown()
        _manager = None


__all__ = [
    # Enums
    "PluginState",
    # Data classes
    "PluginMetadata",
    "HookRegistration",
    "SandboxConfig",
    "VersionRequirement",
    "PluginHealth",
    "PluginEvent",
    "EventFilter",
    "PluginContext",
    # Decorator
    "hook",
    # Base class
    "Plugin",
    # Manager
    "PluginManager",
    "get_plugin_manager",
    # Built-in plugins
    "LoggingPlugin",
    "MetricsPlugin",
    # Functions
    "dispatch_plugin_event",
    "shutdown_plugins",
    # Facades
    "RegistryFacade",
    "DependencyFacade",
    "LifecycleFacade",
    "HookFacade",
    "HealthFacade",
    "EventFacade",
]
