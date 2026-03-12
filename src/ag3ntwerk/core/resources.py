"""
Async Resource Management for ag3ntwerk.

Provides async context managers for proper resource lifecycle management:
- Database connections
- HTTP client pools
- LLM providers
- Cleanup guarantees

Usage:
    from ag3ntwerk.core.resources import AsyncResource, managed_resource

    # Define a resource
    class DatabaseConnection(AsyncResource):
        async def acquire(self):
            self.conn = await create_connection()
            return self.conn

        async def release(self):
            if self.conn:
                await self.conn.close()

    # Use as context manager
    async with DatabaseConnection() as conn:
        await conn.execute("SELECT 1")

    # Or with decorator
    @managed_resource
    async def get_database():
        conn = await create_connection()
        try:
            yield conn
        finally:
            await conn.close()
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Dict, Generic, List, Optional, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncResource(ABC, Generic[T]):
    """
    Base class for async resources with proper lifecycle management.

    Subclass this to create resources that need async setup and cleanup.
    """

    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__
        self._acquired = False
        self._resource: Optional[T] = None
        self._acquired_at: Optional[datetime] = None

    @abstractmethod
    async def acquire(self) -> T:
        """
        Acquire the resource.

        Called when entering the context manager.

        Returns:
            The acquired resource
        """
        pass

    @abstractmethod
    async def release(self) -> None:
        """
        Release the resource.

        Called when exiting the context manager (always, even on exception).
        """
        pass

    async def __aenter__(self) -> T:
        """Enter the async context manager."""
        if self._acquired:
            raise RuntimeError(f"Resource {self.name} already acquired")

        try:
            self._resource = await self.acquire()
            self._acquired = True
            self._acquired_at = datetime.now(timezone.utc)
            logger.debug(f"Acquired resource: {self.name}")
            return self._resource
        except Exception as e:
            logger.error(f"Failed to acquire resource {self.name}: {e}")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager."""
        if not self._acquired:
            return

        try:
            await self.release()
            logger.debug(f"Released resource: {self.name}")
        except Exception as e:
            logger.error(f"Error releasing resource {self.name}: {e}")
            # Don't suppress the original exception
        finally:
            self._acquired = False
            self._resource = None
            self._acquired_at = None

    @property
    def is_acquired(self) -> bool:
        """Check if resource is currently acquired."""
        return self._acquired

    @property
    def resource(self) -> Optional[T]:
        """Get the acquired resource (or None if not acquired)."""
        return self._resource

    @property
    def held_duration(self) -> Optional[float]:
        """Get how long the resource has been held (seconds)."""
        if self._acquired_at:
            return (datetime.now(timezone.utc) - self._acquired_at).total_seconds()
        return None


@dataclass
class ResourceStats:
    """Statistics about resource usage."""

    name: str
    acquisitions: int = 0
    releases: int = 0
    failures: int = 0
    total_hold_time_seconds: float = 0.0
    current_held: int = 0
    max_held: int = 0

    @property
    def avg_hold_time(self) -> float:
        """Average time resources are held."""
        if self.releases == 0:
            return 0.0
        return self.total_hold_time_seconds / self.releases


class ResourcePool(Generic[T]):
    """
    Pool of reusable async resources.

    Manages a pool of resources with automatic cleanup and size limits.

    Usage:
        pool = ResourcePool(
            create=create_connection,
            destroy=lambda c: c.close(),
            max_size=10,
        )

        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
    """

    def __init__(
        self,
        create: Callable[[], AsyncIterator[T]],
        destroy: Optional[Callable[[T], AsyncIterator[None]]] = None,
        max_size: int = 10,
        min_size: int = 0,
        max_idle_time: float = 300.0,
        name: str = "ResourcePool",
    ):
        """
        Initialize the resource pool.

        Args:
            create: Async factory function to create resources
            destroy: Async function to destroy resources
            max_size: Maximum pool size
            min_size: Minimum pool size to maintain
            max_idle_time: Max time a resource can be idle before eviction
            name: Pool name for logging
        """
        self._create = create
        self._destroy = destroy
        self._max_size = max_size
        self._min_size = min_size
        self._max_idle_time = max_idle_time
        self._name = name

        self._pool: asyncio.Queue[tuple[T, datetime]] = asyncio.Queue(maxsize=max_size)
        self._size = 0
        self._lock = asyncio.Lock()
        self._closed = False
        self._stats = ResourceStats(name=name)

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[T]:
        """
        Acquire a resource from the pool.

        Returns a pooled resource or creates a new one if needed.
        """
        if self._closed:
            raise RuntimeError(f"Pool {self._name} is closed")

        resource = await self._get_resource()
        self._stats.acquisitions += 1
        self._stats.current_held += 1
        self._stats.max_held = max(self._stats.max_held, self._stats.current_held)
        acquire_time = datetime.now(timezone.utc)

        try:
            yield resource
        finally:
            hold_time = (datetime.now(timezone.utc) - acquire_time).total_seconds()
            self._stats.total_hold_time_seconds += hold_time
            self._stats.current_held -= 1
            self._stats.releases += 1

            # Return to pool if not closed
            if not self._closed:
                await self._return_resource(resource)

    async def _get_resource(self) -> T:
        """Get a resource from the pool or create a new one."""
        # Try to get from pool
        try:
            while not self._pool.empty():
                resource, created_at = self._pool.get_nowait()
                idle_time = (datetime.now(timezone.utc) - created_at).total_seconds()

                # Check if too old
                if idle_time > self._max_idle_time:
                    async with self._lock:
                        self._size -= 1
                    if self._destroy:
                        try:
                            await self._destroy(resource)
                        except Exception as e:
                            logger.warning(f"Error destroying stale resource: {e}")
                    continue

                return resource
        except asyncio.QueueEmpty:
            pass

        # Create new resource
        async with self._lock:
            if self._size >= self._max_size:
                raise RuntimeError(f"Pool {self._name} exhausted (max={self._max_size})")
            self._size += 1

        try:
            resource = await self._create()
            return resource
        except Exception as e:
            async with self._lock:
                self._size -= 1
            self._stats.failures += 1
            raise

    async def _return_resource(self, resource: T) -> None:
        """Return a resource to the pool."""
        try:
            self._pool.put_nowait((resource, datetime.now(timezone.utc)))
        except asyncio.QueueFull:
            # Pool is full, destroy the resource
            async with self._lock:
                self._size -= 1
            if self._destroy:
                try:
                    await self._destroy(resource)
                except Exception as e:
                    logger.warning(f"Error destroying excess resource: {e}")

    async def close(self) -> None:
        """Close the pool and destroy all resources."""
        self._closed = True

        while not self._pool.empty():
            try:
                resource, _ = self._pool.get_nowait()
                if self._destroy:
                    try:
                        await self._destroy(resource)
                    except Exception as e:
                        logger.warning(f"Error destroying resource during close: {e}")
            except asyncio.QueueEmpty:
                break

        self._size = 0
        logger.info(f"Closed resource pool: {self._name}")

    @property
    def stats(self) -> ResourceStats:
        """Get pool statistics."""
        return self._stats

    @property
    def size(self) -> int:
        """Current pool size."""
        return self._size

    @property
    def available(self) -> int:
        """Number of available resources."""
        return self._pool.qsize()

    async def __aenter__(self) -> "ResourcePool[T]":
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context, closing pool."""
        await self.close()


class ResourceManager:
    """
    Central manager for all application resources.

    Tracks and manages multiple resources with coordinated cleanup.

    Usage:
        manager = ResourceManager()

        # Register resources
        manager.register("db", db_pool)
        manager.register("http", http_client)

        # Cleanup all
        await manager.cleanup()
    """

    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._cleanup_order: List[str] = []
        self._lock = asyncio.Lock()

    def register(
        self,
        name: str,
        resource: Any,
        cleanup: Optional[Callable[[], AsyncIterator[None]]] = None,
        priority: int = 50,
    ) -> None:
        """
        Register a resource for management.

        Args:
            name: Unique resource name
            resource: The resource object
            cleanup: Optional cleanup function (called if resource doesn't have __aexit__)
            priority: Cleanup priority (lower = cleaned up first)
        """
        self._resources[name] = {
            "resource": resource,
            "cleanup": cleanup,
            "priority": priority,
            "registered_at": datetime.now(timezone.utc),
        }

        # Maintain cleanup order
        self._cleanup_order.append(name)
        self._cleanup_order.sort(key=lambda n: self._resources[n]["priority"])

        logger.debug(f"Registered resource: {name}")

    def unregister(self, name: str) -> None:
        """Unregister a resource."""
        if name in self._resources:
            del self._resources[name]
            self._cleanup_order.remove(name)
            logger.debug(f"Unregistered resource: {name}")

    def get(self, name: str) -> Any:
        """Get a registered resource."""
        if name not in self._resources:
            raise KeyError(f"Resource not found: {name}")
        return self._resources[name]["resource"]

    async def cleanup(self, timeout: float = 30.0) -> Dict[str, bool]:
        """
        Cleanup all resources.

        Args:
            timeout: Maximum time for cleanup

        Returns:
            Dict mapping resource names to cleanup success status
        """
        results = {}

        async with self._lock:
            for name in self._cleanup_order:
                info = self._resources.get(name)
                if not info:
                    continue

                resource = info["resource"]
                cleanup_func = info["cleanup"]

                try:
                    # Try __aexit__ first
                    if hasattr(resource, "__aexit__"):
                        await asyncio.wait_for(
                            resource.__aexit__(None, None, None),
                            timeout=timeout,
                        )
                    elif hasattr(resource, "close"):
                        await asyncio.wait_for(resource.close(), timeout=timeout)
                    elif cleanup_func:
                        await asyncio.wait_for(cleanup_func(), timeout=timeout)

                    results[name] = True
                    logger.debug(f"Cleaned up resource: {name}")

                except asyncio.TimeoutError:
                    logger.warning(f"Cleanup timed out for resource: {name}")
                    results[name] = False
                except Exception as e:
                    logger.error(f"Error cleaning up resource {name}: {e}")
                    results[name] = False

            self._resources.clear()
            self._cleanup_order.clear()

        return results

    def list_resources(self) -> List[Dict[str, Any]]:
        """List all registered resources."""
        return [
            {
                "name": name,
                "type": type(info["resource"]).__name__,
                "priority": info["priority"],
                "registered_at": info["registered_at"].isoformat(),
            }
            for name, info in self._resources.items()
        ]


def managed_resource(func: Callable[..., AsyncIterator[T]]) -> Callable[..., AsyncIterator[T]]:
    """
    Decorator to create a managed async context manager.

    Usage:
        @managed_resource
        async def get_connection():
            conn = await create_connection()
            try:
                yield conn
            finally:
                await conn.close()

        async with get_connection() as conn:
            await conn.execute("...")
    """
    return asynccontextmanager(func)


# Global resource manager
_global_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = ResourceManager()
    return _global_manager


async def cleanup_all_resources(timeout: float = 30.0) -> Dict[str, bool]:
    """Cleanup all globally managed resources."""
    manager = get_resource_manager()
    return await manager.cleanup(timeout)


__all__ = [
    # Base class
    "AsyncResource",
    # Pool
    "ResourcePool",
    "ResourceStats",
    # Manager
    "ResourceManager",
    "get_resource_manager",
    "cleanup_all_resources",
    # Decorator
    "managed_resource",
]
