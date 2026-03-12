"""
Tests for the Agent Registry (Sprint 3.1).

Tests cover:
- Agent registry completeness
- Task type to agent mapping
- Text-based routing
- Agent info retrieval
- Capability queries
"""

import pytest
import os
import sys
import importlib.util

# Add nexus to path for imports
_nexus_src_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "src", "nexus", "src")
)


def _import_from_path(module_name: str, file_path: str):
    """Import a module from a specific file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Import the agent_registry module directly
_registry_path = os.path.join(_nexus_src_path, "nexus", "coo", "agent_registry.py")

if os.path.exists(_registry_path):
    _registry_module = _import_from_path("test_exec_registry", _registry_path)
    ExecutiveInfo = _registry_module.ExecutiveInfo
    AGENT_CAPABILITIES = _registry_module.AGENT_CAPABILITIES
    get_agent_for_task = _registry_module.get_agent_for_task
    get_agent_for_text = _registry_module.get_agent_for_text
    get_agent_info = _registry_module.get_agent_info
    get_all_executives = _registry_module.get_all_executives
    get_agent_codes = _registry_module.get_agent_codes
    get_capabilities_for_executive = _registry_module.get_capabilities_for_executive
    get_all_task_types = _registry_module.get_all_task_types
    find_executives_for_capability = _registry_module.find_executives_for_capability
    KEYWORD_ROUTING = _registry_module.KEYWORD_ROUTING
    REGISTRY_AVAILABLE = True
else:
    REGISTRY_AVAILABLE = False


pytestmark = pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Agent registry not available")


class TestAgentRegistryCompleteness:
    """Test that the registry contains all expected agents."""

    def test_registry_has_16_executives(self):
        """Registry should contain all 16 ag3ntwerk agents."""
        assert len(AGENT_CAPABILITIES) == 16

    def test_all_expected_executives_present(self):
        """All expected agent codes should be in the registry."""
        expected_codes = [
            "Forge",
            "Echo",
            "Keystone",
            "Sentinel",
            "Citadel",
            "Compass",
            "Axiom",
            "Index",
            "Accord",
            "Aegis",
            "Blueprint",
            "Beacon",
            "Vector",
            "Foundry",
            "Overwatch",
            "Nexus",
        ]
        for code in expected_codes:
            assert code in AGENT_CAPABILITIES, f"Missing agent: {code}"

    def test_executives_have_required_fields(self):
        """Each agent should have all required fields."""
        for code, info in AGENT_CAPABILITIES.items():
            assert info.code == code
            assert info.name, f"{code} missing name"
            assert info.codename, f"{code} missing codename"
            assert info.domain, f"{code} missing domain"
            assert len(info.capabilities) > 0, f"{code} has no capabilities"

    def test_agent_codenames(self):
        """Agents should have correct codenames."""
        expected_codenames = {
            "Forge": "Forge",
            "Echo": "Echo",
            "Keystone": "Keystone",
            "Sentinel": "Sentinel",
            "Citadel": "Citadel",
            "Compass": "Compass",
            "Axiom": "Axiom",
            "Index": "Index",
            "Accord": "Accord",
            "Aegis": "Aegis",
            "Blueprint": "Blueprint",
            "Beacon": "Beacon",
            "Vector": "Vector",
            "Foundry": "Foundry",
            "Overwatch": "Overwatch",
            "Nexus": "Nexus",
        }
        for code, expected_name in expected_codenames.items():
            assert AGENT_CAPABILITIES[code].codename == expected_name


class TestGetExecutiveForTask:
    """Test task type to agent mapping."""

    def test_code_review_routes_to_cto(self):
        """code_review should route to Forge."""
        assert get_agent_for_task("code_review") == "Forge"

    def test_campaign_creation_routes_to_cmo(self):
        """campaign_creation should route to Echo."""
        assert get_agent_for_task("campaign_creation") == "Echo"

    def test_budget_analysis_routes_to_cfo(self):
        """budget_analysis should route to Keystone."""
        assert get_agent_for_task("budget_analysis") == "Keystone"

    def test_security_scan_routes_to_cio(self):
        """security_scan should route to Sentinel."""
        assert get_agent_for_task("security_scan") == "Sentinel"

    def test_vulnerability_check_routes_to_cseco(self):
        """vulnerability_check should route to Citadel."""
        assert get_agent_for_task("vulnerability_check") == "Citadel"

    def test_strategic_analysis_routes_to_cso(self):
        """strategic_analysis should route to Compass."""
        assert get_agent_for_task("strategic_analysis") == "Compass"

    def test_research_routes_to_cro(self):
        """research should route to Axiom."""
        assert get_agent_for_task("research") == "Axiom"

    def test_data_governance_routes_to_cdo(self):
        """data_governance should route to Index."""
        assert get_agent_for_task("data_governance") == "Index"

    def test_compliance_check_routes_to_ccomo(self):
        """compliance_check should route to Accord."""
        assert get_agent_for_task("compliance_check") == "Accord"

    def test_risk_assessment_routes_to_crio(self):
        """risk_assessment should route to Aegis."""
        assert get_agent_for_task("risk_assessment") == "Aegis"

    def test_product_strategy_routes_to_cpo(self):
        """product_strategy should route to Blueprint."""
        assert get_agent_for_task("product_strategy") == "Blueprint"

    def test_customer_feedback_routes_to_cco(self):
        """customer_feedback should route to Beacon."""
        assert get_agent_for_task("customer_feedback") == "Beacon"

    def test_revenue_optimization_routes_to_crevo(self):
        """revenue_optimization should route to Vector."""
        assert get_agent_for_task("revenue_optimization") == "Vector"

    def test_infrastructure_routes_to_cengo(self):
        """infrastructure should route to Foundry."""
        assert get_agent_for_task("infrastructure") == "Foundry"

    def test_unknown_task_returns_none(self):
        """Unknown task types should return None."""
        assert get_agent_for_task("unknown_task_xyz") is None

    def test_case_insensitive_matching(self):
        """Task type matching should be case insensitive."""
        assert get_agent_for_task("CODE_REVIEW") == "Forge"
        assert get_agent_for_task("Code_Review") == "Forge"


class TestGetExecutiveForText:
    """Test text-based routing."""

    def test_code_keyword_routes_to_cto(self):
        """Text containing 'code' should route to Forge."""
        assert get_agent_for_text("Review this code") == "Forge"

    def test_security_keyword_routes_to_cio(self):
        """Text containing 'security' should route to Sentinel."""
        assert get_agent_for_text("Check security settings") == "Sentinel"

    def test_marketing_keyword_routes_to_cmo(self):
        """Text containing 'marketing' should route to Echo."""
        assert get_agent_for_text("Plan marketing campaign") == "Echo"

    def test_budget_keyword_routes_to_cfo(self):
        """Text containing 'budget' should route to Keystone."""
        assert get_agent_for_text("Review budget allocation") == "Keystone"

    def test_customer_keyword_routes_to_cco(self):
        """Text containing 'customer' should route to Beacon."""
        assert get_agent_for_text("Handle customer complaint") == "Beacon"

    def test_empty_text_returns_none(self):
        """Empty text should return None."""
        assert get_agent_for_text("") is None
        assert get_agent_for_text(None) is None

    def test_no_match_returns_none(self):
        """Text with no matching keywords should return None."""
        assert get_agent_for_text("Lorem ipsum dolor sit amet") is None


class TestGetExecutiveInfo:
    """Test agent info retrieval."""

    def test_get_cto_info(self):
        """Should return correct info for Forge."""
        info = get_agent_info("Forge")
        assert info is not None
        assert info.code == "Forge"
        assert info.codename == "Forge"
        assert "code_review" in info.capabilities

    def test_get_info_case_insensitive(self):
        """Agent lookup should be case insensitive."""
        assert get_agent_info("cto") is not None
        assert get_agent_info("Cto") is not None

    def test_unknown_executive_returns_none(self):
        """Unknown agent should return None."""
        assert get_agent_info("UNKNOWN") is None


class TestGetAllExecutives:
    """Test getting all agents."""

    def test_returns_list_of_executive_info(self):
        """Should return list of ExecutiveInfo objects."""
        agents = get_all_executives()
        assert len(agents) == 16
        for exec_info in agents:
            assert isinstance(exec_info, ExecutiveInfo)


class TestGetExecutiveCodes:
    """Test getting agent codes."""

    def test_returns_all_codes(self):
        """Should return all 16 agent codes."""
        codes = get_agent_codes()
        assert len(codes) == 16
        assert "Forge" in codes
        assert "Echo" in codes
        assert "Keystone" in codes


class TestGetCapabilitiesForExecutive:
    """Test capability queries."""

    def test_cto_capabilities(self):
        """Forge should have expected capabilities."""
        caps = get_capabilities_for_executive("Forge")
        assert "code_review" in caps
        assert "code_generation" in caps
        assert "architecture" in caps

    def test_unknown_executive_returns_empty(self):
        """Unknown agent should return empty list."""
        caps = get_capabilities_for_executive("UNKNOWN")
        assert caps == []


class TestGetAllTaskTypes:
    """Test getting all task types."""

    def test_returns_set_of_task_types(self):
        """Should return set of all known task types."""
        task_types = get_all_task_types()
        assert isinstance(task_types, set)
        assert "code_review" in task_types
        assert "campaign_creation" in task_types
        assert "budget_analysis" in task_types


class TestFindExecutivesForCapability:
    """Test finding agents by capability."""

    def test_find_code_capability(self):
        """Should find agents that can handle code-related tasks."""
        agents = find_executives_for_capability("code")
        assert "Forge" in agents

    def test_find_security_capability(self):
        """Should find agents that can handle security tasks."""
        agents = find_executives_for_capability("security")
        assert "Sentinel" in agents or "Citadel" in agents

    def test_find_nonexistent_capability(self):
        """Should return empty for nonexistent capability."""
        agents = find_executives_for_capability("nonexistent_xyz_123")
        assert agents == []


class TestKeywordRouting:
    """Test keyword routing dictionary."""

    def test_keyword_routing_has_entries(self):
        """Keyword routing should have entries."""
        assert len(KEYWORD_ROUTING) > 0

    def test_keyword_routing_values_are_executives(self):
        """All keyword routing values should be valid agent codes."""
        valid_codes = set(AGENT_CAPABILITIES.keys())
        for keyword, agent_code in KEYWORD_ROUTING.items():
            assert agent_code in valid_codes, f"Invalid agent {agent_code} for keyword {keyword}"


class TestExecutiveInfoDataclass:
    """Test ExecutiveInfo dataclass."""

    def test_create_executive_info(self):
        """Should be able to create ExecutiveInfo."""
        info = ExecutiveInfo(
            code="TEST",
            name="Test Agent",
            codename="TestName",
            domain="Testing",
            capabilities=["test_cap"],
            description="Test description",
        )
        assert info.code == "TEST"
        assert info.name == "Test Agent"
        assert info.codename == "TestName"
        assert info.domain == "Testing"
        assert info.capabilities == ["test_cap"]
        assert info.description == "Test description"

    def test_default_values(self):
        """Should have sensible defaults."""
        info = ExecutiveInfo(
            code="TEST",
            name="Test",
            codename="Test",
            domain="Test",
        )
        assert info.capabilities == []
        assert info.description == ""
