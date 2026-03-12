"""
Unit tests for Accord (Accord) managers and specialists.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.accord import (
    Accord,
    ComplianceManager,
    PolicyManager,
    AuditManager,
    EthicsManager,
    LicenseManager,
    ComplianceAnalyst,
    PolicyAnalyst,
    AuditCoordinator,
    EthicsOfficer,
    TrainingCoordinator,
)
from ag3ntwerk.core.base import Task, TaskStatus


class TestComplianceManager:
    """Test ComplianceManager functionality."""

    @pytest.fixture
    def cm(self, mock_llm_provider):
        return ComplianceManager(llm_provider=mock_llm_provider)

    def test_cm_initialization(self, cm):
        assert cm.code == "CPLM"
        assert cm.name == "Compliance Manager"
        assert "compliance_assessment" in cm.capabilities
        assert "compliance_monitoring" in cm.capabilities

    def test_cm_can_handle_assessment(self, cm):
        task = Task(description="Assess compliance", task_type="compliance_assessment")
        assert cm.can_handle(task) is True

    def test_cm_cannot_handle_policy_creation(self, cm):
        task = Task(description="Create policy", task_type="policy_creation")
        assert cm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_cm_execute(self, cm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Compliance assessment complete")
        )

        task = Task(
            description="Assess GDPR compliance",
            task_type="compliance_assessment",
            context={"framework": "gdpr"},
        )

        result = await cm.execute(task)
        assert result.success is True


class TestPolicyManager:
    """Test PolicyManager functionality."""

    @pytest.fixture
    def pm(self, mock_llm_provider):
        return PolicyManager(llm_provider=mock_llm_provider)

    def test_pm_initialization(self, pm):
        assert pm.code == "POLM"
        assert pm.name == "Policy Manager"
        assert "policy_review" in pm.capabilities
        assert "policy_creation" in pm.capabilities

    def test_pm_can_handle_review(self, pm):
        task = Task(description="Review policy", task_type="policy_review")
        assert pm.can_handle(task) is True

    def test_pm_cannot_handle_audit(self, pm):
        task = Task(description="Plan audit", task_type="audit_planning")
        assert pm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_pm_execute(self, pm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Policy review complete")
        )

        task = Task(
            description="Review security policy",
            task_type="policy_review",
            context={"policy_name": "InfoSec Policy"},
        )

        result = await pm.execute(task)
        assert result.success is True


class TestAuditManager:
    """Test AuditManager functionality."""

    @pytest.fixture
    def aum(self, mock_llm_provider):
        return AuditManager(llm_provider=mock_llm_provider)

    def test_aum_initialization(self, aum):
        assert aum.code == "AUM"
        assert aum.name == "Audit Manager"
        assert "audit_planning" in aum.capabilities
        assert "audit_preparation" in aum.capabilities

    def test_aum_can_handle_planning(self, aum):
        task = Task(description="Plan audit", task_type="audit_planning")
        assert aum.can_handle(task) is True

    def test_aum_cannot_handle_ethics(self, aum):
        task = Task(description="Ethics review", task_type="ethics_review")
        assert aum.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_aum_execute(self, aum, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Audit plan created"))

        task = Task(
            description="Plan SOC 2 audit",
            task_type="audit_planning",
            context={"audit_type": "external"},
        )

        result = await aum.execute(task)
        assert result.success is True


class TestEthicsManager:
    """Test EthicsManager functionality."""

    @pytest.fixture
    def em(self, mock_llm_provider):
        return EthicsManager(llm_provider=mock_llm_provider)

    def test_em_initialization(self, em):
        assert em.code == "EM"
        assert em.name == "Ethics Manager"
        assert "ethics_review" in em.capabilities
        assert "conflict_of_interest" in em.capabilities

    def test_em_can_handle_ethics(self, em):
        task = Task(description="Ethics review", task_type="ethics_review")
        assert em.can_handle(task) is True

    def test_em_cannot_handle_audit(self, em):
        task = Task(description="Plan audit", task_type="audit_planning")
        assert em.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_em_execute(self, em, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Ethics review complete")
        )

        task = Task(
            description="Review conflict of interest",
            task_type="conflict_of_interest",
            context={"situation": "vendor relationship"},
        )

        result = await em.execute(task)
        assert result.success is True


class TestLicenseManager:
    """Test LicenseManager functionality."""

    @pytest.fixture
    def lm(self, mock_llm_provider):
        return LicenseManager(llm_provider=mock_llm_provider)

    def test_lm_initialization(self, lm):
        assert lm.code == "LM"
        assert lm.name == "License Manager"
        assert "license_tracking" in lm.capabilities
        assert "license_renewal" in lm.capabilities

    def test_lm_can_handle_tracking(self, lm):
        task = Task(description="Track licenses", task_type="license_tracking")
        assert lm.can_handle(task) is True

    def test_lm_cannot_handle_compliance(self, lm):
        task = Task(description="Assess compliance", task_type="compliance_assessment")
        assert lm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_lm_execute(self, lm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="License tracking complete")
        )

        task = Task(
            description="Track software licenses",
            task_type="license_tracking",
            context={"license_type": "software"},
        )

        result = await lm.execute(task)
        assert result.success is True


class TestComplianceAnalyst:
    """Test ComplianceAnalyst specialist."""

    @pytest.fixture
    def can(self, mock_llm_provider):
        return ComplianceAnalyst(llm_provider=mock_llm_provider)

    def test_can_initialization(self, can):
        assert can.code == "CAN"
        assert can.name == "Compliance Analyst"
        assert "compliance_assessment" in can.capabilities

    def test_can_can_handle(self, can):
        task = Task(description="Assess compliance", task_type="compliance_assessment")
        assert can.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_can_execute(self, can, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Compliance analysis complete")
        )

        task = Task(
            description="Analyze compliance status",
            task_type="compliance_assessment",
        )

        result = await can.execute(task)
        assert result.success is True


class TestPolicyAnalyst:
    """Test PolicyAnalyst specialist."""

    @pytest.fixture
    def pa(self, mock_llm_provider):
        return PolicyAnalyst(llm_provider=mock_llm_provider)

    def test_pa_initialization(self, pa):
        assert pa.code == "PA"
        assert pa.name == "Policy Analyst"
        assert "policy_review" in pa.capabilities

    def test_pa_can_handle(self, pa):
        task = Task(description="Review policy", task_type="policy_review")
        assert pa.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_pa_execute(self, pa, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Policy analysis complete")
        )

        task = Task(
            description="Analyze policy gaps",
            task_type="policy_review",
        )

        result = await pa.execute(task)
        assert result.success is True


class TestAuditCoordinator:
    """Test AuditCoordinator specialist."""

    @pytest.fixture
    def ac(self, mock_llm_provider):
        return AuditCoordinator(llm_provider=mock_llm_provider)

    def test_ac_initialization(self, ac):
        assert ac.code == "AC"
        assert ac.name == "Audit Coordinator"
        assert "audit_planning" in ac.capabilities

    def test_ac_can_handle(self, ac):
        task = Task(description="Coordinate audit", task_type="audit_planning")
        assert ac.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_ac_execute(self, ac, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Audit coordination complete")
        )

        task = Task(
            description="Coordinate audit activities",
            task_type="audit_planning",
        )

        result = await ac.execute(task)
        assert result.success is True


class TestEthicsOfficer:
    """Test EthicsOfficer specialist."""

    @pytest.fixture
    def eo(self, mock_llm_provider):
        return EthicsOfficer(llm_provider=mock_llm_provider)

    def test_eo_initialization(self, eo):
        assert eo.code == "EO"
        assert eo.name == "Ethics Officer"
        assert "ethics_review" in eo.capabilities

    def test_eo_can_handle(self, eo):
        task = Task(description="Ethics review", task_type="ethics_review")
        assert eo.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_eo_execute(self, eo, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Ethics review complete")
        )

        task = Task(
            description="Review ethical concerns",
            task_type="ethics_review",
        )

        result = await eo.execute(task)
        assert result.success is True


class TestTrainingCoordinator:
    """Test TrainingCoordinator specialist."""

    @pytest.fixture
    def tc(self, mock_llm_provider):
        return TrainingCoordinator(llm_provider=mock_llm_provider)

    def test_tc_initialization(self, tc):
        assert tc.code == "TC"
        assert tc.name == "Training Coordinator"
        assert "compliance_training" in tc.capabilities

    def test_tc_can_handle(self, tc):
        task = Task(description="Plan training", task_type="compliance_training")
        assert tc.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_tc_execute(self, tc, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Training plan complete")
        )

        task = Task(
            description="Plan compliance training",
            task_type="compliance_training",
        )

        result = await tc.execute(task)
        assert result.success is True


class TestCComOManagerHierarchy:
    """Test Accord manager and specialist hierarchy."""

    @pytest.fixture
    def ccomo(self, mock_llm_provider):
        return Accord(llm_provider=mock_llm_provider)

    def test_ccomo_has_managers(self, ccomo):
        """Test that Accord has registered managers."""
        assert len(ccomo.subordinates) == 5

        manager_codes = [m.code for m in ccomo.subordinates]
        assert "CPLM" in manager_codes
        assert "POLM" in manager_codes
        assert "AUM" in manager_codes
        assert "EM" in manager_codes
        assert "LM" in manager_codes

    def test_cm_has_specialists(self, ccomo):
        """Test that ComplianceManager has specialists."""
        cm = ccomo.get_subordinate("CPLM")
        assert cm is not None

        specialist_codes = [s.code for s in cm.subordinates]
        assert "CAN" in specialist_codes
        assert "TC" in specialist_codes

    def test_pm_has_specialists(self, ccomo):
        """Test that PolicyManager has specialists."""
        pm = ccomo.get_subordinate("POLM")
        assert pm is not None

        specialist_codes = [s.code for s in pm.subordinates]
        assert "PA" in specialist_codes

    def test_aum_has_specialists(self, ccomo):
        """Test that AuditManager has specialists."""
        aum = ccomo.get_subordinate("AUM")
        assert aum is not None

        specialist_codes = [s.code for s in aum.subordinates]
        assert "AC" in specialist_codes

    def test_em_has_specialists(self, ccomo):
        """Test that EthicsManager has specialists."""
        em = ccomo.get_subordinate("EM")
        assert em is not None

        specialist_codes = [s.code for s in em.subordinates]
        assert "EO" in specialist_codes

    @pytest.mark.asyncio
    async def test_ccomo_delegate_to_manager(self, ccomo, mock_llm_provider):
        """Test delegation from Accord to manager."""
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Task delegated"))

        task = Task(
            description="Compliance assessment",
            task_type="compliance_assessment",
        )

        result = await ccomo.delegate(task, "CPLM")
        assert result.success is True
