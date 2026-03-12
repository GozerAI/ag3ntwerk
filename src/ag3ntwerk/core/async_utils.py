"""
Async utility helpers for ag3ntwerk.

Provides helpers to bridge synchronous SDK calls into async code
without repeating boilerplate.
"""

import asyncio
import functools
from typing import Any, Callable, TypeVar

T = TypeVar("T")


async def run_sync(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Run a synchronous function in the default executor (thread pool).

    Replaces the common pattern::

        loop = asyncio.get_event_loop()
        def _inner():
            return some_blocking_call(...)
        return await loop.run_in_executor(None, _inner)

    With::

        return await run_sync(some_blocking_call, arg1, arg2)

    Args:
        fn: Synchronous callable to execute in a thread.
        *args: Positional arguments forwarded to *fn*.
        **kwargs: Keyword arguments forwarded to *fn*.

    Returns:
        The return value of *fn*.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))
