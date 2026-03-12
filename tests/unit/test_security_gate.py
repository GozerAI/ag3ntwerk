"""
Unit tests for Security-Gated Deployment integration (Citadel <-> Foundry).

Tests the security gate that enforces security requirements before deployments.
"""

import pytest


class TestSecurityGateModule:
    """Test security gate module structure."""

    def test_security_gate_imports(self):
        """Verify module can be imported."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/__init__.py", encoding="utf-8") as f:
            content = f.read()

        assert "SecurityGatedDeployment" in content
        assert "SecurityGateStatus" in content
        assert "SecurityCheckType" in content
        assert "DeploymentSecurityGate" in content
        assert "DeploymentRisk" in content

    def test_security_gate_status_enum(self):
        """Verify SecurityGateStatus enum values."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        statuses = [
            'PENDING = "pending"',
            'PASSED = "passed"',
            'FAILED = "failed"',
            'WAIVED = "waived"',
            'BLOCKED = "blocked"',
        ]
        for status in statuses:
            assert status in content, f"Missing status: {status}"

    def test_security_check_type_enum(self):
        """Verify SecurityCheckType enum values."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        check_types = [
            'SAST_SCAN = "sast_scan"',
            'DAST_SCAN = "dast_scan"',
            'DEPENDENCY_SCAN = "dependency_scan"',
            'CONTAINER_SCAN = "container_scan"',
            'SECRET_SCAN = "secret_scan"',
            'COMPLIANCE_CHECK = "compliance_check"',
            'VULNERABILITY_ASSESSMENT = "vulnerability_assessment"',
            'INCIDENT_CHECK = "incident_check"',
        ]
        for check_type in check_types:
            assert check_type in content, f"Missing check type: {check_type}"

    def test_deployment_risk_enum(self):
        """Verify DeploymentRisk enum values."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        risks = [
            'LOW = "low"',
            'MEDIUM = "medium"',
            'HIGH = "high"',
            'CRITICAL = "critical"',
        ]
        for risk in risks:
            assert risk in content, f"Missing risk level: {risk}"


class TestSecurityCheck:
    """Test SecurityCheck dataclass."""

    def test_security_check_fields(self):
        """Verify SecurityCheck has required fields."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        fields = [
            "id: UUID",
            "check_type: SecurityCheckType",
            "name: str",
            "passed: bool",
            "score: float",
            "findings: List[Dict[str, Any]]",
            "critical_findings: int",
            "high_findings: int",
            "waived: bool",
            "waiver_reason: Optional[str]",
        ]
        for field in fields:
            assert field in content, f"Missing field: {field}"

    def test_is_blocking_property(self):
        """Verify is_blocking property logic."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def is_blocking(self) -> bool:" in content
        assert "if self.waived:" in content
        assert "if self.critical_findings > 0:" in content
        assert "if self.high_findings >= 3:" in content
        assert "if self.score < 60.0:" in content


class TestDeploymentSecurityGate:
    """Test DeploymentSecurityGate dataclass."""

    def test_gate_fields(self):
        """Verify DeploymentSecurityGate has required fields."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        fields = [
            "id: UUID",
            "deployment_id: str",
            "environment: str",
            "version: str",
            "status: SecurityGateStatus",
            "checks: List[SecurityCheck]",
            "overall_score: float",
            "risk_level: DeploymentRisk",
            "approved_by: Optional[str]",
            "blocked_reason: Optional[str]",
        ]
        for field in fields:
            assert field in content, f"Missing field: {field}"

    def test_blocking_checks_property(self):
        """Verify blocking_checks property."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def blocking_checks(self) -> List[SecurityCheck]:" in content
        assert "[c for c in self.checks if c.is_blocking]" in content

    def test_can_proceed_property(self):
        """Verify can_proceed property."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def can_proceed(self) -> bool:" in content
        assert "SecurityGateStatus.PASSED" in content
        assert "SecurityGateStatus.WAIVED" in content


class TestSecurityGatedDeployment:
    """Test SecurityGatedDeployment class."""

    def test_class_exists(self):
        """Verify SecurityGatedDeployment class exists."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "class SecurityGatedDeployment:" in content

    def test_environment_risk_mapping(self):
        """Verify environment risk level mapping."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "ENVIRONMENT_RISK = {" in content
        assert '"development": DeploymentRisk.LOW' in content
        assert '"staging": DeploymentRisk.MEDIUM' in content
        assert '"production": DeploymentRisk.HIGH' in content
        assert '"production-critical": DeploymentRisk.CRITICAL' in content

    def test_required_checks_by_environment(self):
        """Verify required checks vary by environment."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "REQUIRED_CHECKS = {" in content
        assert '"development"' in content
        assert '"staging"' in content
        assert '"production"' in content
        # Production should have more checks than staging
        assert "SecurityCheckType.DAST_SCAN" in content
        assert "SecurityCheckType.VULNERABILITY_ASSESSMENT" in content

    def test_score_thresholds_by_risk(self):
        """Verify score thresholds vary by risk level."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "SCORE_THRESHOLDS = {" in content
        assert "DeploymentRisk.LOW: 60.0" in content
        assert "DeploymentRisk.MEDIUM: 70.0" in content
        assert "DeploymentRisk.HIGH: 80.0" in content
        assert "DeploymentRisk.CRITICAL: 90.0" in content

    def test_evaluate_deployment_method(self):
        """Verify evaluate_deployment method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "async def evaluate_deployment(" in content
        assert "deployment_id: str," in content
        assert "environment: str," in content
        assert "version: str," in content
        assert ") -> DeploymentSecurityGate:" in content


class TestSecurityCheckExecution:
    """Test security check execution methods."""

    def test_sast_scan_method(self):
        """Verify SAST scan execution."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "async def _run_sast_scan(" in content
        assert "if self._cseco:" in content
        assert 'task_type="sast_scan"' in content

    def test_dast_scan_method(self):
        """Verify DAST scan execution."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "async def _run_dast_scan(" in content
        assert 'task_type="dast_scan"' in content

    def test_dependency_scan_method(self):
        """Verify dependency scan execution."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "async def _run_dependency_scan(" in content
        assert 'task_type="dependency_scan"' in content

    def test_incident_check_method(self):
        """Verify active incident check."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "async def _check_active_incidents(" in content
        assert "blocking_incidents" in content


class TestGateManagement:
    """Test gate management methods."""

    def test_approve_gate_method(self):
        """Verify gate approval method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def approve_gate(" in content
        assert "approved_by: str," in content
        assert "gate.approved_by = approved_by" in content
        assert "gate.approved_at = datetime.now(timezone.utc)" in content

    def test_waive_check_method(self):
        """Verify check waiver method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def waive_check(" in content
        assert "waiver_reason: str," in content
        assert "waiver_by: str," in content
        assert "check.waived = True" in content

    def test_connect_executives_method(self):
        """Verify agent connection method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def connect_executives(" in content
        assert "cseco: Optional[Any]" in content
        assert "cengo: Optional[Any]" in content


class TestGateEvaluation:
    """Test gate evaluation logic."""

    def test_calculate_overall_score(self):
        """Verify overall score calculation."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def _calculate_overall_score(self, checks: List[SecurityCheck])" in content
        assert "weighted_score" in content
        assert "total_weight" in content

    def test_evaluate_gate_status(self):
        """Verify gate status evaluation."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def _evaluate_gate_status(" in content
        assert "SecurityGateStatus.BLOCKED" in content
        assert "SecurityGateStatus.FAILED" in content
        assert "SecurityGateStatus.WAIVED" in content
        assert "SecurityGateStatus.PASSED" in content

    def test_auto_approve_threshold(self):
        """Verify auto-approval on high score."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "auto_approve_threshold" in content
        assert 'gate.approved_by = "auto"' in content


class TestDeploymentNotifications:
    """Test deployment notification methods."""

    def test_notify_deployment_started(self):
        """Verify deployment start notification."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "async def notify_deployment_started(self, gate_id: UUID)" in content

    def test_notify_deployment_completed(self):
        """Verify deployment completion notification."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "async def notify_deployment_completed(" in content
        assert "success: bool," in content


class TestSecurityReporting:
    """Test security reporting methods."""

    def test_get_deployment_report(self):
        """Verify deployment report generation."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def get_deployment_report(" in content
        assert '"deployment_id"' in content
        assert '"gate"' in content
        assert '"checks"' in content
        assert '"recommendation"' in content

    def test_get_recommendation(self):
        """Verify recommendation generation."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def _get_recommendation(self, gate: DeploymentSecurityGate)" in content
        assert "Deployment approved" in content
        assert "Deployment blocked" in content
        assert "Security score too low" in content

    def test_stats_property(self):
        """Verify stats property."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/security_gate.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def stats(self) -> Dict[str, Any]:" in content
        assert '"total_evaluations"' in content
        assert '"total_passed"' in content
        assert '"total_blocked"' in content
        assert '"pass_rate"' in content
