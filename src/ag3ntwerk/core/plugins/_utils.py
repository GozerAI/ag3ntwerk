"""
Plugin Utilities - Shared utility functions for the Plugin system.
"""

from functools import wraps
from typing import Callable


def hook(event_name: str, priority: int = 50) -> Callable:
    """
    Decorator to mark a method as a hook handler.

    Args:
        event_name: Name of the event to hook
        priority: Execution priority (lower = first)

    Usage:
        @hook("task.created")
        async def handle_task_created(self, event):
            ...
    """

    def decorator(func: Callable) -> Callable:
        func._hook_event = event_name
        func._hook_priority = priority
        return func

    return decorator
