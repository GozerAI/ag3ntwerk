"""
VLS Hard Gate Validation System.

Implements evidence-based gate validation between VLS stages.
Each gate validates that sufficient evidence exists before allowing progression.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from ag3ntwerk.modules.vls.core import GateStatus

logger = logging.getLogger(__name__)


# =============================================================================
# Gate Data Structures
# =============================================================================


@dataclass
class GateEvidence:
    """Evidence item for gate validation."""

    evidence_type: str
    value: Any
    weight: float  # 0.0 to 1.0 (importance multiplier)
    source: str  # Stage or system that provided evidence
    confidence: float  # 0.0 to 1.0 (confidence in this evidence)


@dataclass
class GateResult:
    """Result of gate validation."""

    status: GateStatus
    score: float  # 0.0 to 100.0
    evidence: List[GateEvidence]
    pass_threshold: float
    failures: List[str]
    warnings: List[str]
    recommendation: str


# =============================================================================
# Base Gate Class
# =============================================================================


class VLSGate:
    """Base class for VLS stage gates."""

    def __init__(self, stage_name: str, pass_threshold: float = 70.0):
        """
        Initialize gate.

        Args:
            stage_name: Name of the stage this gate guards
            pass_threshold: Minimum score required to pass (0-100)
        """
        self.stage_name = stage_name
        self.pass_threshold = pass_threshold

    def validate(self, context: Dict[str, Any]) -> GateResult:
        """
        Validate gate criteria.

        Must be implemented by subclasses.

        Args:
            context: Stage results and evidence

        Returns:
            Gate validation result
        """
        raise NotImplementedError


# =============================================================================
# Stage-Specific Gates
# =============================================================================


class MarketIntelligenceGate(VLSGate):
    """Gate between Stage 1 (Market Intelligence) and Stage 2 (Validation)."""

    def __init__(self):
        super().__init__("market_intelligence", pass_threshold=70.0)

    def validate(self, context: Dict[str, Any]) -> GateResult:
        """Validate market intelligence findings."""
        evidence = []
        failures = []
        warnings = []

        candidates = context.get("niche_candidates", [])

        # Required: At least 3 viable candidates
        if len(candidates) < 3:
            failures.append(f"Insufficient candidates: {len(candidates)} < 3 required")
        else:
            evidence.append(
                GateEvidence(
                    evidence_type="candidate_count",
                    value=len(candidates),
                    weight=0.2,
                    source="market_intelligence",
                    confidence=1.0,
                )
            )

        # Required: Top candidate has confidence > 0.7
        if candidates:
            top_candidate = candidates[0]
            confidence = top_candidate.get("confidence_score", 0)

            if confidence < 0.7:
                failures.append(f"Low confidence in top candidate: {confidence:.2f} < 0.70")
            else:
                evidence.append(
                    GateEvidence(
                        evidence_type="top_candidate_confidence",
                        value=confidence,
                        weight=0.3,
                        source="market_intelligence",
                        confidence=confidence,
                    )
                )

            # Warning if trend score is low
            trend_score = top_candidate.get("trend_score", 0)
            if trend_score < 50:
                warnings.append(f"Low trend score for top candidate: {trend_score:.1f}")

            evidence.append(
                GateEvidence(
                    evidence_type="trend_score",
                    value=trend_score,
                    weight=0.25,
                    source="market_intelligence",
                    confidence=0.8,
                )
            )

        # Check for market size estimate
        if candidates and candidates[0].get("estimated_market_size"):
            market_size = candidates[0]["estimated_market_size"]
            evidence.append(
                GateEvidence(
                    evidence_type="market_size",
                    value=market_size,
                    weight=0.25,
                    source="market_intelligence",
                    confidence=0.7,
                )
            )
        else:
            warnings.append("No market size estimate available")

        # Calculate score
        if evidence:
            score = sum(
                e.value * e.weight * e.confidence
                for e in evidence
                if isinstance(e.value, (int, float))
            )
            score = min(100.0, score * 100)  # Normalize to 0-100
        else:
            score = 0.0

        # Determine status
        if failures:
            status = GateStatus.FAIL
            recommendation = "Refine market intelligence: " + "; ".join(failures)
        elif score >= self.pass_threshold:
            status = GateStatus.PASS
            recommendation = "Proceed to validation & economics stage"
        else:
            status = GateStatus.INSUFFICIENT_EVIDENCE
            recommendation = f"Gather more evidence (score: {score:.1f}/{self.pass_threshold})"

        return GateResult(
            status=status,
            score=score,
            evidence=evidence,
            pass_threshold=self.pass_threshold,
            failures=failures,
            warnings=warnings,
            recommendation=recommendation,
        )


class ValidationEconomicsGate(VLSGate):
    """Gate between Stage 2 (Validation) and Stage 3 (Blueprint)."""

    def __init__(self):
        super().__init__("validation_economics", pass_threshold=75.0)

    def validate(self, context: Dict[str, Any]) -> GateResult:
        """Validate economics model."""
        evidence = []
        failures = []
        warnings = []

        economics = context.get("economics_model", {})

        if not economics:
            failures.append("No economics model provided")
            return GateResult(
                status=GateStatus.FAIL,
                score=0.0,
                evidence=[],
                pass_threshold=self.pass_threshold,
                failures=failures,
                warnings=[],
                recommendation="Create economics model before proceeding",
            )

        # Required: Positive expected margin
        margin = economics.get("expected_margin", 0)
        if margin <= 0:
            failures.append(f"Negative or zero margin: {margin}%")
        elif margin < 20:
            warnings.append(f"Low margin: {margin}% (recommended: >20%)")
            evidence.append(
                GateEvidence(
                    evidence_type="margin",
                    value=margin / 100,  # Normalize to 0-1
                    weight=0.35,
                    source="validation_economics",
                    confidence=0.8,
                )
            )
        else:
            evidence.append(
                GateEvidence(
                    evidence_type="margin",
                    value=margin / 100,
                    weight=0.35,
                    source="validation_economics",
                    confidence=0.9,
                )
            )

        # Required: Acceptable CAC/LTV ratio
        cac_ltv = economics.get("cac_ltv_ratio", float("inf"))
        if cac_ltv > 3.0:
            failures.append(f"Poor CAC/LTV ratio: {cac_ltv:.2f} (must be < 3.0)")
        else:
            # Lower is better; normalize inversely
            normalized_cac = max(0, 1 - (cac_ltv / 3.0))
            evidence.append(
                GateEvidence(
                    evidence_type="cac_ltv_ratio",
                    value=normalized_cac,
                    weight=0.30,
                    source="validation_economics",
                    confidence=0.85,
                )
            )

        # Check break-even timeline
        break_even_months = economics.get("break_even_months", float("inf"))
        if break_even_months > 12:
            warnings.append(f"Long break-even period: {break_even_months} months")
            confidence = 0.6
        else:
            confidence = 0.8

        # Normalize to 0-1 (12 months = 0, 0 months = 1)
        normalized_breakeven = max(0, 1 - (break_even_months / 12))
        evidence.append(
            GateEvidence(
                evidence_type="break_even_timeline",
                value=normalized_breakeven,
                weight=0.20,
                source="validation_economics",
                confidence=confidence,
            )
        )

        # Check confidence level
        confidence_level = economics.get("confidence_level", 0)
        if confidence_level < 0.6:
            warnings.append(f"Low confidence in economics model: {confidence_level:.2f}")

        evidence.append(
            GateEvidence(
                evidence_type="model_confidence",
                value=confidence_level,
                weight=0.15,
                source="validation_economics",
                confidence=confidence_level,
            )
        )

        # Calculate score
        score = sum(e.value * e.weight * e.confidence for e in evidence) * 100

        # Determine status
        if failures:
            status = GateStatus.FAIL
            recommendation = "Revise economics model: " + "; ".join(failures)
        elif score >= self.pass_threshold:
            status = GateStatus.PASS
            recommendation = "Proceed to blueprint definition"
        else:
            status = (
                GateStatus.CONDITIONAL_PASS if score >= 65 else GateStatus.INSUFFICIENT_EVIDENCE
            )
            recommendation = (
                f"Economics marginally viable (score: {score:.1f}/{self.pass_threshold})"
            )

        return GateResult(
            status=status,
            score=score,
            evidence=evidence,
            pass_threshold=self.pass_threshold,
            failures=failures,
            warnings=warnings,
            recommendation=recommendation,
        )


class BlueprintDefinitionGate(VLSGate):
    """Gate between Stage 3 (Blueprint) and Stage 4 (Build)."""

    def __init__(self):
        super().__init__("blueprint_definition", pass_threshold=80.0)

    def validate(self, context: Dict[str, Any]) -> GateResult:
        """Validate blueprint completeness."""
        evidence = []
        failures = []
        warnings = []

        blueprint = context.get("blueprint", {})

        if not blueprint:
            failures.append("No blueprint provided")
            return GateResult(
                status=GateStatus.FAIL,
                score=0.0,
                evidence=[],
                pass_threshold=self.pass_threshold,
                failures=failures,
                warnings=[],
                recommendation="Create complete blueprint before proceeding",
            )

        # Required fields checklist
        required_fields = [
            "vertical_name",
            "icp_definition",
            "value_proposition",
            "pricing_tiers",
            "lead_sources",
            "tech_stack",
            "success_metrics",
            "stop_loss_thresholds",
        ]

        missing_fields = [field for field in required_fields if not blueprint.get(field)]

        if missing_fields:
            failures.append(f"Missing required fields: {', '.join(missing_fields)}")
            score = (len(required_fields) - len(missing_fields)) / len(required_fields) * 100
        else:
            score = 100.0
            evidence.append(
                GateEvidence(
                    evidence_type="blueprint_completeness",
                    value=1.0,
                    weight=1.0,
                    source="blueprint_definition",
                    confidence=1.0,
                )
            )

        # Check for CEO approval
        if not blueprint.get("approved_by"):
            warnings.append("Blueprint not yet approved by CEO")

        # Determine status
        if failures:
            status = GateStatus.FAIL
            recommendation = "Complete blueprint: " + "; ".join(failures)
        elif score >= self.pass_threshold:
            status = GateStatus.PASS
            recommendation = "Proceed to build & deployment"
        else:
            status = GateStatus.INSUFFICIENT_EVIDENCE
            recommendation = f"Blueprint incomplete (score: {score:.1f}/{self.pass_threshold})"

        return GateResult(
            status=status,
            score=score,
            evidence=evidence,
            pass_threshold=self.pass_threshold,
            failures=failures,
            warnings=warnings,
            recommendation=recommendation,
        )


class OperationalReadinessGate(VLSGate):
    """Generic gate for operational readiness (stages 4-8)."""

    def __init__(self, stage_name: str, pass_threshold: float = 70.0):
        super().__init__(stage_name, pass_threshold)

    def validate(self, context: Dict[str, Any]) -> GateResult:
        """Validate operational readiness."""
        evidence = []
        failures = []
        warnings = []

        # Check if stage completed successfully
        stage_completed = context.get("stage_completed", False)
        if not stage_completed:
            failures.append(f"Stage {self.stage_name} not completed")

        # Check for errors
        errors = context.get("errors", [])
        if errors:
            failures.append(f"{len(errors)} error(s) encountered during stage")

        # Calculate score based on completion
        score = 100.0 if stage_completed and not errors else 0.0

        if stage_completed:
            evidence.append(
                GateEvidence(
                    evidence_type="stage_completion",
                    value=1.0,
                    weight=1.0,
                    source=self.stage_name,
                    confidence=1.0,
                )
            )

        # Determine status
        if failures:
            status = GateStatus.FAIL
            recommendation = f"Resolve issues in {self.stage_name}: " + "; ".join(failures)
        else:
            status = GateStatus.PASS
            recommendation = "Proceed to next stage"

        return GateResult(
            status=status,
            score=score,
            evidence=evidence,
            pass_threshold=self.pass_threshold,
            failures=failures,
            warnings=warnings,
            recommendation=recommendation,
        )


class MonitoringStopLossGate(VLSGate):
    """Gate for Stage 9 (Monitoring & Stop-Loss)."""

    def __init__(self):
        super().__init__("monitoring_stoploss", pass_threshold=75.0)

    def validate(self, context: Dict[str, Any]) -> GateResult:
        """Validate monitoring setup and check for stop-loss violations."""
        evidence = []
        failures = []
        warnings = []

        # Check monitoring configuration
        monitoring_configured = context.get("monitoring_configured", False)
        if not monitoring_configured:
            failures.append("Monitoring not configured")
        else:
            evidence.append(
                GateEvidence(
                    evidence_type="monitoring_setup",
                    value=1.0,
                    weight=0.5,
                    source="monitoring_stoploss",
                    confidence=1.0,
                )
            )

        # Check for stop-loss violations
        violations = context.get("stop_loss_violations", [])
        if violations:
            severe_violations = [v for v in violations if v.get("severity") == "critical"]
            if severe_violations:
                failures.append(f"{len(severe_violations)} critical stop-loss violation(s)")
            else:
                warnings.append(f"{len(violations)} stop-loss warning(s)")
                evidence.append(
                    GateEvidence(
                        evidence_type="stop_loss_status",
                        value=0.5,  # Warnings present but not critical
                        weight=0.5,
                        source="monitoring_stoploss",
                        confidence=1.0,
                    )
                )
        else:
            evidence.append(
                GateEvidence(
                    evidence_type="stop_loss_status",
                    value=1.0,
                    weight=0.5,
                    source="monitoring_stoploss",
                    confidence=1.0,
                )
            )

        # Calculate score
        score = sum(e.value * e.weight * e.confidence for e in evidence) * 100

        # Determine status
        if failures:
            status = GateStatus.FAIL
            recommendation = "Resolve monitoring issues: " + "; ".join(failures)
        elif score >= self.pass_threshold:
            status = GateStatus.PASS
            recommendation = "Proceed to knowledge capture"
        else:
            status = GateStatus.CONDITIONAL_PASS
            recommendation = "Monitor closely and address warnings"

        return GateResult(
            status=status,
            score=score,
            evidence=evidence,
            pass_threshold=self.pass_threshold,
            failures=failures,
            warnings=warnings,
            recommendation=recommendation,
        )


# =============================================================================
# Gate Registry
# =============================================================================


GATE_REGISTRY: Dict[str, type] = {
    "market_intelligence": MarketIntelligenceGate,
    "validation_economics": ValidationEconomicsGate,
    "blueprint_definition": BlueprintDefinitionGate,
    "build_deployment": OperationalReadinessGate,
    "lead_intake": OperationalReadinessGate,
    "buyer_acquisition": OperationalReadinessGate,
    "routing_delivery": OperationalReadinessGate,
    "billing_revenue": OperationalReadinessGate,
    "monitoring_stoploss": MonitoringStopLossGate,
    "knowledge_capture": OperationalReadinessGate,
}


def get_gate(stage_name: str) -> VLSGate:
    """
    Get a gate instance for a stage.

    Args:
        stage_name: Name of the stage

    Returns:
        Gate instance

    Raises:
        KeyError: If stage not found in registry
    """
    gate_class = GATE_REGISTRY.get(stage_name)
    if not gate_class:
        raise KeyError(f"No gate defined for stage: {stage_name}")

    # Instantiate with stage name if generic gate
    if gate_class == OperationalReadinessGate:
        return gate_class(stage_name)
    else:
        return gate_class()
