"""
Batch event processing for webhooks.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from ag3ntwerk.core.webhooks._types import (
    DeliveryRecord,
    Webhook,
    WebhookEvent,
)

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Queues events and flushes them in batches."""

    def __init__(
        self,
        batch_size: int,
        batch_timeout: float,
        get_webhooks: Callable[[], Dict[str, Webhook]],
        get_paused: Callable[[], Set[str]],
        deliver: Callable[[Webhook, WebhookEvent], Awaitable[DeliveryRecord]],
    ):
        self._batch_size = batch_size
        self._batch_timeout = batch_timeout
        self._event_batch: List[WebhookEvent] = []
        self._batch_task: Optional[asyncio.Task] = None
        self._get_webhooks = get_webhooks
        self._get_paused = get_paused
        self._deliver = deliver

    def queue_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Queue an event for batch dispatch.

        Events are dispatched when batch size is reached or timeout expires.

        Returns:
            Event ID
        """
        event = WebhookEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            payload=payload,
            metadata=metadata or {},
        )

        self._event_batch.append(event)

        # Start batch timer if not running
        if self._batch_task is None or self._batch_task.done():
            self._batch_task = asyncio.create_task(self._batch_timer())

        # Flush if batch is full
        if len(self._event_batch) >= self._batch_size:
            asyncio.create_task(self._flush_batch())

        return event.id

    async def _batch_timer(self) -> None:
        """Wait for batch timeout then flush."""
        await asyncio.sleep(self._batch_timeout)
        await self._flush_batch()

    async def _flush_batch(self) -> None:
        """Flush the event batch."""
        if not self._event_batch:
            return

        batch = self._event_batch
        self._event_batch = []
        paused = self._get_paused()

        for event in batch:
            matching = [
                w
                for w in self._get_webhooks().values()
                if w.active
                and w.matches_event(event.event_type)
                and w.id not in paused
                and w.circuit_breaker.can_execute()
                and not w.is_rate_limited()
                and (not w.filters or w.filters.matches(event.payload))
            ]

            for webhook in matching:
                asyncio.create_task(self._deliver(webhook, event))

        logger.debug(f"Flushed batch of {len(batch)} events")

    @property
    def pending_count(self) -> int:
        """Number of events waiting in the batch."""
        return len(self._event_batch)
