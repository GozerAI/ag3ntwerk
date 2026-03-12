"""
Manager Aggregation Workflows.

Workflows that aggregate outputs from multiple specialists, coordinated
by manager agents. These workflows represent the manager's role in
synthesizing specialist outputs into cohesive results.
"""

from typing import Any, Dict, List

from ag3ntwerk.orchestration.base import Workflow, WorkflowContext, WorkflowStep


# =============================================================================
# Keystone Aggregation Workflows
# =============================================================================


class ComprehensiveCostReviewWorkflow(Workflow):
    """
    Keystone manager-level workflow that aggregates cost analysis
    from multiple specialist perspectives.
    """

    @property
    def name(self) -> str:
        return "comprehensive_cost_review"

    @property
    def description(self) -> str:
        return "Comprehensive cost review aggregating multiple analyses"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="cost_accounting",
                agent="Keystone",
                task_type="cost_accounting",
                description="Perform detailed cost accounting",
                context_builder=lambda ctx: {
                    "period": ctx.get("period", "quarterly"),
                    "cost_data": ctx.get("cost_data", {}),
                },
            ),
            WorkflowStep(
                name="cash_flow",
                agent="Keystone",
                task_type="cash_flow_analysis",
                description="Analyze cash flow implications",
                depends_on=["cost_accounting"],
                context_builder=lambda ctx: {
                    "period": ctx.get("period", "quarterly"),
                    "cost_breakdown": ctx.step_results.get("cost_accounting"),
                },
            ),
            WorkflowStep(
                name="optimization",
                agent="Keystone",
                task_type="cost_optimization",
                description="Identify cost optimization opportunities",
                depends_on=["cost_accounting", "cash_flow"],
                context_builder=lambda ctx: {
                    "cost_accounting": ctx.step_results.get("cost_accounting"),
                    "cash_flow": ctx.step_results.get("cash_flow"),
                },
            ),
        ]


class BudgetPlanningCycleWorkflow(Workflow):
    """
    Keystone workflow for complete budget planning cycle using
    multiple specialist inputs.
    """

    @property
    def name(self) -> str:
        return "budget_planning_cycle"

    @property
    def description(self) -> str:
        return "Complete budget planning cycle with forecasting"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="budget_creation",
                agent="Keystone",
                task_type="budget_creation",
                description="Create initial budget",
                context_builder=lambda ctx: {
                    "period": ctx.get("period", "annual"),
                    "departments": ctx.get("departments", []),
                    "constraints": ctx.get("constraints", {}),
                },
            ),
            WorkflowStep(
                name="financial_modeling",
                agent="Keystone",
                task_type="financial_modeling",
                description="Build financial model for scenarios",
                depends_on=["budget_creation"],
                context_builder=lambda ctx: {
                    "budget": ctx.step_results.get("budget_creation"),
                    "scenarios": ctx.get("scenarios", ["base", "optimistic", "pessimistic"]),
                },
            ),
            WorkflowStep(
                name="rolling_forecast",
                agent="Keystone",
                task_type="rolling_forecast",
                description="Create rolling forecast",
                depends_on=["financial_modeling"],
                context_builder=lambda ctx: {
                    "budget": ctx.step_results.get("budget_creation"),
                    "model": ctx.step_results.get("financial_modeling"),
                    "horizon": ctx.get("forecast_horizon", "12 months"),
                },
            ),
        ]


# =============================================================================
# Forge Aggregation Workflows
# =============================================================================


class TechnicalAssessmentWorkflow(Workflow):
    """
    Forge manager-level workflow for comprehensive technical assessment
    using multiple specialists.
    """

    @property
    def name(self) -> str:
        return "technical_assessment"

    @property
    def description(self) -> str:
        return "Comprehensive technical assessment across domains"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="architecture_review",
                agent="Forge",
                task_type="architecture",
                description="Review system architecture",
                context_builder=lambda ctx: {
                    "system": ctx.get("system", ""),
                    "requirements": ctx.get("requirements", []),
                },
            ),
            WorkflowStep(
                name="code_quality",
                agent="Forge",
                task_type="code_analysis",
                description="Analyze code quality",
                context_builder=lambda ctx: {
                    "codebase": ctx.get("codebase", ""),
                    "code": ctx.get("code", ""),
                },
            ),
            WorkflowStep(
                name="security_review",
                agent="Forge",
                task_type="security_review",
                description="Review security posture",
                depends_on=["architecture_review", "code_quality"],
                context_builder=lambda ctx: {
                    "architecture": ctx.step_results.get("architecture_review"),
                    "code_quality": ctx.step_results.get("code_quality"),
                    "code": ctx.get("code", ""),
                },
            ),
            WorkflowStep(
                name="tech_debt",
                agent="Forge",
                task_type="technical_debt",
                description="Assess technical debt",
                depends_on=["code_quality"],
                context_builder=lambda ctx: {
                    "code_analysis": ctx.step_results.get("code_quality"),
                    "areas": ctx.get("areas", []),
                },
            ),
        ]


class FullDevOpsCycleWorkflow(Workflow):
    """
    Forge workflow for complete DevOps cycle setup.
    """

    @property
    def name(self) -> str:
        return "full_devops_cycle"

    @property
    def description(self) -> str:
        return "Setup complete DevOps pipeline"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="containerization",
                agent="Forge",
                task_type="containerization",
                description="Create container configuration",
                context_builder=lambda ctx: {
                    "application": ctx.get("application", ""),
                    "language": ctx.get("language", "python"),
                },
            ),
            WorkflowStep(
                name="ci_cd_setup",
                agent="Forge",
                task_type="ci_cd",
                description="Setup CI/CD pipeline",
                depends_on=["containerization"],
                context_builder=lambda ctx: {
                    "containerization": ctx.step_results.get("containerization"),
                    "platform": ctx.get("platform", "GitHub Actions"),
                },
            ),
            WorkflowStep(
                name="monitoring_setup",
                agent="Forge",
                task_type="monitoring",
                description="Setup monitoring and observability",
                depends_on=["ci_cd_setup"],
                context_builder=lambda ctx: {
                    "application": ctx.get("application", ""),
                    "stack": ctx.get("monitoring_stack", "Prometheus/Grafana"),
                },
            ),
        ]


# =============================================================================
# Echo Aggregation Workflows
# =============================================================================


class FullCampaignWorkflow(Workflow):
    """
    Echo manager-level workflow for complete campaign execution
    aggregating multiple specialist outputs.
    """

    @property
    def name(self) -> str:
        return "full_campaign"

    @property
    def description(self) -> str:
        return "Complete campaign planning and execution"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="market_research",
                agent="Echo",
                task_type="market_sizing",
                description="Research target market",
                context_builder=lambda ctx: {
                    "market": ctx.get("market", ""),
                    "audience": ctx.get("target_audience", ""),
                },
            ),
            WorkflowStep(
                name="campaign_strategy",
                agent="Echo",
                task_type="campaign_planning",
                description="Develop campaign strategy",
                depends_on=["market_research"],
                context_builder=lambda ctx: {
                    "market_research": ctx.step_results.get("market_research"),
                    "objectives": ctx.get("objectives", []),
                    "budget": ctx.get("budget", {}),
                },
            ),
            WorkflowStep(
                name="content_creation",
                agent="Echo",
                task_type="content_creation",
                description="Create campaign content",
                depends_on=["campaign_strategy"],
                context_builder=lambda ctx: {
                    "strategy": ctx.step_results.get("campaign_strategy"),
                    "content_type": ctx.get("content_type", "multi-channel"),
                },
            ),
            WorkflowStep(
                name="digital_execution",
                agent="Echo",
                task_type="digital_campaign_execution",
                description="Execute digital campaign",
                depends_on=["content_creation"],
                context_builder=lambda ctx: {
                    "content": ctx.step_results.get("content_creation"),
                    "channels": ctx.get("channels", []),
                },
            ),
        ]


class BrandHealthCheckWorkflow(Workflow):
    """
    Echo workflow for comprehensive brand health assessment.
    """

    @property
    def name(self) -> str:
        return "brand_health_check"

    @property
    def description(self) -> str:
        return "Comprehensive brand health assessment"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="competitive_intel",
                agent="Echo",
                task_type="competitive_intelligence",
                description="Gather competitive intelligence",
                context_builder=lambda ctx: {
                    "competitors": ctx.get("competitors", []),
                    "market": ctx.get("market", ""),
                },
            ),
            WorkflowStep(
                name="brand_assessment",
                agent="Echo",
                task_type="brand_health",
                description="Assess brand health metrics",
                depends_on=["competitive_intel"],
                context_builder=lambda ctx: {
                    "competitive_intel": ctx.step_results.get("competitive_intel"),
                    "brand_metrics": ctx.get("brand_metrics", {}),
                },
            ),
            WorkflowStep(
                name="positioning_review",
                agent="Echo",
                task_type="brand_positioning",
                description="Review brand positioning",
                depends_on=["brand_assessment"],
                context_builder=lambda ctx: {
                    "brand_assessment": ctx.step_results.get("brand_assessment"),
                    "current_positioning": ctx.get("current_positioning", ""),
                },
            ),
        ]


# =============================================================================
# Blueprint Aggregation Workflows
# =============================================================================


class FeatureDeliveryWorkflow(Workflow):
    """
    Blueprint manager-level workflow for complete feature delivery
    from ideation to release planning.
    """

    @property
    def name(self) -> str:
        return "feature_delivery"

    @property
    def description(self) -> str:
        return "Complete feature delivery from ideation to planning"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="market_validation",
                agent="Blueprint",
                task_type="market_analysis",
                description="Validate feature market need",
                context_builder=lambda ctx: {
                    "feature": ctx.get("feature", ""),
                    "market": ctx.get("market", ""),
                },
            ),
            WorkflowStep(
                name="feature_scoring",
                agent="Blueprint",
                task_type="feature_scoring",
                description="Score and prioritize feature",
                depends_on=["market_validation"],
                context_builder=lambda ctx: {
                    "feature": ctx.get("feature", ""),
                    "market_validation": ctx.step_results.get("market_validation"),
                    "framework": ctx.get("framework", "RICE"),
                },
            ),
            WorkflowStep(
                name="requirements",
                agent="Blueprint",
                task_type="user_story_writing",
                description="Write user stories and requirements",
                depends_on=["feature_scoring"],
                context_builder=lambda ctx: {
                    "feature": ctx.get("feature", ""),
                    "scoring": ctx.step_results.get("feature_scoring"),
                },
            ),
            WorkflowStep(
                name="roadmap_update",
                agent="Blueprint",
                task_type="roadmap_update",
                description="Update roadmap with feature",
                depends_on=["requirements"],
                context_builder=lambda ctx: {
                    "feature": ctx.get("feature", ""),
                    "requirements": ctx.step_results.get("requirements"),
                },
            ),
        ]


class SprintReadinessWorkflow(Workflow):
    """
    Blueprint workflow for sprint readiness preparation.
    """

    @property
    def name(self) -> str:
        return "sprint_readiness"

    @property
    def description(self) -> str:
        return "Prepare sprint backlog and capacity"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="backlog_grooming",
                agent="Blueprint",
                task_type="backlog_refinement",
                description="Refine sprint backlog",
                context_builder=lambda ctx: {
                    "backlog": ctx.get("backlog", []),
                    "sprint_goal": ctx.get("sprint_goal", ""),
                },
            ),
            WorkflowStep(
                name="capacity_planning",
                agent="Blueprint",
                task_type="sprint_capacity",
                description="Plan sprint capacity",
                depends_on=["backlog_grooming"],
                context_builder=lambda ctx: {
                    "groomed_backlog": ctx.step_results.get("backlog_grooming"),
                    "team_capacity": ctx.get("team_capacity", {}),
                },
            ),
            WorkflowStep(
                name="sprint_scope",
                agent="Blueprint",
                task_type="sprint_scope",
                description="Define sprint scope",
                depends_on=["capacity_planning"],
                context_builder=lambda ctx: {
                    "capacity": ctx.step_results.get("capacity_planning"),
                    "priorities": ctx.get("priorities", []),
                },
            ),
        ]


# =============================================================================
# Beacon Aggregation Workflows
# =============================================================================


class CustomerHealthReviewWorkflow(Workflow):
    """
    Beacon manager-level workflow for comprehensive customer health review.
    """

    @property
    def name(self) -> str:
        return "customer_health_review"

    @property
    def description(self) -> str:
        return "Comprehensive customer health review"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="health_scoring",
                agent="Beacon",
                task_type="customer_health_scoring",
                description="Calculate customer health scores",
                context_builder=lambda ctx: {
                    "customer_data": ctx.get("customer_data", {}),
                    "metrics": ctx.get("health_metrics", []),
                },
            ),
            WorkflowStep(
                name="churn_analysis",
                agent="Beacon",
                task_type="churn_prediction",
                description="Analyze churn risk",
                depends_on=["health_scoring"],
                context_builder=lambda ctx: {
                    "health_scores": ctx.step_results.get("health_scoring"),
                    "customer_data": ctx.get("customer_data", {}),
                },
            ),
            WorkflowStep(
                name="retention_strategy",
                agent="Beacon",
                task_type="retention_strategy",
                description="Develop retention strategies",
                depends_on=["churn_analysis"],
                context_builder=lambda ctx: {
                    "churn_analysis": ctx.step_results.get("churn_analysis"),
                    "at_risk_customers": ctx.get("at_risk_customers", []),
                },
            ),
        ]


class VoiceOfCustomerWorkflow(Workflow):
    """
    Beacon workflow for comprehensive voice of customer analysis.
    """

    @property
    def name(self) -> str:
        return "voice_of_customer"

    @property
    def description(self) -> str:
        return "Comprehensive voice of customer analysis"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="feedback_collection",
                agent="Beacon",
                task_type="feedback_collection",
                description="Collect and aggregate feedback",
                context_builder=lambda ctx: {
                    "sources": ctx.get("feedback_sources", []),
                    "period": ctx.get("period", "monthly"),
                },
            ),
            WorkflowStep(
                name="sentiment_analysis",
                agent="Beacon",
                task_type="sentiment_analysis",
                description="Analyze feedback sentiment",
                depends_on=["feedback_collection"],
                context_builder=lambda ctx: {
                    "feedback": ctx.step_results.get("feedback_collection"),
                },
            ),
            WorkflowStep(
                name="nps_analysis",
                agent="Beacon",
                task_type="nps_analysis",
                description="Analyze NPS trends",
                depends_on=["feedback_collection"],
                context_builder=lambda ctx: {
                    "nps_data": ctx.get("nps_data", []),
                },
            ),
            WorkflowStep(
                name="insights_synthesis",
                agent="Beacon",
                task_type="voice_of_customer",
                description="Synthesize customer insights",
                depends_on=["sentiment_analysis", "nps_analysis"],
                context_builder=lambda ctx: {
                    "sentiment": ctx.step_results.get("sentiment_analysis"),
                    "nps": ctx.step_results.get("nps_analysis"),
                },
            ),
        ]


# =============================================================================
# Vector Aggregation Workflows
# =============================================================================


class RevenueHealthCheckWorkflow(Workflow):
    """
    Vector manager-level workflow for comprehensive revenue health assessment.
    """

    @property
    def name(self) -> str:
        return "revenue_health_check"

    @property
    def description(self) -> str:
        return "Comprehensive revenue health assessment"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="revenue_tracking",
                agent="Vector",
                task_type="revenue_tracking",
                description="Track current revenue metrics",
                context_builder=lambda ctx: {
                    "revenue_data": ctx.get("revenue_data", {}),
                    "period": ctx.get("period", "monthly"),
                },
            ),
            WorkflowStep(
                name="mrr_analysis",
                agent="Vector",
                task_type="mrr_analysis",
                description="Analyze MRR movements",
                depends_on=["revenue_tracking"],
                context_builder=lambda ctx: {
                    "mrr_data": ctx.get("mrr_data", {}),
                    "revenue_tracking": ctx.step_results.get("revenue_tracking"),
                },
            ),
            WorkflowStep(
                name="churn_analysis",
                agent="Vector",
                task_type="churn_analysis",
                description="Analyze churn patterns",
                depends_on=["mrr_analysis"],
                context_builder=lambda ctx: {
                    "churn_data": ctx.get("churn_data", {}),
                    "mrr_analysis": ctx.step_results.get("mrr_analysis"),
                },
            ),
            WorkflowStep(
                name="revenue_forecasting",
                agent="Vector",
                task_type="revenue_forecasting",
                description="Create revenue forecast",
                depends_on=["revenue_tracking", "churn_analysis"],
                context_builder=lambda ctx: {
                    "historical_data": ctx.step_results.get("revenue_tracking"),
                    "churn_analysis": ctx.step_results.get("churn_analysis"),
                    "forecast_period": ctx.get("forecast_period", "quarter"),
                },
            ),
        ]


class GrowthAnalysisWorkflow(Workflow):
    """
    Vector workflow for comprehensive growth analysis.
    """

    @property
    def name(self) -> str:
        return "growth_analysis"

    @property
    def description(self) -> str:
        return "Comprehensive growth analysis with conversion and adoption"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="conversion_analysis",
                agent="Vector",
                task_type="conversion_analysis",
                description="Analyze conversion funnel",
                context_builder=lambda ctx: {
                    "funnel_data": ctx.get("funnel_data", {}),
                    "funnel_type": ctx.get("funnel_type", "signup_to_paid"),
                },
            ),
            WorkflowStep(
                name="feature_adoption",
                agent="Vector",
                task_type="feature_adoption_metrics",
                description="Track feature adoption",
                context_builder=lambda ctx: {
                    "adoption_data": ctx.get("adoption_data", {}),
                    "features": ctx.get("features", []),
                },
            ),
            WorkflowStep(
                name="cohort_analysis",
                agent="Vector",
                task_type="cohort_analysis",
                description="Analyze customer cohorts",
                depends_on=["conversion_analysis", "feature_adoption"],
                context_builder=lambda ctx: {
                    "cohort_data": ctx.get("cohort_data", {}),
                    "conversion_analysis": ctx.step_results.get("conversion_analysis"),
                    "feature_adoption": ctx.step_results.get("feature_adoption"),
                },
            ),
            WorkflowStep(
                name="growth_experiment",
                agent="Vector",
                task_type="growth_experiment_design",
                description="Design growth experiments",
                depends_on=["conversion_analysis", "cohort_analysis"],
                context_builder=lambda ctx: {
                    "conversion_analysis": ctx.step_results.get("conversion_analysis"),
                    "cohort_analysis": ctx.step_results.get("cohort_analysis"),
                    "hypothesis": ctx.get("hypothesis", ""),
                },
            ),
        ]


# =============================================================================
# Sentinel Aggregation Workflows
# =============================================================================


class ITGovernanceReviewWorkflow(Workflow):
    """
    Sentinel manager-level workflow for comprehensive IT governance review.
    """

    @property
    def name(self) -> str:
        return "it_governance_review"

    @property
    def description(self) -> str:
        return "Comprehensive IT governance and compliance review"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="data_governance",
                agent="Sentinel",
                task_type="data_governance",
                description="Assess data governance practices",
                context_builder=lambda ctx: {
                    "data_domain": ctx.get("data_domain", ""),
                    "compliance_requirements": ctx.get("compliance_requirements", []),
                },
            ),
            WorkflowStep(
                name="security_assessment",
                agent="Sentinel",
                task_type="security_assessment",
                description="Perform security assessment",
                depends_on=["data_governance"],
                context_builder=lambda ctx: {
                    "scope": ctx.get("scope", "infrastructure"),
                    "data_governance": ctx.step_results.get("data_governance"),
                },
            ),
            WorkflowStep(
                name="systems_analysis",
                agent="Sentinel",
                task_type="systems_analysis",
                description="Analyze IT systems",
                depends_on=["data_governance"],
                context_builder=lambda ctx: {
                    "system": ctx.get("system", ""),
                    "data_governance": ctx.step_results.get("data_governance"),
                },
            ),
            WorkflowStep(
                name="governance_synthesis",
                agent="Sentinel",
                task_type="data_verification",
                description="Synthesize governance findings",
                depends_on=["security_assessment", "systems_analysis"],
                context_builder=lambda ctx: {
                    "security_assessment": ctx.step_results.get("security_assessment"),
                    "systems_analysis": ctx.step_results.get("systems_analysis"),
                },
            ),
        ]


class KnowledgeManagementWorkflow(Workflow):
    """
    Sentinel workflow for comprehensive knowledge management.
    """

    @property
    def name(self) -> str:
        return "knowledge_management"

    @property
    def description(self) -> str:
        return "Extract, organize, and verify knowledge"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="knowledge_extraction",
                agent="Sentinel",
                task_type="knowledge_extraction",
                description="Extract knowledge from sources",
                context_builder=lambda ctx: {
                    "source_documents": ctx.get("source_documents", []),
                    "extraction_type": ctx.get("extraction_type", "entities"),
                },
            ),
            WorkflowStep(
                name="knowledge_organization",
                agent="Sentinel",
                task_type="knowledge_curation",
                description="Organize extracted knowledge",
                depends_on=["knowledge_extraction"],
                context_builder=lambda ctx: {
                    "extracted_knowledge": ctx.step_results.get("knowledge_extraction"),
                    "taxonomy": ctx.get("taxonomy", {}),
                },
            ),
            WorkflowStep(
                name="verification",
                agent="Sentinel",
                task_type="data_verification",
                description="Verify knowledge accuracy",
                depends_on=["knowledge_organization"],
                context_builder=lambda ctx: {
                    "knowledge": ctx.step_results.get("knowledge_organization"),
                    "verification_rules": ctx.get("verification_rules", []),
                },
            ),
        ]


# =============================================================================
# Axiom Aggregation Workflows
# =============================================================================


class ComprehensiveResearchWorkflow(Workflow):
    """
    Axiom manager-level workflow for comprehensive research project.
    """

    @property
    def name(self) -> str:
        return "comprehensive_research"

    @property
    def description(self) -> str:
        return "End-to-end research from literature review to analysis"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="literature_review",
                agent="Axiom",
                task_type="literature_review",
                description="Conduct literature review",
                context_builder=lambda ctx: {
                    "field": ctx.get("field", ""),
                    "timeframe": ctx.get("timeframe", "recent"),
                },
            ),
            WorkflowStep(
                name="experiment_design",
                agent="Axiom",
                task_type="experiment_design",
                description="Design research methodology",
                depends_on=["literature_review"],
                context_builder=lambda ctx: {
                    "objective": ctx.get("objective", ""),
                    "literature_review": ctx.step_results.get("literature_review"),
                },
            ),
            WorkflowStep(
                name="data_analysis",
                agent="Axiom",
                task_type="data_analysis",
                description="Analyze research data",
                depends_on=["experiment_design"],
                context_builder=lambda ctx: {
                    "data_description": ctx.get("data_description", ""),
                    "experiment_design": ctx.step_results.get("experiment_design"),
                },
            ),
            WorkflowStep(
                name="findings_synthesis",
                agent="Axiom",
                task_type="meta_analysis",
                description="Synthesize research findings",
                depends_on=["data_analysis"],
                context_builder=lambda ctx: {
                    "literature_review": ctx.step_results.get("literature_review"),
                    "data_analysis": ctx.step_results.get("data_analysis"),
                },
            ),
        ]


class FeasibilityAssessmentWorkflow(Workflow):
    """
    Axiom workflow for comprehensive feasibility assessment.
    """

    @property
    def name(self) -> str:
        return "feasibility_assessment"

    @property
    def description(self) -> str:
        return "Multi-dimensional feasibility assessment"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="technology_assessment",
                agent="Axiom",
                task_type="technology_assessment",
                description="Assess technical feasibility",
                context_builder=lambda ctx: {
                    "technology": ctx.get("technology", ""),
                    "use_case": ctx.get("use_case", ""),
                },
            ),
            WorkflowStep(
                name="impact_analysis",
                agent="Axiom",
                task_type="impact_analysis",
                description="Analyze potential impact",
                depends_on=["technology_assessment"],
                context_builder=lambda ctx: {
                    "change": ctx.get("proposal", ""),
                    "technology_assessment": ctx.step_results.get("technology_assessment"),
                },
            ),
            WorkflowStep(
                name="feasibility_study",
                agent="Axiom",
                task_type="feasibility_study",
                description="Conduct overall feasibility study",
                depends_on=["technology_assessment", "impact_analysis"],
                context_builder=lambda ctx: {
                    "proposal": ctx.get("proposal", ""),
                    "technology_assessment": ctx.step_results.get("technology_assessment"),
                    "impact_analysis": ctx.step_results.get("impact_analysis"),
                },
            ),
        ]


# =============================================================================
# Compass Aggregation Workflows
# =============================================================================


class StrategicAnalysisWorkflow(Workflow):
    """
    Compass manager-level workflow for comprehensive strategic analysis.
    """

    @property
    def name(self) -> str:
        return "strategic_analysis"

    @property
    def description(self) -> str:
        return "Comprehensive strategic analysis with market and competitive insights"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="market_analysis",
                agent="Compass",
                task_type="market_analysis",
                description="Analyze target market",
                context_builder=lambda ctx: {
                    "market": ctx.get("market", ""),
                    "scope": ctx.get("scope", "comprehensive"),
                },
            ),
            WorkflowStep(
                name="competitive_analysis",
                agent="Compass",
                task_type="competitive_analysis",
                description="Analyze competitive landscape",
                depends_on=["market_analysis"],
                context_builder=lambda ctx: {
                    "industry": ctx.get("industry", ""),
                    "market_analysis": ctx.step_results.get("market_analysis"),
                },
            ),
            WorkflowStep(
                name="swot_analysis",
                agent="Compass",
                task_type="swot_analysis",
                description="Perform SWOT analysis",
                depends_on=["market_analysis", "competitive_analysis"],
                context_builder=lambda ctx: {
                    "subject": ctx.get("subject", "organization"),
                    "market_analysis": ctx.step_results.get("market_analysis"),
                    "competitive_analysis": ctx.step_results.get("competitive_analysis"),
                },
            ),
            WorkflowStep(
                name="strategic_plan",
                agent="Compass",
                task_type="strategic_planning",
                description="Develop strategic plan",
                depends_on=["swot_analysis"],
                context_builder=lambda ctx: {
                    "swot_analysis": ctx.step_results.get("swot_analysis"),
                    "timeframe": ctx.get("timeframe", "1 year"),
                },
            ),
        ]


class GTMPlanningWorkflow(Workflow):
    """
    Compass workflow for comprehensive go-to-market planning.
    """

    @property
    def name(self) -> str:
        return "gtm_planning"

    @property
    def description(self) -> str:
        return "Develop comprehensive go-to-market strategy"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="market_research",
                agent="Compass",
                task_type="market_analysis",
                description="Research target market",
                context_builder=lambda ctx: {
                    "market": ctx.get("market", ""),
                    "product": ctx.get("product", ""),
                },
            ),
            WorkflowStep(
                name="value_proposition",
                agent="Compass",
                task_type="value_proposition",
                description="Define value proposition",
                depends_on=["market_research"],
                context_builder=lambda ctx: {
                    "segment": ctx.get("segment", ""),
                    "product": ctx.get("product", ""),
                    "market_research": ctx.step_results.get("market_research"),
                },
            ),
            WorkflowStep(
                name="content_strategy",
                agent="Compass",
                task_type="content_strategy",
                description="Develop content strategy",
                depends_on=["value_proposition"],
                context_builder=lambda ctx: {
                    "audience": ctx.get("audience", ""),
                    "value_proposition": ctx.step_results.get("value_proposition"),
                },
            ),
            WorkflowStep(
                name="gtm_plan",
                agent="Compass",
                task_type="go_to_market",
                description="Create go-to-market plan",
                depends_on=["market_research", "value_proposition", "content_strategy"],
                context_builder=lambda ctx: {
                    "product": ctx.get("product", ""),
                    "market": ctx.get("market", ""),
                    "market_research": ctx.step_results.get("market_research"),
                    "value_proposition": ctx.step_results.get("value_proposition"),
                    "content_strategy": ctx.step_results.get("content_strategy"),
                },
            ),
        ]


# =============================================================================
# Nexus Aggregation Workflows
# =============================================================================


class OperationsReviewWorkflow(Workflow):
    """
    Nexus manager-level workflow for comprehensive operations review.
    """

    @property
    def name(self) -> str:
        return "operations_review"

    @property
    def description(self) -> str:
        return "Comprehensive operations review with metrics and recommendations"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="performance_analysis",
                agent="Nexus",
                task_type="performance_analysis",
                description="Analyze cross-functional performance",
                context_builder=lambda ctx: {
                    "metrics": ctx.get("metrics", {}),
                    "period": ctx.get("period", "current"),
                },
            ),
            WorkflowStep(
                name="bottleneck_analysis",
                agent="Nexus",
                task_type="efficiency_analysis",
                description="Identify operational bottlenecks",
                depends_on=["performance_analysis"],
                context_builder=lambda ctx: {
                    "performance_analysis": ctx.step_results.get("performance_analysis"),
                    "scope": ctx.get("scope", "all"),
                },
            ),
            WorkflowStep(
                name="process_review",
                agent="Nexus",
                task_type="process_optimization",
                description="Review and optimize processes",
                depends_on=["bottleneck_analysis"],
                context_builder=lambda ctx: {
                    "bottlenecks": ctx.step_results.get("bottleneck_analysis"),
                    "goals": ctx.get("goals", ["improve efficiency"]),
                },
            ),
            WorkflowStep(
                name="operations_report",
                agent="Nexus",
                task_type="reporting",
                description="Generate operations report",
                depends_on=["performance_analysis", "bottleneck_analysis", "process_review"],
                context_builder=lambda ctx: {
                    "data": {
                        "performance": ctx.step_results.get("performance_analysis"),
                        "bottlenecks": ctx.step_results.get("bottleneck_analysis"),
                        "process_review": ctx.step_results.get("process_review"),
                    },
                    "report_type": "comprehensive",
                    "audience": "agent",
                },
            ),
        ]


class CrossFunctionalCoordinationWorkflow(Workflow):
    """
    Nexus workflow for coordinating cross-functional initiatives.
    """

    @property
    def name(self) -> str:
        return "cross_functional_coordination"

    @property
    def description(self) -> str:
        return "Coordinate cross-functional initiative across agents"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="task_analysis",
                agent="Nexus",
                task_type="task_classification",
                description="Analyze initiative requirements",
                context_builder=lambda ctx: {
                    "task_description": ctx.get("initiative", ""),
                    "context": ctx.get("context", {}),
                },
            ),
            WorkflowStep(
                name="workflow_design",
                agent="Nexus",
                task_type="workflow_creation",
                description="Design coordination workflow",
                depends_on=["task_analysis"],
                context_builder=lambda ctx: {
                    "goal": ctx.get("initiative", ""),
                    "agents": ctx.get("teams", []),
                    "task_analysis": ctx.step_results.get("task_analysis"),
                },
            ),
            WorkflowStep(
                name="resource_allocation",
                agent="Nexus",
                task_type="resource_allocation",
                description="Plan resource allocation",
                depends_on=["workflow_design"],
                context_builder=lambda ctx: {
                    "project": ctx.get("initiative", ""),
                    "resources": ctx.get("resources", {}),
                    "workflow": ctx.step_results.get("workflow_design"),
                },
            ),
            WorkflowStep(
                name="coordination_plan",
                agent="Nexus",
                task_type="cross_functional_coordination",
                description="Finalize coordination plan",
                depends_on=["workflow_design", "resource_allocation"],
                context_builder=lambda ctx: {
                    "teams": ctx.get("teams", []),
                    "workflow": ctx.step_results.get("workflow_design"),
                    "resources": ctx.step_results.get("resource_allocation"),
                },
            ),
        ]


# =============================================================================
# Accord Aggregation Workflows (Compliance)
# =============================================================================


class ComplianceProgramReviewWorkflow(Workflow):
    """Multi-step workflow for comprehensive compliance program review."""

    @property
    def name(self) -> str:
        return "compliance_program_review"

    @property
    def description(self) -> str:
        return "Comprehensive compliance program review with gap analysis and remediation"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="compliance_assessment",
                agent="Accord",
                task_type="compliance_assessment",
                description="Assess current compliance posture",
                context_builder=lambda ctx: {
                    "framework": ctx.get("framework", "general"),
                    "scope": ctx.get("scope", "enterprise"),
                },
            ),
            WorkflowStep(
                name="gap_analysis",
                agent="Accord",
                task_type="gap_analysis",
                description="Identify compliance gaps",
                depends_on=["compliance_assessment"],
                context_builder=lambda ctx: {
                    "assessment": ctx.step_results.get("compliance_assessment"),
                    "requirements": ctx.get("requirements", []),
                },
            ),
            WorkflowStep(
                name="policy_review",
                agent="Accord",
                task_type="policy_review",
                description="Review relevant policies",
                depends_on=["gap_analysis"],
                context_builder=lambda ctx: {
                    "gaps": ctx.step_results.get("gap_analysis"),
                    "policies": ctx.get("policies", []),
                },
            ),
            WorkflowStep(
                name="remediation_plan",
                agent="Accord",
                task_type="compliance_remediation",
                description="Develop remediation plan",
                depends_on=["gap_analysis", "policy_review"],
                context_builder=lambda ctx: {
                    "gaps": ctx.step_results.get("gap_analysis"),
                    "policy_findings": ctx.step_results.get("policy_review"),
                    "priority": ctx.get("priority", "medium"),
                },
            ),
        ]


class AuditReadinessWorkflow(Workflow):
    """Multi-step workflow for audit preparation and readiness."""

    @property
    def name(self) -> str:
        return "audit_readiness"

    @property
    def description(self) -> str:
        return "Prepare for audit with evidence collection and gap remediation"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="scope_review",
                agent="Accord",
                task_type="audit_scoping",
                description="Review audit scope and requirements",
                context_builder=lambda ctx: {
                    "audit_type": ctx.get("audit_type", ""),
                    "framework": ctx.get("framework", ""),
                },
            ),
            WorkflowStep(
                name="evidence_collection",
                agent="Accord",
                task_type="evidence_gathering",
                description="Collect audit evidence",
                depends_on=["scope_review"],
                context_builder=lambda ctx: {
                    "scope": ctx.step_results.get("scope_review"),
                    "controls": ctx.get("controls", []),
                },
            ),
            WorkflowStep(
                name="readiness_assessment",
                agent="Accord",
                task_type="audit_preparation",
                description="Assess audit readiness",
                depends_on=["evidence_collection"],
                context_builder=lambda ctx: {
                    "evidence": ctx.step_results.get("evidence_collection"),
                    "framework": ctx.get("framework", ""),
                },
            ),
        ]


# =============================================================================
# Aegis Aggregation Workflows (Risk)
# =============================================================================


class EnterpriseRiskAssessmentWorkflow(Workflow):
    """Multi-step workflow for enterprise risk assessment."""

    @property
    def name(self) -> str:
        return "enterprise_risk_assessment"

    @property
    def description(self) -> str:
        return "Comprehensive enterprise risk assessment with scoring and mitigation"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="risk_identification",
                agent="Aegis",
                task_type="risk_identification",
                description="Identify enterprise risks",
                context_builder=lambda ctx: {
                    "scope": ctx.get("scope", "enterprise"),
                    "categories": ctx.get("categories", []),
                },
            ),
            WorkflowStep(
                name="risk_scoring",
                agent="Aegis",
                task_type="risk_scoring",
                description="Score and prioritize risks",
                depends_on=["risk_identification"],
                context_builder=lambda ctx: {
                    "risks": ctx.step_results.get("risk_identification"),
                    "methodology": ctx.get("methodology", "5x5"),
                },
            ),
            WorkflowStep(
                name="control_assessment",
                agent="Aegis",
                task_type="control_assessment",
                description="Assess existing controls",
                depends_on=["risk_scoring"],
                context_builder=lambda ctx: {
                    "risks": ctx.step_results.get("risk_scoring"),
                    "controls": ctx.get("controls", []),
                },
            ),
            WorkflowStep(
                name="mitigation_planning",
                agent="Aegis",
                task_type="mitigation_planning",
                description="Develop mitigation strategies",
                depends_on=["risk_scoring", "control_assessment"],
                context_builder=lambda ctx: {
                    "risks": ctx.step_results.get("risk_scoring"),
                    "controls": ctx.step_results.get("control_assessment"),
                    "appetite": ctx.get("risk_appetite", {}),
                },
            ),
        ]


class BCPDRPlanningWorkflow(Workflow):
    """Multi-step workflow for BCP and DR planning."""

    @property
    def name(self) -> str:
        return "bcp_dr_planning"

    @property
    def description(self) -> str:
        return "Business continuity and disaster recovery planning"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="impact_analysis",
                agent="Aegis",
                task_type="impact_analysis",
                description="Conduct business impact analysis",
                context_builder=lambda ctx: {
                    "processes": ctx.get("processes", []),
                    "systems": ctx.get("systems", []),
                },
            ),
            WorkflowStep(
                name="recovery_planning",
                agent="Aegis",
                task_type="recovery_planning",
                description="Develop recovery strategies",
                depends_on=["impact_analysis"],
                context_builder=lambda ctx: {
                    "impact": ctx.step_results.get("impact_analysis"),
                    "rto_rpo": ctx.get("rto_rpo", {}),
                },
            ),
            WorkflowStep(
                name="bcp_development",
                agent="Aegis",
                task_type="bcp_planning",
                description="Develop business continuity plan",
                depends_on=["impact_analysis", "recovery_planning"],
                context_builder=lambda ctx: {
                    "impact": ctx.step_results.get("impact_analysis"),
                    "recovery": ctx.step_results.get("recovery_planning"),
                },
            ),
        ]


# =============================================================================
# Citadel Aggregation Workflows (Security)
# =============================================================================


class SecurityPostureAssessmentWorkflow(Workflow):
    """Multi-step workflow for security posture assessment."""

    @property
    def name(self) -> str:
        return "security_posture_assessment"

    @property
    def description(self) -> str:
        return "Comprehensive security posture assessment"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="vulnerability_scan",
                agent="Citadel",
                task_type="vulnerability_assessment",
                description="Scan for vulnerabilities",
                context_builder=lambda ctx: {
                    "scope": ctx.get("scope", ""),
                    "targets": ctx.get("targets", []),
                },
            ),
            WorkflowStep(
                name="threat_assessment",
                agent="Citadel",
                task_type="threat_assessment",
                description="Assess threat landscape",
                context_builder=lambda ctx: {
                    "environment": ctx.get("environment", ""),
                    "threat_intel": ctx.get("threat_intel", {}),
                },
            ),
            WorkflowStep(
                name="risk_analysis",
                agent="Citadel",
                task_type="security_risk_analysis",
                description="Analyze security risks",
                depends_on=["vulnerability_scan", "threat_assessment"],
                context_builder=lambda ctx: {
                    "vulnerabilities": ctx.step_results.get("vulnerability_scan"),
                    "threats": ctx.step_results.get("threat_assessment"),
                },
            ),
            WorkflowStep(
                name="remediation_recommendations",
                agent="Citadel",
                task_type="security_remediation",
                description="Develop remediation plan",
                depends_on=["risk_analysis"],
                context_builder=lambda ctx: {
                    "risks": ctx.step_results.get("risk_analysis"),
                    "priority": ctx.get("priority", "critical_first"),
                },
            ),
        ]


class SecurityIncidentWorkflow(Workflow):
    """Multi-step workflow for security incident handling."""

    @property
    def name(self) -> str:
        return "security_incident_handling"

    @property
    def description(self) -> str:
        return "End-to-end security incident response"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="triage",
                agent="Citadel",
                task_type="incident_triage",
                description="Triage the security incident",
                context_builder=lambda ctx: {
                    "incident": ctx.get("incident", {}),
                    "indicators": ctx.get("indicators", []),
                },
            ),
            WorkflowStep(
                name="investigation",
                agent="Citadel",
                task_type="incident_investigation",
                description="Investigate incident details",
                depends_on=["triage"],
                context_builder=lambda ctx: {
                    "triage_results": ctx.step_results.get("triage"),
                    "scope": ctx.get("scope", {}),
                },
            ),
            WorkflowStep(
                name="containment",
                agent="Citadel",
                task_type="incident_containment",
                description="Contain the incident",
                depends_on=["investigation"],
                context_builder=lambda ctx: {
                    "findings": ctx.step_results.get("investigation"),
                    "affected_systems": ctx.get("affected_systems", []),
                },
            ),
            WorkflowStep(
                name="lessons_learned",
                agent="Citadel",
                task_type="incident_review",
                description="Document lessons learned",
                depends_on=["containment"],
                context_builder=lambda ctx: {
                    "incident": ctx.get("incident", {}),
                    "response": ctx.step_results.get("containment"),
                },
            ),
        ]


# =============================================================================
# Foundry Aggregation Workflows (Engineering)
# =============================================================================


class ReleaseCycleWorkflow(Workflow):
    """Multi-step workflow for complete release cycle."""

    @property
    def name(self) -> str:
        return "release_cycle"

    @property
    def description(self) -> str:
        return "Complete release cycle from planning to deployment"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="sprint_planning",
                agent="Foundry",
                task_type="sprint_planning",
                description="Plan sprint deliverables",
                context_builder=lambda ctx: {
                    "backlog": ctx.get("backlog", []),
                    "capacity": ctx.get("capacity", {}),
                },
            ),
            WorkflowStep(
                name="quality_gate",
                agent="Foundry",
                task_type="qa_testing",
                description="Execute QA testing",
                depends_on=["sprint_planning"],
                context_builder=lambda ctx: {
                    "features": ctx.get("features", []),
                    "criteria": ctx.get("acceptance_criteria", []),
                },
            ),
            WorkflowStep(
                name="release_preparation",
                agent="Foundry",
                task_type="release_preparation",
                description="Prepare release artifacts",
                depends_on=["quality_gate"],
                context_builder=lambda ctx: {
                    "qa_results": ctx.step_results.get("quality_gate"),
                    "version": ctx.get("version", ""),
                },
            ),
            WorkflowStep(
                name="deployment",
                agent="Foundry",
                task_type="deployment",
                description="Deploy to target environment",
                depends_on=["release_preparation"],
                context_builder=lambda ctx: {
                    "artifacts": ctx.step_results.get("release_preparation"),
                    "environment": ctx.get("environment", "production"),
                },
            ),
        ]


class EngineeringMetricsWorkflow(Workflow):
    """Multi-step workflow for engineering metrics analysis."""

    @property
    def name(self) -> str:
        return "engineering_metrics"

    @property
    def description(self) -> str:
        return "Comprehensive engineering metrics collection and analysis"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="metrics_collection",
                agent="Foundry",
                task_type="metrics_collection",
                description="Collect engineering metrics",
                context_builder=lambda ctx: {
                    "period": ctx.get("period", "sprint"),
                    "metrics": ctx.get("metrics", ["velocity", "quality", "throughput"]),
                },
            ),
            WorkflowStep(
                name="quality_analysis",
                agent="Foundry",
                task_type="quality_analysis",
                description="Analyze code quality metrics",
                depends_on=["metrics_collection"],
                context_builder=lambda ctx: {
                    "data": ctx.step_results.get("metrics_collection"),
                    "thresholds": ctx.get("thresholds", {}),
                },
            ),
            WorkflowStep(
                name="improvement_recommendations",
                agent="Foundry",
                task_type="process_improvement",
                description="Generate improvement recommendations",
                depends_on=["metrics_collection", "quality_analysis"],
                context_builder=lambda ctx: {
                    "metrics": ctx.step_results.get("metrics_collection"),
                    "quality": ctx.step_results.get("quality_analysis"),
                },
            ),
        ]
