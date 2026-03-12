"""
Infrastructure Workflows (Workbench).

Workflows for database provisioning, secrets management,
and content distribution pipelines.
"""

from typing import Any, Dict, List

from ag3ntwerk.orchestration.base import Workflow, WorkflowStep


class DatabaseProvisioningWorkflow(Workflow):
    """
    Database setup: Schema design -> Provisioning -> Migrations -> Seeding.

    Coordinates across Index (schema design, data quality) and Forge (infrastructure).

    Stages:
    1. Schema Design - Index: SchemaAnalyst designs database schema
    2. DB Provisioning - Forge: DevOpsEngineer provisions database instance
    3. Migration Run - Foundry: DeploymentEngineer runs migrations
    4. Data Seeding - Index: DataSteward seeds initial data and validates
    """

    @property
    def name(self) -> str:
        return "database_provisioning"

    @property
    def description(self) -> str:
        return "Database schema design, provisioning, migration, and seeding"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="schema_design",
                agent="Index",
                task_type="schema_design",
                description="Design database schema based on requirements",
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "database_type": ctx.get("database_type", "postgres"),
                    "entities": ctx.get("entities", []),
                    "relationships": ctx.get("relationships", []),
                    "code_models": ctx.get("code_models"),
                },
            ),
            WorkflowStep(
                name="db_provisioning",
                agent="Forge",
                task_type="infrastructure",
                description="Provision database instance",
                depends_on=["schema_design"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "database_type": ctx.get("database_type", "postgres"),
                    "schema": ctx.step_results.get("schema_design"),
                    "environment": ctx.get("environment", "development"),
                    "sizing": ctx.get("db_sizing", "small"),
                },
            ),
            WorkflowStep(
                name="migration_run",
                agent="Foundry",
                task_type="deployment_execution",
                description="Run database migrations",
                depends_on=["db_provisioning"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "db_connection": ctx.step_results.get("db_provisioning"),
                    "schema": ctx.step_results.get("schema_design"),
                    "migration_tool": ctx.get("migration_tool", "alembic"),
                },
            ),
            WorkflowStep(
                name="data_seeding",
                agent="Index",
                task_type="data_quality_check",
                description="Seed initial data and validate",
                depends_on=["migration_run"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "db_connection": ctx.step_results.get("db_provisioning"),
                    "seed_data": ctx.get("seed_data", {}),
                    "validation_rules": ctx.get("validation_rules", []),
                },
            ),
        ]


class SecretsManagementWorkflow(Workflow):
    """
    Secrets: Audit -> Generation -> Encryption -> Environment config.

    Handles secure generation, encryption, and distribution of secrets.
    Coordinates Citadel (security) and Forge (infrastructure configuration).

    Stages:
    1. Secret Audit - Citadel: SecurityEngineer audits existing secrets
    2. Secret Generation - Citadel: SecurityEngineer generates new secrets
    3. Secret Encryption - Citadel: SecurityEngineer encrypts secrets
    4. Env Configuration - Forge: DevOpsEngineer configures environments
    """

    @property
    def name(self) -> str:
        return "secrets_management"

    @property
    def description(self) -> str:
        return "Secrets audit, generation, encryption, and environment configuration"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="secret_audit",
                agent="Citadel",
                task_type="security_scan",
                description="Audit existing secrets and identify requirements",
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "code_path": ctx.get("code_path", "/workspace"),
                    "scan_for_exposed": ctx.get("scan_for_exposed", True),
                    "secret_patterns": ctx.get("secret_patterns", []),
                },
            ),
            WorkflowStep(
                name="secret_generation",
                agent="Citadel",
                task_type="security_automation",
                description="Generate required secrets securely",
                depends_on=["secret_audit"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "audit_results": ctx.step_results.get("secret_audit"),
                    "secret_types": ctx.get("secret_types", ["api_key", "db_password"]),
                    "key_length": ctx.get("key_length", 32),
                },
            ),
            WorkflowStep(
                name="secret_encryption",
                agent="Citadel",
                task_type="encryption",
                description="Encrypt secrets for storage",
                depends_on=["secret_generation"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "secrets": ctx.step_results.get("secret_generation"),
                    "encryption_method": ctx.get("encryption_method", "aes256"),
                    "key_management": ctx.get("key_management", "local"),
                },
            ),
            WorkflowStep(
                name="env_configuration",
                agent="Forge",
                task_type="configuration",
                description="Configure environment with secrets",
                depends_on=["secret_encryption"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "encrypted_secrets": ctx.step_results.get("secret_encryption"),
                    "environment": ctx.get("environment", "development"),
                    "env_file_path": ctx.get("env_file_path", ".env"),
                },
            ),
        ]


class ContentDistributionPipelineWorkflow(Workflow):
    """
    End-to-end content distribution pipeline.

    Takes content from creation through social adaptation and
    multi-platform publishing, then tracks revenue impact.

    Coordinates across:
    - Echo (Echo): Content creation and social distribution
    - Vector (Vector): Revenue tracking for distributed content

    Steps:
    1. Content Creation - Echo generates content piece
    2. Social Distribution - Echo adapts and publishes to social platforms
    3. Revenue Tracking - Vector tracks revenue impact of distribution

    Example:
        result = await workflow.execute(
            content_topic="AI for Solo Developers",
            content_type="blog_post",
            platforms=["linkedin", "twitter"],
            track_revenue=True,
        )
    """

    @property
    def name(self) -> str:
        return "content_distribution_pipeline"

    @property
    def description(self) -> str:
        return "Content creation -> social adaptation -> multi-platform publish -> revenue tracking"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="content_creation",
                agent="Echo",
                task_type="content_creation",
                description="Generate content piece for distribution",
                context_builder=lambda ctx: {
                    "topic": ctx.get("content_topic", ""),
                    "content_type": ctx.get("content_type", "blog_post"),
                    "audience": ctx.get("target_audience", ""),
                    "tone": ctx.get("tone", "professional"),
                    "keywords": ctx.get("keywords", []),
                },
            ),
            WorkflowStep(
                name="social_distribution",
                agent="Echo",
                task_type="social_distribute",
                description="Adapt and distribute content across social platforms",
                depends_on=["content_creation"],
                context_builder=lambda ctx: {
                    "content": ctx.step_results.get("content_creation", {}),
                    "platforms": ctx.get("platforms", ["linkedin", "twitter"]),
                    "hashtags": ctx.get("hashtags", []),
                    "schedule_time": ctx.get("schedule_time"),
                },
            ),
            WorkflowStep(
                name="revenue_tracking",
                agent="Vector",
                task_type="revenue_tracking",
                description="Track revenue impact of distributed content",
                depends_on=["social_distribution"],
                required=False,
                context_builder=lambda ctx: {
                    "content_result": ctx.step_results.get("content_creation", {}),
                    "distribution_result": ctx.step_results.get("social_distribution", {}),
                    "period": ctx.get("tracking_period", "weekly"),
                    "revenue_data": ctx.get("revenue_data", {}),
                },
            ),
        ]
