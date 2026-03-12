"""
Workbench Fake Runner - In-memory runner for testing.

Implements the BaseRunner interface without requiring Docker,
useful for unit tests and development without Docker.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.modules.workbench.runner.base import BaseRunner, RunnerCapabilities
from ag3ntwerk.modules.workbench.schemas import (
    Workspace,
    RunResult,
    RunStatus,
    PortExposeResult,
    PortProtocol,
    RuntimeType,
)
from ag3ntwerk.modules.workbench.settings import WorkbenchSettings, get_workbench_settings

logger = logging.getLogger(__name__)


class FakeRunner(BaseRunner):
    """
    Fake runner for testing without Docker.

    Simulates container behavior in-memory. Command execution
    returns predefined responses or runs simple Python commands.
    """

    def __init__(self, settings: Optional[WorkbenchSettings] = None):
        """
        Initialize the fake runner.

        Args:
            settings: Workbench settings. Uses global settings if not provided.
        """
        self._settings = settings or get_workbench_settings()
        self._initialized = False

        # Simulated workspace state
        self._workspaces: Dict[str, Dict[str, Any]] = {}  # workspace_id -> state

        # Track runs
        self._runs: Dict[str, RunResult] = {}

        # Track exposed ports
        self._exposed_ports: Dict[str, List[PortExposeResult]] = {}

        # Port allocation
        self._next_port = self._settings.preview_port_start

        # Stats
        self._total_runs = 0

        # Predefined command responses for testing
        self._command_responses: Dict[str, tuple] = {
            # cmd_key -> (exit_code, stdout, stderr)
            "python,-c,print('ok')": (0, "ok\n", ""),
            "python,--version": (0, "Python 3.11.0\n", ""),
            "node,--version": (0, "v20.0.0\n", ""),
            "echo,hello": (0, "hello\n", ""),
            "ls": (0, "file1.txt\nfile2.py\n", ""),
            "pwd": (0, "/workspace\n", ""),
        }

    def set_command_response(
        self,
        cmd: List[str],
        exit_code: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        """Set a predefined response for a command (for testing)."""
        key = ",".join(cmd)
        self._command_responses[key] = (exit_code, stdout, stderr)

    async def initialize(self) -> None:
        """Initialize the fake runner."""
        self._initialized = True
        logger.info("FakeRunner initialized")

    async def shutdown(self) -> None:
        """Shutdown the fake runner."""
        self._workspaces.clear()
        self._runs.clear()
        self._initialized = False
        logger.info("FakeRunner shutdown")

    def get_capabilities(self) -> RunnerCapabilities:
        """Get fake runner capabilities."""
        return RunnerCapabilities(
            supports_docker=False,
            supports_port_mapping=True,
            supports_resource_limits=False,
            supports_network_isolation=False,
            max_concurrent_workspaces=100,
            supported_runtimes=list(RuntimeType),
        )

    async def create_workspace_container(
        self,
        workspace: Workspace,
    ) -> None:
        """Create a fake container for a workspace."""
        self._workspaces[workspace.id] = {
            "workspace": workspace,
            "status": "created",
            "created_at": datetime.now(timezone.utc),
        }
        logger.info(f"FakeRunner: Created container for workspace {workspace.id}")

    async def start(self, workspace_id: str) -> None:
        """Start a workspace's fake container."""
        if workspace_id not in self._workspaces:
            raise ValueError(f"No container found for workspace: {workspace_id}")

        self._workspaces[workspace_id]["status"] = "running"
        self._workspaces[workspace_id]["started_at"] = datetime.now(timezone.utc)
        logger.info(f"FakeRunner: Started workspace {workspace_id}")

    async def stop(self, workspace_id: str) -> None:
        """Stop a workspace's fake container."""
        if workspace_id not in self._workspaces:
            raise ValueError(f"No container found for workspace: {workspace_id}")

        self._workspaces[workspace_id]["status"] = "stopped"
        logger.info(f"FakeRunner: Stopped workspace {workspace_id}")

    async def remove(self, workspace_id: str) -> None:
        """Remove a workspace's fake container."""
        self._workspaces.pop(workspace_id, None)
        self._exposed_ports.pop(workspace_id, None)
        logger.info(f"FakeRunner: Removed workspace {workspace_id}")

    async def exec(
        self,
        workspace_id: str,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """Execute a command asynchronously."""
        run_id = str(uuid.uuid4())

        run_result = RunResult(
            run_id=run_id,
            workspace_id=workspace_id,
            cmd=cmd,
            status=RunStatus.PENDING,
            started_at=datetime.now(timezone.utc),
        )
        self._runs[run_id] = run_result
        self._total_runs += 1

        # Execute in background
        asyncio.create_task(self._execute_fake(run_id, workspace_id, cmd, env, cwd, timeout))

        return run_id

    async def _execute_fake(
        self,
        run_id: str,
        workspace_id: str,
        cmd: List[str],
        env: Optional[Dict[str, str]],
        cwd: Optional[str],
        timeout: Optional[int],
    ) -> None:
        """Execute command and update result."""
        run_result = self._runs[run_id]
        run_result.status = RunStatus.RUNNING

        # Simulate some execution time
        await asyncio.sleep(0.1)

        result = await self.exec_sync(workspace_id, cmd, env, cwd, timeout)

        run_result.status = result.status
        run_result.exit_code = result.exit_code
        run_result.stdout = result.stdout
        run_result.stderr = result.stderr
        run_result.ended_at = result.ended_at
        run_result.duration_seconds = result.duration_seconds

    async def exec_sync(
        self,
        workspace_id: str,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> RunResult:
        """Execute a command synchronously."""
        if workspace_id not in self._workspaces:
            raise ValueError(f"No container found for workspace: {workspace_id}")

        workspace_state = self._workspaces[workspace_id]
        if workspace_state["status"] != "running":
            raise RuntimeError(f"Container is not running: {workspace_state['status']}")

        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        # Look up predefined response
        cmd_key = ",".join(cmd)
        if cmd_key in self._command_responses:
            exit_code, stdout, stderr = self._command_responses[cmd_key]
        else:
            # Default: simulate successful empty command
            exit_code = 0
            stdout = ""
            stderr = ""

        ended_at = datetime.now(timezone.utc)

        return RunResult(
            run_id=run_id,
            workspace_id=workspace_id,
            cmd=cmd,
            status=RunStatus.COMPLETED if exit_code == 0 else RunStatus.FAILED,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=(ended_at - started_at).total_seconds(),
        )

    async def get_run_result(self, run_id: str) -> Optional[RunResult]:
        """Get the result of a command execution."""
        return self._runs.get(run_id)

    async def get_logs(
        self,
        run_id: str,
        stdout: bool = True,
        stderr: bool = True,
    ) -> str:
        """Get logs from a command execution."""
        run_result = self._runs.get(run_id)
        if not run_result:
            raise ValueError(f"Run not found: {run_id}")

        logs = []
        if stdout and run_result.stdout:
            logs.append(run_result.stdout)
        if stderr and run_result.stderr:
            logs.append(run_result.stderr)

        return "\n".join(logs)

    async def expose_port(
        self,
        workspace_id: str,
        port: int,
        proto: str = "http",
        label: Optional[str] = None,
    ) -> PortExposeResult:
        """Expose a port from a workspace."""
        if workspace_id not in self._workspaces:
            raise ValueError(f"No container found for workspace: {workspace_id}")

        host_port = self._next_port
        self._next_port += 1

        result = PortExposeResult(
            workspace_id=workspace_id,
            port=port,
            host_port=host_port,
            proto=PortProtocol(proto),
            preview_url=self._settings.get_preview_url(workspace_id, port, host_port),
            label=label,
        )

        if workspace_id not in self._exposed_ports:
            self._exposed_ports[workspace_id] = []
        self._exposed_ports[workspace_id].append(result)

        return result

    async def list_exposed_ports(
        self,
        workspace_id: str,
    ) -> List[PortExposeResult]:
        """List all exposed ports for a workspace."""
        return self._exposed_ports.get(workspace_id, [])

    async def get_container_status(
        self,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Get status of a fake container."""
        if workspace_id not in self._workspaces:
            return {
                "running": False,
                "state": "not_found",
            }

        state = self._workspaces[workspace_id]
        return {
            "running": state["status"] == "running",
            "state": state["status"],
            "started_at": (
                state.get("started_at", "").isoformat() if state.get("started_at") else None
            ),
            "cpu_usage": 1.5,  # Fake values
            "memory_usage": "128MB",
        }

    async def is_healthy(self) -> bool:
        """Check if fake runner is healthy."""
        return self._initialized

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the fake runner."""
        running_count = sum(1 for ws in self._workspaces.values() if ws["status"] == "running")

        return {
            "total_containers": len(self._workspaces),
            "running_containers": running_count,
            "total_runs": self._total_runs,
            "active_runs": sum(1 for r in self._runs.values() if r.status == RunStatus.RUNNING),
            "exposed_ports": sum(len(ports) for ports in self._exposed_ports.values()),
            "images_available": ["python", "node", "go", "rust"],
            "network": "fake_network",
        }
