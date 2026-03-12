"""
Engineering & DevOps Workflows.

Workflows for feature releases, sprint planning, technology migration,
tech debt review, code quality, infrastructure health, and CI/CD pipelines.
"""

from typing import Any, Dict, List

from ag3ntwerk.orchestration.base import Workflow, WorkflowStep


class FeatureReleaseWorkflow(Workflow):
    """
    Workflow for releasing a new feature.

    A lighter-weight workflow than full product launch, focused on
    shipping a single feature safely.

    Coordinates across:
    - Blueprint (Blueprint): Feature spec and approval
    - Foundry (Foundry): Release execution
    - Citadel (Citadel): Security review (if needed)
    - Vector (Vector): Feature adoption tracking setup

    Steps:
    1. Feature Review - Blueprint reviews feature for release
    2. Security Check - Citadel quick security review
    3. Release Execution - Foundry handles the release
    4. Adoption Tracking - Vector sets up tracking
    """

    @property
    def name(self) -> str:
        return "feature_release"

    @property
    def description(self) -> str:
        return "Streamlined feature release workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="feature_review",
                agent="Blueprint",
                task_type="feature_prioritization",
                description="Review feature for release readiness",
                context_builder=lambda ctx: {
                    "feature_name": ctx.get("feature_name"),
                    "feature_id": ctx.get("feature_id"),
                    "description": ctx.get("description"),
                    "product_id": ctx.get("product_id"),
                    "features": [ctx.get("feature_name")] if ctx.get("feature_name") else [],
                },
            ),
            WorkflowStep(
                name="security_check",
                agent="Citadel",
                task_type="security_assessment",
                description="Quick security review of feature",
                depends_on=["feature_review"],
                required=False,  # Optional - only for security-relevant features
                context_builder=lambda ctx: {
                    "feature_name": ctx.get("feature_name"),
                    "feature_review": ctx.step_results.get("feature_review"),
                    "security_relevant": ctx.get("security_relevant", False),
                },
            ),
            WorkflowStep(
                name="release_execution",
                agent="Foundry",
                task_type="release_coordination",
                description="Execute the feature release",
                depends_on=["feature_review"],
                context_builder=lambda ctx: {
                    "feature_name": ctx.get("feature_name"),
                    "feature_id": ctx.get("feature_id"),
                    "version": ctx.get("version"),
                    "release_type": "feature",
                    "feature_review": ctx.step_results.get("feature_review"),
                },
            ),
            WorkflowStep(
                name="adoption_tracking",
                agent="Vector",
                task_type="feature_adoption_metrics",
                description="Set up feature adoption tracking",
                depends_on=["release_execution"],
                required=False,
                context_builder=lambda ctx: {
                    "feature_name": ctx.get("feature_name"),
                    "feature_id": ctx.get("feature_id"),
                    "product_id": ctx.get("product_id"),
                    "release_info": ctx.step_results.get("release_execution"),
                },
            ),
        ]


class SprintPlanningWorkflow(Workflow):
    """
    Workflow for agile sprint planning.

    Coordinates across:
    - Foundry (Foundry): Sprint execution planning
    - Blueprint (Blueprint): Backlog prioritization
    - Forge (Forge): Technical guidance

    Steps:
    1. Backlog Review - Blueprint reviews and prioritizes backlog
    2. Technical Assessment - Forge provides technical guidance
    3. Capacity Planning - Foundry calculates team capacity
    4. Sprint Scope - Foundry defines sprint scope
    5. Task Breakdown - Foundry breaks down user stories
    6. Sprint Commitment - Foundry finalizes sprint plan
    """

    @property
    def name(self) -> str:
        return "sprint_planning"

    @property
    def description(self) -> str:
        return "Agile sprint planning and commitment"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="backlog_review",
                agent="Blueprint",
                task_type="backlog_grooming",
                description="Review and prioritize product backlog",
                context_builder=lambda ctx: {
                    "sprint_number": ctx.get("sprint_number"),
                    "sprint_goal": ctx.get("sprint_goal"),
                    "backlog_items": ctx.get("backlog_items", []),
                    "product_priorities": ctx.get("product_priorities", []),
                },
            ),
            WorkflowStep(
                name="technical_assessment",
                agent="Forge",
                task_type="architecture",
                description="Provide technical guidance and identify risks",
                depends_on=["backlog_review"],
                context_builder=lambda ctx: {
                    "prioritized_backlog": ctx.step_results.get("backlog_review"),
                    "technical_debt": ctx.get("technical_debt", []),
                    "dependencies": ctx.get("dependencies", []),
                },
            ),
            WorkflowStep(
                name="capacity_planning",
                agent="Foundry",
                task_type="sprint_planning",
                description="Calculate team capacity for sprint",
                context_builder=lambda ctx: {
                    "team_members": ctx.get("team_members", []),
                    "sprint_duration": ctx.get("sprint_duration", 14),
                    "holidays": ctx.get("holidays", []),
                    "pto": ctx.get("pto", []),
                },
            ),
            WorkflowStep(
                name="sprint_scope",
                agent="Foundry",
                task_type="sprint_planning",
                description="Define sprint scope based on capacity and priorities",
                depends_on=["backlog_review", "technical_assessment", "capacity_planning"],
                context_builder=lambda ctx: {
                    "prioritized_backlog": ctx.step_results.get("backlog_review"),
                    "technical_guidance": ctx.step_results.get("technical_assessment"),
                    "capacity": ctx.step_results.get("capacity_planning"),
                    "sprint_goal": ctx.get("sprint_goal"),
                },
            ),
            WorkflowStep(
                name="task_breakdown",
                agent="Foundry",
                task_type="backlog_management",
                description="Break down user stories into tasks",
                depends_on=["sprint_scope"],
                context_builder=lambda ctx: {
                    "sprint_items": ctx.step_results.get("sprint_scope"),
                    "estimation_method": ctx.get("estimation_method", "story_points"),
                },
            ),
            WorkflowStep(
                name="sprint_commitment",
                agent="Foundry",
                task_type="sprint_planning",
                description="Finalize sprint plan and commitment",
                depends_on=["sprint_scope", "task_breakdown"],
                context_builder=lambda ctx: {
                    "sprint_scope": ctx.step_results.get("sprint_scope"),
                    "task_breakdown": ctx.step_results.get("task_breakdown"),
                    "sprint_number": ctx.get("sprint_number"),
                    "sprint_goal": ctx.get("sprint_goal"),
                    "start_date": ctx.get("start_date"),
                },
            ),
        ]


class TechnologyMigrationWorkflow(Workflow):
    """
    Workflow for technology/infrastructure migration.

    Coordinates across:
    - Forge (Forge): Migration strategy
    - Foundry (Foundry): Execution planning
    - Citadel (Citadel): Security validation
    - Aegis (Aegis): Risk assessment
    - Keystone (Keystone): Cost analysis

    Steps:
    1. Migration Strategy - Forge defines migration approach
    2. Risk Assessment - Aegis evaluates migration risks
    3. Security Planning - Citadel plans security measures
    4. Cost Analysis - Keystone analyzes migration costs
    5. Execution Plan - Foundry creates detailed execution plan
    6. Rollback Plan - Foundry prepares rollback strategy
    """

    @property
    def name(self) -> str:
        return "technology_migration"

    @property
    def description(self) -> str:
        return "Technology or infrastructure migration planning"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="migration_strategy",
                agent="Forge",
                task_type="architecture",
                description="Define migration strategy and approach",
                context_builder=lambda ctx: {
                    "source_system": ctx.get("source_system"),
                    "target_system": ctx.get("target_system"),
                    "migration_type": ctx.get("migration_type", "lift_and_shift"),
                    "requirements": ctx.get("requirements", []),
                },
            ),
            WorkflowStep(
                name="risk_assessment",
                agent="Aegis",
                task_type="risk_assessment",
                description="Evaluate migration risks",
                depends_on=["migration_strategy"],
                context_builder=lambda ctx: {
                    "migration_strategy": ctx.step_results.get("migration_strategy"),
                    "criticality": ctx.get("criticality", "high"),
                    "downtime_tolerance": ctx.get("downtime_tolerance"),
                },
            ),
            WorkflowStep(
                name="security_planning",
                agent="Citadel",
                task_type="security_assessment",
                description="Plan security measures for migration",
                depends_on=["migration_strategy"],
                context_builder=lambda ctx: {
                    "migration_strategy": ctx.step_results.get("migration_strategy"),
                    "security_requirements": ctx.get("security_requirements", []),
                    "data_sensitivity": ctx.get("data_sensitivity", "confidential"),
                },
            ),
            WorkflowStep(
                name="cost_analysis",
                agent="Keystone",
                task_type="cost_analysis",
                description="Analyze migration costs and ROI",
                depends_on=["migration_strategy"],
                context_builder=lambda ctx: {
                    "migration_strategy": ctx.step_results.get("migration_strategy"),
                    "current_costs": ctx.get("current_costs", {}),
                    "budget_constraint": ctx.get("budget_constraint"),
                },
            ),
            WorkflowStep(
                name="execution_plan",
                agent="Foundry",
                task_type="deployment_planning",
                description="Create detailed execution plan",
                depends_on=[
                    "migration_strategy",
                    "risk_assessment",
                    "security_planning",
                    "cost_analysis",
                ],
                context_builder=lambda ctx: {
                    "migration_strategy": ctx.step_results.get("migration_strategy"),
                    "risk_assessment": ctx.step_results.get("risk_assessment"),
                    "security_plan": ctx.step_results.get("security_planning"),
                    "cost_analysis": ctx.step_results.get("cost_analysis"),
                    "timeline": ctx.get("timeline"),
                },
            ),
            WorkflowStep(
                name="rollback_plan",
                agent="Foundry",
                task_type="rollback_execution",
                description="Prepare rollback strategy",
                depends_on=["execution_plan"],
                context_builder=lambda ctx: {
                    "execution_plan": ctx.step_results.get("execution_plan"),
                    "recovery_time_objective": ctx.get("recovery_time_objective"),
                    "rollback_triggers": ctx.get("rollback_triggers", []),
                },
            ),
        ]


class TechDebtReviewWorkflow(Workflow):
    """
    Forge internal workflow for technical debt assessment.

    Steps:
    1. Debt Inventory - Catalog existing technical debt
    2. Impact Analysis - Assess impact of each debt item
    3. Prioritization - Prioritize debt by business impact
    4. Remediation Plan - Create debt paydown plan
    5. Architecture Recommendations - Suggest architectural improvements
    """

    @property
    def name(self) -> str:
        return "tech_debt_review"

    @property
    def description(self) -> str:
        return "Forge technical debt assessment and remediation planning"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="debt_inventory",
                agent="Forge",
                task_type="tech_debt",
                description="Catalog existing technical debt",
                context_builder=lambda ctx: {
                    "codebase_areas": ctx.get("codebase_areas", []),
                    "debt_categories": ctx.get(
                        "debt_categories",
                        [
                            "code_quality",
                            "dependencies",
                            "architecture",
                            "testing",
                            "documentation",
                        ],
                    ),
                },
            ),
            WorkflowStep(
                name="impact_analysis",
                agent="Forge",
                task_type="architecture",
                description="Assess impact of technical debt items",
                depends_on=["debt_inventory"],
                context_builder=lambda ctx: {
                    "debt_items": ctx.step_results.get("debt_inventory"),
                    "impact_criteria": ctx.get(
                        "impact_criteria",
                        ["velocity", "reliability", "security", "maintainability"],
                    ),
                },
            ),
            WorkflowStep(
                name="prioritization",
                agent="Forge",
                task_type="tech_debt",
                description="Prioritize debt by business impact",
                depends_on=["impact_analysis"],
                context_builder=lambda ctx: {
                    "impact_analysis": ctx.step_results.get("impact_analysis"),
                    "business_priorities": ctx.get("business_priorities", []),
                    "capacity": ctx.get("engineering_capacity"),
                },
            ),
            WorkflowStep(
                name="remediation_plan",
                agent="Forge",
                task_type="tech_debt",
                description="Create debt paydown plan",
                depends_on=["prioritization"],
                context_builder=lambda ctx: {
                    "prioritized_debt": ctx.step_results.get("prioritization"),
                    "budget_allocation": ctx.get("budget_allocation"),
                    "timeline": ctx.get("timeline", "quarter"),
                },
            ),
            WorkflowStep(
                name="architecture_recommendations",
                agent="Forge",
                task_type="architecture",
                description="Suggest architectural improvements",
                depends_on=["remediation_plan"],
                context_builder=lambda ctx: {
                    "remediation_plan": ctx.step_results.get("remediation_plan"),
                    "current_architecture": ctx.get("current_architecture", {}),
                    "target_state": ctx.get("target_state", {}),
                },
            ),
        ]


class CodeQualityWorkflow(Workflow):
    """
    Foundry internal workflow for code quality assessment.

    Steps:
    1. Static Analysis - Run static code analysis
    2. Test Coverage - Analyze test coverage
    3. Performance Profiling - Profile code performance
    4. Quality Metrics - Calculate quality metrics
    5. Improvement Recommendations - Generate recommendations
    """

    @property
    def name(self) -> str:
        return "code_quality"

    @property
    def description(self) -> str:
        return "Foundry code quality assessment workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="static_analysis",
                agent="Foundry",
                task_type="code_review",
                description="Run static code analysis",
                context_builder=lambda ctx: {
                    "repositories": ctx.get("repositories", []),
                    "analysis_tools": ctx.get("analysis_tools", ["eslint", "pylint", "sonar"]),
                    "severity_threshold": ctx.get("severity_threshold", "warning"),
                },
            ),
            WorkflowStep(
                name="test_coverage",
                agent="Foundry",
                task_type="testing",
                description="Analyze test coverage",
                context_builder=lambda ctx: {
                    "repositories": ctx.get("repositories", []),
                    "coverage_target": ctx.get("coverage_target", 80),
                    "test_types": ctx.get("test_types", ["unit", "integration"]),
                },
            ),
            WorkflowStep(
                name="performance_profiling",
                agent="Foundry",
                task_type="performance_optimization",
                description="Profile code performance",
                depends_on=["static_analysis"],
                context_builder=lambda ctx: {
                    "static_results": ctx.step_results.get("static_analysis"),
                    "hot_paths": ctx.get("hot_paths", []),
                    "performance_targets": ctx.get("performance_targets", {}),
                },
            ),
            WorkflowStep(
                name="quality_metrics",
                agent="Foundry",
                task_type="code_review",
                description="Calculate quality metrics",
                depends_on=["static_analysis", "test_coverage", "performance_profiling"],
                context_builder=lambda ctx: {
                    "static_analysis": ctx.step_results.get("static_analysis"),
                    "coverage": ctx.step_results.get("test_coverage"),
                    "performance": ctx.step_results.get("performance_profiling"),
                },
            ),
            WorkflowStep(
                name="improvement_recommendations",
                agent="Foundry",
                task_type="code_review",
                description="Generate quality improvement recommendations",
                depends_on=["quality_metrics"],
                context_builder=lambda ctx: {
                    "metrics": ctx.step_results.get("quality_metrics"),
                    "priority_areas": ctx.get("priority_areas", []),
                    "resource_allocation": ctx.get("resource_allocation"),
                },
            ),
        ]


class InfrastructureHealthWorkflow(Workflow):
    """
    Sentinel internal workflow for infrastructure health monitoring.

    Steps:
    1. System Health - Check system health metrics
    2. Capacity Analysis - Analyze capacity utilization
    3. Performance Metrics - Review performance metrics
    4. Cost Analysis - Analyze infrastructure costs
    5. Optimization Plan - Create optimization plan
    """

    @property
    def name(self) -> str:
        return "infrastructure_health"

    @property
    def description(self) -> str:
        return "Sentinel infrastructure health monitoring workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="system_health",
                agent="Sentinel",
                task_type="system_health_check",
                description="Check overall system health metrics",
                context_builder=lambda ctx: {
                    "systems": ctx.get("systems", []),
                    "health_metrics": ctx.get("health_metrics", ["uptime", "latency", "errors"]),
                    "monitoring_window": ctx.get("monitoring_window", "24h"),
                },
            ),
            WorkflowStep(
                name="capacity_analysis",
                agent="Sentinel",
                task_type="capacity_planning",
                description="Analyze capacity utilization",
                depends_on=["system_health"],
                context_builder=lambda ctx: {
                    "health_status": ctx.step_results.get("system_health"),
                    "capacity_dimensions": ctx.get(
                        "capacity_dimensions", ["compute", "storage", "network"]
                    ),
                    "utilization_thresholds": ctx.get("utilization_thresholds", {}),
                },
            ),
            WorkflowStep(
                name="performance_metrics",
                agent="Sentinel",
                task_type="performance_monitoring",
                description="Review detailed performance metrics",
                depends_on=["system_health"],
                context_builder=lambda ctx: {
                    "health_status": ctx.step_results.get("system_health"),
                    "performance_slas": ctx.get("performance_slas", {}),
                    "critical_paths": ctx.get("critical_paths", []),
                },
            ),
            WorkflowStep(
                name="cost_analysis",
                agent="Sentinel",
                task_type="it_cost_optimization",
                description="Analyze infrastructure costs",
                depends_on=["capacity_analysis"],
                context_builder=lambda ctx: {
                    "capacity_data": ctx.step_results.get("capacity_analysis"),
                    "cost_centers": ctx.get("cost_centers", []),
                    "budget": ctx.get("budget", {}),
                },
            ),
            WorkflowStep(
                name="optimization_plan",
                agent="Sentinel",
                task_type="infrastructure_optimization",
                description="Create infrastructure optimization plan",
                depends_on=["capacity_analysis", "performance_metrics", "cost_analysis"],
                context_builder=lambda ctx: {
                    "capacity": ctx.step_results.get("capacity_analysis"),
                    "performance": ctx.step_results.get("performance_metrics"),
                    "costs": ctx.step_results.get("cost_analysis"),
                    "optimization_targets": ctx.get("optimization_targets", []),
                },
            ),
        ]


class CodeEvaluationDeploymentWorkflow(Workflow):
    """
    Multi-stage pipeline: Evaluate -> Correct -> Secure -> Test -> Build -> Deploy.

    Orchestrated by Nexus, recruiting specialists from Forge, Citadel, Foundry.
    Used by the Workbench module for full code-to-production pipelines.

    Stages:
    1. Code Evaluation - Forge: CodeReviewer analyzes code quality and patterns
    2. Security Review - Forge: SecurityArchitect reviews for vulnerabilities
    3. Code Correction - Forge: SeniorDeveloper fixes issues found
    4. SAST Scan - Citadel: AppSecEngineer performs static analysis
    5. Dependency Scan - Citadel: VulnerabilityAnalyst checks dependencies
    6. Test Planning - Foundry: QAEngineer creates test strategy
    7. Test Execution - Foundry: QAAutomationEngineer runs tests
    8. Quality Gate - Foundry: QualityManager validates quality metrics
    9. Build - Foundry: BuildEngineer creates artifacts
    10. Containerize - Forge: DevOpsEngineer creates container image
    11. Deploy - Foundry: DeploymentEngineer deploys to target
    """

    @property
    def name(self) -> str:
        return "code_evaluation_deployment"

    @property
    def description(self) -> str:
        return "Full code evaluation, correction, testing, and deployment pipeline"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            # Stage 1: Code Evaluation
            WorkflowStep(
                name="code_review",
                agent="Forge",
                task_type="code_review",
                description="Analyze code quality, patterns, and identify issues",
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "code_path": ctx.get("code_path", "/workspace"),
                    "review_scope": ctx.get("review_scope", "full"),
                    "language": ctx.get("language"),
                    "focus_areas": ctx.get("focus_areas", []),
                },
            ),
            WorkflowStep(
                name="security_review",
                agent="Forge",
                task_type="security_review",
                description="Review code for security vulnerabilities and best practices",
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "code_path": ctx.get("code_path", "/workspace"),
                    "security_standards": ctx.get("security_standards", ["OWASP"]),
                },
            ),
            # Stage 2: Code Correction (depends on evaluation)
            WorkflowStep(
                name="bug_fix",
                agent="Forge",
                task_type="bug_fix",
                description="Fix issues identified in code and security reviews",
                depends_on=["code_review", "security_review"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "code_review_results": ctx.step_results.get("code_review"),
                    "security_review_results": ctx.step_results.get("security_review"),
                    "auto_fix": ctx.get("auto_fix", True),
                },
            ),
            # Stage 3: Security Scanning
            WorkflowStep(
                name="sast_scan",
                agent="Citadel",
                task_type="sast_scan",
                description="Perform static application security testing",
                depends_on=["bug_fix"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "code_path": ctx.get("code_path", "/workspace"),
                    "scan_profile": ctx.get("scan_profile", "standard"),
                },
            ),
            WorkflowStep(
                name="dependency_scan",
                agent="Citadel",
                task_type="dependency_scan",
                description="Scan dependencies for known vulnerabilities",
                depends_on=["bug_fix"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "manifest_files": ctx.get("manifest_files", []),
                    "severity_threshold": ctx.get("severity_threshold", "high"),
                },
            ),
            # Stage 4: Testing
            WorkflowStep(
                name="test_planning",
                agent="Foundry",
                task_type="test_planning",
                description="Create test strategy and test cases",
                depends_on=["sast_scan", "dependency_scan"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "code_review_results": ctx.step_results.get("code_review"),
                    "test_types": ctx.get("test_types", ["unit", "integration"]),
                },
            ),
            WorkflowStep(
                name="test_execution",
                agent="Foundry",
                task_type="test_execution",
                description="Execute planned tests",
                depends_on=["test_planning"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "test_plan": ctx.step_results.get("test_planning"),
                    "coverage_target": ctx.get("coverage_target", 80),
                },
            ),
            WorkflowStep(
                name="quality_gate",
                agent="Foundry",
                task_type="quality_gate_check",
                description="Validate code meets quality gate criteria",
                depends_on=["test_execution"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "test_results": ctx.step_results.get("test_execution"),
                    "sast_results": ctx.step_results.get("sast_scan"),
                    "quality_thresholds": ctx.get("quality_thresholds", {}),
                },
            ),
            # Stage 5: Build
            WorkflowStep(
                name="build",
                agent="Foundry",
                task_type="build_management",
                description="Build application artifacts",
                depends_on=["quality_gate"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "build_config": ctx.get("build_config", {}),
                    "artifact_type": ctx.get("artifact_type", "binary"),
                },
            ),
            WorkflowStep(
                name="containerize",
                agent="Forge",
                task_type="containerization",
                description="Create container image from build artifacts",
                depends_on=["build"],
                required=False,  # Only if deployment_target requires containers
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "build_artifacts": ctx.step_results.get("build"),
                    "base_image": ctx.get("base_image"),
                    "registry": ctx.get("docker_registry"),
                },
            ),
            # Stage 6: Deployment
            WorkflowStep(
                name="deploy",
                agent="Foundry",
                task_type="deployment_execution",
                description="Deploy to target environment",
                depends_on=["containerize"],
                context_builder=lambda ctx: {
                    "workspace_id": ctx.get("workspace_id"),
                    "deployment_target": ctx.get("deployment_target", "local"),
                    "container_image": ctx.step_results.get("containerize"),
                    "build_artifacts": ctx.step_results.get("build"),
                    "environment_config": ctx.get("environment_config", {}),
                },
            ),
        ]
