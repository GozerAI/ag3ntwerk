"""
Task Routing Rules for the Overwatch (Overwatch) coordination layer.

Maps task types to their primary agent agent handlers.
Comprehensive routing table with fallback routes for health-aware routing.

Security Task Routing Guide:
- Sentinel (Sentinel): Information security GOVERNANCE - policies, audits, reviews,
  high-level security strategy, and compliance-related security tasks.
  Think: "What should our security posture be?" and "Are we following policy?"

- Citadel (Citadel): Security OPERATIONS - active monitoring, threat hunting,
  vulnerability scanning, incident response execution, and technical security.
  Think: "Are we under attack?" and "What vulnerabilities exist right now?"

- Aegis (Aegis): Risk MANAGEMENT - risk assessment, threat modeling, BCP/DR.
  Think: "What could go wrong?" and "What's the business impact?"
"""

from typing import Dict, List


# Task type to agent routing rules
ROUTING_RULES: Dict[str, str] = {
    # Sentinel (Sentinel) - Information Security GOVERNANCE
    # High-level security oversight, policy compliance, and strategic reviews
    "security_review": "Sentinel",  # Strategic security posture review
    "access_audit": "Sentinel",  # Access control compliance auditing
    "penetration_test": "Sentinel",  # Commissioned security testing oversight
    "security_policy": "Sentinel",  # Security policy management
    "security_compliance": "Sentinel",  # Security compliance verification
    "security_governance": "Sentinel",  # Overall security governance
    # Development tasks -> Forge (Forge)
    "code_review": "Forge",
    "code_generation": "Forge",
    "bug_fix": "Forge",
    "refactoring": "Forge",
    "testing": "Forge",
    "deployment": "Forge",
    "architecture": "Forge",
    "debugging": "Forge",
    "optimization": "Forge",
    "api_design": "Forge",
    "database_design": "Forge",
    "technical_design": "Forge",
    # Strategy tasks -> Compass (Compass)
    "market_analysis": "Compass",
    "competitive_analysis": "Compass",
    "strategic_analysis": "Compass",
    "strategic_planning": "Compass",
    "content_strategy": "Compass",
    "content_creation": "Compass",
    "brand_positioning": "Compass",
    "go_to_market": "Compass",
    "trend_analysis": "Compass",
    "swot_analysis": "Compass",
    "opportunity_assessment": "Compass",
    "messaging_framework": "Compass",
    "value_proposition": "Compass",
    # Data & Knowledge tasks -> Index (Index)
    "data_governance": "Index",
    "data_quality": "Index",
    "data_quality_check": "Index",
    "data_profiling": "Index",
    "schema_validation": "Index",
    "schema_design": "Index",
    "data_lineage": "Index",
    "data_catalog": "Index",
    "data_classification": "Index",
    "metadata_management": "Index",
    "documentation": "Index",
    "knowledge_management": "Index",
    "knowledge_retrieval": "Index",
    "research_synthesis": "Index",
    "learning_path": "Index",
    "best_practices": "Index",
    "summary_generation": "Index",
    "analytics_design": "Index",
    "metrics_definition": "Index",
    # Knowledge tasks -> CKO (deprecated, routes to Index)
    "knowledge_base_update": "Index",
    "faq_generation": "Index",
    "glossary_management": "Index",
    "tutorial_creation": "Index",
    # Risk tasks -> Aegis (Aegis)
    "risk_assessment": "Aegis",
    "risk_identification": "Aegis",
    "risk_quantification": "Aegis",
    "risk_scoring": "Aegis",
    "risk_register": "Aegis",
    "risk_mitigation": "Aegis",
    "mitigation_planning": "Aegis",
    "control_assessment": "Aegis",
    "control_design": "Aegis",
    "threat_modeling": "Aegis",
    "threat_analysis": "Aegis",
    "attack_surface_analysis": "Aegis",
    "bcp_planning": "Aegis",
    "disaster_recovery": "Aegis",
    "impact_analysis": "Aegis",
    "risk_appetite": "Aegis",
    "risk_reporting": "Aegis",
    "incident_analysis": "Aegis",
    "root_cause_analysis": "Aegis",
    "lessons_learned": "Aegis",
    # Compliance tasks -> Accord (Accord)
    "compliance_assessment": "Accord",
    "compliance_monitoring": "Accord",
    "compliance_check": "Accord",
    "audit": "Accord",
    "regulatory_analysis": "Accord",
    "regulatory_mapping": "Accord",
    "gap_analysis": "Accord",
    "compliance_reporting": "Accord",
    "policy_review": "Accord",
    "policy_creation": "Accord",
    "policy_update": "Accord",
    "policy_enforcement": "Accord",
    "exception_management": "Accord",
    "audit_planning": "Accord",
    "audit_preparation": "Accord",
    "audit_response": "Accord",
    "finding_remediation": "Accord",
    "license_tracking": "Accord",
    "license_renewal": "Accord",
    "ethics_review": "Accord",
    "conduct_investigation": "Accord",
    "conflict_of_interest": "Accord",
    "compliance_training": "Accord",
    # Research tasks -> Axiom (Axiom)
    "research": "Axiom",
    "deep_research": "Axiom",
    "literature_review": "Axiom",
    "experiment_design": "Axiom",
    "data_analysis": "Axiom",
    "hypothesis_testing": "Axiom",
    "meta_analysis": "Axiom",
    "trend_research": "Axiom",
    "feasibility_study": "Axiom",
    "technology_assessment": "Axiom",
    "benchmarking": "Axiom",
    "insights": "Axiom",
    # Financial tasks -> Keystone (Keystone)
    "budget_analysis": "Keystone",
    "cost_analysis": "Keystone",
    "budget_planning": "Keystone",
    "resource_allocation": "Keystone",
    "roi_analysis": "Keystone",
    "roi_calculation": "Keystone",
    "financial_modeling": "Keystone",
    "financial_report": "Keystone",
    "usage_tracking": "Keystone",
    "cost_optimization": "Keystone",
    "pricing_analysis": "Keystone",
    "investment_analysis": "Keystone",
    "break_even_analysis": "Keystone",
    "variance_analysis": "Keystone",
    "forecast": "Keystone",
    # Customer tasks -> Beacon (Beacon)
    "customer_feedback": "Beacon",
    "customer_success": "Beacon",
    "feedback_collection": "Beacon",
    "satisfaction_tracking": "Beacon",
    "support_escalation": "Beacon",
    "customer_health_scoring": "Beacon",
    "onboarding_optimization": "Beacon",
    "customer_journey_mapping": "Beacon",
    "churn_analysis": "Beacon",
    "nps_analysis": "Beacon",
    "csat_analysis": "Beacon",
    "voice_of_customer": "Beacon",
    "customer_advocacy": "Beacon",
    "retention_strategy": "Beacon",
    # Product tasks -> Blueprint (Blueprint)
    "product_strategy": "Blueprint",
    "feature_planning": "Blueprint",
    "feature_prioritization": "Blueprint",
    "roadmap_update": "Blueprint",
    "requirements_gathering": "Blueprint",
    "sprint_planning": "Blueprint",
    "backlog_grooming": "Blueprint",
    "milestone_tracking": "Blueprint",
    "product_spec": "Blueprint",
    "user_story": "Blueprint",
    "user_research": "Blueprint",
    "acceptance_criteria": "Blueprint",
    "feature_scoping": "Blueprint",
    "market_research": "Blueprint",
    # Revenue tasks -> Vector (Vector)
    "revenue_optimization": "Vector",
    "sales_strategy": "Vector",
    "revenue_summary": "Vector",
    "revenue_tracking": "Vector",
    "feature_adoption_metrics": "Vector",
    "conversion_analysis": "Vector",
    "growth_experiment_design": "Vector",
    "revenue_forecasting": "Vector",
    "unit_economics": "Vector",
    "cohort_analysis": "Vector",
    "ltv_calculation": "Vector",
    "mrr_analysis": "Vector",
    "expansion_revenue": "Vector",
    # Citadel (Citadel) - Security OPERATIONS
    # Active monitoring, scanning, incident response execution, technical security
    "security_scan": "Citadel",  # Active security scanning
    "vulnerability_check": "Citadel",  # Vulnerability verification
    "incident_response": "Citadel",  # Active incident response
    "threat_detection": "Citadel",
    "threat_hunting": "Citadel",
    "threat_mitigation": "Citadel",
    "vulnerability_scanning": "Citadel",
    "vulnerability_assessment": "Citadel",
    "vulnerability_remediation": "Citadel",
    "patch_management": "Citadel",
    "incident_detection": "Citadel",
    "incident_triage": "Citadel",
    "incident_investigation": "Citadel",
    "forensics": "Citadel",
    "security_monitoring": "Citadel",
    "access_review": "Citadel",
    "access_control": "Citadel",
    "security_posture": "Citadel",
    "sast_scan": "Citadel",
    "dast_scan": "Citadel",
    "dependency_scan": "Citadel",
    "detection_engineering": "Citadel",
    "security_automation": "Citadel",
    # Engineering/Delivery tasks -> Foundry (Foundry)
    "infrastructure": "Foundry",
    "devops": "Foundry",
    "platform_engineering": "Foundry",
    "sprint_review": "Foundry",
    "velocity_tracking": "Foundry",
    "release_planning": "Foundry",
    "release_coordination": "Foundry",
    "delivery_tracking": "Foundry",
    "backlog_management": "Foundry",
    "quality_gate_check": "Foundry",
    "test_planning": "Foundry",
    "test_execution": "Foundry",
    "test_automation": "Foundry",
    "coverage_analysis": "Foundry",
    "defect_triage": "Foundry",
    "regression_testing": "Foundry",
    "pipeline_design": "Foundry",
    "pipeline_execution": "Foundry",
    "build_management": "Foundry",
    # Marketing tasks -> Echo (Echo)
    "campaign_creation": "Echo",
    "campaign_management": "Echo",
    "brand_strategy": "Echo",
    "brand_analysis": "Echo",
    "content_marketing": "Echo",
    "social_media_strategy": "Echo",
    "social_distribute": "Echo",
    "social_publish": "Echo",
    "social_schedule": "Echo",
    "social_analytics": "Echo",
    "social_metrics": "Echo",
    "marketing_analytics": "Echo",
    "customer_segmentation": "Echo",
    "competitive_positioning": "Echo",
    "demand_generation": "Echo",
    "marketing_roi": "Echo",
    "campaign_planning": "Echo",
    "campaign_execution": "Echo",
    "ab_testing": "Echo",
    "campaign_optimization": "Echo",
    "email_campaign": "Echo",
    "editorial_planning": "Echo",
    "seo_optimization": "Echo",
    "content_distribution": "Echo",
    "brand_identity": "Echo",
    "brand_guidelines": "Echo",
    "brand_health": "Echo",
    "brand_audit": "Echo",
    # Workbench Pipeline tasks -> Overwatch orchestrates, routes to specialists
    "workbench_pipeline": "Overwatch",  # Full pipeline orchestration
    "workbench_evaluate": "Forge",  # Code evaluation/review
    "workbench_security_scan": "Citadel",  # Security scanning
    "workbench_test": "Foundry",  # Test planning and execution
    "workbench_build": "Foundry",  # Build management
    "workbench_deploy": "Foundry",  # Deployment execution
    "workbench_database": "Index",  # Database schema/provisioning
    "workbench_secrets": "Citadel",  # Secrets management
    # Additional Workbench-related task types
    "containerization": "Forge",  # Docker/container operations
    "configuration": "Forge",  # Environment configuration
    "deployment_execution": "Foundry",  # Actual deployment execution
    "encryption": "Citadel",  # Encryption operations
    # VLS (Vertical Launch System) Pipeline tasks
    "vls_launch": "Overwatch",  # Full VLS pipeline orchestration
    "vls_market_intelligence": "Echo",  # Stage 1: Market & niche identification
    "vls_validation_economics": "Keystone",  # Stage 2: Financial validation
    "vls_blueprint_definition": "Blueprint",  # Stage 3: Launch specification
    "vls_build_deployment": "Forge",  # Stage 4: Infrastructure generation
    "vls_lead_intake": "Index",  # Stage 5: Lead capture systems
    "vls_buyer_acquisition": "Vector",  # Stage 6: Buyer onboarding
    "vls_routing_delivery": "Foundry",  # Stage 7: Lead routing
    "vls_billing_revenue": "Vector",  # Stage 8: Payment processing
    "vls_monitoring_stoploss": "Aegis",  # Stage 9: Monitoring & risk
    "vls_knowledge_capture": "Index",  # Stage 10: Knowledge management
    "vls_status": "Overwatch",  # VLS status queries
    "vls_pause": "Aegis",  # Pause launch (risk decision)
    "vls_resume": "Overwatch",  # Resume launch
}


# Fallback routes when primary agent is unhealthy
FALLBACK_ROUTES: Dict[str, List[str]] = {
    # Security OPERATIONS (Citadel primary) - fallback to Sentinel for governance view
    "security_scan": ["Citadel", "Sentinel", "Aegis"],
    "vulnerability_check": ["Citadel", "Sentinel", "Aegis"],
    "incident_response": ["Citadel", "Sentinel", "Aegis"],
    "threat_detection": ["Citadel", "Sentinel", "Aegis"],
    "threat_hunting": ["Citadel", "Sentinel", "Aegis"],
    "vulnerability_scanning": ["Citadel", "Sentinel"],
    "vulnerability_assessment": ["Citadel", "Sentinel", "Aegis"],
    "security_monitoring": ["Citadel", "Sentinel"],
    "access_review": ["Citadel", "Sentinel", "Accord"],
    # Security GOVERNANCE (Sentinel primary) - fallback to Citadel for technical view
    "security_review": ["Sentinel", "Citadel", "Aegis"],
    "penetration_test": ["Sentinel", "Citadel"],
    "access_audit": ["Sentinel", "Citadel", "Accord"],
    "security_policy": ["Sentinel", "Accord", "Citadel"],
    "security_compliance": ["Sentinel", "Accord", "Citadel"],
    "security_governance": ["Sentinel", "Citadel", "Accord"],
    # Development & Engineering tasks - Forge, Foundry overlap
    "code_review": ["Forge", "Foundry"],
    "code_generation": ["Forge", "Foundry"],
    "bug_fix": ["Forge", "Foundry"],
    "testing": ["Forge", "Foundry"],
    "deployment": ["Forge", "Foundry"],
    "architecture": ["Forge", "Sentinel"],
    "api_design": ["Forge", "Blueprint"],
    "release_planning": ["Foundry", "Blueprint", "Forge"],
    "release_coordination": ["Foundry", "Forge"],
    "sprint_planning": ["Blueprint", "Foundry"],
    "sprint_review": ["Foundry", "Blueprint"],
    "quality_gate_check": ["Foundry", "Forge"],
    "test_planning": ["Foundry", "Forge"],
    "test_automation": ["Foundry", "Forge"],
    "pipeline_design": ["Foundry", "Forge"],
    # Risk & Compliance tasks - Aegis, Accord overlap
    "risk_assessment": ["Aegis", "Accord", "Sentinel"],
    "risk_identification": ["Aegis", "Accord"],
    "compliance_check": ["Accord", "Aegis"],
    "compliance_assessment": ["Accord", "Aegis"],
    "compliance_monitoring": ["Accord", "Aegis"],
    "audit_planning": ["Accord", "Aegis", "Keystone"],
    "audit_preparation": ["Accord", "Aegis"],
    "policy_review": ["Accord", "Aegis"],
    "threat_modeling": ["Aegis", "Citadel", "Sentinel"],
    "bcp_planning": ["Aegis", "Citadel"],
    "disaster_recovery": ["Aegis", "Citadel", "Sentinel"],
    "impact_analysis": ["Aegis", "Keystone"],
    # Financial tasks - Keystone overlaps
    "cost_analysis": ["Keystone", "Vector"],
    "budget_planning": ["Keystone", "Vector"],
    "roi_calculation": ["Keystone", "Vector"],
    "financial_modeling": ["Keystone", "Vector"],
    "pricing_analysis": ["Keystone", "Vector", "Echo"],
    "investment_analysis": ["Keystone", "Vector"],
    "forecast": ["Keystone", "Vector"],
    # Customer & Product tasks - Beacon, Blueprint, Vector overlap
    "feature_prioritization": ["Blueprint", "Beacon", "Vector"],
    "churn_analysis": ["Beacon", "Vector"],
    "customer_health_scoring": ["Beacon", "Vector"],
    "nps_analysis": ["Beacon", "Vector"],
    "retention_strategy": ["Beacon", "Vector", "Echo"],
    "customer_journey_mapping": ["Beacon", "Blueprint"],
    "requirements_gathering": ["Blueprint", "Beacon"],
    "product_spec": ["Blueprint", "Forge"],
    "user_story": ["Blueprint", "Foundry"],
    "market_research": ["Blueprint", "Compass", "Echo"],
    # Data & Research tasks - Index, Axiom, Sentinel overlap
    "data_analysis": ["Axiom", "Index", "Vector"],
    "data_governance": ["Index", "Sentinel", "Accord"],
    "data_quality_check": ["Index", "Sentinel"],
    "analytics_design": ["Index", "Axiom"],
    "metrics_definition": ["Index", "Axiom", "Vector"],
    "deep_research": ["Axiom", "Index"],
    "literature_review": ["Axiom", "Index"],
    "experiment_design": ["Axiom", "Vector"],
    "benchmarking": ["Axiom", "Forge", "Vector"],
    # Strategy & Marketing tasks - Compass, Echo overlap
    "market_analysis": ["Compass", "Echo", "Axiom"],
    "competitive_analysis": ["Compass", "Echo", "Axiom"],
    "strategic_planning": ["Compass", "Keystone"],
    "content_strategy": ["Compass", "Echo"],
    "brand_positioning": ["Compass", "Echo"],
    "go_to_market": ["Compass", "Echo", "Vector"],
    "campaign_creation": ["Echo", "Compass"],
    "demand_generation": ["Echo", "Vector"],
    "customer_segmentation": ["Echo", "Beacon", "Vector"],
    # Revenue tasks - Vector overlaps
    "revenue_tracking": ["Vector", "Keystone"],
    "conversion_analysis": ["Vector", "Echo"],
    "growth_experiment_design": ["Vector", "Axiom"],
    "cohort_analysis": ["Vector", "Index"],
    "ltv_calculation": ["Vector", "Keystone"],
    # Workbench Pipeline tasks - Multi-agent orchestration
    "workbench_evaluate": ["Forge", "Foundry"],
    "workbench_security_scan": ["Citadel", "Sentinel"],
    "workbench_test": ["Foundry", "Forge"],
    "workbench_build": ["Foundry", "Forge"],
    "workbench_deploy": ["Foundry", "Forge"],
    "workbench_database": ["Index", "Forge"],
    "workbench_secrets": ["Citadel", "Sentinel"],
    "containerization": ["Forge", "Foundry"],
    "infrastructure": ["Forge", "Foundry"],
    "configuration": ["Forge", "Foundry"],
    "deployment_execution": ["Foundry", "Forge"],
    "encryption": ["Citadel", "Sentinel"],
    # VLS Pipeline tasks - Multi-agent collaboration
    "vls_market_intelligence": ["Echo", "Compass", "Axiom"],
    "vls_validation_economics": ["Keystone", "Vector"],
    "vls_blueprint_definition": ["Blueprint", "Compass", "Echo"],
    "vls_build_deployment": ["Forge", "Foundry"],
    "vls_lead_intake": ["Index", "Forge"],
    "vls_buyer_acquisition": ["Vector", "Echo", "Beacon"],
    "vls_routing_delivery": ["Foundry", "Forge"],
    "vls_billing_revenue": ["Vector", "Keystone"],
    "vls_monitoring_stoploss": ["Aegis", "Keystone", "Citadel"],
    "vls_knowledge_capture": ["Index", "Axiom"],
}
