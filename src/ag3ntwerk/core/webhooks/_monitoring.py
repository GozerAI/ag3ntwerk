"""
Webhook observability: history, stats, dead letter queue, and health.
"""

import asyncio
import logging
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from ag3ntwerk.core.webhooks._types import (
    CircuitState,
    DeliveryRecord,
    DeliveryStatus,
    Webhook,
    WebhookEvent,
)

logger = logging.getLogger(__name__)


class WebhookMonitor:
    """Provides observability into webhook system health and history."""

    def __init__(
        self,
        webhooks: Dict[str, Webhook],
        delivery_history: deque,
        dead_letter_queue: deque,
        paused_webhooks: Set[str],
        deliver_fn: Callable,
        attempt_delivery_fn: Callable,
        get_batch_pending: Callable[[], int],
    ):
        self._webhooks = webhooks
        self._history = delivery_history
        self._dlq = dead_letter_queue
        self._paused = paused_webhooks
        self._deliver = deliver_fn
        self._attempt_delivery = attempt_delivery_fn
        self._get_batch_pending = get_batch_pending

    def get_delivery_history(
        self,
        webhook_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[DeliveryRecord]:
        """
        Get delivery history.

        Args:
            webhook_id: Filter by webhook ID
            event_type: Filter by event type
            limit: Maximum records to return

        Returns:
            List of delivery records
        """
        records = list(self._history)

        if webhook_id:
            records = [r for r in records if r.webhook_id == webhook_id]

        records = records[-limit:]
        return records

    def get_stats(self) -> Dict[str, Any]:
        """Get webhook system statistics."""
        total_webhooks = len(self._webhooks)
        active_webhooks = sum(1 for w in self._webhooks.values() if w.active)
        paused_webhooks = len(self._paused)

        circuit_open = sum(
            1 for w in self._webhooks.values() if w.circuit_breaker.state == CircuitState.OPEN
        )

        total_deliveries = sum(w.total_deliveries for w in self._webhooks.values())
        successful = sum(w.successful_deliveries for w in self._webhooks.values())
        failed = sum(w.failed_deliveries for w in self._webhooks.values())

        return {
            "webhooks": {
                "total": total_webhooks,
                "active": active_webhooks,
                "paused": paused_webhooks,
                "circuit_open": circuit_open,
            },
            "deliveries": {
                "total": total_deliveries,
                "successful": successful,
                "failed": failed,
                "success_rate": successful / total_deliveries if total_deliveries > 0 else 1.0,
            },
            "dead_letter_queue": len(self._dlq),
            "history_size": len(self._history),
            "batch_pending": self._get_batch_pending(),
        }

    def get_dead_letter_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get events from the dead letter queue.

        Args:
            limit: Maximum items to return

        Returns:
            List of failed events with error info
        """
        items = list(self._dlq)[-limit:]
        return [
            {
                "event": event.to_dict(),
                "webhook_id": webhook_id,
                "error": error,
            }
            for event, webhook_id, error in items
        ]

    async def retry_dead_letter(
        self,
        event_id: str,
        webhook_id: Optional[str] = None,
    ) -> bool:
        """
        Retry an event from the dead letter queue.

        Args:
            event_id: Event ID to retry
            webhook_id: Specific webhook to retry (optional)

        Returns:
            True if event was requeued
        """
        # Find and remove the event from DLQ
        # We iterate over a copy to safely modify during iteration
        for event, wh_id, _ in list(self._dlq):
            if event.id == event_id:
                if webhook_id and wh_id != webhook_id:
                    continue

                # Remove the matching entry
                self._dlq = type(self._dlq)(
                    (e, w, t)
                    for e, w, t in self._dlq
                    if not (e.id == event_id and (not webhook_id or w == webhook_id))
                )

                webhook = self._webhooks.get(wh_id)
                if webhook and webhook.active:
                    asyncio.create_task(self._deliver(webhook, event))
                    return True

        return False

    async def clear_dead_letter_queue(self) -> int:
        """Clear the dead letter queue."""
        count = len(self._dlq)
        self._dlq.clear()
        return count

    async def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Send a test event to a webhook.

        Args:
            webhook_id: Webhook to test

        Returns:
            Test result with status and response
        """
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return {"success": False, "error": "Webhook not found"}

        test_event = WebhookEvent(
            id=str(uuid.uuid4()),
            event_type="webhook.test",
            payload={
                "message": "This is a test event",
                "webhook_id": webhook_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            metadata={"test": True},
        )

        try:
            result = await self._attempt_delivery(webhook, test_event, 1)

            return {
                "success": result.status_code and 200 <= result.status_code < 300,
                "status_code": result.status_code,
                "duration_ms": result.duration_ms,
                "response": result.response_body[:500] if result.response_body else None,
                "error": result.error,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def get_webhook_health(self, webhook_id: str) -> Dict[str, Any]:
        """
        Get health status for a webhook.

        Args:
            webhook_id: Webhook ID

        Returns:
            Health information
        """
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return {"error": "Webhook not found"}

        recent_records = [r for r in self._history if r.webhook_id == webhook_id][-100:]

        recent_success = sum(1 for r in recent_records if r.status == DeliveryStatus.DELIVERED)
        recent_rate = recent_success / len(recent_records) if recent_records else 1.0

        if webhook.circuit_breaker.state == CircuitState.OPEN:
            health = "critical"
        elif webhook.consecutive_failures >= 10:
            health = "degraded"
        elif recent_rate < 0.9:
            health = "warning"
        else:
            health = "healthy"

        return {
            "webhook_id": webhook_id,
            "health": health,
            "active": webhook.active,
            "paused": webhook_id in self._paused,
            "circuit_breaker": {
                "state": webhook.circuit_breaker.state.value,
                "failure_count": webhook.circuit_breaker.failure_count,
            },
            "recent_success_rate": recent_rate,
            "consecutive_failures": webhook.consecutive_failures,
            "total_deliveries": webhook.total_deliveries,
            "rate_limited": webhook.is_rate_limited(),
        }

    def add_event_handler(
        self,
        event_type: str,
        handler: Callable[[WebhookEvent], Any],
        event_handlers: Dict[str, List[Callable]],
    ) -> None:
        """
        Add a local event handler (in addition to webhooks).

        Args:
            event_type: Event type to handle
            handler: Async handler function
            event_handlers: Shared event handlers dict
        """
        if event_type not in event_handlers:
            event_handlers[event_type] = []
        event_handlers[event_type].append(handler)
