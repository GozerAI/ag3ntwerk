"""
Trend Collectors - Data collection from various sources.

Provides collectors for gathering trend data from external platforms
including Google Trends, Reddit, Hacker News, Product Hunt, and more.
"""

import asyncio
import json
import logging
import re
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ag3ntwerk.modules.trends.core import (
    Trend,
    TrendCategory,
    TrendSource,
    TrendStatus,
    TrendDatabase,
    NicheOpportunity,
)

logger = logging.getLogger(__name__)


class TrendCollector(ABC):
    """Base class for trend collectors."""

    def __init__(self, name: str, source: TrendSource):
        self.name = name
        self.source = source
        self.last_collection: Optional[datetime] = None
        self.collection_count = 0
        self.error_count = 0

    @abstractmethod
    async def collect(self) -> List[Trend]:
        """Collect trends from the source."""
        pass

    def _make_request(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request and return JSON response."""
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "AgentWerk-TrendCollector/1.0")
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)

            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")
            self.error_count += 1
            return None

    def _create_trend(
        self,
        name: str,
        description: str = "",
        score: float = 50.0,
        category: TrendCategory = TrendCategory.EMERGING,
        **kwargs,
    ) -> Trend:
        """Create a trend with common defaults."""
        return Trend(
            id=str(uuid4()),
            name=name,
            description=description,
            category=category,
            source=self.source,
            score=score,
            first_seen=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
            **kwargs,
        )


class GoogleTrendsCollector(TrendCollector):
    """Collector for Google Trends data."""

    def __init__(self):
        super().__init__("Google Trends", TrendSource.GOOGLE_TRENDS)
        # Note: In production, use pytrends or Google Trends API
        self.daily_trends_url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"

    async def collect(self) -> List[Trend]:
        """Collect trending searches from Google."""
        trends = []

        # Simulated data - in production, use actual API
        # This provides a framework for integration
        sample_trends = [
            {"name": "AI Agents", "score": 85, "category": TrendCategory.TECHNOLOGY},
            {"name": "Sustainable Fashion", "score": 72, "category": TrendCategory.LIFESTYLE},
            {"name": "Home Fitness", "score": 68, "category": TrendCategory.HEALTH},
        ]

        for t in sample_trends:
            trend = self._create_trend(
                name=t["name"],
                description=f"Trending on Google: {t['name']}",
                score=t["score"],
                category=t["category"],
                keywords=[t["name"].lower()],
            )
            trends.append(trend)

        self.last_collection = datetime.now(timezone.utc)
        self.collection_count += 1
        return trends


class RedditCollector(TrendCollector):
    """Collector for Reddit trends."""

    def __init__(self, subreddits: Optional[List[str]] = None):
        super().__init__("Reddit", TrendSource.REDDIT)
        self.subreddits = subreddits or [
            "technology",
            "gadgets",
            "startups",
            "entrepreneur",
            "ecommerce",
            "dropship",
            "smallbusiness",
        ]
        self.base_url = "https://www.reddit.com"

    async def collect(self) -> List[Trend]:
        """Collect trends from Reddit."""
        trends = []

        for subreddit in self.subreddits:
            url = f"{self.base_url}/r/{subreddit}/hot.json?limit=10"
            data = self._make_request(url)

            if not data:
                continue

            posts = data.get("data", {}).get("children", [])
            for post in posts[:5]:
                post_data = post.get("data", {})
                if post_data.get("stickied"):
                    continue

                score = min(100, post_data.get("score", 0) / 100)
                trend = self._create_trend(
                    name=post_data.get("title", "")[:100],
                    description=post_data.get("selftext", "")[:500],
                    score=score,
                    category=self._categorize_subreddit(subreddit),
                    keywords=self._extract_keywords(post_data.get("title", "")),
                    volume=post_data.get("num_comments", 0),
                    raw_data={
                        "subreddit": subreddit,
                        "url": post_data.get("url"),
                        "author": post_data.get("author"),
                        "upvote_ratio": post_data.get("upvote_ratio"),
                    },
                )
                trends.append(trend)

        self.last_collection = datetime.now(timezone.utc)
        self.collection_count += 1
        return trends

    def _categorize_subreddit(self, subreddit: str) -> TrendCategory:
        """Map subreddit to trend category."""
        mapping = {
            "technology": TrendCategory.TECHNOLOGY,
            "gadgets": TrendCategory.TECHNOLOGY,
            "startups": TrendCategory.BUSINESS,
            "entrepreneur": TrendCategory.BUSINESS,
            "ecommerce": TrendCategory.ECOMMERCE,
            "dropship": TrendCategory.ECOMMERCE,
            "smallbusiness": TrendCategory.BUSINESS,
        }
        return mapping.get(subreddit.lower(), TrendCategory.EMERGING)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        stopwords = {"this", "that", "with", "from", "have", "been", "were", "they"}
        return list(set(words) - stopwords)[:10]


class HackerNewsCollector(TrendCollector):
    """Collector for Hacker News trends."""

    def __init__(self):
        super().__init__("Hacker News", TrendSource.HACKER_NEWS)
        self.base_url = "https://hacker-news.firebaseio.com/v0"

    async def collect(self) -> List[Trend]:
        """Collect trends from Hacker News."""
        trends = []

        # Get top stories
        top_stories = self._make_request(f"{self.base_url}/topstories.json")
        if not top_stories:
            return trends

        for story_id in top_stories[:15]:
            story = self._make_request(f"{self.base_url}/item/{story_id}.json")
            if not story:
                continue

            score = min(100, story.get("score", 0) / 10)
            trend = self._create_trend(
                name=story.get("title", "")[:100],
                description=f"HN discussion with {story.get('descendants', 0)} comments",
                score=score,
                category=TrendCategory.TECHNOLOGY,
                keywords=self._extract_keywords(story.get("title", "")),
                volume=story.get("descendants", 0),
                raw_data={
                    "hn_id": story_id,
                    "url": story.get("url"),
                    "author": story.get("by"),
                    "type": story.get("type"),
                },
            )
            trends.append(trend)

        self.last_collection = datetime.now(timezone.utc)
        self.collection_count += 1
        return trends

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from title."""
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        tech_terms = {
            "python",
            "javascript",
            "rust",
            "golang",
            "kubernetes",
            "docker",
            "machine",
            "learning",
            "startup",
            "cloud",
            "data",
            "open",
            "source",
        }
        keywords = [w for w in words if w in tech_terms or len(w) > 5]
        return list(set(keywords))[:10]


class ProductHuntCollector(TrendCollector):
    """Collector for Product Hunt trends."""

    def __init__(self):
        super().__init__("Product Hunt", TrendSource.PRODUCT_HUNT)
        # Note: Requires API key in production
        self.api_url = "https://api.producthunt.com/v2/api/graphql"

    async def collect(self) -> List[Trend]:
        """Collect trends from Product Hunt."""
        # In production, use GraphQL API with proper authentication
        # This provides framework for integration
        trends = []

        # Simulated trending products
        sample_products = [
            {"name": "AI Writing Assistant", "tagline": "Write better with AI", "votes": 450},
            {"name": "E-commerce Analytics", "tagline": "Understand your sales", "votes": 320},
            {"name": "Remote Team Tools", "tagline": "Collaborate from anywhere", "votes": 280},
        ]

        for p in sample_products:
            score = min(100, p["votes"] / 5)
            trend = self._create_trend(
                name=p["name"],
                description=p["tagline"],
                score=score,
                category=TrendCategory.TECHNOLOGY,
                keywords=[w.lower() for w in p["name"].split()],
                volume=p["votes"],
            )
            trends.append(trend)

        self.last_collection = datetime.now(timezone.utc)
        self.collection_count += 1
        return trends


class NicheIdentifier:
    """Identifies niche market opportunities from trend data."""

    def __init__(self, db: TrendDatabase):
        self.db = db

        # Niche storefront mapping
        self.storefronts = {
            "tech_gadgets": ["technology", "gadgets", "electronics"],
            "home_wellness": ["health", "lifestyle", "home"],
            "fashion_accessories": ["fashion", "lifestyle", "accessories"],
            "pet_supplies": ["pets", "animals", "lifestyle"],
            "outdoor_adventure": ["outdoor", "sports", "adventure"],
            "sustainable_living": ["eco", "sustainable", "green"],
            "creative_tools": ["art", "creative", "design"],
            "productivity": ["productivity", "work", "business"],
        }

    def identify_niches(
        self,
        trends: List[Trend],
        min_confidence: float = 0.5,
    ) -> List[NicheOpportunity]:
        """Identify niche opportunities from trends."""
        niches = []

        # Group trends by keywords
        keyword_groups: Dict[str, List[Trend]] = {}
        for trend in trends:
            for keyword in trend.keywords:
                if keyword not in keyword_groups:
                    keyword_groups[keyword] = []
                keyword_groups[keyword].append(trend)

        # Find keyword clusters with high scores
        for keyword, group_trends in keyword_groups.items():
            if len(group_trends) < 2:
                continue

            avg_score = sum(t.score for t in group_trends) / len(group_trends)
            avg_velocity = sum(t.velocity for t in group_trends) / len(group_trends)

            if avg_score < 50:
                continue

            # Calculate opportunity metrics
            opportunity_score = (avg_score + (avg_velocity * 50)) / 2
            confidence = min(1.0, len(group_trends) / 5)

            if confidence < min_confidence:
                continue

            # Determine storefront fit
            storefront_fit = []
            for sf, sf_keywords in self.storefronts.items():
                if keyword in sf_keywords or any(kw in keyword for kw in sf_keywords):
                    storefront_fit.append(sf)

            niche = NicheOpportunity(
                name=f"{keyword.title()} Market",
                description=f"Emerging opportunity in {keyword} space based on {len(group_trends)} related trends",
                parent_trend_ids=[t.id for t in group_trends],
                opportunity_score=opportunity_score,
                confidence=confidence,
                growth_rate=avg_velocity * 100,
                competition_density=sum(t.competition_level for t in group_trends)
                / len(group_trends),
                product_ideas=self._generate_product_ideas(keyword, group_trends),
                target_audience=self._identify_target_audience(group_trends),
                pain_points=self._extract_pain_points(group_trends),
                storefront_fit=storefront_fit,
                product_categories=[keyword],
                recommended_action=self._recommend_action(opportunity_score, avg_velocity),
                urgency=self._calculate_urgency(avg_velocity, opportunity_score),
            )
            niches.append(niche)

        # Sort by opportunity score
        niches.sort(key=lambda n: n.opportunity_score, reverse=True)
        return niches[:20]

    def _generate_product_ideas(self, keyword: str, trends: List[Trend]) -> List[str]:
        """Generate product ideas based on trend data."""
        ideas = []

        # Extract common themes
        all_keywords = []
        for t in trends:
            all_keywords.extend(t.keywords)

        top_keywords = sorted(set(all_keywords), key=all_keywords.count, reverse=True)[:5]

        for kw in top_keywords:
            ideas.append(f"{kw.title()}-focused {keyword} products")

        return ideas[:5]

    def _identify_target_audience(self, trends: List[Trend]) -> str:
        """Identify target audience from trends."""
        categories = [t.category.value for t in trends]
        primary_category = max(set(categories), key=categories.count)

        audience_map = {
            "technology": "Tech enthusiasts and early adopters",
            "ecommerce": "Online shoppers and digital natives",
            "lifestyle": "Lifestyle-conscious consumers",
            "health": "Health and wellness seekers",
            "business": "Entrepreneurs and business professionals",
        }

        return audience_map.get(primary_category, "General consumers")

    def _extract_pain_points(self, trends: List[Trend]) -> List[str]:
        """Extract potential pain points from trend descriptions."""
        pain_points = []

        for trend in trends:
            desc = trend.description.lower()
            if "problem" in desc or "issue" in desc or "need" in desc:
                pain_points.append(f"Addressing {trend.name[:50]} needs")

        return pain_points[:5] or ["Market gap to be explored"]

    def _recommend_action(self, opportunity_score: float, velocity: float) -> str:
        """Recommend action based on metrics."""
        if opportunity_score >= 75 and velocity > 0.3:
            return "IMMEDIATE: High opportunity with strong momentum - act now"
        elif opportunity_score >= 60:
            return "PRIORITIZE: Good opportunity - begin research and planning"
        elif opportunity_score >= 40:
            return "MONITOR: Moderate opportunity - track development"
        else:
            return "OBSERVE: Low priority - keep on watchlist"

    def _calculate_urgency(self, velocity: float, opportunity_score: float) -> str:
        """Calculate urgency level."""
        if velocity > 0.5 and opportunity_score > 70:
            return "critical"
        elif velocity > 0.3 or opportunity_score > 60:
            return "high"
        elif velocity > 0 or opportunity_score > 40:
            return "medium"
        else:
            return "low"


class TrendCollectorManager:
    """Manages multiple trend collectors."""

    def __init__(self, db: Optional[TrendDatabase] = None):
        self.db = db or TrendDatabase()
        self.collectors: Dict[str, TrendCollector] = {}
        self.niche_identifier = NicheIdentifier(self.db)

    def add_collector(self, collector: TrendCollector) -> None:
        """Add a collector."""
        self.collectors[collector.name] = collector
        logger.info(f"Added collector: {collector.name}")

    def add_default_collectors(self) -> None:
        """Add all default collectors."""
        self.add_collector(GoogleTrendsCollector())
        self.add_collector(RedditCollector())
        self.add_collector(HackerNewsCollector())
        self.add_collector(ProductHuntCollector())

    async def collect_all(self, save: bool = True) -> List[Trend]:
        """Collect from all sources."""
        all_trends = []

        for name, collector in self.collectors.items():
            try:
                logger.info(f"Collecting from {name}...")
                trends = await collector.collect()
                all_trends.extend(trends)
                logger.info(f"Collected {len(trends)} trends from {name}")
            except Exception as e:
                logger.error(f"Collection failed for {name}: {e}")

        if save:
            for trend in all_trends:
                self.db.save_trend(trend)

        return all_trends

    async def collect_from(self, source_name: str, save: bool = True) -> List[Trend]:
        """Collect from a specific source."""
        collector = self.collectors.get(source_name)
        if not collector:
            raise ValueError(f"Unknown collector: {source_name}")

        trends = await collector.collect()

        if save:
            for trend in trends:
                self.db.save_trend(trend)

        return trends

    def identify_niches(self, min_confidence: float = 0.5) -> List[NicheOpportunity]:
        """Identify niche opportunities from collected trends."""
        trends = self.db.get_trends(limit=200)
        niches = self.niche_identifier.identify_niches(trends, min_confidence)

        # Save niches
        for niche in niches:
            self.db.save_niche(niche)

        return niches

    def get_collector_stats(self) -> Dict[str, Any]:
        """Get statistics for all collectors."""
        stats = {}
        for name, collector in self.collectors.items():
            stats[name] = {
                "source": collector.source.value,
                "last_collection": (
                    collector.last_collection.isoformat() if collector.last_collection else None
                ),
                "collection_count": collector.collection_count,
                "error_count": collector.error_count,
            }
        return stats
