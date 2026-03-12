"""
Payment platform integrations for ag3ntwerk.

Provides clients for payment/marketplace platforms used by:
- Vector (Vector) for revenue tracking
- Echo (Echo) for product distribution
- Existing W18 Marketplace Uploader

Components:
- base: PaymentClient ABC
- gumroad: Gumroad API client

Note: The existing Stripe integration lives at
ag3ntwerk.integrations.business.payments and handles Stripe-specific
billing (invoices, subscriptions). This package provides
marketplace-oriented payment integrations (Gumroad, etc.)
for the revenue stack.
"""

from ag3ntwerk.integrations.payments.gumroad import GumroadClient

__all__ = [
    "GumroadClient",
]
