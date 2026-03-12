"""
VLS Stage 5: Lead Intake.

Configures lead capture, classification, and qualification systems.
"""

import logging
from typing import Any, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def execute_lead_intake(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute lead intake stage.

    Configures lead capture and classification systems.

    Args:
        context: Stage execution context with:
            - blueprint: Launch specification
            - vertical_runtime: Runtime deployment info
            - qualification_rules: Lead qualification rules

    Returns:
        Stage results with intake configuration
    """
    logger.info("Executing VLS Stage 5: Lead Intake")

    blueprint = context.get("blueprint", {})
    vertical_runtime = context.get("vertical_runtime", {})

    if not blueprint:
        return {
            "stage": "lead_intake",
            "success": False,
            "error": "No blueprint provided",
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

    qualification_criteria = blueprint.get("lead_qualification_criteria", {})

    # Configure intake system
    intake_config = {
        "capture_forms": _generate_capture_forms(blueprint),
        "validation_rules": qualification_criteria.get("validation_rules", {}),
        "qualification_scoring": {
            "algorithm": "weighted_score",
            "min_passing_score": qualification_criteria.get("min_score", 60),
            "weights": {
                "completeness": 0.3,
                "response_time": 0.2,
                "verification_status": 0.5,
            },
        },
        "classification_rules": {
            "hot_lead": "> 80",
            "warm_lead": "60-80",
            "cold_lead": "< 60",
        },
        "data_schema": _generate_data_schema(qualification_criteria),
    }

    result = {
        "stage": "lead_intake",
        "success": True,
        "stage_completed": True,
        "intake_config": intake_config,
        "endpoints": {
            "form_submission": f"{vertical_runtime.get('endpoints', {}).get('lead_capture', '')}/submit",
            "validation": f"{vertical_runtime.get('endpoints', {}).get('api', '')}/validate",
        },
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("Lead Intake configuration complete")

    return result


def _generate_capture_forms(blueprint: Dict[str, Any]) -> Dict[str, Any]:
    """Generate lead capture form definitions."""
    required_fields = blueprint.get("lead_qualification_criteria", {}).get("required_fields", [])

    return {
        "primary_form": {
            "fields": [
                {"name": field, "type": "text", "required": True} for field in required_fields
            ],
            "submit_button_text": "Get Your Free Quote",
            "thank_you_message": "Thank you! A qualified professional will contact you soon.",
        }
    }


def _generate_data_schema(qualification_criteria: Dict[str, Any]) -> Dict[str, Any]:
    """Generate lead data schema."""
    return {
        "table": "leads",
        "fields": [
            {"name": field, "type": "VARCHAR(255)", "nullable": False}
            for field in qualification_criteria.get("required_fields", [])
        ]
        + [
            {"name": "lead_score", "type": "DECIMAL(5,2)", "nullable": False},
            {"name": "classification", "type": "VARCHAR(50)", "nullable": False},
            {"name": "created_at", "type": "TIMESTAMP", "nullable": False},
        ],
    }
