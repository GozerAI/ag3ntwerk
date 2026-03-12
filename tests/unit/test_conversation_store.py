"""Tests for ConversationStore."""

import pytest

from ag3ntwerk.api.conversation_store import ConversationStore
from ag3ntwerk.memory.state_store import StateStore


@pytest.fixture
async def store(tmp_path):
    """Create a ConversationStore backed by a temp-dir StateStore."""
    db_path = tmp_path / "test_state.db"
    ss = StateStore(db_path=str(db_path))
    await ss.initialize()
    cs = ConversationStore(store=ss)
    yield cs
    await ss.close()


# ------------------------------------------------------------------
# Create & Get
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_returns_conv_prefix(store):
    conv_id = await store.create("Forge")
    assert conv_id.startswith("conv_")


@pytest.mark.asyncio
async def test_get_returns_created_conversation(store):
    conv_id = await store.create("Keystone")
    data = await store.get(conv_id)
    assert data is not None
    assert data["id"] == conv_id
    assert data["agent"] == "Keystone"
    assert data["messages"] == []
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(store):
    result = await store.get("conv_nonexistent")
    assert result is None


# ------------------------------------------------------------------
# add_message
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_message_appends(store):
    conv_id = await store.create("Forge")
    await store.add_message(conv_id, "user", "Hello")
    await store.add_message(conv_id, "assistant", "Hi there!")

    data = await store.get(conv_id)
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "Hello"
    assert data["messages"][1]["role"] == "assistant"
    assert data["messages"][1]["content"] == "Hi there!"
    assert "timestamp" in data["messages"][0]


@pytest.mark.asyncio
async def test_add_message_to_nonexistent_is_noop(store):
    # Should not raise
    await store.add_message("conv_fake", "user", "Hello")


# ------------------------------------------------------------------
# get_recent_messages (windowing)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_recent_messages_windowed(store):
    conv_id = await store.create("Nexus")
    for i in range(30):
        await store.add_message(conv_id, "user", f"msg-{i}")

    recent = await store.get_recent_messages(conv_id, limit=10)
    assert len(recent) == 10
    # Should be the last 10
    assert recent[0]["content"] == "msg-20"
    assert recent[-1]["content"] == "msg-29"


@pytest.mark.asyncio
async def test_get_recent_messages_fewer_than_limit(store):
    conv_id = await store.create("Nexus")
    await store.add_message(conv_id, "user", "only one")

    recent = await store.get_recent_messages(conv_id, limit=20)
    assert len(recent) == 1


@pytest.mark.asyncio
async def test_get_recent_messages_nonexistent(store):
    result = await store.get_recent_messages("conv_nope")
    assert result == []


# ------------------------------------------------------------------
# list_conversations
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_conversations_returns_summaries(store):
    id1 = await store.create("Forge")
    await store.add_message(id1, "user", "First conversation message")
    id2 = await store.create("Keystone")
    await store.add_message(id2, "user", "Second conversation")

    convs = await store.list_conversations()
    assert len(convs) == 2

    ids = {c["id"] for c in convs}
    assert id1 in ids
    assert id2 in ids

    for c in convs:
        assert "agent" in c
        assert "message_count" in c
        assert "preview" in c


@pytest.mark.asyncio
async def test_list_conversations_respects_limit(store):
    for i in range(5):
        await store.create("Nexus")

    convs = await store.list_conversations(limit=3)
    assert len(convs) == 3


@pytest.mark.asyncio
async def test_list_conversations_empty(store):
    convs = await store.list_conversations()
    assert convs == []


# ------------------------------------------------------------------
# delete
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_removes_conversation(store):
    conv_id = await store.create("Forge")
    assert await store.get(conv_id) is not None

    deleted = await store.delete(conv_id)
    assert deleted is True
    assert await store.get(conv_id) is None


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_false(store):
    deleted = await store.delete("conv_nonexistent")
    assert deleted is False
