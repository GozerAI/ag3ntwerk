"""
Expertise Extractor for ag3ntwerk.

Analyzes voice transcripts to extract unique insights, frameworks,
and actionable advice using LLM-based analysis.

Primary consumers:
- Echo (Echo): Content marketing from expertise insights
- Vector (Vector): Revenue-relevant market insights
- ContentOrchestratorBridge: Automated content pipelines

Usage:
    extractor = ExpertiseExtractor(llm_provider=llm)

    # From a TranscriptionResult
    result = await extractor.extract_from_transcription(transcription)

    # From a VoiceTranscript model
    result = await extractor.extract_from_transcript(voice_transcript)
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ag3ntwerk.llm.base import LLMProvider
from ag3ntwerk.models.content import ExpertiseInsight, VoiceTranscript

logger = logging.getLogger(__name__)


class ExtractionResult:
    """Result of expertise extraction from a transcript."""

    def __init__(
        self,
        transcript_id: str,
        insights: List[ExpertiseInsight],
        topics: List[str],
        summary: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.transcript_id = transcript_id
        self.insights = insights
        self.topics = topics
        self.summary = summary
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "transcript_id": self.transcript_id,
            "insights": [i.model_dump() for i in self.insights],
            "topics": self.topics,
            "summary": self.summary,
            "insight_count": len(self.insights),
            "metadata": self.metadata,
        }


class ExpertiseExtractor:
    """
    Extracts expertise insights from voice transcripts.

    Uses LLM analysis to identify unique perspectives, frameworks,
    and actionable advice from transcribed speech. Produces
    ExpertiseInsight objects that can feed into content pipelines.

    Example:
        extractor = ExpertiseExtractor(llm_provider=llm)
        result = await extractor.extract_from_transcript(transcript)
        for insight in result.insights:
            print(f"[{insight.topic}] {insight.insight}")
    """

    # Minimum transcript length (characters) worth extracting from
    MIN_TRANSCRIPT_LENGTH = 50

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        max_insights: int = 10,
    ):
        """
        Initialize the ExpertiseExtractor.

        Args:
            llm_provider: LLM provider for analysis
            max_insights: Maximum insights to extract per transcript
        """
        self._llm = llm_provider
        self._max_insights = max_insights

    @property
    def llm_provider(self) -> Optional[LLMProvider]:
        """Access the LLM provider."""
        return self._llm

    @llm_provider.setter
    def llm_provider(self, value: LLMProvider) -> None:
        """Set the LLM provider."""
        self._llm = value

    async def extract_from_transcription(
        self,
        transcription_result,
        audio_file: str = "",
    ) -> ExtractionResult:
        """
        Extract insights from a WhisperIntegration TranscriptionResult.

        Converts the dataclass-based TranscriptionResult into a
        VoiceTranscript Pydantic model, then extracts insights.

        Args:
            transcription_result: TranscriptionResult from WhisperIntegration
            audio_file: Original audio file path (optional)

        Returns:
            ExtractionResult with extracted insights
        """
        # Convert TranscriptionResult (dataclass) to VoiceTranscript (Pydantic)
        segments = []
        for seg in transcription_result.segments:
            segments.append(
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                }
            )

        transcript = VoiceTranscript(
            id=transcription_result.audio_path or audio_file or "unknown",
            audio_file=transcription_result.audio_path or audio_file,
            full_text=transcription_result.text,
            duration_seconds=transcription_result.duration,
            language=transcription_result.language,
            segments=segments,
        )

        return await self.extract_from_transcript(transcript)

    async def extract_from_transcript(
        self,
        transcript: VoiceTranscript,
    ) -> ExtractionResult:
        """
        Extract expertise insights from a VoiceTranscript.

        Args:
            transcript: VoiceTranscript model to analyze

        Returns:
            ExtractionResult with extracted insights
        """
        if not self._llm:
            return ExtractionResult(
                transcript_id=transcript.id,
                insights=[],
                topics=[],
                summary="No LLM provider configured for extraction",
                metadata={"error": "no_llm"},
            )

        text = transcript.full_text.strip()
        if len(text) < self.MIN_TRANSCRIPT_LENGTH:
            return ExtractionResult(
                transcript_id=transcript.id,
                insights=[],
                topics=[],
                summary="Transcript too short for meaningful extraction",
                metadata={"error": "too_short", "length": len(text)},
            )

        # Extract insights via LLM
        insights, topics, summary = await self._extract_with_llm(text, transcript.id)

        return ExtractionResult(
            transcript_id=transcript.id,
            insights=insights,
            topics=topics,
            summary=summary,
            metadata={
                "duration_seconds": transcript.duration_seconds,
                "language": transcript.language,
                "text_length": len(text),
            },
        )

    async def extract_from_text(
        self,
        text: str,
        source_id: str = "raw_text",
    ) -> ExtractionResult:
        """
        Extract insights from raw text (no transcript wrapper).

        Args:
            text: Raw text to analyze
            source_id: Identifier for the source

        Returns:
            ExtractionResult with extracted insights
        """
        if not self._llm:
            return ExtractionResult(
                transcript_id=source_id,
                insights=[],
                topics=[],
                summary="No LLM provider configured",
                metadata={"error": "no_llm"},
            )

        text = text.strip()
        if len(text) < self.MIN_TRANSCRIPT_LENGTH:
            return ExtractionResult(
                transcript_id=source_id,
                insights=[],
                topics=[],
                summary="Text too short for extraction",
                metadata={"error": "too_short", "length": len(text)},
            )

        insights, topics, summary = await self._extract_with_llm(text, source_id)

        return ExtractionResult(
            transcript_id=source_id,
            insights=insights,
            topics=topics,
            summary=summary,
            metadata={"text_length": len(text)},
        )

    async def _extract_with_llm(
        self,
        text: str,
        source_id: str,
    ) -> tuple:
        """
        Use LLM to extract insights from text.

        Returns:
            Tuple of (insights, topics, summary)
        """
        prompt = f"""Analyze the following transcript and extract unique expertise insights.

TRANSCRIPT:
{text[:4000]}

INSTRUCTIONS:
Return a JSON object with exactly these keys:
- "summary": A 1-2 sentence summary of the main topic
- "topics": A list of 3-5 topic keywords
- "insights": A list of objects, each with:
  - "topic": The specific topic area (2-4 words)
  - "insight": The key insight or advice (1-2 sentences)
  - "quote": A direct quote under 20 words from the transcript
  - "tags": 2-3 relevant tags

Extract up to {self._max_insights} insights. Focus on:
1. Unique perspectives or unconventional views
2. Actionable frameworks or methods
3. Data-backed claims or evidence
4. Practical advice based on experience

Return ONLY valid JSON, no other text."""

        try:
            response = await self._llm.generate(prompt)
            return self._parse_extraction_response(response.content, source_id)
        except Exception as e:
            logger.warning("LLM extraction failed: %s", e)
            return ([], [], f"Extraction failed: {e}")

    def _parse_extraction_response(
        self,
        response_text: str,
        source_id: str,
    ) -> tuple:
        """
        Parse LLM response into structured insights.

        Returns:
            Tuple of (insights, topics, summary)
        """
        try:
            # Try to parse JSON from response
            data = json.loads(self._clean_json(response_text))
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse extraction JSON, using fallback")
            return (
                [],
                [],
                "Could not parse LLM response",
            )

        summary = data.get("summary", "")
        topics = data.get("topics", [])

        insights = []
        for item in data.get("insights", []):
            try:
                insight = ExpertiseInsight(
                    topic=item.get("topic", "General"),
                    insight=item.get("insight", ""),
                    quote=item.get("quote", ""),
                    tags=item.get("tags", []),
                    source_transcript_id=source_id,
                )
                insights.append(insight)
            except (KeyError, TypeError, ValueError) as e:
                logger.debug("Skipping malformed insight: %s", e)
                continue

        return (insights, topics, summary)

    @staticmethod
    def _clean_json(text: str) -> str:
        """Clean LLM response to extract JSON."""
        text = text.strip()

        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Find JSON object boundaries
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

        return text
