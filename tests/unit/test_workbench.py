"""
Unit tests for the Workbench module.

Tests workspace management, command execution, and service functionality
using the FakeRunner to avoid Docker dependencies.
"""

import asyncio
import pytest
from pathlib import Path
from datetime import datetime

from ag3ntwerk.modules.workbench.schemas import (
    Workspace,
    WorkspaceCreate,
    WorkspaceStatus,
    RuntimeType,
    WorkspaceTemplate,
    RunRequest,
    RunResult,
    RunStatus,
    PortExposeRequest,
    PortProtocol,
    FileWriteRequest,
    FileReadRequest,
)
from ag3ntwerk.modules.workbench.settings import (
    WorkbenchSettings,
    configure_workbench_settings,
)
from ag3ntwerk.modules.workbench.service import WorkbenchService
from ag3ntwerk.modules.workbench.runner.fake_runner import FakeRunner
from ag3ntwerk.modules.workbench.utils.paths import (
    ensure_workspace_dir,
    init_workspace_from_template,
    clean_workspace,
)
from ag3ntwerk.modules.workbench.utils.ports import (
    PortAllocator,
    is_port_in_use,
    find_free_port,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_workspace_dir(tmp_path):
    """Create a temporary directory for workspaces."""
    workspace_dir = tmp_path / "workspaces"
    workspace_dir.mkdir()
    return workspace_dir


@pytest.fixture
def workbench_settings(temp_workspace_dir):
    """Create workbench settings for testing."""
    settings = WorkbenchSettings()
    settings.root_dir = str(temp_workspace_dir)
    settings.runner_type = "fake"
    settings.security.auth_token = None  # Disable auth for tests
    configure_workbench_settings(settings)
    return settings


@pytest.fixture
def fake_runner(workbench_settings):
    """Create a fake runner for testing."""
    return FakeRunner(workbench_settings)


@pytest.fixture
async def workbench_service(workbench_settings):
    """Create and initialize a workbench service."""
    service = WorkbenchService(workbench_settings)
    await service.initialize()
    yield service
    await service.shutdown()


@pytest.fixture
def sample_workspace_create():
    """Sample workspace creation request."""
    return WorkspaceCreate(
        name="test-project",
        template=WorkspaceTemplate.PYTHON_BASIC,
        runtime=RuntimeType.PYTHON,
    )


# =============================================================================
# Schema Tests
# =============================================================================


class TestSchemas:
    """Tests for Pydantic schemas."""

    def test_workspace_create_valid(self):
        """Test valid workspace creation."""
        ws = WorkspaceCreate(
            name="my-project",
            runtime=RuntimeType.PYTHON,
        )
        assert ws.name == "my-project"
        assert ws.runtime == RuntimeType.PYTHON
        assert ws.template == WorkspaceTemplate.EMPTY

    def test_workspace_create_name_validation(self):
        """Test workspace name validation."""
        # Valid names
        for name in ["project", "my-project", "project_1", "Project123"]:
            ws = WorkspaceCreate(name=name)
            assert ws.name == name.lower()

        # Invalid names
        with pytest.raises(ValueError):
            WorkspaceCreate(name="-invalid")

        with pytest.raises(ValueError):
            WorkspaceCreate(name="has spaces")

        with pytest.raises(ValueError):
            WorkspaceCreate(name="has.dots")

    def test_run_request_valid(self):
        """Test valid run request."""
        req = RunRequest(
            workspace_id="abc123",
            cmd=["python", "-c", "print('hello')"],
        )
        assert req.cmd == ["python", "-c", "print('hello')"]
        assert req.timeout == 300

    def test_run_request_dangerous_command(self):
        """Test that dangerous commands are rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="[Dd]angerous"):
            RunRequest(
                workspace_id="abc123",
                cmd=["rm", "-rf", "/"],
            )

    def test_workspace_to_dict(self):
        """Test workspace serialization."""
        ws = Workspace(
            id="test-id",
            name="test",
            path="/path/to/workspace",
            runtime=RuntimeType.PYTHON,
            status=WorkspaceStatus.RUNNING,
        )
        data = ws.to_dict()
        assert data["id"] == "test-id"
        assert data["name"] == "test"
        assert data["runtime"] == "python"
        assert data["status"] == "running"

    def test_run_result_to_dict(self):
        """Test run result serialization."""
        result = RunResult(
            run_id="run-123",
            workspace_id="ws-456",
            cmd=["python", "--version"],
            status=RunStatus.COMPLETED,
            exit_code=0,
            stdout="Python 3.11.0\n",
        )
        data = result.to_dict()
        assert data["run_id"] == "run-123"
        assert data["status"] == "completed"
        assert data["exit_code"] == 0


# =============================================================================
# Settings Tests
# =============================================================================


class TestSettings:
    """Tests for workbench settings."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = WorkbenchSettings()
        assert settings.enabled is True
        assert settings.runner_type == "docker"
        assert settings.security.localhost_only is True

    def test_settings_validation(self):
        """Test settings validation."""
        settings = WorkbenchSettings()
        errors = settings.validate()
        assert errors == []  # Default settings should be valid

        # Invalid port range
        settings.preview_port_start = 9000
        settings.preview_port_end = 8000
        errors = settings.validate()
        assert len(errors) > 0

    def test_workspace_path_generation(self, temp_workspace_dir):
        """Test workspace path generation."""
        settings = WorkbenchSettings()
        settings.root_dir = str(temp_workspace_dir)

        path = settings.get_workspace_path("test-123")
        assert "test-123" in str(path)

    def test_preview_url_generation(self):
        """Test preview URL generation."""
        settings = WorkbenchSettings()
        url = settings.get_preview_url("ws-123", 8080, 8100)
        assert "localhost" in url
        assert "8100" in url
        assert "ws-123" in url


# =============================================================================
# FakeRunner Tests
# =============================================================================


class TestFakeRunner:
    """Tests for the fake runner."""

    @pytest.mark.asyncio
    async def test_runner_initialize(self, fake_runner):
        """Test runner initialization."""
        await fake_runner.initialize()
        assert fake_runner._initialized is True

    @pytest.mark.asyncio
    async def test_runner_capabilities(self, fake_runner):
        """Test runner capabilities."""
        caps = fake_runner.get_capabilities()
        assert caps.supports_docker is False
        assert caps.supports_port_mapping is True
        assert RuntimeType.PYTHON in caps.supported_runtimes

    @pytest.mark.asyncio
    async def test_create_and_start_workspace(self, fake_runner, temp_workspace_dir):
        """Test creating and starting a workspace."""
        await fake_runner.initialize()

        workspace = Workspace(
            id="test-123",
            name="test",
            path=str(temp_workspace_dir / "test-123"),
            runtime=RuntimeType.PYTHON,
        )

        await fake_runner.create_workspace_container(workspace)
        assert workspace.id in fake_runner._workspaces

        await fake_runner.start(workspace.id)
        status = await fake_runner.get_container_status(workspace.id)
        assert status["running"] is True

    @pytest.mark.asyncio
    async def test_exec_command(self, fake_runner, temp_workspace_dir):
        """Test executing a command."""
        await fake_runner.initialize()

        workspace = Workspace(
            id="test-exec",
            name="test",
            path=str(temp_workspace_dir / "test-exec"),
            runtime=RuntimeType.PYTHON,
        )

        await fake_runner.create_workspace_container(workspace)
        await fake_runner.start(workspace.id)

        # Execute predefined command
        result = await fake_runner.exec_sync(
            workspace.id,
            ["python", "-c", "print('ok')"],
        )

        assert result.status == RunStatus.COMPLETED
        assert result.exit_code == 0
        assert "ok" in result.stdout

    @pytest.mark.asyncio
    async def test_exec_async(self, fake_runner, temp_workspace_dir):
        """Test asynchronous execution."""
        await fake_runner.initialize()

        workspace = Workspace(
            id="test-async",
            name="test",
            path=str(temp_workspace_dir / "test-async"),
            runtime=RuntimeType.PYTHON,
        )

        await fake_runner.create_workspace_container(workspace)
        await fake_runner.start(workspace.id)

        # Execute async
        run_id = await fake_runner.exec(
            workspace.id,
            ["echo", "hello"],
        )

        assert run_id is not None

        # Wait a bit for execution
        await asyncio.sleep(0.2)

        result = await fake_runner.get_run_result(run_id)
        assert result is not None
        assert result.status in (RunStatus.COMPLETED, RunStatus.FAILED)

    @pytest.mark.asyncio
    async def test_expose_port(self, fake_runner, temp_workspace_dir):
        """Test port exposure."""
        await fake_runner.initialize()

        workspace = Workspace(
            id="test-port",
            name="test",
            path=str(temp_workspace_dir / "test-port"),
            runtime=RuntimeType.PYTHON,
        )

        await fake_runner.create_workspace_container(workspace)

        result = await fake_runner.expose_port(workspace.id, 8080)
        assert result.port == 8080
        assert result.host_port > 0
        assert "localhost" in result.preview_url

    @pytest.mark.asyncio
    async def test_runner_stats(self, fake_runner, temp_workspace_dir):
        """Test runner statistics."""
        await fake_runner.initialize()

        # Create a workspace
        workspace = Workspace(
            id="test-stats",
            name="test",
            path=str(temp_workspace_dir / "test-stats"),
            runtime=RuntimeType.PYTHON,
        )

        await fake_runner.create_workspace_container(workspace)
        await fake_runner.start(workspace.id)

        stats = await fake_runner.get_stats()
        assert stats["total_containers"] == 1
        assert stats["running_containers"] == 1


# =============================================================================
# Path Utilities Tests
# =============================================================================


class TestPathUtilities:
    """Tests for path utilities."""

    def test_ensure_workspace_dir(self, workbench_settings, temp_workspace_dir):
        """Test workspace directory creation."""
        path = ensure_workspace_dir("new-workspace")
        assert path.exists()
        assert path.is_dir()

    def test_init_python_workspace(self, workbench_settings, temp_workspace_dir):
        """Test Python workspace initialization."""
        path = init_workspace_from_template(
            "python-ws",
            WorkspaceTemplate.PYTHON_BASIC,
            RuntimeType.PYTHON,
        )

        assert (path / "main.py").exists()
        assert (path / "requirements.txt").exists()
        assert (path / ".gitignore").exists()

    def test_init_node_workspace(self, workbench_settings, temp_workspace_dir):
        """Test Node.js workspace initialization."""
        path = init_workspace_from_template(
            "node-ws",
            WorkspaceTemplate.NODE_BASIC,
            RuntimeType.NODE,
        )

        assert (path / "package.json").exists()
        assert (path / "index.js").exists()

    def test_clean_workspace(self, workbench_settings, temp_workspace_dir):
        """Test workspace cleanup."""
        path = ensure_workspace_dir("to-clean")
        (path / "file.txt").write_text("content")

        success = clean_workspace("to-clean")
        assert success is True
        assert not path.exists()


# =============================================================================
# Port Utilities Tests
# =============================================================================


class TestPortUtilities:
    """Tests for port utilities."""

    def test_port_allocator_basic(self):
        """Test basic port allocation."""
        allocator = PortAllocator(start_port=10000, end_port=10010)

        port1 = allocator.allocate("ws1")
        assert port1 is not None
        assert allocator.is_allocated(port1)

        port2 = allocator.allocate("ws2")
        assert port2 is not None
        assert port1 != port2

    def test_port_allocator_release(self):
        """Test port release."""
        allocator = PortAllocator(start_port=10000, end_port=10010)

        port = allocator.allocate("ws1")
        assert allocator.release("ws1", port) is True
        assert not allocator.is_allocated(port)

    def test_port_allocator_release_all(self):
        """Test releasing all ports for a workspace."""
        allocator = PortAllocator(start_port=10000, end_port=10010)

        allocator.allocate("ws1")
        allocator.allocate("ws1")

        count = allocator.release_all("ws1")
        assert count == 2

    def test_port_allocator_stats(self):
        """Test allocator statistics."""
        allocator = PortAllocator(start_port=10000, end_port=10010)
        allocator.allocate("ws1")

        stats = allocator.get_stats()
        assert stats["allocated_ports"] == 1
        assert stats["available_ports"] == 9


# =============================================================================
# WorkbenchService Tests
# =============================================================================


class TestWorkbenchService:
    """Tests for the WorkbenchService."""

    @pytest.mark.asyncio
    async def test_service_initialize(self, workbench_service):
        """Test service initialization."""
        assert workbench_service._initialized is True

    @pytest.mark.asyncio
    async def test_create_workspace(self, workbench_service, sample_workspace_create):
        """Test workspace creation."""
        workspace = await workbench_service.create_workspace(sample_workspace_create)

        assert workspace.id is not None
        assert workspace.name == sample_workspace_create.name
        assert workspace.runtime == RuntimeType.PYTHON
        assert workspace.status == WorkspaceStatus.STOPPED

    @pytest.mark.asyncio
    async def test_list_workspaces(self, workbench_service, sample_workspace_create):
        """Test listing workspaces."""
        # Create a workspace
        await workbench_service.create_workspace(sample_workspace_create)

        workspaces = await workbench_service.list_workspaces()
        assert len(workspaces) >= 1

    @pytest.mark.asyncio
    async def test_start_stop_workspace(self, workbench_service, sample_workspace_create):
        """Test starting and stopping a workspace."""
        workspace = await workbench_service.create_workspace(sample_workspace_create)

        # Start
        started = await workbench_service.start_workspace(workspace.id)
        assert started.status == WorkspaceStatus.RUNNING

        # Stop
        stopped = await workbench_service.stop_workspace(workspace.id)
        assert stopped.status == WorkspaceStatus.STOPPED

    @pytest.mark.asyncio
    async def test_run_command(self, workbench_service, sample_workspace_create):
        """Test running a command in a workspace."""
        workspace = await workbench_service.create_workspace(sample_workspace_create)
        await workbench_service.start_workspace(workspace.id)

        request = RunRequest(
            workspace_id=workspace.id,
            cmd=["python", "-c", "print('ok')"],
        )

        result = await workbench_service.run_command_sync(request)
        assert result.status == RunStatus.COMPLETED
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_write_and_read_files(self, workbench_service, sample_workspace_create):
        """Test writing and reading files."""
        workspace = await workbench_service.create_workspace(sample_workspace_create)

        # Write files
        write_request = FileWriteRequest(
            workspace_id=workspace.id,
            files={
                "test.txt": "Hello World",
                "data/config.json": '{"key": "value"}',
            },
        )
        results = await workbench_service.write_files(write_request)
        assert results["test.txt"] is True

        # Read files
        read_request = FileReadRequest(
            workspace_id=workspace.id,
            paths=["test.txt"],
        )
        contents = await workbench_service.read_files(read_request)
        assert len(contents) == 1
        assert contents[0].content == "Hello World"

    @pytest.mark.asyncio
    async def test_list_files(self, workbench_service, sample_workspace_create):
        """Test listing files in a workspace."""
        workspace = await workbench_service.create_workspace(sample_workspace_create)

        files = await workbench_service.list_files(workspace.id)
        assert len(files) > 0  # Template files should exist

    @pytest.mark.asyncio
    async def test_delete_workspace(self, workbench_service, sample_workspace_create):
        """Test deleting a workspace."""
        workspace = await workbench_service.create_workspace(sample_workspace_create)

        success = await workbench_service.delete_workspace(workspace.id)
        assert success is True

        # Should not find it anymore
        result = await workbench_service.get_workspace(workspace.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_stats(self, workbench_service, sample_workspace_create):
        """Test getting service statistics."""
        await workbench_service.create_workspace(sample_workspace_create)

        stats = workbench_service.get_stats()
        assert stats.total_workspaces >= 1

    @pytest.mark.asyncio
    async def test_executive_report(self, workbench_service, sample_workspace_create):
        """Test agent report generation."""
        await workbench_service.create_workspace(sample_workspace_create)

        # Forge report
        report = workbench_service.get_agent_report("Forge")
        assert report["agent"] == "Forge"
        assert "overview" in report

        # Foundry report
        report = workbench_service.get_agent_report("Foundry")
        assert report["agent"] == "Foundry"

        # Default report
        report = workbench_service.get_agent_report("Keystone")
        assert report["agent"] == "Keystone"


# =============================================================================
# Security Tests
# =============================================================================


class TestSecurity:
    """Tests for security features."""

    def test_validate_workspace_name(self):
        """Test workspace name validation."""
        from ag3ntwerk.modules.workbench.security import validate_workspace_name

        assert validate_workspace_name("valid-name") is True
        assert validate_workspace_name("valid_name123") is True
        assert validate_workspace_name("-invalid") is False
        assert validate_workspace_name("../traversal") is False
        assert validate_workspace_name("con") is False  # Reserved name

    def test_sanitize_file_path(self):
        """Test file path sanitization."""
        import os
        import sys
        from ag3ntwerk.modules.workbench.security import sanitize_file_path

        assert sanitize_file_path("file.txt") == "file.txt"
        # On Windows, path separators are normalized to backslash
        expected_sep = os.sep
        assert sanitize_file_path("dir/file.txt") == f"dir{expected_sep}file.txt"

        with pytest.raises(ValueError):
            sanitize_file_path("../parent/file.txt")

        # On Windows, "/path" is not absolute (it's relative to current drive)
        # Use a platform-appropriate absolute path for testing
        if sys.platform == "win32":
            with pytest.raises(ValueError):
                sanitize_file_path("C:\\absolute\\path.txt")
        else:
            with pytest.raises(ValueError):
                sanitize_file_path("/absolute/path.txt")

    def test_sanitize_command(self):
        """Test command sanitization."""
        from ag3ntwerk.modules.workbench.security import sanitize_command

        # Valid commands pass through
        assert sanitize_command(["python", "main.py"]) == ["python", "main.py"]

        # Dangerous commands raise errors
        with pytest.raises(ValueError):
            sanitize_command(["rm", "-rf", "/"])

    def test_check_environment_vars(self):
        """Test environment variable checking."""
        from ag3ntwerk.modules.workbench.security import check_environment_vars

        env = {
            "MYVAR": "value",
            "PATH": "/dangerous",  # Should be filtered
            "NORMAL": "ok",
        }

        sanitized = check_environment_vars(env)
        assert "MYVAR" in sanitized
        assert "PATH" not in sanitized
        assert "NORMAL" in sanitized
