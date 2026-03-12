"""
Bridge for communication with external Sentinel (Sentinel/Citadel) service.

Sentinel handles:
- Network security monitoring
- Threat detection and response
- Security governance
- Compliance verification
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import Task, TaskResult

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class SentinelBridgeConfig:
    """Configuration for Sentinel bridge."""

    redis_url: str = "redis://localhost:6379"
    channel_prefix: str = "ag3ntwerk:sentinel"
    timeout_seconds: int = 60
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    # Security-specific settings
    alert_channel: str = "ag3ntwerk:sentinel:alerts"
    threat_level_threshold: str = "medium"  # low, medium, high, critical


class SentinelBridge:
    """
    Bridge for communicating with external Sentinel service.

    Sentinel is the security layer that monitors for threats, enforces
    security policies, and provides security intelligence to the ag3ntwerk.
    """

    def __init__(self, config: Optional[SentinelBridgeConfig] = None):
        self.config = config or SentinelBridgeConfig()
        self._connected = False
        self._redis = None
        self._alert_callbacks: List = []

    @property
    def is_connected(self) -> bool:
        """Check if bridge is connected to Sentinel service."""
        return self._connected

    async def connect(self) -> bool:
        """Connect to Sentinel service via Redis."""
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(self.config.redis_url)
            await self._redis.ping()
            self._connected = True
            logger.info("Connected to Sentinel bridge")
            return True
        except ImportError:
            logger.error("redis package not installed. Install with: pip install redis")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Sentinel: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Sentinel service."""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Disconnected from Sentinel bridge")

    async def delegate_task(self, task: Task) -> TaskResult:
        """
        Delegate a security task to Sentinel.

        Args:
            task: The security task to delegate

        Returns:
            TaskResult from Sentinel execution
        """
        if not self._connected:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="Sentinel bridge not connected",
            )

        request_channel = f"{self.config.channel_prefix}:tasks"
        response_channel = f"{self.config.channel_prefix}:responses:{task.id}"

        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(response_channel)

            await self._redis.publish(
                request_channel,
                json.dumps(
                    {
                        "type": "task_delegation",
                        "task": task.to_dict(),
                        "response_channel": response_channel,
                        "timestamp": _utcnow().isoformat(),
                    }
                ),
            )

            async def wait_for_response():
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        return json.loads(message["data"])

            response = await asyncio.wait_for(
                wait_for_response(), timeout=self.config.timeout_seconds
            )

            await pubsub.unsubscribe(response_channel)
            await pubsub.close()

            return TaskResult(
                task_id=task.id,
                success=response.get("success", False),
                output=response.get("output"),
                error=response.get("error"),
                metrics=response.get("metrics", {}),
            )

        except asyncio.TimeoutError:
            logger.warning(f"Task {task.id} timed out waiting for Sentinel response")
            return TaskResult(
                task_id=task.id,
                success=False,
                error="Sentinel task execution timed out",
            )
        except Exception as e:
            logger.error(f"Failed to delegate task to Sentinel: {e}")
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
            )

    async def get_threat_status(self) -> Dict[str, Any]:
        """
        Get current threat landscape from Sentinel.

        Returns:
            Threat status with current alerts and risk level
        """
        if not self._connected:
            return {
                "connected": False,
                "available": False,
            }

        try:
            status_key = f"{self.config.channel_prefix}:threat_status"
            data = await self._redis.get(status_key)

            if data:
                status = json.loads(data)
                status["connected"] = True
                return status

            return {
                "connected": True,
                "available": True,
                "threat_level": "unknown",
                "active_alerts": 0,
            }

        except Exception as e:
            logger.error(f"Failed to get threat status: {e}")
            return {
                "connected": True,
                "available": False,
                "error": str(e),
            }

    async def request_security_scan(
        self,
        target: str,
        scan_type: str = "vulnerability",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Request a security scan from Sentinel.

        Args:
            target: Target to scan (host, network, application)
            scan_type: Type of scan (vulnerability, compliance, penetration)
            options: Additional scan options

        Returns:
            Scan request status and ID
        """
        if not self._connected:
            return {"error": "Sentinel bridge not connected"}

        channel = f"{self.config.channel_prefix}:scans:request"

        scan_id = f"scan_{_utcnow().timestamp()}"

        try:
            await self._redis.publish(
                channel,
                json.dumps(
                    {
                        "type": "security_scan_request",
                        "scan_id": scan_id,
                        "target": target,
                        "scan_type": scan_type,
                        "options": options or {},
                        "timestamp": _utcnow().isoformat(),
                    }
                ),
            )

            return {
                "scan_id": scan_id,
                "status": "initiated",
                "target": target,
                "scan_type": scan_type,
            }

        except Exception as e:
            logger.error(f"Security scan request failed: {e}")
            return {"error": str(e)}

    async def get_scan_results(
        self,
        scan_id: str,
    ) -> Dict[str, Any]:
        """
        Get results of a security scan.

        Args:
            scan_id: ID of the scan to retrieve

        Returns:
            Scan results or status if still running
        """
        if not self._connected:
            return {"error": "Sentinel bridge not connected"}

        try:
            results_key = f"{self.config.channel_prefix}:scans:results:{scan_id}"
            data = await self._redis.get(results_key)

            if data:
                return json.loads(data)

            return {
                "scan_id": scan_id,
                "status": "pending",
            }

        except Exception as e:
            logger.error(f"Failed to get scan results: {e}")
            return {"error": str(e)}

    async def subscribe_to_alerts(
        self,
        callback,
        min_severity: str = "medium",
    ) -> None:
        """
        Subscribe to security alerts from Sentinel.

        Args:
            callback: Async function to call when alert received
            min_severity: Minimum severity level to receive (low, medium, high, critical)
        """
        if not self._connected:
            logger.warning("Cannot subscribe: Sentinel bridge not connected")
            return

        severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        min_level = severity_order.get(min_severity, 2)

        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(self.config.alert_channel)

            async for message in pubsub.listen():
                if message["type"] == "message":
                    alert = json.loads(message["data"])
                    alert_severity = alert.get("severity", "medium")

                    if severity_order.get(alert_severity, 2) >= min_level:
                        await callback(alert)

        except Exception as e:
            logger.error(f"Error in alert subscription: {e}")

    async def report_security_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        severity: str = "medium",
    ) -> bool:
        """
        Report a security event to Sentinel.

        Args:
            event_type: Type of security event
            details: Event details
            severity: Event severity (low, medium, high, critical)

        Returns:
            True if event was reported successfully
        """
        if not self._connected:
            return False

        channel = f"{self.config.channel_prefix}:events"

        try:
            await self._redis.publish(
                channel,
                json.dumps(
                    {
                        "type": "security_event",
                        "event_type": event_type,
                        "severity": severity,
                        "details": details,
                        "source": "Overwatch",
                        "timestamp": _utcnow().isoformat(),
                    }
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to report security event: {e}")
            return False

    async def get_compliance_status(
        self,
        framework: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get compliance status from Sentinel.

        Args:
            framework: Optional specific framework (e.g., "SOC2", "GDPR")

        Returns:
            Compliance status and any violations
        """
        if not self._connected:
            return {"error": "Sentinel bridge not connected"}

        try:
            if framework:
                status_key = f"{self.config.channel_prefix}:compliance:{framework}"
            else:
                status_key = f"{self.config.channel_prefix}:compliance:overall"

            data = await self._redis.get(status_key)

            if data:
                return json.loads(data)

            return {
                "status": "unknown",
                "framework": framework,
            }

        except Exception as e:
            logger.error(f"Failed to get compliance status: {e}")
            return {"error": str(e)}
