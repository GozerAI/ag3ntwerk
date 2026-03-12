"""
Security & Compliance Workflows.

Workflows for security audits, compliance audits, risk assessment,
threat monitoring, risk monitoring, and compliance monitoring.
"""

from typing import Any, Dict, List

from ag3ntwerk.orchestration.base import Workflow, WorkflowStep


class SecurityAuditWorkflow(Workflow):
    """
    Workflow for comprehensive security audit.

    Coordinates across:
    - Citadel (Citadel): Security scanning and assessment
    - Sentinel (Sentinel): Infrastructure and access review
    - Aegis (Aegis): Risk assessment
    - Accord (Accord): Compliance verification

    Steps:
    1. Security Scan - Citadel performs comprehensive security scan
    2. Vulnerability Assessment - Citadel analyzes vulnerabilities
    3. Access Review - Sentinel audits access controls
    4. Risk Assessment - Aegis evaluates security risks
    5. Compliance Check - Accord verifies regulatory compliance
    6. Remediation Plan - Citadel creates remediation roadmap
    """

    @property
    def name(self) -> str:
        return "security_audit"

    @property
    def description(self) -> str:
        return "Comprehensive security audit with risk and compliance assessment"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="security_scan",
                agent="Citadel",
                task_type="security_scan",
                description="Perform comprehensive security scan",
                context_builder=lambda ctx: {
                    "audit_scope": ctx.get("audit_scope", "full"),
                    "systems": ctx.get("systems", []),
                    "audit_id": ctx.get("audit_id"),
                },
            ),
            WorkflowStep(
                name="vulnerability_assessment",
                agent="Citadel",
                task_type="vulnerability_assessment",
                description="Analyze and categorize vulnerabilities",
                depends_on=["security_scan"],
                context_builder=lambda ctx: {
                    "scan_results": ctx.step_results.get("security_scan"),
                    "severity_threshold": ctx.get("severity_threshold", "medium"),
                },
            ),
            WorkflowStep(
                name="access_review",
                agent="Sentinel",
                task_type="access_audit",
                description="Audit access controls and permissions",
                depends_on=["security_scan"],
                context_builder=lambda ctx: {
                    "systems": ctx.get("systems", []),
                    "scan_results": ctx.step_results.get("security_scan"),
                },
            ),
            WorkflowStep(
                name="risk_assessment",
                agent="Aegis",
                task_type="risk_assessment",
                description="Evaluate security risks and impact",
                depends_on=["vulnerability_assessment", "access_review"],
                context_builder=lambda ctx: {
                    "vulnerabilities": ctx.step_results.get("vulnerability_assessment"),
                    "access_findings": ctx.step_results.get("access_review"),
                    "risk_appetite": ctx.get("risk_appetite", "moderate"),
                },
            ),
            WorkflowStep(
                name="compliance_check",
                agent="Accord",
                task_type="compliance_assessment",
                description="Verify regulatory and policy compliance",
                depends_on=["security_scan", "access_review"],
                context_builder=lambda ctx: {
                    "scan_results": ctx.step_results.get("security_scan"),
                    "access_review": ctx.step_results.get("access_review"),
                    "compliance_frameworks": ctx.get("compliance_frameworks", ["SOC2", "GDPR"]),
                },
            ),
            WorkflowStep(
                name="remediation_plan",
                agent="Citadel",
                task_type="vulnerability_remediation",
                description="Create prioritized remediation roadmap",
                depends_on=["vulnerability_assessment", "risk_assessment", "compliance_check"],
                context_builder=lambda ctx: {
                    "vulnerabilities": ctx.step_results.get("vulnerability_assessment"),
                    "risk_assessment": ctx.step_results.get("risk_assessment"),
                    "compliance_gaps": ctx.step_results.get("compliance_check"),
                    "remediation_timeline": ctx.get("remediation_timeline", "30_days"),
                },
            ),
        ]


class ComplianceAuditWorkflow(Workflow):
    """
    Workflow for regulatory compliance audit.

    Coordinates across:
    - Accord (Accord): Compliance assessment
    - Aegis (Aegis): Risk evaluation
    - Citadel (Citadel): Security compliance
    - Keystone (Keystone): Financial compliance

    Steps:
    1. Compliance Assessment - Accord assesses current compliance state
    2. Gap Analysis - Accord identifies compliance gaps
    3. Risk Evaluation - Aegis evaluates compliance risks
    4. Security Compliance - Citadel verifies security controls
    5. Financial Compliance - Keystone verifies financial controls
    6. Remediation Plan - Accord creates compliance roadmap
    """

    @property
    def name(self) -> str:
        return "compliance_audit"

    @property
    def description(self) -> str:
        return "Regulatory compliance audit and remediation planning"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="compliance_assessment",
                agent="Accord",
                task_type="compliance_assessment",
                description="Assess current compliance state",
                context_builder=lambda ctx: {
                    "frameworks": ctx.get("frameworks", ["SOC2", "GDPR", "HIPAA"]),
                    "audit_scope": ctx.get("audit_scope", "full"),
                    "audit_period": ctx.get("audit_period"),
                },
            ),
            WorkflowStep(
                name="gap_analysis",
                agent="Accord",
                task_type="gap_analysis",
                description="Identify compliance gaps",
                depends_on=["compliance_assessment"],
                context_builder=lambda ctx: {
                    "assessment_results": ctx.step_results.get("compliance_assessment"),
                    "target_state": ctx.get("target_state", {}),
                },
            ),
            WorkflowStep(
                name="risk_evaluation",
                agent="Aegis",
                task_type="risk_assessment",
                description="Evaluate compliance-related risks",
                depends_on=["gap_analysis"],
                context_builder=lambda ctx: {
                    "compliance_gaps": ctx.step_results.get("gap_analysis"),
                    "risk_tolerance": ctx.get("risk_tolerance", "low"),
                },
            ),
            WorkflowStep(
                name="security_compliance",
                agent="Citadel",
                task_type="compliance_audit",
                description="Verify security control compliance",
                depends_on=["compliance_assessment"],
                context_builder=lambda ctx: {
                    "frameworks": ctx.get("frameworks", []),
                    "assessment_results": ctx.step_results.get("compliance_assessment"),
                    "security_controls": ctx.get("security_controls", []),
                },
            ),
            WorkflowStep(
                name="financial_compliance",
                agent="Keystone",
                task_type="variance_analysis",
                description="Verify financial control compliance",
                depends_on=["compliance_assessment"],
                context_builder=lambda ctx: {
                    "frameworks": ctx.get("frameworks", []),
                    "assessment_results": ctx.step_results.get("compliance_assessment"),
                    "financial_controls": ctx.get("financial_controls", []),
                },
            ),
            WorkflowStep(
                name="remediation_plan",
                agent="Accord",
                task_type="finding_remediation",
                description="Create compliance remediation roadmap",
                depends_on=[
                    "gap_analysis",
                    "risk_evaluation",
                    "security_compliance",
                    "financial_compliance",
                ],
                context_builder=lambda ctx: {
                    "all_findings": {
                        "gaps": ctx.step_results.get("gap_analysis"),
                        "risks": ctx.step_results.get("risk_evaluation"),
                        "security": ctx.step_results.get("security_compliance"),
                        "financial": ctx.step_results.get("financial_compliance"),
                    },
                    "remediation_priority": ctx.get("remediation_priority", "high"),
                    "deadline": ctx.get("deadline"),
                },
            ),
        ]


class RiskAssessmentWorkflow(Workflow):
    """
    Workflow for enterprise risk assessment.

    Coordinates across:
    - Aegis (Aegis): Risk identification and assessment
    - Citadel (Citadel): Security risk analysis
    - Accord (Accord): Compliance risk analysis
    - Keystone (Keystone): Financial risk analysis

    Steps:
    1. Risk Identification - Aegis identifies enterprise risks
    2. Security Risks - Citadel analyzes security-related risks
    3. Compliance Risks - Accord analyzes regulatory risks
    4. Financial Risks - Keystone analyzes financial risks
    5. Risk Quantification - Aegis quantifies and prioritizes risks
    6. Mitigation Strategy - Aegis creates risk mitigation plan
    """

    @property
    def name(self) -> str:
        return "risk_assessment"

    @property
    def description(self) -> str:
        return "Enterprise risk assessment and mitigation planning"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="risk_identification",
                agent="Aegis",
                task_type="risk_identification",
                description="Identify enterprise-wide risks",
                context_builder=lambda ctx: {
                    "risk_categories": ctx.get(
                        "risk_categories",
                        ["operational", "strategic", "financial", "compliance", "security"],
                    ),
                    "business_context": ctx.get("business_context", {}),
                    "assessment_scope": ctx.get("assessment_scope", "enterprise"),
                },
            ),
            WorkflowStep(
                name="security_risks",
                agent="Citadel",
                task_type="threat_analysis",
                description="Analyze security-related risks",
                depends_on=["risk_identification"],
                context_builder=lambda ctx: {
                    "identified_risks": ctx.step_results.get("risk_identification"),
                    "threat_landscape": ctx.get("threat_landscape", {}),
                },
            ),
            WorkflowStep(
                name="compliance_risks",
                agent="Accord",
                task_type="regulatory_analysis",
                description="Analyze regulatory and compliance risks",
                depends_on=["risk_identification"],
                context_builder=lambda ctx: {
                    "identified_risks": ctx.step_results.get("risk_identification"),
                    "regulatory_environment": ctx.get("regulatory_environment", {}),
                },
            ),
            WorkflowStep(
                name="financial_risks",
                agent="Keystone",
                task_type="financial_modeling",
                description="Analyze financial risks and impact",
                depends_on=["risk_identification"],
                context_builder=lambda ctx: {
                    "identified_risks": ctx.step_results.get("risk_identification"),
                    "financial_exposure": ctx.get("financial_exposure", {}),
                },
            ),
            WorkflowStep(
                name="risk_quantification",
                agent="Aegis",
                task_type="risk_quantification",
                description="Quantify and prioritize all risks",
                depends_on=["security_risks", "compliance_risks", "financial_risks"],
                context_builder=lambda ctx: {
                    "security_risks": ctx.step_results.get("security_risks"),
                    "compliance_risks": ctx.step_results.get("compliance_risks"),
                    "financial_risks": ctx.step_results.get("financial_risks"),
                    "risk_appetite": ctx.get("risk_appetite", "moderate"),
                },
            ),
            WorkflowStep(
                name="mitigation_strategy",
                agent="Aegis",
                task_type="mitigation_planning",
                description="Create risk mitigation strategy",
                depends_on=["risk_quantification"],
                context_builder=lambda ctx: {
                    "quantified_risks": ctx.step_results.get("risk_quantification"),
                    "mitigation_budget": ctx.get("mitigation_budget"),
                    "priority_threshold": ctx.get("priority_threshold", "high"),
                },
            ),
        ]


class ThreatMonitoringWorkflow(Workflow):
    """
    Citadel internal workflow for threat monitoring.

    Steps:
    1. Threat Intelligence - Gather threat intelligence
    2. Vulnerability Scan - Scan for vulnerabilities
    3. Threat Assessment - Assess threat levels
    4. Incident Detection - Check for active incidents
    5. Response Recommendations - Generate response plan
    """

    @property
    def name(self) -> str:
        return "threat_monitoring"

    @property
    def description(self) -> str:
        return "Citadel threat monitoring and assessment workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="threat_intelligence",
                agent="Citadel",
                task_type="threat_analysis",
                description="Gather and analyze threat intelligence",
                context_builder=lambda ctx: {
                    "intelligence_sources": ctx.get("intelligence_sources", []),
                    "industry_focus": ctx.get("industry_focus"),
                    "threat_categories": ctx.get("threat_categories", []),
                },
            ),
            WorkflowStep(
                name="vulnerability_scan",
                agent="Citadel",
                task_type="security_scan",
                description="Scan systems for vulnerabilities",
                context_builder=lambda ctx: {
                    "scan_targets": ctx.get("scan_targets", []),
                    "scan_type": ctx.get("scan_type", "full"),
                    "severity_threshold": ctx.get("severity_threshold", "medium"),
                },
            ),
            WorkflowStep(
                name="threat_assessment",
                agent="Citadel",
                task_type="threat_analysis",
                description="Assess threat levels and exposure",
                depends_on=["threat_intelligence", "vulnerability_scan"],
                context_builder=lambda ctx: {
                    "intelligence": ctx.step_results.get("threat_intelligence"),
                    "vulnerabilities": ctx.step_results.get("vulnerability_scan"),
                    "asset_inventory": ctx.get("asset_inventory", {}),
                },
            ),
            WorkflowStep(
                name="incident_detection",
                agent="Citadel",
                task_type="incident_response",
                description="Check for active security incidents",
                depends_on=["threat_assessment"],
                context_builder=lambda ctx: {
                    "threat_assessment": ctx.step_results.get("threat_assessment"),
                    "detection_sources": ctx.get("detection_sources", ["siem", "edr", "ndr"]),
                    "time_window": ctx.get("time_window", "24h"),
                },
            ),
            WorkflowStep(
                name="response_recommendations",
                agent="Citadel",
                task_type="security_assessment",
                description="Generate threat response recommendations",
                depends_on=["threat_assessment", "incident_detection"],
                context_builder=lambda ctx: {
                    "threats": ctx.step_results.get("threat_assessment"),
                    "incidents": ctx.step_results.get("incident_detection"),
                    "response_playbooks": ctx.get("response_playbooks", []),
                },
            ),
        ]


class RiskMonitoringWorkflow(Workflow):
    """
    Aegis internal workflow for ongoing risk monitoring.

    Steps:
    1. Risk Register Update - Update risk register
    2. KRI Monitoring - Monitor key risk indicators
    3. Threshold Analysis - Check risk thresholds
    4. Emerging Risks - Identify emerging risks
    5. Risk Report - Generate risk monitoring report
    """

    @property
    def name(self) -> str:
        return "risk_monitoring"

    @property
    def description(self) -> str:
        return "Aegis ongoing risk monitoring workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="risk_register_update",
                agent="Aegis",
                task_type="risk_identification",
                description="Update enterprise risk register",
                context_builder=lambda ctx: {
                    "current_register": ctx.get("current_register", {}),
                    "update_period": ctx.get("update_period", "monthly"),
                    "risk_categories": ctx.get("risk_categories", []),
                },
            ),
            WorkflowStep(
                name="kri_monitoring",
                agent="Aegis",
                task_type="risk_quantification",
                description="Monitor key risk indicators",
                depends_on=["risk_register_update"],
                context_builder=lambda ctx: {
                    "risk_register": ctx.step_results.get("risk_register_update"),
                    "kris": ctx.get("kris", []),
                    "measurement_period": ctx.get("measurement_period", "last_month"),
                },
            ),
            WorkflowStep(
                name="threshold_analysis",
                agent="Aegis",
                task_type="risk_assessment",
                description="Check risk thresholds and triggers",
                depends_on=["kri_monitoring"],
                context_builder=lambda ctx: {
                    "kri_values": ctx.step_results.get("kri_monitoring"),
                    "thresholds": ctx.get("thresholds", {}),
                    "escalation_rules": ctx.get("escalation_rules", {}),
                },
            ),
            WorkflowStep(
                name="emerging_risks",
                agent="Aegis",
                task_type="risk_identification",
                description="Identify emerging risks",
                depends_on=["risk_register_update"],
                context_builder=lambda ctx: {
                    "current_register": ctx.step_results.get("risk_register_update"),
                    "external_factors": ctx.get("external_factors", {}),
                    "industry_trends": ctx.get("industry_trends", []),
                },
            ),
            WorkflowStep(
                name="risk_report",
                agent="Aegis",
                task_type="risk_assessment",
                description="Generate risk monitoring report",
                depends_on=["threshold_analysis", "emerging_risks"],
                context_builder=lambda ctx: {
                    "thresholds": ctx.step_results.get("threshold_analysis"),
                    "emerging": ctx.step_results.get("emerging_risks"),
                    "report_format": ctx.get("report_format", "executive_summary"),
                    "audience": ctx.get("audience", "board"),
                },
            ),
        ]


class ComplianceMonitoringWorkflow(Workflow):
    """
    Accord internal workflow for compliance monitoring.

    Steps:
    1. Control Testing - Test compliance controls
    2. Policy Review - Review policy adherence
    3. Regulatory Updates - Check regulatory changes
    4. Gap Tracking - Track compliance gaps
    5. Compliance Report - Generate compliance report
    """

    @property
    def name(self) -> str:
        return "compliance_monitoring"

    @property
    def description(self) -> str:
        return "Accord compliance monitoring workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="control_testing",
                agent="Accord",
                task_type="control_testing",
                description="Test compliance controls effectiveness",
                context_builder=lambda ctx: {
                    "control_framework": ctx.get("control_framework", "SOC2"),
                    "controls_to_test": ctx.get("controls_to_test", []),
                    "testing_method": ctx.get("testing_method", "sample"),
                },
            ),
            WorkflowStep(
                name="policy_review",
                agent="Accord",
                task_type="policy_management",
                description="Review policy adherence",
                context_builder=lambda ctx: {
                    "policies": ctx.get("policies", []),
                    "review_scope": ctx.get("review_scope", "all_departments"),
                    "exception_tracking": ctx.get("exception_tracking", True),
                },
            ),
            WorkflowStep(
                name="regulatory_updates",
                agent="Accord",
                task_type="regulatory_analysis",
                description="Check for regulatory changes",
                context_builder=lambda ctx: {
                    "jurisdictions": ctx.get("jurisdictions", []),
                    "frameworks": ctx.get("frameworks", []),
                    "update_period": ctx.get("update_period", "last_month"),
                },
            ),
            WorkflowStep(
                name="gap_tracking",
                agent="Accord",
                task_type="gap_analysis",
                description="Track and update compliance gaps",
                depends_on=["control_testing", "policy_review", "regulatory_updates"],
                context_builder=lambda ctx: {
                    "control_results": ctx.step_results.get("control_testing"),
                    "policy_results": ctx.step_results.get("policy_review"),
                    "regulatory_changes": ctx.step_results.get("regulatory_updates"),
                    "existing_gaps": ctx.get("existing_gaps", []),
                },
            ),
            WorkflowStep(
                name="compliance_report",
                agent="Accord",
                task_type="compliance_assessment",
                description="Generate compliance monitoring report",
                depends_on=["gap_tracking"],
                context_builder=lambda ctx: {
                    "all_findings": {
                        "controls": ctx.step_results.get("control_testing"),
                        "policies": ctx.step_results.get("policy_review"),
                        "gaps": ctx.step_results.get("gap_tracking"),
                    },
                    "report_period": ctx.get("report_period"),
                    "stakeholders": ctx.get("stakeholders", []),
                },
            ),
        ]
