"""
Trend Service - High-level service interface for agents.

Provides a clean API for ag3ntwerk agents to interact with the
trend intelligence system.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.modules.trends.core import (
    Trend,
    TrendCategory,
    TrendSource,
    TrendDatabase,
    TrendAnalyzer,
    NicheOpportunity,
)
from ag3ntwerk.modules.trends.collectors import (
    TrendCollectorManager,
    NicheIdentifier,
)
from ag3ntwerk.modules.trends.intelligence import (
    TrendIntelligenceManager,
    TrendCorrelation,
    TrendDrift,
)

logger = logging.getLogger(__name__)


class TrendService:
    """
    High-level trend intelligence service for ag3ntwerk agents.

    This service provides a unified interface for:
    - Echo (Echo): Market trends for campaign planning
    - Blueprint (Visionary): Product opportunity identification
    - Axiom (Axiom): Revenue trend analysis
    - CEO (Apex): Strategic trend overview

    Example:
        ```python
        service = TrendService()
        await service.initialize()

        # Get trend report for Echo
        report = await service.get_agent_report("Echo")

        # Find niche opportunities for Blueprint
        opportunities = await service.find_opportunities(min_score=60)

        # Collect fresh data
        await service.refresh_trends()
        ```
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the trend service."""
        from pathlib import Path

        if db_path:
            self.db = TrendDatabase(Path(db_path))
        else:
            self.db = TrendDatabase()

        self.collector_manager = TrendCollectorManager(self.db)
        self.intelligence = TrendIntelligenceManager(self.db)
        self.analyzer = TrendAnalyzer(self.db)

        self._initialized = False
        self._last_refresh: Optional[datetime] = None

    async def initialize(self) -> None:
        """Initialize the service with default collectors."""
        if self._initialized:
            return

        self.collector_manager.add_default_collectors()
        self._initialized = True
        logger.info("TrendService initialized")

    async def refresh_trends(self, sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Refresh trend data from sources.

        Args:
            sources: Optional list of source names to refresh. If None, refreshes all.

        Returns:
            Summary of collection results
        """
        if not self._initialized:
            await self.initialize()

        if sources:
            trends = []
            for source in sources:
                try:
                    source_trends = await self.collector_manager.collect_from(source)
                    trends.extend(source_trends)
                except ValueError as e:
                    logger.warning(f"Unknown source: {source}")
        else:
            trends = await self.collector_manager.collect_all()

        self._last_refresh = datetime.now(timezone.utc)

        return {
            "trends_collected": len(trends),
            "sources_used": sources or list(self.collector_manager.collectors.keys()),
            "refreshed_at": self._last_refresh.isoformat(),
        }

    async def get_trends(
        self,
        category: Optional[str] = None,
        min_score: float = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get trends with optional filters.

        Args:
            category: Optional category filter
            min_score: Minimum score threshold
            limit: Maximum number of trends to return

        Returns:
            List of trend dictionaries
        """
        cat = TrendCategory(category) if category else None
        trends = self.db.get_trends(category=cat, min_score=min_score, limit=limit)
        return [t.to_dict() for t in trends]

    async def get_trend(self, trend_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific trend by ID."""
        trend = self.db.get_trend(trend_id)
        return trend.to_dict() if trend else None

    async def search_trends(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search trends by name or keywords."""
        trends = self.db.search_trends(query, limit=limit)
        return [t.to_dict() for t in trends]

    async def get_top_trends(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top-scoring trends."""
        trends = self.db.get_top_trends(limit=limit)
        return [t.to_dict() for t in trends]

    async def get_emerging_trends(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get emerging trends with high velocity."""
        trends = self.db.get_emerging_trends(limit=limit)
        return [t.to_dict() for t in trends]

    async def find_opportunities(
        self,
        min_score: float = 50,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Find niche market opportunities.

        Args:
            min_score: Minimum opportunity score
            limit: Maximum number of opportunities

        Returns:
            List of niche opportunity dictionaries
        """
        # First, identify new niches from current trends
        niches = self.collector_manager.identify_niches(min_confidence=0.4)

        # Get all niches above threshold
        all_niches = self.db.get_niches(min_score=min_score, limit=limit)

        # Rank them
        ranked = self.intelligence.opportunity_scorer.rank_opportunities(all_niches)

        return [
            {
                "opportunity": n.to_dict(),
                "score": score,
                "breakdown": breakdown,
            }
            for n, score, breakdown in ranked
        ]

    async def get_signals(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get buy/sell signals for trends."""
        return self.intelligence.get_trend_signals()

    async def detect_drifts(self, lookback_days: int = 7) -> List[Dict[str, Any]]:
        """Detect significant trend changes."""
        drifts = self.intelligence.drift_detector.detect_drifts(lookback_days=lookback_days)
        return [d.to_dict() for d in drifts]

    async def find_correlations(self, min_correlation: float = 0.3) -> List[Dict[str, Any]]:
        """Find correlations between trends."""
        correlations = self.intelligence.find_correlations(min_correlation=min_correlation)
        return [c.to_dict() for c in correlations]

    async def get_intelligence_report(self) -> Dict[str, Any]:
        """Generate comprehensive intelligence report."""
        return self.intelligence.generate_intelligence_report()

    async def get_agent_report(self, agent_code: str) -> Dict[str, Any]:
        """
        Generate a report tailored for a specific agent.

        Args:
            agent_code: The agent code (Echo, Blueprint, Axiom, CEO)

        Returns:
            Agent-specific trend report
        """
        base_report = self.intelligence.generate_intelligence_report()

        if agent_code == "Echo":
            # Marketing focus: campaigns, segments, content trends
            return {
                "agent": "Echo",
                "focus": "Marketing & Growth",
                "generated_at": base_report["generated_at"],
                "key_trends": await self.get_top_trends(limit=5),
                "emerging_opportunities": await self.get_emerging_trends(limit=5),
                "campaign_signals": {
                    "hot_topics": [s for s in base_report["signals"]["strong_buy"][:3]],
                    "declining_topics": [s for s in base_report["signals"]["strong_sell"][:3]],
                },
                "content_recommendations": self._get_content_recommendations(base_report),
                "market_pulse": base_report["summary"],
            }

        elif agent_code == "Blueprint":
            # Product focus: opportunities, niches, innovation
            opportunities = await self.find_opportunities(min_score=50, limit=5)
            return {
                "agent": "Blueprint",
                "focus": "Product & Innovation",
                "generated_at": base_report["generated_at"],
                "product_opportunities": opportunities,
                "technology_trends": [
                    t for t in await self.get_trends(category="technology", limit=10)
                ],
                "innovation_signals": base_report["signals"]["strong_buy"][:5],
                "market_gaps": [
                    opp["opportunity"]["pain_points"]
                    for opp in opportunities
                    if opp["opportunity"].get("pain_points")
                ],
                "recommendations": base_report["recommendations"],
            }

        elif agent_code == "Axiom":
            # Revenue focus: commercial trends, pricing signals
            return {
                "agent": "Axiom",
                "focus": "Revenue & Research",
                "generated_at": base_report["generated_at"],
                "commercial_trends": await self.get_trends(category="ecommerce", limit=10),
                "revenue_signals": {
                    "growth": base_report["signals"]["strong_buy"],
                    "caution": base_report["signals"]["strong_sell"],
                },
                "market_drifts": base_report["alerts"]["drifts"],
                "correlations": base_report["alerts"]["correlations"][:5],
                "research_priorities": self._get_research_priorities(base_report),
            }

        elif agent_code == "CEO":
            # Strategic overview: high-level summary
            return {
                "agent": "CEO",
                "focus": "Strategic Overview",
                "generated_at": base_report["generated_at"],
                "executive_summary": {
                    "trends_analyzed": base_report["summary"]["total_trends_analyzed"],
                    "opportunities_identified": len(base_report["top_opportunities"]),
                    "market_sentiment": self._calculate_sentiment(base_report["signals"]),
                },
                "strategic_signals": base_report["signals"]["strong_buy"][:3],
                "risk_indicators": base_report["signals"]["strong_sell"][:3],
                "top_opportunities": base_report["top_opportunities"][:3],
                "key_recommendations": base_report["recommendations"][:3],
            }

        else:
            # Default: full report
            return base_report

    def _get_content_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate content recommendations for Echo."""
        recommendations = []

        for signal in report["signals"]["strong_buy"][:3]:
            recommendations.append(f"Create content around '{signal['name']}' - trending upward")

        for signal in report["signals"]["buy"][:2]:
            recommendations.append(f"Consider exploring '{signal['name']}' in upcoming campaigns")

        return recommendations

    def _get_research_priorities(self, report: Dict[str, Any]) -> List[str]:
        """Generate research priorities for Axiom."""
        priorities = []

        if report["alerts"]["drifts"]:
            priorities.append(f"Investigate drift: {report['alerts']['drifts'][0]['analysis']}")

        for opp in report["top_opportunities"][:2]:
            priorities.append(f"Research opportunity: {opp['niche']['name']}")

        return priorities

    def _calculate_sentiment(self, signals: Dict[str, List]) -> str:
        """Calculate overall market sentiment."""
        buy_count = len(signals["strong_buy"]) + len(signals["buy"])
        sell_count = len(signals["strong_sell"]) + len(signals["sell"])
        hold_count = len(signals["hold"])

        total = buy_count + sell_count + hold_count
        if total == 0:
            return "neutral"

        buy_ratio = buy_count / total
        sell_ratio = sell_count / total

        if buy_ratio > 0.6:
            return "bullish"
        elif sell_ratio > 0.6:
            return "bearish"
        elif buy_ratio > sell_ratio:
            return "slightly_bullish"
        elif sell_ratio > buy_ratio:
            return "slightly_bearish"
        else:
            return "neutral"

    async def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        db_stats = self.db.get_stats()
        collector_stats = self.collector_manager.get_collector_stats()

        return {
            "database": db_stats,
            "collectors": collector_stats,
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "initialized": self._initialized,
        }

    async def run_autonomous_analysis(self) -> Dict[str, Any]:
        """
        Run autonomous analysis cycle.

        This method is designed to be called by the scheduler for
        periodic autonomous trend analysis.
        """
        if not self._initialized:
            await self.initialize()

        # 1. Refresh data
        refresh_result = await self.refresh_trends()

        # 2. Run analysis
        analysis_result = self.intelligence.analyze_all()

        # 3. Identify niches
        niches = self.collector_manager.identify_niches()

        # 4. Detect drifts
        drifts = await self.detect_drifts()

        # 5. Generate report
        report = await self.get_intelligence_report()

        return {
            "cycle_completed_at": datetime.now(timezone.utc).isoformat(),
            "refresh": refresh_result,
            "analysis": analysis_result,
            "niches_identified": len(niches),
            "drifts_detected": len(drifts),
            "report_generated": True,
            "next_actions": report.get("recommendations", []),
        }

    # =========================================================================
    # MCP Interface Methods (aliases for consistency with MCP tool handlers)
    # =========================================================================

    async def run_analysis_cycle(
        self,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run analysis cycle - MCP interface alias.

        Alias for run_autonomous_analysis() that accepts sources parameter.
        """
        if sources:
            await self.refresh_trends(sources=sources)
        return await self.run_autonomous_analysis()

    async def get_trending(
        self,
        category: Optional[str] = None,
        min_score: float = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get trending topics - MCP interface alias.

        Alias for get_trends() for MCP compatibility.
        """
        return await self.get_trends(
            category=category,
            min_score=min_score,
            limit=limit,
        )

    async def identify_niches(
        self,
        min_opportunity_score: float = 50,
    ) -> List[Dict[str, Any]]:
        """
        Identify niche opportunities - MCP interface alias.

        Alias for find_opportunities() for MCP compatibility.
        """
        return await self.find_opportunities(
            min_score=min_opportunity_score,
            limit=20,
        )

    async def get_correlations(
        self,
        trend_id: Optional[str] = None,
        min_correlation: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Get trend correlations - MCP interface alias.

        Alias for find_correlations() for MCP compatibility.
        If trend_id is provided, filters results to that trend.
        """
        correlations = await self.find_correlations(min_correlation=min_correlation)

        if trend_id:
            # Filter to correlations involving this trend
            correlations = [
                c
                for c in correlations
                if c.get("trend_a_id") == trend_id or c.get("trend_b_id") == trend_id
            ]

        return correlations
