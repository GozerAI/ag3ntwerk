"""
Specialist Workflow Definitions.

Single-step focused workflows designed to leverage specialist agents.
Each workflow represents a single, well-defined task.
"""

from ag3ntwerk.orchestration.factory import (
    WorkflowDefinition,
    StepDefinition,
    param,
)


# =============================================================================
# Keystone Specialist Workflows
# =============================================================================

FINANCIAL_MODELING = WorkflowDefinition(
    name="financial_modeling",
    description="Create financial models and projections",
    category="specialist",
    tags=("cfo", "finance", "modeling"),
    steps=[
        StepDefinition(
            name="model",
            agent="Keystone",
            task_type="financial_modeling",
            description="Build financial model with projections",
            context_mapping={
                "model_type": param("model_type", "dcf"),
                "time_horizon": param("time_horizon", "5 years"),
                "assumptions": param("assumptions", {}),
                "data": param("financial_data", {}),
            },
        ),
    ],
)

COST_ALLOCATION = WorkflowDefinition(
    name="cost_allocation",
    description="Analyze and allocate costs across departments",
    category="specialist",
    tags=("cfo", "finance", "cost"),
    steps=[
        StepDefinition(
            name="allocate",
            agent="Keystone",
            task_type="cost_allocation",
            description="Allocate costs to departments/projects",
            context_mapping={
                "cost_data": param("cost_data", {}),
                "allocation_method": param("allocation_method", "activity_based"),
                "departments": param("departments", []),
            },
        ),
    ],
)

INVESTMENT_ANALYSIS = WorkflowDefinition(
    name="investment_analysis",
    description="Evaluate investment opportunities with ROI analysis",
    category="specialist",
    tags=("cfo", "finance", "investment"),
    steps=[
        StepDefinition(
            name="evaluate",
            agent="Keystone",
            task_type="investment_evaluation",
            description="Evaluate investment with NPV, IRR, payback",
            context_mapping={
                "investment": param("investment", {}),
                "cash_flows": param("cash_flows", []),
                "discount_rate": param("discount_rate", 0.1),
            },
        ),
    ],
)

# =============================================================================
# Forge Specialist Workflows
# =============================================================================

CODE_REVIEW = WorkflowDefinition(
    name="code_review",
    description="Perform comprehensive code review",
    category="specialist",
    tags=("cto", "engineering", "quality"),
    steps=[
        StepDefinition(
            name="review",
            agent="Forge",
            task_type="code_review",
            description="Review code for quality, security, and best practices",
            context_mapping={
                "code": param("code", ""),
                "file": param("file_path", ""),
                "language": param("language", "python"),
            },
        ),
    ],
)

BUG_FIX = WorkflowDefinition(
    name="bug_fix",
    description="Analyze and fix bugs in code",
    category="specialist",
    tags=("cto", "engineering", "bugfix"),
    steps=[
        StepDefinition(
            name="fix",
            agent="Forge",
            task_type="bug_fix",
            description="Diagnose and fix the bug",
            context_mapping={
                "code": param("code", ""),
                "error": param("error_message", ""),
                "symptoms": param("symptoms", ""),
            },
        ),
    ],
)

TEST_GENERATION = WorkflowDefinition(
    name="test_generation",
    description="Generate comprehensive tests for code",
    category="specialist",
    tags=("cto", "engineering", "testing"),
    steps=[
        StepDefinition(
            name="generate",
            agent="Forge",
            task_type="test_creation",
            description="Generate unit and integration tests",
            context_mapping={
                "code": param("code", ""),
                "test_type": param("test_type", "unit"),
                "framework": param("framework", "pytest"),
            },
        ),
    ],
)

DEPLOYMENT_PLANNING = WorkflowDefinition(
    name="deployment_planning",
    description="Plan deployment strategy and configuration",
    category="specialist",
    tags=("cto", "engineering", "deployment"),
    steps=[
        StepDefinition(
            name="plan",
            agent="Forge",
            task_type="deployment",
            description="Create deployment plan with rollback strategy",
            context_mapping={
                "application": param("application", ""),
                "environment": param("environment", "production"),
                "strategy": param("strategy", "rolling"),
            },
        ),
    ],
)

# =============================================================================
# Echo Specialist Workflows
# =============================================================================

CONTENT_CREATION = WorkflowDefinition(
    name="content_creation",
    description="Create marketing content",
    category="specialist",
    tags=("cmo", "marketing", "content"),
    steps=[
        StepDefinition(
            name="create",
            agent="Echo",
            task_type="content_creation",
            description="Create marketing content asset",
            context_mapping={
                "content_type": param("content_type", "blog"),
                "topic": param("topic", ""),
                "audience": param("audience", ""),
                "tone": param("tone", "professional"),
            },
        ),
    ],
)

SEO_ANALYSIS = WorkflowDefinition(
    name="seo_analysis",
    description="Analyze and optimize for search engines",
    category="specialist",
    tags=("cmo", "marketing", "seo"),
    steps=[
        StepDefinition(
            name="analyze",
            agent="Echo",
            task_type="keyword_research",
            description="Perform keyword research and SEO analysis",
            context_mapping={
                "keywords": param("keywords", []),
                "url": param("url", ""),
                "competitors": param("competitors", []),
            },
        ),
    ],
)

LEAD_GENERATION = WorkflowDefinition(
    name="lead_generation",
    description="Create lead generation strategy",
    category="specialist",
    tags=("cmo", "marketing", "leads"),
    steps=[
        StepDefinition(
            name="generate",
            agent="Echo",
            task_type="lead_generation",
            description="Create lead generation plan",
            context_mapping={
                "target_audience": param("target_audience", ""),
                "channels": param("channels", []),
                "goals": param("goals", {}),
            },
        ),
    ],
)

# =============================================================================
# Blueprint Specialist Workflows
# =============================================================================

USER_STORY_CREATION = WorkflowDefinition(
    name="user_story_creation",
    description="Create user stories with acceptance criteria",
    category="specialist",
    tags=("cpo", "product", "agile"),
    steps=[
        StepDefinition(
            name="create",
            agent="Blueprint",
            task_type="user_story_writing",
            description="Write user stories with acceptance criteria",
            context_mapping={
                "feature": param("feature", ""),
                "persona": param("persona", ""),
                "goal": param("goal", ""),
            },
        ),
    ],
)

FEATURE_SCORING = WorkflowDefinition(
    name="feature_scoring",
    description="Score and prioritize features",
    category="specialist",
    tags=("cpo", "product", "prioritization"),
    steps=[
        StepDefinition(
            name="score",
            agent="Blueprint",
            task_type="feature_scoring",
            description="Score features using RICE or similar framework",
            context_mapping={
                "features": param("features", []),
                "framework": param("framework", "RICE"),
                "criteria": param("criteria", {}),
            },
        ),
    ],
)

BACKLOG_REFINEMENT = WorkflowDefinition(
    name="backlog_refinement",
    description="Refine and groom product backlog",
    category="specialist",
    tags=("cpo", "product", "agile"),
    steps=[
        StepDefinition(
            name="refine",
            agent="Blueprint",
            task_type="backlog_refinement",
            description="Refine backlog items",
            context_mapping={
                "backlog": param("backlog", []),
                "sprint_goal": param("sprint_goal", ""),
            },
        ),
    ],
)

# =============================================================================
# Beacon Specialist Workflows
# =============================================================================

FEEDBACK_ANALYSIS = WorkflowDefinition(
    name="feedback_analysis",
    description="Analyze customer feedback",
    category="specialist",
    tags=("cco", "customer", "feedback"),
    steps=[
        StepDefinition(
            name="analyze",
            agent="Beacon",
            task_type="feedback_analysis",
            description="Analyze and categorize customer feedback",
            context_mapping={
                "feedback_data": param("feedback_data", []),
                "period": param("period", "monthly"),
            },
        ),
    ],
)

CHURN_PREDICTION = WorkflowDefinition(
    name="churn_prediction",
    description="Predict customer churn risk",
    category="specialist",
    tags=("cco", "customer", "churn"),
    steps=[
        StepDefinition(
            name="predict",
            agent="Beacon",
            task_type="churn_prediction",
            description="Analyze churn risk factors",
            context_mapping={
                "customer_data": param("customer_data", {}),
                "health_scores": param("health_scores", {}),
            },
        ),
    ],
)

NPS_ANALYSIS = WorkflowDefinition(
    name="nps_analysis",
    description="Analyze Net Promoter Score data",
    category="specialist",
    tags=("cco", "customer", "nps"),
    steps=[
        StepDefinition(
            name="analyze",
            agent="Beacon",
            task_type="nps_calculation",
            description="Calculate and analyze NPS",
            context_mapping={
                "nps_responses": param("nps_responses", []),
                "segment": param("segment", "all"),
            },
        ),
    ],
)

TICKET_TRIAGE = WorkflowDefinition(
    name="ticket_triage",
    description="Triage and classify support tickets",
    category="specialist",
    tags=("cco", "customer", "support"),
    steps=[
        StepDefinition(
            name="triage",
            agent="Beacon",
            task_type="ticket_triage",
            description="Classify and prioritize tickets",
            context_mapping={
                "tickets": param("tickets", []),
            },
        ),
    ],
)

# =============================================================================
# Index Specialist Workflows
# =============================================================================

DATA_QUALITY_CHECK = WorkflowDefinition(
    name="data_quality_check",
    description="Check data quality and identify issues",
    category="specialist",
    tags=("cdo", "data", "quality"),
    steps=[
        StepDefinition(
            name="check",
            agent="Index",
            task_type="data_quality_check",
            description="Perform data quality assessment",
            context_mapping={
                "data_source": param("data_source", ""),
                "rules": param("quality_rules", []),
            },
        ),
    ],
)

SCHEMA_VALIDATION = WorkflowDefinition(
    name="schema_validation",
    description="Validate data schema compliance",
    category="specialist",
    tags=("cdo", "data", "schema"),
    steps=[
        StepDefinition(
            name="validate",
            agent="Index",
            task_type="schema_validation",
            description="Validate data against schema",
            context_mapping={
                "schema": param("schema", {}),
                "data": param("data", {}),
            },
        ),
    ],
)

# =============================================================================
# Vector Specialist Workflows
# =============================================================================

REVENUE_TRACKING = WorkflowDefinition(
    name="revenue_tracking",
    description="Track and analyze revenue performance",
    category="specialist",
    tags=("crevo", "revenue", "tracking"),
    steps=[
        StepDefinition(
            name="track",
            agent="Vector",
            task_type="revenue_tracking",
            description="Track revenue metrics and performance",
            context_mapping={
                "revenue_data": param("revenue_data", {}),
                "period": param("period", "monthly"),
                "product_id": param("product_id", ""),
            },
        ),
    ],
)

CHURN_ANALYSIS = WorkflowDefinition(
    name="churn_analysis",
    description="Analyze customer and revenue churn",
    category="specialist",
    tags=("crevo", "revenue", "churn"),
    steps=[
        StepDefinition(
            name="analyze",
            agent="Vector",
            task_type="churn_analysis",
            description="Analyze churn patterns and drivers",
            context_mapping={
                "churn_data": param("churn_data", {}),
                "period": param("period", "quarterly"),
            },
        ),
    ],
)

COHORT_ANALYSIS = WorkflowDefinition(
    name="cohort_analysis",
    description="Perform cohort analysis for retention and revenue",
    category="specialist",
    tags=("crevo", "revenue", "cohort"),
    steps=[
        StepDefinition(
            name="analyze",
            agent="Vector",
            task_type="cohort_analysis",
            description="Analyze customer cohorts",
            context_mapping={
                "cohort_data": param("cohort_data", {}),
                "cohort_type": param("cohort_type", "acquisition"),
            },
        ),
    ],
)

GROWTH_EXPERIMENT = WorkflowDefinition(
    name="growth_experiment",
    description="Design and plan growth experiments",
    category="specialist",
    tags=("crevo", "growth", "experiment"),
    steps=[
        StepDefinition(
            name="design",
            agent="Vector",
            task_type="growth_experiment_design",
            description="Design growth experiment",
            context_mapping={
                "hypothesis": param("hypothesis", ""),
                "target_metrics": param("target_metrics", []),
                "constraints": param("constraints", {}),
            },
        ),
    ],
)

# =============================================================================
# Sentinel Specialist Workflows
# =============================================================================

DATA_GOVERNANCE = WorkflowDefinition(
    name="data_governance",
    description="Assess and improve data governance practices",
    category="specialist",
    tags=("cio", "data", "governance"),
    steps=[
        StepDefinition(
            name="assess",
            agent="Sentinel",
            task_type="data_governance",
            description="Assess data governance practices and compliance",
            context_mapping={
                "data_domain": param("data_domain", ""),
                "compliance_requirements": param("compliance_requirements", []),
                "current_policies": param("current_policies", {}),
            },
        ),
    ],
)

SECURITY_ASSESSMENT = WorkflowDefinition(
    name="security_assessment",
    description="Perform security assessment and identify vulnerabilities",
    category="specialist",
    tags=("cio", "security", "assessment"),
    steps=[
        StepDefinition(
            name="assess",
            agent="Sentinel",
            task_type="security_assessment",
            description="Assess security posture and identify risks",
            context_mapping={
                "scope": param("scope", "infrastructure"),
                "systems": param("systems", []),
                "compliance_framework": param("compliance_framework", ""),
            },
        ),
    ],
)

KNOWLEDGE_EXTRACTION = WorkflowDefinition(
    name="knowledge_extraction",
    description="Extract and organize knowledge from documents",
    category="specialist",
    tags=("cio", "knowledge", "extraction"),
    steps=[
        StepDefinition(
            name="extract",
            agent="Sentinel",
            task_type="knowledge_extraction",
            description="Extract and structure knowledge from sources",
            context_mapping={
                "source_documents": param("source_documents", []),
                "extraction_type": param("extraction_type", "entities"),
                "knowledge_domain": param("knowledge_domain", ""),
            },
        ),
    ],
)

SYSTEMS_ANALYSIS = WorkflowDefinition(
    name="systems_analysis",
    description="Analyze IT systems and recommend improvements",
    category="specialist",
    tags=("cio", "systems", "analysis"),
    steps=[
        StepDefinition(
            name="analyze",
            agent="Sentinel",
            task_type="systems_analysis",
            description="Analyze system architecture and performance",
            context_mapping={
                "system": param("system", ""),
                "analysis_type": param("analysis_type", "architecture"),
                "requirements": param("requirements", []),
            },
        ),
    ],
)

# =============================================================================
# Axiom Specialist Workflows
# =============================================================================

DEEP_RESEARCH = WorkflowDefinition(
    name="deep_research",
    description="Conduct thorough research on a topic",
    category="specialist",
    tags=("cro", "research", "deep"),
    steps=[
        StepDefinition(
            name="research",
            agent="Axiom",
            task_type="deep_research",
            description="Conduct comprehensive research",
            context_mapping={
                "topic": param("topic", ""),
                "depth": param("depth", "comprehensive"),
                "focus_areas": param("focus_areas", []),
            },
        ),
    ],
)

LITERATURE_REVIEW = WorkflowDefinition(
    name="literature_review",
    description="Conduct structured literature review",
    category="specialist",
    tags=("cro", "research", "literature"),
    steps=[
        StepDefinition(
            name="review",
            agent="Axiom",
            task_type="literature_review",
            description="Review and synthesize literature",
            context_mapping={
                "field": param("field", ""),
                "timeframe": param("timeframe", "recent"),
                "scope": param("scope", "comprehensive"),
            },
        ),
    ],
)

EXPERIMENT_DESIGN = WorkflowDefinition(
    name="experiment_design",
    description="Design rigorous experiments and studies",
    category="specialist",
    tags=("cro", "research", "experiment"),
    steps=[
        StepDefinition(
            name="design",
            agent="Axiom",
            task_type="experiment_design",
            description="Design experiment methodology",
            context_mapping={
                "objective": param("objective", ""),
                "constraints": param("constraints", []),
                "resources": param("resources", []),
            },
        ),
    ],
)

FEASIBILITY_STUDY = WorkflowDefinition(
    name="feasibility_study",
    description="Conduct feasibility study for proposals",
    category="specialist",
    tags=("cro", "research", "feasibility"),
    steps=[
        StepDefinition(
            name="study",
            agent="Axiom",
            task_type="feasibility_study",
            description="Assess proposal feasibility",
            context_mapping={
                "proposal": param("proposal", ""),
                "criteria": param("criteria", []),
            },
        ),
    ],
)

# =============================================================================
# Compass Specialist Workflows
# =============================================================================

MARKET_ANALYSIS = WorkflowDefinition(
    name="market_analysis",
    description="Analyze market conditions and opportunities",
    category="specialist",
    tags=("cso", "strategy", "market"),
    steps=[
        StepDefinition(
            name="analyze",
            agent="Compass",
            task_type="market_analysis",
            description="Perform comprehensive market analysis",
            context_mapping={
                "market": param("market", ""),
                "scope": param("scope", "comprehensive"),
            },
        ),
    ],
)

COMPETITIVE_ANALYSIS = WorkflowDefinition(
    name="competitive_analysis",
    description="Analyze competitive landscape",
    category="specialist",
    tags=("cso", "strategy", "competitive"),
    steps=[
        StepDefinition(
            name="analyze",
            agent="Compass",
            task_type="competitive_analysis",
            description="Analyze competitors and positioning",
            context_mapping={
                "industry": param("industry", ""),
                "competitors": param("competitors", []),
            },
        ),
    ],
)

STRATEGIC_PLANNING = WorkflowDefinition(
    name="strategic_planning",
    description="Develop strategic plans and roadmaps",
    category="specialist",
    tags=("cso", "strategy", "planning"),
    steps=[
        StepDefinition(
            name="plan",
            agent="Compass",
            task_type="strategic_planning",
            description="Develop strategic plan",
            context_mapping={
                "timeframe": param("timeframe", "1 year"),
                "focus_areas": param("focus_areas", []),
            },
        ),
    ],
)

GO_TO_MARKET = WorkflowDefinition(
    name="go_to_market",
    description="Develop go-to-market strategy",
    category="specialist",
    tags=("cso", "strategy", "gtm"),
    steps=[
        StepDefinition(
            name="plan",
            agent="Compass",
            task_type="go_to_market",
            description="Create GTM plan",
            context_mapping={
                "product": param("product", ""),
                "market": param("market", ""),
            },
        ),
    ],
)

# =============================================================================
# Nexus Specialist Workflows
# =============================================================================

WORKFLOW_DESIGN = WorkflowDefinition(
    name="workflow_design",
    description="Design new workflows for cross-functional operations",
    category="specialist",
    tags=("coo", "operations", "workflow"),
    steps=[
        StepDefinition(
            name="design",
            agent="Nexus",
            task_type="workflow_creation",
            description="Design workflow architecture and steps",
            context_mapping={
                "goal": param("goal", ""),
                "agents": param("agents", []),
                "constraints": param("constraints", []),
            },
        ),
    ],
)

TASK_ANALYSIS = WorkflowDefinition(
    name="task_analysis",
    description="Analyze and classify tasks for routing",
    category="specialist",
    tags=("coo", "operations", "analysis"),
    steps=[
        StepDefinition(
            name="analyze",
            agent="Nexus",
            task_type="task_classification",
            description="Classify and analyze task requirements",
            context_mapping={
                "task_description": param("task_description", ""),
                "context": param("context", {}),
            },
        ),
    ],
)

PERFORMANCE_REPORT = WorkflowDefinition(
    name="performance_report",
    description="Generate performance reports from agent data",
    category="specialist",
    tags=("coo", "operations", "reporting"),
    steps=[
        StepDefinition(
            name="report",
            agent="Nexus",
            task_type="reporting",
            description="Generate comprehensive performance report",
            context_mapping={
                "data": param("executive_data", {}),
                "report_type": param("report_type", "comprehensive"),
                "audience": param("audience", "agent"),
            },
        ),
    ],
)

PROCESS_OPTIMIZATION = WorkflowDefinition(
    name="process_optimization",
    description="Optimize business processes for efficiency",
    category="specialist",
    tags=("coo", "operations", "optimization"),
    steps=[
        StepDefinition(
            name="optimize",
            agent="Nexus",
            task_type="process_optimization",
            description="Analyze and optimize process",
            context_mapping={
                "process": param("process", ""),
                "performance": param("performance_data", {}),
                "goals": param("goals", ["improve efficiency"]),
            },
        ),
    ],
)

# =============================================================================
# Accord Specialist Workflows (Compliance)
# =============================================================================

COMPLIANCE_ASSESSMENT = WorkflowDefinition(
    name="compliance_assessment",
    description="Assess compliance against regulatory frameworks",
    category="specialist",
    tags=("ccomo", "compliance", "assessment"),
    steps=[
        StepDefinition(
            name="assess",
            agent="Accord",
            task_type="compliance_assessment",
            description="Perform compliance assessment",
            context_mapping={
                "framework": param("framework", "general"),
                "scope": param("scope", ""),
                "current_controls": param("controls", {}),
            },
        ),
    ],
)

POLICY_REVIEW = WorkflowDefinition(
    name="policy_review",
    description="Review and analyze organizational policies",
    category="specialist",
    tags=("ccomo", "compliance", "policy"),
    steps=[
        StepDefinition(
            name="review",
            agent="Accord",
            task_type="policy_review",
            description="Review policy for compliance and effectiveness",
            context_mapping={
                "policy_name": param("policy_name", ""),
                "policy_content": param("policy_content", ""),
                "review_criteria": param("criteria", ["currency", "compliance", "clarity"]),
            },
        ),
    ],
)

AUDIT_PREPARATION = WorkflowDefinition(
    name="audit_preparation",
    description="Prepare for audit engagement",
    category="specialist",
    tags=("ccomo", "compliance", "audit"),
    steps=[
        StepDefinition(
            name="prepare",
            agent="Accord",
            task_type="audit_preparation",
            description="Prepare documentation and evidence for audit",
            context_mapping={
                "audit_name": param("audit_name", ""),
                "framework": param("framework", ""),
                "audit_type": param("audit_type", "internal"),
            },
        ),
    ],
)

ETHICS_REVIEW = WorkflowDefinition(
    name="ethics_review",
    description="Review ethics-related matters",
    category="specialist",
    tags=("ccomo", "compliance", "ethics"),
    steps=[
        StepDefinition(
            name="review",
            agent="Accord",
            task_type="ethics_review",
            description="Conduct ethics review and provide guidance",
            context_mapping={
                "matter": param("matter", ""),
                "stakeholders": param("stakeholders", []),
                "urgency": param("urgency", "normal"),
            },
        ),
    ],
)

# =============================================================================
# Aegis Specialist Workflows (Risk)
# =============================================================================

RISK_ASSESSMENT = WorkflowDefinition(
    name="risk_assessment",
    description="Assess and score enterprise risks",
    category="specialist",
    tags=("crio", "risk", "assessment"),
    steps=[
        StepDefinition(
            name="assess",
            agent="Aegis",
            task_type="risk_assessment",
            description="Identify and assess risks",
            context_mapping={
                "scope": param("scope", "enterprise"),
                "risk_categories": param("categories", []),
                "context": param("business_context", {}),
            },
        ),
    ],
)

THREAT_MODELING = WorkflowDefinition(
    name="threat_modeling",
    description="Model threats using STRIDE methodology",
    category="specialist",
    tags=("crio", "risk", "threat"),
    steps=[
        StepDefinition(
            name="model",
            agent="Aegis",
            task_type="threat_modeling",
            description="Create threat model for system",
            context_mapping={
                "system": param("system", ""),
                "methodology": param("methodology", "STRIDE"),
                "components": param("components", []),
            },
        ),
    ],
)

BCP_PLANNING = WorkflowDefinition(
    name="bcp_planning",
    description="Develop business continuity plans",
    category="specialist",
    tags=("crio", "risk", "bcp"),
    steps=[
        StepDefinition(
            name="plan",
            agent="Aegis",
            task_type="bcp_planning",
            description="Create business continuity plan",
            context_mapping={
                "scope": param("scope", "enterprise"),
                "critical_functions": param("critical_functions", []),
                "rto_rpo": param("rto_rpo", {}),
            },
        ),
    ],
)

INCIDENT_ANALYSIS = WorkflowDefinition(
    name="incident_analysis",
    description="Analyze incidents and determine root cause",
    category="specialist",
    tags=("crio", "risk", "incident"),
    steps=[
        StepDefinition(
            name="analyze",
            agent="Aegis",
            task_type="incident_analysis",
            description="Analyze incident and identify root cause",
            context_mapping={
                "incident": param("incident", {}),
                "timeline": param("timeline", []),
                "impact": param("impact", {}),
            },
        ),
    ],
)

# =============================================================================
# Citadel Specialist Workflows (Security)
# =============================================================================

SECURITY_SCAN = WorkflowDefinition(
    name="security_scan",
    description="Perform security vulnerability scanning",
    category="specialist",
    tags=("cseco", "security", "scan"),
    steps=[
        StepDefinition(
            name="scan",
            agent="Citadel",
            task_type="vulnerability_assessment",
            description="Scan for security vulnerabilities",
            context_mapping={
                "target": param("target", ""),
                "scan_type": param("scan_type", "comprehensive"),
                "scope": param("scope", {}),
            },
        ),
    ],
)

THREAT_HUNTING = WorkflowDefinition(
    name="threat_hunting",
    description="Proactively hunt for security threats",
    category="specialist",
    tags=("cseco", "security", "hunt"),
    steps=[
        StepDefinition(
            name="hunt",
            agent="Citadel",
            task_type="threat_hunting",
            description="Hunt for indicators of compromise",
            context_mapping={
                "hypothesis": param("hypothesis", ""),
                "indicators": param("indicators", []),
                "data_sources": param("data_sources", []),
            },
        ),
    ],
)

INCIDENT_RESPONSE = WorkflowDefinition(
    name="incident_response",
    description="Respond to security incidents",
    category="specialist",
    tags=("cseco", "security", "incident"),
    steps=[
        StepDefinition(
            name="respond",
            agent="Citadel",
            task_type="incident_response",
            description="Execute incident response procedures",
            context_mapping={
                "incident": param("incident", {}),
                "severity": param("severity", "medium"),
                "affected_systems": param("affected_systems", []),
            },
        ),
    ],
)

SECURITY_COMPLIANCE = WorkflowDefinition(
    name="security_compliance",
    description="Assess security compliance against standards",
    category="specialist",
    tags=("cseco", "security", "compliance"),
    steps=[
        StepDefinition(
            name="assess",
            agent="Citadel",
            task_type="security_compliance",
            description="Assess compliance with security standards",
            context_mapping={
                "framework": param("framework", "SOC2"),
                "scope": param("scope", ""),
                "controls": param("controls", []),
            },
        ),
    ],
)

# =============================================================================
# Foundry Specialist Workflows (Engineering)
# =============================================================================

SPRINT_PLANNING_ENG = WorkflowDefinition(
    name="sprint_planning_eng",
    description="Plan engineering sprint with capacity and deliverables",
    category="specialist",
    tags=("cengo", "engineering", "sprint"),
    steps=[
        StepDefinition(
            name="plan",
            agent="Foundry",
            task_type="sprint_planning",
            description="Plan sprint with capacity allocation",
            context_mapping={
                "backlog": param("backlog", []),
                "capacity": param("capacity", {}),
                "sprint_goals": param("goals", []),
            },
        ),
    ],
)

RELEASE_MANAGEMENT = WorkflowDefinition(
    name="release_management",
    description="Manage software release process",
    category="specialist",
    tags=("cengo", "engineering", "release"),
    steps=[
        StepDefinition(
            name="release",
            agent="Foundry",
            task_type="release_management",
            description="Coordinate and execute release",
            context_mapping={
                "version": param("version", ""),
                "features": param("features", []),
                "environment": param("environment", "production"),
            },
        ),
    ],
)

QUALITY_ASSURANCE = WorkflowDefinition(
    name="quality_assurance",
    description="Execute quality assurance testing",
    category="specialist",
    tags=("cengo", "engineering", "qa"),
    steps=[
        StepDefinition(
            name="test",
            agent="Foundry",
            task_type="qa_testing",
            description="Execute QA testing procedures",
            context_mapping={
                "test_scope": param("scope", ""),
                "test_types": param("test_types", ["functional", "regression"]),
                "criteria": param("acceptance_criteria", []),
            },
        ),
    ],
)

DEVOPS_PIPELINE = WorkflowDefinition(
    name="devops_pipeline",
    description="Manage CI/CD pipeline operations",
    category="specialist",
    tags=("cengo", "engineering", "devops"),
    steps=[
        StepDefinition(
            name="pipeline",
            agent="Foundry",
            task_type="pipeline_management",
            description="Manage and optimize CI/CD pipeline",
            context_mapping={
                "pipeline": param("pipeline", ""),
                "action": param("action", "analyze"),
                "metrics": param("metrics", {}),
            },
        ),
    ],
)


# =============================================================================
# All Definitions Export
# =============================================================================

ALL_DEFINITIONS = [
    # Keystone
    FINANCIAL_MODELING,
    COST_ALLOCATION,
    INVESTMENT_ANALYSIS,
    # Forge
    CODE_REVIEW,
    BUG_FIX,
    TEST_GENERATION,
    DEPLOYMENT_PLANNING,
    # Echo
    CONTENT_CREATION,
    SEO_ANALYSIS,
    LEAD_GENERATION,
    # Blueprint
    USER_STORY_CREATION,
    FEATURE_SCORING,
    BACKLOG_REFINEMENT,
    # Beacon
    FEEDBACK_ANALYSIS,
    CHURN_PREDICTION,
    NPS_ANALYSIS,
    TICKET_TRIAGE,
    # Index
    DATA_QUALITY_CHECK,
    SCHEMA_VALIDATION,
    # Vector
    REVENUE_TRACKING,
    CHURN_ANALYSIS,
    COHORT_ANALYSIS,
    GROWTH_EXPERIMENT,
    # Sentinel
    DATA_GOVERNANCE,
    SECURITY_ASSESSMENT,
    KNOWLEDGE_EXTRACTION,
    SYSTEMS_ANALYSIS,
    # Axiom
    DEEP_RESEARCH,
    LITERATURE_REVIEW,
    EXPERIMENT_DESIGN,
    FEASIBILITY_STUDY,
    # Compass
    MARKET_ANALYSIS,
    COMPETITIVE_ANALYSIS,
    STRATEGIC_PLANNING,
    GO_TO_MARKET,
    # Nexus
    WORKFLOW_DESIGN,
    TASK_ANALYSIS,
    PERFORMANCE_REPORT,
    PROCESS_OPTIMIZATION,
    # Accord
    COMPLIANCE_ASSESSMENT,
    POLICY_REVIEW,
    AUDIT_PREPARATION,
    ETHICS_REVIEW,
    # Aegis
    RISK_ASSESSMENT,
    THREAT_MODELING,
    BCP_PLANNING,
    INCIDENT_ANALYSIS,
    # Citadel
    SECURITY_SCAN,
    THREAT_HUNTING,
    INCIDENT_RESPONSE,
    SECURITY_COMPLIANCE,
    # Foundry
    SPRINT_PLANNING_ENG,
    RELEASE_MANAGEMENT,
    QUALITY_ASSURANCE,
    DEVOPS_PIPELINE,
]
