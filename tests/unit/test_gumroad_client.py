"""
Unit tests for Gumroad payment client.

All HTTP calls are mocked - no real API access needed.
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.integrations.payments.gumroad import GumroadClient


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client():
    return GumroadClient(access_token="test_gumroad_token")


# =============================================================================
# Initialization
# =============================================================================


class TestGumroadClientInit:
    """Tests for client initialization."""

    def test_creation_with_token(self):
        client = GumroadClient(access_token="tok_123")
        assert client.access_token == "tok_123"

    def test_creation_missing_token_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="GUMROAD_ACCESS_TOKEN"):
                GumroadClient(access_token=None)

    def test_creation_from_env(self):
        with patch.dict("os.environ", {"GUMROAD_ACCESS_TOKEN": "env_tok"}):
            client = GumroadClient()
            assert client.access_token == "env_tok"


# =============================================================================
# Product Management
# =============================================================================


class TestGumroadProducts:
    """Tests for product management."""

    async def test_get_products(self, client):
        mock_products = [
            {"id": "prod_1", "name": "E-book", "price": 2999},
            {"id": "prod_2", "name": "Course", "price": 9999},
        ]

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"success": True, "products": mock_products}
            mock_resp.raise_for_status = MagicMock()
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            products = await client.get_products()
            assert len(products) == 2
            assert products[0]["name"] == "E-book"

    async def test_create_product(self, client):
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "success": True,
                "product": {"id": "prod_new", "name": "New Product"},
            }
            mock_resp.raise_for_status = MagicMock()
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await client.create_product(
                name="New Product",
                description="A description",
                price=4999,
            )
            assert result["success"] is True

    async def test_update_product(self, client):
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"success": True}
            mock_resp.raise_for_status = MagicMock()
            mock_instance = AsyncMock()
            mock_instance.put = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await client.update_product("prod_1", name="Updated Name")
            assert result["success"] is True


# =============================================================================
# Sales & Revenue
# =============================================================================


class TestGumroadSales:
    """Tests for sales retrieval and revenue summary."""

    async def test_get_sales(self, client):
        mock_sales = [
            {
                "id": "sale_1",
                "product_id": "prod_1",
                "product_name": "E-book",
                "price": 2999,
                "refunded": False,
            },
            {
                "id": "sale_2",
                "product_id": "prod_1",
                "product_name": "E-book",
                "price": 2999,
                "refunded": True,
            },
        ]

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"success": True, "sales": mock_sales}
            mock_resp.raise_for_status = MagicMock()
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            sales = await client.get_sales()
            assert len(sales) == 2

    async def test_get_sales_with_date_filter(self, client):
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"success": True, "sales": []}
            mock_resp.raise_for_status = MagicMock()
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            sales = await client.get_sales(
                after=date(2026, 1, 1),
                before=date(2026, 1, 31),
            )
            assert sales == []

    async def test_revenue_summary(self, client):
        mock_sales = [
            {
                "id": "s1",
                "product_id": "p1",
                "product_name": "Ebook",
                "price": 5000,
                "gumroad_fee": 500,
                "affiliate_credit": 0,
                "refunded": False,
            },
            {
                "id": "s2",
                "product_id": "p1",
                "product_name": "Ebook",
                "price": 5000,
                "gumroad_fee": 500,
                "affiliate_credit": 0,
                "refunded": False,
            },
            {
                "id": "s3",
                "product_id": "p2",
                "product_name": "Course",
                "price": 9900,
                "gumroad_fee": 990,
                "affiliate_credit": 0,
                "refunded": True,  # Refund
            },
        ]

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"success": True, "sales": mock_sales}
            mock_resp.raise_for_status = MagicMock()
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            summary = await client.get_revenue_summary(period_days=30)

            assert summary["total_sales"] == 2  # excludes refund
            assert summary["refunds"] == 1
            assert summary["refund_amount_usd"] == 99.0  # 9900 cents
            # Revenue = (5000-500) + (5000-500) = 9000 cents
            assert summary["total_revenue_cents"] == 9000
            assert summary["total_revenue_usd"] == 90.0

    def test_group_by_product(self, client):
        sales = [
            {"product_id": "p1", "product_name": "Ebook", "price": 2999, "refunded": False},
            {"product_id": "p1", "product_name": "Ebook", "price": 2999, "refunded": False},
            {"product_id": "p2", "product_name": "Course", "price": 9999, "refunded": False},
            {"product_id": "p1", "product_name": "Ebook", "price": 2999, "refunded": True},
        ]

        grouped = client._group_by_product(sales)
        assert grouped["p1"]["sales"] == 2  # Excludes refunded
        assert grouped["p1"]["revenue_cents"] == 5998
        assert grouped["p2"]["sales"] == 1


# =============================================================================
# Subscribers
# =============================================================================


class TestGumroadSubscribers:
    """Tests for subscriber retrieval."""

    async def test_get_subscribers(self, client):
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "success": True,
                "subscribers": [{"id": "sub_1", "email": "user@example.com"}],
            }
            mock_resp.raise_for_status = MagicMock()
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            subs = await client.get_subscribers()
            assert len(subs) == 1
            assert subs[0]["email"] == "user@example.com"


# =============================================================================
# Package import
# =============================================================================


class TestPaymentsPackageImport:
    """Test package-level imports work."""

    def test_import_gumroad_client(self):
        from ag3ntwerk.integrations.payments import GumroadClient

        assert GumroadClient is not None
