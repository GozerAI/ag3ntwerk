"""
Brand Asset Management - Asset library and organization.

Provides asset storage, organization, and retrieval for
brand materials and resources.
"""

import json
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ag3ntwerk.modules.brand.core import (
    BrandAsset,
    BrandAssetType,
    ContentType,
)

logger = logging.getLogger(__name__)


@dataclass
class AssetVersion:
    """Version of an asset."""

    version: str = "1.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    file_path: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "file_path": self.file_path,
            "notes": self.notes,
        }


@dataclass
class AssetCollection:
    """Collection of related assets."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    asset_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "asset_count": len(self.asset_ids),
            "tags": self.tags,
        }


class AssetManager:
    """Manages individual brand assets."""

    def __init__(self, storage_path: Optional[Path] = None):
        self._assets: Dict[str, BrandAsset] = {}
        self._versions: Dict[str, List[AssetVersion]] = {}
        self._storage_path = storage_path

        if storage_path:
            storage_path.mkdir(parents=True, exist_ok=True)

    def add_asset(
        self,
        asset: BrandAsset,
        file_path: Optional[Path] = None,
    ) -> str:
        """Add an asset to the manager."""
        self._assets[asset.id] = asset

        if file_path and file_path.exists() and self._storage_path:
            # Copy file to storage
            dest = self._storage_path / f"{asset.id}_{file_path.name}"
            shutil.copy(file_path, dest)
            asset.file_path = str(dest)

        # Create initial version
        version = AssetVersion(
            version="1.0",
            file_path=asset.file_path or "",
            created_by="system",
        )
        self._versions[asset.id] = [version]

        logger.info(f"Added asset: {asset.name} ({asset.id})")
        return asset.id

    def get_asset(self, asset_id: str) -> Optional[BrandAsset]:
        """Get an asset by ID."""
        return self._assets.get(asset_id)

    def update_asset(
        self,
        asset_id: str,
        updates: Dict[str, Any],
        new_file: Optional[Path] = None,
    ) -> Optional[BrandAsset]:
        """Update an asset."""
        asset = self._assets.get(asset_id)
        if not asset:
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(asset, key):
                setattr(asset, key, value)

        asset.updated_at = datetime.now(timezone.utc)

        # Handle new file version
        if new_file and new_file.exists() and self._storage_path:
            # Increment version
            versions = self._versions.get(asset_id, [])
            current_version = versions[-1].version if versions else "1.0"
            parts = current_version.split(".")
            new_version = f"{parts[0]}.{int(parts[1]) + 1}"

            # Copy file
            dest = self._storage_path / f"{asset_id}_v{new_version}_{new_file.name}"
            shutil.copy(new_file, dest)

            # Add version
            version = AssetVersion(
                version=new_version,
                file_path=str(dest),
                created_by="system",
            )
            self._versions.setdefault(asset_id, []).append(version)
            asset.version = new_version
            asset.file_path = str(dest)

        return asset

    def delete_asset(self, asset_id: str) -> bool:
        """Delete an asset."""
        if asset_id not in self._assets:
            return False

        asset = self._assets[asset_id]

        # Delete file if exists
        if asset.file_path and self._storage_path:
            file_path = Path(asset.file_path)
            if file_path.exists():
                file_path.unlink()

        del self._assets[asset_id]
        self._versions.pop(asset_id, None)

        logger.info(f"Deleted asset: {asset_id}")
        return True

    def get_by_type(self, asset_type: BrandAssetType) -> List[BrandAsset]:
        """Get assets by type."""
        return [a for a in self._assets.values() if a.asset_type == asset_type]

    def get_for_content_type(self, content_type: ContentType) -> List[BrandAsset]:
        """Get assets applicable to a content type."""
        return [a for a in self._assets.values() if content_type in a.usage_contexts]

    def search(self, query: str) -> List[BrandAsset]:
        """Search assets by name or tags."""
        query_lower = query.lower()
        return [
            a
            for a in self._assets.values()
            if query_lower in a.name.lower() or any(query_lower in tag.lower() for tag in a.tags)
        ]

    def get_versions(self, asset_id: str) -> List[AssetVersion]:
        """Get all versions of an asset."""
        return self._versions.get(asset_id, [])

    def list_all(self) -> List[BrandAsset]:
        """List all assets."""
        return list(self._assets.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get asset statistics."""
        assets = self.list_all()
        return {
            "total_assets": len(assets),
            "by_type": {
                t.value: len([a for a in assets if a.asset_type == t]) for t in BrandAssetType
            },
            "total_size_bytes": sum(a.file_size for a in assets),
        }


class AssetLibrary:
    """
    High-level asset library for brand management.

    Provides organized access to brand assets with collections
    and intelligent retrieval.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self._manager = AssetManager(storage_path)
        self._collections: Dict[str, AssetCollection] = {}

    def add_asset(self, asset: BrandAsset, file_path: Optional[Path] = None) -> str:
        """Add an asset to the library."""
        return self._manager.add_asset(asset, file_path)

    def get_asset(self, asset_id: str) -> Optional[BrandAsset]:
        """Get an asset by ID."""
        return self._manager.get_asset(asset_id)

    def create_collection(
        self,
        name: str,
        description: str = "",
        asset_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Create an asset collection."""
        collection = AssetCollection(
            name=name,
            description=description,
            asset_ids=asset_ids or [],
            tags=tags or [],
        )
        self._collections[collection.id] = collection
        logger.info(f"Created collection: {name}")
        return collection.id

    def add_to_collection(self, collection_id: str, asset_id: str) -> bool:
        """Add an asset to a collection."""
        collection = self._collections.get(collection_id)
        if not collection:
            return False

        if asset_id not in collection.asset_ids:
            collection.asset_ids.append(asset_id)

        return True

    def get_collection(self, collection_id: str) -> Optional[AssetCollection]:
        """Get a collection by ID."""
        return self._collections.get(collection_id)

    def get_collection_assets(self, collection_id: str) -> List[BrandAsset]:
        """Get all assets in a collection."""
        collection = self._collections.get(collection_id)
        if not collection:
            return []

        return [
            self._manager.get_asset(aid)
            for aid in collection.asset_ids
            if self._manager.get_asset(aid)
        ]

    def list_collections(self) -> List[AssetCollection]:
        """List all collections."""
        return list(self._collections.values())

    # Convenience methods

    def get_logos(self) -> List[BrandAsset]:
        """Get all logo assets."""
        logos = self._manager.get_by_type(BrandAssetType.LOGO)
        logos.extend(self._manager.get_by_type(BrandAssetType.LOGO_VARIANT))
        return logos

    def get_primary_logo(self) -> Optional[BrandAsset]:
        """Get the primary logo."""
        logos = self._manager.get_by_type(BrandAssetType.LOGO)
        return logos[0] if logos else None

    def get_icons(self) -> List[BrandAsset]:
        """Get all icon assets."""
        return self._manager.get_by_type(BrandAssetType.ICON)

    def get_templates(self) -> List[BrandAsset]:
        """Get all template assets."""
        return self._manager.get_by_type(BrandAssetType.TEMPLATE)

    def get_for_social_media(self) -> List[BrandAsset]:
        """Get assets for social media use."""
        return self._manager.get_for_content_type(ContentType.SOCIAL_MEDIA)

    def get_for_print(self) -> List[BrandAsset]:
        """Get assets for print use."""
        return self._manager.get_for_content_type(ContentType.PRINT)

    def search(self, query: str) -> List[BrandAsset]:
        """Search the library."""
        return self._manager.search(query)

    def get_stats(self) -> Dict[str, Any]:
        """Get library statistics."""
        manager_stats = self._manager.get_stats()
        return {
            **manager_stats,
            "total_collections": len(self._collections),
        }

    def generate_asset_report(self) -> Dict[str, Any]:
        """Generate a comprehensive asset report."""
        assets = self._manager.list_all()

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": self.get_stats(),
            "by_type": {},
            "by_usage": {},
            "collections": [c.to_dict() for c in self._collections.values()],
            "recent_updates": [],
        }

        # Group by type
        for asset_type in BrandAssetType:
            type_assets = self._manager.get_by_type(asset_type)
            if type_assets:
                report["by_type"][asset_type.value] = [
                    {"id": a.id, "name": a.name} for a in type_assets
                ]

        # Group by usage context
        for content_type in ContentType:
            context_assets = self._manager.get_for_content_type(content_type)
            if context_assets:
                report["by_usage"][content_type.value] = [
                    {"id": a.id, "name": a.name} for a in context_assets
                ]

        # Recent updates
        sorted_assets = sorted(
            assets,
            key=lambda a: a.updated_at or a.created_at,
            reverse=True,
        )
        report["recent_updates"] = [
            {
                "id": a.id,
                "name": a.name,
                "updated": (a.updated_at or a.created_at).isoformat(),
            }
            for a in sorted_assets[:10]
        ]

        return report
