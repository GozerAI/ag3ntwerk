"""
Notification Facade - Notification handlers and message formatting.

This facade manages:
- Notification handlers registration
- Message formatting
- Notification sending and tracking
"""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ag3ntwerk.core.decisions.models import Decision, Notification
from ag3ntwerk.core.decisions._utils import generate_id, utc_now, apply_max_limit

logger = logging.getLogger(__name__)


class NotificationFacade:
    """
    Facade for notification-related operations.

    Manages notification sending, formatting, and handler registration.
    """

    def __init__(self, max_notifications: int = 10000):
        """
        Initialize the notification facade.

        Args:
            max_notifications: Maximum notifications to store
        """
        self._notifications: List[Notification] = []
        self._notification_handlers: List[Callable[[Notification], Awaitable[None]]] = []
        self._max_notifications = max_notifications

    # --- Handler Management ---

    def add_notification_handler(
        self,
        handler: Callable[[Notification], Awaitable[None]],
    ) -> None:
        """
        Add a notification handler.

        Args:
            handler: Async function to handle notifications
        """
        self._notification_handlers.append(handler)

    # --- Sending ---

    async def send_notifications(
        self,
        decision: Decision,
        event_type: str,
    ) -> None:
        """
        Send notifications for a decision event.

        Args:
            decision: The decision
            event_type: Type of event (created, escalated, resolved, etc.)
        """
        recipients = list(decision.required_voters)

        for recipient in recipients:
            notification = Notification(
                id=generate_id(),
                decision_id=decision.id,
                recipient=recipient,
                event_type=event_type,
                message=self._format_notification_message(decision, event_type, recipient),
                created_at=utc_now(),
            )

            self._notifications.append(notification)
            self._notifications = apply_max_limit(self._notifications, self._max_notifications)

            # Send through handlers
            for handler in self._notification_handlers:
                try:
                    await handler(notification)
                    notification.sent = True
                    notification.sent_at = utc_now()
                except Exception as e:
                    logger.error(f"Notification handler error: {e}")

    # --- Formatting ---

    def _format_notification_message(
        self,
        decision: Decision,
        event_type: str,
        recipient: str,
    ) -> str:
        """
        Format a notification message.

        Args:
            decision: The decision
            event_type: Type of event
            recipient: Who is being notified

        Returns:
            Formatted message string
        """
        if event_type == "created":
            return f"New decision '{decision.title}' requires your vote."
        elif event_type == "escalated":
            return (
                f"Decision '{decision.title}' has been escalated and requires immediate attention."
            )
        elif event_type == "resolved":
            return f"Decision '{decision.title}' has been resolved."
        elif event_type == "cancelled":
            return f"Decision '{decision.title}' has been cancelled."
        else:
            return f"Update on decision '{decision.title}'."

    # --- Queries ---

    def get_notifications(
        self,
        recipient: Optional[str] = None,
        decision_id: Optional[str] = None,
        sent: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Notification]:
        """
        Get notifications.

        Args:
            recipient: Filter by recipient
            decision_id: Filter by decision
            sent: Filter by sent status
            limit: Maximum results

        Returns:
            List of notifications
        """
        notifications = self._notifications

        if recipient:
            notifications = [n for n in notifications if n.recipient == recipient]
        if decision_id:
            notifications = [n for n in notifications if n.decision_id == decision_id]
        if sent is not None:
            notifications = [n for n in notifications if n.sent == sent]

        return notifications[-limit:]

    # --- Stats ---

    def get_stats(self) -> Dict[str, Any]:
        """Get notification facade statistics."""
        return {
            "pending_notifications": sum(1 for n in self._notifications if not n.sent),
            "total_notifications": len(self._notifications),
        }
