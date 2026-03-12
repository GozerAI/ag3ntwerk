"""
Research Papers Integration for ag3ntwerk.

Provides access to academic papers and preprints.

Requirements:
    - pip install arxiv semanticscholar

Papers is ideal for:
    - R&D research
    - Technology trends
    - Competitive intelligence
    - Due diligence
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class PaperSource(str, Enum):
    """Paper sources."""

    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"


@dataclass
class Author:
    """Represents a paper author."""

    name: str
    affiliation: str = ""
    author_id: str = ""


@dataclass
class Paper:
    """Represents an academic paper."""

    title: str
    abstract: str = ""
    authors: List[Author] = field(default_factory=list)
    source: PaperSource = PaperSource.ARXIV
    paper_id: str = ""
    url: str = ""
    pdf_url: str = ""
    published_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    categories: List[str] = field(default_factory=list)
    citation_count: int = 0
    doi: str = ""
    venue: str = ""
    year: int = 0


class PapersIntegration:
    """
    Integration for academic paper retrieval.

    Supports arXiv and Semantic Scholar.

    Example:
        papers = PapersIntegration()

        # Search arXiv
        results = await papers.search_arxiv("transformer neural networks")

        # Get paper details
        paper = await papers.get_paper("2106.09685")

        # Get citations
        citations = await papers.get_citations(paper.paper_id)
    """

    def __init__(self):
        """Initialize papers integration."""
        self._arxiv = None
        self._semantic_scholar = None

    async def search_arxiv(
        self,
        query: str,
        max_results: int = 20,
        sort_by: str = "relevance",  # relevance, lastUpdatedDate, submittedDate
        categories: Optional[List[str]] = None,
    ) -> List[Paper]:
        """
        Search arXiv for papers.

        Args:
            query: Search query
            max_results: Maximum results
            sort_by: Sort order
            categories: Filter by categories (e.g., ["cs.AI", "cs.LG"])

        Returns:
            List of Papers
        """
        try:
            import arxiv
        except ImportError:
            raise ImportError("arxiv not installed. Install with: pip install arxiv")

        loop = asyncio.get_running_loop()

        def _search():
            # Build search query
            search_query = query
            if categories:
                cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
                search_query = f"({query}) AND ({cat_query})"

            sort_map = {
                "relevance": arxiv.SortCriterion.Relevance,
                "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
                "submittedDate": arxiv.SortCriterion.SubmittedDate,
            }

            search = arxiv.Search(
                query=search_query,
                max_results=max_results,
                sort_by=sort_map.get(sort_by, arxiv.SortCriterion.Relevance),
            )

            papers = []
            for result in search.results():
                papers.append(
                    Paper(
                        title=result.title,
                        abstract=result.summary,
                        authors=[Author(name=a.name) for a in result.authors],
                        source=PaperSource.ARXIV,
                        paper_id=result.entry_id.split("/")[-1],
                        url=result.entry_id,
                        pdf_url=result.pdf_url,
                        published_date=result.published,
                        updated_date=result.updated,
                        categories=result.categories,
                        doi=result.doi or "",
                    )
                )

            return papers

        return await loop.run_in_executor(None, _search)

    async def get_arxiv_paper(self, paper_id: str) -> Optional[Paper]:
        """
        Get a specific arXiv paper by ID.

        Args:
            paper_id: arXiv paper ID (e.g., "2106.09685")

        Returns:
            Paper or None
        """
        try:
            import arxiv
        except ImportError:
            raise ImportError("arxiv not installed. Install with: pip install arxiv")

        loop = asyncio.get_running_loop()

        def _get():
            search = arxiv.Search(id_list=[paper_id])
            results = list(search.results())

            if not results:
                return None

            result = results[0]
            return Paper(
                title=result.title,
                abstract=result.summary,
                authors=[Author(name=a.name) for a in result.authors],
                source=PaperSource.ARXIV,
                paper_id=paper_id,
                url=result.entry_id,
                pdf_url=result.pdf_url,
                published_date=result.published,
                updated_date=result.updated,
                categories=result.categories,
                doi=result.doi or "",
            )

        return await loop.run_in_executor(None, _get)

    async def search_semantic_scholar(
        self,
        query: str,
        limit: int = 20,
        year: Optional[int] = None,
        fields_of_study: Optional[List[str]] = None,
    ) -> List[Paper]:
        """
        Search Semantic Scholar for papers.

        Args:
            query: Search query
            limit: Maximum results
            year: Filter by year
            fields_of_study: Filter by fields

        Returns:
            List of Papers
        """
        try:
            from semanticscholar import SemanticScholar
        except ImportError:
            raise ImportError(
                "semanticscholar not installed. Install with: pip install semanticscholar"
            )

        loop = asyncio.get_running_loop()

        def _search():
            sch = SemanticScholar()

            results = sch.search_paper(
                query,
                limit=limit,
                year=str(year) if year else None,
                fields_of_study=fields_of_study,
            )

            papers = []
            for result in results:
                papers.append(
                    Paper(
                        title=result.title or "",
                        abstract=result.abstract or "",
                        authors=[
                            Author(
                                name=a.name,
                                author_id=a.authorId or "",
                            )
                            for a in (result.authors or [])
                        ],
                        source=PaperSource.SEMANTIC_SCHOLAR,
                        paper_id=result.paperId or "",
                        url=result.url or "",
                        citation_count=result.citationCount or 0,
                        venue=result.venue or "",
                        year=result.year or 0,
                    )
                )

            return papers

        return await loop.run_in_executor(None, _search)

    async def get_semantic_scholar_paper(self, paper_id: str) -> Optional[Paper]:
        """
        Get a paper from Semantic Scholar by ID.

        Args:
            paper_id: Semantic Scholar paper ID or DOI

        Returns:
            Paper or None
        """
        try:
            from semanticscholar import SemanticScholar
        except ImportError:
            raise ImportError(
                "semanticscholar not installed. Install with: pip install semanticscholar"
            )

        loop = asyncio.get_running_loop()

        def _get():
            sch = SemanticScholar()

            try:
                result = sch.get_paper(paper_id)
            except Exception as e:
                logger.debug("SemanticScholar get_paper failed for %s: %s", paper_id, e)
                return None

            if not result:
                return None

            return Paper(
                title=result.title or "",
                abstract=result.abstract or "",
                authors=[
                    Author(
                        name=a.name,
                        author_id=a.authorId or "",
                    )
                    for a in (result.authors or [])
                ],
                source=PaperSource.SEMANTIC_SCHOLAR,
                paper_id=result.paperId or "",
                url=result.url or "",
                citation_count=result.citationCount or 0,
                venue=result.venue or "",
                year=result.year or 0,
            )

        return await loop.run_in_executor(None, _get)

    async def get_citations(
        self,
        paper_id: str,
        source: PaperSource = PaperSource.SEMANTIC_SCHOLAR,
        limit: int = 50,
    ) -> List[Paper]:
        """
        Get papers that cite a given paper.

        Args:
            paper_id: Paper ID
            source: Paper source
            limit: Maximum citations

        Returns:
            List of citing Papers
        """
        try:
            from semanticscholar import SemanticScholar
        except ImportError:
            raise ImportError(
                "semanticscholar not installed. Install with: pip install semanticscholar"
            )

        loop = asyncio.get_running_loop()

        def _get():
            sch = SemanticScholar()

            try:
                result = sch.get_paper(paper_id)
                citations = result.citations[:limit] if result.citations else []
            except Exception as e:
                logger.debug("SemanticScholar get_citations failed for %s: %s", paper_id, e)
                return []

            papers = []
            for cit in citations:
                if cit:
                    papers.append(
                        Paper(
                            title=cit.title or "",
                            source=PaperSource.SEMANTIC_SCHOLAR,
                            paper_id=cit.paperId or "",
                            citation_count=cit.citationCount or 0,
                            year=cit.year or 0,
                        )
                    )

            return papers

        return await loop.run_in_executor(None, _get)

    async def get_references(
        self,
        paper_id: str,
        limit: int = 50,
    ) -> List[Paper]:
        """
        Get papers referenced by a given paper.

        Args:
            paper_id: Paper ID
            limit: Maximum references

        Returns:
            List of referenced Papers
        """
        try:
            from semanticscholar import SemanticScholar
        except ImportError:
            raise ImportError(
                "semanticscholar not installed. Install with: pip install semanticscholar"
            )

        loop = asyncio.get_running_loop()

        def _get():
            sch = SemanticScholar()

            try:
                result = sch.get_paper(paper_id)
                references = result.references[:limit] if result.references else []
            except Exception as e:
                logger.debug("SemanticScholar get_references failed for %s: %s", paper_id, e)
                return []

            papers = []
            for ref in references:
                if ref:
                    papers.append(
                        Paper(
                            title=ref.title or "",
                            source=PaperSource.SEMANTIC_SCHOLAR,
                            paper_id=ref.paperId or "",
                            citation_count=ref.citationCount or 0,
                            year=ref.year or 0,
                        )
                    )

            return papers

        return await loop.run_in_executor(None, _get)

    async def download_pdf(
        self,
        paper: Paper,
        output_path: str,
    ) -> Optional[str]:
        """
        Download paper PDF.

        Args:
            paper: Paper to download
            output_path: Output file path

        Returns:
            Downloaded file path or None
        """
        if not paper.pdf_url:
            return None

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(paper.pdf_url) as response:
                    if response.status == 200:
                        with open(output_path, "wb") as f:
                            f.write(await response.read())
                        return output_path

        except Exception as e:
            logger.error(f"Failed to download PDF: {e}")

        return None

    async def get_trending_papers(
        self,
        field: str = "cs.AI",
        days: int = 7,
        limit: int = 20,
    ) -> List[Paper]:
        """
        Get trending papers in a field.

        Args:
            field: arXiv category
            days: Look back period
            limit: Maximum results

        Returns:
            List of trending Papers
        """
        from datetime import timedelta

        # Search recent papers sorted by relevance
        papers = await self.search_arxiv(
            query=f"cat:{field}",
            max_results=limit * 2,
            sort_by="submittedDate",
            categories=[field],
        )

        # Filter to recent papers
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            p for p in papers if p.published_date and p.published_date.replace(tzinfo=None) > cutoff
        ]

        return recent[:limit]
