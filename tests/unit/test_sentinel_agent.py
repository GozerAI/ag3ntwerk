"""
Unit tests for Sentinel (Sentinel) agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.sentinel import Sentinel, Sentinel
from ag3ntwerk.agents.sentinel.managers import (
    DataGovernanceManager,
    ITSystemsManager,
    KnowledgeManager,
    VerificationManager,
)
from ag3ntwerk.agents.sentinel.specialists import (
    DataSteward,
    CloudComplianceAnalyst,
    PrivacyGovernanceOfficer,
    SecurityAnalyst,
    KnowledgeSpecialist,
    SystemsAnalyst,
)
from ag3ntwerk.core.base import Task, TaskStatus


class TestCIOAgent:
    """Tests for Sentinel agent."""

    def test_cio_creation(self):
        """Test Sentinel agent creation."""
        cio = Sentinel()

        assert cio.code == "Sentinel"
        assert cio.name == "Sentinel"
        assert cio.codename == "Sentinel"
        assert cio.domain == "Security, Compliance, Risk Management"

    def test_sentinel_alias(self):
        """Test Sentinel is an alias for Sentinel."""
        sentinel = Sentinel()

        assert sentinel.code == "Sentinel"
        assert sentinel.codename == "Sentinel"

    def test_cio_capabilities(self):
        """Test Sentinel has expected capabilities."""
        cio = Sentinel()

        expected_capabilities = [
            "security_scan",
            "vulnerability_check",
            "threat_analysis",
            "access_audit",
            "compliance_check",
            "incident_response",
            "security_review",
            "penetration_test",
            "risk_assessment",
        ]

        for cap in expected_capabilities:
            assert cap in cio.capabilities, f"Missing capability: {cap}"

    def test_can_handle_security_tasks(self):
        """Test Sentinel can handle security tasks."""
        cio = Sentinel()

        security_tasks = [
            "security_scan",
            "vulnerability_check",
            "threat_analysis",
            "compliance_check",
            "risk_assessment",
            "incident_response",
            "security_review",
        ]

        for task_type in security_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert cio.can_handle(task), f"Sentinel should handle {task_type}"

    def test_cannot_handle_non_security_tasks(self):
        """Test Sentinel doesn't handle non-security tasks."""
        cio = Sentinel()

        non_security_tasks = [
            "code_review",
            "campaign_creation",
            "cost_analysis",
            "feature_prioritization",
        ]

        for task_type in non_security_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert not cio.can_handle(task), f"Sentinel should not handle {task_type}"

    def test_incident_reporting(self):
        """Test incident reporting."""
        cio = Sentinel()

        incident = {
            "type": "data_breach",
            "severity": "high",
            "description": "Unauthorized access detected",
        }
        result = cio.report_incident(incident)

        assert "1 active incidents" in result
        assert len(cio._active_incidents) == 1
        assert cio._active_incidents[0]["status"] == "open"

    def test_get_security_status(self):
        """Test getting security status."""
        cio = Sentinel()

        # Report some incidents
        cio.report_incident({"type": "phishing", "severity": "medium"})
        cio.report_incident({"type": "malware", "severity": "high"})

        status = cio.get_security_status()

        assert status["active_incidents"] == 2
        assert status["threat_intel_entries"] == 0
        assert "capabilities" in status

    def test_subordinate_managers_registered(self):
        """Test that managers are registered as subordinates."""
        cio = Sentinel()

        # Sentinel should have 4 managers registered
        subordinate_codes = list(cio._subordinates.keys())

        assert "IDGM" in subordinate_codes  # DataGovernanceManager
        assert "ITSM" in subordinate_codes  # ITSystemsManager
        assert "IKM" in subordinate_codes  # KnowledgeManager
        assert "VM" in subordinate_codes  # VerificationManager


class TestCIOExecute:
    """Tests for Sentinel task execution."""

    @pytest.mark.asyncio
    async def test_execute_security_scan(self):
        """Test executing security scan task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Security scan complete")

        cio = Sentinel(llm_provider=mock_provider)

        task = Task(
            description="Scan auth module for vulnerabilities",
            task_type="security_scan",
            context={
                "target": "src/auth/",
            },
        )

        result = await cio.execute(task)

        assert result.success is True
        assert "scan_type" in result.output
        assert result.output["scan_type"] == "security_scan"
        assert result.output["target"] == "src/auth/"

    @pytest.mark.asyncio
    async def test_execute_vulnerability_check(self):
        """Test executing vulnerability check task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Vulnerability report")

        cio = Sentinel(llm_provider=mock_provider)

        task = Task(
            description="Check for known CVEs in dependencies",
            task_type="vulnerability_check",
            context={
                "target": "package.json",
            },
        )

        result = await cio.execute(task)

        assert result.success is True
        assert "check_type" in result.output
        assert result.output["check_type"] == "vulnerability"

    @pytest.mark.asyncio
    async def test_execute_threat_analysis(self):
        """Test executing threat analysis task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Threat model complete")

        cio = Sentinel(llm_provider=mock_provider)

        task = Task(
            description="Analyze threats to payment processing system",
            task_type="threat_analysis",
            context={
                "system": "payment_gateway",
                "threat_level": "high",
            },
        )

        result = await cio.execute(task)

        assert result.success is True
        assert "analysis_type" in result.output
        assert result.output["analysis_type"] == "threat"

    @pytest.mark.asyncio
    async def test_execute_compliance_check(self):
        """Test executing compliance check task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Compliance report")

        cio = Sentinel(llm_provider=mock_provider)

        task = Task(
            description="Check SOC 2 compliance",
            task_type="compliance_check",
            context={
                "framework": "SOC2",
                "scope": "all_systems",
            },
        )

        result = await cio.execute(task)

        assert result.success is True
        assert "check_type" in result.output
        assert result.output["check_type"] == "compliance"
        assert result.output["framework"] == "SOC2"

    @pytest.mark.asyncio
    async def test_execute_risk_assessment(self):
        """Test executing risk assessment task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Risk assessment complete")

        cio = Sentinel(llm_provider=mock_provider)

        task = Task(
            description="Assess risk of migrating to new cloud provider",
            task_type="risk_assessment",
            context={
                "assets": ["databases", "APIs", "user_data"],
            },
        )

        result = await cio.execute(task)

        assert result.success is True
        assert "assessment_type" in result.output
        assert result.output["assessment_type"] == "risk"

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self):
        """Test handling of LLM errors during execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=Exception("LLM Error"))

        cio = Sentinel(llm_provider=mock_provider)

        task = Task(
            description="Scan for vulnerabilities",
            task_type="security_scan",
            context={"target": "src/"},
        )

        result = await cio.execute(task)

        assert result.success is False
        assert "failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_without_provider(self):
        """Test execution without LLM provider."""
        cio = Sentinel(llm_provider=None)

        task = Task(
            description="Unknown security task",
            task_type="unknown_type",
        )

        result = await cio.execute(task)

        assert result.success is False
        assert "No LLM provider" in result.error

    @pytest.mark.asyncio
    async def test_execute_security_scan_without_provider(self):
        """Test security scan without LLM provider returns error."""
        cio = Sentinel(llm_provider=None)

        task = Task(
            description="Scan auth",
            task_type="security_scan",
            context={"target": "auth/"},
        )

        result = await cio.execute(task)

        assert result.success is False
        assert "No LLM provider" in result.error

    @pytest.mark.asyncio
    async def test_execute_fallback_to_llm_for_unhandled_type(self):
        """Test that unhandled security tasks fall back to LLM."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="LLM handled response")

        cio = Sentinel(llm_provider=mock_provider)

        task = Task(
            description="Respond to security incident",
            task_type="incident_response",
        )

        result = await cio.execute(task)

        # incident_response is a capability but has no dedicated handler,
        # so it falls through to _handle_with_llm
        assert result.success is True


class TestDataGovernanceManager:
    """Tests for DataGovernanceManager."""

    def test_manager_creation(self):
        """Test data governance manager creation."""
        manager = DataGovernanceManager()

        assert manager.code == "IDGM"
        assert manager.name == "Data Governance Manager"
        assert manager.domain == "Data Classification, Quality, Lifecycle Management"

    def test_can_handle_governance_tasks(self):
        """Test manager handles governance-related tasks."""
        manager = DataGovernanceManager()

        tasks = [
            "data_classification",
            "data_quality_check",
            "data_lineage",
            "data_catalog",
            "retention_management",
            "data_stewardship",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"


class TestITSystemsManager:
    """Tests for ITSystemsManager."""

    def test_manager_creation(self):
        """Test IT systems manager creation."""
        manager = ITSystemsManager()

        assert manager.code == "ITSM"
        assert manager.name == "IT Systems Manager"
        assert manager.domain == "IT Systems, Integrations, Health Monitoring"

    def test_can_handle_system_tasks(self):
        """Test manager handles system-related tasks."""
        manager = ITSystemsManager()

        tasks = [
            "system_inventory",
            "integration_management",
            "health_monitoring",
            "change_management",
            "capacity_planning",
            "vendor_management",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"


class TestKnowledgeManager:
    """Tests for KnowledgeManager."""

    def test_manager_creation(self):
        """Test knowledge manager creation."""
        manager = KnowledgeManager()

        assert manager.code == "IKM"
        assert manager.name == "Knowledge Manager"
        assert manager.domain == "Knowledge Creation, Retrieval, Curation"

    def test_can_handle_knowledge_tasks(self):
        """Test manager handles knowledge-related tasks."""
        manager = KnowledgeManager()

        tasks = [
            "knowledge_creation",
            "knowledge_retrieval",
            "knowledge_curation",
            "knowledge_sharing",
            "taxonomy_management",
            "expertise_mapping",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"


class TestVerificationManager:
    """Tests for VerificationManager."""

    def test_manager_creation(self):
        """Test verification manager creation."""
        manager = VerificationManager()

        assert manager.code == "VM"
        assert manager.name == "Verification Manager"
        assert manager.domain == "Truth Verification, Evidence, Decision Integrity"

    def test_can_handle_verification_tasks(self):
        """Test manager handles verification-related tasks."""
        manager = VerificationManager()

        tasks = [
            "truth_verification",
            "claim_validation",
            "evidence_collection",
            "decision_audit",
            "integrity_check",
            "source_verification",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"


class TestCloudComplianceAnalyst:
    """Tests for CloudComplianceAnalyst specialist."""

    def test_creation(self):
        """Test CCA creation."""
        cca = CloudComplianceAnalyst()
        assert cca.code == "CCA"
        assert cca.name == "Cloud Compliance Analyst"
        assert "Cloud Compliance" in cca.domain

    def test_capabilities(self):
        """Test CCA has expected capabilities."""
        cca = CloudComplianceAnalyst()
        expected = [
            "cloud_compliance_audit",
            "iac_validation",
            "multi_cloud_governance",
            "data_residency_check",
            "cloud_security_posture",
            "cost_compliance",
        ]
        for cap in expected:
            assert cap in cca.capabilities, f"Missing: {cap}"

    def test_can_handle_cloud_tasks(self):
        """Test CCA can handle cloud compliance tasks."""
        cca = CloudComplianceAnalyst()
        cloud_types = [
            "cloud_compliance_audit",
            "cloud_compliance",
            "iac_validation",
            "infrastructure_validation",
            "multi_cloud_governance",
            "data_residency_check",
            "data_residency",
            "cloud_security_posture",
            "cloud_security",
            "cost_compliance",
        ]
        for task_type in cloud_types:
            task = Task(description="Test", task_type=task_type)
            assert cca.can_handle(task), f"Should handle {task_type}"

    def test_cannot_handle_non_cloud_tasks(self):
        """Test CCA doesn't handle unrelated tasks."""
        cca = CloudComplianceAnalyst()
        for task_type in ["code_review", "data_quality_check", "security_scan"]:
            task = Task(description="Test", task_type=task_type)
            assert not cca.can_handle(task), f"Should not handle {task_type}"

    def test_handler_dispatch(self):
        """Test _get_handler routes correctly."""
        cca = CloudComplianceAnalyst()
        assert cca._get_handler("cloud_compliance_audit") is not None
        assert cca._get_handler("iac_validation") is not None
        assert cca._get_handler("multi_cloud_governance") is not None
        assert cca._get_handler("data_residency_check") is not None
        assert cca._get_handler("cloud_security_posture") is not None
        assert cca._get_handler("cost_compliance") is not None
        assert cca._get_handler("nonexistent") is None

    @pytest.mark.asyncio
    async def test_execute_cloud_compliance_audit(self):
        """Test executing cloud compliance audit."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Audit complete")
        cca = CloudComplianceAnalyst(llm_provider=mock_provider)

        task = Task(
            description="Audit AWS compliance",
            task_type="cloud_compliance_audit",
            context={"provider": "aws", "framework": "CIS"},
        )
        result = await cca.execute(task)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_iac_validation(self):
        """Test executing IaC validation."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="IaC validated")
        cca = CloudComplianceAnalyst(llm_provider=mock_provider)

        task = Task(
            description="Validate Terraform modules",
            task_type="iac_validation",
            context={"tool": "terraform", "path": "infra/"},
        )
        result = await cca.execute(task)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_without_provider(self):
        """Test execution without LLM provider."""
        cca = CloudComplianceAnalyst(llm_provider=None)
        task = Task(description="Test", task_type="cloud_compliance_audit")
        result = await cca.execute(task)
        assert result.success is False


class TestPrivacyGovernanceOfficer:
    """Tests for PrivacyGovernanceOfficer specialist."""

    def test_creation(self):
        """Test PGO creation."""
        pgo = PrivacyGovernanceOfficer()
        assert pgo.code == "PGO"
        assert pgo.name == "Privacy Governance Officer"
        assert "Privacy" in pgo.domain

    def test_capabilities(self):
        """Test PGO has expected capabilities."""
        pgo = PrivacyGovernanceOfficer()
        expected = [
            "privacy_impact_assessment",
            "data_subject_rights",
            "consent_management",
            "privacy_compliance",
            "data_processor_audit",
            "breach_assessment",
        ]
        for cap in expected:
            assert cap in pgo.capabilities, f"Missing: {cap}"

    def test_can_handle_privacy_tasks(self):
        """Test PGO can handle privacy tasks."""
        pgo = PrivacyGovernanceOfficer()
        privacy_types = [
            "privacy_impact_assessment",
            "privacy_assessment",
            "data_subject_rights",
            "data_subject_request",
            "consent_management",
            "consent_audit",
            "privacy_compliance",
            "privacy_audit",
            "data_processor_audit",
            "breach_assessment",
            "breach_notification",
        ]
        for task_type in privacy_types:
            task = Task(description="Test", task_type=task_type)
            assert pgo.can_handle(task), f"Should handle {task_type}"

    def test_cannot_handle_non_privacy_tasks(self):
        """Test PGO doesn't handle unrelated tasks."""
        pgo = PrivacyGovernanceOfficer()
        for task_type in ["code_review", "cloud_compliance", "security_scan"]:
            task = Task(description="Test", task_type=task_type)
            assert not pgo.can_handle(task), f"Should not handle {task_type}"

    def test_handler_dispatch(self):
        """Test _get_handler routes correctly."""
        pgo = PrivacyGovernanceOfficer()
        assert pgo._get_handler("privacy_impact_assessment") is not None
        assert pgo._get_handler("data_subject_rights") is not None
        assert pgo._get_handler("consent_management") is not None
        assert pgo._get_handler("privacy_compliance") is not None
        assert pgo._get_handler("data_processor_audit") is not None
        assert pgo._get_handler("breach_assessment") is not None
        assert pgo._get_handler("nonexistent") is None

    @pytest.mark.asyncio
    async def test_execute_privacy_impact_assessment(self):
        """Test executing privacy impact assessment."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="PIA complete")
        pgo = PrivacyGovernanceOfficer(llm_provider=mock_provider)

        task = Task(
            description="Assess user tracking feature",
            task_type="privacy_impact_assessment",
            context={"regulation": "GDPR", "data_types": ["email", "location"]},
        )
        result = await pgo.execute(task)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_breach_assessment(self):
        """Test executing breach assessment."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Breach assessed")
        pgo = PrivacyGovernanceOfficer(llm_provider=mock_provider)

        task = Task(
            description="Assess data breach impact",
            task_type="breach_assessment",
            context={"records_affected": 5000, "data_types": ["PII"]},
        )
        result = await pgo.execute(task)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_without_provider(self):
        """Test execution without LLM provider."""
        pgo = PrivacyGovernanceOfficer(llm_provider=None)
        task = Task(description="Test", task_type="privacy_impact_assessment")
        result = await pgo.execute(task)
        assert result.success is False
