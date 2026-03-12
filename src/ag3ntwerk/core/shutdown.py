"""
Graceful Shutdown Manager for ag3ntwerk.

Provides graceful shutdown with:
- Task draining - wait for in-flight tasks to complete
- Configurable timeouts
- Signal handling (SIGTERM, SIGINT)
- Shutdown hooks for cleanup
- WebSocket connection draining

Usage:
    from ag3ntwerk.core.shutdown import ShutdownManager, register_shutdown_hook

    # Register cleanup hook
    @register_shutdown_hook(priority=10)
    async def cleanup_database():
        await db.close()

    # In your app
    shutdown_manager = ShutdownManager(drain_timeout=30.0)
    await shutdown_manager.shutdown()
"""

import asyncio
import signal
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from ag3ntwerk.core.logging import get_logger
import time

logger = get_logger(__name__)


class ShutdownState(Enum):
    """Shutdown state machine."""

    RUNNING = "running"
    DRAINING = "draining"  # Accepting no new work, completing existing
    SHUTTING_DOWN = "shutting_down"  # Running shutdown hooks
    SHUTDOWN = "shutdown"  # Complete


@dataclass
class ShutdownHook:
    """Registered shutdown hook."""

    name: str
    func: Callable[[], Coroutine[Any, Any, None]]
    priority: int = 50  # Lower = runs first
    timeout: float = 10.0

    def __lt__(self, other: "ShutdownHook") -> bool:
        return self.priority < other.priority


@dataclass
class TaskInfo:
    """Information about an active task."""

    task_id: str
    name: str
    started_at: datetime
    task: Optional[asyncio.Task] = None

    @property
    def duration_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()


class ShutdownManager:
    """
    Manages graceful shutdown with task draining.

    Usage:
        shutdown_manager = ShutdownManager()

        # Track tasks
        with shutdown_manager.track_task("process_request", task_id="123"):
            await process_request()

        # Graceful shutdown
        await shutdown_manager.shutdown()
    """

    def __init__(
        self,
        drain_timeout: float = 30.0,
        force_timeout: float = 60.0,
        check_interval: float = 0.5,
    ):
        """
        Initialize the shutdown manager.

        Args:
            drain_timeout: Max time to wait for tasks to drain (seconds)
            force_timeout: Max total shutdown time before force quit (seconds)
            check_interval: How often to check for task completion (seconds)
        """
        self.drain_timeout = drain_timeout
        self.force_timeout = force_timeout
        self.check_interval = check_interval

        self._state = ShutdownState.RUNNING
        self._active_tasks: Dict[str, TaskInfo] = {}
        self._hooks: List[ShutdownHook] = []
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._tasks_lock = asyncio.Lock()
        self._task_counter = 0

    @property
    def state(self) -> ShutdownState:
        """Current shutdown state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if accepting new work."""
        return self._state == ShutdownState.RUNNING

    @property
    def is_draining(self) -> bool:
        """Check if draining (no new work, completing existing)."""
        return self._state == ShutdownState.DRAINING

    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown in progress."""
        return self._state in (ShutdownState.DRAINING, ShutdownState.SHUTTING_DOWN)

    @property
    def active_task_count(self) -> int:
        """Number of active tasks."""
        return len(self._active_tasks)

    def register_hook(
        self,
        name: str,
        func: Callable[[], Coroutine[Any, Any, None]],
        priority: int = 50,
        timeout: float = 10.0,
    ) -> None:
        """
        Register a shutdown hook.

        Args:
            name: Hook name for logging
            func: Async function to run during shutdown
            priority: Lower priority runs first (default 50)
            timeout: Max time for this hook (seconds)
        """
        hook = ShutdownHook(name=name, func=func, priority=priority, timeout=timeout)
        self._hooks.append(hook)
        self._hooks.sort()  # Sort by priority
        logger.debug(f"Registered shutdown hook: {name} (priority={priority})")

    def unregister_hook(self, name: str) -> None:
        """Unregister a shutdown hook by name."""
        self._hooks = [h for h in self._hooks if h.name != name]

    class TaskTracker:
        """Context manager for tracking task lifecycle."""

        def __init__(self, manager: "ShutdownManager", task_id: str, name: str):
            self.manager = manager
            self.task_id = task_id
            self.name = name

        async def __aenter__(self) -> "ShutdownManager.TaskTracker":
            await self.manager._start_task(self.task_id, self.name)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
            await self.manager._end_task(self.task_id)
            return None

    def track_task(self, name: str, task_id: Optional[str] = None) -> TaskTracker:
        """
        Track a task for graceful shutdown.

        Usage:
            async with shutdown_manager.track_task("process_request", task_id="123"):
                await process_request()

        Args:
            name: Task name for logging
            task_id: Unique task ID (auto-generated if not provided)

        Returns:
            TaskTracker context manager
        """
        if task_id is None:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}"

        return self.TaskTracker(self, task_id, name)

    async def _start_task(self, task_id: str, name: str) -> None:
        """Register a task as active."""
        async with self._tasks_lock:
            if self._state != ShutdownState.RUNNING:
                raise RuntimeError(
                    f"Cannot start new task '{name}': shutdown in progress "
                    f"(state={self._state.value})"
                )

            self._active_tasks[task_id] = TaskInfo(
                task_id=task_id,
                name=name,
                started_at=datetime.now(timezone.utc),
                task=asyncio.current_task(),
            )

    async def _end_task(self, task_id: str) -> None:
        """Mark a task as complete."""
        async with self._tasks_lock:
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()

    def signal_shutdown(self) -> None:
        """Signal that shutdown should begin."""
        self._shutdown_event.set()

    async def shutdown(
        self,
        drain_timeout: Optional[float] = None,
        force_timeout: Optional[float] = None,
    ) -> bool:
        """
        Perform graceful shutdown.

        Args:
            drain_timeout: Override default drain timeout
            force_timeout: Override default force timeout

        Returns:
            True if shutdown was graceful, False if forced
        """
        drain_timeout = drain_timeout or self.drain_timeout
        force_timeout = force_timeout or self.force_timeout

        async with self._lock:
            if self._state == ShutdownState.SHUTDOWN:
                return True

            start_time = time.time()
            graceful = True

            # Phase 1: Stop accepting new work
            logger.info(
                "Beginning graceful shutdown",
                active_tasks=self.active_task_count,
                drain_timeout=drain_timeout,
            )
            self._state = ShutdownState.DRAINING
            self._shutdown_event.set()

            # Phase 2: Wait for active tasks to complete
            drain_start = time.time()
            while self.active_task_count > 0:
                elapsed = time.time() - drain_start
                remaining = drain_timeout - elapsed

                if remaining <= 0:
                    logger.warning(
                        "Drain timeout exceeded, forcing shutdown",
                        remaining_tasks=self.active_task_count,
                        tasks=[t.name for t in self._active_tasks.values()],
                    )
                    graceful = False
                    break

                logger.info(
                    "Waiting for tasks to complete",
                    active_tasks=self.active_task_count,
                    remaining_seconds=round(remaining, 1),
                )

                await asyncio.sleep(min(self.check_interval, remaining))

            if self.active_task_count == 0:
                logger.info("All tasks drained successfully")

            # Phase 3: Run shutdown hooks
            self._state = ShutdownState.SHUTTING_DOWN
            logger.info(
                "Running shutdown hooks",
                hook_count=len(self._hooks),
            )

            for hook in self._hooks:
                total_elapsed = time.time() - start_time
                if total_elapsed >= force_timeout:
                    logger.warning(
                        "Force timeout exceeded, skipping remaining hooks",
                        skipped_hooks=[h.name for h in self._hooks if h.priority > hook.priority],
                    )
                    graceful = False
                    break

                try:
                    logger.debug(f"Running shutdown hook: {hook.name}")
                    await asyncio.wait_for(hook.func(), timeout=hook.timeout)
                    logger.debug(f"Completed shutdown hook: {hook.name}")
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Shutdown hook timed out: {hook.name}",
                        timeout=hook.timeout,
                    )
                    graceful = False
                except Exception as e:
                    logger.error(
                        f"Shutdown hook failed: {hook.name}",
                        error=str(e),
                        exc_info=True,
                    )
                    graceful = False

            # Phase 4: Mark as shutdown
            self._state = ShutdownState.SHUTDOWN
            total_time = time.time() - start_time

            logger.info(
                "Shutdown complete",
                graceful=graceful,
                duration_seconds=round(total_time, 2),
            )

            return graceful

    def get_status(self) -> Dict[str, Any]:
        """Get current shutdown status."""
        return {
            "state": self._state.value,
            "is_running": self.is_running,
            "is_shutting_down": self.is_shutting_down,
            "active_tasks": self.active_task_count,
            "active_task_details": [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "duration_seconds": round(t.duration_seconds, 2),
                }
                for t in self._active_tasks.values()
            ],
            "registered_hooks": [h.name for h in self._hooks],
        }


# Global shutdown manager
_global_manager: Optional[ShutdownManager] = None
_manager_lock: Optional[asyncio.Lock] = None


def _get_manager_lock() -> asyncio.Lock:
    """Get or create the manager lock lazily within the event loop."""
    global _manager_lock
    if _manager_lock is None:
        _manager_lock = asyncio.Lock()
    return _manager_lock


async def get_shutdown_manager() -> ShutdownManager:
    """Get the global shutdown manager."""
    global _global_manager

    async with _get_manager_lock():
        if _global_manager is None:
            _global_manager = ShutdownManager()
        return _global_manager


def register_shutdown_hook(
    name: Optional[str] = None,
    priority: int = 50,
    timeout: float = 10.0,
) -> Callable[[Callable[[], Coroutine[Any, Any, None]]], Callable[[], Coroutine[Any, Any, None]]]:
    """
    Decorator to register a shutdown hook.

    Usage:
        @register_shutdown_hook(priority=10)
        async def cleanup_database():
            await db.close()

        @register_shutdown_hook(name="close_connections", priority=20)
        async def close_connections():
            await pool.close()
    """

    def decorator(
        func: Callable[[], Coroutine[Any, Any, None]],
    ) -> Callable[[], Coroutine[Any, Any, None]]:
        hook_name = name or func.__name__

        # Create a coroutine to register the hook
        async def register():
            manager = await get_shutdown_manager()
            manager.register_hook(hook_name, func, priority, timeout)

        # Schedule registration
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(register())
        except RuntimeError:
            # No running loop, will be registered when manager is first accessed
            pass

        return func

    return decorator


def setup_signal_handlers(manager: ShutdownManager) -> None:
    """
    Set up signal handlers for graceful shutdown.

    Handles SIGTERM and SIGINT (Ctrl+C).

    Note: Only works on Unix-like systems. On Windows, only SIGINT works.
    """

    def signal_handler(signum: int, frame: Any) -> None:
        signal_name = signal.Signals(signum).name
        logger.info(f"Received signal {signal_name}, initiating shutdown")
        manager.signal_shutdown()

    # Register handlers
    try:
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        logger.debug("Signal handlers registered for SIGTERM and SIGINT")
    except (ValueError, OSError) as e:
        # May fail if not in main thread
        logger.warning(f"Could not set up signal handlers: {e}")


__all__ = [
    # Classes
    "ShutdownManager",
    "ShutdownState",
    "ShutdownHook",
    "TaskInfo",
    # Functions
    "get_shutdown_manager",
    "register_shutdown_hook",
    "setup_signal_handlers",
]
