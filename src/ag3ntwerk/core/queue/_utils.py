"""
Shared utilities for the Task Queue system.

Provides common helper functions used across facades.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string."""
    if value:
        return datetime.fromisoformat(value)
    return None


def to_json(data: Any) -> str:
    """Serialize to JSON."""
    return json.dumps(data)


def from_json(data: Optional[str]) -> Any:
    """Deserialize from JSON."""
    if data:
        return json.loads(data)
    return None
