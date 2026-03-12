"""
Unit tests for Nexus health-aware routing.

Tests the HealthAwareRouter and Nexus integration for:
- Agent health tracking
- Circuit breaker pattern
- Fallback routing
- Health score calculation
"""

import pytest


class TestAgentHealthStatus:
    """Test AgentHealthStatus dataclass."""

    def test_health_status_fields(self):
        """Verify AgentHealthStatus has required fields."""
        # AgentHealthStatus is now in models.py
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        fields = [
            "agent_code: str",
            "is_healthy: bool = True",
            "health_score: float = 1.0",
            "consecutive_failures: int = 0",
            "total_tasks: int = 0",
            "successful_tasks: int = 0",
            "avg_latency_ms: float = 0.0",
            "last_error: Optional[str] = None",
            "circuit_breaker_open: bool = False",
            "circuit_breaker_until: Optional[datetime] = None",
        ]
        for field in fields:
            assert field in content, f"Missing field: {field}"

    def test_success_rate_property(self):
        """Verify success_rate property calculation."""
        # AgentHealthStatus is now in models.py
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "def success_rate(self) -> float:" in content
        assert "self.successful_tasks / self.total_tasks" in content

    def test_is_available_property(self):
        """Verify is_available property logic."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "def is_available(self) -> bool:" in content
        assert "circuit_breaker_open" in content
        assert "circuit_breaker_until" in content


class TestHealthAwareRouter:
    """Test HealthAwareRouter class."""

    def test_router_class_exists(self):
        """Verify HealthAwareRouter class exists."""
        # HealthAwareRouter is now in health_router.py
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "class HealthAwareRouter:" in content

    def test_router_thresholds(self):
        """Verify router configuration thresholds."""
        # HealthAwareRouter is now in health_router.py
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "FAILURE_THRESHOLD = 3" in content
        assert "CIRCUIT_TIMEOUT_SECONDS = 60" in content
        assert "HEALTH_DECAY_FACTOR = 0.9" in content
        assert "HEALTH_RECOVERY_FACTOR = 1.05" in content

    def test_fallback_routes_defined(self):
        """Verify fallback routes are defined."""
        # FALLBACK_ROUTES is now in routing_rules.py
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/routing_rules.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "FALLBACK_ROUTES: Dict[str, List[str]]" in content
        assert '"security_scan": ["Citadel", "Sentinel", "Aegis"]' in content
        assert '"incident_response": ["Citadel", "Sentinel", "Aegis"]' in content
        assert '"code_review": ["Forge", "Foundry"]' in content

    def test_record_success_method(self):
        """Verify record_success method."""
        # HealthAwareRouter is now in health_router.py
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "def record_success(self, agent_code: str, latency_ms: float)" in content
        assert "health.successful_tasks += 1" in content
        assert "health.consecutive_failures = 0" in content
        assert (
            "health.health_score = min(1.0, health.health_score * self.HEALTH_RECOVERY_FACTOR)"
            in content
        )

    def test_record_failure_method(self):
        """Verify record_failure method."""
        # HealthAwareRouter is now in health_router.py
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "def record_failure(self, agent_code: str, error: str)" in content
        assert "health.consecutive_failures += 1" in content
        assert (
            "health.health_score = max(0.1, health.health_score * self.HEALTH_DECAY_FACTOR)"
            in content
        )

    def test_circuit_breaker_logic(self):
        """Verify circuit breaker opens on threshold."""
        # HealthAwareRouter is now in health_router.py
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "if health.consecutive_failures >= self.FAILURE_THRESHOLD:" in content
        assert "health.circuit_breaker_open = True" in content
        assert "health.is_healthy = False" in content

    def test_get_best_agent_method(self):
        """Verify get_best_agent method."""
        # HealthAwareRouter is now in health_router.py
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "def get_best_agent(" in content
        assert "task_type: str," in content
        assert "available_agents: Dict[str, Agent]" in content
        assert "-> Optional[Tuple[str, float]]:" in content

    def test_fallback_routing_logic(self):
        """Verify fallback routing when primary unhealthy."""
        # HealthAwareRouter is now in health_router.py
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "fallbacks = self._fallback_routes.get(task_type, [])" in content
        assert "Using fallback" in content
        assert "(primary {primary} unhealthy)" in content


class TestCOOHealthIntegration:
    """Test Nexus integration with health-aware routing."""

    def test_coo_init_has_health_routing(self):
        """Verify Nexus __init__ includes health routing."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "enable_health_routing: bool = True" in content
        assert "self._health_routing_enabled = enable_health_routing" in content
        assert "self._health_router = HealthAwareRouter()" in content

    def test_coo_tracks_task_timing(self):
        """Verify Nexus tracks task start times for latency."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "self._task_start_times: Dict[str, datetime] = {}" in content
        assert "self._task_start_times[task.id] = datetime.now(timezone.utc)" in content

    def test_coo_calculates_latency(self):
        """Verify latency calculation method."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "def _calculate_task_latency(self, task_id: str) -> float:" in content
        assert "delta.total_seconds() * 1000" in content

    def test_coo_records_success_on_completion(self):
        """Verify Nexus records success with latency."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "latency_ms = self._calculate_task_latency(task.id)" in content
        assert "self._health_router.record_success(target_agent, latency_ms)" in content

    def test_coo_records_failure(self):
        """Verify Nexus records failures."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "self._health_router.record_failure(" in content
        assert "target_agent, result.error" in content

    def test_coo_tracks_reroutes(self):
        """Verify Nexus tracks rerouted tasks."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert '"tasks_rerouted": 0' in content
        assert 'self._metrics["tasks_rerouted"] += 1' in content


class TestCOOHealthMethods:
    """Test Nexus health management methods."""

    def test_get_agent_health_method(self):
        """Verify get_agent_health method."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "def get_agent_health(self, agent_code: Optional[str] = None)" in content
        assert '"health_routing_enabled"' in content
        assert '"is_healthy"' in content
        assert '"health_score"' in content
        assert '"circuit_breaker_open"' in content

    def test_reset_agent_health_method(self):
        """Verify reset_agent_health method."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "def reset_agent_health(self, agent_code: Optional[str] = None)" in content
        assert "self._health_router.reset_health(agent_code)" in content

    def test_add_fallback_route_method(self):
        """Verify add_fallback_route method."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "def add_fallback_route(self, task_type: str, fallbacks: List[str])" in content
        assert "self._health_router.add_fallback_route(task_type, fallbacks)" in content

    def test_set_health_routing_enabled_method(self):
        """Verify set_health_routing_enabled method."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "def set_health_routing_enabled(self, enabled: bool)" in content
        assert "self._health_routing_enabled = enabled" in content


class TestRouteTaskHealthAware:
    """Test _route_task with health awareness."""

    def test_route_task_uses_health_router(self):
        """Verify _route_task uses health router when enabled."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "if self._health_routing_enabled and self._health_router:" in content
        assert "result = self._health_router.get_best_agent(" in content

    def test_route_task_logs_reroutes(self):
        """Verify reroutes are logged."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        # Check for reroute tracking and logging
        assert "Health-rerouted {task.task_type} from {static_route} to" in content
        assert "(health: {health_score:.2f})" in content

    def test_route_task_falls_back_to_standard(self):
        """Verify fallback to standard routing using ROUTING_RULES."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        # Static routing rules are used for fallback
        assert "static_route = ROUTING_RULES.get(task.task_type)" in content


class TestLatencyTracking:
    """Test latency tracking with exponential moving average."""

    def test_ema_latency_calculation(self):
        """Verify EMA for latency tracking."""
        # Latency tracking is now in health_router.py
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        # Initial latency assignment
        assert "health.avg_latency_ms = latency_ms" in content
        # EMA update
        assert "health.avg_latency_ms = 0.8 * health.avg_latency_ms + 0.2 * latency_ms" in content


class TestCircuitBreakerRecovery:
    """Test circuit breaker recovery behavior."""

    def test_circuit_closes_on_success(self):
        """Verify circuit breaker closes on successful request."""
        # Circuit breaker logic is now in health_router.py
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert "if health.circuit_breaker_open:" in content
        assert "health.circuit_breaker_open = False" in content
        assert "health.circuit_breaker_until = None" in content
        assert 'logger.info(f"Circuit breaker closed for {agent_code}")' in content

    def test_half_open_state(self):
        """Verify half-open state after timeout."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/agents/overwatch/agent.py", encoding="utf-8") as f:
            content = f.read()

        assert (
            "if self.circuit_breaker_until and datetime.now(timezone.utc) > self.circuit_breaker_until:"
            in content
        )
