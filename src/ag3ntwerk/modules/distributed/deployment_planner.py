"""
Deployment Planner - Guided, approval-gated deployment plan generation.

Generates comprehensive, human-readable deployment plans for end-to-end
node assimilation into the ag3ntwerk fleet. Every phase of the plan must
be reviewed and explicitly approved before execution proceeds.

The planner covers the full lifecycle:
  1. Network assessment and device profiling
  2. Storage analysis and filesystem preparation
  3. OS evaluation and configuration recommendations
  4. Dependency resolution and installation guides
  5. ag3ntwerk agent deployment and configuration
  6. Workload allocation planning
  7. Verification and health checks

NO steps execute automatically. The operator reviews each phase,
approves or modifies it, and then triggers execution of that phase only.

Primary owners: Nexus, Forge
"""

import asyncio
import hashlib
import logging
import platform
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class PlanStatus(str, Enum):
    """Overall status of a deployment plan."""

    DRAFT = "draft"
    AWAITING_REVIEW = "awaiting_review"
    PARTIALLY_APPROVED = "partially_approved"
    FULLY_APPROVED = "fully_approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PhaseStatus(str, Enum):
    """Status of a single deployment phase."""

    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class StepRisk(str, Enum):
    """Risk level of a deployment step."""

    INFO = "info"  # Read-only / informational
    LOW = "low"  # Easily reversible
    MEDIUM = "medium"  # Reversible with effort
    HIGH = "high"  # Hard to reverse (installs, configs)
    CRITICAL = "critical"  # Destructive / irreversible (format, partition)


class TargetOS(str, Enum):
    """Target operating systems."""

    UBUNTU = "ubuntu"
    DEBIAN = "debian"
    CENTOS = "centos"
    RHEL = "rhel"
    FEDORA = "fedora"
    ARCH = "arch"
    ALPINE = "alpine"
    MACOS = "macos"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class DeploymentStep:
    """A single atomic step within a deployment phase."""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    order: int = 0
    title: str = ""
    description: str = ""
    risk: StepRisk = StepRisk.LOW
    commands: List[str] = field(default_factory=list)
    verify_commands: List[str] = field(default_factory=list)
    rollback_commands: List[str] = field(default_factory=list)
    expected_output: str = ""
    notes: str = ""
    estimated_duration_seconds: int = 0
    requires_reboot: bool = False
    requires_root: bool = False
    idempotent: bool = True
    executed: bool = False
    execution_output: str = ""
    execution_error: str = ""
    executed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order": self.order,
            "title": self.title,
            "description": self.description,
            "risk": self.risk.value,
            "commands": self.commands,
            "verify_commands": self.verify_commands,
            "rollback_commands": self.rollback_commands,
            "expected_output": self.expected_output,
            "notes": self.notes,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "requires_reboot": self.requires_reboot,
            "requires_root": self.requires_root,
            "idempotent": self.idempotent,
            "executed": self.executed,
            "execution_output": self.execution_output,
            "execution_error": self.execution_error,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }

    def to_guide_text(self) -> str:
        """Render this step as a human-readable guide."""
        lines = []
        risk_icon = {
            "info": "[INFO]",
            "low": "[LOW RISK]",
            "medium": "[MEDIUM RISK]",
            "high": "[HIGH RISK]",
            "critical": "[!! CRITICAL !!]",
        }
        lines.append(f"  Step {self.order}: {self.title}  {risk_icon.get(self.risk.value, '')}")
        lines.append(f"    {self.description}")
        if self.requires_root:
            lines.append("    Requires: root/sudo access")
        if self.requires_reboot:
            lines.append("    Note: Requires system reboot after completion")
        if self.notes:
            lines.append(f"    Note: {self.notes}")
        if self.commands:
            lines.append("    Commands:")
            for cmd in self.commands:
                lines.append(f"      $ {cmd}")
        if self.verify_commands:
            lines.append("    Verify with:")
            for cmd in self.verify_commands:
                lines.append(f"      $ {cmd}")
        if self.expected_output:
            lines.append(f"    Expected: {self.expected_output}")
        if self.rollback_commands:
            lines.append("    Rollback:")
            for cmd in self.rollback_commands:
                lines.append(f"      $ {cmd}")
        if self.estimated_duration_seconds:
            mins = self.estimated_duration_seconds // 60
            secs = self.estimated_duration_seconds % 60
            lines.append(f"    Estimated time: {mins}m {secs}s")
        return "\n".join(lines)


@dataclass
class DeploymentPhase:
    """A phase containing multiple ordered steps."""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    order: int = 0
    name: str = ""
    description: str = ""
    status: PhaseStatus = PhaseStatus.PENDING
    steps: List[DeploymentStep] = field(default_factory=list)
    approved_by: str = ""
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    skipped_reason: str = ""
    error: str = ""

    @property
    def max_risk(self) -> StepRisk:
        """Get the highest risk level in this phase."""
        risk_order = [
            StepRisk.INFO,
            StepRisk.LOW,
            StepRisk.MEDIUM,
            StepRisk.HIGH,
            StepRisk.CRITICAL,
        ]
        max_r = StepRisk.INFO
        for step in self.steps:
            if risk_order.index(step.risk) > risk_order.index(max_r):
                max_r = step.risk
        return max_r

    @property
    def estimated_duration_seconds(self) -> int:
        return sum(s.estimated_duration_seconds for s in self.steps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order": self.order,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "max_risk": self.max_risk.value,
            "step_count": len(self.steps),
            "steps": [s.to_dict() for s in self.steps],
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "skipped_reason": self.skipped_reason,
            "error": self.error,
            "estimated_duration_seconds": self.estimated_duration_seconds,
        }

    def to_guide_text(self) -> str:
        """Render this phase as a human-readable guide section."""
        risk_banner = ""
        if self.max_risk in (StepRisk.HIGH, StepRisk.CRITICAL):
            risk_banner = (
                f"\n  *** WARNING: This phase contains {self.max_risk.value}-risk operations ***\n"
            )

        header = (
            f"\n{'='*70}\n"
            f"PHASE {self.order}: {self.name.upper()}\n"
            f"{'='*70}\n"
            f"{self.description}\n"
            f"Steps: {len(self.steps)} | "
            f"Max Risk: {self.max_risk.value} | "
            f"Est. Time: {self.estimated_duration_seconds // 60}m {self.estimated_duration_seconds % 60}s\n"
            f"Status: {self.status.value}\n"
            f"{risk_banner}"
            f"{'-'*70}"
        )
        step_text = "\n\n".join(s.to_guide_text() for s in self.steps)
        return f"{header}\n\n{step_text}"


@dataclass
class DeploymentPlan:
    """Complete end-to-end deployment plan for a target node."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: PlanStatus = PlanStatus.DRAFT
    target_ip: str = ""
    target_hostname: str = ""
    target_os: TargetOS = TargetOS.UNKNOWN
    target_os_version: str = ""
    target_role: str = "compute_node"
    phases: List[DeploymentPhase] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    last_modified_at: Optional[datetime] = None
    fully_approved_at: Optional[datetime] = None
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None
    plan_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @property
    def total_steps(self) -> int:
        return sum(len(p.steps) for p in self.phases)

    @property
    def completed_steps(self) -> int:
        return sum(1 for p in self.phases for s in p.steps if s.executed)

    @property
    def phases_approved(self) -> int:
        return len(
            [p for p in self.phases if p.status in (PhaseStatus.APPROVED, PhaseStatus.COMPLETED)]
        )

    @property
    def estimated_total_duration_seconds(self) -> int:
        return sum(p.estimated_duration_seconds for p in self.phases)

    def compute_hash(self) -> str:
        """Compute a content hash for integrity verification."""
        content = f"{self.target_ip}:{self.target_hostname}:{len(self.phases)}"
        for phase in self.phases:
            for step in phase.steps:
                content += f":{step.title}:{'|'.join(step.commands)}"
        self.plan_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return self.plan_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "target_ip": self.target_ip,
            "target_hostname": self.target_hostname,
            "target_os": self.target_os.value,
            "target_os_version": self.target_os_version,
            "target_role": self.target_role,
            "phase_count": len(self.phases),
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "phases_approved": self.phases_approved,
            "phases": [p.to_dict() for p in self.phases],
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "last_modified_at": (
                self.last_modified_at.isoformat() if self.last_modified_at else None
            ),
            "fully_approved_at": (
                self.fully_approved_at.isoformat() if self.fully_approved_at else None
            ),
            "execution_started_at": (
                self.execution_started_at.isoformat() if self.execution_started_at else None
            ),
            "execution_completed_at": (
                self.execution_completed_at.isoformat() if self.execution_completed_at else None
            ),
            "estimated_total_duration_seconds": self.estimated_total_duration_seconds,
            "plan_hash": self.plan_hash,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    def to_guide_text(self) -> str:
        """Render the complete plan as a human-readable deployment guide."""
        est_total = self.estimated_total_duration_seconds
        header = textwrap.dedent(
            f"""\
        {'#'*70}
        #  AG3NTWERK FLEET DEPLOYMENT PLAN
        #  Plan ID: {self.id[:12]}
        #  Hash: {self.plan_hash or 'not computed'}
        {'#'*70}

        Target:     {self.target_ip} ({self.target_hostname or 'unknown'})
        OS:         {self.target_os.value} {self.target_os_version}
        Role:       {self.target_role}
        Status:     {self.status.value}
        Created:    {self.created_at.strftime('%Y-%m-%d %H:%M UTC')}
        Created By: {self.created_by or 'system'}

        Phases:     {len(self.phases)}
        Steps:      {self.total_steps}
        Approved:   {self.phases_approved}/{len(self.phases)} phases
        Completed:  {self.completed_steps}/{self.total_steps} steps
        Est. Time:  {est_total // 3600}h {(est_total % 3600) // 60}m
        """
        )

        if self.warnings:
            header += "\nWARNINGS:\n"
            for w in self.warnings:
                header += f"  ! {w}\n"

        header += textwrap.dedent(
            """
        APPROVAL PROCESS:
          Each phase below must be reviewed and approved individually.
          You may skip phases that are not applicable.
          Phases with CRITICAL risk steps require extra confirmation.
          No commands are executed until you explicitly approve and trigger them.
        """
        )

        phase_text = "\n".join(p.to_guide_text() for p in self.phases)

        footer = textwrap.dedent(
            f"""
        {'='*70}
        END OF DEPLOYMENT PLAN
        {'='*70}
        To approve a phase:  POST /api/v1/fleet/plans/{self.id}/phases/{{phase_id}}/approve
        To execute a phase:  POST /api/v1/fleet/plans/{self.id}/phases/{{phase_id}}/execute
        To skip a phase:     POST /api/v1/fleet/plans/{self.id}/phases/{{phase_id}}/skip
        To cancel the plan:  POST /api/v1/fleet/plans/{self.id}/cancel
        """
        )

        return f"{header}\n{phase_text}\n{footer}"


# =============================================================================
# Package Manager Mapping
# =============================================================================

# Maps target OS to its package manager and common install patterns
OS_PACKAGE_MANAGERS: Dict[str, Dict[str, Any]] = {
    "ubuntu": {
        "manager": "apt",
        "update": "sudo apt update",
        "install": "sudo apt install -y",
        "python": "python3",
        "pip": "pip3",
        "python_pkg": "python3 python3-pip python3-venv",
        "docker_install": [
            "sudo apt install -y ca-certificates curl gnupg",
            "sudo install -m 0755 -d /etc/apt/keyrings",
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
            "sudo chmod a+r /etc/apt/keyrings/docker.gpg",
            'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
            "sudo apt update",
            "sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
        ],
    },
    "debian": {
        "manager": "apt",
        "update": "sudo apt update",
        "install": "sudo apt install -y",
        "python": "python3",
        "pip": "pip3",
        "python_pkg": "python3 python3-pip python3-venv",
        "docker_install": [
            "sudo apt install -y ca-certificates curl gnupg",
            "sudo install -m 0755 -d /etc/apt/keyrings",
            "curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
            "sudo chmod a+r /etc/apt/keyrings/docker.gpg",
            'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
            "sudo apt update",
            "sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
        ],
    },
    "centos": {
        "manager": "yum",
        "update": "sudo yum check-update || true",
        "install": "sudo yum install -y",
        "python": "python3",
        "pip": "pip3",
        "python_pkg": "python3 python3-pip",
        "docker_install": [
            "sudo yum install -y yum-utils",
            "sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo",
            "sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
            "sudo systemctl start docker",
            "sudo systemctl enable docker",
        ],
    },
    "rhel": {
        "manager": "dnf",
        "update": "sudo dnf check-update || true",
        "install": "sudo dnf install -y",
        "python": "python3",
        "pip": "pip3",
        "python_pkg": "python3 python3-pip",
        "docker_install": [
            "sudo dnf install -y dnf-plugins-core",
            "sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo",
            "sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
            "sudo systemctl start docker",
            "sudo systemctl enable docker",
        ],
    },
    "fedora": {
        "manager": "dnf",
        "update": "sudo dnf check-update || true",
        "install": "sudo dnf install -y",
        "python": "python3",
        "pip": "pip3",
        "python_pkg": "python3 python3-pip",
        "docker_install": [
            "sudo dnf install -y dnf-plugins-core",
            "sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo",
            "sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
            "sudo systemctl start docker",
            "sudo systemctl enable docker",
        ],
    },
    "arch": {
        "manager": "pacman",
        "update": "sudo pacman -Sy",
        "install": "sudo pacman -S --noconfirm",
        "python": "python",
        "pip": "pip",
        "python_pkg": "python python-pip",
        "docker_install": [
            "sudo pacman -S --noconfirm docker docker-compose",
            "sudo systemctl start docker",
            "sudo systemctl enable docker",
        ],
    },
    "alpine": {
        "manager": "apk",
        "update": "sudo apk update",
        "install": "sudo apk add --no-cache",
        "python": "python3",
        "pip": "pip3",
        "python_pkg": "python3 py3-pip",
        "docker_install": [
            "sudo apk add --no-cache docker docker-compose",
            "sudo rc-update add docker boot",
            "sudo service docker start",
        ],
    },
    "macos": {
        "manager": "brew",
        "update": "brew update",
        "install": "brew install",
        "python": "python3",
        "pip": "pip3",
        "python_pkg": "python@3.11",
        "docker_install": ["brew install --cask docker"],
    },
}


# =============================================================================
# Deployment Planner
# =============================================================================


class DeploymentPlanner:
    """
    Generates comprehensive, approval-gated deployment plans.

    Analyzes a target device's discovered profile and generates
    a complete step-by-step guide covering:
    - Network assessment and connectivity verification
    - Storage analysis and filesystem preparation
    - OS configuration and hardening
    - Dependency installation (OS packages, Python, Docker, etc.)
    - ag3ntwerk agent deployment
    - Fleet registration and workload allocation

    Every phase requires explicit approval before execution.
    """

    def __init__(self):
        self._plans: Dict[str, DeploymentPlan] = {}

    def generate_plan(
        self,
        target_ip: str,
        target_hostname: str = "",
        target_os: str = "unknown",
        target_os_version: str = "",
        target_role: str = "compute_node",
        created_by: str = "",
        include_docker: bool = True,
        include_gpu: bool = False,
        include_storage_prep: bool = False,
        target_storage_device: str = "",
        controller_url: str = "http://controller:8000",
        node_resources: Optional[Dict[str, Any]] = None,
        device_fingerprint: Optional[Dict[str, Any]] = None,
    ) -> DeploymentPlan:
        """
        Generate a complete deployment plan for a target node.

        Returns the plan for review -- nothing is executed.
        """
        os_key = target_os.lower() if target_os else "unknown"
        os_enum = TargetOS(os_key) if os_key in TargetOS.__members__.values() else TargetOS.UNKNOWN
        os_info = OS_PACKAGE_MANAGERS.get(os_key, OS_PACKAGE_MANAGERS.get("ubuntu", {}))

        plan = DeploymentPlan(
            name=f"Deploy ag3ntwerk Node: {target_ip}",
            description=(
                f"End-to-end deployment plan for adding {target_ip} "
                f"({target_hostname or 'unknown host'}) to the ag3ntwerk fleet "
                f"as a {target_role}."
            ),
            target_ip=target_ip,
            target_hostname=target_hostname,
            target_os=os_enum,
            target_os_version=target_os_version,
            target_role=target_role,
            created_by=created_by,
            metadata={
                "controller_url": controller_url,
                "include_docker": include_docker,
                "include_gpu": include_gpu,
                "include_storage_prep": include_storage_prep,
            },
        )

        # ---- Phase 1: Network Assessment ----
        plan.phases.append(self._build_network_assessment_phase(target_ip, device_fingerprint))

        # ---- Phase 2: Storage Preparation (optional) ----
        if include_storage_prep and target_storage_device:
            plan.phases.append(
                self._build_storage_preparation_phase(target_storage_device, node_resources)
            )

        # ---- Phase 3: OS Configuration ----
        plan.phases.append(self._build_os_configuration_phase(os_key, os_info, target_os_version))

        # ---- Phase 4: Core Dependencies ----
        plan.phases.append(self._build_core_dependencies_phase(os_key, os_info))

        # ---- Phase 5: Docker Setup (optional) ----
        if include_docker:
            plan.phases.append(self._build_docker_setup_phase(os_key, os_info))

        # ---- Phase 6: GPU Setup (optional) ----
        if include_gpu:
            plan.phases.append(self._build_gpu_setup_phase(os_key))

        # ---- Phase 7: ag3ntwerk Agent Deployment ----
        plan.phases.append(
            self._build_agent_deployment_phase(target_ip, controller_url, target_role)
        )

        # ---- Phase 8: Directory Structure ----
        plan.phases.append(self._build_directory_structure_phase())

        # ---- Phase 9: Fleet Registration ----
        plan.phases.append(
            self._build_fleet_registration_phase(
                target_ip, target_hostname, target_role, controller_url
            )
        )

        # ---- Phase 10: Verification and Health Check ----
        plan.phases.append(self._build_verification_phase(target_ip, controller_url))

        # Number all phases and steps
        for i, phase in enumerate(plan.phases, 1):
            phase.order = i
            phase.status = PhaseStatus.AWAITING_APPROVAL
            for j, step in enumerate(phase.steps, 1):
                step.order = j

        # Add warnings
        if os_enum == TargetOS.UNKNOWN:
            plan.warnings.append(
                "Target OS is unknown. Package installation commands may need adjustment."
            )
        if include_storage_prep:
            plan.warnings.append(
                "Storage preparation phase contains CRITICAL-risk operations "
                "(disk formatting). Review carefully before approving."
            )

        plan.status = PlanStatus.AWAITING_REVIEW
        plan.compute_hash()
        self._plans[plan.id] = plan

        logger.info(
            f"Deployment plan generated: {plan.id[:12]} for {target_ip} "
            f"({len(plan.phases)} phases, {plan.total_steps} steps)"
        )
        return plan

    # ---- Phase Builders ----

    def _build_network_assessment_phase(
        self,
        target_ip: str,
        fingerprint: Optional[Dict[str, Any]] = None,
    ) -> DeploymentPhase:
        """Build the network assessment and connectivity phase."""
        phase = DeploymentPhase(
            name="Network Assessment & Connectivity",
            description="Verify network connectivity, SSH access, and baseline port status.",
        )

        phase.steps.append(
            DeploymentStep(
                title="Verify network reachability",
                description=f"Confirm that {target_ip} is reachable from the controller.",
                risk=StepRisk.INFO,
                commands=[f"ping -c 3 -W 2 {target_ip}"],
                expected_output="3 packets transmitted, 3 received",
                estimated_duration_seconds=10,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Test SSH connectivity",
                description="Verify SSH access to the target node. You will need credentials.",
                risk=StepRisk.LOW,
                commands=[
                    f"ssh -o ConnectTimeout=5 -o BatchMode=yes user@{target_ip} 'echo SSH_OK'"
                ],
                expected_output="SSH_OK",
                notes="Replace 'user' with your actual SSH username. Set up key-based auth for automation.",
                estimated_duration_seconds=15,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Gather system information",
                description="Collect OS, architecture, and hardware details from the target.",
                risk=StepRisk.INFO,
                commands=[
                    f"ssh user@{target_ip} 'uname -a'",
                    f"ssh user@{target_ip} 'cat /etc/os-release 2>/dev/null || sw_vers 2>/dev/null || echo UNKNOWN_OS'",
                    f"ssh user@{target_ip} 'free -h 2>/dev/null || sysctl hw.memsize 2>/dev/null'",
                    f"ssh user@{target_ip} 'df -h /'",
                    f"ssh user@{target_ip} 'nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null'",
                ],
                notes="Output from these commands informs all subsequent phases.",
                estimated_duration_seconds=20,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Check firewall and required ports",
                description="Verify that required ports can be opened for ag3ntwerk communication.",
                risk=StepRisk.INFO,
                commands=[
                    f"ssh user@{target_ip} 'sudo iptables -L -n 2>/dev/null || sudo ufw status 2>/dev/null || echo NO_FIREWALL_TOOL'",
                    f"ssh user@{target_ip} 'ss -tlnp 2>/dev/null | head -20'",
                ],
                notes="ag3ntwerk agent needs ports 8000 (API), 9876 (beacon). Redis needs 6379 if distributed.",
                estimated_duration_seconds=10,
            )
        )

        return phase

    def _build_storage_preparation_phase(
        self,
        storage_device: str,
        resources: Optional[Dict[str, Any]] = None,
    ) -> DeploymentPhase:
        """Build the storage preparation phase with disk operations."""
        phase = DeploymentPhase(
            name="Storage & Filesystem Preparation",
            description=(
                f"Prepare storage device {storage_device} for ag3ntwerk data. "
                "THIS PHASE CONTAINS DESTRUCTIVE OPERATIONS. Review each step carefully."
            ),
        )

        phase.steps.append(
            DeploymentStep(
                title="Inspect current disk layout",
                description=f"Examine the current partition table and usage of {storage_device}.",
                risk=StepRisk.INFO,
                commands=[
                    f"lsblk {storage_device}",
                    f"sudo fdisk -l {storage_device}",
                    f"sudo blkid {storage_device}*",
                ],
                notes="Review output carefully. Ensure you are targeting the correct device.",
                estimated_duration_seconds=10,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Back up existing data (if any)",
                description=f"If {storage_device} has existing data, back it up before proceeding.",
                risk=StepRisk.HIGH,
                commands=[
                    f"# If the device has a mountpoint, back up important data:",
                    f"# sudo rsync -av /mnt/existing/ /backup/location/",
                    f"# Verify backup before continuing",
                ],
                notes="SKIP this step if the device is empty/new. This is a safety checkpoint.",
                estimated_duration_seconds=300,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title=f"Create partition on {storage_device}",
                description=f"Create a single partition spanning {storage_device} for ag3ntwerk data.",
                risk=StepRisk.CRITICAL,
                commands=[
                    f"# WARNING: This will DESTROY all data on {storage_device}",
                    f"# Ensure this is the correct device before proceeding!",
                    f"sudo parted {storage_device} --script mklabel gpt",
                    f"sudo parted {storage_device} --script mkpart primary ext4 0% 100%",
                ],
                verify_commands=[f"lsblk {storage_device}"],
                rollback_commands=[
                    f"# Partition table changes cannot be easily undone.",
                    f"# If this was wrong, restore from backup.",
                ],
                requires_root=True,
                notes="THIS DESTROYS ALL DATA on the device. Triple-check the device name.",
                estimated_duration_seconds=30,
                idempotent=False,
            )
        )

        partition = (
            f"{storage_device}1" if not storage_device[-1].isdigit() else f"{storage_device}p1"
        )

        phase.steps.append(
            DeploymentStep(
                title=f"Format partition as ext4",
                description=f"Create an ext4 filesystem on {partition}.",
                risk=StepRisk.CRITICAL,
                commands=[
                    f"# WARNING: This will format {partition}",
                    f"sudo mkfs.ext4 -L ag3ntwerk-data {partition}",
                ],
                verify_commands=[f"sudo blkid {partition}"],
                expected_output='TYPE="ext4"',
                requires_root=True,
                estimated_duration_seconds=60,
                idempotent=False,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Mount filesystem and configure auto-mount",
                description=f"Mount {partition} at /opt/ag3ntwerk and add to /etc/fstab.",
                risk=StepRisk.HIGH,
                commands=[
                    "sudo mkdir -p /opt/ag3ntwerk",
                    f"sudo mount {partition} /opt/ag3ntwerk",
                    f'echo "{partition} /opt/ag3ntwerk ext4 defaults,noatime 0 2" | sudo tee -a /etc/fstab',
                ],
                verify_commands=["df -h /opt/ag3ntwerk", "mount | grep ag3ntwerk"],
                rollback_commands=[
                    "sudo umount /opt/ag3ntwerk",
                    "sudo sed -i '/ag3ntwerk-data/d' /etc/fstab",
                ],
                requires_root=True,
                estimated_duration_seconds=15,
            )
        )

        return phase

    def _build_os_configuration_phase(
        self, os_key: str, os_info: Dict, os_version: str
    ) -> DeploymentPhase:
        """Build OS configuration and hardening phase."""
        update_cmd = os_info.get("update", "# No update command for this OS")
        install_cmd = os_info.get("install", "# No install command for this OS")

        phase = DeploymentPhase(
            name="OS Configuration & System Preparation",
            description="Update system packages, configure firewall, set hostname, and prepare the environment.",
        )

        phase.steps.append(
            DeploymentStep(
                title="Update system packages",
                description="Bring all system packages to their latest versions.",
                risk=StepRisk.MEDIUM,
                commands=[
                    update_cmd,
                    (
                        f"{install_cmd} curl wget git ca-certificates gnupg"
                        if "apt" in str(os_info.get("manager", ""))
                        else f"{install_cmd} curl wget git"
                    ),
                ],
                requires_root=True,
                estimated_duration_seconds=120,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Configure firewall rules",
                description="Open required ports for ag3ntwerk agent communication.",
                risk=StepRisk.MEDIUM,
                commands=[
                    "# For UFW (Ubuntu/Debian):",
                    "sudo ufw allow 22/tcp comment 'SSH'",
                    "sudo ufw allow 8000/tcp comment 'ag3ntwerk API'",
                    "sudo ufw allow 9876/tcp comment 'ag3ntwerk Beacon'",
                    "sudo ufw --force enable",
                    "",
                    "# For firewalld (CentOS/RHEL/Fedora):",
                    "# sudo firewall-cmd --permanent --add-port=8000/tcp",
                    "# sudo firewall-cmd --permanent --add-port=9876/tcp",
                    "# sudo firewall-cmd --reload",
                ],
                verify_commands=["sudo ufw status || sudo firewall-cmd --list-ports"],
                rollback_commands=[
                    "sudo ufw delete allow 8000/tcp",
                    "sudo ufw delete allow 9876/tcp",
                ],
                requires_root=True,
                notes="Adjust commands based on your firewall tool. Keep SSH (22) open.",
                estimated_duration_seconds=15,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Create ag3ntwerk service account",
                description="Create a dedicated system user for running ag3ntwerk agent processes.",
                risk=StepRisk.LOW,
                commands=[
                    "sudo useradd --system --shell /bin/bash --home-dir /opt/ag3ntwerk --create-home ag3ntwerk 2>/dev/null || echo 'User may already exist'",
                    "sudo usermod -aG docker ag3ntwerk 2>/dev/null || true",
                ],
                verify_commands=["id ag3ntwerk"],
                rollback_commands=["sudo userdel ag3ntwerk"],
                requires_root=True,
                estimated_duration_seconds=5,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Configure system limits",
                description="Increase file descriptor and process limits for workload handling.",
                risk=StepRisk.LOW,
                commands=[
                    "echo 'ag3ntwerk soft nofile 65536' | sudo tee -a /etc/security/limits.d/ag3ntwerk.conf",
                    "echo 'ag3ntwerk hard nofile 65536' | sudo tee -a /etc/security/limits.d/ag3ntwerk.conf",
                    "echo 'ag3ntwerk soft nproc 32768' | sudo tee -a /etc/security/limits.d/ag3ntwerk.conf",
                    "echo 'ag3ntwerk hard nproc 32768' | sudo tee -a /etc/security/limits.d/ag3ntwerk.conf",
                ],
                verify_commands=["cat /etc/security/limits.d/ag3ntwerk.conf"],
                rollback_commands=["sudo rm -f /etc/security/limits.d/ag3ntwerk.conf"],
                requires_root=True,
                estimated_duration_seconds=5,
            )
        )

        return phase

    def _build_core_dependencies_phase(self, os_key: str, os_info: Dict) -> DeploymentPhase:
        """Build core dependency installation phase."""
        install_cmd = os_info.get("install", "sudo apt install -y")
        python_pkg = os_info.get("python_pkg", "python3 python3-pip")
        pip_cmd = os_info.get("pip", "pip3")

        phase = DeploymentPhase(
            name="Core Dependency Installation",
            description="Install Python, pip, and required Python packages for the ag3ntwerk agent.",
        )

        phase.steps.append(
            DeploymentStep(
                title="Install Python runtime",
                description="Install Python 3.10+ and pip package manager.",
                risk=StepRisk.LOW,
                commands=[
                    f"{install_cmd} {python_pkg}",
                ],
                verify_commands=[
                    "python3 --version",
                    f"{pip_cmd} --version",
                ],
                expected_output="Python 3.10+",
                requires_root=True,
                estimated_duration_seconds=30,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Create Python virtual environment",
                description="Create an isolated Python environment for ag3ntwerk dependencies.",
                risk=StepRisk.LOW,
                commands=[
                    "sudo -u ag3ntwerk python3 -m venv /opt/ag3ntwerk/venv",
                    "sudo -u ag3ntwerk /opt/ag3ntwerk/venv/bin/pip install --upgrade pip setuptools wheel",
                ],
                verify_commands=["/opt/ag3ntwerk/venv/bin/python --version"],
                rollback_commands=["sudo rm -rf /opt/ag3ntwerk/venv"],
                estimated_duration_seconds=20,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Install ag3ntwerk Python dependencies",
                description="Install FastAPI, uvicorn, Redis client, and supporting libraries.",
                risk=StepRisk.LOW,
                commands=[
                    "/opt/ag3ntwerk/venv/bin/pip install 'fastapi>=0.100.0' 'uvicorn[standard]>=0.20.0' 'redis>=4.0.0' 'httpx>=0.24.0' 'pydantic>=2.0' 'structlog>=23.0' 'python-dotenv>=1.0'",
                ],
                verify_commands=[
                    "/opt/ag3ntwerk/venv/bin/python -c 'import fastapi; print(fastapi.__version__)'",
                    "/opt/ag3ntwerk/venv/bin/python -c 'import uvicorn; print(uvicorn.__version__)'",
                ],
                rollback_commands=[
                    "/opt/ag3ntwerk/venv/bin/pip uninstall -y fastapi uvicorn redis httpx"
                ],
                estimated_duration_seconds=45,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Install system monitoring tools",
                description="Install tools for resource monitoring and health reporting.",
                risk=StepRisk.LOW,
                commands=[
                    (
                        f"{install_cmd} htop iotop sysstat net-tools"
                        if os_key not in ("alpine", "macos")
                        else f"{install_cmd} htop sysstat"
                    ),
                ],
                requires_root=True,
                estimated_duration_seconds=15,
            )
        )

        return phase

    def _build_docker_setup_phase(self, os_key: str, os_info: Dict) -> DeploymentPhase:
        """Build Docker installation and configuration phase."""
        docker_cmds = os_info.get(
            "docker_install", ["# Docker install commands not available for this OS"]
        )

        phase = DeploymentPhase(
            name="Docker Container Runtime Setup",
            description="Install and configure Docker for containerized workload execution.",
        )

        phase.steps.append(
            DeploymentStep(
                title="Install Docker Engine",
                description="Install Docker CE and the Docker Compose plugin.",
                risk=StepRisk.MEDIUM,
                commands=docker_cmds,
                verify_commands=[
                    "docker --version",
                    "docker compose version",
                ],
                requires_root=True,
                estimated_duration_seconds=120,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Configure Docker for ag3ntwerk",
                description="Add the ag3ntwerk user to the docker group and configure Docker daemon.",
                risk=StepRisk.LOW,
                commands=[
                    "sudo usermod -aG docker ag3ntwerk",
                    'echo \'{"log-driver": "json-file", "log-opts": {"max-size": "10m", "max-file": "3"}, "storage-driver": "overlay2"}\' | sudo tee /etc/docker/daemon.json',
                    "sudo systemctl restart docker",
                ],
                verify_commands=[
                    "sudo -u ag3ntwerk docker ps",
                    "docker info --format '{{.Driver}}'",
                ],
                rollback_commands=["sudo gpasswd -d ag3ntwerk docker"],
                requires_root=True,
                estimated_duration_seconds=15,
            )
        )

        return phase

    def _build_gpu_setup_phase(self, os_key: str) -> DeploymentPhase:
        """Build GPU driver and toolkit installation phase."""
        phase = DeploymentPhase(
            name="GPU Driver & Toolkit Setup",
            description="Install NVIDIA drivers, CUDA toolkit, and GPU monitoring tools.",
        )

        phase.steps.append(
            DeploymentStep(
                title="Detect GPU hardware",
                description="Check for NVIDIA GPU presence.",
                risk=StepRisk.INFO,
                commands=["lspci | grep -i nvidia"],
                notes="If no output, this machine has no NVIDIA GPU. Skip this phase.",
                estimated_duration_seconds=5,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Install NVIDIA drivers",
                description="Install the latest NVIDIA GPU drivers.",
                risk=StepRisk.HIGH,
                commands=[
                    "# For Ubuntu/Debian:",
                    "sudo apt install -y nvidia-driver-535",
                    "",
                    "# For CentOS/RHEL:",
                    "# sudo dnf install -y nvidia-driver",
                ],
                verify_commands=["nvidia-smi"],
                requires_root=True,
                requires_reboot=True,
                notes="Driver version may vary. Check NVIDIA's compatibility matrix for your GPU.",
                estimated_duration_seconds=180,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Install NVIDIA Container Toolkit",
                description="Enable GPU access inside Docker containers.",
                risk=StepRisk.MEDIUM,
                commands=[
                    "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg",
                    "curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list",
                    "sudo apt update && sudo apt install -y nvidia-container-toolkit",
                    "sudo nvidia-ctk runtime configure --runtime=docker",
                    "sudo systemctl restart docker",
                ],
                verify_commands=["docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi"],
                requires_root=True,
                estimated_duration_seconds=90,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Install PyTorch with CUDA support",
                description="Install PyTorch for GPU-accelerated workloads.",
                risk=StepRisk.LOW,
                commands=[
                    "/opt/ag3ntwerk/venv/bin/pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121",
                ],
                verify_commands=[
                    "/opt/ag3ntwerk/venv/bin/python -c \"import torch; print(f'CUDA available: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}')\"",
                ],
                estimated_duration_seconds=120,
            )
        )

        return phase

    def _build_agent_deployment_phase(
        self,
        target_ip: str,
        controller_url: str,
        role: str,
    ) -> DeploymentPhase:
        """Build the ag3ntwerk agent deployment phase."""
        phase = DeploymentPhase(
            name="ag3ntwerk Agent Deployment",
            description="Deploy and configure the ag3ntwerk fleet agent that manages workloads on this node.",
        )

        phase.steps.append(
            DeploymentStep(
                title="Deploy agent configuration",
                description="Write the fleet agent configuration file.",
                risk=StepRisk.LOW,
                commands=[
                    "sudo mkdir -p /opt/ag3ntwerk/config",
                    f"""sudo tee /opt/ag3ntwerk/config/agent.json << 'AGENT_EOF'
{{
  "controller_url": "{controller_url}",
  "node_ip": "{target_ip}",
  "node_role": "{role}",
  "agent_port": 8000,
  "beacon_port": 9876,
  "heartbeat_interval_seconds": 30,
  "max_concurrent_workloads": 4,
  "workload_sandbox": true,
  "log_level": "INFO",
  "data_dir": "/opt/ag3ntwerk/data",
  "log_dir": "/opt/ag3ntwerk/logs",
  "workload_dir": "/opt/ag3ntwerk/workloads"
}}
AGENT_EOF""",
                ],
                verify_commands=["cat /opt/ag3ntwerk/config/agent.json | python3 -m json.tool"],
                rollback_commands=["sudo rm -f /opt/ag3ntwerk/config/agent.json"],
                estimated_duration_seconds=5,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Deploy agent application code",
                description="Clone or copy the ag3ntwerk fleet agent to the node.",
                risk=StepRisk.LOW,
                commands=[
                    "# Option A: Clone from repository",
                    "# sudo -u ag3ntwerk git clone https://github.com/your-org/ag3ntwerk-agent.git /opt/ag3ntwerk/agent",
                    "",
                    "# Option B: Copy from controller",
                    f"# scp -r controller:/path/to/ag3ntwerk-agent/ user@{target_ip}:/opt/ag3ntwerk/agent/",
                    "",
                    "# Option C: Pull Docker image",
                    "# docker pull your-registry/ag3ntwerk-agent:latest",
                ],
                notes="Choose the deployment method that matches your infrastructure. Update the commands accordingly.",
                estimated_duration_seconds=60,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Create systemd service",
                description="Set up the ag3ntwerk agent as a system service for automatic startup.",
                risk=StepRisk.MEDIUM,
                commands=[
                    """sudo tee /etc/systemd/system/ag3ntwerk-agent.service << 'SERVICE_EOF'
[Unit]
Description=ag3ntwerk Fleet Agent
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=ag3ntwerk
Group=ag3ntwerk
WorkingDirectory=/opt/ag3ntwerk/agent
ExecStart=/opt/ag3ntwerk/venv/bin/uvicorn ag3ntwerk_agent:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10
Environment=AGENTWERK_CONFIG=/opt/ag3ntwerk/config/agent.json
StandardOutput=append:/opt/ag3ntwerk/logs/agent.log
StandardError=append:/opt/ag3ntwerk/logs/agent-error.log

[Install]
WantedBy=multi-user.target
SERVICE_EOF""",
                    "sudo systemctl daemon-reload",
                    "sudo systemctl enable ag3ntwerk-agent",
                    "sudo systemctl start ag3ntwerk-agent",
                ],
                verify_commands=[
                    "sudo systemctl status ag3ntwerk-agent",
                    "curl -s http://localhost:8000/health || echo 'Agent not yet responding'",
                ],
                rollback_commands=[
                    "sudo systemctl stop ag3ntwerk-agent",
                    "sudo systemctl disable ag3ntwerk-agent",
                    "sudo rm -f /etc/systemd/system/ag3ntwerk-agent.service",
                    "sudo systemctl daemon-reload",
                ],
                requires_root=True,
                estimated_duration_seconds=15,
            )
        )

        return phase

    def _build_directory_structure_phase(self) -> DeploymentPhase:
        """Build the directory structure creation phase."""
        phase = DeploymentPhase(
            name="Directory Structure Setup",
            description="Create the standard ag3ntwerk directory layout for data, logs, and workloads.",
        )

        dirs = [
            ("/opt/ag3ntwerk/data", "Working data and databases"),
            ("/opt/ag3ntwerk/data/models", "ML model cache"),
            ("/opt/ag3ntwerk/data/embeddings", "Embedding vectors"),
            ("/opt/ag3ntwerk/logs", "Agent and workload logs"),
            ("/opt/ag3ntwerk/workloads", "Active workload sandboxes"),
            ("/opt/ag3ntwerk/cache", "Temporary cache"),
            ("/opt/ag3ntwerk/config", "Configuration files"),
            ("/opt/ag3ntwerk/backups", "Backup storage"),
        ]

        mkdir_cmds = [f"sudo mkdir -p {d[0]}  # {d[1]}" for d in dirs]
        mkdir_cmds.append("sudo chown -R ag3ntwerk:ag3ntwerk /opt/ag3ntwerk")
        mkdir_cmds.append("sudo chmod -R 755 /opt/ag3ntwerk")

        phase.steps.append(
            DeploymentStep(
                title="Create directory tree",
                description="Create the complete ag3ntwerk directory structure.",
                risk=StepRisk.LOW,
                commands=mkdir_cmds,
                verify_commands=[
                    "ls -la /opt/ag3ntwerk/",
                    "tree /opt/ag3ntwerk/ 2>/dev/null || find /opt/ag3ntwerk -type d | head -20",
                ],
                rollback_commands=["sudo rm -rf /opt/ag3ntwerk"],
                requires_root=True,
                estimated_duration_seconds=5,
            )
        )

        return phase

    def _build_fleet_registration_phase(
        self,
        target_ip: str,
        target_hostname: str,
        role: str,
        controller_url: str,
    ) -> DeploymentPhase:
        """Build the fleet registration phase."""
        phase = DeploymentPhase(
            name="Fleet Registration",
            description="Register this node with the ag3ntwerk fleet controller and verify communication.",
        )

        phase.steps.append(
            DeploymentStep(
                title="Register with fleet controller",
                description="Announce this node to the fleet controller's API.",
                risk=StepRisk.LOW,
                commands=[
                    f"""curl -X POST {controller_url}/api/v1/fleet/enroll \\
  -H 'Content-Type: application/json' \\
  -d '{{
    "device_id": "node-{target_ip.replace('.', '-')}",
    "approved_by": "deployment-plan",
    "role": "{role}",
    "tags": ["auto-deployed"]
  }}'""",
                ],
                verify_commands=[
                    f"curl -s {controller_url}/api/v1/fleet/nodes | python3 -m json.tool",
                ],
                expected_output="success: true",
                estimated_duration_seconds=10,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Verify bidirectional communication",
                description="Confirm the controller can reach this node's agent API.",
                risk=StepRisk.INFO,
                commands=[
                    f"# From the controller, run:",
                    f"# curl -s http://{target_ip}:8000/health",
                    f"# Expected: healthy response",
                    "",
                    f"# From this node, verify controller:",
                    f"curl -s {controller_url}/health",
                ],
                estimated_duration_seconds=10,
            )
        )

        return phase

    def _build_verification_phase(
        self,
        target_ip: str,
        controller_url: str,
    ) -> DeploymentPhase:
        """Build the final verification and health check phase."""
        phase = DeploymentPhase(
            name="Verification & Health Check",
            description="Run comprehensive checks to verify the node is fully operational.",
        )

        phase.steps.append(
            DeploymentStep(
                title="Verify agent health endpoint",
                description="Check that the ag3ntwerk agent is responding to health checks.",
                risk=StepRisk.INFO,
                commands=[f"curl -s http://{target_ip}:8000/health"],
                expected_output='{"status": "healthy"}',
                estimated_duration_seconds=5,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Verify resource reporting",
                description="Check that the agent is correctly reporting its resources.",
                risk=StepRisk.INFO,
                commands=[
                    f"curl -s http://{target_ip}:8000/api/v1/node/resources | python3 -m json.tool"
                ],
                estimated_duration_seconds=5,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Run a test workload",
                description="Submit a lightweight test workload to verify end-to-end execution.",
                risk=StepRisk.LOW,
                commands=[
                    f"""curl -X POST {controller_url}/api/v1/fleet/workloads \\
  -H 'Content-Type: application/json' \\
  -d '{{
    "name": "deployment-verification-test",
    "owner_executive": "Forge",
    "task_type": "health_check",
    "priority": "normal",
    "min_cpu_cores": 1,
    "min_memory_gb": 0.25
  }}'""",
                ],
                notes="Check the controller's workload dashboard to confirm allocation to this node.",
                estimated_duration_seconds=15,
            )
        )

        phase.steps.append(
            DeploymentStep(
                title="Final checklist",
                description="Manual verification checklist for the operator.",
                risk=StepRisk.INFO,
                commands=[
                    "echo '--- DEPLOYMENT VERIFICATION CHECKLIST ---'",
                    "echo '[ ] Agent service is running (systemctl status ag3ntwerk-agent)'",
                    "echo '[ ] Agent API responds on port 8000'",
                    "echo '[ ] Node appears in fleet dashboard'",
                    "echo '[ ] Resource profile shows correct hardware'",
                    "echo '[ ] Test workload was allocated and executed'",
                    "echo '[ ] Firewall allows required ports'",
                    "echo '[ ] Logs are being written to /opt/ag3ntwerk/logs/'",
                    "echo '[ ] Directory permissions are correct (ag3ntwerk user)'",
                    "echo '--- END CHECKLIST ---'",
                ],
                estimated_duration_seconds=60,
            )
        )

        return phase

    # ====================================================================
    # Plan Management
    # ====================================================================

    def approve_phase(self, plan_id: str, phase_id: str, approved_by: str) -> Dict[str, Any]:
        """Approve a specific phase for execution."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found"}

        phase = next((p for p in plan.phases if p.id == phase_id), None)
        if not phase:
            return {"success": False, "error": "Phase not found"}

        if phase.status not in (PhaseStatus.AWAITING_APPROVAL, PhaseStatus.PENDING):
            return {"success": False, "error": f"Phase is {phase.status.value}, cannot approve"}

        phase.status = PhaseStatus.APPROVED
        phase.approved_by = approved_by
        phase.approved_at = datetime.now(timezone.utc)
        plan.last_modified_at = datetime.now(timezone.utc)

        # Update plan status
        if all(
            p.status in (PhaseStatus.APPROVED, PhaseStatus.SKIPPED, PhaseStatus.COMPLETED)
            for p in plan.phases
        ):
            plan.status = PlanStatus.FULLY_APPROVED
            plan.fully_approved_at = datetime.now(timezone.utc)
        elif any(p.status == PhaseStatus.APPROVED for p in plan.phases):
            plan.status = PlanStatus.PARTIALLY_APPROVED

        logger.info(f"Phase '{phase.name}' approved by {approved_by}")
        return {
            "success": True,
            "phase": phase.name,
            "approved_by": approved_by,
            "plan_status": plan.status.value,
        }

    def skip_phase(self, plan_id: str, phase_id: str, reason: str = "") -> Dict[str, Any]:
        """Skip a phase that is not applicable."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found"}

        phase = next((p for p in plan.phases if p.id == phase_id), None)
        if not phase:
            return {"success": False, "error": "Phase not found"}

        phase.status = PhaseStatus.SKIPPED
        phase.skipped_reason = reason
        plan.last_modified_at = datetime.now(timezone.utc)

        if all(
            p.status in (PhaseStatus.APPROVED, PhaseStatus.SKIPPED, PhaseStatus.COMPLETED)
            for p in plan.phases
        ):
            plan.status = PlanStatus.FULLY_APPROVED
            plan.fully_approved_at = datetime.now(timezone.utc)

        return {"success": True, "phase": phase.name, "skipped": True, "reason": reason}

    async def execute_phase(self, plan_id: str, phase_id: str) -> Dict[str, Any]:
        """
        Execute an approved phase.

        The phase must be approved first. Steps are executed in order
        on the target node via SSH or the agent API.
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found"}

        phase = next((p for p in plan.phases if p.id == phase_id), None)
        if not phase:
            return {"success": False, "error": "Phase not found"}

        if phase.status != PhaseStatus.APPROVED:
            return {
                "success": False,
                "error": f"Phase must be approved before execution. Current status: {phase.status.value}",
            }

        # Check that all prior phases are complete or skipped
        for prior in plan.phases:
            if prior.order >= phase.order:
                break
            if prior.status not in (PhaseStatus.COMPLETED, PhaseStatus.SKIPPED):
                return {
                    "success": False,
                    "error": f"Prior phase '{prior.name}' must be completed or skipped first (status: {prior.status.value})",
                }

        phase.status = PhaseStatus.EXECUTING
        phase.started_at = datetime.now(timezone.utc)
        plan.status = PlanStatus.EXECUTING

        if not plan.execution_started_at:
            plan.execution_started_at = datetime.now(timezone.utc)

        step_results = []
        all_ok = True

        for step in phase.steps:
            try:
                result = await self._execute_step(plan.target_ip, step)
                step_results.append(
                    {
                        "step": step.title,
                        "success": not bool(step.execution_error),
                        "output": step.execution_output[:500] if step.execution_output else "",
                        "error": step.execution_error,
                    }
                )
                if step.execution_error:
                    all_ok = False
                    logger.warning(f"Step '{step.title}' had errors: {step.execution_error}")
            except Exception as e:
                step.execution_error = str(e)
                step.executed = True
                step.executed_at = datetime.now(timezone.utc)
                step_results.append(
                    {
                        "step": step.title,
                        "success": False,
                        "error": str(e),
                    }
                )
                all_ok = False
                logger.error(f"Step '{step.title}' failed: {e}")

        if all_ok:
            phase.status = PhaseStatus.COMPLETED
        else:
            phase.status = PhaseStatus.FAILED
            phase.error = "One or more steps had errors. Review step results."

        phase.completed_at = datetime.now(timezone.utc)

        # Check if all phases are done
        if all(p.status in (PhaseStatus.COMPLETED, PhaseStatus.SKIPPED) for p in plan.phases):
            plan.status = PlanStatus.COMPLETED
            plan.execution_completed_at = datetime.now(timezone.utc)

        return {
            "success": all_ok,
            "phase": phase.name,
            "steps_executed": len(step_results),
            "steps": step_results,
        }

    async def _execute_step(self, target_ip: str, step: DeploymentStep) -> Dict[str, Any]:
        """Execute a single step on the target node."""
        step.executed = True
        step.executed_at = datetime.now(timezone.utc)

        if not step.commands:
            step.execution_output = "No commands to execute"
            return {"success": True}

        # Filter out comment-only commands
        real_commands = [
            cmd for cmd in step.commands if cmd.strip() and not cmd.strip().startswith("#")
        ]

        if not real_commands:
            step.execution_output = "All commands were comments/instructions only"
            return {"success": True}

        # Execute via the agent API on the target
        combined_output = []
        combined_errors = []

        for cmd in real_commands:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(target_ip, 8000),
                    timeout=10.0,
                )
                import json

                payload = json.dumps({"command": cmd, "timeout": 120})
                request = (
                    f"POST /api/v1/node/execute HTTP/1.1\r\n"
                    f"Host: {target_ip}:8000\r\n"
                    f"Content-Type: application/json\r\n"
                    f"Content-Length: {len(payload)}\r\n"
                    f"Connection: close\r\n\r\n"
                    f"{payload}"
                )
                writer.write(request.encode())
                await writer.drain()

                response = await asyncio.wait_for(reader.read(65536), timeout=130.0)
                writer.close()
                await writer.wait_closed()

                resp_text = response.decode("utf-8", errors="ignore")
                body_start = resp_text.find("\r\n\r\n")
                if body_start > 0:
                    body = resp_text[body_start + 4 :]
                    try:
                        result = json.loads(body)
                        combined_output.append(result.get("output", ""))
                        if result.get("error"):
                            combined_errors.append(result["error"])
                    except json.JSONDecodeError:
                        combined_output.append(body[:200])
                else:
                    combined_output.append("(no response body)")

            except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                combined_errors.append(f"Command '{cmd[:50]}' connection failed: {e}")

        step.execution_output = "\n".join(combined_output)
        step.execution_error = "\n".join(combined_errors) if combined_errors else ""

        return {
            "success": not combined_errors,
            "output": step.execution_output,
            "errors": step.execution_error,
        }

    def cancel_plan(self, plan_id: str, reason: str = "") -> Dict[str, Any]:
        """Cancel a deployment plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found"}

        plan.status = PlanStatus.CANCELLED
        plan.last_modified_at = datetime.now(timezone.utc)
        plan.metadata["cancellation_reason"] = reason

        for phase in plan.phases:
            if phase.status in (
                PhaseStatus.AWAITING_APPROVAL,
                PhaseStatus.APPROVED,
                PhaseStatus.PENDING,
            ):
                phase.status = PhaseStatus.SKIPPED
                phase.skipped_reason = f"Plan cancelled: {reason}"

        return {"success": True, "plan_id": plan_id, "status": "cancelled"}

    # ====================================================================
    # Query Methods
    # ====================================================================

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get a deployment plan."""
        plan = self._plans.get(plan_id)
        return plan.to_dict() if plan else None

    def get_plan_guide(self, plan_id: str) -> Optional[str]:
        """Get the human-readable deployment guide text."""
        plan = self._plans.get(plan_id)
        return plan.to_guide_text() if plan else None

    def list_plans(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all deployment plans."""
        plans = list(self._plans.values())
        if status:
            plans = [p for p in plans if p.status.value == status]
        return [
            {
                "id": p.id,
                "name": p.name,
                "target_ip": p.target_ip,
                "status": p.status.value,
                "phases": len(p.phases),
                "phases_approved": p.phases_approved,
                "total_steps": p.total_steps,
                "completed_steps": p.completed_steps,
                "created_at": p.created_at.isoformat(),
            }
            for p in plans
        ]
