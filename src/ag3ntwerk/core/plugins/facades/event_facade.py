"""
Event Facade - Plugin event history and listeners.

This facade handles:
- Event history recording
- Event listener management
- History queries with filtering
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ag3ntwerk.core.plugins.models import PluginEvent

logger = logging.getLogger(__name__)


class EventFacade:
    """
    Facade for plugin event operations.

    Manages event history and listeners.
    """

    def __init__(self, max_event_history: int = 1000):
        """
        Initialize the event facade.

        Args:
            max_event_history: Maximum events to keep in history
        """
        self._event_history: List[PluginEvent] = []
        self._max_event_history = max_event_history
        self._listeners: List[Callable[[PluginEvent], Awaitable[None]]] = []

    def record_event(self, event: PluginEvent) -> None:
        """
        Record an event in history.

        Args:
            event: Plugin event to record
        """
        self._event_history.append(event)
        if len(self._event_history) > self._max_event_history:
            self._event_history = self._event_history[-self._max_event_history :]

        # Notify listeners
        for listener in self._listeners:
            try:
                asyncio.create_task(listener(event))
            except Exception as e:
                logger.error(f"Event listener error: {e}")

    def add_event_listener(
        self,
        listener: Callable[[PluginEvent], Awaitable[None]],
    ) -> None:
        """
        Add a listener for plugin events.

        Args:
            listener: Async function to call with each event
        """
        self._listeners.append(listener)

    def get_event_history(
        self,
        plugin_name: Optional[str] = None,
        hook_name: Optional[str] = None,
        success_only: Optional[bool] = None,
        limit: int = 100,
    ) -> List[PluginEvent]:
        """
        Get event history with filtering.

        Args:
            plugin_name: Filter by plugin
            hook_name: Filter by hook
            success_only: Filter by success status
            limit: Maximum events to return

        Returns:
            List of events
        """
        events = self._event_history

        if plugin_name:
            events = [e for e in events if e.plugin_name == plugin_name]
        if hook_name:
            events = [e for e in events if e.hook_name == hook_name]
        if success_only is not None:
            events = [e for e in events if e.success == success_only]

        return events[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get event statistics."""
        return {
            "event_history_size": len(self._event_history),
            "listener_count": len(self._listeners),
        }
