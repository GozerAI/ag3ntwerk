"""
Cross-Functional Workflow Definitions.

Multi-agent workflows that coordinate across multiple C-level agents
to accomplish complex cross-functional tasks.
"""

from ag3ntwerk.orchestration.factory import (
    WorkflowDefinition,
    StepDefinition,
    param,
    step_result,
    aggregate,
)


# =============================================================================
# Product Launch and Release Workflows
# =============================================================================

PRODUCT_LAUNCH = WorkflowDefinition(
    name="product_launch",
    description="End-to-end product launch coordination across all agents",
    category="cross_functional",
    tags=("product", "launch", "cpo", "cfo", "cseco", "cengo", "cco"),
    steps=[
        StepDefinition(
            name="product_strategy",
            agent="Blueprint",
            task_type="product_spec",
            description="Define product strategy, vision, and requirements",
            context_mapping={
                "product_name": "product_name",
                "features": param("features", []),
                "target_market": param("target_market", ""),
                "objectives": param("objectives", []),
            },
        ),
        StepDefinition(
            name="budget_analysis",
            agent="Keystone",
            task_type="budget_planning",
            description="Analyze development costs and set pricing strategy",
            depends_on=("product_strategy",),
            context_mapping={
                "product_strategy": step_result("product_strategy"),
                "product_name": "product_name",
                "target_price": "target_price",
                "period": "launch",
            },
        ),
        StepDefinition(
            name="security_review",
            agent="Citadel",
            task_type="security_assessment",
            description="Review security implications and requirements",
            depends_on=("product_strategy",),
            context_mapping={
                "product_name": "product_name",
                "features": param("features", []),
                "product_strategy": step_result("product_strategy"),
            },
        ),
        StepDefinition(
            name="engineering_assessment",
            agent="Foundry",
            task_type="technical_assessment",
            description="Assess engineering readiness and release plan",
            depends_on=("product_strategy", "security_review"),
            context_mapping={
                "product_name": "product_name",
                "features": param("features", []),
                "security_requirements": step_result("security_review"),
                "target_date": "target_launch_date",
            },
        ),
        StepDefinition(
            name="marketing_plan",
            agent="Echo",
            task_type="campaign_creation",
            description="Create go-to-market and marketing strategy",
            depends_on=("product_strategy", "budget_analysis"),
            required=False,
            context_mapping={
                "product_name": "product_name",
                "product_strategy": step_result("product_strategy"),
                "budget": step_result("budget_analysis"),
                "target_market": param("target_market", ""),
                "launch_date": "target_launch_date",
            },
        ),
        StepDefinition(
            name="customer_success_plan",
            agent="Beacon",
            task_type="onboarding_design",
            description="Prepare customer onboarding and support plan",
            depends_on=("product_strategy", "engineering_assessment"),
            context_mapping={
                "product_name": "product_name",
                "features": param("features", []),
                "product_strategy": step_result("product_strategy"),
                "engineering_plan": step_result("engineering_assessment"),
            },
        ),
        StepDefinition(
            name="launch_approval",
            agent="Blueprint",
            task_type="milestone_tracking",
            description="Final launch readiness check and approval",
            depends_on=(
                "budget_analysis",
                "security_review",
                "engineering_assessment",
                "customer_success_plan",
            ),
            context_mapping={
                "product_name": "product_name",
                "milestone": "launch_readiness",
                "all_reviews": aggregate(
                    budget="budget_analysis",
                    security="security_review",
                    engineering="engineering_assessment",
                    marketing="marketing_plan",
                    customer_success="customer_success_plan",
                ),
            },
        ),
    ],
)

FEATURE_RELEASE = WorkflowDefinition(
    name="feature_release",
    description="Streamlined feature release workflow",
    category="cross_functional",
    tags=("product", "release", "cpo", "cengo", "cseco", "crevo"),
    steps=[
        StepDefinition(
            name="feature_review",
            agent="Blueprint",
            task_type="feature_prioritization",
            description="Review feature for release readiness",
            context_mapping={
                "feature_name": "feature_name",
                "feature_id": "feature_id",
                "description": "description",
                "product_id": "product_id",
                "features": param("features", []),
            },
        ),
        StepDefinition(
            name="security_check",
            agent="Citadel",
            task_type="security_assessment",
            description="Quick security review of feature",
            depends_on=("feature_review",),
            required=False,
            context_mapping={
                "feature_name": "feature_name",
                "feature_review": step_result("feature_review"),
                "security_relevant": param("security_relevant", False),
            },
        ),
        StepDefinition(
            name="release_execution",
            agent="Foundry",
            task_type="release_coordination",
            description="Execute the feature release",
            depends_on=("feature_review",),
            context_mapping={
                "feature_name": "feature_name",
                "feature_id": "feature_id",
                "version": "version",
                "release_type": "feature",
                "feature_review": step_result("feature_review"),
            },
        ),
        StepDefinition(
            name="adoption_tracking",
            agent="Vector",
            task_type="feature_adoption_metrics",
            description="Set up feature adoption tracking",
            depends_on=("release_execution",),
            required=False,
            context_mapping={
                "feature_name": "feature_name",
                "feature_id": "feature_id",
                "product_id": "product_id",
                "release_info": step_result("release_execution"),
            },
        ),
    ],
)

# =============================================================================
# Incident Response Workflows
# =============================================================================

INCIDENT_RESPONSE = WorkflowDefinition(
    name="incident_response",
    description="Coordinated incident response across technical and customer-facing teams",
    category="cross_functional",
    tags=("incident", "cengo", "cseco", "cco"),
    steps=[
        StepDefinition(
            name="initial_assessment",
            agent="Foundry",
            task_type="incident_assessment",
            description="Assess incident scope and severity",
            context_mapping={
                "incident_id": "incident_id",
                "incident_type": "incident_type",
                "description": "description",
                "severity": param("severity", "medium"),
                "affected_systems": param("affected_systems", []),
            },
        ),
        StepDefinition(
            name="security_check",
            agent="Citadel",
            task_type="incident_response",
            description="Check for security implications",
            depends_on=("initial_assessment",),
            context_mapping={
                "incident_id": "incident_id",
                "incident_type": "incident_type",
                "initial_assessment": step_result("initial_assessment"),
                "affected_systems": param("affected_systems", []),
            },
        ),
        StepDefinition(
            name="customer_impact",
            agent="Beacon",
            task_type="health_scoring",
            description="Assess customer impact and at-risk accounts",
            depends_on=("initial_assessment",),
            context_mapping={
                "incident_id": "incident_id",
                "initial_assessment": step_result("initial_assessment"),
                "affected_customers": param("affected_customers", []),
            },
        ),
        StepDefinition(
            name="remediation_plan",
            agent="Foundry",
            task_type="remediation_planning",
            description="Create remediation and fix plan",
            depends_on=("initial_assessment", "security_check"),
            context_mapping={
                "incident_id": "incident_id",
                "initial_assessment": step_result("initial_assessment"),
                "security_findings": step_result("security_check"),
            },
        ),
        StepDefinition(
            name="customer_communication",
            agent="Beacon",
            task_type="support_escalation",
            description="Handle customer communication and updates",
            depends_on=("customer_impact", "remediation_plan"),
            context_mapping={
                "incident_id": "incident_id",
                "customer_impact": step_result("customer_impact"),
                "remediation_plan": step_result("remediation_plan"),
                "communication_type": "incident_update",
            },
        ),
        StepDefinition(
            name="post_incident_review",
            agent="Foundry",
            task_type="post_incident_review",
            description="Conduct post-incident retrospective",
            depends_on=("remediation_plan", "customer_communication"),
            required=False,
            context_mapping={
                "incident_id": "incident_id",
                "timeline": aggregate(
                    initial_assessment="initial_assessment",
                    security_check="security_check",
                    remediation="remediation_plan",
                ),
            },
        ),
    ],
)

# =============================================================================
# Budget and Financial Workflows
# =============================================================================

BUDGET_APPROVAL = WorkflowDefinition(
    name="budget_approval",
    description="Multi-stakeholder budget approval process",
    category="cross_functional",
    tags=("budget", "cfo", "cpo", "cengo", "coo"),
    steps=[
        StepDefinition(
            name="budget_analysis",
            agent="Keystone",
            task_type="budget_variance",
            description="Analyze budget request and financial impact",
            context_mapping={
                "request_id": "request_id",
                "amount": "amount",
                "purpose": "purpose",
                "department": "department",
                "budget": param("current_budget", {}),
                "actuals": param("current_spend", {}),
            },
        ),
        StepDefinition(
            name="product_impact",
            agent="Blueprint",
            task_type="roadmap_update",
            description="Assess impact on product roadmap",
            depends_on=("budget_analysis",),
            context_mapping={
                "budget_request": step_result("budget_analysis"),
                "purpose": "purpose",
                "affected_products": param("affected_products", []),
            },
        ),
        StepDefinition(
            name="technical_feasibility",
            agent="Foundry",
            task_type="technical_assessment",
            description="Assess technical feasibility and requirements",
            depends_on=("budget_analysis",),
            context_mapping={
                "budget_request": step_result("budget_analysis"),
                "purpose": "purpose",
                "technical_requirements": param("technical_requirements", []),
            },
        ),
        StepDefinition(
            name="operational_impact",
            agent="Nexus",
            task_type="operational_review",
            description="Assess operational implications",
            depends_on=("budget_analysis",),
            required=False,
            context_mapping={
                "budget_request": step_result("budget_analysis"),
                "purpose": "purpose",
                "operational_areas": param("operational_areas", []),
            },
        ),
        StepDefinition(
            name="final_approval",
            agent="Keystone",
            task_type="budget_planning",
            description="Make final budget decision",
            depends_on=("budget_analysis", "product_impact", "technical_feasibility"),
            context_mapping={
                "request_id": "request_id",
                "amount": "amount",
                "purpose": "purpose",
                "assessments": aggregate(
                    financial="budget_analysis",
                    product="product_impact",
                    technical="technical_feasibility",
                    operational="operational_impact",
                ),
                "period": "approval",
            },
        ),
    ],
)

# =============================================================================
# Strategic Planning Workflows
# =============================================================================

STRATEGIC_PLANNING = WorkflowDefinition(
    name="strategic_planning",
    description="Comprehensive strategic planning across all business functions",
    category="cross_functional",
    tags=("strategy", "cso", "cfo", "cpo", "cro", "coo"),
    steps=[
        StepDefinition(
            name="market_analysis",
            agent="Compass",
            task_type="market_analysis",
            description="Analyze market trends, competition, and opportunities",
            context_mapping={
                "planning_period": param("planning_period", "Q1 2026"),
                "focus_areas": param("focus_areas", []),
                "current_position": param("current_position", ""),
                "objectives": param("objectives", []),
            },
        ),
        StepDefinition(
            name="research_insights",
            agent="Axiom",
            task_type="trend_research",
            description="Provide research-backed market and technology insights",
            depends_on=("market_analysis",),
            context_mapping={
                "market_analysis": step_result("market_analysis"),
                "planning_period": param("planning_period", "Q1 2026"),
                "research_areas": param("research_areas", []),
            },
        ),
        StepDefinition(
            name="financial_planning",
            agent="Keystone",
            task_type="budget_planning",
            description="Create financial plan and resource allocation",
            depends_on=("market_analysis",),
            context_mapping={
                "market_analysis": step_result("market_analysis"),
                "planning_period": param("planning_period", "Q1 2026"),
                "current_budget": param("current_budget", {}),
            },
        ),
        StepDefinition(
            name="product_alignment",
            agent="Blueprint",
            task_type="roadmap_update",
            description="Align product roadmap with strategy",
            depends_on=("market_analysis", "research_insights"),
            context_mapping={
                "market_analysis": step_result("market_analysis"),
                "research_insights": step_result("research_insights"),
                "planning_period": param("planning_period", "Q1 2026"),
            },
        ),
        StepDefinition(
            name="operational_review",
            agent="Nexus",
            task_type="operational_review",
            description="Assess operational feasibility of strategy",
            depends_on=("financial_planning", "product_alignment"),
            context_mapping={
                "financial_plan": step_result("financial_planning"),
                "product_roadmap": step_result("product_alignment"),
                "planning_period": param("planning_period", "Q1 2026"),
            },
        ),
        StepDefinition(
            name="strategy_finalization",
            agent="Compass",
            task_type="strategic_planning",
            description="Finalize and consolidate strategic plan",
            depends_on=(
                "market_analysis",
                "research_insights",
                "financial_planning",
                "product_alignment",
                "operational_review",
            ),
            context_mapping={
                "all_inputs": aggregate(
                    market="market_analysis",
                    research="research_insights",
                    financial="financial_planning",
                    product="product_alignment",
                    operations="operational_review",
                ),
                "planning_period": param("planning_period", "Q1 2026"),
            },
        ),
    ],
)

# =============================================================================
# Security and Compliance Workflows
# =============================================================================

SECURITY_AUDIT = WorkflowDefinition(
    name="security_audit",
    description="Comprehensive security audit across systems",
    category="cross_functional",
    tags=("security", "audit", "cseco", "cengo", "ccomo", "crio"),
    steps=[
        StepDefinition(
            name="vulnerability_scan",
            agent="Citadel",
            task_type="vulnerability_assessment",
            description="Scan systems for vulnerabilities",
            context_mapping={
                "scope": param("scope", "full"),
                "systems": param("systems", []),
                "scan_type": param("scan_type", "comprehensive"),
            },
        ),
        StepDefinition(
            name="code_security_review",
            agent="Foundry",
            task_type="security_review",
            description="Review code security practices",
            context_mapping={
                "codebase": param("codebase", ""),
                "focus_areas": param("focus_areas", []),
            },
        ),
        StepDefinition(
            name="compliance_check",
            agent="Accord",
            task_type="compliance_assessment",
            description="Check security compliance requirements",
            depends_on=("vulnerability_scan",),
            context_mapping={
                "vulnerability_findings": step_result("vulnerability_scan"),
                "frameworks": param("frameworks", []),
            },
        ),
        StepDefinition(
            name="risk_assessment",
            agent="Aegis",
            task_type="risk_assessment",
            description="Assess security risks",
            depends_on=("vulnerability_scan", "code_security_review"),
            context_mapping={
                "vulnerabilities": step_result("vulnerability_scan"),
                "code_review": step_result("code_security_review"),
            },
        ),
        StepDefinition(
            name="remediation_plan",
            agent="Citadel",
            task_type="security_remediation",
            description="Create remediation plan",
            depends_on=("vulnerability_scan", "compliance_check", "risk_assessment"),
            context_mapping={
                "vulnerabilities": step_result("vulnerability_scan"),
                "compliance": step_result("compliance_check"),
                "risks": step_result("risk_assessment"),
            },
        ),
    ],
)

COMPLIANCE_AUDIT = WorkflowDefinition(
    name="compliance_audit",
    description="Full compliance audit across organization",
    category="cross_functional",
    tags=("compliance", "audit", "ccomo", "cfo", "cseco", "crio"),
    steps=[
        StepDefinition(
            name="scope_definition",
            agent="Accord",
            task_type="audit_scoping",
            description="Define audit scope and requirements",
            context_mapping={
                "audit_type": param("audit_type", "annual"),
                "frameworks": param("frameworks", []),
                "areas": param("areas", []),
            },
        ),
        StepDefinition(
            name="financial_compliance",
            agent="Keystone",
            task_type="compliance_review",
            description="Review financial compliance",
            depends_on=("scope_definition",),
            context_mapping={
                "scope": step_result("scope_definition"),
                "financial_areas": param("financial_areas", []),
            },
        ),
        StepDefinition(
            name="security_compliance",
            agent="Citadel",
            task_type="security_compliance",
            description="Review security compliance",
            depends_on=("scope_definition",),
            context_mapping={
                "scope": step_result("scope_definition"),
                "security_frameworks": param("security_frameworks", []),
            },
        ),
        StepDefinition(
            name="risk_compliance",
            agent="Aegis",
            task_type="risk_assessment",
            description="Assess compliance risks",
            depends_on=("scope_definition",),
            context_mapping={
                "scope": step_result("scope_definition"),
                "risk_areas": param("risk_areas", []),
            },
        ),
        StepDefinition(
            name="audit_synthesis",
            agent="Accord",
            task_type="compliance_assessment",
            description="Synthesize audit findings and recommendations",
            depends_on=("financial_compliance", "security_compliance", "risk_compliance"),
            context_mapping={
                "financial": step_result("financial_compliance"),
                "security": step_result("security_compliance"),
                "risk": step_result("risk_compliance"),
            },
        ),
    ],
)

# =============================================================================
# Customer Success Workflows
# =============================================================================

CUSTOMER_ONBOARDING = WorkflowDefinition(
    name="customer_onboarding",
    description="End-to-end customer onboarding coordination",
    category="cross_functional",
    tags=("customer", "onboarding", "cco", "cengo", "crevo"),
    steps=[
        StepDefinition(
            name="onboarding_plan",
            agent="Beacon",
            task_type="onboarding_design",
            description="Create customer onboarding plan",
            context_mapping={
                "customer_name": "customer_name",
                "customer_id": "customer_id",
                "product": "product",
                "tier": param("tier", "standard"),
            },
        ),
        StepDefinition(
            name="technical_setup",
            agent="Foundry",
            task_type="environment_setup",
            description="Setup technical environment for customer",
            depends_on=("onboarding_plan",),
            context_mapping={
                "customer_id": "customer_id",
                "onboarding_plan": step_result("onboarding_plan"),
                "requirements": param("technical_requirements", []),
            },
        ),
        StepDefinition(
            name="adoption_tracking_setup",
            agent="Vector",
            task_type="customer_metrics",
            description="Setup adoption tracking for customer",
            depends_on=("onboarding_plan",),
            context_mapping={
                "customer_id": "customer_id",
                "onboarding_plan": step_result("onboarding_plan"),
            },
        ),
        StepDefinition(
            name="onboarding_execution",
            agent="Beacon",
            task_type="customer_engagement",
            description="Execute onboarding and training",
            depends_on=("technical_setup", "adoption_tracking_setup"),
            context_mapping={
                "customer_id": "customer_id",
                "technical_setup": step_result("technical_setup"),
                "tracking": step_result("adoption_tracking_setup"),
            },
        ),
    ],
)

CUSTOMER_CHURN_ANALYSIS = WorkflowDefinition(
    name="customer_churn_analysis",
    description="Comprehensive churn analysis and intervention planning",
    category="cross_functional",
    tags=("customer", "churn", "cco", "crevo", "cpo"),
    steps=[
        StepDefinition(
            name="churn_detection",
            agent="Beacon",
            task_type="churn_prediction",
            description="Detect at-risk customers",
            context_mapping={
                "customer_data": param("customer_data", {}),
                "threshold": param("threshold", 0.7),
            },
        ),
        StepDefinition(
            name="revenue_impact",
            agent="Vector",
            task_type="revenue_impact_analysis",
            description="Analyze revenue impact of potential churn",
            depends_on=("churn_detection",),
            context_mapping={
                "at_risk_customers": step_result("churn_detection"),
                "revenue_data": param("revenue_data", {}),
            },
        ),
        StepDefinition(
            name="product_insights",
            agent="Blueprint",
            task_type="usage_analysis",
            description="Analyze product usage patterns",
            depends_on=("churn_detection",),
            context_mapping={
                "at_risk_customers": step_result("churn_detection"),
                "usage_data": param("usage_data", {}),
            },
        ),
        StepDefinition(
            name="intervention_plan",
            agent="Beacon",
            task_type="retention_strategy",
            description="Create intervention plan for at-risk customers",
            depends_on=("churn_detection", "revenue_impact", "product_insights"),
            context_mapping={
                "churn_analysis": step_result("churn_detection"),
                "revenue_impact": step_result("revenue_impact"),
                "product_insights": step_result("product_insights"),
            },
        ),
    ],
)

# =============================================================================
# Data and Analytics Workflows
# =============================================================================

DATA_QUALITY = WorkflowDefinition(
    name="data_quality",
    description="Cross-functional data quality assessment",
    category="cross_functional",
    tags=("data", "quality", "cdo", "cio", "cengo"),
    steps=[
        StepDefinition(
            name="quality_assessment",
            agent="Index",
            task_type="data_quality_check",
            description="Assess overall data quality",
            context_mapping={
                "data_sources": param("data_sources", []),
                "quality_rules": param("quality_rules", []),
            },
        ),
        StepDefinition(
            name="governance_review",
            agent="Sentinel",
            task_type="data_governance",
            description="Review data governance practices",
            depends_on=("quality_assessment",),
            context_mapping={
                "quality_findings": step_result("quality_assessment"),
                "governance_policies": param("governance_policies", []),
            },
        ),
        StepDefinition(
            name="technical_fixes",
            agent="Foundry",
            task_type="data_pipeline_review",
            description="Identify technical fixes for data issues",
            depends_on=("quality_assessment",),
            context_mapping={
                "quality_findings": step_result("quality_assessment"),
                "pipelines": param("pipelines", []),
            },
        ),
        StepDefinition(
            name="remediation_plan",
            agent="Index",
            task_type="data_remediation",
            description="Create data quality remediation plan",
            depends_on=("quality_assessment", "governance_review", "technical_fixes"),
            context_mapping={
                "quality": step_result("quality_assessment"),
                "governance": step_result("governance_review"),
                "technical": step_result("technical_fixes"),
            },
        ),
    ],
)

# =============================================================================
# Research and Innovation Workflows
# =============================================================================

RESEARCH_INITIATIVE = WorkflowDefinition(
    name="research_initiative",
    description="Cross-functional research initiative coordination",
    category="cross_functional",
    tags=("research", "cro", "cto", "cpo", "cfo"),
    steps=[
        StepDefinition(
            name="research_proposal",
            agent="Axiom",
            task_type="research_proposal",
            description="Create research proposal",
            context_mapping={
                "topic": "topic",
                "objectives": param("objectives", []),
                "scope": param("scope", ""),
            },
        ),
        StepDefinition(
            name="technical_feasibility",
            agent="Forge",
            task_type="technical_assessment",
            description="Assess technical feasibility",
            depends_on=("research_proposal",),
            context_mapping={
                "proposal": step_result("research_proposal"),
                "technical_constraints": param("technical_constraints", []),
            },
        ),
        StepDefinition(
            name="product_alignment",
            agent="Blueprint",
            task_type="roadmap_impact",
            description="Assess product roadmap impact",
            depends_on=("research_proposal",),
            context_mapping={
                "proposal": step_result("research_proposal"),
                "current_roadmap": param("current_roadmap", {}),
            },
        ),
        StepDefinition(
            name="budget_allocation",
            agent="Keystone",
            task_type="budget_planning",
            description="Allocate research budget",
            depends_on=("research_proposal", "technical_feasibility"),
            context_mapping={
                "proposal": step_result("research_proposal"),
                "technical_assessment": step_result("technical_feasibility"),
                "available_budget": param("available_budget", {}),
            },
        ),
        StepDefinition(
            name="research_plan",
            agent="Axiom",
            task_type="research_planning",
            description="Finalize research plan",
            depends_on=(
                "research_proposal",
                "technical_feasibility",
                "product_alignment",
                "budget_allocation",
            ),
            context_mapping={
                "proposal": step_result("research_proposal"),
                "technical": step_result("technical_feasibility"),
                "product": step_result("product_alignment"),
                "budget": step_result("budget_allocation"),
            },
        ),
    ],
)


# =============================================================================
# All Definitions Export
# =============================================================================

ALL_DEFINITIONS = [
    # Product and Release
    PRODUCT_LAUNCH,
    FEATURE_RELEASE,
    # Incident Response
    INCIDENT_RESPONSE,
    # Budget and Finance
    BUDGET_APPROVAL,
    # Strategic Planning
    STRATEGIC_PLANNING,
    # Security and Compliance
    SECURITY_AUDIT,
    COMPLIANCE_AUDIT,
    # Customer Success
    CUSTOMER_ONBOARDING,
    CUSTOMER_CHURN_ANALYSIS,
    # Data and Analytics
    DATA_QUALITY,
    # Research
    RESEARCH_INITIATIVE,
]
