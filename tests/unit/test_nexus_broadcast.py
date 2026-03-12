"""Tests for Item 4: Nexus Broadcast to All Agents.

Covers Agent.receive_strategic_context(), _strategic_context default,
broadcast delivery, stale context overwrite, no-op on empty subordinates,
and error isolation during broadcast.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.core.base import Agent, Task, TaskResult
from ag3ntwerk.agents.overwatch.nexus_mixin import NexusMixin


# ---------------------------------------------------------------------------
# Concrete Agent subclass (Agent is abstract)
# ---------------------------------------------------------------------------


class ConcreteAgent(Agent):
    async def execute(self, task):
        return TaskResult(task_id=task.id, success=True)

    def can_handle(self, task):
        return True


# ---------------------------------------------------------------------------
# Lightweight broadcaster that mixes in NexusMixin
# ---------------------------------------------------------------------------


class MockCoS(NexusMixin):
    def __init__(self):
        self._subordinates = {}
        self._nexus_bridge = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(name: str = "test-agent") -> ConcreteAgent:
    return ConcreteAgent(code=name.upper(), name=name, domain="testing")


def _make_task(**kwargs) -> Task:
    defaults = {"description": "unit-test task", "priority": 1}
    defaults.update(kwargs)
    return Task(**defaults)


# ---------------------------------------------------------------------------
# 1. receive_strategic_context() stores context
# ---------------------------------------------------------------------------


class TestReceiveStrategicContext:
    async def test_stores_context(self):
        agent = _make_agent()
        ctx = {"quarter": "Q3", "priority": "growth"}
        agent.receive_strategic_context(ctx)
        assert agent._strategic_context == ctx

    # 2. _strategic_context defaults to empty dict
    async def test_default_is_empty_dict(self):
        agent = _make_agent()
        assert agent._strategic_context == {}

    # 5. Stale context handling – new context overwrites old
    async def test_new_context_overwrites_old(self):
        agent = _make_agent()
        agent.receive_strategic_context({"old_key": "old_value"})
        agent.receive_strategic_context({"new_key": "new_value"})
        assert agent._strategic_context == {"new_key": "new_value"}
        assert "old_key" not in agent._strategic_context


# ---------------------------------------------------------------------------
# Broadcast tests via MockCoS (NexusMixin._broadcast_nexus_context)
# ---------------------------------------------------------------------------


class TestBroadcastNexusContext:
    # 3. Broadcast reaches all agents
    async def test_broadcast_reaches_all_agents(self):
        cos = MockCoS()
        agents = [_make_agent(f"agent-{i}") for i in range(4)]
        for a in agents:
            cos._subordinates[a.name] = a

        ctx = {"directive": "cut costs", "horizon": "6mo"}
        cos._broadcast_nexus_context(ctx)

        for a in agents:
            assert a._strategic_context == ctx

    # 4. Context stored on each agent matches broadcast payload
    async def test_context_stored_matches_payload(self):
        cos = MockCoS()
        a1 = _make_agent("alpha")
        a2 = _make_agent("beta")
        cos._subordinates["alpha"] = a1
        cos._subordinates["beta"] = a2

        payload = {"market": "APAC", "focus": "retention"}
        cos._broadcast_nexus_context(payload)

        assert a1._strategic_context["market"] == "APAC"
        assert a2._strategic_context["focus"] == "retention"

    # 6. No-op when no agents registered
    async def test_noop_when_no_subordinates(self):
        cos = MockCoS()
        assert cos._subordinates == {}
        # Should not raise
        cos._broadcast_nexus_context({"anything": True})

    # 7. Error in one agent doesn't stop broadcast to others
    async def test_error_in_one_agent_does_not_block_others(self):
        cos = MockCoS()

        good_agent_1 = _make_agent("good-1")
        good_agent_2 = _make_agent("good-2")

        bad_agent = _make_agent("bad")
        # Make receive_strategic_context raise on the bad agent
        bad_agent.receive_strategic_context = MagicMock(side_effect=RuntimeError("boom"))

        cos._subordinates["good-1"] = good_agent_1
        cos._subordinates["bad"] = bad_agent
        cos._subordinates["good-2"] = good_agent_2

        ctx = {"resilience": "test"}
        # Broadcast should not raise even though bad_agent errors
        cos._broadcast_nexus_context(ctx)

        assert good_agent_1._strategic_context == ctx
        assert good_agent_2._strategic_context == ctx

    # Broadcast with empty context dict
    async def test_broadcast_empty_context(self):
        cos = MockCoS()
        agent = _make_agent("solo")
        cos._subordinates["solo"] = agent

        cos._broadcast_nexus_context({})
        assert agent._strategic_context == {}

    # Broadcast with nested context data
    async def test_broadcast_nested_context(self):
        cos = MockCoS()
        agent = _make_agent("nested")
        cos._subordinates["nested"] = agent

        ctx = {
            "goals": {"revenue": 1_000_000, "churn": 0.02},
            "tags": ["urgent", "board-level"],
        }
        cos._broadcast_nexus_context(ctx)
        assert agent._strategic_context["goals"]["revenue"] == 1_000_000
        assert "urgent" in agent._strategic_context["tags"]

    # Successive broadcasts each fully replace context
    async def test_successive_broadcasts_replace(self):
        cos = MockCoS()
        agent = _make_agent("replacer")
        cos._subordinates["replacer"] = agent

        cos._broadcast_nexus_context({"round": 1})
        assert agent._strategic_context == {"round": 1}

        cos._broadcast_nexus_context({"round": 2, "extra": True})
        assert agent._strategic_context == {"round": 2, "extra": True}
        assert "round" in agent._strategic_context
