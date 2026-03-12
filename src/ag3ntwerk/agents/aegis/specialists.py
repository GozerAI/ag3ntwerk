"""
Specialists for the Aegis (Aegis) agent.

Specialists are the workers that perform specific operational tasks
within risk management.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Specialist,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider


class RiskAnalyst(Specialist):
    """
    Specialist responsible for risk analysis.

    Handles risk identification, quantification, scoring,
    and treatment recommendations.

    Capabilities:
    - Risk identification
    - Risk quantification
    - Risk scoring
    - Risk appetite assessment
    - Treatment recommendations
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="RA",
            name="Risk Analyst",
            domain="Risk Analysis, Quantification, Scoring",
            capabilities=[
                "risk_assessment",
                "risk_identification",
                "risk_quantification",
                "risk_scoring",
                "risk_register",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute risk analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "risk_assessment": self._handle_assessment,
            "risk_identification": self._handle_identification,
            "risk_quantification": self._handle_quantification,
            "risk_scoring": self._handle_scoring,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_assessment(self, task: Task) -> TaskResult:
        """Handle risk assessment task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Risk Analyst, perform risk assessment:

Description: {task.description}
Context: {task.context}

Conduct assessment including:
1. Risk identification - potential risks and threats
2. Likelihood assessment (1-5 scale with justification)
3. Impact assessment (1-5 scale with justification)
4. Risk score calculation (L x I)
5. Risk level determination
6. Treatment recommendations
7. Key risk indicators"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"risk_assessment": response, "specialist": self.code},
        )

    async def _handle_identification(self, task: Task) -> TaskResult:
        """Handle risk identification task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Risk Analyst, identify risks:

Description: {task.description}
Context: {task.context}

Identify risks across categories:
1. Strategic risks
2. Operational risks
3. Financial risks
4. Technology risks
5. Compliance risks
6. Reputational risks

For each risk provide:
- Risk name and description
- Category
- Potential impact
- Preliminary likelihood"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"identified_risks": response, "specialist": self.code},
        )

    async def _handle_quantification(self, task: Task) -> TaskResult:
        """Handle risk quantification task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Risk Analyst, quantify this risk:

Description: {task.description}
Context: {task.context}

Provide quantitative analysis:
1. Value at Risk (VaR) estimate
2. Expected loss calculation
3. Worst-case scenario
4. Probability distribution
5. Financial exposure range
6. Confidence intervals
7. Key assumptions"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"quantification": response, "specialist": self.code},
        )

    async def _handle_scoring(self, task: Task) -> TaskResult:
        """Handle risk scoring task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Risk Analyst, score these risks:

Description: {task.description}
Context: {task.context}

Score using 5x5 matrix:
- Likelihood (1-5): Rare/Unlikely/Possible/Likely/Almost Certain
- Impact (1-5): Minimal/Low/Medium/High/Critical

For each risk provide:
- Likelihood score with justification
- Impact score with justification
- Combined risk score
- Risk level (Critical/High/Medium/Low)
- Priority ranking"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"risk_scores": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic risk task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Risk Analyst, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide risk analysis and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class ThreatAnalyst(Specialist):
    """
    Specialist responsible for threat analysis.

    Handles threat modeling, attack analysis, and
    security threat assessment.

    Capabilities:
    - Threat modeling (STRIDE)
    - Attack surface analysis
    - Threat intelligence
    - Vulnerability assessment
    - Mitigation recommendations
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="TA",
            name="Threat Analyst",
            domain="Threat Analysis, Modeling, Intelligence",
            capabilities=[
                "threat_modeling",
                "threat_analysis",
                "attack_surface_analysis",
                "vulnerability_assessment",
                "threat_intelligence",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute threat analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "threat_modeling": self._handle_modeling,
            "threat_analysis": self._handle_analysis,
            "attack_surface_analysis": self._handle_attack_surface,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_modeling(self, task: Task) -> TaskResult:
        """Handle threat modeling task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        methodology = task.context.get("methodology", "STRIDE")

        prompt = f"""As a Threat Analyst, perform threat modeling:

Methodology: {methodology}
Description: {task.description}
Context: {task.context}

Using {methodology}, analyze:
- Spoofing: Identity spoofing attacks
- Tampering: Data/code tampering
- Repudiation: Denying actions
- Information Disclosure: Data breaches
- Denial of Service: Availability attacks
- Elevation of Privilege: Unauthorized access

For each threat:
1. Threat description
2. Attack vector
3. Affected components
4. Severity rating
5. Mitigation strategies"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "threat_model": response,
                "methodology": methodology,
                "specialist": self.code,
            },
        )

    async def _handle_analysis(self, task: Task) -> TaskResult:
        """Handle threat analysis task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Threat Analyst, analyze this threat:

Description: {task.description}
Context: {task.context}

Provide analysis including:
1. Threat actor profile
2. Motivation and capability
3. Attack techniques (MITRE ATT&CK)
4. Kill chain analysis
5. Indicators of compromise
6. Detection strategies
7. Response procedures"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"threat_analysis": response, "specialist": self.code},
        )

    async def _handle_attack_surface(self, task: Task) -> TaskResult:
        """Handle attack surface analysis task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Threat Analyst, analyze attack surface:

Description: {task.description}
Context: {task.context}

Analyze:
1. Entry points (APIs, interfaces, ports)
2. Data flows and trust boundaries
3. Authentication mechanisms
4. External dependencies
5. Network exposure
6. Vulnerable components
7. Attack surface reduction recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"attack_surface": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic threat task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Threat Analyst, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide threat analysis and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class ControlsAnalyst(Specialist):
    """
    Specialist responsible for controls analysis.

    Handles control design, assessment, and
    mitigation planning.

    Capabilities:
    - Control design
    - Control assessment
    - Control testing
    - Mitigation planning
    - Gap remediation
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="CA",
            name="Controls Analyst",
            domain="Controls Design, Assessment, Testing",
            capabilities=[
                "control_assessment",
                "control_design",
                "mitigation_planning",
                "control_testing",
                "gap_remediation",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute controls analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "control_assessment": self._handle_assessment,
            "control_design": self._handle_design,
            "mitigation_planning": self._handle_mitigation,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_assessment(self, task: Task) -> TaskResult:
        """Handle control assessment task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Controls Analyst, assess controls:

Description: {task.description}
Context: {task.context}

Evaluate each control on:
1. Design effectiveness
2. Operating effectiveness
3. Risk coverage
4. Residual gaps
5. Redundancy analysis
6. Cost efficiency
7. Improvement recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"control_assessment": response, "specialist": self.code},
        )

    async def _handle_design(self, task: Task) -> TaskResult:
        """Handle control design task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Controls Analyst, design controls:

Description: {task.description}
Context: {task.context}

Design controls including:
1. Control name and objective
2. Control type (Preventive/Detective/Corrective)
3. Control description and procedures
4. Implementation requirements
5. Testing approach
6. Monitoring requirements
7. Expected effectiveness"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"control_design": response, "specialist": self.code},
        )

    async def _handle_mitigation(self, task: Task) -> TaskResult:
        """Handle mitigation planning task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Controls Analyst, develop mitigation plan:

Description: {task.description}
Context: {task.context}

Develop plan including:
1. Mitigation strategy (Avoid/Mitigate/Transfer/Accept)
2. Specific control recommendations
3. Implementation steps
4. Resource requirements
5. Timeline
6. Expected risk reduction
7. Success criteria"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"mitigation_plan": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic controls task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Controls Analyst, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide controls analysis and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class BCPSpecialist(Specialist):
    """
    Specialist responsible for business continuity planning.

    Handles BCP development, disaster recovery planning,
    impact analysis, and recovery procedures.

    Capabilities:
    - BCP planning
    - Disaster recovery planning
    - Business impact analysis
    - Recovery planning
    - Continuity testing
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="BCP",
            name="BCP Specialist",
            domain="Business Continuity, Disaster Recovery, Impact Analysis",
            capabilities=[
                "bcp_planning",
                "disaster_recovery",
                "impact_analysis",
                "recovery_planning",
                "continuity_testing",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute business continuity task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "bcp_planning": self._handle_bcp_planning,
            "disaster_recovery": self._handle_disaster_recovery,
            "impact_analysis": self._handle_impact_analysis,
            "recovery_planning": self._handle_recovery_planning,
            "continuity_testing": self._handle_testing,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_bcp_planning(self, task: Task) -> TaskResult:
        """Handle BCP planning task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        scope = task.context.get("scope", "enterprise")

        prompt = f"""As a BCP Specialist, develop business continuity plan:

Scope: {scope}
Description: {task.description}
Context: {task.context}

Develop BCP including:
1. Scope and objectives
2. Critical business functions
3. Recovery priorities
4. Recovery time objectives (RTO)
5. Recovery point objectives (RPO)
6. Resource requirements
7. Communication plan
8. Activation procedures
9. Testing schedule
10. Maintenance plan"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "bcp_plan": response,
                "scope": scope,
                "specialist": self.code,
            },
        )

    async def _handle_disaster_recovery(self, task: Task) -> TaskResult:
        """Handle disaster recovery planning task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        systems = task.context.get("systems", [])

        prompt = f"""As a BCP Specialist, develop disaster recovery plan:

Systems: {systems if systems else 'All critical systems'}
Description: {task.description}
Context: {task.context}

Develop DR plan including:
1. System inventory and dependencies
2. Recovery priorities and sequence
3. RTO/RPO for each system
4. Backup strategies
5. Alternative site requirements
6. Data recovery procedures
7. System restoration steps
8. Testing and validation
9. Roles and responsibilities
10. Escalation procedures"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "dr_plan": response,
                "systems": systems,
                "specialist": self.code,
            },
        )

    async def _handle_impact_analysis(self, task: Task) -> TaskResult:
        """Handle business impact analysis task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a BCP Specialist, perform business impact analysis:

Description: {task.description}
Context: {task.context}

Analyze including:
1. Critical business processes
2. Dependencies and interdependencies
3. Financial impact over time
4. Operational impact
5. Regulatory impact
6. Reputational impact
7. Maximum tolerable downtime
8. Recovery priority ranking
9. Resource requirements
10. Gap analysis"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "impact_analysis": response,
                "specialist": self.code,
            },
        )

    async def _handle_recovery_planning(self, task: Task) -> TaskResult:
        """Handle recovery planning task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        scenario = task.context.get("scenario", "general disruption")

        prompt = f"""As a BCP Specialist, develop recovery plan:

Scenario: {scenario}
Description: {task.description}
Context: {task.context}

Develop plan including:
1. Recovery objectives
2. Immediate response actions
3. Short-term recovery (0-24 hours)
4. Medium-term recovery (1-7 days)
5. Long-term recovery (1-4 weeks)
6. Resource allocation
7. Communication protocols
8. Return to normal operations
9. Post-incident review"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "recovery_plan": response,
                "scenario": scenario,
                "specialist": self.code,
            },
        )

    async def _handle_testing(self, task: Task) -> TaskResult:
        """Handle continuity testing task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        test_type = task.context.get("test_type", "tabletop")

        prompt = f"""As a BCP Specialist, design continuity test:

Test Type: {test_type}
Description: {task.description}
Context: {task.context}

Design test including:
1. Test objectives
2. Test scope and scenarios
3. Participants and roles
4. Test procedures
5. Success criteria
6. Data collection approach
7. Risk mitigation for test
8. Schedule and timeline
9. Post-test evaluation
10. Improvement recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "test_plan": response,
                "test_type": test_type,
                "specialist": self.code,
            },
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic BCP task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a BCP Specialist, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide business continuity guidance and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class IncidentAnalyst(Specialist):
    """
    Specialist responsible for incident analysis.

    Handles incident investigation, root cause analysis,
    and lessons learned documentation.

    Capabilities:
    - Incident analysis
    - Root cause analysis
    - Lessons learned
    - Corrective action planning
    - Trend analysis
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="IA",
            name="Incident Analyst",
            domain="Incident Analysis, RCA, Lessons Learned",
            capabilities=[
                "incident_analysis",
                "root_cause_analysis",
                "lessons_learned",
                "corrective_action",
                "incident_trending",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute incident analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "incident_analysis": self._handle_analysis,
            "root_cause_analysis": self._handle_rca,
            "lessons_learned": self._handle_lessons,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_analysis(self, task: Task) -> TaskResult:
        """Handle incident analysis task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Incident Analyst, analyze this incident:

Description: {task.description}
Context: {task.context}

Provide analysis including:
1. Incident timeline
2. Impact assessment
3. Contributing factors
4. Control failures
5. Response effectiveness
6. Immediate actions
7. Long-term remediation"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"incident_analysis": response, "specialist": self.code},
        )

    async def _handle_rca(self, task: Task) -> TaskResult:
        """Handle root cause analysis task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Incident Analyst, perform root cause analysis:

Description: {task.description}
Context: {task.context}

Perform RCA using multiple techniques:
1. 5 Whys analysis
2. Fishbone diagram factors
3. Contributing factors
4. Systemic issues
5. Process gaps
6. Human factors
7. Technology factors
8. Root cause determination
9. Corrective actions"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"root_cause_analysis": response, "specialist": self.code},
        )

    async def _handle_lessons(self, task: Task) -> TaskResult:
        """Handle lessons learned task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Incident Analyst, document lessons learned:

Description: {task.description}
Context: {task.context}

Document including:
1. What happened (factual summary)
2. What went well
3. What didn't go well
4. Key learnings
5. Process improvements
6. Control enhancements
7. Training needs
8. Action items with owners"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"lessons_learned": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic incident task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Incident Analyst, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide incident analysis and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )
