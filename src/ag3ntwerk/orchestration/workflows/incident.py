"""
Incident Response Workflow.

Workflow for responding to production incidents.
"""

from typing import Any, Dict, List

from ag3ntwerk.orchestration.base import Workflow, WorkflowStep


class IncidentResponseWorkflow(Workflow):
    """
    Workflow for responding to production incidents.

    Coordinates across:
    - Foundry (Foundry): Technical investigation and fix
    - Citadel (Citadel): Security impact assessment
    - Beacon (Beacon): Customer communication

    Steps:
    1. Initial Assessment - Foundry assesses incident scope
    2. Security Check - Citadel checks for security implications
    3. Customer Impact - Beacon assesses customer impact
    4. Remediation Plan - Foundry creates fix plan
    5. Customer Communication - Beacon handles customer updates
    6. Post-Incident Review - Foundry leads retrospective
    """

    @property
    def name(self) -> str:
        return "incident_response"

    @property
    def description(self) -> str:
        return "Coordinated incident response across technical and customer-facing teams"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="initial_assessment",
                agent="Foundry",
                task_type="incident_assessment",
                description="Assess incident scope and severity",
                context_builder=lambda ctx: {
                    "incident_id": ctx.get("incident_id"),
                    "incident_type": ctx.get("incident_type"),
                    "description": ctx.get("description"),
                    "severity": ctx.get("severity", "medium"),
                    "affected_systems": ctx.get("affected_systems", []),
                },
            ),
            WorkflowStep(
                name="security_check",
                agent="Citadel",
                task_type="incident_response",
                description="Check for security implications",
                depends_on=["initial_assessment"],
                context_builder=lambda ctx: {
                    "incident_id": ctx.get("incident_id"),
                    "incident_type": ctx.get("incident_type"),
                    "initial_assessment": ctx.step_results.get("initial_assessment"),
                    "affected_systems": ctx.get("affected_systems", []),
                },
            ),
            WorkflowStep(
                name="customer_impact",
                agent="Beacon",
                task_type="health_scoring",
                description="Assess customer impact and at-risk accounts",
                depends_on=["initial_assessment"],
                context_builder=lambda ctx: {
                    "incident_id": ctx.get("incident_id"),
                    "initial_assessment": ctx.step_results.get("initial_assessment"),
                    "affected_customers": ctx.get("affected_customers", []),
                },
            ),
            WorkflowStep(
                name="remediation_plan",
                agent="Foundry",
                task_type="remediation_planning",
                description="Create remediation and fix plan",
                depends_on=["initial_assessment", "security_check"],
                context_builder=lambda ctx: {
                    "incident_id": ctx.get("incident_id"),
                    "initial_assessment": ctx.step_results.get("initial_assessment"),
                    "security_findings": ctx.step_results.get("security_check"),
                },
            ),
            WorkflowStep(
                name="customer_communication",
                agent="Beacon",
                task_type="support_escalation",
                description="Handle customer communication and updates",
                depends_on=["customer_impact", "remediation_plan"],
                context_builder=lambda ctx: {
                    "incident_id": ctx.get("incident_id"),
                    "customer_impact": ctx.step_results.get("customer_impact"),
                    "remediation_plan": ctx.step_results.get("remediation_plan"),
                    "communication_type": "incident_update",
                },
            ),
            WorkflowStep(
                name="post_incident_review",
                agent="Foundry",
                task_type="post_incident_review",
                description="Conduct post-incident retrospective",
                depends_on=["remediation_plan", "customer_communication"],
                required=False,  # Can be done async
                context_builder=lambda ctx: {
                    "incident_id": ctx.get("incident_id"),
                    "timeline": {
                        "initial_assessment": ctx.step_results.get("initial_assessment"),
                        "security_check": ctx.step_results.get("security_check"),
                        "remediation": ctx.step_results.get("remediation_plan"),
                    },
                },
            ),
        ]
