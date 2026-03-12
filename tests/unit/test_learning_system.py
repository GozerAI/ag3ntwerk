"""
Unit tests for the Learning System.

Tests:
- Data models (HierarchyPath, TaskOutcomeRecord, LearnedPattern, etc.)
- PatternStore persistence and retrieval
- OutcomeTracker recording and categorization
- Learning loops (Agent, Manager, Specialist)
- IssueManager issue detection and task creation
- LearningOrchestrator coordination
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

from ag3ntwerk.learning.models import (
    HierarchyPath,
    TaskOutcomeRecord,
    LearnedPattern,
    LearningIssue,
    LearningAdjustment,
    AgentPerformance,
    OutcomeType,
    ErrorCategory,
    PatternType,
    ScopeLevel,
    IssueSeverity,
    IssueType,
    IssueStatus,
    PerformanceTrend,
)


class TestHierarchyPath:
    """Test HierarchyPath data model."""

    def test_full_path(self):
        path = HierarchyPath(
            agent="Forge",
            manager="AM",
            specialist="SD",
        )
        assert path.agent == "Forge"
        assert path.manager == "AM"
        assert path.specialist == "SD"

    def test_executive_only(self):
        path = HierarchyPath(agent="Keystone")
        assert path.agent == "Keystone"
        assert path.manager is None
        assert path.specialist is None

    def test_to_dict(self):
        path = HierarchyPath(agent="Sentinel", manager="DG")
        d = path.to_dict()
        assert d["agent"] == "Sentinel"
        assert d["manager"] == "DG"
        assert d["specialist"] is None


class TestTaskOutcomeRecord:
    """Test TaskOutcomeRecord data model."""

    def test_successful_outcome(self):
        record = TaskOutcomeRecord(
            task_id="task-123",
            task_type="code_review",
            agent_code="Forge",
            success=True,
            effectiveness=0.9,
            duration_ms=1500.0,
        )
        assert record.success is True
        assert record.outcome_type == OutcomeType.SUCCESS
        assert record.effectiveness == 0.9
        assert record.id is not None

    def test_failed_outcome_with_error(self):
        record = TaskOutcomeRecord(
            task_id="task-456",
            task_type="deployment",
            agent_code="Forge",
            success=False,
            error_category=ErrorCategory.TIMEOUT,
            error_message="Operation timed out",
            is_recoverable=True,
        )
        assert record.success is False
        assert record.error_category == ErrorCategory.TIMEOUT
        assert record.is_recoverable is True

    def test_default_values(self):
        record = TaskOutcomeRecord(
            task_id="task-789",
            task_type="analysis",
            agent_code="Axiom",
            success=True,
        )
        assert record.outcome_type == OutcomeType.SUCCESS
        assert record.effectiveness == 0.0
        assert record.duration_ms == 0.0
        assert record.context_snapshot == {}


class TestLearnedPattern:
    """Test LearnedPattern data model."""

    def test_routing_pattern(self):
        pattern = LearnedPattern(
            pattern_type=PatternType.ROUTING,
            scope_level=ScopeLevel.AGENT,
            scope_code="Forge",
            condition_json='{"task_type": "code_review"}',
            recommendation="Route to AM for code reviews",
            confidence=0.85,
            sample_size=50,
            routing_preference="AM",
        )
        assert pattern.pattern_type == PatternType.ROUTING
        assert pattern.scope_level == ScopeLevel.AGENT
        assert pattern.routing_preference == "AM"
        assert pattern.is_active is True

    def test_confidence_pattern(self):
        pattern = LearnedPattern(
            pattern_type=PatternType.CONFIDENCE,
            scope_level=ScopeLevel.SPECIALIST,
            scope_code="SD",
            condition_json='{"confidence_bucket": "high"}',
            recommendation="Specialist is overconfident in high range",
            confidence=0.7,
            sample_size=30,
            confidence_adjustment=-0.1,
        )
        assert pattern.confidence_adjustment == -0.1

    def test_default_values(self):
        pattern = LearnedPattern(
            pattern_type=PatternType.CAPABILITY,
            scope_level=ScopeLevel.MANAGER,
            scope_code="AM",
            condition_json="{}",
            recommendation="Test",
        )
        assert pattern.confidence == 0.5
        assert pattern.sample_size == 0
        assert pattern.application_count == 0


class TestLearningIssue:
    """Test LearningIssue data model."""

    def test_anomaly_issue(self):
        issue = LearningIssue(
            issue_type=IssueType.ANOMALY,
            severity=IssueSeverity.HIGH,
            priority=2,
            source_agent_code="Forge",
            source_level=ScopeLevel.AGENT,
            title="Unusual task failures",
            description="Task failure rate spiked 50% in the last hour",
            suggested_action="investigate_failures",
        )
        assert issue.issue_type == IssueType.ANOMALY
        assert issue.severity == IssueSeverity.HIGH
        assert issue.status == IssueStatus.OPEN
        assert issue.id is not None

    def test_issue_with_evidence(self):
        evidence = {
            "failure_rate": 0.75,
            "sample_size": 20,
            "time_window_hours": 1,
        }
        issue = LearningIssue(
            issue_type=IssueType.ERROR_SPIKE,
            severity=IssueSeverity.CRITICAL,
            priority=1,
            source_agent_code="SD",
            source_level=ScopeLevel.SPECIALIST,
            title="Error spike detected",
            description="75% failure rate in last hour",
            evidence_json=json.dumps(evidence),
        )
        parsed_evidence = json.loads(issue.evidence_json)
        assert parsed_evidence["failure_rate"] == 0.75


class TestLearningAdjustment:
    """Test LearningAdjustment data model."""

    def test_empty_adjustment(self):
        adj = LearningAdjustment()
        assert adj.confidence_adjustment == 0.0
        assert adj.priority_adjustment == 0
        assert adj.preferred_route is None
        assert len(adj.warnings) == 0

    def test_adjustment_with_values(self):
        adj = LearningAdjustment(
            confidence_adjustment=-0.15,
            priority_adjustment=-2,
            preferred_route="AM",
            routing_confidence=0.85,
        )
        assert adj.confidence_adjustment == -0.15
        assert adj.priority_adjustment == -2
        assert adj.preferred_route == "AM"
        assert adj.routing_confidence == 0.85

    def test_add_warning(self):
        adj = LearningAdjustment()
        adj.add_warning("High failure rate on this task type")
        adj.add_warning("Consider routing to alternative agent")
        assert len(adj.warnings) == 2

    def test_merge_adjustments(self):
        adj1 = LearningAdjustment(
            confidence_adjustment=-0.1,
            priority_adjustment=-1,
        )
        adj1.add_warning("Warning 1")
        adj1.effectiveness_hints.append("Hint 1")

        adj2 = LearningAdjustment(
            confidence_adjustment=-0.05,
            priority_adjustment=-1,
            preferred_route="AM",
            routing_confidence=0.8,
        )
        adj2.add_warning("Warning 2")
        adj2.avoid_routes.append("CQM")

        adj1.merge(adj2)

        assert abs(adj1.confidence_adjustment - (-0.15)) < 0.001  # Float precision
        assert adj1.priority_adjustment == -2
        assert adj1.preferred_route == "AM"
        assert len(adj1.warnings) == 2
        assert len(adj1.effectiveness_hints) == 1
        assert len(adj1.avoid_routes) == 1

    def test_clamp_values(self):
        adj = LearningAdjustment(
            confidence_adjustment=-0.8,  # Should be clamped to -0.3
            priority_adjustment=-15,  # Should be clamped to -3
        )
        adj.clamp()
        assert adj.confidence_adjustment == -0.3
        assert adj.priority_adjustment == -3


class TestAgentPerformance:
    """Test AgentPerformance data model."""

    def test_default_performance(self):
        perf = AgentPerformance(
            agent_code="Forge",
            agent_level=ScopeLevel.AGENT,
        )
        assert perf.total_tasks == 0
        assert perf.health_score == 1.0
        assert perf.circuit_breaker_open is False

    def test_success_rate_calculation(self):
        perf = AgentPerformance(
            agent_code="AM",
            agent_level=ScopeLevel.MANAGER,
            total_tasks=100,
            successful_tasks=85,
        )
        assert perf.success_rate == 0.85

    def test_success_rate_no_tasks(self):
        perf = AgentPerformance(
            agent_code="SD",
            agent_level=ScopeLevel.SPECIALIST,
        )
        assert perf.success_rate == 0.0


class TestEnums:
    """Test enum values."""

    def test_outcome_types(self):
        assert OutcomeType.SUCCESS.value == "success"
        assert OutcomeType.FAILURE.value == "failure"
        assert OutcomeType.PARTIAL.value == "partial"
        assert OutcomeType.TIMEOUT.value == "timeout"

    def test_error_categories(self):
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.CAPABILITY.value == "capability"
        assert ErrorCategory.RESOURCE.value == "resource"
        assert ErrorCategory.LOGIC.value == "logic"
        assert ErrorCategory.EXTERNAL.value == "external"

    def test_pattern_types(self):
        assert PatternType.ROUTING.value == "routing"
        assert PatternType.CONFIDENCE.value == "confidence"
        assert PatternType.CAPABILITY.value == "capability"
        assert PatternType.ERROR.value == "error"

    def test_scope_levels(self):
        assert ScopeLevel.AGENT.value == "agent"
        assert ScopeLevel.MANAGER.value == "manager"
        assert ScopeLevel.SPECIALIST.value == "specialist"

    def test_issue_severities(self):
        assert IssueSeverity.CRITICAL.value == "critical"
        assert IssueSeverity.HIGH.value == "high"
        assert IssueSeverity.MEDIUM.value == "medium"
        assert IssueSeverity.LOW.value == "low"


# =============================================================================
# Pattern Store Tests
# =============================================================================


class TestPatternStore:
    """Test PatternStore functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(return_value=None)
        db.execute = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_store_pattern(self, mock_db):
        from ag3ntwerk.learning.pattern_store import PatternStore

        store = PatternStore(mock_db)
        pattern = LearnedPattern(
            pattern_type=PatternType.ROUTING,
            scope_level=ScopeLevel.AGENT,
            scope_code="Forge",
            condition_json="{}",
            recommendation="Test",
        )

        await store.store_pattern(pattern)

        mock_db.execute.assert_called_once()
        # Verify pattern has an ID
        assert pattern.id is not None

    @pytest.mark.asyncio
    async def test_get_all_active_patterns(self, mock_db):
        from ag3ntwerk.learning.pattern_store import PatternStore

        now = datetime.now(timezone.utc).isoformat()

        mock_db.fetch_all = AsyncMock(
            return_value=[
                {
                    "id": "pattern-1",
                    "pattern_type": "routing",
                    "scope_level": "agent",
                    "scope_code": "Forge",
                    "condition_json": '{"task_type": "code_review"}',
                    "recommendation": "Route to AM",
                    "confidence": 0.9,
                    "sample_size": 50,
                    "success_rate": 0.85,
                    "avg_improvement": 0.15,
                    "confidence_adjustment": 0.0,
                    "priority_adjustment": 0,
                    "routing_preference": "AM",
                    "is_active": 1,
                    "last_applied_at": None,
                    "application_count": 20,
                    "expires_at": None,
                    "validated_by": None,
                    "validation_score": None,
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "pattern-2",
                    "pattern_type": "confidence",
                    "scope_level": "specialist",
                    "scope_code": "SD",
                    "condition_json": '{"confidence_bucket": "high"}',
                    "recommendation": "Adjust confidence",
                    "confidence": 0.7,
                    "sample_size": 30,
                    "success_rate": 0.75,
                    "avg_improvement": 0.1,
                    "confidence_adjustment": -0.1,
                    "priority_adjustment": 0,
                    "routing_preference": None,
                    "is_active": 1,
                    "last_applied_at": None,
                    "application_count": 10,
                    "expires_at": None,
                    "validated_by": None,
                    "validation_score": None,
                    "created_at": now,
                    "updated_at": now,
                },
            ]
        )

        store = PatternStore(mock_db)
        patterns = await store.get_all_active_patterns()

        assert len(patterns) == 2
        assert patterns[0].id == "pattern-1"
        assert patterns[0].confidence == 0.9
        assert patterns[1].id == "pattern-2"
        assert patterns[1].confidence == 0.7

        # Verify correct SQL query was used
        call_args = mock_db.fetch_all.call_args
        sql = call_args[0][0]
        assert "is_active = 1" in sql
        assert "ORDER BY confidence DESC" in sql

    @pytest.mark.asyncio
    async def test_get_all_active_patterns_empty(self, mock_db):
        from ag3ntwerk.learning.pattern_store import PatternStore

        mock_db.fetch_all = AsyncMock(return_value=[])

        store = PatternStore(mock_db)
        patterns = await store.get_all_active_patterns()

        assert patterns == []

    @pytest.mark.asyncio
    async def test_activate_pattern(self, mock_db):
        from ag3ntwerk.learning.pattern_store import PatternStore

        now = datetime.now(timezone.utc).isoformat()

        # Mock fetch_one to return the pattern after activation
        mock_db.fetch_one = AsyncMock(
            return_value={
                "id": "pattern-1",
                "pattern_type": "routing",
                "scope_level": "agent",
                "scope_code": "Forge",
                "condition_json": '{"task_type": "code_review"}',
                "recommendation": "Route to AM",
                "confidence": 0.85,
                "sample_size": 50,
                "success_rate": 0.9,
                "avg_improvement": 0.15,
                "confidence_adjustment": 0.0,
                "priority_adjustment": 0,
                "routing_preference": "AM",
                "is_active": 1,
                "last_applied_at": None,
                "application_count": 20,
                "expires_at": None,
                "validated_by": None,
                "validation_score": None,
                "created_at": now,
                "updated_at": now,
            }
        )

        store = PatternStore(mock_db)
        await store.activate_pattern("pattern-1")

        # Verify the UPDATE SQL was called
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        sql = call_args[0][0]
        assert "is_active = 1" in sql

        # Verify fetch_one was called to reload the pattern for caching
        mock_db.fetch_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_pattern_updates_cache(self, mock_db):
        from ag3ntwerk.learning.pattern_store import PatternStore

        now = datetime.now(timezone.utc).isoformat()

        pattern_row = {
            "id": "pattern-1",
            "pattern_type": "routing",
            "scope_level": "agent",
            "scope_code": "Forge",
            "condition_json": '{"task_type": "code_review"}',
            "recommendation": "Route to AM",
            "confidence": 0.85,
            "sample_size": 50,
            "success_rate": 0.9,
            "avg_improvement": 0.15,
            "confidence_adjustment": 0.0,
            "priority_adjustment": 0,
            "routing_preference": "AM",
            "is_active": 1,
            "last_applied_at": None,
            "application_count": 20,
            "expires_at": None,
            "validated_by": None,
            "validation_score": None,
            "created_at": now,
            "updated_at": now,
        }

        mock_db.fetch_one = AsyncMock(return_value=pattern_row)
        mock_db.fetch_all = AsyncMock(return_value=[])

        store = PatternStore(mock_db)
        # Load patterns to initialize cache
        await store.load_patterns()

        await store.activate_pattern("pattern-1")

        # Verify the pattern is now in the cache
        cache_key = "agent:Forge"
        assert cache_key in store._cache
        assert any(p.id == "pattern-1" for p in store._cache[cache_key])

    @pytest.mark.asyncio
    async def test_load_patterns(self, mock_db):
        from ag3ntwerk.learning.pattern_store import PatternStore

        now = datetime.now(timezone.utc).isoformat()

        # Mock database returning patterns with all required fields
        mock_db.fetch_all = AsyncMock(
            return_value=[
                {
                    "id": "pattern-1",
                    "pattern_type": "routing",
                    "scope_level": "agent",
                    "scope_code": "Forge",
                    "condition_json": "{}",
                    "recommendation": "Test",
                    "confidence": 0.8,
                    "sample_size": 10,
                    "success_rate": 0.9,
                    "avg_improvement": 0.15,
                    "confidence_adjustment": 0.0,
                    "priority_adjustment": 0,
                    "routing_preference": "AM",
                    "is_active": 1,
                    "last_applied_at": None,
                    "application_count": 5,
                    "expires_at": None,
                    "validated_by": None,
                    "validation_score": None,
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        )

        store = PatternStore(mock_db)
        count = await store.load_patterns()

        assert count == 1
        patterns = await store.get_patterns(scope_code="Forge")
        assert len(patterns) == 1
        assert patterns[0].routing_preference == "AM"


# =============================================================================
# Outcome Tracker Tests
# =============================================================================


class TestOutcomeTracker:
    """Test OutcomeTracker functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.execute = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_record_outcome(self, mock_db):
        from ag3ntwerk.learning.outcome_tracker import OutcomeTracker

        tracker = OutcomeTracker(mock_db)
        tracker._flush_threshold = 1  # Flush immediately

        hierarchy = HierarchyPath(
            agent="Forge",
            manager="AM",
            specialist="SD",
        )

        outcome_id = await tracker.record_outcome(
            task_id="task-123",
            task_type="code_review",
            hierarchy_path=hierarchy,
            success=True,
            duration_ms=1500.0,
            effectiveness=0.9,
        )

        assert outcome_id is not None
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_categorization(self, mock_db):
        from ag3ntwerk.learning.outcome_tracker import OutcomeTracker

        tracker = OutcomeTracker(mock_db)

        # Test timeout error
        cat = tracker._categorize_error("Operation timed out after 30s")
        assert cat == ErrorCategory.TIMEOUT

        # Test capability error
        cat = tracker._categorize_error("Agent cannot handle task type")
        assert cat == ErrorCategory.CAPABILITY

        # Test resource error
        cat = tracker._categorize_error("Out of memory")
        assert cat == ErrorCategory.RESOURCE

        # Test external error
        cat = tracker._categorize_error("LLM provider returned 503")
        assert cat == ErrorCategory.EXTERNAL

        # Test logic error (default)
        cat = tracker._categorize_error("Invalid input format")
        assert cat == ErrorCategory.LOGIC


# =============================================================================
# Learning Loop Tests
# =============================================================================


class TestSpecialistLearningLoop:
    """Test SpecialistLearningLoop functionality."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_pattern_store(self):
        store = AsyncMock()
        store.get_patterns = AsyncMock(return_value=[])
        return store

    @pytest.mark.asyncio
    async def test_analyze_outcomes_high_success(self, mock_db, mock_pattern_store):
        from ag3ntwerk.learning.loops.specialist_loop import SpecialistLearningLoop

        loop = SpecialistLearningLoop(
            specialist_code="SD",
            manager_code="AM",
            capabilities=["code_generation"],
            pattern_store=mock_pattern_store,
            db=mock_db,
        )

        # Create outcomes with high success rate
        outcomes = [
            TaskOutcomeRecord(
                task_id=f"task-{i}",
                task_type="code_generation",
                agent_code="Forge",
                manager_code="AM",
                specialist_code="SD",
                success=True,
                effectiveness=0.9,
            )
            for i in range(15)
        ]

        patterns = await loop.analyze_outcomes(outcomes)

        # Should detect high performance pattern
        assert len(patterns) >= 1
        capability_patterns = [p for p in patterns if p.pattern_type == PatternType.CAPABILITY]
        assert len(capability_patterns) >= 1

    @pytest.mark.asyncio
    async def test_analyze_outcomes_low_success(self, mock_db, mock_pattern_store):
        from ag3ntwerk.learning.loops.specialist_loop import SpecialistLearningLoop

        loop = SpecialistLearningLoop(
            specialist_code="SD",
            manager_code="AM",
            capabilities=["refactoring"],
            pattern_store=mock_pattern_store,
            db=mock_db,
        )

        # Create outcomes with low success rate
        outcomes = [
            TaskOutcomeRecord(
                task_id=f"task-{i}",
                task_type="refactoring",
                agent_code="Forge",
                manager_code="AM",
                specialist_code="SD",
                success=(i < 3),  # Only 3/15 success
                effectiveness=0.3 if i < 3 else 0.0,
            )
            for i in range(15)
        ]

        patterns = await loop.analyze_outcomes(outcomes)

        # Should detect low performance pattern
        weak_patterns = [
            p
            for p in patterns
            if p.pattern_type == PatternType.CAPABILITY and p.confidence_adjustment < 0
        ]
        assert len(weak_patterns) >= 1

    @pytest.mark.asyncio
    async def test_detect_performance_issues(self, mock_db, mock_pattern_store):
        from ag3ntwerk.learning.loops.specialist_loop import SpecialistLearningLoop

        loop = SpecialistLearningLoop(
            specialist_code="SD",
            manager_code="AM",
            capabilities=["testing"],
            pattern_store=mock_pattern_store,
            db=mock_db,
        )

        # Create outcomes with very low success rate
        outcomes = [
            TaskOutcomeRecord(
                task_id=f"task-{i}",
                task_type="testing",
                agent_code="Forge",
                manager_code="AM",
                specialist_code="SD",
                success=(i < 2),  # Only 2/20 success = 10%
                effectiveness=0.1 if i < 2 else 0.0,
            )
            for i in range(20)
        ]

        issues = await loop.detect_issues(outcomes, [])

        # Should detect high failure rate issue
        assert len(issues) >= 1
        assert any(i.issue_type == IssueType.PATTERN_DECLINE for i in issues)


# =============================================================================
# Issue Manager Tests
# =============================================================================


class TestIssueManager:
    """Test IssueManager functionality."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(return_value=None)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_task_queue(self):
        queue = AsyncMock()
        queue.enqueue = AsyncMock(return_value="task-123")
        return queue

    @pytest.mark.asyncio
    async def test_create_issue(self, mock_db, mock_task_queue):
        from ag3ntwerk.learning.issue_manager import IssueManager

        manager = IssueManager(mock_db, mock_task_queue)

        issue = LearningIssue(
            issue_type=IssueType.ERROR_SPIKE,
            severity=IssueSeverity.HIGH,
            priority=2,
            source_agent_code="SD",
            source_level=ScopeLevel.SPECIALIST,
            title="Test issue",
            description="Test description",
        )

        issue_id = await manager.create_issue(issue)

        assert issue_id is not None
        mock_db.execute.assert_called()
        mock_task_queue.enqueue.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, mock_db, mock_task_queue):
        from ag3ntwerk.learning.issue_manager import IssueManager

        # Mock finding existing issue
        mock_db.fetch_one = AsyncMock(return_value={"id": "existing-issue"})

        manager = IssueManager(mock_db, mock_task_queue)

        issue = LearningIssue(
            issue_type=IssueType.ERROR_SPIKE,
            severity=IssueSeverity.HIGH,
            priority=2,
            source_agent_code="SD",
            source_level=ScopeLevel.SPECIALIST,
            title="Duplicate issue",
            description="Should be detected as duplicate",
        )

        issue_id = await manager.create_issue(issue)

        # Should return None for duplicate
        assert issue_id is None
        mock_task_queue.enqueue.assert_not_called()

    @pytest.mark.asyncio
    async def test_severity_priority_mapping(self, mock_db, mock_task_queue):
        from ag3ntwerk.learning.issue_manager import IssueManager

        manager = IssueManager(mock_db)

        assert manager.SEVERITY_PRIORITY[IssueSeverity.CRITICAL] == 1
        assert manager.SEVERITY_PRIORITY[IssueSeverity.HIGH] == 3
        assert manager.SEVERITY_PRIORITY[IssueSeverity.MEDIUM] == 5
        assert manager.SEVERITY_PRIORITY[IssueSeverity.LOW] == 7


# =============================================================================
# Learning Orchestrator Tests
# =============================================================================


class TestLearningOrchestrator:
    """Test LearningOrchestrator functionality."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(return_value=None)
        db.execute = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_register_agents(self, mock_db):
        from ag3ntwerk.learning.orchestrator import LearningOrchestrator

        orchestrator = LearningOrchestrator(mock_db)

        orchestrator.register_executive("Forge", ["AM", "CQM"])
        orchestrator.register_manager("AM", "Forge", ["SD", "CR"])
        orchestrator.register_specialist("SD", "AM", ["code_generation"])

        # Verify registration
        assert "Forge" in orchestrator._agent_loops
        assert "AM" in orchestrator._manager_loops
        assert "SD" in orchestrator._specialist_loops

    @pytest.mark.asyncio
    async def test_record_outcome(self, mock_db):
        from ag3ntwerk.learning.orchestrator import LearningOrchestrator

        orchestrator = LearningOrchestrator(mock_db)
        orchestrator.register_executive("Forge", ["AM"])
        orchestrator.register_manager("AM", "Forge", ["SD"])
        orchestrator.register_specialist("SD", "AM", [])

        hierarchy = HierarchyPath(
            agent="Forge",
            manager="AM",
            specialist="SD",
        )

        outcome_id = await orchestrator.record_outcome(
            task_id="task-123",
            task_type="code_review",
            hierarchy_path=hierarchy,
            success=True,
            duration_ms=1500.0,
        )

        assert outcome_id is not None

    @pytest.mark.asyncio
    async def test_get_task_adjustments(self, mock_db):
        from ag3ntwerk.learning.orchestrator import LearningOrchestrator

        orchestrator = LearningOrchestrator(mock_db)
        orchestrator.register_executive("Forge", [])

        adjustments = await orchestrator.get_task_adjustments(
            task_type="code_review",
            target_agent="Forge",
        )

        assert isinstance(adjustments, LearningAdjustment)

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_db):
        from ag3ntwerk.learning.orchestrator import LearningOrchestrator

        # Mock issue stats
        mock_db.fetch_all = AsyncMock(return_value=[])

        orchestrator = LearningOrchestrator(mock_db)
        orchestrator.register_executive("Forge", ["AM"])
        orchestrator.register_manager("AM", "Forge", ["SD"])
        orchestrator.register_specialist("SD", "AM", [])

        stats = await orchestrator.get_stats()

        assert "loops" in stats
        assert stats["loops"]["agents"] == 1
        assert stats["loops"]["managers"] == 1
        assert stats["loops"]["specialists"] == 1
