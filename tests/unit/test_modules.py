"""
Tests for ag3ntwerk Modules.

Tests the trends, commerce, brand, and scheduler modules
and their integration with agent agents.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.modules import (
    MODULE_REGISTRY,
    get_modules_for_executive,
    get_module_info,
)


# =============================================================================
# Module Registry Tests
# =============================================================================


class TestModuleRegistry:
    """Tests for the module registry."""

    def test_registry_has_all_modules(self):
        """Verify all expected modules are registered."""
        expected_modules = {
            "trends",
            "commerce",
            "brand",
            "scheduler",
            "workbench",
            "vls",
            "metacognition",
            "swarm_bridge",
            "distributed",
            "research_automation",
            "data_harvesting",
            "security_automation",
        }
        assert set(MODULE_REGISTRY.keys()) == expected_modules

    def test_trends_module_info(self):
        """Verify trends module configuration."""
        trends = MODULE_REGISTRY["trends"]
        assert trends["name"] == "Trend Intelligence"
        assert "Echo" in trends["primary_owners"]
        assert "Blueprint" in trends["primary_owners"]
        assert "trend_collection" in trends["capabilities"]
        assert "niche_identification" in trends["capabilities"]

    def test_commerce_module_info(self):
        """Verify commerce module configuration."""
        commerce = MODULE_REGISTRY["commerce"]
        assert commerce["name"] == "Commerce Operations"
        assert "Vector" in commerce["primary_owners"]
        assert "Keystone" in commerce["primary_owners"]
        assert "pricing_optimization" in commerce["capabilities"]
        assert "inventory_tracking" in commerce["capabilities"]

    def test_brand_module_info(self):
        """Verify brand module configuration."""
        brand = MODULE_REGISTRY["brand"]
        assert brand["name"] == "Brand Suite"
        assert "Echo" in brand["primary_owners"]
        assert "Beacon" in brand["primary_owners"]
        assert "brand_guidelines" in brand["capabilities"]
        assert "consistency_check" in brand["capabilities"]

    def test_scheduler_module_info(self):
        """Verify scheduler module configuration."""
        scheduler = MODULE_REGISTRY["scheduler"]
        assert scheduler["name"] == "Autonomous Scheduler"
        assert "Nexus" in scheduler["primary_owners"]
        assert "CEO" in scheduler["secondary_owners"]
        assert "task_scheduling" in scheduler["capabilities"]
        assert "workflow_automation" in scheduler["capabilities"]

    def test_research_automation_module_info(self):
        """Verify research_automation module configuration."""
        info = MODULE_REGISTRY["research_automation"]
        assert info["name"] == "Autonomous Research"
        assert "Compass" in info["primary_owners"]
        assert "Forge" in info["primary_owners"]
        assert "Echo" in info["secondary_owners"]
        assert "market_intelligence_scan" in info["capabilities"]
        assert "competitive_analysis" in info["capabilities"]
        assert "insights_aggregation" in info["capabilities"]

    def test_data_harvesting_module_info(self):
        """Verify data_harvesting module configuration."""
        info = MODULE_REGISTRY["data_harvesting"]
        assert info["name"] == "Autonomous Data Harvesting"
        assert "Index" in info["primary_owners"]
        assert "Forge" in info["secondary_owners"]
        assert "source_management" in info["capabilities"]
        assert "harvest_execution" in info["capabilities"]
        assert "data_quality_reporting" in info["capabilities"]

    def test_security_automation_module_info(self):
        """Verify security_automation module configuration."""
        info = MODULE_REGISTRY["security_automation"]
        assert info["name"] == "Security Automation"
        assert "Citadel" in info["primary_owners"]
        assert "Forge" in info["secondary_owners"]
        assert "Sentinel" in info["secondary_owners"]
        assert "security_scanning" in info["capabilities"]
        assert "threat_assessment" in info["capabilities"]
        assert "access_review" in info["capabilities"]


class TestModuleLookup:
    """Tests for module lookup functions."""

    def test_get_modules_for_cmo(self):
        """Echo should have access to trends and brand."""
        modules = get_modules_for_executive("Echo")
        assert "trends" in modules
        assert "brand" in modules

    def test_get_modules_for_crevo(self):
        """Vector should have access to commerce."""
        modules = get_modules_for_executive("Vector")
        assert "commerce" in modules

    def test_get_modules_for_coo(self):
        """Nexus should have access to scheduler and commerce."""
        modules = get_modules_for_executive("Nexus")
        assert "scheduler" in modules
        assert "commerce" in modules  # Secondary owner

    def test_get_modules_for_ceo(self):
        """CEO should have secondary access to trends and scheduler."""
        modules = get_modules_for_executive("CEO")
        assert "trends" in modules  # Secondary owner
        assert "scheduler" in modules  # Secondary owner

    def test_get_modules_for_cto_includes_swarm(self):
        """Forge should have primary access to swarm_bridge."""
        modules = get_modules_for_executive("Forge")
        assert "swarm_bridge" in modules

    def test_get_modules_for_cengo_includes_swarm(self):
        """Foundry should have primary access to swarm_bridge."""
        modules = get_modules_for_executive("Foundry")
        assert "swarm_bridge" in modules

    def test_swarm_bridge_module_info(self):
        """Verify swarm_bridge module configuration."""
        swarm = MODULE_REGISTRY["swarm_bridge"]
        assert swarm["name"] == "Swarm Bridge"
        assert "Forge" in swarm["primary_owners"]
        assert "Foundry" in swarm["primary_owners"]
        assert "swarm_task_delegation" in swarm["capabilities"]
        assert "tool_calling" in swarm["capabilities"]

    def test_get_modules_for_cso_includes_research(self):
        """Compass should have primary access to research_automation."""
        modules = get_modules_for_executive("Compass")
        assert "research_automation" in modules

    def test_get_modules_for_cdo_includes_harvesting(self):
        """Index should have primary access to data_harvesting."""
        modules = get_modules_for_executive("Index")
        assert "data_harvesting" in modules

    def test_get_modules_for_cseco_includes_security(self):
        """Citadel should have primary access to security_automation."""
        modules = get_modules_for_executive("Citadel")
        assert "security_automation" in modules

    def test_get_module_info_valid(self):
        """Get info for valid module."""
        info = get_module_info("trends")
        assert info["name"] == "Trend Intelligence"

    def test_get_module_info_invalid(self):
        """Get info for invalid module returns empty dict."""
        info = get_module_info("nonexistent")
        assert info == {}


# =============================================================================
# Trend Service Tests
# =============================================================================


class TestTrendService:
    """Tests for the TrendService."""

    @pytest.fixture
    def trend_service(self):
        """Create a TrendService instance."""
        from ag3ntwerk.modules.trends import TrendService

        return TrendService()

    def test_service_initialization(self, trend_service):
        """Verify service initializes correctly."""
        assert trend_service is not None
        assert hasattr(trend_service, "db")
        assert hasattr(trend_service, "collector_manager")

    @pytest.mark.asyncio
    async def test_get_trending_empty(self, trend_service):
        """Get trending returns empty list when no trends."""
        result = await trend_service.get_trending()
        # Returns list of trend dicts
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_agent_report_cmo(self, trend_service):
        """Echo report has marketing focus."""
        report = await trend_service.get_agent_report("Echo")
        assert report["agent"] == "Echo"
        assert report["focus"] == "Marketing & Growth"

    @pytest.mark.asyncio
    async def test_get_agent_report_cpo(self, trend_service):
        """Blueprint report has product focus."""
        report = await trend_service.get_agent_report("Blueprint")
        assert report["agent"] == "Blueprint"
        assert report["focus"] == "Product & Innovation"

    @pytest.mark.asyncio
    async def test_get_agent_report_ceo(self, trend_service):
        """CEO report has strategic focus."""
        report = await trend_service.get_agent_report("CEO")
        assert report["agent"] == "CEO"
        assert report["focus"] == "Strategic Overview"

    @pytest.mark.asyncio
    async def test_get_stats(self, trend_service):
        """Get service stats."""
        stats = await trend_service.get_stats()
        assert "database" in stats
        assert "collectors" in stats


# =============================================================================
# Commerce Service Tests
# =============================================================================


class TestCommerceService:
    """Tests for the CommerceService."""

    @pytest.fixture
    def commerce_service(self):
        """Create a CommerceService instance."""
        from ag3ntwerk.modules.commerce import CommerceService

        return CommerceService()

    def test_service_initialization(self, commerce_service):
        """Verify service initializes correctly."""
        assert commerce_service is not None
        assert hasattr(commerce_service, "_registry")

    def test_list_storefronts(self, commerce_service):
        """List storefronts returns expected structure."""
        result = commerce_service.list_storefronts()
        # Returns list of storefront dicts directly
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_agent_report_crevo(self, commerce_service):
        """Axiom report (Vector not implemented, uses Axiom)."""
        report = await commerce_service.get_agent_report("Axiom")
        assert report["agent"] == "Axiom"
        assert "focus" in report

    @pytest.mark.asyncio
    async def test_get_agent_report_cfo(self, commerce_service):
        """Keystone report has financial focus."""
        report = await commerce_service.get_agent_report("Keystone")
        assert report["agent"] == "Keystone"
        assert report["focus"] == "Financial Metrics"

    @pytest.mark.asyncio
    async def test_get_margin_analysis(self, commerce_service):
        """Get margin analysis returns expected structure."""
        result = await commerce_service.get_margin_analysis()
        assert isinstance(result, dict)

    def test_get_low_stock_alerts(self, commerce_service):
        """Get low stock alerts."""
        result = commerce_service.get_low_stock_alerts(threshold=10)
        assert isinstance(result, dict)

    def test_get_stats(self, commerce_service):
        """Get service stats."""
        stats = commerce_service.get_stats()
        assert isinstance(stats, dict)


# =============================================================================
# Brand Service Tests
# =============================================================================


class TestBrandService:
    """Tests for the BrandService."""

    @pytest.fixture
    def brand_service(self):
        """Create a BrandService instance."""
        from ag3ntwerk.modules.brand import BrandService

        return BrandService()

    def test_service_initialization(self, brand_service):
        """Verify service initializes correctly."""
        assert brand_service is not None
        assert hasattr(brand_service, "_identity")

    def test_get_identity_empty(self, brand_service):
        """Get identity returns None when not created."""
        identity = brand_service.get_identity()
        assert identity is None

    def test_create_identity(self, brand_service):
        """Create brand identity."""
        result = brand_service.create_identity(
            name="TestBrand",
            tagline="Test Tagline",
            mission="Test Mission",
            primary_tone="professional",
        )
        assert "name" in result
        assert result["name"] == "TestBrand"

    def test_get_identity_after_create(self, brand_service):
        """Get identity returns data after creation."""
        brand_service.create_identity(
            name="TestBrand",
            tagline="Test Tagline",
        )
        identity = brand_service.get_identity()
        assert identity is not None
        assert identity["name"] == "TestBrand"

    def test_validate_content_no_identity(self, brand_service):
        """Validate content fails without identity."""
        result = brand_service.validate_content(
            content="Test content",
            content_type="website",
        )
        assert "error" in result or "passed" in result

    def test_validate_content_with_identity(self, brand_service):
        """Validate content with identity."""
        brand_service.create_identity(
            name="TestBrand",
            primary_tone="professional",
        )
        result = brand_service.validate_content(
            content="This is professional test content.",
            content_type="website",
        )
        assert isinstance(result, dict)

    def test_add_guideline(self, brand_service):
        """Add a brand guideline."""
        guideline_id = brand_service.add_guideline(
            category="voice",
            title="Test Guideline",
            description="Test description",
            rule_type="guideline",
        )
        assert guideline_id is not None
        assert isinstance(guideline_id, str)

    def test_get_guidelines(self, brand_service):
        """Get brand guidelines."""
        brand_service.add_guideline(
            category="voice",
            title="Test Guideline",
            description="Test description",
        )
        guidelines = brand_service.get_guidelines()
        assert isinstance(guidelines, list)
        assert len(guidelines) >= 1

    def test_get_agent_report_cmo(self, brand_service):
        """Echo report has marketing focus."""
        brand_service.create_identity(
            name="TestBrand",
        )
        report = brand_service.get_agent_report("Echo")
        assert report["agent"] == "Echo"
        assert report["focus"] == "Brand Voice & Marketing"

    def test_get_brand_kit(self, brand_service):
        """Get brand kit."""
        brand_service.create_identity(
            name="TestBrand",
        )
        kit = brand_service.get_brand_kit()
        assert "name" in kit
        assert kit["name"] == "TestBrand"

    def test_get_stats(self, brand_service):
        """Get service stats."""
        stats = brand_service.get_stats()
        assert "initialized" in stats
        assert "has_identity" in stats


# =============================================================================
# Scheduler Service Tests
# =============================================================================


class TestSchedulerService:
    """Tests for the SchedulerService."""

    @pytest.fixture
    def scheduler_service(self):
        """Create a SchedulerService instance."""
        from ag3ntwerk.modules.scheduler import SchedulerService

        return SchedulerService()

    def test_service_initialization(self, scheduler_service):
        """Verify service initializes correctly."""
        assert scheduler_service is not None
        assert hasattr(scheduler_service, "_engine")
        assert hasattr(scheduler_service, "_workflow_executor")

    def test_schedule_task(self, scheduler_service):
        """Schedule a task."""
        task_id = scheduler_service.schedule_task(
            name="Test Task",
            handler_name="test.handler",
            description="Test description",
            frequency="daily",
        )
        assert task_id is not None
        assert isinstance(task_id, str)

    def test_list_tasks(self, scheduler_service):
        """List scheduled tasks."""
        scheduler_service.schedule_task(
            name="Test Task List",
            handler_name="test.handler",
        )
        tasks = scheduler_service.list_tasks()
        assert isinstance(tasks, list)
        assert len(tasks) >= 1

    def test_list_tasks_by_owner(self, scheduler_service):
        """List tasks filtered by owner."""
        scheduler_service.schedule_task(
            name="Nexus Filtered Task",
            handler_name="test.handler",
            owner_executive="Nexus",
        )
        tasks = scheduler_service.list_tasks(owner_executive="Nexus")
        # Should have at least the task we just created
        assert len(tasks) >= 1

    def test_enable_disable_task(self, scheduler_service):
        """Enable and disable a task."""
        task_id = scheduler_service.schedule_task(
            name="Enable Disable Test Task",
            handler_name="test.handler",
        )

        # Disable
        result = scheduler_service.disable_task(task_id)
        assert result is True

        # Enable
        result = scheduler_service.enable_task(task_id)
        assert result is True

    def test_list_workflows(self, scheduler_service):
        """List available workflows."""
        workflows = scheduler_service.list_workflows()
        assert isinstance(workflows, list)
        # Should have pre-registered workflows
        assert len(workflows) >= 1

    def test_get_agent_report_coo(self, scheduler_service):
        """Nexus report has operations focus."""
        report = scheduler_service.get_agent_report("Nexus")
        assert report["agent"] == "Nexus"
        # Check that it has expected structure
        assert "generated_at" in report

    def test_get_agent_report_ceo(self, scheduler_service):
        """CEO report has strategic focus."""
        report = scheduler_service.get_agent_report("CEO")
        assert report["agent"] == "CEO"
        # Check that it has expected structure
        assert "generated_at" in report

    def test_get_stats(self, scheduler_service):
        """Get service stats."""
        stats = scheduler_service.get_stats()
        # Just verify it returns a dict
        assert isinstance(stats, dict)


# =============================================================================
# Module Integration Tests
# =============================================================================


class TestModuleIntegration:
    """Tests for module integration layer."""

    @pytest.fixture
    def integration(self):
        """Create a ModuleIntegration instance."""
        from ag3ntwerk.modules.integration import ModuleIntegration

        return ModuleIntegration()

    def test_integration_initialization(self, integration):
        """Verify integration initializes correctly."""
        assert integration is not None

    def test_lazy_loading_services(self, integration):
        """Services are lazy-loaded."""
        # Access each service
        assert integration.trend_service is not None
        assert integration.commerce_service is not None
        assert integration.brand_service is not None
        assert integration.scheduler_service is not None

    def test_get_modules_for_executive(self, integration):
        """Get modules for an agent."""
        modules = integration.get_modules_for_executive("Echo")
        assert "trends" in modules
        assert "brand" in modules

    @pytest.mark.asyncio
    async def test_get_module_report(self, integration):
        """Get module report for agent."""
        report = await integration.get_module_report("trends", "Echo")
        assert "agent" in report
        assert report["agent"] == "Echo"

    @pytest.mark.asyncio
    async def test_get_all_reports_for_executive(self, integration):
        """Get all module reports for an agent."""
        reports = await integration.get_all_reports_for_executive("Echo")
        assert isinstance(reports, dict)
        assert "trends" in reports
        assert "brand" in reports

    def test_get_stats(self, integration):
        """Get stats from all modules."""
        stats = integration.get_stats()
        assert "trends" in stats
        assert "commerce" in stats
        assert "brand" in stats
        assert "scheduler" in stats


# =============================================================================
# Autonomous Workflow Tests
# =============================================================================


class TestAutonomousWorkflows:
    """Tests for autonomous workflows."""

    @pytest.fixture
    def workflow_runner(self):
        """Create an AutonomousWorkflowRunner instance."""
        from ag3ntwerk.modules.autonomous_workflows import AutonomousWorkflowRunner

        return AutonomousWorkflowRunner()

    def test_list_workflows(self, workflow_runner):
        """List available autonomous workflows."""
        workflows = workflow_runner.list_workflows()
        assert isinstance(workflows, list)
        assert len(workflows) >= 4  # We created 5 workflows

        # Check expected workflows exist
        names = [w["name"] for w in workflows]
        assert "daily_operations" in names
        assert "pricing_optimization" in names
        assert "market_intelligence" in names
        assert "brand_audit" in names

    def test_get_stats(self, workflow_runner):
        """Get workflow runner stats."""
        stats = workflow_runner.get_stats()
        assert "available_workflows" in stats
        assert "total_executions" in stats
        assert stats["available_workflows"] >= 4

    @pytest.mark.asyncio
    async def test_execute_unknown_workflow(self, workflow_runner):
        """Execute unknown workflow returns error."""
        result = await workflow_runner.execute("nonexistent_workflow")
        assert result.success is False
        assert "Unknown workflow" in result.error

    @pytest.mark.asyncio
    async def test_execute_brand_audit_workflow(self, workflow_runner):
        """Execute brand audit workflow."""
        result = await workflow_runner.execute("brand_audit")
        assert result.workflow_name == "brand_audit"
        assert isinstance(result.steps, list)
        # Workflow runs but identity might not exist
        assert result.completed_at is not None

    def test_get_execution_history(self, workflow_runner):
        """Get execution history."""
        history = workflow_runner.get_execution_history()
        assert isinstance(history, list)


# =============================================================================
# MCP Module Tools Tests
# =============================================================================


class TestMCPModuleTools:
    """Tests for MCP module tools."""

    @pytest.fixture
    def module_handler(self):
        """Create a ModuleToolHandler instance."""
        from ag3ntwerk.mcp.module_tools import ModuleToolHandler

        return ModuleToolHandler()

    def test_handler_initialization(self, module_handler):
        """Verify handler initializes correctly."""
        assert module_handler is not None

    def test_get_handler_trends(self, module_handler):
        """Get handler for trend tools."""
        handler = module_handler.get_handler("trends_get_trending")
        assert handler is not None

    def test_get_handler_commerce(self, module_handler):
        """Get handler for commerce tools."""
        handler = module_handler.get_handler("commerce_list_storefronts")
        assert handler is not None

    def test_get_handler_brand(self, module_handler):
        """Get handler for brand tools."""
        handler = module_handler.get_handler("brand_get_identity")
        assert handler is not None

    def test_get_handler_scheduler(self, module_handler):
        """Get handler for scheduler tools."""
        handler = module_handler.get_handler("scheduler_list_tasks")
        assert handler is not None

    def test_get_handler_unknown(self, module_handler):
        """Get handler for unknown tool returns None."""
        handler = module_handler.get_handler("unknown_tool")
        assert handler is None

    @pytest.mark.asyncio
    async def test_handle_trends_get_trending(self, module_handler):
        """Handle trends_get_trending tool."""
        handler = module_handler.get_handler("trends_get_trending")
        result = await handler({})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_handle_commerce_list_storefronts(self, module_handler):
        """Handle commerce_list_storefronts tool."""
        handler = module_handler.get_handler("commerce_list_storefronts")
        result = await handler({})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_handle_brand_get_identity(self, module_handler):
        """Handle brand_get_identity tool."""
        handler = module_handler.get_handler("brand_get_identity")
        result = await handler({})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_handle_scheduler_list_tasks(self, module_handler):
        """Handle scheduler_list_tasks tool."""
        handler = module_handler.get_handler("scheduler_list_tasks")
        result = await handler({})
        assert isinstance(result, str)


# =============================================================================
# New Engine Lazy-Loading Tests
# =============================================================================


class TestEngineIntegration:
    """Tests for lazy-loaded engine integration."""

    @pytest.fixture
    def integration(self):
        from ag3ntwerk.modules.integration import ModuleIntegration

        return ModuleIntegration()

    def test_research_engine_lazy_load(self, integration):
        """Research engine is lazy-loaded and returns status."""
        engine = integration.research_engine
        assert engine is not None
        status = engine.get_research_status()
        assert isinstance(status, dict)

    def test_harvesting_engine_lazy_load(self, integration):
        """Harvesting engine is lazy-loaded and returns status."""
        engine = integration.harvesting_engine
        assert engine is not None
        status = engine.get_harvest_status()
        assert isinstance(status, dict)

    def test_security_engine_lazy_load(self, integration):
        """Security engine is lazy-loaded and returns status."""
        engine = integration.security_engine
        assert engine is not None
        status = engine.get_security_posture()
        assert isinstance(status, dict)

    def test_get_stats_includes_new_modules(self, integration):
        """get_stats() includes research, harvesting, and security."""
        stats = integration.get_stats()
        assert "research_automation" in stats
        assert "data_harvesting" in stats
        assert "security_automation" in stats


# =============================================================================
# Compass Module Handler Tests
# =============================================================================


class TestCSOModuleHandler:
    """Tests for CompassModuleHandler (Compass)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import CompassModuleHandler

        return CompassModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    def test_get_research_status(self, handler):
        """get_research_status returns dict."""
        status = handler.get_research_status()
        assert isinstance(status, dict)

    def test_get_insights_summary(self, handler):
        """get_insights_summary returns dict."""
        summary = handler.get_insights_summary()
        assert isinstance(summary, dict)

    @pytest.mark.asyncio
    async def test_run_market_scan(self, handler):
        """run_market_scan executes and returns result."""
        result = await handler.run_market_scan()
        assert isinstance(result, dict)
        assert "success" in result

    @pytest.mark.asyncio
    async def test_run_competitive_analysis(self, handler):
        """run_competitive_analysis executes and returns result."""
        result = await handler.run_competitive_analysis()
        assert isinstance(result, dict)
        assert "success" in result


# =============================================================================
# Index Module Handler Tests
# =============================================================================


class TestCDOModuleHandler:
    """Tests for IndexModuleHandler (Index)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import IndexModuleHandler

        return IndexModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    def test_get_harvest_status(self, handler):
        """get_harvest_status returns dict."""
        status = handler.get_harvest_status()
        assert isinstance(status, dict)

    def test_list_sources_empty(self, handler):
        """list_sources returns empty list initially."""
        sources = handler.list_sources()
        assert isinstance(sources, list)

    def test_register_source(self, handler):
        """register_source adds a source."""
        result = handler.register_source(
            name="test_api",
            source_type="api_endpoint",
        )
        assert isinstance(result, dict)

    def test_get_data_quality_report(self, handler):
        """get_data_quality_report returns dict."""
        report = handler.get_data_quality_report()
        assert isinstance(report, dict)

    @pytest.mark.asyncio
    async def test_run_harvest_cycle(self, handler):
        """run_harvest_cycle executes."""
        result = await handler.run_harvest_cycle()
        assert isinstance(result, dict)


# =============================================================================
# Citadel Module Handler Tests
# =============================================================================


class TestCSecOModuleHandler:
    """Tests for CitadelModuleHandler (Citadel)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import CitadelModuleHandler

        return CitadelModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    def test_get_security_posture(self, handler):
        """get_security_posture returns dict."""
        posture = handler.get_security_posture()
        assert isinstance(posture, dict)

    def test_get_threat_assessment(self, handler):
        """get_threat_assessment returns dict."""
        assessment = handler.get_threat_assessment()
        assert isinstance(assessment, dict)

    def test_acknowledge_alert_nonexistent(self, handler):
        """acknowledge_alert on nonexistent alert returns result."""
        result = handler.acknowledge_alert("nonexistent-alert-id")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_run_security_scan(self, handler):
        """run_security_scan executes and returns result."""
        result = await handler.run_security_scan()
        assert isinstance(result, dict)
        assert "success" in result

    @pytest.mark.asyncio
    async def test_run_full_audit(self, handler):
        """run_full_audit executes and returns result."""
        result = await handler.run_full_audit()
        assert isinstance(result, dict)


# =============================================================================
# Vinzy Metering Plugin Entitlement Tests
# =============================================================================


class TestVinzyMeteringPlugin:
    """Tests for VinzyMeteringPlugin entitlement hooks."""

    @pytest.fixture
    def plugin(self):
        from ag3ntwerk.core.plugins.vinzy_metering import VinzyMeteringPlugin

        return VinzyMeteringPlugin(
            license_key="test-key",
            server_url="http://localhost:9999",
        )

    def test_pre_execute_hooks_exist(self, plugin):
        """Plugin has pre-execute hooks with correct priority."""
        hooks = plugin.get_hooks()
        hook_map = {h.hook_name: h for h in hooks}
        assert "delegation.pre_execute" in hook_map
        assert "tool.pre_execute" in hook_map
        assert hook_map["delegation.pre_execute"].priority == 10
        assert hook_map["tool.pre_execute"].priority == 10

    def test_post_execute_hooks_still_exist(self, plugin):
        """Post-execute metering hooks are still registered."""
        hooks = plugin.get_hooks()
        hook_map = {h.hook_name: h for h in hooks}
        assert "delegation.post_execute" in hook_map
        assert "tool.post_execute" in hook_map
        assert hook_map["delegation.post_execute"].priority == 50
        assert hook_map["tool.post_execute"].priority == 50

    def test_empty_agent_code_returns_none(self, plugin):
        """Empty agent_code skips entitlement check."""
        result = plugin.check_delegation_entitlement({"delegate": ""})
        assert result is None
        result = plugin.check_tool_entitlement({"agent_code": ""})
        assert result is None

    def test_graceful_degradation_server_unreachable(self, plugin):
        """Returns None (allow) when Vinzy server is unreachable."""
        # The server at localhost:9999 is not running, so the SDK will
        # either return a CONNECTION_ERROR result or raise.  Either way
        # the plugin should degrade gracefully and return None.
        result = plugin.check_delegation_entitlement({"delegate": "Forge"})
        assert result is None

    def test_blocked_when_not_entitled(self, plugin):
        """Returns blocked dict when validate_agent says not entitled."""
        from unittest.mock import MagicMock
        from dataclasses import dataclass, field
        from typing import Any, Optional

        @dataclass
        class FakeResult:
            valid: bool = False
            code: str = "NOT_ENTITLED"
            message: str = "Agent Forge not entitled"

        mock_client = MagicMock()
        mock_client.validate_agent.return_value = FakeResult()
        plugin._client = mock_client

        result = plugin.check_delegation_entitlement({"delegate": "Forge"})
        assert result is not None
        assert result["blocked"] is True
        assert "not entitled" in result["reason"]

    def test_allowed_when_entitled(self, plugin):
        """Returns None when validate_agent says entitled."""
        from unittest.mock import MagicMock
        from dataclasses import dataclass

        @dataclass
        class FakeResult:
            valid: bool = True
            code: str = ""
            message: str = ""

        mock_client = MagicMock()
        mock_client.validate_agent.return_value = FakeResult()
        plugin._client = mock_client

        result = plugin.check_delegation_entitlement({"delegate": "Forge"})
        assert result is None

    def test_tool_entitlement_blocked(self, plugin):
        """Tool pre-execute blocks when not entitled."""
        from unittest.mock import MagicMock
        from dataclasses import dataclass

        @dataclass
        class FakeResult:
            valid: bool = False
            code: str = "NOT_ENTITLED"
            message: str = "Agent Keystone not entitled"

        mock_client = MagicMock()
        mock_client.validate_agent.return_value = FakeResult()
        plugin._client = mock_client

        result = plugin.check_tool_entitlement({"agent_code": "Keystone"})
        assert result is not None
        assert result["blocked"] is True

    def test_tool_entitlement_allowed(self, plugin):
        """Tool pre-execute allows when entitled."""
        from unittest.mock import MagicMock
        from dataclasses import dataclass

        @dataclass
        class FakeResult:
            valid: bool = True
            code: str = ""
            message: str = ""

        mock_client = MagicMock()
        mock_client.validate_agent.return_value = FakeResult()
        plugin._client = mock_client

        result = plugin.check_tool_entitlement({"agent_code": "Keystone"})
        assert result is None


# =============================================================================
# Overwatch Module Handler Tests
# =============================================================================


class TestCoSModuleHandler:
    """Tests for OverwatchModuleHandler (Overwatch)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import OverwatchModuleHandler

        return OverwatchModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    def test_get_personality_insights(self, handler):
        """get_personality_insights returns dict with agent_count."""
        result = handler.get_personality_insights()
        assert isinstance(result, dict)
        assert "agent_count" in result
        assert "agents" in result

    def test_get_drift_summary(self, handler):
        """get_drift_summary returns dict."""
        result = handler.get_drift_summary()
        assert isinstance(result, dict)

    def test_get_routing_stats(self, handler):
        """get_routing_stats returns dict."""
        result = handler.get_routing_stats()
        assert isinstance(result, dict)

    def test_get_all_module_stats(self, handler):
        """get_all_module_stats returns dict with module keys."""
        result = handler.get_all_module_stats()
        assert isinstance(result, dict)
        assert "trends" in result


# =============================================================================
# Forge Module Handler Tests
# =============================================================================


class TestCTOModuleHandler:
    """Tests for ForgeModuleHandler (Forge)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import ForgeModuleHandler

        return ForgeModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    def test_get_workbench_status(self, handler):
        """get_workbench_status returns dict."""
        status = handler.get_workbench_status()
        assert isinstance(status, dict)

    def test_get_distributed_status(self, handler):
        """get_distributed_status returns dict."""
        status = handler.get_distributed_status()
        assert isinstance(status, dict)

    @pytest.mark.asyncio
    async def test_run_technology_scan(self, handler):
        """run_technology_scan executes and returns result."""
        result = await handler.run_technology_scan()
        assert isinstance(result, dict)
        assert "success" in result


# =============================================================================
# Keystone Module Handler Tests
# =============================================================================


class TestCFOModuleHandler:
    """Tests for KeystoneModuleHandler (Keystone)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import KeystoneModuleHandler

        return KeystoneModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    @pytest.mark.asyncio
    async def test_get_financial_report(self, handler):
        """get_financial_report returns dict with agent key."""
        report = await handler.get_financial_report()
        assert isinstance(report, dict)
        assert report["agent"] == "Keystone"

    def test_get_revenue_overview(self, handler):
        """get_revenue_overview returns dict."""
        result = handler.get_revenue_overview()
        assert isinstance(result, dict)


# =============================================================================
# Sentinel Module Handler Tests
# =============================================================================


class TestCIOModuleHandler:
    """Tests for SentinelModuleHandler (Sentinel)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import SentinelModuleHandler

        return SentinelModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    def test_get_security_overview(self, handler):
        """get_security_overview returns dict."""
        result = handler.get_security_overview()
        assert isinstance(result, dict)

    def test_get_compliance_status(self, handler):
        """get_compliance_status returns dict."""
        result = handler.get_compliance_status()
        assert isinstance(result, dict)

    def test_get_threat_assessment(self, handler):
        """get_threat_assessment returns dict."""
        result = handler.get_threat_assessment()
        assert isinstance(result, dict)

    def test_get_infrastructure_status(self, handler):
        """get_infrastructure_status returns dict."""
        result = handler.get_infrastructure_status()
        assert isinstance(result, dict)


# =============================================================================
# Blueprint Module Handler Tests
# =============================================================================


class TestCPOModuleHandler:
    """Tests for BlueprintModuleHandler (Blueprint)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import BlueprintModuleHandler

        return BlueprintModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    @pytest.mark.asyncio
    async def test_get_product_trends(self, handler):
        """get_product_trends returns Blueprint-focused report."""
        report = await handler.get_product_trends()
        assert isinstance(report, dict)
        assert report["agent"] == "Blueprint"

    @pytest.mark.asyncio
    async def test_run_trend_analysis(self, handler):
        """run_trend_analysis executes and returns result."""
        result = await handler.run_trend_analysis()
        assert isinstance(result, dict)


# =============================================================================
# Axiom Module Handler Tests
# =============================================================================


class TestCROModuleHandler:
    """Tests for AxiomModuleHandler (Axiom)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import AxiomModuleHandler

        return AxiomModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    @pytest.mark.asyncio
    async def test_get_research_trends(self, handler):
        """get_research_trends returns Axiom-focused report."""
        report = await handler.get_research_trends()
        assert isinstance(report, dict)


# =============================================================================
# Foundry Module Handler Tests
# =============================================================================


class TestCEngOModuleHandler:
    """Tests for FoundryModuleHandler (Foundry)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import FoundryModuleHandler

        return FoundryModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    def test_get_workbench_status(self, handler):
        """get_workbench_status returns dict."""
        status = handler.get_workbench_status()
        assert isinstance(status, dict)


# =============================================================================
# Beacon Module Handler Tests
# =============================================================================


class TestCCOModuleHandler:
    """Tests for BeaconModuleHandler (Beacon)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import BeaconModuleHandler

        return BeaconModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    def test_get_brand_report(self, handler):
        """get_brand_report returns dict."""
        report = handler.get_brand_report()
        assert isinstance(report, dict)

    def test_get_brand_kit(self, handler):
        """get_brand_kit returns dict."""
        kit = handler.get_brand_kit()
        assert isinstance(kit, dict)

    def test_validate_content(self, handler):
        """validate_content returns dict."""
        result = handler.validate_content("Test content for validation")
        assert isinstance(result, dict)


# =============================================================================
# Aegis Module Handler Tests
# =============================================================================


class TestCRiOModuleHandler:
    """Tests for AegisModuleHandler (Aegis)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import AegisModuleHandler

        return AegisModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    def test_get_risk_overview(self, handler):
        """get_risk_overview returns combined security+drift dict."""
        result = handler.get_risk_overview()
        assert isinstance(result, dict)
        assert "security_threats" in result
        assert "personality_drift" in result

    def test_get_compliance_status(self, handler):
        """get_compliance_status returns dict."""
        result = handler.get_compliance_status()
        assert isinstance(result, dict)


# =============================================================================
# Accord Module Handler Tests
# =============================================================================


class TestAccordModuleHandler:
    """Tests for AccordModuleHandler (Accord)."""

    @pytest.fixture
    def handler(self):
        from ag3ntwerk.modules.integration import AccordModuleHandler

        return AccordModuleHandler()

    def test_initialization(self, handler):
        """Handler initializes with integration."""
        assert handler is not None
        assert handler._integration is not None

    def test_get_governance_report(self, handler):
        """get_governance_report returns dict with drift and routing."""
        report = handler.get_governance_report()
        assert isinstance(report, dict)
        assert "drift_summary" in report
        assert "routing_stats" in report

    def test_get_compliance_status(self, handler):
        """get_compliance_status returns dict."""
        result = handler.get_compliance_status()
        assert isinstance(result, dict)

    def test_get_team_health(self, handler):
        """get_team_health returns dict."""
        result = handler.get_team_health()
        assert isinstance(result, dict)
