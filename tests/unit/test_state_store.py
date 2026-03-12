"""
Unit tests for StateStore.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone

from ag3ntwerk.memory.state_store import StateStore, StateEntry


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class TestStateEntry:
    """Test StateEntry dataclass."""

    def test_basic_entry(self):
        entry = StateEntry(
            key="test_key",
            value={"data": "value"},
            namespace="test_ns",
        )
        assert entry.key == "test_key"
        assert entry.value == {"data": "value"}
        assert entry.namespace == "test_ns"
        assert entry.ttl_seconds is None
        assert entry.is_expired is False

    def test_entry_with_ttl_not_expired(self):
        entry = StateEntry(
            key="ttl_key",
            value="data",
            ttl_seconds=3600,  # 1 hour
            updated_at=_utcnow(),
        )
        assert entry.is_expired is False

    def test_entry_with_ttl_expired(self):
        entry = StateEntry(
            key="expired_key",
            value="data",
            ttl_seconds=1,
            updated_at=_utcnow() - timedelta(seconds=10),
        )
        assert entry.is_expired is True

    def test_entry_to_dict(self):
        entry = StateEntry(
            key="dict_key",
            value={"nested": "value"},
            namespace="dict_ns",
            metadata={"meta": "data"},
        )
        d = entry.to_dict()

        assert d["key"] == "dict_key"
        assert d["value"] == {"nested": "value"}
        assert d["namespace"] == "dict_ns"
        assert d["metadata"] == {"meta": "data"}


class TestStateStoreBasic:
    """Test basic StateStore operations."""

    @pytest.mark.asyncio
    async def test_initialize(self, state_store):
        # Should be able to list namespaces
        namespaces = await state_store.list_namespaces()
        assert isinstance(namespaces, list)

    @pytest.mark.asyncio
    async def test_set_and_get(self, state_store):
        await state_store.set("key1", "value1")
        value = await state_store.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_get_missing_key(self, state_store):
        value = await state_store.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_get_with_default(self, state_store):
        value = await state_store.get("nonexistent", default="default_val")
        assert value == "default_val"

    @pytest.mark.asyncio
    async def test_set_complex_value(self, state_store):
        complex_value = {
            "list": [1, 2, 3],
            "nested": {"key": "value"},
            "number": 42,
            "boolean": True,
        }
        await state_store.set("complex", complex_value)
        retrieved = await state_store.get("complex")

        assert retrieved == complex_value

    @pytest.mark.asyncio
    async def test_overwrite_value(self, state_store):
        await state_store.set("overwrite", "first")
        await state_store.set("overwrite", "second")

        value = await state_store.get("overwrite")
        assert value == "second"


class TestStateStoreNamespaces:
    """Test namespace isolation."""

    @pytest.mark.asyncio
    async def test_namespace_isolation(self, state_store):
        await state_store.set("key", "ns1_value", namespace="ns1")
        await state_store.set("key", "ns2_value", namespace="ns2")

        ns1_value = await state_store.get("key", namespace="ns1")
        ns2_value = await state_store.get("key", namespace="ns2")

        assert ns1_value == "ns1_value"
        assert ns2_value == "ns2_value"

    @pytest.mark.asyncio
    async def test_list_namespaces(self, state_store):
        await state_store.set("k1", "v1", namespace="alpha")
        await state_store.set("k2", "v2", namespace="beta")
        await state_store.set("k3", "v3", namespace="gamma")

        namespaces = await state_store.list_namespaces()

        assert "alpha" in namespaces
        assert "beta" in namespaces
        assert "gamma" in namespaces

    @pytest.mark.asyncio
    async def test_clear_namespace(self, state_store):
        await state_store.set("k1", "v1", namespace="to_clear")
        await state_store.set("k2", "v2", namespace="to_clear")
        await state_store.set("k3", "v3", namespace="to_keep")

        deleted = await state_store.clear_namespace("to_clear")

        assert deleted == 2

        # Cleared keys should be gone
        assert await state_store.get("k1", namespace="to_clear") is None
        assert await state_store.get("k2", namespace="to_clear") is None

        # Other namespace should be unaffected
        assert await state_store.get("k3", namespace="to_keep") == "v3"


class TestStateStoreDelete:
    """Test delete operations."""

    @pytest.mark.asyncio
    async def test_delete_existing(self, state_store):
        await state_store.set("to_delete", "value")
        deleted = await state_store.delete("to_delete")

        assert deleted is True
        assert await state_store.get("to_delete") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, state_store):
        deleted = await state_store.delete("never_existed")
        assert deleted is False


class TestStateStoreTTL:
    """Test TTL (time-to-live) functionality."""

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, state_store):
        await state_store.set("ttl_key", "value", ttl_seconds=3600)

        entry = await state_store.get_entry("ttl_key")
        assert entry is not None
        assert entry.ttl_seconds == 3600

    @pytest.mark.asyncio
    async def test_expired_key_returns_none(self, temp_db_path):
        # Use fresh store to control timing
        store = StateStore(db_path=temp_db_path)
        await store.initialize()

        # Set with 1 second TTL
        await store.set("expire_fast", "value", ttl_seconds=1)

        # Should exist immediately
        assert await store.get("expire_fast") == "value"

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should be gone
        assert await store.get("expire_fast") is None

        await store.close()

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, temp_db_path):
        store = StateStore(db_path=temp_db_path)
        await store.initialize()

        # Set some keys with short TTL
        await store.set("expire1", "v1", ttl_seconds=1)
        await store.set("expire2", "v2", ttl_seconds=1)
        await store.set("keep", "v3", ttl_seconds=3600)

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Cleanup
        cleaned = await store.cleanup_expired()

        assert cleaned == 2
        assert await store.get("keep") == "v3"

        await store.close()


class TestStateStoreListKeys:
    """Test key listing functionality."""

    @pytest.mark.asyncio
    async def test_list_keys(self, state_store):
        await state_store.set("key_a", "va", namespace="list_test")
        await state_store.set("key_b", "vb", namespace="list_test")
        await state_store.set("key_c", "vc", namespace="list_test")

        keys = await state_store.list_keys(namespace="list_test")

        assert len(keys) == 3
        assert "key_a" in keys
        assert "key_b" in keys
        assert "key_c" in keys

    @pytest.mark.asyncio
    async def test_list_keys_pattern(self, state_store):
        await state_store.set("user_123", "u1", namespace="patterns")
        await state_store.set("user_456", "u2", namespace="patterns")
        await state_store.set("config", "c1", namespace="patterns")

        keys = await state_store.list_keys(namespace="patterns", pattern="user_*")

        assert len(keys) == 2
        assert "user_123" in keys
        assert "user_456" in keys
        assert "config" not in keys


class TestStateStoreHistory:
    """Test history tracking."""

    @pytest.mark.asyncio
    async def test_get_history(self, state_store):
        await state_store.set("history_key", "v1", namespace="hist")
        await state_store.set("history_key", "v2", namespace="hist")
        await state_store.set("history_key", "v3", namespace="hist")

        history = await state_store.get_history("history_key", namespace="hist")

        assert len(history) == 3
        # Most recent first
        assert history[0]["value"] == "v3"

    @pytest.mark.asyncio
    async def test_history_limit(self, state_store):
        for i in range(20):
            await state_store.set("many_changes", f"v{i}", namespace="hist_limit")

        history = await state_store.get_history("many_changes", namespace="hist_limit", limit=5)

        assert len(history) == 5


class TestStateStoreEntry:
    """Test get_entry method."""

    @pytest.mark.asyncio
    async def test_get_entry_full(self, state_store):
        await state_store.set(
            "entry_key",
            {"data": "value"},
            namespace="entry_ns",
            ttl_seconds=3600,
            metadata={"source": "test"},
        )

        entry = await state_store.get_entry("entry_key", namespace="entry_ns")

        assert entry is not None
        assert entry.key == "entry_key"
        assert entry.value == {"data": "value"}
        assert entry.namespace == "entry_ns"
        assert entry.ttl_seconds == 3600
        assert entry.metadata == {"source": "test"}
        assert isinstance(entry.created_at, datetime)
        assert isinstance(entry.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_get_entry_missing(self, state_store):
        entry = await state_store.get_entry("nonexistent")
        assert entry is None


class TestStateStoreContextManager:
    """Test context manager usage."""

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_db_path):
        async with StateStore(db_path=temp_db_path) as store:
            await store.set("ctx_key", "ctx_value")
            value = await store.get("ctx_key")
            assert value == "ctx_value"

        # Store should be closed after exiting context
        assert store._initialized is False
