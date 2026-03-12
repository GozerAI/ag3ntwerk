"""
Brand Suite Core - Data models and identity structures.

Provides foundational data structures for brand management
including identity, guidelines, and assets.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class BrandAssetType(Enum):
    """Types of brand assets."""

    LOGO = "logo"
    LOGO_VARIANT = "logo_variant"
    ICON = "icon"
    FAVICON = "favicon"
    WORDMARK = "wordmark"
    COLOR_PALETTE = "color_palette"
    TYPOGRAPHY = "typography"
    PATTERN = "pattern"
    ILLUSTRATION = "illustration"
    PHOTOGRAPHY = "photography"
    VIDEO = "video"
    AUDIO = "audio"
    TEMPLATE = "template"
    DOCUMENT = "document"


class BrandTone(Enum):
    """Brand voice tones."""

    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    AUTHORITATIVE = "authoritative"
    PLAYFUL = "playful"
    INSPIRATIONAL = "inspirational"
    EDUCATIONAL = "educational"
    CONVERSATIONAL = "conversational"
    FORMAL = "formal"
    CASUAL = "casual"
    BOLD = "bold"
    EMPATHETIC = "empathetic"


class BrandVoice(Enum):
    """Brand voice characteristics."""

    CONFIDENT = "confident"
    APPROACHABLE = "approachable"
    INNOVATIVE = "innovative"
    TRUSTWORTHY = "trustworthy"
    PASSIONATE = "passionate"
    EXPERT = "expert"
    HELPFUL = "helpful"
    AUTHENTIC = "authentic"


class ContentType(Enum):
    """Types of content for brand application."""

    SOCIAL_MEDIA = "social_media"
    EMAIL = "email"
    WEBSITE = "website"
    BLOG = "blog"
    ADVERTISING = "advertising"
    PACKAGING = "packaging"
    PRESENTATION = "presentation"
    DOCUMENTATION = "documentation"
    VIDEO = "video"
    PRINT = "print"


@dataclass
class ColorValue:
    """Color representation."""

    name: str = ""
    hex: str = ""
    rgb: Optional[tuple] = None
    cmyk: Optional[tuple] = None
    pantone: Optional[str] = None
    usage: str = ""  # primary, secondary, accent, background, text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "hex": self.hex,
            "rgb": self.rgb,
            "cmyk": self.cmyk,
            "pantone": self.pantone,
            "usage": self.usage,
        }


@dataclass
class ColorPalette:
    """Brand color palette."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "Primary Palette"
    primary: ColorValue = field(default_factory=ColorValue)
    secondary: List[ColorValue] = field(default_factory=list)
    accent: List[ColorValue] = field(default_factory=list)
    neutral: List[ColorValue] = field(default_factory=list)
    background: List[ColorValue] = field(default_factory=list)

    # Usage guidelines
    contrast_requirements: Dict[str, str] = field(default_factory=dict)
    forbidden_combinations: List[tuple] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "primary": self.primary.to_dict(),
            "secondary": [c.to_dict() for c in self.secondary],
            "accent": [c.to_dict() for c in self.accent],
            "neutral": [c.to_dict() for c in self.neutral],
            "background": [c.to_dict() for c in self.background],
        }

    def get_all_colors(self) -> List[ColorValue]:
        """Get all colors in the palette."""
        colors = [self.primary]
        colors.extend(self.secondary)
        colors.extend(self.accent)
        colors.extend(self.neutral)
        colors.extend(self.background)
        return colors


@dataclass
class FontFamily:
    """Font family specification."""

    name: str = ""
    category: str = ""  # serif, sans-serif, display, monospace
    weights: List[int] = field(default_factory=list)
    styles: List[str] = field(default_factory=list)  # normal, italic
    fallback: List[str] = field(default_factory=list)
    license: str = ""
    source: str = ""  # google fonts, adobe, custom

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "weights": self.weights,
            "styles": self.styles,
            "fallback": self.fallback,
        }


@dataclass
class Typography:
    """Brand typography system."""

    id: str = field(default_factory=lambda: str(uuid4()))

    # Font families
    primary_font: FontFamily = field(default_factory=FontFamily)
    secondary_font: Optional[FontFamily] = None
    accent_font: Optional[FontFamily] = None
    monospace_font: Optional[FontFamily] = None

    # Type scale
    base_size: int = 16
    scale_ratio: float = 1.25
    line_height: float = 1.5

    # Heading styles
    heading_styles: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Body styles
    body_styles: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "primary_font": self.primary_font.to_dict(),
            "secondary_font": self.secondary_font.to_dict() if self.secondary_font else None,
            "base_size": self.base_size,
            "scale_ratio": self.scale_ratio,
            "line_height": self.line_height,
            "heading_styles": self.heading_styles,
        }


@dataclass
class BrandAsset:
    """Brand asset record."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    asset_type: BrandAssetType = BrandAssetType.LOGO

    # File info
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    file_format: str = ""
    file_size: int = 0
    dimensions: Optional[Dict[str, int]] = None

    # Variants
    variants: List[Dict[str, Any]] = field(default_factory=list)

    # Usage
    usage_contexts: List[ContentType] = field(default_factory=list)
    usage_guidelines: str = ""
    min_size: Optional[Dict[str, int]] = None
    clear_space: Optional[str] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "asset_type": self.asset_type.value,
            "file_path": self.file_path,
            "file_url": self.file_url,
            "file_format": self.file_format,
            "dimensions": self.dimensions,
            "usage_contexts": [c.value for c in self.usage_contexts],
            "usage_guidelines": self.usage_guidelines,
            "tags": self.tags,
            "version": self.version,
        }


@dataclass
class BrandGuideline:
    """Brand guideline rule or instruction."""

    id: str = field(default_factory=lambda: str(uuid4()))
    category: str = ""  # logo, color, typography, voice, imagery
    title: str = ""
    description: str = ""
    rule_type: str = "guideline"  # guideline, requirement, prohibition

    # Applicability
    applies_to: List[ContentType] = field(default_factory=list)

    # Examples
    correct_examples: List[Dict[str, Any]] = field(default_factory=list)
    incorrect_examples: List[Dict[str, Any]] = field(default_factory=list)

    # Priority
    priority: str = "normal"  # critical, high, normal, low
    enforcement: str = "recommended"  # required, recommended, optional

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "rule_type": self.rule_type,
            "applies_to": [c.value for c in self.applies_to],
            "priority": self.priority,
            "enforcement": self.enforcement,
        }


@dataclass
class BrandVoiceGuideline:
    """Brand voice and messaging guidelines."""

    id: str = field(default_factory=lambda: str(uuid4()))

    # Voice characteristics
    primary_tone: BrandTone = BrandTone.PROFESSIONAL
    secondary_tones: List[BrandTone] = field(default_factory=list)
    voice_attributes: List[BrandVoice] = field(default_factory=list)

    # Messaging
    tagline: str = ""
    mission_statement: str = ""
    value_propositions: List[str] = field(default_factory=list)
    key_messages: List[str] = field(default_factory=list)

    # Vocabulary
    preferred_words: List[str] = field(default_factory=list)
    avoided_words: List[str] = field(default_factory=list)
    industry_terms: Dict[str, str] = field(default_factory=dict)

    # Writing style
    sentence_length: str = "medium"  # short, medium, long
    paragraph_length: str = "short"  # short, medium, long
    use_contractions: bool = True
    use_first_person: bool = False
    use_active_voice: bool = True

    # Content-specific guidance
    content_guidelines: Dict[ContentType, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "primary_tone": self.primary_tone.value,
            "secondary_tones": [t.value for t in self.secondary_tones],
            "voice_attributes": [v.value for v in self.voice_attributes],
            "tagline": self.tagline,
            "mission_statement": self.mission_statement,
            "value_propositions": self.value_propositions,
            "key_messages": self.key_messages,
            "preferred_words": self.preferred_words,
            "avoided_words": self.avoided_words,
            "writing_style": {
                "sentence_length": self.sentence_length,
                "use_contractions": self.use_contractions,
                "use_active_voice": self.use_active_voice,
            },
        }


@dataclass
class BrandIdentity:
    """Complete brand identity."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0"

    # Visual identity
    color_palette: ColorPalette = field(default_factory=ColorPalette)
    typography: Typography = field(default_factory=Typography)

    # Voice
    voice_guidelines: BrandVoiceGuideline = field(default_factory=BrandVoiceGuideline)

    # Assets
    assets: List[BrandAsset] = field(default_factory=list)

    # Guidelines
    guidelines: List[BrandGuideline] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    created_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "color_palette": self.color_palette.to_dict(),
            "typography": self.typography.to_dict(),
            "voice_guidelines": self.voice_guidelines.to_dict(),
            "assets_count": len(self.assets),
            "guidelines_count": len(self.guidelines),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def get_assets_by_type(self, asset_type: BrandAssetType) -> List[BrandAsset]:
        """Get assets of a specific type."""
        return [a for a in self.assets if a.asset_type == asset_type]

    def get_guidelines_by_category(self, category: str) -> List[BrandGuideline]:
        """Get guidelines for a category."""
        return [g for g in self.guidelines if g.category == category]

    def get_logo(self) -> Optional[BrandAsset]:
        """Get primary logo asset."""
        logos = self.get_assets_by_type(BrandAssetType.LOGO)
        return logos[0] if logos else None
