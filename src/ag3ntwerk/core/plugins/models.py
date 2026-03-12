"""
Plugin Models - Enums and Dataclasses for the Plugin system.

Contains all data structures used by the plugin facades and manager.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Enums
# =============================================================================


class PluginState(str, Enum):
    """Plugin lifecycle state."""

    REGISTERED = "registered"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class PluginMetadata:
    """Plugin metadata."""

    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class HookRegistration:
    """Registration of a hook handler."""

    hook_name: str
    handler: Callable
    plugin_name: str
    priority: int = 50  # Lower = runs first


@dataclass
class SandboxConfig:
    """Configuration for plugin sandboxing."""

    enabled: bool = True
    hook_timeout_seconds: float = 30.0
    startup_timeout_seconds: float = 60.0
    shutdown_timeout_seconds: float = 30.0
    max_errors_before_disable: int = 5
    error_reset_interval_seconds: float = 300.0  # 5 minutes


@dataclass
class VersionRequirement:
    """Version requirement for dependencies."""

    plugin_name: str
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    exact_version: Optional[str] = None

    def is_satisfied(self, version: str) -> bool:
        """Check if a version satisfies this requirement."""
        if self.exact_version:
            return version == self.exact_version

        if self.min_version and not self._version_gte(version, self.min_version):
            return False

        if self.max_version and not self._version_lte(version, self.max_version):
            return False

        return True

    def _parse_version(self, version: str) -> Tuple[int, ...]:
        """Parse version string to tuple of integers."""
        parts = re.split(r"[.-]", version)
        return tuple(int(p) for p in parts if p.isdigit())

    def _version_gte(self, v1: str, v2: str) -> bool:
        """Check if v1 >= v2."""
        return self._parse_version(v1) >= self._parse_version(v2)

    def _version_lte(self, v1: str, v2: str) -> bool:
        """Check if v1 <= v2."""
        return self._parse_version(v1) <= self._parse_version(v2)


@dataclass
class PluginHealth:
    """Health status of a plugin."""

    plugin_name: str
    state: PluginState
    healthy: bool = True
    error_count: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    uptime_seconds: float = 0.0
    hooks_executed: int = 0
    hooks_failed: int = 0
    avg_hook_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_name": self.plugin_name,
            "state": self.state.value,
            "healthy": self.healthy,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "uptime_seconds": self.uptime_seconds,
            "hooks_executed": self.hooks_executed,
            "hooks_failed": self.hooks_failed,
            "avg_hook_duration_ms": self.avg_hook_duration_ms,
        }


@dataclass
class PluginEvent:
    """Event dispatched to plugins."""

    event_type: str
    hook_name: str
    plugin_name: str
    timestamp: datetime
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class EventFilter:
    """Filter for which events a plugin receives."""

    include_patterns: List[str] = field(default_factory=list)  # Glob patterns
    exclude_patterns: List[str] = field(default_factory=list)

    def matches(self, hook_name: str) -> bool:
        """Check if hook name matches filter."""
        # Check excludes first
        for pattern in self.exclude_patterns:
            if self._glob_match(hook_name, pattern):
                return False

        # If no includes, allow all
        if not self.include_patterns:
            return True

        # Check includes
        for pattern in self.include_patterns:
            if self._glob_match(hook_name, pattern):
                return True

        return False

    def _glob_match(self, name: str, pattern: str) -> bool:
        """Simple glob matching (* for any)."""
        if pattern == "*":
            return True
        if "*" not in pattern:
            return name == pattern

        regex = pattern.replace(".", r"\.").replace("*", ".*")
        return bool(re.match(f"^{regex}$", name))


@dataclass
class PluginContext:
    """
    Context provided to plugins.

    Contains references to shared services and utilities.
    """

    # Core services
    config: Dict[str, Any] = field(default_factory=dict)
    logger: Optional[Any] = None  # logging.Logger

    # Plugin manager reference (set after manager init)
    manager: Optional[Any] = None

    # Shared data between plugins
    shared: Dict[str, Any] = field(default_factory=dict)

    def get_service(self, name: str) -> Any:
        """Get a registered service."""
        return self.shared.get(f"service:{name}")

    def register_service(self, name: str, service: Any) -> None:
        """Register a service for other plugins to use."""
        self.shared[f"service:{name}"] = service
