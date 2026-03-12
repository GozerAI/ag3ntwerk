"""
Unit tests for Aegis (Aegis) managers and specialists.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.aegis import (
    Aegis,
    RiskAssessmentManager,
    ThreatModelingManager,
    BCPManager,
    IncidentManager,
    RiskAnalyst,
    ThreatAnalyst,
    ControlsAnalyst,
    IncidentAnalyst,
)
from ag3ntwerk.core.base import Task, TaskStatus


class TestRiskAssessmentManager:
    """Test RiskAssessmentManager functionality."""

    @pytest.fixture
    def ram(self, mock_llm_provider):
        return RiskAssessmentManager(llm_provider=mock_llm_provider)

    def test_ram_initialization(self, ram):
        assert ram.code == "RAM"
        assert ram.name == "Risk Assessment Manager"
        assert "risk_assessment" in ram.capabilities
        assert "risk_scoring" in ram.capabilities

    def test_ram_can_handle_assessment(self, ram):
        task = Task(description="Assess risks", task_type="risk_assessment")
        assert ram.can_handle(task) is True

    def test_ram_cannot_handle_threat_modeling(self, ram):
        task = Task(description="Model threats", task_type="threat_modeling")
        assert ram.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_ram_execute(self, ram, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Risk assessment complete")
        )

        task = Task(
            description="Assess security risks",
            task_type="risk_assessment",
            context={"scope": "api_endpoints"},
        )

        result = await ram.execute(task)
        assert result.success is True


class TestThreatModelingManager:
    """Test ThreatModelingManager functionality."""

    @pytest.fixture
    def tmm(self, mock_llm_provider):
        return ThreatModelingManager(llm_provider=mock_llm_provider)

    def test_tmm_initialization(self, tmm):
        assert tmm.code == "TMM"
        assert tmm.name == "Threat Modeling Manager"
        assert "threat_modeling" in tmm.capabilities
        assert "threat_analysis" in tmm.capabilities

    def test_tmm_can_handle_modeling(self, tmm):
        task = Task(description="Model threats", task_type="threat_modeling")
        assert tmm.can_handle(task) is True

    def test_tmm_cannot_handle_bcp(self, tmm):
        task = Task(description="Plan BCP", task_type="bcp_planning")
        assert tmm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_tmm_execute(self, tmm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Threat model complete")
        )

        task = Task(
            description="Create threat model for auth service",
            task_type="threat_modeling",
            context={"methodology": "STRIDE"},
        )

        result = await tmm.execute(task)
        assert result.success is True


class TestBCPManager:
    """Test BCPManager functionality."""

    @pytest.fixture
    def bcpm(self, mock_llm_provider):
        return BCPManager(llm_provider=mock_llm_provider)

    def test_bcpm_initialization(self, bcpm):
        assert bcpm.code == "BCPM"
        assert bcpm.name == "BCP Manager"
        assert "bcp_planning" in bcpm.capabilities
        assert "disaster_recovery" in bcpm.capabilities

    def test_bcpm_can_handle_bcp(self, bcpm):
        task = Task(description="Plan BCP", task_type="bcp_planning")
        assert bcpm.can_handle(task) is True

    def test_bcpm_cannot_handle_threat_modeling(self, bcpm):
        task = Task(description="Model threats", task_type="threat_modeling")
        assert bcpm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_bcpm_execute(self, bcpm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="BCP plan created"))

        task = Task(
            description="Create business continuity plan",
            task_type="bcp_planning",
            context={"scope": "data_center"},
        )

        result = await bcpm.execute(task)
        assert result.success is True


class TestIncidentManager:
    """Test IncidentManager functionality."""

    @pytest.fixture
    def im(self, mock_llm_provider):
        return IncidentManager(llm_provider=mock_llm_provider)

    def test_im_initialization(self, im):
        assert im.code == "IM"
        assert im.name == "Incident Manager"
        assert "incident_analysis" in im.capabilities
        assert "root_cause_analysis" in im.capabilities

    def test_im_can_handle_incident(self, im):
        task = Task(description="Analyze incident", task_type="incident_analysis")
        assert im.can_handle(task) is True

    def test_im_cannot_handle_risk_assessment(self, im):
        task = Task(description="Assess risks", task_type="risk_assessment")
        assert im.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_im_execute(self, im, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Incident analysis complete")
        )

        task = Task(
            description="Analyze security incident",
            task_type="incident_analysis",
            context={"incident_id": "INC-001"},
        )

        result = await im.execute(task)
        assert result.success is True


class TestRiskAnalyst:
    """Test RiskAnalyst specialist."""

    @pytest.fixture
    def ra(self, mock_llm_provider):
        return RiskAnalyst(llm_provider=mock_llm_provider)

    def test_ra_initialization(self, ra):
        assert ra.code == "RA"
        assert ra.name == "Risk Analyst"
        assert "risk_assessment" in ra.capabilities

    def test_ra_can_handle(self, ra):
        task = Task(description="Assess risk", task_type="risk_assessment")
        assert ra.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_ra_execute(self, ra, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Risk assessment complete")
        )

        task = Task(
            description="Assess operational risk",
            task_type="risk_assessment",
        )

        result = await ra.execute(task)
        assert result.success is True


class TestThreatAnalyst:
    """Test ThreatAnalyst specialist."""

    @pytest.fixture
    def ta(self, mock_llm_provider):
        return ThreatAnalyst(llm_provider=mock_llm_provider)

    def test_ta_initialization(self, ta):
        assert ta.code == "TA"
        assert ta.name == "Threat Analyst"
        assert "threat_modeling" in ta.capabilities

    def test_ta_can_handle(self, ta):
        task = Task(description="Model threats", task_type="threat_modeling")
        assert ta.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_ta_execute(self, ta, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Threat analysis complete")
        )

        task = Task(
            description="Analyze threat landscape",
            task_type="threat_modeling",
        )

        result = await ta.execute(task)
        assert result.success is True


class TestControlsAnalyst:
    """Test ControlsAnalyst specialist."""

    @pytest.fixture
    def ca(self, mock_llm_provider):
        return ControlsAnalyst(llm_provider=mock_llm_provider)

    def test_ca_initialization(self, ca):
        assert ca.code == "CA"
        assert ca.name == "Controls Analyst"
        assert "control_assessment" in ca.capabilities

    def test_ca_can_handle(self, ca):
        task = Task(description="Assess controls", task_type="control_assessment")
        assert ca.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_ca_execute(self, ca, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Control assessment complete")
        )

        task = Task(
            description="Assess access controls",
            task_type="control_assessment",
        )

        result = await ca.execute(task)
        assert result.success is True


class TestIncidentAnalyst:
    """Test IncidentAnalyst specialist."""

    @pytest.fixture
    def ia(self, mock_llm_provider):
        return IncidentAnalyst(llm_provider=mock_llm_provider)

    def test_ia_initialization(self, ia):
        assert ia.code == "IA"
        assert ia.name == "Incident Analyst"
        assert "incident_analysis" in ia.capabilities

    def test_ia_can_handle(self, ia):
        task = Task(description="Analyze incident", task_type="incident_analysis")
        assert ia.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_ia_execute(self, ia, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Incident analysis complete")
        )

        task = Task(
            description="Analyze security incident",
            task_type="incident_analysis",
        )

        result = await ia.execute(task)
        assert result.success is True


class TestCRiOManagerHierarchy:
    """Test Aegis manager and specialist hierarchy."""

    @pytest.fixture
    def crio(self, mock_llm_provider):
        return Aegis(llm_provider=mock_llm_provider)

    def test_crio_has_managers(self, crio):
        """Test that Aegis has registered managers."""
        assert len(crio.subordinates) == 4

        manager_codes = [m.code for m in crio.subordinates]
        assert "RAM" in manager_codes
        assert "TMM" in manager_codes
        assert "BCPM" in manager_codes
        assert "IM" in manager_codes

    def test_ram_has_specialists(self, crio):
        """Test that RiskAssessmentManager has specialists."""
        ram = crio.get_subordinate("RAM")
        assert ram is not None

        specialist_codes = [s.code for s in ram.subordinates]
        assert "RA" in specialist_codes
        assert "CA" in specialist_codes

    def test_tmm_has_specialists(self, crio):
        """Test that ThreatModelingManager has specialists."""
        tmm = crio.get_subordinate("TMM")
        assert tmm is not None

        specialist_codes = [s.code for s in tmm.subordinates]
        assert "TA" in specialist_codes

    def test_im_has_specialists(self, crio):
        """Test that IncidentManager has specialists."""
        im = crio.get_subordinate("IM")
        assert im is not None

        specialist_codes = [s.code for s in im.subordinates]
        assert "IA" in specialist_codes

    @pytest.mark.asyncio
    async def test_crio_delegate_to_manager(self, crio, mock_llm_provider):
        """Test delegation from Aegis to manager."""
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Task delegated"))

        task = Task(
            description="Risk assessment for API",
            task_type="risk_assessment",
        )

        result = await crio.delegate(task, "RAM")
        assert result.success is True
