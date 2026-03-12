"""
Swarm Bridge Service.

HTTP client to the Swarm API that handles task submission, status polling,
and routing outcome feedback to ag3ntwerk's metacognition system.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default Swarm API URL
DEFAULT_SWARM_URL = "http://localhost:8766"


class SwarmBridgeService:
    """
    Service for communicating with the Claude Swarm API.

    Submits tasks, polls for results, and feeds outcomes
    back into the ag3ntwerk metacognition system.
    """

    def __init__(
        self,
        swarm_url: str = DEFAULT_SWARM_URL,
        metacognition_service=None,
        poll_interval: float = 2.0,
    ):
        self.swarm_url = swarm_url.rstrip("/")
        self.metacognition_service = metacognition_service
        self.poll_interval = poll_interval
        self._pending_callbacks: Dict[str, Callable] = {}

    async def is_swarm_available(self) -> bool:
        """Check if the Swarm API is reachable."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.swarm_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def get_swarm_status(self) -> Dict[str, Any]:
        """Get the current Swarm status."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.swarm_url}/status") as resp:
                if resp.status != 200:
                    raise Exception(f"Swarm API error: {resp.status}")
                return await resp.json()

    async def submit_task(
        self,
        prompt: str,
        agent_code: str = "",
        priority: str = "normal",
        timeout: int = 300,
        metadata: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None,
    ) -> str:
        """
        Submit a task to the Swarm.

        Args:
            prompt: Task prompt.
            agent_code: ag3ntwerk agent code submitting this task.
            priority: Task priority (low, normal, high, critical).
            timeout: Timeout in seconds.
            metadata: Additional metadata.
            callback: Optional async callback(result) when task completes.

        Returns:
            task_id from the Swarm.
        """
        import aiohttp

        payload = {
            "prompt": prompt,
            "name": f"[{agent_code}] {prompt[:50]}" if agent_code else prompt[:50],
            "priority": priority,
            "timeout": timeout,
            "metadata": {
                **(metadata or {}),
                "csuite_agent": agent_code,
                "source": "csuite_bridge",
            },
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.swarm_url}/tasks",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise Exception(f"Swarm task submit failed: {error}")
                data = await resp.json()

        task_id = data["task_id"]
        logger.info(f"Swarm task submitted: {task_id} by {agent_code}")

        if callback:
            self._pending_callbacks[task_id] = callback

        return task_id

    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a Swarm task."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.swarm_url}/tasks/{task_id}") as resp:
                if resp.status == 404:
                    return None
                if resp.status != 200:
                    raise Exception(f"Swarm API error: {resp.status}")
                return await resp.json()

    async def wait_for_task(
        self,
        task_id: str,
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """
        Poll until a task completes or times out.

        Returns:
            Task result dict.
        """
        start = time.time()
        while (time.time() - start) < timeout:
            result = await self.get_task_result(task_id)
            if result and result.get("status") in ("completed", "failed"):
                # Feed outcome to metacognition
                await self._record_outcome(task_id, result)

                # Call callback if registered
                cb = self._pending_callbacks.pop(task_id, None)
                if cb:
                    try:
                        await cb(result)
                    except Exception as e:
                        logger.warning(f"Task callback error: {e}")

                return result
            await asyncio.sleep(self.poll_interval)

        raise TimeoutError(f"Swarm task {task_id} did not complete within {timeout}s")

    async def _record_outcome(self, task_id: str, result: Dict[str, Any]) -> None:
        """Feed a task outcome into the metacognition service."""
        if not self.metacognition_service:
            return

        try:
            agent_code = result.get("metadata", {}).get("csuite_agent", "")
            if not agent_code:
                return

            success = result.get("status") == "completed"
            duration = result.get("duration_seconds", 0) * 1000

            self.metacognition_service.on_task_completed(
                agent_code=agent_code,
                task_id=task_id,
                task_type=result.get("metadata", {}).get("task_type", "swarm_task"),
                success=success,
                duration_ms=duration,
                context={
                    "source": "swarm_bridge",
                    "model": result.get("result", {}).get("model", ""),
                    "tool_calls": result.get("result", {}).get("tool_calls", []),
                },
            )
            logger.info(f"Metacognition outcome recorded for {agent_code}: {task_id}")
        except Exception as e:
            logger.warning(f"Failed to record metacognition outcome: {e}")

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get available models from the Swarm."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.swarm_url}/models") as resp:
                if resp.status != 200:
                    return []
                return await resp.json()

    async def get_routing_insights(self) -> Dict[str, Any]:
        """Get routing performance insights from the Swarm."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.swarm_url}/routing/stats") as resp:
                if resp.status != 200:
                    return {}
                return await resp.json()
