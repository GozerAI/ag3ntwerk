"""
Fleet Orchestration API Routes - REST API for distributed fleet management.

Provides endpoints for network discovery, node enrollment, resource
profiling, workload distribution, and fleet health monitoring.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ag3ntwerk.api.auth import AuthenticatedUser, Permission, optional_auth, require_auth

logger = logging.getLogger(__name__)

# Configurable auth: mirrors app.py pattern
_auth_required = __import__("os").getenv("AGENTWERK_AUTH_REQUIRED", "true").lower() == "true"
if not _auth_required:
    import warnings
    warnings.warn(
        "AGENTWERK_AUTH_REQUIRED is disabled — API is unauthenticated!",
        stacklevel=2,
    )


def _get_auth(permissions: set | None = None):
    """Return auth dependency based on configuration."""
    if _auth_required:
        return require_auth(permissions)
    return optional_auth()


# =============================================================================
# Pydantic Models
# =============================================================================


class DiscoverNetworkRequest(BaseModel):
    cidr: str
    name: str = ""
    scan_ports: Optional[List[int]] = None


class EnrollDeviceRequest(BaseModel):
    device_id: str
    approved_by: str
    role: str = "compute_node"
    tags: Optional[List[str]] = None


class ProvisionNodeRequest(BaseModel):
    node_id: str
    approved_by: str
    include_docker: bool = False
    include_gpu: bool = False
    custom_config: Optional[Dict[str, Any]] = None


class SubmitWorkloadRequest(BaseModel):
    name: str
    owner_executive: str
    module: str = ""
    task_type: str = ""
    priority: str = "normal"
    min_cpu_cores: int = 1
    min_memory_gb: float = 0.5
    requires_gpu: bool = False
    requires_docker: bool = False
    affinity_tags: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


class CompleteWorkloadRequest(BaseModel):
    workload_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SetStrategyRequest(BaseModel):
    strategy: str


class AddScanTargetRequest(BaseModel):
    name: str
    cidr: str
    description: str = ""
    scan_interval_minutes: int = 60
    probe_ports: Optional[List[int]] = None


class RejectDeviceRequest(BaseModel):
    device_id: str
    reason: str = ""


class GenerateDeploymentPlanRequest(BaseModel):
    target_ip: str
    target_hostname: str = ""
    target_os: str = "unknown"
    target_os_version: str = ""
    target_role: str = "compute_node"
    created_by: str = ""
    include_docker: bool = True
    include_gpu: bool = False
    include_storage_prep: bool = False
    target_storage_device: str = ""
    controller_url: str = "http://controller:8000"


class ApprovePlanPhaseRequest(BaseModel):
    approved_by: str


class SkipPlanPhaseRequest(BaseModel):
    reason: str = ""


class CancelPlanRequest(BaseModel):
    reason: str = ""


class GenerateRelayTokenRequest(BaseModel):
    relay_name: str = ""
    created_by: str = ""
    networks: Optional[List[str]] = None


class RevokeRelayRequest(BaseModel):
    relay_id: str


# =============================================================================
# Fleet Orchestrator Singleton (double-checked locking)
# =============================================================================

_fleet_orchestrator = None
_fleet_init_lock = asyncio.Lock()
_deployment_planner = None
_planner_init_lock = asyncio.Lock()


def get_fleet():
    """Get FleetOrchestrator singleton (sync fast-path).

    For the async-safe initialisation path, use ``_get_fleet_async``.
    This synchronous helper is kept for backwards compatibility with
    call-sites that already guard against ``None``.
    """
    global _fleet_orchestrator
    if _fleet_orchestrator is None:
        from ag3ntwerk.modules.distributed.fleet import FleetOrchestrator

        _fleet_orchestrator = FleetOrchestrator()
    return _fleet_orchestrator


async def _get_fleet_async():
    """Get or create FleetOrchestrator singleton with async lock."""
    global _fleet_orchestrator
    if _fleet_orchestrator is None:
        async with _fleet_init_lock:
            if _fleet_orchestrator is None:
                from ag3ntwerk.modules.distributed.fleet import FleetOrchestrator

                _fleet_orchestrator = FleetOrchestrator()
    return _fleet_orchestrator


# =============================================================================
# Fleet Router
# =============================================================================

fleet_router = APIRouter(
    prefix="/api/v1/fleet",
    tags=["Fleet Orchestration"],
)


# ---- Fleet Status ----


@fleet_router.get("/")
async def fleet_overview(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get fleet orchestration status and overview."""
    fleet = await _get_fleet_async()
    return {
        "module": "distributed_orchestration",
        "primary_owner": "Nexus",
        "status": fleet.get_fleet_status(),
    }


@fleet_router.post("/initialize")
async def initialize_fleet(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """Initialize the fleet orchestrator and profile the controller node."""
    fleet = await _get_fleet_async()
    result = await fleet.initialize()
    return result


@fleet_router.get("/health")
async def check_fleet_health(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Run health check across all fleet nodes."""
    fleet = await _get_fleet_async()
    return await fleet.check_fleet_health()


@fleet_router.get("/nodes")
async def list_fleet_nodes(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """List all nodes in the fleet."""
    fleet = await _get_fleet_async()
    return {"nodes": fleet.get_fleet_nodes()}


@fleet_router.delete("/nodes/{node_id}")
async def remove_fleet_node(
    node_id: str,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """Remove a node from the fleet."""
    fleet = await _get_fleet_async()
    result = fleet.remove_node(node_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed"))
    return result


@fleet_router.get("/events")
async def get_fleet_events(
    limit: int = Query(50, ge=1, le=200),
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get fleet event log."""
    fleet = await _get_fleet_async()
    return {"events": fleet.get_event_log(limit=limit)}


# ---- Network Discovery ----


@fleet_router.post("/discover")
async def discover_network(
    request: DiscoverNetworkRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """
    Discover devices on a network range.

    Scans the specified CIDR for responsive devices.
    Only scans networks explicitly provided - no auto-discovery.
    """
    fleet = await _get_fleet_async()
    try:
        result = await fleet.discover_network(
            cidr=request.cidr,
            name=request.name,
            scan_ports=request.scan_ports,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@fleet_router.get("/discover/devices")
async def get_discovered_devices(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get all devices found during network scans."""
    fleet = await _get_fleet_async()
    return {"devices": fleet.get_discovered_devices()}


@fleet_router.get("/discover/targets")
async def list_scan_targets(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """List configured scan targets."""
    fleet = await _get_fleet_async()
    return {"targets": fleet.discovery.list_scan_targets()}


@fleet_router.post("/discover/targets")
async def add_scan_target(
    request: AddScanTargetRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """Add a new network scan target."""
    fleet = await _get_fleet_async()
    try:
        target = fleet.discovery.add_scan_target(
            name=request.name,
            cidr=request.cidr,
            description=request.description,
            scan_interval_minutes=request.scan_interval_minutes,
            probe_ports=request.probe_ports,
        )
        return {"success": True, "target": target.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@fleet_router.get("/discover/history")
async def get_scan_history(
    limit: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get network scan history."""
    fleet = await _get_fleet_async()
    return {"history": fleet.discovery.get_scan_history(limit=limit)}


# ---- Device Enrollment ----


@fleet_router.post("/enroll")
async def enroll_device(
    request: EnrollDeviceRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """
    Enroll a discovered device into the fleet.

    REQUIRES explicit approval - provide the approved_by field
    with the identity of the person authorizing enrollment.
    """
    fleet = await _get_fleet_async()
    try:
        from ag3ntwerk.modules.distributed.discovery import DeviceRole

        role = DeviceRole(request.role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role: {request.role}. Valid: {[r.value for r in DeviceRole]}",
        )

    result = await fleet.enroll_device(
        device_id=request.device_id,
        approved_by=request.approved_by,
        role=role,
        tags=request.tags,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Enrollment failed"))
    return result


@fleet_router.post("/reject")
async def reject_device(
    request: RejectDeviceRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """Reject a discovered device from fleet enrollment."""
    fleet = await _get_fleet_async()
    success = fleet.discovery.reject_device(request.device_id, request.reason)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"success": True, "device_id": request.device_id}


# ---- Provisioning ----


@fleet_router.post("/provision")
async def provision_node(
    request: ProvisionNodeRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """
    Provision an enrolled node with dependencies and configuration.

    The node must be enrolled first. Provisioning installs required
    software, creates directory structures, and configures the node
    for workload execution.
    """
    fleet = await _get_fleet_async()
    result = await fleet.provision_node(
        node_id=request.node_id,
        approved_by=request.approved_by,
        include_docker=request.include_docker,
        include_gpu=request.include_gpu,
        custom_config=request.custom_config,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Provisioning failed"))
    return result


@fleet_router.get("/provision/manifest")
async def get_standard_manifest(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get the standard provisioning manifest for review."""
    fleet = await _get_fleet_async()
    return fleet.provisioner.get_standard_manifest()


@fleet_router.get("/provision/plans")
async def list_provision_plans(
    node_id: Optional[str] = Query(None),
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """List provisioning plans."""
    fleet = await _get_fleet_async()
    return {"plans": fleet.provisioner.list_plans(node_id=node_id)}


@fleet_router.get("/provision/history")
async def get_provision_history(
    limit: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get provisioning history."""
    fleet = await _get_fleet_async()
    return {"history": fleet.provisioner.get_provision_history(limit=limit)}


# ---- Resource Profiling ----


@fleet_router.get("/resources")
async def get_fleet_resources(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get aggregate fleet resource summary."""
    fleet = await _get_fleet_async()
    return fleet.resources.get_fleet_summary()


@fleet_router.get("/resources/profiles")
async def get_all_resource_profiles(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get resource profiles for all nodes."""
    fleet = await _get_fleet_async()
    return {"profiles": fleet.resources.get_all_profiles()}


@fleet_router.get("/resources/{node_id}")
async def get_node_resources(
    node_id: str,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get resource profile for a specific node."""
    fleet = await _get_fleet_async()
    profile = fleet.resources.get_node_profile(node_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"No profile for node: {node_id}")
    return profile


@fleet_router.get("/resources/search/{workload_type}")
async def find_nodes_for_workload(
    workload_type: str,
    min_score: float = Query(0.0, ge=0.0, le=100.0),
    require_docker: bool = Query(False),
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Find nodes suitable for a specific workload type."""
    fleet = await _get_fleet_async()
    nodes = fleet.resources.find_nodes_for_workload(
        workload_type=workload_type,
        min_score=min_score,
        require_docker=require_docker,
    )
    return {"workload_type": workload_type, "suitable_nodes": nodes}


# ---- Workload Distribution ----


@fleet_router.post("/workloads")
async def submit_workload(
    request: SubmitWorkloadRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.EXECUTE_TASK})),
):
    """
    Submit a workload for distributed execution.

    The workload is automatically allocated to the best available
    node based on the current allocation strategy.
    """
    fleet = await _get_fleet_async()
    result = fleet.submit_workload(
        name=request.name,
        owner_executive=request.owner_executive,
        module=request.module,
        task_type=request.task_type,
        priority=request.priority,
        min_cpu_cores=request.min_cpu_cores,
        min_memory_gb=request.min_memory_gb,
        requires_gpu=request.requires_gpu,
        requires_docker=request.requires_docker,
        affinity_tags=request.affinity_tags,
        context=request.context,
    )
    return result


@fleet_router.post("/workloads/complete")
async def complete_workload(
    request: CompleteWorkloadRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.EXECUTE_TASK})),
):
    """Mark a workload as completed or failed."""
    fleet = await _get_fleet_async()
    result = fleet.complete_workload(
        workload_id=request.workload_id,
        result=request.result,
        error=request.error,
    )
    return result


@fleet_router.get("/workloads/pending")
async def get_pending_workloads(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get pending workloads sorted by priority."""
    fleet = await _get_fleet_async()
    return {"workloads": fleet.allocator.get_pending_workloads()}


@fleet_router.get("/workloads/active")
async def get_active_workloads(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get currently running workloads."""
    fleet = await _get_fleet_async()
    return {"workloads": fleet.allocator.get_active_workloads()}


@fleet_router.get("/workloads/{workload_id}")
async def get_workload(
    workload_id: str,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get workload details."""
    fleet = await _get_fleet_async()
    workload = fleet.allocator.get_workload(workload_id)
    if not workload:
        raise HTTPException(status_code=404, detail=f"Workload not found: {workload_id}")
    return workload


@fleet_router.get("/workloads/stats/summary")
async def get_workload_stats(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get workload allocation statistics."""
    fleet = await _get_fleet_async()
    return fleet.allocator.get_allocation_stats()


@fleet_router.post("/strategy")
async def set_allocation_strategy(
    request: SetStrategyRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """Set the fleet-wide workload allocation strategy."""
    fleet = await _get_fleet_async()
    result = fleet.set_allocation_strategy(request.strategy)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@fleet_router.get("/allocations/history")
async def get_allocation_history(
    limit: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get allocation decision history."""
    fleet = await _get_fleet_async()
    return {"history": fleet.allocator.get_allocation_history(limit=limit)}


# =============================================================================
# Deployment Planner Singleton
# =============================================================================


def get_planner():
    """Get DeploymentPlanner singleton (sync fast-path).

    For the async-safe initialisation path, use ``_get_planner_async``.
    """
    global _deployment_planner
    if _deployment_planner is None:
        from ag3ntwerk.modules.distributed.deployment_planner import DeploymentPlanner

        _deployment_planner = DeploymentPlanner()
    return _deployment_planner


async def _get_planner_async():
    """Get or create DeploymentPlanner singleton with async lock."""
    global _deployment_planner
    if _deployment_planner is None:
        async with _planner_init_lock:
            if _deployment_planner is None:
                from ag3ntwerk.modules.distributed.deployment_planner import DeploymentPlanner

                _deployment_planner = DeploymentPlanner()
    return _deployment_planner


# ---- Deployment Plans ----


@fleet_router.post("/plans/generate")
async def generate_deployment_plan(
    request: GenerateDeploymentPlanRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """
    Generate a complete deployment plan for a target node.

    Returns a detailed, step-by-step plan covering network assessment,
    storage preparation, OS configuration, dependency installation,
    agent deployment, and verification.

    The plan is returned for review -- NOTHING is executed.
    Each phase must be individually approved before execution.
    """
    planner = await _get_planner_async()
    plan = planner.generate_plan(
        target_ip=request.target_ip,
        target_hostname=request.target_hostname,
        target_os=request.target_os,
        target_os_version=request.target_os_version,
        target_role=request.target_role,
        created_by=request.created_by,
        include_docker=request.include_docker,
        include_gpu=request.include_gpu,
        include_storage_prep=request.include_storage_prep,
        target_storage_device=request.target_storage_device,
        controller_url=request.controller_url,
    )
    return plan.to_dict()


@fleet_router.get("/plans")
async def list_deployment_plans(
    status: Optional[str] = Query(None),
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """List all deployment plans, optionally filtered by status."""
    planner = await _get_planner_async()
    return {"plans": planner.list_plans(status=status)}


@fleet_router.get("/plans/{plan_id}")
async def get_deployment_plan(
    plan_id: str,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get full details of a deployment plan."""
    planner = await _get_planner_async()
    plan = planner.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@fleet_router.get("/plans/{plan_id}/guide")
async def get_deployment_guide(
    plan_id: str,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """
    Get the deployment plan as a human-readable text guide.

    Returns a formatted text document you can review, print, or
    share with your team before approving and executing.
    """
    planner = await _get_planner_async()
    guide = planner.get_plan_guide(plan_id)
    if not guide:
        raise HTTPException(status_code=404, detail="Plan not found")
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(content=guide, media_type="text/plain")


@fleet_router.post("/plans/{plan_id}/phases/{phase_id}/approve")
async def approve_plan_phase(
    plan_id: str,
    phase_id: str,
    request: ApprovePlanPhaseRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """
    Approve a specific phase for execution.

    You must review the phase's steps before approving.
    Provide your identity in approved_by for audit trail.
    """
    planner = await _get_planner_async()
    result = planner.approve_phase(plan_id, phase_id, request.approved_by)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@fleet_router.post("/plans/{plan_id}/phases/{phase_id}/skip")
async def skip_plan_phase(
    plan_id: str,
    phase_id: str,
    request: SkipPlanPhaseRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """Skip a phase that is not applicable to this deployment."""
    planner = await _get_planner_async()
    result = planner.skip_phase(plan_id, phase_id, request.reason)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@fleet_router.post("/plans/{plan_id}/phases/{phase_id}/execute")
async def execute_plan_phase(
    plan_id: str,
    phase_id: str,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """
    Execute an approved phase.

    The phase must be approved first. All prior phases must be
    completed or skipped. Steps execute sequentially on the target node.
    """
    planner = await _get_planner_async()
    result = await planner.execute_phase(plan_id, phase_id)
    if not result.get("success"):
        status = 400 if "must be approved" in result.get("error", "") else 500
        raise HTTPException(status_code=status, detail=result.get("error"))
    return result


@fleet_router.post("/plans/{plan_id}/cancel")
async def cancel_deployment_plan(
    plan_id: str,
    request: CancelPlanRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """Cancel a deployment plan."""
    planner = await _get_planner_async()
    result = planner.cancel_plan(plan_id, request.reason)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@fleet_router.get("/loads")
async def get_node_loads(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get current resource load on all nodes."""
    fleet = await _get_fleet_async()
    return {"loads": fleet.allocator.get_node_loads()}


# =============================================================================
# Relay Management Endpoints
# =============================================================================


@fleet_router.post("/relays/token")
async def generate_relay_token(
    request: GenerateRelayTokenRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """
    Generate a pre-shared token for a new relay agent.

    Run this on your cloud-hosted ag3ntwerk, then copy the token to
    your local relay agent. The relay will use this token to authenticate
    its WebSocket tunnel back to the controller.

    Returns a one-time token and setup instructions.
    """
    fleet = await _get_fleet_async()
    token_info = fleet.relay_bridge.generate_relay_token(
        relay_name=request.relay_name,
        created_by=request.created_by,
    )
    return token_info


@fleet_router.get("/relays")
async def list_relays(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """List all relay agents (connected and disconnected)."""
    fleet = await _get_fleet_async()
    return {
        "relays": fleet.relay_bridge.get_all_relays(),
        "network_map": fleet.relay_bridge.get_network_map(),
    }


@fleet_router.get("/relays/connected")
async def list_connected_relays(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """List only actively connected relay agents."""
    fleet = await _get_fleet_async()
    return {"relays": fleet.relay_bridge.get_connected_relays()}


@fleet_router.get("/relays/{relay_id}")
async def get_relay_details(
    relay_id: str,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get details for a specific relay agent."""
    fleet = await _get_fleet_async()
    relay = fleet.relay_bridge.get_relay(relay_id)
    if not relay:
        raise HTTPException(status_code=404, detail="Relay not found")
    return relay


@fleet_router.get("/relays/health")
async def check_relay_health(
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Check health of all connected relays."""
    fleet = await _get_fleet_async()
    return await fleet.relay_bridge.check_relay_health()


@fleet_router.post("/relays/revoke")
async def revoke_relay(
    request: RevokeRelayRequest,
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.ADMIN})),
):
    """
    Revoke a relay agent's token, disconnecting it.

    The relay will not be able to reconnect until a new token is issued.
    """
    fleet = await _get_fleet_async()
    success = fleet.relay_bridge.revoke_token(request.relay_id)
    if not success:
        raise HTTPException(status_code=404, detail="Relay not found")
    return {"success": True, "revoked": request.relay_id}


@fleet_router.get("/relays/commands")
async def get_relay_command_history(
    limit: int = Query(50, ge=1, le=500),
    user: AuthenticatedUser | None = Depends(_get_auth({Permission.READ})),
):
    """Get recent command history across all relays."""
    fleet = await _get_fleet_async()
    return {"history": fleet.relay_bridge.get_command_history(limit=limit)}


# =============================================================================
# Relay WebSocket Tunnel
# =============================================================================


@fleet_router.websocket("/ws/relay")
async def relay_websocket_tunnel(websocket: WebSocket):
    """
    WebSocket endpoint for relay agent tunnels.

    Relay agents on local networks connect here to establish a
    persistent tunnel. All fleet operations for that network are
    then routed through this tunnel.

    Protocol:
    1. Relay sends: {"type": "auth", "token": "...", "identity": {...}}
    2. Server responds: {"type": "auth_ok"} or {"type": "auth_failed"}
    3. Server sends commands: {"type": "command", "command_id": "...", ...}
    4. Relay responds: {"type": "command_response", "command_id": "...", "result": {...}}
    5. Periodic heartbeats in both directions
    """
    await websocket.accept()

    fleet = await _get_fleet_async()
    bridge = fleet.relay_bridge
    relay_id = None

    try:
        # Step 1: Wait for authentication message
        auth_msg = await websocket.receive_json()

        if auth_msg.get("type") != "auth":
            await websocket.send_json(
                {
                    "type": "auth_failed",
                    "error": "Expected auth message",
                }
            )
            await websocket.close(code=1008)
            return

        token = auth_msg.get("token", "")
        identity_data = auth_msg.get("identity", {})

        # Validate token
        validated_id = bridge.validate_token(token)
        if not validated_id:
            await websocket.send_json(
                {
                    "type": "auth_failed",
                    "error": "Invalid relay token",
                }
            )
            await websocket.close(code=1008)
            return

        # Build identity
        from ag3ntwerk.modules.distributed.relay import RelayIdentity, RelayCapability

        identity = RelayIdentity(
            relay_id=validated_id,
            name=identity_data.get("name", ""),
            hostname=identity_data.get("hostname", ""),
            platform=identity_data.get("platform", ""),
            version=identity_data.get("version", "0.1.0"),
            capabilities=[
                RelayCapability(c)
                for c in identity_data.get("capabilities", [])
                if c in [e.value for e in RelayCapability]
            ]
            or list(RelayCapability),
            networks=identity_data.get("networks", []),
        )

        # Register the relay
        conn = await bridge.register_relay(websocket, token, identity)
        if not conn:
            await websocket.send_json(
                {
                    "type": "auth_failed",
                    "error": "Registration failed",
                }
            )
            await websocket.close(code=1008)
            return

        relay_id = validated_id
        await websocket.send_json({"type": "auth_ok", "relay_id": relay_id})
        logger.info(f"Relay tunnel established: {identity.name} ({relay_id})")

        # Step 2: Message loop
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type", "")

            if msg_type == "heartbeat_response":
                import time

                await bridge.handle_heartbeat(relay_id)

            elif msg_type == "command_response":
                command_id = message.get("command_id", "")
                result = message.get("result", {})
                await bridge.handle_command_response(relay_id, command_id, result)

            elif msg_type == "heartbeat":
                await websocket.send_json(
                    {
                        "type": "heartbeat_response",
                        "timestamp": __import__("datetime")
                        .datetime.now(__import__("datetime").timezone.utc)
                        .isoformat(),
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"Relay tunnel disconnected: {relay_id}")
    except Exception as e:
        logger.error(f"Relay tunnel error: {e}")
    finally:
        if relay_id:
            await bridge.unregister_relay(relay_id)
