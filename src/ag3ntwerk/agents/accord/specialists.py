"""
Specialists for the Accord (Accord) agent.

Specialists are the workers that perform specific operational tasks
within compliance management.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Specialist,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider


class ComplianceAnalyst(Specialist):
    """
    Specialist responsible for compliance analysis.

    Handles compliance assessments, regulatory analysis,
    and gap identification.

    Capabilities:
    - Compliance assessment
    - Regulatory analysis
    - Gap analysis
    - Compliance monitoring
    - Remediation planning
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="CAN",
            name="Compliance Analyst",
            domain="Compliance Assessment, Regulatory Analysis",
            capabilities=[
                "compliance_assessment",
                "compliance_monitoring",
                "regulatory_analysis",
                "regulatory_mapping",
                "gap_analysis",
                "compliance_check",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute compliance analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "compliance_assessment": self._handle_assessment,
            "regulatory_analysis": self._handle_regulatory,
            "gap_analysis": self._handle_gap,
            "compliance_monitoring": self._handle_monitoring,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_assessment(self, task: Task) -> TaskResult:
        """Handle compliance assessment task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        framework = task.context.get("framework", "general")

        prompt = f"""As a Compliance Analyst, perform compliance assessment:

Framework: {framework}
Description: {task.description}
Context: {task.context}

Assess compliance including:
1. Applicable requirements
2. Current state for each requirement
3. Compliance status (Compliant/Partial/Non-Compliant)
4. Evidence evaluation
5. Gap identification
6. Risk assessment
7. Remediation recommendations
8. Overall compliance score"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "compliance_assessment": response,
                "framework": framework,
                "specialist": self.code,
            },
        )

    async def _handle_regulatory(self, task: Task) -> TaskResult:
        """Handle regulatory analysis task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Compliance Analyst, analyze regulation:

Description: {task.description}
Context: {task.context}

Analyze including:
1. Purpose and scope
2. Key requirements
3. Applicability assessment
4. Compliance obligations
5. Penalties for non-compliance
6. Timeline and deadlines
7. Related regulations
8. Implementation considerations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"regulatory_analysis": response, "specialist": self.code},
        )

    async def _handle_gap(self, task: Task) -> TaskResult:
        """Handle gap analysis task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Compliance Analyst, perform gap analysis:

Description: {task.description}
Context: {task.context}

Analyze gaps including:
1. Current state assessment
2. Target state definition
3. Identified gaps
4. Gap severity rating
5. Root cause analysis
6. Remediation recommendations
7. Resource requirements
8. Prioritized action plan"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"gap_analysis": response, "specialist": self.code},
        )

    async def _handle_monitoring(self, task: Task) -> TaskResult:
        """Handle compliance monitoring task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Compliance Analyst, provide monitoring update:

Description: {task.description}
Context: {task.context}

Provide monitoring including:
1. Overall compliance health
2. Key compliance metrics
3. Approaching deadlines
4. Regulatory changes
5. Areas of concern
6. Recommended actions
7. Upcoming requirements"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"monitoring_update": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic compliance task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Compliance Analyst, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide compliance analysis and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class PolicyAnalyst(Specialist):
    """
    Specialist responsible for policy analysis.

    Handles policy review, creation, and updates.

    Capabilities:
    - Policy review
    - Policy creation
    - Policy updates
    - Exception evaluation
    - Policy enforcement support
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="PA",
            name="Policy Analyst",
            domain="Policy Analysis, Review, Development",
            capabilities=[
                "policy_review",
                "policy_creation",
                "policy_update",
                "exception_management",
                "policy_enforcement",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute policy analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "policy_review": self._handle_review,
            "policy_creation": self._handle_creation,
            "policy_update": self._handle_update,
            "exception_management": self._handle_exception,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_review(self, task: Task) -> TaskResult:
        """Handle policy review task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Policy Analyst, review this policy:

Description: {task.description}
Context: {task.context}

Review for:
1. Currency and relevance
2. Regulatory alignment
3. Clarity and completeness
4. Consistency with other policies
5. Enforceability
6. Gap identification
7. Recommended updates
8. Approval recommendation"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"policy_review": response, "specialist": self.code},
        )

    async def _handle_creation(self, task: Task) -> TaskResult:
        """Handle policy creation task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Policy Analyst, create policy:

Description: {task.description}
Context: {task.context}

Create policy document including:
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
            output={"policy_document": response, "specialist": self.code},
        )

    async def _handle_update(self, task: Task) -> TaskResult:
        """Handle policy update task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Policy Analyst, update policy:

Description: {task.description}
Context: {task.context}

Provide update including:
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
            output={"policy_update": response, "specialist": self.code},
        )

    async def _handle_exception(self, task: Task) -> TaskResult:
        """Handle exception management task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Policy Analyst, evaluate exception:

Description: {task.description}
Context: {task.context}

Evaluate including:
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
            output={"exception_evaluation": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic policy task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Policy Analyst, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide policy analysis and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class AuditCoordinator(Specialist):
    """
    Specialist responsible for audit coordination.

    Handles audit planning, preparation, and finding management.

    Capabilities:
    - Audit planning
    - Audit preparation
    - Evidence coordination
    - Finding management
    - Remediation tracking
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="AC",
            name="Audit Coordinator",
            domain="Audit Coordination, Planning, Findings",
            capabilities=[
                "audit_planning",
                "audit_preparation",
                "audit_response",
                "finding_remediation",
                "audit_coordination",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute audit coordination task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "audit_planning": self._handle_planning,
            "audit_preparation": self._handle_preparation,
            "audit_response": self._handle_response,
            "finding_remediation": self._handle_remediation,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_planning(self, task: Task) -> TaskResult:
        """Handle audit planning task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Audit Coordinator, plan audit:

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
            output={"audit_plan": response, "specialist": self.code},
        )

    async def _handle_preparation(self, task: Task) -> TaskResult:
        """Handle audit preparation task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Audit Coordinator, prepare for audit:

Description: {task.description}
Context: {task.context}

Prepare including:
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
            output={"audit_preparation": response, "specialist": self.code},
        )

    async def _handle_response(self, task: Task) -> TaskResult:
        """Handle audit response task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Audit Coordinator, respond to audit:

Description: {task.description}
Context: {task.context}

Provide response including:
1. Request acknowledgment
2. Relevant documentation
3. Evidence provided
4. Clarifications
5. Additional context
6. Management response
7. Remediation plan
8. Timeline commitment"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"audit_response": response, "specialist": self.code},
        )

    async def _handle_remediation(self, task: Task) -> TaskResult:
        """Handle finding remediation task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Audit Coordinator, plan finding remediation:

Description: {task.description}
Context: {task.context}

Create plan including:
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
            output={"remediation_plan": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic audit task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Audit Coordinator, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide audit coordination guidance."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class EthicsOfficer(Specialist):
    """
    Specialist responsible for ethics and conduct matters.

    Handles ethics reviews, investigations, and
    conflict of interest evaluations.

    Capabilities:
    - Ethics review
    - Conduct investigation
    - Conflict of interest evaluation
    - Ethics case management
    - Ethics guidance
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="EO",
            name="Ethics Officer",
            domain="Ethics, Conduct, Investigations",
            capabilities=[
                "ethics_review",
                "conduct_investigation",
                "conflict_of_interest",
                "ethics_case_management",
                "ethics_guidance",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute ethics task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "ethics_review": self._handle_review,
            "conduct_investigation": self._handle_investigation,
            "conflict_of_interest": self._handle_coi,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_review(self, task: Task) -> TaskResult:
        """Handle ethics review task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Ethics Officer, review ethics matter:

Description: {task.description}
Context: {task.context}

Provide review including:
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
            output={"ethics_review": response, "specialist": self.code},
        )

    async def _handle_investigation(self, task: Task) -> TaskResult:
        """Handle conduct investigation task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Ethics Officer, plan investigation:

Description: {task.description}
Context: {task.context}

Provide investigation guidance:
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
            output={"investigation_guidance": response, "specialist": self.code},
        )

    async def _handle_coi(self, task: Task) -> TaskResult:
        """Handle conflict of interest task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Ethics Officer, evaluate conflict of interest:

Description: {task.description}
Context: {task.context}

Evaluate including:
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
            output={"coi_evaluation": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic ethics task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Ethics Officer, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide ethics guidance and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class TrainingCoordinator(Specialist):
    """
    Specialist responsible for compliance training.

    Handles training program design, tracking, and
    compliance verification.

    Capabilities:
    - Training program design
    - Training tracking
    - Compliance verification
    - Training material review
    - Assessment design
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="TC",
            name="Training Coordinator",
            domain="Compliance Training, Tracking, Assessment",
            capabilities=[
                "compliance_training",
                "training_tracking",
                "training_design",
                "assessment_design",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute training coordination task."""
        task.status = TaskStatus.IN_PROGRESS

        return await self._handle_training(task)

    async def _handle_training(self, task: Task) -> TaskResult:
        """Handle training task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Training Coordinator, handle training request:

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
            output={"training_plan": response, "specialist": self.code},
        )


class LicenseSpecialist(Specialist):
    """
    Specialist responsible for license and certification management.

    Handles license tracking, renewals, compliance verification,
    and certification maintenance.

    Capabilities:
    - License tracking
    - License renewal
    - Certification management
    - License compliance verification
    - Cost analysis for licenses
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="LS",
            name="License Specialist",
            domain="License Management, Certification, Renewals",
            capabilities=[
                "license_tracking",
                "license_renewal",
                "certification_management",
                "license_compliance",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute license management task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "license_tracking": self._handle_tracking,
            "license_renewal": self._handle_renewal,
            "certification_management": self._handle_certification,
            "license_compliance": self._handle_compliance,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_tracking(self, task: Task) -> TaskResult:
        """Handle license tracking task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        license_type = task.context.get("license_type", "all")

        prompt = f"""As a License Specialist, track licenses:

License Type: {license_type}
Description: {task.description}
Context: {task.context}

Provide license tracking including:
1. License inventory status
2. Active licenses summary
3. Upcoming renewal deadlines
4. Expired or at-risk licenses
5. Cost summary by category
6. Compliance requirements
7. Action items and priorities
8. Risk areas"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "license_tracking": response,
                "license_type": license_type,
                "specialist": self.code,
            },
        )

    async def _handle_renewal(self, task: Task) -> TaskResult:
        """Handle license renewal task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        license_name = task.context.get("license_name", task.description)

        prompt = f"""As a License Specialist, process license renewal:

License: {license_name}
Description: {task.description}
Context: {task.context}

Provide renewal guidance including:
1. Current license status
2. Renewal requirements
3. Documentation needed
4. Timeline and deadlines
5. Cost estimate
6. Approval process
7. Submission steps
8. Post-renewal verification"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "renewal_guidance": response,
                "license": license_name,
                "specialist": self.code,
            },
        )

    async def _handle_certification(self, task: Task) -> TaskResult:
        """Handle certification management task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        certification = task.context.get("certification", task.description)

        prompt = f"""As a License Specialist, manage certification:

Certification: {certification}
Description: {task.description}
Context: {task.context}

Provide certification management including:
1. Certification requirements
2. Current status
3. Maintenance requirements
4. Continuing education needs
5. Renewal timeline
6. Associated costs
7. Documentation requirements
8. Compliance verification"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "certification_management": response,
                "certification": certification,
                "specialist": self.code,
            },
        )

    async def _handle_compliance(self, task: Task) -> TaskResult:
        """Handle license compliance verification task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a License Specialist, verify license compliance:

Description: {task.description}
Context: {task.context}

Provide compliance verification including:
1. License requirements check
2. Current compliance status
3. Gaps identified
4. Regulatory requirements
5. Risk assessment
6. Remediation recommendations
7. Documentation status
8. Action plan"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "compliance_verification": response,
                "specialist": self.code,
            },
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic license task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a License Specialist, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide license management guidance and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )
