"""
Research Integrations for ag3ntwerk.

This package provides integrations for information gathering:
- Web Scraping: Playwright-based browser automation
- News/RSS: News and feed aggregation
- Papers: Academic paper retrieval
"""

from ag3ntwerk.integrations.research.scraping import (
    ScrapingIntegration,
    ScrapingConfig,
    PageContent,
)
from ag3ntwerk.integrations.research.news import (
    NewsIntegration,
    NewsConfig,
    NewsArticle,
    RSSFeed,
)
from ag3ntwerk.integrations.research.papers import (
    PapersIntegration,
    Paper,
    PaperSource,
)

__all__ = [
    "ScrapingIntegration",
    "ScrapingConfig",
    "PageContent",
    "NewsIntegration",
    "NewsConfig",
    "NewsArticle",
    "RSSFeed",
    "PapersIntegration",
    "Paper",
    "PaperSource",
]
