"""Tests for multi-turn reason() in Agent."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from ag3ntwerk.core.base import Agent, Task, TaskResult, TaskPriority


# ------------------------------------------------------------------
# Minimal concrete agent for testing
# ------------------------------------------------------------------


class _TestAgent(Agent):
    """Minimal concrete agent for testing reason()."""

    async def execute(self, task: Task) -> TaskResult:
        return TaskResult(task_id=task.id, success=True, output="ok")

    def can_handle(self, task: Task) -> bool:
        return True


def _make_agent(llm_provider=None):
    return _TestAgent(
        code="TST",
        name="Test Agent",
        domain="testing",
        llm_provider=llm_provider,
    )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


@dataclass
class FakeLLMResponse:
    content: str
    model: str = "test-model"


def _mock_llm():
    """Return a mock LLM provider with generate and chat methods."""
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=FakeLLMResponse(content="single-turn answer"))
    llm.chat = AsyncMock(return_value=FakeLLMResponse(content="multi-turn answer"))
    return llm


# ------------------------------------------------------------------
# Tests: single-turn path
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reason_single_turn_uses_generate():
    llm = _mock_llm()
    agent = _make_agent(llm)

    result = await agent.reason("Hello")

    llm.generate.assert_called_once()
    llm.chat.assert_not_called()
    # generate returns an LLMResponse; reason() returns its .content via
    # the llm_provider.generate() path which returns the raw object.
    # The single-turn path returns `await self.llm_provider.generate(full_prompt)`
    # which is the FakeLLMResponse — but reason() returns the object itself
    # (the agent base class returns the raw result of generate).
    assert result.content == "single-turn answer"


@pytest.mark.asyncio
async def test_reason_single_turn_without_history_in_context():
    llm = _mock_llm()
    agent = _make_agent(llm)

    result = await agent.reason("Hello", context={"some_key": "value"})

    llm.generate.assert_called_once()
    llm.chat.assert_not_called()


# ------------------------------------------------------------------
# Tests: multi-turn path
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reason_multi_turn_uses_chat():
    llm = _mock_llm()
    agent = _make_agent(llm)

    history = [
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "4"},
    ]
    context = {"_conversation_history": history}

    result = await agent.reason("And what is 3+3?", context=context)

    llm.chat.assert_called_once()
    llm.generate.assert_not_called()
    assert result == "multi-turn answer"


@pytest.mark.asyncio
async def test_reason_multi_turn_message_structure():
    """Verify the messages list sent to chat() has system + history + user."""
    llm = _mock_llm()
    agent = _make_agent(llm)

    history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
    ]
    context = {"_conversation_history": history}

    await agent.reason("Follow-up question", context=context)

    call_args = llm.chat.call_args
    messages = call_args[1].get("messages") or call_args[0][0]

    assert len(messages) == 4  # system + 2 history + 1 current

    assert messages[0].role == "system"
    assert "TST" in messages[0].content
    assert "Test Agent" in messages[0].content

    assert messages[1].role == "user"
    assert messages[1].content == "Hi"

    assert messages[2].role == "assistant"
    assert messages[2].content == "Hello!"

    assert messages[3].role == "user"
    assert messages[3].content == "Follow-up question"


@pytest.mark.asyncio
async def test_reason_multi_turn_system_message_includes_domain():
    llm = _mock_llm()
    agent = _make_agent(llm)

    context = {"_conversation_history": []}
    await agent.reason("test", context=context)

    messages = llm.chat.call_args[0][0]
    assert "testing" in messages[0].content  # domain


@pytest.mark.asyncio
async def test_reason_multi_turn_with_heuristic_flags():
    llm = _mock_llm()
    agent = _make_agent(llm)

    context = {
        "_conversation_history": [],
        "_thoroughness_boost": True,
        "_risk_allowance": True,
        "_collaboration_suggested": True,
    }
    await agent.reason("test", context=context)

    messages = llm.chat.call_args[0][0]
    system_content = messages[0].content
    assert "thorough" in system_content.lower()
    assert "bold" in system_content.lower() or "risk" in system_content.lower()
    assert "consulting" in system_content.lower() or "collaborat" in system_content.lower()


@pytest.mark.asyncio
async def test_reason_multi_turn_empty_history():
    """Empty history list still triggers multi-turn path (system + user only)."""
    llm = _mock_llm()
    agent = _make_agent(llm)

    context = {"_conversation_history": []}
    await agent.reason("First message", context=context)

    llm.chat.assert_called_once()
    messages = llm.chat.call_args[0][0]
    assert len(messages) == 2  # system + user
    assert messages[-1].content == "First message"


@pytest.mark.asyncio
async def test_reason_multi_turn_with_personality():
    llm = _mock_llm()
    agent = _make_agent(llm)

    # Attach a mock personality
    personality = MagicMock()
    personality.to_system_prompt_fragment.return_value = "I am analytical and detail-oriented."
    agent.personality = personality

    context = {"_conversation_history": []}
    await agent.reason("test", context=context)

    messages = llm.chat.call_args[0][0]
    assert "analytical" in messages[0].content


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reason_no_llm_provider_raises():
    agent = _make_agent(llm_provider=None)
    with pytest.raises(RuntimeError, match="no LLM provider"):
        await agent.reason("test")


@pytest.mark.asyncio
async def test_reason_history_none_uses_single_turn():
    """_conversation_history=None should NOT trigger multi-turn."""
    llm = _mock_llm()
    agent = _make_agent(llm)

    context = {"_conversation_history": None}
    await agent.reason("test", context=context)

    # None is falsy, so single-turn path
    llm.generate.assert_called_once()
    llm.chat.assert_not_called()


# ------------------------------------------------------------------
# Tests: enriched system message with organizational context
# ------------------------------------------------------------------


def _make_agent_with_codename(llm_provider=None, codename="Forge"):
    agent = _TestAgent(
        code="Forge",
        name="Forge",
        domain="Development, Engineering, Architecture",
        llm_provider=llm_provider,
    )
    agent.codename = codename
    return agent


@pytest.mark.asyncio
async def test_org_context_csuite_framing_and_codename():
    """System message includes ag3ntwerk framing and codename when org context is provided."""
    llm = _mock_llm()
    agent = _make_agent_with_codename(llm, codename="Forge")

    context = {
        "_conversation_history": [],
        "_organizational_context": {"peers": [], "goals": []},
    }
    await agent.reason("hello", context=context)

    messages = llm.chat.call_args[0][0]
    system = messages[0].content
    assert "Forge" in system
    assert "ag3ntwerk" in system
    assert "Forge" in system
    assert "Respond conversationally" in system


@pytest.mark.asyncio
async def test_org_context_peer_executives_appear():
    """Peer agents appear in the system message."""
    llm = _mock_llm()
    agent = _make_agent_with_codename(llm)

    context = {
        "_conversation_history": [],
        "_organizational_context": {
            "peers": [
                "Keystone (Keystone): Finance, Budgeting, Resource Management",
                "Echo (Echo): Marketing, Brand, Growth",
            ],
        },
    }
    await agent.reason("hello", context=context)

    messages = llm.chat.call_args[0][0]
    system = messages[0].content
    assert "Your peer agents:" in system
    assert "Keystone (Keystone)" in system
    assert "Echo (Echo)" in system


@pytest.mark.asyncio
async def test_org_context_goals_appear():
    """Active goals appear in the system message."""
    llm = _mock_llm()
    agent = _make_agent_with_codename(llm)

    context = {
        "_conversation_history": [],
        "_organizational_context": {
            "goals": [
                "Phase 1: Foundation Hardening (25%)",
                "Eliminate Claude API Costs (0%)",
            ],
        },
    }
    await agent.reason("hello", context=context)

    messages = llm.chat.call_args[0][0]
    system = messages[0].content
    assert "Current organizational focus:" in system
    assert "Foundation Hardening (25%)" in system
    assert "Eliminate Claude API Costs (0%)" in system


@pytest.mark.asyncio
async def test_org_context_system_state_appears():
    """System state lines appear in the system message."""
    llm = _mock_llm()
    agent = _make_agent_with_codename(llm)

    context = {
        "_conversation_history": [],
        "_organizational_context": {
            "system_state": [
                "LLM: Ollama (qwen2.5:14b)",
                "Tasks: 12 total (8 completed, 3 pending, 1 failed)",
                "Services: Overwatch (Overwatch), Database, Task Queue",
                "Operating mode: supervised",
            ],
        },
    }
    await agent.reason("hello", context=context)

    messages = llm.chat.call_args[0][0]
    system = messages[0].content
    assert "System state:" in system
    assert "Ollama (qwen2.5:14b)" in system
    assert "Tasks: 12 total" in system
    assert "Overwatch (Overwatch)" in system
    assert "supervised" in system


@pytest.mark.asyncio
async def test_without_org_context_backward_compatible():
    """Without _organizational_context, system message stays lean (backward compat)."""
    llm = _mock_llm()
    agent = _make_agent_with_codename(llm, codename="Forge")

    # No _organizational_context key at all
    context = {"_conversation_history": []}
    await agent.reason("hello", context=context)

    messages = llm.chat.call_args[0][0]
    system = messages[0].content
    assert "ag3ntwerk" not in system
    assert "Respond conversationally" not in system
    assert "peer agents" not in system
    # Should still have identity
    assert "Forge" in system
    assert "Forge" in system
