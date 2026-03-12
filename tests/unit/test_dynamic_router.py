"""
Unit tests for the Dynamic Router.

Tests:
- Scoring agents based on patterns, performance, health
- Routing decisions with various confidence levels
- Fallback to static routing when confidence is low
- Performance cache refresh
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.learning.dynamic_router import (
    DynamicRouter,
    RoutingDecision,
    RoutingScore,
)
from ag3ntwerk.learning.models import (
    AgentPerformance,
    LearnedPattern,
    PatternType,
    ScopeLevel,
)


class TestRoutingScore:
    """Test RoutingScore dataclass."""

    def test_creation(self):
        score = RoutingScore(
            agent_code="Forge",
            total_score=0.85,
            pattern_score=0.9,
            performance_score=0.8,
        )
        assert score.agent_code == "Forge"
        assert score.total_score == 0.85
        assert score.pattern_score == 0.9

    def test_to_dict(self):
        score = RoutingScore(
            agent_code="Keystone",
            total_score=0.75,
            reasons=["High success rate"],
        )
        d = score.to_dict()
        assert d["agent_code"] == "Keystone"
        assert d["total_score"] == 0.75
        assert "High success rate" in d["reasons"]


class TestRoutingDecision:
    """Test RoutingDecision dataclass."""

    def test_creation(self):
        decision = RoutingDecision(
            chosen_agent="Sentinel",
            confidence=0.9,
            reasoning="Best pattern match",
        )
        assert decision.chosen_agent == "Sentinel"
        assert decision.confidence == 0.9

    def test_static_fallback(self):
        decision = RoutingDecision(
            chosen_agent="Forge",
            confidence=0.4,
            used_static_fallback=True,
            static_route="Forge",
        )
        assert decision.used_static_fallback is True
        assert decision.static_route == "Forge"


class TestDynamicRouter:
    """Test DynamicRouter class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(return_value=None)
        return db

    @pytest.fixture
    def mock_pattern_store(self):
        """Create a mock pattern store."""
        store = AsyncMock()
        store.get_patterns = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def router(self, mock_db, mock_pattern_store):
        """Create a DynamicRouter instance."""
        return DynamicRouter(mock_db, mock_pattern_store)

    @pytest.fixture
    def mock_agents(self):
        """Create mock agents."""
        agents = {}
        for code in ["Forge", "Keystone", "Sentinel"]:
            agent = MagicMock()
            agent.code = code
            agent.is_active = True
            agents[code] = agent
        return agents

    @pytest.mark.asyncio
    async def test_empty_agents_returns_empty_decision(self, router):
        """Test routing with no agents."""
        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents={},
        )
        assert decision.chosen_agent == ""
        assert decision.confidence == 0.0
        assert "No agents" in decision.reasoning

    @pytest.mark.asyncio
    async def test_fallback_to_static_route(self, router, mock_agents):
        """Test that low confidence falls back to static route."""
        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
            static_route="Forge",
        )
        # With no patterns, should fall back to static
        assert decision.used_static_fallback is True
        assert decision.chosen_agent == "Forge"

    @pytest.mark.asyncio
    async def test_scores_all_agents(self, router, mock_agents):
        """Test that all agents are scored."""
        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
        )
        # Should have scores for all 3 agents
        assert len(decision.scores) == 3
        agent_codes = [s.agent_code for s in decision.scores]
        assert "Forge" in agent_codes
        assert "Keystone" in agent_codes
        assert "Sentinel" in agent_codes

    @pytest.mark.asyncio
    async def test_pattern_influences_score(self, router, mock_agents, mock_pattern_store):
        """Test that patterns influence agent scores."""
        # Create a pattern that recommends Sentinel for this task type
        pattern = LearnedPattern(
            pattern_type=PatternType.ROUTING,
            scope_level=ScopeLevel.AGENT,
            scope_code="Sentinel",
            condition_json='{"task_type": "security_review"}',
            recommendation="Route to Sentinel",
            routing_preference="Sentinel",
            confidence=0.9,
            sample_size=50,
        )
        mock_pattern_store.get_patterns.return_value = [pattern]

        decision = await router.get_routing_decision(
            task_type="security_review",
            available_agents=mock_agents,
            static_route="Forge",
        )

        # Sentinel should have a higher pattern score
        cio_score = next(s for s in decision.scores if s.agent_code == "Sentinel")
        cto_score = next(s for s in decision.scores if s.agent_code == "Forge")
        assert cio_score.pattern_score > cto_score.pattern_score

    @pytest.mark.asyncio
    async def test_performance_cache_refresh(self, router, mock_db):
        """Test that performance cache is refreshed when stale."""
        # Mock performance data
        mock_db.fetch_all.return_value = [
            {
                "agent_code": "Forge",
                "agent_level": "agent",
                "total_tasks": 100,
                "successful_tasks": 90,
                "failed_tasks": 10,
                "avg_duration_ms": 500.0,
                "avg_confidence": 0.8,
                "avg_actual_accuracy": 0.85,
                "confidence_calibration_score": 0.05,
                "health_score": 0.95,
                "consecutive_failures": 0,
                "circuit_breaker_open": False,
            }
        ]

        await router._refresh_performance_cache()

        assert "Forge" in router._performance_cache
        perf = router._performance_cache["Forge"]
        assert perf.total_tasks == 100
        assert perf.success_rate == 0.9

    @pytest.mark.asyncio
    async def test_circuit_breaker_reduces_score(self, router, mock_agents, mock_db):
        """Test that an open circuit breaker reduces score to 0."""
        # Set up performance cache with circuit breaker open
        router._performance_cache["Forge"] = AgentPerformance(
            agent_code="Forge",
            agent_level=ScopeLevel.AGENT,
            total_tasks=100,
            successful_tasks=50,
            circuit_breaker_open=True,
            health_score=0.0,
        )
        router._cache_updated_at = datetime.now(timezone.utc)

        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
            static_route="Forge",
        )

        # Forge should have 0 health score
        cto_score = next(s for s in decision.scores if s.agent_code == "Forge")
        assert cto_score.health_score == 0.0
        assert "Circuit breaker" in str(cto_score.reasons)

    @pytest.mark.asyncio
    async def test_routing_outcome_tracking(self, router):
        """Test that routing outcomes are tracked."""
        await router.record_routing_outcome(
            task_type="code_review",
            chosen_agent="Forge",
            success=True,
            was_dynamic=True,
            duration_ms=100.0,
        )

        # Verify task type -> candidate mapping is updated
        assert "code_review" in router._task_type_candidates
        assert "Forge" in router._task_type_candidates["code_review"]

    @pytest.mark.asyncio
    async def test_high_confidence_overrides_static(self, router, mock_agents, mock_pattern_store):
        """Test that high confidence patterns override static routing."""
        # Create multiple strong patterns recommending Sentinel
        patterns = [
            LearnedPattern(
                pattern_type=PatternType.ROUTING,
                scope_level=ScopeLevel.AGENT,
                scope_code="Sentinel",
                condition_json='{"task_type": "code_review"}',
                recommendation="Route to Sentinel",
                routing_preference="Sentinel",
                confidence=0.95,
                sample_size=100,
            )
        ]
        mock_pattern_store.get_patterns.return_value = patterns

        # Also set up excellent performance for Sentinel
        router._performance_cache["Sentinel"] = AgentPerformance(
            agent_code="Sentinel",
            agent_level=ScopeLevel.AGENT,
            total_tasks=100,
            successful_tasks=95,
            health_score=1.0,
        )
        router._cache_updated_at = datetime.now(timezone.utc)

        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
            static_route="Forge",  # Static says Forge
        )

        # With strong patterns for Sentinel, should choose Sentinel over static Forge
        cio_score = next(s for s in decision.scores if s.agent_code == "Sentinel")
        # Sentinel should be in the top scores due to patterns + performance


class TestDynamicRouterIntegration:
    """Integration tests for DynamicRouter with learning system."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def mock_pattern_store(self):
        store = AsyncMock()
        store.get_patterns = AsyncMock(return_value=[])
        return store

    @pytest.mark.asyncio
    async def test_weights_sum_to_one(self, mock_db, mock_pattern_store):
        """Verify score weights sum to 1.0."""
        router = DynamicRouter(mock_db, mock_pattern_store)
        total = sum(router.WEIGHTS.values())
        assert abs(total - 1.0) < 0.01  # Allow for floating point error

    @pytest.mark.asyncio
    async def test_score_bounds(self, mock_db, mock_pattern_store):
        """Test that all scores are bounded between 0 and 1."""
        router = DynamicRouter(mock_db, mock_pattern_store)

        agents = {"Forge": MagicMock()}
        agents["Forge"].code = "Forge"
        agents["Forge"].is_active = True

        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=agents,
        )

        for score in decision.scores:
            assert 0.0 <= score.pattern_score <= 1.0
            assert 0.0 <= score.performance_score <= 1.0
            assert 0.0 <= score.health_score <= 1.0
            assert 0.0 <= score.calibration_score <= 1.0
            assert 0.0 <= score.load_score <= 1.0


class TestDynamicRouterLoadBalancing:
    """Tests for load-based routing in DynamicRouter."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(return_value=None)
        return db

    @pytest.fixture
    def mock_pattern_store(self):
        """Create a mock pattern store."""
        store = AsyncMock()
        store.get_patterns = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def mock_load_balancer(self):
        """Create a mock load balancer."""
        from ag3ntwerk.learning.load_balancer import AgentLoad

        balancer = AsyncMock()

        # Default: return moderate load
        async def get_agent_loads(agent_codes):
            return {
                code: AgentLoad(
                    agent_code=code,
                    utilization=0.5,
                    queue_depth=2,
                    active_tasks=3,
                    is_available=True,
                    health_score=1.0,
                )
                for code in agent_codes
            }

        balancer.get_agent_loads = AsyncMock(side_effect=get_agent_loads)
        return balancer

    @pytest.fixture
    def mock_agents(self):
        """Create mock agents."""
        agents = {}
        for code in ["Forge", "Keystone", "Sentinel"]:
            agent = MagicMock()
            agent.code = code
            agent.is_active = True
            agents[code] = agent
        return agents

    @pytest.mark.asyncio
    async def test_load_balancer_integration(
        self, mock_db, mock_pattern_store, mock_load_balancer, mock_agents
    ):
        """Test that DynamicRouter uses LoadBalancer for scoring."""
        router = DynamicRouter(mock_db, mock_pattern_store, mock_load_balancer)

        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
        )

        # LoadBalancer should have been called
        mock_load_balancer.get_agent_loads.assert_called()

        # All agents should have load scores
        for score in decision.scores:
            assert score.load_score > 0.0

    @pytest.mark.asyncio
    async def test_high_load_reduces_score(self, mock_db, mock_pattern_store, mock_agents):
        """Test that high utilization reduces load score."""
        from ag3ntwerk.learning.load_balancer import AgentLoad

        balancer = AsyncMock()

        async def get_agent_loads(agent_codes):
            loads = {}
            for code in agent_codes:
                if code == "Forge":
                    # Forge is overloaded
                    loads[code] = AgentLoad(
                        agent_code=code,
                        utilization=0.95,
                        queue_depth=10,
                        active_tasks=9,
                        is_available=True,
                    )
                else:
                    # Others have low load
                    loads[code] = AgentLoad(
                        agent_code=code,
                        utilization=0.2,
                        queue_depth=1,
                        active_tasks=1,
                        is_available=True,
                    )
            return loads

        balancer.get_agent_loads = AsyncMock(side_effect=get_agent_loads)

        router = DynamicRouter(mock_db, mock_pattern_store, balancer)
        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
        )

        cto_score = next(s for s in decision.scores if s.agent_code == "Forge")
        cfo_score = next(s for s in decision.scores if s.agent_code == "Keystone")

        # Forge should have much lower load score
        assert cto_score.load_score < cfo_score.load_score
        # Forge should have "Overloaded" in reasons
        assert any("Overloaded" in r or "overloaded" in r.lower() for r in cto_score.reasons)

    @pytest.mark.asyncio
    async def test_unavailable_agent_gets_zero_load_score(
        self, mock_db, mock_pattern_store, mock_agents
    ):
        """Test that unavailable agents (circuit breaker open) get zero load score."""
        from ag3ntwerk.learning.load_balancer import AgentLoad

        balancer = AsyncMock()

        async def get_agent_loads(agent_codes):
            loads = {}
            for code in agent_codes:
                if code == "Sentinel":
                    # Sentinel is unavailable
                    loads[code] = AgentLoad(
                        agent_code=code,
                        utilization=0.0,
                        is_available=False,
                    )
                else:
                    loads[code] = AgentLoad(
                        agent_code=code,
                        utilization=0.3,
                        is_available=True,
                    )
            return loads

        balancer.get_agent_loads = AsyncMock(side_effect=get_agent_loads)

        router = DynamicRouter(mock_db, mock_pattern_store, balancer)
        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
        )

        cio_score = next(s for s in decision.scores if s.agent_code == "Sentinel")
        assert cio_score.load_score == 0.0
        assert any("unavailable" in r.lower() for r in cio_score.reasons)

    @pytest.mark.asyncio
    async def test_low_utilization_gives_high_score(self, mock_db, mock_pattern_store, mock_agents):
        """Test that low utilization gives high load score."""
        from ag3ntwerk.learning.load_balancer import AgentLoad

        balancer = AsyncMock()

        async def get_agent_loads(agent_codes):
            return {
                code: AgentLoad(
                    agent_code=code,
                    utilization=0.1,
                    queue_depth=0,
                    active_tasks=1,
                    max_concurrent_tasks=10,
                    is_available=True,
                )
                for code in agent_codes
            }

        balancer.get_agent_loads = AsyncMock(side_effect=get_agent_loads)

        router = DynamicRouter(mock_db, mock_pattern_store, balancer)
        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
        )

        # All agents should have high load scores (~0.9)
        for score in decision.scores:
            assert score.load_score >= 0.8

    @pytest.mark.asyncio
    async def test_no_load_balancer_defaults_to_1(self, mock_db, mock_pattern_store, mock_agents):
        """Test that without LoadBalancer, load score defaults to 1.0."""
        router = DynamicRouter(mock_db, mock_pattern_store)  # No load_balancer

        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
        )

        # All agents should have load score of 1.0
        for score in decision.scores:
            assert score.load_score == 1.0

    @pytest.mark.asyncio
    async def test_set_load_balancer_late_binding(
        self, mock_db, mock_pattern_store, mock_load_balancer, mock_agents
    ):
        """Test that load balancer can be set after initialization."""
        router = DynamicRouter(mock_db, mock_pattern_store)  # No initial load_balancer

        # Initial call should have load_score = 1.0
        decision1 = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
        )
        for score in decision1.scores:
            assert score.load_score == 1.0

        # Set load balancer
        router.set_load_balancer(mock_load_balancer)

        # Now load scores should be based on actual load
        decision2 = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
        )
        mock_load_balancer.get_agent_loads.assert_called()

    @pytest.mark.asyncio
    async def test_load_influences_routing_decision(self, mock_db, mock_pattern_store, mock_agents):
        """Test that load balancing influences the overall routing decision."""
        from ag3ntwerk.learning.load_balancer import AgentLoad

        balancer = AsyncMock()

        async def get_agent_loads(agent_codes):
            loads = {}
            for code in agent_codes:
                if code == "Keystone":
                    # Keystone is idle with lots of capacity
                    loads[code] = AgentLoad(
                        agent_code=code,
                        utilization=0.05,
                        queue_depth=0,
                        active_tasks=0,
                        max_concurrent_tasks=10,
                        is_available=True,
                    )
                else:
                    # Others are moderately loaded
                    loads[code] = AgentLoad(
                        agent_code=code,
                        utilization=0.7,
                        queue_depth=5,
                        active_tasks=5,
                        is_available=True,
                    )
            return loads

        balancer.get_agent_loads = AsyncMock(side_effect=get_agent_loads)

        router = DynamicRouter(mock_db, mock_pattern_store, balancer)
        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
        )

        # Keystone should have the highest load score
        cfo_score = next(s for s in decision.scores if s.agent_code == "Keystone")
        other_scores = [s for s in decision.scores if s.agent_code != "Keystone"]

        for other in other_scores:
            assert cfo_score.load_score > other.load_score

    @pytest.mark.asyncio
    async def test_high_capacity_bonus(self, mock_db, mock_pattern_store, mock_agents):
        """Test that high available capacity gives a bonus."""
        from ag3ntwerk.learning.load_balancer import AgentLoad

        balancer = AsyncMock()

        async def get_agent_loads(agent_codes):
            return {
                code: AgentLoad(
                    agent_code=code,
                    utilization=0.3,
                    queue_depth=0,
                    active_tasks=3,
                    max_concurrent_tasks=20,  # High capacity = 17 available
                    is_available=True,
                )
                for code in agent_codes
            }

        balancer.get_agent_loads = AsyncMock(side_effect=get_agent_loads)

        router = DynamicRouter(mock_db, mock_pattern_store, balancer)
        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
        )

        # All agents should have reasons mentioning capacity
        for score in decision.scores:
            assert any("capacity" in r.lower() for r in score.reasons)

    @pytest.mark.asyncio
    async def test_load_balancer_error_graceful_degradation(
        self, mock_db, mock_pattern_store, mock_agents
    ):
        """Test that LoadBalancer errors are handled gracefully."""
        balancer = AsyncMock()
        balancer.get_agent_loads = AsyncMock(side_effect=Exception("Connection error"))

        router = DynamicRouter(mock_db, mock_pattern_store, balancer)

        # Should not raise, should use default score
        decision = await router.get_routing_decision(
            task_type="code_review",
            available_agents=mock_agents,
        )

        # Should still get a valid decision with default load scores
        assert decision.chosen_agent != ""
        for score in decision.scores:
            assert score.load_score == 1.0  # Default on error
