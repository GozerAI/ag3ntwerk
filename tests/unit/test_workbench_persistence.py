"""
Unit tests for Workbench Persistence Layer.

Tests SQLite-based storage for workspaces, runs, and ports.
"""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ag3ntwerk.modules.workbench.persistence import WorkbenchPersistence
from ag3ntwerk.modules.workbench.schemas import (
    Workspace,
    WorkspaceStatus,
    RuntimeType,
    RunResult,
    RunStatus,
    PortExposeResult,
    PortProtocol,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    yield db_path

    # Cleanup
    if db_path.exists():
        os.unlink(db_path)


@pytest.fixture
def persistence(temp_db):
    """Create a persistence instance with a temp database."""
    p = WorkbenchPersistence(db_path=temp_db)
    p.initialize()
    return p


@pytest.fixture
def sample_workspace():
    """Create a sample workspace for testing."""
    return Workspace(
        id="ws-test-001",
        name="Test Workspace",
        path="/workspaces/test",
        runtime=RuntimeType.PYTHON,
        status=WorkspaceStatus.STOPPED,
        metadata={"version": "1.0", "template": "python-basic"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestWorkbenchPersistenceInit:
    """Tests for persistence initialization."""

    def test_initialize_creates_tables(self, temp_db):
        """Test that initialization creates required tables."""
        p = WorkbenchPersistence(db_path=temp_db)
        p.initialize()

        import sqlite3

        conn = sqlite3.connect(str(temp_db))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "workspaces" in tables
        assert "run_history" in tables
        assert "exposed_ports" in tables
        assert "port_allocations" in tables

    def test_initialize_idempotent(self, persistence):
        """Test that initialization can be called multiple times."""
        persistence.initialize()
        persistence.initialize()
        # Should not raise


class TestWorkspaceOperations:
    """Tests for workspace CRUD operations."""

    def test_save_and_load_workspace(self, persistence, sample_workspace):
        """Test saving and loading a workspace."""
        persistence.save_workspace(sample_workspace, container_id="abc123")

        loaded = persistence.load_workspace(sample_workspace.id)

        assert loaded is not None
        assert loaded.id == sample_workspace.id
        assert loaded.name == sample_workspace.name
        assert loaded.path == sample_workspace.path
        assert loaded.runtime == sample_workspace.runtime
        assert loaded.status == sample_workspace.status
        assert loaded.metadata == sample_workspace.metadata

    def test_load_workspace_not_found(self, persistence):
        """Test loading a non-existent workspace."""
        loaded = persistence.load_workspace("non-existent")
        assert loaded is None

    def test_load_all_workspaces(self, persistence, sample_workspace):
        """Test loading all workspaces."""
        # Save multiple workspaces
        workspace1 = sample_workspace
        workspace2 = Workspace(
            id="ws-test-002",
            name="Second Workspace",
            path="/workspaces/test2",
            runtime=RuntimeType.NODE,
            status=WorkspaceStatus.RUNNING,
        )

        persistence.save_workspace(workspace1)
        persistence.save_workspace(workspace2)

        all_workspaces = persistence.load_all_workspaces()

        assert len(all_workspaces) == 2
        ids = {w.id for w in all_workspaces}
        assert "ws-test-001" in ids
        assert "ws-test-002" in ids

    def test_update_workspace_status(self, persistence, sample_workspace):
        """Test updating workspace status."""
        persistence.save_workspace(sample_workspace)

        persistence.update_workspace_status(
            sample_workspace.id, WorkspaceStatus.RUNNING, container_id="new-container-id"
        )

        loaded = persistence.load_workspace(sample_workspace.id)
        assert loaded.status == WorkspaceStatus.RUNNING

    def test_delete_workspace(self, persistence, sample_workspace):
        """Test deleting a workspace."""
        persistence.save_workspace(sample_workspace)

        persistence.delete_workspace(sample_workspace.id)

        loaded = persistence.load_workspace(sample_workspace.id)
        assert loaded is None

    def test_get_container_id(self, persistence, sample_workspace):
        """Test getting container ID."""
        persistence.save_workspace(sample_workspace, container_id="my-container")

        container_id = persistence.get_container_id(sample_workspace.id)

        assert container_id == "my-container"


class TestRunHistoryOperations:
    """Tests for run history operations."""

    def test_save_and_load_runs(self, persistence, sample_workspace):
        """Test saving and loading run history."""
        persistence.save_workspace(sample_workspace)

        run = RunResult(
            run_id="run-001",
            workspace_id=sample_workspace.id,
            cmd=["python", "main.py"],
            status=RunStatus.COMPLETED,
            exit_code=0,
            stdout="Hello World",
            stderr="",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            duration_seconds=1.5,
        )

        persistence.save_run(run)

        runs = persistence.load_runs_for_workspace(sample_workspace.id)

        assert len(runs) == 1
        assert runs[0].run_id == "run-001"
        assert runs[0].exit_code == 0
        assert runs[0].stdout == "Hello World"

    def test_load_runs_ordered_by_time(self, persistence, sample_workspace):
        """Test that runs are ordered by most recent first."""
        persistence.save_workspace(sample_workspace)

        # Save runs with different timestamps
        for i in range(5):
            run = RunResult(
                run_id=f"run-{i:03d}",
                workspace_id=sample_workspace.id,
                cmd=["echo", str(i)],
                status=RunStatus.COMPLETED,
                started_at=datetime.now(timezone.utc),
            )
            persistence.save_run(run)

        runs = persistence.load_runs_for_workspace(sample_workspace.id, limit=3)

        assert len(runs) == 3


class TestPortOperations:
    """Tests for port allocation operations."""

    def test_save_and_load_exposed_port(self, persistence, sample_workspace):
        """Test saving and loading exposed ports."""
        persistence.save_workspace(sample_workspace)

        port_result = PortExposeResult(
            workspace_id=sample_workspace.id,
            port=8080,
            host_port=32768,
            proto=PortProtocol.HTTP,
            label="Web Server",
            preview_url="http://localhost:32768",
        )

        persistence.save_exposed_port(port_result)

        ports = persistence.load_exposed_ports(sample_workspace.id)

        assert len(ports) == 1
        assert ports[0].port == 8080
        assert ports[0].host_port == 32768
        assert ports[0].label == "Web Server"

    def test_load_all_port_allocations(self, persistence, sample_workspace):
        """Test loading all port allocations."""
        persistence.save_workspace(sample_workspace)

        port_result = PortExposeResult(
            workspace_id=sample_workspace.id,
            port=8080,
            host_port=32768,
            proto=PortProtocol.HTTP,
            preview_url="http://localhost:32768",
        )
        persistence.save_exposed_port(port_result)

        allocations = persistence.load_all_port_allocations()

        assert 32768 in allocations
        assert allocations[32768] == sample_workspace.id

    def test_release_port(self, persistence, sample_workspace):
        """Test releasing a port."""
        persistence.save_workspace(sample_workspace)

        port_result = PortExposeResult(
            workspace_id=sample_workspace.id,
            port=8080,
            host_port=32768,
            proto=PortProtocol.HTTP,
            preview_url="http://localhost:32768",
        )
        persistence.save_exposed_port(port_result)

        persistence.release_port(32768)

        allocations = persistence.load_all_port_allocations()
        assert 32768 not in allocations

    def test_release_workspace_ports(self, persistence, sample_workspace):
        """Test releasing all ports for a workspace."""
        persistence.save_workspace(sample_workspace)

        # Add multiple ports
        for i, port in enumerate([8080, 8081, 8082]):
            port_result = PortExposeResult(
                workspace_id=sample_workspace.id,
                port=port,
                host_port=32768 + i,
                proto=PortProtocol.HTTP,
                preview_url=f"http://localhost:{32768 + i}",
            )
            persistence.save_exposed_port(port_result)

        persistence.release_workspace_ports(sample_workspace.id)

        ports = persistence.load_exposed_ports(sample_workspace.id)
        assert len(ports) == 0


class TestContainerMappings:
    """Tests for container mapping operations."""

    def test_get_all_container_mappings(self, persistence):
        """Test getting all workspace to container mappings."""
        # Save multiple workspaces with containers
        for i in range(3):
            ws = Workspace(
                id=f"ws-{i:03d}",
                name=f"Workspace {i}",
                path=f"/workspaces/{i}",
                runtime=RuntimeType.PYTHON,
                status=WorkspaceStatus.RUNNING,
            )
            persistence.save_workspace(ws, container_id=f"container-{i}")

        mappings = persistence.get_all_container_mappings()

        assert len(mappings) == 3
        assert mappings["ws-000"] == "container-0"
        assert mappings["ws-001"] == "container-1"
        assert mappings["ws-002"] == "container-2"


class TestStatistics:
    """Tests for statistics operations."""

    def test_get_stats(self, persistence, sample_workspace):
        """Test getting persistence statistics."""
        persistence.save_workspace(sample_workspace)

        run = RunResult(
            run_id="run-001",
            workspace_id=sample_workspace.id,
            cmd=["python", "-c", "print('hi')"],
            status=RunStatus.COMPLETED,
        )
        persistence.save_run(run)

        port = PortExposeResult(
            workspace_id=sample_workspace.id,
            port=8080,
            host_port=32768,
            proto=PortProtocol.HTTP,
            preview_url="http://localhost:32768",
        )
        persistence.save_exposed_port(port)

        stats = persistence.get_stats()

        assert stats["total_workspaces"] == 1
        assert stats["total_runs"] == 1
        assert stats["allocated_ports"] == 1
