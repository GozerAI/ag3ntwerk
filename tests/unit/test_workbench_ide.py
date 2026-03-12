"""
Unit tests for the Workbench IDE and One-Click Deploy features.

Tests browser IDE management, framework detection, config generation,
and one-click deployment functionality.
"""

import pytest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.modules.workbench.schemas import (
    Workspace,
    WorkspaceStatus,
    RuntimeType,
    IDEMode,
    IDEInfo,
)
from ag3ntwerk.modules.workbench.settings import (
    WorkbenchSettings,
    configure_workbench_settings,
)
from ag3ntwerk.modules.workbench.ide.manager import IDEContainerManager, IDEStatus
from ag3ntwerk.modules.workbench.detection.framework_detector import (
    FrameworkDetector,
    FrameworkInfo,
    FrameworkType,
)
from ag3ntwerk.modules.workbench.detection.config_generator import (
    ConfigGenerator,
    GeneratedConfigs,
)
from ag3ntwerk.modules.workbench.deployers.oneclick import (
    OneClickDeployer,
    OneClickResult,
    DeployPreview,
)
from ag3ntwerk.modules.workbench.pipeline_schemas import DeployResult
from ag3ntwerk.modules.workbench.utils.ports import PortAllocator


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
    settings.security.auth_token = None
    configure_workbench_settings(settings)
    return settings


@pytest.fixture
def port_allocator():
    """Create a port allocator for testing."""
    return PortAllocator(start_port=9000, end_port=9100)


@pytest.fixture
def mock_docker_client():
    """Create a mock Docker client."""
    client = MagicMock()
    container = MagicMock()
    container.id = "mock-container-id"
    container.status = "running"
    container.stats.return_value = {
        "cpu_stats": {"cpu_usage": {"total_usage": 100}, "system_cpu_usage": 1000},
        "precpu_stats": {"cpu_usage": {"total_usage": 50}, "system_cpu_usage": 500},
        "memory_stats": {"usage": 1024 * 1024 * 100, "limit": 1024 * 1024 * 512},
    }
    client.containers.run.return_value = container
    client.containers.get.return_value = container
    client.containers.list.return_value = []
    return client


@pytest.fixture
def ide_manager(workbench_settings, mock_docker_client, port_allocator):
    """Create an IDE container manager for testing."""
    manager = IDEContainerManager(
        settings=workbench_settings,
        docker_client=mock_docker_client,
        port_allocator=port_allocator,
    )
    return manager


@pytest.fixture
def sample_workspace(temp_workspace_dir):
    """Create a sample workspace."""
    workspace_path = temp_workspace_dir / "test-workspace"
    workspace_path.mkdir(parents=True, exist_ok=True)
    return Workspace(
        id="ws-test-123",
        name="test-workspace",
        path=str(workspace_path),
        runtime=RuntimeType.PYTHON,
        status=WorkspaceStatus.RUNNING,
    )


# =============================================================================
# IDE Manager Tests
# =============================================================================


class TestIDEContainerManager:
    """Tests for IDE container management."""

    @pytest.mark.asyncio
    async def test_start_ide_success(self, ide_manager, sample_workspace):
        """Test successfully starting an IDE container."""
        with patch.object(ide_manager, "_wait_for_ready", new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = True

            ide_info = await ide_manager.start_ide(
                workspace_id=sample_workspace.id,
                workspace_path=sample_workspace.path,
            )

            assert ide_info.workspace_id == sample_workspace.id
            assert ide_info.ide_url is not None
            assert "localhost" in ide_info.ide_url

    @pytest.mark.asyncio
    async def test_start_ide_with_custom_password(self, ide_manager, sample_workspace):
        """Test starting IDE with custom password."""
        with patch.object(ide_manager, "_wait_for_ready", new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = True

            await ide_manager.start_ide(
                workspace_id=sample_workspace.id,
                workspace_path=sample_workspace.path,
                password="custom-password",
            )

            token = ide_manager.get_auth_token(sample_workspace.id)
            assert token == "custom-password"

    @pytest.mark.asyncio
    async def test_stop_ide(self, ide_manager, sample_workspace):
        """Test stopping an IDE container."""
        with patch.object(ide_manager, "_wait_for_ready", new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = True

            # Start first
            await ide_manager.start_ide(
                workspace_id=sample_workspace.id,
                workspace_path=sample_workspace.path,
            )

            # Then stop
            success = await ide_manager.stop_ide(sample_workspace.id)
            assert success is True

    @pytest.mark.asyncio
    async def test_stop_ide_not_running(self, ide_manager, sample_workspace):
        """Test stopping IDE that isn't running."""
        success = await ide_manager.stop_ide(sample_workspace.id)
        assert success is False

    @pytest.mark.asyncio
    async def test_get_ide_status_running(self, ide_manager, sample_workspace):
        """Test getting status of running IDE."""
        with patch.object(ide_manager, "_wait_for_ready", new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = True

            await ide_manager.start_ide(
                workspace_id=sample_workspace.id,
                workspace_path=sample_workspace.path,
            )

            status = await ide_manager.get_ide_status(sample_workspace.id)
            assert status.workspace_id == sample_workspace.id
            assert status.running is True
            assert status.container_id is not None

    @pytest.mark.asyncio
    async def test_get_ide_status_not_running(self, ide_manager, sample_workspace):
        """Test getting status when IDE isn't running."""
        status = await ide_manager.get_ide_status(sample_workspace.id)
        assert status.workspace_id == sample_workspace.id
        assert status.running is False
        assert status.container_id is None

    def test_ide_status_to_dict(self):
        """Test IDEStatus serialization."""
        status = IDEStatus(
            workspace_id="ws-123",
            running=True,
            container_id="abc123",
            ide_url="http://localhost:9000",
            cpu_usage=25.5,
        )
        data = status.to_dict()
        assert data["workspace_id"] == "ws-123"
        assert data["running"] is True
        assert data["cpu_usage"] == 25.5


# =============================================================================
# Framework Detector Tests
# =============================================================================


class TestFrameworkDetector:
    """Tests for framework detection."""

    @pytest.fixture
    def python_workspace(self, temp_workspace_dir):
        """Create a Python FastAPI workspace."""
        ws_path = temp_workspace_dir / "python-fastapi"
        ws_path.mkdir()
        (ws_path / "requirements.txt").write_text("fastapi==0.100.0\nuvicorn[standard]\n")
        (ws_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
        return ws_path

    @pytest.fixture
    def nextjs_workspace(self, temp_workspace_dir):
        """Create a Next.js workspace."""
        ws_path = temp_workspace_dir / "nextjs-app"
        ws_path.mkdir()
        (ws_path / "package.json").write_text(
            """{
            "name": "my-nextjs-app",
            "version": "1.0.0",
            "dependencies": {
                "next": "13.4.0",
                "react": "18.2.0",
                "react-dom": "18.2.0"
            },
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start"
            }
        }"""
        )
        return ws_path

    @pytest.fixture
    def react_workspace(self, temp_workspace_dir):
        """Create a React workspace."""
        ws_path = temp_workspace_dir / "react-app"
        ws_path.mkdir()
        (ws_path / "package.json").write_text(
            """{
            "name": "my-react-app",
            "version": "1.0.0",
            "dependencies": {
                "react": "18.2.0",
                "react-dom": "18.2.0",
                "react-scripts": "5.0.1"
            },
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build"
            }
        }"""
        )
        return ws_path

    @pytest.fixture
    def go_workspace(self, temp_workspace_dir):
        """Create a Go workspace."""
        ws_path = temp_workspace_dir / "go-app"
        ws_path.mkdir()
        (ws_path / "go.mod").write_text(
            "module example.com/myapp\n\ngo 1.21\n\nrequire github.com/gin-gonic/gin v1.9.0\n"
        )
        (ws_path / "main.go").write_text("package main\n\nfunc main() {}\n")
        return ws_path

    @pytest.mark.asyncio
    async def test_detect_fastapi(self, python_workspace):
        """Test detecting FastAPI framework."""
        detector = FrameworkDetector(str(python_workspace))
        info = await detector.detect()

        assert info.framework == FrameworkType.FASTAPI
        assert info.start_command is not None
        assert "uvicorn" in info.start_command

    @pytest.mark.asyncio
    async def test_detect_nextjs(self, nextjs_workspace):
        """Test detecting Next.js framework."""
        detector = FrameworkDetector(str(nextjs_workspace))
        info = await detector.detect()

        assert info.framework == FrameworkType.NEXTJS
        assert info.build_command == "npm run build"
        assert info.port == 3000

    @pytest.mark.asyncio
    async def test_detect_react(self, react_workspace):
        """Test detecting React framework."""
        detector = FrameworkDetector(str(react_workspace))
        info = await detector.detect()

        assert info.framework == FrameworkType.REACT
        assert info.build_command == "npm run build"

    @pytest.mark.asyncio
    async def test_detect_go_gin(self, go_workspace):
        """Test detecting Go Gin framework."""
        detector = FrameworkDetector(str(go_workspace))
        info = await detector.detect()

        assert info.framework == FrameworkType.GIN
        assert "go" in info.dockerfile_base

    @pytest.mark.asyncio
    async def test_detect_unknown_framework(self, temp_workspace_dir):
        """Test detecting unknown/generic framework."""
        ws_path = temp_workspace_dir / "unknown"
        ws_path.mkdir()
        (ws_path / "README.md").write_text("# Unknown Project")

        detector = FrameworkDetector(str(ws_path))
        info = await detector.detect()

        assert info.framework == FrameworkType.UNKNOWN

    def test_framework_info_dataclass(self):
        """Test FrameworkInfo dataclass."""
        info = FrameworkInfo(
            framework=FrameworkType.FASTAPI,
            version="0.100.0",
            build_command=None,
            start_command="uvicorn main:app",
            port=8000,
        )
        assert info.framework == FrameworkType.FASTAPI
        assert info.port == 8000


# =============================================================================
# Config Generator Tests
# =============================================================================


class TestConfigGenerator:
    """Tests for config file generation."""

    @pytest.fixture
    def nextjs_framework_info(self):
        """Create Next.js framework info."""
        return FrameworkInfo(
            framework=FrameworkType.NEXTJS,
            version="13.4.0",
            build_command="npm run build",
            start_command="npm start",
            install_command="npm install",
            output_directory=".next",
            port=3000,
            dockerfile_base="node:18-alpine",
        )

    @pytest.fixture
    def fastapi_framework_info(self):
        """Create FastAPI framework info."""
        return FrameworkInfo(
            framework=FrameworkType.FASTAPI,
            version="0.100.0",
            start_command="uvicorn main:app --host 0.0.0.0 --port 8000",
            install_command="pip install -r requirements.txt",
            port=8000,
            dockerfile_base="python:3.11-slim",
        )

    def test_generate_dockerfile_nextjs(self, temp_workspace_dir, nextjs_framework_info):
        """Test generating Dockerfile for Next.js."""
        ws_path = temp_workspace_dir / "nextjs-gen"
        ws_path.mkdir()

        generator = ConfigGenerator(str(ws_path), nextjs_framework_info)
        dockerfile = generator._generate_dockerfile()

        assert "FROM node:20-alpine" in dockerfile
        assert "npm run build" in dockerfile
        assert "EXPOSE 3000" in dockerfile

    def test_generate_dockerfile_fastapi(self, temp_workspace_dir, fastapi_framework_info):
        """Test generating Dockerfile for FastAPI."""
        ws_path = temp_workspace_dir / "fastapi-gen"
        ws_path.mkdir()
        (ws_path / "requirements.txt").write_text("fastapi\nuvicorn\n")

        generator = ConfigGenerator(str(ws_path), fastapi_framework_info)
        dockerfile = generator._generate_dockerfile()

        assert "FROM python:3.11-slim" in dockerfile
        assert "pip install" in dockerfile
        assert "EXPOSE 8000" in dockerfile

    def test_generate_vercel_json(self, temp_workspace_dir, nextjs_framework_info):
        """Test generating vercel.json."""
        ws_path = temp_workspace_dir / "vercel-gen"
        ws_path.mkdir()

        generator = ConfigGenerator(str(ws_path), nextjs_framework_info)
        vercel_json = generator._generate_vercel_json()

        assert '"framework"' in vercel_json or '"buildCommand"' in vercel_json

    def test_generate_env_file(self, temp_workspace_dir, nextjs_framework_info):
        """Test generating .env from .env.example."""
        ws_path = temp_workspace_dir / "env-gen"
        ws_path.mkdir()
        (ws_path / ".env.example").write_text("DATABASE_URL=\nAPI_KEY=\n")

        generator = ConfigGenerator(str(ws_path), nextjs_framework_info)
        env_content = generator._generate_env_file()

        assert env_content is not None
        assert "DATABASE_URL" in env_content

    @pytest.mark.asyncio
    async def test_generate_all_no_write(self, temp_workspace_dir, nextjs_framework_info):
        """Test generating all configs without writing."""
        ws_path = temp_workspace_dir / "all-gen"
        ws_path.mkdir()

        generator = ConfigGenerator(str(ws_path), nextjs_framework_info)
        configs = await generator.generate_all(write_files=False)

        assert isinstance(configs, GeneratedConfigs)
        assert configs.dockerfile is not None
        assert not (ws_path / "Dockerfile").exists()

    @pytest.mark.asyncio
    async def test_generate_all_with_write(self, temp_workspace_dir, nextjs_framework_info):
        """Test generating all configs with writing."""
        ws_path = temp_workspace_dir / "write-gen"
        ws_path.mkdir()

        generator = ConfigGenerator(str(ws_path), nextjs_framework_info)
        configs = await generator.generate_all(write_files=True)

        assert configs.files_written is not None
        assert len(configs.files_written) > 0
        assert (ws_path / "Dockerfile").exists()


# =============================================================================
# One-Click Deployer Tests
# =============================================================================


class TestOneClickDeployer:
    """Tests for one-click deployment."""

    @pytest.fixture
    def mock_workbench_service(self, sample_workspace):
        """Create a mock workbench service."""
        service = MagicMock()
        service.get_workspace = AsyncMock(return_value=sample_workspace)
        service._settings = MagicMock()
        service._settings.get_workspace_path = MagicMock(return_value=Path(sample_workspace.path))
        return service

    @pytest.fixture
    def oneclick_deployer(self, mock_workbench_service):
        """Create a one-click deployer."""
        return OneClickDeployer(mock_workbench_service)

    @pytest.mark.asyncio
    async def test_preview_deployment(
        self, oneclick_deployer, sample_workspace, temp_workspace_dir
    ):
        """Test previewing a deployment."""
        # Create a package.json for detection
        ws_path = Path(sample_workspace.path)
        (ws_path / "package.json").write_text('{"dependencies": {"next": "13.0.0"}}')

        mock_framework_info = FrameworkInfo(
            framework=FrameworkType.NEXTJS,
            version="13.0.0",
            build_command="npm run build",
            start_command="npm start",
            port=3000,
        )

        with patch("ag3ntwerk.modules.workbench.deployers.oneclick.FrameworkDetector") as MockDetector:
            mock_detector_instance = AsyncMock()
            mock_detector_instance.detect.return_value = mock_framework_info
            MockDetector.return_value = mock_detector_instance

            preview = await oneclick_deployer.preview(sample_workspace.id)

            assert preview.workspace_id == sample_workspace.id
            assert preview.detected_framework == "nextjs"
            assert preview.recommended_target is not None

    @pytest.mark.asyncio
    async def test_deploy_success(self, oneclick_deployer, sample_workspace):
        """Test successful deployment."""
        mock_framework_info = FrameworkInfo(
            framework=FrameworkType.NEXTJS,
            version="13.0.0",
            build_command="npm run build",
            start_command="npm start",
            port=3000,
        )

        with (
            patch("ag3ntwerk.modules.workbench.deployers.oneclick.FrameworkDetector") as MockDetector,
            patch("ag3ntwerk.modules.workbench.deployers.oneclick.get_deployer") as mock_get_deployer,
        ):

            # Mock framework detector
            mock_detector_instance = AsyncMock()
            mock_detector_instance.detect.return_value = mock_framework_info
            MockDetector.return_value = mock_detector_instance

            # Mock deployer
            mock_deployer = AsyncMock()
            mock_deployer.deploy.return_value = DeployResult(
                deployment_id="deploy-123",
                target="local",
                status="success",
                url="https://example.vercel.app",
            )
            mock_get_deployer.return_value = mock_deployer

            result = await oneclick_deployer.deploy(
                workspace_id=sample_workspace.id,
                target="local",
            )

            assert result.detected_framework == "nextjs"

    @pytest.mark.asyncio
    async def test_deploy_with_environment(self, oneclick_deployer, sample_workspace):
        """Test deployment with custom environment variables."""
        mock_framework_info = FrameworkInfo(
            framework=FrameworkType.FASTAPI,
            port=8000,
        )

        with (
            patch("ag3ntwerk.modules.workbench.deployers.oneclick.FrameworkDetector") as MockDetector,
            patch("ag3ntwerk.modules.workbench.deployers.oneclick.get_deployer") as mock_get_deployer,
        ):

            # Mock framework detector
            mock_detector_instance = AsyncMock()
            mock_detector_instance.detect.return_value = mock_framework_info
            MockDetector.return_value = mock_detector_instance

            # Mock deployer
            mock_deployer = AsyncMock()
            mock_deployer.deploy.return_value = DeployResult(
                deployment_id="deploy-456",
                target="local",
                status="success",
            )
            mock_get_deployer.return_value = mock_deployer

            result = await oneclick_deployer.deploy(
                workspace_id=sample_workspace.id,
                target="local",
                environment={"DATABASE_URL": "postgres://localhost/db"},
            )

            assert result is not None

    def test_oneclick_result_to_dict(self):
        """Test OneClickResult serialization."""
        result = OneClickResult(
            deployment_id="deploy-123",
            status="success",
            detected_framework="nextjs",
            build_command="npm run build",
            start_command="npm start",
            configs_generated=["Dockerfile", "vercel.json"],
            deployment_target="vercel",
            deployment_url="https://app.vercel.app",
        )
        data = result.to_dict()

        assert data["deployment_id"] == "deploy-123"
        assert data["status"] == "success"
        assert "Dockerfile" in data["configs_generated"]


# =============================================================================
# Integration Tests
# =============================================================================


class TestIDEServiceIntegration:
    """Tests for IDE integration with WorkbenchService."""

    @pytest.fixture
    def mock_service_with_ide(self, workbench_settings, mock_docker_client):
        """Create a mock service with IDE manager."""
        from ag3ntwerk.modules.workbench.service import WorkbenchService

        service = WorkbenchService(workbench_settings)
        service._ide_manager = IDEContainerManager(
            settings=workbench_settings,
            docker_client=mock_docker_client,
            port_allocator=PortAllocator(start_port=9000, end_port=9100),
        )
        return service

    @pytest.mark.asyncio
    async def test_service_start_ide(self, mock_service_with_ide, sample_workspace):
        """Test starting IDE through service."""
        mock_service_with_ide._workspaces[sample_workspace.id] = sample_workspace

        with patch.object(
            mock_service_with_ide._ide_manager, "start_ide", new_callable=AsyncMock
        ) as mock_start:
            mock_start.return_value = IDEInfo(
                workspace_id=sample_workspace.id,
                ide_url="http://localhost:9000",
                mode=IDEMode.CODESERVER_PER_WORKSPACE,
            )

            ide_info = await mock_service_with_ide.start_ide(sample_workspace.id)

            assert ide_info.workspace_id == sample_workspace.id
            assert ide_info.ide_url is not None

    @pytest.mark.asyncio
    async def test_service_stop_ide(self, mock_service_with_ide, sample_workspace):
        """Test stopping IDE through service."""
        mock_service_with_ide._workspaces[sample_workspace.id] = sample_workspace

        with patch.object(
            mock_service_with_ide._ide_manager, "stop_ide", new_callable=AsyncMock
        ) as mock_stop:
            mock_stop.return_value = True

            success = await mock_service_with_ide.stop_ide(sample_workspace.id)

            assert success is True
            mock_stop.assert_called_once_with(sample_workspace.id)
