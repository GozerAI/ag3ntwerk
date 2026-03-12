"""
Research Tool Definitions.

Tools for Web Scraping, News, and Academic Papers.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.tools.base import (
    BaseTool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ParameterType,
)


class WebScrapeTool(BaseTool):
    """Scrape content from web pages."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="web_scrape",
            description="Scrape content from a web page",
            category=ToolCategory.RESEARCH,
            tags=["scrape", "web", "extract", "crawl"],
            examples=[
                "Scrape the pricing page",
                "Extract data from the website",
                "Get content from URL",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="url",
                description="URL to scrape",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="selector",
                description="CSS selector for specific content",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="wait_for",
                description="Wait for element (CSS selector)",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="screenshot",
                description="Take a screenshot",
                param_type=ParameterType.BOOLEAN,
                required=False,
                default=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        url = kwargs.get("url")
        selector = kwargs.get("selector")
        wait_for = kwargs.get("wait_for")
        screenshot = kwargs.get("screenshot", False)

        try:
            from ag3ntwerk.integrations.research.scraping import ScrapingIntegration

            scraper = ScrapingIntegration()

            result = await scraper.scrape(
                url=url,
                selector=selector,
                wait_for=wait_for,
                screenshot=screenshot,
            )

            return ToolResult(
                success=True,
                data={
                    "title": result.title,
                    "content": result.content,
                    "html": result.html[:1000] if result.html else None,
                    "screenshot_path": result.screenshot_path,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class SearchNewsTool(BaseTool):
    """Search for news articles."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="search_news",
            description="Search for news articles on a topic",
            category=ToolCategory.RESEARCH,
            tags=["news", "search", "articles", "current events"],
            examples=[
                "Find news about AI",
                "Get latest tech news",
                "Search for market updates",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                description="Search query",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="sources",
                description="News sources to search",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="limit",
                description="Maximum number of results",
                param_type=ParameterType.INTEGER,
                required=False,
                default=10,
            ),
            ToolParameter(
                name="language",
                description="Language code (e.g., 'en')",
                param_type=ParameterType.STRING,
                required=False,
                default="en",
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        sources = kwargs.get("sources")
        limit = kwargs.get("limit", 10)
        language = kwargs.get("language", "en")

        try:
            from ag3ntwerk.integrations.research.news import NewsIntegration

            news = NewsIntegration()

            articles = await news.search(
                query=query,
                sources=sources,
                limit=limit,
                language=language,
            )

            return ToolResult(
                success=True,
                data={
                    "articles": [
                        {
                            "title": a.title,
                            "source": a.source,
                            "url": a.url,
                            "published": a.published_at.isoformat() if a.published_at else None,
                            "summary": a.description,
                        }
                        for a in articles
                    ],
                    "count": len(articles),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class SearchPapersTool(BaseTool):
    """Search for academic papers."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="search_papers",
            description="Search for academic papers and research",
            category=ToolCategory.RESEARCH,
            tags=["papers", "research", "academic", "arxiv"],
            examples=[
                "Find papers on machine learning",
                "Search for research on quantum computing",
                "Get academic papers about NLP",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                description="Search query",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="source",
                description="Paper source (arxiv, semantic_scholar)",
                param_type=ParameterType.STRING,
                required=False,
                default="arxiv",
            ),
            ToolParameter(
                name="limit",
                description="Maximum number of results",
                param_type=ParameterType.INTEGER,
                required=False,
                default=10,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        source = kwargs.get("source", "arxiv")
        limit = kwargs.get("limit", 10)

        try:
            from ag3ntwerk.integrations.research.papers import PapersIntegration

            papers = PapersIntegration()

            results = await papers.search(
                query=query,
                source=source,
                limit=limit,
            )

            return ToolResult(
                success=True,
                data={
                    "papers": [
                        {
                            "title": p.title,
                            "authors": p.authors,
                            "abstract": p.abstract[:500] if p.abstract else None,
                            "url": p.url,
                            "published": p.published_at.isoformat() if p.published_at else None,
                        }
                        for p in results
                    ],
                    "count": len(results),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )
