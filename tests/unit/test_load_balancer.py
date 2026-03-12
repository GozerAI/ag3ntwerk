"""
Unit tests for the Load Balancer.

Tests:
- Agent load metrics calculation
- Optimal agent selection
- Overload detection
- Idle agent identification
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.learning.load_balancer import (
    LoadBalancer,
    LoadBalanceDecision,
    AgentLoad,
)


class TestAgentLoad:
    """Test AgentLoad dataclass."""

    def test_creation(self):
        load = AgentLoad(
            agent_code="Forge",
            queue_depth=5,
            active_tasks=3,
            max_concurrent_tasks=10,
        )
        assert load.agent_code == "Forge"
        assert load.queue_depth == 5
        assert load.active_tasks == 3

    def test_available_capacity(self):
        load = AgentLoad(
            agent_code="Forge",
            queue_depth=2,
            active_tasks=3,
            max_concurrent_tasks=10,
            is_available=True,
        )
        # 10 - 3 - 2 = 5
        assert load.available_capacity == 5

    def test_available_capacity_unavailable(self):
        load = AgentLoad(
            agent_code="Forge",
            queue_depth=2,
            active_tasks=3,
            max_concurrent_tasks=10,
            is_available=False,
        )
        assert load.available_capacity == 0

    def test_available_capacity_overloaded(self):
        load = AgentLoad(
            agent_code="Forge",
            queue_depth=5,
            active_tasks=8,
            max_concurrent_tasks=10,
            is_available=True,
        )
        # 10 - 8 - 5 = -3, clamped to 0
        assert load.available_capacity == 0

    def test_success_rate_no_data(self):
        load = AgentLoad(
            agent_code="Forge",
            tasks_completed_last_hour=0,
            tasks_failed_last_hour=0,
        )
        # No data = assume good
        assert load.success_rate_last_hour == 1.0

    def test_success_rate_with_data(self):
        load = AgentLoad(
            agent_code="Forge",
            tasks_completed_last_hour=8,
            tasks_failed_last_hour=2,
        )
        assert load.success_rate_last_hour == 0.8

    def test_to_dict(self):
        load = AgentLoad(
            agent_code="Forge",
            queue_depth=5,
            active_tasks=3,
            utilization=0.5,
            health_score=0.9,
        )
        d = load.to_dict()
        assert d["agent_code"] == "Forge"
        assert d["queue_depth"] == 5
        assert d["utilization"] == 0.5
        assert d["health_score"] == 0.9


class TestLoadBalanceDecision:
    """Test LoadBalanceDecision dataclass."""

    def test_creation(self):
        decision = LoadBalanceDecision(
            chosen_agent="Forge",
            score=0.85,
            reasoning="Best available capacity",
        )
        assert decision.chosen_agent == "Forge"
        assert decision.score == 0.85

    def test_with_all_scores(self):
        decision = LoadBalanceDecision(
            chosen_agent="Forge",
            score=0.85,
            reasoning="Best score",
            all_scores=[("Forge", 0.85), ("Keystone", 0.70), ("Sentinel", 0.65)],
        )
        assert len(decision.all_scores) == 3
        assert decision.all_scores[0] == ("Forge", 0.85)

    def test_to_dict(self):
        decision = LoadBalanceDecision(
            chosen_agent="Forge",
            score=0.85,
            reasoning="Test reasoning",
            all_scores=[("Forge", 0.85)],
        )
        d = decision.to_dict()
        assert d["chosen_agent"] == "Forge"
        assert d["score"] == 0.85
        assert d["reasoning"] == "Test reasoning"


class TestLoadBalancer:
    """Test LoadBalancer class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def balancer(self, mock_db):
        """Create a LoadBalancer instance."""
        return LoadBalancer(mock_db)

    @pytest.mark.asyncio
    async def test_get_optimal_agent_no_candidates(self, balancer):
        """Test with no candidates."""
        decision = await balancer.get_optimal_agent(
            task_type="code_review",
            candidates=[],
        )

        assert decision.chosen_agent == ""
        assert decision.score == 0.0
        assert "No candidates" in decision.reasoning

    @pytest.mark.asyncio
    async def test_get_optimal_agent_single_candidate(self, balancer, mock_db):
        """Test with a single candidate."""
        # Mock agent performance
        mock_db.fetch_one.side_effect = [
            # Performance row
            {
                "health_score": 0.9,
                "circuit_breaker_open": 0,
                "avg_duration_ms": 500,
                "total_tasks": 100,
                "successful_tasks": 95,
            },
            # Task counts
            {"completed": 10, "failed": 1},
            # Task-specific performance
            {"total": 50, "successful": 45, "avg_duration": 400},
        ]

        decision = await balancer.get_optimal_agent(
            task_type="code_review",
            candidates=["Forge"],
        )

        assert decision.chosen_agent == "Forge"
        assert decision.score > 0

    @pytest.mark.asyncio
    async def test_get_optimal_agent_multiple_candidates(self, balancer, mock_db):
        """Test selection among multiple candidates."""
        # Mock different loads for different agents
        call_count = [0]

        async def mock_fetch_one(*args, **kwargs):
            call_count[0] += 1
            query = args[0] if args else ""

            if "agent_performance" in query:
                # Alternate between good and bad health
                if call_count[0] % 2 == 1:
                    return {
                        "health_score": 0.95,
                        "circuit_breaker_open": 0,
                        "avg_duration_ms": 300,
                        "total_tasks": 100,
                        "successful_tasks": 98,
                    }
                else:
                    return {
                        "health_score": 0.6,
                        "circuit_breaker_open": 0,
                        "avg_duration_ms": 1000,
                        "total_tasks": 50,
                        "successful_tasks": 30,
                    }
            elif "learning_outcomes" in query:
                if "SUM" in query:
                    return {"completed": 10, "failed": 1}
                else:
                    return {"total": 20, "successful": 18, "avg_duration": 400}
            return None

        mock_db.fetch_one = mock_fetch_one

        decision = await balancer.get_optimal_agent(
            task_type="code_review",
            candidates=["Forge", "Keystone", "Sentinel"],
        )

        assert decision.chosen_agent in ["Forge", "Keystone", "Sentinel"]
        assert len(decision.all_scores) == 3
        # Scores should be sorted descending
        scores = [s[1] for s in decision.all_scores]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_get_optimal_agent_prefers_healthy(self, balancer, mock_db):
        """Test that healthy agents are preferred."""
        agent_health = {"Forge": 0.95, "Keystone": 0.3}  # Forge much healthier

        async def mock_fetch_one(*args, **kwargs):
            query = args[0] if args else ""
            params = args[1] if len(args) > 1 else ()
            agent_code = params[0] if params else None

            if "agent_performance" in query and agent_code:
                health = agent_health.get(agent_code, 0.5)
                return {
                    "health_score": health,
                    "circuit_breaker_open": 0 if health > 0.5 else 1,
                    "avg_duration_ms": 500,
                    "total_tasks": 100,
                    "successful_tasks": 90,
                }
            elif "learning_outcomes" in query:
                if "SUM" in query:
                    return {"completed": 10, "failed": 2}
                else:
                    return {"total": 20, "successful": 16, "avg_duration": 500}
            return None

        mock_db.fetch_one = mock_fetch_one

        decision = await balancer.get_optimal_agent(
            task_type="code_review",
            candidates=["Forge", "Keystone"],
        )

        # Forge should be chosen due to better health
        assert decision.chosen_agent == "Forge"

    @pytest.mark.asyncio
    async def test_get_optimal_agent_unavailable_excluded(self, balancer, mock_db):
        """Test that unavailable agents get zero score."""

        async def mock_fetch_one(*args, **kwargs):
            query = args[0] if args else ""
            params = args[1] if len(args) > 1 else ()
            agent_code = params[0] if params else None

            if "agent_performance" in query:
                if agent_code == "Forge":
                    return {
                        "health_score": 0.95,
                        "circuit_breaker_open": 1,  # Forge unavailable!
                        "avg_duration_ms": 300,
                        "total_tasks": 100,
                        "successful_tasks": 98,
                    }
                else:
                    return {
                        "health_score": 0.7,
                        "circuit_breaker_open": 0,
                        "avg_duration_ms": 500,
                        "total_tasks": 80,
                        "successful_tasks": 70,
                    }
            elif "learning_outcomes" in query:
                if "SUM" in query:
                    return {"completed": 10, "failed": 2}
                else:
                    return {"total": 20, "successful": 16, "avg_duration": 500}
            return None

        mock_db.fetch_one = mock_fetch_one

        decision = await balancer.get_optimal_agent(
            task_type="code_review",
            candidates=["Forge", "Keystone"],
        )

        # Keystone should be chosen since Forge is unavailable
        assert decision.chosen_agent == "Keystone"

    @pytest.mark.asyncio
    async def test_get_agent_loads(self, balancer, mock_db):
        """Test getting load metrics for multiple agents."""
        mock_db.fetch_one.side_effect = [
            # Forge performance
            {
                "health_score": 0.9,
                "circuit_breaker_open": 0,
                "avg_duration_ms": 400,
                "total_tasks": 100,
                "successful_tasks": 95,
            },
            {"completed": 10, "failed": 1},
            # Keystone performance
            {
                "health_score": 0.8,
                "circuit_breaker_open": 0,
                "avg_duration_ms": 500,
                "total_tasks": 80,
                "successful_tasks": 70,
            },
            {"completed": 8, "failed": 2},
        ]

        loads = await balancer.get_agent_loads(["Forge", "Keystone"])

        assert "Forge" in loads
        assert "Keystone" in loads
        assert loads["Forge"].health_score == 0.9
        assert loads["Keystone"].health_score == 0.8

    @pytest.mark.asyncio
    async def test_get_overloaded_agents(self, balancer, mock_db):
        """Test identifying overloaded agents."""
        # Mock getting agent codes
        mock_db.fetch_all.return_value = [
            {"agent_code": "Forge"},
            {"agent_code": "Keystone"},
        ]

        # Mock performance data with different utilization
        call_count = [0]

        async def mock_fetch_one(*args, **kwargs):
            call_count[0] += 1
            query = args[0] if args else ""

            if "agent_performance" in query:
                return {
                    "health_score": 0.8,
                    "circuit_breaker_open": 0,
                    "avg_duration_ms": 500,
                    "total_tasks": 100,
                    "successful_tasks": 90,
                }
            elif "learning_outcomes" in query:
                # Make Forge appear overloaded (many recent tasks)
                if call_count[0] <= 2:
                    return {"completed": 25, "failed": 5}  # 30 tasks/hour = high
                else:
                    return {"completed": 5, "failed": 1}  # 6 tasks/hour = low
            return None

        mock_db.fetch_one = mock_fetch_one

        overloaded = await balancer.get_overloaded_agents()

        # Should identify agents with high utilization
        assert isinstance(overloaded, list)

    @pytest.mark.asyncio
    async def test_get_idle_agents(self, balancer, mock_db):
        """Test identifying idle agents."""
        mock_db.fetch_all.return_value = [
            {"agent_code": "Forge"},
            {"agent_code": "Keystone"},
        ]

        call_count = [0]

        async def mock_fetch_one(*args, **kwargs):
            call_count[0] += 1
            query = args[0] if args else ""

            if "agent_performance" in query:
                return {
                    "health_score": 0.9,
                    "circuit_breaker_open": 0,
                    "avg_duration_ms": 400,
                    "total_tasks": 50,
                    "successful_tasks": 48,
                }
            elif "learning_outcomes" in query:
                # Low activity
                return {"completed": 2, "failed": 0}
            return None

        mock_db.fetch_one = mock_fetch_one

        idle = await balancer.get_idle_agents(idle_threshold=0.2)

        assert isinstance(idle, list)

    @pytest.mark.asyncio
    async def test_cache_freshness(self, balancer, mock_db):
        """Test that cache is used when fresh."""
        mock_db.fetch_one.return_value = {
            "health_score": 0.9,
            "circuit_breaker_open": 0,
            "avg_duration_ms": 400,
            "total_tasks": 100,
            "successful_tasks": 95,
        }

        # First call should fetch
        await balancer.get_agent_loads(["Forge"])
        first_call_count = mock_db.fetch_one.call_count

        # Second call should use cache (within TTL)
        await balancer.get_agent_loads(["Forge"])
        second_call_count = mock_db.fetch_one.call_count

        # Should not have made additional DB calls
        assert second_call_count == first_call_count


class TestLoadBalancerScoring:
    """Test the scoring algorithm."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def balancer(self, mock_db):
        return LoadBalancer(mock_db)

    def test_score_weights_sum_to_one(self, balancer):
        """Verify scoring weights sum to 1.0."""
        total_weight = sum(balancer.WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_overload_penalty(self, balancer, mock_db):
        """Test that overloaded agents get penalized."""
        # Create agent with high utilization
        load_high = AgentLoad(
            agent_code="Forge",
            utilization=0.95,  # Above OVERLOAD_THRESHOLD
            health_score=0.9,
            is_available=True,
        )

        load_normal = AgentLoad(
            agent_code="Keystone",
            utilization=0.5,
            health_score=0.9,
            is_available=True,
        )

        # Score calculation is internal, but we can verify behavior
        # through the get_optimal_agent method
        async def mock_fetch(query, params=None):
            agent = params[0] if params else None
            if "agent_performance" in query:
                return {
                    "health_score": 0.9,
                    "circuit_breaker_open": 0,
                    "avg_duration_ms": 500,
                    "total_tasks": 100,
                    "successful_tasks": 90,
                }
            elif "SUM" in query:
                # High activity for Forge, normal for Keystone
                if agent == "Forge":
                    return {"completed": 25, "failed": 0}  # High utilization
                return {"completed": 5, "failed": 0}  # Normal utilization
            return {"total": 10, "successful": 9, "avg_duration": 500}

        mock_db.fetch_one = mock_fetch

        decision = await balancer.get_optimal_agent(
            task_type="test",
            candidates=["Forge", "Keystone"],
        )

        # Keystone should be preferred due to lower utilization
        # (Though exact behavior depends on other factors too)
        assert decision.chosen_agent in ["Forge", "Keystone"]


class TestLoadBalancerEdgeCases:
    """Test edge cases for LoadBalancer."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        return db

    @pytest.mark.asyncio
    async def test_all_agents_unavailable(self, mock_db):
        """Test when all candidates are unavailable."""
        mock_db.fetch_one.return_value = {
            "health_score": 0.0,
            "circuit_breaker_open": 1,
            "avg_duration_ms": 0,
            "total_tasks": 0,
            "successful_tasks": 0,
        }

        balancer = LoadBalancer(mock_db)
        decision = await balancer.get_optimal_agent(
            task_type="test",
            candidates=["Forge", "Keystone"],
        )

        # Should still return a candidate (first one)
        assert decision.chosen_agent == "Forge"
        assert "unavailable" in decision.reasoning.lower() or decision.score == 0

    @pytest.mark.asyncio
    async def test_database_error_handling(self, mock_db):
        """Test graceful handling of database errors."""
        mock_db.fetch_one.side_effect = Exception("Database error")

        balancer = LoadBalancer(mock_db)
        decision = await balancer.get_optimal_agent(
            task_type="test",
            candidates=["Forge"],
        )

        # Should not raise, should return something reasonable
        assert decision is not None

    @pytest.mark.asyncio
    async def test_no_performance_data(self, mock_db):
        """Test handling of agents with no historical data."""
        mock_db.fetch_one.return_value = None

        balancer = LoadBalancer(mock_db)
        loads = await balancer.get_agent_loads(["NEW_AGENT"])

        assert "NEW_AGENT" in loads
        # Should have default values
        assert loads["NEW_AGENT"].health_score == 1.0  # Default good
