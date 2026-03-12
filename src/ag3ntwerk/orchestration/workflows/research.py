"""
Research & Knowledge Workflows.

Workflows for research initiatives and knowledge base maintenance.
"""

from typing import Any, Dict, List

from ag3ntwerk.orchestration.base import Workflow, WorkflowStep


class ResearchInitiativeWorkflow(Workflow):
    """
    Workflow for research and development initiative.

    Coordinates across:
    - Axiom (Axiom): Research leadership
    - Forge (Forge): Technical feasibility
    - Index (Index): Data requirements
    - Keystone (Keystone): Investment analysis

    Steps:
    1. Research Proposal - Axiom defines research scope and hypothesis
    2. Feasibility Study - Axiom conducts feasibility analysis
    3. Technical Assessment - Forge evaluates technical requirements
    4. Data Requirements - Index identifies data needs
    5. Investment Analysis - Keystone analyzes ROI and funding
    6. Research Plan - Axiom creates detailed research plan
    """

    @property
    def name(self) -> str:
        return "research_initiative"

    @property
    def description(self) -> str:
        return "Research and development initiative planning"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="research_proposal",
                agent="Axiom",
                task_type="hypothesis_testing",
                description="Define research scope and hypothesis",
                context_builder=lambda ctx: {
                    "research_topic": ctx.get("research_topic"),
                    "hypothesis": ctx.get("hypothesis"),
                    "objectives": ctx.get("objectives", []),
                    "expected_outcomes": ctx.get("expected_outcomes", []),
                },
            ),
            WorkflowStep(
                name="feasibility_study",
                agent="Axiom",
                task_type="feasibility_study",
                description="Conduct feasibility analysis",
                depends_on=["research_proposal"],
                context_builder=lambda ctx: {
                    "proposal": ctx.step_results.get("research_proposal"),
                    "constraints": ctx.get("constraints", []),
                    "resources_available": ctx.get("resources_available", {}),
                },
            ),
            WorkflowStep(
                name="technical_assessment",
                agent="Forge",
                task_type="architecture",
                description="Evaluate technical requirements and approach",
                depends_on=["research_proposal"],
                context_builder=lambda ctx: {
                    "proposal": ctx.step_results.get("research_proposal"),
                    "technology_stack": ctx.get("technology_stack", []),
                    "infrastructure_needs": ctx.get("infrastructure_needs", []),
                },
            ),
            WorkflowStep(
                name="data_requirements",
                agent="Index",
                task_type="data_catalog",
                description="Identify data requirements and sources",
                depends_on=["research_proposal", "feasibility_study"],
                context_builder=lambda ctx: {
                    "proposal": ctx.step_results.get("research_proposal"),
                    "feasibility": ctx.step_results.get("feasibility_study"),
                    "available_data": ctx.get("available_data", []),
                },
            ),
            WorkflowStep(
                name="investment_analysis",
                agent="Keystone",
                task_type="roi_calculation",
                description="Analyze investment and expected ROI",
                depends_on=["feasibility_study", "technical_assessment", "data_requirements"],
                context_builder=lambda ctx: {
                    "feasibility": ctx.step_results.get("feasibility_study"),
                    "technical_needs": ctx.step_results.get("technical_assessment"),
                    "data_needs": ctx.step_results.get("data_requirements"),
                    "budget_constraint": ctx.get("budget_constraint"),
                    "timeline": ctx.get("timeline"),
                },
            ),
            WorkflowStep(
                name="research_plan",
                agent="Axiom",
                task_type="experiment_design",
                description="Create detailed research plan",
                depends_on=[
                    "research_proposal",
                    "feasibility_study",
                    "technical_assessment",
                    "data_requirements",
                    "investment_analysis",
                ],
                context_builder=lambda ctx: {
                    "all_inputs": {
                        "proposal": ctx.step_results.get("research_proposal"),
                        "feasibility": ctx.step_results.get("feasibility_study"),
                        "technical": ctx.step_results.get("technical_assessment"),
                        "data": ctx.step_results.get("data_requirements"),
                        "investment": ctx.step_results.get("investment_analysis"),
                    },
                    "timeline": ctx.get("timeline"),
                    "milestones": ctx.get("milestones", []),
                },
            ),
        ]


class KnowledgeMaintenanceWorkflow(Workflow):
    """
    CKO internal workflow for knowledge base maintenance.

    Steps:
    1. Content Audit - Audit knowledge base content
    2. Freshness Check - Check content freshness
    3. Usage Analysis - Analyze content usage
    4. Gap Identification - Identify knowledge gaps
    5. Maintenance Plan - Create maintenance plan
    """

    @property
    def name(self) -> str:
        return "knowledge_maintenance"

    @property
    def description(self) -> str:
        return "CKO knowledge base maintenance workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="content_audit",
                agent="CKO",
                task_type="knowledge_audit",
                description="Audit knowledge base content",
                context_builder=lambda ctx: {
                    "knowledge_bases": ctx.get("knowledge_bases", []),
                    "audit_criteria": ctx.get(
                        "audit_criteria", ["accuracy", "completeness", "relevance"]
                    ),
                    "content_types": ctx.get("content_types", []),
                },
            ),
            WorkflowStep(
                name="freshness_check",
                agent="CKO",
                task_type="documentation",
                description="Check content freshness and staleness",
                depends_on=["content_audit"],
                context_builder=lambda ctx: {
                    "audit_results": ctx.step_results.get("content_audit"),
                    "freshness_threshold": ctx.get("freshness_threshold", "90_days"),
                    "critical_content": ctx.get("critical_content", []),
                },
            ),
            WorkflowStep(
                name="usage_analysis",
                agent="CKO",
                task_type="expertise_location",
                description="Analyze content usage patterns",
                depends_on=["content_audit"],
                context_builder=lambda ctx: {
                    "audit_results": ctx.step_results.get("content_audit"),
                    "usage_metrics": ctx.get("usage_metrics", ["views", "searches", "feedback"]),
                    "analysis_period": ctx.get("analysis_period", "last_quarter"),
                },
            ),
            WorkflowStep(
                name="gap_identification",
                agent="CKO",
                task_type="knowledge_audit",
                description="Identify knowledge gaps",
                depends_on=["usage_analysis"],
                context_builder=lambda ctx: {
                    "usage_data": ctx.step_results.get("usage_analysis"),
                    "search_queries": ctx.get("search_queries", []),
                    "feedback_themes": ctx.get("feedback_themes", []),
                },
            ),
            WorkflowStep(
                name="maintenance_plan",
                agent="CKO",
                task_type="documentation",
                description="Create knowledge maintenance plan",
                depends_on=["freshness_check", "gap_identification"],
                context_builder=lambda ctx: {
                    "stale_content": ctx.step_results.get("freshness_check"),
                    "gaps": ctx.step_results.get("gap_identification"),
                    "resources_available": ctx.get("resources_available", {}),
                    "priority_areas": ctx.get("priority_areas", []),
                },
            ),
        ]
