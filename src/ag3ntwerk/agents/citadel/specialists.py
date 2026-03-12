"""
Citadel (Citadel) Security Specialists.

Individual contributor specialists for specific security functions.
"""

import logging
from typing import Optional

from ag3ntwerk.core.base import Specialist, Task, TaskResult
from ag3ntwerk.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class ThreatHunter(Specialist):
    """
    Threat Hunter - Proactive threat hunting specialist.

    Responsible for:
    - Proactive threat hunting
    - Hypothesis-driven investigations
    - Advanced threat detection
    - IOC development
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="TH",
            name="Threat Hunter",
            domain="Threat Hunting, Advanced Threat Detection",
            capabilities=[
                "threat_hunting",
                "hypothesis_development",
                "behavioral_analysis",
                "ioc_development",
                "attack_pattern_analysis",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if ThreatHunter can handle the task."""
        hunting_types = [
            "threat_hunting",
            "hypothesis_development",
            "behavioral_analysis",
            "ioc_development",
        ]
        return task.task_type in hunting_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "threat_hunting": self._handle_threat_hunting,
            "hypothesis_development": self._handle_hypothesis_development,
            "behavioral_analysis": self._handle_behavioral_analysis,
            "ioc_development": self._handle_ioc_development,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute threat hunting task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_threat_hunting(self, task: Task) -> TaskResult:
        """Handle threat hunting."""
        context = task.context or {}

        prompt = f"""Execute threat hunting operation:

Hypothesis: {context.get('hypothesis', 'APT activity')}
Data Sources: {context.get('data_sources', [])}
Environment: {context.get('environment', 'Enterprise')}
TTPs of Interest: {context.get('ttps', [])}

Hunting Requirements:
1. Develop hunting queries
2. Analyze data for anomalies
3. Identify potential threats
4. Document findings
5. Create detection rules

Provide threat hunting results.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_hypothesis_development(self, task: Task) -> TaskResult:
        """Handle hypothesis development."""
        context = task.context or {}

        prompt = f"""Develop threat hunting hypothesis:

Threat Landscape: {context.get('threat_landscape', 'General')}
Recent Intelligence: {context.get('intelligence', [])}
Environment: {context.get('environment', 'Enterprise')}

Hypothesis Development:
1. Analyze threat landscape
2. Identify likely attack vectors
3. Develop testable hypotheses
4. Define success criteria
5. Plan hunting approach

Provide hunting hypotheses.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_behavioral_analysis(self, task: Task) -> TaskResult:
        """Handle behavioral analysis."""
        context = task.context or {}

        prompt = f"""Analyze behavioral patterns:

Entity: {context.get('entity', 'Unknown')}
Behaviors: {context.get('behaviors', [])}
Baseline: {context.get('baseline', 'Standard')}

Analysis Requirements:
1. Establish baseline behavior
2. Identify deviations
3. Correlate anomalies
4. Assess threat potential
5. Recommend actions

Provide behavioral analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_ioc_development(self, task: Task) -> TaskResult:
        """Handle IOC development."""
        context = task.context or {}

        prompt = f"""Develop indicators of compromise:

Threat: {context.get('threat', 'Unknown')}
Evidence: {context.get('evidence', [])}
Context: {context.get('context', {})}

IOC Development:
1. Analyze threat artifacts
2. Extract indicators
3. Validate accuracy
4. Enrich with context
5. Format for sharing

Provide developed IOCs.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler for unmatched tasks."""
        prompt = f"As a Threat Hunter, analyze: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class VulnerabilityAnalyst(Specialist):
    """
    Vulnerability Analyst - Vulnerability analysis specialist.

    Responsible for:
    - Vulnerability analysis
    - Risk assessment
    - Remediation guidance
    - Patch prioritization
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="VA",
            name="Vulnerability Analyst",
            domain="Vulnerability Analysis, Risk Assessment",
            capabilities=[
                "vulnerability_analysis",
                "risk_assessment",
                "remediation_guidance",
                "patch_prioritization",
                "exploit_analysis",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if VulnerabilityAnalyst can handle the task."""
        vuln_types = [
            "vulnerability_analysis",
            "vulnerability_assessment",
            "risk_assessment",
            "remediation_guidance",
            "patch_prioritization",
        ]
        return task.task_type in vuln_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "vulnerability_analysis": self._handle_vulnerability_analysis,
            "vulnerability_assessment": self._handle_vulnerability_assessment,
            "risk_assessment": self._handle_risk_assessment,
            "remediation_guidance": self._handle_remediation_guidance,
            "patch_prioritization": self._handle_patch_prioritization,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute vulnerability analysis task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_vulnerability_analysis(self, task: Task) -> TaskResult:
        """Handle vulnerability analysis."""
        context = task.context or {}

        prompt = f"""Analyze vulnerability:

Vulnerability: {context.get('vulnerability', 'Unknown')}
CVE: {context.get('cve', 'N/A')}
CVSS: {context.get('cvss', 'N/A')}
Affected Systems: {context.get('affected_systems', [])}

Analysis Requirements:
1. Assess vulnerability details
2. Determine exploitability
3. Evaluate impact
4. Identify mitigations
5. Recommend priority

Provide vulnerability analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_vulnerability_assessment(self, task: Task) -> TaskResult:
        """Handle vulnerability assessment."""
        context = task.context or {}

        prompt = f"""Assess vulnerabilities:

Scope: {context.get('scope', 'Full environment')}
Scan Results: {context.get('scan_results', [])}
Assets: {context.get('assets', [])}

Assessment Requirements:
1. Review scan results
2. Validate findings
3. Assess risk levels
4. Prioritize by impact
5. Create remediation plan

Provide vulnerability assessment.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_risk_assessment(self, task: Task) -> TaskResult:
        """Handle risk assessment."""
        context = task.context or {}

        prompt = f"""Assess vulnerability risk:

Vulnerabilities: {context.get('vulnerabilities', [])}
Asset Criticality: {context.get('asset_criticality', 'medium')}
Exposure: {context.get('exposure', 'internal')}

Risk Assessment:
1. Calculate risk scores
2. Consider asset value
3. Evaluate threat likelihood
4. Determine business impact
5. Recommend mitigations

Provide risk assessment.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_remediation_guidance(self, task: Task) -> TaskResult:
        """Handle remediation guidance."""
        context = task.context or {}

        prompt = f"""Provide remediation guidance:

Vulnerability: {context.get('vulnerability', 'Unknown')}
System: {context.get('system', 'Unknown')}
Constraints: {context.get('constraints', [])}

Remediation Guidance:
1. Primary remediation
2. Workarounds
3. Mitigating controls
4. Testing requirements
5. Validation steps

Provide remediation guidance.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_patch_prioritization(self, task: Task) -> TaskResult:
        """Handle patch prioritization."""
        context = task.context or {}

        prompt = f"""Prioritize patches:

Patches: {context.get('patches', [])}
Systems: {context.get('systems', [])}
Constraints: {context.get('constraints', [])}

Prioritization Requirements:
1. Assess severity
2. Consider exploitability
3. Evaluate asset criticality
4. Factor in dependencies
5. Create priority list

Provide patch prioritization.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a Vulnerability Analyst, analyze: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class IncidentResponder(Specialist):
    """
    Incident Responder - Security incident response specialist.

    Responsible for:
    - Incident triage
    - Containment
    - Investigation
    - Forensics
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="IR",
            name="Incident Responder",
            domain="Incident Response, Forensics",
            capabilities=[
                "incident_triage",
                "incident_containment",
                "incident_investigation",
                "forensics",
                "evidence_collection",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if IncidentResponder can handle the task."""
        ir_types = [
            "incident_triage",
            "incident_containment",
            "incident_investigation",
            "forensics",
            "evidence_collection",
        ]
        return task.task_type in ir_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "incident_triage": self._handle_incident_triage,
            "incident_containment": self._handle_incident_containment,
            "incident_investigation": self._handle_incident_investigation,
            "forensics": self._handle_forensics,
            "evidence_collection": self._handle_evidence_collection,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute incident response task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_incident_triage(self, task: Task) -> TaskResult:
        """Handle incident triage."""
        context = task.context or {}

        prompt = f"""Triage security incident:

Incident: {context.get('incident', 'Unknown')}
Initial Report: {context.get('report', '')}
Affected Systems: {context.get('affected_systems', [])}

Triage Requirements:
1. Assess severity
2. Determine scope
3. Identify stakeholders
4. Prioritize response
5. Initial recommendations

Provide incident triage.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_incident_containment(self, task: Task) -> TaskResult:
        """Handle incident containment."""
        context = task.context or {}

        prompt = f"""Contain security incident:

Incident: {context.get('incident', 'Unknown')}
Affected Systems: {context.get('affected_systems', [])}
Attack Vector: {context.get('attack_vector', 'Unknown')}

Containment Requirements:
1. Identify containment scope
2. Isolate affected systems
3. Block attack vectors
4. Preserve evidence
5. Monitor for spread

Provide containment plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_incident_investigation(self, task: Task) -> TaskResult:
        """Handle incident investigation."""
        context = task.context or {}

        prompt = f"""Investigate security incident:

Incident: {context.get('incident', 'Unknown')}
Evidence: {context.get('evidence', [])}
Timeline: {context.get('timeline', [])}

Investigation Requirements:
1. Collect evidence
2. Analyze artifacts
3. Reconstruct timeline
4. Identify root cause
5. Document findings

Provide investigation results.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_forensics(self, task: Task) -> TaskResult:
        """Handle digital forensics."""
        context = task.context or {}

        prompt = f"""Conduct digital forensics:

Target: {context.get('target', 'Unknown')}
Evidence Type: {context.get('evidence_type', 'disk_image')}
Objectives: {context.get('objectives', [])}

Forensics Requirements:
1. Acquire evidence
2. Preserve chain of custody
3. Analyze artifacts
4. Extract relevant data
5. Document findings

Provide forensics analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_evidence_collection(self, task: Task) -> TaskResult:
        """Handle evidence collection."""
        context = task.context or {}

        prompt = f"""Collect incident evidence:

Incident: {context.get('incident', 'Unknown')}
Systems: {context.get('systems', [])}
Evidence Types: {context.get('evidence_types', [])}

Collection Requirements:
1. Identify evidence sources
2. Preserve volatile data
3. Collect artifacts
4. Maintain chain of custody
5. Document collection

Provide evidence collection plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As an Incident Responder, handle: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class ComplianceAnalyst(Specialist):
    """
    Compliance Analyst - Compliance and governance specialist.

    Responsible for:
    - Compliance assessments
    - Control testing
    - Evidence gathering
    - Gap analysis
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="CA",
            name="Compliance Analyst",
            domain="Compliance Assessment, Governance",
            capabilities=[
                "compliance_assessment",
                "control_testing",
                "evidence_gathering",
                "gap_analysis",
                "framework_mapping",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if ComplianceAnalyst can handle the task."""
        compliance_types = [
            "compliance_assessment",
            "control_testing",
            "evidence_gathering",
            "gap_analysis",
            "framework_mapping",
        ]
        return task.task_type in compliance_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "compliance_assessment": self._handle_compliance_assessment,
            "control_testing": self._handle_control_testing,
            "evidence_gathering": self._handle_evidence_gathering,
            "gap_analysis": self._handle_gap_analysis,
            "framework_mapping": self._handle_framework_mapping,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute compliance task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_compliance_assessment(self, task: Task) -> TaskResult:
        """Handle compliance assessment."""
        context = task.context or {}

        prompt = f"""Assess compliance:

Framework: {context.get('framework', 'SOC2')}
Controls: {context.get('controls', [])}
Scope: {context.get('scope', 'Full organization')}

Assessment Requirements:
1. Review control requirements
2. Gather evidence
3. Test control effectiveness
4. Identify gaps
5. Recommend improvements

Provide compliance assessment.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_control_testing(self, task: Task) -> TaskResult:
        """Handle control testing."""
        context = task.context or {}

        prompt = f"""Test security controls:

Controls: {context.get('controls', [])}
Testing Approach: {context.get('approach', 'inquiry_and_observation')}
Period: {context.get('period', 'Current')}

Testing Requirements:
1. Define test procedures
2. Execute tests
3. Collect evidence
4. Document results
5. Assess effectiveness

Provide control testing results.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_evidence_gathering(self, task: Task) -> TaskResult:
        """Handle evidence gathering."""
        context = task.context or {}

        prompt = f"""Gather compliance evidence:

Requirements: {context.get('requirements', [])}
Controls: {context.get('controls', [])}
Period: {context.get('period', 'Current')}

Evidence Requirements:
1. Identify evidence needs
2. Collect artifacts
3. Validate completeness
4. Organize documentation
5. Prepare for review

Provide evidence gathering plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_gap_analysis(self, task: Task) -> TaskResult:
        """Handle gap analysis."""
        context = task.context or {}

        prompt = f"""Conduct gap analysis:

Framework: {context.get('framework', 'ISO27001')}
Current State: {context.get('current_state', {})}
Target State: {context.get('target_state', {})}

Gap Analysis:
1. Map current controls
2. Identify requirements
3. Document gaps
4. Prioritize remediation
5. Create roadmap

Provide gap analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_framework_mapping(self, task: Task) -> TaskResult:
        """Handle framework mapping."""
        context = task.context or {}

        prompt = f"""Map compliance frameworks:

Source Framework: {context.get('source_framework', 'SOC2')}
Target Framework: {context.get('target_framework', 'ISO27001')}
Scope: {context.get('scope', [])}

Mapping Requirements:
1. Identify control mappings
2. Document relationships
3. Identify gaps
4. Optimize coverage
5. Create mapping matrix

Provide framework mapping.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a Compliance Analyst, handle: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class SecurityEngineer(Specialist):
    """
    Security Engineer - Security infrastructure specialist.

    Responsible for:
    - Security tooling
    - Detection engineering
    - Security automation
    - Infrastructure security
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="SE",
            name="Security Engineer",
            domain="Security Engineering, Detection, Automation",
            capabilities=[
                "detection_engineering",
                "security_automation",
                "security_tooling",
                "infrastructure_security",
                "siem_engineering",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if SecurityEngineer can handle the task."""
        eng_types = [
            "detection_engineering",
            "security_automation",
            "security_tooling",
            "infrastructure_security",
            "siem_engineering",
        ]
        return task.task_type in eng_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "detection_engineering": self._handle_detection_engineering,
            "security_automation": self._handle_security_automation,
            "security_tooling": self._handle_security_tooling,
            "infrastructure_security": self._handle_infrastructure_security,
            "siem_engineering": self._handle_siem_engineering,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute security engineering task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_detection_engineering(self, task: Task) -> TaskResult:
        """Handle detection engineering."""
        context = task.context or {}

        prompt = f"""Engineer detection rules:

Threat: {context.get('threat', 'Unknown')}
TTPs: {context.get('ttps', [])}
Data Sources: {context.get('data_sources', [])}

Detection Requirements:
1. Analyze threat behavior
2. Design detection logic
3. Create detection rules
4. Test effectiveness
5. Tune for accuracy

Provide detection rules.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_security_automation(self, task: Task) -> TaskResult:
        """Handle security automation."""
        context = task.context or {}

        prompt = f"""Build security automation:

Workflow: {context.get('workflow', 'Incident response')}
Triggers: {context.get('triggers', [])}
Actions: {context.get('actions', [])}

Automation Requirements:
1. Design workflow
2. Define triggers
3. Build integrations
4. Test automation
5. Deploy and monitor

Provide automation design.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_security_tooling(self, task: Task) -> TaskResult:
        """Handle security tooling."""
        context = task.context or {}

        prompt = f"""Configure security tools:

Tool: {context.get('tool', 'Unknown')}
Purpose: {context.get('purpose', 'Detection')}
Requirements: {context.get('requirements', [])}

Tooling Requirements:
1. Configure tool
2. Integrate with stack
3. Optimize settings
4. Test functionality
5. Document configuration

Provide tooling configuration.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_infrastructure_security(self, task: Task) -> TaskResult:
        """Handle infrastructure security."""
        context = task.context or {}

        prompt = f"""Secure infrastructure:

Infrastructure: {context.get('infrastructure', 'Cloud')}
Components: {context.get('components', [])}
Requirements: {context.get('requirements', [])}

Security Requirements:
1. Assess current state
2. Identify gaps
3. Design controls
4. Implement security
5. Validate effectiveness

Provide infrastructure security plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_siem_engineering(self, task: Task) -> TaskResult:
        """Handle SIEM engineering."""
        context = task.context or {}

        prompt = f"""Engineer SIEM configuration:

SIEM: {context.get('siem', 'Splunk')}
Use Cases: {context.get('use_cases', [])}
Data Sources: {context.get('data_sources', [])}

SIEM Requirements:
1. Configure data ingestion
2. Create correlation rules
3. Build dashboards
4. Set up alerting
5. Optimize performance

Provide SIEM engineering plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a Security Engineer, handle: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class AppSecEngineer(Specialist):
    """
    Application Security Engineer - AppSec specialist.

    Responsible for:
    - Code review
    - SAST/DAST
    - Dependency scanning
    - Secure development
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="ASE",
            name="AppSec Engineer",
            domain="Application Security, Secure Development",
            capabilities=[
                "code_review",
                "sast_scan",
                "dast_scan",
                "dependency_scan",
                "secure_development",
                "threat_modeling",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if AppSecEngineer can handle the task."""
        appsec_types = [
            "code_review",
            "sast_scan",
            "dast_scan",
            "dependency_scan",
            "secure_development",
            "threat_modeling",
        ]
        return task.task_type in appsec_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "code_review": self._handle_code_review,
            "sast_scan": self._handle_sast_scan,
            "dast_scan": self._handle_dast_scan,
            "dependency_scan": self._handle_dependency_scan,
            "secure_development": self._handle_secure_development,
            "threat_modeling": self._handle_threat_modeling,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute AppSec task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_code_review(self, task: Task) -> TaskResult:
        """Handle security code review."""
        context = task.context or {}

        prompt = f"""Review code for security:

Repository: {context.get('repository', 'Unknown')}
Language: {context.get('language', 'Unknown')}
Files: {context.get('files', [])}

Review Focus:
1. Authentication/Authorization
2. Input validation
3. SQL injection
4. XSS vulnerabilities
5. Secrets handling

Provide code review findings.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_sast_scan(self, task: Task) -> TaskResult:
        """Handle SAST scanning."""
        context = task.context or {}

        prompt = f"""Execute SAST scan:

Repository: {context.get('repository', 'Unknown')}
Language: {context.get('language', 'auto')}
Tool: {context.get('tool', 'auto')}

SAST Requirements:
1. Configure scanner
2. Execute analysis
3. Triage findings
4. Filter false positives
5. Prioritize issues

Provide SAST results.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_dast_scan(self, task: Task) -> TaskResult:
        """Handle DAST scanning."""
        context = task.context or {}

        prompt = f"""Execute DAST scan:

Target: {context.get('target', 'Unknown')}
Authentication: {context.get('auth', 'None')}
Scope: {context.get('scope', 'Full')}

DAST Requirements:
1. Configure scanner
2. Define scope
3. Execute testing
4. Validate findings
5. Report issues

Provide DAST results.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_dependency_scan(self, task: Task) -> TaskResult:
        """Handle dependency scanning."""
        context = task.context or {}

        prompt = f"""Scan dependencies:

Repository: {context.get('repository', 'Unknown')}
Package Manager: {context.get('package_manager', 'auto')}
Manifests: {context.get('manifests', [])}

Dependency Requirements:
1. Identify dependencies
2. Check vulnerabilities
3. Assess licenses
4. Find outdated packages
5. Recommend updates

Provide dependency scan results.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_secure_development(self, task: Task) -> TaskResult:
        """Handle secure development guidance."""
        context = task.context or {}

        prompt = f"""Provide secure development guidance:

Technology: {context.get('technology', 'Web application')}
Framework: {context.get('framework', 'Unknown')}
Feature: {context.get('feature', 'General')}

Guidance Requirements:
1. Security requirements
2. Design patterns
3. Implementation guidelines
4. Testing requirements
5. Common pitfalls

Provide secure development guidance.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_threat_modeling(self, task: Task) -> TaskResult:
        """Handle application threat modeling."""
        context = task.context or {}

        prompt = f"""Model application threats:

Application: {context.get('application', 'Unknown')}
Architecture: {context.get('architecture', {})}
Data Flows: {context.get('data_flows', [])}

Threat Modeling:
1. Identify assets
2. Map trust boundaries
3. Enumerate threats (STRIDE)
4. Assess risks
5. Recommend mitigations

Provide threat model.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As an AppSec Engineer, handle: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))
