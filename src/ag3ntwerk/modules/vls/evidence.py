"""
VLS Evidence Collection Framework.

Provides utilities for collecting, scoring, and aggregating evidence
throughout the VLS pipeline to support evidence-based decision making.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Evidence Types
# =============================================================================


@dataclass
class EvidenceItem:
    """A single piece of evidence collected during VLS execution."""

    evidence_type: str
    value: Any
    source: str  # Stage or system that provided evidence
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "evidence_type": self.evidence_type,
            "value": self.value,
            "source": self.source,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class EvidenceScore:
    """Aggregated evidence score for a decision."""

    total_score: float  # 0.0 to 100.0
    evidence_count: int
    confidence_level: float  # 0.0 to 1.0
    evidence_items: List[EvidenceItem]
    decision_recommendation: str


# =============================================================================
# Evidence Collector
# =============================================================================


class EvidenceCollector:
    """Collects and manages evidence throughout VLS execution."""

    def __init__(self):
        """Initialize evidence collector."""
        self.evidence_store: Dict[str, List[EvidenceItem]] = {}

    def add_evidence(
        self,
        stage: str,
        evidence_type: str,
        value: Any,
        source: str,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceItem:
        """
        Add a piece of evidence.

        Args:
            stage: Stage this evidence belongs to
            evidence_type: Type of evidence
            value: Evidence value
            source: Source of evidence
            confidence: Confidence level (0.0 to 1.0)
            metadata: Additional metadata

        Returns:
            Created evidence item
        """
        evidence = EvidenceItem(
            evidence_type=evidence_type,
            value=value,
            source=source,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

        if stage not in self.evidence_store:
            self.evidence_store[stage] = []

        self.evidence_store[stage].append(evidence)

        logger.debug(
            f"Added evidence to {stage}: {evidence_type} = {value} (confidence: {confidence})"
        )

        return evidence

    def get_evidence(self, stage: str) -> List[EvidenceItem]:
        """Get all evidence for a stage."""
        return self.evidence_store.get(stage, [])

    def get_all_evidence(self) -> Dict[str, List[EvidenceItem]]:
        """Get all collected evidence."""
        return self.evidence_store.copy()

    def clear_stage_evidence(self, stage: str) -> None:
        """Clear evidence for a specific stage."""
        if stage in self.evidence_store:
            del self.evidence_store[stage]
            logger.debug(f"Cleared evidence for {stage}")


# =============================================================================
# Confidence Scoring
# =============================================================================


def calculate_confidence_score(
    evidence_items: List[EvidenceItem], weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate aggregate confidence score from evidence items.

    Args:
        evidence_items: List of evidence items
        weights: Optional weights by evidence type (default: equal weight)

    Returns:
        Aggregate confidence score (0.0 to 1.0)
    """
    if not evidence_items:
        return 0.0

    weights = weights or {}
    total_weighted_confidence = 0.0
    total_weight = 0.0

    for item in evidence_items:
        weight = weights.get(item.evidence_type, 1.0)
        total_weighted_confidence += item.confidence * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return total_weighted_confidence / total_weight


def calculate_evidence_score(
    evidence_items: List[EvidenceItem],
    weights: Optional[Dict[str, float]] = None,
    min_confidence: float = 0.5,
) -> EvidenceScore:
    """
    Calculate aggregate evidence score with decision recommendation.

    Args:
        evidence_items: List of evidence items
        weights: Optional weights by evidence type
        min_confidence: Minimum confidence threshold

    Returns:
        Evidence score with recommendation
    """
    if not evidence_items:
        return EvidenceScore(
            total_score=0.0,
            evidence_count=0,
            confidence_level=0.0,
            evidence_items=[],
            decision_recommendation="Insufficient evidence - gather more data",
        )

    # Calculate weighted score
    weights = weights or {}
    total_score = 0.0
    total_weight = 0.0

    for item in evidence_items:
        if item.confidence < min_confidence:
            continue  # Skip low-confidence evidence

        weight = weights.get(item.evidence_type, 1.0)

        # Normalize value to 0-1 if it's a number
        if isinstance(item.value, (int, float)):
            normalized_value = min(1.0, max(0.0, item.value))
        else:
            normalized_value = 1.0  # Non-numeric evidence counts as present

        total_score += normalized_value * weight * item.confidence
        total_weight += weight

    # Normalize score to 0-100
    if total_weight > 0:
        score = (total_score / total_weight) * 100
    else:
        score = 0.0

    # Calculate aggregate confidence
    confidence = calculate_confidence_score(evidence_items, weights)

    # Generate recommendation
    if score >= 80 and confidence >= 0.8:
        recommendation = "Strong evidence - proceed with high confidence"
    elif score >= 70 and confidence >= 0.7:
        recommendation = "Good evidence - proceed with caution"
    elif score >= 60 and confidence >= 0.6:
        recommendation = "Moderate evidence - gather additional data or proceed with risk awareness"
    elif score >= 50:
        recommendation = "Weak evidence - recommend gathering more data"
    else:
        recommendation = "Insufficient evidence - do not proceed without additional validation"

    return EvidenceScore(
        total_score=score,
        evidence_count=len(evidence_items),
        confidence_level=confidence,
        evidence_items=evidence_items,
        decision_recommendation=recommendation,
    )


# =============================================================================
# Evidence Aggregation
# =============================================================================


def aggregate_evidence_by_type(evidence_items: List[EvidenceItem]) -> Dict[str, List[EvidenceItem]]:
    """
    Group evidence items by type.

    Args:
        evidence_items: List of evidence items

    Returns:
        Dictionary mapping evidence type to items
    """
    aggregated: Dict[str, List[EvidenceItem]] = {}

    for item in evidence_items:
        if item.evidence_type not in aggregated:
            aggregated[item.evidence_type] = []
        aggregated[item.evidence_type].append(item)

    return aggregated


def filter_evidence_by_confidence(
    evidence_items: List[EvidenceItem], min_confidence: float
) -> List[EvidenceItem]:
    """
    Filter evidence items by minimum confidence threshold.

    Args:
        evidence_items: List of evidence items
        min_confidence: Minimum confidence threshold (0.0 to 1.0)

    Returns:
        Filtered list of evidence items
    """
    return [item for item in evidence_items if item.confidence >= min_confidence]


def get_most_recent_evidence(
    evidence_items: List[EvidenceItem], count: int = 10
) -> List[EvidenceItem]:
    """
    Get the most recent evidence items.

    Args:
        evidence_items: List of evidence items
        count: Number of items to return

    Returns:
        Most recent evidence items
    """
    sorted_items = sorted(evidence_items, key=lambda x: x.timestamp, reverse=True)
    return sorted_items[:count]


# =============================================================================
# Evidence Reporting
# =============================================================================


def generate_evidence_summary(evidence_items: List[EvidenceItem]) -> Dict[str, Any]:
    """
    Generate a summary report of evidence.

    Args:
        evidence_items: List of evidence items

    Returns:
        Evidence summary dictionary
    """
    if not evidence_items:
        return {
            "total_count": 0,
            "average_confidence": 0.0,
            "evidence_types": [],
            "sources": [],
            "time_range": None,
        }

    # Calculate statistics
    total_count = len(evidence_items)
    average_confidence = sum(item.confidence for item in evidence_items) / total_count

    # Get unique types and sources
    evidence_types = list(set(item.evidence_type for item in evidence_items))
    sources = list(set(item.source for item in evidence_items))

    # Get time range
    timestamps = [item.timestamp for item in evidence_items]
    time_range = {
        "earliest": min(timestamps).isoformat(),
        "latest": max(timestamps).isoformat(),
    }

    # Group by type with counts
    type_counts = {}
    for item in evidence_items:
        type_counts[item.evidence_type] = type_counts.get(item.evidence_type, 0) + 1

    return {
        "total_count": total_count,
        "average_confidence": average_confidence,
        "evidence_types": evidence_types,
        "type_counts": type_counts,
        "sources": sources,
        "time_range": time_range,
    }
