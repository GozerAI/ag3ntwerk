"""
Bridge for communication with external Nexus (Nexus) service.

Nexus is the strategic intelligence layer that provides:
- Strategic context and routing rules
- Performance thresholds and SLOs
- Guidance when drift is detected
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ag3ntwerk.agents.overwatch.models import StrategicContext

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class NexusBridgeConfig:
    """Configuration for Nexus bridge."""

    redis_url: str = field(
        default_factory=lambda: os.environ.get("REDIS_URL", "redis://localhost:6379")
    )
    channel_prefix: str = "ag3ntwerk:nexus"
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0


class NexusBridge:
    """
    Bridge for communicating with external Nexus service.

    Communication patterns:
    - Request/Response: For strategic guidance requests
    - Pub/Sub: For context updates and broadcasts
    - Metrics: For reporting outcomes to Nexus
    """

    def __init__(self, config: Optional[NexusBridgeConfig] = None):
        self.config = config or NexusBridgeConfig()
        self._connected = False
        self._redis = None
        self._last_context_sync: Optional[datetime] = None

    @property
    def is_connected(self) -> bool:
        """Check if bridge is connected to Nexus service."""
        return self._connected

    async def connect(self) -> bool:
        """Connect to Nexus service via Redis."""
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(self.config.redis_url)
            await self._redis.ping()
            self._connected = True
            logger.info("Connected to Nexus bridge")
            return True
        except ImportError:
            logger.error("redis package not installed. Install with: pip install redis")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Nexus: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Nexus service."""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Disconnected from Nexus bridge")

    async def request_strategic_guidance(
        self,
        drift_context: Dict[str, Any],
    ) -> Optional[StrategicContext]:
        """
        Request strategic guidance from Nexus due to drift.

        Args:
            drift_context: Current drift state and metrics

        Returns:
            Updated StrategicContext or None if unavailable
        """
        if not self._connected:
            logger.warning("Nexus bridge not connected")
            return None

        request_channel = f"{self.config.channel_prefix}:guidance:request"
        response_channel = f"{self.config.channel_prefix}:guidance:response"

        request = {
            "type": "guidance_request",
            "drift_context": drift_context,
            "timestamp": _utcnow().isoformat(),
        }

        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(response_channel)

            await self._redis.publish(request_channel, json.dumps(request))

            async def wait_for_response():
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        return json.loads(message["data"])

            response = await asyncio.wait_for(
                wait_for_response(), timeout=self.config.timeout_seconds
            )

            await pubsub.unsubscribe(response_channel)
            await pubsub.close()

            if response and response.get("context"):
                logger.info("Received strategic guidance from Nexus")
                return StrategicContext(**response["context"])

        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for Nexus guidance")
        except Exception as e:
            logger.error(f"Error requesting guidance: {e}")

        return None

    async def report_outcomes(
        self,
        metrics: Dict[str, Any],
    ) -> bool:
        """
        Report task outcomes to Nexus for learning.

        Args:
            metrics: Outcome metrics to report

        Returns:
            True if report was sent successfully
        """
        if not self._connected:
            return False

        channel = f"{self.config.channel_prefix}:outcomes"

        try:
            await self._redis.publish(
                channel,
                json.dumps(
                    {
                        "type": "outcome_report",
                        "metrics": metrics,
                        "timestamp": _utcnow().isoformat(),
                    }
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to report outcomes: {e}")
            return False

    async def sync_context(self) -> Optional[StrategicContext]:
        """
        Sync strategic context from Nexus.

        Returns:
            Current StrategicContext or None if unavailable
        """
        if not self._connected:
            return None

        try:
            context_key = f"{self.config.channel_prefix}:context:current"
            data = await self._redis.get(context_key)
            if data:
                self._last_context_sync = _utcnow()
                context_data = json.loads(data)
                return StrategicContext(**context_data)
        except Exception as e:
            logger.error(f"Failed to sync context: {e}")

        return None

    async def publish_health_status(
        self,
        health_data: Dict[str, Any],
    ) -> bool:
        """
        Publish Overwatch health status to Nexus.

        Args:
            health_data: Current health metrics

        Returns:
            True if published successfully
        """
        if not self._connected:
            return False

        channel = f"{self.config.channel_prefix}:health"

        try:
            await self._redis.publish(
                channel,
                json.dumps(
                    {
                        "type": "health_status",
                        "source": "Overwatch",
                        "data": health_data,
                        "timestamp": _utcnow().isoformat(),
                    }
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish health status: {e}")
            return False

    async def subscribe_to_directives(
        self,
        callback,
    ) -> None:
        """
        Subscribe to real-time directives from Nexus.

        Args:
            callback: Async function to call when directive received
        """
        if not self._connected:
            logger.warning("Cannot subscribe: Nexus bridge not connected")
            return

        channel = f"{self.config.channel_prefix}:directives"

        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(channel)

            async for message in pubsub.listen():
                if message["type"] == "message":
                    directive = json.loads(message["data"])
                    await callback(directive)

        except Exception as e:
            logger.error(f"Error in directive subscription: {e}")

    async def subscribe_to_execution_requests(
        self,
        callback,
    ) -> None:
        """
        Subscribe to execution requests from Nexus.

        Nexus can request ag3ntwerk to execute tasks on its behalf.

        Args:
            callback: Async function to call when execution request received.
                      Should return execution result dict.
        """
        if not self._connected:
            logger.warning("Cannot subscribe: Nexus bridge not connected")
            return

        request_channel = f"{self.config.channel_prefix}:execute:request"

        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(request_channel)
            logger.info(f"Subscribed to execution requests on {request_channel}")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        request = json.loads(message["data"])
                        logger.info(
                            f"Received execution request: {request.get('request_id')} "
                            f"for agent {request.get('target_agent')}"
                        )

                        # Execute via callback and send response
                        result = await callback(request)

                        # Send response back to Nexus
                        await self._send_execution_response(
                            request_id=request.get("request_id"),
                            result=result,
                        )

                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in execution request: {e}")
                    except Exception as e:
                        logger.error(f"Error handling execution request: {e}")

        except asyncio.CancelledError:
            logger.info("Execution request subscription cancelled")
        except Exception as e:
            logger.error(f"Error in execution request subscription: {e}")

    async def _send_execution_response(
        self,
        request_id: str,
        result: Dict[str, Any],
    ) -> bool:
        """
        Send execution response back to Nexus.

        Args:
            request_id: Original request ID to correlate response
            result: Execution result to send

        Returns:
            True if sent successfully
        """
        if not self._connected:
            return False

        response_channel = f"{self.config.channel_prefix}:execute:response"

        try:
            response = {
                "type": "execution_response",
                "request_id": request_id,
                "success": result.get("success", False),
                "output": result.get("output", {}),
                "error": result.get("error"),
                "confidence": result.get("confidence", 0.8),
                "duration_ms": result.get("duration_ms", 0),
                "timestamp": _utcnow().isoformat(),
            }

            await self._redis.publish(response_channel, json.dumps(response))
            logger.debug(f"Sent execution response for request {request_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send execution response: {e}")
            return False

    async def publish_execution_result(
        self,
        task_id: str,
        result: Dict[str, Any],
    ) -> bool:
        """
        Publish execution result for a specific task.

        This is used when Overwatch completes a task that was requested by Nexus.

        Args:
            task_id: The task ID that was executed
            result: Execution result with success, output, etc.

        Returns:
            True if published successfully
        """
        if not self._connected:
            return False

        response_channel = f"{self.config.channel_prefix}:execute:response"

        try:
            response = {
                "type": "execution_result",
                "task_id": task_id,
                "success": result.get("success", False),
                "output": result.get("output", {}),
                "error": result.get("error"),
                "confidence": result.get("confidence", 0.8),
                "duration_ms": result.get("duration_ms", 0),
                "timestamp": _utcnow().isoformat(),
            }

            await self._redis.publish(response_channel, json.dumps(response))
            logger.info(f"Published execution result for task {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish execution result: {e}")
            return False
