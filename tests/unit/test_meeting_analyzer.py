"""Tests for MeetingAnalyzer LLM-driven transcript analysis."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from ag3ntwerk.integrations.voice.meeting_analyzer import MeetingAnalyzer
from ag3ntwerk.models.meeting import MeetingAnalysis


# ============================================================
# Fixtures
# ============================================================


def _make_llm_response(content: str):
    """Create a mock LLM response."""
    resp = MagicMock()
    resp.content = content
    return resp


def _make_mock_llm(response_content: str):
    """Create a mock LLM provider that returns given content."""
    llm = MagicMock()
    llm.generate = AsyncMock(return_value=_make_llm_response(response_content))
    return llm


VALID_ANALYSIS_JSON = json.dumps({
    "executive_summary": "The team discussed Q2 goals and agreed on priorities.",
    "key_decisions": [
        {
            "summary": "Adopt microservices for payment system",
            "context": "Monolith is too slow to deploy",
            "decided_by": "Alice",
        }
    ],
    "action_items": [
        {
            "description": "Draft architecture proposal",
            "assignee": "Bob",
            "deadline": "2026-04-01",
            "priority": "high",
        },
        {
            "description": "Review competitor pricing",
            "assignee": None,
            "deadline": None,
            "priority": "medium",
        },
    ],
    "themes": ["architecture", "Q2 planning", "payments"],
    "questions": [
        {
            "question": "What's the migration timeline?",
            "answered": True,
            "answer": "6 weeks starting April",
            "asked_by": "Charlie",
        },
        {
            "question": "Do we need more headcount?",
            "answered": False,
            "answer": None,
            "asked_by": "Alice",
        },
    ],
    "sentiment": "productive",
    "participants": [
        {"name": "Alice", "role": "CTO"},
        {"name": "Bob", "role": "Lead Engineer"},
        {"name": "Charlie", "role": None},
    ],
    "suggested_title": "Q2 Architecture and Planning Review",
})


SAMPLE_TRANSCRIPT = (
    "Alice: Good morning everyone. Let's discuss our Q2 priorities. "
    "Bob: I think we should focus on the payment system migration. "
    "Charlie: What's the timeline for that? "
    "Alice: I'd say six weeks starting April. Bob, can you draft an "
    "architecture proposal by end of this week? "
    "Bob: Sure, I'll have it ready. "
    "Alice: Great. We're going with microservices for the payment system. "
    "The monolith is too slow to deploy. "
) * 3  # Repeat to exceed MIN_TRANSCRIPT_LENGTH


# ============================================================
# No LLM / Short Transcript
# ============================================================


class TestMeetingAnalyzerEdgeCases:
    @pytest.mark.asyncio
    async def test_no_llm_provider(self):
        analyzer = MeetingAnalyzer(llm_provider=None)
        result = await analyzer.analyze("Some transcript", "m_001")
        assert isinstance(result, MeetingAnalysis)
        assert "No LLM provider" in result.executive_summary

    @pytest.mark.asyncio
    async def test_short_transcript(self):
        llm = _make_mock_llm("{}")
        analyzer = MeetingAnalyzer(llm_provider=llm)
        result = await analyzer.analyze("Too short", "m_002")
        assert "too short" in result.executive_summary.lower()
        llm.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_transcript(self):
        llm = _make_mock_llm("{}")
        analyzer = MeetingAnalyzer(llm_provider=llm)
        result = await analyzer.analyze("", "m_003")
        assert "too short" in result.executive_summary.lower()

    @pytest.mark.asyncio
    async def test_whitespace_only_transcript(self):
        llm = _make_mock_llm("{}")
        analyzer = MeetingAnalyzer(llm_provider=llm)
        result = await analyzer.analyze("   \n\n  ", "m_004")
        assert "too short" in result.executive_summary.lower()


# ============================================================
# Successful Analysis
# ============================================================


class TestMeetingAnalyzerSuccess:
    @pytest.mark.asyncio
    async def test_full_analysis(self):
        llm = _make_mock_llm(VALID_ANALYSIS_JSON)
        analyzer = MeetingAnalyzer(llm_provider=llm)
        result = await analyzer.analyze(SAMPLE_TRANSCRIPT, "m_010")

        assert "Q2 goals" in result.executive_summary
        assert len(result.key_decisions) == 1
        assert result.key_decisions[0].summary == "Adopt microservices for payment system"
        assert len(result.action_items) == 2
        assert result.action_items[0]["assignee"] == "Bob"
        assert result.action_items[0]["priority"] == "high"
        assert result.action_items[1]["assignee"] is None
        assert result.themes == ["architecture", "Q2 planning", "payments"]
        assert len(result.questions) == 2
        assert result.questions[0].answered is True
        assert result.questions[1].answered is False
        assert result.sentiment == "productive"
        assert len(result.participants) == 3
        assert result.suggested_title == "Q2 Architecture and Planning Review"

    @pytest.mark.asyncio
    async def test_llm_called_with_correct_params(self):
        llm = _make_mock_llm(VALID_ANALYSIS_JSON)
        analyzer = MeetingAnalyzer(llm_provider=llm)
        await analyzer.analyze(SAMPLE_TRANSCRIPT, "m_011")

        llm.generate.assert_called_once()
        call_kwargs = llm.generate.call_args
        assert call_kwargs.kwargs.get("max_tokens") == 4096
        assert call_kwargs.kwargs.get("temperature") == 0.3

    @pytest.mark.asyncio
    async def test_llm_provider_property(self):
        llm1 = _make_mock_llm("{}")
        llm2 = _make_mock_llm(VALID_ANALYSIS_JSON)
        analyzer = MeetingAnalyzer(llm_provider=llm1)
        assert analyzer.llm_provider is llm1
        analyzer.llm_provider = llm2
        assert analyzer.llm_provider is llm2


# ============================================================
# JSON Parsing Edge Cases
# ============================================================


class TestMeetingAnalyzerParsing:
    @pytest.mark.asyncio
    async def test_markdown_fenced_json(self):
        fenced = f"```json\n{VALID_ANALYSIS_JSON}\n```"
        llm = _make_mock_llm(fenced)
        analyzer = MeetingAnalyzer(llm_provider=llm)
        result = await analyzer.analyze(SAMPLE_TRANSCRIPT, "m_020")
        assert len(result.action_items) == 2

    @pytest.mark.asyncio
    async def test_json_with_preamble(self):
        with_preamble = f"Here is the analysis:\n{VALID_ANALYSIS_JSON}"
        llm = _make_mock_llm(with_preamble)
        analyzer = MeetingAnalyzer(llm_provider=llm)
        result = await analyzer.analyze(SAMPLE_TRANSCRIPT, "m_021")
        assert result.sentiment == "productive"

    @pytest.mark.asyncio
    async def test_invalid_json_graceful(self):
        llm = _make_mock_llm("This is not JSON at all")
        analyzer = MeetingAnalyzer(llm_provider=llm)
        result = await analyzer.analyze(SAMPLE_TRANSCRIPT, "m_022")
        assert isinstance(result, MeetingAnalysis)
        assert "Could not parse" in result.executive_summary

    @pytest.mark.asyncio
    async def test_partial_json_fields(self):
        partial = json.dumps({
            "executive_summary": "Partial response",
            "themes": ["only-themes"],
        })
        llm = _make_mock_llm(partial)
        analyzer = MeetingAnalyzer(llm_provider=llm)
        result = await analyzer.analyze(SAMPLE_TRANSCRIPT, "m_023")
        assert result.executive_summary == "Partial response"
        assert result.themes == ["only-themes"]
        assert result.action_items == []
        assert result.participants == []

    @pytest.mark.asyncio
    async def test_empty_json_object(self):
        llm = _make_mock_llm("{}")
        analyzer = MeetingAnalyzer(llm_provider=llm)
        result = await analyzer.analyze(SAMPLE_TRANSCRIPT, "m_024")
        assert result.executive_summary == ""
        assert result.action_items == []

    @pytest.mark.asyncio
    async def test_malformed_action_items_skipped(self):
        data = json.dumps({
            "executive_summary": "Test",
            "action_items": [
                {"description": "Valid item", "priority": "low"},
                {"not_description": "Invalid item"},  # no description
                "not even a dict",
                {"description": "", "priority": "high"},  # empty description
            ],
        })
        llm = _make_mock_llm(data)
        analyzer = MeetingAnalyzer(llm_provider=llm)
        result = await analyzer.analyze(SAMPLE_TRANSCRIPT, "m_025")
        assert len(result.action_items) == 1
        assert result.action_items[0]["description"] == "Valid item"

    @pytest.mark.asyncio
    async def test_malformed_participants_skipped(self):
        data = json.dumps({
            "executive_summary": "Test",
            "participants": [
                {"name": "Alice", "role": "PM"},
                {"role": "Unknown"},  # no name
                "not a dict",
                {"name": "", "role": "Empty"},  # empty name
            ],
        })
        llm = _make_mock_llm(data)
        analyzer = MeetingAnalyzer(llm_provider=llm)
        result = await analyzer.analyze(SAMPLE_TRANSCRIPT, "m_026")
        assert len(result.participants) == 1
        assert result.participants[0].name == "Alice"


# ============================================================
# LLM Errors
# ============================================================


class TestMeetingAnalyzerErrors:
    @pytest.mark.asyncio
    async def test_llm_exception_handled(self):
        llm = MagicMock()
        llm.generate = AsyncMock(side_effect=RuntimeError("Connection timeout"))
        analyzer = MeetingAnalyzer(llm_provider=llm)
        result = await analyzer.analyze(SAMPLE_TRANSCRIPT, "m_030")
        assert isinstance(result, MeetingAnalysis)
        assert "failed" in result.executive_summary.lower()


# ============================================================
# Prompt Building
# ============================================================


class TestMeetingAnalyzerPrompt:
    def test_prompt_contains_transcript(self):
        analyzer = MeetingAnalyzer()
        prompt = analyzer._build_analysis_prompt("Hello world " * 20)
        assert "Hello world" in prompt

    def test_long_transcript_truncated(self):
        long_text = "A" * 20000
        analyzer = MeetingAnalyzer()
        prompt = analyzer._build_analysis_prompt(long_text)
        assert "truncated" in prompt.lower()
        # Prompt should not contain all 20000 chars
        assert len(prompt) < 20000

    def test_short_transcript_no_truncation_note(self):
        analyzer = MeetingAnalyzer()
        prompt = analyzer._build_analysis_prompt("Short meeting notes here.")
        assert "truncated" not in prompt.lower()

    def test_prompt_requests_json_format(self):
        analyzer = MeetingAnalyzer()
        prompt = analyzer._build_analysis_prompt("Some transcript text here.")
        assert "JSON" in prompt
        assert "executive_summary" in prompt
        assert "action_items" in prompt
        assert "themes" in prompt


# ============================================================
# _clean_json
# ============================================================


class TestCleanJson:
    def test_plain_json(self):
        assert MeetingAnalyzer._clean_json('{"a": 1}') == '{"a": 1}'

    def test_markdown_fences(self):
        assert MeetingAnalyzer._clean_json('```json\n{"a": 1}\n```') == '{"a": 1}'

    def test_preamble_text(self):
        assert MeetingAnalyzer._clean_json('Here: {"a": 1}') == '{"a": 1}'

    def test_trailing_text(self):
        assert MeetingAnalyzer._clean_json('{"a": 1} done!') == '{"a": 1}'

    def test_no_json(self):
        result = MeetingAnalyzer._clean_json("no json here")
        assert result == "no json here"
