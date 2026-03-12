"""
Webhook Notification System for ag3ntwerk.

Provides event-driven notifications to external systems:
- Webhook subscription management
- Event dispatching with retries
- Payload signing for security
- Delivery tracking and history

Usage:
    from ag3ntwerk.core.webhooks import (
        WebhookManager,
        WebhookEvent,
        get_webhook_manager,
        dispatch_event,
    )

    # Register a webhook
    manager = get_webhook_manager()
    webhook = await manager.register(
        url="https://example.com/webhook",
        events=["task.completed", "workflow.finished"],
        secret="my-secret-key",
    )

    # Dispatch an event
    await dispatch_event(
        event_type="task.completed",
        payload={"task_id": "123", "result": "success"},
    )
"""

import os
import threading
from typing import Any, Dict, Optional

from ag3ntwerk.core.webhooks._types import (
    CircuitState,
    CircuitBreaker,
    WebhookFilter,
    WebhookEventType,
    DeliveryStatus,
    WebhookEvent,
    DeliveryAttempt,
    DeliveryRecord,
    Webhook,
)
from ag3ntwerk.core.webhooks._manager import WebhookManager

# Module-level singleton with thread-safe initialization
_manager: Optional[WebhookManager] = None
_manager_lock = threading.Lock()


def get_webhook_manager() -> WebhookManager:
    """Get the global webhook manager (thread-safe)."""
    global _manager
    if _manager is None:
        with _manager_lock:
            # Double-check pattern for thread safety
            if _manager is None:
                _env = os.getenv("AGENTWERK_ENV", os.getenv("ENVIRONMENT", "development")).lower()
                _is_prod = _env == "production"
                _manager = WebhookManager(
                    allow_http=not _is_prod,
                    allow_localhost=not _is_prod,
                )
    return _manager


async def dispatch_event(
    event_type: str,
    payload: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Dispatch a webhook event.

    Args:
        event_type: Type of event
        payload: Event payload
        metadata: Optional metadata

    Returns:
        Event ID
    """
    manager = get_webhook_manager()
    return await manager.dispatch(event_type, payload, metadata)


async def shutdown_webhooks() -> None:
    """Shutdown the webhook manager."""
    global _manager
    if _manager:
        await _manager.close()
        _manager = None


__all__ = [
    # Enums
    "WebhookEventType",
    "DeliveryStatus",
    "CircuitState",
    # Data classes
    "WebhookEvent",
    "DeliveryAttempt",
    "DeliveryRecord",
    "Webhook",
    "CircuitBreaker",
    "WebhookFilter",
    # Manager
    "WebhookManager",
    "get_webhook_manager",
    # Functions
    "dispatch_event",
    "shutdown_webhooks",
]
