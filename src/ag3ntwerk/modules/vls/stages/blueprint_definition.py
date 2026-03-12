"""
VLS Stage 3: Blueprint Definition.

Creates formal executable launch specification with ICP and positioning.
"""

import logging
from typing import Any, Dict
from datetime import datetime, timezone
import uuid

from ag3ntwerk.modules.vls.core import VerticalBlueprint, NicheCandidate, EconomicsModel

logger = logging.getLogger(__name__)


async def execute_blueprint_definition(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute blueprint definition stage.

    Creates comprehensive launch specification.

    Args:
        context: Stage execution context with:
            - approved_niche: Approved niche from validation
            - economics_model: Financial model
            - niche_data: Original niche data
            - require_ceo_approval: Whether CEO approval is required

    Returns:
        Stage results with blueprint
    """
    logger.info("Executing VLS Stage 3: Blueprint Definition")

    approved_niche = context.get("approved_niche", {})
    economics_model = context.get("economics_model", {})
    require_ceo_approval = context.get("require_ceo_approval", True)

    if not approved_niche or not economics_model:
        return {
            "stage": "blueprint_definition",
            "success": False,
            "error": "Missing required niche or economics data",
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

    vertical_name = approved_niche.get("name", "Unknown Vertical")
    vertical_key = vertical_name.lower().replace(" ", "_").replace("-", "_")

    # Define ICP (Ideal Customer Profile)
    icp_definition = {
        "customer_type": "businesses",
        "industry": _extract_industry(vertical_name),
        "company_size": "small_to_medium",
        "decision_maker": "owner_or_manager",
        "pain_points": [
            "Need consistent lead flow",
            "Limited marketing resources",
            "High customer acquisition costs",
        ],
        "budget_range": {
            "min": economics_model.get("price_per_lead", 0) * 10,
            "max": economics_model.get("price_per_lead", 0) * 100,
        },
        "geographic_focus": context.get("target_metros", ["nationwide"]),
    }

    # Create value proposition
    value_proposition = (
        f"Pre-qualified, exclusive {_extract_service_type(vertical_name)} leads "
        f"delivered directly to your business with guaranteed response quality."
    )

    # Create positioning statement
    positioning_statement = (
        f"The trusted lead generation partner for {_extract_industry(vertical_name)} professionals "
        f"who need consistent, high-quality customer opportunities without the complexity "
        f"of managing their own marketing."
    )

    # Define lead sources
    lead_sources = [
        "google_ads",
        "social_media",
        "seo_organic",
        "local_directories",
        "referral_network",
    ]

    # Lead qualification criteria
    lead_qualification_criteria = {
        "required_fields": ["name", "phone", "email", "service_needed", "zip_code"],
        "validation_rules": {
            "phone": "valid_us_phone",
            "email": "valid_email_format",
            "zip_code": "valid_us_zip",
        },
        "qualification_questions": [
            "What service do you need?",
            "When do you need it?",
            "Is this for residential or commercial?",
        ],
        "min_score": 60,
    }

    # Buyer qualification criteria
    buyer_qualification_criteria = {
        "required_credentials": [
            "business_license",
            "insurance_certificate",
        ],
        "service_area": "defined_zip_codes",
        "capacity_verification": True,
        "background_check": True,
        "min_experience_years": 2,
    }

    # Pricing tiers
    pricing_tiers = [
        {
            "tier": "basic",
            "price_per_lead": economics_model.get("price_per_lead", 0),
            "features": ["Standard leads", "48hr exclusivity", "Email delivery"],
            "min_monthly_commitment": 10,
        },
        {
            "tier": "professional",
            "price_per_lead": economics_model.get("price_per_lead", 0) * 0.85,
            "features": [
                "Priority leads",
                "7-day exclusivity",
                "SMS + Email delivery",
                "Performance dashboard",
            ],
            "min_monthly_commitment": 25,
        },
        {
            "tier": "enterprise",
            "price_per_lead": economics_model.get("price_per_lead", 0) * 0.75,
            "features": [
                "Exclusive territory",
                "14-day exclusivity",
                "Dedicated account manager",
                "Custom integration",
            ],
            "min_monthly_commitment": 50,
        },
    ]

    # Required integrations
    required_integrations = [
        "payment_processor",  # Stripe
        "email_service",  # Transactional email
        "sms_service",  # SMS notifications
        "crm_system",  # Lead management
        "analytics",  # Tracking and reporting
    ]

    # Tech stack
    tech_stack = {
        "lead_capture": "custom_forms",
        "lead_routing": "rules_engine",
        "payment_processing": "stripe",
        "notifications": "twilio_sendgrid",
        "crm": "lightweight_custom",
        "hosting": "cloud_provider",
        "database": "postgresql",
    }

    # Deployment targets
    deployment_targets = ["staging", "production"]

    # Success metrics
    success_metrics = {
        "lead_acceptance_rate": 0.80,  # 80% of leads accepted by buyers
        "buyer_satisfaction": 4.0,  # 4.0/5.0 rating
        "lead_quality_score": 75.0,  # 75/100 quality score
        "time_to_delivery_minutes": 15,  # Average 15 min delivery time
        "monthly_revenue_target": economics_model.get("month_3_revenue", 0),
    }

    # Stop-loss thresholds
    stop_loss_thresholds = context.get(
        "stop_loss_thresholds",
        {
            "min_margin": economics_model.get("expected_margin", 0) * 0.5,
            "max_cpl": economics_model.get("cost_per_lead", 0) * 1.5,
            "min_acceptance_rate": 0.60,  # 60% minimum
            "max_churn_rate": 0.30,  # 30% maximum monthly churn
        },
    )

    # Monitoring frequency
    monitoring_frequency = "hourly"

    # Routing rules
    routing_rules = {
        "distribution": "round_robin",
        "exclusivity_period_hours": 48,
        "max_leads_per_buyer_daily": context.get("max_leads_per_buyer", 10),
        "geographic_matching": True,
        "tier_priority": True,
    }

    # Create blueprint
    blueprint_id = str(uuid.uuid4())

    blueprint_dict = {
        "blueprint_id": blueprint_id,
        "vertical_name": vertical_name,
        "vertical_key": vertical_key,
        "niche": approved_niche,
        "icp_definition": icp_definition,
        "value_proposition": value_proposition,
        "positioning_statement": positioning_statement,
        "economics": economics_model,
        "lead_sources": lead_sources,
        "lead_qualification_criteria": lead_qualification_criteria,
        "buyer_qualification_criteria": buyer_qualification_criteria,
        "pricing_tiers": pricing_tiers,
        "required_integrations": required_integrations,
        "tech_stack": tech_stack,
        "deployment_targets": deployment_targets,
        "success_metrics": success_metrics,
        "stop_loss_thresholds": stop_loss_thresholds,
        "monitoring_frequency": monitoring_frequency,
        "routing_rules": routing_rules,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "Blueprint",
        "approved_by": "CEO" if not require_ceo_approval else None,
        "version": "1.0",
    }

    result = {
        "stage": "blueprint_definition",
        "success": True,
        "blueprint": blueprint_dict,
        "qualification_criteria": lead_qualification_criteria,
        "pricing_tiers": pricing_tiers,
        "routing_rules": routing_rules,
        "requires_ceo_approval": require_ceo_approval and blueprint_dict["approved_by"] is None,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"Blueprint Definition complete: {vertical_name} ({blueprint_id})")

    return result


def _extract_industry(vertical_name: str) -> str:
    """Extract industry from vertical name."""
    name_lower = vertical_name.lower()
    if "plumbing" in name_lower:
        return "plumbing"
    elif "hvac" in name_lower or "heating" in name_lower or "cooling" in name_lower:
        return "hvac"
    elif "cleaning" in name_lower:
        return "cleaning_services"
    elif "pest" in name_lower:
        return "pest_control"
    elif "landscaping" in name_lower or "lawn" in name_lower:
        return "landscaping"
    else:
        return "home_services"


def _extract_service_type(vertical_name: str) -> str:
    """Extract service type from vertical name."""
    if "-" in vertical_name:
        parts = vertical_name.split("-")
        return parts[-1].strip().lower()
    return "service"
