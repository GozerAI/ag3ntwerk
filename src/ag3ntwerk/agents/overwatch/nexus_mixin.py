"""Nexus bridge integration mixin for Overwatch."""

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.core.base import Task, TaskResult

if TYPE_CHECKING:
    from ag3ntwerk.agents.overwatch.models import StrategicContext

# NexusBridge integration (optional)
try:
    from ag3ntwerk.agents.bridges.nexus_bridge import NexusBridge, NexusBridgeConfig

    NEXUS_BRIDGE_AVAILABLE = True
except ImportError:
    NEXUS_BRIDGE_AVAILABLE = False
    NexusBridge = None
    NexusBridgeConfig = None

logger = get_logger(__name__)


class NexusMixin:
    """Nexus bridge integration for Overwatch."""

    async def connect_to_nexus(
        self,
        redis_url: str = "redis://localhost:6379",
        channel_prefix: str = "ag3ntwerk:nexus",
        timeout_seconds: int = 30,
    ) -> bool:
        """
        Connect to the Nexus strategic brain via Redis.

        Args:
            redis_url: Redis connection URL
            channel_prefix: Channel prefix for pub/sub communication
            timeout_seconds: Timeout for requests

        Returns:
            True if connection successful

        Example:
            ```python
            cos = Overwatch()
            connected = await cos.connect_to_nexus("redis://localhost:6379")
            if connected:
                print("Connected to Nexus strategic brain")
            ```
        """
        if not NEXUS_BRIDGE_AVAILABLE:
            logger.error("NexusBridge not available. Install with: pip install redis")
            return False

        if not self._nexus_bridge:
            config = NexusBridgeConfig(
                redis_url=redis_url,
                channel_prefix=channel_prefix,
                timeout_seconds=timeout_seconds,
            )
            self._nexus_bridge = NexusBridge(config)

        connected = await self._nexus_bridge.connect()
        if connected:
            logger.info(f"Connected to Nexus at {redis_url}")
            # Sync initial context
            context = await self._nexus_bridge.sync_context()
            if context:
                self._drift_monitor.update_context(context)
                logger.info("Synced strategic context from Nexus")

            # Start listening for execution requests from Nexus
            await self.start_nexus_execution_listener()

        return connected

    async def disconnect_from_nexus(self) -> None:
        """Disconnect from Nexus strategic brain."""
        if self._nexus_bridge:
            await self._nexus_bridge.disconnect()
            logger.info("Disconnected from Nexus")

    def is_nexus_connected(self) -> bool:
        """Check if connected to Nexus strategic brain."""
        return self._nexus_bridge is not None and self._nexus_bridge.is_connected

    async def escalate_to_nexus(
        self,
        drift_context: Optional[Dict[str, Any]] = None,
    ) -> Optional["StrategicContext"]:
        """
        Escalate a drift situation to Nexus for strategic guidance.

        Args:
            drift_context: Optional override for drift context.
                          If not provided, uses current drift summary.

        Returns:
            Updated StrategicContext from Nexus, or None if unavailable

        Example:
            ```python
            if cos.get_drift_status()["should_escalate"]:
                new_context = await cos.escalate_to_nexus()
                if new_context:
                    print(f"Got guidance: {new_context.routing_priorities}")
            ```
        """
        if not self._nexus_bridge or not self._nexus_bridge.is_connected:
            logger.warning("Cannot escalate: Nexus bridge not connected")
            return None

        context = drift_context or self._drift_monitor.get_drift_summary()
        self._metrics["escalations_to_coo"] += 1

        try:
            new_context = await self._nexus_bridge.request_strategic_guidance(context)
            if new_context:
                self._drift_monitor.update_context(new_context)
                self._drift_monitor.mark_escalated()
                logger.info("Received strategic guidance from Nexus")
            return new_context
        except Exception as e:
            logger.error(f"Failed to escalate to Nexus: {e}")
            return None

    async def report_outcome_to_nexus(
        self,
        task_result: TaskResult,
    ) -> bool:
        """
        Report task outcome to Nexus for cross-system learning.

        Args:
            task_result: The completed task result

        Returns:
            True if report was sent successfully

        Example:
            ```python
            result = await cos.execute(task)
            await cos.report_outcome_to_nexus(result)
            ```
        """
        if not self._nexus_bridge or not self._nexus_bridge.is_connected:
            return False

        try:
            metrics = {
                "task_id": task_result.task_id,
                "success": task_result.success,
                "error": task_result.error,
                "metrics": task_result.metrics or {},
                "source": "Overwatch",
            }
            return await self._nexus_bridge.report_outcomes(metrics)
        except Exception as e:
            logger.error(f"Failed to report outcome to Nexus: {e}")
            return False

    async def sync_context_from_nexus(self) -> Optional["StrategicContext"]:
        """
        Sync strategic context from Nexus.

        Returns:
            Current StrategicContext or None if unavailable
        """
        if not self._nexus_bridge or not self._nexus_bridge.is_connected:
            return None

        try:
            context = await self._nexus_bridge.sync_context()
            if context:
                self._drift_monitor.update_context(context)
                # Broadcast to all agents
                self._broadcast_nexus_context({"strategic_context": context})
                logger.info("Synced strategic context from Nexus")
            return context
        except Exception as e:
            logger.error(f"Failed to sync context from Nexus: {e}")
            return None

    async def publish_health_to_nexus(self) -> bool:
        """
        Publish current health status to Nexus.

        Returns:
            True if published successfully
        """
        if not self._nexus_bridge or not self._nexus_bridge.is_connected:
            return False

        try:
            health_data = {
                "cos_metrics": self.get_metrics(),
                "drift_status": self.get_drift_status(),
                "agent_health": self.get_agent_health(),
                "learning_enabled": self.is_learning_enabled(),
                "metacognition_insights": self._get_metacognition_insights(),
            }
            return await self._nexus_bridge.publish_health_status(health_data)
        except Exception as e:
            logger.error(f"Failed to publish health to Nexus: {e}")
            return False

    async def subscribe_to_nexus_directives(
        self,
        callback,
    ) -> None:
        """
        Subscribe to real-time directives from Nexus.

        Args:
            callback: Async function to call when directive received.
                     Signature: async def callback(directive: Dict[str, Any])

        Example:
            ```python
            async def handle_directive(directive):
                print(f"Received directive: {directive['type']}")
                if directive['type'] == 'update_routing':
                    # Handle routing update
                    pass

            await cos.subscribe_to_nexus_directives(handle_directive)
            ```
        """
        if not self._nexus_bridge or not self._nexus_bridge.is_connected:
            logger.warning("Cannot subscribe: Nexus bridge not connected")
            return

        await self._nexus_bridge.subscribe_to_directives(callback)

    async def _handle_nexus_execution_request(
        self,
        request: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle a task execution request from Nexus.

        Nexus (AutonomousCOO) can request ag3ntwerk to execute tasks on its behalf.
        This method:
        1. Parses the execution request
        2. Creates a Task from the request
        3. Routes to the appropriate agent (or uses target_agent hint)
        4. Returns the result

        Args:
            request: Execution request from Nexus containing:
                - task_id: Unique task identifier
                - task_type: Type of task to execute
                - title: Task title/summary
                - description: Full task description
                - target_agent: Suggested agent code (e.g., "Forge", "Echo")
                - context: Additional context for execution

        Returns:
            Execution result dictionary with:
                - success: Whether execution succeeded
                - output: Task output/result
                - error: Error message if failed
                - confidence: Confidence score
                - duration_ms: Execution time
        """
        import time

        start_time = time.perf_counter()

        task_id = request.get("task_id", f"nexus-{datetime.now(timezone.utc).timestamp()}")
        task_type = request.get("task_type", "general")
        title = request.get("title", "")
        description = request.get("description", "")
        target_agent = request.get("target_agent")
        context = request.get("context", {})

        logger.info(
            f"Received execution request from Nexus: {task_id} "
            f"(type={task_type}, target={target_agent})"
        )

        try:
            # Create task from request
            task = Task(
                id=task_id,
                task_type=task_type,
                description=description or title,
                context={
                    **(context or {}),
                    "nexus_request": True,
                    "target_agent": target_agent,
                    "original_title": title,
                },
            )

            # If Nexus specified a target agent and we have it, route there directly
            if target_agent and target_agent in self._subordinates:
                logger.info(f"Routing to Nexus-specified agent: {target_agent}")
                result = await self.delegate(task, target_agent)
            else:
                # Use normal routing
                result = await self.execute(task)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Build response
            response = {
                "success": result.success,
                "output": result.output if result.output else {},
                "error": result.error,
                "confidence": result.metrics.get("confidence", 0.8) if result.metrics else 0.8,
                "duration_ms": duration_ms,
                "executor": (
                    target_agent or result.metrics.get("handled_by") if result.metrics else None
                ),
            }

            logger.info(
                f"Completed Nexus execution request {task_id}: "
                f"success={result.success}, duration={duration_ms:.0f}ms"
            )

            # Report outcome to Nexus if connected
            if self._nexus_bridge and self._nexus_bridge.is_connected:
                await self._nexus_bridge.publish_execution_result(task_id, response)

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Failed to execute Nexus request {task_id}: {e}")
            return {
                "success": False,
                "output": {},
                "error": str(e),
                "confidence": 0.0,
                "duration_ms": duration_ms,
            }

    async def start_nexus_execution_listener(self) -> None:
        """
        Start listening for execution requests from Nexus.

        This is called automatically by connect_to_nexus() but can also be
        called manually if you need to restart the listener.

        The listener runs as a background task and handles incoming
        execution requests from Nexus AutonomousCOO.
        """
        if not self._nexus_bridge or not self._nexus_bridge.is_connected:
            logger.warning("Cannot start listener: Nexus bridge not connected")
            return

        logger.info("Starting Nexus execution request listener")
        asyncio.create_task(
            self._nexus_bridge.subscribe_to_execution_requests(self._handle_nexus_execution_request)
        )

    def _broadcast_nexus_context(self, context: Dict[str, Any]) -> None:
        """Broadcast strategic context from Nexus to all registered agents.

        Args:
            context: Strategic context dictionary to propagate
        """
        if not hasattr(self, "_subordinates"):
            return
        for agent_code, agent in self._subordinates.items():
            try:
                agent.receive_strategic_context(context)
            except Exception as e:
                logger.debug("Failed to broadcast context to %s: %s", agent_code, e)

    def get_nexus_status(self) -> Dict[str, Any]:
        """
        Get Nexus connection status.

        Returns:
            Dictionary with connection status and details
        """
        if not self._nexus_bridge:
            return {
                "connected": False,
                "available": NEXUS_BRIDGE_AVAILABLE,
                "error": None if NEXUS_BRIDGE_AVAILABLE else "NexusBridge not installed",
            }

        return {
            "connected": self._nexus_bridge.is_connected,
            "available": True,
            "config": (
                {
                    "redis_url": self._nexus_bridge.config.redis_url,
                    "channel_prefix": self._nexus_bridge.config.channel_prefix,
                    "timeout_seconds": self._nexus_bridge.config.timeout_seconds,
                }
                if self._nexus_bridge.is_connected
                else None
            ),
        }
