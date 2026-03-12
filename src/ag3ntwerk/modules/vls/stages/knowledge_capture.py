"""
VLS Stage 10: Knowledge Capture.

Captures launch knowledge and creates reusable templates.
"""

import logging
from typing import Any, Dict
from datetime import datetime, timezone
import json
from pathlib import Path

logger = logging.getLogger(__name__)


async def execute_knowledge_capture(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute knowledge capture stage.

    Captures launch knowledge and generates templates.

    Args:
        context: Stage execution context with:
            - launch_data: Aggregated data from all stages
            - create_template: Whether to create reusable template

    Returns:
        Stage results with knowledge artifacts
    """
    logger.info("Executing VLS Stage 10: Knowledge Capture")

    launch_data = context.get("launch_data", {})
    create_template = context.get("create_template", True)

    blueprint = launch_data.get("blueprint", {})
    economics = launch_data.get("economics", {})
    buyer_data = launch_data.get("buyer_data", {})
    metrics = launch_data.get("metrics", {})

    if not blueprint:
        return {
            "stage": "knowledge_capture",
            "success": False,
            "error": "Insufficient launch data for knowledge capture",
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

    # Capture key learnings
    learnings = {
        "vertical_name": blueprint.get("vertical_name", "Unknown"),
        "industry": _extract_industry(blueprint.get("vertical_name", "")),
        "launch_date": blueprint.get("created_at", datetime.now(timezone.utc).isoformat()),
        "economics_summary": {
            "price_per_lead": economics.get("price_per_lead", 0),
            "cost_per_lead": economics.get("cost_per_lead", 0),
            "expected_margin": economics.get("expected_margin", 0),
            "break_even_months": economics.get("break_even_months", 0),
        },
        "buyer_summary": {
            "total_buyers": len(buyer_data.get("buyer_pools", [])),
            "geographic_coverage": buyer_data.get("geographic_coverage", []),
        },
        "success_factors": [
            "Clear ICP definition",
            "Strong unit economics",
            "Qualified buyer pool",
            "Automated monitoring",
        ],
        "challenges": [
            "Buyer acquisition timeline",
            "Initial lead quality calibration",
        ],
    }

    # Generate playbook
    playbook = {
        "vertical_type": _extract_industry(blueprint.get("vertical_name", "")),
        "recommended_approach": {
            "market_intelligence": "Use trends module for niche identification",
            "economics_validation": "Target 30%+ margins with CAC/LTV < 3.0",
            "buyer_acquisition": "Start with 3-5 buyers per metro",
            "lead_pricing": f"${economics.get('price_per_lead', 0):.2f} per lead (adjust by market)",
        },
        "critical_metrics": list(blueprint.get("success_metrics", {}).keys()),
        "stop_loss_thresholds": blueprint.get("stop_loss_thresholds", {}),
        "timeline": {
            "stage_1_market_intelligence": "1-2 days",
            "stage_2_validation": "2-3 days",
            "stage_3_blueprint": "3-5 days",
            "stage_4_build": "5-10 days",
            "stage_5_intake": "2-3 days",
            "stage_6_buyers": "10-15 days",
            "stage_7_routing": "2-3 days",
            "stage_8_billing": "2-3 days",
            "stage_9_monitoring": "1-2 days",
            "total_to_live": "30-45 days",
        },
    }

    # Create template if requested
    template = None
    if create_template:
        template = _generate_vertical_template(blueprint, economics, playbook)

        # Save template to disk
        try:
            template_dir = Path.home() / ".ag3ntwerk" / "vls" / "templates"
            template_dir.mkdir(parents=True, exist_ok=True)

            vertical_type = _extract_industry(blueprint.get("vertical_name", ""))
            template_file = template_dir / f"{vertical_type}_template.json"

            with open(template_file, "w") as f:
                json.dump(template, f, indent=2)

            logger.info(f"Template saved: {template_file}")
            template["saved_to"] = str(template_file)

        except Exception as e:
            logger.warning(f"Could not save template: {e}")

    # Knowledge artifacts
    artifacts = {
        "learnings": learnings,
        "playbook": playbook,
        "template": template,
    }

    result = {
        "stage": "knowledge_capture",
        "success": True,
        "stage_completed": True,
        "artifacts": artifacts,
        "template_created": create_template and template is not None,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("Knowledge Capture complete")

    return result


def _extract_industry(vertical_name: str) -> str:
    """Extract industry from vertical name."""
    name_lower = vertical_name.lower()
    if "plumbing" in name_lower:
        return "plumbing"
    elif "hvac" in name_lower:
        return "hvac"
    elif "cleaning" in name_lower:
        return "cleaning"
    elif "pest" in name_lower:
        return "pest_control"
    elif "landscaping" in name_lower or "lawn" in name_lower:
        return "landscaping"
    else:
        return "home_services"


def _generate_vertical_template(
    blueprint: Dict[str, Any], economics: Dict[str, Any], playbook: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate reusable vertical template."""
    return {
        "template_type": _extract_industry(blueprint.get("vertical_name", "")),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "blueprint_template": {
            "icp_definition": blueprint.get("icp_definition", {}),
            "lead_qualification_criteria": blueprint.get("lead_qualification_criteria", {}),
            "buyer_qualification_criteria": blueprint.get("buyer_qualification_criteria", {}),
            "pricing_tiers": blueprint.get("pricing_tiers", []),
            "routing_rules": blueprint.get("routing_rules", {}),
        },
        "economics_template": {
            "typical_cpl_range": [
                economics.get("cost_per_lead", 0) * 0.8,
                economics.get("cost_per_lead", 0) * 1.2,
            ],
            "typical_price_range": [
                economics.get("price_per_lead", 0) * 0.8,
                economics.get("price_per_lead", 0) * 1.2,
            ],
            "target_margin": economics.get("expected_margin", 0),
        },
        "playbook": playbook,
    }
