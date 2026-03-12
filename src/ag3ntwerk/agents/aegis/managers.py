"""
Managers for the Aegis (Aegis) agent.

Managers coordinate specialist teams and handle complex workflows
within risk management domains.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Manager,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider


class RiskAssessmentManager(Manager):
    """
    Manager for risk assessment operations.

    Coordinates risk identification, analysis, evaluation,
    and treatment planning across the enterprise.

    Responsibilities:
    - Risk identification coordination
    - Risk analysis oversight
    - Risk scoring and prioritization
    - Risk treatment planning
    - Risk register management
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="RAM",
            name="Risk Assessment Manager",
            domain="Risk Assessment, Analysis, Evaluation",
            llm_provider=llm_provider,
        )
        self.capabilities = [
            "risk_assessment",
            "risk_identification",
            "risk_quantification",
            "risk_scoring",
            "risk_register",
            "risk_review",
            "mitigation_planning",
            "risk_treatment",
        ]

    def can_handle(self, task: Task) -> bool:
        """Check if this manager can handle the task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute risk assessment task or delegate to specialists."""
        task.status = TaskStatus.IN_PROGRESS

        # Try to delegate to appropriate specialist
        specialist_code = self._route_to_specialist(task.task_type)
        if specialist_code and specialist_code in self._subordinates:
            return await self.delegate(task, specialist_code)

        # Handle directly with LLM
        return await self._handle_with_llm(task)

    def _route_to_specialist(self, task_type: str) -> Optional[str]:
        """Route task to appropriate specialist."""
        routing = {
            "risk_assessment": "RA",  # Risk Analyst
            "risk_identification": "RA",
            "risk_quantification": "RA",
            "risk_scoring": "RA",
            "mitigation_planning": "CA",  # Controls Analyst
            "control_assessment": "CA",
            "control_design": "CA",
        }
        return routing.get(task_type)

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider available",
            )

        prompt = f"""As the Risk Assessment Manager, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide comprehensive risk assessment including:
1. Risk identification
2. Likelihood and impact analysis
3. Risk scoring and prioritization
4. Treatment recommendations
5. Monitoring approach"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"assessment": response, "manager": self.code},
        )


class ThreatModelingManager(Manager):
    """
    Manager for threat modeling operations.

    Coordinates threat identification, analysis, and
    security architecture review.

    Responsibilities:
    - Threat modeling methodology
    - Attack surface analysis
    - Threat scenario development
    - Security architecture review
    - Mitigation strategy coordination
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="TMM",
            name="Threat Modeling Manager",
            domain="Threat Modeling, Security Analysis",
            llm_provider=llm_provider,
        )
        self.capabilities = [
            "threat_modeling",
            "threat_analysis",
            "attack_surface_analysis",
            "vulnerability_assessment",
            "security_architecture_review",
        ]

    def can_handle(self, task: Task) -> bool:
        """Check if this manager can handle the task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute threat modeling task or delegate."""
        task.status = TaskStatus.IN_PROGRESS

        # Try to delegate to Threat Analyst
        if "TA" in self._subordinates:
            return await self.delegate(task, "TA")

        return await self._handle_with_llm(task)

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider available",
            )

        methodology = task.context.get("methodology", "STRIDE")

        prompt = f"""As the Threat Modeling Manager, handle this task:

Methodology: {methodology}
Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Using {methodology} methodology, provide:
1. Threat identification
2. Attack vector analysis
3. Severity assessment
4. Mitigation strategies
5. Residual risk assessment"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "threat_model": response,
                "methodology": methodology,
                "manager": self.code,
            },
        )


class BCPManager(Manager):
    """
    Manager for Business Continuity Planning operations.

    Coordinates disaster recovery, impact analysis, and
    continuity planning efforts.

    Responsibilities:
    - Business impact analysis
    - Recovery strategy development
    - DR planning and testing
    - Crisis management planning
    - Continuity program governance
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="BCPM",
            name="BCP Manager",
            domain="Business Continuity, Disaster Recovery",
            llm_provider=llm_provider,
        )
        self.capabilities = [
            "bcp_planning",
            "disaster_recovery",
            "impact_analysis",
            "recovery_planning",
            "crisis_management",
            "continuity_testing",
        ]

    def can_handle(self, task: Task) -> bool:
        """Check if this manager can handle the task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute BCP task or delegate to specialist."""
        task.status = TaskStatus.IN_PROGRESS

        # Try to delegate to BCP Specialist
        if "BCP" in self._subordinates:
            return await self.delegate(task, "BCP")

        return await self._handle_with_llm(task)

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider available",
            )

        prompt = f"""As the BCP Manager, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide comprehensive BCP/DR guidance including:
1. Business impact assessment
2. Recovery objectives (RTO/RPO)
3. Recovery strategies
4. Resource requirements
5. Testing and maintenance plan
6. Communication procedures"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"bcp_plan": response, "manager": self.code},
        )


class IncidentManager(Manager):
    """
    Manager for incident management operations.

    Coordinates incident response, analysis, and
    lessons learned activities.

    Responsibilities:
    - Incident response coordination
    - Root cause analysis oversight
    - Lessons learned facilitation
    - Incident trend analysis
    - Process improvement recommendations
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="IM",
            name="Incident Manager",
            domain="Incident Management, Response, Analysis",
            llm_provider=llm_provider,
        )
        self.capabilities = [
            "incident_analysis",
            "root_cause_analysis",
            "lessons_learned",
            "incident_response",
            "incident_trending",
        ]

    def can_handle(self, task: Task) -> bool:
        """Check if this manager can handle the task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute incident management task or delegate."""
        task.status = TaskStatus.IN_PROGRESS

        # Try to delegate to Incident Analyst
        if "IA" in self._subordinates:
            return await self.delegate(task, "IA")

        return await self._handle_with_llm(task)

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider available",
            )

        prompt = f"""As the Incident Manager, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide incident management guidance including:
1. Incident assessment
2. Impact analysis
3. Response actions
4. Root cause determination
5. Corrective actions
6. Preventive measures
7. Lessons learned"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"incident_analysis": response, "manager": self.code},
        )
