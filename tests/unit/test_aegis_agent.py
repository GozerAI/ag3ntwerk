"""
Unit tests for Aegis (Aegis) agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from ag3ntwerk.agents.aegis import Aegis, Aegis
from ag3ntwerk.agents.aegis.models import (
    Risk,
    RiskScore,
    RiskCategory,
    RiskSeverity,
    RiskLikelihood,
    RiskStatus,
    MitigationStrategy,
    Control,
    Threat,
    ThreatModel,
    ThreatType,
    RiskAppetite,
    BusinessContinuityPlan,
    RiskIncident,
)
from ag3ntwerk.core.base import Task, TaskStatus


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class TestCRiOModels:
    """Test Aegis data models."""

    def test_risk_score_creation(self):
        score = RiskScore(
            likelihood_score=4.0,
            impact_score=5.0,
        )
        assert score.likelihood_score == 4.0
        assert score.impact_score == 5.0
        assert score.inherent_score == 20.0
        assert score.risk_level == RiskSeverity.CRITICAL

    def test_risk_score_levels(self):
        # Critical: score >= 20
        assert RiskScore(5.0, 4.0).risk_level == RiskSeverity.CRITICAL

        # High: score >= 12
        assert RiskScore(4.0, 3.0).risk_level == RiskSeverity.HIGH

        # Medium: score >= 6
        assert RiskScore(3.0, 2.0).risk_level == RiskSeverity.MEDIUM

        # Low: score >= 3
        assert RiskScore(1.5, 2.0).risk_level == RiskSeverity.LOW

        # Minimal: score < 3
        assert RiskScore(1.0, 1.0).risk_level == RiskSeverity.MINIMAL

    def test_control_creation(self):
        control = Control(
            id="ctrl1",
            name="Access Control",
            description="Multi-factor authentication",
            control_type="preventive",
            effectiveness=0.8,
        )
        assert control.id == "ctrl1"
        assert control.effectiveness == 0.8
        assert control.status == "proposed"

    def test_risk_creation(self):
        risk = Risk(
            id="risk1",
            name="Data Breach",
            description="Unauthorized access to customer data",
            category=RiskCategory.TECHNOLOGY,
            status=RiskStatus.ASSESSED,
            inherent_score=RiskScore(4.0, 5.0),
        )
        assert risk.id == "risk1"
        assert risk.category == RiskCategory.TECHNOLOGY
        assert risk.inherent_score.risk_level == RiskSeverity.CRITICAL

    def test_risk_calculate_residual(self):
        risk = Risk(
            id="risk1",
            name="Test Risk",
            inherent_score=RiskScore(4.0, 4.0),
        )

        controls = [
            Control(id="c1", name="Control 1", effectiveness=0.3),
            Control(id="c2", name="Control 2", effectiveness=0.3),
        ]

        residual = risk.calculate_residual_risk(controls)
        # 60% reduction in likelihood (capped at 90%)
        assert residual.likelihood_score < risk.inherent_score.likelihood_score

    def test_threat_creation(self):
        threat = Threat(
            id="t1",
            name="SQL Injection",
            description="SQL injection attack on login form",
            threat_type=ThreatType.TAMPERING,
            severity=RiskSeverity.HIGH,
            likelihood=RiskLikelihood.POSSIBLE,
        )
        assert threat.threat_type == ThreatType.TAMPERING
        assert threat.severity == RiskSeverity.HIGH

    def test_threat_model_creation(self):
        model = ThreatModel(
            id="tm1",
            name="API Threat Model",
            scope="Public REST API",
        )
        assert model.id == "tm1"
        assert len(model.threats) == 0

    def test_threat_model_add_threat(self):
        model = ThreatModel(id="tm1", name="Test Model")
        threat = Threat(id="t1", name="Spoofing Attack", threat_type=ThreatType.SPOOFING)
        model.add_threat(threat)

        assert len(model.threats) == 1
        assert model.get_threats_by_type(ThreatType.SPOOFING) == [threat]

    def test_threat_model_high_severity(self):
        model = ThreatModel(id="tm1", name="Test")
        model.add_threat(Threat(id="t1", name="Low", severity=RiskSeverity.LOW))
        model.add_threat(Threat(id="t2", name="High", severity=RiskSeverity.HIGH))
        model.add_threat(Threat(id="t3", name="Critical", severity=RiskSeverity.CRITICAL))

        high_threats = model.get_high_severity_threats()
        assert len(high_threats) == 2

    def test_risk_appetite_within_appetite(self):
        appetite = RiskAppetite(
            id="ra1",
            tolerances={"technology": RiskSeverity.MEDIUM},
            max_financial_exposure=1000000,
        )

        # Risk within appetite
        risk = Risk(
            id="r1",
            name="Low Risk",
            category=RiskCategory.TECHNOLOGY,
            financial_exposure=500000,
            inherent_score=RiskScore(2.0, 2.0),  # LOW
        )
        assert appetite.is_within_appetite(risk) is True

        # Risk exceeds appetite
        high_risk = Risk(
            id="r2",
            name="High Risk",
            category=RiskCategory.TECHNOLOGY,
            financial_exposure=500000,
            inherent_score=RiskScore(4.0, 4.0),  # HIGH
        )
        assert appetite.is_within_appetite(high_risk) is False

    def test_risk_appetite_zero_tolerance(self):
        appetite = RiskAppetite(
            id="ra1",
            zero_tolerance_categories=[RiskCategory.COMPLIANCE],
        )

        risk = Risk(
            id="r1",
            name="Compliance Risk",
            category=RiskCategory.COMPLIANCE,
        )
        assert appetite.is_within_appetite(risk) is False

    def test_bcp_creation(self):
        bcp = BusinessContinuityPlan(
            id="bcp1",
            name="IT Disaster Recovery",
            rto_hours=4.0,
            rpo_hours=1.0,
            critical_functions=["payment_processing", "order_management"],
        )
        assert bcp.rto_hours == 4.0
        assert len(bcp.critical_functions) == 2

    def test_risk_incident_resolution_time(self):
        detected = _utcnow() - timedelta(hours=5)
        resolved = _utcnow()

        incident = RiskIncident(
            id="inc1",
            name="Security Incident",
            detected_at=detected,
            resolved_at=resolved,
            status="closed",
        )

        assert incident.resolution_time_hours is not None
        assert 4.9 < incident.resolution_time_hours < 5.1


class TestCRiOAgent:
    """Test Aegis agent functionality."""

    @pytest.fixture
    def crio(self, mock_llm_provider):
        return Aegis(llm_provider=mock_llm_provider)

    def test_crio_initialization(self, crio):
        assert crio.code == "Aegis"
        assert crio.codename == "Aegis"
        assert crio.name == "Aegis"

    def test_crio_alias(self):
        assert Aegis == Aegis

    def test_crio_capabilities(self, crio):
        assert "risk_assessment" in crio.capabilities
        assert "threat_modeling" in crio.capabilities
        assert "bcp_planning" in crio.capabilities
        assert "incident_analysis" in crio.capabilities

    def test_can_handle_risk_assessment(self, crio):
        task = Task(description="Assess risks", task_type="risk_assessment")
        assert crio.can_handle(task) is True

    def test_can_handle_threat_modeling(self, crio):
        task = Task(description="Model threats", task_type="threat_modeling")
        assert crio.can_handle(task) is True

    def test_cannot_handle_code_review(self, crio):
        task = Task(description="Review code", task_type="code_review")
        assert crio.can_handle(task) is False

    def test_register_risk(self, crio):
        risk = Risk(id="r1", name="Test Risk", category=RiskCategory.OPERATIONAL)
        result = crio.register_risk(risk)

        assert result == "r1"
        assert crio.get_risk("r1") is not None

    def test_register_control(self, crio):
        control = Control(id="c1", name="Test Control")
        result = crio.register_control(control)
        assert result == "c1"

    def test_register_threat_model(self, crio):
        model = ThreatModel(id="tm1", name="Test Model")
        result = crio.register_threat_model(model)
        assert result == "tm1"

    def test_register_bcp(self, crio):
        bcp = BusinessContinuityPlan(id="bcp1", name="Test BCP")
        result = crio.register_bcp(bcp)
        assert result == "bcp1"

    def test_get_risks_by_category(self, crio):
        crio.register_risk(Risk(id="r1", name="Tech Risk", category=RiskCategory.TECHNOLOGY))
        crio.register_risk(Risk(id="r2", name="Op Risk", category=RiskCategory.OPERATIONAL))
        crio.register_risk(Risk(id="r3", name="Tech Risk 2", category=RiskCategory.TECHNOLOGY))

        tech_risks = crio.get_risks_by_category(RiskCategory.TECHNOLOGY)
        assert len(tech_risks) == 2

    def test_get_high_severity_risks(self, crio):
        crio.register_risk(
            Risk(
                id="r1",
                name="Critical",
                inherent_score=RiskScore(5.0, 4.0),
            )
        )
        crio.register_risk(
            Risk(
                id="r2",
                name="Low",
                inherent_score=RiskScore(1.0, 1.0),
            )
        )

        high_risks = crio.get_high_severity_risks()
        assert len(high_risks) == 1

    def test_risk_status(self, crio):
        crio.register_risk(
            Risk(
                id="r1",
                name="Risk 1",
                inherent_score=RiskScore(4.0, 4.0),
            )
        )
        crio.register_control(Control(id="c1", name="Control 1"))
        crio.register_threat_model(ThreatModel(id="tm1", name="Model 1"))

        status = crio.get_risk_status()

        assert status["total_risks"] == 1
        assert status["controls_registered"] == 1
        assert status["threat_models"] == 1

    @pytest.mark.asyncio
    async def test_execute_risk_assessment(self, crio, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Risk assessment complete")
        )

        task = Task(
            description="Assess API security risks",
            task_type="risk_assessment",
            context={"scope": "public-api", "system": "payment-service"},
        )

        result = await crio.execute(task)

        assert result.success is True
        assert "assessment" in result.output

    @pytest.mark.asyncio
    async def test_execute_threat_modeling(self, crio, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Threat model analysis using STRIDE")
        )

        task = Task(
            description="Model threats for auth service",
            task_type="threat_modeling",
            context={"system": "auth-service", "methodology": "STRIDE"},
        )

        result = await crio.execute(task)

        assert result.success is True
        assert result.output["methodology"] == "STRIDE"

    @pytest.mark.asyncio
    async def test_execute_bcp_planning(self, crio, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Business continuity plan")
        )

        task = Task(
            description="Create BCP for data center",
            task_type="bcp_planning",
            context={"scope": "primary-datacenter"},
        )

        result = await crio.execute(task)

        assert result.success is True
        assert result.output["plan_type"] == "bcp"

    @pytest.mark.asyncio
    async def test_execute_no_llm_provider(self):
        crio = Aegis()  # No LLM provider

        task = Task(
            description="Custom task",
            task_type="unknown_task",
        )

        result = await crio.execute(task)

        assert result.success is False
        assert "No LLM provider" in result.error
