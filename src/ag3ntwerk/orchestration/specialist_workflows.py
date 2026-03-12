"""
Specialist Workflows.

Single-task focused workflows designed to leverage specialist agents
for highly focused operations. Each workflow represents a single,
well-defined task that a specialist excels at.
"""

from typing import Any, Dict, List

from ag3ntwerk.orchestration.base import Workflow, WorkflowContext, WorkflowStep


# =============================================================================
# Keystone Specialist Workflows
# =============================================================================


class FinancialModelingWorkflow(Workflow):
    """Single-task workflow for financial modeling via specialist."""

    @property
    def name(self) -> str:
        return "financial_modeling"

    @property
    def description(self) -> str:
        return "Create financial models and projections"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="model",
                agent="Keystone",
                task_type="financial_modeling",
                description="Build financial model with projections",
                context_builder=lambda ctx: {
                    "model_type": ctx.get("model_type", "dcf"),
                    "time_horizon": ctx.get("time_horizon", "5 years"),
                    "assumptions": ctx.get("assumptions", {}),
                    "data": ctx.get("financial_data", {}),
                },
            ),
        ]


class CostAllocationWorkflow(Workflow):
    """Single-task workflow for cost allocation analysis."""

    @property
    def name(self) -> str:
        return "cost_allocation"

    @property
    def description(self) -> str:
        return "Analyze and allocate costs across departments"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="allocate",
                agent="Keystone",
                task_type="cost_allocation",
                description="Allocate costs to departments/projects",
                context_builder=lambda ctx: {
                    "cost_data": ctx.get("cost_data", {}),
                    "allocation_method": ctx.get("allocation_method", "activity_based"),
                    "departments": ctx.get("departments", []),
                },
            ),
        ]


class InvestmentAnalysisWorkflow(Workflow):
    """Single-task workflow for investment evaluation."""

    @property
    def name(self) -> str:
        return "investment_analysis"

    @property
    def description(self) -> str:
        return "Evaluate investment opportunities with ROI analysis"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="evaluate",
                agent="Keystone",
                task_type="investment_evaluation",
                description="Evaluate investment with NPV, IRR, payback",
                context_builder=lambda ctx: {
                    "investment": ctx.get("investment", {}),
                    "cash_flows": ctx.get("cash_flows", []),
                    "discount_rate": ctx.get("discount_rate", 0.1),
                },
            ),
        ]


# =============================================================================
# Forge Specialist Workflows
# =============================================================================


class CodeReviewWorkflow(Workflow):
    """Single-task workflow for code review."""

    @property
    def name(self) -> str:
        return "code_review"

    @property
    def description(self) -> str:
        return "Perform comprehensive code review"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="review",
                agent="Forge",
                task_type="code_review",
                description="Review code for quality, security, and best practices",
                context_builder=lambda ctx: {
                    "code": ctx.get("code", ""),
                    "file": ctx.get("file_path", ""),
                    "language": ctx.get("language", "python"),
                },
            ),
        ]


class BugFixWorkflow(Workflow):
    """Single-task workflow for bug fixing."""

    @property
    def name(self) -> str:
        return "bug_fix"

    @property
    def description(self) -> str:
        return "Analyze and fix bugs in code"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="fix",
                agent="Forge",
                task_type="bug_fix",
                description="Diagnose and fix the bug",
                context_builder=lambda ctx: {
                    "code": ctx.get("code", ""),
                    "error": ctx.get("error_message", ""),
                    "symptoms": ctx.get("symptoms", ""),
                },
            ),
        ]


class TestGenerationWorkflow(Workflow):
    """Single-task workflow for test generation."""

    @property
    def name(self) -> str:
        return "test_generation"

    @property
    def description(self) -> str:
        return "Generate comprehensive tests for code"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="generate",
                agent="Forge",
                task_type="test_creation",
                description="Generate unit and integration tests",
                context_builder=lambda ctx: {
                    "code": ctx.get("code", ""),
                    "test_type": ctx.get("test_type", "unit"),
                    "framework": ctx.get("framework", "pytest"),
                },
            ),
        ]


class DeploymentPlanningWorkflow(Workflow):
    """Single-task workflow for deployment planning."""

    @property
    def name(self) -> str:
        return "deployment_planning"

    @property
    def description(self) -> str:
        return "Plan deployment strategy and configuration"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="plan",
                agent="Forge",
                task_type="deployment",
                description="Create deployment plan with rollback strategy",
                context_builder=lambda ctx: {
                    "application": ctx.get("application", ""),
                    "environment": ctx.get("environment", "production"),
                    "strategy": ctx.get("strategy", "rolling"),
                },
            ),
        ]


# =============================================================================
# Echo Specialist Workflows
# =============================================================================


class ContentCreationWorkflow(Workflow):
    """Single-task workflow for content creation."""

    @property
    def name(self) -> str:
        return "content_creation"

    @property
    def description(self) -> str:
        return "Create marketing content"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="create",
                agent="Echo",
                task_type="content_creation",
                description="Create marketing content asset",
                context_builder=lambda ctx: {
                    "content_type": ctx.get("content_type", "blog"),
                    "topic": ctx.get("topic", ""),
                    "audience": ctx.get("audience", ""),
                    "tone": ctx.get("tone", "professional"),
                },
            ),
        ]


class SEOAnalysisWorkflow(Workflow):
    """Single-task workflow for SEO analysis."""

    @property
    def name(self) -> str:
        return "seo_analysis"

    @property
    def description(self) -> str:
        return "Analyze and optimize for search engines"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="analyze",
                agent="Echo",
                task_type="keyword_research",
                description="Perform keyword research and SEO analysis",
                context_builder=lambda ctx: {
                    "keywords": ctx.get("keywords", []),
                    "url": ctx.get("url", ""),
                    "competitors": ctx.get("competitors", []),
                },
            ),
        ]


class LeadGenerationWorkflow(Workflow):
    """Single-task workflow for lead generation planning."""

    @property
    def name(self) -> str:
        return "lead_generation"

    @property
    def description(self) -> str:
        return "Create lead generation strategy"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="generate",
                agent="Echo",
                task_type="lead_generation",
                description="Create lead generation plan",
                context_builder=lambda ctx: {
                    "target_audience": ctx.get("target_audience", ""),
                    "channels": ctx.get("channels", []),
                    "goals": ctx.get("goals", {}),
                },
            ),
        ]


# =============================================================================
# Blueprint Specialist Workflows
# =============================================================================


class UserStoryCreationWorkflow(Workflow):
    """Single-task workflow for user story creation."""

    @property
    def name(self) -> str:
        return "user_story_creation"

    @property
    def description(self) -> str:
        return "Create user stories with acceptance criteria"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="create",
                agent="Blueprint",
                task_type="user_story_writing",
                description="Write user stories with acceptance criteria",
                context_builder=lambda ctx: {
                    "feature": ctx.get("feature", ""),
                    "persona": ctx.get("persona", ""),
                    "goal": ctx.get("goal", ""),
                },
            ),
        ]


class FeatureScoringWorkflow(Workflow):
    """Single-task workflow for feature scoring."""

    @property
    def name(self) -> str:
        return "feature_scoring"

    @property
    def description(self) -> str:
        return "Score and prioritize features"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="score",
                agent="Blueprint",
                task_type="feature_scoring",
                description="Score features using RICE or similar framework",
                context_builder=lambda ctx: {
                    "features": ctx.get("features", []),
                    "framework": ctx.get("framework", "RICE"),
                    "criteria": ctx.get("criteria", {}),
                },
            ),
        ]


class BacklogRefinementWorkflow(Workflow):
    """Single-task workflow for backlog refinement."""

    @property
    def name(self) -> str:
        return "backlog_refinement"

    @property
    def description(self) -> str:
        return "Refine and groom product backlog"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="refine",
                agent="Blueprint",
                task_type="backlog_refinement",
                description="Refine backlog items",
                context_builder=lambda ctx: {
                    "backlog": ctx.get("backlog", []),
                    "sprint_goal": ctx.get("sprint_goal", ""),
                },
            ),
        ]


# =============================================================================
# Beacon Specialist Workflows
# =============================================================================


class FeedbackAnalysisWorkflow(Workflow):
    """Single-task workflow for feedback analysis."""

    @property
    def name(self) -> str:
        return "feedback_analysis"

    @property
    def description(self) -> str:
        return "Analyze customer feedback"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="analyze",
                agent="Beacon",
                task_type="feedback_analysis",
                description="Analyze and categorize customer feedback",
                context_builder=lambda ctx: {
                    "feedback_data": ctx.get("feedback_data", []),
                    "period": ctx.get("period", "monthly"),
                },
            ),
        ]


class ChurnPredictionWorkflow(Workflow):
    """Single-task workflow for churn prediction."""

    @property
    def name(self) -> str:
        return "churn_prediction"

    @property
    def description(self) -> str:
        return "Predict customer churn risk"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="predict",
                agent="Beacon",
                task_type="churn_prediction",
                description="Analyze churn risk factors",
                context_builder=lambda ctx: {
                    "customer_data": ctx.get("customer_data", {}),
                    "health_scores": ctx.get("health_scores", {}),
                },
            ),
        ]


class NPSAnalysisWorkflow(Workflow):
    """Single-task workflow for NPS analysis."""

    @property
    def name(self) -> str:
        return "nps_analysis"

    @property
    def description(self) -> str:
        return "Analyze Net Promoter Score data"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="analyze",
                agent="Beacon",
                task_type="nps_calculation",
                description="Calculate and analyze NPS",
                context_builder=lambda ctx: {
                    "nps_responses": ctx.get("nps_responses", []),
                    "segment": ctx.get("segment", "all"),
                },
            ),
        ]


class TicketTriageWorkflow(Workflow):
    """Single-task workflow for support ticket triage."""

    @property
    def name(self) -> str:
        return "ticket_triage"

    @property
    def description(self) -> str:
        return "Triage and classify support tickets"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="triage",
                agent="Beacon",
                task_type="ticket_triage",
                description="Classify and prioritize tickets",
                context_builder=lambda ctx: {
                    "tickets": ctx.get("tickets", []),
                },
            ),
        ]


# =============================================================================
# Index Specialist Workflows
# =============================================================================


class DataQualityCheckWorkflow(Workflow):
    """Single-task workflow for data quality check."""

    @property
    def name(self) -> str:
        return "data_quality_check"

    @property
    def description(self) -> str:
        return "Check data quality and identify issues"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="check",
                agent="Index",
                task_type="data_quality_check",
                description="Perform data quality assessment",
                context_builder=lambda ctx: {
                    "data_source": ctx.get("data_source", ""),
                    "rules": ctx.get("quality_rules", []),
                },
            ),
        ]


class SchemaValidationWorkflow(Workflow):
    """Single-task workflow for schema validation."""

    @property
    def name(self) -> str:
        return "schema_validation"

    @property
    def description(self) -> str:
        return "Validate data schema compliance"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="validate",
                agent="Index",
                task_type="schema_validation",
                description="Validate data against schema",
                context_builder=lambda ctx: {
                    "schema": ctx.get("schema", {}),
                    "data": ctx.get("data", {}),
                },
            ),
        ]


# =============================================================================
# Vector Specialist Workflows
# =============================================================================


class RevenueTrackingWorkflow(Workflow):
    """Single-task workflow for revenue tracking."""

    @property
    def name(self) -> str:
        return "revenue_tracking"

    @property
    def description(self) -> str:
        return "Track and analyze revenue performance"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="track",
                agent="Vector",
                task_type="revenue_tracking",
                description="Track revenue metrics and performance",
                context_builder=lambda ctx: {
                    "revenue_data": ctx.get("revenue_data", {}),
                    "period": ctx.get("period", "monthly"),
                    "product_id": ctx.get("product_id", ""),
                },
            ),
        ]


class ChurnAnalysisWorkflow(Workflow):
    """Single-task workflow for churn analysis."""

    @property
    def name(self) -> str:
        return "churn_analysis"

    @property
    def description(self) -> str:
        return "Analyze customer and revenue churn"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="analyze",
                agent="Vector",
                task_type="churn_analysis",
                description="Analyze churn patterns and drivers",
                context_builder=lambda ctx: {
                    "churn_data": ctx.get("churn_data", {}),
                    "period": ctx.get("period", "quarterly"),
                },
            ),
        ]


class CohortAnalysisWorkflow(Workflow):
    """Single-task workflow for cohort analysis."""

    @property
    def name(self) -> str:
        return "cohort_analysis"

    @property
    def description(self) -> str:
        return "Perform cohort analysis for retention and revenue"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="analyze",
                agent="Vector",
                task_type="cohort_analysis",
                description="Analyze customer cohorts",
                context_builder=lambda ctx: {
                    "cohort_data": ctx.get("cohort_data", {}),
                    "cohort_type": ctx.get("cohort_type", "acquisition"),
                },
            ),
        ]


class GrowthExperimentWorkflow(Workflow):
    """Single-task workflow for growth experiment design."""

    @property
    def name(self) -> str:
        return "growth_experiment"

    @property
    def description(self) -> str:
        return "Design and plan growth experiments"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="design",
                agent="Vector",
                task_type="growth_experiment_design",
                description="Design growth experiment",
                context_builder=lambda ctx: {
                    "hypothesis": ctx.get("hypothesis", ""),
                    "target_metrics": ctx.get("target_metrics", []),
                    "constraints": ctx.get("constraints", {}),
                },
            ),
        ]


# =============================================================================
# Sentinel Specialist Workflows
# =============================================================================


class DataGovernanceWorkflow(Workflow):
    """Single-task workflow for data governance assessment."""

    @property
    def name(self) -> str:
        return "data_governance"

    @property
    def description(self) -> str:
        return "Assess and improve data governance practices"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="assess",
                agent="Sentinel",
                task_type="data_governance",
                description="Assess data governance practices and compliance",
                context_builder=lambda ctx: {
                    "data_domain": ctx.get("data_domain", ""),
                    "compliance_requirements": ctx.get("compliance_requirements", []),
                    "current_policies": ctx.get("current_policies", {}),
                },
            ),
        ]


class SecurityAssessmentWorkflow(Workflow):
    """Single-task workflow for security assessment."""

    @property
    def name(self) -> str:
        return "security_assessment"

    @property
    def description(self) -> str:
        return "Perform security assessment and identify vulnerabilities"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="assess",
                agent="Sentinel",
                task_type="security_assessment",
                description="Assess security posture and identify risks",
                context_builder=lambda ctx: {
                    "scope": ctx.get("scope", "infrastructure"),
                    "systems": ctx.get("systems", []),
                    "compliance_framework": ctx.get("compliance_framework", ""),
                },
            ),
        ]


class KnowledgeExtractionWorkflow(Workflow):
    """Single-task workflow for knowledge extraction."""

    @property
    def name(self) -> str:
        return "knowledge_extraction"

    @property
    def description(self) -> str:
        return "Extract and organize knowledge from documents"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="extract",
                agent="Sentinel",
                task_type="knowledge_extraction",
                description="Extract and structure knowledge from sources",
                context_builder=lambda ctx: {
                    "source_documents": ctx.get("source_documents", []),
                    "extraction_type": ctx.get("extraction_type", "entities"),
                    "knowledge_domain": ctx.get("knowledge_domain", ""),
                },
            ),
        ]


class SystemsAnalysisWorkflow(Workflow):
    """Single-task workflow for systems analysis."""

    @property
    def name(self) -> str:
        return "systems_analysis"

    @property
    def description(self) -> str:
        return "Analyze IT systems and recommend improvements"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="analyze",
                agent="Sentinel",
                task_type="systems_analysis",
                description="Analyze system architecture and performance",
                context_builder=lambda ctx: {
                    "system": ctx.get("system", ""),
                    "analysis_type": ctx.get("analysis_type", "architecture"),
                    "requirements": ctx.get("requirements", []),
                },
            ),
        ]


# =============================================================================
# Axiom Specialist Workflows
# =============================================================================


class DeepResearchWorkflow(Workflow):
    """Single-task workflow for deep research."""

    @property
    def name(self) -> str:
        return "deep_research"

    @property
    def description(self) -> str:
        return "Conduct thorough research on a topic"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="research",
                agent="Axiom",
                task_type="deep_research",
                description="Conduct comprehensive research",
                context_builder=lambda ctx: {
                    "topic": ctx.get("topic", ""),
                    "depth": ctx.get("depth", "comprehensive"),
                    "focus_areas": ctx.get("focus_areas", []),
                },
            ),
        ]


class LiteratureReviewWorkflow(Workflow):
    """Single-task workflow for literature review."""

    @property
    def name(self) -> str:
        return "literature_review"

    @property
    def description(self) -> str:
        return "Conduct structured literature review"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="review",
                agent="Axiom",
                task_type="literature_review",
                description="Review and synthesize literature",
                context_builder=lambda ctx: {
                    "field": ctx.get("field", ""),
                    "timeframe": ctx.get("timeframe", "recent"),
                    "scope": ctx.get("scope", "comprehensive"),
                },
            ),
        ]


class ExperimentDesignWorkflow(Workflow):
    """Single-task workflow for experiment design."""

    @property
    def name(self) -> str:
        return "experiment_design"

    @property
    def description(self) -> str:
        return "Design rigorous experiments and studies"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="design",
                agent="Axiom",
                task_type="experiment_design",
                description="Design experiment methodology",
                context_builder=lambda ctx: {
                    "objective": ctx.get("objective", ""),
                    "constraints": ctx.get("constraints", []),
                    "resources": ctx.get("resources", []),
                },
            ),
        ]


class FeasibilityStudyWorkflow(Workflow):
    """Single-task workflow for feasibility studies."""

    @property
    def name(self) -> str:
        return "feasibility_study"

    @property
    def description(self) -> str:
        return "Conduct feasibility study for proposals"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="study",
                agent="Axiom",
                task_type="feasibility_study",
                description="Assess proposal feasibility",
                context_builder=lambda ctx: {
                    "proposal": ctx.get("proposal", ""),
                    "criteria": ctx.get("criteria", []),
                },
            ),
        ]


# =============================================================================
# Compass Specialist Workflows
# =============================================================================


class MarketAnalysisWorkflow(Workflow):
    """Single-task workflow for market analysis."""

    @property
    def name(self) -> str:
        return "market_analysis"

    @property
    def description(self) -> str:
        return "Analyze market conditions and opportunities"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="analyze",
                agent="Compass",
                task_type="market_analysis",
                description="Perform comprehensive market analysis",
                context_builder=lambda ctx: {
                    "market": ctx.get("market", ""),
                    "scope": ctx.get("scope", "comprehensive"),
                },
            ),
        ]


class CompetitiveAnalysisWorkflow(Workflow):
    """Single-task workflow for competitive analysis."""

    @property
    def name(self) -> str:
        return "competitive_analysis"

    @property
    def description(self) -> str:
        return "Analyze competitive landscape"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="analyze",
                agent="Compass",
                task_type="competitive_analysis",
                description="Analyze competitors and positioning",
                context_builder=lambda ctx: {
                    "industry": ctx.get("industry", ""),
                    "competitors": ctx.get("competitors", []),
                },
            ),
        ]


class StrategicPlanningWorkflow(Workflow):
    """Single-task workflow for strategic planning."""

    @property
    def name(self) -> str:
        return "strategic_planning"

    @property
    def description(self) -> str:
        return "Develop strategic plans and roadmaps"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="plan",
                agent="Compass",
                task_type="strategic_planning",
                description="Develop strategic plan",
                context_builder=lambda ctx: {
                    "timeframe": ctx.get("timeframe", "1 year"),
                    "focus_areas": ctx.get("focus_areas", []),
                },
            ),
        ]


class GoToMarketWorkflow(Workflow):
    """Single-task workflow for go-to-market planning."""

    @property
    def name(self) -> str:
        return "go_to_market"

    @property
    def description(self) -> str:
        return "Develop go-to-market strategy"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="plan",
                agent="Compass",
                task_type="go_to_market",
                description="Create GTM plan",
                context_builder=lambda ctx: {
                    "product": ctx.get("product", ""),
                    "market": ctx.get("market", ""),
                },
            ),
        ]


# =============================================================================
# Nexus Specialist Workflows
# =============================================================================


class WorkflowDesignWorkflow(Workflow):
    """Single-task workflow for workflow design."""

    @property
    def name(self) -> str:
        return "workflow_design"

    @property
    def description(self) -> str:
        return "Design new workflows for cross-functional operations"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="design",
                agent="Nexus",
                task_type="workflow_creation",
                description="Design workflow architecture and steps",
                context_builder=lambda ctx: {
                    "goal": ctx.get("goal", ""),
                    "agents": ctx.get("agents", []),
                    "constraints": ctx.get("constraints", []),
                },
            ),
        ]


class TaskAnalysisWorkflow(Workflow):
    """Single-task workflow for task analysis."""

    @property
    def name(self) -> str:
        return "task_analysis"

    @property
    def description(self) -> str:
        return "Analyze and classify tasks for routing"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="analyze",
                agent="Nexus",
                task_type="task_classification",
                description="Classify and analyze task requirements",
                context_builder=lambda ctx: {
                    "task_description": ctx.get("task_description", ""),
                    "context": ctx.get("context", {}),
                },
            ),
        ]


class PerformanceReportWorkflow(Workflow):
    """Single-task workflow for performance reporting."""

    @property
    def name(self) -> str:
        return "performance_report"

    @property
    def description(self) -> str:
        return "Generate performance reports from agent data"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="report",
                agent="Nexus",
                task_type="reporting",
                description="Generate comprehensive performance report",
                context_builder=lambda ctx: {
                    "data": ctx.get("executive_data", {}),
                    "report_type": ctx.get("report_type", "comprehensive"),
                    "audience": ctx.get("audience", "agent"),
                },
            ),
        ]


class ProcessOptimizationWorkflow(Workflow):
    """Single-task workflow for process optimization."""

    @property
    def name(self) -> str:
        return "process_optimization"

    @property
    def description(self) -> str:
        return "Optimize business processes for efficiency"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="optimize",
                agent="Nexus",
                task_type="process_optimization",
                description="Analyze and optimize process",
                context_builder=lambda ctx: {
                    "process": ctx.get("process", ""),
                    "performance": ctx.get("performance_data", {}),
                    "goals": ctx.get("goals", ["improve efficiency"]),
                },
            ),
        ]


# =============================================================================
# Accord Specialist Workflows (Compliance)
# =============================================================================


class ComplianceAssessmentWorkflow(Workflow):
    """Single-task workflow for compliance assessment."""

    @property
    def name(self) -> str:
        return "compliance_assessment"

    @property
    def description(self) -> str:
        return "Assess compliance against regulatory frameworks"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="assess",
                agent="Accord",
                task_type="compliance_assessment",
                description="Perform compliance assessment",
                context_builder=lambda ctx: {
                    "framework": ctx.get("framework", "general"),
                    "scope": ctx.get("scope", ""),
                    "current_controls": ctx.get("controls", {}),
                },
            ),
        ]


class PolicyReviewWorkflow(Workflow):
    """Single-task workflow for policy review."""

    @property
    def name(self) -> str:
        return "policy_review"

    @property
    def description(self) -> str:
        return "Review and analyze organizational policies"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="review",
                agent="Accord",
                task_type="policy_review",
                description="Review policy for compliance and effectiveness",
                context_builder=lambda ctx: {
                    "policy_name": ctx.get("policy_name", ""),
                    "policy_content": ctx.get("policy_content", ""),
                    "review_criteria": ctx.get("criteria", ["currency", "compliance", "clarity"]),
                },
            ),
        ]


class AuditPreparationWorkflow(Workflow):
    """Single-task workflow for audit preparation."""

    @property
    def name(self) -> str:
        return "audit_preparation"

    @property
    def description(self) -> str:
        return "Prepare for audit engagement"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="prepare",
                agent="Accord",
                task_type="audit_preparation",
                description="Prepare documentation and evidence for audit",
                context_builder=lambda ctx: {
                    "audit_name": ctx.get("audit_name", ""),
                    "framework": ctx.get("framework", ""),
                    "audit_type": ctx.get("audit_type", "internal"),
                },
            ),
        ]


class EthicsReviewWorkflow(Workflow):
    """Single-task workflow for ethics review."""

    @property
    def name(self) -> str:
        return "ethics_review"

    @property
    def description(self) -> str:
        return "Review ethics-related matters"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="review",
                agent="Accord",
                task_type="ethics_review",
                description="Conduct ethics review and provide guidance",
                context_builder=lambda ctx: {
                    "matter": ctx.get("matter", ""),
                    "stakeholders": ctx.get("stakeholders", []),
                    "urgency": ctx.get("urgency", "normal"),
                },
            ),
        ]


# =============================================================================
# Aegis Specialist Workflows (Risk)
# =============================================================================


class RiskAssessmentWorkflow(Workflow):
    """Single-task workflow for risk assessment."""

    @property
    def name(self) -> str:
        return "risk_assessment"

    @property
    def description(self) -> str:
        return "Assess and score enterprise risks"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="assess",
                agent="Aegis",
                task_type="risk_assessment",
                description="Identify and assess risks",
                context_builder=lambda ctx: {
                    "scope": ctx.get("scope", "enterprise"),
                    "risk_categories": ctx.get("categories", []),
                    "context": ctx.get("business_context", {}),
                },
            ),
        ]


class ThreatModelingWorkflow(Workflow):
    """Single-task workflow for threat modeling."""

    @property
    def name(self) -> str:
        return "threat_modeling"

    @property
    def description(self) -> str:
        return "Model threats using STRIDE methodology"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="model",
                agent="Aegis",
                task_type="threat_modeling",
                description="Create threat model for system",
                context_builder=lambda ctx: {
                    "system": ctx.get("system", ""),
                    "methodology": ctx.get("methodology", "STRIDE"),
                    "components": ctx.get("components", []),
                },
            ),
        ]


class BCPPlanningWorkflow(Workflow):
    """Single-task workflow for business continuity planning."""

    @property
    def name(self) -> str:
        return "bcp_planning"

    @property
    def description(self) -> str:
        return "Develop business continuity plans"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="plan",
                agent="Aegis",
                task_type="bcp_planning",
                description="Create business continuity plan",
                context_builder=lambda ctx: {
                    "scope": ctx.get("scope", "enterprise"),
                    "critical_functions": ctx.get("critical_functions", []),
                    "rto_rpo": ctx.get("rto_rpo", {}),
                },
            ),
        ]


class IncidentAnalysisWorkflow(Workflow):
    """Single-task workflow for incident analysis."""

    @property
    def name(self) -> str:
        return "incident_analysis"

    @property
    def description(self) -> str:
        return "Analyze incidents and determine root cause"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="analyze",
                agent="Aegis",
                task_type="incident_analysis",
                description="Analyze incident and identify root cause",
                context_builder=lambda ctx: {
                    "incident": ctx.get("incident", {}),
                    "timeline": ctx.get("timeline", []),
                    "impact": ctx.get("impact", {}),
                },
            ),
        ]


# =============================================================================
# Citadel Specialist Workflows (Security)
# =============================================================================


class SecurityScanWorkflow(Workflow):
    """Single-task workflow for security scanning."""

    @property
    def name(self) -> str:
        return "security_scan"

    @property
    def description(self) -> str:
        return "Perform security vulnerability scanning"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="scan",
                agent="Citadel",
                task_type="vulnerability_assessment",
                description="Scan for security vulnerabilities",
                context_builder=lambda ctx: {
                    "target": ctx.get("target", ""),
                    "scan_type": ctx.get("scan_type", "comprehensive"),
                    "scope": ctx.get("scope", {}),
                },
            ),
        ]


class ThreatHuntingWorkflow(Workflow):
    """Single-task workflow for threat hunting."""

    @property
    def name(self) -> str:
        return "threat_hunting"

    @property
    def description(self) -> str:
        return "Proactively hunt for security threats"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="hunt",
                agent="Citadel",
                task_type="threat_hunting",
                description="Hunt for indicators of compromise",
                context_builder=lambda ctx: {
                    "hypothesis": ctx.get("hypothesis", ""),
                    "indicators": ctx.get("indicators", []),
                    "data_sources": ctx.get("data_sources", []),
                },
            ),
        ]


class IncidentResponseWorkflow(Workflow):
    """Single-task workflow for incident response."""

    @property
    def name(self) -> str:
        return "incident_response"

    @property
    def description(self) -> str:
        return "Respond to security incidents"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="respond",
                agent="Citadel",
                task_type="incident_response",
                description="Execute incident response procedures",
                context_builder=lambda ctx: {
                    "incident": ctx.get("incident", {}),
                    "severity": ctx.get("severity", "medium"),
                    "affected_systems": ctx.get("affected_systems", []),
                },
            ),
        ]


class SecurityComplianceWorkflow(Workflow):
    """Single-task workflow for security compliance checking."""

    @property
    def name(self) -> str:
        return "security_compliance"

    @property
    def description(self) -> str:
        return "Assess security compliance against standards"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="assess",
                agent="Citadel",
                task_type="security_compliance",
                description="Assess compliance with security standards",
                context_builder=lambda ctx: {
                    "framework": ctx.get("framework", "SOC2"),
                    "scope": ctx.get("scope", ""),
                    "controls": ctx.get("controls", []),
                },
            ),
        ]


# =============================================================================
# Foundry Specialist Workflows (Engineering)
# =============================================================================


class SprintPlanningWorkflow(Workflow):
    """Single-task workflow for sprint planning."""

    @property
    def name(self) -> str:
        return "sprint_planning_eng"

    @property
    def description(self) -> str:
        return "Plan engineering sprint with capacity and deliverables"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="plan",
                agent="Foundry",
                task_type="sprint_planning",
                description="Plan sprint with capacity allocation",
                context_builder=lambda ctx: {
                    "backlog": ctx.get("backlog", []),
                    "capacity": ctx.get("capacity", {}),
                    "sprint_goals": ctx.get("goals", []),
                },
            ),
        ]


class ReleaseManagementWorkflow(Workflow):
    """Single-task workflow for release management."""

    @property
    def name(self) -> str:
        return "release_management"

    @property
    def description(self) -> str:
        return "Manage software release process"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="release",
                agent="Foundry",
                task_type="release_management",
                description="Coordinate and execute release",
                context_builder=lambda ctx: {
                    "version": ctx.get("version", ""),
                    "features": ctx.get("features", []),
                    "environment": ctx.get("environment", "production"),
                },
            ),
        ]


class QualityAssuranceWorkflow(Workflow):
    """Single-task workflow for quality assurance."""

    @property
    def name(self) -> str:
        return "quality_assurance"

    @property
    def description(self) -> str:
        return "Execute quality assurance testing"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="test",
                agent="Foundry",
                task_type="qa_testing",
                description="Execute QA testing procedures",
                context_builder=lambda ctx: {
                    "test_scope": ctx.get("scope", ""),
                    "test_types": ctx.get("test_types", ["functional", "regression"]),
                    "criteria": ctx.get("acceptance_criteria", []),
                },
            ),
        ]


class DevOpsPipelineWorkflow(Workflow):
    """Single-task workflow for DevOps pipeline management."""

    @property
    def name(self) -> str:
        return "devops_pipeline"

    @property
    def description(self) -> str:
        return "Manage CI/CD pipeline operations"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="pipeline",
                agent="Foundry",
                task_type="pipeline_management",
                description="Manage and optimize CI/CD pipeline",
                context_builder=lambda ctx: {
                    "pipeline": ctx.get("pipeline", ""),
                    "action": ctx.get("action", "analyze"),
                    "metrics": ctx.get("metrics", {}),
                },
            ),
        ]
