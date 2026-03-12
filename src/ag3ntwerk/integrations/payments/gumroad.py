"""
Gumroad API client for ag3ntwerk.

Provides product management, sales tracking, and revenue analytics
from the Gumroad marketplace platform.

Used by:
- Vector (Vector) for revenue tracking
- Echo (Echo) for product distribution
- W18 Marketplace Uploader

Environment variables:
- GUMROAD_ACCESS_TOKEN

Requirements:
    pip install httpx
"""

import logging
import os
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_resource_id(resource_id: str, name: str = "resource_id") -> str:
    """Validate a resource ID for safe URL path construction."""
    if not resource_id or not _SAFE_ID_PATTERN.match(resource_id):
        raise ValueError(
            f"Invalid {name}: must be non-empty and contain only "
            f"alphanumeric characters, hyphens, and underscores."
        )
    return resource_id


class GumroadClient:
    """
    Gumroad API v2 client.

    Handles product CRUD, sales retrieval, revenue aggregation,
    and subscriber management.

    Example:
        client = GumroadClient()
        products = await client.get_products()
        summary = await client.get_revenue_summary(period_days=30)
    """

    BASE_URL = "https://api.gumroad.com/v2"

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("GUMROAD_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError("GUMROAD_ACCESS_TOKEN not configured")

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to Gumroad API."""
        url = f"{self.BASE_URL}/{endpoint}"

        if data is None:
            data = {}
        # Gumroad API v2 authenticates via access_token form/query parameter
        data["access_token"] = self.access_token

        async with httpx.AsyncClient(timeout=60.0) as client:
            if method == "GET":
                resp = await client.get(url, params={**data, **(params or {})})
            elif method == "POST":
                resp = await client.post(url, data=data)
            elif method == "PUT":
                resp = await client.put(url, data=data)
            elif method == "DELETE":
                resp = await client.delete(url, params=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            resp.raise_for_status()
            return resp.json()

    # --- Product Management (for Echo) ---

    async def create_product(
        self,
        name: str,
        description: str,
        price: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create a new Gumroad product. Price in cents."""
        return await self._request(
            "POST",
            "products",
            {
                "name": name,
                "description": description,
                "price": price,
                **kwargs,
            },
        )

    async def get_products(self) -> List[Dict[str, Any]]:
        """Get all products for the authenticated account."""
        result = await self._request("GET", "products")
        return result.get("products", [])

    async def update_product(
        self,
        product_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Update a product by ID."""
        _validate_resource_id(product_id, "product_id")
        return await self._request("PUT", f"products/{product_id}", kwargs)

    async def enable_product(self, product_id: str) -> Dict[str, Any]:
        """Enable/publish a product."""
        _validate_resource_id(product_id, "product_id")
        return await self._request("PUT", f"products/{product_id}/enable")

    async def disable_product(self, product_id: str) -> Dict[str, Any]:
        """Disable/unpublish a product."""
        _validate_resource_id(product_id, "product_id")
        return await self._request("PUT", f"products/{product_id}/disable")

    # --- Sales & Revenue (for Vector) ---

    async def get_sales(
        self,
        after: Optional[date] = None,
        before: Optional[date] = None,
        product_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get sales data with optional date and product filters.

        Args:
            after: Only sales after this date.
            before: Only sales before this date.
            product_id: Filter by specific product.

        Returns:
            List of sale records.
        """
        params: Dict[str, Any] = {}
        if after:
            params["after"] = after.isoformat()
        if before:
            params["before"] = before.isoformat()
        if product_id:
            params["product_id"] = product_id

        result = await self._request("GET", "sales", params=params)
        return result.get("sales", [])

    async def get_revenue_summary(
        self,
        period_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Compute revenue summary for a period.

        Args:
            period_days: Number of days to look back.

        Returns:
            Dict with total_sales, total_revenue, refunds,
            and per-product breakdown.
        """
        after = date.today() - timedelta(days=period_days)
        sales = await self.get_sales(after=after)

        total_revenue = sum(
            s.get("price", 0) - s.get("gumroad_fee", 0) - s.get("affiliate_credit", 0)
            for s in sales
            if not s.get("refunded")
        )

        refund_amount = sum(s.get("price", 0) for s in sales if s.get("refunded"))

        return {
            "period_days": period_days,
            "total_sales": len([s for s in sales if not s.get("refunded")]),
            "total_revenue_cents": total_revenue,
            "total_revenue_usd": total_revenue / 100,
            "refunds": len([s for s in sales if s.get("refunded")]),
            "refund_amount_usd": refund_amount / 100,
            "products": self._group_by_product(sales),
        }

    def _group_by_product(self, sales: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Group sales data by product."""
        products: Dict[str, Any] = {}
        for sale in sales:
            pid = sale.get("product_id", "unknown")
            if pid not in products:
                products[pid] = {
                    "name": sale.get("product_name", "Unknown"),
                    "sales": 0,
                    "revenue_cents": 0,
                }
            if not sale.get("refunded"):
                products[pid]["sales"] += 1
                products[pid]["revenue_cents"] += sale.get("price", 0)
        return products

    async def get_subscribers(self) -> List[Dict[str, Any]]:
        """Get subscription/membership data."""
        result = await self._request("GET", "subscribers")
        return result.get("subscribers", [])
