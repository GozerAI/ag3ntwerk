"""
Unit tests for Accord (Accord) agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from ag3ntwerk.agents.accord import Accord, Accord
from ag3ntwerk.agents.accord.models import (
    Regulation,
    ComplianceRequirement,
    ComplianceStatus,
    RegulatoryFramework,
    Policy,
    PolicyStatus,
    Audit,
    AuditType,
    AuditStatus,
    AuditFinding,
    FindingSeverity,
    FindingStatus,
    License,
    ComplianceAssessment,
    EthicsCase,
)
from ag3ntwerk.core.base import Task, TaskStatus


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class TestCComOModels:
    """Test Accord data models."""

    def test_regulation_creation(self):
        reg = Regulation(
            id="gdpr",
            name="General Data Protection Regulation",
            framework=RegulatoryFramework.GDPR,
            jurisdiction="EU",
            regulatory_body="European Commission",
        )
        assert reg.id == "gdpr"
        assert reg.framework == RegulatoryFramework.GDPR

    def test_compliance_requirement_creation(self):
        req = ComplianceRequirement(
            id="req1",
            name="Data Subject Access Request",
            framework=RegulatoryFramework.GDPR,
            control_reference="GDPR Art. 15",
            status=ComplianceStatus.COMPLIANT,
        )
        assert req.id == "req1"
        assert req.status == ComplianceStatus.COMPLIANT
        assert req.is_overdue is False

    def test_compliance_requirement_overdue(self):
        req = ComplianceRequirement(
            id="req1",
            name="Overdue Requirement",
            status=ComplianceStatus.PENDING,
            due_date=_utcnow() - timedelta(days=1),
        )
        assert req.is_overdue is True

    def test_compliance_requirement_not_overdue_when_compliant(self):
        req = ComplianceRequirement(
            id="req1",
            name="Compliant Requirement",
            status=ComplianceStatus.COMPLIANT,
            due_date=_utcnow() - timedelta(days=1),
        )
        assert req.is_overdue is False

    def test_policy_creation(self):
        policy = Policy(
            id="pol1",
            name="Information Security Policy",
            policy_type="security",
            status=PolicyStatus.ACTIVE,
            version="2.0",
        )
        assert policy.id == "pol1"
        assert policy.status == PolicyStatus.ACTIVE

    def test_policy_needs_review(self):
        policy = Policy(
            id="pol1",
            name="Old Policy",
            review_date=_utcnow() - timedelta(days=1),
        )
        assert policy.needs_review is True

    def test_policy_is_expired(self):
        policy = Policy(
            id="pol1",
            name="Expired Policy",
            expiration_date=_utcnow() - timedelta(days=1),
        )
        assert policy.is_expired is True

    def test_audit_creation(self):
        audit = Audit(
            id="aud1",
            name="SOC 2 Type II Audit",
            audit_type=AuditType.CERTIFICATION,
            status=AuditStatus.PLANNED,
            framework=RegulatoryFramework.SOC2,
        )
        assert audit.id == "aud1"
        assert audit.audit_type == AuditType.CERTIFICATION

    def test_audit_finding_creation(self):
        finding = AuditFinding(
            id="f1",
            audit_id="aud1",
            title="Missing Access Controls",
            severity=FindingSeverity.HIGH,
            status=FindingStatus.OPEN,
        )
        assert finding.severity == FindingSeverity.HIGH
        assert finding.status == FindingStatus.OPEN

    def test_audit_finding_overdue(self):
        finding = AuditFinding(
            id="f1",
            audit_id="aud1",
            title="Overdue Finding",
            status=FindingStatus.OPEN,
            due_date=_utcnow() - timedelta(days=1),
        )
        assert finding.is_overdue is True

    def test_audit_finding_not_overdue_when_closed(self):
        finding = AuditFinding(
            id="f1",
            audit_id="aud1",
            title="Closed Finding",
            status=FindingStatus.CLOSED,
            due_date=_utcnow() - timedelta(days=1),
        )
        assert finding.is_overdue is False

    def test_license_creation(self):
        lic = License(
            id="lic1",
            name="Software License",
            license_type="software",
            issuing_authority="Vendor Inc",
            expiration_date=_utcnow() + timedelta(days=30),
        )
        assert lic.id == "lic1"
        assert lic.is_expired is False

    def test_license_needs_renewal(self):
        lic = License(
            id="lic1",
            name="Expiring License",
            renewal_lead_days=90,
            expiration_date=_utcnow() + timedelta(days=30),
        )
        assert lic.needs_renewal is True

    def test_license_days_until_expiration(self):
        lic = License(
            id="lic1",
            name="Active License",
            expiration_date=_utcnow() + timedelta(days=45),
        )
        days = lic.days_until_expiration
        assert days is not None
        assert 44 <= days <= 46

    def test_compliance_assessment_score(self):
        assessment = ComplianceAssessment(
            id="ca1",
            name="GDPR Assessment",
            framework=RegulatoryFramework.GDPR,
            requirements_assessed=100,
            requirements_compliant=70,
            requirements_partial=20,
            requirements_non_compliant=10,
            requirements_na=0,
        )
        # Score = (70 + 20*0.5) / 100 * 100 = 80%
        assert assessment.compliance_score == 80.0

    def test_compliance_assessment_score_with_na(self):
        assessment = ComplianceAssessment(
            id="ca1",
            name="Assessment",
            framework=RegulatoryFramework.CUSTOM,
            requirements_assessed=100,
            requirements_compliant=80,
            requirements_partial=0,
            requirements_non_compliant=0,
            requirements_na=20,
        )
        # Score = 80 / (100 - 20) * 100 = 100%
        assert assessment.compliance_score == 100.0

    def test_ethics_case_creation(self):
        case = EthicsCase(
            id="eth1",
            title="Conflict of Interest",
            case_type="conflict_of_interest",
            status="investigating",
            is_anonymous=True,
        )
        assert case.id == "eth1"
        assert case.is_anonymous is True


class TestCComOAgent:
    """Test Accord agent functionality."""

    @pytest.fixture
    def ccomo(self, mock_llm_provider):
        return Accord(llm_provider=mock_llm_provider)

    def test_ccomo_initialization(self, ccomo):
        assert ccomo.code == "Accord"
        assert ccomo.codename == "Accord"
        assert ccomo.name == "Accord"

    def test_ccomo_alias(self):
        assert Accord == Accord

    def test_ccomo_capabilities(self, ccomo):
        assert "compliance_assessment" in ccomo.capabilities
        assert "policy_review" in ccomo.capabilities
        assert "audit_planning" in ccomo.capabilities
        assert "ethics_review" in ccomo.capabilities

    def test_can_handle_compliance(self, ccomo):
        task = Task(description="Assess compliance", task_type="compliance_assessment")
        assert ccomo.can_handle(task) is True

    def test_can_handle_policy(self, ccomo):
        task = Task(description="Review policy", task_type="policy_review")
        assert ccomo.can_handle(task) is True

    def test_cannot_handle_code_review(self, ccomo):
        task = Task(description="Review code", task_type="code_review")
        assert ccomo.can_handle(task) is False

    def test_register_regulation(self, ccomo):
        reg = Regulation(id="reg1", name="Test Regulation")
        result = ccomo.register_regulation(reg)
        assert result == "reg1"

    def test_register_requirement(self, ccomo):
        req = ComplianceRequirement(id="req1", name="Test Requirement")
        result = ccomo.register_requirement(req)
        assert result == "req1"

    def test_register_policy(self, ccomo):
        policy = Policy(id="pol1", name="Test Policy")
        result = ccomo.register_policy(policy)
        assert result == "pol1"
        assert ccomo.get_policy("pol1") is not None

    def test_register_audit(self, ccomo):
        audit = Audit(id="aud1", name="Test Audit")
        result = ccomo.register_audit(audit)
        assert result == "aud1"

    def test_register_finding(self, ccomo):
        finding = AuditFinding(id="f1", audit_id="aud1", title="Test Finding")
        result = ccomo.register_finding(finding)
        assert result == "f1"

    def test_register_license(self, ccomo):
        lic = License(id="lic1", name="Test License")
        result = ccomo.register_license(lic)
        assert result == "lic1"

    def test_get_policies_by_status(self, ccomo):
        ccomo.register_policy(Policy(id="p1", name="Active", status=PolicyStatus.ACTIVE))
        ccomo.register_policy(Policy(id="p2", name="Draft", status=PolicyStatus.DRAFT))
        ccomo.register_policy(Policy(id="p3", name="Active 2", status=PolicyStatus.ACTIVE))

        active = ccomo.get_policies_by_status(PolicyStatus.ACTIVE)
        assert len(active) == 2

    def test_get_overdue_requirements(self, ccomo):
        ccomo.register_requirement(
            ComplianceRequirement(
                id="r1",
                name="Overdue",
                status=ComplianceStatus.PENDING,
                due_date=_utcnow() - timedelta(days=1),
            )
        )
        ccomo.register_requirement(
            ComplianceRequirement(
                id="r2",
                name="On Time",
                status=ComplianceStatus.PENDING,
                due_date=_utcnow() + timedelta(days=30),
            )
        )

        overdue = ccomo.get_overdue_requirements()
        assert len(overdue) == 1

    def test_get_open_findings(self, ccomo):
        ccomo.register_finding(
            AuditFinding(id="f1", audit_id="a1", title="Open", status=FindingStatus.OPEN)
        )
        ccomo.register_finding(
            AuditFinding(id="f2", audit_id="a1", title="Closed", status=FindingStatus.CLOSED)
        )
        ccomo.register_finding(
            AuditFinding(
                id="f3", audit_id="a1", title="In Remediation", status=FindingStatus.IN_REMEDIATION
            )
        )

        open_findings = ccomo.get_open_findings()
        assert len(open_findings) == 2

    def test_get_expiring_licenses(self, ccomo):
        ccomo.register_license(
            License(
                id="l1",
                name="Expiring",
                renewal_lead_days=90,
                expiration_date=_utcnow() + timedelta(days=30),
            )
        )
        ccomo.register_license(
            License(
                id="l2",
                name="Not Expiring",
                renewal_lead_days=30,
                expiration_date=_utcnow() + timedelta(days=365),
            )
        )

        expiring = ccomo.get_expiring_licenses()
        assert len(expiring) == 1

    def test_compliance_status(self, ccomo):
        ccomo.register_regulation(Regulation(id="r1", name="Reg 1"))
        ccomo.register_requirement(
            ComplianceRequirement(id="req1", name="Req 1", status=ComplianceStatus.COMPLIANT)
        )
        ccomo.register_policy(Policy(id="p1", name="Policy 1", status=PolicyStatus.ACTIVE))

        status = ccomo.get_compliance_status()

        assert status["regulations_tracked"] == 1
        assert status["requirements"]["total"] == 1
        assert status["policies"]["total"] == 1

    @pytest.mark.asyncio
    async def test_execute_compliance_assessment(self, ccomo, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Compliance assessment complete")
        )

        task = Task(
            description="Assess GDPR compliance",
            task_type="compliance_assessment",
            context={"framework": "gdpr", "scope": "customer_data"},
        )

        result = await ccomo.execute(task)

        assert result.success is True
        assert result.output["framework"] == "gdpr"

    @pytest.mark.asyncio
    async def test_execute_policy_review(self, ccomo, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Policy review complete")
        )

        task = Task(
            description="Review security policy",
            task_type="policy_review",
            context={"policy_name": "Information Security Policy"},
        )

        result = await ccomo.execute(task)

        assert result.success is True
        assert result.output["review_type"] == "policy"

    @pytest.mark.asyncio
    async def test_execute_audit_planning(self, ccomo, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Audit plan created"))

        task = Task(
            description="Plan SOC 2 audit",
            task_type="audit_planning",
            context={"audit_type": "external", "scope": "security_controls"},
        )

        result = await ccomo.execute(task)

        assert result.success is True
        assert result.output["plan_type"] == "audit"

    @pytest.mark.asyncio
    async def test_execute_ethics_review(self, ccomo, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Ethics review complete")
        )

        task = Task(
            description="Review potential conflict",
            task_type="ethics_review",
            context={"matter": "vendor relationship"},
        )

        result = await ccomo.execute(task)

        assert result.success is True
        assert result.output["review_type"] == "ethics"

    @pytest.mark.asyncio
    async def test_execute_no_llm_provider(self):
        ccomo = Accord()  # No LLM provider

        task = Task(
            description="Custom task",
            task_type="unknown_task",
        )

        result = await ccomo.execute(task)

        assert result.success is False
        assert "No LLM provider" in result.error
