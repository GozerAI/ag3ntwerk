"""
Dependency Facade - Plugin dependency and version checking.

This facade handles:
- Dependency checking
- Version requirement validation
- Topological sort for startup order
"""

import logging
from typing import Any, Dict, List, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from ag3ntwerk.core.plugins.base import Plugin

logger = logging.getLogger(__name__)


class DependencyFacade:
    """
    Facade for plugin dependency operations.

    Manages dependency resolution and version checking.
    """

    def __init__(self, plugins: Dict[str, "Plugin"]):
        """
        Initialize the dependency facade.

        Args:
            plugins: Shared plugins dictionary
        """
        self._plugins = plugins

    def check_dependencies(self, plugin: "Plugin") -> List[str]:
        """
        Check for missing dependencies.

        Args:
            plugin: Plugin to check

        Returns:
            List of missing dependency names
        """
        missing = []
        for dep in plugin.dependencies:
            if dep not in self._plugins:
                missing.append(dep)
        return missing

    def check_version_requirements(self, plugin: "Plugin") -> List[str]:
        """
        Check version requirements for a plugin.

        Args:
            plugin: Plugin to check

        Returns:
            List of version requirement errors
        """
        errors = []
        for req in plugin.version_requirements:
            dep_plugin = self._plugins.get(req.plugin_name)
            if not dep_plugin:
                continue  # Dependency check handles missing plugins

            if not req.is_satisfied(dep_plugin.version):
                errors.append(
                    f"{req.plugin_name} version {dep_plugin.version} "
                    f"does not satisfy requirement"
                )
        return errors

    def get_dependency_order(self) -> List[str]:
        """
        Get plugin names in dependency order (topological sort).

        Returns:
            List of plugin names in order
        """
        visited: Set[str] = set()
        result: List[str] = []

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)

            plugin = self._plugins.get(name)
            if plugin:
                for dep in plugin.dependencies:
                    if dep in self._plugins:
                        visit(dep)
                result.append(name)

        for name in self._plugins:
            visit(name)

        return result

    def get_reverse_dependency_order(self) -> List[str]:
        """
        Get plugin names in reverse dependency order (for shutdown).

        Returns:
            List of plugin names in reverse order
        """
        return list(reversed(self.get_dependency_order()))

    def get_dependents(self, plugin_name: str) -> List[str]:
        """
        Get plugins that depend on the given plugin.

        Args:
            plugin_name: Plugin name

        Returns:
            List of dependent plugin names
        """
        dependents = []
        for name, plugin in self._plugins.items():
            if plugin_name in plugin.dependencies:
                dependents.append(name)
        return dependents

    def get_stats(self) -> Dict[str, Any]:
        """Get dependency statistics."""
        total_dependencies = sum(len(p.dependencies) for p in self._plugins.values())
        return {
            "total_dependencies": total_dependencies,
        }
