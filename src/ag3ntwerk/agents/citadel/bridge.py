"""
Sentinel Bridge - Integration layer between Citadel (Citadel) and Sentinel platform.

This module provides a clean bridge to the Sentinel security platform,
enabling Citadel to leverage Sentinel's hierarchical agents for security operations.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import Task, TaskResult

logger = logging.getLogger(__name__)


class SentinelBridge:
    """
    Bridge between ag3ntwerk Citadel and Sentinel platform.

    Provides unified access to Sentinel's hierarchical agents:
    - Guardian: Security operations (threat detection, blocking, quarantine)
    - Healer: Incident response and recovery
    - Discovery: Asset discovery and classification
    - Optimizer: Network optimization
    - Compliance: Compliance monitoring and reporting
    - DisasterRecovery: DR operations
    - CostManager: Security cost optimization

    Usage:
        bridge = SentinelBridge()
        await bridge.connect()

        # Execute security task
        result = await bridge.execute_security_task(task)

        # Or route to specific agent
        result = await bridge.route_to_agent("guardian", "block_ip", {"ip": "10.0.0.1"})
    """

    # Task type to Sentinel domain mapping
    TASK_DOMAIN_MAP = {
        # ===========================================
        # Guardian domain (security) - threat ops
        # ===========================================
        "threat_detection": "security",
        "threat_analysis": "security",
        "threat_hunting": "security",
        "threat_mitigation": "security",
        "threat_blocking": "security",
        "threat_investigation": "security",
        "block_ip": "security",
        "unblock_ip": "security",
        "quarantine": "security",
        "unquarantine": "security",
        "firewall_rule": "security",
        "firewall_update": "security",
        "acl_update": "security",
        "ids_analysis": "security",
        "siem_alert": "security",
        "malware_scan": "security",
        "intrusion_detection": "security",
        "security_event": "security",
        "security_alert": "security",
        # SAST/DAST - application security
        "sast_scan": "security",
        "dast_scan": "security",
        "code_security_scan": "security",
        "dependency_scan": "security",
        "container_scan": "security",
        "image_scan": "security",
        # ===========================================
        # Healer domain (reliability/incident response)
        # ===========================================
        "incident_response": "reliability",
        "incident_investigation": "reliability",
        "incident_triage": "reliability",
        "incident_containment": "reliability",
        "incident_eradication": "reliability",
        "incident_recovery": "reliability",
        "incident_post_mortem": "reliability",
        "service_restart": "reliability",
        "service_scale": "reliability",
        "service_config": "reliability",
        "failover": "reliability",
        "failover_auto": "reliability",
        "failover_dns": "reliability",
        "failover_loadbalancer": "reliability",
        "health_check": "reliability",
        "health_monitor": "reliability",
        "healing_recovery": "reliability",
        "healing_cleanup": "reliability",
        "healing_cache": "reliability",
        # ===========================================
        # Discovery domain - scanning & classification
        # ===========================================
        "vulnerability_scan": "discovery",
        "vulnerability_scanning": "discovery",
        "vulnerability_assessment": "discovery",
        "vulnerability_remediation": "discovery",
        "patch_management": "discovery",
        "patch_status": "discovery",
        "asset_discovery": "discovery",
        "asset_inventory": "discovery",
        "network_scan": "discovery",
        "port_scan": "discovery",
        "arp_scan": "discovery",
        "ping_scan": "discovery",
        "classify_device": "discovery",
        "fingerprint_device": "discovery",
        "classify_vendor": "discovery",
        "topology_discovery": "discovery",
        "topology_lldp": "discovery",
        "topology_cdp": "discovery",
        "inventory_tracking": "discovery",
        "inventory_change": "discovery",
        "inventory_compliance": "discovery",
        # ===========================================
        # Optimizer domain (network)
        # ===========================================
        "network_optimization": "network",
        "apply_qos": "network",
        "traffic_analysis": "network",
        "traffic_shaping": "network",
        "bandwidth_management": "network",
        "latency_optimization": "network",
        "route_optimization": "network",
        "netflow_analysis": "network",
        "sflow_analysis": "network",
        # ===========================================
        # Compliance domain - audit & regulatory
        # ===========================================
        "compliance_assessment": "compliance",
        "compliance_audit": "compliance",
        "compliance_scan": "compliance",
        "compliance_check": "compliance",
        "compliance_report": "compliance",
        "policy_enforcement": "compliance",
        "policy_audit": "compliance",
        "framework_mapping": "compliance",
        "regulatory_audit": "compliance",
        "pci_compliance": "compliance",
        "hipaa_compliance": "compliance",
        "soc2_compliance": "compliance",
        "iso27001_compliance": "compliance",
        "gdpr_compliance": "compliance",
        "certification_audit": "compliance",
        "evidence_collection": "compliance",
        # ===========================================
        # Disaster Recovery domain
        # ===========================================
        "disaster_recovery": "dr",
        "backup_validation": "dr",
        "backup_verify": "dr",
        "backup_status": "dr",
        "recovery_test": "dr",
        "rto_test": "dr",
        "rpo_test": "dr",
        "failover_test": "dr",
        "runbook_execute": "dr",
        "runbook_status": "dr",
        "dr_plan_validate": "dr",
        "dr_compliance": "dr",
        # ===========================================
        # Cost domain - security cost management
        # ===========================================
        "security_cost_analysis": "cost",
        "cost_optimization": "cost",
        "cost_forecast": "cost",
        "cost_alert": "cost",
        "cost_budget": "cost",
        "cost_tracking": "cost",
        "cost_rightsize": "cost",
        "cost_chargeback": "cost",
        "cost_allocation": "cost",
    }

    # Agent name mapping
    AGENT_NAME_MAP = {
        "guardian": "security",
        "healer": "reliability",
        "discovery": "discovery",
        "optimizer": "network",
        "compliance": "compliance",
        "disaster_recovery": "dr",
        "cost_manager": "cost",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Sentinel bridge.

        Args:
            config: Optional configuration for Sentinel connection
        """
        self._config = config or {}
        self._sentinel_agent = None
        self._connected = False
        self._connection_time: Optional[datetime] = None
        self._tasks_executed = 0
        self._tasks_succeeded = 0

    @property
    def is_connected(self) -> bool:
        """Check if bridge is connected to Sentinel."""
        return self._connected and self._sentinel_agent is not None

    @property
    def connection_uptime(self) -> Optional[float]:
        """Get connection uptime in seconds."""
        if self._connection_time:
            return (datetime.now(timezone.utc) - self._connection_time).total_seconds()
        return None

    @property
    def stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "connected": self._connected,
            "uptime_seconds": self.connection_uptime,
            "tasks_executed": self._tasks_executed,
            "tasks_succeeded": self._tasks_succeeded,
            "success_rate": (
                self._tasks_succeeded / self._tasks_executed if self._tasks_executed > 0 else 0.0
            ),
        }

    async def connect(self, config_path: Optional[str] = None) -> bool:
        """
        Connect to the Sentinel platform.

        Args:
            config_path: Optional path to Sentinel configuration file

        Returns:
            True if connection successful
        """
        if self._connected:
            logger.info("Sentinel bridge already connected")
            return True

        try:
            # Import SentinelAgent from sentinel package
            from sentinel.nexus_agent import SentinelAgent

            # Create SentinelAgent instance
            self._sentinel_agent = SentinelAgent(config_path=config_path)

            # Initialize the agent (starts engine and hierarchical agents)
            success = await self._sentinel_agent.initialize()

            if success:
                self._connected = True
                self._connection_time = datetime.now(timezone.utc)
                logger.info(
                    f"Sentinel bridge connected successfully "
                    f"(version: {self._sentinel_agent.version})"
                )
                return True
            else:
                logger.error("Failed to initialize SentinelAgent")
                return False

        except ImportError as e:
            logger.warning(f"Sentinel package not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Sentinel: {e}")
            return False

    async def disconnect(self) -> bool:
        """
        Disconnect from Sentinel platform.

        Returns:
            True if disconnection successful
        """
        if not self._connected:
            return True

        try:
            if self._sentinel_agent:
                await self._sentinel_agent.shutdown()

            self._sentinel_agent = None
            self._connected = False
            self._connection_time = None
            logger.info("Sentinel bridge disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Sentinel: {e}")
            return False

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a ag3ntwerk Task via Sentinel.

        Args:
            task: ag3ntwerk Task to execute

        Returns:
            TaskResult with execution results
        """
        if not self.is_connected:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="Sentinel bridge not connected",
            )

        self._tasks_executed += 1

        try:
            # Convert ag3ntwerk task to Sentinel task format
            sentinel_task = self._convert_task(task)

            # Execute via SentinelAgent
            result = await self._sentinel_agent.execute(sentinel_task)

            success = result.get("status") == "success"
            if success:
                self._tasks_succeeded += 1

            return TaskResult(
                task_id=task.id,
                success=success,
                output=result.get("result"),
                error=result.get("metadata", {}).get("error"),
                metrics={
                    "sentinel_agent": result.get("metadata", {}).get("agent"),
                    "sentinel_domain": result.get("metadata", {}).get("domain"),
                    "duration_ms": result.get("metadata", {}).get("duration_ms"),
                    "trace": result.get("trace", []),
                },
            )

        except Exception as e:
            logger.error(f"Sentinel task execution failed: {e}")
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
            )

    async def route_to_agent(
        self,
        agent_name: str,
        action: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Route a task directly to a specific Sentinel agent.

        Args:
            agent_name: Name of Sentinel agent (guardian, healer, etc.)
            action: Action to perform
            parameters: Action parameters
            context: Optional execution context

        Returns:
            Execution result dictionary
        """
        if not self.is_connected:
            return {
                "success": False,
                "error": "Sentinel bridge not connected",
            }

        self._tasks_executed += 1

        try:
            # Map agent name to domain
            domain = self.AGENT_NAME_MAP.get(agent_name, agent_name)

            # Create Sentinel task
            sentinel_task = {
                "task_id": f"citadel_{datetime.now(timezone.utc).timestamp()}",
                "task_type": f"{domain}.{action}",
                "parameters": parameters,
                "context": context or {},
            }

            # Execute
            result = await self._sentinel_agent.execute(sentinel_task)

            if result.get("status") == "success":
                self._tasks_succeeded += 1

            return {
                "success": result.get("status") == "success",
                "result": result.get("result"),
                "error": result.get("metadata", {}).get("error"),
                "agent": agent_name,
                "domain": domain,
                "action": action,
                "trace": result.get("trace", []),
            }

        except Exception as e:
            logger.error(f"Agent routing failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def get_agent_health(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get health status of Sentinel agents.

        Args:
            agent_name: Optional specific agent to check (all if None)

        Returns:
            Health status dictionary
        """
        if not self.is_connected:
            return {
                "healthy": False,
                "error": "Sentinel bridge not connected",
            }

        try:
            health = await self._sentinel_agent.health_check()
            return health
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
            }

    async def get_capabilities(self) -> List[str]:
        """
        Get list of Sentinel capabilities.

        Returns:
            List of capability names
        """
        if not self.is_connected:
            return []

        try:
            return [cap.value for cap in self._sentinel_agent.capabilities]
        except (AttributeError, TypeError) as e:
            import logging

            logging.getLogger(__name__).debug(f"Could not get sentinel capabilities: {e}")
            return []

    def _convert_task(self, task: Task) -> Dict[str, Any]:
        """
        Convert ag3ntwerk Task to Sentinel task format.

        Args:
            task: ag3ntwerk Task object

        Returns:
            Sentinel-compatible task dictionary
        """
        # Determine domain from task type
        domain = self.TASK_DOMAIN_MAP.get(task.task_type, "security")

        # Extract action from task type
        action = task.task_type.split("_")[-1] if "_" in task.task_type else "execute"

        return {
            "task_id": task.id,
            "task_type": f"{domain}.{action}",
            "parameters": task.context or {},
            "context": {
                "description": task.description,
                "priority": task.priority,
                "source": "ag3ntwerk.citadel",
                "original_type": task.task_type,
            },
        }


# Convenience function for quick bridge creation
async def create_sentinel_bridge(
    config: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None,
) -> Optional[SentinelBridge]:
    """
    Create and connect a Sentinel bridge.

    Args:
        config: Optional configuration dictionary
        config_path: Optional path to config file

    Returns:
        Connected SentinelBridge or None if connection failed
    """
    bridge = SentinelBridge(config)
    success = await bridge.connect(config_path)
    return bridge if success else None
