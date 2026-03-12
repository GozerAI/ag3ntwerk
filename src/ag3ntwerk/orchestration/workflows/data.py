"""
Data & Analytics Workflows.

Workflows for data quality, data pipeline monitoring, experiment cycles,
feature prioritization, and brand health.
"""

from typing import Any, Dict, List

from ag3ntwerk.orchestration.base import Workflow, WorkflowStep


class DataQualityWorkflow(Workflow):
    """
    Workflow for data quality assessment and improvement.

    Coordinates across:
    - Index (Index): Data governance and quality
    - Forge (Forge): Technical data infrastructure
    - Axiom (Axiom): Data analysis and validation

    Steps:
    1. Data Profiling - Index profiles data sources
    2. Quality Assessment - Index assesses data quality metrics
    3. Technical Review - Forge reviews data infrastructure
    4. Validation Analysis - Axiom performs statistical validation
    5. Governance Review - Index reviews data governance policies
    6. Improvement Plan - Index creates data quality improvement plan
    """

    @property
    def name(self) -> str:
        return "data_quality"

    @property
    def description(self) -> str:
        return "Data quality assessment and improvement workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="data_profiling",
                agent="Index",
                task_type="data_profiling",
                description="Profile data sources and structure",
                context_builder=lambda ctx: {
                    "data_sources": ctx.get("data_sources", []),
                    "profiling_scope": ctx.get("profiling_scope", "full"),
                    "sample_size": ctx.get("sample_size", 10000),
                },
            ),
            WorkflowStep(
                name="quality_assessment",
                agent="Index",
                task_type="data_quality_check",
                description="Assess data quality metrics",
                depends_on=["data_profiling"],
                context_builder=lambda ctx: {
                    "profiling_results": ctx.step_results.get("data_profiling"),
                    "quality_dimensions": ctx.get(
                        "quality_dimensions",
                        ["completeness", "accuracy", "consistency", "timeliness"],
                    ),
                },
            ),
            WorkflowStep(
                name="technical_review",
                agent="Forge",
                task_type="architecture",
                description="Review data infrastructure and pipelines",
                depends_on=["data_profiling"],
                context_builder=lambda ctx: {
                    "data_sources": ctx.get("data_sources", []),
                    "profiling_results": ctx.step_results.get("data_profiling"),
                    "infrastructure_scope": ctx.get("infrastructure_scope", []),
                },
            ),
            WorkflowStep(
                name="validation_analysis",
                agent="Axiom",
                task_type="data_analysis",
                description="Perform statistical validation of data",
                depends_on=["quality_assessment"],
                context_builder=lambda ctx: {
                    "quality_results": ctx.step_results.get("quality_assessment"),
                    "validation_rules": ctx.get("validation_rules", []),
                    "statistical_tests": ctx.get("statistical_tests", []),
                },
            ),
            WorkflowStep(
                name="governance_review",
                agent="Index",
                task_type="data_governance",
                description="Review data governance policies",
                depends_on=["quality_assessment", "validation_analysis"],
                context_builder=lambda ctx: {
                    "quality_results": ctx.step_results.get("quality_assessment"),
                    "validation_results": ctx.step_results.get("validation_analysis"),
                    "governance_policies": ctx.get("governance_policies", []),
                },
            ),
            WorkflowStep(
                name="improvement_plan",
                agent="Index",
                task_type="data_lineage",
                description="Create data quality improvement plan",
                depends_on=["quality_assessment", "technical_review", "governance_review"],
                context_builder=lambda ctx: {
                    "all_findings": {
                        "quality": ctx.step_results.get("quality_assessment"),
                        "technical": ctx.step_results.get("technical_review"),
                        "governance": ctx.step_results.get("governance_review"),
                    },
                    "priority_areas": ctx.get("priority_areas", []),
                    "timeline": ctx.get("improvement_timeline", "90_days"),
                },
            ),
        ]


class DataPipelineMonitoringWorkflow(Workflow):
    """
    Index internal workflow for data pipeline monitoring.

    Steps:
    1. Pipeline Health - Check pipeline health status
    2. Data Freshness - Verify data freshness
    3. Quality Gates - Run data quality gates
    4. Anomaly Detection - Detect data anomalies
    5. Pipeline Optimization - Recommend optimizations
    """

    @property
    def name(self) -> str:
        return "data_pipeline_monitoring"

    @property
    def description(self) -> str:
        return "Index data pipeline monitoring workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="pipeline_health",
                agent="Index",
                task_type="data_lineage",
                description="Check data pipeline health status",
                context_builder=lambda ctx: {
                    "pipelines": ctx.get("pipelines", []),
                    "health_metrics": ctx.get(
                        "health_metrics", ["latency", "throughput", "errors"]
                    ),
                    "monitoring_window": ctx.get("monitoring_window", "24h"),
                },
            ),
            WorkflowStep(
                name="data_freshness",
                agent="Index",
                task_type="data_quality_check",
                description="Verify data freshness across sources",
                depends_on=["pipeline_health"],
                context_builder=lambda ctx: {
                    "pipeline_status": ctx.step_results.get("pipeline_health"),
                    "freshness_slas": ctx.get("freshness_slas", {}),
                    "data_sources": ctx.get("data_sources", []),
                },
            ),
            WorkflowStep(
                name="quality_gates",
                agent="Index",
                task_type="data_quality_check",
                description="Run data quality gates",
                depends_on=["pipeline_health"],
                context_builder=lambda ctx: {
                    "pipeline_status": ctx.step_results.get("pipeline_health"),
                    "quality_rules": ctx.get("quality_rules", []),
                    "quality_thresholds": ctx.get("quality_thresholds", {}),
                },
            ),
            WorkflowStep(
                name="anomaly_detection",
                agent="Index",
                task_type="descriptive_analytics",
                description="Detect data anomalies",
                depends_on=["data_freshness", "quality_gates"],
                context_builder=lambda ctx: {
                    "freshness_results": ctx.step_results.get("data_freshness"),
                    "quality_results": ctx.step_results.get("quality_gates"),
                    "anomaly_rules": ctx.get("anomaly_rules", []),
                },
            ),
            WorkflowStep(
                name="pipeline_optimization",
                agent="Index",
                task_type="data_governance",
                description="Recommend pipeline optimizations",
                depends_on=["pipeline_health", "anomaly_detection"],
                context_builder=lambda ctx: {
                    "health_status": ctx.step_results.get("pipeline_health"),
                    "anomalies": ctx.step_results.get("anomaly_detection"),
                    "optimization_targets": ctx.get("optimization_targets", ["latency", "cost"]),
                },
            ),
        ]


class ExperimentCycleWorkflow(Workflow):
    """
    Axiom internal workflow for experiment lifecycle management.

    Steps:
    1. Hypothesis Formulation - Define experiment hypothesis
    2. Experiment Design - Design experiment methodology
    3. Sample Size Calculation - Calculate required sample
    4. Results Analysis - Analyze experiment results
    5. Conclusion Report - Generate experiment report
    """

    @property
    def name(self) -> str:
        return "experiment_cycle"

    @property
    def description(self) -> str:
        return "Axiom experiment lifecycle management workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="hypothesis_formulation",
                agent="Axiom",
                task_type="hypothesis_testing",
                description="Define and validate experiment hypothesis",
                context_builder=lambda ctx: {
                    "research_question": ctx.get("research_question"),
                    "hypothesis": ctx.get("hypothesis"),
                    "success_criteria": ctx.get("success_criteria", []),
                    "experiment_type": ctx.get("experiment_type", "ab_test"),
                },
            ),
            WorkflowStep(
                name="experiment_design",
                agent="Axiom",
                task_type="experiment_design",
                description="Design experiment methodology",
                depends_on=["hypothesis_formulation"],
                context_builder=lambda ctx: {
                    "hypothesis": ctx.step_results.get("hypothesis_formulation"),
                    "variables": ctx.get("variables", {}),
                    "control_group": ctx.get("control_group", {}),
                    "duration": ctx.get("duration"),
                },
            ),
            WorkflowStep(
                name="sample_size_calculation",
                agent="Axiom",
                task_type="statistical_analysis",
                description="Calculate required sample size",
                depends_on=["experiment_design"],
                context_builder=lambda ctx: {
                    "design": ctx.step_results.get("experiment_design"),
                    "confidence_level": ctx.get("confidence_level", 0.95),
                    "power": ctx.get("statistical_power", 0.8),
                    "minimum_effect": ctx.get("minimum_effect"),
                },
            ),
            WorkflowStep(
                name="results_analysis",
                agent="Axiom",
                task_type="statistical_analysis",
                description="Analyze experiment results",
                depends_on=["sample_size_calculation"],
                context_builder=lambda ctx: {
                    "experiment_data": ctx.get("experiment_data", {}),
                    "design": ctx.step_results.get("experiment_design"),
                    "sample_requirements": ctx.step_results.get("sample_size_calculation"),
                    "analysis_methods": ctx.get("analysis_methods", ["t_test", "chi_square"]),
                },
            ),
            WorkflowStep(
                name="conclusion_report",
                agent="Axiom",
                task_type="findings_report",
                description="Generate experiment conclusion report",
                depends_on=["results_analysis"],
                context_builder=lambda ctx: {
                    "hypothesis": ctx.step_results.get("hypothesis_formulation"),
                    "design": ctx.step_results.get("experiment_design"),
                    "results": ctx.step_results.get("results_analysis"),
                    "recommendations": ctx.get("include_recommendations", True),
                },
            ),
        ]


class FeaturePrioritizationWorkflow(Workflow):
    """
    Blueprint internal workflow for feature prioritization.

    Steps:
    1. Feature Inventory - Catalog feature requests
    2. Value Assessment - Assess business value
    3. Effort Estimation - Estimate implementation effort
    4. Prioritization Matrix - Build priority matrix
    5. Roadmap Update - Update product roadmap
    """

    @property
    def name(self) -> str:
        return "feature_prioritization"

    @property
    def description(self) -> str:
        return "Blueprint feature prioritization workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="feature_inventory",
                agent="Blueprint",
                task_type="backlog_grooming",
                description="Catalog and categorize feature requests",
                context_builder=lambda ctx: {
                    "feature_sources": ctx.get("feature_sources", ["feedback", "sales", "support"]),
                    "time_period": ctx.get("time_period", "last_quarter"),
                    "categories": ctx.get("categories", []),
                },
            ),
            WorkflowStep(
                name="value_assessment",
                agent="Blueprint",
                task_type="user_story_creation",
                description="Assess business value of features",
                depends_on=["feature_inventory"],
                context_builder=lambda ctx: {
                    "features": ctx.step_results.get("feature_inventory"),
                    "value_criteria": ctx.get(
                        "value_criteria",
                        ["revenue_impact", "user_retention", "market_differentiation"],
                    ),
                    "customer_segments": ctx.get("customer_segments", []),
                },
            ),
            WorkflowStep(
                name="effort_estimation",
                agent="Blueprint",
                task_type="product_spec",
                description="Estimate implementation effort",
                depends_on=["feature_inventory"],
                context_builder=lambda ctx: {
                    "features": ctx.step_results.get("feature_inventory"),
                    "estimation_method": ctx.get("estimation_method", "t_shirt"),
                    "team_capacity": ctx.get("team_capacity"),
                },
            ),
            WorkflowStep(
                name="prioritization_matrix",
                agent="Blueprint",
                task_type="feature_prioritization",
                description="Build priority matrix (value vs effort)",
                depends_on=["value_assessment", "effort_estimation"],
                context_builder=lambda ctx: {
                    "value_scores": ctx.step_results.get("value_assessment"),
                    "effort_scores": ctx.step_results.get("effort_estimation"),
                    "prioritization_framework": ctx.get("framework", "rice"),
                },
            ),
            WorkflowStep(
                name="roadmap_update",
                agent="Blueprint",
                task_type="roadmap_update",
                description="Update product roadmap",
                depends_on=["prioritization_matrix"],
                context_builder=lambda ctx: {
                    "priorities": ctx.step_results.get("prioritization_matrix"),
                    "current_roadmap": ctx.get("current_roadmap", {}),
                    "planning_horizon": ctx.get("planning_horizon", "6_months"),
                },
            ),
        ]


class BrandHealthWorkflow(Workflow):
    """
    Echo internal workflow for brand health monitoring.

    Steps:
    1. Brand Awareness - Measure brand awareness
    2. Sentiment Analysis - Analyze brand sentiment
    3. Competitive Position - Analyze competitive positioning
    4. Channel Performance - Review channel performance
    5. Brand Strategy - Update brand strategy
    """

    @property
    def name(self) -> str:
        return "brand_health"

    @property
    def description(self) -> str:
        return "Echo brand health monitoring workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="brand_awareness",
                agent="Echo",
                task_type="brand_strategy",
                description="Measure brand awareness metrics",
                context_builder=lambda ctx: {
                    "measurement_channels": ctx.get(
                        "measurement_channels", ["survey", "social", "search"]
                    ),
                    "target_audience": ctx.get("target_audience", {}),
                    "time_period": ctx.get("time_period", "last_quarter"),
                },
            ),
            WorkflowStep(
                name="sentiment_analysis",
                agent="Echo",
                task_type="marketing_analytics",
                description="Analyze brand sentiment across channels",
                depends_on=["brand_awareness"],
                context_builder=lambda ctx: {
                    "awareness_data": ctx.step_results.get("brand_awareness"),
                    "sentiment_sources": ctx.get(
                        "sentiment_sources", ["social", "reviews", "surveys"]
                    ),
                    "sentiment_aspects": ctx.get("sentiment_aspects", []),
                },
            ),
            WorkflowStep(
                name="competitive_position",
                agent="Echo",
                task_type="competitive_analysis",
                description="Analyze competitive brand positioning",
                depends_on=["brand_awareness"],
                context_builder=lambda ctx: {
                    "awareness_data": ctx.step_results.get("brand_awareness"),
                    "competitors": ctx.get("competitors", []),
                    "positioning_dimensions": ctx.get("positioning_dimensions", []),
                },
            ),
            WorkflowStep(
                name="channel_performance",
                agent="Echo",
                task_type="marketing_analytics",
                description="Review marketing channel performance",
                depends_on=["sentiment_analysis"],
                context_builder=lambda ctx: {
                    "sentiment_data": ctx.step_results.get("sentiment_analysis"),
                    "channels": ctx.get("channels", []),
                    "performance_metrics": ctx.get(
                        "performance_metrics", ["reach", "engagement", "conversion"]
                    ),
                },
            ),
            WorkflowStep(
                name="brand_strategy",
                agent="Echo",
                task_type="brand_strategy",
                description="Update brand strategy recommendations",
                depends_on=["sentiment_analysis", "competitive_position", "channel_performance"],
                context_builder=lambda ctx: {
                    "sentiment": ctx.step_results.get("sentiment_analysis"),
                    "competitive": ctx.step_results.get("competitive_position"),
                    "channels": ctx.step_results.get("channel_performance"),
                    "strategic_priorities": ctx.get("strategic_priorities", []),
                },
            ),
        ]
