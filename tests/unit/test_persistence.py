"""
Tests for the persistence layer.

Tests database initialization, migration fallback, analytics, audit trails,
and plugin configuration storage using temporary SQLite databases.
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ag3ntwerk.persistence.database import DatabaseManager, DatabaseConfig, DatabaseBackend
from ag3ntwerk.persistence.analytics import (
    AnalyticsStore,
    MetricPoint,
    AggregationType,
    TimeGranularity,
)
from ag3ntwerk.persistence.audit import AuditTrail, AuditAction, AuditOutcome
from ag3ntwerk.persistence.plugin_config import PluginConfigStore


def _utcnow():
    return datetime.now(timezone.utc)


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_persistence.db"


@pytest.fixture
def db_config(temp_db_path):
    """Create test database config."""
    return DatabaseConfig(
        backend=DatabaseBackend.SQLITE,
        sqlite_path=str(temp_db_path),
    )


@pytest.fixture
async def db_manager(db_config):
    """Create and initialize database manager."""
    db = DatabaseManager(db_config)
    await db.initialize(auto_migrate=True)
    yield db
    await db.close()


class TestDatabaseManager:
    """Tests for DatabaseManager."""

    @pytest.mark.asyncio
    async def test_initialize(self, db_config):
        """Test database initialization."""
        db = DatabaseManager(db_config)
        await db.initialize(auto_migrate=True)

        # Verify tables exist
        tables = await db.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [t["name"] for t in tables]

        assert "analytics" in table_names
        assert "audit_trail" in table_names
        assert "plugin_config" in table_names
        assert "decision_history" in table_names

        await db.close()

    @pytest.mark.asyncio
    async def test_execute_and_fetch(self, db_manager):
        """Test basic execute and fetch operations."""
        # Insert data
        await db_manager.execute(
            "INSERT INTO analytics (metric_name, metric_value, timestamp, source) VALUES (?, ?, ?, ?)",
            ("test_metric", 42.0, _utcnow().isoformat(), "test"),
        )

        # Fetch data
        row = await db_manager.fetch_one(
            "SELECT * FROM analytics WHERE metric_name = ?",
            ("test_metric",),
        )

        assert row is not None
        assert row["metric_value"] == 42.0

    @pytest.mark.asyncio
    async def test_fetch_all(self, db_manager):
        """Test fetch_all operation."""
        # Insert multiple rows
        for i in range(5):
            await db_manager.execute(
                "INSERT INTO analytics (metric_name, metric_value, timestamp, source) VALUES (?, ?, ?, ?)",
                (f"metric_{i}", float(i), _utcnow().isoformat(), "test"),
            )

        # Fetch all
        rows = await db_manager.fetch_all(
            "SELECT * FROM analytics WHERE source = ?",
            ("test",),
        )

        assert len(rows) == 5

    @pytest.mark.asyncio
    async def test_execute_many(self, db_manager):
        """Test batch insert."""
        params = [
            (f"batch_metric_{i}", float(i * 10), _utcnow().isoformat(), "batch") for i in range(10)
        ]

        count = await db_manager.execute_many(
            "INSERT INTO analytics (metric_name, metric_value, timestamp, source) VALUES (?, ?, ?, ?)",
            params,
        )

        assert count == 10

        # Verify
        rows = await db_manager.fetch_all(
            "SELECT * FROM analytics WHERE source = ?",
            ("batch",),
        )
        assert len(rows) == 10


class TestAnalyticsStore:
    """Tests for AnalyticsStore."""

    @pytest.fixture
    async def analytics_store(self, db_manager):
        """Create analytics store with test database."""
        store = AnalyticsStore(db=db_manager)
        await store.initialize()
        return store

    @pytest.mark.asyncio
    async def test_record_metric(self, analytics_store):
        """Test recording a single metric."""
        await analytics_store.record(
            metric_name="test_metric",
            value=100.5,
            dimensions={"agent": "Nexus", "endpoint": "/health"},
        )

        # Query it back
        results = await analytics_store.query("test_metric", limit=1)
        assert len(results) == 1
        assert results[0]["metric_value"] == 100.5

    @pytest.mark.asyncio
    async def test_record_batch(self, analytics_store):
        """Test batch recording."""
        metrics = [
            MetricPoint(metric_name="batch_test", value=float(i), source="batch") for i in range(20)
        ]

        count = await analytics_store.record_batch(metrics)
        assert count == 20

    @pytest.mark.asyncio
    async def test_query_with_time_range(self, analytics_store):
        """Test querying with time range."""
        now = _utcnow()

        # Record metrics at different times
        for i in range(5):
            await analytics_store.record(
                metric_name="time_test",
                value=float(i),
                timestamp=now - timedelta(minutes=i * 10),
            )

        # Query last 30 minutes
        results = await analytics_store.query(
            metric_name="time_test",
            start_time=now - timedelta(minutes=30),
        )

        # Should get 4 (0, 10, 20, 30 minutes ago)
        assert len(results) >= 3

    @pytest.mark.asyncio
    async def test_get_latest(self, analytics_store):
        """Test getting latest value."""
        await analytics_store.record("latest_test", 1.0)
        await asyncio.sleep(0.01)
        await analytics_store.record("latest_test", 2.0)
        await asyncio.sleep(0.01)
        await analytics_store.record("latest_test", 3.0)

        latest = await analytics_store.get_latest("latest_test")
        assert latest == 3.0

    @pytest.mark.asyncio
    async def test_dashboard_stats(self, analytics_store):
        """Test dashboard stats generation."""
        # Record some metrics
        await analytics_store.record("api_requests", 10)
        await analytics_store.record("response_time_ms", 45.0)
        await analytics_store.record("task_completed", 5)
        await analytics_store.record("task_failed", 1)

        stats = await analytics_store.get_dashboard_stats(time_window=timedelta(hours=1))

        assert "total_requests" in stats
        assert "avg_response_time_ms" in stats
        assert "task_success_rate" in stats


class TestAuditTrail:
    """Tests for AuditTrail."""

    @pytest.fixture
    async def audit_trail(self, db_manager):
        """Create audit trail with test database."""
        trail = AuditTrail(db=db_manager)
        await trail.initialize()
        return trail

    @pytest.mark.asyncio
    async def test_log_action(self, audit_trail):
        """Test logging an audit action."""
        entry_id = await audit_trail.log(
            action=AuditAction.TASK_COMPLETED,
            entity_type="task",
            entity_id="task-123",
            actor="Nexus",
            details={"duration_ms": 1500},
        )

        assert entry_id is not None

        # Query it back
        entries = await audit_trail.query(entity_id="task-123")
        assert len(entries) == 1
        assert entries[0].action == AuditAction.TASK_COMPLETED
        assert entries[0].details["duration_ms"] == 1500

    @pytest.mark.asyncio
    async def test_record_decision(self, audit_trail):
        """Test recording a decision."""
        decision_id = await audit_trail.record_decision(
            agent_code="Keystone",
            decision_type="budget_approval",
            input_summary="Request for $10,000",
            reasoning="Within quarterly budget, approved based on ROI",
            confidence=0.95,
            alternatives=[
                {"option": "deny", "reason": "budget constraints"},
                {"option": "partial", "reason": "approve 50%"},
            ],
            selected_option="approve",
        )

        assert decision_id is not None

        # Get decision history
        decisions = await audit_trail.get_decision_history(agent_code="Keystone")
        assert len(decisions) == 1
        assert decisions[0].confidence == 0.95
        assert len(decisions[0].alternatives) == 2

    @pytest.mark.asyncio
    async def test_query_by_action(self, audit_trail):
        """Test querying by action type."""
        # Log different actions
        await audit_trail.log(AuditAction.TASK_CREATED, "task", "t1", "user")
        await audit_trail.log(AuditAction.TASK_COMPLETED, "task", "t1", "Nexus")
        await audit_trail.log(AuditAction.TASK_CREATED, "task", "t2", "user")

        # Query only completions
        entries = await audit_trail.query(action=AuditAction.TASK_COMPLETED)
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_compliance_report(self, audit_trail):
        """Test generating compliance report."""
        # Log various actions
        await audit_trail.log(AuditAction.TASK_COMPLETED, "task", "t1", "Nexus")
        await audit_trail.log(
            AuditAction.TASK_FAILED, "task", "t2", "Forge", outcome=AuditOutcome.FAILURE
        )
        await audit_trail.record_decision("Keystone", "approval", reasoning="test", confidence=0.9)

        report = await audit_trail.generate_compliance_report(
            start_time=_utcnow() - timedelta(hours=1)
        )

        assert "action_summary" in report
        assert "decision_statistics" in report
        assert report["decision_statistics"]["total_decisions"] >= 1


class TestPluginConfigStore:
    """Tests for PluginConfigStore."""

    @pytest.fixture
    async def plugin_store(self, db_manager):
        """Create plugin config store with test database."""
        store = PluginConfigStore(db=db_manager)
        await store.initialize()
        return store

    @pytest.mark.asyncio
    async def test_save_and_load(self, plugin_store):
        """Test saving and loading config."""
        config = {
            "api_key": "test-key",
            "max_retries": 3,
            "timeout": 30.0,
        }

        await plugin_store.save(
            plugin_id="test-plugin",
            config=config,
            version="1.0.0",
        )

        loaded = await plugin_store.load("test-plugin")
        assert loaded == config

    @pytest.mark.asyncio
    async def test_load_nonexistent(self, plugin_store):
        """Test loading nonexistent config."""
        result = await plugin_store.load("nonexistent")
        assert result is None

        result = await plugin_store.load("nonexistent", default={"default": True})
        assert result == {"default": True}

    @pytest.mark.asyncio
    async def test_enable_disable(self, plugin_store):
        """Test enabling and disabling plugins."""
        await plugin_store.save("toggle-plugin", {"key": "value"})

        assert await plugin_store.is_enabled("toggle-plugin") is True

        await plugin_store.set_enabled("toggle-plugin", False)
        assert await plugin_store.is_enabled("toggle-plugin") is False

        await plugin_store.set_enabled("toggle-plugin", True)
        assert await plugin_store.is_enabled("toggle-plugin") is True

    @pytest.mark.asyncio
    async def test_list_plugins(self, plugin_store):
        """Test listing plugins."""
        await plugin_store.save("plugin-a", {})
        await plugin_store.save("plugin-b", {}, enabled=False)
        await plugin_store.save("plugin-c", {})

        all_plugins = await plugin_store.list_plugins()
        assert len(all_plugins) == 3

        enabled_only = await plugin_store.list_plugins(enabled_only=True)
        assert len(enabled_only) == 2

    @pytest.mark.asyncio
    async def test_update_config(self, plugin_store):
        """Test partial config update."""
        await plugin_store.save(
            "update-plugin",
            {"key1": "value1", "key2": "value2"},
        )

        await plugin_store.update_config("update-plugin", {"key2": "updated"})

        loaded = await plugin_store.load("update-plugin")
        assert loaded["key1"] == "value1"
        assert loaded["key2"] == "updated"

    @pytest.mark.asyncio
    async def test_delete(self, plugin_store):
        """Test deleting config."""
        await plugin_store.save("delete-me", {"data": "test"})

        deleted = await plugin_store.delete("delete-me")
        assert deleted is True

        loaded = await plugin_store.load("delete-me")
        assert loaded is None

        # Delete nonexistent
        deleted = await plugin_store.delete("never-existed")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_export_import(self, plugin_store):
        """Test export and import."""
        await plugin_store.save("export-1", {"data": 1})
        await plugin_store.save("export-2", {"data": 2}, enabled=False)

        exported = await plugin_store.export_all()
        assert len(exported) == 2
        assert "export-1" in exported
        assert "export-2" in exported

        # Clear and import
        await plugin_store.delete("export-1")
        await plugin_store.delete("export-2")

        imported = await plugin_store.import_configs(exported)
        assert imported == 2

        # Verify
        assert await plugin_store.load("export-1") is not None


class TestDatabaseConfig:
    """Tests for DatabaseConfig."""

    def test_from_env_defaults(self):
        """Test default configuration."""
        config = DatabaseConfig()
        assert config.backend == DatabaseBackend.SQLITE
        assert "ag3ntwerk.db" in config.sqlite_path

    def test_connection_string_sqlite(self, tmp_path):
        """Test SQLite connection string."""
        config = DatabaseConfig(sqlite_path=str(tmp_path / "test.db"))
        conn_str = config.connection_string
        assert conn_str.startswith("sqlite:///")

    def test_connection_string_postgresql(self):
        """Test PostgreSQL connection string."""
        config = DatabaseConfig(
            backend=DatabaseBackend.POSTGRESQL,
            pg_host="localhost",
            pg_port=5432,
            pg_database="testdb",
            pg_user="testuser",
            pg_password="testpass",
        )
        conn_str = config.connection_string
        assert "postgresql://" in conn_str
        assert "testuser" in conn_str
        assert "testdb" in conn_str

    def test_safe_connection_string_masks_password(self):
        """Test that safe_connection_string masks the PostgreSQL password."""
        config = DatabaseConfig(
            backend=DatabaseBackend.POSTGRESQL,
            pg_host="db.example.com",
            pg_port=5432,
            pg_database="ag3ntwerk_prod",
            pg_user="admin",
            pg_password="s3cret!@#",
        )
        safe = config.safe_connection_string
        assert "s3cret" not in safe
        assert "***" in safe
        assert "admin" in safe
        assert "db.example.com" in safe
        assert "ag3ntwerk_prod" in safe

    def test_safe_connection_string_sqlite(self, tmp_path):
        """Test that safe_connection_string for SQLite is unchanged."""
        config = DatabaseConfig(sqlite_path=str(tmp_path / "test.db"))
        assert config.safe_connection_string == config.connection_string

    def test_safe_connection_string_empty_password(self):
        """Test safe_connection_string with empty password."""
        config = DatabaseConfig(
            backend=DatabaseBackend.POSTGRESQL,
            pg_password="",
        )
        safe = config.safe_connection_string
        assert "postgresql://" in safe
        assert "***" not in safe

    def test_repr_masks_password(self):
        """Test that repr never exposes database credentials."""
        config = DatabaseConfig(
            backend=DatabaseBackend.POSTGRESQL,
            pg_host="db.example.com",
            pg_port=5432,
            pg_database="ag3ntwerk_prod",
            pg_user="admin",
            pg_password="s3cret!@#",
        )
        representation = repr(config)
        assert "s3cret" not in representation
        assert "***" in representation
        assert "POSTGRESQL" in representation

    def test_repr_sqlite(self, tmp_path):
        """Test repr for SQLite config."""
        config = DatabaseConfig(sqlite_path=str(tmp_path / "test.db"))
        representation = repr(config)
        assert "SQLITE" in representation
        assert "test.db" in representation
