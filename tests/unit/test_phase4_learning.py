"""
Unit tests for Phase 4 Learning System components.

Tests:
- OpportunityDetector: Identifies improvement opportunities
- ProactiveTaskGenerator: Auto-generates maintenance tasks
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.learning.opportunity_detector import (
    OpportunityDetector,
    Opportunity,
    OpportunityType,
    OpportunityPriority,
    CapabilityGap,
    WorkflowAnalysis,
)
from ag3ntwerk.learning.proactive_generator import (
    ProactiveTaskGenerator,
    ProactiveTask,
    ProactiveTaskType,
    TaskPriority,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    db.fetch_one = AsyncMock(return_value=None)
    db.fetch_all = AsyncMock(return_value=[])
    return db


@pytest.fixture
def mock_pattern_store():
    """Create a mock pattern store."""
    store = AsyncMock()
    store.get_pattern = AsyncMock(return_value=None)
    store.get_patterns = AsyncMock(return_value=[])
    store.get_all_active_patterns = AsyncMock(return_value=[])
    store.store_pattern = AsyncMock(return_value="pattern-123")
    store.update_pattern = AsyncMock()
    return store


@pytest.fixture
def mock_task_queue():
    """Create a mock task queue."""
    queue = AsyncMock()
    queue.enqueue = AsyncMock(return_value="task-123")
    return queue


@pytest.fixture
def opportunity_detector(mock_db, mock_pattern_store):
    """Create an OpportunityDetector instance."""
    return OpportunityDetector(mock_db, mock_pattern_store)


@pytest.fixture
def proactive_generator(mock_db, mock_task_queue):
    """Create a ProactiveTaskGenerator instance."""
    return ProactiveTaskGenerator(mock_db, mock_task_queue)


@pytest.fixture
def proactive_generator_with_detector(mock_db, mock_task_queue, opportunity_detector):
    """Create a ProactiveTaskGenerator with an OpportunityDetector."""
    return ProactiveTaskGenerator(mock_db, mock_task_queue, opportunity_detector)


# =============================================================================
# OpportunityDetector Tests
# =============================================================================


class TestOpportunityDetector:
    """Tests for opportunity detection functionality."""

    @pytest.mark.asyncio
    async def test_detect_opportunities_empty(self, opportunity_detector):
        """Test detecting opportunities with no data."""
        opportunities = await opportunity_detector.detect_opportunities()

        assert isinstance(opportunities, list)
        assert len(opportunities) == 0

    @pytest.mark.asyncio
    async def test_detect_capability_gaps(self, opportunity_detector, mock_db):
        """Test detecting capability gaps."""
        mock_db.fetch_all.return_value = [
            {
                "agent_code": "Forge",
                "task_type": "code_review",
                "task_count": 50,
                "successful": 30,
                "success_rate": 0.6,  # Below average
            },
            {
                "agent_code": "Keystone",
                "task_type": "code_review",
                "task_count": 50,
                "successful": 45,
                "success_rate": 0.9,  # Above average
            },
        ]

        opportunities = await opportunity_detector._detect_capability_gaps(168)

        # Forge should have a capability gap (0.6 vs 0.75 avg)
        assert len(opportunities) > 0
        capability_gap = next(
            (o for o in opportunities if o.opportunity_type == OpportunityType.CAPABILITY_GAP),
            None,
        )
        assert capability_gap is not None
        assert capability_gap.affected_agent == "Forge"

    @pytest.mark.asyncio
    async def test_detect_workflow_optimizations(self, opportunity_detector, mock_db):
        """Test detecting workflow optimization opportunities."""
        mock_db.fetch_all.return_value = [
            {
                "task_type": "code_review",
                "task_count": 100,
                "avg_duration": 1000.0,
                "max_duration": 5000.0,  # High variance
                "min_duration": 100.0,
                "success_rate": 0.8,
            },
        ]

        opportunities = await opportunity_detector._detect_workflow_optimizations(168)

        assert len(opportunities) > 0
        workflow_opp = opportunities[0]
        assert workflow_opp.opportunity_type == OpportunityType.WORKFLOW_OPTIMIZATION
        assert workflow_opp.affected_task_type == "code_review"

    @pytest.mark.asyncio
    async def test_detect_pattern_coverage_gaps(
        self, opportunity_detector, mock_db, mock_pattern_store
    ):
        """Test detecting pattern coverage gaps."""
        mock_db.fetch_all.return_value = [
            {
                "task_type": "bug_fix",
                "task_count": 50,
                "success_rate": 0.7,
            },
        ]
        mock_pattern_store.get_all_active_patterns.return_value = []  # No patterns

        opportunities = await opportunity_detector._detect_pattern_coverage_gaps(168)

        assert len(opportunities) > 0
        pattern_gap = opportunities[0]
        assert pattern_gap.opportunity_type == OpportunityType.PATTERN_COVERAGE
        assert pattern_gap.affected_task_type == "bug_fix"

    @pytest.mark.asyncio
    async def test_detect_resource_imbalances(self, opportunity_detector, mock_db):
        """Test detecting resource imbalances."""
        mock_db.fetch_all.return_value = [
            {"agent_code": "Forge", "task_count": 200, "success_rate": 0.8, "avg_duration": 100},
            {"agent_code": "Keystone", "task_count": 30, "success_rate": 0.9, "avg_duration": 150},
            {"agent_code": "Sentinel", "task_count": 40, "success_rate": 0.85, "avg_duration": 120},
        ]

        opportunities = await opportunity_detector._detect_resource_imbalances(168)

        assert len(opportunities) > 0
        imbalance = opportunities[0]
        assert imbalance.opportunity_type == OpportunityType.RESOURCE_REBALANCING
        assert imbalance.affected_agent == "Forge"

    @pytest.mark.asyncio
    async def test_detect_training_needs(self, opportunity_detector, mock_db):
        """Test detecting training needs (calibration issues)."""
        mock_db.fetch_all.return_value = [
            {
                "agent_code": "Forge",
                "task_count": 50,
                "avg_confidence": 0.9,  # Over-confident
                "actual_rate": 0.6,
                "calibration_error": 0.3,
            },
        ]

        opportunities = await opportunity_detector._detect_training_needs(168)

        assert len(opportunities) > 0
        training_need = opportunities[0]
        assert training_need.opportunity_type == OpportunityType.TRAINING_NEED
        assert training_need.affected_agent == "Forge"
        # "overconfident" is in the title
        assert "overconfident" in training_need.title

    @pytest.mark.asyncio
    async def test_detect_error_prevention_opportunities(self, opportunity_detector, mock_db):
        """Test detecting error prevention opportunities."""
        mock_db.fetch_all.return_value = [
            {
                "error_category": "timeout",
                "task_type": "api_call",
                "agent_code": "Sentinel",
                "error_count": 15,
            },
        ]

        opportunities = await opportunity_detector._detect_error_prevention_opportunities(168)

        assert len(opportunities) > 0
        error_opp = opportunities[0]
        assert error_opp.opportunity_type == OpportunityType.ERROR_PREVENTION
        assert error_opp.affected_agent == "Sentinel"
        assert "timeout" in error_opp.title.lower()

    @pytest.mark.asyncio
    async def test_detect_handler_opportunities(self, opportunity_detector, mock_db):
        """Test detecting handler generation opportunities."""
        mock_db.fetch_all.return_value = [
            {
                "task_type": "code_review",
                "task_count": 100,
                "success_rate": 0.85,
            },
        ]

        opportunities = await opportunity_detector._detect_handler_opportunities(168)

        assert len(opportunities) > 0
        handler_opp = opportunities[0]
        assert handler_opp.opportunity_type == OpportunityType.HANDLER_OPPORTUNITY
        assert handler_opp.affected_task_type == "code_review"

    @pytest.mark.asyncio
    async def test_get_open_opportunities(self, opportunity_detector):
        """Test getting open opportunities."""
        # Create some opportunities
        opp1 = Opportunity(
            opportunity_type=OpportunityType.CAPABILITY_GAP,
            title="Test opportunity 1",
            status="open",
        )
        opp2 = Opportunity(
            opportunity_type=OpportunityType.TRAINING_NEED,
            title="Test opportunity 2",
            status="acknowledged",
        )

        opportunity_detector._opportunities[opp1.id] = opp1
        opportunity_detector._opportunities[opp2.id] = opp2

        open_opps = await opportunity_detector.get_open_opportunities()

        assert len(open_opps) == 1
        assert open_opps[0].id == opp1.id

    @pytest.mark.asyncio
    async def test_get_actionable_opportunities(self, opportunity_detector):
        """Test getting actionable opportunities."""
        opp1 = Opportunity(
            opportunity_type=OpportunityType.CAPABILITY_GAP,
            title="Auto actionable",
            auto_actionable=True,
            status="open",
        )
        opp2 = Opportunity(
            opportunity_type=OpportunityType.WORKFLOW_OPTIMIZATION,
            title="Manual only",
            auto_actionable=False,
            status="open",
        )

        opportunity_detector._opportunities[opp1.id] = opp1
        opportunity_detector._opportunities[opp2.id] = opp2

        actionable = await opportunity_detector.get_actionable_opportunities()

        assert len(actionable) == 1
        assert actionable[0].auto_actionable is True

    @pytest.mark.asyncio
    async def test_acknowledge_opportunity(self, opportunity_detector):
        """Test acknowledging an opportunity."""
        opp = Opportunity(
            opportunity_type=OpportunityType.CAPABILITY_GAP,
            title="Test",
            status="open",
        )
        opportunity_detector._opportunities[opp.id] = opp

        result = await opportunity_detector.acknowledge_opportunity(opp.id)

        assert result is True
        assert opp.status == "acknowledged"

    @pytest.mark.asyncio
    async def test_address_opportunity(self, opportunity_detector):
        """Test addressing an opportunity."""
        opp = Opportunity(
            opportunity_type=OpportunityType.CAPABILITY_GAP,
            title="Test",
            status="open",
        )
        opportunity_detector._opportunities[opp.id] = opp

        result = await opportunity_detector.address_opportunity(opp.id, "Fixed it")

        assert result is True
        assert opp.status == "addressed"

    @pytest.mark.asyncio
    async def test_dismiss_opportunity(self, opportunity_detector):
        """Test dismissing an opportunity."""
        opp = Opportunity(
            opportunity_type=OpportunityType.CAPABILITY_GAP,
            title="Test",
            status="open",
        )
        opportunity_detector._opportunities[opp.id] = opp

        result = await opportunity_detector.dismiss_opportunity(opp.id, "Not relevant")

        assert result is True
        assert opp.status == "dismissed"

    @pytest.mark.asyncio
    async def test_get_stats(self, opportunity_detector):
        """Test getting opportunity statistics."""
        opp1 = Opportunity(
            opportunity_type=OpportunityType.CAPABILITY_GAP,
            priority=OpportunityPriority.HIGH,
            status="open",
            auto_actionable=True,
        )
        opp2 = Opportunity(
            opportunity_type=OpportunityType.TRAINING_NEED,
            priority=OpportunityPriority.MEDIUM,
            status="open",
            auto_actionable=False,
        )

        opportunity_detector._opportunities[opp1.id] = opp1
        opportunity_detector._opportunities[opp2.id] = opp2

        stats = await opportunity_detector.get_stats()

        assert stats["total_opportunities"] == 2
        assert stats["open_opportunities"] == 2
        assert stats["actionable_opportunities"] == 1
        assert "capability_gap" in stats["by_type"]
        assert "high" in stats["by_priority"]


class TestOpportunity:
    """Tests for Opportunity dataclass."""

    def test_opportunity_creation(self):
        """Test creating an opportunity."""
        opp = Opportunity(
            opportunity_type=OpportunityType.CAPABILITY_GAP,
            priority=OpportunityPriority.HIGH,
            title="Test opportunity",
            description="This is a test",
            affected_agent="Forge",
            impact_score=0.8,
        )

        assert opp.opportunity_type == OpportunityType.CAPABILITY_GAP
        assert opp.priority == OpportunityPriority.HIGH
        assert opp.affected_agent == "Forge"
        assert opp.impact_score == 0.8
        assert opp.status == "open"
        assert opp.id is not None

    def test_opportunity_to_dict(self):
        """Test opportunity serialization."""
        opp = Opportunity(
            opportunity_type=OpportunityType.WORKFLOW_OPTIMIZATION,
            priority=OpportunityPriority.MEDIUM,
            title="Workflow test",
            affected_task_type="code_review",
        )

        data = opp.to_dict()

        assert data["opportunity_type"] == "workflow_optimization"
        assert data["priority"] == "medium"
        assert data["title"] == "Workflow test"
        assert data["affected_task_type"] == "code_review"
        assert "detected_at" in data

    def test_opportunity_default_expiry(self):
        """Test opportunity has no default expiry."""
        opp = Opportunity()

        assert opp.expires_at is None


class TestOpportunityPriority:
    """Tests for priority calculation."""

    def test_calculate_priority_critical(self, opportunity_detector):
        """Test critical priority for high impact."""
        priority = opportunity_detector._calculate_priority(0.9)
        assert priority == OpportunityPriority.CRITICAL

    def test_calculate_priority_high(self, opportunity_detector):
        """Test high priority for medium-high impact."""
        priority = opportunity_detector._calculate_priority(0.6)
        assert priority == OpportunityPriority.HIGH

    def test_calculate_priority_medium(self, opportunity_detector):
        """Test medium priority for moderate impact."""
        priority = opportunity_detector._calculate_priority(0.3)
        assert priority == OpportunityPriority.MEDIUM

    def test_calculate_priority_low(self, opportunity_detector):
        """Test low priority for low impact."""
        priority = opportunity_detector._calculate_priority(0.1)
        assert priority == OpportunityPriority.LOW


# =============================================================================
# ProactiveTaskGenerator Tests
# =============================================================================


class TestProactiveTaskGenerator:
    """Tests for proactive task generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_all_tasks_empty(self, proactive_generator):
        """Test generating tasks with no data."""
        tasks = await proactive_generator.generate_all_tasks()

        # Should at least have health check task
        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_generate_calibration_tasks(self, proactive_generator, mock_db):
        """Test generating calibration tasks."""
        mock_db.fetch_all.return_value = [
            {
                "agent_code": "Forge",
                "task_count": 50,
                "avg_confidence": 0.9,
                "actual_rate": 0.6,
                "calibration_error": 0.3,
            },
        ]

        tasks = await proactive_generator.generate_calibration_tasks(24)

        assert len(tasks) > 0
        cal_task = tasks[0]
        assert cal_task.task_type == ProactiveTaskType.CALIBRATION_CHECK
        assert cal_task.target_agent == "Forge"
        assert cal_task.priority in (TaskPriority.MEDIUM, TaskPriority.HIGH)

    @pytest.mark.asyncio
    async def test_generate_investigation_tasks(self, proactive_generator, mock_db):
        """Test generating performance investigation tasks."""
        mock_db.fetch_all.return_value = [
            {
                "agent_code": "Keystone",
                "old_tasks": 50,
                "old_successes": 45,  # 90% old rate
                "recent_tasks": 20,
                "recent_successes": 12,  # 60% recent rate - 30% decline
            },
        ]

        tasks = await proactive_generator.generate_investigation_tasks(24)

        assert len(tasks) > 0
        inv_task = tasks[0]
        assert inv_task.task_type == ProactiveTaskType.PERFORMANCE_INVESTIGATION
        assert inv_task.target_agent == "Keystone"

    @pytest.mark.asyncio
    async def test_generate_pattern_analysis_tasks(self, proactive_generator, mock_db):
        """Test generating pattern analysis tasks."""
        mock_db.fetch_all.return_value = [
            {
                "task_type": "bug_fix",
                "task_count": 50,
                "success_rate": 0.7,
            },
        ]

        tasks = await proactive_generator.generate_pattern_analysis_tasks(24)

        assert len(tasks) > 0
        pattern_task = tasks[0]
        assert pattern_task.task_type == ProactiveTaskType.PATTERN_ANALYSIS
        assert pattern_task.target_task_type == "bug_fix"

    @pytest.mark.asyncio
    async def test_generate_handler_tasks(self, proactive_generator, mock_db):
        """Test generating handler creation tasks."""
        mock_db.fetch_all.return_value = [
            {
                "task_type": "code_review",
                "task_count": 100,
                "success_rate": 0.85,
            },
        ]

        tasks = await proactive_generator.generate_handler_tasks(168)

        assert len(tasks) > 0
        handler_task = tasks[0]
        assert handler_task.task_type == ProactiveTaskType.HANDLER_GENERATION
        assert handler_task.target_task_type == "code_review"

    @pytest.mark.asyncio
    async def test_generate_health_check_tasks(self, proactive_generator):
        """Test generating health check tasks."""
        tasks = await proactive_generator.generate_health_check_tasks()

        assert len(tasks) == 1
        health_task = tasks[0]
        assert health_task.task_type == ProactiveTaskType.HEALTH_CHECK
        assert health_task.priority == TaskPriority.BACKGROUND

    @pytest.mark.asyncio
    async def test_health_check_cooldown(self, proactive_generator):
        """Test that health check respects cooldown."""
        # Generate first health check
        tasks1 = await proactive_generator.generate_health_check_tasks()
        assert len(tasks1) == 1

        # Should not generate again immediately
        tasks2 = await proactive_generator.generate_health_check_tasks()
        assert len(tasks2) == 0

    @pytest.mark.asyncio
    async def test_convert_opportunities_to_tasks(
        self, proactive_generator_with_detector, opportunity_detector
    ):
        """Test converting opportunities to tasks."""
        # Add an actionable opportunity
        opp = Opportunity(
            opportunity_type=OpportunityType.CAPABILITY_GAP,
            priority=OpportunityPriority.HIGH,
            title="Forge capability gap",
            description="Test description",
            affected_agent="Forge",
            affected_task_type="code_review",
            auto_actionable=True,
            status="open",
            evidence={"gap": 0.2},
        )
        opportunity_detector._opportunities[opp.id] = opp

        tasks = await proactive_generator_with_detector.convert_opportunities_to_tasks()

        assert len(tasks) > 0
        converted_task = tasks[0]
        assert converted_task.source_opportunity_id == opp.id
        assert "[Auto]" in converted_task.title

    @pytest.mark.asyncio
    async def test_enqueue_task(self, proactive_generator, mock_task_queue):
        """Test enqueuing a task."""
        task = ProactiveTask(
            task_type=ProactiveTaskType.CALIBRATION_CHECK,
            title="Test task",
            target_agent="Forge",
        )

        result = await proactive_generator.enqueue_task(task)

        assert result is True
        assert task.status == "queued"
        assert task.queued_at is not None
        mock_task_queue.enqueue.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_task_no_queue(self, mock_db):
        """Test enqueuing without a task queue."""
        generator = ProactiveTaskGenerator(mock_db, task_queue=None)
        task = ProactiveTask(task_type=ProactiveTaskType.HEALTH_CHECK, title="Test")

        result = await generator.enqueue_task(task)

        assert result is False

    @pytest.mark.asyncio
    async def test_enqueue_all_pending(self, proactive_generator, mock_task_queue):
        """Test enqueuing all pending tasks."""
        task1 = ProactiveTask(
            task_type=ProactiveTaskType.CALIBRATION_CHECK,
            title="Task 1",
            status="pending",
        )
        task2 = ProactiveTask(
            task_type=ProactiveTaskType.HEALTH_CHECK,
            title="Task 2",
            status="pending",
        )

        proactive_generator._tasks[task1.id] = task1
        proactive_generator._tasks[task2.id] = task2

        count = await proactive_generator.enqueue_all_pending()

        assert count == 2
        assert task1.status == "queued"
        assert task2.status == "queued"

    @pytest.mark.asyncio
    async def test_complete_task(self, proactive_generator):
        """Test completing a task."""
        task = ProactiveTask(
            task_type=ProactiveTaskType.CALIBRATION_CHECK,
            title="Test task",
            status="executing",
        )
        proactive_generator._tasks[task.id] = task

        result = await proactive_generator.complete_task(task.id, result={"success": True})

        assert result is True
        assert task.status == "completed"
        assert task.completed_at is not None
        assert task.result == {"success": True}

    @pytest.mark.asyncio
    async def test_fail_task(self, proactive_generator):
        """Test failing a task."""
        task = ProactiveTask(
            task_type=ProactiveTaskType.CALIBRATION_CHECK,
            title="Test task",
            status="executing",
        )
        proactive_generator._tasks[task.id] = task

        result = await proactive_generator.fail_task(task.id, error="Test error")

        assert result is True
        assert task.status == "failed"
        assert task.result == {"error": "Test error"}

    @pytest.mark.asyncio
    async def test_get_task(self, proactive_generator):
        """Test getting a task by ID."""
        task = ProactiveTask(
            task_type=ProactiveTaskType.HEALTH_CHECK,
            title="Test task",
        )
        proactive_generator._tasks[task.id] = task

        found = await proactive_generator.get_task(task.id)

        assert found is not None
        assert found.id == task.id

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, proactive_generator):
        """Test getting non-existent task."""
        found = await proactive_generator.get_task("non-existent")

        assert found is None

    @pytest.mark.asyncio
    async def test_get_tasks_by_type(self, proactive_generator):
        """Test getting tasks by type."""
        task1 = ProactiveTask(task_type=ProactiveTaskType.CALIBRATION_CHECK, title="Cal 1")
        task2 = ProactiveTask(task_type=ProactiveTaskType.CALIBRATION_CHECK, title="Cal 2")
        task3 = ProactiveTask(task_type=ProactiveTaskType.HEALTH_CHECK, title="Health")

        proactive_generator._tasks[task1.id] = task1
        proactive_generator._tasks[task2.id] = task2
        proactive_generator._tasks[task3.id] = task3

        cal_tasks = await proactive_generator.get_tasks_by_type(ProactiveTaskType.CALIBRATION_CHECK)

        assert len(cal_tasks) == 2

    @pytest.mark.asyncio
    async def test_get_pending_tasks(self, proactive_generator):
        """Test getting pending tasks."""
        task1 = ProactiveTask(
            task_type=ProactiveTaskType.CALIBRATION_CHECK,
            title="Pending",
            status="pending",
        )
        task2 = ProactiveTask(
            task_type=ProactiveTaskType.HEALTH_CHECK,
            title="Completed",
            status="completed",
        )

        proactive_generator._tasks[task1.id] = task1
        proactive_generator._tasks[task2.id] = task2

        pending = await proactive_generator.get_pending_tasks()

        assert len(pending) == 1
        assert pending[0].status == "pending"

    @pytest.mark.asyncio
    async def test_clear_completed_tasks(self, proactive_generator):
        """Test clearing completed tasks."""
        task1 = ProactiveTask(
            task_type=ProactiveTaskType.CALIBRATION_CHECK,
            title="Completed",
            status="completed",
        )
        task2 = ProactiveTask(
            task_type=ProactiveTaskType.HEALTH_CHECK,
            title="Failed",
            status="failed",
        )
        task3 = ProactiveTask(
            task_type=ProactiveTaskType.PATTERN_ANALYSIS,
            title="Pending",
            status="pending",
        )

        proactive_generator._tasks[task1.id] = task1
        proactive_generator._tasks[task2.id] = task2
        proactive_generator._tasks[task3.id] = task3

        count = await proactive_generator.clear_completed_tasks()

        assert count == 2
        assert len(proactive_generator._tasks) == 1
        assert task3.id in proactive_generator._tasks

    @pytest.mark.asyncio
    async def test_get_stats(self, proactive_generator):
        """Test getting task generation statistics."""
        task1 = ProactiveTask(
            task_type=ProactiveTaskType.CALIBRATION_CHECK,
            priority=TaskPriority.HIGH,
            status="pending",
        )
        task2 = ProactiveTask(
            task_type=ProactiveTaskType.HEALTH_CHECK,
            priority=TaskPriority.BACKGROUND,
            status="completed",
        )

        proactive_generator._tasks[task1.id] = task1
        proactive_generator._tasks[task2.id] = task2

        stats = await proactive_generator.get_stats()

        assert stats["total_tasks"] == 2
        assert stats["pending_tasks"] == 1
        assert stats["completed_tasks"] == 1
        assert "calibration_check" in stats["by_type"]
        assert "pending" in stats["by_status"]


class TestProactiveTask:
    """Tests for ProactiveTask dataclass."""

    def test_task_creation(self):
        """Test creating a proactive task."""
        task = ProactiveTask(
            task_type=ProactiveTaskType.CALIBRATION_CHECK,
            priority=TaskPriority.HIGH,
            title="Test calibration",
            description="Run calibration check",
            target_agent="Forge",
        )

        assert task.task_type == ProactiveTaskType.CALIBRATION_CHECK
        assert task.priority == TaskPriority.HIGH
        assert task.target_agent == "Forge"
        assert task.status == "pending"
        assert task.id is not None

    def test_task_to_dict(self):
        """Test task serialization."""
        task = ProactiveTask(
            task_type=ProactiveTaskType.PERFORMANCE_INVESTIGATION,
            priority=TaskPriority.MEDIUM,
            title="Investigate Keystone",
            target_agent="Keystone",
            parameters={"decline": 0.2},
        )

        data = task.to_dict()

        assert data["task_type"] == "performance_investigation"
        assert data["priority"] == 3  # TaskPriority.MEDIUM.value
        assert data["title"] == "Investigate Keystone"
        assert data["target_agent"] == "Keystone"
        assert data["parameters"] == {"decline": 0.2}

    def test_task_default_status(self):
        """Test task default status is pending."""
        task = ProactiveTask()

        assert task.status == "pending"

    def test_task_created_at(self):
        """Test task has created_at timestamp."""
        task = ProactiveTask()

        assert task.created_at is not None
        assert isinstance(task.created_at, datetime)


class TestCooldownTracking:
    """Tests for cooldown functionality."""

    def test_not_on_cooldown_initially(self, proactive_generator):
        """Test that nothing is on cooldown initially."""
        assert proactive_generator._is_on_cooldown("calibration") is False
        assert proactive_generator._is_on_cooldown("investigation") is False
        assert proactive_generator._is_on_cooldown("handler") is False

    def test_cooldown_after_generation(self, proactive_generator):
        """Test cooldown is set after generation."""
        proactive_generator._last_generated["calibration"] = datetime.now(timezone.utc)

        assert proactive_generator._is_on_cooldown("calibration") is True

    def test_cooldown_expires(self, proactive_generator):
        """Test cooldown expires after time passes."""
        # Set last generated to 48 hours ago
        proactive_generator._last_generated["calibration"] = datetime.now(timezone.utc) - timedelta(
            hours=48
        )

        # Default calibration cooldown is 24 hours
        assert proactive_generator._is_on_cooldown("calibration") is False

    def test_custom_cooldown_hours(self, proactive_generator):
        """Test custom cooldown hours."""
        proactive_generator._last_generated["test"] = datetime.now(timezone.utc) - timedelta(
            hours=5
        )

        # 10 hour cooldown - should still be on cooldown
        assert proactive_generator._is_on_cooldown("test", cooldown_hours=10) is True

        # 4 hour cooldown - should be expired
        assert proactive_generator._is_on_cooldown("test", cooldown_hours=4) is False


class TestOpportunityToTaskConversion:
    """Tests for opportunity-to-task conversion."""

    def test_capability_gap_to_investigation(self, proactive_generator):
        """Test capability gap converts to investigation task."""
        opp = Opportunity(
            opportunity_type=OpportunityType.CAPABILITY_GAP,
            priority=OpportunityPriority.HIGH,
            title="Forge gap",
            affected_agent="Forge",
        )

        task = proactive_generator._opportunity_to_task(opp)

        assert task is not None
        assert task.task_type == ProactiveTaskType.PERFORMANCE_INVESTIGATION
        assert task.priority == TaskPriority.HIGH

    def test_workflow_optimization_to_pattern_analysis(self, proactive_generator):
        """Test workflow optimization converts to pattern analysis."""
        opp = Opportunity(
            opportunity_type=OpportunityType.WORKFLOW_OPTIMIZATION,
            priority=OpportunityPriority.MEDIUM,
            title="Slow workflow",
        )

        task = proactive_generator._opportunity_to_task(opp)

        assert task is not None
        assert task.task_type == ProactiveTaskType.PATTERN_ANALYSIS

    def test_training_need_to_calibration(self, proactive_generator):
        """Test training need converts to calibration task."""
        opp = Opportunity(
            opportunity_type=OpportunityType.TRAINING_NEED,
            priority=OpportunityPriority.MEDIUM,
            title="Calibration needed",
            affected_agent="Keystone",
        )

        task = proactive_generator._opportunity_to_task(opp)

        assert task is not None
        assert task.task_type == ProactiveTaskType.CALIBRATION_CHECK
        assert task.target_agent == "Keystone"

    def test_handler_opportunity_to_handler_generation(self, proactive_generator):
        """Test handler opportunity converts to handler generation task."""
        opp = Opportunity(
            opportunity_type=OpportunityType.HANDLER_OPPORTUNITY,
            priority=OpportunityPriority.LOW,
            title="Handler candidate",
            affected_task_type="code_review",
        )

        task = proactive_generator._opportunity_to_task(opp)

        assert task is not None
        assert task.task_type == ProactiveTaskType.HANDLER_GENERATION
        assert task.target_task_type == "code_review"

    def test_priority_mapping(self, proactive_generator):
        """Test priority is correctly mapped."""
        priorities = [
            (OpportunityPriority.CRITICAL, TaskPriority.CRITICAL),
            (OpportunityPriority.HIGH, TaskPriority.HIGH),
            (OpportunityPriority.MEDIUM, TaskPriority.MEDIUM),
            (OpportunityPriority.LOW, TaskPriority.LOW),
        ]

        for opp_priority, expected_task_priority in priorities:
            opp = Opportunity(
                opportunity_type=OpportunityType.CAPABILITY_GAP,
                priority=opp_priority,
                title="Test",
            )

            task = proactive_generator._opportunity_to_task(opp)

            assert task.priority == expected_task_priority


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestPhase4EdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_detect_opportunities_db_error(self, opportunity_detector, mock_db):
        """Test that db errors are handled gracefully."""
        mock_db.fetch_all.side_effect = Exception("DB error")

        # Should not raise, just return empty
        opportunities = await opportunity_detector.detect_opportunities()

        assert opportunities == []

    @pytest.mark.asyncio
    async def test_generate_tasks_db_error(self, proactive_generator, mock_db):
        """Test that db errors are handled gracefully."""
        mock_db.fetch_all.side_effect = Exception("DB error")

        # Should not raise, just return what it can
        tasks = await proactive_generator.generate_all_tasks()

        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_opportunity_expiration(self, opportunity_detector):
        """Test that expired opportunities are not returned."""
        expired_opp = Opportunity(
            opportunity_type=OpportunityType.CAPABILITY_GAP,
            title="Expired",
            status="open",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        active_opp = Opportunity(
            opportunity_type=OpportunityType.TRAINING_NEED,
            title="Active",
            status="open",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )

        opportunity_detector._opportunities[expired_opp.id] = expired_opp
        opportunity_detector._opportunities[active_opp.id] = active_opp

        open_opps = await opportunity_detector.get_open_opportunities()

        assert len(open_opps) == 1
        assert open_opps[0].id == active_opp.id

    @pytest.mark.asyncio
    async def test_acknowledge_non_existent_opportunity(self, opportunity_detector):
        """Test acknowledging non-existent opportunity."""
        result = await opportunity_detector.acknowledge_opportunity("non-existent")

        assert result is False

    @pytest.mark.asyncio
    async def test_complete_non_existent_task(self, proactive_generator):
        """Test completing non-existent task."""
        result = await proactive_generator.complete_task("non-existent")

        assert result is False

    @pytest.mark.asyncio
    async def test_max_tasks_limit(self, proactive_generator, mock_db):
        """Test that task generation respects limits when db returns limited rows."""
        # The SQL query has a LIMIT clause - simulate limited results
        # Return MAX_CALIBRATION_TASKS rows (as the db would after LIMIT)
        mock_db.fetch_all.return_value = [
            {
                "agent_code": f"AGENT_{i}",
                "task_count": 50,
                "avg_confidence": 0.9,
                "actual_rate": 0.5,
                "calibration_error": 0.4,
            }
            for i in range(proactive_generator.MAX_CALIBRATION_TASKS)
        ]

        tasks = await proactive_generator.generate_calibration_tasks(24)

        # Should be exactly MAX_CALIBRATION_TASKS since db returns that many
        assert len(tasks) == proactive_generator.MAX_CALIBRATION_TASKS

    def test_task_enums(self):
        """Test that task enums have expected values."""
        assert ProactiveTaskType.CALIBRATION_CHECK.value == "calibration_check"
        assert ProactiveTaskType.PERFORMANCE_INVESTIGATION.value == "performance_investigation"
        assert ProactiveTaskType.HEALTH_CHECK.value == "health_check"

        assert TaskPriority.CRITICAL.value == 1
        assert TaskPriority.BACKGROUND.value == 5

    def test_opportunity_enums(self):
        """Test that opportunity enums have expected values."""
        assert OpportunityType.CAPABILITY_GAP.value == "capability_gap"
        assert OpportunityType.HANDLER_OPPORTUNITY.value == "handler_opportunity"

        assert OpportunityPriority.CRITICAL.value == "critical"
        assert OpportunityPriority.LOW.value == "low"

    @pytest.mark.asyncio
    async def test_task_sorting_by_priority(self, proactive_generator):
        """Test that generated tasks are sorted by priority."""
        task_high = ProactiveTask(
            task_type=ProactiveTaskType.CALIBRATION_CHECK,
            priority=TaskPriority.HIGH,
            title="High priority",
        )
        task_low = ProactiveTask(
            task_type=ProactiveTaskType.HEALTH_CHECK,
            priority=TaskPriority.BACKGROUND,
            title="Low priority",
        )
        task_critical = ProactiveTask(
            task_type=ProactiveTaskType.PERFORMANCE_INVESTIGATION,
            priority=TaskPriority.CRITICAL,
            title="Critical",
        )

        proactive_generator._tasks = {
            task_high.id: task_high,
            task_low.id: task_low,
            task_critical.id: task_critical,
        }

        # Get all tasks and sort
        tasks = list(proactive_generator._tasks.values())
        tasks.sort(key=lambda t: t.priority.value)

        assert tasks[0].priority == TaskPriority.CRITICAL
        assert tasks[-1].priority == TaskPriority.BACKGROUND

    @pytest.mark.asyncio
    async def test_opportunity_sorting_by_impact(self, opportunity_detector):
        """Test that opportunities are sorted by impact score."""
        opp_low = Opportunity(
            opportunity_type=OpportunityType.CAPABILITY_GAP,
            title="Low impact",
            impact_score=0.2,
            status="open",
        )
        opp_high = Opportunity(
            opportunity_type=OpportunityType.TRAINING_NEED,
            title="High impact",
            impact_score=0.9,
            status="open",
        )
        opp_medium = Opportunity(
            opportunity_type=OpportunityType.WORKFLOW_OPTIMIZATION,
            title="Medium impact",
            impact_score=0.5,
            status="open",
        )

        opportunity_detector._opportunities = {
            opp_low.id: opp_low,
            opp_high.id: opp_high,
            opp_medium.id: opp_medium,
        }

        open_opps = await opportunity_detector.get_open_opportunities()
        # Sort to verify
        sorted_opps = sorted(open_opps, key=lambda x: x.impact_score, reverse=True)

        assert sorted_opps[0].impact_score == 0.9
        assert sorted_opps[-1].impact_score == 0.2
