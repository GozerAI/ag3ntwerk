"""
Bridge for communication with external Forge (Forge) service.

Forge handles:
- Code generation and review
- Architecture decisions
- Development pipelines
- Technical operations
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ag3ntwerk.core.base import Task, TaskResult

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class ForgeBridgeConfig:
    """Configuration for Forge bridge."""

    redis_url: str = "redis://localhost:6379"
    channel_prefix: str = "ag3ntwerk:forge"
    timeout_seconds: int = 300  # Development tasks can be slow
    retry_attempts: int = 3
    retry_delay_seconds: float = 2.0


class ForgeBridge:
    """
    Bridge for communicating with external Forge service.

    Forge is the technical execution layer that handles development tasks,
    code generation, architecture decisions, and technical operations.
    """

    def __init__(self, config: Optional[ForgeBridgeConfig] = None):
        self.config = config or ForgeBridgeConfig()
        self._connected = False
        self._redis = None
        self._pending_tasks: Dict[str, asyncio.Future] = {}

    @property
    def is_connected(self) -> bool:
        """Check if bridge is connected to Forge service."""
        return self._connected

    async def connect(self) -> bool:
        """Connect to Forge service via Redis."""
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(self.config.redis_url)
            await self._redis.ping()
            self._connected = True
            logger.info("Connected to Forge bridge")

            # Start response listener
            asyncio.create_task(self._listen_for_responses())

            return True
        except ImportError:
            logger.error("redis package not installed. Install with: pip install redis")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Forge: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Forge service."""
        if self._redis:
            # Cancel pending tasks
            for future in self._pending_tasks.values():
                future.cancel()
            self._pending_tasks.clear()

            await self._redis.close()
            self._connected = False
            logger.info("Disconnected from Forge bridge")

    async def _listen_for_responses(self) -> None:
        """Background task to listen for task responses."""
        if not self._redis:
            return

        channel = f"{self.config.channel_prefix}:responses"

        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(channel)

            async for message in pubsub.listen():
                if message["type"] == "message":
                    response = json.loads(message["data"])
                    task_id = response.get("task_id")

                    if task_id and task_id in self._pending_tasks:
                        future = self._pending_tasks.pop(task_id)
                        if not future.cancelled():
                            future.set_result(response)

        except Exception as e:
            logger.error(f"Error in response listener: {e}")

    async def delegate_task(self, task: Task) -> TaskResult:
        """
        Delegate a development task to Forge.

        Args:
            task: The task to delegate

        Returns:
            TaskResult from Forge execution
        """
        if not self._connected:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="Forge bridge not connected",
            )

        request_channel = f"{self.config.channel_prefix}:tasks"

        # Create future for response
        response_future = asyncio.get_running_loop().create_future()
        self._pending_tasks[task.id] = response_future

        try:
            # Publish task
            await self._redis.publish(
                request_channel,
                json.dumps(
                    {
                        "type": "task_delegation",
                        "task": task.to_dict(),
                        "timestamp": _utcnow().isoformat(),
                    }
                ),
            )

            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=self.config.timeout_seconds)

            return TaskResult(
                task_id=task.id,
                success=response.get("success", False),
                output=response.get("output"),
                error=response.get("error"),
                metrics=response.get("metrics", {}),
            )

        except asyncio.TimeoutError:
            self._pending_tasks.pop(task.id, None)
            logger.warning(f"Task {task.id} timed out waiting for Forge response")
            return TaskResult(
                task_id=task.id,
                success=False,
                error="Forge task execution timed out",
            )
        except Exception as e:
            self._pending_tasks.pop(task.id, None)
            logger.error(f"Failed to delegate task to Forge: {e}")
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
            )

    async def get_status(self) -> Dict[str, Any]:
        """
        Get Forge service status.

        Returns:
            Status dictionary with health and metrics
        """
        if not self._connected:
            return {
                "connected": False,
                "available": False,
            }

        try:
            status_key = f"{self.config.channel_prefix}:status"
            data = await self._redis.get(status_key)

            if data:
                status = json.loads(data)
                status["connected"] = True
                return status

            return {
                "connected": True,
                "available": True,
                "status": "unknown",
            }

        except Exception as e:
            logger.error(f"Failed to get Forge status: {e}")
            return {
                "connected": True,
                "available": False,
                "error": str(e),
            }

    async def request_code_review(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Request a code review from Forge.

        Args:
            code: The code to review
            context: Additional context (language, standards, etc.)

        Returns:
            Review results with suggestions and issues
        """
        if not self._connected:
            return {"error": "Forge bridge not connected"}

        channel = f"{self.config.channel_prefix}:review:request"
        response_channel = f"{self.config.channel_prefix}:review:response"

        request_id = f"review_{_utcnow().timestamp()}"

        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(response_channel)

            await self._redis.publish(
                channel,
                json.dumps(
                    {
                        "type": "code_review_request",
                        "request_id": request_id,
                        "code": code,
                        "context": context or {},
                        "timestamp": _utcnow().isoformat(),
                    }
                ),
            )

            async def wait_for_response():
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        response = json.loads(message["data"])
                        if response.get("request_id") == request_id:
                            return response

            response = await asyncio.wait_for(
                wait_for_response(), timeout=self.config.timeout_seconds
            )

            await pubsub.unsubscribe(response_channel)
            await pubsub.close()

            return response.get("review", {})

        except asyncio.TimeoutError:
            logger.warning("Code review request timed out")
            return {"error": "Code review timed out"}
        except Exception as e:
            logger.error(f"Code review request failed: {e}")
            return {"error": str(e)}

    async def get_architecture_recommendation(
        self,
        requirements: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Get architecture recommendations from Forge.

        Args:
            requirements: Project requirements and constraints

        Returns:
            Architecture recommendations
        """
        if not self._connected:
            return {"error": "Forge bridge not connected"}

        channel = f"{self.config.channel_prefix}:architecture:request"

        try:
            await self._redis.publish(
                channel,
                json.dumps(
                    {
                        "type": "architecture_request",
                        "requirements": requirements,
                        "timestamp": _utcnow().isoformat(),
                    }
                ),
            )

            # Architecture recommendations are async - check status key
            # This is a simplified implementation
            return {"status": "request_submitted"}

        except Exception as e:
            logger.error(f"Architecture request failed: {e}")
            return {"error": str(e)}
