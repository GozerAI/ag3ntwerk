"""
Customer & Revenue Workflows.

Workflows for customer onboarding, churn analysis, customer health,
revenue growth, revenue analysis, and marketing campaigns.
"""

from typing import Any, Dict, List

from ag3ntwerk.orchestration.base import Workflow, WorkflowStep


class CustomerOnboardingWorkflow(Workflow):
    """
    Workflow for enterprise customer onboarding.

    Coordinates across:
    - Beacon (Beacon): Customer success and onboarding
    - Blueprint (Blueprint): Product configuration
    - Foundry (Foundry): Technical setup
    - Citadel (Citadel): Security provisioning

    Steps:
    1. Onboarding Plan - Beacon creates customized onboarding plan
    2. Product Setup - Blueprint configures product for customer
    3. Technical Provisioning - Foundry handles technical setup
    4. Security Setup - Citadel provisions access and security
    5. Training Plan - Beacon creates training and adoption plan
    6. Success Metrics - Beacon defines success criteria
    """

    @property
    def name(self) -> str:
        return "customer_onboarding"

    @property
    def description(self) -> str:
        return "Enterprise customer onboarding with technical and success setup"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="onboarding_plan",
                agent="Beacon",
                task_type="onboarding_optimization",
                description="Create customized onboarding plan",
                context_builder=lambda ctx: {
                    "customer_name": ctx.get("customer_name"),
                    "customer_tier": ctx.get("customer_tier", "enterprise"),
                    "use_cases": ctx.get("use_cases", []),
                    "timeline": ctx.get("timeline", "30_days"),
                },
            ),
            WorkflowStep(
                name="product_setup",
                agent="Blueprint",
                task_type="product_spec",
                description="Configure product for customer requirements",
                depends_on=["onboarding_plan"],
                context_builder=lambda ctx: {
                    "customer_name": ctx.get("customer_name"),
                    "onboarding_plan": ctx.step_results.get("onboarding_plan"),
                    "features_required": ctx.get("features_required", []),
                    "customizations": ctx.get("customizations", {}),
                },
            ),
            WorkflowStep(
                name="technical_provisioning",
                agent="Foundry",
                task_type="infrastructure_provisioning",
                description="Handle technical environment setup",
                depends_on=["product_setup"],
                context_builder=lambda ctx: {
                    "customer_name": ctx.get("customer_name"),
                    "product_config": ctx.step_results.get("product_setup"),
                    "environment": ctx.get("environment", "production"),
                    "integrations": ctx.get("integrations", []),
                },
            ),
            WorkflowStep(
                name="security_setup",
                agent="Citadel",
                task_type="access_review",
                description="Provision access and security controls",
                depends_on=["technical_provisioning"],
                context_builder=lambda ctx: {
                    "customer_name": ctx.get("customer_name"),
                    "technical_setup": ctx.step_results.get("technical_provisioning"),
                    "user_count": ctx.get("user_count", 10),
                    "security_requirements": ctx.get("security_requirements", []),
                },
            ),
            WorkflowStep(
                name="training_plan",
                agent="Beacon",
                task_type="customer_journey_mapping",
                description="Create training and adoption plan",
                depends_on=["product_setup", "security_setup"],
                context_builder=lambda ctx: {
                    "customer_name": ctx.get("customer_name"),
                    "product_config": ctx.step_results.get("product_setup"),
                    "user_roles": ctx.get("user_roles", []),
                    "training_format": ctx.get("training_format", "virtual"),
                },
            ),
            WorkflowStep(
                name="success_metrics",
                agent="Beacon",
                task_type="customer_health_scoring",
                description="Define success criteria and health metrics",
                depends_on=["onboarding_plan", "training_plan"],
                context_builder=lambda ctx: {
                    "customer_name": ctx.get("customer_name"),
                    "onboarding_plan": ctx.step_results.get("onboarding_plan"),
                    "use_cases": ctx.get("use_cases", []),
                    "kpis": ctx.get("kpis", []),
                },
            ),
        ]


class CustomerChurnAnalysisWorkflow(Workflow):
    """
    Workflow for customer churn analysis and prevention.

    Coordinates across:
    - Beacon (Beacon): Customer health analysis
    - Vector (Vector): Revenue impact analysis
    - Index (Index): Data analytics
    - Echo (Echo): Retention campaigns

    Steps:
    1. Churn Analysis - Beacon analyzes churn patterns
    2. Revenue Impact - Vector calculates revenue impact
    3. Predictive Analysis - Index builds churn prediction
    4. Root Cause - Vector identifies churn drivers
    5. Retention Strategy - Beacon creates retention plan
    6. Win-back Campaign - Echo designs win-back campaign
    """

    @property
    def name(self) -> str:
        return "churn_analysis"

    @property
    def description(self) -> str:
        return "Customer churn analysis and prevention planning"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="churn_analysis",
                agent="Beacon",
                task_type="churn_analysis",
                description="Analyze customer churn patterns",
                context_builder=lambda ctx: {
                    "analysis_period": ctx.get("analysis_period", "last_quarter"),
                    "customer_segments": ctx.get("customer_segments", []),
                    "churn_definition": ctx.get("churn_definition", "90_days_inactive"),
                },
            ),
            WorkflowStep(
                name="revenue_impact",
                agent="Vector",
                task_type="churn_analysis",
                description="Calculate revenue impact of churn",
                depends_on=["churn_analysis"],
                context_builder=lambda ctx: {
                    "churn_data": ctx.step_results.get("churn_analysis"),
                    "ltv_model": ctx.get("ltv_model", {}),
                },
            ),
            WorkflowStep(
                name="predictive_analysis",
                agent="Index",
                task_type="predictive_analytics",
                description="Build churn prediction model",
                depends_on=["churn_analysis"],
                context_builder=lambda ctx: {
                    "churn_data": ctx.step_results.get("churn_analysis"),
                    "prediction_features": ctx.get("prediction_features", []),
                    "model_type": ctx.get("model_type", "classification"),
                },
            ),
            WorkflowStep(
                name="root_cause",
                agent="Vector",
                task_type="cohort_analysis",
                description="Identify churn drivers and root causes",
                depends_on=["churn_analysis", "revenue_impact"],
                context_builder=lambda ctx: {
                    "churn_data": ctx.step_results.get("churn_analysis"),
                    "revenue_impact": ctx.step_results.get("revenue_impact"),
                    "feedback_data": ctx.get("feedback_data", {}),
                },
            ),
            WorkflowStep(
                name="retention_strategy",
                agent="Beacon",
                task_type="retention_strategy",
                description="Create customer retention plan",
                depends_on=["root_cause", "predictive_analysis"],
                context_builder=lambda ctx: {
                    "root_causes": ctx.step_results.get("root_cause"),
                    "at_risk_customers": ctx.step_results.get("predictive_analysis"),
                    "retention_budget": ctx.get("retention_budget"),
                },
            ),
            WorkflowStep(
                name="winback_campaign",
                agent="Echo",
                task_type="campaign_creation",
                description="Design win-back campaign for churned customers",
                depends_on=["root_cause", "retention_strategy"],
                context_builder=lambda ctx: {
                    "churned_segments": ctx.step_results.get("root_cause"),
                    "retention_strategy": ctx.step_results.get("retention_strategy"),
                    "campaign_budget": ctx.get("winback_budget"),
                    "channels": ctx.get("channels", ["email", "in-app"]),
                },
            ),
        ]


class CustomerHealthReviewWorkflow(Workflow):
    """
    Beacon internal workflow for customer health review.

    Steps:
    1. Health Score Calculation - Calculate customer health scores
    2. Engagement Analysis - Analyze customer engagement
    3. Risk Identification - Identify at-risk customers
    4. Success Planning - Create success plans
    5. Outreach Strategy - Plan customer outreach
    """

    @property
    def name(self) -> str:
        return "customer_health_review"

    @property
    def description(self) -> str:
        return "Beacon customer health review workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="health_score_calculation",
                agent="Beacon",
                task_type="customer_health_scoring",
                description="Calculate customer health scores",
                context_builder=lambda ctx: {
                    "customer_segments": ctx.get("customer_segments", []),
                    "health_factors": ctx.get(
                        "health_factors",
                        ["product_usage", "support_tickets", "nps", "payment_history"],
                    ),
                    "time_period": ctx.get("time_period", "last_30_days"),
                },
            ),
            WorkflowStep(
                name="engagement_analysis",
                agent="Beacon",
                task_type="engagement_tracking",
                description="Analyze customer engagement patterns",
                depends_on=["health_score_calculation"],
                context_builder=lambda ctx: {
                    "health_scores": ctx.step_results.get("health_score_calculation"),
                    "engagement_channels": ctx.get("engagement_channels", []),
                    "activity_threshold": ctx.get("activity_threshold"),
                },
            ),
            WorkflowStep(
                name="risk_identification",
                agent="Beacon",
                task_type="churn_analysis",
                description="Identify at-risk customers",
                depends_on=["health_score_calculation", "engagement_analysis"],
                context_builder=lambda ctx: {
                    "health_scores": ctx.step_results.get("health_score_calculation"),
                    "engagement": ctx.step_results.get("engagement_analysis"),
                    "risk_threshold": ctx.get("risk_threshold", 0.3),
                },
            ),
            WorkflowStep(
                name="success_planning",
                agent="Beacon",
                task_type="success_planning",
                description="Create customer success plans",
                depends_on=["risk_identification"],
                context_builder=lambda ctx: {
                    "at_risk_customers": ctx.step_results.get("risk_identification"),
                    "success_templates": ctx.get("success_templates", {}),
                    "resources_available": ctx.get("resources_available", {}),
                },
            ),
            WorkflowStep(
                name="outreach_strategy",
                agent="Beacon",
                task_type="customer_journey_mapping",
                description="Plan customer outreach strategy",
                depends_on=["success_planning"],
                context_builder=lambda ctx: {
                    "success_plans": ctx.step_results.get("success_planning"),
                    "outreach_channels": ctx.get("outreach_channels", ["email", "call", "in-app"]),
                    "priority_tiers": ctx.get("priority_tiers", {}),
                },
            ),
        ]


class RevenueGrowthWorkflow(Workflow):
    """
    Workflow for revenue growth initiative planning.

    Coordinates across:
    - Vector (Vector): Revenue strategy and metrics
    - Echo (Echo): Marketing and demand generation
    - Compass (Compass): Market strategy
    - Keystone (Keystone): Financial modeling

    Steps:
    1. Revenue Analysis - Vector analyzes current revenue performance
    2. Market Opportunity - Compass identifies growth opportunities
    3. Marketing Strategy - Echo creates demand generation plan
    4. Financial Modeling - Keystone builds revenue projections
    5. Pricing Analysis - Vector optimizes pricing strategy
    6. Growth Plan - Vector consolidates growth roadmap
    """

    @property
    def name(self) -> str:
        return "revenue_growth"

    @property
    def description(self) -> str:
        return "Revenue growth initiative planning and execution"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="revenue_analysis",
                agent="Vector",
                task_type="revenue_tracking",
                description="Analyze current revenue performance",
                context_builder=lambda ctx: {
                    "analysis_period": ctx.get("analysis_period", "last_quarter"),
                    "revenue_streams": ctx.get("revenue_streams", []),
                    "growth_target": ctx.get("growth_target"),
                },
            ),
            WorkflowStep(
                name="market_opportunity",
                agent="Compass",
                task_type="opportunity_assessment",
                description="Identify market growth opportunities",
                depends_on=["revenue_analysis"],
                context_builder=lambda ctx: {
                    "revenue_analysis": ctx.step_results.get("revenue_analysis"),
                    "target_markets": ctx.get("target_markets", []),
                    "competitive_landscape": ctx.get("competitive_landscape", {}),
                },
            ),
            WorkflowStep(
                name="marketing_strategy",
                agent="Echo",
                task_type="demand_generation",
                description="Create demand generation and marketing plan",
                depends_on=["market_opportunity"],
                context_builder=lambda ctx: {
                    "market_opportunities": ctx.step_results.get("market_opportunity"),
                    "marketing_budget": ctx.get("marketing_budget"),
                    "channels": ctx.get("marketing_channels", []),
                    "target_segments": ctx.get("target_segments", []),
                },
            ),
            WorkflowStep(
                name="financial_modeling",
                agent="Keystone",
                task_type="financial_modeling",
                description="Build revenue projections and unit economics",
                depends_on=["revenue_analysis", "market_opportunity"],
                context_builder=lambda ctx: {
                    "revenue_analysis": ctx.step_results.get("revenue_analysis"),
                    "market_opportunities": ctx.step_results.get("market_opportunity"),
                    "growth_target": ctx.get("growth_target"),
                    "investment_level": ctx.get("investment_level"),
                },
            ),
            WorkflowStep(
                name="pricing_analysis",
                agent="Vector",
                task_type="pricing_analysis",
                description="Optimize pricing strategy for growth",
                depends_on=["financial_modeling"],
                context_builder=lambda ctx: {
                    "financial_model": ctx.step_results.get("financial_modeling"),
                    "current_pricing": ctx.get("current_pricing", {}),
                    "competitor_pricing": ctx.get("competitor_pricing", {}),
                },
            ),
            WorkflowStep(
                name="growth_plan",
                agent="Vector",
                task_type="growth_experiment_design",
                description="Consolidate growth roadmap and experiments",
                depends_on=[
                    "revenue_analysis",
                    "market_opportunity",
                    "marketing_strategy",
                    "financial_modeling",
                    "pricing_analysis",
                ],
                context_builder=lambda ctx: {
                    "all_inputs": {
                        "revenue": ctx.step_results.get("revenue_analysis"),
                        "market": ctx.step_results.get("market_opportunity"),
                        "marketing": ctx.step_results.get("marketing_strategy"),
                        "financial": ctx.step_results.get("financial_modeling"),
                        "pricing": ctx.step_results.get("pricing_analysis"),
                    },
                    "growth_target": ctx.get("growth_target"),
                    "timeline": ctx.get("timeline", "12_months"),
                },
            ),
        ]


class RevenueAnalysisWorkflow(Workflow):
    """
    Vector internal workflow for revenue analysis.

    Steps:
    1. Revenue Breakdown - Break down revenue by streams
    2. Cohort Analysis - Analyze customer cohorts
    3. Retention Metrics - Calculate retention metrics
    4. Expansion Analysis - Analyze expansion revenue
    5. Revenue Forecast - Generate revenue forecast
    """

    @property
    def name(self) -> str:
        return "revenue_analysis"

    @property
    def description(self) -> str:
        return "Vector revenue analysis workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="revenue_breakdown",
                agent="Vector",
                task_type="revenue_tracking",
                description="Break down revenue by streams and segments",
                context_builder=lambda ctx: {
                    "analysis_period": ctx.get("analysis_period", "last_quarter"),
                    "revenue_streams": ctx.get("revenue_streams", []),
                    "segmentation": ctx.get("segmentation", ["product", "region", "customer_tier"]),
                },
            ),
            WorkflowStep(
                name="cohort_analysis",
                agent="Vector",
                task_type="cohort_analysis",
                description="Analyze customer cohort performance",
                depends_on=["revenue_breakdown"],
                context_builder=lambda ctx: {
                    "revenue_data": ctx.step_results.get("revenue_breakdown"),
                    "cohort_definition": ctx.get("cohort_definition", "signup_month"),
                    "cohort_periods": ctx.get("cohort_periods", 12),
                },
            ),
            WorkflowStep(
                name="retention_metrics",
                agent="Vector",
                task_type="revenue_tracking",
                description="Calculate revenue retention metrics",
                depends_on=["cohort_analysis"],
                context_builder=lambda ctx: {
                    "cohort_data": ctx.step_results.get("cohort_analysis"),
                    "retention_types": ctx.get("retention_types", ["gross", "net", "logo"]),
                },
            ),
            WorkflowStep(
                name="expansion_analysis",
                agent="Vector",
                task_type="upsell_analysis",
                description="Analyze expansion and upsell revenue",
                depends_on=["revenue_breakdown", "retention_metrics"],
                context_builder=lambda ctx: {
                    "revenue_data": ctx.step_results.get("revenue_breakdown"),
                    "retention_data": ctx.step_results.get("retention_metrics"),
                    "expansion_types": ctx.get(
                        "expansion_types", ["upsell", "cross_sell", "expansion"]
                    ),
                },
            ),
            WorkflowStep(
                name="revenue_forecast",
                agent="Vector",
                task_type="revenue_forecasting",
                description="Generate revenue forecast",
                depends_on=["retention_metrics", "expansion_analysis"],
                context_builder=lambda ctx: {
                    "retention_data": ctx.step_results.get("retention_metrics"),
                    "expansion_data": ctx.step_results.get("expansion_analysis"),
                    "forecast_horizon": ctx.get("forecast_horizon", "12_months"),
                    "scenarios": ctx.get("scenarios", ["base", "optimistic", "pessimistic"]),
                },
            ),
        ]


class MarketingCampaignWorkflow(Workflow):
    """
    Workflow for marketing campaign execution.

    Coordinates across:
    - Echo (Echo): Campaign strategy and execution
    - Keystone (Keystone): Budget management
    - Index (Index): Analytics and targeting
    - Beacon (Beacon): Customer feedback

    Steps:
    1. Campaign Strategy - Echo defines campaign objectives and approach
    2. Audience Analysis - Index analyzes target audience data
    3. Budget Allocation - Keystone allocates campaign budget
    4. Content Creation - Echo creates campaign content
    5. Campaign Launch - Echo executes campaign
    6. Performance Analysis - Echo and Beacon analyze results
    """

    @property
    def name(self) -> str:
        return "marketing_campaign"

    @property
    def description(self) -> str:
        return "Marketing campaign planning and execution"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="campaign_strategy",
                agent="Echo",
                task_type="campaign_creation",
                description="Define campaign objectives and strategy",
                context_builder=lambda ctx: {
                    "campaign_name": ctx.get("campaign_name"),
                    "campaign_type": ctx.get("campaign_type", "awareness"),
                    "objectives": ctx.get("objectives", []),
                    "target_audience": ctx.get("target_audience", {}),
                    "channels": ctx.get("channels", []),
                },
            ),
            WorkflowStep(
                name="audience_analysis",
                agent="Index",
                task_type="descriptive_analytics",
                description="Analyze target audience data and segments",
                depends_on=["campaign_strategy"],
                context_builder=lambda ctx: {
                    "campaign_strategy": ctx.step_results.get("campaign_strategy"),
                    "target_audience": ctx.get("target_audience", {}),
                    "data_sources": ctx.get("data_sources", []),
                },
            ),
            WorkflowStep(
                name="budget_allocation",
                agent="Keystone",
                task_type="budget_planning",
                description="Allocate and optimize campaign budget",
                depends_on=["campaign_strategy", "audience_analysis"],
                context_builder=lambda ctx: {
                    "campaign_strategy": ctx.step_results.get("campaign_strategy"),
                    "audience_insights": ctx.step_results.get("audience_analysis"),
                    "total_budget": ctx.get("total_budget"),
                    "channels": ctx.get("channels", []),
                },
            ),
            WorkflowStep(
                name="content_creation",
                agent="Echo",
                task_type="content_marketing",
                description="Create campaign content and assets",
                depends_on=["campaign_strategy", "audience_analysis"],
                context_builder=lambda ctx: {
                    "campaign_strategy": ctx.step_results.get("campaign_strategy"),
                    "audience_insights": ctx.step_results.get("audience_analysis"),
                    "content_types": ctx.get("content_types", []),
                    "brand_guidelines": ctx.get("brand_guidelines", {}),
                },
            ),
            WorkflowStep(
                name="campaign_launch",
                agent="Echo",
                task_type="campaign_management",
                description="Execute and manage campaign launch",
                depends_on=["budget_allocation", "content_creation"],
                context_builder=lambda ctx: {
                    "budget_allocation": ctx.step_results.get("budget_allocation"),
                    "content": ctx.step_results.get("content_creation"),
                    "launch_date": ctx.get("launch_date"),
                    "channels": ctx.get("channels", []),
                },
            ),
            WorkflowStep(
                name="performance_analysis",
                agent="Echo",
                task_type="marketing_analytics",
                description="Analyze campaign performance and ROI",
                depends_on=["campaign_launch"],
                context_builder=lambda ctx: {
                    "campaign_data": ctx.step_results.get("campaign_launch"),
                    "success_metrics": ctx.get("success_metrics", []),
                    "budget_spent": ctx.step_results.get("budget_allocation"),
                },
            ),
        ]
