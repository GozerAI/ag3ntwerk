"""
Single Agent Workflow Definitions.

Workflows that primarily use one agent for internal operations.
These are simpler workflows that don't require cross-functional coordination.
"""

from ag3ntwerk.orchestration.factory import (
    WorkflowDefinition,
    StepDefinition,
    param,
    step_result,
)


# =============================================================================
# Keystone Internal Workflows
# =============================================================================

FINANCIAL_CLOSE = WorkflowDefinition(
    name="financial_close",
    description="Financial period close process",
    category="single_agent",
    tags=("cfo", "finance", "close"),
    steps=[
        StepDefinition(
            name="revenue_recognition",
            agent="Keystone",
            task_type="revenue_tracking",
            description="Recognize revenue for period",
            context_mapping={
                "period": "period",
                "revenue_data": param("revenue_data", {}),
            },
        ),
        StepDefinition(
            name="expense_reconciliation",
            agent="Keystone",
            task_type="expense_analysis",
            description="Reconcile expenses",
            depends_on=("revenue_recognition",),
            context_mapping={
                "period": "period",
                "expense_data": param("expense_data", {}),
            },
        ),
        StepDefinition(
            name="close_report",
            agent="Keystone",
            task_type="financial_reporting",
            description="Generate close report",
            depends_on=("revenue_recognition", "expense_reconciliation"),
            context_mapping={
                "period": "period",
                "revenue": step_result("revenue_recognition"),
                "expenses": step_result("expense_reconciliation"),
            },
        ),
    ],
)

# =============================================================================
# Forge Internal Workflows
# =============================================================================

TECH_DEBT_REVIEW = WorkflowDefinition(
    name="tech_debt_review",
    description="Technical debt review and prioritization",
    category="single_agent",
    tags=("cto", "engineering", "tech_debt"),
    steps=[
        StepDefinition(
            name="debt_assessment",
            agent="Forge",
            task_type="technical_debt",
            description="Assess technical debt",
            context_mapping={
                "codebase": param("codebase", ""),
                "areas": param("areas", []),
            },
        ),
        StepDefinition(
            name="impact_analysis",
            agent="Forge",
            task_type="impact_analysis",
            description="Analyze impact of technical debt",
            depends_on=("debt_assessment",),
            context_mapping={
                "debt_assessment": step_result("debt_assessment"),
            },
        ),
        StepDefinition(
            name="remediation_roadmap",
            agent="Forge",
            task_type="roadmap_creation",
            description="Create debt remediation roadmap",
            depends_on=("debt_assessment", "impact_analysis"),
            context_mapping={
                "assessment": step_result("debt_assessment"),
                "impact": step_result("impact_analysis"),
            },
        ),
    ],
)

CODE_QUALITY = WorkflowDefinition(
    name="code_quality",
    description="Code quality assessment workflow",
    category="single_agent",
    tags=("cto", "engineering", "quality"),
    steps=[
        StepDefinition(
            name="code_analysis",
            agent="Forge",
            task_type="code_analysis",
            description="Analyze code quality",
            context_mapping={
                "codebase": param("codebase", ""),
                "code": param("code", ""),
            },
        ),
        StepDefinition(
            name="best_practices_review",
            agent="Forge",
            task_type="best_practices",
            description="Review against best practices",
            depends_on=("code_analysis",),
            context_mapping={
                "analysis": step_result("code_analysis"),
                "standards": param("standards", []),
            },
        ),
        StepDefinition(
            name="recommendations",
            agent="Forge",
            task_type="code_improvement",
            description="Generate improvement recommendations",
            depends_on=("code_analysis", "best_practices_review"),
            context_mapping={
                "analysis": step_result("code_analysis"),
                "practices": step_result("best_practices_review"),
            },
        ),
    ],
)

# =============================================================================
# Blueprint Internal Workflows
# =============================================================================

FEATURE_PRIORITIZATION = WorkflowDefinition(
    name="feature_prioritization",
    description="Feature prioritization workflow",
    category="single_agent",
    tags=("cpo", "product", "prioritization"),
    steps=[
        StepDefinition(
            name="feature_analysis",
            agent="Blueprint",
            task_type="feature_analysis",
            description="Analyze feature requests",
            context_mapping={
                "features": param("features", []),
                "criteria": param("criteria", {}),
            },
        ),
        StepDefinition(
            name="scoring",
            agent="Blueprint",
            task_type="feature_scoring",
            description="Score features using framework",
            depends_on=("feature_analysis",),
            context_mapping={
                "features": step_result("feature_analysis"),
                "framework": param("framework", "RICE"),
            },
        ),
        StepDefinition(
            name="roadmap_placement",
            agent="Blueprint",
            task_type="roadmap_update",
            description="Place features on roadmap",
            depends_on=("scoring",),
            context_mapping={
                "scored_features": step_result("scoring"),
                "current_roadmap": param("current_roadmap", {}),
            },
        ),
    ],
)

# =============================================================================
# Nexus Internal Workflows
# =============================================================================

OPERATIONS_REVIEW = WorkflowDefinition(
    name="operations_review",
    description="Internal operations review",
    category="single_agent",
    tags=("coo", "operations", "review"),
    steps=[
        StepDefinition(
            name="performance_metrics",
            agent="Nexus",
            task_type="performance_analysis",
            description="Collect performance metrics",
            context_mapping={
                "period": param("period", "current"),
                "metrics": param("metrics", {}),
            },
        ),
        StepDefinition(
            name="bottleneck_analysis",
            agent="Nexus",
            task_type="efficiency_analysis",
            description="Identify bottlenecks",
            depends_on=("performance_metrics",),
            context_mapping={
                "metrics": step_result("performance_metrics"),
            },
        ),
        StepDefinition(
            name="improvement_plan",
            agent="Nexus",
            task_type="process_optimization",
            description="Create improvement plan",
            depends_on=("performance_metrics", "bottleneck_analysis"),
            context_mapping={
                "metrics": step_result("performance_metrics"),
                "bottlenecks": step_result("bottleneck_analysis"),
            },
        ),
    ],
)


# =============================================================================
# All Definitions Export
# =============================================================================

ALL_DEFINITIONS = [
    # Keystone
    FINANCIAL_CLOSE,
    # Forge
    TECH_DEBT_REVIEW,
    CODE_QUALITY,
    # Blueprint
    FEATURE_PRIORITIZATION,
    # Nexus
    OPERATIONS_REVIEW,
]
