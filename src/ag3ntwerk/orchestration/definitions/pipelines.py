"""
Pipeline Workflow Definitions.

Complex multi-stage pipeline workflows that involve sequential processing
across multiple agents with specific data flow requirements.
"""

from ag3ntwerk.orchestration.factory import (
    WorkflowDefinition,
    StepDefinition,
    param,
    step_result,
)
from ag3ntwerk.modules.vls.workflows import VERTICAL_LAUNCH_PIPELINE, VLS_QUICK_VALIDATION


# =============================================================================
# Code Evaluation and Deployment Pipeline
# =============================================================================

CODE_EVALUATION_DEPLOYMENT = WorkflowDefinition(
    name="code_evaluation_deployment",
    description="Code evaluation and deployment pipeline",
    category="pipeline",
    tags=("cto", "cengo", "cseco", "deployment"),
    steps=[
        StepDefinition(
            name="code_review",
            agent="Forge",
            task_type="code_review",
            description="Review code changes",
            context_mapping={
                "code": "code",
                "file_path": param("file_path", ""),
                "language": param("language", "python"),
            },
        ),
        StepDefinition(
            name="security_scan",
            agent="Citadel",
            task_type="vulnerability_assessment",
            description="Scan code for security issues",
            depends_on=("code_review",),
            context_mapping={
                "code": "code",
                "code_review": step_result("code_review"),
            },
        ),
        StepDefinition(
            name="test_execution",
            agent="Foundry",
            task_type="qa_testing",
            description="Execute test suite",
            depends_on=("code_review",),
            context_mapping={
                "code": "code",
                "code_review": step_result("code_review"),
                "test_types": param("test_types", ["unit", "integration"]),
            },
        ),
        StepDefinition(
            name="deployment",
            agent="Foundry",
            task_type="deployment",
            description="Deploy to target environment",
            depends_on=("code_review", "security_scan", "test_execution"),
            context_mapping={
                "code_review": step_result("code_review"),
                "security_scan": step_result("security_scan"),
                "test_results": step_result("test_execution"),
                "environment": param("environment", "staging"),
            },
        ),
    ],
)

# =============================================================================
# Database Provisioning Pipeline
# =============================================================================

DATABASE_PROVISIONING = WorkflowDefinition(
    name="database_provisioning",
    description="Database provisioning and setup pipeline",
    category="pipeline",
    tags=("cto", "cengo", "cseco", "database"),
    steps=[
        StepDefinition(
            name="schema_design",
            agent="Forge",
            task_type="architecture",
            description="Design database schema",
            context_mapping={
                "requirements": param("requirements", []),
                "database_type": param("database_type", "postgresql"),
            },
        ),
        StepDefinition(
            name="security_config",
            agent="Citadel",
            task_type="security_configuration",
            description="Configure security settings",
            depends_on=("schema_design",),
            context_mapping={
                "schema": step_result("schema_design"),
                "security_requirements": param("security_requirements", []),
            },
        ),
        StepDefinition(
            name="provisioning",
            agent="Foundry",
            task_type="infrastructure_provisioning",
            description="Provision database infrastructure",
            depends_on=("schema_design", "security_config"),
            context_mapping={
                "schema": step_result("schema_design"),
                "security": step_result("security_config"),
                "environment": param("environment", "production"),
            },
        ),
    ],
)

# =============================================================================
# Secrets Management Pipeline
# =============================================================================

SECRETS_MANAGEMENT = WorkflowDefinition(
    name="secrets_management",
    description="Secrets rotation and management pipeline",
    category="pipeline",
    tags=("cseco", "cengo", "secrets"),
    steps=[
        StepDefinition(
            name="secrets_audit",
            agent="Citadel",
            task_type="secrets_audit",
            description="Audit current secrets",
            context_mapping={
                "scope": param("scope", "all"),
                "environment": param("environment", "production"),
            },
        ),
        StepDefinition(
            name="rotation_plan",
            agent="Citadel",
            task_type="secrets_rotation",
            description="Plan secrets rotation",
            depends_on=("secrets_audit",),
            context_mapping={
                "audit": step_result("secrets_audit"),
                "rotation_policy": param("rotation_policy", {}),
            },
        ),
        StepDefinition(
            name="rotation_execution",
            agent="Foundry",
            task_type="secrets_update",
            description="Execute secrets rotation",
            depends_on=("rotation_plan",),
            context_mapping={
                "plan": step_result("rotation_plan"),
                "environment": param("environment", "production"),
            },
        ),
    ],
)

# =============================================================================
# Content Distribution Pipeline
# =============================================================================

CONTENT_DISTRIBUTION = WorkflowDefinition(
    name="content_distribution_pipeline",
    description="Content creation and distribution pipeline",
    category="pipeline",
    tags=("cmo", "cpo", "content"),
    steps=[
        StepDefinition(
            name="content_planning",
            agent="Echo",
            task_type="content_planning",
            description="Plan content strategy",
            context_mapping={
                "campaign": param("campaign", ""),
                "audience": param("audience", ""),
                "channels": param("channels", []),
            },
        ),
        StepDefinition(
            name="content_creation",
            agent="Echo",
            task_type="content_creation",
            description="Create content assets",
            depends_on=("content_planning",),
            context_mapping={
                "plan": step_result("content_planning"),
                "content_types": param("content_types", []),
            },
        ),
        StepDefinition(
            name="product_alignment_check",
            agent="Blueprint",
            task_type="messaging_review",
            description="Verify product messaging alignment",
            depends_on=("content_creation",),
            context_mapping={
                "content": step_result("content_creation"),
                "product_guidelines": param("product_guidelines", {}),
            },
        ),
        StepDefinition(
            name="distribution",
            agent="Echo",
            task_type="digital_campaign_execution",
            description="Distribute content",
            depends_on=("content_creation", "product_alignment_check"),
            context_mapping={
                "content": step_result("content_creation"),
                "alignment": step_result("product_alignment_check"),
                "channels": param("channels", []),
            },
        ),
    ],
)


# =============================================================================
# All Definitions Export
# =============================================================================

ALL_DEFINITIONS = [
    CODE_EVALUATION_DEPLOYMENT,
    DATABASE_PROVISIONING,
    SECRETS_MANAGEMENT,
    CONTENT_DISTRIBUTION,
    VERTICAL_LAUNCH_PIPELINE,
    VLS_QUICK_VALIDATION,
]
