"""
Aegis (Aegis) Agent - Aegis.

Codename: Aegis
Core function: Enterprise risk management and threat mitigation.

The Aegis handles all risk-related tasks:
- Enterprise risk assessment and quantification
- Risk mitigation planning and tracking
- Threat modeling (STRIDE, etc.)
- Business continuity planning
- Risk appetite management
- Incident response coordination

Sphere of influence: Enterprise risk management, threat modeling,
business continuity, insurance strategy, risk quantification.
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
from ag3ntwerk.agents.aegis.managers import (
    RiskAssessmentManager,
    ThreatModelingManager,
    BCPManager,
    IncidentManager,
)
from ag3ntwerk.agents.aegis.specialists import (
    RiskAnalyst,
    ThreatAnalyst,
    ControlsAnalyst,
    BCPSpecialist,
    IncidentAnalyst,
)
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


# Risk management task types
RISK_MANAGEMENT_CAPABILITIES = [
    # Risk assessment
    "risk_assessment",
    "risk_identification",
    "risk_quantification",
    "risk_scoring",
    "risk_register",
    "risk_review",
    # Risk mitigation
    "mitigation_planning",
    "control_assessment",
    "control_design",
    "risk_treatment",
    # Threat modeling
    "threat_modeling",
    "threat_analysis",
    "attack_surface_analysis",
    "vulnerability_assessment",
    # Business continuity
    "bcp_planning",
    "disaster_recovery",
    "impact_analysis",
    "recovery_planning",
    # Governance
    "risk_appetite",
    "risk_reporting",
    "risk_monitoring",
    # Incident management
    "incident_analysis",
    "root_cause_analysis",
    "lessons_learned",
]


class Aegis(Manager):
    """
    Aegis - Aegis.

    The Aegis is responsible for enterprise risk management, threat
    modeling, and business continuity planning within the ag3ntwerk system.

    Codename: Aegis

    Core Responsibilities:
    - Enterprise risk identification and assessment
    - Risk quantification and scoring
    - Mitigation planning and tracking
    - Threat modeling (STRIDE methodology)
    - Business continuity planning
    - Risk appetite management
    - Incident analysis and lessons learned

    Example:
        ```python
        crio = Aegis(llm_provider=llm)

        task = Task(
            description="Assess risks for new API deployment",
            task_type="risk_assessment",
            context={"system": "payment-api", "deployment": "v2.0"},
        )
        result = await crio.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__(
            code="Aegis",
            name="Aegis",
            domain="Risk Management, Threat Modeling, Business Continuity",
            llm_provider=llm_provider,
        )
        self.codename = "Aegis"

        self.capabilities = RISK_MANAGEMENT_CAPABILITIES

        # Risk management state
        self._risks: Dict[str, Risk] = {}
        self._controls: Dict[str, Control] = {}
        self._threat_models: Dict[str, ThreatModel] = {}
        self._bcp_plans: Dict[str, BusinessContinuityPlan] = {}
        self._incidents: Dict[str, RiskIncident] = {}
        self._risk_appetite: Optional[RiskAppetite] = None

        # Initialize and register managers with their specialists
        self._init_managers()

    def _init_managers(self) -> None:
        """Initialize and register managers with their specialists."""
        # Create managers
        ram = RiskAssessmentManager(llm_provider=self.llm_provider)
        tmm = ThreatModelingManager(llm_provider=self.llm_provider)
        bcpm = BCPManager(llm_provider=self.llm_provider)
        im = IncidentManager(llm_provider=self.llm_provider)

        # Create specialists
        risk_analyst = RiskAnalyst(llm_provider=self.llm_provider)
        threat_analyst = ThreatAnalyst(llm_provider=self.llm_provider)
        controls_analyst = ControlsAnalyst(llm_provider=self.llm_provider)
        bcp_specialist = BCPSpecialist(llm_provider=self.llm_provider)
        incident_analyst = IncidentAnalyst(llm_provider=self.llm_provider)

        # Register specialists with appropriate managers
        ram.register_subordinate(risk_analyst)
        ram.register_subordinate(controls_analyst)
        tmm.register_subordinate(threat_analyst)
        bcpm.register_subordinate(bcp_specialist)
        im.register_subordinate(incident_analyst)

        # Register managers with Aegis
        self.register_subordinate(ram)
        self.register_subordinate(tmm)
        self.register_subordinate(bcpm)
        self.register_subordinate(im)

    def can_handle(self, task: Task) -> bool:
        """Check if this is a risk management task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute a risk management task."""
        task.status = TaskStatus.IN_PROGRESS

        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            # Risk assessment handlers
            "risk_assessment": self._handle_risk_assessment,
            "risk_identification": self._handle_risk_identification,
            "risk_quantification": self._handle_risk_quantification,
            "risk_scoring": self._handle_risk_scoring,
            "risk_register": self._handle_risk_register,
            # Mitigation handlers
            "mitigation_planning": self._handle_mitigation_planning,
            "control_assessment": self._handle_control_assessment,
            "control_design": self._handle_control_design,
            # Threat modeling handlers
            "threat_modeling": self._handle_threat_modeling,
            "threat_analysis": self._handle_threat_analysis,
            "attack_surface_analysis": self._handle_attack_surface,
            # Business continuity handlers
            "bcp_planning": self._handle_bcp_planning,
            "disaster_recovery": self._handle_disaster_recovery,
            "impact_analysis": self._handle_impact_analysis,
            # Governance handlers
            "risk_appetite": self._handle_risk_appetite,
            "risk_reporting": self._handle_risk_reporting,
            # Incident handlers
            "incident_analysis": self._handle_incident_analysis,
            "root_cause_analysis": self._handle_root_cause_analysis,
            "lessons_learned": self._handle_lessons_learned,
            # VLS handlers
            "vls_monitoring_stoploss": self._handle_vls_monitoring_stoploss,
        }
        return handlers.get(task_type)

    # =========================================================================
    # Risk Assessment Handlers
    # =========================================================================

    async def _handle_risk_assessment(self, task: Task) -> TaskResult:
        """Perform comprehensive risk assessment."""
        scope = task.context.get("scope", "")
        system = task.context.get("system", "")

        prompt = f"""As the Aegis (Aegis), perform a risk assessment.

Scope: {scope}
System: {system}
Description: {task.description}
Context: {task.context}

Conduct a comprehensive risk assessment including:
1. Risk identification - potential risks and threats
2. Risk analysis - likelihood and impact assessment
3. Risk evaluation - prioritization and comparison to risk appetite
4. Risk treatment recommendations
5. Residual risk after proposed treatments
6. Key risk indicators (KRIs) to monitor

Use standard risk assessment methodology and provide actionable insights."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "assessment_type": "comprehensive",
                "scope": scope,
                "system": system,
                "assessment": response,
            },
            metrics={"task_type": "risk_assessment"},
        )

    async def _handle_risk_identification(self, task: Task) -> TaskResult:
        """Identify risks in a given context."""
        scope = task.context.get("scope", "")
        categories = task.context.get("categories", list(RiskCategory))

        prompt = f"""As the Aegis (Aegis), identify risks.

Scope: {scope}
Categories to Consider: {[c.value if isinstance(c, RiskCategory) else c for c in categories]}
Description: {task.description}
Context: {task.context}

Identify potential risks across the following dimensions:
1. Strategic risks - market, competitive, regulatory changes
2. Operational risks - process, people, systems failures
3. Financial risks - credit, liquidity, market exposure
4. Technology risks - cyber, infrastructure, data breaches
5. Compliance risks - legal, regulatory violations
6. Third-party risks - vendor, supply chain issues

For each risk identified, provide:
- Risk name and description
- Category
- Potential impact
- Preliminary likelihood assessment"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "identification_type": "comprehensive",
                "scope": scope,
                "risks": response,
            },
        )

    async def _handle_risk_quantification(self, task: Task) -> TaskResult:
        """Quantify risk in financial or measurable terms."""
        risk_id = task.context.get("risk_id", "")
        risk_name = task.context.get("risk_name", task.description)

        prompt = f"""As the Aegis (Aegis), quantify this risk.

Risk: {risk_name}
Description: {task.description}
Context: {task.context}

Provide quantitative risk analysis including:
1. Value at Risk (VaR) estimate
2. Expected loss calculation
3. Worst-case scenario impact
4. Probability distribution
5. Confidence intervals
6. Financial exposure range
7. Key assumptions and limitations

Express results in measurable terms with clear methodology."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "quantification_type": "financial",
                "risk": risk_name,
                "analysis": response,
            },
        )

    async def _handle_risk_scoring(self, task: Task) -> TaskResult:
        """Score and prioritize risks."""
        risks = task.context.get("risks", [])

        prompt = f"""As the Aegis (Aegis), score these risks.

Risks: {risks if risks else task.description}
Context: {task.context}

Score each risk using a 5x5 matrix:

Likelihood (1-5):
1 = Rare (<10%), 2 = Unlikely (10-30%), 3 = Possible (30-60%)
4 = Likely (60-90%), 5 = Almost Certain (>90%)

Impact (1-5):
1 = Minimal, 2 = Low, 3 = Medium, 4 = High, 5 = Critical

For each risk provide:
- Likelihood score with justification
- Impact score with justification
- Combined risk score (L x I)
- Risk level (Critical/High/Medium/Low)
- Priority ranking"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "scoring_method": "5x5_matrix",
                "scored_risks": response,
            },
        )

    async def _handle_risk_register(self, task: Task) -> TaskResult:
        """Generate or update risk register."""
        action = task.context.get("action", "generate")

        # Include current risks in context
        current_risks = [r.to_dict() for r in self._risks.values()]

        prompt = f"""As the Aegis (Aegis), manage the risk register.

Action: {action}
Current Registered Risks: {len(current_risks)} risks
Description: {task.description}
Context: {task.context}

For the risk register, provide:
1. Risk ID and name
2. Description
3. Category
4. Owner
5. Inherent risk score
6. Current controls
7. Residual risk score
8. Treatment plan
9. Status
10. Review date"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "register_action": action,
                "total_risks": len(self._risks),
                "register": response,
            },
        )

    # =========================================================================
    # Mitigation Handlers
    # =========================================================================

    async def _handle_mitigation_planning(self, task: Task) -> TaskResult:
        """Plan risk mitigation strategies."""
        risk_id = task.context.get("risk_id", "")
        risk_name = task.context.get("risk_name", task.description)

        prompt = f"""As the Aegis (Aegis), develop mitigation plan.

Risk: {risk_name}
Description: {task.description}
Context: {task.context}

Develop a comprehensive mitigation plan including:
1. Mitigation strategy selection (Avoid/Mitigate/Transfer/Accept)
2. Specific control recommendations
3. Implementation timeline
4. Resource requirements
5. Cost-benefit analysis
6. Expected risk reduction
7. Key milestones and deliverables
8. Success metrics"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "plan_type": "mitigation",
                "risk": risk_name,
                "plan": response,
            },
        )

    async def _handle_control_assessment(self, task: Task) -> TaskResult:
        """Assess effectiveness of controls."""
        controls = task.context.get("controls", [])

        prompt = f"""As the Aegis (Aegis), assess control effectiveness.

Controls: {controls if controls else 'Current control framework'}
Description: {task.description}
Context: {task.context}

Assess each control on:
1. Design effectiveness - Is the control properly designed?
2. Operating effectiveness - Is the control working as intended?
3. Coverage - What risks does it address?
4. Gaps - What risks remain uncontrolled?
5. Redundancy - Are there overlapping controls?
6. Cost efficiency - Is the control cost-effective?
7. Recommendations for improvement"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "assessment_type": "control_effectiveness",
                "assessment": response,
            },
        )

    async def _handle_control_design(self, task: Task) -> TaskResult:
        """Design new controls for risk mitigation."""
        risk_name = task.context.get("risk", task.description)

        prompt = f"""As the Aegis (Aegis), design controls.

Risk: {risk_name}
Description: {task.description}
Context: {task.context}

Design controls including:
1. Control name and objective
2. Control type (Preventive/Detective/Corrective)
3. Control description and procedures
4. Implementation requirements
5. Testing approach
6. Monitoring requirements
7. Expected effectiveness
8. Cost and resource needs"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "design_type": "control",
                "risk": risk_name,
                "controls": response,
            },
        )

    # =========================================================================
    # Threat Modeling Handlers
    # =========================================================================

    async def _handle_threat_modeling(self, task: Task) -> TaskResult:
        """Perform threat modeling using STRIDE methodology."""
        system = task.context.get("system", "")
        methodology = task.context.get("methodology", "STRIDE")

        prompt = f"""As the Aegis (Aegis), perform threat modeling.

System: {system}
Methodology: {methodology}
Description: {task.description}
Context: {task.context}

Using {methodology} methodology, analyze threats:

STRIDE Categories:
- Spoofing: Identity spoofing attacks
- Tampering: Data or code tampering
- Repudiation: Denying actions performed
- Information Disclosure: Data breaches
- Denial of Service: Availability attacks
- Elevation of Privilege: Unauthorized access

For each threat:
1. Threat description
2. Attack vector
3. Affected component
4. Severity rating
5. Mitigation recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "model_type": "threat",
                "methodology": methodology,
                "system": system,
                "threats": response,
            },
        )

    async def _handle_threat_analysis(self, task: Task) -> TaskResult:
        """Analyze specific threats in detail."""
        threat = task.context.get("threat", task.description)

        prompt = f"""As the Aegis (Aegis), analyze this threat.

Threat: {threat}
Description: {task.description}
Context: {task.context}

Provide detailed threat analysis:
1. Threat actor profile
2. Motivation and capability
3. Attack techniques (MITRE ATT&CK mapping)
4. Kill chain analysis
5. Indicators of compromise
6. Detection strategies
7. Response procedures
8. Prevention measures"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "threat",
                "threat": threat,
                "analysis": response,
            },
        )

    async def _handle_attack_surface(self, task: Task) -> TaskResult:
        """Analyze attack surface."""
        system = task.context.get("system", "")

        prompt = f"""As the Aegis (Aegis), analyze attack surface.

System: {system}
Description: {task.description}
Context: {task.context}

Analyze the attack surface including:
1. Entry points (APIs, interfaces, ports)
2. Data flows and trust boundaries
3. Authentication mechanisms
4. External dependencies
5. Network exposure
6. Vulnerable components
7. Reduction recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "attack_surface",
                "system": system,
                "analysis": response,
            },
        )

    # =========================================================================
    # Business Continuity Handlers
    # =========================================================================

    async def _handle_bcp_planning(self, task: Task) -> TaskResult:
        """Develop business continuity plan."""
        scope = task.context.get("scope", "")

        prompt = f"""As the Aegis (Aegis), develop BCP.

Scope: {scope}
Description: {task.description}
Context: {task.context}

Develop a Business Continuity Plan including:
1. Scope and objectives
2. Critical business functions
3. Recovery Time Objective (RTO)
4. Recovery Point Objective (RPO)
5. Recovery procedures
6. Communication plan
7. Resource requirements
8. Testing schedule
9. Maintenance procedures"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "plan_type": "bcp",
                "scope": scope,
                "plan": response,
            },
        )

    async def _handle_disaster_recovery(self, task: Task) -> TaskResult:
        """Develop disaster recovery plan."""
        system = task.context.get("system", "")

        prompt = f"""As the Aegis (Aegis), develop DR plan.

System: {system}
Description: {task.description}
Context: {task.context}

Develop a Disaster Recovery Plan including:
1. DR objectives and scope
2. Recovery site strategy
3. Data backup procedures
4. System recovery procedures
5. Network recovery
6. Testing procedures
7. Activation criteria
8. Roles and responsibilities"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "plan_type": "disaster_recovery",
                "system": system,
                "plan": response,
            },
        )

    async def _handle_impact_analysis(self, task: Task) -> TaskResult:
        """Perform business impact analysis."""
        function = task.context.get("function", "")

        prompt = f"""As the Aegis (Aegis), perform impact analysis.

Business Function: {function}
Description: {task.description}
Context: {task.context}

Perform Business Impact Analysis (BIA) including:
1. Function criticality rating
2. Dependencies (systems, data, people)
3. Revenue impact per hour/day
4. Regulatory impact
5. Reputational impact
6. Maximum Tolerable Downtime
7. Minimum recovery requirements
8. Priority ranking"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "business_impact",
                "function": function,
                "analysis": response,
            },
        )

    # =========================================================================
    # Governance Handlers
    # =========================================================================

    async def _handle_risk_appetite(self, task: Task) -> TaskResult:
        """Define or assess risk appetite."""
        action = task.context.get("action", "define")

        prompt = f"""As the Aegis (Aegis), manage risk appetite.

Action: {action}
Description: {task.description}
Context: {task.context}

For risk appetite, provide:
1. Risk appetite statement
2. Tolerance levels by category
3. Key risk limits
4. Escalation thresholds
5. Zero-tolerance areas
6. Monitoring approach
7. Reporting requirements"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "appetite_action": action,
                "risk_appetite": response,
            },
        )

    async def _handle_risk_reporting(self, task: Task) -> TaskResult:
        """Generate risk reports."""
        report_type = task.context.get("report_type", "summary")

        # Gather current risk data
        risk_summary = {
            "total_risks": len(self._risks),
            "by_category": {},
            "by_status": {},
        }

        for risk in self._risks.values():
            cat = risk.category.value
            risk_summary["by_category"][cat] = risk_summary["by_category"].get(cat, 0) + 1
            stat = risk.status.value
            risk_summary["by_status"][stat] = risk_summary["by_status"].get(stat, 0) + 1

        prompt = f"""As the Aegis (Aegis), generate risk report.

Report Type: {report_type}
Current Risk Summary: {risk_summary}
Description: {task.description}
Context: {task.context}

Generate a risk report including:
1. Agent summary
2. Risk profile overview
3. Key risk indicators
4. Top risks by severity
5. Emerging risks
6. Mitigation progress
7. Recommendations
8. Next steps"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "report_type": report_type,
                "summary": risk_summary,
                "report": response,
            },
        )

    # =========================================================================
    # Incident Handlers
    # =========================================================================

    async def _handle_incident_analysis(self, task: Task) -> TaskResult:
        """Analyze a risk incident."""
        incident = task.context.get("incident", task.description)

        prompt = f"""As the Aegis (Aegis), analyze incident.

Incident: {incident}
Description: {task.description}
Context: {task.context}

Analyze the incident including:
1. Incident timeline
2. Impact assessment
3. Contributing factors
4. Control failures
5. Response effectiveness
6. Immediate actions taken
7. Long-term remediation
8. Prevention recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "incident",
                "incident": incident,
                "analysis": response,
            },
        )

    async def _handle_root_cause_analysis(self, task: Task) -> TaskResult:
        """Perform root cause analysis."""
        incident = task.context.get("incident", task.description)

        prompt = f"""As the Aegis (Aegis), perform RCA.

Incident: {incident}
Description: {task.description}
Context: {task.context}

Perform Root Cause Analysis using multiple techniques:
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
            output={
                "analysis_type": "root_cause",
                "incident": incident,
                "analysis": response,
            },
        )

    async def _handle_lessons_learned(self, task: Task) -> TaskResult:
        """Document lessons learned from incidents."""
        incident = task.context.get("incident", task.description)

        prompt = f"""As the Aegis (Aegis), document lessons learned.

Incident: {incident}
Description: {task.description}
Context: {task.context}

Document lessons learned including:
1. What happened (factual summary)
2. What went well
3. What didn't go well
4. Key learnings
5. Process improvements
6. Control enhancements
7. Training needs
8. Action items and owners"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "doc_type": "lessons_learned",
                "incident": incident,
                "lessons": response,
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

        prompt = f"""As the Aegis (Aegis) specializing in enterprise
risk management, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough risk-focused response."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )

    # =========================================================================
    # Risk Management Methods
    # =========================================================================

    def register_risk(self, risk: Risk) -> str:
        """Register a risk in the risk register."""
        self._risks[risk.id] = risk
        return risk.id

    def register_control(self, control: Control) -> str:
        """Register a control."""
        self._controls[control.id] = control
        return control.id

    def register_threat_model(self, model: ThreatModel) -> str:
        """Register a threat model."""
        self._threat_models[model.id] = model
        return model.id

    def register_bcp(self, plan: BusinessContinuityPlan) -> str:
        """Register a business continuity plan."""
        self._bcp_plans[plan.id] = plan
        return plan.id

    def register_incident(self, incident: RiskIncident) -> str:
        """Register a risk incident."""
        self._incidents[incident.id] = incident
        return incident.id

    def set_risk_appetite(self, appetite: RiskAppetite) -> None:
        """Set the organization's risk appetite."""
        self._risk_appetite = appetite

    async def _handle_vls_monitoring_stoploss(self, task: Task) -> TaskResult:
        """Execute VLS Stage: Monitoring & Stop-Loss."""
        from ag3ntwerk.modules.vls.stages import execute_monitoring_stoploss

        try:
            result = await execute_monitoring_stoploss(task.context)

            return TaskResult(
                task_id=task.id,
                success=result.get("success", False),
                output=result,
                error=result.get("error"),
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"VLS Monitoring & Stop-Loss failed: {e}",
            )

    def get_risk(self, risk_id: str) -> Optional[Risk]:
        """Get a risk by ID."""
        return self._risks.get(risk_id)

    def get_risks_by_category(self, category: RiskCategory) -> List[Risk]:
        """Get all risks in a category."""
        return [r for r in self._risks.values() if r.category == category]

    def get_high_severity_risks(self) -> List[Risk]:
        """Get all high and critical severity risks."""
        results = []
        for risk in self._risks.values():
            if risk.inherent_score:
                level = risk.inherent_score.risk_level
                if level in (RiskSeverity.HIGH, RiskSeverity.CRITICAL):
                    results.append(risk)
        return results

    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk management status."""
        severity_counts: Dict[str, int] = {}
        for risk in self._risks.values():
            if risk.inherent_score:
                level = risk.inherent_score.risk_level.value
                severity_counts[level] = severity_counts.get(level, 0) + 1

        return {
            "total_risks": len(self._risks),
            "by_severity": severity_counts,
            "controls_registered": len(self._controls),
            "threat_models": len(self._threat_models),
            "bcp_plans": len(self._bcp_plans),
            "active_incidents": len([i for i in self._incidents.values() if i.status == "open"]),
            "risk_appetite_defined": self._risk_appetite is not None,
            "capabilities": self.capabilities,
        }
