"""
Network Discovery - Authorized network scanning and device detection.

Provides controlled network discovery for the ag3ntwerk distributed
orchestration system. All scanning requires explicit authorization
and only discovers devices that respond to standard probes.

IMPORTANT: This module only scans networks that are explicitly configured.
It does NOT auto-assimilate or make changes to discovered devices.
All enrollment requires explicit operator approval.

Primary owners: Forge, Sentinel
"""

import asyncio
import ipaddress
import json
import logging
import socket
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class DeviceRole(str, Enum):
    """Role a discovered device can serve in the fleet."""

    UNKNOWN = "unknown"
    COMPUTE_NODE = "compute_node"
    STORAGE_NODE = "storage_node"
    GPU_NODE = "gpu_node"
    EDGE_NODE = "edge_node"
    CONTROLLER = "controller"
    GATEWAY = "gateway"


class DeviceStatus(str, Enum):
    """Status of a discovered device."""

    DISCOVERED = "discovered"
    PROBING = "probing"
    PROFILED = "profiled"
    ENROLLED = "enrolled"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    UNREACHABLE = "unreachable"
    REJECTED = "rejected"


class ScanProtocol(str, Enum):
    """Protocols used for device discovery."""

    ICMP_PING = "icmp_ping"
    TCP_CONNECT = "tcp_connect"
    MDNS = "mdns"
    SSDP = "ssdp"
    ARP_SCAN = "arp_scan"
    AGENTWERK_BEACON = "ag3ntwerk_beacon"


@dataclass
class PortScanResult:
    """Result from scanning a single port."""

    port: int
    open: bool
    service: str = ""
    banner: str = ""
    response_ms: float = 0.0


@dataclass
class DeviceFingerprint:
    """Fingerprint data from probing a device."""

    os_family: str = "unknown"
    os_version: str = ""
    hostname: str = ""
    mac_address: str = ""
    open_ports: List[PortScanResult] = field(default_factory=list)
    services: Dict[str, str] = field(default_factory=dict)
    has_ssh: bool = False
    has_http: bool = False
    has_agent: bool = False
    agent_version: str = ""
    response_time_ms: float = 0.0
    probed_at: Optional[datetime] = None


@dataclass
class DiscoveredDevice:
    """A device found during network scanning."""

    id: str = field(default_factory=lambda: str(uuid4()))
    ip_address: str = ""
    hostname: str = ""
    mac_address: str = ""
    status: DeviceStatus = DeviceStatus.DISCOVERED
    role: DeviceRole = DeviceRole.UNKNOWN
    fingerprint: Optional[DeviceFingerprint] = None
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    enrolled: bool = False
    enrollment_approved_by: str = ""
    enrollment_approved_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ip_address": self.ip_address,
            "hostname": self.hostname,
            "mac_address": self.mac_address,
            "status": self.status.value,
            "role": self.role.value,
            "fingerprint": (
                {
                    "os_family": self.fingerprint.os_family,
                    "os_version": self.fingerprint.os_version,
                    "hostname": self.fingerprint.hostname,
                    "open_ports": [
                        {"port": p.port, "open": p.open, "service": p.service}
                        for p in self.fingerprint.open_ports
                    ],
                    "services": self.fingerprint.services,
                    "has_ssh": self.fingerprint.has_ssh,
                    "has_http": self.fingerprint.has_http,
                    "has_agent": self.fingerprint.has_agent,
                    "agent_version": self.fingerprint.agent_version,
                    "response_time_ms": self.fingerprint.response_time_ms,
                }
                if self.fingerprint
                else None
            ),
            "discovered_at": self.discovered_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "enrolled": self.enrolled,
            "enrollment_approved_by": self.enrollment_approved_by,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class ScanTarget:
    """A network range configured for scanning."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    cidr: str = ""
    description: str = ""
    enabled: bool = True
    scan_interval_minutes: int = 60
    last_scanned: Optional[datetime] = None
    protocols: List[ScanProtocol] = field(default_factory=lambda: [ScanProtocol.TCP_CONNECT])
    probe_ports: List[int] = field(
        default_factory=lambda: [22, 80, 443, 8000, 8080, 9090, 6379, 5432]
    )
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "cidr": self.cidr,
            "description": self.description,
            "enabled": self.enabled,
            "scan_interval_minutes": self.scan_interval_minutes,
            "last_scanned": self.last_scanned.isoformat() if self.last_scanned else None,
            "protocols": [p.value for p in self.protocols],
            "probe_ports": self.probe_ports,
        }


# Well-known port to service mapping
KNOWN_SERVICES: Dict[int, str] = {
    22: "ssh",
    80: "http",
    443: "https",
    3000: "dev-server",
    3306: "mysql",
    5432: "postgresql",
    6379: "redis",
    8000: "ag3ntwerk-api",
    8080: "http-alt",
    8443: "https-alt",
    9090: "prometheus",
    9200: "elasticsearch",
    27017: "mongodb",
}

# ag3ntwerk agent beacon port
AGENTWERK_AGENT_PORT = 9876
AGENTWERK_BEACON_MAGIC = b"AGENTWERK_BEACON_V1"


class NetworkDiscoveryEngine:
    """
    Network discovery engine for authorized device detection.

    Scans configured network ranges to discover devices, probe their
    capabilities, and prepare them for fleet enrollment.

    All scanning is opt-in: networks must be explicitly added as scan targets.
    All enrollment requires explicit operator approval.
    """

    def __init__(self):
        self._scan_targets: Dict[str, ScanTarget] = {}
        self._discovered_devices: Dict[str, DiscoveredDevice] = {}
        self._scan_history: List[Dict[str, Any]] = []
        self._device_by_ip: Dict[str, str] = {}  # ip -> device_id
        self._scan_lock = asyncio.Lock()

    # ---- Scan Target Management ----

    def add_scan_target(
        self,
        name: str,
        cidr: str,
        description: str = "",
        scan_interval_minutes: int = 60,
        probe_ports: Optional[List[int]] = None,
    ) -> ScanTarget:
        """
        Add a network range to scan.

        Args:
            name: Human-readable name for this target
            cidr: Network CIDR notation (e.g. "192.168.1.0/24")
            description: What this network is
            scan_interval_minutes: How often to re-scan
            probe_ports: Specific ports to probe on discovered hosts
        """
        # Validate CIDR
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid CIDR notation '{cidr}': {e}")

        # Safety: refuse absurdly large scans
        if network.num_addresses > 65536:
            raise ValueError(
                f"Network {cidr} has {network.num_addresses} addresses. "
                f"Maximum supported is /16 (65536 addresses)."
            )

        target = ScanTarget(
            name=name,
            cidr=cidr,
            description=description,
            scan_interval_minutes=scan_interval_minutes,
            probe_ports=probe_ports or [22, 80, 443, 8000, 8080, 9090],
        )

        self._scan_targets[target.id] = target
        logger.info(f"Added scan target: {name} ({cidr})")
        return target

    def remove_scan_target(self, target_id: str) -> bool:
        """Remove a scan target."""
        if target_id in self._scan_targets:
            target = self._scan_targets.pop(target_id)
            logger.info(f"Removed scan target: {target.name}")
            return True
        return False

    def list_scan_targets(self) -> List[Dict[str, Any]]:
        """List all configured scan targets."""
        return [t.to_dict() for t in self._scan_targets.values()]

    # ---- Scanning ----

    async def scan_network(
        self,
        target_id: Optional[str] = None,
        timeout_per_host: float = 2.0,
        concurrency: int = 50,
    ) -> Dict[str, Any]:
        """
        Scan configured networks to discover devices.

        Args:
            target_id: Scan a specific target, or all if None
            timeout_per_host: Timeout per host in seconds
            concurrency: Max concurrent connection attempts
        """
        async with self._scan_lock:
            targets = []
            if target_id:
                if target_id not in self._scan_targets:
                    raise KeyError(f"Scan target not found: {target_id}")
                targets = [self._scan_targets[target_id]]
            else:
                targets = [t for t in self._scan_targets.values() if t.enabled]

            if not targets:
                return {
                    "scanned": 0,
                    "discovered": 0,
                    "message": "No scan targets configured. Add a target first.",
                }

            scan_start = datetime.now(timezone.utc)
            total_discovered = 0
            total_scanned = 0
            scan_results = []

            for target in targets:
                result = await self._scan_target(target, timeout_per_host, concurrency)
                target.last_scanned = datetime.now(timezone.utc)
                total_discovered += result["new_devices"]
                total_scanned += result["hosts_scanned"]
                scan_results.append(result)

            scan_record = {
                "scan_id": str(uuid4()),
                "started_at": scan_start.isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "targets_scanned": len(targets),
                "hosts_scanned": total_scanned,
                "new_devices_found": total_discovered,
                "total_known_devices": len(self._discovered_devices),
                "results": scan_results,
            }
            self._scan_history.append(scan_record)

            logger.info(
                f"Network scan complete: {total_scanned} hosts scanned, "
                f"{total_discovered} new devices found"
            )
            return scan_record

    async def _scan_target(
        self,
        target: ScanTarget,
        timeout: float,
        concurrency: int,
    ) -> Dict[str, Any]:
        """Scan a single target network."""
        network = ipaddress.ip_network(target.cidr, strict=False)
        hosts = [str(h) for h in network.hosts()]

        semaphore = asyncio.Semaphore(concurrency)
        new_devices = 0
        updated_devices = 0

        async def probe_host(ip: str):
            nonlocal new_devices, updated_devices
            async with semaphore:
                is_alive, open_ports = await self._probe_host(ip, target.probe_ports, timeout)
                if is_alive:
                    if ip in self._device_by_ip:
                        # Update existing device
                        device_id = self._device_by_ip[ip]
                        device = self._discovered_devices[device_id]
                        device.last_seen = datetime.now(timezone.utc)
                        if device.status == DeviceStatus.UNREACHABLE:
                            device.status = DeviceStatus.DISCOVERED
                        updated_devices += 1
                    else:
                        # New device
                        device = DiscoveredDevice(
                            ip_address=ip,
                            fingerprint=DeviceFingerprint(
                                open_ports=open_ports,
                                services={
                                    KNOWN_SERVICES.get(p.port, f"port-{p.port}"): str(p.port)
                                    for p in open_ports
                                    if p.open
                                },
                                has_ssh=any(p.port == 22 and p.open for p in open_ports),
                                has_http=any(
                                    p.port in (80, 443, 8000, 8080) and p.open for p in open_ports
                                ),
                                has_agent=any(
                                    p.port == AGENTWERK_AGENT_PORT and p.open for p in open_ports
                                ),
                                probed_at=datetime.now(timezone.utc),
                            ),
                        )
                        device.status = DeviceStatus.PROFILED
                        self._discovered_devices[device.id] = device
                        self._device_by_ip[ip] = device.id
                        new_devices += 1

        tasks = [probe_host(ip) for ip in hosts]
        await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "target": target.name,
            "cidr": target.cidr,
            "hosts_scanned": len(hosts),
            "new_devices": new_devices,
            "updated_devices": updated_devices,
        }

    async def _probe_host(
        self,
        ip: str,
        ports: List[int],
        timeout: float,
    ) -> Tuple[bool, List[PortScanResult]]:
        """Probe a single host with TCP connect scan."""
        results = []
        host_alive = False

        for port in ports:
            try:
                start = time.monotonic()
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=timeout,
                )
                elapsed = (time.monotonic() - start) * 1000
                writer.close()
                await writer.wait_closed()

                results.append(
                    PortScanResult(
                        port=port,
                        open=True,
                        service=KNOWN_SERVICES.get(port, ""),
                        response_ms=elapsed,
                    )
                )
                host_alive = True
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                results.append(PortScanResult(port=port, open=False))

        return host_alive, results

    # ---- Device Management ----

    def get_discovered_devices(
        self,
        status: Optional[DeviceStatus] = None,
        role: Optional[DeviceRole] = None,
        enrolled_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get discovered devices with optional filtering."""
        devices = list(self._discovered_devices.values())

        if status:
            devices = [d for d in devices if d.status == status]
        if role:
            devices = [d for d in devices if d.role == role]
        if enrolled_only:
            devices = [d for d in devices if d.enrolled]

        return [d.to_dict() for d in devices]

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific device."""
        device = self._discovered_devices.get(device_id)
        return device.to_dict() if device else None

    def assign_device_role(
        self, device_id: str, role: DeviceRole, tags: Optional[List[str]] = None
    ) -> bool:
        """Assign a role and tags to a discovered device."""
        device = self._discovered_devices.get(device_id)
        if not device:
            return False
        device.role = role
        if tags:
            device.tags = list(set(device.tags + tags))
        logger.info(f"Assigned role {role.value} to device {device.ip_address}")
        return True

    def approve_enrollment(self, device_id: str, approved_by: str) -> bool:
        """
        Approve a device for fleet enrollment.

        REQUIRES explicit human approval - devices are never auto-enrolled.
        """
        device = self._discovered_devices.get(device_id)
        if not device:
            return False
        if device.status == DeviceStatus.REJECTED:
            logger.warning(f"Cannot enroll rejected device: {device.ip_address}")
            return False

        device.enrolled = True
        device.status = DeviceStatus.ENROLLED
        device.enrollment_approved_by = approved_by
        device.enrollment_approved_at = datetime.now(timezone.utc)
        logger.info(f"Device {device.ip_address} enrolled by {approved_by}")
        return True

    def reject_device(self, device_id: str, reason: str = "") -> bool:
        """Reject a device from fleet enrollment."""
        device = self._discovered_devices.get(device_id)
        if not device:
            return False
        device.status = DeviceStatus.REJECTED
        device.enrolled = False
        device.metadata["rejection_reason"] = reason
        logger.info(f"Device {device.ip_address} rejected: {reason}")
        return True

    def remove_device(self, device_id: str) -> bool:
        """Remove a device from the discovered devices list."""
        device = self._discovered_devices.get(device_id)
        if not device:
            return False
        self._device_by_ip.pop(device.ip_address, None)
        self._discovered_devices.pop(device_id, None)
        return True

    # ---- Status and History ----

    def get_discovery_status(self) -> Dict[str, Any]:
        """Get current discovery engine status."""
        devices = list(self._discovered_devices.values())
        return {
            "scan_targets": len(self._scan_targets),
            "total_devices": len(devices),
            "devices_by_status": {
                status.value: len([d for d in devices if d.status == status])
                for status in DeviceStatus
                if any(d.status == status for d in devices)
            },
            "devices_by_role": {
                role.value: len([d for d in devices if d.role == role])
                for role in DeviceRole
                if any(d.role == role for d in devices)
            },
            "enrolled_count": len([d for d in devices if d.enrolled]),
            "last_scan": self._scan_history[-1] if self._scan_history else None,
            "total_scans": len(self._scan_history),
        }

    def get_scan_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent scan history."""
        return sorted(
            self._scan_history,
            key=lambda x: x["started_at"],
            reverse=True,
        )[:limit]
