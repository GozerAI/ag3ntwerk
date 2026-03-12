"""
Payment Integration for ag3ntwerk.

Provides integration with Stripe for payment processing.

Requirements:
    - pip install stripe

Payments is ideal for:
    - Revenue tracking
    - Subscription management
    - Invoice generation
    - Financial reporting
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StripeConfig:
    """Configuration for Stripe."""

    api_key: str = ""
    webhook_secret: str = ""


@dataclass
class Customer:
    """Represents a Stripe customer."""

    id: str
    email: str
    name: str = ""
    description: str = ""
    created: Optional[datetime] = None
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Invoice:
    """Represents a Stripe invoice."""

    id: str
    customer_id: str
    amount_due: int  # in cents
    amount_paid: int
    currency: str = "usd"
    status: str = ""
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created: Optional[datetime] = None
    invoice_pdf: str = ""
    lines: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Subscription:
    """Represents a Stripe subscription."""

    id: str
    customer_id: str
    status: str = ""
    plan_id: str = ""
    plan_name: str = ""
    amount: int = 0  # in cents
    currency: str = "usd"
    interval: str = ""  # month, year
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    created: Optional[datetime] = None


@dataclass
class PaymentIntent:
    """Represents a Stripe payment intent."""

    id: str
    amount: int
    currency: str
    status: str
    customer_id: str = ""
    created: Optional[datetime] = None


class PaymentIntegration:
    """
    Integration with Stripe for payments.

    Example:
        payments = PaymentIntegration(StripeConfig(
            api_key="sk_...",
        ))

        # List customers
        customers = await payments.list_customers()

        # Get revenue metrics
        metrics = await payments.get_revenue_metrics()

        # Create invoice
        invoice = await payments.create_invoice(
            customer_id="cus_...",
            items=[{"description": "Service", "amount": 10000}],
        )
    """

    def __init__(self, config: StripeConfig):
        """Initialize payment integration."""
        self.config = config
        self._stripe = None

    def _get_stripe(self):
        """Get Stripe module (without setting global api_key)."""
        if self._stripe is None:
            try:
                import stripe

                self._stripe = stripe
            except ImportError:
                raise ImportError("stripe not installed. Install with: pip install stripe")
        return self._stripe

    async def list_customers(
        self,
        limit: int = 100,
        email: Optional[str] = None,
    ) -> List[Customer]:
        """
        List Stripe customers.

        Args:
            limit: Maximum customers
            email: Filter by email

        Returns:
            List of Customers
        """
        loop = asyncio.get_running_loop()
        stripe = self._get_stripe()
        api_key = self.config.api_key

        def _list():
            params = {"limit": limit}
            if email:
                params["email"] = email

            customers = stripe.Customer.list(**params, api_key=api_key)
            return [
                Customer(
                    id=c.id,
                    email=c.email or "",
                    name=c.name or "",
                    description=c.description or "",
                    created=datetime.fromtimestamp(c.created, tz=timezone.utc),
                    metadata=dict(c.metadata) if c.metadata else {},
                )
                for c in customers.data
            ]

        return await loop.run_in_executor(None, _list)

    async def create_customer(
        self,
        email: str,
        name: str = "",
        description: str = "",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Customer:
        """Create a Stripe customer."""
        loop = asyncio.get_running_loop()
        stripe = self._get_stripe()
        api_key = self.config.api_key

        def _create():
            c = stripe.Customer.create(
                email=email,
                name=name,
                description=description,
                metadata=metadata or {},
                api_key=api_key,
            )
            return Customer(
                id=c.id,
                email=c.email or "",
                name=c.name or "",
                description=c.description or "",
                created=datetime.fromtimestamp(c.created, tz=timezone.utc),
            )

        return await loop.run_in_executor(None, _create)

    async def list_invoices(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Invoice]:
        """
        List invoices.

        Args:
            customer_id: Filter by customer
            status: Filter by status (draft, open, paid, void, uncollectible)
            limit: Maximum invoices

        Returns:
            List of Invoices
        """
        loop = asyncio.get_running_loop()
        stripe = self._get_stripe()
        api_key = self.config.api_key

        def _list():
            params = {"limit": limit}
            if customer_id:
                params["customer"] = customer_id
            if status:
                params["status"] = status

            invoices = stripe.Invoice.list(**params, api_key=api_key)
            return [
                Invoice(
                    id=inv.id,
                    customer_id=inv.customer,
                    amount_due=inv.amount_due,
                    amount_paid=inv.amount_paid,
                    currency=inv.currency,
                    status=inv.status,
                    due_date=(
                        datetime.fromtimestamp(inv.due_date, tz=timezone.utc)
                        if inv.due_date
                        else None
                    ),
                    created=datetime.fromtimestamp(inv.created, tz=timezone.utc),
                    invoice_pdf=inv.invoice_pdf or "",
                )
                for inv in invoices.data
            ]

        return await loop.run_in_executor(None, _list)

    async def create_invoice(
        self,
        customer_id: str,
        items: List[Dict[str, Any]],
        auto_advance: bool = True,
    ) -> Invoice:
        """
        Create an invoice.

        Args:
            customer_id: Customer ID
            items: Invoice line items [{"description": "...", "amount": cents}]
            auto_advance: Auto-finalize invoice

        Returns:
            Created Invoice
        """
        loop = asyncio.get_running_loop()
        stripe = self._get_stripe()
        api_key = self.config.api_key

        def _create():
            # Create invoice
            inv = stripe.Invoice.create(
                customer=customer_id,
                auto_advance=auto_advance,
                api_key=api_key,
            )

            # Add line items
            for item in items:
                stripe.InvoiceItem.create(
                    customer=customer_id,
                    invoice=inv.id,
                    description=item.get("description", ""),
                    amount=item.get("amount", 0),
                    currency=item.get("currency", "usd"),
                    api_key=api_key,
                )

            # Refresh invoice
            inv = stripe.Invoice.retrieve(inv.id, api_key=api_key)

            return Invoice(
                id=inv.id,
                customer_id=inv.customer,
                amount_due=inv.amount_due,
                amount_paid=inv.amount_paid,
                currency=inv.currency,
                status=inv.status,
                created=datetime.fromtimestamp(inv.created, tz=timezone.utc),
            )

        return await loop.run_in_executor(None, _create)

    async def list_subscriptions(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Subscription]:
        """
        List subscriptions.

        Args:
            customer_id: Filter by customer
            status: Filter by status
            limit: Maximum subscriptions

        Returns:
            List of Subscriptions
        """
        loop = asyncio.get_running_loop()
        stripe = self._get_stripe()
        api_key = self.config.api_key

        def _list():
            params = {"limit": limit}
            if customer_id:
                params["customer"] = customer_id
            if status:
                params["status"] = status

            subs = stripe.Subscription.list(**params, api_key=api_key)
            return [
                Subscription(
                    id=sub.id,
                    customer_id=sub.customer,
                    status=sub.status,
                    plan_id=sub.items.data[0].price.id if sub.items.data else "",
                    plan_name=sub.items.data[0].price.nickname or "" if sub.items.data else "",
                    amount=sub.items.data[0].price.unit_amount or 0 if sub.items.data else 0,
                    currency=sub.currency,
                    interval=sub.items.data[0].price.recurring.interval if sub.items.data else "",
                    current_period_start=datetime.fromtimestamp(
                        sub.current_period_start, tz=timezone.utc
                    ),
                    current_period_end=datetime.fromtimestamp(
                        sub.current_period_end, tz=timezone.utc
                    ),
                    cancel_at_period_end=sub.cancel_at_period_end,
                    created=datetime.fromtimestamp(sub.created, tz=timezone.utc),
                )
                for sub in subs.data
            ]

        return await loop.run_in_executor(None, _list)

    async def get_revenue_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get revenue metrics.

        Args:
            start_date: Start of period
            end_date: End of period

        Returns:
            Dict with revenue metrics
        """
        loop = asyncio.get_running_loop()
        stripe = self._get_stripe()
        api_key = self.config.api_key

        def _metrics():
            # Get balance transactions
            params = {"limit": 100}
            if start_date:
                params["created"] = {"gte": int(start_date.timestamp())}
            if end_date:
                if "created" in params:
                    params["created"]["lte"] = int(end_date.timestamp())
                else:
                    params["created"] = {"lte": int(end_date.timestamp())}

            transactions = stripe.BalanceTransaction.list(**params, api_key=api_key)

            total_revenue = 0
            fees = 0
            refunds = 0

            for tx in transactions.data:
                if tx.type == "charge":
                    total_revenue += tx.amount
                    fees += tx.fee
                elif tx.type == "refund":
                    refunds += abs(tx.amount)

            # Get MRR from active subscriptions
            subs = stripe.Subscription.list(status="active", limit=100, api_key=api_key)
            mrr = sum(
                sub.items.data[0].price.unit_amount or 0 for sub in subs.data if sub.items.data
            )

            return {
                "total_revenue": total_revenue / 100,  # Convert to dollars
                "fees": fees / 100,
                "net_revenue": (total_revenue - fees) / 100,
                "refunds": refunds / 100,
                "mrr": mrr / 100,
                "active_subscriptions": len(subs.data),
            }

        return await loop.run_in_executor(None, _metrics)

    async def get_balance(self) -> Dict[str, int]:
        """Get Stripe account balance."""
        loop = asyncio.get_running_loop()
        stripe = self._get_stripe()
        api_key = self.config.api_key

        def _balance():
            balance = stripe.Balance.retrieve(api_key=api_key)
            return {
                "available": sum(b.amount for b in balance.available),
                "pending": sum(b.amount for b in balance.pending),
            }

        return await loop.run_in_executor(None, _balance)
