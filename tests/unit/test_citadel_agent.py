"""
Unit tests for Citadel (Citadel) agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.citadel import Citadel, Citadel
from ag3ntwerk.agents.citadel.managers import (
    ThreatManager,
    VulnerabilityManager,
    ComplianceManager,
    SOCManager,
)
from ag3ntwerk.agents.citadel.specialists import (
    ThreatHunter,
    VulnerabilityAnalyst,
    IncidentResponder,
    ComplianceAnalyst,
    SecurityEngineer,
    AppSecEngineer,
)
from ag3ntwerk.agents.citadel.models import (
    SECURITY_CAPABILITIES,
    Threat,
    ThreatSeverity,
    ThreatStatus,
    Vulnerability,
    SecurityIncident,
    IncidentSeverity,
    SecurityPolicy,
    ComplianceControl,
    ComplianceStatus,
)
from ag3ntwerk.core.base import Task, TaskStatus


class TestCSecOAgent:
    """Tests for Citadel agent."""

    @pytest.fixture
    def cseco(self, mock_llm_provider):
        return Citadel(llm_provider=mock_llm_provider)

    def test_cseco_creation(self):
        """Test Citadel agent creation."""
        cseco = Citadel()

        assert cseco.code == "Citadel"
        assert cseco.name == "Citadel"
        assert cseco.codename == "Citadel"
        assert cseco.domain == "Security Operations, Threat Management, Compliance, AppSec"

    def test_citadel_alias(self):
        """Test Citadel is an alias for Citadel."""
        assert Citadel is Citadel

        citadel = Citadel()
        assert citadel.code == "Citadel"
        assert citadel.codename == "Citadel"

    def test_cseco_capabilities(self, cseco):
        """Test Citadel has expected capabilities from SECURITY_CAPABILITIES."""
        expected_capabilities = [
            "threat_detection",
            "threat_analysis",
            "threat_hunting",
            "threat_mitigation",
            "vulnerability_scanning",
            "vulnerability_assessment",
            "vulnerability_remediation",
            "incident_response",
            "incident_investigation",
            "forensics",
            "compliance_assessment",
            "policy_management",
            "access_review",
            "security_monitoring",
            "siem_operations",
            "security_automation",
            "code_review",
        ]

        for cap in expected_capabilities:
            assert cap in cseco.capabilities, f"Missing capability: {cap}"

    def test_can_handle_security_tasks(self, cseco):
        """Test Citadel can handle security-related tasks."""
        security_tasks = [
            "threat_detection",
            "threat_analysis",
            "threat_hunting",
            "vulnerability_scan",
            "vulnerability_assessment",
            "security_scan",
            "incident_response",
            "incident_investigation",
            "forensics",
            "compliance_assessment",
            "compliance_audit",
            "policy_management",
            "access_review",
            "security_monitoring",
            "siem_operations",
            "code_review",
            "sast_scan",
            "dast_scan",
            "dependency_scan",
            "security_automation",
            "penetration_test",
        ]

        for task_type in security_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert cseco.can_handle(task), f"Citadel should handle {task_type}"

    def test_can_handle_by_description_keywords(self, cseco):
        """Test Citadel can handle tasks based on security keywords in description."""
        keyword_tasks = [
            ("Evaluate security posture", "general_task"),
            ("Identify threat vectors", "general_task"),
            ("Check vulnerability in API", "general_task"),
            ("Ensure compliance with SOC2", "general_task"),
        ]

        for description, task_type in keyword_tasks:
            task = Task(description=description, task_type=task_type)
            assert cseco.can_handle(
                task
            ), f"Citadel should handle task with description: {description}"

    def test_cannot_handle_non_security_tasks(self, cseco):
        """Test Citadel doesn't handle non-security tasks."""
        non_security_tasks = [
            ("Analyze market trends", "market_analysis"),
            ("Create budget plan", "budget_planning"),
            ("Track revenue metrics", "revenue_tracking"),
            ("Design product roadmap", "product_roadmap"),
        ]

        for description, task_type in non_security_tasks:
            task = Task(description=description, task_type=task_type)
            assert not cseco.can_handle(task), f"Citadel should not handle {task_type}"

    def test_cseco_subordinate_registration(self, cseco):
        """Test Citadel registers managers as subordinates."""
        subordinate_codes = [sub.code for sub in cseco.subordinates]

        assert "TM" in subordinate_codes  # ThreatManager
        assert "VM" in subordinate_codes  # VulnerabilityManager
        assert "CM" in subordinate_codes  # ComplianceManager
        assert "SOCM" in subordinate_codes  # SOCManager
        assert len(cseco.subordinates) == 4

    def test_cseco_manager_specialist_hierarchy(self, cseco):
        """Test managers have specialists registered."""
        for manager in cseco.subordinates:
            if manager.code == "TM":
                sub_codes = [s.code for s in manager.subordinates]
                assert "TH" in sub_codes  # ThreatHunter
            elif manager.code == "VM":
                sub_codes = [s.code for s in manager.subordinates]
                assert "VA" in sub_codes  # VulnerabilityAnalyst
                assert "ASE" in sub_codes  # AppSecEngineer
            elif manager.code == "CM":
                sub_codes = [s.code for s in manager.subordinates]
                assert "CA" in sub_codes  # ComplianceAnalyst
            elif manager.code == "SOCM":
                sub_codes = [s.code for s in manager.subordinates]
                assert "IR" in sub_codes  # IncidentResponder
                assert "SE" in sub_codes  # SecurityEngineer

    def test_sentinel_not_connected_by_default(self, cseco):
        """Test Sentinel is not connected by default."""
        assert cseco.sentinel_connected is False
        assert cseco._sentinel_bridge is None
        assert cseco._sentinel_engine is None

    def test_state_dictionaries_empty_on_creation(self, cseco):
        """Test all state dictionaries are empty on creation."""
        assert len(cseco.threats) == 0
        assert len(cseco.vulnerabilities) == 0
        assert len(cseco.scans) == 0
        assert len(cseco.incidents) == 0
        assert len(cseco.policies) == 0
        assert len(cseco.controls) == 0
        assert len(cseco.access_reviews) == 0

    def test_security_metrics_empty(self, cseco):
        """Test security metrics with no data."""
        metrics = cseco.get_security_metrics()

        assert metrics.open_vulnerabilities == 0
        assert metrics.critical_vulnerabilities == 0
        assert metrics.active_threats == 0
        assert metrics.open_incidents == 0
        assert metrics.compliance_score == 0

    def test_security_posture_empty(self, cseco):
        """Test security posture with no data."""
        posture = cseco.get_security_posture()

        assert posture["overall_score"] == 75.0  # (100 + 100 + 100 + 0) / 4
        assert posture["vulnerability_score"] == 100
        assert posture["threat_score"] == 100
        assert posture["incident_score"] == 100
        assert posture["sentinel_connected"] is False

    def test_sentinel_stats_not_initialized(self, cseco):
        """Test Sentinel stats when bridge is not initialized."""
        stats = cseco.get_sentinel_stats()

        assert stats["connected"] is False
        assert "not initialized" in stats["message"]

    def test_cseco_personality_seed(self):
        """Test Citadel personality seed traits are defined."""
        from ag3ntwerk.core.personality import PERSONALITY_SEEDS, DOMAIN_TRAIT_SEEDS

        assert "Citadel" in PERSONALITY_SEEDS
        seed = PERSONALITY_SEEDS["Citadel"]
        assert seed["risk"] == 0.1  # Very risk averse
        assert seed["thoroughness"] == 0.95  # Extremely thorough
        assert seed["decision"] == "analytical"
        assert seed["communication"] == "formal"

        # Citadel has domain-specific traits
        assert "Citadel" in DOMAIN_TRAIT_SEEDS
        domain = DOMAIN_TRAIT_SEEDS["Citadel"]
        assert domain["vigilance"] == 0.95
        assert domain["zero_trust_mindset"] == 0.9
        assert domain["compliance_rigor"] == 0.85


class TestCSecOExecute:
    """Tests for Citadel task execution."""

    @pytest.mark.asyncio
    async def test_execute_threat_detection(self, mock_llm_provider):
        """Test executing threat detection task."""
        cseco = Citadel(llm_provider=mock_llm_provider)

        task = Task(
            description="Detect threats in network traffic",
            task_type="threat_detection",
            context={
                "target": "production-network",
                "data_sources": ["firewall_logs", "ids_alerts"],
                "timeframe": "Last 24 hours",
            },
        )

        result = await cseco.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_threat_analysis(self, mock_llm_provider):
        """Test executing threat analysis task."""
        cseco = Citadel(llm_provider=mock_llm_provider)

        task = Task(
            description="Analyze APT activity targeting finance systems",
            task_type="threat_analysis",
            context={
                "attack_vector": "spear_phishing",
                "affected_systems": ["email_server", "file_server"],
            },
        )

        result = await cseco.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_vulnerability_scan(self, mock_llm_provider):
        """Test executing vulnerability scan task."""
        cseco = Citadel(llm_provider=mock_llm_provider)

        task = Task(
            description="Scan production infrastructure for vulnerabilities",
            task_type="vulnerability_scan",
            context={
                "target": "production-cluster",
                "scope": ["web-servers", "api-gateways"],
                "authenticated": True,
            },
        )

        result = await cseco.execute(task)

        assert result.success is True
        # Verify scan was registered in state
        assert len(cseco.scans) == 1

    @pytest.mark.asyncio
    async def test_execute_incident_response(self, mock_llm_provider):
        """Test executing incident response task."""
        cseco = Citadel(llm_provider=mock_llm_provider)

        task = Task(
            description="Respond to ransomware detected on workstation",
            task_type="incident_response",
            context={
                "title": "Ransomware Detection",
                "severity": "p1_critical",
                "category": "malware",
                "affected_systems": ["ws-042", "file-share-01"],
            },
        )

        result = await cseco.execute(task)

        assert result.success is True
        # Verify incident was registered
        assert len(cseco.incidents) == 1

    @pytest.mark.asyncio
    async def test_execute_compliance_assessment(self, mock_llm_provider):
        """Test executing compliance assessment task."""
        cseco = Citadel(llm_provider=mock_llm_provider)

        task = Task(
            description="Assess SOC2 compliance readiness",
            task_type="compliance_assessment",
            context={
                "framework": "SOC2",
                "scope": "Full organization",
            },
        )

        result = await cseco.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_code_review(self, mock_llm_provider):
        """Test executing security code review task."""
        cseco = Citadel(llm_provider=mock_llm_provider)

        task = Task(
            description="Security review of authentication module",
            task_type="code_review",
            context={
                "repository": "auth-service",
                "language": "Python",
                "focus_areas": ["authentication", "authorization", "input_validation"],
            },
        )

        result = await cseco.execute(task)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_access_review(self, mock_llm_provider):
        """Test executing access review task."""
        cseco = Citadel(llm_provider=mock_llm_provider)

        task = Task(
            description="Quarterly access review for admin accounts",
            task_type="access_review",
            context={
                "name": "Q1 Admin Access Review",
                "review_type": "privileged",
                "scope": ["admin-users"],
            },
        )

        result = await cseco.execute(task)

        assert result.success is True
        # Verify access review was registered
        assert len(cseco.access_reviews) == 1

    @pytest.mark.asyncio
    async def test_execute_sast_scan(self, mock_llm_provider):
        """Test executing SAST scan task."""
        cseco = Citadel(llm_provider=mock_llm_provider)

        task = Task(
            description="Static analysis of payment-service codebase",
            task_type="sast_scan",
            context={
                "repository": "payment-service",
                "language": "Python",
                "branch": "main",
            },
        )

        result = await cseco.execute(task)

        assert result.success is True
        assert len(cseco.scans) == 1

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self, mock_llm_provider):
        """Test handling of LLM errors during execution."""
        mock_llm_provider.generate = AsyncMock(side_effect=Exception("LLM Error"))

        cseco = Citadel(llm_provider=mock_llm_provider)

        task = Task(
            description="Detect threats",
            task_type="threat_detection",
            context={"target": "test"},
        )

        result = await cseco.execute(task)

        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_routes_to_manager_for_unknown_type(self, mock_llm_provider):
        """Test execution routes to manager for unhandled task types."""
        cseco = Citadel(llm_provider=mock_llm_provider)

        # A task type that has no direct handler and no sentinel mapping
        task = Task(
            description="Custom security task",
            task_type="custom_security_task",
        )

        result = await cseco.execute(task)

        # Should fail because no handler and no manager can handle it
        assert result.success is False

    @pytest.mark.asyncio
    async def test_sentinel_security_action_not_connected(self):
        """Test sentinel action when not connected."""
        cseco = Citadel()

        result = await cseco.sentinel_security_action("block_ip", {"ip": "192.168.1.1"})

        assert result["success"] is False
        assert "not connected" in result["error"]

    @pytest.mark.asyncio
    async def test_sentinel_health_check_not_connected(self):
        """Test sentinel health check when not connected."""
        cseco = Citadel()

        result = await cseco.sentinel_health_check()

        assert result["healthy"] is False
        assert "not connected" in result["error"]

    @pytest.mark.asyncio
    async def test_sentinel_discovery_scan_not_connected(self):
        """Test sentinel discovery scan when not connected."""
        cseco = Citadel()

        result = await cseco.sentinel_discovery_scan(network="10.0.0.0/24")

        assert result["success"] is False
        assert "not connected" in result["error"]

    @pytest.mark.asyncio
    async def test_sentinel_compliance_check_not_connected(self):
        """Test sentinel compliance check when not connected."""
        cseco = Citadel()

        result = await cseco.sentinel_compliance_check(framework="CIS")

        assert result["success"] is False
        assert "not connected" in result["error"]
