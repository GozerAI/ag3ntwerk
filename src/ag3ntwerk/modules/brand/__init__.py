"""
Brand Suite Module.

Provides brand guidelines, asset management, and consistency enforcement
for ag3ntwerk agents. Enables brand-aligned content creation and
marketing material validation.

Primary Owners: Echo (Echo), Beacon (Artisan)
Secondary Owners: Blueprint (Visionary)
"""

from ag3ntwerk.modules.brand.core import (
    BrandAssetType,
    BrandTone,
    BrandVoice,
    ColorPalette,
    Typography,
    BrandAsset,
    BrandGuideline,
    BrandIdentity,
)
from ag3ntwerk.modules.brand.guidelines import (
    GuidelineManager,
    GuidelineValidator,
    ConsistencyChecker,
)
from ag3ntwerk.modules.brand.assets import (
    AssetManager,
    AssetLibrary,
)
from ag3ntwerk.modules.brand.service import BrandService

__all__ = [
    # Core
    "BrandAssetType",
    "BrandTone",
    "BrandVoice",
    "ColorPalette",
    "Typography",
    "BrandAsset",
    "BrandGuideline",
    "BrandIdentity",
    # Guidelines
    "GuidelineManager",
    "GuidelineValidator",
    "ConsistencyChecker",
    # Assets
    "AssetManager",
    "AssetLibrary",
    # Service
    "BrandService",
]
