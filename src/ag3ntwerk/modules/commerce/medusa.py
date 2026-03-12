"""
Medusa Integration - Multi-storefront niche commerce.

Provides Medusa backend integration for managing multiple niche
storefronts connected to a central Shopify fulfillment hub.

Architecture:
- Shopify (Cirrus1) = Source of truth, Zendrop fulfillment hub
- 8 Medusa storefronts = Niche customer-facing stores
"""

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.modules.commerce.core import (
    StorefrontPlatform,
    StorefrontStatus,
    InventoryStatus,
    Product,
    ProductVariant,
    Storefront,
)

logger = logging.getLogger(__name__)


# Niche storefront definitions
NICHE_STOREFRONTS = {
    "tech_gadgets": {
        "name": "TechGadgets Store",
        "description": "Consumer electronics and tech accessories",
        "url": "tech-gadgets.example.com",
        "segments": ["technology", "electronics", "gadgets"],
        "product_filters": {
            "product_types": ["Electronics", "Tech Accessories", "Gadgets"],
            "tags": ["tech", "electronic", "gadget", "smart"],
        },
    },
    "home_wellness": {
        "name": "Home Wellness",
        "description": "Health, wellness, and home improvement",
        "url": "home-wellness.example.com",
        "segments": ["health", "wellness", "home"],
        "product_filters": {
            "product_types": ["Health", "Wellness", "Home"],
            "tags": ["health", "wellness", "home", "lifestyle"],
        },
    },
    "fashion_forward": {
        "name": "Fashion Forward",
        "description": "Trendy fashion and accessories",
        "url": "fashion-forward.example.com",
        "segments": ["fashion", "accessories", "lifestyle"],
        "product_filters": {
            "product_types": ["Fashion", "Accessories", "Apparel"],
            "tags": ["fashion", "style", "trendy", "accessory"],
        },
    },
    "pet_paradise": {
        "name": "Pet Paradise",
        "description": "Pet supplies and accessories",
        "url": "pet-paradise.example.com",
        "segments": ["pets", "animals"],
        "product_filters": {
            "product_types": ["Pet Supplies", "Pet Accessories"],
            "tags": ["pet", "dog", "cat", "animal"],
        },
    },
    "outdoor_adventure": {
        "name": "Outdoor Adventure",
        "description": "Outdoor and adventure gear",
        "url": "outdoor-adventure.example.com",
        "segments": ["outdoor", "sports", "adventure"],
        "product_filters": {
            "product_types": ["Outdoor", "Sports", "Adventure"],
            "tags": ["outdoor", "camping", "hiking", "adventure"],
        },
    },
    "eco_living": {
        "name": "Eco Living",
        "description": "Sustainable and eco-friendly products",
        "url": "eco-living.example.com",
        "segments": ["sustainable", "eco", "green"],
        "product_filters": {
            "product_types": ["Sustainable", "Eco-Friendly"],
            "tags": ["eco", "sustainable", "green", "organic"],
        },
    },
    "creative_corner": {
        "name": "Creative Corner",
        "description": "Art, craft, and creative supplies",
        "url": "creative-corner.example.com",
        "segments": ["art", "craft", "creative"],
        "product_filters": {
            "product_types": ["Art", "Craft", "Creative"],
            "tags": ["art", "craft", "creative", "diy"],
        },
    },
    "productivity_hub": {
        "name": "Productivity Hub",
        "description": "Work and productivity tools",
        "url": "productivity-hub.example.com",
        "segments": ["work", "productivity", "office"],
        "product_filters": {
            "product_types": ["Office", "Productivity", "Work"],
            "tags": ["work", "office", "productivity", "desk"],
        },
    },
}


@dataclass
class MedusaCredentials:
    """Medusa API credentials."""

    base_url: str
    api_key: Optional[str] = None
    jwt_token: Optional[str] = None


class MedusaClient:
    """
    Medusa API client.

    Provides methods for interacting with Medusa backend.
    """

    def __init__(self, credentials: MedusaCredentials):
        self.credentials = credentials
        self._request_count = 0

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make request to Medusa API."""
        url = f"{self.credentials.base_url}/{endpoint}"

        try:
            req = urllib.request.Request(url)
            req.add_header("Content-Type", "application/json")

            if self.credentials.api_key:
                req.add_header("x-medusa-access-token", self.credentials.api_key)
            if self.credentials.jwt_token:
                req.add_header("Authorization", f"Bearer {self.credentials.jwt_token}")

            req.method = method

            if data:
                req.data = json.dumps(data).encode("utf-8")

            with urllib.request.urlopen(req, timeout=30) as response:
                self._request_count += 1
                return json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as e:
            logger.error(f"Medusa API error: {e.code} - {e.reason}")
            return None
        except Exception as e:
            logger.error(f"Medusa request failed: {e}")
            return None

    def get_products(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Get products from Medusa."""
        response = self._make_request(f"admin/products?limit={limit}&offset={offset}")
        return response or {"products": [], "count": 0}

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get a single product."""
        response = self._make_request(f"admin/products/{product_id}")
        return response.get("product") if response else None

    def create_product(self, product_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a product in Medusa."""
        response = self._make_request(
            "admin/products",
            method="POST",
            data=product_data,
        )
        return response.get("product") if response else None

    def update_product(
        self,
        product_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update a product."""
        response = self._make_request(
            f"admin/products/{product_id}",
            method="POST",
            data=updates,
        )
        return response.get("product") if response else None

    def get_regions(self) -> List[Dict[str, Any]]:
        """Get available regions."""
        response = self._make_request("admin/regions")
        return response.get("regions", []) if response else []

    def get_orders(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get orders."""
        response = self._make_request(f"admin/orders?limit={limit}")
        return response.get("orders", []) if response else []

    def health_check(self) -> bool:
        """Check if Medusa is healthy."""
        response = self._make_request("health")
        return response is not None


@dataclass
class NicheStorefront:
    """
    Represents a niche storefront in the Medusa ecosystem.

    Each niche storefront filters products from the master Shopify
    catalog based on specific criteria.
    """

    key: str
    name: str
    description: str
    url: str
    segments: List[str] = field(default_factory=list)
    product_filters: Dict[str, Any] = field(default_factory=dict)
    status: StorefrontStatus = StorefrontStatus.ACTIVE

    # Metrics
    product_count: int = 0
    order_count: int = 0
    revenue: float = 0.0

    # Pricing
    markup_percentage: float = 0.0  # Additional markup for this storefront
    pricing_strategy: str = "competitive"

    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches_product(self, product: Product) -> bool:
        """Check if a product matches this storefront's filters."""
        # Check product type
        if "product_types" in self.product_filters:
            if product.product_type not in self.product_filters["product_types"]:
                # Also check partial match
                if not any(
                    pt.lower() in (product.product_type or "").lower()
                    for pt in self.product_filters["product_types"]
                ):
                    return False

        # Check tags
        if "tags" in self.product_filters:
            product_tags = set(t.lower() for t in product.tags)
            filter_tags = set(t.lower() for t in self.product_filters["tags"])
            if not product_tags & filter_tags:
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "segments": self.segments,
            "status": self.status.value,
            "product_count": self.product_count,
            "order_count": self.order_count,
            "revenue": self.revenue,
            "markup_percentage": self.markup_percentage,
        }


class MedusaStorefront:
    """
    High-level Medusa storefront manager.

    Manages niche storefronts and product synchronization
    with the master Shopify catalog.
    """

    def __init__(
        self,
        credentials: Optional[MedusaCredentials] = None,
    ):
        self.client = MedusaClient(credentials) if credentials else None
        self._niche_storefronts: Dict[str, NicheStorefront] = {}
        self._init_niche_storefronts()

    def _init_niche_storefronts(self) -> None:
        """Initialize niche storefront definitions."""
        for key, config in NICHE_STOREFRONTS.items():
            self._niche_storefronts[key] = NicheStorefront(
                key=key,
                name=config["name"],
                description=config["description"],
                url=config["url"],
                segments=config["segments"],
                product_filters=config["product_filters"],
            )

    def get_niche_storefront(self, key: str) -> Optional[NicheStorefront]:
        """Get a niche storefront by key."""
        return self._niche_storefronts.get(key)

    def list_niche_storefronts(self) -> List[NicheStorefront]:
        """List all niche storefronts."""
        return list(self._niche_storefronts.values())

    def filter_products_for_storefront(
        self,
        storefront_key: str,
        products: List[Product],
    ) -> List[Product]:
        """Filter products for a specific niche storefront."""
        storefront = self._niche_storefronts.get(storefront_key)
        if not storefront:
            return []

        matching = [p for p in products if storefront.matches_product(p)]
        storefront.product_count = len(matching)
        return matching

    def get_storefront_product_summary(
        self,
        products: List[Product],
    ) -> Dict[str, Dict[str, Any]]:
        """Get product summary for all niche storefronts."""
        summary = {}

        for key, storefront in self._niche_storefronts.items():
            matching = self.filter_products_for_storefront(key, products)

            summary[key] = {
                "name": storefront.name,
                "product_count": len(matching),
                "segments": storefront.segments,
                "sample_products": [{"title": p.title, "price": p.price} for p in matching[:3]],
            }

        return summary

    async def sync_products_to_medusa(
        self,
        products: List[Product],
        storefront_key: str,
    ) -> Dict[str, Any]:
        """
        Sync products to a Medusa storefront.

        Args:
            products: Products to sync
            storefront_key: Target niche storefront

        Returns:
            Sync results
        """
        if not self.client:
            return {"error": "Medusa client not configured"}

        storefront = self._niche_storefronts.get(storefront_key)
        if not storefront:
            return {"error": f"Unknown storefront: {storefront_key}"}

        # Filter products for this storefront
        filtered = self.filter_products_for_storefront(storefront_key, products)

        synced = 0
        errors = 0

        for product in filtered:
            # Apply storefront markup
            adjusted_price = product.price * (1 + storefront.markup_percentage / 100)

            # Prepare Medusa product data
            medusa_data = {
                "title": product.title,
                "handle": product.handle,
                "description": product.description,
                "status": "published" if product.published else "draft",
                "metadata": {
                    "source_platform": "shopify",
                    "source_id": product.platform_id,
                    "storefront": storefront_key,
                },
                "variants": [
                    {
                        "title": v.title,
                        "sku": v.sku,
                        "prices": [{"amount": int(adjusted_price * 100), "currency_code": "usd"}],
                        "inventory_quantity": v.inventory_quantity,
                    }
                    for v in product.variants
                ],
            }

            result = self.client.create_product(medusa_data)
            if result:
                synced += 1
            else:
                errors += 1

        return {
            "storefront": storefront_key,
            "products_filtered": len(filtered),
            "products_synced": synced,
            "errors": errors,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_architecture_summary(self) -> Dict[str, Any]:
        """Get summary of the multi-storefront architecture."""
        return {
            "architecture": {
                "fulfillment_hub": "Shopify (Cirrus1)",
                "backend": "Medusa",
                "niche_storefronts": len(self._niche_storefronts),
                "future": ["TikTok Shop"],
            },
            "storefronts": {
                key: {
                    "name": sf.name,
                    "segments": sf.segments,
                    "status": sf.status.value,
                    "product_count": sf.product_count,
                }
                for key, sf in self._niche_storefronts.items()
            },
            "total_capacity": "10 storefronts on Zendrop Plus",
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get storefront statistics."""
        storefronts = self.list_niche_storefronts()
        return {
            "total_niche_storefronts": len(storefronts),
            "active_storefronts": len(
                [s for s in storefronts if s.status == StorefrontStatus.ACTIVE]
            ),
            "total_products_across_niches": sum(s.product_count for s in storefronts),
            "total_revenue": sum(s.revenue for s in storefronts),
            "segments_covered": list(set(seg for sf in storefronts for seg in sf.segments)),
        }
