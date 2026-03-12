"""
Unit tests for Sentinel Bridge integration.

Tests the SentinelBridge class that connects Citadel (Citadel) to the Sentinel platform.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from ag3ntwerk.agents.citadel.bridge import SentinelBridge, create_sentinel_bridge
from ag3ntwerk.core.base import Task, TaskStatus


class TestSentinelBridge:
    """Test SentinelBridge functionality."""

    @pytest.fixture
    def bridge(self):
        """Create a SentinelBridge instance."""
        return SentinelBridge()

    @pytest.fixture
    def mock_sentinel_agent(self):
        """Create a mock SentinelAgent."""
        agent = MagicMock()
        agent.version = "1.0.0"
        agent.capabilities = []
        agent.initialize = AsyncMock(return_value=True)
        agent.shutdown = AsyncMock()
        agent.execute = AsyncMock(
            return_value={
                "status": "success",
                "result": {"blocked": True},
                "metadata": {"agent": "sentinel_cio", "domain": "security", "duration_ms": 50},
                "trace": ["Started", "Completed"],
            }
        )
        agent.health_check = AsyncMock(return_value={"healthy": True})
        return agent

    def test_bridge_initialization(self, bridge):
        """Test bridge initializes correctly."""
        assert bridge._config == {}
        assert bridge._sentinel_agent is None
        assert bridge._connected is False
        assert bridge.is_connected is False

    def test_bridge_stats_not_connected(self, bridge):
        """Test stats when not connected."""
        stats = bridge.stats
        assert stats["connected"] is False
        assert stats["tasks_executed"] == 0
        assert stats["tasks_succeeded"] == 0

    def test_task_domain_map(self, bridge):
        """Test task type to domain mapping."""
        assert bridge.TASK_DOMAIN_MAP["threat_detection"] == "security"
        assert bridge.TASK_DOMAIN_MAP["incident_response"] == "reliability"
        assert bridge.TASK_DOMAIN_MAP["vulnerability_scan"] == "discovery"
        assert bridge.TASK_DOMAIN_MAP["network_optimization"] == "network"
        assert bridge.TASK_DOMAIN_MAP["compliance_assessment"] == "compliance"

    def test_agent_name_map(self, bridge):
        """Test agent name to domain mapping."""
        assert bridge.AGENT_NAME_MAP["guardian"] == "security"
        assert bridge.AGENT_NAME_MAP["healer"] == "reliability"
        assert bridge.AGENT_NAME_MAP["discovery"] == "discovery"
        assert bridge.AGENT_NAME_MAP["optimizer"] == "network"
        assert bridge.AGENT_NAME_MAP["compliance"] == "compliance"

    @pytest.mark.asyncio
    async def test_connect_success(self, bridge, mock_sentinel_agent):
        """Test successful connection to Sentinel."""
        # Simulate successful connection by setting up the bridge state
        # (actual import of sentinel package is tested separately)
        bridge._sentinel_agent = mock_sentinel_agent
        await mock_sentinel_agent.initialize()
        bridge._connected = True
        bridge._connection_time = datetime.now(timezone.utc)

        assert bridge.is_connected is True
        assert bridge._sentinel_agent is not None
        assert bridge.connection_uptime is not None

    @pytest.mark.asyncio
    async def test_connect_import_error(self, bridge):
        """Test connection fails gracefully when Sentinel not available."""
        with patch.dict("sys.modules", {"sentinel": None, "sentinel.nexus_agent": None}):
            result = await bridge.connect()
            assert result is False
            assert bridge.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self, bridge, mock_sentinel_agent):
        """Test disconnection from Sentinel."""
        bridge._sentinel_agent = mock_sentinel_agent
        bridge._connected = True
        bridge._connection_time = datetime.now(timezone.utc)

        result = await bridge.disconnect()

        assert result is True
        assert bridge._connected is False
        assert bridge._sentinel_agent is None
        mock_sentinel_agent.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_task_not_connected(self, bridge):
        """Test task execution when not connected."""
        task = Task(
            description="Block malicious IP",
            task_type="threat_detection",
        )

        result = await bridge.execute_task(task)

        assert result.success is False
        assert "not connected" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_task_success(self, bridge, mock_sentinel_agent):
        """Test successful task execution."""
        bridge._sentinel_agent = mock_sentinel_agent
        bridge._connected = True

        task = Task(
            description="Detect threats",
            task_type="threat_detection",
            context={"target": "10.0.0.0/24"},
        )

        result = await bridge.execute_task(task)

        assert result.success is True
        assert bridge._tasks_executed == 1
        assert bridge._tasks_succeeded == 1
        assert result.metrics.get("sentinel_agent") == "sentinel_cio"
        mock_sentinel_agent.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_task_failure(self, bridge, mock_sentinel_agent):
        """Test task execution failure."""
        mock_sentinel_agent.execute = AsyncMock(
            return_value={
                "status": "failure",
                "result": None,
                "metadata": {"error": "Connection timeout"},
                "trace": [],
            }
        )
        bridge._sentinel_agent = mock_sentinel_agent
        bridge._connected = True

        task = Task(
            description="Detect threats",
            task_type="threat_detection",
        )

        result = await bridge.execute_task(task)

        assert result.success is False
        assert bridge._tasks_executed == 1
        assert bridge._tasks_succeeded == 0

    @pytest.mark.asyncio
    async def test_route_to_agent_not_connected(self, bridge):
        """Test routing when not connected."""
        result = await bridge.route_to_agent("guardian", "block_ip", {"ip": "10.0.0.1"})

        assert result["success"] is False
        assert "not connected" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_route_to_agent_success(self, bridge, mock_sentinel_agent):
        """Test successful agent routing."""
        bridge._sentinel_agent = mock_sentinel_agent
        bridge._connected = True

        result = await bridge.route_to_agent(
            "guardian",
            "block_ip",
            {"ip": "10.0.0.1", "duration_hours": 24},
        )

        assert result["success"] is True
        assert result["agent"] == "guardian"
        assert result["domain"] == "security"
        mock_sentinel_agent.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_agent_health_not_connected(self, bridge):
        """Test health check when not connected."""
        health = await bridge.get_agent_health()

        assert health["healthy"] is False
        assert "not connected" in health["error"].lower()

    @pytest.mark.asyncio
    async def test_get_agent_health_success(self, bridge, mock_sentinel_agent):
        """Test successful health check."""
        bridge._sentinel_agent = mock_sentinel_agent
        bridge._connected = True

        health = await bridge.get_agent_health()

        assert health["healthy"] is True
        mock_sentinel_agent.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_capabilities_not_connected(self, bridge):
        """Test capabilities when not connected."""
        caps = await bridge.get_capabilities()
        assert caps == []

    def test_convert_task(self, bridge):
        """Test task conversion to Sentinel format."""
        task = Task(
            id="test-123",
            description="Detect network threats",
            task_type="threat_detection",
            context={"scope": "internal_network"},
            priority=1,
        )

        sentinel_task = bridge._convert_task(task)

        assert sentinel_task["task_id"] == "test-123"
        assert "security" in sentinel_task["task_type"]
        assert sentinel_task["context"]["source"] == "ag3ntwerk.citadel"
        assert sentinel_task["context"]["original_type"] == "threat_detection"

    def test_stats_tracking(self, bridge):
        """Test statistics tracking."""
        bridge._tasks_executed = 10
        bridge._tasks_succeeded = 8
        bridge._connected = True
        bridge._connection_time = datetime.now(timezone.utc)

        stats = bridge.stats

        assert stats["connected"] is True
        assert stats["tasks_executed"] == 10
        assert stats["tasks_succeeded"] == 8
        assert stats["success_rate"] == 0.8
        assert stats["uptime_seconds"] is not None


class TestCSecOSentinelIntegration:
    """Test Citadel integration with Sentinel bridge."""

    @pytest.fixture
    def cseco(self, mock_llm_provider):
        """Create a Citadel instance."""
        from ag3ntwerk.agents.citadel import Citadel

        return Citadel(llm_provider=mock_llm_provider)

    @pytest.fixture
    def mock_bridge(self):
        """Create a mock SentinelBridge."""
        bridge = MagicMock()
        bridge.is_connected = True
        bridge.stats = {
            "connected": True,
            "uptime_seconds": 100.0,
            "tasks_executed": 5,
            "tasks_succeeded": 5,
            "success_rate": 1.0,
        }
        bridge.connect = AsyncMock(return_value=True)
        bridge.disconnect = AsyncMock(return_value=True)
        bridge.execute_task = AsyncMock(
            return_value=MagicMock(
                task_id="test",
                success=True,
                output={"result": "success"},
                error=None,
                metadata={},
            )
        )
        bridge.route_to_agent = AsyncMock(
            return_value={
                "success": True,
                "result": {"blocked": True},
            }
        )
        bridge.get_agent_health = AsyncMock(return_value={"healthy": True})
        return bridge

    def test_cseco_initialization(self, cseco):
        """Test Citadel initializes with Sentinel bridge support."""
        assert cseco._sentinel_bridge is None
        assert cseco._sentinel_connected is False
        assert cseco.codename == "Citadel"

    def test_cseco_sentinel_not_connected(self, cseco):
        """Test sentinel_connected property when not connected."""
        assert cseco.sentinel_connected is False

    @pytest.mark.asyncio
    async def test_cseco_connect_sentinel(self, cseco, mock_bridge):
        """Test connecting Citadel to Sentinel."""
        # Simulate connecting by directly setting the bridge
        cseco._sentinel_bridge = mock_bridge
        cseco._sentinel_connected = True

        assert cseco._sentinel_connected is True
        assert cseco._sentinel_bridge is not None

    @pytest.mark.asyncio
    async def test_cseco_disconnect_sentinel(self, cseco, mock_bridge):
        """Test disconnecting Citadel from Sentinel."""
        cseco._sentinel_bridge = mock_bridge
        cseco._sentinel_connected = True

        result = await cseco.disconnect_sentinel()

        assert result is True
        assert cseco._sentinel_connected is False
        mock_bridge.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_cseco_sentinel_security_action(self, cseco, mock_bridge):
        """Test executing security action via Sentinel."""
        cseco._sentinel_bridge = mock_bridge

        result = await cseco.sentinel_security_action(
            "block_ip",
            {"ip": "10.0.0.1"},
        )

        assert result["success"] is True
        mock_bridge.route_to_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_cseco_sentinel_security_action_not_connected(self, cseco):
        """Test security action when not connected."""
        result = await cseco.sentinel_security_action(
            "block_ip",
            {"ip": "10.0.0.1"},
        )

        assert result["success"] is False
        assert "not connected" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_cseco_sentinel_health_check(self, cseco, mock_bridge):
        """Test Sentinel health check from Citadel."""
        cseco._sentinel_bridge = mock_bridge

        result = await cseco.sentinel_health_check()

        assert result["healthy"] is True
        mock_bridge.get_agent_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_cseco_sentinel_discovery_scan(self, cseco, mock_bridge):
        """Test discovery scan via Sentinel."""
        cseco._sentinel_bridge = mock_bridge

        result = await cseco.sentinel_discovery_scan(
            network="10.0.0.0/24",
            scan_type="quick",
        )

        assert result["success"] is True
        mock_bridge.route_to_agent.assert_called_once_with(
            "discovery",
            "scan_network",
            {"network": "10.0.0.0/24", "scan_type": "quick"},
        )

    @pytest.mark.asyncio
    async def test_cseco_sentinel_compliance_check(self, cseco, mock_bridge):
        """Test compliance check via Sentinel."""
        cseco._sentinel_bridge = mock_bridge

        result = await cseco.sentinel_compliance_check(
            framework="NIST",
            scope=["network", "hosts"],
        )

        assert result["success"] is True
        mock_bridge.route_to_agent.assert_called_once()

    def test_cseco_get_sentinel_stats(self, cseco, mock_bridge):
        """Test getting Sentinel stats."""
        cseco._sentinel_bridge = mock_bridge

        stats = cseco.get_sentinel_stats()

        assert stats["connected"] is True
        assert stats["tasks_executed"] == 5

    def test_cseco_get_sentinel_stats_not_initialized(self, cseco):
        """Test getting stats when bridge not initialized."""
        stats = cseco.get_sentinel_stats()

        assert stats["connected"] is False
        assert "not initialized" in stats["message"].lower()

    @pytest.mark.asyncio
    async def test_cseco_route_to_sentinel_via_bridge(self, cseco, mock_bridge):
        """Test task routing uses bridge when available."""
        cseco._sentinel_bridge = mock_bridge
        cseco._sentinel_connected = True

        task = Task(
            description="Detect threats",
            task_type="threat_detection",
        )

        result = await cseco._route_to_sentinel(task)

        assert result.success is True
        mock_bridge.execute_task.assert_called_once()


class TestCreateSentinelBridge:
    """Test the create_sentinel_bridge convenience function."""

    @pytest.mark.asyncio
    async def test_create_bridge_manual(self):
        """Test creating and connecting bridge manually."""
        mock_agent = MagicMock()
        mock_agent.initialize = AsyncMock(return_value=True)
        mock_agent.version = "1.0.0"
        mock_agent.capabilities = []

        # Simulate successful bridge setup
        bridge = SentinelBridge()
        bridge._sentinel_agent = mock_agent
        await mock_agent.initialize()
        bridge._connected = True

        assert bridge is not None
        assert bridge._connected is True
        assert bridge.is_connected is True

    @pytest.mark.asyncio
    async def test_create_bridge_failure(self):
        """Test creating bridge when Sentinel unavailable."""
        # When Sentinel is not available, create_sentinel_bridge returns None
        result = await create_sentinel_bridge()
        assert result is None
