"""
Shared utilities for the Decision Support system.

Provides common helper functions used across facades.
"""

import uuid
from datetime import datetime, timezone
from typing import List, TypeVar

T = TypeVar("T")


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def apply_max_limit(items: List[T], max_items: int) -> List[T]:
    """
    Trim a list to max items, keeping newest (last items).

    Args:
        items: List to trim
        max_items: Maximum number of items to keep

    Returns:
        Trimmed list with at most max_items elements
    """
    if len(items) > max_items:
        return items[-max_items:]
    return items
