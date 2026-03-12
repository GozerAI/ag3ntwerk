"""
Unit tests for Sentinel Bridge task mappings.

Tests the comprehensive TASK_DOMAIN_MAP and AGENT_NAME_MAP
to ensure all security task types are properly routed.
"""

import pytest


class TestSentinelBridgeMappings:
    """Test Sentinel Bridge task type mappings."""

    def test_task_domain_map_exists(self):
        """Verify TASK_DOMAIN_MAP is defined."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        assert "TASK_DOMAIN_MAP = {" in content

    def test_agent_name_map_exists(self):
        """Verify AGENT_NAME_MAP is defined."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        assert "AGENT_NAME_MAP = {" in content

    def test_guardian_domain_mappings(self):
        """Verify Guardian (security) domain task mappings."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        # Core threat operations
        security_tasks = [
            '"threat_detection": "security"',
            '"threat_analysis": "security"',
            '"threat_hunting": "security"',
            '"threat_mitigation": "security"',
            '"threat_blocking": "security"',
            '"block_ip": "security"',
            '"quarantine": "security"',
            '"firewall_rule": "security"',
            '"ids_analysis": "security"',
            '"siem_alert": "security"',
            '"malware_scan": "security"',
        ]
        for task in security_tasks:
            assert task in content, f"Missing task mapping: {task}"

    def test_sast_dast_mappings(self):
        """Verify SAST/DAST security scan mappings."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        app_security_tasks = [
            '"sast_scan": "security"',
            '"dast_scan": "security"',
            '"code_security_scan": "security"',
            '"dependency_scan": "security"',
            '"container_scan": "security"',
            '"image_scan": "security"',
        ]
        for task in app_security_tasks:
            assert task in content, f"Missing SAST/DAST mapping: {task}"

    def test_healer_domain_mappings(self):
        """Verify Healer (reliability) domain task mappings."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        reliability_tasks = [
            '"incident_response": "reliability"',
            '"incident_investigation": "reliability"',
            '"incident_triage": "reliability"',
            '"incident_containment": "reliability"',
            '"incident_eradication": "reliability"',
            '"incident_recovery": "reliability"',
            '"incident_post_mortem": "reliability"',
            '"service_restart": "reliability"',
            '"failover": "reliability"',
            '"health_check": "reliability"',
        ]
        for task in reliability_tasks:
            assert task in content, f"Missing reliability mapping: {task}"

    def test_discovery_domain_mappings(self):
        """Verify Discovery domain task mappings."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        discovery_tasks = [
            '"vulnerability_scan": "discovery"',
            '"vulnerability_assessment": "discovery"',
            '"patch_management": "discovery"',
            '"asset_discovery": "discovery"',
            '"network_scan": "discovery"',
            '"port_scan": "discovery"',
            '"topology_discovery": "discovery"',
            '"inventory_tracking": "discovery"',
        ]
        for task in discovery_tasks:
            assert task in content, f"Missing discovery mapping: {task}"

    def test_optimizer_domain_mappings(self):
        """Verify Optimizer (network) domain task mappings."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        network_tasks = [
            '"network_optimization": "network"',
            '"apply_qos": "network"',
            '"traffic_analysis": "network"',
            '"traffic_shaping": "network"',
            '"bandwidth_management": "network"',
            '"route_optimization": "network"',
        ]
        for task in network_tasks:
            assert task in content, f"Missing network mapping: {task}"

    def test_compliance_domain_mappings(self):
        """Verify Compliance domain task mappings."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        compliance_tasks = [
            '"compliance_assessment": "compliance"',
            '"compliance_audit": "compliance"',
            '"compliance_report": "compliance"',
            '"policy_enforcement": "compliance"',
            '"pci_compliance": "compliance"',
            '"hipaa_compliance": "compliance"',
            '"soc2_compliance": "compliance"',
            '"iso27001_compliance": "compliance"',
            '"gdpr_compliance": "compliance"',
        ]
        for task in compliance_tasks:
            assert task in content, f"Missing compliance mapping: {task}"

    def test_dr_domain_mappings(self):
        """Verify Disaster Recovery domain task mappings."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        dr_tasks = [
            '"disaster_recovery": "dr"',
            '"backup_validation": "dr"',
            '"recovery_test": "dr"',
            '"rto_test": "dr"',
            '"rpo_test": "dr"',
            '"runbook_execute": "dr"',
        ]
        for task in dr_tasks:
            assert task in content, f"Missing DR mapping: {task}"

    def test_cost_domain_mappings(self):
        """Verify Cost domain task mappings."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        cost_tasks = [
            '"security_cost_analysis": "cost"',
            '"cost_optimization": "cost"',
            '"cost_forecast": "cost"',
            '"cost_alert": "cost"',
            '"cost_rightsize": "cost"',
        ]
        for task in cost_tasks:
            assert task in content, f"Missing cost mapping: {task}"

    def test_agent_name_to_domain_mapping(self):
        """Verify agent name to domain mappings."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        agent_mappings = [
            '"guardian": "security"',
            '"healer": "reliability"',
            '"discovery": "discovery"',
            '"optimizer": "network"',
            '"compliance": "compliance"',
            '"disaster_recovery": "dr"',
            '"cost_manager": "cost"',
        ]
        for mapping in agent_mappings:
            assert mapping in content, f"Missing agent mapping: {mapping}"


class TestSentinelBridgeConvertTask:
    """Test task conversion logic."""

    def test_convert_task_method_exists(self):
        """Verify _convert_task method exists."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        assert "def _convert_task(self, task: Task)" in content

    def test_convert_task_uses_mapping(self):
        """Verify _convert_task uses TASK_DOMAIN_MAP."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        assert "domain = self.TASK_DOMAIN_MAP.get(task.task_type" in content

    def test_convert_task_default_domain(self):
        """Verify default domain when task type not found."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        # Default should be "security"
        assert 'TASK_DOMAIN_MAP.get(task.task_type, "security")' in content


class TestSentinelBridgeRouting:
    """Test direct agent routing."""

    def test_route_to_agent_method_exists(self):
        """Verify route_to_agent method exists."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        assert "async def route_to_agent(" in content

    def test_route_to_agent_uses_mapping(self):
        """Verify route_to_agent uses AGENT_NAME_MAP."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        assert "domain = self.AGENT_NAME_MAP.get(agent_name, agent_name)" in content


class TestSentinelBridgeStats:
    """Test bridge statistics tracking."""

    def test_stats_property_exists(self):
        """Verify stats property exists."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        assert "def stats(self) -> Dict[str, Any]:" in content

    def test_stats_tracks_tasks(self):
        """Verify stats tracks task execution."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        assert '"tasks_executed"' in content
        assert '"tasks_succeeded"' in content
        assert '"success_rate"' in content

    def test_connection_uptime_tracked(self):
        """Verify connection uptime is tracked."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/citadel/bridge.py", encoding="utf-8") as f:
            content = f.read()

        assert "connection_uptime" in content
        assert '"uptime_seconds"' in content
