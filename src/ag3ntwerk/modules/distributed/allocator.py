"""
Distributed Task Allocator - Intelligent workload distribution engine.

Routes ag3ntwerk agent workloads across the compute fleet based on
resource profiles, current load, affinity rules, and optimization
objectives (latency, throughput, cost, resilience).

Primary owners: Nexus, Forge
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class AllocationStrategy(str, Enum):
    """Strategy for distributing workloads."""

    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    BEST_FIT = "best_fit"  # Match workload requirements to node capabilities
    AFFINITY = "affinity"  # Prefer nodes with related data/services
    SPREAD = "spread"  # Maximize distribution for resilience
    PACK = "pack"  # Minimize node count (consolidation)


class WorkloadPriority(str, Enum):
    """Priority level for workload scheduling."""

    CRITICAL = "critical"  # Must run immediately, preempt if needed
    HIGH = "high"  # Run as soon as possible
    NORMAL = "normal"  # Standard scheduling
    LOW = "low"  # Run when resources available
    BACKGROUND = "background"  # Best-effort, defer to other workloads


class WorkloadState(str, Enum):
    """State of a distributed workload."""

    PENDING = "pending"
    SCHEDULING = "scheduling"
    ALLOCATED = "allocated"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    MIGRATING = "migrating"


@dataclass
class WorkloadRequirements:
    """Resource requirements for a workload."""

    min_cpu_cores: int = 1
    min_memory_gb: float = 0.5
    min_storage_gb: float = 1.0
    requires_gpu: bool = False
    min_gpu_vram_gb: float = 0.0
    requires_docker: bool = False
    requires_network: bool = True
    preferred_os: str = ""
    required_runtimes: List[str] = field(default_factory=list)
    affinity_tags: List[str] = field(default_factory=list)
    anti_affinity_tags: List[str] = field(default_factory=list)
    max_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_cpu_cores": self.min_cpu_cores,
            "min_memory_gb": self.min_memory_gb,
            "min_storage_gb": self.min_storage_gb,
            "requires_gpu": self.requires_gpu,
            "min_gpu_vram_gb": self.min_gpu_vram_gb,
            "requires_docker": self.requires_docker,
            "preferred_os": self.preferred_os,
            "required_runtimes": self.required_runtimes,
            "affinity_tags": self.affinity_tags,
            "anti_affinity_tags": self.anti_affinity_tags,
        }


@dataclass
class DistributedWorkload:
    """A workload to be distributed across the fleet."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    owner_executive: str = ""
    module: str = ""
    task_type: str = ""
    priority: WorkloadPriority = WorkloadPriority.NORMAL
    state: WorkloadState = WorkloadState.PENDING
    requirements: WorkloadRequirements = field(default_factory=WorkloadRequirements)
    context: Dict[str, Any] = field(default_factory=dict)
    allocated_node_id: str = ""
    allocated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner_executive": self.owner_executive,
            "module": self.module,
            "task_type": self.task_type,
            "priority": self.priority.value,
            "state": self.state.value,
            "requirements": self.requirements.to_dict(),
            "allocated_node_id": self.allocated_node_id,
            "allocated_at": self.allocated_at.isoformat() if self.allocated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "retry_count": self.retry_count,
        }


@dataclass
class AllocationDecision:
    """Result of an allocation decision."""

    workload_id: str
    node_id: str
    score: float
    strategy_used: AllocationStrategy
    reasoning: str
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workload_id": self.workload_id,
            "node_id": self.node_id,
            "score": round(self.score, 2),
            "strategy_used": self.strategy_used.value,
            "reasoning": self.reasoning,
            "alternatives": self.alternatives,
            "decided_at": self.decided_at.isoformat(),
        }


@dataclass
class NodeLoad:
    """Current load tracking for a node."""

    node_id: str
    active_workloads: int = 0
    reserved_cpu_cores: int = 0
    reserved_memory_gb: float = 0.0
    reserved_storage_gb: float = 0.0
    reserved_gpu_vram_gb: float = 0.0
    workload_ids: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "active_workloads": self.active_workloads,
            "reserved_cpu_cores": self.reserved_cpu_cores,
            "reserved_memory_gb": round(self.reserved_memory_gb, 2),
            "reserved_storage_gb": round(self.reserved_storage_gb, 2),
            "reserved_gpu_vram_gb": round(self.reserved_gpu_vram_gb, 2),
        }


# Mapping of agent-owned modules to their preferred workload types
AGENT_WORKLOAD_MAP: Dict[str, List[str]] = {
    "Nexus": ["orchestration", "scheduling", "monitoring", "reporting"],
    "Forge": ["code_review", "development", "gpu_compute", "model_training"],
    "Sentinel": ["security_scan", "threat_detection", "compliance_audit", "monitoring"],
    "Index": ["data_processing", "analytics", "data_harvesting", "model_inference"],
    "Axiom": ["research", "competitive_analysis", "trend_analysis"],
    "Echo": ["content_generation", "brand_audit", "market_analysis"],
    "Keystone": ["financial_analysis", "forecasting", "reporting"],
    "Vector": ["pricing_optimization", "commerce_operations", "inventory"],
}


class TaskAllocator:
    """
    Distributed task allocation engine.

    Routes workloads to the optimal compute node based on requirements,
    current fleet load, and the selected allocation strategy.
    """

    def __init__(self):
        self._workloads: Dict[str, DistributedWorkload] = {}
        self._node_loads: Dict[str, NodeLoad] = {}
        self._allocation_history: List[AllocationDecision] = []
        self._node_profiles: Dict[str, Dict[str, Any]] = {}
        self._default_strategy = AllocationStrategy.BEST_FIT
        self._round_robin_index = 0

    def set_strategy(self, strategy: AllocationStrategy) -> None:
        """Set the default allocation strategy."""
        self._default_strategy = strategy
        logger.info(f"Allocation strategy set to: {strategy.value}")

    def register_node(self, node_id: str, profile: Dict[str, Any]) -> None:
        """Register a node and its resource profile with the allocator."""
        self._node_profiles[node_id] = profile
        if node_id not in self._node_loads:
            self._node_loads[node_id] = NodeLoad(node_id=node_id)
        logger.info(f"Node {node_id} registered with allocator")

    def unregister_node(self, node_id: str) -> None:
        """Remove a node from the allocator."""
        self._node_profiles.pop(node_id, None)
        self._node_loads.pop(node_id, None)
        logger.info(f"Node {node_id} unregistered from allocator")

    def submit_workload(
        self,
        name: str,
        owner_executive: str,
        module: str = "",
        task_type: str = "",
        priority: WorkloadPriority = WorkloadPriority.NORMAL,
        requirements: Optional[WorkloadRequirements] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> DistributedWorkload:
        """Submit a workload for allocation."""
        workload = DistributedWorkload(
            name=name,
            owner_executive=owner_executive,
            module=module,
            task_type=task_type,
            priority=priority,
            requirements=requirements or WorkloadRequirements(),
            context=context or {},
        )
        self._workloads[workload.id] = workload
        logger.info(f"Workload submitted: {name} (priority={priority.value})")
        return workload

    def allocate(
        self,
        workload_id: str,
        strategy: Optional[AllocationStrategy] = None,
    ) -> Optional[AllocationDecision]:
        """
        Allocate a workload to a node.

        Returns an AllocationDecision or None if no suitable node is found.
        """
        workload = self._workloads.get(workload_id)
        if not workload:
            return None

        if not self._node_profiles:
            workload.error = "No nodes available in the fleet"
            return None

        strategy = strategy or self._default_strategy
        workload.state = WorkloadState.SCHEDULING

        # Score all available nodes
        candidates = self._score_candidates(workload, strategy)

        if not candidates:
            workload.error = "No suitable nodes found for workload requirements"
            workload.state = WorkloadState.PENDING
            return None

        # Select the best candidate
        best = candidates[0]
        node_id = best["node_id"]

        # Reserve resources on the node
        self._reserve_resources(node_id, workload)

        # Record the allocation
        decision = AllocationDecision(
            workload_id=workload_id,
            node_id=node_id,
            score=best["score"],
            strategy_used=strategy,
            reasoning=best["reasoning"],
            alternatives=[c for c in candidates[1:4]],  # Top 3 alternatives
        )
        self._allocation_history.append(decision)

        workload.allocated_node_id = node_id
        workload.allocated_at = datetime.now(timezone.utc)
        workload.state = WorkloadState.ALLOCATED

        logger.info(
            f"Workload {workload.name} allocated to node {node_id} "
            f"(score={best['score']:.1f}, strategy={strategy.value})"
        )
        return decision

    def _score_candidates(
        self,
        workload: DistributedWorkload,
        strategy: AllocationStrategy,
    ) -> List[Dict[str, Any]]:
        """Score and rank node candidates for a workload."""
        candidates = []
        reqs = workload.requirements

        for node_id, profile in self._node_profiles.items():
            score_info = profile.get("score", {})
            cpu_data = profile.get("cpu", {})
            mem_data = profile.get("memory", {})
            storage_data = profile.get("storage", {})
            gpu_data = profile.get("gpu", {})
            sw_data = profile.get("software", {})

            # Hard constraints: filter out nodes that can't run the workload
            if cpu_data.get("logical_cores", 0) < reqs.min_cpu_cores:
                continue
            if mem_data.get("available_gb", 0) < reqs.min_memory_gb:
                continue
            if storage_data.get("available_gb", 0) < reqs.min_storage_gb:
                continue
            if reqs.requires_gpu and not gpu_data.get("available", False):
                continue
            if reqs.requires_gpu and gpu_data.get("total_vram_gb", 0) < reqs.min_gpu_vram_gb:
                continue
            if reqs.requires_docker and not sw_data.get("docker_available", False):
                continue
            if reqs.required_runtimes:
                installed = set(sw_data.get("installed_runtimes", []))
                if not set(reqs.required_runtimes).issubset(installed):
                    continue

            # Check current load
            load = self._node_loads.get(node_id, NodeLoad(node_id=node_id))
            remaining_cores = cpu_data.get("logical_cores", 0) - load.reserved_cpu_cores
            remaining_mem = mem_data.get("available_gb", 0) - load.reserved_memory_gb

            if remaining_cores < reqs.min_cpu_cores:
                continue
            if remaining_mem < reqs.min_memory_gb:
                continue

            # Soft scoring based on strategy
            score = 0.0
            reasoning = ""

            if strategy == AllocationStrategy.BEST_FIT:
                # Prefer nodes whose capacity closely matches requirements
                fit_score = score_info.get("overall", 0)
                headroom_penalty = (remaining_cores - reqs.min_cpu_cores) * 2
                score = fit_score - headroom_penalty
                reasoning = (
                    f"Best fit: capability={fit_score:.1f}, headroom_penalty={headroom_penalty:.1f}"
                )

            elif strategy == AllocationStrategy.LEAST_LOADED:
                # Prefer nodes with the most free resources
                score = (remaining_cores * 10) + (remaining_mem * 5)
                reasoning = (
                    f"Least loaded: {remaining_cores} free cores, {remaining_mem:.1f}GB free mem"
                )

            elif strategy == AllocationStrategy.SPREAD:
                # Prefer nodes with fewest active workloads
                score = 100 - (load.active_workloads * 20)
                reasoning = f"Spread: {load.active_workloads} active workloads"

            elif strategy == AllocationStrategy.PACK:
                # Prefer nodes already running workloads (consolidate)
                score = load.active_workloads * 20 + score_info.get("overall", 0) * 0.5
                reasoning = f"Pack: {load.active_workloads} active workloads, consolidating"

            elif strategy == AllocationStrategy.ROUND_ROBIN:
                # Simple round-robin, but still respect requirements
                score = 50
                reasoning = "Round-robin selection"

            elif strategy == AllocationStrategy.AFFINITY:
                # Prefer nodes with matching tags
                node_tags = set(profile.get("tags", []))
                affinity_match = len(set(reqs.affinity_tags) & node_tags)
                anti_affinity_match = len(set(reqs.anti_affinity_tags) & node_tags)
                score = (
                    (affinity_match * 30)
                    - (anti_affinity_match * 50)
                    + score_info.get("overall", 0) * 0.5
                )
                reasoning = (
                    f"Affinity: {affinity_match} matches, {anti_affinity_match} anti-matches"
                )

            candidates.append(
                {
                    "node_id": node_id,
                    "score": score,
                    "reasoning": reasoning,
                    "remaining_cores": remaining_cores,
                    "remaining_memory_gb": remaining_mem,
                    "active_workloads": load.active_workloads,
                }
            )

        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # Handle round-robin
        if strategy == AllocationStrategy.ROUND_ROBIN and candidates:
            self._round_robin_index = (self._round_robin_index + 1) % len(candidates)
            selected = candidates[self._round_robin_index]
            candidates.remove(selected)
            candidates.insert(0, selected)

        return candidates

    def _reserve_resources(self, node_id: str, workload: DistributedWorkload) -> None:
        """Reserve resources on a node for a workload."""
        if node_id not in self._node_loads:
            self._node_loads[node_id] = NodeLoad(node_id=node_id)

        load = self._node_loads[node_id]
        load.active_workloads += 1
        load.reserved_cpu_cores += workload.requirements.min_cpu_cores
        load.reserved_memory_gb += workload.requirements.min_memory_gb
        load.reserved_storage_gb += workload.requirements.min_storage_gb
        load.reserved_gpu_vram_gb += workload.requirements.min_gpu_vram_gb
        load.workload_ids.add(workload.id)

    def release_workload(self, workload_id: str) -> bool:
        """Release resources when a workload completes."""
        workload = self._workloads.get(workload_id)
        if not workload or not workload.allocated_node_id:
            return False

        node_id = workload.allocated_node_id
        load = self._node_loads.get(node_id)
        if load:
            load.active_workloads = max(0, load.active_workloads - 1)
            load.reserved_cpu_cores = max(
                0, load.reserved_cpu_cores - workload.requirements.min_cpu_cores
            )
            load.reserved_memory_gb = max(
                0, load.reserved_memory_gb - workload.requirements.min_memory_gb
            )
            load.reserved_storage_gb = max(
                0, load.reserved_storage_gb - workload.requirements.min_storage_gb
            )
            load.reserved_gpu_vram_gb = max(
                0, load.reserved_gpu_vram_gb - workload.requirements.min_gpu_vram_gb
            )
            load.workload_ids.discard(workload_id)

        workload.completed_at = datetime.now(timezone.utc)
        return True

    def complete_workload(
        self,
        workload_id: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Mark a workload as completed or failed."""
        workload = self._workloads.get(workload_id)
        if not workload:
            return False

        if error:
            workload.state = WorkloadState.FAILED
            workload.error = error
            if workload.retry_count < workload.max_retries:
                workload.retry_count += 1
                workload.state = WorkloadState.PENDING
                self.release_workload(workload_id)
                logger.info(
                    f"Workload {workload.name} retrying ({workload.retry_count}/{workload.max_retries})"
                )
                return True
        else:
            workload.state = WorkloadState.COMPLETED
            workload.result = result

        self.release_workload(workload_id)
        return True

    # ---- Query Methods ----

    def get_workload(self, workload_id: str) -> Optional[Dict[str, Any]]:
        """Get workload details."""
        workload = self._workloads.get(workload_id)
        return workload.to_dict() if workload else None

    def get_pending_workloads(self) -> List[Dict[str, Any]]:
        """Get all pending workloads sorted by priority."""
        priority_order = {
            WorkloadPriority.CRITICAL: 0,
            WorkloadPriority.HIGH: 1,
            WorkloadPriority.NORMAL: 2,
            WorkloadPriority.LOW: 3,
            WorkloadPriority.BACKGROUND: 4,
        }
        pending = [w for w in self._workloads.values() if w.state == WorkloadState.PENDING]
        pending.sort(key=lambda w: (priority_order.get(w.priority, 5), w.created_at))
        return [w.to_dict() for w in pending]

    def get_active_workloads(self) -> List[Dict[str, Any]]:
        """Get all actively running workloads."""
        active_states = {WorkloadState.ALLOCATED, WorkloadState.RUNNING, WorkloadState.SCHEDULING}
        return [w.to_dict() for w in self._workloads.values() if w.state in active_states]

    def get_node_loads(self) -> List[Dict[str, Any]]:
        """Get current load on all nodes."""
        return [l.to_dict() for l in self._node_loads.values()]

    def get_allocation_stats(self) -> Dict[str, Any]:
        """Get allocation statistics."""
        workloads = list(self._workloads.values())
        return {
            "total_workloads": len(workloads),
            "by_state": {
                state.value: len([w for w in workloads if w.state == state])
                for state in WorkloadState
                if any(w.state == state for w in workloads)
            },
            "by_priority": {
                prio.value: len([w for w in workloads if w.priority == prio])
                for prio in WorkloadPriority
                if any(w.priority == prio for w in workloads)
            },
            "registered_nodes": len(self._node_profiles),
            "allocation_decisions": len(self._allocation_history),
            "default_strategy": self._default_strategy.value,
        }

    def get_allocation_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent allocation decisions."""
        return [
            d.to_dict()
            for d in sorted(
                self._allocation_history,
                key=lambda x: x.decided_at,
                reverse=True,
            )[:limit]
        ]
