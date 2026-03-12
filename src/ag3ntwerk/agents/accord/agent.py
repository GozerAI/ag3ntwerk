"""
Accord (Accord) Agent - Accord.

Codename: Accord
Core function: Regulatory compliance and policy enforcement.

The Accord handles all compliance-related tasks:
- Regulatory compliance monitoring and assessment
- Policy management and enforcement
- Audit coordination and finding remediation
- License and certification tracking
- Ethics and conduct oversight
- Regulatory reporting and filings

Sphere of influence: Regulatory compliance, policy management, audit
coordination, ethics oversight, licensing, regulatory relations.
"""

from typing import Any, Dict, List, Optional
import uuid

from ag3ntwerk.core.base import (
    Manager,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider
from ag3ntwerk.agents.accord.managers import (
    ComplianceManager,
    PolicyManager,
    AuditManager,
    EthicsManager,
    LicenseManager,
)
from ag3ntwerk.agents.accord.specialists import (
    ComplianceAnalyst,
    PolicyAnalyst,
    AuditCoordinator,
    EthicsOfficer,
    TrainingCoordinator,
    LicenseSpecialist,
)
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


# Compliance management task types
COMPLIANCE_CAPABILITIES = [
    # Regulatory compliance
    "compliance_assessment",
    "compliance_monitoring",
    "regulatory_analysis",
    "regulatory_mapping",
    "gap_analysis",
    "compliance_reporting",
    # Policy management
    "policy_review",
    "policy_creation",
    "policy_update",
    "policy_enforcement",
    "exception_management",
    # Audit management
    "audit_planning",
    "audit_preparation",
    "audit_response",
    "finding_remediation",
    "audit_reporting",
    # Licensing
    "license_tracking",
    "license_renewal",
    "certification_management",
    # Ethics
    "ethics_review",
    "conduct_investigation",
    "conflict_of_interest",
    # Training
    "compliance_training",
    "training_tracking",
]


class Accord(Manager):
    """
    Accord - Accord.

    The Accord is responsible for regulatory compliance, policy
    management, and ethics oversight within the ag3ntwerk system.

    Codename: Accord

    Core Responsibilities:
    - Regulatory compliance monitoring and assessment
    - Policy creation, review, and enforcement
    - Audit coordination and finding management
    - License and certification tracking
    - Ethics and conduct case management
    - Compliance training coordination

    Example:
        ```python
        ccomo = Accord(llm_provider=llm)

        task = Task(
            description="Assess GDPR compliance for customer data processing",
            task_type="compliance_assessment",
            context={"framework": "gdpr", "scope": "customer_data"},
        )
        result = await ccomo.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__(
            code="Accord",
            name="Accord",
            domain="Regulatory Compliance, Policy, Ethics",
            llm_provider=llm_provider,
        )
        self.codename = "Accord"

        self.capabilities = COMPLIANCE_CAPABILITIES

        # Compliance management state
        self._regulations: Dict[str, Regulation] = {}
        self._requirements: Dict[str, ComplianceRequirement] = {}
        self._policies: Dict[str, Policy] = {}
        self._audits: Dict[str, Audit] = {}
        self._findings: Dict[str, AuditFinding] = {}
        self._licenses: Dict[str, License] = {}
        self._assessments: Dict[str, ComplianceAssessment] = {}
        self._ethics_cases: Dict[str, EthicsCase] = {}

        # Initialize and register managers with their specialists
        self._init_managers()

    def _init_managers(self) -> None:
        """Initialize and register managers with their specialists."""
        # Create managers
        cm = ComplianceManager(llm_provider=self.llm_provider)
        pm = PolicyManager(llm_provider=self.llm_provider)
        aum = AuditManager(llm_provider=self.llm_provider)
        em = EthicsManager(llm_provider=self.llm_provider)
        lm = LicenseManager(llm_provider=self.llm_provider)

        # Create specialists
        compliance_analyst = ComplianceAnalyst(llm_provider=self.llm_provider)
        policy_analyst = PolicyAnalyst(llm_provider=self.llm_provider)
        audit_coordinator = AuditCoordinator(llm_provider=self.llm_provider)
        ethics_officer = EthicsOfficer(llm_provider=self.llm_provider)
        training_coordinator = TrainingCoordinator(llm_provider=self.llm_provider)
        license_specialist = LicenseSpecialist(llm_provider=self.llm_provider)

        # Register specialists with appropriate managers
        cm.register_subordinate(compliance_analyst)
        pm.register_subordinate(policy_analyst)
        aum.register_subordinate(audit_coordinator)
        em.register_subordinate(ethics_officer)
        cm.register_subordinate(training_coordinator)
        lm.register_subordinate(license_specialist)

        # Register managers with Accord
        self.register_subordinate(cm)
        self.register_subordinate(pm)
        self.register_subordinate(aum)
        self.register_subordinate(em)
        self.register_subordinate(lm)

    def can_handle(self, task: Task) -> bool:
        """Check if this is a compliance task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute a compliance task."""
        task.status = TaskStatus.IN_PROGRESS

        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            # Regulatory compliance handlers
            "compliance_assessment": self._handle_compliance_assessment,
            "compliance_monitoring": self._handle_compliance_monitoring,
            "regulatory_analysis": self._handle_regulatory_analysis,
            "regulatory_mapping": self._handle_regulatory_mapping,
            "gap_analysis": self._handle_gap_analysis,
            "compliance_reporting": self._handle_compliance_reporting,
            # Policy handlers
            "policy_review": self._handle_policy_review,
            "policy_creation": self._handle_policy_creation,
            "policy_update": self._handle_policy_update,
            "policy_enforcement": self._handle_policy_enforcement,
            "exception_management": self._handle_exception_management,
            # Audit handlers
            "audit_planning": self._handle_audit_planning,
            "audit_preparation": self._handle_audit_preparation,
            "audit_response": self._handle_audit_response,
            "finding_remediation": self._handle_finding_remediation,
            # Licensing handlers
            "license_tracking": self._handle_license_tracking,
            "license_renewal": self._handle_license_renewal,
            # Ethics handlers
            "ethics_review": self._handle_ethics_review,
            "conduct_investigation": self._handle_conduct_investigation,
            "conflict_of_interest": self._handle_conflict_of_interest,
            # Training handlers
            "compliance_training": self._handle_compliance_training,
        }
        return handlers.get(task_type)

    # =========================================================================
    # Regulatory Compliance Handlers
    # =========================================================================

    async def _handle_compliance_assessment(self, task: Task) -> TaskResult:
        """Perform compliance assessment against a framework."""
        framework = task.context.get("framework", "general")
        scope = task.context.get("scope", "")

        prompt = f"""As the Accord (Accord), perform compliance assessment.

Framework: {framework}
Scope: {scope}
Description: {task.description}
Context: {task.context}

Conduct a comprehensive compliance assessment including:
1. Applicable requirements identification
2. Current state assessment for each requirement
3. Compliance status determination (Compliant/Partial/Non-Compliant)
4. Evidence evaluation
5. Gap identification
6. Risk assessment for non-compliance
7. Remediation recommendations
8. Overall compliance score and opinion"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "assessment_type": "compliance",
                "framework": framework,
                "scope": scope,
                "assessment": response,
            },
            metrics={"task_type": "compliance_assessment"},
        )

    async def _handle_compliance_monitoring(self, task: Task) -> TaskResult:
        """Monitor ongoing compliance status."""
        frameworks = task.context.get("frameworks", [])

        # Gather current compliance data
        compliance_summary = {
            "requirements_count": len(self._requirements),
            "by_status": {},
            "overdue_count": 0,
        }

        for req in self._requirements.values():
            status = req.status.value
            compliance_summary["by_status"][status] = (
                compliance_summary["by_status"].get(status, 0) + 1
            )
            if req.is_overdue:
                compliance_summary["overdue_count"] += 1

        prompt = f"""As the Accord (Accord), provide compliance monitoring update.

Frameworks: {frameworks if frameworks else 'All monitored frameworks'}
Current Status Summary: {compliance_summary}
Description: {task.description}
Context: {task.context}

Provide monitoring update including:
1. Overall compliance health
2. Key compliance metrics
3. Requirements approaching due date
4. Recent changes in regulatory landscape
5. Areas of concern
6. Recommended actions
7. Upcoming compliance deadlines"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "monitoring_type": "compliance",
                "summary": compliance_summary,
                "update": response,
            },
        )

    async def _handle_regulatory_analysis(self, task: Task) -> TaskResult:
        """Analyze regulatory requirements."""
        regulation = task.context.get("regulation", task.description)

        prompt = f"""As the Accord (Accord), analyze regulation.

Regulation: {regulation}
Description: {task.description}
Context: {task.context}

Analyze the regulation including:
1. Purpose and scope
2. Key requirements
3. Applicability to our organization
4. Compliance obligations
5. Penalties for non-compliance
6. Timeline and deadlines
7. Relationship to other regulations
8. Implementation considerations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "regulatory",
                "regulation": regulation,
                "analysis": response,
            },
        )

    async def _handle_regulatory_mapping(self, task: Task) -> TaskResult:
        """Map regulations to controls and processes."""
        framework = task.context.get("framework", "")

        prompt = f"""As the Accord (Accord), create regulatory mapping.

Framework: {framework}
Description: {task.description}
Context: {task.context}

Create a mapping that includes:
1. Regulatory requirement reference
2. Requirement description
3. Applicable controls
4. Responsible parties
5. Evidence required
6. Current compliance status
7. Gaps identified
8. Remediation needed"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "mapping_type": "regulatory",
                "framework": framework,
                "mapping": response,
            },
        )

    async def _handle_gap_analysis(self, task: Task) -> TaskResult:
        """Perform compliance gap analysis."""
        framework = task.context.get("framework", "")
        target_state = task.context.get("target_state", "full_compliance")

        prompt = f"""As the Accord (Accord), perform gap analysis.

Framework: {framework}
Target State: {target_state}
Description: {task.description}
Context: {task.context}

Perform gap analysis including:
1. Current state assessment
2. Target state definition
3. Identified gaps
4. Gap severity rating
5. Root cause for each gap
6. Remediation recommendations
7. Resource requirements
8. Prioritized action plan"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "gap",
                "framework": framework,
                "target_state": target_state,
                "analysis": response,
            },
        )

    async def _handle_compliance_reporting(self, task: Task) -> TaskResult:
        """Generate compliance reports."""
        report_type = task.context.get("report_type", "summary")
        audience = task.context.get("audience", "management")

        prompt = f"""As the Accord (Accord), generate compliance report.

Report Type: {report_type}
Audience: {audience}
Description: {task.description}
Context: {task.context}

Generate a compliance report including:
1. Agent summary
2. Compliance scorecard
3. Key metrics and trends
4. Risk areas
5. Regulatory updates
6. Audit status
7. Remediation progress
8. Recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "report_type": report_type,
                "audience": audience,
                "report": response,
            },
        )

    # =========================================================================
    # Policy Management Handlers
    # =========================================================================

    async def _handle_policy_review(self, task: Task) -> TaskResult:
        """Review existing policies."""
        policy_id = task.context.get("policy_id", "")
        policy_name = task.context.get("policy_name", task.description)

        prompt = f"""As the Accord (Accord), review policy.

Policy: {policy_name}
Description: {task.description}
Context: {task.context}

Review the policy for:
1. Currency and relevance
2. Regulatory alignment
3. Clarity and completeness
4. Consistency with other policies
5. Enforceability
6. Gap identification
7. Recommended updates
8. Approval status"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "review_type": "policy",
                "policy": policy_name,
                "review": response,
            },
        )

    async def _handle_policy_creation(self, task: Task) -> TaskResult:
        """Create a new policy."""
        policy_type = task.context.get("policy_type", "general")
        topic = task.context.get("topic", task.description)

        prompt = f"""As the Accord (Accord), create policy.

Policy Type: {policy_type}
Topic: {topic}
Description: {task.description}
Context: {task.context}

Create a policy document including:
1. Policy title and purpose
2. Scope and applicability
3. Definitions
4. Policy statement
5. Roles and responsibilities
6. Procedures
7. Compliance requirements
8. Exceptions process
9. Related policies
10. Review schedule"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "creation_type": "policy",
                "policy_type": policy_type,
                "topic": topic,
                "policy": response,
            },
        )

    async def _handle_policy_update(self, task: Task) -> TaskResult:
        """Update an existing policy."""
        policy_name = task.context.get("policy_name", task.description)
        changes = task.context.get("changes", [])

        prompt = f"""As the Accord (Accord), update policy.

Policy: {policy_name}
Requested Changes: {changes}
Description: {task.description}
Context: {task.context}

Provide policy update including:
1. Summary of changes
2. Rationale for changes
3. Impact assessment
4. Updated sections
5. Effective date
6. Communication plan
7. Training requirements"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "update_type": "policy",
                "policy": policy_name,
                "update": response,
            },
        )

    async def _handle_policy_enforcement(self, task: Task) -> TaskResult:
        """Enforce policy compliance."""
        policy_name = task.context.get("policy_name", "")
        violation = task.context.get("violation", task.description)

        prompt = f"""As the Accord (Accord), handle policy enforcement.

Policy: {policy_name}
Violation/Issue: {violation}
Description: {task.description}
Context: {task.context}

Provide enforcement guidance including:
1. Violation assessment
2. Applicable policy provisions
3. Severity determination
4. Required actions
5. Notification requirements
6. Documentation needs
7. Follow-up procedures
8. Preventive measures"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "enforcement_type": "policy",
                "policy": policy_name,
                "violation": violation,
                "guidance": response,
            },
        )

    async def _handle_exception_management(self, task: Task) -> TaskResult:
        """Manage policy exceptions."""
        policy_name = task.context.get("policy_name", "")
        exception_request = task.context.get("exception", task.description)

        prompt = f"""As the Accord (Accord), evaluate exception request.

Policy: {policy_name}
Exception Request: {exception_request}
Description: {task.description}
Context: {task.context}

Evaluate the exception including:
1. Justification assessment
2. Risk evaluation
3. Compensating controls
4. Time limitation
5. Approval recommendation
6. Conditions/requirements
7. Monitoring approach
8. Documentation needs"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "evaluation_type": "exception",
                "policy": policy_name,
                "request": exception_request,
                "evaluation": response,
            },
        )

    # =========================================================================
    # Audit Management Handlers
    # =========================================================================

    async def _handle_audit_planning(self, task: Task) -> TaskResult:
        """Plan audit engagement."""
        audit_type = task.context.get("audit_type", "internal")
        scope = task.context.get("scope", "")

        prompt = f"""As the Accord (Accord), plan audit.

Audit Type: {audit_type}
Scope: {scope}
Description: {task.description}
Context: {task.context}

Create audit plan including:
1. Audit objectives
2. Scope and boundaries
3. Methodology
4. Timeline
5. Resource requirements
6. Key stakeholders
7. Risk areas to focus
8. Deliverables
9. Communication plan"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "plan_type": "audit",
                "audit_type": audit_type,
                "scope": scope,
                "plan": response,
            },
        )

    async def _handle_audit_preparation(self, task: Task) -> TaskResult:
        """Prepare for audit engagement."""
        audit_name = task.context.get("audit_name", task.description)
        framework = task.context.get("framework", "")

        prompt = f"""As the Accord (Accord), prepare for audit.

Audit: {audit_name}
Framework: {framework}
Description: {task.description}
Context: {task.context}

Prepare for audit including:
1. Documentation checklist
2. Evidence requirements
3. Control testing preparation
4. Key contacts and SMEs
5. Potential risk areas
6. Prior finding status
7. Interview preparation
8. Timeline coordination"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "preparation_type": "audit",
                "audit": audit_name,
                "preparation": response,
            },
        )

    async def _handle_audit_response(self, task: Task) -> TaskResult:
        """Respond to audit requests or findings."""
        request = task.context.get("request", task.description)

        prompt = f"""As the Accord (Accord), respond to audit.

Request/Finding: {request}
Description: {task.description}
Context: {task.context}

Provide audit response including:
1. Request acknowledgment
2. Relevant documentation
3. Evidence provided
4. Clarifications
5. Additional context
6. Management response (if finding)
7. Remediation plan (if needed)
8. Timeline commitment"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "response_type": "audit",
                "request": request,
                "response": response,
            },
        )

    async def _handle_finding_remediation(self, task: Task) -> TaskResult:
        """Plan remediation for audit findings."""
        finding = task.context.get("finding", task.description)
        severity = task.context.get("severity", "medium")

        prompt = f"""As the Accord (Accord), plan finding remediation.

Finding: {finding}
Severity: {severity}
Description: {task.description}
Context: {task.context}

Create remediation plan including:
1. Root cause analysis
2. Remediation approach
3. Specific action items
4. Responsible parties
5. Timeline
6. Resource needs
7. Success criteria
8. Validation approach"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "remediation_type": "finding",
                "finding": finding,
                "severity": severity,
                "plan": response,
            },
        )

    # =========================================================================
    # Licensing Handlers
    # =========================================================================

    async def _handle_license_tracking(self, task: Task) -> TaskResult:
        """Track licenses and certifications."""
        license_type = task.context.get("license_type", "all")

        # Gather license data
        license_summary = {
            "total_licenses": len(self._licenses),
            "expiring_soon": 0,
            "expired": 0,
        }

        for lic in self._licenses.values():
            if lic.is_expired:
                license_summary["expired"] += 1
            elif lic.needs_renewal:
                license_summary["expiring_soon"] += 1

        prompt = f"""As the Accord (Accord), track licenses.

License Type: {license_type}
Current Status: {license_summary}
Description: {task.description}
Context: {task.context}

Provide license tracking update including:
1. Active licenses summary
2. Upcoming renewals
3. Expired licenses
4. Cost summary
5. Compliance requirements
6. Action items
7. Risk areas"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "tracking_type": "license",
                "license_type": license_type,
                "summary": license_summary,
                "tracking": response,
            },
        )

    async def _handle_license_renewal(self, task: Task) -> TaskResult:
        """Process license renewal."""
        license_name = task.context.get("license_name", task.description)

        prompt = f"""As the Accord (Accord), process license renewal.

License: {license_name}
Description: {task.description}
Context: {task.context}

Provide renewal guidance including:
1. Renewal requirements
2. Documentation needed
3. Timeline
4. Cost estimate
5. Approval process
6. Submission steps
7. Follow-up actions"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "renewal_type": "license",
                "license": license_name,
                "guidance": response,
            },
        )

    # =========================================================================
    # Ethics Handlers
    # =========================================================================

    async def _handle_ethics_review(self, task: Task) -> TaskResult:
        """Review ethics-related matter."""
        matter = task.context.get("matter", task.description)

        prompt = f"""As the Accord (Accord), review ethics matter.

Matter: {matter}
Description: {task.description}
Context: {task.context}

Provide ethics review including:
1. Issue identification
2. Applicable policies/codes
3. Stakeholder impact
4. Legal considerations
5. Recommended course of action
6. Communication guidance
7. Documentation requirements"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "review_type": "ethics",
                "matter": matter,
                "review": response,
            },
        )

    async def _handle_conduct_investigation(self, task: Task) -> TaskResult:
        """Conduct investigation into conduct issue."""
        allegation = task.context.get("allegation", task.description)

        prompt = f"""As the Accord (Accord), conduct investigation.

Allegation: {allegation}
Description: {task.description}
Context: {task.context}

Provide investigation guidance including:
1. Investigation scope
2. Evidence to gather
3. Interviews to conduct
4. Timeline
5. Confidentiality measures
6. Documentation requirements
7. Reporting structure
8. Interim measures"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "investigation_type": "conduct",
                "allegation": allegation,
                "guidance": response,
            },
        )

    async def _handle_conflict_of_interest(self, task: Task) -> TaskResult:
        """Evaluate conflict of interest."""
        situation = task.context.get("situation", task.description)

        prompt = f"""As the Accord (Accord), evaluate conflict of interest.

Situation: {situation}
Description: {task.description}
Context: {task.context}

Provide COI evaluation including:
1. Nature of potential conflict
2. Relationship to organization
3. Materiality assessment
4. Applicable policies
5. Mitigation options
6. Disclosure requirements
7. Recommended course of action
8. Documentation needs"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "evaluation_type": "conflict_of_interest",
                "situation": situation,
                "evaluation": response,
            },
        )

    # =========================================================================
    # Training Handlers
    # =========================================================================

    async def _handle_compliance_training(self, task: Task) -> TaskResult:
        """Manage compliance training."""
        training_topic = task.context.get("topic", task.description)
        audience = task.context.get("audience", "all_employees")

        prompt = f"""As the Accord (Accord), manage compliance training.

Topic: {training_topic}
Audience: {audience}
Description: {task.description}
Context: {task.context}

Provide training plan including:
1. Training objectives
2. Content outline
3. Delivery method
4. Duration and schedule
5. Assessment approach
6. Completion tracking
7. Remediation for non-compliance
8. Record keeping"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "training_type": "compliance",
                "topic": training_topic,
                "audience": audience,
                "plan": response,
            },
        )

    # =========================================================================
    # Fallback Handler
    # =========================================================================

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM when no specific handler exists."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider and no handler for task type",
            )

        prompt = f"""As the Accord (Accord) specializing in regulatory
compliance and ethics, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough compliance-focused response."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )

    # =========================================================================
    # Compliance Management Methods
    # =========================================================================

    def register_regulation(self, regulation: Regulation) -> str:
        """Register a regulation."""
        self._regulations[regulation.id] = regulation
        return regulation.id

    def register_requirement(self, requirement: ComplianceRequirement) -> str:
        """Register a compliance requirement."""
        self._requirements[requirement.id] = requirement
        return requirement.id

    def register_policy(self, policy: Policy) -> str:
        """Register a policy."""
        self._policies[policy.id] = policy
        return policy.id

    def register_audit(self, audit: Audit) -> str:
        """Register an audit engagement."""
        self._audits[audit.id] = audit
        return audit.id

    def register_finding(self, finding: AuditFinding) -> str:
        """Register an audit finding."""
        self._findings[finding.id] = finding
        return finding.id

    def register_license(self, license: License) -> str:
        """Register a license."""
        self._licenses[license.id] = license
        return license.id

    def register_ethics_case(self, case: EthicsCase) -> str:
        """Register an ethics case."""
        self._ethics_cases[case.id] = case
        return case.id

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    def get_policies_by_status(self, status: PolicyStatus) -> List[Policy]:
        """Get policies by status."""
        return [p for p in self._policies.values() if p.status == status]

    def get_overdue_requirements(self) -> List[ComplianceRequirement]:
        """Get overdue compliance requirements."""
        return [r for r in self._requirements.values() if r.is_overdue]

    def get_open_findings(self) -> List[AuditFinding]:
        """Get open audit findings."""
        return [
            f
            for f in self._findings.values()
            if f.status in (FindingStatus.OPEN, FindingStatus.IN_REMEDIATION)
        ]

    def get_expiring_licenses(self, days: int = 90) -> List[License]:
        """Get licenses expiring within specified days."""
        return [l for l in self._licenses.values() if l.needs_renewal]

    def get_compliance_status(self) -> Dict[str, Any]:
        """Get current compliance status."""
        requirement_status: Dict[str, int] = {}
        for req in self._requirements.values():
            status = req.status.value
            requirement_status[status] = requirement_status.get(status, 0) + 1

        finding_status: Dict[str, int] = {}
        for finding in self._findings.values():
            status = finding.status.value
            finding_status[status] = finding_status.get(status, 0) + 1

        return {
            "regulations_tracked": len(self._regulations),
            "requirements": {
                "total": len(self._requirements),
                "by_status": requirement_status,
                "overdue": len(self.get_overdue_requirements()),
            },
            "policies": {
                "total": len(self._policies),
                "active": len(
                    [p for p in self._policies.values() if p.status == PolicyStatus.ACTIVE]
                ),
                "needs_review": len([p for p in self._policies.values() if p.needs_review]),
            },
            "audits": {
                "total": len(self._audits),
                "in_progress": len(
                    [a for a in self._audits.values() if a.status == AuditStatus.IN_PROGRESS]
                ),
            },
            "findings": {
                "total": len(self._findings),
                "by_status": finding_status,
                "overdue": len([f for f in self._findings.values() if f.is_overdue]),
            },
            "licenses": {
                "total": len(self._licenses),
                "expiring_soon": len(self.get_expiring_licenses()),
                "expired": len([l for l in self._licenses.values() if l.is_expired]),
            },
            "ethics_cases": {
                "total": len(self._ethics_cases),
                "open": len([c for c in self._ethics_cases.values() if c.status == "open"]),
            },
            "capabilities": self.capabilities,
        }
