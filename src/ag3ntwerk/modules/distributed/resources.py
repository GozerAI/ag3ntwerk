"""
Resource Analysis Engine - Profile and score compute node capabilities.

Analyzes enrolled nodes' hardware, software, and network characteristics
to build a capability map used by the task allocator for optimal
workload placement.

Primary owners: Forge, Sentinel
"""

import asyncio
import logging
import os
import platform
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class CapabilityTier(str, Enum):
    """Capability tier for resource scoring."""

    MINIMAL = "minimal"  # Raspberry Pi, low-end
    BASIC = "basic"  # Budget desktop/laptop
    STANDARD = "standard"  # Mid-range workstation
    HIGH = "high"  # High-end workstation / server
    ENTERPRISE = "enterprise"  # Multi-GPU server, high-mem


class ResourceDomain(str, Enum):
    """Domains of resource capability."""

    CPU_COMPUTE = "cpu_compute"
    GPU_COMPUTE = "gpu_compute"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    SPECIALIZED = "specialized"  # e.g., TPU, FPGA


@dataclass
class CPUProfile:
    """CPU resource profile."""

    architecture: str = ""
    model_name: str = ""
    physical_cores: int = 0
    logical_cores: int = 0
    clock_speed_mhz: float = 0.0
    cache_size_kb: int = 0
    load_percent: float = 0.0
    available_cores: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "architecture": self.architecture,
            "model_name": self.model_name,
            "physical_cores": self.physical_cores,
            "logical_cores": self.logical_cores,
            "clock_speed_mhz": self.clock_speed_mhz,
            "cache_size_kb": self.cache_size_kb,
            "load_percent": self.load_percent,
            "available_cores": self.available_cores,
        }


@dataclass
class MemoryProfile:
    """Memory resource profile."""

    total_bytes: int = 0
    available_bytes: int = 0
    used_percent: float = 0.0
    swap_total_bytes: int = 0
    swap_used_bytes: int = 0

    @property
    def total_gb(self) -> float:
        return self.total_bytes / (1024**3) if self.total_bytes else 0

    @property
    def available_gb(self) -> float:
        return self.available_bytes / (1024**3) if self.available_bytes else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_gb": round(self.total_gb, 2),
            "available_gb": round(self.available_gb, 2),
            "used_percent": round(self.used_percent, 1),
            "swap_total_gb": (
                round(self.swap_total_bytes / (1024**3), 2) if self.swap_total_bytes else 0
            ),
            "swap_used_gb": (
                round(self.swap_used_bytes / (1024**3), 2) if self.swap_used_bytes else 0
            ),
        }


@dataclass
class StorageProfile:
    """Storage resource profile."""

    total_bytes: int = 0
    available_bytes: int = 0
    used_percent: float = 0.0
    is_ssd: bool = False
    read_speed_mbps: float = 0.0
    write_speed_mbps: float = 0.0
    mount_points: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total_gb(self) -> float:
        return self.total_bytes / (1024**3) if self.total_bytes else 0

    @property
    def available_gb(self) -> float:
        return self.available_bytes / (1024**3) if self.available_bytes else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_gb": round(self.total_gb, 2),
            "available_gb": round(self.available_gb, 2),
            "used_percent": round(self.used_percent, 1),
            "is_ssd": self.is_ssd,
            "read_speed_mbps": self.read_speed_mbps,
            "write_speed_mbps": self.write_speed_mbps,
            "mount_points": self.mount_points,
        }


@dataclass
class GPUProfile:
    """GPU resource profile."""

    available: bool = False
    devices: List[Dict[str, Any]] = field(default_factory=list)
    total_vram_gb: float = 0.0
    cuda_available: bool = False
    cuda_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "device_count": len(self.devices),
            "devices": self.devices,
            "total_vram_gb": round(self.total_vram_gb, 2),
            "cuda_available": self.cuda_available,
            "cuda_version": self.cuda_version,
        }


@dataclass
class NetworkProfile:
    """Network capability profile."""

    bandwidth_mbps: float = 0.0
    latency_ms: float = 0.0
    interfaces: List[Dict[str, str]] = field(default_factory=list)
    public_ip: str = ""
    is_nat: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bandwidth_mbps": self.bandwidth_mbps,
            "latency_ms": self.latency_ms,
            "interface_count": len(self.interfaces),
            "interfaces": self.interfaces,
            "is_nat": self.is_nat,
        }


@dataclass
class SoftwareProfile:
    """Software environment profile."""

    os_name: str = ""
    os_version: str = ""
    kernel_version: str = ""
    python_version: str = ""
    docker_available: bool = False
    docker_version: str = ""
    container_runtime: str = ""
    installed_runtimes: List[str] = field(default_factory=list)
    package_managers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "os_name": self.os_name,
            "os_version": self.os_version,
            "kernel_version": self.kernel_version,
            "python_version": self.python_version,
            "docker_available": self.docker_available,
            "docker_version": self.docker_version,
            "container_runtime": self.container_runtime,
            "installed_runtimes": self.installed_runtimes,
            "package_managers": self.package_managers,
        }


@dataclass
class ResourceScore:
    """Composite capability score for a node."""

    overall: float = 0.0
    cpu_score: float = 0.0
    memory_score: float = 0.0
    storage_score: float = 0.0
    gpu_score: float = 0.0
    network_score: float = 0.0
    tier: CapabilityTier = CapabilityTier.MINIMAL
    suitable_workloads: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": round(self.overall, 2),
            "cpu_score": round(self.cpu_score, 2),
            "memory_score": round(self.memory_score, 2),
            "storage_score": round(self.storage_score, 2),
            "gpu_score": round(self.gpu_score, 2),
            "network_score": round(self.network_score, 2),
            "tier": self.tier.value,
            "suitable_workloads": self.suitable_workloads,
        }


@dataclass
class NodeResourceProfile:
    """Complete resource profile for a compute node."""

    node_id: str = ""
    ip_address: str = ""
    hostname: str = ""
    cpu: CPUProfile = field(default_factory=CPUProfile)
    memory: MemoryProfile = field(default_factory=MemoryProfile)
    storage: StorageProfile = field(default_factory=StorageProfile)
    gpu: GPUProfile = field(default_factory=GPUProfile)
    network: NetworkProfile = field(default_factory=NetworkProfile)
    software: SoftwareProfile = field(default_factory=SoftwareProfile)
    score: ResourceScore = field(default_factory=ResourceScore)
    profiled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "ip_address": self.ip_address,
            "hostname": self.hostname,
            "cpu": self.cpu.to_dict(),
            "memory": self.memory.to_dict(),
            "storage": self.storage.to_dict(),
            "gpu": self.gpu.to_dict(),
            "network": self.network.to_dict(),
            "software": self.software.to_dict(),
            "score": self.score.to_dict(),
            "profiled_at": self.profiled_at.isoformat(),
        }


class ResourceAnalysisEngine:
    """
    Resource analysis engine for profiling compute node capabilities.

    Collects hardware/software inventory from enrolled nodes and
    computes capability scores to guide workload placement.
    """

    def __init__(self):
        self._node_profiles: Dict[str, NodeResourceProfile] = {}
        self._profile_history: List[Dict[str, Any]] = []

    def profile_local_node(self) -> NodeResourceProfile:
        """
        Profile the local machine's resources.

        Used for the controller node and as a reference baseline.
        """
        import sys

        profile = NodeResourceProfile(
            node_id="local",
            hostname=platform.node(),
            ip_address="127.0.0.1",
        )

        # CPU
        profile.cpu = CPUProfile(
            architecture=platform.machine(),
            model_name=platform.processor() or "unknown",
            physical_cores=os.cpu_count() or 1,
            logical_cores=os.cpu_count() or 1,
        )

        # Memory (from /proc/meminfo on Linux)
        try:
            with open("/proc/meminfo", "r") as f:
                meminfo = {}
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0]
                        meminfo[key] = int(val) * 1024  # Convert from kB
                profile.memory = MemoryProfile(
                    total_bytes=meminfo.get("MemTotal", 0),
                    available_bytes=meminfo.get("MemAvailable", meminfo.get("MemFree", 0)),
                    used_percent=round(
                        (1 - meminfo.get("MemAvailable", 0) / max(meminfo.get("MemTotal", 1), 1))
                        * 100,
                        1,
                    ),
                    swap_total_bytes=meminfo.get("SwapTotal", 0),
                    swap_used_bytes=meminfo.get("SwapTotal", 0) - meminfo.get("SwapFree", 0),
                )
        except (FileNotFoundError, PermissionError):
            pass

        # Storage
        try:
            usage = shutil.disk_usage("/")
            profile.storage = StorageProfile(
                total_bytes=usage.total,
                available_bytes=usage.free,
                used_percent=round((usage.used / usage.total) * 100, 1),
            )
        except OSError:
            pass

        # Software
        profile.software = SoftwareProfile(
            os_name=platform.system(),
            os_version=platform.release(),
            kernel_version=platform.version(),
            python_version=sys.version.split()[0],
        )

        # Check for docker
        docker_path = shutil.which("docker")
        if docker_path:
            profile.software.docker_available = True

        # Check runtimes
        for runtime in ["node", "go", "rustc", "java"]:
            if shutil.which(runtime):
                profile.software.installed_runtimes.append(runtime)

        for pm in ["pip", "npm", "apt", "yum", "brew", "cargo"]:
            if shutil.which(pm):
                profile.software.package_managers.append(pm)

        # Score it
        profile.score = self._compute_score(profile)
        profile.profiled_at = datetime.now(timezone.utc)

        self._node_profiles["local"] = profile
        return profile

    async def profile_remote_node(
        self,
        node_id: str,
        ip_address: str,
        hostname: str = "",
    ) -> NodeResourceProfile:
        """
        Profile a remote node by querying its ag3ntwerk agent endpoint.

        Remote nodes must have the ag3ntwerk agent installed and running.
        The agent exposes a /resources endpoint with system information.
        """
        profile = NodeResourceProfile(
            node_id=node_id,
            ip_address=ip_address,
            hostname=hostname,
        )

        # Attempt to query the ag3ntwerk agent for resource info
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip_address, 8000),
                timeout=5.0,
            )

            # Send HTTP request for resource profile
            request = (
                f"GET /api/v1/node/resources HTTP/1.1\r\n"
                f"Host: {ip_address}:8000\r\n"
                f"Accept: application/json\r\n"
                f"Connection: close\r\n\r\n"
            )
            writer.write(request.encode())
            await writer.drain()

            response = await asyncio.wait_for(reader.read(65536), timeout=10.0)
            writer.close()
            await writer.wait_closed()

            # Parse JSON response body (skip HTTP headers)
            response_text = response.decode("utf-8", errors="ignore")
            body_start = response_text.find("\r\n\r\n")
            if body_start > 0:
                body = response_text[body_start + 4 :]
                try:
                    data = json.loads(body)
                    profile = self._parse_remote_profile(node_id, ip_address, hostname, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from {ip_address}")

        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            logger.warning(f"Could not profile remote node {ip_address}: {e}")
            profile.score = ResourceScore(
                overall=0.0,
                tier=CapabilityTier.MINIMAL,
                suitable_workloads=["monitoring_only"],
            )
        else:
            profile.score = self._compute_score(profile)
        profile.profiled_at = datetime.now(timezone.utc)
        self._node_profiles[node_id] = profile

        self._profile_history.append(
            {
                "node_id": node_id,
                "ip_address": ip_address,
                "profiled_at": profile.profiled_at.isoformat(),
                "score": profile.score.overall,
                "tier": profile.score.tier.value,
            }
        )

        return profile

    def _parse_remote_profile(
        self,
        node_id: str,
        ip_address: str,
        hostname: str,
        data: Dict[str, Any],
    ) -> NodeResourceProfile:
        """Parse resource data from a remote agent response."""
        cpu_data = data.get("cpu", {})
        mem_data = data.get("memory", {})
        storage_data = data.get("storage", {})
        gpu_data = data.get("gpu", {})
        sw_data = data.get("software", {})

        return NodeResourceProfile(
            node_id=node_id,
            ip_address=ip_address,
            hostname=hostname or data.get("hostname", ""),
            cpu=CPUProfile(
                architecture=cpu_data.get("architecture", ""),
                model_name=cpu_data.get("model_name", ""),
                physical_cores=cpu_data.get("physical_cores", 0),
                logical_cores=cpu_data.get("logical_cores", 0),
                clock_speed_mhz=cpu_data.get("clock_speed_mhz", 0),
                load_percent=cpu_data.get("load_percent", 0),
                available_cores=cpu_data.get("available_cores", 0),
            ),
            memory=MemoryProfile(
                total_bytes=mem_data.get("total_bytes", 0),
                available_bytes=mem_data.get("available_bytes", 0),
                used_percent=mem_data.get("used_percent", 0),
                swap_total_bytes=mem_data.get("swap_total_bytes", 0),
                swap_used_bytes=mem_data.get("swap_used_bytes", 0),
            ),
            storage=StorageProfile(
                total_bytes=storage_data.get("total_bytes", 0),
                available_bytes=storage_data.get("available_bytes", 0),
                used_percent=storage_data.get("used_percent", 0),
                is_ssd=storage_data.get("is_ssd", False),
            ),
            gpu=GPUProfile(
                available=gpu_data.get("available", False),
                devices=gpu_data.get("devices", []),
                total_vram_gb=gpu_data.get("total_vram_gb", 0),
                cuda_available=gpu_data.get("cuda_available", False),
                cuda_version=gpu_data.get("cuda_version", ""),
            ),
            software=SoftwareProfile(
                os_name=sw_data.get("os_name", ""),
                os_version=sw_data.get("os_version", ""),
                python_version=sw_data.get("python_version", ""),
                docker_available=sw_data.get("docker_available", False),
                docker_version=sw_data.get("docker_version", ""),
                installed_runtimes=sw_data.get("installed_runtimes", []),
                package_managers=sw_data.get("package_managers", []),
            ),
        )

    def _compute_score(self, profile: NodeResourceProfile) -> ResourceScore:
        """Compute capability score from a resource profile."""
        # CPU score (0-100): based on core count and availability
        cores = profile.cpu.logical_cores or 1
        cpu_score = min(cores * 10, 100)  # 10 points per core, max 100

        # Memory score (0-100): based on total and available GB
        mem_gb = profile.memory.total_gb
        if mem_gb >= 64:
            mem_score = 100.0
        elif mem_gb >= 32:
            mem_score = 80.0
        elif mem_gb >= 16:
            mem_score = 60.0
        elif mem_gb >= 8:
            mem_score = 40.0
        elif mem_gb >= 4:
            mem_score = 20.0
        else:
            mem_score = 10.0

        # Storage score (0-100): based on available space and speed
        storage_gb = profile.storage.available_gb
        if storage_gb >= 500:
            storage_score = 100.0
        elif storage_gb >= 200:
            storage_score = 80.0
        elif storage_gb >= 100:
            storage_score = 60.0
        elif storage_gb >= 50:
            storage_score = 40.0
        else:
            storage_score = 20.0
        if profile.storage.is_ssd:
            storage_score = min(storage_score + 10, 100)

        # GPU score (0-100)
        gpu_score = 0.0
        if profile.gpu.available:
            gpu_score = 50.0
            if profile.gpu.cuda_available:
                gpu_score += 25.0
            gpu_score += min(profile.gpu.total_vram_gb * 3, 25)

        # Network score (0-100)
        net_score = 50.0  # Default baseline
        if profile.network.bandwidth_mbps > 0:
            if profile.network.bandwidth_mbps >= 1000:
                net_score = 100.0
            elif profile.network.bandwidth_mbps >= 100:
                net_score = 70.0

        # Overall: weighted average
        weights = {
            "cpu": 0.30,
            "memory": 0.25,
            "storage": 0.15,
            "gpu": 0.15,
            "network": 0.15,
        }
        overall = (
            cpu_score * weights["cpu"]
            + mem_score * weights["memory"]
            + storage_score * weights["storage"]
            + gpu_score * weights["gpu"]
            + net_score * weights["network"]
        )

        # Determine tier
        if overall >= 80:
            tier = CapabilityTier.ENTERPRISE
        elif overall >= 60:
            tier = CapabilityTier.HIGH
        elif overall >= 40:
            tier = CapabilityTier.STANDARD
        elif overall >= 20:
            tier = CapabilityTier.BASIC
        else:
            tier = CapabilityTier.MINIMAL

        # Determine suitable workloads
        suitable = []
        if cpu_score >= 40:
            suitable.append("general_compute")
        if mem_score >= 60:
            suitable.append("data_processing")
            suitable.append("model_inference")
        if gpu_score >= 50:
            suitable.append("gpu_compute")
            suitable.append("model_training")
        if storage_score >= 60:
            suitable.append("data_storage")
            suitable.append("log_aggregation")
        if cpu_score >= 20 and mem_score >= 20:
            suitable.append("lightweight_agent")
            suitable.append("monitoring")
        if profile.software.docker_available:
            suitable.append("containerized_workloads")

        return ResourceScore(
            overall=overall,
            cpu_score=cpu_score,
            memory_score=mem_score,
            storage_score=storage_score,
            gpu_score=gpu_score,
            network_score=net_score,
            tier=tier,
            suitable_workloads=suitable,
        )

    # ---- Query Methods ----

    def get_node_profile(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get the resource profile for a specific node."""
        profile = self._node_profiles.get(node_id)
        return profile.to_dict() if profile else None

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        """Get all node profiles."""
        return [p.to_dict() for p in self._node_profiles.values()]

    def get_fleet_summary(self) -> Dict[str, Any]:
        """Get aggregate fleet resource summary."""
        profiles = list(self._node_profiles.values())
        if not profiles:
            return {"nodes": 0, "message": "No nodes profiled yet"}

        total_cores = sum(p.cpu.logical_cores for p in profiles)
        total_memory_gb = sum(p.memory.total_gb for p in profiles)
        total_storage_gb = sum(p.storage.total_gb for p in profiles)
        total_gpu_vram = sum(p.gpu.total_vram_gb for p in profiles)
        gpu_nodes = len([p for p in profiles if p.gpu.available])

        return {
            "nodes": len(profiles),
            "total_cpu_cores": total_cores,
            "total_memory_gb": round(total_memory_gb, 2),
            "total_storage_gb": round(total_storage_gb, 2),
            "gpu_nodes": gpu_nodes,
            "total_gpu_vram_gb": round(total_gpu_vram, 2),
            "tiers": {
                tier.value: len([p for p in profiles if p.score.tier == tier])
                for tier in CapabilityTier
                if any(p.score.tier == tier for p in profiles)
            },
            "average_score": round(sum(p.score.overall for p in profiles) / len(profiles), 2),
        }

    def find_nodes_for_workload(
        self,
        workload_type: str,
        min_score: float = 0.0,
        require_docker: bool = False,
    ) -> List[Dict[str, Any]]:
        """Find nodes suitable for a specific workload type."""
        suitable = []
        for profile in self._node_profiles.values():
            if workload_type in profile.score.suitable_workloads:
                if profile.score.overall >= min_score:
                    if require_docker and not profile.software.docker_available:
                        continue
                    suitable.append(profile.to_dict())

        return sorted(suitable, key=lambda x: x["score"]["overall"], reverse=True)

    def get_profile_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get profiling history."""
        return sorted(
            self._profile_history,
            key=lambda x: x["profiled_at"],
            reverse=True,
        )[:limit]


# Import json at module level for remote profiling
import json
