"""
Shared revenue models for ag3ntwerk.

Used by:
- Vector (Vector) for revenue tracking and forecasting
- Echo (Echo) for campaign attribution
- Payment integrations (Gumroad, Stripe) for transaction data

These are Pydantic models for validated data at integration boundaries.
The existing dataclass models in agents/crevo/models.py remain for
internal agent state.
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class RevenueType(str, Enum):
    """Revenue classification by billing model."""

    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    USAGE = "usage"


class RevenueRecord(BaseModel):
    """
    Individual revenue transaction.

    Normalized record from any payment platform (Gumroad, Stripe, etc.)
    used for cross-platform revenue aggregation.
    """

    id: str
    amount_cents: int
    amount_usd: float = 0.0

    product_id: str
    product_name: str
    platform: str  # gumroad, stripe, etc.

    transaction_date: datetime
    revenue_type: RevenueType = RevenueType.ONE_TIME

    # Attribution
    campaign_id: Optional[str] = None
    source: Optional[str] = None

    refunded: bool = False

    def model_post_init(self, __context) -> None:
        """Compute USD from cents if not provided."""
        if self.amount_usd == 0.0 and self.amount_cents != 0:
            self.amount_usd = self.amount_cents / 100


class MRRSnapshot(BaseModel):
    """
    Monthly Recurring Revenue snapshot.

    Point-in-time capture of subscription revenue metrics,
    used by Vector for MRR trend analysis.
    """

    date: date
    mrr: float
    new_mrr: float = 0.0
    churned_mrr: float = 0.0
    net_new_mrr: float = 0.0

    total_customers: int = 0
    new_customers: int = 0
    churned_customers: int = 0


class RevenueMetrics(BaseModel):
    """
    Aggregated revenue metrics for a time period.

    Produced by RevenueManager after querying all payment platforms
    and normalizing the data.
    """

    period_start: date
    period_end: date

    # Revenue
    total_revenue_usd: float
    transaction_count: int
    average_order_value: float

    # Breakdown
    by_product: Dict[str, float] = Field(default_factory=dict)
    by_platform: Dict[str, float] = Field(default_factory=dict)
    by_source: Dict[str, float] = Field(default_factory=dict)

    # Growth
    growth_rate: Optional[float] = None  # vs previous period
