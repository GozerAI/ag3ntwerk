"""
Unit tests for ag3ntwerk MCP Server.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.mcp.server import AgentWerkMCPServer
from ag3ntwerk.orchestration.registry import AgentRegistry
from ag3ntwerk.core.base import Task, TaskResult


class TestAgentWerkMCPServerInit:
    """Tests for AgentWerkMCPServer initialization."""

    def test_server_creation(self):
        """Test MCP server creation."""
        server = AgentWerkMCPServer()

        assert server.registry is not None
        assert server.orchestrator is not None
        assert server.server is not None

    def test_server_with_provider(self):
        """Test server creation with LLM provider."""
        mock_provider = MagicMock()
        server = AgentWerkMCPServer(llm_provider=mock_provider)

        assert server.llm_provider == mock_provider
        assert server.registry.llm_provider == mock_provider

    def test_server_with_registry(self):
        """Test server creation with custom registry."""
        mock_registry = MagicMock(spec=AgentRegistry)
        server = AgentWerkMCPServer(registry=mock_registry)

        assert server.registry == mock_registry

    def test_workflows_registered(self):
        """Test that standard workflows are registered."""
        server = AgentWerkMCPServer()

        workflows = server.orchestrator.list_workflows()
        workflow_names = [w["name"] for w in workflows]

        assert "product_launch" in workflow_names
        assert "incident_response" in workflow_names
        assert "budget_approval" in workflow_names
        assert "feature_release" in workflow_names


class TestMCPServerTools:
    """Tests for MCP server tool functionality."""

    @pytest.fixture
    def server(self):
        """Create server with mocked components."""
        mock_provider = MagicMock()
        return AgentWerkMCPServer(llm_provider=mock_provider)

    def test_tools_registered(self, server):
        """Test that tools are registered on the server."""
        # The server should have tools registered
        # Tools are registered via decorators, so we can check the server object
        assert server.server is not None


class TestExecutiveListingTools:
    """Tests for agent listing functionality."""

    @pytest.fixture
    def mock_server(self):
        """Create server with mock registry."""
        mock_provider = MagicMock()
        server = AgentWerkMCPServer(llm_provider=mock_provider)
        return server

    def test_list_agents_returns_all(self, mock_server):
        """Test that list_agents includes all agents."""
        agents = mock_server.registry.list_agents()

        # Should have multiple agents
        assert len(agents) > 0

        # Should have expected structure
        for exec_info in agents:
            assert "code" in exec_info
            assert "codename" in exec_info
            assert "available" in exec_info

    def test_get_available_codes(self, mock_server):
        """Test getting available agent codes."""
        codes = mock_server.registry.get_available_codes()

        # Should include implemented agents
        assert "Blueprint" in codes
        assert "Keystone" in codes
        assert "Echo" in codes


class TestTaskExecutionTools:
    """Tests for task execution tool functionality."""

    @pytest.fixture
    def mock_server(self):
        """Create server with mock provider."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Test response")
        return AgentWerkMCPServer(llm_provider=mock_provider)

    @pytest.mark.asyncio
    async def test_execute_task_with_executive(self, mock_server):
        """Test executing task with specific agent."""
        # Get Blueprint from registry
        cpo = mock_server.registry.get("Blueprint")
        assert cpo is not None

        # Execute a task
        task = Task(
            description="Create product spec",
            task_type="product_spec",
            context={"product_name": "TestProduct"},
        )

        result = await cpo.execute(task)

        assert result.task_id == task.id

    @pytest.mark.asyncio
    async def test_execute_task_unknown_executive(self, mock_server):
        """Test executing task with unknown agent returns None."""
        agent = mock_server.registry.get("FAKE")
        assert agent is None


class TestWorkflowTools:
    """Tests for workflow tool functionality."""

    @pytest.fixture
    def mock_server(self):
        """Create server instance."""
        mock_provider = MagicMock()
        return AgentWerkMCPServer(llm_provider=mock_provider)

    def test_list_workflows(self, mock_server):
        """Test listing available workflows."""
        workflows = mock_server.orchestrator.list_workflows()

        assert len(workflows) == 4

        names = [w["name"] for w in workflows]
        assert "product_launch" in names
        assert "incident_response" in names
        assert "budget_approval" in names
        assert "feature_release" in names

    def test_workflow_has_description(self, mock_server):
        """Test that workflows have descriptions."""
        workflows = mock_server.orchestrator.list_workflows()

        for wf in workflows:
            assert "description" in wf
            assert len(wf["description"]) > 0


class TestSystemStatusTools:
    """Tests for system status tool functionality."""

    @pytest.fixture
    def mock_server(self):
        """Create server instance."""
        mock_provider = MagicMock()
        mock_provider.is_connected = True
        return AgentWerkMCPServer(llm_provider=mock_provider)

    def test_system_status_structure(self, mock_server):
        """Test system status has expected structure."""
        agents = mock_server.registry.list_agents()
        available = [e for e in agents if e.get("available")]

        assert len(agents) > 0
        assert len(available) > 0

    def test_llm_provider_status(self, mock_server):
        """Test LLM provider status is reported."""
        assert mock_server.llm_provider is not None
        assert mock_server.llm_provider.is_connected is True


class TestCapabilityTools:
    """Tests for capability tool functionality."""

    @pytest.fixture
    def mock_server(self):
        """Create server instance."""
        mock_provider = MagicMock()
        return AgentWerkMCPServer(llm_provider=mock_provider)

    def test_get_agent_capabilities(self, mock_server):
        """Test getting capabilities for a specific agent."""
        cpo = mock_server.registry.get("Blueprint")
        assert cpo is not None

        capabilities = getattr(cpo, "capabilities", [])
        assert len(capabilities) > 0
        assert "product_spec" in capabilities or "feature_prioritization" in capabilities

    def test_get_all_capabilities(self, mock_server):
        """Test getting capabilities for all agents."""
        all_caps = {}

        for code in mock_server.registry.get_available_codes():
            agent = mock_server.registry.get(code)
            if agent:
                all_caps[code] = getattr(agent, "capabilities", [])

        assert len(all_caps) > 0
        assert "Blueprint" in all_caps
        assert "Keystone" in all_caps


class TestFindExecutiveForTask:
    """Tests for finding agents by task type."""

    @pytest.fixture
    def mock_server(self):
        """Create server instance."""
        mock_provider = MagicMock()
        return AgentWerkMCPServer(llm_provider=mock_provider)

    def test_find_executive_for_cost_analysis(self, mock_server):
        """Test finding agent for cost_analysis."""
        agents = mock_server.registry.get_by_capability("cost_analysis")

        codes = [e.code for e in agents]
        assert "Keystone" in codes

    def test_find_executive_for_campaign_creation(self, mock_server):
        """Test finding agent for campaign_creation."""
        agents = mock_server.registry.get_by_capability("campaign_creation")

        codes = [e.code for e in agents]
        assert "Echo" in codes

    def test_find_executive_for_product_spec(self, mock_server):
        """Test finding agent for product_spec."""
        agents = mock_server.registry.get_by_capability("product_spec")

        codes = [e.code for e in agents]
        assert "Blueprint" in codes

    def test_find_executive_for_unknown_task(self, mock_server):
        """Test finding agent for unknown task type."""
        agents = mock_server.registry.get_by_capability("totally_made_up_task")

        assert len(agents) == 0


class TestRegistryWithMCPServer:
    """Tests for registry integration with MCP server."""

    def test_registry_contains_cmo(self):
        """Test that Echo is in the registry."""
        server = AgentWerkMCPServer()

        assert "Echo" in server.registry
        cmo = server.registry.get("Echo")
        assert cmo is not None
        assert cmo.codename == "Echo"

    def test_registry_contains_all_standard_executives(self):
        """Test registry has all standard agents."""
        server = AgentWerkMCPServer()

        expected_codes = [
            "Nexus",
            "Forge",
            "Keystone",
            "Echo",
            "Sentinel",
            "Compass",
            "Axiom",
            "Index",
            "Aegis",
            "Accord",
            "Citadel",
            "Foundry",
            "Blueprint",
            "Beacon",
            "Vector",
        ]

        for code in expected_codes:
            assert code in server.registry, f"Missing agent: {code}"


class TestMCPHandlers:
    """Tests for MCP server handler methods."""

    @pytest.fixture
    def mock_server(self):
        """Create server with mock provider."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Test response")
        mock_provider.is_connected = True
        return AgentWerkMCPServer(llm_provider=mock_provider)

    @pytest.mark.asyncio
    async def test_handle_list_agents(self, mock_server):
        """Test _handle_list_agents handler."""
        result = await mock_server._handle_list_agents({})

        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 16  # All agents including Overwatch

        # Check structure
        for exec_info in data:
            assert "code" in exec_info
            assert "codename" in exec_info

    @pytest.mark.asyncio
    async def test_handle_get_agent_found(self, mock_server):
        """Test _handle_get_agent for existing agent."""
        result = await mock_server._handle_get_agent({"code": "Blueprint"})

        data = json.loads(result)
        assert data["code"] == "Blueprint"
        assert data["codename"] == "Blueprint"
        assert "capabilities" in data

    @pytest.mark.asyncio
    async def test_handle_get_agent_not_found(self, mock_server):
        """Test _handle_get_agent for non-existent agent."""
        result = await mock_server._handle_get_agent({"code": "FAKE"})

        data = json.loads(result)
        assert "error" in data
        assert "FAKE" in data["error"]
        assert "available_codes" in data

    @pytest.mark.asyncio
    async def test_handle_find_executive(self, mock_server):
        """Test _handle_find_executive handler."""
        result = await mock_server._handle_find_executive({"task_type": "cost_analysis"})

        data = json.loads(result)
        assert isinstance(data, list)
        codes = [e["code"] for e in data]
        assert "Keystone" in codes

    @pytest.mark.asyncio
    async def test_handle_find_executive_not_found(self, mock_server):
        """Test _handle_find_executive for unknown task type."""
        result = await mock_server._handle_find_executive({"task_type": "unknown_task"})

        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_handle_execute_task_success(self, mock_server):
        """Test _handle_execute_task success case."""
        args = {
            "agent_code": "Blueprint",
            "description": "Create product spec",
            "task_type": "product_spec",
            "context": "{}",
            "priority": "medium",
        }

        result = await mock_server._handle_execute_task(args)

        data = json.loads(result)
        assert "task_id" in data
        assert data["agent"] == "Blueprint"

    @pytest.mark.asyncio
    async def test_handle_execute_task_executive_not_found(self, mock_server):
        """Test _handle_execute_task with unknown agent."""
        args = {
            "agent_code": "FAKE",
            "description": "Test task",
            "task_type": "test",
        }

        result = await mock_server._handle_execute_task(args)

        data = json.loads(result)
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_handle_execute_task_invalid_context(self, mock_server):
        """Test _handle_execute_task with invalid JSON context."""
        args = {
            "agent_code": "Blueprint",
            "description": "Test task",
            "task_type": "product_spec",
            "context": "not valid json",
        }

        result = await mock_server._handle_execute_task(args)

        # Should still work with empty context fallback
        data = json.loads(result)
        assert "task_id" in data

    @pytest.mark.asyncio
    async def test_handle_route_task_success(self, mock_server):
        """Test _handle_route_task success case."""
        args = {
            "description": "Analyze budget",
            "task_type": "cost_analysis",
            "context": "{}",
            "priority": "high",
        }

        result = await mock_server._handle_route_task(args)

        data = json.loads(result)
        assert "task_id" in data
        assert data["routed_via"] == "Nexus"

    @pytest.mark.asyncio
    async def test_handle_list_workflows(self, mock_server):
        """Test _handle_list_workflows handler."""
        result = await mock_server._handle_list_workflows({})

        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 4

        names = [w["name"] for w in data]
        assert "product_launch" in names

    @pytest.mark.asyncio
    async def test_handle_run_workflow_invalid_params(self, mock_server):
        """Test _handle_run_workflow with invalid JSON params."""
        args = {
            "workflow_name": "product_launch",
            "params": "not valid json",
        }

        result = await mock_server._handle_run_workflow(args)

        data = json.loads(result)
        assert data["success"] is False
        assert "Invalid JSON" in data["error"]

    @pytest.mark.asyncio
    async def test_handle_run_workflow_unknown(self, mock_server):
        """Test _handle_run_workflow with unknown workflow."""
        args = {
            "workflow_name": "unknown_workflow",
            "params": "{}",
        }

        result = await mock_server._handle_run_workflow(args)

        data = json.loads(result)
        assert data["success"] is False
        assert "available_workflows" in data

    @pytest.mark.asyncio
    async def test_handle_system_status(self, mock_server):
        """Test _handle_system_status handler."""
        result = await mock_server._handle_system_status({})

        data = json.loads(result)
        assert "total_executives" in data
        assert "available_executives" in data
        assert "llm_provider" in data
        assert "registered_workflows" in data
        assert data["total_executives"] == 16  # Including Overwatch

    @pytest.mark.asyncio
    async def test_handle_capabilities_specific(self, mock_server):
        """Test _handle_capabilities for specific agent."""
        result = await mock_server._handle_capabilities({"agent_code": "Keystone"})

        data = json.loads(result)
        assert "Keystone" in data
        assert "cost_analysis" in data["Keystone"]

    @pytest.mark.asyncio
    async def test_handle_capabilities_all(self, mock_server):
        """Test _handle_capabilities for all agents."""
        result = await mock_server._handle_capabilities({})

        data = json.loads(result)
        assert "Blueprint" in data
        assert "Keystone" in data
        assert "Echo" in data

    @pytest.mark.asyncio
    async def test_handle_capabilities_not_found(self, mock_server):
        """Test _handle_capabilities for non-existent agent."""
        result = await mock_server._handle_capabilities({"agent_code": "FAKE"})

        data = json.loads(result)
        assert "error" in data

    def test_get_handler_returns_correct_handler(self, mock_server):
        """Test _get_handler returns correct handler for each tool."""
        tool_handlers = {
            "ag3ntwerk_list_agents": mock_server._handle_list_agents,
            "ag3ntwerk_get_agent": mock_server._handle_get_agent,
            "agentwerk_find_executive_for_task": mock_server._handle_find_executive,
            "agentwerk_execute_task": mock_server._handle_execute_task,
            "agentwerk_route_task": mock_server._handle_route_task,
            "agentwerk_list_workflows": mock_server._handle_list_workflows,
            "agentwerk_run_workflow": mock_server._handle_run_workflow,
            "agentwerk_system_status": mock_server._handle_system_status,
            "agentwerk_agent_capabilities": mock_server._handle_capabilities,
        }

        for tool_name, expected_handler in tool_handlers.items():
            handler = mock_server._get_handler(tool_name)
            assert handler == expected_handler, f"Handler mismatch for {tool_name}"

    def test_get_handler_unknown_tool(self, mock_server):
        """Test _get_handler returns None for unknown tool."""
        handler = mock_server._get_handler("unknown_tool")
        assert handler is None

    def test_tools_constant(self, mock_server):
        """Test TOOLS constant has all expected tools."""
        tool_names = [t.name for t in mock_server.TOOLS]

        expected_tools = [
            "ag3ntwerk_list_agents",
            "ag3ntwerk_get_agent",
            "agentwerk_find_executive_for_task",
            "agentwerk_execute_task",
            "agentwerk_route_task",
            "agentwerk_list_workflows",
            "agentwerk_run_workflow",
            "agentwerk_system_status",
            "agentwerk_agent_capabilities",
        ]

        for tool in expected_tools:
            assert tool in tool_names, f"Missing tool: {tool}"


class TestMCPServerPriorityMapping:
    """Tests for priority mapping in task execution."""

    @pytest.fixture
    def mock_server(self):
        """Create server with mock provider."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Test response")
        return AgentWerkMCPServer(llm_provider=mock_provider)

    @pytest.mark.asyncio
    async def test_priority_low(self, mock_server):
        """Test low priority mapping."""
        args = {
            "agent_code": "Blueprint",
            "description": "Test",
            "task_type": "product_spec",
            "priority": "low",
        }
        result = await mock_server._handle_execute_task(args)
        data = json.loads(result)
        assert "task_id" in data

    @pytest.mark.asyncio
    async def test_priority_critical(self, mock_server):
        """Test critical priority mapping."""
        args = {
            "agent_code": "Blueprint",
            "description": "Test",
            "task_type": "product_spec",
            "priority": "critical",
        }
        result = await mock_server._handle_execute_task(args)
        data = json.loads(result)
        assert "task_id" in data

    @pytest.mark.asyncio
    async def test_priority_default(self, mock_server):
        """Test default priority when not specified."""
        args = {
            "agent_code": "Blueprint",
            "description": "Test",
            "task_type": "product_spec",
        }
        result = await mock_server._handle_execute_task(args)
        data = json.loads(result)
        assert "task_id" in data
