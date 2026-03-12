"""
Aggregation Workflow Definitions.

Multi-step workflows that aggregate outputs from multiple specialists,
coordinated by manager agents to synthesize cohesive results.
"""

from ag3ntwerk.orchestration.factory import (
    WorkflowDefinition,
    StepDefinition,
    param,
    step_result,
    aggregate,
)


# =============================================================================
# Keystone Aggregation Workflows
# =============================================================================

COMPREHENSIVE_COST_REVIEW = WorkflowDefinition(
    name="comprehensive_cost_review",
    description="Comprehensive cost review aggregating multiple analyses",
    category="aggregation",
    tags=("cfo", "finance", "cost"),
    steps=[
        StepDefinition(
            name="cost_accounting",
            agent="Keystone",
            task_type="cost_accounting",
            description="Perform detailed cost accounting",
            context_mapping={
                "period": param("period", "quarterly"),
                "cost_data": param("cost_data", {}),
            },
        ),
        StepDefinition(
            name="cash_flow",
            agent="Keystone",
            task_type="cash_flow_analysis",
            description="Analyze cash flow implications",
            depends_on=("cost_accounting",),
            context_mapping={
                "period": param("period", "quarterly"),
                "cost_breakdown": step_result("cost_accounting"),
            },
        ),
        StepDefinition(
            name="optimization",
            agent="Keystone",
            task_type="cost_optimization",
            description="Identify cost optimization opportunities",
            depends_on=("cost_accounting", "cash_flow"),
            context_mapping={
                "cost_accounting": step_result("cost_accounting"),
                "cash_flow": step_result("cash_flow"),
            },
        ),
    ],
)

BUDGET_PLANNING_CYCLE = WorkflowDefinition(
    name="budget_planning_cycle",
    description="Complete budget planning cycle with forecasting",
    category="aggregation",
    tags=("cfo", "finance", "budget"),
    steps=[
        StepDefinition(
            name="budget_creation",
            agent="Keystone",
            task_type="budget_creation",
            description="Create initial budget",
            context_mapping={
                "period": param("period", "annual"),
                "departments": param("departments", []),
                "constraints": param("constraints", {}),
            },
        ),
        StepDefinition(
            name="financial_modeling",
            agent="Keystone",
            task_type="financial_modeling",
            description="Build financial model for scenarios",
            depends_on=("budget_creation",),
            context_mapping={
                "budget": step_result("budget_creation"),
                "scenarios": param("scenarios", ["base", "optimistic", "pessimistic"]),
            },
        ),
        StepDefinition(
            name="rolling_forecast",
            agent="Keystone",
            task_type="rolling_forecast",
            description="Create rolling forecast",
            depends_on=("financial_modeling",),
            context_mapping={
                "budget": step_result("budget_creation"),
                "model": step_result("financial_modeling"),
                "horizon": param("forecast_horizon", "12 months"),
            },
        ),
    ],
)

# =============================================================================
# Forge Aggregation Workflows
# =============================================================================

TECHNICAL_ASSESSMENT = WorkflowDefinition(
    name="technical_assessment",
    description="Comprehensive technical assessment across domains",
    category="aggregation",
    tags=("cto", "engineering", "assessment"),
    steps=[
        StepDefinition(
            name="architecture_review",
            agent="Forge",
            task_type="architecture",
            description="Review system architecture",
            context_mapping={
                "system": param("system", ""),
                "requirements": param("requirements", []),
            },
        ),
        StepDefinition(
            name="code_quality",
            agent="Forge",
            task_type="code_analysis",
            description="Analyze code quality",
            context_mapping={
                "codebase": param("codebase", ""),
                "code": param("code", ""),
            },
        ),
        StepDefinition(
            name="security_review",
            agent="Forge",
            task_type="security_review",
            description="Review security posture",
            depends_on=("architecture_review", "code_quality"),
            context_mapping={
                "architecture": step_result("architecture_review"),
                "code_quality": step_result("code_quality"),
                "code": param("code", ""),
            },
        ),
        StepDefinition(
            name="tech_debt",
            agent="Forge",
            task_type="technical_debt",
            description="Assess technical debt",
            depends_on=("code_quality",),
            context_mapping={
                "code_analysis": step_result("code_quality"),
                "areas": param("areas", []),
            },
        ),
    ],
)

FULL_DEVOPS_CYCLE = WorkflowDefinition(
    name="full_devops_cycle",
    description="Setup complete DevOps pipeline",
    category="aggregation",
    tags=("cto", "engineering", "devops"),
    steps=[
        StepDefinition(
            name="containerization",
            agent="Forge",
            task_type="containerization",
            description="Create container configuration",
            context_mapping={
                "application": param("application", ""),
                "language": param("language", "python"),
            },
        ),
        StepDefinition(
            name="ci_cd_setup",
            agent="Forge",
            task_type="ci_cd",
            description="Setup CI/CD pipeline",
            depends_on=("containerization",),
            context_mapping={
                "containerization": step_result("containerization"),
                "platform": param("platform", "GitHub Actions"),
            },
        ),
        StepDefinition(
            name="monitoring_setup",
            agent="Forge",
            task_type="monitoring",
            description="Setup monitoring and observability",
            depends_on=("ci_cd_setup",),
            context_mapping={
                "application": param("application", ""),
                "stack": param("monitoring_stack", "Prometheus/Grafana"),
            },
        ),
    ],
)

# =============================================================================
# Echo Aggregation Workflows
# =============================================================================

FULL_CAMPAIGN = WorkflowDefinition(
    name="full_campaign",
    description="Complete campaign planning and execution",
    category="aggregation",
    tags=("cmo", "marketing", "campaign"),
    steps=[
        StepDefinition(
            name="market_research",
            agent="Echo",
            task_type="market_sizing",
            description="Research target market",
            context_mapping={
                "market": param("market", ""),
                "audience": param("target_audience", ""),
            },
        ),
        StepDefinition(
            name="campaign_strategy",
            agent="Echo",
            task_type="campaign_planning",
            description="Develop campaign strategy",
            depends_on=("market_research",),
            context_mapping={
                "market_research": step_result("market_research"),
                "objectives": param("objectives", []),
                "budget": param("budget", {}),
            },
        ),
        StepDefinition(
            name="content_creation",
            agent="Echo",
            task_type="content_creation",
            description="Create campaign content",
            depends_on=("campaign_strategy",),
            context_mapping={
                "strategy": step_result("campaign_strategy"),
                "content_type": param("content_type", "multi-channel"),
            },
        ),
        StepDefinition(
            name="digital_execution",
            agent="Echo",
            task_type="digital_campaign_execution",
            description="Execute digital campaign",
            depends_on=("content_creation",),
            context_mapping={
                "content": step_result("content_creation"),
                "channels": param("channels", []),
            },
        ),
    ],
)

BRAND_HEALTH_CHECK = WorkflowDefinition(
    name="brand_health_check",
    description="Comprehensive brand health assessment",
    category="aggregation",
    tags=("cmo", "marketing", "brand"),
    steps=[
        StepDefinition(
            name="competitive_intel",
            agent="Echo",
            task_type="competitive_intelligence",
            description="Gather competitive intelligence",
            context_mapping={
                "competitors": param("competitors", []),
                "market": param("market", ""),
            },
        ),
        StepDefinition(
            name="brand_assessment",
            agent="Echo",
            task_type="brand_health",
            description="Assess brand health metrics",
            depends_on=("competitive_intel",),
            context_mapping={
                "competitive_intel": step_result("competitive_intel"),
                "brand_metrics": param("brand_metrics", {}),
            },
        ),
        StepDefinition(
            name="positioning_review",
            agent="Echo",
            task_type="brand_positioning",
            description="Review brand positioning",
            depends_on=("brand_assessment",),
            context_mapping={
                "brand_assessment": step_result("brand_assessment"),
                "current_positioning": param("current_positioning", ""),
            },
        ),
    ],
)

# =============================================================================
# Blueprint Aggregation Workflows
# =============================================================================

FEATURE_DELIVERY = WorkflowDefinition(
    name="feature_delivery",
    description="Complete feature delivery from ideation to planning",
    category="aggregation",
    tags=("cpo", "product", "feature"),
    steps=[
        StepDefinition(
            name="market_validation",
            agent="Blueprint",
            task_type="market_analysis",
            description="Validate feature market need",
            context_mapping={
                "feature": param("feature", ""),
                "market": param("market", ""),
            },
        ),
        StepDefinition(
            name="feature_scoring",
            agent="Blueprint",
            task_type="feature_scoring",
            description="Score and prioritize feature",
            depends_on=("market_validation",),
            context_mapping={
                "feature": param("feature", ""),
                "market_validation": step_result("market_validation"),
                "framework": param("framework", "RICE"),
            },
        ),
        StepDefinition(
            name="requirements",
            agent="Blueprint",
            task_type="user_story_writing",
            description="Write user stories and requirements",
            depends_on=("feature_scoring",),
            context_mapping={
                "feature": param("feature", ""),
                "scoring": step_result("feature_scoring"),
            },
        ),
        StepDefinition(
            name="roadmap_update",
            agent="Blueprint",
            task_type="roadmap_update",
            description="Update roadmap with feature",
            depends_on=("requirements",),
            context_mapping={
                "feature": param("feature", ""),
                "requirements": step_result("requirements"),
            },
        ),
    ],
)

SPRINT_READINESS = WorkflowDefinition(
    name="sprint_readiness",
    description="Prepare sprint backlog and capacity",
    category="aggregation",
    tags=("cpo", "product", "sprint"),
    steps=[
        StepDefinition(
            name="backlog_grooming",
            agent="Blueprint",
            task_type="backlog_refinement",
            description="Refine sprint backlog",
            context_mapping={
                "backlog": param("backlog", []),
                "sprint_goal": param("sprint_goal", ""),
            },
        ),
        StepDefinition(
            name="capacity_planning",
            agent="Blueprint",
            task_type="sprint_capacity",
            description="Plan sprint capacity",
            depends_on=("backlog_grooming",),
            context_mapping={
                "groomed_backlog": step_result("backlog_grooming"),
                "team_capacity": param("team_capacity", {}),
            },
        ),
        StepDefinition(
            name="sprint_scope",
            agent="Blueprint",
            task_type="sprint_scope",
            description="Define sprint scope",
            depends_on=("capacity_planning",),
            context_mapping={
                "capacity": step_result("capacity_planning"),
                "priorities": param("priorities", []),
            },
        ),
    ],
)

# =============================================================================
# Beacon Aggregation Workflows
# =============================================================================

CUSTOMER_HEALTH_REVIEW = WorkflowDefinition(
    name="customer_health_review",
    description="Comprehensive customer health review",
    category="aggregation",
    tags=("cco", "customer", "health"),
    steps=[
        StepDefinition(
            name="health_scoring",
            agent="Beacon",
            task_type="customer_health_scoring",
            description="Calculate customer health scores",
            context_mapping={
                "customer_data": param("customer_data", {}),
                "metrics": param("health_metrics", []),
            },
        ),
        StepDefinition(
            name="churn_analysis",
            agent="Beacon",
            task_type="churn_prediction",
            description="Analyze churn risk",
            depends_on=("health_scoring",),
            context_mapping={
                "health_scores": step_result("health_scoring"),
                "customer_data": param("customer_data", {}),
            },
        ),
        StepDefinition(
            name="retention_strategy",
            agent="Beacon",
            task_type="retention_strategy",
            description="Develop retention strategies",
            depends_on=("churn_analysis",),
            context_mapping={
                "churn_analysis": step_result("churn_analysis"),
                "at_risk_customers": param("at_risk_customers", []),
            },
        ),
    ],
)

VOICE_OF_CUSTOMER = WorkflowDefinition(
    name="voice_of_customer",
    description="Comprehensive voice of customer analysis",
    category="aggregation",
    tags=("cco", "customer", "feedback"),
    steps=[
        StepDefinition(
            name="feedback_collection",
            agent="Beacon",
            task_type="feedback_collection",
            description="Collect and aggregate feedback",
            context_mapping={
                "sources": param("feedback_sources", []),
                "period": param("period", "monthly"),
            },
        ),
        StepDefinition(
            name="sentiment_analysis",
            agent="Beacon",
            task_type="sentiment_analysis",
            description="Analyze feedback sentiment",
            depends_on=("feedback_collection",),
            context_mapping={
                "feedback": step_result("feedback_collection"),
            },
        ),
        StepDefinition(
            name="nps_analysis",
            agent="Beacon",
            task_type="nps_analysis",
            description="Analyze NPS trends",
            depends_on=("feedback_collection",),
            context_mapping={
                "nps_data": param("nps_data", []),
            },
        ),
        StepDefinition(
            name="insights_synthesis",
            agent="Beacon",
            task_type="voice_of_customer",
            description="Synthesize customer insights",
            depends_on=("sentiment_analysis", "nps_analysis"),
            context_mapping={
                "sentiment": step_result("sentiment_analysis"),
                "nps": step_result("nps_analysis"),
            },
        ),
    ],
)

# =============================================================================
# Vector Aggregation Workflows
# =============================================================================

REVENUE_HEALTH_CHECK = WorkflowDefinition(
    name="revenue_health_check",
    description="Comprehensive revenue health assessment",
    category="aggregation",
    tags=("crevo", "revenue", "health"),
    steps=[
        StepDefinition(
            name="revenue_tracking",
            agent="Vector",
            task_type="revenue_tracking",
            description="Track current revenue metrics",
            context_mapping={
                "revenue_data": param("revenue_data", {}),
                "period": param("period", "monthly"),
            },
        ),
        StepDefinition(
            name="mrr_analysis",
            agent="Vector",
            task_type="mrr_analysis",
            description="Analyze MRR movements",
            depends_on=("revenue_tracking",),
            context_mapping={
                "mrr_data": param("mrr_data", {}),
                "revenue_tracking": step_result("revenue_tracking"),
            },
        ),
        StepDefinition(
            name="churn_analysis",
            agent="Vector",
            task_type="churn_analysis",
            description="Analyze churn patterns",
            depends_on=("mrr_analysis",),
            context_mapping={
                "churn_data": param("churn_data", {}),
                "mrr_analysis": step_result("mrr_analysis"),
            },
        ),
        StepDefinition(
            name="revenue_forecasting",
            agent="Vector",
            task_type="revenue_forecasting",
            description="Create revenue forecast",
            depends_on=("revenue_tracking", "churn_analysis"),
            context_mapping={
                "historical_data": step_result("revenue_tracking"),
                "churn_analysis": step_result("churn_analysis"),
                "forecast_period": param("forecast_period", "quarter"),
            },
        ),
    ],
)

GROWTH_ANALYSIS = WorkflowDefinition(
    name="growth_analysis",
    description="Comprehensive growth analysis with conversion and adoption",
    category="aggregation",
    tags=("crevo", "growth", "analysis"),
    steps=[
        StepDefinition(
            name="conversion_analysis",
            agent="Vector",
            task_type="conversion_analysis",
            description="Analyze conversion funnel",
            context_mapping={
                "funnel_data": param("funnel_data", {}),
                "funnel_type": param("funnel_type", "signup_to_paid"),
            },
        ),
        StepDefinition(
            name="feature_adoption",
            agent="Vector",
            task_type="feature_adoption_metrics",
            description="Track feature adoption",
            context_mapping={
                "adoption_data": param("adoption_data", {}),
                "features": param("features", []),
            },
        ),
        StepDefinition(
            name="cohort_analysis",
            agent="Vector",
            task_type="cohort_analysis",
            description="Analyze customer cohorts",
            depends_on=("conversion_analysis", "feature_adoption"),
            context_mapping={
                "cohort_data": param("cohort_data", {}),
                "conversion_analysis": step_result("conversion_analysis"),
                "feature_adoption": step_result("feature_adoption"),
            },
        ),
        StepDefinition(
            name="growth_experiment",
            agent="Vector",
            task_type="growth_experiment_design",
            description="Design growth experiments",
            depends_on=("conversion_analysis", "cohort_analysis"),
            context_mapping={
                "conversion_analysis": step_result("conversion_analysis"),
                "cohort_analysis": step_result("cohort_analysis"),
                "hypothesis": param("hypothesis", ""),
            },
        ),
    ],
)

# =============================================================================
# Sentinel Aggregation Workflows
# =============================================================================

IT_GOVERNANCE_REVIEW = WorkflowDefinition(
    name="it_governance_review",
    description="Comprehensive IT governance and compliance review",
    category="aggregation",
    tags=("cio", "governance", "compliance"),
    steps=[
        StepDefinition(
            name="data_governance",
            agent="Sentinel",
            task_type="data_governance",
            description="Assess data governance practices",
            context_mapping={
                "data_domain": param("data_domain", ""),
                "compliance_requirements": param("compliance_requirements", []),
            },
        ),
        StepDefinition(
            name="security_assessment",
            agent="Sentinel",
            task_type="security_assessment",
            description="Perform security assessment",
            depends_on=("data_governance",),
            context_mapping={
                "scope": param("scope", "infrastructure"),
                "data_governance": step_result("data_governance"),
            },
        ),
        StepDefinition(
            name="systems_analysis",
            agent="Sentinel",
            task_type="systems_analysis",
            description="Analyze IT systems",
            depends_on=("data_governance",),
            context_mapping={
                "system": param("system", ""),
                "data_governance": step_result("data_governance"),
            },
        ),
        StepDefinition(
            name="governance_synthesis",
            agent="Sentinel",
            task_type="data_verification",
            description="Synthesize governance findings",
            depends_on=("security_assessment", "systems_analysis"),
            context_mapping={
                "security_assessment": step_result("security_assessment"),
                "systems_analysis": step_result("systems_analysis"),
            },
        ),
    ],
)

KNOWLEDGE_MANAGEMENT = WorkflowDefinition(
    name="knowledge_management",
    description="Extract, organize, and verify knowledge",
    category="aggregation",
    tags=("cio", "knowledge", "management"),
    steps=[
        StepDefinition(
            name="knowledge_extraction",
            agent="Sentinel",
            task_type="knowledge_extraction",
            description="Extract knowledge from sources",
            context_mapping={
                "source_documents": param("source_documents", []),
                "extraction_type": param("extraction_type", "entities"),
            },
        ),
        StepDefinition(
            name="knowledge_organization",
            agent="Sentinel",
            task_type="knowledge_curation",
            description="Organize extracted knowledge",
            depends_on=("knowledge_extraction",),
            context_mapping={
                "extracted_knowledge": step_result("knowledge_extraction"),
                "taxonomy": param("taxonomy", {}),
            },
        ),
        StepDefinition(
            name="verification",
            agent="Sentinel",
            task_type="data_verification",
            description="Verify knowledge accuracy",
            depends_on=("knowledge_organization",),
            context_mapping={
                "knowledge": step_result("knowledge_organization"),
                "verification_rules": param("verification_rules", []),
            },
        ),
    ],
)

# =============================================================================
# Axiom Aggregation Workflows
# =============================================================================

COMPREHENSIVE_RESEARCH = WorkflowDefinition(
    name="comprehensive_research",
    description="End-to-end research from literature review to analysis",
    category="aggregation",
    tags=("cro", "research", "comprehensive"),
    steps=[
        StepDefinition(
            name="literature_review",
            agent="Axiom",
            task_type="literature_review",
            description="Conduct literature review",
            context_mapping={
                "field": param("field", ""),
                "timeframe": param("timeframe", "recent"),
            },
        ),
        StepDefinition(
            name="experiment_design",
            agent="Axiom",
            task_type="experiment_design",
            description="Design research methodology",
            depends_on=("literature_review",),
            context_mapping={
                "objective": param("objective", ""),
                "literature_review": step_result("literature_review"),
            },
        ),
        StepDefinition(
            name="data_analysis",
            agent="Axiom",
            task_type="data_analysis",
            description="Analyze research data",
            depends_on=("experiment_design",),
            context_mapping={
                "data_description": param("data_description", ""),
                "experiment_design": step_result("experiment_design"),
            },
        ),
        StepDefinition(
            name="findings_synthesis",
            agent="Axiom",
            task_type="meta_analysis",
            description="Synthesize research findings",
            depends_on=("data_analysis",),
            context_mapping={
                "literature_review": step_result("literature_review"),
                "data_analysis": step_result("data_analysis"),
            },
        ),
    ],
)

FEASIBILITY_ASSESSMENT = WorkflowDefinition(
    name="feasibility_assessment",
    description="Multi-dimensional feasibility assessment",
    category="aggregation",
    tags=("cro", "research", "feasibility"),
    steps=[
        StepDefinition(
            name="technology_assessment",
            agent="Axiom",
            task_type="technology_assessment",
            description="Assess technical feasibility",
            context_mapping={
                "technology": param("technology", ""),
                "use_case": param("use_case", ""),
            },
        ),
        StepDefinition(
            name="impact_analysis",
            agent="Axiom",
            task_type="impact_analysis",
            description="Analyze potential impact",
            depends_on=("technology_assessment",),
            context_mapping={
                "change": param("proposal", ""),
                "technology_assessment": step_result("technology_assessment"),
            },
        ),
        StepDefinition(
            name="feasibility_study",
            agent="Axiom",
            task_type="feasibility_study",
            description="Conduct overall feasibility study",
            depends_on=("technology_assessment", "impact_analysis"),
            context_mapping={
                "proposal": param("proposal", ""),
                "technology_assessment": step_result("technology_assessment"),
                "impact_analysis": step_result("impact_analysis"),
            },
        ),
    ],
)

# =============================================================================
# Compass Aggregation Workflows
# =============================================================================

STRATEGIC_ANALYSIS = WorkflowDefinition(
    name="strategic_analysis",
    description="Comprehensive strategic analysis with market and competitive insights",
    category="aggregation",
    tags=("cso", "strategy", "analysis"),
    steps=[
        StepDefinition(
            name="market_analysis",
            agent="Compass",
            task_type="market_analysis",
            description="Analyze target market",
            context_mapping={
                "market": param("market", ""),
                "scope": param("scope", "comprehensive"),
            },
        ),
        StepDefinition(
            name="competitive_analysis",
            agent="Compass",
            task_type="competitive_analysis",
            description="Analyze competitive landscape",
            depends_on=("market_analysis",),
            context_mapping={
                "industry": param("industry", ""),
                "market_analysis": step_result("market_analysis"),
            },
        ),
        StepDefinition(
            name="swot_analysis",
            agent="Compass",
            task_type="swot_analysis",
            description="Perform SWOT analysis",
            depends_on=("market_analysis", "competitive_analysis"),
            context_mapping={
                "subject": param("subject", "organization"),
                "market_analysis": step_result("market_analysis"),
                "competitive_analysis": step_result("competitive_analysis"),
            },
        ),
        StepDefinition(
            name="strategic_plan",
            agent="Compass",
            task_type="strategic_planning",
            description="Develop strategic plan",
            depends_on=("swot_analysis",),
            context_mapping={
                "swot_analysis": step_result("swot_analysis"),
                "timeframe": param("timeframe", "1 year"),
            },
        ),
    ],
)

GTM_PLANNING = WorkflowDefinition(
    name="gtm_planning",
    description="Develop comprehensive go-to-market strategy",
    category="aggregation",
    tags=("cso", "strategy", "gtm"),
    steps=[
        StepDefinition(
            name="market_research",
            agent="Compass",
            task_type="market_analysis",
            description="Research target market",
            context_mapping={
                "market": param("market", ""),
                "product": param("product", ""),
            },
        ),
        StepDefinition(
            name="value_proposition",
            agent="Compass",
            task_type="value_proposition",
            description="Define value proposition",
            depends_on=("market_research",),
            context_mapping={
                "segment": param("segment", ""),
                "product": param("product", ""),
                "market_research": step_result("market_research"),
            },
        ),
        StepDefinition(
            name="content_strategy",
            agent="Compass",
            task_type="content_strategy",
            description="Develop content strategy",
            depends_on=("value_proposition",),
            context_mapping={
                "audience": param("audience", ""),
                "value_proposition": step_result("value_proposition"),
            },
        ),
        StepDefinition(
            name="gtm_plan",
            agent="Compass",
            task_type="go_to_market",
            description="Create go-to-market plan",
            depends_on=("market_research", "value_proposition", "content_strategy"),
            context_mapping={
                "product": param("product", ""),
                "market": param("market", ""),
                "market_research": step_result("market_research"),
                "value_proposition": step_result("value_proposition"),
                "content_strategy": step_result("content_strategy"),
            },
        ),
    ],
)

# =============================================================================
# Nexus Aggregation Workflows
# =============================================================================

OPERATIONS_REVIEW = WorkflowDefinition(
    name="operations_review",
    description="Comprehensive operations review with metrics and recommendations",
    category="aggregation",
    tags=("coo", "operations", "review"),
    steps=[
        StepDefinition(
            name="performance_analysis",
            agent="Nexus",
            task_type="performance_analysis",
            description="Analyze cross-functional performance",
            context_mapping={
                "metrics": param("metrics", {}),
                "period": param("period", "current"),
            },
        ),
        StepDefinition(
            name="bottleneck_analysis",
            agent="Nexus",
            task_type="efficiency_analysis",
            description="Identify operational bottlenecks",
            depends_on=("performance_analysis",),
            context_mapping={
                "performance_analysis": step_result("performance_analysis"),
                "scope": param("scope", "all"),
            },
        ),
        StepDefinition(
            name="process_review",
            agent="Nexus",
            task_type="process_optimization",
            description="Review and optimize processes",
            depends_on=("bottleneck_analysis",),
            context_mapping={
                "bottlenecks": step_result("bottleneck_analysis"),
                "goals": param("goals", ["improve efficiency"]),
            },
        ),
        StepDefinition(
            name="operations_report",
            agent="Nexus",
            task_type="reporting",
            description="Generate operations report",
            depends_on=("performance_analysis", "bottleneck_analysis", "process_review"),
            context_mapping={
                "data": aggregate(
                    performance="performance_analysis",
                    bottlenecks="bottleneck_analysis",
                    process_review="process_review",
                ),
                "report_type": "comprehensive",
                "audience": "agent",
            },
        ),
    ],
)

CROSS_FUNCTIONAL_COORDINATION = WorkflowDefinition(
    name="cross_functional_coordination",
    description="Coordinate cross-functional initiative across agents",
    category="aggregation",
    tags=("coo", "operations", "coordination"),
    steps=[
        StepDefinition(
            name="task_analysis",
            agent="Nexus",
            task_type="task_classification",
            description="Analyze initiative requirements",
            context_mapping={
                "task_description": param("initiative", ""),
                "context": param("context", {}),
            },
        ),
        StepDefinition(
            name="workflow_design",
            agent="Nexus",
            task_type="workflow_creation",
            description="Design coordination workflow",
            depends_on=("task_analysis",),
            context_mapping={
                "goal": param("initiative", ""),
                "agents": param("teams", []),
                "task_analysis": step_result("task_analysis"),
            },
        ),
        StepDefinition(
            name="resource_allocation",
            agent="Nexus",
            task_type="resource_allocation",
            description="Plan resource allocation",
            depends_on=("workflow_design",),
            context_mapping={
                "project": param("initiative", ""),
                "resources": param("resources", {}),
                "workflow": step_result("workflow_design"),
            },
        ),
        StepDefinition(
            name="coordination_plan",
            agent="Nexus",
            task_type="cross_functional_coordination",
            description="Finalize coordination plan",
            depends_on=("workflow_design", "resource_allocation"),
            context_mapping={
                "teams": param("teams", []),
                "workflow": step_result("workflow_design"),
                "resources": step_result("resource_allocation"),
            },
        ),
    ],
)

# =============================================================================
# Accord Aggregation Workflows (Compliance)
# =============================================================================

COMPLIANCE_PROGRAM_REVIEW = WorkflowDefinition(
    name="compliance_program_review",
    description="Comprehensive compliance program review with gap analysis and remediation",
    category="aggregation",
    tags=("ccomo", "compliance", "program"),
    steps=[
        StepDefinition(
            name="compliance_assessment",
            agent="Accord",
            task_type="compliance_assessment",
            description="Assess current compliance posture",
            context_mapping={
                "framework": param("framework", "general"),
                "scope": param("scope", "enterprise"),
            },
        ),
        StepDefinition(
            name="gap_analysis",
            agent="Accord",
            task_type="gap_analysis",
            description="Identify compliance gaps",
            depends_on=("compliance_assessment",),
            context_mapping={
                "assessment": step_result("compliance_assessment"),
                "requirements": param("requirements", []),
            },
        ),
        StepDefinition(
            name="policy_review",
            agent="Accord",
            task_type="policy_review",
            description="Review relevant policies",
            depends_on=("gap_analysis",),
            context_mapping={
                "gaps": step_result("gap_analysis"),
                "policies": param("policies", []),
            },
        ),
        StepDefinition(
            name="remediation_plan",
            agent="Accord",
            task_type="compliance_remediation",
            description="Develop remediation plan",
            depends_on=("gap_analysis", "policy_review"),
            context_mapping={
                "gaps": step_result("gap_analysis"),
                "policy_findings": step_result("policy_review"),
                "priority": param("priority", "medium"),
            },
        ),
    ],
)

AUDIT_READINESS = WorkflowDefinition(
    name="audit_readiness",
    description="Prepare for audit with evidence collection and gap remediation",
    category="aggregation",
    tags=("ccomo", "compliance", "audit"),
    steps=[
        StepDefinition(
            name="scope_review",
            agent="Accord",
            task_type="audit_scoping",
            description="Review audit scope and requirements",
            context_mapping={
                "audit_type": param("audit_type", ""),
                "framework": param("framework", ""),
            },
        ),
        StepDefinition(
            name="evidence_collection",
            agent="Accord",
            task_type="evidence_gathering",
            description="Collect audit evidence",
            depends_on=("scope_review",),
            context_mapping={
                "scope": step_result("scope_review"),
                "controls": param("controls", []),
            },
        ),
        StepDefinition(
            name="readiness_assessment",
            agent="Accord",
            task_type="audit_preparation",
            description="Assess audit readiness",
            depends_on=("evidence_collection",),
            context_mapping={
                "evidence": step_result("evidence_collection"),
                "framework": param("framework", ""),
            },
        ),
    ],
)

# =============================================================================
# Aegis Aggregation Workflows (Risk)
# =============================================================================

ENTERPRISE_RISK_ASSESSMENT = WorkflowDefinition(
    name="enterprise_risk_assessment",
    description="Comprehensive enterprise risk assessment with scoring and mitigation",
    category="aggregation",
    tags=("crio", "risk", "enterprise"),
    steps=[
        StepDefinition(
            name="risk_identification",
            agent="Aegis",
            task_type="risk_identification",
            description="Identify enterprise risks",
            context_mapping={
                "scope": param("scope", "enterprise"),
                "categories": param("categories", []),
            },
        ),
        StepDefinition(
            name="risk_scoring",
            agent="Aegis",
            task_type="risk_scoring",
            description="Score and prioritize risks",
            depends_on=("risk_identification",),
            context_mapping={
                "risks": step_result("risk_identification"),
                "methodology": param("methodology", "5x5"),
            },
        ),
        StepDefinition(
            name="control_assessment",
            agent="Aegis",
            task_type="control_assessment",
            description="Assess existing controls",
            depends_on=("risk_scoring",),
            context_mapping={
                "risks": step_result("risk_scoring"),
                "controls": param("controls", []),
            },
        ),
        StepDefinition(
            name="mitigation_planning",
            agent="Aegis",
            task_type="mitigation_planning",
            description="Develop mitigation strategies",
            depends_on=("risk_scoring", "control_assessment"),
            context_mapping={
                "risks": step_result("risk_scoring"),
                "controls": step_result("control_assessment"),
                "appetite": param("risk_appetite", {}),
            },
        ),
    ],
)

BCP_DR_PLANNING = WorkflowDefinition(
    name="bcp_dr_planning",
    description="Business continuity and disaster recovery planning",
    category="aggregation",
    tags=("crio", "risk", "bcp"),
    steps=[
        StepDefinition(
            name="impact_analysis",
            agent="Aegis",
            task_type="impact_analysis",
            description="Conduct business impact analysis",
            context_mapping={
                "processes": param("processes", []),
                "systems": param("systems", []),
            },
        ),
        StepDefinition(
            name="recovery_planning",
            agent="Aegis",
            task_type="recovery_planning",
            description="Develop recovery strategies",
            depends_on=("impact_analysis",),
            context_mapping={
                "impact": step_result("impact_analysis"),
                "rto_rpo": param("rto_rpo", {}),
            },
        ),
        StepDefinition(
            name="bcp_development",
            agent="Aegis",
            task_type="bcp_planning",
            description="Develop business continuity plan",
            depends_on=("impact_analysis", "recovery_planning"),
            context_mapping={
                "impact": step_result("impact_analysis"),
                "recovery": step_result("recovery_planning"),
            },
        ),
    ],
)

# =============================================================================
# Citadel Aggregation Workflows (Security)
# =============================================================================

SECURITY_POSTURE_ASSESSMENT = WorkflowDefinition(
    name="security_posture_assessment",
    description="Comprehensive security posture assessment",
    category="aggregation",
    tags=("cseco", "security", "posture"),
    steps=[
        StepDefinition(
            name="vulnerability_scan",
            agent="Citadel",
            task_type="vulnerability_assessment",
            description="Scan for vulnerabilities",
            context_mapping={
                "scope": param("scope", ""),
                "targets": param("targets", []),
            },
        ),
        StepDefinition(
            name="threat_assessment",
            agent="Citadel",
            task_type="threat_assessment",
            description="Assess threat landscape",
            context_mapping={
                "environment": param("environment", ""),
                "threat_intel": param("threat_intel", {}),
            },
        ),
        StepDefinition(
            name="risk_analysis",
            agent="Citadel",
            task_type="security_risk_analysis",
            description="Analyze security risks",
            depends_on=("vulnerability_scan", "threat_assessment"),
            context_mapping={
                "vulnerabilities": step_result("vulnerability_scan"),
                "threats": step_result("threat_assessment"),
            },
        ),
        StepDefinition(
            name="remediation_recommendations",
            agent="Citadel",
            task_type="security_remediation",
            description="Develop remediation plan",
            depends_on=("risk_analysis",),
            context_mapping={
                "risks": step_result("risk_analysis"),
                "priority": param("priority", "critical_first"),
            },
        ),
    ],
)

SECURITY_INCIDENT_HANDLING = WorkflowDefinition(
    name="security_incident_handling",
    description="End-to-end security incident response",
    category="aggregation",
    tags=("cseco", "security", "incident"),
    steps=[
        StepDefinition(
            name="triage",
            agent="Citadel",
            task_type="incident_triage",
            description="Triage the security incident",
            context_mapping={
                "incident": param("incident", {}),
                "indicators": param("indicators", []),
            },
        ),
        StepDefinition(
            name="investigation",
            agent="Citadel",
            task_type="incident_investigation",
            description="Investigate incident details",
            depends_on=("triage",),
            context_mapping={
                "triage_results": step_result("triage"),
                "scope": param("scope", {}),
            },
        ),
        StepDefinition(
            name="containment",
            agent="Citadel",
            task_type="incident_containment",
            description="Contain the incident",
            depends_on=("investigation",),
            context_mapping={
                "findings": step_result("investigation"),
                "affected_systems": param("affected_systems", []),
            },
        ),
        StepDefinition(
            name="lessons_learned",
            agent="Citadel",
            task_type="incident_review",
            description="Document lessons learned",
            depends_on=("containment",),
            context_mapping={
                "incident": param("incident", {}),
                "response": step_result("containment"),
            },
        ),
    ],
)

# =============================================================================
# Foundry Aggregation Workflows (Engineering)
# =============================================================================

RELEASE_CYCLE = WorkflowDefinition(
    name="release_cycle",
    description="Complete release cycle from planning to deployment",
    category="aggregation",
    tags=("cengo", "engineering", "release"),
    steps=[
        StepDefinition(
            name="sprint_planning",
            agent="Foundry",
            task_type="sprint_planning",
            description="Plan sprint deliverables",
            context_mapping={
                "backlog": param("backlog", []),
                "capacity": param("capacity", {}),
            },
        ),
        StepDefinition(
            name="quality_gate",
            agent="Foundry",
            task_type="qa_testing",
            description="Execute QA testing",
            depends_on=("sprint_planning",),
            context_mapping={
                "features": param("features", []),
                "criteria": param("acceptance_criteria", []),
            },
        ),
        StepDefinition(
            name="release_preparation",
            agent="Foundry",
            task_type="release_preparation",
            description="Prepare release artifacts",
            depends_on=("quality_gate",),
            context_mapping={
                "qa_results": step_result("quality_gate"),
                "version": param("version", ""),
            },
        ),
        StepDefinition(
            name="deployment",
            agent="Foundry",
            task_type="deployment",
            description="Deploy to target environment",
            depends_on=("release_preparation",),
            context_mapping={
                "artifacts": step_result("release_preparation"),
                "environment": param("environment", "production"),
            },
        ),
    ],
)

ENGINEERING_METRICS = WorkflowDefinition(
    name="engineering_metrics",
    description="Comprehensive engineering metrics collection and analysis",
    category="aggregation",
    tags=("cengo", "engineering", "metrics"),
    steps=[
        StepDefinition(
            name="metrics_collection",
            agent="Foundry",
            task_type="metrics_collection",
            description="Collect engineering metrics",
            context_mapping={
                "period": param("period", "sprint"),
                "metrics": param("metrics", ["velocity", "quality", "throughput"]),
            },
        ),
        StepDefinition(
            name="quality_analysis",
            agent="Foundry",
            task_type="quality_analysis",
            description="Analyze code quality metrics",
            depends_on=("metrics_collection",),
            context_mapping={
                "data": step_result("metrics_collection"),
                "thresholds": param("thresholds", {}),
            },
        ),
        StepDefinition(
            name="improvement_recommendations",
            agent="Foundry",
            task_type="process_improvement",
            description="Generate improvement recommendations",
            depends_on=("metrics_collection", "quality_analysis"),
            context_mapping={
                "metrics": step_result("metrics_collection"),
                "quality": step_result("quality_analysis"),
            },
        ),
    ],
)


# =============================================================================
# All Definitions Export
# =============================================================================

ALL_DEFINITIONS = [
    # Keystone
    COMPREHENSIVE_COST_REVIEW,
    BUDGET_PLANNING_CYCLE,
    # Forge
    TECHNICAL_ASSESSMENT,
    FULL_DEVOPS_CYCLE,
    # Echo
    FULL_CAMPAIGN,
    BRAND_HEALTH_CHECK,
    # Blueprint
    FEATURE_DELIVERY,
    SPRINT_READINESS,
    # Beacon
    CUSTOMER_HEALTH_REVIEW,
    VOICE_OF_CUSTOMER,
    # Vector
    REVENUE_HEALTH_CHECK,
    GROWTH_ANALYSIS,
    # Sentinel
    IT_GOVERNANCE_REVIEW,
    KNOWLEDGE_MANAGEMENT,
    # Axiom
    COMPREHENSIVE_RESEARCH,
    FEASIBILITY_ASSESSMENT,
    # Compass
    STRATEGIC_ANALYSIS,
    GTM_PLANNING,
    # Nexus
    OPERATIONS_REVIEW,
    CROSS_FUNCTIONAL_COORDINATION,
    # Accord
    COMPLIANCE_PROGRAM_REVIEW,
    AUDIT_READINESS,
    # Aegis
    ENTERPRISE_RISK_ASSESSMENT,
    BCP_DR_PLANNING,
    # Citadel
    SECURITY_POSTURE_ASSESSMENT,
    SECURITY_INCIDENT_HANDLING,
    # Foundry
    RELEASE_CYCLE,
    ENGINEERING_METRICS,
]
