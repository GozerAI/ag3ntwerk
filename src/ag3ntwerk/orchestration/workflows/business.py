"""
Business Operations Workflows.

Workflows for product launches, budget approval, strategic planning,
operations review, financial close, strategic review, and knowledge transfer.
"""

from typing import Any, Dict, List

from ag3ntwerk.orchestration.base import Workflow, WorkflowStep


class ProductLaunchWorkflow(Workflow):
    """
    Workflow for launching a new product.

    Coordinates across:
    - Blueprint (Blueprint): Product strategy and requirements
    - Keystone (Keystone): Budget and pricing
    - Echo (Echo): Marketing and go-to-market (optional - not yet implemented)
    - Foundry (Foundry): Engineering readiness
    - Citadel (Citadel): Security review
    - Beacon (Beacon): Customer success preparation

    Steps:
    1. Product Strategy - Blueprint defines product vision and requirements
    2. Budget Analysis - Keystone analyzes costs and sets pricing
    3. Security Review - Citadel reviews security implications
    4. Engineering Assessment - Foundry assesses technical readiness
    5. Marketing Plan - Echo creates go-to-market strategy (optional)
    6. Customer Success Plan - Beacon prepares support and onboarding
    7. Launch Approval - Blueprint gives final approval
    """

    @property
    def name(self) -> str:
        return "product_launch"

    @property
    def description(self) -> str:
        return "End-to-end product launch coordination across all agents"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="product_strategy",
                agent="Blueprint",
                task_type="product_spec",
                description="Define product strategy, vision, and requirements",
                context_builder=lambda ctx: {
                    "product_name": ctx.get("product_name"),
                    "features": ctx.get("features", []),
                    "target_market": ctx.get("target_market", ""),
                    "objectives": ctx.get("objectives", []),
                },
            ),
            WorkflowStep(
                name="budget_analysis",
                agent="Keystone",
                task_type="budget_planning",
                description="Analyze development costs and set pricing strategy",
                depends_on=["product_strategy"],
                context_builder=lambda ctx: {
                    "product_strategy": ctx.step_results.get("product_strategy"),
                    "product_name": ctx.get("product_name"),
                    "target_price": ctx.get("target_price"),
                    "period": "launch",
                },
            ),
            WorkflowStep(
                name="security_review",
                agent="Citadel",
                task_type="security_assessment",
                description="Review security implications and requirements",
                depends_on=["product_strategy"],
                context_builder=lambda ctx: {
                    "product_name": ctx.get("product_name"),
                    "features": ctx.get("features", []),
                    "product_strategy": ctx.step_results.get("product_strategy"),
                },
            ),
            WorkflowStep(
                name="engineering_assessment",
                agent="Foundry",
                task_type="technical_assessment",
                description="Assess engineering readiness and release plan",
                depends_on=["product_strategy", "security_review"],
                context_builder=lambda ctx: {
                    "product_name": ctx.get("product_name"),
                    "features": ctx.get("features", []),
                    "security_requirements": ctx.step_results.get("security_review"),
                    "target_date": ctx.get("target_launch_date"),
                },
            ),
            WorkflowStep(
                name="marketing_plan",
                agent="Echo",
                task_type="campaign_creation",
                description="Create go-to-market and marketing strategy",
                depends_on=["product_strategy", "budget_analysis"],
                required=False,  # Echo not yet implemented - step will be skipped
                context_builder=lambda ctx: {
                    "product_name": ctx.get("product_name"),
                    "product_strategy": ctx.step_results.get("product_strategy"),
                    "budget": ctx.step_results.get("budget_analysis"),
                    "target_market": ctx.get("target_market", ""),
                    "launch_date": ctx.get("target_launch_date"),
                },
            ),
            WorkflowStep(
                name="customer_success_plan",
                agent="Beacon",
                task_type="onboarding_design",
                description="Prepare customer onboarding and support plan",
                depends_on=["product_strategy", "engineering_assessment"],
                context_builder=lambda ctx: {
                    "product_name": ctx.get("product_name"),
                    "features": ctx.get("features", []),
                    "product_strategy": ctx.step_results.get("product_strategy"),
                    "engineering_plan": ctx.step_results.get("engineering_assessment"),
                },
            ),
            WorkflowStep(
                name="launch_approval",
                agent="Blueprint",
                task_type="milestone_tracking",
                description="Final launch readiness check and approval",
                depends_on=[
                    "budget_analysis",
                    "security_review",
                    "engineering_assessment",
                    # "marketing_plan",  # Optional - Echo not yet implemented
                    "customer_success_plan",
                ],
                context_builder=lambda ctx: {
                    "product_name": ctx.get("product_name"),
                    "milestone": "launch_readiness",
                    "all_reviews": {
                        "budget": ctx.step_results.get("budget_analysis"),
                        "security": ctx.step_results.get("security_review"),
                        "engineering": ctx.step_results.get("engineering_assessment"),
                        "marketing": ctx.step_results.get("marketing_plan"),
                        "customer_success": ctx.step_results.get("customer_success_plan"),
                    },
                },
            ),
        ]


class BudgetApprovalWorkflow(Workflow):
    """
    Workflow for budget approval process.

    Coordinates across:
    - Keystone (Keystone): Budget analysis and approval
    - Blueprint (Blueprint): Product impact assessment
    - Foundry (Foundry): Technical feasibility
    - Nexus (Nexus): Operational impact

    Steps:
    1. Budget Request Analysis - Keystone analyzes the request
    2. Product Impact - Blueprint assesses impact on product roadmap
    3. Technical Feasibility - Foundry assesses technical needs
    4. Operational Impact - Nexus assesses operational implications
    5. Final Approval - Keystone makes final decision
    """

    @property
    def name(self) -> str:
        return "budget_approval"

    @property
    def description(self) -> str:
        return "Multi-stakeholder budget approval process"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="budget_analysis",
                agent="Keystone",
                task_type="budget_variance",
                description="Analyze budget request and financial impact",
                context_builder=lambda ctx: {
                    "request_id": ctx.get("request_id"),
                    "amount": ctx.get("amount"),
                    "purpose": ctx.get("purpose"),
                    "department": ctx.get("department"),
                    "budget": ctx.get("current_budget", {}),
                    "actuals": ctx.get("current_spend", {}),
                },
            ),
            WorkflowStep(
                name="product_impact",
                agent="Blueprint",
                task_type="roadmap_update",
                description="Assess impact on product roadmap",
                depends_on=["budget_analysis"],
                context_builder=lambda ctx: {
                    "budget_request": ctx.step_results.get("budget_analysis"),
                    "purpose": ctx.get("purpose"),
                    "affected_products": ctx.get("affected_products", []),
                },
            ),
            WorkflowStep(
                name="technical_feasibility",
                agent="Foundry",
                task_type="technical_assessment",
                description="Assess technical feasibility and requirements",
                depends_on=["budget_analysis"],
                context_builder=lambda ctx: {
                    "budget_request": ctx.step_results.get("budget_analysis"),
                    "purpose": ctx.get("purpose"),
                    "technical_requirements": ctx.get("technical_requirements", []),
                },
            ),
            WorkflowStep(
                name="operational_impact",
                agent="Nexus",
                task_type="operational_review",
                description="Assess operational implications",
                depends_on=["budget_analysis"],
                required=False,
                context_builder=lambda ctx: {
                    "budget_request": ctx.step_results.get("budget_analysis"),
                    "purpose": ctx.get("purpose"),
                    "operational_areas": ctx.get("operational_areas", []),
                },
            ),
            WorkflowStep(
                name="final_approval",
                agent="Keystone",
                task_type="budget_planning",
                description="Make final budget decision",
                depends_on=[
                    "budget_analysis",
                    "product_impact",
                    "technical_feasibility",
                ],
                context_builder=lambda ctx: {
                    "request_id": ctx.get("request_id"),
                    "amount": ctx.get("amount"),
                    "purpose": ctx.get("purpose"),
                    "assessments": {
                        "financial": ctx.step_results.get("budget_analysis"),
                        "product": ctx.step_results.get("product_impact"),
                        "technical": ctx.step_results.get("technical_feasibility"),
                        "operational": ctx.step_results.get("operational_impact"),
                    },
                    "period": "approval",
                },
            ),
        ]


class StrategicPlanningWorkflow(Workflow):
    """
    Workflow for quarterly/annual strategic planning.

    Coordinates across:
    - Compass (Compass): Market analysis and strategic direction
    - Keystone (Keystone): Financial planning and resource allocation
    - Blueprint (Blueprint): Product roadmap alignment
    - Axiom (Axiom): Research and trend analysis
    - Nexus (Nexus): Operational feasibility

    Steps:
    1. Market Analysis - Compass analyzes market trends and competition
    2. Research Insights - Axiom provides research-backed insights
    3. Financial Planning - Keystone creates budget and resource plan
    4. Product Alignment - Blueprint aligns roadmap with strategy
    5. Operational Review - Nexus assesses execution feasibility
    6. Strategy Finalization - Compass consolidates final strategy
    """

    @property
    def name(self) -> str:
        return "strategic_planning"

    @property
    def description(self) -> str:
        return "Comprehensive strategic planning across all business functions"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="market_analysis",
                agent="Compass",
                task_type="market_analysis",
                description="Analyze market trends, competition, and opportunities",
                context_builder=lambda ctx: {
                    "planning_period": ctx.get("planning_period", "Q1 2026"),
                    "focus_areas": ctx.get("focus_areas", []),
                    "current_position": ctx.get("current_position", ""),
                    "objectives": ctx.get("objectives", []),
                },
            ),
            WorkflowStep(
                name="research_insights",
                agent="Axiom",
                task_type="trend_research",
                description="Provide research-backed market and technology insights",
                depends_on=["market_analysis"],
                context_builder=lambda ctx: {
                    "market_analysis": ctx.step_results.get("market_analysis"),
                    "research_areas": ctx.get("focus_areas", []),
                    "planning_period": ctx.get("planning_period"),
                },
            ),
            WorkflowStep(
                name="financial_planning",
                agent="Keystone",
                task_type="budget_planning",
                description="Create financial plan and resource allocation",
                depends_on=["market_analysis"],
                context_builder=lambda ctx: {
                    "market_analysis": ctx.step_results.get("market_analysis"),
                    "budget_target": ctx.get("budget_target"),
                    "period": ctx.get("planning_period"),
                    "growth_targets": ctx.get("growth_targets", {}),
                },
            ),
            WorkflowStep(
                name="product_alignment",
                agent="Blueprint",
                task_type="roadmap_update",
                description="Align product roadmap with strategic direction",
                depends_on=["market_analysis", "research_insights"],
                context_builder=lambda ctx: {
                    "market_analysis": ctx.step_results.get("market_analysis"),
                    "research_insights": ctx.step_results.get("research_insights"),
                    "current_roadmap": ctx.get("current_roadmap", {}),
                    "priorities": ctx.get("product_priorities", []),
                },
            ),
            WorkflowStep(
                name="operational_review",
                agent="Nexus",
                task_type="operational_review",
                description="Assess operational feasibility of strategic plan",
                depends_on=["financial_planning", "product_alignment"],
                context_builder=lambda ctx: {
                    "financial_plan": ctx.step_results.get("financial_planning"),
                    "product_roadmap": ctx.step_results.get("product_alignment"),
                    "current_capacity": ctx.get("current_capacity", {}),
                },
            ),
            WorkflowStep(
                name="strategy_finalization",
                agent="Compass",
                task_type="strategic_planning",
                description="Consolidate and finalize strategic plan",
                depends_on=[
                    "market_analysis",
                    "research_insights",
                    "financial_planning",
                    "product_alignment",
                    "operational_review",
                ],
                context_builder=lambda ctx: {
                    "all_inputs": {
                        "market": ctx.step_results.get("market_analysis"),
                        "research": ctx.step_results.get("research_insights"),
                        "financial": ctx.step_results.get("financial_planning"),
                        "product": ctx.step_results.get("product_alignment"),
                        "operations": ctx.step_results.get("operational_review"),
                    },
                    "planning_period": ctx.get("planning_period"),
                },
            ),
        ]


class OperationsReviewWorkflow(Workflow):
    """
    Nexus internal workflow for periodic operations review.

    Steps:
    1. Performance Metrics - Gather operational KPIs
    2. Bottleneck Analysis - Identify operational bottlenecks
    3. Resource Utilization - Analyze resource efficiency
    4. Process Optimization - Recommend process improvements
    5. Action Plan - Create operational action items
    """

    @property
    def name(self) -> str:
        return "operations_review"

    @property
    def description(self) -> str:
        return "Nexus periodic operations review and optimization"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="performance_metrics",
                agent="Nexus",
                task_type="performance_review",
                description="Gather and analyze operational KPIs",
                context_builder=lambda ctx: {
                    "review_period": ctx.get("review_period", "last_month"),
                    "departments": ctx.get("departments", []),
                    "kpi_targets": ctx.get("kpi_targets", {}),
                },
            ),
            WorkflowStep(
                name="bottleneck_analysis",
                agent="Nexus",
                task_type="bottleneck_analysis",
                description="Identify operational bottlenecks",
                depends_on=["performance_metrics"],
                context_builder=lambda ctx: {
                    "metrics": ctx.step_results.get("performance_metrics"),
                    "process_flows": ctx.get("process_flows", []),
                },
            ),
            WorkflowStep(
                name="resource_utilization",
                agent="Nexus",
                task_type="resource_optimization",
                description="Analyze resource efficiency and utilization",
                depends_on=["performance_metrics"],
                context_builder=lambda ctx: {
                    "metrics": ctx.step_results.get("performance_metrics"),
                    "resource_inventory": ctx.get("resource_inventory", {}),
                },
            ),
            WorkflowStep(
                name="process_optimization",
                agent="Nexus",
                task_type="process_improvement",
                description="Recommend process improvements",
                depends_on=["bottleneck_analysis", "resource_utilization"],
                context_builder=lambda ctx: {
                    "bottlenecks": ctx.step_results.get("bottleneck_analysis"),
                    "utilization": ctx.step_results.get("resource_utilization"),
                    "improvement_budget": ctx.get("improvement_budget"),
                },
            ),
            WorkflowStep(
                name="action_plan",
                agent="Nexus",
                task_type="operational_review",
                description="Create operational action plan",
                depends_on=["process_optimization"],
                context_builder=lambda ctx: {
                    "optimizations": ctx.step_results.get("process_optimization"),
                    "priority_areas": ctx.get("priority_areas", []),
                    "timeline": ctx.get("timeline", "30_days"),
                },
            ),
        ]


class FinancialCloseWorkflow(Workflow):
    """
    Keystone internal workflow for financial period close.

    Steps:
    1. Revenue Recognition - Process revenue entries
    2. Expense Reconciliation - Reconcile expenses
    3. Variance Analysis - Analyze budget variances
    4. Financial Statements - Prepare financial statements
    5. Close Report - Generate close report
    """

    @property
    def name(self) -> str:
        return "financial_close"

    @property
    def description(self) -> str:
        return "Keystone financial period close process"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="revenue_recognition",
                agent="Keystone",
                task_type="revenue_recognition",
                description="Process and recognize revenue",
                context_builder=lambda ctx: {
                    "close_period": ctx.get("close_period"),
                    "revenue_streams": ctx.get("revenue_streams", []),
                    "recognition_rules": ctx.get("recognition_rules", {}),
                },
            ),
            WorkflowStep(
                name="expense_reconciliation",
                agent="Keystone",
                task_type="expense_analysis",
                description="Reconcile all expenses",
                context_builder=lambda ctx: {
                    "close_period": ctx.get("close_period"),
                    "expense_categories": ctx.get("expense_categories", []),
                    "cost_centers": ctx.get("cost_centers", []),
                },
            ),
            WorkflowStep(
                name="variance_analysis",
                agent="Keystone",
                task_type="variance_analysis",
                description="Analyze budget vs actual variances",
                depends_on=["revenue_recognition", "expense_reconciliation"],
                context_builder=lambda ctx: {
                    "revenue": ctx.step_results.get("revenue_recognition"),
                    "expenses": ctx.step_results.get("expense_reconciliation"),
                    "budget": ctx.get("budget", {}),
                    "variance_threshold": ctx.get("variance_threshold", 0.05),
                },
            ),
            WorkflowStep(
                name="financial_statements",
                agent="Keystone",
                task_type="financial_modeling",
                description="Prepare financial statements",
                depends_on=["variance_analysis"],
                context_builder=lambda ctx: {
                    "revenue": ctx.step_results.get("revenue_recognition"),
                    "expenses": ctx.step_results.get("expense_reconciliation"),
                    "variances": ctx.step_results.get("variance_analysis"),
                    "statement_types": ctx.get(
                        "statement_types", ["income", "balance", "cashflow"]
                    ),
                },
            ),
            WorkflowStep(
                name="close_report",
                agent="Keystone",
                task_type="budget_variance_analysis",
                description="Generate financial close report",
                depends_on=["financial_statements"],
                context_builder=lambda ctx: {
                    "statements": ctx.step_results.get("financial_statements"),
                    "variances": ctx.step_results.get("variance_analysis"),
                    "close_period": ctx.get("close_period"),
                    "commentary_required": ctx.get("commentary_required", True),
                },
            ),
        ]


class StrategicReviewWorkflow(Workflow):
    """
    Compass internal workflow for strategic review.

    Steps:
    1. Market Analysis - Analyze market conditions
    2. Competitive Intelligence - Gather competitive intelligence
    3. Strategy Assessment - Assess current strategy performance
    4. Opportunity Identification - Identify strategic opportunities
    5. Strategy Recommendations - Generate strategy recommendations
    """

    @property
    def name(self) -> str:
        return "strategic_review"

    @property
    def description(self) -> str:
        return "Compass strategic review workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="market_analysis",
                agent="Compass",
                task_type="market_analysis",
                description="Analyze market conditions and trends",
                context_builder=lambda ctx: {
                    "markets": ctx.get("markets", []),
                    "analysis_dimensions": ctx.get(
                        "analysis_dimensions", ["size", "growth", "trends"]
                    ),
                    "time_horizon": ctx.get("time_horizon", "3_years"),
                },
            ),
            WorkflowStep(
                name="competitive_intelligence",
                agent="Compass",
                task_type="competitive_analysis",
                description="Gather and analyze competitive intelligence",
                depends_on=["market_analysis"],
                context_builder=lambda ctx: {
                    "market_data": ctx.step_results.get("market_analysis"),
                    "competitors": ctx.get("competitors", []),
                    "intelligence_areas": ctx.get(
                        "intelligence_areas", ["product", "pricing", "positioning"]
                    ),
                },
            ),
            WorkflowStep(
                name="strategy_assessment",
                agent="Compass",
                task_type="strategic_planning",
                description="Assess current strategy performance",
                depends_on=["market_analysis", "competitive_intelligence"],
                context_builder=lambda ctx: {
                    "market_data": ctx.step_results.get("market_analysis"),
                    "competitive_data": ctx.step_results.get("competitive_intelligence"),
                    "current_strategy": ctx.get("current_strategy", {}),
                    "strategic_kpis": ctx.get("strategic_kpis", []),
                },
            ),
            WorkflowStep(
                name="opportunity_identification",
                agent="Compass",
                task_type="opportunity_assessment",
                description="Identify strategic opportunities",
                depends_on=["strategy_assessment"],
                context_builder=lambda ctx: {
                    "assessment": ctx.step_results.get("strategy_assessment"),
                    "opportunity_criteria": ctx.get("opportunity_criteria", []),
                    "risk_tolerance": ctx.get("risk_tolerance", "moderate"),
                },
            ),
            WorkflowStep(
                name="strategy_recommendations",
                agent="Compass",
                task_type="strategic_planning",
                description="Generate strategy recommendations",
                depends_on=["strategy_assessment", "opportunity_identification"],
                context_builder=lambda ctx: {
                    "assessment": ctx.step_results.get("strategy_assessment"),
                    "opportunities": ctx.step_results.get("opportunity_identification"),
                    "constraints": ctx.get("constraints", []),
                    "planning_horizon": ctx.get("planning_horizon", "annual"),
                },
            ),
        ]


class KnowledgeTransferWorkflow(Workflow):
    """
    Workflow for knowledge transfer and documentation.

    Coordinates across:
    - Index (Index): Knowledge management
    - CKO (Oracle): Documentation
    - Forge (Forge): Technical documentation

    Steps:
    1. Knowledge Audit - Index audits existing knowledge
    2. Gap Analysis - Index identifies knowledge gaps
    3. Documentation Plan - CKO creates documentation plan
    4. Technical Docs - Forge creates technical documentation
    5. Knowledge Base Update - Index updates knowledge base
    6. Training Materials - CKO creates training materials
    """

    @property
    def name(self) -> str:
        return "knowledge_transfer"

    @property
    def description(self) -> str:
        return "Knowledge transfer and documentation workflow"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                name="knowledge_audit",
                agent="Index",
                task_type="knowledge_retrieval",
                description="Audit existing knowledge and documentation",
                context_builder=lambda ctx: {
                    "knowledge_area": ctx.get("knowledge_area"),
                    "scope": ctx.get("scope", "comprehensive"),
                    "systems": ctx.get("systems", []),
                },
            ),
            WorkflowStep(
                name="gap_analysis",
                agent="Index",
                task_type="data_profiling",
                description="Identify knowledge and documentation gaps",
                depends_on=["knowledge_audit"],
                context_builder=lambda ctx: {
                    "audit_results": ctx.step_results.get("knowledge_audit"),
                    "required_knowledge": ctx.get("required_knowledge", []),
                },
            ),
            WorkflowStep(
                name="documentation_plan",
                agent="CKO",
                task_type="documentation",
                description="Create documentation plan",
                depends_on=["gap_analysis"],
                context_builder=lambda ctx: {
                    "gaps": ctx.step_results.get("gap_analysis"),
                    "documentation_standards": ctx.get("documentation_standards", {}),
                    "audience": ctx.get("audience", []),
                },
            ),
            WorkflowStep(
                name="technical_docs",
                agent="Forge",
                task_type="code_review",
                description="Create technical documentation",
                depends_on=["documentation_plan"],
                context_builder=lambda ctx: {
                    "documentation_plan": ctx.step_results.get("documentation_plan"),
                    "technical_areas": ctx.get("technical_areas", []),
                    "code_repositories": ctx.get("code_repositories", []),
                },
            ),
            WorkflowStep(
                name="knowledge_base_update",
                agent="Index",
                task_type="data_catalog",
                description="Update knowledge base with new documentation",
                depends_on=["technical_docs"],
                context_builder=lambda ctx: {
                    "technical_docs": ctx.step_results.get("technical_docs"),
                    "documentation_plan": ctx.step_results.get("documentation_plan"),
                    "knowledge_base_location": ctx.get("knowledge_base_location"),
                },
            ),
            WorkflowStep(
                name="training_materials",
                agent="CKO",
                task_type="tutorial_creation",
                description="Create training materials",
                depends_on=["knowledge_base_update"],
                context_builder=lambda ctx: {
                    "knowledge_base": ctx.step_results.get("knowledge_base_update"),
                    "training_format": ctx.get("training_format", "mixed"),
                    "target_audience": ctx.get("target_audience", []),
                },
            ),
        ]
