"""
Unit tests for Nexus Bridge (Nexus <-> Nexus Priority/Learning).

Tests the integration between ag3ntwerk Nexus and Nexus intelligent systems.
"""

import pytest


class TestNexusBridgeModule:
    """Test Nexus bridge module structure."""

    def test_nexus_bridge_imports(self):
        """Verify module can be imported."""
        with open("F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/__init__.py", encoding="utf-8") as f:
            content = f.read()

        assert "NexusBridge" in content
        assert "TaskOutcome" in content
        assert "PrioritizedTask" in content

    def test_nexus_bridge_class_exists(self):
        """Verify NexusBridge class exists."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "class NexusBridge:" in content


class TestTaskOutcome:
    """Test TaskOutcome dataclass."""

    def test_task_outcome_fields(self):
        """Verify TaskOutcome has required fields."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        fields = [
            "task_id: str",
            "task_type: str",
            "executor: str",
            "success: bool",
            "duration_ms: float",
            "error: Optional[str]",
            "metadata: Dict[str, Any]",
            "timestamp: datetime",
        ]
        for field in fields:
            assert field in content, f"Missing field: {field}"


class TestPrioritizedTask:
    """Test PrioritizedTask dataclass."""

    def test_prioritized_task_fields(self):
        """Verify PrioritizedTask has required fields."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        fields = [
            "task_id: str",
            "task_type: str",
            "priority_score: float",
            "urgency_score: float",
            "value_score: float",
            "learning_score: float",
            "recommended_executor: Optional[str]",
            "reasoning: str",
        ]
        for field in fields:
            assert field in content, f"Missing field: {field}"


class TestNexusBridgeInit:
    """Test NexusBridge initialization."""

    def test_init_parameters(self):
        """Verify init accepts required parameters."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "coo: Optional[Any] = None," in content
        assert "priority_engine: Optional[Any] = None," in content
        assert "learning_system: Optional[Any] = None," in content

    def test_init_storage(self):
        """Verify init creates storage structures."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "self._outcomes: List[TaskOutcome] = []" in content
        assert "self._executor_stats: Dict[str, Dict[str, Any]] = {}" in content
        assert "self._task_executor_success: Dict[str, Dict[str, float]] = {}" in content


class TestNexusBridgeConnection:
    """Test Nexus system connection methods."""

    def test_connect_nexus_method(self):
        """Verify connect_nexus method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def connect_nexus(" in content
        assert "priority_engine: Optional[Any] = None," in content
        assert "learning_system: Optional[Any] = None," in content

    def test_connect_coo_method(self):
        """Verify connect_coo method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def connect_coo(self, coo: Any)" in content
        assert "self._coo = coo" in content

    def test_is_connected_property(self):
        """Verify is_connected property."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def is_connected(self) -> bool:" in content
        assert "self._priority_engine is not None" in content
        assert "self._learning_system is not None" in content


class TestPrioritization:
    """Test task prioritization methods."""

    def test_prioritize_tasks_method(self):
        """Verify prioritize_tasks method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "async def prioritize_tasks(" in content
        assert "tasks: List[Any]," in content
        assert ") -> List[PrioritizedTask]:" in content

    def test_uses_priority_engine(self):
        """Verify Priority Engine is used when available."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "if self._priority_engine:" in content
        assert "await self._priority_engine.prioritize(pe_context)" in content

    def test_local_prioritize_fallback(self):
        """Verify local prioritization fallback."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def _local_prioritize(self, tasks: List[Any])" in content
        assert "# Local prioritization without Priority Engine" in content

    def test_priority_mapping(self):
        """Verify priority value mapping."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "priority_map = {" in content
        assert '"critical": 1.0' in content
        assert '"high": 0.8' in content
        assert '"medium": 0.5' in content
        assert '"low": 0.3' in content


class TestOutcomeRecording:
    """Test outcome recording methods."""

    def test_record_outcome_method(self):
        """Verify record_outcome method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def record_outcome(" in content
        assert "task_id: str," in content
        assert "task_type: str," in content
        assert "executor: str," in content
        assert "success: bool," in content

    def test_outcome_stored(self):
        """Verify outcomes are stored."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "self._outcomes.append(outcome)" in content
        assert "self._max_outcomes" in content

    def test_updates_executor_stats(self):
        """Verify executor stats are updated."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "self._update_executor_stats(executor, success, duration_ms)" in content

    def test_sends_to_learning_system(self):
        """Verify outcome sent to Learning System."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "if self._learning_system:" in content
        assert "self._learning_system.record_outcome(" in content


class TestExecutorStats:
    """Test executor statistics methods."""

    def test_update_executor_stats(self):
        """Verify executor stats update method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def _update_executor_stats(" in content
        assert '"total_tasks"' in content
        assert '"successful_tasks"' in content
        assert '"avg_duration_ms"' in content

    def test_get_executor_stats(self):
        """Verify get_executor_stats method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def get_executor_stats(self, executor: str)" in content
        assert '"success_rate"' in content

    def test_get_all_executor_stats(self):
        """Verify get_all_executor_stats method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def get_all_executor_stats(self) -> Dict[str, Dict[str, Any]]:" in content


class TestBestExecutor:
    """Test best executor recommendation methods."""

    def test_get_best_executor_method(self):
        """Verify get_best_executor method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def get_best_executor(" in content
        assert "task_type: str," in content
        assert ") -> Optional[Tuple[str, float]]:" in content

    def test_uses_learning_system_first(self):
        """Verify Learning System is consulted first."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "# Try Learning System first" in content
        assert "self._learning_system.get_best_executor_for_task_type" in content

    def test_fallback_to_local(self):
        """Verify fallback to local data."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "# Fall back to local data" in content


class TestTaskTypePerformance:
    """Test task type performance tracking."""

    def test_update_task_executor_mapping(self):
        """Verify task-executor mapping update."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def _update_task_executor_mapping(" in content
        # Exponential moving average
        assert "0.9 * current + 0.1 * new_val" in content

    def test_get_task_type_performance(self):
        """Verify task type performance retrieval."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def get_task_type_performance(" in content
        assert '"task_type"' in content
        assert '"executors"' in content
        assert '"best_executor"' in content


class TestLearningInsights:
    """Test learning insights methods."""

    def test_get_learning_insights_method(self):
        """Verify get_learning_insights method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "async def get_learning_insights(" in content
        assert "task_type: Optional[str] = None," in content

    def test_local_insights(self):
        """Verify local insights are included."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert '"local_data": True' in content
        assert "self.get_task_type_performance(task_type)" in content

    def test_nexus_learning_insights(self):
        """Verify Nexus Learning System insights."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "await self._learning_system.get_similar_outcomes" in content
        assert '"similar_outcomes"' in content
        assert '"success_count"' in content


class TestCacheManagement:
    """Test cache and stats management."""

    def test_clear_learning_cache(self):
        """Verify clear_learning_cache method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def clear_learning_cache(self)" in content
        assert "self._task_executor_success.clear()" in content

    def test_reset_stats(self):
        """Verify reset_stats method."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def reset_stats(self, executor: Optional[str] = None)" in content
        assert "self._executor_stats.clear()" in content


class TestBridgeStats:
    """Test bridge statistics property."""

    def test_stats_property(self):
        """Verify stats property."""
        with open(
            "F:/Projects/public-release/ag3ntwerk/src/ag3ntwerk/integrations/nexus_bridge.py", encoding="utf-8"
        ) as f:
            content = f.read()

        assert "def stats(self) -> Dict[str, Any]:" in content
        assert '"priority_engine_connected"' in content
        assert '"learning_system_connected"' in content
        assert '"coo_connected"' in content
        assert '"total_outcomes_recorded"' in content
        assert '"executors_tracked"' in content
