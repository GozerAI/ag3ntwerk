"""
Conversation persistence store for multi-turn chat.

Wraps the existing StateStore with namespace isolation for
conversation data. Each conversation is stored as a single
key containing the full message history.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.memory.state_store import StateStore

logger = get_logger(__name__)

NAMESPACE = "conversations"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationStore:
    """
    Persistent conversation storage backed by StateStore.

    Each conversation is stored as a single key in the ``conversations``
    namespace. The value is a dict containing the message list plus
    metadata (agent, timestamps).
    """

    def __init__(self, store: Optional[StateStore] = None):
        self._store = store

    async def _get_store(self) -> StateStore:
        if self._store is None:
            from ag3ntwerk.memory.state_store import get_default_store

            self._store = await get_default_store()
        return self._store

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, agent: str) -> str:
        """Create a new conversation and return its ID."""
        conv_id = f"conv_{uuid.uuid4().hex[:12]}"
        now = _utcnow_iso()
        data: Dict[str, Any] = {
            "id": conv_id,
            "agent": agent,
            "messages": [],
            "created_at": now,
            "updated_at": now,
        }
        store = await self._get_store()
        await store.set(conv_id, data, namespace=NAMESPACE)
        return conv_id

    async def get(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Return full conversation dict, or None if not found."""
        store = await self._get_store()
        return await store.get(conversation_id, namespace=NAMESPACE)

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        """Append a message to an existing conversation."""
        store = await self._get_store()
        data = await store.get(conversation_id, namespace=NAMESPACE)
        if data is None:
            logger.warning(
                "Conversation not found for add_message",
                conversation_id=conversation_id,
            )
            return

        data["messages"].append(
            {
                "role": role,
                "content": content,
                "timestamp": _utcnow_iso(),
            }
        )
        data["updated_at"] = _utcnow_iso()
        await store.set(conversation_id, data, namespace=NAMESPACE)

    async def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Return the most recent *limit* messages (windowed history)."""
        data = await self.get(conversation_id)
        if data is None:
            return []
        messages = data.get("messages", [])
        return messages[-limit:]

    async def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return conversation summaries sorted by most-recently-updated."""
        store = await self._get_store()
        keys = await store.list_keys(namespace=NAMESPACE)

        summaries: List[Dict[str, Any]] = []
        for key in keys:
            data = await store.get(key, namespace=NAMESPACE)
            if data is None:
                continue
            messages = data.get("messages", [])
            summaries.append(
                {
                    "id": data["id"],
                    "agent": data.get("agent", ""),
                    "message_count": len(messages),
                    "preview": messages[0]["content"][:80] if messages else "",
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                }
            )

        # Sort newest first, then cap
        summaries.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return summaries[:limit]

    async def delete(self, conversation_id: str) -> bool:
        """Delete a conversation. Returns True if it existed."""
        store = await self._get_store()
        return await store.delete(conversation_id, namespace=NAMESPACE)
