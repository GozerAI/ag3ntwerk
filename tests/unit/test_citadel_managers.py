"""
Unit tests for Citadel (Citadel) managers and specialists.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.citadel import (
    Citadel,
    ThreatManager,
    VulnerabilityManager,
    ComplianceManager,
    SOCManager,
    ThreatHunter,
    VulnerabilityAnalyst,
    IncidentResponder,
    ComplianceAnalyst,
    SecurityEngineer,
    AppSecEngineer,
)
from ag3ntwerk.core.base import Task, TaskStatus


class TestThreatManager:
    """Test ThreatManager functionality."""

    @pytest.fixture
    def tm(self, mock_llm_provider):
        return ThreatManager(llm_provider=mock_llm_provider)

    def test_tm_initialization(self, tm):
        assert tm.code == "TM"
        assert tm.name == "Threat Manager"
        assert "threat_detection" in tm.capabilities
        assert "threat_hunting" in tm.capabilities

    def test_tm_can_handle_detection(self, tm):
        task = Task(description="Detect threats", task_type="threat_detection")
        assert tm.can_handle(task) is True

    def test_tm_cannot_handle_vulnerability(self, tm):
        task = Task(description="Scan vulnerabilities", task_type="vulnerability_scan")
        assert tm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_tm_execute(self, tm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Threat detected"))

        task = Task(
            description="Detect APT activity",
            task_type="threat_detection",
            context={"scope": "network"},
        )

        result = await tm.execute(task)
        assert result.success is True


class TestVulnerabilityManager:
    """Test VulnerabilityManager functionality."""

    @pytest.fixture
    def vm(self, mock_llm_provider):
        return VulnerabilityManager(llm_provider=mock_llm_provider)

    def test_vm_initialization(self, vm):
        assert vm.code == "VM"
        assert vm.name == "Vulnerability Manager"
        assert "vulnerability_scan" in vm.capabilities
        assert "patch_management" in vm.capabilities

    def test_vm_can_handle_scan(self, vm):
        task = Task(description="Scan vulnerabilities", task_type="vulnerability_scan")
        assert vm.can_handle(task) is True

    def test_vm_cannot_handle_incident(self, vm):
        task = Task(description="Respond to incident", task_type="incident_response")
        assert vm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_vm_execute(self, vm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Vulnerability scan complete")
        )

        task = Task(
            description="Scan API for vulnerabilities",
            task_type="vulnerability_scan",
            context={"target": "api.example.com"},
        )

        result = await vm.execute(task)
        assert result.success is True


class TestComplianceManager:
    """Test ComplianceManager functionality."""

    @pytest.fixture
    def cm(self, mock_llm_provider):
        return ComplianceManager(llm_provider=mock_llm_provider)

    def test_cm_initialization(self, cm):
        assert cm.code == "CM"
        assert cm.name == "Compliance Manager"
        assert "compliance_assessment" in cm.capabilities
        assert "policy_management" in cm.capabilities

    def test_cm_can_handle_assessment(self, cm):
        task = Task(description="Assess compliance", task_type="compliance_assessment")
        assert cm.can_handle(task) is True

    def test_cm_cannot_handle_threat(self, cm):
        task = Task(description="Hunt threats", task_type="threat_hunting")
        assert cm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_cm_execute(self, cm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Compliance assessment complete")
        )

        task = Task(
            description="Assess SOC2 compliance",
            task_type="compliance_assessment",
            context={"framework": "SOC2"},
        )

        result = await cm.execute(task)
        assert result.success is True


class TestSOCManager:
    """Test SOCManager functionality."""

    @pytest.fixture
    def socm(self, mock_llm_provider):
        return SOCManager(llm_provider=mock_llm_provider)

    def test_socm_initialization(self, socm):
        assert socm.code == "SOCM"
        assert socm.name == "SOC Manager"
        assert "incident_response" in socm.capabilities
        assert "security_monitoring" in socm.capabilities

    def test_socm_can_handle_incident(self, socm):
        task = Task(description="Respond to incident", task_type="incident_response")
        assert socm.can_handle(task) is True

    def test_socm_cannot_handle_compliance(self, socm):
        task = Task(description="Audit compliance", task_type="compliance_audit")
        assert socm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_socm_execute(self, socm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Incident response initiated")
        )

        task = Task(
            description="Respond to security incident",
            task_type="incident_response",
            context={"severity": "high"},
        )

        result = await socm.execute(task)
        assert result.success is True


class TestThreatHunter:
    """Test ThreatHunter specialist."""

    @pytest.fixture
    def th(self, mock_llm_provider):
        return ThreatHunter(llm_provider=mock_llm_provider)

    def test_th_initialization(self, th):
        assert th.code == "TH"
        assert th.name == "Threat Hunter"
        assert "threat_hunting" in th.capabilities

    def test_th_can_handle(self, th):
        task = Task(description="Hunt threats", task_type="threat_hunting")
        assert th.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_th_execute(self, th, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Threat hunt complete")
        )

        task = Task(
            description="Hunt for APT activity",
            task_type="threat_hunting",
        )

        result = await th.execute(task)
        assert result.success is True


class TestVulnerabilityAnalyst:
    """Test VulnerabilityAnalyst specialist."""

    @pytest.fixture
    def va(self, mock_llm_provider):
        return VulnerabilityAnalyst(llm_provider=mock_llm_provider)

    def test_va_initialization(self, va):
        assert va.code == "VA"
        assert va.name == "Vulnerability Analyst"
        assert "vulnerability_analysis" in va.capabilities

    def test_va_can_handle(self, va):
        task = Task(description="Analyze vulnerability", task_type="vulnerability_analysis")
        assert va.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_va_execute(self, va, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Vulnerability analysis complete")
        )

        task = Task(
            description="Analyze CVE-2024-1234",
            task_type="vulnerability_analysis",
        )

        result = await va.execute(task)
        assert result.success is True


class TestIncidentResponder:
    """Test IncidentResponder specialist."""

    @pytest.fixture
    def ir(self, mock_llm_provider):
        return IncidentResponder(llm_provider=mock_llm_provider)

    def test_ir_initialization(self, ir):
        assert ir.code == "IR"
        assert ir.name == "Incident Responder"
        assert "incident_triage" in ir.capabilities

    def test_ir_can_handle(self, ir):
        task = Task(description="Triage incident", task_type="incident_triage")
        assert ir.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_ir_execute(self, ir, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Incident triaged"))

        task = Task(
            description="Triage security incident",
            task_type="incident_triage",
        )

        result = await ir.execute(task)
        assert result.success is True


class TestComplianceAnalyst:
    """Test ComplianceAnalyst specialist."""

    @pytest.fixture
    def ca(self, mock_llm_provider):
        return ComplianceAnalyst(llm_provider=mock_llm_provider)

    def test_ca_initialization(self, ca):
        assert ca.code == "CA"
        assert ca.name == "Compliance Analyst"
        assert "compliance_assessment" in ca.capabilities

    def test_ca_can_handle(self, ca):
        task = Task(description="Assess compliance", task_type="compliance_assessment")
        assert ca.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_ca_execute(self, ca, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Compliance assessed")
        )

        task = Task(
            description="Assess ISO27001 compliance",
            task_type="compliance_assessment",
        )

        result = await ca.execute(task)
        assert result.success is True


class TestSecurityEngineer:
    """Test SecurityEngineer specialist."""

    @pytest.fixture
    def se(self, mock_llm_provider):
        return SecurityEngineer(llm_provider=mock_llm_provider)

    def test_se_initialization(self, se):
        assert se.code == "SE"
        assert se.name == "Security Engineer"
        assert "detection_engineering" in se.capabilities

    def test_se_can_handle(self, se):
        task = Task(description="Engineer detection", task_type="detection_engineering")
        assert se.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_se_execute(self, se, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Detection rule created")
        )

        task = Task(
            description="Create detection rule",
            task_type="detection_engineering",
        )

        result = await se.execute(task)
        assert result.success is True


class TestAppSecEngineer:
    """Test AppSecEngineer specialist."""

    @pytest.fixture
    def ase(self, mock_llm_provider):
        return AppSecEngineer(llm_provider=mock_llm_provider)

    def test_ase_initialization(self, ase):
        assert ase.code == "ASE"
        assert ase.name == "AppSec Engineer"
        assert "code_review" in ase.capabilities

    def test_ase_can_handle(self, ase):
        task = Task(description="Review code", task_type="code_review")
        assert ase.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_ase_execute(self, ase, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Code review complete")
        )

        task = Task(
            description="Security code review",
            task_type="code_review",
        )

        result = await ase.execute(task)
        assert result.success is True


class TestCSecOManagerHierarchy:
    """Test Citadel manager and specialist hierarchy."""

    @pytest.fixture
    def cseco(self, mock_llm_provider):
        return Citadel(llm_provider=mock_llm_provider)

    def test_cseco_initialization(self, cseco):
        assert cseco.code == "Citadel"
        assert cseco.name == "Citadel"
        assert cseco.codename == "Citadel"

    def test_cseco_has_managers(self, cseco):
        """Test that Citadel has registered managers."""
        assert len(cseco.subordinates) == 4

        manager_codes = [m.code for m in cseco.subordinates]
        assert "TM" in manager_codes
        assert "VM" in manager_codes
        assert "CM" in manager_codes
        assert "SOCM" in manager_codes

    def test_tm_has_specialists(self, cseco):
        """Test that ThreatManager has specialists."""
        tm = cseco.get_subordinate("TM")
        assert tm is not None

        specialist_codes = [s.code for s in tm.subordinates]
        assert "TH" in specialist_codes

    def test_vm_has_specialists(self, cseco):
        """Test that VulnerabilityManager has specialists."""
        vm = cseco.get_subordinate("VM")
        assert vm is not None

        specialist_codes = [s.code for s in vm.subordinates]
        assert "VA" in specialist_codes
        assert "ASE" in specialist_codes

    def test_cm_has_specialists(self, cseco):
        """Test that ComplianceManager has specialists."""
        cm = cseco.get_subordinate("CM")
        assert cm is not None

        specialist_codes = [s.code for s in cm.subordinates]
        assert "CA" in specialist_codes

    def test_socm_has_specialists(self, cseco):
        """Test that SOCManager has specialists."""
        socm = cseco.get_subordinate("SOCM")
        assert socm is not None

        specialist_codes = [s.code for s in socm.subordinates]
        assert "IR" in specialist_codes
        assert "SE" in specialist_codes

    def test_cseco_can_handle_threat(self, cseco):
        """Test Citadel can handle threat tasks."""
        task = Task(description="Detect threats", task_type="threat_detection")
        assert cseco.can_handle(task) is True

    def test_cseco_can_handle_vulnerability(self, cseco):
        """Test Citadel can handle vulnerability tasks."""
        task = Task(description="Scan vulnerabilities", task_type="vulnerability_scan")
        assert cseco.can_handle(task) is True

    def test_cseco_can_handle_incident(self, cseco):
        """Test Citadel can handle incident tasks."""
        task = Task(description="Respond to incident", task_type="incident_response")
        assert cseco.can_handle(task) is True

    def test_cseco_can_handle_compliance(self, cseco):
        """Test Citadel can handle compliance tasks."""
        task = Task(description="Assess compliance", task_type="compliance_assessment")
        assert cseco.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_cseco_delegate_to_manager(self, cseco, mock_llm_provider):
        """Test delegation from Citadel to manager."""
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Task delegated"))

        task = Task(
            description="Hunt for threats",
            task_type="threat_hunting",
        )

        result = await cseco.delegate(task, "TM")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_cseco_execute_threat_task(self, cseco, mock_llm_provider):
        """Test Citadel execute threat task."""
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Threat detected and analyzed")
        )

        task = Task(
            description="Detect and analyze threats",
            task_type="threat_detection",
            context={"scope": "entire_network"},
        )

        result = await cseco.execute(task)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_cseco_execute_incident_task(self, cseco, mock_llm_provider):
        """Test Citadel execute incident task."""
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Incident response complete")
        )

        task = Task(
            description="Respond to ransomware incident",
            task_type="incident_response",
            context={"severity": "p1_critical", "category": "ransomware"},
        )

        result = await cseco.execute(task)
        assert result.success is True

    def test_cseco_sentinel_not_connected(self, cseco):
        """Test Sentinel is not connected by default."""
        assert cseco.sentinel_connected is False

    def test_cseco_security_posture(self, cseco):
        """Test security posture tracking."""
        posture = cseco.get_security_posture()

        assert posture is not None
        assert "overall_score" in posture
        assert "sentinel_connected" in posture
        assert "metrics" in posture

    def test_cseco_security_metrics(self, cseco):
        """Test security metrics tracking."""
        metrics = cseco.get_security_metrics()

        assert metrics is not None
        assert hasattr(metrics, "open_vulnerabilities")
        assert hasattr(metrics, "active_threats")
        assert hasattr(metrics, "open_incidents")
        assert hasattr(metrics, "compliance_score")
