"""
Memory module for agent state and context management.

Provides persistent state storage with:
- SQLite-backed key-value store
- Namespace isolation for multi-tenant usage
- TTL support for automatic expiration
- History tracking for auditing

Usage:
    from ag3ntwerk.memory import StateStore, get_default_store

    # Using context manager
    async with StateStore() as store:
        await store.set("key", {"data": "value"}, namespace="agent_123")
        data = await store.get("key", namespace="agent_123")

    # Using singleton
    store = await get_default_store()
    await store.set("key", "value")
"""

from ag3ntwerk.memory.state_store import (
    StateStore,
    StateEntry,
    get_default_store,
)

__all__ = [
    "StateStore",
    "StateEntry",
    "get_default_store",
]
