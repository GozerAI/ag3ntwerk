"""
Meeting Analyzer for ag3ntwerk.

Analyzes meeting transcripts using LLM to extract structured intelligence:
executive summary, key decisions, action items, themes, questions,
sentiment, and participant detection.

Follows the ExpertiseExtractor pattern: build prompt -> LLM generate -> parse JSON.

Usage:
    analyzer = MeetingAnalyzer(llm_provider=llm)
    analysis = await analyzer.analyze("transcript text here...", "meeting_123")
"""

import json
import logging
from typing import Optional

from ag3ntwerk.llm.base import LLMProvider
from ag3ntwerk.models.meeting import MeetingAnalysis

logger = logging.getLogger(__name__)


class MeetingAnalyzer:
    """
    LLM-driven meeting transcript analysis.

    Produces structured MeetingAnalysis from raw transcript text,
    extracting decisions, action items, themes, and more.

    Example:
        analyzer = MeetingAnalyzer(llm_provider=llm)
        analysis = await analyzer.analyze(transcript_text, meeting_id)
        print(analysis.executive_summary)
        for item in analysis.action_items:
            print(f"  [{item['priority']}] {item['description']} -> {item['assignee']}")
    """

    MIN_TRANSCRIPT_LENGTH = 100

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm = llm_provider

    @property
    def llm_provider(self) -> Optional[LLMProvider]:
        return self._llm

    @llm_provider.setter
    def llm_provider(self, value: LLMProvider) -> None:
        self._llm = value

    async def analyze(
        self,
        transcript_text: str,
        meeting_id: str = "",
    ) -> MeetingAnalysis:
        """
        Analyze a meeting transcript and return structured analysis.

        Args:
            transcript_text: Full transcript text
            meeting_id: Meeting identifier for logging

        Returns:
            MeetingAnalysis with extracted information
        """
        if not self._llm:
            logger.warning("No LLM provider configured for meeting analysis")
            return MeetingAnalysis(
                executive_summary="No LLM provider configured for analysis.",
            )

        text = transcript_text.strip()
        if len(text) < self.MIN_TRANSCRIPT_LENGTH:
            return MeetingAnalysis(
                executive_summary="Transcript too short for meaningful analysis.",
            )

        prompt = self._build_analysis_prompt(text)

        try:
            response = await self._llm.generate(
                prompt,
                max_tokens=4096,
                temperature=0.3,
            )
            return self._parse_analysis_response(response.content)
        except Exception as e:
            logger.error("Meeting analysis failed for %s: %s", meeting_id, e)
            return MeetingAnalysis(
                executive_summary=f"Analysis failed: {e}",
            )

    def _build_analysis_prompt(self, text: str) -> str:
        """Build the LLM prompt for meeting analysis."""
        # Truncate very long transcripts to fit context window
        truncated = text[:12000]
        was_truncated = len(text) > 12000

        truncation_note = ""
        if was_truncated:
            truncation_note = (
                "\n\nNOTE: This transcript was truncated. "
                "Focus on the content provided."
            )

        return f"""You are a meeting analyst. Analyze this meeting transcript and extract structured information.

TRANSCRIPT:
{truncated}{truncation_note}

Return a JSON object with EXACTLY these keys:
{{
  "executive_summary": "2-3 paragraph summary of the meeting covering main topics, outcomes, and next steps",
  "key_decisions": [
    {{"summary": "What was decided", "context": "Why or how it was decided", "decided_by": "Person name or null"}}
  ],
  "action_items": [
    {{
      "description": "What needs to be done",
      "assignee": "Person name or null",
      "deadline": "ISO date string (YYYY-MM-DD) or null",
      "priority": "low or medium or high"
    }}
  ],
  "themes": ["theme1", "theme2"],
  "questions": [
    {{"question": "The question raised", "answered": true, "answer": "The answer given or null", "asked_by": "Person or null"}}
  ],
  "sentiment": "One word: collaborative, productive, tense, neutral, positive, or negative",
  "participants": [
    {{"name": "Person name", "role": "Their role or null"}}
  ],
  "suggested_title": "Short meeting title, 5-10 words"
}}

Rules:
- For action items, infer deadlines from phrases like "by Friday", "next week", "end of month". Convert to ISO dates.
- Detect participants from speech patterns, name mentions, and speaker attribution.
- If no clear assignee for an action item, set to null.
- Focus on actionable, specific items over vague notes.
- Include both answered and unanswered questions.
- Return ONLY valid JSON, no other text."""

    def _parse_analysis_response(self, response_text: str) -> MeetingAnalysis:
        """Parse LLM JSON response into a MeetingAnalysis."""
        try:
            data = json.loads(self._clean_json(response_text))
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse meeting analysis JSON")
            return MeetingAnalysis(
                executive_summary="Could not parse analysis response.",
            )

        return MeetingAnalysis(
            executive_summary=data.get("executive_summary", ""),
            key_decisions=[
                {
                    "summary": d.get("summary", ""),
                    "context": d.get("context", ""),
                    "decided_by": d.get("decided_by"),
                }
                for d in data.get("key_decisions", [])
                if isinstance(d, dict)
            ],
            action_items=[
                {
                    "description": a.get("description", ""),
                    "assignee": a.get("assignee"),
                    "deadline": a.get("deadline"),
                    "priority": a.get("priority", "medium"),
                }
                for a in data.get("action_items", [])
                if isinstance(a, dict) and a.get("description")
            ],
            themes=[t for t in data.get("themes", []) if isinstance(t, str)],
            questions=[
                {
                    "question": q.get("question", ""),
                    "answered": q.get("answered", False),
                    "answer": q.get("answer"),
                    "asked_by": q.get("asked_by"),
                }
                for q in data.get("questions", [])
                if isinstance(q, dict)
            ],
            sentiment=data.get("sentiment", "neutral"),
            participants=[
                {"name": p.get("name", "Unknown"), "role": p.get("role")}
                for p in data.get("participants", [])
                if isinstance(p, dict) and p.get("name")
            ],
            suggested_title=data.get("suggested_title", ""),
        )

    @staticmethod
    def _clean_json(text: str) -> str:
        """Clean LLM response to extract JSON."""
        text = text.strip()

        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Find JSON object boundaries
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

        return text
