"""
Hook Facade - Hook dispatch with sandboxed execution.

This facade handles:
- Hook dispatch with sandboxed execution
- Timeout enforcement
- Event filter checking
- Handler execution with error recovery
"""

import asyncio
import inspect
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, TYPE_CHECKING

from ag3ntwerk.core.plugins.models import (
    HookRegistration,
    PluginEvent,
    PluginState,
    SandboxConfig,
)

if TYPE_CHECKING:
    from ag3ntwerk.core.plugins.base import Plugin

logger = logging.getLogger(__name__)


class HookFacade:
    """
    Facade for hook dispatch operations.

    Manages hook execution with sandboxing.
    """

    def __init__(
        self,
        plugins: Dict[str, "Plugin"],
        hooks: Dict[str, List[HookRegistration]],
        sandbox: SandboxConfig,
    ):
        """
        Initialize the hook facade.

        Args:
            plugins: Shared plugins dictionary
            hooks: Shared hooks dictionary
            sandbox: Sandbox configuration
        """
        self._plugins = plugins
        self._hooks = hooks
        self._sandbox = sandbox

        # Callback for recording events
        self._event_callback: Optional[Callable[[PluginEvent], None]] = None

    def set_event_callback(
        self,
        callback: Callable[[PluginEvent], None],
    ) -> None:
        """
        Set callback for event recording.

        Args:
            callback: Function to call with each PluginEvent
        """
        self._event_callback = callback

    async def dispatch(
        self,
        hook_name: str,
        event: Dict[str, Any],
        stop_on_error: bool = False,
    ) -> List[Any]:
        """
        Dispatch an event to all registered hooks with sandboxed execution.

        Args:
            hook_name: Name of the hook
            event: Event data
            stop_on_error: Stop if a handler raises an error

        Returns:
            List of results from handlers
        """
        # Get handlers for exact match AND wildcard handlers
        handlers = list(self._hooks.get(hook_name, []))

        # Also include wildcard handlers that listen to all events
        if hook_name != "*":
            handlers.extend(self._hooks.get("*", []))

        results = []

        for hook_reg in handlers:
            plugin = self._plugins.get(hook_reg.plugin_name)
            if not plugin or plugin.state != PluginState.ACTIVE:
                continue

            # Skip disabled plugins
            if plugin.is_disabled:
                continue

            # Check event filter
            if not plugin.accepts_event(hook_name):
                continue

            start_time = datetime.now(timezone.utc)
            success = True
            error_msg: Optional[str] = None
            result = None

            try:
                if self._sandbox.enabled:
                    # Execute with timeout
                    if inspect.iscoroutinefunction(hook_reg.handler):
                        result = await asyncio.wait_for(
                            hook_reg.handler(event), timeout=self._sandbox.hook_timeout_seconds
                        )
                    else:
                        result = hook_reg.handler(event)
                else:
                    if inspect.iscoroutinefunction(hook_reg.handler):
                        result = await hook_reg.handler(event)
                    else:
                        result = hook_reg.handler(event)

                results.append(result)

            except asyncio.TimeoutError:
                success = False
                error_msg = f"Hook timeout ({self._sandbox.hook_timeout_seconds}s)"
                logger.warning(f"Hook {hook_name} in {hook_reg.plugin_name} timed out")

            except Exception as e:
                success = False
                error_msg = str(e)
                logger.exception(f"Hook handler error: {hook_reg.plugin_name}.{hook_name}")
                if stop_on_error:
                    raise

            # Record execution
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            plugin.record_hook_execution(duration_ms, success, error_msg)

            # Record event
            plugin_event = PluginEvent(
                event_type=event.get("type", "unknown"),
                hook_name=hook_name,
                plugin_name=hook_reg.plugin_name,
                timestamp=start_time,
                duration_ms=duration_ms,
                success=success,
                error=error_msg,
            )

            if self._event_callback:
                self._event_callback(plugin_event)

            # Check if plugin should be disabled
            if (
                self._sandbox.enabled
                and plugin._error_count >= self._sandbox.max_errors_before_disable
            ):
                plugin.disable(
                    f"Too many errors ({plugin._error_count} >= "
                    f"{self._sandbox.max_errors_before_disable})"
                )

        return results

    def get_handlers(self, hook_name: str) -> List[HookRegistration]:
        """
        Get all handlers for a hook.

        Args:
            hook_name: Hook name

        Returns:
            List of hook registrations
        """
        return self._hooks.get(hook_name, [])

    def get_stats(self) -> Dict[str, Any]:
        """Get hook statistics."""
        total_hooks_executed = sum(p._hooks_executed for p in self._plugins.values())
        total_hooks_failed = sum(p._hooks_failed for p in self._plugins.values())

        return {
            "total_hooks_executed": total_hooks_executed,
            "total_hooks_failed": total_hooks_failed,
            "sandbox_enabled": self._sandbox.enabled,
        }
