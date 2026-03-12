"""
E-Commerce Bridge - Integration between ag3ntwerk and E-Commerce platforms.

This module provides a bridge connecting ag3ntwerk agents to:
- Shopify Manager (multi-storefront management)
- Medusa Backend (e-commerce operations)

Primary users:
- Axiom (Axiom): Revenue operations, pricing strategy, market analysis
- Echo (Echo): Campaign creation, customer segmentation
- Keystone (Ledger): Financial analysis, margin optimization

Features:
- Multi-storefront product management
- Pricing and margin analysis
- Inventory tracking
- Sales analytics
- Customer segmentation
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class StorefrontPlatform(Enum):
    """Supported e-commerce platforms."""

    SHOPIFY = "shopify"
    MEDUSA = "medusa"


class PricingStrategy(Enum):
    """Pricing strategies for products."""

    COST_PLUS = "cost_plus"
    COMPETITIVE = "competitive"
    VALUE_BASED = "value_based"
    DYNAMIC = "dynamic"
    LOSS_LEADER = "loss_leader"
    PREMIUM = "premium"


class InventoryStatus(Enum):
    """Inventory status levels."""

    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    BACKORDERED = "backordered"
    DISCONTINUED = "discontinued"


@dataclass
class ProductInfo:
    """Product information from e-commerce platform."""

    id: str
    platform: StorefrontPlatform
    storefront_key: str
    title: str
    handle: str
    price: float
    compare_at_price: Optional[float] = None
    cost: Optional[float] = None
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    inventory_quantity: int = 0
    inventory_status: InventoryStatus = InventoryStatus.IN_STOCK
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def margin(self) -> Optional[float]:
        """Calculate profit margin if cost is known."""
        if self.cost and self.cost > 0 and self.price > 0:
            return ((self.price - self.cost) / self.price) * 100
        return None

    @property
    def markup(self) -> Optional[float]:
        """Calculate markup percentage if cost is known."""
        if self.cost and self.cost > 0:
            return ((self.price - self.cost) / self.cost) * 100
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "platform": self.platform.value,
            "storefront_key": self.storefront_key,
            "title": self.title,
            "handle": self.handle,
            "price": self.price,
            "compare_at_price": self.compare_at_price,
            "cost": self.cost,
            "vendor": self.vendor,
            "product_type": self.product_type,
            "tags": self.tags,
            "inventory_quantity": self.inventory_quantity,
            "inventory_status": self.inventory_status.value,
            "margin": self.margin,
            "markup": self.markup,
        }


@dataclass
class PricingRecommendation:
    """Pricing recommendation for a product."""

    product_id: str
    current_price: float
    recommended_price: float
    strategy: PricingStrategy
    target_margin: float
    expected_margin: float
    reasoning: str
    confidence: float = 0.8
    competitive_context: Optional[Dict[str, Any]] = None

    @property
    def price_change_pct(self) -> float:
        """Calculate percentage change in price."""
        if self.current_price > 0:
            return ((self.recommended_price - self.current_price) / self.current_price) * 100
        return 0.0


@dataclass
class StorefrontAnalytics:
    """Analytics for a storefront."""

    storefront_key: str
    platform: StorefrontPlatform
    total_products: int = 0
    active_products: int = 0
    out_of_stock_products: int = 0
    avg_price: float = 0.0
    avg_margin: Optional[float] = None
    total_inventory_value: float = 0.0
    products_needing_attention: int = 0
    low_margin_products: int = 0
    high_margin_products: int = 0
    price_distribution: Dict[str, int] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ECommerceBridge:
    """
    Bridge between ag3ntwerk agents and e-commerce platforms.

    This bridge enables:
    1. Axiom - Revenue optimization, pricing strategy
    2. Echo - Campaign and segmentation support
    3. Keystone - Financial analysis and margin tracking

    Usage:
        bridge = ECommerceBridge()
        bridge.connect_platform("main_store", StorefrontPlatform.SHOPIFY, client)

        # Get product analytics
        analytics = await bridge.get_storefront_analytics("main_store")

        # Get pricing recommendations
        recommendations = await bridge.get_pricing_recommendations(
            "main_store",
            target_margin=40.0
        )
    """

    # Default target margins by category
    CATEGORY_TARGET_MARGINS = {
        "apparel": 50.0,
        "electronics": 25.0,
        "accessories": 60.0,
        "home_goods": 45.0,
        "consumables": 35.0,
        "default": 40.0,
    }

    # Price tier thresholds
    PRICE_TIERS = {
        "budget": (0, 25),
        "mid_range": (25, 75),
        "premium": (75, 150),
        "luxury": (150, float("inf")),
    }

    def __init__(
        self,
        cro: Optional[Any] = None,
        cmo: Optional[Any] = None,
        cfo: Optional[Any] = None,
    ):
        """
        Initialize the E-Commerce bridge.

        Args:
            cro: Optional Vector instance
            cmo: Optional Echo instance
            cfo: Optional Keystone instance
        """
        self._cro = cro
        self._cmo = cmo
        self._cfo = cfo

        # Platform connections
        self._platforms: Dict[str, Dict[str, Any]] = {}

        # Product cache
        self._product_cache: Dict[str, Dict[str, ProductInfo]] = {}
        self._cache_ttl_seconds = 300  # 5 minutes
        self._cache_timestamps: Dict[str, datetime] = {}

        # Analytics cache
        self._analytics_cache: Dict[str, StorefrontAnalytics] = {}

        # Metrics
        self._metrics = {
            "products_analyzed": 0,
            "recommendations_generated": 0,
            "price_updates_suggested": 0,
            "total_potential_revenue_gain": 0.0,
        }

        logger.info("ECommerceBridge initialized")

    def connect_platform(
        self,
        storefront_key: str,
        platform: StorefrontPlatform,
        client: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Connect an e-commerce platform.

        Args:
            storefront_key: Unique identifier for this storefront
            platform: Platform type (Shopify, Medusa)
            client: Platform client instance
            config: Optional platform-specific configuration
        """
        self._platforms[storefront_key] = {
            "platform": platform,
            "client": client,
            "config": config or {},
            "connected_at": datetime.now(timezone.utc),
        }
        logger.info(f"Connected {platform.value} storefront: {storefront_key}")

    def connect_executives(
        self,
        cro: Any = None,
        cmo: Any = None,
        cfo: Any = None,
    ) -> None:
        """Connect ag3ntwerk agents to the bridge."""
        if cro:
            self._cro = cro
            logger.info("Connected Axiom (Axiom) to e-commerce bridge")
        if cmo:
            self._cmo = cmo
            logger.info("Connected Echo (Echo) to e-commerce bridge")
        if cfo:
            self._cfo = cfo
            logger.info("Connected Keystone (Ledger) to e-commerce bridge")

    def list_storefronts(self) -> List[Dict[str, Any]]:
        """List all connected storefronts."""
        return [
            {
                "key": key,
                "platform": info["platform"].value,
                "connected_at": info["connected_at"].isoformat(),
            }
            for key, info in self._platforms.items()
        ]

    async def get_products(
        self,
        storefront_key: str,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> List[ProductInfo]:
        """
        Get products from a storefront.

        Args:
            storefront_key: Storefront identifier
            limit: Maximum products to return
            filters: Optional filters (vendor, product_type, etc.)
            use_cache: Whether to use cached data

        Returns:
            List of ProductInfo objects
        """
        if storefront_key not in self._platforms:
            raise ValueError(f"Unknown storefront: {storefront_key}")

        # Check cache
        if use_cache and self._is_cache_valid(storefront_key):
            products = list(self._product_cache.get(storefront_key, {}).values())
            return self._apply_filters(products[:limit], filters)

        platform_info = self._platforms[storefront_key]
        platform = platform_info["platform"]
        client = platform_info["client"]

        products = []

        if platform == StorefrontPlatform.SHOPIFY:
            products = await self._fetch_shopify_products(client, storefront_key, limit)
        elif platform == StorefrontPlatform.MEDUSA:
            products = await self._fetch_medusa_products(client, storefront_key, limit)

        # Update cache
        self._product_cache[storefront_key] = {p.id: p for p in products}
        self._cache_timestamps[storefront_key] = datetime.now(timezone.utc)

        self._metrics["products_analyzed"] += len(products)

        return self._apply_filters(products, filters)

    async def _fetch_shopify_products(
        self,
        client: Any,
        storefront_key: str,
        limit: int,
    ) -> List[ProductInfo]:
        """Fetch products from Shopify."""
        products = []

        try:
            # Call Shopify client
            raw_products = client.get_products(limit=limit)

            for p in raw_products:
                # Get first variant for pricing (handle empty list case)
                variants = p.get("variants") or []
                variant = variants[0] if variants else {}

                inventory_qty = variant.get("inventory_quantity", 0)
                status = InventoryStatus.IN_STOCK
                if inventory_qty <= 0:
                    status = InventoryStatus.OUT_OF_STOCK
                elif inventory_qty < 10:
                    status = InventoryStatus.LOW_STOCK

                products.append(
                    ProductInfo(
                        id=str(p.get("id", "")),
                        platform=StorefrontPlatform.SHOPIFY,
                        storefront_key=storefront_key,
                        title=p.get("title", ""),
                        handle=p.get("handle", ""),
                        price=float(variant.get("price", 0)),
                        compare_at_price=float(variant.get("compare_at_price") or 0) or None,
                        cost=float(
                            variant.get("cost")
                            or variant.get("inventory_item", {}).get("cost")
                            or 0
                        )
                        or None,
                        vendor=p.get("vendor"),
                        product_type=p.get("product_type"),
                        tags=p.get("tags", "").split(", ") if p.get("tags") else [],
                        inventory_quantity=inventory_qty,
                        inventory_status=status,
                        created_at=p.get("created_at"),
                        updated_at=p.get("updated_at"),
                    )
                )
        except Exception as e:
            logger.error(f"Error fetching Shopify products: {e}")

        return products

    async def _fetch_medusa_products(
        self,
        client: Any,
        storefront_key: str,
        limit: int,
    ) -> List[ProductInfo]:
        """Fetch products from Medusa."""
        products = []

        try:
            # Call Medusa client
            raw_products = client.list_products(limit=limit)

            for p in raw_products.get("products", []):
                # Get first variant (handle empty list case)
                variants = p.get("variants") or []
                variant = variants[0] if variants else {}

                # Get first price (handle empty list case)
                prices = variant.get("prices") or []
                first_price = prices[0] if prices else {}

                products.append(
                    ProductInfo(
                        id=str(p.get("id", "")),
                        platform=StorefrontPlatform.MEDUSA,
                        storefront_key=storefront_key,
                        title=p.get("title", ""),
                        handle=p.get("handle", ""),
                        price=float(first_price.get("amount", 0)) / 100,
                        vendor=p.get("vendor"),
                        product_type=p.get("type", {}).get("value"),
                        tags=p.get("tags", []),
                        inventory_quantity=variant.get("inventory_quantity", 0),
                    )
                )
        except Exception as e:
            logger.error(f"Error fetching Medusa products: {e}")

        return products

    def _is_cache_valid(self, storefront_key: str) -> bool:
        """Check if cache is still valid."""
        if storefront_key not in self._cache_timestamps:
            return False

        age = datetime.now(timezone.utc) - self._cache_timestamps[storefront_key]
        return age.total_seconds() < self._cache_ttl_seconds

    def _apply_filters(
        self,
        products: List[ProductInfo],
        filters: Optional[Dict[str, Any]],
    ) -> List[ProductInfo]:
        """Apply filters to product list."""
        if not filters:
            return products

        result = products

        if "vendor" in filters:
            result = [p for p in result if p.vendor == filters["vendor"]]
        if "product_type" in filters:
            result = [p for p in result if p.product_type == filters["product_type"]]
        if "min_price" in filters:
            result = [p for p in result if p.price >= filters["min_price"]]
        if "max_price" in filters:
            result = [p for p in result if p.price <= filters["max_price"]]
        if "in_stock" in filters and filters["in_stock"]:
            result = [p for p in result if p.inventory_status == InventoryStatus.IN_STOCK]
        if "has_cost" in filters and filters["has_cost"]:
            result = [p for p in result if p.cost is not None]

        return result

    async def get_storefront_analytics(
        self,
        storefront_key: str,
    ) -> StorefrontAnalytics:
        """
        Get analytics for a storefront.

        Args:
            storefront_key: Storefront identifier

        Returns:
            StorefrontAnalytics with key metrics
        """
        products = await self.get_products(storefront_key, limit=1000)

        if not products:
            return StorefrontAnalytics(
                storefront_key=storefront_key,
                platform=self._platforms[storefront_key]["platform"],
            )

        # Calculate metrics
        total = len(products)
        active = len([p for p in products if p.inventory_status != InventoryStatus.DISCONTINUED])
        out_of_stock = len(
            [p for p in products if p.inventory_status == InventoryStatus.OUT_OF_STOCK]
        )

        prices = [p.price for p in products if p.price > 0]
        avg_price = sum(prices) / len(prices) if prices else 0.0

        margins = [p.margin for p in products if p.margin is not None]
        avg_margin = sum(margins) / len(margins) if margins else None

        # Count products by margin category
        low_margin = len([p for p in products if p.margin is not None and p.margin < 20])
        high_margin = len([p for p in products if p.margin is not None and p.margin > 50])

        # Price distribution
        price_dist = {tier: 0 for tier in self.PRICE_TIERS}
        for p in products:
            for tier, (low, high) in self.PRICE_TIERS.items():
                if low <= p.price < high:
                    price_dist[tier] += 1
                    break

        # Products needing attention (low stock, no cost, etc.)
        attention = len(
            [
                p
                for p in products
                if p.inventory_status == InventoryStatus.LOW_STOCK
                or p.cost is None
                or (p.margin is not None and p.margin < 10)
            ]
        )

        # Total inventory value
        inventory_value = sum(
            p.cost * p.inventory_quantity for p in products if p.cost and p.inventory_quantity > 0
        )

        analytics = StorefrontAnalytics(
            storefront_key=storefront_key,
            platform=self._platforms[storefront_key]["platform"],
            total_products=total,
            active_products=active,
            out_of_stock_products=out_of_stock,
            avg_price=avg_price,
            avg_margin=avg_margin,
            total_inventory_value=inventory_value,
            products_needing_attention=attention,
            low_margin_products=low_margin,
            high_margin_products=high_margin,
            price_distribution=price_dist,
        )

        self._analytics_cache[storefront_key] = analytics
        return analytics

    async def get_pricing_recommendations(
        self,
        storefront_key: str,
        target_margin: Optional[float] = None,
        strategy: PricingStrategy = PricingStrategy.COST_PLUS,
        product_ids: Optional[List[str]] = None,
    ) -> List[PricingRecommendation]:
        """
        Get pricing recommendations for products.

        Args:
            storefront_key: Storefront identifier
            target_margin: Target profit margin percentage
            strategy: Pricing strategy to use
            product_ids: Optional list of specific products

        Returns:
            List of PricingRecommendation objects
        """
        products = await self.get_products(
            storefront_key,
            filters={"has_cost": True},
        )

        if product_ids:
            products = [p for p in products if p.id in product_ids]

        recommendations = []

        for product in products:
            if product.cost is None or product.cost <= 0:
                continue

            # Determine target margin
            category = self._get_product_category(product)
            tm = target_margin or self.CATEGORY_TARGET_MARGINS.get(
                category,
                self.CATEGORY_TARGET_MARGINS["default"],
            )

            # Calculate recommended price based on strategy
            if strategy == PricingStrategy.COST_PLUS:
                # Price = Cost / (1 - margin)
                recommended = product.cost / (1 - tm / 100)
            elif strategy == PricingStrategy.COMPETITIVE:
                # Use compare_at_price or add standard markup
                if product.compare_at_price:
                    recommended = product.compare_at_price * 0.95
                else:
                    recommended = product.cost * 1.5
            elif strategy == PricingStrategy.VALUE_BASED:
                # Premium on top of cost-plus
                base = product.cost / (1 - tm / 100)
                recommended = base * 1.2
            elif strategy == PricingStrategy.LOSS_LEADER:
                # Minimal margin
                recommended = product.cost * 1.1
            elif strategy == PricingStrategy.PREMIUM:
                # High margin
                recommended = product.cost / (1 - 0.6)
            else:
                recommended = product.cost / (1 - tm / 100)

            # Round to nice price point
            recommended = self._round_to_price_point(recommended)

            # Calculate expected margin
            expected_margin = ((recommended - product.cost) / recommended) * 100

            # Skip if no meaningful change
            if abs(recommended - product.price) < 1.0:
                continue

            reasoning = self._generate_pricing_reasoning(
                product, recommended, strategy, tm, expected_margin
            )

            recommendations.append(
                PricingRecommendation(
                    product_id=product.id,
                    current_price=product.price,
                    recommended_price=recommended,
                    strategy=strategy,
                    target_margin=tm,
                    expected_margin=expected_margin,
                    reasoning=reasoning,
                )
            )

        self._metrics["recommendations_generated"] += len(recommendations)
        self._metrics["price_updates_suggested"] += len(recommendations)

        # Calculate potential revenue gain
        potential_gain = sum(
            r.recommended_price - r.current_price
            for r in recommendations
            if r.recommended_price > r.current_price
        )
        self._metrics["total_potential_revenue_gain"] += potential_gain

        return recommendations

    def _get_product_category(self, product: ProductInfo) -> str:
        """Determine product category for margin targeting."""
        pt = (product.product_type or "").lower()

        if any(t in pt for t in ["shirt", "pants", "dress", "apparel", "clothing"]):
            return "apparel"
        if any(t in pt for t in ["electronic", "tech", "gadget", "phone"]):
            return "electronics"
        if any(t in pt for t in ["accessory", "jewelry", "watch", "bag"]):
            return "accessories"
        if any(t in pt for t in ["home", "decor", "furniture"]):
            return "home_goods"

        return "default"

    def _round_to_price_point(self, price: float) -> float:
        """Round price to a nice price point."""
        if price < 10:
            return round(price, 2)
        if price < 50:
            # Round to .99 or .95
            return round(price) - 0.01
        if price < 100:
            # Round to nearest 5 - 1
            return round(price / 5) * 5 - 1
        # Round to nearest 10 - 1
        return round(price / 10) * 10 - 1

    def _generate_pricing_reasoning(
        self,
        product: ProductInfo,
        recommended: float,
        strategy: PricingStrategy,
        target_margin: float,
        expected_margin: float,
    ) -> str:
        """Generate reasoning for pricing recommendation."""
        change_pct = ((recommended - product.price) / product.price) * 100
        direction = "increase" if change_pct > 0 else "decrease"

        return (
            f"{strategy.value.replace('_', ' ').title()} strategy suggests "
            f"{direction} of {abs(change_pct):.1f}% to achieve "
            f"{expected_margin:.1f}% margin (target: {target_margin:.1f}%). "
            f"Current margin: {product.margin:.1f}%."
            if product.margin
            else f"{strategy.value.replace('_', ' ').title()} strategy suggests "
            f"price of ${recommended:.2f}."
        )

    async def get_inventory_alerts(
        self,
        storefront_key: str,
        low_stock_threshold: int = 10,
    ) -> Dict[str, Any]:
        """
        Get inventory alerts for a storefront.

        Args:
            storefront_key: Storefront identifier
            low_stock_threshold: Threshold for low stock warning

        Returns:
            Dictionary with inventory alerts
        """
        products = await self.get_products(storefront_key, limit=1000)

        out_of_stock = [p for p in products if p.inventory_quantity <= 0]
        low_stock = [p for p in products if 0 < p.inventory_quantity <= low_stock_threshold]

        return {
            "storefront_key": storefront_key,
            "out_of_stock_count": len(out_of_stock),
            "out_of_stock_products": [
                {"id": p.id, "title": p.title, "vendor": p.vendor} for p in out_of_stock[:20]
            ],
            "low_stock_count": len(low_stock),
            "low_stock_products": [
                {
                    "id": p.id,
                    "title": p.title,
                    "quantity": p.inventory_quantity,
                    "vendor": p.vendor,
                }
                for p in low_stock[:20]
            ],
            "threshold": low_stock_threshold,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_margin_analysis(
        self,
        storefront_key: str,
    ) -> Dict[str, Any]:
        """
        Get comprehensive margin analysis for a storefront.

        Args:
            storefront_key: Storefront identifier

        Returns:
            Dictionary with margin analysis
        """
        products = await self.get_products(
            storefront_key,
            filters={"has_cost": True},
        )

        if not products:
            return {
                "storefront_key": storefront_key,
                "error": "No products with cost data found",
            }

        # Categorize by margin
        negative_margin = [p for p in products if p.margin is not None and p.margin < 0]
        low_margin = [p for p in products if p.margin is not None and 0 <= p.margin < 20]
        mid_margin = [p for p in products if p.margin is not None and 20 <= p.margin < 40]
        good_margin = [p for p in products if p.margin is not None and 40 <= p.margin < 60]
        high_margin = [p for p in products if p.margin is not None and p.margin >= 60]

        margins = [p.margin for p in products if p.margin is not None]

        return {
            "storefront_key": storefront_key,
            "total_products_with_cost": len(products),
            "margin_distribution": {
                "negative_margin": len(negative_margin),
                "low_margin_0_20": len(low_margin),
                "mid_margin_20_40": len(mid_margin),
                "good_margin_40_60": len(good_margin),
                "high_margin_60_plus": len(high_margin),
            },
            "statistics": {
                "avg_margin": sum(margins) / len(margins) if margins else 0,
                "min_margin": min(margins) if margins else 0,
                "max_margin": max(margins) if margins else 0,
            },
            "products_losing_money": [
                {"id": p.id, "title": p.title, "margin": p.margin} for p in negative_margin[:10]
            ],
            "top_margin_products": [
                {"id": p.id, "title": p.title, "margin": p.margin}
                for p in sorted(products, key=lambda x: x.margin or 0, reverse=True)[:10]
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_products_for_cro(
        self,
        storefront_key: str,
    ) -> Dict[str, Any]:
        """
        Get product data formatted for Axiom revenue analysis.

        Args:
            storefront_key: Storefront identifier

        Returns:
            Data structured for Axiom consumption
        """
        analytics = await self.get_storefront_analytics(storefront_key)
        margin_analysis = await self.get_margin_analysis(storefront_key)
        inventory_alerts = await self.get_inventory_alerts(storefront_key)

        return {
            "storefront_key": storefront_key,
            "summary": {
                "total_products": analytics.total_products,
                "active_products": analytics.active_products,
                "avg_price": analytics.avg_price,
                "avg_margin": analytics.avg_margin,
                "inventory_value": analytics.total_inventory_value,
            },
            "margin_analysis": margin_analysis,
            "inventory_alerts": inventory_alerts,
            "price_distribution": analytics.price_distribution,
            "recommendations": {
                "low_margin_products": margin_analysis.get("margin_distribution", {}).get(
                    "low_margin_0_20", 0
                ),
                "needs_pricing_review": analytics.products_needing_attention,
                "out_of_stock": inventory_alerts.get("out_of_stock_count", 0),
            },
        }

    async def get_segments_for_cmo(
        self,
        storefront_key: str,
    ) -> Dict[str, Any]:
        """
        Get customer segmentation data for Echo marketing campaigns.

        Args:
            storefront_key: Storefront identifier

        Returns:
            Data structured for Echo consumption
        """
        products = await self.get_products(storefront_key, limit=1000)
        analytics = await self.get_storefront_analytics(storefront_key)

        # Group by price tier
        tiers = {tier: [] for tier in self.PRICE_TIERS}
        for p in products:
            for tier, (low, high) in self.PRICE_TIERS.items():
                if low <= p.price < high:
                    tiers[tier].append(p.to_dict())
                    break

        # Group by vendor
        vendors: Dict[str, List[Dict]] = {}
        for p in products:
            if p.vendor:
                if p.vendor not in vendors:
                    vendors[p.vendor] = []
                vendors[p.vendor].append(p.to_dict())

        # Group by product type
        types: Dict[str, List[Dict]] = {}
        for p in products:
            if p.product_type:
                if p.product_type not in types:
                    types[p.product_type] = []
                types[p.product_type].append(p.to_dict())

        return {
            "storefront_key": storefront_key,
            "price_segments": {
                tier: {
                    "count": len(prods),
                    "avg_price": sum(p["price"] for p in prods) / len(prods) if prods else 0,
                    "sample_products": prods[:5],
                }
                for tier, prods in tiers.items()
            },
            "vendor_segments": {
                vendor: {
                    "count": len(prods),
                    "sample_products": prods[:3],
                }
                for vendor, prods in list(vendors.items())[:10]
            },
            "type_segments": {
                ptype: {
                    "count": len(prods),
                    "sample_products": prods[:3],
                }
                for ptype, prods in list(types.items())[:10]
            },
            "campaign_opportunities": {
                "premium_products": analytics.price_distribution.get("premium", 0)
                + analytics.price_distribution.get("luxury", 0),
                "budget_friendly": analytics.price_distribution.get("budget", 0),
                "high_margin_for_promotion": analytics.high_margin_products,
            },
        }

    def clear_cache(self, storefront_key: Optional[str] = None) -> None:
        """Clear product cache."""
        if storefront_key:
            self._product_cache.pop(storefront_key, None)
            self._cache_timestamps.pop(storefront_key, None)
            self._analytics_cache.pop(storefront_key, None)
        else:
            self._product_cache.clear()
            self._cache_timestamps.clear()
            self._analytics_cache.clear()
        logger.info(
            f"Cleared cache for {'all storefronts' if not storefront_key else storefront_key}"
        )

    @property
    def stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "connected_storefronts": len(self._platforms),
            "cro_connected": self._cro is not None,
            "cmo_connected": self._cmo is not None,
            "cfo_connected": self._cfo is not None,
            "cached_products": sum(len(p) for p in self._product_cache.values()),
            **self._metrics,
        }
