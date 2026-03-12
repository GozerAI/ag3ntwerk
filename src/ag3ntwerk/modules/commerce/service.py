"""
Commerce Service - High-level service interface for agents.

Provides a unified API for ag3ntwerk agents to interact with
multi-storefront commerce operations.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.modules.commerce.core import (
    StorefrontPlatform,
    StorefrontStatus,
    PricingStrategy,
    Product,
    Storefront,
    StorefrontRegistry,
)
from ag3ntwerk.modules.commerce.shopify import (
    ShopifyClient,
    ShopifyCredentials,
    ShopifyStorefront,
)
from ag3ntwerk.modules.commerce.medusa import (
    MedusaClient,
    MedusaCredentials,
    MedusaStorefront,
    NicheStorefront,
)
from ag3ntwerk.modules.commerce.pricing import (
    PricingEngine,
    PricingRecommendation,
    MarginAnalyzer,
)

logger = logging.getLogger(__name__)


class CommerceService:
    """
    High-level commerce service for ag3ntwerk agents.

    This service provides a unified interface for:
    - Axiom (Axiom): Revenue optimization, pricing strategy
    - Keystone (Ledger): Margin analysis, financial metrics
    - Echo (Echo): Product segmentation, campaign support
    - Nexus (Conductor): Operations oversight, inventory management

    Example:
        ```python
        service = CommerceService()

        # Connect Shopify storefront
        service.connect_shopify(
            key="main_store",
            store_url="mystore.myshopify.com",
            access_token="shpat_xxxxx",
        )

        # Get revenue report for Axiom
        report = await service.get_agent_report("Axiom")

        # Optimize pricing
        recommendations = await service.optimize_pricing("main_store")
        ```
    """

    def __init__(self):
        """Initialize the commerce service."""
        self._registry = StorefrontRegistry()
        self._shopify_clients: Dict[str, ShopifyStorefront] = {}
        self._medusa = MedusaStorefront()
        self._pricing_engine = PricingEngine()
        self._margin_analyzer = MarginAnalyzer()

        self._initialized = False
        self._last_sync: Optional[datetime] = None

    def connect_shopify(
        self,
        key: str,
        store_url: str,
        access_token: str,
        name: Optional[str] = None,
        api_version: str = "2024-01",
    ) -> bool:
        """
        Connect a Shopify storefront.

        Args:
            key: Unique identifier for this storefront
            store_url: Shopify store URL (e.g., mystore.myshopify.com)
            access_token: Shopify Admin API access token
            name: Display name for the storefront
            api_version: Shopify API version

        Returns:
            True if connection successful
        """
        try:
            credentials = ShopifyCredentials(
                store_url=store_url,
                access_token=access_token,
                api_version=api_version,
            )

            storefront = Storefront(
                key=key,
                name=name or key,
                platform=StorefrontPlatform.SHOPIFY,
                store_url=store_url,
                api_version=api_version,
            )

            self._shopify_clients[key] = ShopifyStorefront(storefront, credentials)
            self._registry.register(storefront)

            logger.info(f"Connected Shopify storefront: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect Shopify: {e}")
            return False

    def connect_medusa(
        self,
        base_url: str,
        api_key: Optional[str] = None,
    ) -> bool:
        """
        Connect Medusa backend.

        Args:
            base_url: Medusa API base URL
            api_key: Optional API key

        Returns:
            True if connection successful
        """
        try:
            credentials = MedusaCredentials(
                base_url=base_url,
                api_key=api_key,
            )
            self._medusa = MedusaStorefront(credentials)

            # Register niche storefronts
            for sf in self._medusa.list_niche_storefronts():
                storefront = Storefront(
                    key=sf.key,
                    name=sf.name,
                    platform=StorefrontPlatform.MEDUSA,
                    storefront_type="niche",
                    segments=sf.segments,
                )
                self._registry.register(storefront)

            logger.info("Connected Medusa backend")
            return True

        except Exception as e:
            logger.error(f"Failed to connect Medusa: {e}")
            return False

    async def get_products(
        self,
        storefront_key: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get products from a storefront."""
        if storefront_key in self._shopify_clients:
            products = await self._shopify_clients[storefront_key].get_products(limit=limit)
            return [p.to_dict() for p in products]

        # Check if it's a Medusa niche storefront
        niche = self._medusa.get_niche_storefront(storefront_key)
        if niche:
            # Get products from master Shopify and filter
            master = self._shopify_clients.get("cirrus1") or next(
                iter(self._shopify_clients.values()), None
            )
            if master:
                all_products = await master.get_products(limit=500)
                filtered = self._medusa.filter_products_for_storefront(storefront_key, all_products)
                return [p.to_dict() for p in filtered]

        return []

    async def get_storefront_analytics(self, storefront_key: str) -> Dict[str, Any]:
        """Get analytics for a storefront."""
        if storefront_key in self._shopify_clients:
            return await self._shopify_clients[storefront_key].get_analytics()

        return {"error": f"Storefront not found: {storefront_key}"}

    async def get_all_analytics(self) -> Dict[str, Any]:
        """Get analytics across all storefronts."""
        analytics = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "storefronts": {},
            "totals": {
                "total_products": 0,
                "total_inventory": 0,
                "total_inventory_value": 0,
            },
        }

        for key, client in self._shopify_clients.items():
            try:
                sf_analytics = await client.get_analytics()
                analytics["storefronts"][key] = sf_analytics
                analytics["totals"]["total_products"] += sf_analytics.get("total_products", 0)
                analytics["totals"]["total_inventory"] += sf_analytics.get("total_inventory", 0)
                analytics["totals"]["total_inventory_value"] += sf_analytics.get(
                    "inventory_value", 0
                )
            except Exception as e:
                logger.error(f"Failed to get analytics for {key}: {e}")
                analytics["storefronts"][key] = {"error": str(e)}

        # Add Medusa stats
        analytics["medusa"] = self._medusa.get_stats()

        return analytics

    async def optimize_pricing(
        self,
        storefront_key: str,
        target_margin: float = 40.0,
        strategy: str = "cost_plus",
    ) -> Dict[str, Any]:
        """
        Get pricing optimization recommendations.

        Args:
            storefront_key: Storefront to optimize
            target_margin: Target margin percentage
            strategy: Pricing strategy (cost_plus, competitive, value_based, etc.)

        Returns:
            Pricing recommendations
        """
        if storefront_key not in self._shopify_clients:
            return {"error": f"Storefront not found: {storefront_key}"}

        products = await self._shopify_clients[storefront_key].get_products()

        strategy_map = {
            "cost_plus": PricingStrategy.COST_PLUS,
            "competitive": PricingStrategy.COMPETITIVE,
            "value_based": PricingStrategy.VALUE_BASED,
            "premium": PricingStrategy.PREMIUM,
            "penetration": PricingStrategy.PENETRATION,
        }
        pricing_strategy = strategy_map.get(strategy, PricingStrategy.COST_PLUS)

        recommendations = self._pricing_engine.generate_recommendations(
            products,
            target_margin=target_margin,
            strategy=pricing_strategy,
        )

        return {
            "storefront": storefront_key,
            "strategy": strategy,
            "target_margin": target_margin,
            "products_analyzed": len(products),
            "recommendations_count": len(recommendations),
            "recommendations": [r.to_dict() for r in recommendations[:20]],
            "summary": self._pricing_engine.get_pricing_summary(products),
        }

    async def get_margin_analysis(
        self,
        storefront_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get margin analysis for a storefront or all storefronts."""
        if storefront_key:
            if storefront_key not in self._shopify_clients:
                return {"error": f"Storefront not found: {storefront_key}"}

            products = await self._shopify_clients[storefront_key].get_products()
            analysis = self._margin_analyzer.analyze_portfolio(products, storefront_key)
            return analysis.to_dict()

        # Analyze all storefronts
        all_products = []
        for key, client in self._shopify_clients.items():
            products = await client.get_products()
            all_products.extend(products)

        analysis = self._margin_analyzer.analyze_portfolio(all_products, "All Storefronts")
        return analysis.to_dict()

    async def get_inventory_alerts(
        self,
        low_stock_threshold: int = 10,
    ) -> Dict[str, Any]:
        """Get inventory alerts across all storefronts."""
        alerts = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "low_stock": [],
            "out_of_stock": [],
            "summary": {
                "total_low_stock": 0,
                "total_out_of_stock": 0,
            },
        }

        for key, client in self._shopify_clients.items():
            low_stock = await client.get_low_stock_products(threshold=low_stock_threshold)
            out_of_stock = await client.get_out_of_stock_products()

            for p in low_stock:
                alerts["low_stock"].append(
                    {
                        "storefront": key,
                        "product_id": p.id,
                        "title": p.title,
                        "inventory": p.total_inventory,
                    }
                )

            for p in out_of_stock:
                alerts["out_of_stock"].append(
                    {
                        "storefront": key,
                        "product_id": p.id,
                        "title": p.title,
                    }
                )

            alerts["summary"]["total_low_stock"] += len(low_stock)
            alerts["summary"]["total_out_of_stock"] += len(out_of_stock)

        return alerts

    async def get_niche_storefront_summary(self) -> Dict[str, Any]:
        """Get summary of niche storefronts."""
        # Get products from master storefront
        master = self._shopify_clients.get("cirrus1") or next(
            iter(self._shopify_clients.values()), None
        )
        if not master:
            return {"error": "No master storefront configured"}

        products = await master.get_products(limit=500)
        summary = self._medusa.get_storefront_product_summary(products)

        return {
            "architecture": self._medusa.get_architecture_summary(),
            "storefronts": summary,
            "total_master_products": len(products),
        }

    async def apply_price_update(
        self,
        storefront_key: str,
        product_id: str,
        variant_id: str,
        new_price: float,
        compare_at_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Apply a price update to a product.

        Args:
            storefront_key: Storefront identifier
            product_id: Product ID
            variant_id: Variant ID
            new_price: New price to set
            compare_at_price: Optional compare-at price

        Returns:
            Update result
        """
        if storefront_key not in self._shopify_clients:
            return {"error": f"Storefront not found: {storefront_key}"}

        success = await self._shopify_clients[storefront_key].update_price(
            product_id,
            variant_id,
            new_price,
            compare_at_price,
        )

        return {
            "success": success,
            "storefront": storefront_key,
            "product_id": product_id,
            "variant_id": variant_id,
            "new_price": new_price,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_agent_report(self, agent_code: str) -> Dict[str, Any]:
        """
        Generate a report tailored for a specific agent.

        Args:
            agent_code: The agent code (Axiom, Keystone, Echo, Nexus)

        Returns:
            Agent-specific commerce report
        """
        all_analytics = await self.get_all_analytics()
        margin_analysis = await self.get_margin_analysis()
        inventory_alerts = await self.get_inventory_alerts()

        if agent_code == "Axiom":
            # Revenue focus: pricing, margins, opportunities
            pricing_summary = None
            for key in self._shopify_clients:
                pricing_summary = await self.optimize_pricing(key)
                break  # Just get first one for summary

            return {
                "agent": "Axiom",
                "focus": "Revenue & Pricing",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "revenue_summary": {
                    "total_inventory_value": all_analytics["totals"]["total_inventory_value"],
                    "average_margin": margin_analysis.get("gross_margin", 0),
                    "improvement_potential": margin_analysis.get("improvement_potential", 0),
                },
                "margin_analysis": margin_analysis,
                "pricing_opportunities": (
                    pricing_summary.get("recommendations", [])[:5] if pricing_summary else []
                ),
                "niche_performance": self._medusa.get_stats(),
                "recommendations": margin_analysis.get("recommendations", []),
            }

        elif agent_code == "Keystone":
            # Financial focus: margins, costs, inventory value
            return {
                "agent": "Keystone",
                "focus": "Financial Metrics",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "financial_summary": {
                    "total_inventory_value": all_analytics["totals"]["total_inventory_value"],
                    "gross_profit": margin_analysis.get("gross_profit", 0),
                    "gross_margin": margin_analysis.get("gross_margin", 0),
                },
                "margin_distribution": margin_analysis.get("margin_distribution", {}),
                "negative_margin_products": margin_analysis.get("negative_margin_count", 0),
                "low_margin_products": margin_analysis.get("low_margin_count", 0),
                "inventory_at_risk": {
                    "out_of_stock": inventory_alerts["summary"]["total_out_of_stock"],
                    "low_stock": inventory_alerts["summary"]["total_low_stock"],
                },
                "recommendations": margin_analysis.get("recommendations", []),
            }

        elif agent_code == "Echo":
            # Marketing focus: segments, products for campaigns
            niche_summary = await self.get_niche_storefront_summary()

            return {
                "agent": "Echo",
                "focus": "Product & Segment Strategy",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "product_overview": {
                    "total_products": all_analytics["totals"]["total_products"],
                    "by_storefront": {
                        k: v.get("total_products", 0)
                        for k, v in all_analytics["storefronts"].items()
                    },
                },
                "niche_segments": niche_summary.get("storefronts", {}),
                "segment_opportunities": [
                    {
                        "segment": k,
                        "product_count": v.get("product_count", 0),
                    }
                    for k, v in niche_summary.get("storefronts", {}).items()
                    if v.get("product_count", 0) > 0
                ],
                "campaign_recommendations": self._get_campaign_recommendations(all_analytics),
            }

        elif agent_code == "Nexus":
            # Operations focus: inventory, fulfillment, efficiency
            return {
                "agent": "Nexus",
                "focus": "Operations & Inventory",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "operations_summary": {
                    "total_storefronts": len(self._shopify_clients),
                    "total_products": all_analytics["totals"]["total_products"],
                    "total_inventory_units": all_analytics["totals"]["total_inventory"],
                },
                "inventory_health": {
                    "out_of_stock": inventory_alerts["summary"]["total_out_of_stock"],
                    "low_stock": inventory_alerts["summary"]["total_low_stock"],
                    "healthy": all_analytics["totals"]["total_products"]
                    - inventory_alerts["summary"]["total_out_of_stock"]
                    - inventory_alerts["summary"]["total_low_stock"],
                },
                "alerts": {
                    "critical": inventory_alerts["out_of_stock"][:10],
                    "warnings": inventory_alerts["low_stock"][:10],
                },
                "medusa_architecture": self._medusa.get_architecture_summary(),
            }

        else:
            # Default: comprehensive overview
            return {
                "agent": agent_code,
                "analytics": all_analytics,
                "margins": margin_analysis,
                "inventory": inventory_alerts,
            }

    def _get_campaign_recommendations(
        self,
        analytics: Dict[str, Any],
    ) -> List[str]:
        """Generate campaign recommendations from analytics."""
        recommendations = []

        total_products = analytics["totals"]["total_products"]
        if total_products > 0:
            recommendations.append(f"Catalog of {total_products} products available for campaigns")

        for key, sf_data in analytics["storefronts"].items():
            if sf_data.get("inventory_status", {}).get("in_stock", 0) > 10:
                recommendations.append(
                    f"{key}: {sf_data.get('total_products', 0)} products in stock for promotion"
                )

        return recommendations

    async def sync_to_medusa(
        self,
        source_storefront: str,
        target_niche: str,
    ) -> Dict[str, Any]:
        """
        Sync products from Shopify to a Medusa niche storefront.

        Args:
            source_storefront: Source Shopify storefront key
            target_niche: Target niche storefront key

        Returns:
            Sync results
        """
        if source_storefront not in self._shopify_clients:
            return {"error": f"Source storefront not found: {source_storefront}"}

        products = await self._shopify_clients[source_storefront].get_products(limit=500)
        result = await self._medusa.sync_products_to_medusa(products, target_niche)

        return result

    def list_storefronts(self) -> List[Dict[str, Any]]:
        """List all registered storefronts."""
        return [s.to_dict() for s in self._registry.list_all()]

    def get_storefront(self, storefront_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details about a specific storefront.

        Args:
            storefront_id: The storefront key/ID

        Returns:
            Storefront details dict or None if not found
        """
        storefront = self._registry.get(storefront_id)
        if storefront:
            result = storefront.to_dict()

            # Add additional details based on platform
            if storefront_id in self._shopify_clients:
                result["platform_details"] = {
                    "type": "shopify",
                    "connected": True,
                }
            else:
                # Check Medusa niche storefronts
                niche = self._medusa.get_niche_storefront(storefront_id)
                if niche:
                    result["platform_details"] = {
                        "type": "medusa_niche",
                        "segments": niche.segments,
                        "filters": niche.filters,
                    }

            return result

        return None

    def get_low_stock_alerts(self, threshold: int = 10) -> Dict[str, Any]:
        """
        Get low stock alerts - sync wrapper for MCP.

        This is a synchronous wrapper around get_inventory_alerts()
        for MCP compatibility.
        """
        import asyncio

        # Try to get the running loop or create one
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, we need to use a different approach
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, self.get_inventory_alerts(low_stock_threshold=threshold)
                )
                return future.result()
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(self.get_inventory_alerts(low_stock_threshold=threshold))

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "shopify_storefronts": len(self._shopify_clients),
            "medusa_storefronts": len(self._medusa.list_niche_storefronts()),
            "registry_stats": self._registry.get_stats(),
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
        }

    async def run_autonomous_analysis(self) -> Dict[str, Any]:
        """
        Run autonomous analysis cycle.

        This method is designed to be called by the scheduler for
        periodic autonomous commerce analysis.
        """
        results = {
            "cycle_completed_at": datetime.now(timezone.utc).isoformat(),
            "storefronts_analyzed": 0,
            "pricing_recommendations": 0,
            "alerts_generated": 0,
        }

        # 1. Refresh analytics
        analytics = await self.get_all_analytics()
        results["storefronts_analyzed"] = len(analytics.get("storefronts", {}))

        # 2. Generate pricing recommendations
        for key in self._shopify_clients:
            pricing = await self.optimize_pricing(key)
            results["pricing_recommendations"] += pricing.get("recommendations_count", 0)

        # 3. Check inventory
        alerts = await self.get_inventory_alerts()
        results["alerts_generated"] = (
            alerts["summary"]["total_low_stock"] + alerts["summary"]["total_out_of_stock"]
        )

        # 4. Analyze margins
        margin_analysis = await self.get_margin_analysis()
        results["margin_summary"] = {
            "gross_margin": margin_analysis.get("gross_margin", 0),
            "improvement_potential": margin_analysis.get("improvement_potential", 0),
        }

        self._last_sync = datetime.now(timezone.utc)

        return results
