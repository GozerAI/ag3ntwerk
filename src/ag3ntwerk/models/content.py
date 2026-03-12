"""
Shared content models for ag3ntwerk.

Used by:
- Echo (Echo) for content marketing and distribution
- Voice integration for transcripts and expertise extraction
- Content orchestrator bridge for cross-agent workflows
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ContentFormat(str, Enum):
    """Output format for generated content."""

    ARTICLE = "article"
    BLOG_POST = "blog_post"
    EBOOK = "ebook"
    SOCIAL_POST = "social_post"
    NEWSLETTER = "newsletter"
    WHITEPAPER = "whitepaper"
    VIDEO_SCRIPT = "video_script"
    PODCAST_NOTES = "podcast_notes"


class ContentPiece(BaseModel):
    """
    A piece of content produced by the content pipeline.

    Represents any generated content (articles, ebooks, social posts)
    that can be distributed through social platforms or marketplaces.
    """

    id: str
    title: str
    body: str
    format: ContentFormat = ContentFormat.ARTICLE

    # Metadata
    author: str = ""
    tags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    summary: str = ""

    # Source tracking
    source_transcript_id: Optional[str] = None
    source_interview_id: Optional[str] = None

    # Distribution
    published_platforms: List[str] = Field(default_factory=list)
    marketplace_product_id: Optional[str] = None

    created_at: datetime = Field(default_factory=_utcnow)
    metadata: Dict[str, str] = Field(default_factory=dict)


class VoiceTranscript(BaseModel):
    """
    Transcript from voice capture.

    Wraps transcription output with metadata for the expertise
    extraction pipeline.
    """

    id: str
    audio_file: str
    full_text: str
    duration_seconds: float
    language: str = "en"

    # Segments
    segments: List[Dict[str, float | str]] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=_utcnow)


class ExpertiseInsight(BaseModel):
    """
    Extracted insight from a voice transcript or interview.

    Produced by the ExpertiseExtractor after analyzing transcripts
    for unique perspectives, frameworks, and actionable advice.
    """

    topic: str
    insight: str
    quote: str  # Direct quote, under 20 words
    tags: List[str] = Field(default_factory=list)

    source_transcript_id: Optional[str] = None
