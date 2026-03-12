"""
Commerce Operations Module.

Provides multi-storefront management including Shopify and Medusa integration
for ag3ntwerk agents. Enables pricing optimization, inventory control,
and sales analytics.

Primary Owners: Axiom (Axiom), Keystone (Ledger)
Secondary Owners: Echo (Echo), Nexus (Conductor)
"""

from ag3ntwerk.modules.commerce.core import (
    StorefrontPlatform,
    StorefrontStatus,
    PricingStrategy,
    InventoryStatus,
    Product,
    ProductVariant,
    Collection,
    Order,
    Storefront,
)
from ag3ntwerk.modules.commerce.shopify import (
    ShopifyClient,
    ShopifyStorefront,
)
from ag3ntwerk.modules.commerce.medusa import (
    MedusaClient,
    MedusaStorefront,
    NicheStorefront,
)
from ag3ntwerk.modules.commerce.pricing import (
    PricingEngine,
    PricingRecommendation,
    MarginAnalyzer,
)
from ag3ntwerk.modules.commerce.service import CommerceService

__all__ = [
    # Core
    "StorefrontPlatform",
    "StorefrontStatus",
    "PricingStrategy",
    "InventoryStatus",
    "Product",
    "ProductVariant",
    "Collection",
    "Order",
    "Storefront",
    # Shopify
    "ShopifyClient",
    "ShopifyStorefront",
    # Medusa
    "MedusaClient",
    "MedusaStorefront",
    "NicheStorefront",
    # Pricing
    "PricingEngine",
    "PricingRecommendation",
    "MarginAnalyzer",
    # Service
    "CommerceService",
]
