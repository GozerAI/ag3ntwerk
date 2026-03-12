"""
News and RSS Integration for ag3ntwerk.

Provides news aggregation and RSS feed parsing.

Requirements:
    - pip install feedparser aiohttp

News is ideal for:
    - Industry monitoring
    - Competitive intelligence
    - Market trends
    - Agent briefings
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class NewsConfig:
    """Configuration for news integration."""

    user_agent: str = "ag3ntwerk News Bot/1.0"
    timeout: int = 30
    max_articles: int = 50


@dataclass
class NewsArticle:
    """Represents a news article."""

    title: str
    url: str
    source: str = ""
    description: str = ""
    content: str = ""
    author: str = ""
    published_at: Optional[datetime] = None
    image_url: str = ""
    categories: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


@dataclass
class RSSFeed:
    """Represents an RSS feed."""

    url: str
    title: str = ""
    description: str = ""
    link: str = ""
    language: str = ""
    last_updated: Optional[datetime] = None
    articles: List[NewsArticle] = field(default_factory=list)


class NewsIntegration:
    """
    Integration for news and RSS feeds.

    Example:
        news = NewsIntegration()

        # Parse RSS feed
        feed = await news.parse_feed("https://news.ycombinator.com/rss")

        # Search news (requires API key for some providers)
        articles = await news.search_news("artificial intelligence")

        # Get tech news
        tech_news = await news.get_tech_news()
    """

    def __init__(self, config: Optional[NewsConfig] = None):
        """Initialize news integration."""
        self.config = config or NewsConfig()
        self._session = None

    async def _get_session(self):
        """Get aiohttp session."""
        if self._session is None:
            try:
                import aiohttp

                self._session = aiohttp.ClientSession(
                    headers={"User-Agent": self.config.user_agent},
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                )
            except ImportError:
                raise ImportError("aiohttp not installed. Install with: pip install aiohttp")
        return self._session

    async def parse_feed(self, url: str) -> RSSFeed:
        """
        Parse an RSS/Atom feed.

        Args:
            url: Feed URL

        Returns:
            RSSFeed with articles
        """
        try:
            import feedparser
        except ImportError:
            raise ImportError("feedparser not installed. Install with: pip install feedparser")

        session = await self._get_session()

        async with session.get(url) as response:
            content = await response.text()

        feed = feedparser.parse(content)

        articles = []
        for entry in feed.entries[: self.config.max_articles]:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6])
                except Exception as e:
                    logger.debug("Failed to parse feed entry date: %s", e)

            articles.append(
                NewsArticle(
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    source=feed.feed.get("title", ""),
                    description=entry.get("summary", ""),
                    content=(
                        entry.get("content", [{}])[0].get("value", "")
                        if entry.get("content")
                        else ""
                    ),
                    author=entry.get("author", ""),
                    published_at=published,
                    categories=[tag.get("term", "") for tag in entry.get("tags", [])],
                )
            )

        return RSSFeed(
            url=url,
            title=feed.feed.get("title", ""),
            description=feed.feed.get("description", ""),
            link=feed.feed.get("link", ""),
            language=feed.feed.get("language", ""),
            articles=articles,
        )

    async def parse_multiple_feeds(self, urls: List[str]) -> List[RSSFeed]:
        """Parse multiple feeds concurrently."""
        tasks = [self.parse_feed(url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def aggregate_feeds(
        self,
        urls: List[str],
        sort_by_date: bool = True,
    ) -> List[NewsArticle]:
        """
        Aggregate articles from multiple feeds.

        Args:
            urls: List of feed URLs
            sort_by_date: Sort by publication date

        Returns:
            Combined list of articles
        """
        feeds = await self.parse_multiple_feeds(urls)

        articles = []
        for feed in feeds:
            if isinstance(feed, RSSFeed):
                articles.extend(feed.articles)

        if sort_by_date:
            articles.sort(
                key=lambda a: a.published_at or datetime.min,
                reverse=True,
            )

        return articles[: self.config.max_articles]

    async def get_tech_news(self) -> List[NewsArticle]:
        """Get aggregated tech news."""
        tech_feeds = [
            "https://news.ycombinator.com/rss",
            "https://www.techmeme.com/feed.xml",
            "https://feeds.arstechnica.com/arstechnica/technology-lab",
            "https://www.theverge.com/rss/index.xml",
        ]
        return await self.aggregate_feeds(tech_feeds)

    async def get_business_news(self) -> List[NewsArticle]:
        """Get aggregated business news."""
        business_feeds = [
            "https://feeds.bloomberg.com/markets/news.rss",
            "https://www.ft.com/?format=rss",
            "https://feeds.reuters.com/reuters/businessNews",
        ]
        return await self.aggregate_feeds(business_feeds)

    async def search_news(
        self,
        query: str,
        language: str = "en",
        from_date: Optional[datetime] = None,
    ) -> List[NewsArticle]:
        """
        Search news articles.

        Note: This is a simplified implementation. For production use,
        consider using NewsAPI, GDELT, or similar services.

        Args:
            query: Search query
            language: Language code
            from_date: Search from date

        Returns:
            List of matching articles
        """
        # For a basic implementation, search through RSS feeds
        # Real implementation would use a news API
        all_articles = []

        tech_news = await self.get_tech_news()
        business_news = await self.get_business_news()

        all_articles.extend(tech_news)
        all_articles.extend(business_news)

        query_lower = query.lower()
        filtered = [
            a
            for a in all_articles
            if query_lower in a.title.lower() or query_lower in a.description.lower()
        ]

        if from_date:
            filtered = [a for a in filtered if a.published_at and a.published_at >= from_date]

        return filtered

    async def close(self):
        """Close session."""
        if self._session:
            await self._session.close()
            self._session = None
