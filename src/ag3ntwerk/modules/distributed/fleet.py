"""
Fleet Orchestration Coordinator - Top-level fleet management.

Coordinates discovery, resource analysis, allocation, and provisioning
into a unified fleet management interface. This is the primary entry
point for the ag3ntwerk distributed orchestration system.

Primary owners: Nexus, Forge
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ag3ntwerk.modules.distributed.discovery import (
    NetworkDiscoveryEngine,
    DeviceRole,
    DeviceStatus,
)
from ag3ntwerk.modules.distributed.resources import (
    ResourceAnalysisEngine,
    CapabilityTier,
)
from ag3ntwerk.modules.distributed.allocator import (
    TaskAllocator,
    AllocationStrategy,
    WorkloadPriority,
    WorkloadRequirements,
)
from ag3ntwerk.modules.distributed.provisioner import (
    NodeProvisioner,
)
from ag3ntwerk.modules.distributed.relay import (
    RelayBridge,
    RelayRouter,
)

logger = logging.getLogger(__name__)


class FleetStatus(str, Enum):
    """Overall fleet operational status."""

    INITIALIZING = "initializing"
    DISCOVERING = "discovering"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    SCALING = "scaling"
    MAINTENANCE = "maintenance"


@dataclass
class FleetNode:
    """A node in the fleet with combined state."""

    node_id: str
    ip_address: str
    hostname: str = ""
    role: DeviceRole = DeviceRole.UNKNOWN
    enrolled: bool = False
    provisioned: bool = False
    healthy: bool = True
    last_heartbeat: Optional[datetime] = None
    capability_tier: CapabilityTier = CapabilityTier.MINIMAL
    active_workloads: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "ip_address": self.ip_address,
            "hostname": self.hostname,
            "role": self.role.value,
            "enrolled": self.enrolled,
            "provisioned": self.provisioned,
            "healthy": self.healthy,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "capability_tier": self.capability_tier.value,
            "active_workloads": self.active_workloads,
            "tags": self.tags,
        }


class FleetOrchestrator:
    """
    Top-level fleet orchestration coordinator.

    Provides a unified interface for:
    - Network discovery and device management
    - Resource profiling and capability scoring
    - Workload submission and intelligent allocation
    - Node provisioning and lifecycle management
    - Fleet-wide health monitoring
    """

    def __init__(self):
        self.discovery = NetworkDiscoveryEngine()
        self.resources = ResourceAnalysisEngine()
        self.allocator = TaskAllocator()
        self.provisioner = NodeProvisioner()

        # Hybrid cloud/local relay system
        self.relay_bridge = RelayBridge()
        self.relay_router = RelayRouter(bridge=self.relay_bridge)

        self._fleet_nodes: Dict[str, FleetNode] = {}
        self._fleet_status = FleetStatus.INITIALIZING
        self._event_log: List[Dict[str, Any]] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self._initialized = False

    # ====================================================================
    # Initialization
    # ====================================================================

    async def initialize(self) -> Dict[str, Any]:
        """
        Initialize the fleet orchestrator.

        Profiles the local (controller) node and sets up the fleet.
        """
        if self._initialized:
            return {"status": "already_initialized"}

        self._log_event("fleet_init", "Initializing fleet orchestrator")

        # Profile the local node (controller)
        local_profile = self.resources.profile_local_node()
        controller_node = FleetNode(
            node_id="local",
            ip_address="127.0.0.1",
            hostname=local_profile.hostname,
            role=DeviceRole.CONTROLLER,
            enrolled=True,
            provisioned=True,
            healthy=True,
            last_heartbeat=datetime.now(timezone.utc),
            capability_tier=local_profile.score.tier,
        )
        self._fleet_nodes["local"] = controller_node

        # Register with allocator
        self.allocator.register_node("local", local_profile.to_dict())

        self._fleet_status = FleetStatus.OPERATIONAL
        self._initialized = True

        self._log_event(
            "fleet_ready",
            f"Fleet initialized. Controller: {local_profile.hostname} "
            f"({local_profile.score.tier.value}, score={local_profile.score.overall:.1f})",
        )

        return {
            "status": "initialized",
            "controller": controller_node.to_dict(),
            "controller_resources": local_profile.to_dict(),
        }

    # ====================================================================
    # Discovery Workflow
    # ====================================================================

    async def discover_network(
        self,
        cidr: str,
        name: str = "",
        scan_ports: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Discover devices on a network.

        Args:
            cidr: Network to scan (e.g. "192.168.1.0/24")
            name: Human-readable name for this network
            scan_ports: Custom ports to probe
        """
        self._fleet_status = FleetStatus.DISCOVERING

        target = self.discovery.add_scan_target(
            name=name or f"scan-{cidr}",
            cidr=cidr,
            probe_ports=scan_ports or [22, 80, 443, 8000, 8080, 9090],
        )

        result = await self.discovery.scan_network(target_id=target.id)

        self._fleet_status = FleetStatus.OPERATIONAL
        self._log_event(
            "network_scan",
            f"Scanned {cidr}: {result.get('hosts_scanned', 0)} hosts, "
            f"{result.get('new_devices_found', 0)} new devices",
        )
        return result

    def get_discovered_devices(self) -> List[Dict[str, Any]]:
        """Get all discovered devices."""
        return self.discovery.get_discovered_devices()

    # ====================================================================
    # Enrollment Workflow
    # ====================================================================

    async def enroll_device(
        self,
        device_id: str,
        approved_by: str,
        role: DeviceRole = DeviceRole.COMPUTE_NODE,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Enroll a discovered device into the fleet.

        Requires explicit human approval via approved_by parameter.
        After enrollment, the device is profiled for resource capabilities.
        """
        # Approve in discovery
        success = self.discovery.approve_enrollment(device_id, approved_by)
        if not success:
            return {"success": False, "error": "Device not found or cannot be enrolled"}

        # Assign role
        self.discovery.assign_device_role(device_id, role, tags)

        # Get device info
        device_info = self.discovery.get_device(device_id)
        if not device_info:
            return {"success": False, "error": "Device data lost after enrollment"}

        ip = device_info["ip_address"]
        hostname = device_info.get("hostname", "")

        # Profile the node's resources
        profile = await self.resources.profile_remote_node(
            node_id=device_id,
            ip_address=ip,
            hostname=hostname,
        )

        # Create fleet node entry
        fleet_node = FleetNode(
            node_id=device_id,
            ip_address=ip,
            hostname=hostname,
            role=role,
            enrolled=True,
            provisioned=False,
            healthy=True,
            last_heartbeat=datetime.now(timezone.utc),
            capability_tier=profile.score.tier,
            tags=tags or [],
        )
        self._fleet_nodes[device_id] = fleet_node

        # Register with allocator
        self.allocator.register_node(device_id, profile.to_dict())

        self._log_event(
            "device_enrolled",
            f"Device {ip} enrolled as {role.value} by {approved_by} "
            f"(tier={profile.score.tier.value})",
        )

        return {
            "success": True,
            "node": fleet_node.to_dict(),
            "resources": profile.to_dict(),
        }

    # ====================================================================
    # Provisioning Workflow
    # ====================================================================

    async def provision_node(
        self,
        node_id: str,
        approved_by: str,
        include_docker: bool = False,
        include_gpu: bool = False,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Provision an enrolled node with dependencies and configuration.

        Creates a provision plan and executes it. The node must be
        enrolled first via enroll_device().
        """
        fleet_node = self._fleet_nodes.get(node_id)
        if not fleet_node:
            return {"success": False, "error": "Node not found in fleet"}
        if not fleet_node.enrolled:
            return {"success": False, "error": "Node must be enrolled before provisioning"}

        # Create provision plan
        plan = self.provisioner.create_provision_plan(
            node_id=node_id,
            ip_address=fleet_node.ip_address,
            hostname=fleet_node.hostname,
            approved_by=approved_by,
            include_docker=include_docker,
            include_gpu=include_gpu,
            custom_config=custom_config,
        )

        # Execute the plan
        result = await self.provisioner.execute_plan(plan.id)

        if result.stage.value == "complete":
            fleet_node.provisioned = True
            self._log_event(
                "node_provisioned", f"Node {fleet_node.ip_address} provisioned successfully"
            )
        else:
            self._log_event(
                "provision_failed",
                f"Node {fleet_node.ip_address} provisioning failed: {result.error}",
            )

        return {
            "success": result.stage.value == "complete",
            "plan": result.to_dict(),
        }

    # ====================================================================
    # Workload Distribution
    # ====================================================================

    def submit_workload(
        self,
        name: str,
        owner_executive: str,
        module: str = "",
        task_type: str = "",
        priority: str = "normal",
        min_cpu_cores: int = 1,
        min_memory_gb: float = 0.5,
        requires_gpu: bool = False,
        requires_docker: bool = False,
        affinity_tags: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submit a workload for distributed execution."""
        prio = (
            WorkloadPriority(priority)
            if priority in WorkloadPriority.__members__.values()
            else WorkloadPriority.NORMAL
        )

        reqs = WorkloadRequirements(
            min_cpu_cores=min_cpu_cores,
            min_memory_gb=min_memory_gb,
            requires_gpu=requires_gpu,
            requires_docker=requires_docker,
            affinity_tags=affinity_tags or [],
        )

        workload = self.allocator.submit_workload(
            name=name,
            owner_executive=owner_executive,
            module=module,
            task_type=task_type,
            priority=prio,
            requirements=reqs,
            context=context,
        )

        # Auto-allocate
        decision = self.allocator.allocate(workload.id)

        result = {
            "workload": workload.to_dict(),
            "allocated": decision is not None,
        }
        if decision:
            result["allocation"] = decision.to_dict()
            self._log_event(
                "workload_allocated",
                f"Workload '{name}' -> node {decision.node_id} " f"(score={decision.score:.1f})",
            )
        else:
            self._log_event("allocation_failed", f"No suitable node found for workload '{name}'")

        return result

    def complete_workload(
        self,
        workload_id: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark a workload as completed or failed."""
        success = self.allocator.complete_workload(workload_id, result, error)
        return {"success": success, "workload_id": workload_id}

    def set_allocation_strategy(self, strategy: str) -> Dict[str, Any]:
        """Set the fleet-wide allocation strategy."""
        try:
            strat = AllocationStrategy(strategy)
            self.allocator.set_strategy(strat)
            return {"success": True, "strategy": strategy}
        except ValueError:
            return {
                "success": False,
                "error": f"Unknown strategy: {strategy}",
                "valid_strategies": [s.value for s in AllocationStrategy],
            }

    # ====================================================================
    # Fleet Health and Monitoring
    # ====================================================================

    async def check_fleet_health(self) -> Dict[str, Any]:
        """Run a health check across all fleet nodes (direct or relayed)."""
        results = {}
        unhealthy = 0

        for node_id, node in self._fleet_nodes.items():
            if node_id == "local":
                node.healthy = True
                node.last_heartbeat = datetime.now(timezone.utc)
                results[node_id] = {"healthy": True, "latency_ms": 0}
                continue

            # Use relay router — transparently routes direct or via relay
            is_open, latency = await self.relay_router.tcp_probe(node.ip_address, 8000, timeout=5.0)

            if is_open:
                node.healthy = True
                node.last_heartbeat = datetime.now(timezone.utc)
                results[node_id] = {"healthy": True, "latency_ms": round(latency, 1)}
            else:
                node.healthy = False
                unhealthy += 1
                results[node_id] = {"healthy": False, "error": "unreachable"}

        total = len(self._fleet_nodes)
        if unhealthy == 0:
            self._fleet_status = FleetStatus.OPERATIONAL
        elif unhealthy < total:
            self._fleet_status = FleetStatus.DEGRADED
        else:
            self._fleet_status = FleetStatus.OFFLINE

        return {
            "status": self._fleet_status.value,
            "total_nodes": total,
            "healthy_nodes": total - unhealthy,
            "unhealthy_nodes": unhealthy,
            "nodes": results,
        }

    def remove_node(self, node_id: str) -> Dict[str, Any]:
        """Remove a node from the fleet."""
        if node_id == "local":
            return {"success": False, "error": "Cannot remove controller node"}

        fleet_node = self._fleet_nodes.pop(node_id, None)
        if not fleet_node:
            return {"success": False, "error": "Node not found"}

        self.allocator.unregister_node(node_id)
        self.discovery.remove_device(node_id)

        self._log_event("node_removed", f"Node {fleet_node.ip_address} removed from fleet")
        return {"success": True, "removed": node_id}

    # ====================================================================
    # Status and Reporting
    # ====================================================================

    def get_fleet_status(self) -> Dict[str, Any]:
        """Get comprehensive fleet status."""
        nodes = list(self._fleet_nodes.values())

        return {
            "status": self._fleet_status.value,
            "initialized": self._initialized,
            "nodes": {
                "total": len(nodes),
                "enrolled": len([n for n in nodes if n.enrolled]),
                "provisioned": len([n for n in nodes if n.provisioned]),
                "healthy": len([n for n in nodes if n.healthy]),
                "by_role": {
                    role.value: len([n for n in nodes if n.role == role])
                    for role in DeviceRole
                    if any(n.role == role for n in nodes)
                },
                "by_tier": {
                    tier.value: len([n for n in nodes if n.capability_tier == tier])
                    for tier in CapabilityTier
                    if any(n.capability_tier == tier for n in nodes)
                },
            },
            "fleet_resources": self.resources.get_fleet_summary(),
            "workloads": self.allocator.get_allocation_stats(),
            "discovery": self.discovery.get_discovery_status(),
            "relays": {
                "connected": len(self.relay_bridge.get_connected_relays()),
                "total": len(self.relay_bridge.get_all_relays()),
                "network_map": self.relay_bridge.get_network_map(),
            },
        }

    def get_fleet_nodes(self) -> List[Dict[str, Any]]:
        """Get all fleet nodes."""
        return [n.to_dict() for n in self._fleet_nodes.values()]

    def get_event_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get fleet event log."""
        return sorted(
            self._event_log,
            key=lambda x: x["timestamp"],
            reverse=True,
        )[:limit]

    def _log_event(self, event_type: str, message: str) -> None:
        """Log a fleet event."""
        self._event_log.append(
            {
                "id": str(uuid4()),
                "type": event_type,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info(f"[Fleet] {event_type}: {message}")
