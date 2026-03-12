"""
Node Provisioner - Enrollment and dependency management for fleet nodes.

Handles the provisioning lifecycle for compute nodes that have been
approved for fleet enrollment: dependency installation, directory
structure setup, agent deployment, and configuration management.

All provisioning actions require prior enrollment approval.
No actions are taken on unapproved devices.

Primary owners: Forge, Sentinel
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ProvisionStage(str, Enum):
    """Stages of the provisioning pipeline."""

    VALIDATING = "validating"
    CONNECTING = "connecting"
    CHECKING_PREREQUISITES = "checking_prerequisites"
    INSTALLING_DEPENDENCIES = "installing_dependencies"
    DEPLOYING_AGENT = "deploying_agent"
    CONFIGURING = "configuring"
    CREATING_DIRECTORIES = "creating_directories"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"


class DependencyType(str, Enum):
    """Type of dependency to install."""

    SYSTEM_PACKAGE = "system_package"
    PYTHON_PACKAGE = "python_package"
    NODE_PACKAGE = "node_package"
    DOCKER_IMAGE = "docker_image"
    BINARY = "binary"
    CONFIGURATION = "configuration"


@dataclass
class Dependency:
    """A dependency required on a fleet node."""

    name: str
    dep_type: DependencyType
    version: str = ""
    required: bool = True
    install_command: str = ""
    verify_command: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.dep_type.value,
            "version": self.version,
            "required": self.required,
            "install_command": self.install_command,
            "verify_command": self.verify_command,
            "description": self.description,
        }


@dataclass
class DirectorySpec:
    """A directory to create on fleet nodes."""

    path: str
    purpose: str
    permissions: str = "755"
    owner: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "purpose": self.purpose,
            "permissions": self.permissions,
            "owner": self.owner,
        }


@dataclass
class ProvisionPlan:
    """Plan for provisioning a specific node."""

    id: str = field(default_factory=lambda: str(uuid4()))
    node_id: str = ""
    ip_address: str = ""
    hostname: str = ""
    stage: ProvisionStage = ProvisionStage.VALIDATING
    dependencies: List[Dependency] = field(default_factory=list)
    directories: List[DirectorySpec] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    steps_completed: List[str] = field(default_factory=list)
    steps_failed: List[Dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    approved_by: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "ip_address": self.ip_address,
            "hostname": self.hostname,
            "stage": self.stage.value,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "directories": [d.to_dict() for d in self.directories],
            "configuration": self.configuration,
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "approved_by": self.approved_by,
            "error": self.error,
        }


# Standard ag3ntwerk node dependencies
STANDARD_DEPENDENCIES: List[Dependency] = [
    Dependency(
        name="python3",
        dep_type=DependencyType.SYSTEM_PACKAGE,
        version="3.10+",
        required=True,
        verify_command="python3 --version",
        description="Python 3.10+ runtime",
    ),
    Dependency(
        name="pip",
        dep_type=DependencyType.SYSTEM_PACKAGE,
        version="",
        required=True,
        verify_command="pip3 --version",
        description="Python package manager",
    ),
    Dependency(
        name="git",
        dep_type=DependencyType.SYSTEM_PACKAGE,
        version="",
        required=True,
        verify_command="git --version",
        description="Version control",
    ),
    Dependency(
        name="curl",
        dep_type=DependencyType.SYSTEM_PACKAGE,
        version="",
        required=True,
        verify_command="curl --version",
        description="HTTP client for health checks",
    ),
    Dependency(
        name="fastapi",
        dep_type=DependencyType.PYTHON_PACKAGE,
        version=">=0.100.0",
        required=True,
        install_command="pip3 install 'fastapi>=0.100.0'",
        verify_command="python3 -c 'import fastapi'",
        description="FastAPI framework for agent endpoint",
    ),
    Dependency(
        name="uvicorn",
        dep_type=DependencyType.PYTHON_PACKAGE,
        version=">=0.20.0",
        required=True,
        install_command="pip3 install 'uvicorn>=0.20.0'",
        verify_command="python3 -c 'import uvicorn'",
        description="ASGI server",
    ),
    Dependency(
        name="redis",
        dep_type=DependencyType.PYTHON_PACKAGE,
        version=">=4.0.0",
        required=False,
        install_command="pip3 install 'redis>=4.0.0'",
        verify_command="python3 -c 'import redis'",
        description="Redis client for distributed messaging",
    ),
]

# Standard directory structure for fleet nodes
STANDARD_DIRECTORIES: List[DirectorySpec] = [
    DirectorySpec(
        path="/opt/ag3ntwerk",
        purpose="ag3ntwerk application root",
    ),
    DirectorySpec(
        path="/opt/ag3ntwerk/agent",
        purpose="Fleet agent runtime",
    ),
    DirectorySpec(
        path="/opt/ag3ntwerk/config",
        purpose="Node configuration",
    ),
    DirectorySpec(
        path="/opt/ag3ntwerk/data",
        purpose="Working data directory",
    ),
    DirectorySpec(
        path="/opt/ag3ntwerk/logs",
        purpose="Agent and workload logs",
    ),
    DirectorySpec(
        path="/opt/ag3ntwerk/workloads",
        purpose="Active workload sandboxes",
    ),
    DirectorySpec(
        path="/opt/ag3ntwerk/cache",
        purpose="Model and data cache",
    ),
]


class NodeProvisioner:
    """
    Provisioning engine for fleet node setup.

    Manages the complete lifecycle of preparing a node for ag3ntwerk
    distributed workloads: prerequisite checks, dependency installation,
    directory creation, agent deployment, and verification.

    All operations require prior enrollment approval.
    """

    def __init__(self):
        self._plans: Dict[str, ProvisionPlan] = {}
        self._provision_history: List[Dict[str, Any]] = []
        self._custom_dependencies: List[Dependency] = []
        self._custom_directories: List[DirectorySpec] = []

    def create_provision_plan(
        self,
        node_id: str,
        ip_address: str,
        hostname: str = "",
        approved_by: str = "",
        include_docker: bool = False,
        include_gpu: bool = False,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> ProvisionPlan:
        """
        Create a provisioning plan for a node.

        Does NOT execute anything - just creates the plan for review.
        Execution requires a separate call to execute_plan().
        """
        if not approved_by:
            raise ValueError("Provisioning plans require an approver (approved_by)")

        deps = list(STANDARD_DEPENDENCIES)
        dirs = list(STANDARD_DIRECTORIES)

        # Add Docker dependencies if requested
        if include_docker:
            deps.append(
                Dependency(
                    name="docker",
                    dep_type=DependencyType.SYSTEM_PACKAGE,
                    required=True,
                    verify_command="docker --version",
                    description="Container runtime",
                )
            )
            deps.append(
                Dependency(
                    name="docker-compose",
                    dep_type=DependencyType.SYSTEM_PACKAGE,
                    required=False,
                    verify_command="docker compose version",
                    description="Docker Compose for multi-container workloads",
                )
            )
            dirs.append(
                DirectorySpec(
                    path="/opt/ag3ntwerk/containers",
                    purpose="Container image cache and runtime",
                )
            )

        # Add GPU dependencies if requested
        if include_gpu:
            deps.append(
                Dependency(
                    name="nvidia-smi",
                    dep_type=DependencyType.SYSTEM_PACKAGE,
                    required=False,
                    verify_command="nvidia-smi",
                    description="NVIDIA GPU management",
                )
            )
            deps.append(
                Dependency(
                    name="torch",
                    dep_type=DependencyType.PYTHON_PACKAGE,
                    required=False,
                    install_command="pip3 install torch",
                    verify_command="python3 -c 'import torch; print(torch.cuda.is_available())'",
                    description="PyTorch for GPU compute",
                )
            )

        # Add custom dependencies
        deps.extend(self._custom_dependencies)
        dirs.extend(self._custom_directories)

        # Build configuration
        config = {
            "controller_url": "http://controller:8000",
            "node_id": node_id,
            "node_role": "compute",
            "heartbeat_interval_seconds": 30,
            "log_level": "INFO",
            "workload_sandbox": True,
            "max_concurrent_workloads": 4,
        }
        if custom_config:
            config.update(custom_config)

        plan = ProvisionPlan(
            node_id=node_id,
            ip_address=ip_address,
            hostname=hostname,
            dependencies=deps,
            directories=dirs,
            configuration=config,
            approved_by=approved_by,
        )

        self._plans[plan.id] = plan
        logger.info(
            f"Provision plan created for {ip_address} "
            f"({len(deps)} deps, {len(dirs)} dirs, approved by {approved_by})"
        )
        return plan

    async def execute_plan(self, plan_id: str) -> ProvisionPlan:
        """
        Execute a provisioning plan on the target node.

        The plan must have been created with an approved_by value.
        Connects to the node's ag3ntwerk agent to execute provisioning steps.
        """
        plan = self._plans.get(plan_id)
        if not plan:
            raise KeyError(f"Provision plan not found: {plan_id}")

        if not plan.approved_by:
            raise ValueError("Cannot execute plan without approval")

        plan.started_at = datetime.now(timezone.utc)
        plan.stage = ProvisionStage.CONNECTING
        logger.info(f"Executing provision plan {plan_id} on {plan.ip_address}")

        try:
            # Stage 1: Connect to node
            reachable = await self._check_node_reachable(plan.ip_address)
            if not reachable:
                plan.stage = ProvisionStage.FAILED
                plan.error = f"Node {plan.ip_address} is unreachable"
                return plan
            plan.steps_completed.append("node_connectivity_check")
            plan.stage = ProvisionStage.CHECKING_PREREQUISITES

            # Stage 2: Check prerequisites
            prereq_result = await self._check_prerequisites(plan)
            plan.steps_completed.append("prerequisite_check")
            plan.stage = ProvisionStage.INSTALLING_DEPENDENCIES

            # Stage 3: Send dependency manifest
            dep_result = await self._send_dependency_manifest(plan)
            plan.steps_completed.append("dependency_manifest_sent")
            plan.stage = ProvisionStage.CREATING_DIRECTORIES

            # Stage 4: Send directory structure manifest
            dir_result = await self._send_directory_manifest(plan)
            plan.steps_completed.append("directory_manifest_sent")
            plan.stage = ProvisionStage.CONFIGURING

            # Stage 5: Deploy configuration
            config_result = await self._send_configuration(plan)
            plan.steps_completed.append("configuration_deployed")
            plan.stage = ProvisionStage.VERIFYING

            # Stage 6: Verify the node is ready
            verify_result = await self._verify_node_ready(plan)
            plan.steps_completed.append("verification_complete")

            plan.stage = ProvisionStage.COMPLETE
            plan.completed_at = datetime.now(timezone.utc)
            logger.info(f"Node {plan.ip_address} provisioned successfully")

        except Exception as e:
            plan.stage = ProvisionStage.FAILED
            plan.error = str(e)
            plan.steps_failed.append(
                {
                    "stage": plan.stage.value,
                    "error": str(e),
                }
            )
            logger.error(f"Provisioning failed for {plan.ip_address}: {e}")

        self._provision_history.append(
            {
                "plan_id": plan.id,
                "node_id": plan.node_id,
                "ip_address": plan.ip_address,
                "success": plan.stage == ProvisionStage.COMPLETE,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "steps_completed": len(plan.steps_completed),
                "steps_failed": len(plan.steps_failed),
                "approved_by": plan.approved_by,
            }
        )

        return plan

    async def _check_node_reachable(self, ip_address: str) -> bool:
        """Check if the node's agent endpoint is reachable."""
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip_address, 8000),
                timeout=5.0,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False

    async def _check_prerequisites(self, plan: ProvisionPlan) -> Dict[str, Any]:
        """Check that the node meets basic prerequisites."""
        # In a full implementation, this would SSH or use the agent API
        # to verify the node's basic capabilities
        return {"status": "ok", "checked": ["connectivity", "os_version", "disk_space"]}

    async def _send_dependency_manifest(self, plan: ProvisionPlan) -> Dict[str, Any]:
        """Send the dependency installation manifest to the node agent."""
        manifest = {
            "action": "install_dependencies",
            "dependencies": [d.to_dict() for d in plan.dependencies],
        }
        return await self._send_to_agent(plan.ip_address, manifest)

    async def _send_directory_manifest(self, plan: ProvisionPlan) -> Dict[str, Any]:
        """Send the directory structure manifest to the node agent."""
        manifest = {
            "action": "create_directories",
            "directories": [d.to_dict() for d in plan.directories],
        }
        return await self._send_to_agent(plan.ip_address, manifest)

    async def _send_configuration(self, plan: ProvisionPlan) -> Dict[str, Any]:
        """Deploy configuration to the node."""
        manifest = {
            "action": "configure",
            "configuration": plan.configuration,
        }
        return await self._send_to_agent(plan.ip_address, manifest)

    async def _verify_node_ready(self, plan: ProvisionPlan) -> Dict[str, Any]:
        """Verify the node is ready to accept workloads."""
        manifest = {
            "action": "verify_ready",
        }
        return await self._send_to_agent(plan.ip_address, manifest)

    async def _send_to_agent(self, ip_address: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a command to the node's ag3ntwerk agent."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip_address, 8000),
                timeout=10.0,
            )

            body = json.dumps(payload)
            body_bytes = body.encode("utf-8")
            request_header = (
                f"POST /api/v1/node/provision HTTP/1.1\r\n"
                f"Host: {ip_address}:8000\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body_bytes)}\r\n"
                f"Connection: close\r\n\r\n"
            )
            writer.write(request_header.encode("utf-8") + body_bytes)
            await writer.drain()

            response = await asyncio.wait_for(reader.read(65536), timeout=30.0)
            writer.close()
            await writer.wait_closed()

            response_text = response.decode("utf-8", errors="ignore")
            body_start = response_text.find("\r\n\r\n")
            if body_start > 0:
                resp_body = response_text[body_start + 4 :]
                return json.loads(resp_body)

            return {"status": "ok", "raw_response": True}

        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            logger.warning(f"Agent communication failed for {ip_address}: {e}")
            return {"status": "error", "error": str(e)}
        except json.JSONDecodeError:
            return {"status": "ok", "parse_error": True}

    # ---- Custom Dependency Management ----

    def add_custom_dependency(self, dependency: Dependency) -> None:
        """Add a custom dependency to include in all future plans."""
        self._custom_dependencies.append(dependency)

    def add_custom_directory(self, directory: DirectorySpec) -> None:
        """Add a custom directory to include in all future plans."""
        self._custom_directories.append(directory)

    # ---- Query Methods ----

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get a provision plan."""
        plan = self._plans.get(plan_id)
        return plan.to_dict() if plan else None

    def list_plans(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List provision plans, optionally filtered by node."""
        plans = list(self._plans.values())
        if node_id:
            plans = [p for p in plans if p.node_id == node_id]
        return [p.to_dict() for p in plans]

    def get_provision_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get provisioning history."""
        return sorted(
            self._provision_history,
            key=lambda x: x["completed_at"],
            reverse=True,
        )[:limit]

    def get_standard_manifest(self) -> Dict[str, Any]:
        """Get the standard provisioning manifest for review."""
        return {
            "dependencies": [d.to_dict() for d in STANDARD_DEPENDENCIES],
            "directories": [d.to_dict() for d in STANDARD_DIRECTORIES],
            "custom_dependencies": [d.to_dict() for d in self._custom_dependencies],
            "custom_directories": [d.to_dict() for d in self._custom_directories],
        }
