"""
Trend Intelligence Bridge - Integration between ag3ntwerk and Trend Analyzer.

This module provides a bridge connecting ag3ntwerk agents to the
trend-analyzer system for market intelligence:
- Market trend detection
- Niche identification
- Opportunity scoring
- Competitive signals

Primary users:
- Blueprint (Blueprint): Product strategy and roadmap
- Axiom (Axiom): Market research
- Echo (Echo): Marketing trends

Features:
- Real-time trend tracking
- Opportunity scoring and ranking
- Niche market identification
- Competitive intelligence
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class TrendCategory(Enum):
    """Categories of market trends."""

    PRODUCT = "product"
    TECHNOLOGY = "technology"
    CONSUMER_BEHAVIOR = "consumer_behavior"
    MARKET_SEGMENT = "market_segment"
    PRICING = "pricing"
    CHANNEL = "channel"
    REGULATORY = "regulatory"
    COMPETITIVE = "competitive"


class TrendDirection(Enum):
    """Direction of a trend."""

    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    EMERGING = "emerging"
    MATURE = "mature"


class OpportunityType(Enum):
    """Types of market opportunities."""

    NEW_PRODUCT = "new_product"
    MARKET_EXPANSION = "market_expansion"
    PRICING_OPTIMIZATION = "pricing_optimization"
    COMPETITIVE_GAP = "competitive_gap"
    NICHE_MARKET = "niche_market"
    CROSS_SELL = "cross_sell"
    UPSELL = "upsell"
    PARTNERSHIP = "partnership"


class RiskLevel(Enum):
    """Risk levels for opportunities."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MarketTrend:
    """A market trend identified by the analyzer."""

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    category: TrendCategory = TrendCategory.PRODUCT
    direction: TrendDirection = TrendDirection.RISING
    strength: float = 0.5  # 0-1 scale
    velocity: float = 0.0  # Rate of change
    volume: int = 0  # Data points supporting the trend
    keywords: List[str] = field(default_factory=list)
    related_products: List[str] = field(default_factory=list)
    geographic_regions: List[str] = field(default_factory=list)
    time_horizon: str = "short_term"  # short_term, medium_term, long_term
    confidence: float = 0.7
    first_detected: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "direction": self.direction.value,
            "strength": self.strength,
            "velocity": self.velocity,
            "volume": self.volume,
            "keywords": self.keywords,
            "confidence": self.confidence,
            "time_horizon": self.time_horizon,
            "first_detected": self.first_detected.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class MarketNiche:
    """An identified market niche."""

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    size_estimate: str = ""  # small, medium, large
    growth_rate: float = 0.0
    competition_level: str = "medium"  # low, medium, high
    entry_barriers: List[str] = field(default_factory=list)
    key_players: List[str] = field(default_factory=list)
    target_audience: str = ""
    price_sensitivity: str = "medium"  # low, medium, high
    related_trends: List[UUID] = field(default_factory=list)
    opportunity_score: float = 0.5
    risk_score: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "size_estimate": self.size_estimate,
            "growth_rate": self.growth_rate,
            "competition_level": self.competition_level,
            "entry_barriers": self.entry_barriers,
            "key_players": self.key_players,
            "opportunity_score": self.opportunity_score,
            "risk_score": self.risk_score,
        }


@dataclass
class MarketOpportunity:
    """A market opportunity identified from trends."""

    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    opportunity_type: OpportunityType = OpportunityType.NEW_PRODUCT
    source_trends: List[UUID] = field(default_factory=list)
    source_niches: List[UUID] = field(default_factory=list)
    potential_revenue: Optional[float] = None
    investment_required: Optional[float] = None
    time_to_market: str = ""  # quick, moderate, long
    risk_level: RiskLevel = RiskLevel.MEDIUM
    score: float = 0.5  # 0-1 opportunity score
    confidence: float = 0.7
    recommended_actions: List[str] = field(default_factory=list)
    blocking_factors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "opportunity_type": self.opportunity_type.value,
            "potential_revenue": self.potential_revenue,
            "investment_required": self.investment_required,
            "time_to_market": self.time_to_market,
            "risk_level": self.risk_level.value,
            "score": self.score,
            "confidence": self.confidence,
            "recommended_actions": self.recommended_actions,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CompetitiveSignal:
    """A competitive intelligence signal."""

    id: UUID = field(default_factory=uuid4)
    competitor: str = ""
    signal_type: str = ""  # product_launch, pricing_change, expansion, etc.
    description: str = ""
    impact: str = "medium"  # low, medium, high
    urgency: str = "medium"  # low, medium, high
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""
    recommended_response: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TrendIntelligenceBridge:
    """
    Bridge between ag3ntwerk agents and Trend Analyzer system.

    This bridge enables:
    1. Blueprint - Product strategy informed by market trends
    2. Axiom - Market research and analysis
    3. Echo - Marketing trend insights

    Usage:
        bridge = TrendIntelligenceBridge()
        bridge.connect_analyzer(trend_analyzer)

        # Get rising trends
        trends = await bridge.get_rising_trends(category=TrendCategory.PRODUCT)

        # Find opportunities
        opportunities = await bridge.find_opportunities(min_score=0.7)

        # Get niche markets
        niches = await bridge.get_niche_markets()
    """

    # Scoring weights
    TREND_SCORE_WEIGHTS = {
        "strength": 0.3,
        "velocity": 0.25,
        "confidence": 0.25,
        "volume": 0.2,
    }

    OPPORTUNITY_SCORE_WEIGHTS = {
        "trend_strength": 0.25,
        "market_size": 0.2,
        "competition": 0.2,
        "risk": 0.2,
        "time_to_market": 0.15,
    }

    def __init__(
        self,
        cpo: Optional[Any] = None,
        cro: Optional[Any] = None,
        cmo: Optional[Any] = None,
    ):
        """
        Initialize the Trend Intelligence bridge.

        Args:
            cpo: Optional Blueprint instance
            cro: Optional Axiom instance
            cmo: Optional Echo instance
        """
        self._cpo = cpo
        self._cro = cro
        self._cmo = cmo

        # Trend analyzer connection
        self._trend_analyzer: Optional[Any] = None
        self._api_endpoint: Optional[str] = None

        # Data stores
        self._trends: Dict[UUID, MarketTrend] = {}
        self._niches: Dict[UUID, MarketNiche] = {}
        self._opportunities: Dict[UUID, MarketOpportunity] = {}
        self._signals: Dict[UUID, CompetitiveSignal] = {}

        # Watch lists
        self._watched_keywords: List[str] = []
        self._watched_competitors: List[str] = []

        # Metrics
        self._metrics = {
            "trends_tracked": 0,
            "niches_identified": 0,
            "opportunities_found": 0,
            "signals_detected": 0,
            "last_scan": None,
        }

        logger.info("TrendIntelligenceBridge initialized")

    def connect_analyzer(
        self,
        trend_analyzer: Any = None,
        api_endpoint: Optional[str] = None,
    ) -> None:
        """
        Connect to trend analyzer system.

        Args:
            trend_analyzer: Trend analyzer instance
            api_endpoint: API endpoint for trend-analyzer service
        """
        if trend_analyzer:
            self._trend_analyzer = trend_analyzer
            logger.info("Connected Trend Analyzer instance")
        if api_endpoint:
            self._api_endpoint = api_endpoint
            logger.info(f"Set Trend Analyzer API endpoint: {api_endpoint}")

    def connect_executives(
        self,
        cpo: Any = None,
        cro: Any = None,
        cmo: Any = None,
    ) -> None:
        """Connect ag3ntwerk agents to the bridge."""
        if cpo:
            self._cpo = cpo
            logger.info("Connected Blueprint (Blueprint) to trend intelligence")
        if cro:
            self._cro = cro
            logger.info("Connected Axiom (Axiom) to trend intelligence")
        if cmo:
            self._cmo = cmo
            logger.info("Connected Echo (Echo) to trend intelligence")

    def add_watched_keyword(self, keyword: str) -> None:
        """Add keyword to watch list."""
        if keyword not in self._watched_keywords:
            self._watched_keywords.append(keyword)

    def add_watched_competitor(self, competitor: str) -> None:
        """Add competitor to watch list."""
        if competitor not in self._watched_competitors:
            self._watched_competitors.append(competitor)

    async def scan_trends(
        self,
        categories: Optional[List[TrendCategory]] = None,
        keywords: Optional[List[str]] = None,
    ) -> List[MarketTrend]:
        """
        Scan for market trends.

        Args:
            categories: Optional categories to focus on
            keywords: Optional keywords to search for

        Returns:
            List of detected trends
        """
        trends = []

        # Use trend analyzer if available
        if self._trend_analyzer:
            try:
                # Call trend analyzer API
                raw_trends = await self._trend_analyzer.collect_trends(
                    categories=[c.value for c in (categories or [])],
                    keywords=keywords or self._watched_keywords,
                )

                for rt in raw_trends:
                    trend = self._parse_raw_trend(rt)
                    self._trends[trend.id] = trend
                    trends.append(trend)

            except Exception as e:
                logger.error(f"Trend scan failed: {e}")

        # Use API endpoint if available
        elif self._api_endpoint:
            try:
                import aiohttp

                async with aiohttp.ClientSession() as session:
                    params = {}
                    if keywords:
                        params["keywords"] = ",".join(keywords)

                    async with session.get(
                        f"{self._api_endpoint}/api/trends/rising",
                        params=params,
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for rt in data.get("trends", []):
                                trend = self._parse_api_trend(rt)
                                self._trends[trend.id] = trend
                                trends.append(trend)

            except Exception as e:
                logger.error(f"API trend scan failed: {e}")

        self._metrics["trends_tracked"] = len(self._trends)
        self._metrics["last_scan"] = datetime.now(timezone.utc).isoformat()

        return trends

    def _parse_raw_trend(self, raw: Dict[str, Any]) -> MarketTrend:
        """Parse raw trend data from analyzer."""
        return MarketTrend(
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            category=TrendCategory(raw.get("category", "product")),
            direction=TrendDirection(raw.get("direction", "rising")),
            strength=raw.get("strength", 0.5),
            velocity=raw.get("velocity", 0.0),
            volume=raw.get("volume", 0),
            keywords=raw.get("keywords", []),
            confidence=raw.get("confidence", 0.7),
        )

    def _parse_api_trend(self, raw: Dict[str, Any]) -> MarketTrend:
        """Parse trend data from API response."""
        return MarketTrend(
            name=raw.get("trend", raw.get("name", "")),
            description=raw.get("description", ""),
            category=TrendCategory(raw.get("category", "product")),
            direction=TrendDirection.RISING,
            strength=raw.get("score", 0.5),
            keywords=raw.get("keywords", []),
        )

    async def get_rising_trends(
        self,
        category: Optional[TrendCategory] = None,
        min_strength: float = 0.3,
        limit: int = 10,
    ) -> List[MarketTrend]:
        """
        Get rising market trends.

        Args:
            category: Optional category filter
            min_strength: Minimum trend strength
            limit: Maximum trends to return

        Returns:
            List of rising trends sorted by strength
        """
        trends = list(self._trends.values())

        # Filter by direction
        trends = [
            t for t in trends if t.direction in [TrendDirection.RISING, TrendDirection.EMERGING]
        ]

        # Filter by category
        if category:
            trends = [t for t in trends if t.category == category]

        # Filter by strength
        trends = [t for t in trends if t.strength >= min_strength]

        # Sort by strength descending
        trends.sort(key=lambda t: t.strength, reverse=True)

        return trends[:limit]

    async def identify_niches(
        self,
        min_opportunity_score: float = 0.5,
    ) -> List[MarketNiche]:
        """
        Identify market niches from trends.

        Args:
            min_opportunity_score: Minimum opportunity score

        Returns:
            List of identified niches
        """
        niches = []

        # Use trend analyzer if available
        if self._trend_analyzer:
            try:
                raw_niches = await self._trend_analyzer.identify_niches()

                for rn in raw_niches:
                    niche = MarketNiche(
                        name=rn.get("name", ""),
                        description=rn.get("description", ""),
                        size_estimate=rn.get("size", "medium"),
                        growth_rate=rn.get("growth_rate", 0.0),
                        competition_level=rn.get("competition", "medium"),
                        entry_barriers=rn.get("barriers", []),
                        key_players=rn.get("players", []),
                        opportunity_score=rn.get("opportunity_score", 0.5),
                        risk_score=rn.get("risk_score", 0.5),
                    )

                    if niche.opportunity_score >= min_opportunity_score:
                        self._niches[niche.id] = niche
                        niches.append(niche)

            except Exception as e:
                logger.error(f"Niche identification failed: {e}")

        # Derive niches from strong trends
        strong_trends = [t for t in self._trends.values() if t.strength >= 0.7]
        for trend in strong_trends:
            niche = self._derive_niche_from_trend(trend)
            if niche.opportunity_score >= min_opportunity_score:
                self._niches[niche.id] = niche
                niches.append(niche)

        self._metrics["niches_identified"] = len(self._niches)
        return niches

    def _derive_niche_from_trend(self, trend: MarketTrend) -> MarketNiche:
        """Derive a market niche from a trend."""
        # Calculate opportunity score
        opportunity = 0.5
        if trend.direction == TrendDirection.EMERGING:
            opportunity += 0.2
        if trend.strength >= 0.8:
            opportunity += 0.15
        if trend.velocity > 0:
            opportunity += 0.1

        # Calculate risk score
        risk = 0.5
        if trend.confidence < 0.6:
            risk += 0.2
        if trend.direction == TrendDirection.EMERGING:
            risk += 0.1  # Emerging trends are riskier

        return MarketNiche(
            name=f"{trend.name} Market",
            description=f"Niche market derived from {trend.name} trend",
            growth_rate=trend.velocity,
            related_trends=[trend.id],
            opportunity_score=min(1.0, opportunity),
            risk_score=min(1.0, risk),
        )

    async def find_opportunities(
        self,
        min_score: float = 0.5,
        opportunity_types: Optional[List[OpportunityType]] = None,
        max_risk: RiskLevel = RiskLevel.HIGH,
    ) -> List[MarketOpportunity]:
        """
        Find market opportunities from trends and niches.

        Args:
            min_score: Minimum opportunity score
            opportunity_types: Optional types to filter
            max_risk: Maximum acceptable risk level

        Returns:
            List of market opportunities
        """
        opportunities = []

        # Use trend analyzer if available
        if self._trend_analyzer:
            try:
                raw_opps = await self._trend_analyzer.find_opportunities()

                for ro in raw_opps:
                    opp = self._parse_raw_opportunity(ro)
                    if opp.score >= min_score:
                        self._opportunities[opp.id] = opp
                        opportunities.append(opp)

            except Exception as e:
                logger.error(f"Opportunity finding failed: {e}")

        # Derive opportunities from trends and niches
        derived = self._derive_opportunities()
        for opp in derived:
            if opp.score >= min_score:
                self._opportunities[opp.id] = opp
                opportunities.append(opp)

        # Filter by type
        if opportunity_types:
            opportunities = [o for o in opportunities if o.opportunity_type in opportunity_types]

        # Filter by risk
        risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        max_risk_idx = risk_order.index(max_risk)
        opportunities = [o for o in opportunities if risk_order.index(o.risk_level) <= max_risk_idx]

        # Sort by score
        opportunities.sort(key=lambda o: o.score, reverse=True)

        self._metrics["opportunities_found"] = len(self._opportunities)
        return opportunities

    def _parse_raw_opportunity(self, raw: Dict[str, Any]) -> MarketOpportunity:
        """Parse raw opportunity data."""
        return MarketOpportunity(
            title=raw.get("title", ""),
            description=raw.get("description", ""),
            opportunity_type=OpportunityType(raw.get("type", "new_product")),
            potential_revenue=raw.get("revenue"),
            investment_required=raw.get("investment"),
            time_to_market=raw.get("time_to_market", "moderate"),
            risk_level=RiskLevel(raw.get("risk", "medium")),
            score=raw.get("score", 0.5),
            confidence=raw.get("confidence", 0.7),
            recommended_actions=raw.get("actions", []),
        )

    def _derive_opportunities(self) -> List[MarketOpportunity]:
        """Derive opportunities from trends and niches."""
        opportunities = []

        # Rising trends with high strength = new product opportunities
        for trend in self._trends.values():
            if trend.direction == TrendDirection.RISING and trend.strength >= 0.7:
                opp = MarketOpportunity(
                    title=f"New Product: {trend.name}",
                    description=f"Opportunity to launch product in {trend.name} space",
                    opportunity_type=OpportunityType.NEW_PRODUCT,
                    source_trends=[trend.id],
                    time_to_market="moderate",
                    risk_level=RiskLevel.MEDIUM if trend.confidence >= 0.7 else RiskLevel.HIGH,
                    score=trend.strength * trend.confidence,
                    confidence=trend.confidence,
                    recommended_actions=[
                        "Validate market demand",
                        "Analyze competitor offerings",
                        "Develop MVP",
                    ],
                )
                opportunities.append(opp)

        # Niches with high opportunity = market expansion
        for niche in self._niches.values():
            if niche.opportunity_score >= 0.7:
                opp = MarketOpportunity(
                    title=f"Market Expansion: {niche.name}",
                    description=f"Opportunity to expand into {niche.name}",
                    opportunity_type=OpportunityType.MARKET_EXPANSION,
                    source_niches=[niche.id],
                    time_to_market="moderate" if niche.competition_level == "low" else "long",
                    risk_level=(
                        RiskLevel.LOW if niche.competition_level == "low" else RiskLevel.MEDIUM
                    ),
                    score=niche.opportunity_score,
                    recommended_actions=[
                        "Research target audience",
                        "Identify entry strategy",
                        "Assess required resources",
                    ],
                )
                opportunities.append(opp)

        return opportunities

    async def detect_competitive_signals(
        self,
        competitors: Optional[List[str]] = None,
    ) -> List[CompetitiveSignal]:
        """
        Detect competitive intelligence signals.

        Args:
            competitors: Optional list of competitors to monitor

        Returns:
            List of competitive signals
        """
        signals = []
        target_competitors = competitors or self._watched_competitors

        if self._trend_analyzer and target_competitors:
            try:
                raw_signals = await self._trend_analyzer.detect_signals(
                    competitors=target_competitors
                )

                for rs in raw_signals:
                    signal = CompetitiveSignal(
                        competitor=rs.get("competitor", ""),
                        signal_type=rs.get("type", ""),
                        description=rs.get("description", ""),
                        impact=rs.get("impact", "medium"),
                        urgency=rs.get("urgency", "medium"),
                        source=rs.get("source", ""),
                        recommended_response=rs.get("response"),
                    )
                    self._signals[signal.id] = signal
                    signals.append(signal)

            except Exception as e:
                logger.error(f"Signal detection failed: {e}")

        self._metrics["signals_detected"] = len(self._signals)
        return signals

    def get_trends_for_cpo(self) -> Dict[str, Any]:
        """
        Get trend data formatted for Blueprint product strategy.

        Returns:
            Data structured for Blueprint consumption
        """
        rising = [
            t.to_dict()
            for t in self._trends.values()
            if t.direction in [TrendDirection.RISING, TrendDirection.EMERGING]
        ]
        declining = [
            t.to_dict() for t in self._trends.values() if t.direction == TrendDirection.DECLINING
        ]

        return {
            "summary": {
                "total_trends": len(self._trends),
                "rising_trends": len(rising),
                "declining_trends": len(declining),
                "niches_identified": len(self._niches),
                "opportunities_found": len(self._opportunities),
            },
            "rising_trends": sorted(rising, key=lambda t: t["strength"], reverse=True)[:10],
            "declining_trends": sorted(declining, key=lambda t: t["strength"], reverse=True)[:5],
            "top_niches": [
                n.to_dict()
                for n in sorted(
                    self._niches.values(), key=lambda n: n.opportunity_score, reverse=True
                )[:5]
            ],
            "top_opportunities": [
                o.to_dict()
                for o in sorted(self._opportunities.values(), key=lambda o: o.score, reverse=True)[
                    :5
                ]
            ],
            "product_recommendations": self._generate_product_recommendations(),
            "last_scan": self._metrics.get("last_scan"),
        }

    def get_trends_for_cmo(self) -> Dict[str, Any]:
        """
        Get trend data formatted for Echo marketing strategy.

        Returns:
            Data structured for Echo consumption
        """
        return {
            "summary": {
                "total_trends": len(self._trends),
                "marketing_relevant": len(
                    [
                        t
                        for t in self._trends.values()
                        if t.category in [TrendCategory.CONSUMER_BEHAVIOR, TrendCategory.CHANNEL]
                    ]
                ),
            },
            "consumer_trends": [
                t.to_dict()
                for t in self._trends.values()
                if t.category == TrendCategory.CONSUMER_BEHAVIOR
            ],
            "channel_trends": [
                t.to_dict() for t in self._trends.values() if t.category == TrendCategory.CHANNEL
            ],
            "trending_keywords": self._get_trending_keywords(),
            "competitive_signals": [
                {
                    "competitor": s.competitor,
                    "type": s.signal_type,
                    "impact": s.impact,
                    "description": s.description,
                }
                for s in self._signals.values()
            ][:10],
            "campaign_opportunities": self._generate_campaign_opportunities(),
        }

    def _generate_product_recommendations(self) -> List[Dict[str, Any]]:
        """Generate product recommendations from trends."""
        recommendations = []

        for trend in sorted(self._trends.values(), key=lambda t: t.strength, reverse=True)[:5]:
            if trend.direction in [TrendDirection.RISING, TrendDirection.EMERGING]:
                recommendations.append(
                    {
                        "trend": trend.name,
                        "strength": trend.strength,
                        "recommendation": f"Consider developing products in {trend.name} space",
                        "keywords": trend.keywords[:5],
                    }
                )

        return recommendations

    def _get_trending_keywords(self) -> List[Dict[str, Any]]:
        """Get aggregated trending keywords."""
        keyword_scores: Dict[str, float] = {}

        for trend in self._trends.values():
            for kw in trend.keywords:
                if kw in keyword_scores:
                    keyword_scores[kw] = max(keyword_scores[kw], trend.strength)
                else:
                    keyword_scores[kw] = trend.strength

        return [
            {"keyword": kw, "score": score}
            for kw, score in sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)[:20]
        ]

    def _generate_campaign_opportunities(self) -> List[Dict[str, Any]]:
        """Generate marketing campaign opportunities."""
        campaigns = []

        for trend in self._trends.values():
            if trend.strength >= 0.6 and trend.direction == TrendDirection.RISING:
                campaigns.append(
                    {
                        "trend": trend.name,
                        "campaign_type": (
                            "awareness"
                            if trend.direction == TrendDirection.EMERGING
                            else "conversion"
                        ),
                        "target_keywords": trend.keywords[:5],
                        "recommended_channels": self._recommend_channels(trend),
                    }
                )

        return campaigns[:5]

    def _recommend_channels(self, trend: MarketTrend) -> List[str]:
        """Recommend marketing channels for a trend."""
        channels = ["social_media", "content_marketing"]

        if trend.category == TrendCategory.TECHNOLOGY:
            channels.extend(["tech_publications", "webinars"])
        elif trend.category == TrendCategory.CONSUMER_BEHAVIOR:
            channels.extend(["influencer_marketing", "video"])

        return channels

    @property
    def stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "cpo_connected": self._cpo is not None,
            "cro_connected": self._cro is not None,
            "cmo_connected": self._cmo is not None,
            "analyzer_connected": self._trend_analyzer is not None,
            "api_endpoint": self._api_endpoint,
            "watched_keywords": len(self._watched_keywords),
            "watched_competitors": len(self._watched_competitors),
            **self._metrics,
        }
