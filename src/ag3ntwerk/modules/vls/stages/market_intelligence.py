"""
VLS Stage 1: Market Intelligence.

Identifies and ranks viable niche candidates from market signals.
Integrates with the trends module for market data.
"""

import logging
from typing import Any, Dict, List
from datetime import datetime, timezone

from ag3ntwerk.modules.vls.core import NicheCandidate

logger = logging.getLogger(__name__)


async def execute_market_intelligence(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute market intelligence stage.

    Identifies viable niche candidates from market trends and signals.

    Args:
        context: Stage execution context with:
            - constraints: Budget, geographic, etc.
            - data_sources: Sources to analyze
            - min_confidence: Minimum confidence threshold
            - min_candidates: Minimum number of candidates required

    Returns:
        Stage results with niche candidates
    """
    logger.info("Executing VLS Stage 1: Market Intelligence")

    constraints = context.get("constraints", {})
    min_confidence = context.get("min_confidence", 0.7)
    min_candidates = context.get("min_candidates", 3)

    # Import trends service for market intelligence
    try:
        from ag3ntwerk.modules.trends import TrendService

        trend_service = TrendService()
    except ImportError:
        logger.warning("Trends module not available, using mock data")
        trend_service = None

    candidates = []

    if trend_service:
        # Use real trends data
        try:
            # Get trending opportunities
            opportunities = await trend_service.find_opportunities(min_score=60)

            # Convert opportunities to niche candidates
            for i, opp in enumerate(opportunities[: min_candidates * 2]):
                candidate = NicheCandidate(
                    niche_id=f"niche_{i+1}",
                    name=opp.get("name", f"Niche {i+1}"),
                    description=opp.get("description", "Market opportunity identified from trends"),
                    search_volume=opp.get("search_volume", 10000),
                    trend_score=opp.get("score", 70.0),
                    competition_level=_assess_competition_level(opp.get("score", 70.0)),
                    confidence_score=opp.get("confidence", 0.75),
                    estimated_market_size=opp.get("market_size"),
                    growth_rate=opp.get("growth_rate"),
                    evidence_sources=opp.get("sources", ["trends_module"]),
                    keywords=opp.get("keywords", []),
                    related_niches=opp.get("related", []),
                )
                candidates.append(candidate)

        except Exception as e:
            logger.error(f"Error fetching trends data: {e}")
            # Fall back to mock data
            candidates = _generate_mock_candidates(min_candidates)
    else:
        # Generate mock candidates for testing
        candidates = _generate_mock_candidates(min_candidates)

    # Sort by confidence score
    candidates.sort(key=lambda c: c.confidence_score, reverse=True)

    # Filter by minimum confidence
    qualified_candidates = [c for c in candidates if c.confidence_score >= min_confidence]

    # Convert to dictionaries for serialization
    candidate_dicts = [
        {
            "niche_id": c.niche_id,
            "name": c.name,
            "description": c.description,
            "search_volume": c.search_volume,
            "trend_score": c.trend_score,
            "competition_level": c.competition_level,
            "confidence_score": c.confidence_score,
            "estimated_market_size": c.estimated_market_size,
            "growth_rate": c.growth_rate,
            "evidence_sources": c.evidence_sources,
            "keywords": c.keywords,
            "related_niches": c.related_niches,
        }
        for c in qualified_candidates
    ]

    success = len(qualified_candidates) >= min_candidates

    result = {
        "stage": "market_intelligence",
        "success": success,
        "niche_candidates": candidate_dicts,
        "top_candidate": candidate_dicts[0] if candidate_dicts else None,
        "total_candidates": len(candidates),
        "qualified_candidates": len(qualified_candidates),
        "min_confidence": min_confidence,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

    if not success:
        result["error"] = (
            f"Insufficient qualified candidates: {len(qualified_candidates)} < {min_candidates}"
        )

    logger.info(
        f"Market Intelligence complete: {len(qualified_candidates)} qualified candidates found"
    )

    return result


def _assess_competition_level(trend_score: float) -> str:
    """Assess competition level based on trend score."""
    if trend_score >= 80:
        return "high"
    elif trend_score >= 60:
        return "medium"
    else:
        return "low"


def _generate_mock_candidates(count: int) -> List[NicheCandidate]:
    """Generate mock niche candidates for testing."""
    mock_niches = [
        {
            "name": "Local Home Services - Plumbing",
            "description": "Emergency plumbing services for residential customers",
            "search_volume": 45000,
            "trend_score": 78.5,
            "confidence": 0.82,
            "market_size": 1200000,
            "growth_rate": 0.15,
            "keywords": ["emergency plumber", "plumbing services", "leak repair"],
        },
        {
            "name": "HVAC Maintenance Services",
            "description": "Scheduled HVAC maintenance and repair services",
            "search_volume": 38000,
            "trend_score": 75.2,
            "confidence": 0.79,
            "market_size": 950000,
            "growth_rate": 0.12,
            "keywords": ["hvac maintenance", "air conditioning repair", "furnace service"],
        },
        {
            "name": "Home Cleaning Services",
            "description": "Residential cleaning and maid services",
            "search_volume": 52000,
            "trend_score": 72.8,
            "confidence": 0.76,
            "market_size": 800000,
            "growth_rate": 0.18,
            "keywords": ["house cleaning", "maid service", "cleaning services near me"],
        },
        {
            "name": "Pest Control Services",
            "description": "Residential and commercial pest control",
            "search_volume": 31000,
            "trend_score": 70.5,
            "confidence": 0.74,
            "market_size": 650000,
            "growth_rate": 0.10,
            "keywords": ["pest control", "exterminator", "termite treatment"],
        },
        {
            "name": "Landscaping Services",
            "description": "Lawn care and landscaping for residential properties",
            "search_volume": 42000,
            "trend_score": 68.3,
            "confidence": 0.71,
            "market_size": 720000,
            "growth_rate": 0.14,
            "keywords": ["landscaping", "lawn care", "yard maintenance"],
        },
    ]

    candidates = []
    for i, niche in enumerate(mock_niches[:count]):
        candidate = NicheCandidate(
            niche_id=f"mock_niche_{i+1}",
            name=niche["name"],
            description=niche["description"],
            search_volume=niche["search_volume"],
            trend_score=niche["trend_score"],
            competition_level=_assess_competition_level(niche["trend_score"]),
            confidence_score=niche["confidence"],
            estimated_market_size=niche["market_size"],
            growth_rate=niche["growth_rate"],
            evidence_sources=["mock_data"],
            keywords=niche["keywords"],
            related_niches=[],
        )
        candidates.append(candidate)

    return candidates
