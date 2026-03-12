"""
Plugin Facades - Focused components for the Plugin system.

Each facade handles a specific domain of plugin functionality.
"""

from ag3ntwerk.core.plugins.facades.registry_facade import RegistryFacade
from ag3ntwerk.core.plugins.facades.dependency_facade import DependencyFacade
from ag3ntwerk.core.plugins.facades.lifecycle_facade import LifecycleFacade
from ag3ntwerk.core.plugins.facades.hook_facade import HookFacade
from ag3ntwerk.core.plugins.facades.health_facade import HealthFacade
from ag3ntwerk.core.plugins.facades.event_facade import EventFacade

__all__ = [
    "RegistryFacade",
    "DependencyFacade",
    "LifecycleFacade",
    "HookFacade",
    "HealthFacade",
    "EventFacade",
]
