"""
Plugin configuration persistence for ag3ntwerk.

Provides storage and management for plugin configurations,
enabling persistent plugin settings across restarts.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel

from .database import DatabaseManager, get_database

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _utcnow() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


@dataclass
class PluginMetadata:
    """Metadata about a plugin's configuration."""

    plugin_id: str
    enabled: bool = True
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "enabled": self.enabled,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class PluginConfig:
    """Complete plugin configuration with metadata."""

    metadata: PluginMetadata
    config_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **self.metadata.to_dict(),
            "config": self.config_data,
        }


class PluginConfigStore:
    """
    Plugin configuration storage and management.

    Features:
    - Store and retrieve plugin configurations
    - Enable/disable plugins
    - Version tracking
    - Configuration validation with Pydantic models
    - Bulk operations

    Usage:
        store = PluginConfigStore()

        # Save plugin config
        await store.save(
            plugin_id="weather-plugin",
            config={"api_key": "xxx", "default_location": "NYC"},
            version="1.2.0",
        )

        # Load plugin config
        config = await store.load("weather-plugin")

        # Load with Pydantic validation
        class WeatherConfig(BaseModel):
            api_key: str
            default_location: str = "NYC"

        config = await store.load_typed("weather-plugin", WeatherConfig)

        # Enable/disable
        await store.set_enabled("weather-plugin", False)
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """Initialize plugin config store."""
        self._db = db
        self._initialized = False
        self._cache: Dict[str, PluginConfig] = {}

    async def _get_db(self) -> DatabaseManager:
        """Get database instance."""
        if self._db is None:
            self._db = await get_database()
        return self._db

    async def initialize(self) -> None:
        """Initialize the store."""
        if self._initialized:
            return
        await self._get_db()
        self._initialized = True

    async def save(
        self,
        plugin_id: str,
        config: Dict[str, Any],
        version: str = "1.0.0",
        enabled: bool = True,
    ) -> None:
        """
        Save plugin configuration.

        Args:
            plugin_id: Unique plugin identifier
            config: Configuration dictionary
            version: Plugin version
            enabled: Whether plugin is enabled
        """
        db = await self._get_db()
        now = _utcnow()

        # Check if exists
        existing = await db.fetch_one(
            "SELECT created_at FROM plugin_config WHERE plugin_id = ?",
            (plugin_id,),
        )

        created_at = existing["created_at"] if existing else now.isoformat()

        await db.execute(
            """
            INSERT OR REPLACE INTO plugin_config
            (plugin_id, config_data, enabled, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                plugin_id,
                json.dumps(config),
                1 if enabled else 0,
                version,
                created_at,
                now.isoformat(),
            ),
        )

        # Update cache
        self._cache[plugin_id] = PluginConfig(
            metadata=PluginMetadata(
                plugin_id=plugin_id,
                enabled=enabled,
                version=version,
                created_at=(
                    datetime.fromisoformat(created_at)
                    if isinstance(created_at, str)
                    else created_at
                ),
                updated_at=now,
            ),
            config_data=config,
        )

        logger.debug(f"Saved config for plugin: {plugin_id}")

    async def load(
        self,
        plugin_id: str,
        default: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Load plugin configuration.

        Args:
            plugin_id: Plugin identifier
            default: Default config if not found

        Returns:
            Configuration dictionary or default
        """
        # Check cache first
        if plugin_id in self._cache:
            return self._cache[plugin_id].config_data

        db = await self._get_db()

        row = await db.fetch_one(
            """
            SELECT config_data, enabled, version, created_at, updated_at
            FROM plugin_config WHERE plugin_id = ?
            """,
            (plugin_id,),
        )

        if not row:
            return default

        config_data = json.loads(row["config_data"])

        # Update cache
        self._cache[plugin_id] = PluginConfig(
            metadata=PluginMetadata(
                plugin_id=plugin_id,
                enabled=bool(row["enabled"]),
                version=row["version"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            ),
            config_data=config_data,
        )

        return config_data

    async def load_typed(
        self,
        plugin_id: str,
        config_class: type[T],
        default: Optional[T] = None,
    ) -> Optional[T]:
        """
        Load and validate plugin configuration with a Pydantic model.

        Args:
            plugin_id: Plugin identifier
            config_class: Pydantic model class for validation
            default: Default config if not found

        Returns:
            Validated configuration instance or default
        """
        raw_config = await self.load(plugin_id)

        if raw_config is None:
            return default

        try:
            return config_class.model_validate(raw_config)
        except Exception as e:
            logger.warning(f"Failed to validate config for {plugin_id}: {e}")
            return default

    async def load_full(self, plugin_id: str) -> Optional[PluginConfig]:
        """
        Load full plugin config including metadata.

        Args:
            plugin_id: Plugin identifier

        Returns:
            PluginConfig with metadata or None
        """
        # Ensure it's loaded into cache
        await self.load(plugin_id)
        return self._cache.get(plugin_id)

    async def delete(self, plugin_id: str) -> bool:
        """
        Delete plugin configuration.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if deleted, False if not found
        """
        db = await self._get_db()

        result = await db.execute(
            "DELETE FROM plugin_config WHERE plugin_id = ?",
            (plugin_id,),
        )

        # Remove from cache
        self._cache.pop(plugin_id, None)

        return result > 0

    async def set_enabled(self, plugin_id: str, enabled: bool) -> bool:
        """
        Enable or disable a plugin.

        Args:
            plugin_id: Plugin identifier
            enabled: Whether to enable

        Returns:
            True if updated, False if plugin not found
        """
        db = await self._get_db()

        result = await db.execute(
            """
            UPDATE plugin_config
            SET enabled = ?, updated_at = ?
            WHERE plugin_id = ?
            """,
            (1 if enabled else 0, _utcnow().isoformat(), plugin_id),
        )

        # Update cache
        if plugin_id in self._cache:
            self._cache[plugin_id].metadata.enabled = enabled

        return result > 0

    async def is_enabled(self, plugin_id: str) -> bool:
        """
        Check if a plugin is enabled.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if enabled, False if disabled or not found
        """
        config = await self.load_full(plugin_id)
        return config.metadata.enabled if config else False

    async def list_plugins(
        self,
        enabled_only: bool = False,
    ) -> List[PluginMetadata]:
        """
        List all plugin configurations.

        Args:
            enabled_only: Only return enabled plugins

        Returns:
            List of plugin metadata
        """
        db = await self._get_db()

        query = "SELECT plugin_id, enabled, version, created_at, updated_at FROM plugin_config"
        params: tuple = ()

        if enabled_only:
            query += " WHERE enabled = 1"

        query += " ORDER BY plugin_id"

        rows = await db.fetch_all(query, params)

        return [
            PluginMetadata(
                plugin_id=row["plugin_id"],
                enabled=bool(row["enabled"]),
                version=row["version"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    async def update_config(
        self,
        plugin_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """
        Partially update plugin configuration.

        Args:
            plugin_id: Plugin identifier
            updates: Configuration fields to update

        Returns:
            True if updated, False if plugin not found
        """
        current = await self.load(plugin_id)
        if current is None:
            return False

        # Merge updates
        current.update(updates)

        # Get current metadata
        full_config = await self.load_full(plugin_id)
        if full_config:
            await self.save(
                plugin_id=plugin_id,
                config=current,
                version=full_config.metadata.version,
                enabled=full_config.metadata.enabled,
            )
            return True

        return False

    async def export_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Export all plugin configurations.

        Returns:
            Dictionary mapping plugin_id to full config
        """
        plugins = await self.list_plugins()
        result = {}

        for plugin in plugins:
            full = await self.load_full(plugin.plugin_id)
            if full:
                result[plugin.plugin_id] = full.to_dict()

        return result

    async def import_configs(
        self,
        configs: Dict[str, Dict[str, Any]],
        overwrite: bool = False,
    ) -> int:
        """
        Import plugin configurations.

        Args:
            configs: Dictionary mapping plugin_id to config
            overwrite: Whether to overwrite existing configs

        Returns:
            Number of configs imported
        """
        imported = 0

        for plugin_id, config_data in configs.items():
            existing = await self.load(plugin_id)

            if existing and not overwrite:
                continue

            # Extract metadata if present, otherwise use defaults
            version = config_data.get("version", "1.0.0")
            enabled = config_data.get("enabled", True)
            config = config_data.get("config", config_data)

            await self.save(
                plugin_id=plugin_id,
                config=config,
                version=version,
                enabled=enabled,
            )
            imported += 1

        return imported

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()


# Global instance
_plugin_store: Optional[PluginConfigStore] = None


async def get_plugin_config_store() -> PluginConfigStore:
    """Get the global plugin config store."""
    global _plugin_store
    if _plugin_store is None:
        _plugin_store = PluginConfigStore()
        await _plugin_store.initialize()
    return _plugin_store
