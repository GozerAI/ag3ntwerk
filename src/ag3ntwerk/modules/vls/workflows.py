"""
VLS Workflow Definitions.

Defines the complete Vertical Launch System pipeline workflow
with all 10 stages and their dependencies.
"""

from ag3ntwerk.orchestration.factory import (
    WorkflowDefinition,
    StepDefinition,
    param,
    step_result,
)


# =============================================================================
# Vertical Launch System Pipeline
# =============================================================================


VERTICAL_LAUNCH_PIPELINE = WorkflowDefinition(
    name="vertical_launch_system",
    description="Autonomous vertical discovery and monetization pipeline with evidence-based gating",
    category="pipeline",
    tags=("vls", "revenue", "automation", "multi-stage", "evidence-based"),
    steps=[
        # =====================================================================
        # Stage 1: Market Intelligence
        # =====================================================================
        StepDefinition(
            name="market_intelligence",
            agent="Echo",
            task_type="vls_market_intelligence",
            description="Identify and rank viable niche candidates from market signals",
            required=True,
            context_mapping={
                "constraints": param("constraints", {}),
                "data_sources": param("data_sources", []),
                "min_confidence": param("min_confidence", 0.7),
                "min_candidates": param("min_candidates", 3),
            },
        ),
        # =====================================================================
        # Stage 2: Validation & Economics
        # =====================================================================
        StepDefinition(
            name="validation_economics",
            agent="Keystone",
            task_type="vls_validation_economics",
            description="Model unit economics and determine financial viability",
            required=True,
            depends_on=("market_intelligence",),
            context_mapping={
                "niche_candidates": step_result("market_intelligence", "niche_candidates"),
                "top_candidate": step_result("market_intelligence", "top_candidate"),
                "budget_caps": param("budget_caps", {}),
                "target_margin": param("target_margin", 0.3),
                "max_cac_ltv_ratio": param("max_cac_ltv_ratio", 3.0),
            },
        ),
        # =====================================================================
        # Stage 3: Blueprint Definition
        # =====================================================================
        StepDefinition(
            name="blueprint_definition",
            agent="Blueprint",
            task_type="vls_blueprint_definition",
            description="Create formal executable launch specification with ICP and positioning",
            required=True,
            depends_on=("validation_economics",),
            context_mapping={
                "approved_niche": step_result("validation_economics", "approved_niche"),
                "economics_model": step_result("validation_economics", "economics_model"),
                "niche_data": step_result("market_intelligence", "top_candidate"),
                "require_ceo_approval": param("require_ceo_approval", True),
            },
        ),
        # =====================================================================
        # Stage 4: Build & Deployment
        # =====================================================================
        StepDefinition(
            name="build_deployment",
            agent="Forge",
            task_type="vls_build_deployment",
            description="Generate and deploy vertical runtime infrastructure",
            required=True,
            depends_on=("blueprint_definition",),
            context_mapping={
                "blueprint": step_result("blueprint_definition", "blueprint"),
                "infrastructure_templates": param("infrastructure_templates", {}),
                "deployment_target": param("deployment_target", "staging"),
                "auto_deploy": param("auto_deploy", False),
            },
        ),
        # =====================================================================
        # Stage 5: Lead Intake
        # =====================================================================
        StepDefinition(
            name="lead_intake",
            agent="Index",
            task_type="vls_lead_intake",
            description="Configure lead capture, classification, and qualification systems",
            required=True,
            depends_on=("build_deployment",),
            context_mapping={
                "blueprint": step_result("blueprint_definition", "blueprint"),
                "vertical_runtime": step_result("build_deployment", "runtime_info"),
                "qualification_rules": step_result(
                    "blueprint_definition", "qualification_criteria"
                ),
            },
        ),
        # =====================================================================
        # Stage 6: Buyer Acquisition
        # =====================================================================
        StepDefinition(
            name="buyer_acquisition",
            agent="Vector",
            task_type="vls_buyer_acquisition",
            description="Acquire and onboard lead buyers for the vertical",
            required=True,
            depends_on=("lead_intake",),
            context_mapping={
                "blueprint": step_result("blueprint_definition", "blueprint"),
                "target_metros": param("target_metros", []),
                "min_buyers": param("min_buyers", 3),
                "pricing_tiers": step_result("blueprint_definition", "pricing_tiers"),
            },
        ),
        # =====================================================================
        # Stage 7: Routing & Delivery
        # =====================================================================
        StepDefinition(
            name="routing_delivery",
            agent="Foundry",
            task_type="vls_routing_delivery",
            description="Configure lead routing and delivery orchestration",
            required=True,
            depends_on=("buyer_acquisition",),
            context_mapping={
                "buyer_pools": step_result("buyer_acquisition", "buyer_pools"),
                "routing_rules": step_result("blueprint_definition", "routing_rules"),
                "delivery_sla": param("delivery_sla_minutes", 15),
            },
        ),
        # =====================================================================
        # Stage 8: Billing & Revenue
        # =====================================================================
        StepDefinition(
            name="billing_revenue",
            agent="Vector",
            task_type="vls_billing_revenue",
            description="Configure billing, payment processing, and revenue tracking",
            required=True,
            depends_on=("routing_delivery",),
            context_mapping={
                "buyer_pools": step_result("buyer_acquisition", "buyer_pools"),
                "pricing_tiers": step_result("blueprint_definition", "pricing_tiers"),
                "payment_processor": param("payment_processor", "stripe"),
            },
        ),
        # =====================================================================
        # Stage 9: Monitoring & Stop-Loss
        # =====================================================================
        StepDefinition(
            name="monitoring_stoploss",
            agent="Aegis",
            task_type="vls_monitoring_stoploss",
            description="Configure monitoring, alerts, and stop-loss triggers",
            required=True,
            depends_on=("billing_revenue",),
            context_mapping={
                "thresholds": step_result("validation_economics", "stop_loss_thresholds"),
                "metrics": step_result("blueprint_definition", "success_metrics"),
                "monitoring_frequency": param("monitoring_frequency", "hourly"),
                "alert_channels": param("alert_channels", ["email", "slack"]),
            },
        ),
        # =====================================================================
        # Stage 10: Knowledge Capture
        # =====================================================================
        StepDefinition(
            name="knowledge_capture",
            agent="Index",
            task_type="vls_knowledge_capture",
            description="Capture launch knowledge and create reusable templates",
            required=False,  # Non-blocking for launch completion
            depends_on=("monitoring_stoploss",),
            context_mapping={
                "launch_data": {
                    "blueprint": step_result("blueprint_definition", "blueprint"),
                    "economics": step_result("validation_economics", "economics_model"),
                    "buyer_data": step_result("buyer_acquisition", "buyer_pools"),
                    "metrics": step_result("monitoring_stoploss", "baseline_metrics"),
                },
                "create_template": param("create_template", True),
            },
        ),
    ],
)


# =============================================================================
# Quick Launch Workflow (Stages 1-3 only)
# =============================================================================


VLS_QUICK_VALIDATION = WorkflowDefinition(
    name="vls_quick_validation",
    description="Quick validation workflow for testing VLS viability (stages 1-3 only)",
    category="pipeline",
    tags=("vls", "validation", "quick", "testing"),
    steps=[
        StepDefinition(
            name="market_intelligence",
            agent="Echo",
            task_type="vls_market_intelligence",
            description="Identify and rank viable niche candidates",
            required=True,
            context_mapping={
                "constraints": param("constraints", {}),
                "min_confidence": param("min_confidence", 0.6),
                "min_candidates": param("min_candidates", 2),
            },
        ),
        StepDefinition(
            name="validation_economics",
            agent="Keystone",
            task_type="vls_validation_economics",
            description="Model unit economics",
            required=True,
            depends_on=("market_intelligence",),
            context_mapping={
                "niche_candidates": step_result("market_intelligence", "niche_candidates"),
                "top_candidate": step_result("market_intelligence", "top_candidate"),
            },
        ),
        StepDefinition(
            name="blueprint_definition",
            agent="Blueprint",
            task_type="vls_blueprint_definition",
            description="Create draft blueprint",
            required=True,
            depends_on=("validation_economics",),
            context_mapping={
                "approved_niche": step_result("validation_economics", "approved_niche"),
                "economics_model": step_result("validation_economics", "economics_model"),
                "require_ceo_approval": param("require_ceo_approval", False),
            },
        ),
    ],
)


# =============================================================================
# Export All Workflows
# =============================================================================


ALL_VLS_WORKFLOWS = [
    VERTICAL_LAUNCH_PIPELINE,
    VLS_QUICK_VALIDATION,
]
