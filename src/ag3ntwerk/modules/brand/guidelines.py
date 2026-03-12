"""
Brand Guidelines Management - Validation and consistency checking.

Provides guideline management, content validation, and consistency
enforcement for brand compliance.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ag3ntwerk.modules.brand.core import (
    BrandIdentity,
    BrandGuideline,
    BrandVoiceGuideline,
    BrandTone,
    ContentType,
    ColorPalette,
    ColorValue,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a brand validation check."""

    id: str = field(default_factory=lambda: str(uuid4()))
    passed: bool = True
    score: float = 100.0  # 0-100
    issues: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "passed": self.passed,
            "score": self.score,
            "issues_count": len(self.issues),
            "warnings_count": len(self.warnings),
            "issues": self.issues,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }

    def add_issue(
        self,
        category: str,
        message: str,
        severity: str = "error",
        location: Optional[str] = None,
    ) -> None:
        """Add an issue to the result."""
        self.issues.append(
            {
                "category": category,
                "message": message,
                "severity": severity,
                "location": location,
            }
        )
        self.passed = False
        self._recalculate_score()

    def add_warning(
        self,
        category: str,
        message: str,
        location: Optional[str] = None,
    ) -> None:
        """Add a warning to the result."""
        self.warnings.append(
            {
                "category": category,
                "message": message,
                "location": location,
            }
        )
        self._recalculate_score()

    def _recalculate_score(self) -> None:
        """Recalculate the score based on issues and warnings."""
        issue_penalty = len(self.issues) * 15
        warning_penalty = len(self.warnings) * 5
        self.score = max(0, 100 - issue_penalty - warning_penalty)


class GuidelineValidator:
    """Validates content against brand guidelines."""

    def __init__(self, identity: BrandIdentity):
        self.identity = identity
        self.voice = identity.voice_guidelines

    def validate_text(
        self,
        text: str,
        content_type: ContentType = ContentType.WEBSITE,
    ) -> ValidationResult:
        """Validate text content against brand guidelines."""
        result = ValidationResult()

        # Check voice and tone
        self._check_voice(text, result)

        # Check vocabulary
        self._check_vocabulary(text, result)

        # Check writing style
        self._check_writing_style(text, result)

        # Content-type specific checks
        self._check_content_type_rules(text, content_type, result)

        return result

    def _check_voice(self, text: str, result: ValidationResult) -> None:
        """Check if text aligns with brand voice."""
        text_lower = text.lower()

        # Check for tone indicators
        formal_indicators = ["therefore", "hereby", "pursuant", "whereas"]
        casual_indicators = ["hey", "awesome", "cool", "gonna", "wanna"]

        if self.voice.primary_tone == BrandTone.PROFESSIONAL:
            for indicator in casual_indicators:
                if indicator in text_lower:
                    result.add_warning(
                        "voice",
                        f"Casual language '{indicator}' may not align with professional tone",
                    )

        elif self.voice.primary_tone == BrandTone.CASUAL:
            formal_count = sum(1 for f in formal_indicators if f in text_lower)
            if formal_count > 2:
                result.add_warning(
                    "voice",
                    "Content may be too formal for casual brand voice",
                )

    def _check_vocabulary(self, text: str, result: ValidationResult) -> None:
        """Check vocabulary against preferred/avoided words."""
        text_lower = text.lower()

        # Check avoided words
        for word in self.voice.avoided_words:
            if word.lower() in text_lower:
                result.add_issue(
                    "vocabulary",
                    f"Avoided word detected: '{word}'",
                    severity="warning",
                )

        # Suggest preferred alternatives
        word_pairs = {
            "cheap": "affordable",
            "buy": "invest in",
            "problem": "challenge",
            "but": "however",
        }

        for avoid, prefer in word_pairs.items():
            if avoid in text_lower and prefer in self.voice.preferred_words:
                result.suggestions.append(f"Consider using '{prefer}' instead of '{avoid}'")

    def _check_writing_style(self, text: str, result: ValidationResult) -> None:
        """Check writing style guidelines."""
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return

        # Check sentence length
        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)

        if self.voice.sentence_length == "short" and avg_words > 15:
            result.add_warning(
                "style",
                f"Average sentence length ({avg_words:.1f} words) may be too long for brand style",
            )
        elif self.voice.sentence_length == "long" and avg_words < 10:
            result.add_warning(
                "style",
                f"Average sentence length ({avg_words:.1f} words) may be too short for brand style",
            )

        # Check active voice (simple heuristic)
        if self.voice.use_active_voice:
            passive_indicators = ["was", "were", "been", "being", "is being", "are being"]
            passive_count = sum(1 for p in passive_indicators if p in text.lower())
            if passive_count > len(sentences) * 0.3:
                result.add_warning(
                    "style",
                    "Content may contain too much passive voice",
                )

        # Check contractions
        contractions = ["don't", "won't", "can't", "isn't", "aren't", "we're", "you're"]
        has_contractions = any(c in text.lower() for c in contractions)

        if self.voice.use_contractions and not has_contractions:
            result.suggestions.append("Consider using contractions to match brand voice")
        elif not self.voice.use_contractions and has_contractions:
            result.add_warning(
                "style",
                "Contractions detected but not preferred in brand voice",
            )

    def _check_content_type_rules(
        self,
        text: str,
        content_type: ContentType,
        result: ValidationResult,
    ) -> None:
        """Check content-type specific rules."""
        if content_type == ContentType.SOCIAL_MEDIA:
            if len(text) > 280:
                result.add_warning(
                    "length",
                    "Text may be too long for social media",
                )
            if not any(h in text for h in ["#", "@"]):
                result.suggestions.append("Consider adding hashtags or mentions for social media")

        elif content_type == ContentType.EMAIL:
            if not text.strip().startswith(("Hi", "Hello", "Dear", "Hey")):
                result.suggestions.append("Consider starting email with a greeting")

        elif content_type == ContentType.ADVERTISING:
            if len(text) > 150:
                result.add_warning(
                    "length",
                    "Ad copy may be too long for effective advertising",
                )


class ConsistencyChecker:
    """Checks brand consistency across content."""

    def __init__(self, identity: BrandIdentity):
        self.identity = identity

    def check_color_usage(
        self,
        colors_used: List[str],
    ) -> ValidationResult:
        """Check if colors used are from the brand palette."""
        result = ValidationResult()
        palette = self.identity.color_palette

        # Get all brand colors
        brand_colors = set()
        for color in palette.get_all_colors():
            brand_colors.add(color.hex.lower())
            if color.rgb:
                brand_colors.add(f"rgb({color.rgb[0]},{color.rgb[1]},{color.rgb[2]})")

        # Check each used color
        for color in colors_used:
            color_lower = color.lower().replace(" ", "")
            if color_lower not in brand_colors:
                result.add_warning(
                    "color",
                    f"Color '{color}' is not in the brand palette",
                )

        return result

    def check_typography(
        self,
        fonts_used: List[str],
    ) -> ValidationResult:
        """Check if fonts used are from brand typography."""
        result = ValidationResult()
        typography = self.identity.typography

        # Get brand fonts
        brand_fonts = set()
        brand_fonts.add(typography.primary_font.name.lower())
        if typography.secondary_font:
            brand_fonts.add(typography.secondary_font.name.lower())
        if typography.accent_font:
            brand_fonts.add(typography.accent_font.name.lower())

        # Check each used font
        for font in fonts_used:
            if font.lower() not in brand_fonts:
                result.add_warning(
                    "typography",
                    f"Font '{font}' is not in the brand typography system",
                )

        return result

    def check_logo_usage(
        self,
        logo_size: Optional[Dict[str, int]] = None,
        background_color: Optional[str] = None,
    ) -> ValidationResult:
        """Check logo usage against guidelines."""
        result = ValidationResult()

        logo = self.identity.get_logo()
        if not logo:
            result.add_issue("logo", "No logo defined in brand identity")
            return result

        # Check minimum size
        if logo_size and logo.min_size:
            if logo_size.get("width", 0) < logo.min_size.get("width", 0):
                result.add_issue(
                    "logo",
                    f"Logo width ({logo_size['width']}px) is below minimum ({logo.min_size['width']}px)",
                )
            if logo_size.get("height", 0) < logo.min_size.get("height", 0):
                result.add_issue(
                    "logo",
                    f"Logo height ({logo_size['height']}px) is below minimum ({logo.min_size['height']}px)",
                )

        return result

    def generate_consistency_report(
        self,
        content_samples: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate a comprehensive consistency report."""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "brand": self.identity.name,
            "samples_analyzed": len(content_samples),
            "overall_score": 100.0,
            "category_scores": {},
            "issues": [],
            "recommendations": [],
        }

        total_score = 0
        category_issues: Dict[str, int] = {}

        validator = GuidelineValidator(self.identity)

        for sample in content_samples:
            content_type = ContentType(sample.get("type", "website"))
            text = sample.get("text", "")

            if text:
                result = validator.validate_text(text, content_type)
                total_score += result.score

                for issue in result.issues:
                    cat = issue["category"]
                    category_issues[cat] = category_issues.get(cat, 0) + 1
                    report["issues"].append(
                        {
                            "sample": sample.get("name", "Unknown"),
                            **issue,
                        }
                    )

        if content_samples:
            report["overall_score"] = total_score / len(content_samples)

        # Calculate category scores
        for cat, count in category_issues.items():
            max_issues = len(content_samples)
            report["category_scores"][cat] = max(0, 100 - (count / max_issues * 100))

        # Generate recommendations
        if category_issues.get("voice", 0) > len(content_samples) * 0.3:
            report["recommendations"].append(
                "Review voice guidelines with content team - frequent misalignment detected"
            )
        if category_issues.get("vocabulary", 0) > 0:
            report["recommendations"].append(
                "Update content to remove avoided words and use preferred vocabulary"
            )

        return report


class GuidelineManager:
    """Manages brand guidelines storage and retrieval."""

    def __init__(self, storage_path: Optional[Path] = None):
        self._guidelines: Dict[str, BrandGuideline] = {}
        self._storage_path = storage_path

        if storage_path and storage_path.exists():
            self._load_guidelines()

    def add_guideline(self, guideline: BrandGuideline) -> None:
        """Add a guideline."""
        self._guidelines[guideline.id] = guideline
        logger.info(f"Added guideline: {guideline.title}")

    def get_guideline(self, guideline_id: str) -> Optional[BrandGuideline]:
        """Get a guideline by ID."""
        return self._guidelines.get(guideline_id)

    def get_by_category(self, category: str) -> List[BrandGuideline]:
        """Get guidelines by category."""
        return [g for g in self._guidelines.values() if g.category == category]

    def get_for_content_type(self, content_type: ContentType) -> List[BrandGuideline]:
        """Get guidelines applicable to a content type."""
        return [
            g for g in self._guidelines.values() if not g.applies_to or content_type in g.applies_to
        ]

    def get_required_guidelines(self) -> List[BrandGuideline]:
        """Get all required guidelines."""
        return [g for g in self._guidelines.values() if g.enforcement == "required"]

    def list_all(self) -> List[BrandGuideline]:
        """List all guidelines."""
        return list(self._guidelines.values())

    def search(self, query: str) -> List[BrandGuideline]:
        """Search guidelines."""
        query_lower = query.lower()
        return [
            g
            for g in self._guidelines.values()
            if query_lower in g.title.lower() or query_lower in g.description.lower()
        ]

    def _load_guidelines(self) -> None:
        """Load guidelines from storage."""
        try:
            with open(self._storage_path) as f:
                data = json.load(f)

            for item in data.get("guidelines", []):
                guideline = BrandGuideline(
                    id=item.get("id", str(uuid4())),
                    category=item.get("category", ""),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    rule_type=item.get("rule_type", "guideline"),
                    priority=item.get("priority", "normal"),
                    enforcement=item.get("enforcement", "recommended"),
                )
                self._guidelines[guideline.id] = guideline

        except Exception as e:
            logger.error(f"Failed to load guidelines: {e}")

    def save_guidelines(self) -> None:
        """Save guidelines to storage."""
        if not self._storage_path:
            return

        data = {"guidelines": [g.to_dict() for g in self._guidelines.values()]}

        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        """Get guidelines statistics."""
        guidelines = self.list_all()
        return {
            "total_guidelines": len(guidelines),
            "by_category": {
                cat: len([g for g in guidelines if g.category == cat])
                for cat in set(g.category for g in guidelines)
            },
            "required_count": len(self.get_required_guidelines()),
        }
