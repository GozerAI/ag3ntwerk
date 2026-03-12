"""
VLS Stage 2: Validation & Economics.

Models unit economics and determines financial viability.
"""

import logging
from typing import Any, Dict
from datetime import datetime, timezone

from ag3ntwerk.modules.vls.core import EconomicsModel

logger = logging.getLogger(__name__)


async def execute_validation_economics(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute validation & economics stage.

    Models unit economics and validates financial viability.

    Args:
        context: Stage execution context with:
            - top_candidate: Selected niche from market intelligence
            - niche_candidates: All candidates
            - budget_caps: Budget constraints
            - target_margin: Target profit margin
            - max_cac_ltv_ratio: Maximum CAC/LTV ratio

    Returns:
        Stage results with economics model
    """
    logger.info("Executing VLS Stage 2: Validation & Economics")

    top_candidate = context.get("top_candidate", {})
    budget_caps = context.get("budget_caps", {})
    target_margin = context.get("target_margin", 0.3)
    max_cac_ltv_ratio = context.get("max_cac_ltv_ratio", 3.0)

    if not top_candidate:
        return {
            "stage": "validation_economics",
            "success": False,
            "error": "No candidate provided for validation",
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

    # Build economics model
    vertical_name = top_candidate.get("name", "Unknown Vertical")

    # Estimate costs based on niche characteristics
    search_volume = top_candidate.get("search_volume", 10000)
    competition_level = top_candidate.get("competition_level", "medium")

    # Calculate cost per lead (CPL) based on competition
    cpl_base = {"low": 8.0, "medium": 15.0, "high": 25.0}
    cost_per_lead = cpl_base.get(competition_level, 15.0)

    # Calculate pricing based on market size
    estimated_market_size = top_candidate.get("estimated_market_size", 500000)
    price_per_lead = cost_per_lead * 2.5  # Target 2.5x markup

    # Estimate monthly volume (conservative: 1% of search volume)
    estimated_monthly_volume = int(search_volume * 0.01)

    # Acquisition cost for buyers
    acquisition_cost = price_per_lead * 100  # Cost to acquire one buyer

    # Monthly operational costs
    operational_cost_monthly = 2500.0  # Base operational overhead
    infrastructure_cost_monthly = 500.0  # Infrastructure costs

    # Calculate margins
    gross_margin = ((price_per_lead - cost_per_lead) / price_per_lead) * 100

    # Calculate CAC/LTV
    # Assume buyer LTV = 100 leads * price per lead * 50% margin
    buyer_ltv = 100 * price_per_lead * 0.5
    cac_ltv_ratio = acquisition_cost / buyer_ltv if buyer_ltv > 0 else float("inf")

    # Expected margin after operational costs
    monthly_revenue = estimated_monthly_volume * price_per_lead
    monthly_costs = (
        (estimated_monthly_volume * cost_per_lead)
        + operational_cost_monthly
        + infrastructure_cost_monthly
    )
    expected_margin = (
        ((monthly_revenue - monthly_costs) / monthly_revenue * 100) if monthly_revenue > 0 else 0
    )

    # Break-even calculation
    fixed_monthly_costs = operational_cost_monthly + infrastructure_cost_monthly
    contribution_per_lead = price_per_lead - cost_per_lead
    break_even_leads = (
        fixed_monthly_costs / contribution_per_lead if contribution_per_lead > 0 else float("inf")
    )
    break_even_months = (
        int(break_even_leads / estimated_monthly_volume) + 1 if estimated_monthly_volume > 0 else 12
    )

    # Revenue projections
    month_1_revenue = estimated_monthly_volume * price_per_lead * 0.3  # Ramp up
    month_3_revenue = estimated_monthly_volume * price_per_lead * 0.7
    month_6_revenue = estimated_monthly_volume * price_per_lead
    month_12_revenue = estimated_monthly_volume * price_per_lead * 1.2  # Growth

    # Confidence level based on data quality
    confidence_level = top_candidate.get("confidence_score", 0.7)

    # Build assumptions list
    assumptions = [
        f"Monthly lead volume: {estimated_monthly_volume} (1% of search volume)",
        f"Cost per lead: ${cost_per_lead:.2f} ({competition_level} competition)",
        f"Price per lead: ${price_per_lead:.2f} (2.5x markup)",
        f"Buyer acquisition cost: ${acquisition_cost:.2f}",
        f"Average buyer purchases 100 leads over lifetime",
    ]

    # Identify risk factors
    risk_factors = []
    if cac_ltv_ratio > max_cac_ltv_ratio * 0.8:
        risk_factors.append(f"High CAC/LTV ratio: {cac_ltv_ratio:.2f}")
    if expected_margin < target_margin * 100:
        risk_factors.append(f"Low expected margin: {expected_margin:.1f}%")
    if break_even_months > 6:
        risk_factors.append(f"Long break-even period: {break_even_months} months")
    if competition_level == "high":
        risk_factors.append("High market competition")

    # Create economics model
    economics = EconomicsModel(
        vertical_name=vertical_name,
        cost_per_lead=cost_per_lead,
        acquisition_cost=acquisition_cost,
        operational_cost_monthly=operational_cost_monthly,
        infrastructure_cost_monthly=infrastructure_cost_monthly,
        price_per_lead=price_per_lead,
        estimated_monthly_volume=estimated_monthly_volume,
        gross_margin=gross_margin,
        cac_ltv_ratio=cac_ltv_ratio,
        expected_margin=expected_margin,
        break_even_months=break_even_months,
        month_1_revenue=month_1_revenue,
        month_3_revenue=month_3_revenue,
        month_6_revenue=month_6_revenue,
        month_12_revenue=month_12_revenue,
        confidence_level=confidence_level,
        assumptions=assumptions,
        risk_factors=risk_factors,
        validated_by="Keystone",
    )

    # Validate against criteria
    success = (
        expected_margin >= target_margin * 100 * 0.8  # Allow 20% variance
        and cac_ltv_ratio <= max_cac_ltv_ratio
        and break_even_months <= 12
    )

    # Calculate stop-loss thresholds
    stop_loss_thresholds = {
        "min_margin": expected_margin * 0.5,  # 50% of expected
        "max_cpl": cost_per_lead * 1.5,  # 150% of estimated
        "min_monthly_revenue": month_3_revenue * 0.5,  # 50% of month 3 target
        "max_cac": acquisition_cost * 1.3,  # 130% of estimated
    }

    result = {
        "stage": "validation_economics",
        "success": success,
        "approved_niche": top_candidate if success else None,
        "economics_model": {
            "vertical_name": economics.vertical_name,
            "cost_per_lead": economics.cost_per_lead,
            "price_per_lead": economics.price_per_lead,
            "estimated_monthly_volume": economics.estimated_monthly_volume,
            "gross_margin": economics.gross_margin,
            "expected_margin": economics.expected_margin,
            "cac_ltv_ratio": economics.cac_ltv_ratio,
            "break_even_months": economics.break_even_months,
            "month_1_revenue": economics.month_1_revenue,
            "month_3_revenue": economics.month_3_revenue,
            "month_6_revenue": economics.month_6_revenue,
            "month_12_revenue": economics.month_12_revenue,
            "confidence_level": economics.confidence_level,
            "assumptions": economics.assumptions,
            "risk_factors": economics.risk_factors,
        },
        "stop_loss_thresholds": stop_loss_thresholds,
        "validation_criteria": {
            "target_margin": target_margin * 100,
            "actual_margin": expected_margin,
            "max_cac_ltv": max_cac_ltv_ratio,
            "actual_cac_ltv": cac_ltv_ratio,
            "max_breakeven_months": 12,
            "actual_breakeven_months": break_even_months,
        },
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

    if not success:
        result["error"] = f"Economics validation failed: {', '.join(risk_factors)}"

    logger.info(f"Validation & Economics complete: {'Approved' if success else 'Rejected'}")

    return result
