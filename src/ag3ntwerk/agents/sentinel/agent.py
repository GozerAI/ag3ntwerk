"""
Sentinel (Sentinel) Agent - Sentinel.

Codename: Sentinel
Core function: Govern information, systems-of-record, and decision integrity.

The Sentinel handles all information governance and security-related tasks:
- Data governance and knowledge management
- Vulnerability scanning and threat analysis
- Security audits and compliance checks
- Access control review and incident response
- Truth/verification workflows

Sphere of influence: Data governance, knowledge management, internal tooling,
IT/business systems, information security alignment, truth/verification workflows.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Manager,
    Specialist,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider
from ag3ntwerk.agents.sentinel.managers import (
    DataGovernanceManager,
    ITSystemsManager,
    KnowledgeManager,
    VerificationManager,
)
from ag3ntwerk.agents.sentinel.specialists import (
    DataSteward,
    SecurityAnalyst,
    KnowledgeSpecialist,
    SystemsAnalyst,
)


# Security task types this agent can handle
SECURITY_CAPABILITIES = [
    "security_scan",
    "vulnerability_check",
    "threat_analysis",
    "access_audit",
    "compliance_check",
    "incident_response",
    "security_review",
    "penetration_test",
    "risk_assessment",
]


class Sentinel(Manager):
    """
    Sentinel - Sentinel.

    The Sentinel is responsible for all information governance and security
    operations within the ag3ntwerk system. It manages security
    specialists and coordinates security workflows.

    Codename: Sentinel

    Core Responsibilities:
    - Security scanning and vulnerability detection
    - Threat intelligence and analysis
    - Compliance monitoring
    - Access control management
    - Incident response coordination

    Example:
        ```python
        cio = Sentinel(llm_provider=llm)

        task = Task(
            description="Scan auth module for vulnerabilities",
            task_type="security_scan",
            context={"target": "src/auth/"},
        )
        result = await cio.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__(
            code="Sentinel",
            name="Sentinel",
            domain="Security, Compliance, Risk Management",
            llm_provider=llm_provider,
        )
        self.codename = "Sentinel"

        self.capabilities = SECURITY_CAPABILITIES

        # Security-specific state
        self._threat_intel: Dict[str, Any] = {}
        self._active_incidents: List[Dict[str, Any]] = []
        self._compliance_status: Dict[str, bool] = {}

        # Initialize and register managers with their specialists
        self._init_managers()

    def _init_managers(self) -> None:
        """Initialize and register managers with their specialists."""
        # Create managers
        dg_mgr = DataGovernanceManager(llm_provider=self.llm_provider)
        it_mgr = ITSystemsManager(llm_provider=self.llm_provider)
        km_mgr = KnowledgeManager(llm_provider=self.llm_provider)
        vm_mgr = VerificationManager(llm_provider=self.llm_provider)

        # Create specialists
        data_steward = DataSteward(llm_provider=self.llm_provider)
        security_analyst = SecurityAnalyst(llm_provider=self.llm_provider)
        knowledge_specialist = KnowledgeSpecialist(llm_provider=self.llm_provider)
        systems_analyst = SystemsAnalyst(llm_provider=self.llm_provider)

        # Register specialists with appropriate managers
        dg_mgr.register_subordinate(data_steward)
        it_mgr.register_subordinate(systems_analyst)
        km_mgr.register_subordinate(knowledge_specialist)
        vm_mgr.register_subordinate(security_analyst)

        # Register managers with Sentinel
        self.register_subordinate(dg_mgr)
        self.register_subordinate(it_mgr)
        self.register_subordinate(km_mgr)
        self.register_subordinate(vm_mgr)

    def can_handle(self, task: Task) -> bool:
        """Check if this is a security-related task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute a security task."""
        task.status = TaskStatus.IN_PROGRESS

        # Route to appropriate handler
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        # Fallback to LLM-based handling
        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            "security_scan": self._handle_security_scan,
            "vulnerability_check": self._handle_vulnerability_check,
            "threat_analysis": self._handle_threat_analysis,
            "compliance_check": self._handle_compliance_check,
            "risk_assessment": self._handle_risk_assessment,
        }
        return handlers.get(task_type)

    async def _handle_security_scan(self, task: Task) -> TaskResult:
        """Perform a security scan."""
        target = task.context.get("target", "unknown")

        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider for security analysis",
            )

        prompt = f"""As a security analyst (Sentinel), perform a security scan analysis.

Target: {target}
Description: {task.description}
Context: {task.context}

Identify potential security issues, categorize them by severity,
and provide recommendations. Format as:

FINDINGS:
- [CRITICAL/HIGH/MEDIUM/LOW] Description of issue

RECOMMENDATIONS:
- Remediation steps"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Security scan failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "scan_type": "security_scan",
                "target": target,
                "analysis": response,
            },
            metrics={"task_type": "security_scan"},
        )

    async def _handle_vulnerability_check(self, task: Task) -> TaskResult:
        """Check for known vulnerabilities."""
        target = task.context.get("target", "unknown")

        prompt = f"""As a security analyst (Sentinel), check for vulnerabilities.

Target: {target}
Description: {task.description}

Analyze for common vulnerabilities including:
- OWASP Top 10
- Known CVEs
- Configuration weaknesses
- Dependency vulnerabilities

Format findings with severity and CVE references where applicable."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Vulnerability check failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "check_type": "vulnerability",
                "target": target,
                "findings": response,
            },
        )

    async def _handle_threat_analysis(self, task: Task) -> TaskResult:
        """Analyze potential threats."""
        prompt = f"""As a security analyst (Sentinel), perform threat analysis.

Description: {task.description}
Context: {task.context}

Analyze potential threats including:
- Threat actors and their motivations
- Attack vectors
- Potential impact
- Likelihood assessment

Provide a threat model summary."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Threat analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "threat",
                "threat_model": response,
            },
        )

    async def _handle_compliance_check(self, task: Task) -> TaskResult:
        """Check compliance against standards."""
        framework = task.context.get("framework", "general")

        prompt = f"""As a security analyst (Sentinel), check compliance.

Framework: {framework}
Description: {task.description}
Context: {task.context}

Evaluate compliance with relevant standards and provide:
- Compliance status for each control
- Gaps identified
- Remediation priorities"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Compliance check failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "check_type": "compliance",
                "framework": framework,
                "evaluation": response,
            },
        )

    async def _handle_risk_assessment(self, task: Task) -> TaskResult:
        """Perform risk assessment."""
        prompt = f"""As a security analyst (Sentinel), perform risk assessment.

Description: {task.description}
Context: {task.context}

Assess risks using standard methodology:
- Identify assets and their value
- Identify threats and vulnerabilities
- Calculate risk (likelihood x impact)
- Prioritize risks
- Recommend mitigations"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Risk assessment failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "assessment_type": "risk",
                "analysis": response,
            },
        )

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM when no specific handler exists."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider and no handler for task type",
            )

        prompt = f"""As the Sentinel (Sentinel) specializing in security,
handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough security-focused response."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"LLM handling failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )

    def report_incident(self, incident: Dict[str, Any]) -> str:
        """Record a security incident."""
        incident["reported_at"] = str(Task)
        incident["status"] = "open"
        self._active_incidents.append(incident)
        return f"Incident recorded: {len(self._active_incidents)} active incidents"

    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status."""
        return {
            "active_incidents": len(self._active_incidents),
            "compliance_status": self._compliance_status,
            "threat_intel_entries": len(self._threat_intel),
            "capabilities": self.capabilities,
        }
