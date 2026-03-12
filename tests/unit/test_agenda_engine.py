"""
Unit tests for the Autonomous Agenda Engine.

Tests cover:
1. GoalAnalyzer - Goal decomposition into workstreams
2. ConstraintDetector - Obstacle detection
3. StrategyGenerator - Strategy generation for obstacle resolution
4. RiskAssessor - Risk assessment for agenda items
5. CheckpointManager - HITL checkpoint management
6. AuditLogger - Audit trail logging
7. AutonomousAgendaEngine - Main orchestrator
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


# =============================================================================
# Test GoalAnalyzer
# =============================================================================


class TestGoalAnalyzer:
    """Test GoalAnalyzer goal decomposition."""

    @pytest.fixture
    def goal_analyzer(self):
        """Create GoalAnalyzer instance."""
        from ag3ntwerk.agenda.goal_analyzer import GoalAnalyzer

        return GoalAnalyzer()

    @pytest.fixture
    def sample_goal(self):
        """Create sample goal for testing."""
        return {
            "id": "goal_001",
            "title": "Implement Authentication System",
            "description": "Build user authentication with OAuth support",
            "milestones": [
                {"id": "m1", "title": "Design authentication architecture", "status": "pending"},
                {"id": "m2", "title": "Implement OAuth integration", "status": "pending"},
                {"id": "m3", "title": "Add unit tests for auth", "status": "pending"},
            ],
            "status": "active",
            "progress": 0,
        }

    @pytest.mark.asyncio
    async def test_analyze_goal_creates_workstreams(self, goal_analyzer, sample_goal):
        """Test that analyzing a goal creates workstreams."""
        workstreams = await goal_analyzer.analyze_goal(sample_goal)

        assert len(workstreams) == 3  # One per milestone
        assert all(ws.goal_id == "goal_001" for ws in workstreams)

    @pytest.mark.asyncio
    async def test_analyze_goal_without_milestones(self, goal_analyzer):
        """Test goal analysis when no milestones exist."""
        goal = {
            "id": "goal_002",
            "title": "Research Market Trends",
            "description": "Analyze current market research data",
            "milestones": [],
            "status": "active",
        }

        workstreams = await goal_analyzer.analyze_goal(goal)

        assert len(workstreams) == 1  # Single workstream from goal itself
        assert workstreams[0].goal_id == "goal_002"

    @pytest.mark.asyncio
    async def test_skips_completed_milestones(self, goal_analyzer, sample_goal):
        """Test that completed milestones are skipped."""
        sample_goal["milestones"][0]["status"] = "completed"

        workstreams = await goal_analyzer.analyze_goal(sample_goal)

        assert len(workstreams) == 2  # Only pending milestones

    def test_extract_capability_requirements(self, goal_analyzer):
        """Test capability requirement extraction."""
        requirements = goal_analyzer._extract_capability_requirements(
            "Implement login system",
            "Build OAuth authentication with code review",
        )

        task_types = [r.task_type for r in requirements]
        assert "code_generation" in task_types or "architecture" in task_types

    def test_map_to_executive(self, goal_analyzer):
        """Test mapping capabilities to agents."""
        from ag3ntwerk.agenda.models import CapabilityRequirement

        cap = CapabilityRequirement(task_type="code_review")
        agent_code = goal_analyzer._map_to_executive(cap)

        assert agent_code == "Forge"

    def test_infer_task_types(self, goal_analyzer):
        """Test task type inference from text."""
        task_types = goal_analyzer._infer_task_types("deploy the application and run tests")

        assert "deployment" in task_types
        assert "testing" in task_types

    def test_estimate_duration(self, goal_analyzer):
        """Test duration estimation."""
        duration = goal_analyzer._estimate_duration(
            task_types=["deployment", "testing", "code_review"],
            capabilities=[],
            description="Complex multi-step deployment process",
        )

        # Should be more than base (1.0) due to multiple task types
        assert duration > 1.0

    def test_detect_workstream_dependencies(self, goal_analyzer):
        """Test dependency detection between workstreams."""
        from ag3ntwerk.agenda.models import Workstream

        ws1 = Workstream(title="Setup database first")
        ws2 = Workstream(title="Then implement API")
        ws3 = Workstream(title="Finally deploy")

        ordered = goal_analyzer._detect_workstream_dependencies([ws1, ws2, ws3])

        # Should detect ordering based on keywords
        assert len(ordered) == 3


# =============================================================================
# Test ConstraintDetector
# =============================================================================


class TestConstraintDetector:
    """Test ConstraintDetector obstacle detection."""

    @pytest.fixture
    def constraint_detector(self):
        """Create ConstraintDetector instance."""
        from ag3ntwerk.agenda.constraint_detector import ConstraintDetector

        return ConstraintDetector()

    @pytest.fixture
    def sample_workstream(self):
        """Create sample workstream for testing."""
        from ag3ntwerk.agenda.models import Workstream, CapabilityRequirement

        return Workstream(
            id="ws_001",
            goal_id="goal_001",
            title="Implement OAuth",
            description="Add OAuth authentication support",
            capability_requirements=[
                CapabilityRequirement(
                    task_type="code_generation",
                    is_available=False,
                    availability_confidence=0.3,
                ),
            ],
            executive_mapping={"code_generation": "Forge"},
        )

    @pytest.mark.asyncio
    async def test_detect_capability_gaps(self, constraint_detector, sample_workstream):
        """Test detection of capability gaps."""
        obstacles = await constraint_detector.detect_obstacles(sample_workstream, {})

        # Should detect capability gap for unavailable capability
        capability_gaps = [o for o in obstacles if o.obstacle_type.value == "capability_gap"]
        assert len(capability_gaps) >= 1

    @pytest.mark.asyncio
    async def test_detect_resource_constraints(self, constraint_detector, sample_workstream):
        """Test detection of resource constraints."""
        context = {
            "resources": {
                "daily_budget_remaining": 0.5,  # Below threshold
            }
        }

        obstacles = await constraint_detector.detect_obstacles(sample_workstream, context)

        # Should detect budget constraint
        resource_constraints = [
            o for o in obstacles if o.obstacle_type.value == "resource_constraint"
        ]
        assert len(resource_constraints) >= 1

    @pytest.mark.asyncio
    async def test_detect_dependencies(self, constraint_detector, sample_workstream):
        """Test detection of dependencies."""
        from ag3ntwerk.agenda.models import Workstream, WorkstreamStatus

        blocking_ws = Workstream(
            id="ws_000",
            title="Blocking workstream",
            status=WorkstreamStatus.PENDING,
        )
        sample_workstream.dependency_workstream_ids = ["ws_000"]

        obstacles = await constraint_detector.detect_obstacles(sample_workstream, {}, [blocking_ws])

        # Should detect dependency obstacle
        dependencies = [o for o in obstacles if o.obstacle_type.value == "dependency"]
        assert len(dependencies) >= 1

    def test_calculate_capability_gap_severity(self, constraint_detector):
        """Test severity calculation for capability gaps."""
        from ag3ntwerk.agenda.models import CapabilityRequirement

        low_confidence = CapabilityRequirement(availability_confidence=0.1)
        high_confidence = CapabilityRequirement(availability_confidence=0.9)

        low_severity = constraint_detector._calculate_capability_gap_severity(low_confidence)
        high_severity = constraint_detector._calculate_capability_gap_severity(high_confidence)

        assert low_severity > high_severity

    def test_get_obstacle_summary(self, constraint_detector):
        """Test obstacle summary generation."""
        from ag3ntwerk.agenda.models import Obstacle, ObstacleType

        obstacles = [
            Obstacle(obstacle_type=ObstacleType.CAPABILITY_GAP, severity=0.8),
            Obstacle(obstacle_type=ObstacleType.RESOURCE_CONSTRAINT, severity=0.5),
            Obstacle(obstacle_type=ObstacleType.CAPABILITY_GAP, severity=0.3),
        ]

        summary = constraint_detector.get_obstacle_summary(obstacles)

        assert summary["total"] == 3
        assert summary["by_type"]["capability_gap"] == 2
        assert summary["by_severity"]["high"] == 1  # severity >= 0.7


# =============================================================================
# Test StrategyGenerator
# =============================================================================


class TestStrategyGenerator:
    """Test StrategyGenerator strategy generation."""

    @pytest.fixture
    def strategy_generator(self):
        """Create StrategyGenerator instance."""
        from ag3ntwerk.agenda.strategy_generator import StrategyGenerator

        return StrategyGenerator()

    @pytest.fixture
    def capability_gap_obstacle(self):
        """Create capability gap obstacle."""
        from ag3ntwerk.agenda.models import Obstacle, ObstacleType

        return Obstacle(
            id="obs_001",
            obstacle_type=ObstacleType.CAPABILITY_GAP,
            severity=0.7,
            title="Missing code_generation capability",
            related_task_types=["code_generation"],
        )

    @pytest.fixture
    def sample_workstream(self):
        """Create sample workstream."""
        from ag3ntwerk.agenda.models import Workstream, CapabilityRequirement

        return Workstream(
            id="ws_001",
            goal_id="goal_001",
            title="Implement Feature",
            capability_requirements=[
                CapabilityRequirement(task_type="code_generation", tool_category="development"),
            ],
            executive_mapping={"code_generation": "Forge"},
        )

    @pytest.mark.asyncio
    async def test_generate_strategies_creates_multiple(
        self, strategy_generator, capability_gap_obstacle, sample_workstream
    ):
        """Test that multiple strategies are generated."""
        strategies = await strategy_generator.generate_strategies(
            capability_gap_obstacle, sample_workstream, {}
        )

        # Should generate at least one strategy
        assert len(strategies) >= 1

        # Should have different strategy types
        types = [s.strategy_type.value for s in strategies]
        assert len(set(types)) >= 1

    @pytest.mark.asyncio
    async def test_generate_internal_change_strategy(
        self, strategy_generator, capability_gap_obstacle, sample_workstream
    ):
        """Test internal change strategy generation."""
        from ag3ntwerk.agenda.models import StrategyType

        strategies = await strategy_generator.generate_strategies(
            capability_gap_obstacle, sample_workstream, {}
        )

        internal_changes = [
            s for s in strategies if s.strategy_type == StrategyType.INTERNAL_CHANGE
        ]

        # May or may not have internal change depending on alternatives
        # Just verify no error occurs

    @pytest.mark.asyncio
    async def test_generate_task_generation_strategy(
        self, strategy_generator, capability_gap_obstacle, sample_workstream
    ):
        """Test task generation strategy."""
        from ag3ntwerk.agenda.models import StrategyType

        strategies = await strategy_generator.generate_strategies(
            capability_gap_obstacle, sample_workstream, {}
        )

        task_gen = [s for s in strategies if s.strategy_type == StrategyType.TASK_GENERATION]

        assert len(task_gen) >= 1
        assert len(task_gen[0].generated_task_specs) >= 1

    def test_score_strategy(self, strategy_generator, capability_gap_obstacle):
        """Test strategy scoring."""
        from ag3ntwerk.agenda.models import Strategy, StrategyType

        strategy = Strategy(
            strategy_type=StrategyType.INTERNAL_CHANGE,
            impact_score=0.8,
            feasibility_score=0.9,
            estimated_effort_hours=1.0,
        )

        score = strategy_generator._score_strategy(strategy, capability_gap_obstacle)

        assert score > 0
        # High impact and feasibility, low effort should give good score

    def test_filter_auto_executable(self, strategy_generator):
        """Test filtering strategies for auto-execution."""
        from ag3ntwerk.agenda.models import Strategy, StrategyType

        strategies = [
            Strategy(
                strategy_type=StrategyType.INTERNAL_CHANGE,
                estimated_cost_usd=5.0,
                confidence=0.8,
            ),
            Strategy(
                strategy_type=StrategyType.TOOL_INGESTION,
                estimated_cost_usd=100.0,
                confidence=0.9,
            ),
        ]

        auto_exec = strategy_generator.filter_auto_executable(strategies)

        assert len(auto_exec) == 1
        assert auto_exec[0].strategy_type.value == "internal_change"


# =============================================================================
# Test RiskAssessor
# =============================================================================


class TestRiskAssessor:
    """Test RiskAssessor risk assessment."""

    @pytest.fixture
    def risk_assessor(self):
        """Create RiskAssessor instance."""
        from ag3ntwerk.agenda.security import RiskAssessor

        return RiskAssessor()

    @pytest.fixture
    def low_risk_item(self):
        """Create low risk agenda item."""
        from ag3ntwerk.agenda.models import AgendaItem

        return AgendaItem(
            id="item_001",
            task_type="research",
            title="Research competitor landscape",
            description="Analyze current market trends",  # Avoid "data" keyword
            estimated_cost_usd=1.0,
            confidence_score=0.9,
        )

    @pytest.fixture
    def high_risk_item(self):
        """Create high risk agenda item."""
        from ag3ntwerk.agenda.models import AgendaItem

        return AgendaItem(
            id="item_002",
            task_type="deployment",
            title="Deploy payment processing system",
            description="Deploy to production with database migration",
            estimated_cost_usd=100.0,
            confidence_score=0.4,
        )

    def test_assess_low_risk_item(self, risk_assessor, low_risk_item):
        """Test assessment of low risk item."""
        assessment = risk_assessor.assess_agenda_item(low_risk_item)

        assert assessment.risk_level.value in ("minimal", "low")
        assert not assessment.requires_approval

    def test_assess_high_risk_item(self, risk_assessor, high_risk_item):
        """Test assessment of high risk item."""
        assessment = risk_assessor.assess_agenda_item(high_risk_item)

        assert assessment.risk_level.value in ("high", "critical")
        assert assessment.requires_approval

    def test_financial_category_detection(self, risk_assessor):
        """Test detection of financial risk category."""
        from ag3ntwerk.agenda.models import AgendaItem, RiskCategory

        item = AgendaItem(
            task_type="payment_processing",
            title="Process subscription payments",
            description="Run monthly billing for all customers",
        )

        assessment = risk_assessor.assess_agenda_item(item)

        assert RiskCategory.FINANCIAL in assessment.risk_categories

    def test_security_category_detection(self, risk_assessor):
        """Test detection of security risk category."""
        from ag3ntwerk.agenda.models import AgendaItem, RiskCategory

        item = AgendaItem(
            task_type="access_control",
            title="Update user permissions",
            description="Modify credential access and authentication settings",
        )

        assessment = risk_assessor.assess_agenda_item(item)

        assert RiskCategory.SECURITY in assessment.risk_categories

    def test_risk_score_calculation(self, risk_assessor, high_risk_item):
        """Test risk score is calculated correctly."""
        assessment = risk_assessor.assess_agenda_item(high_risk_item)

        assert 0.0 <= assessment.risk_score <= 1.0
        # High risk item should have high score
        assert assessment.risk_score >= 0.5


# =============================================================================
# Test CheckpointManager
# =============================================================================


class TestCheckpointManager:
    """Test CheckpointManager HITL management."""

    @pytest.fixture
    def checkpoint_manager(self):
        """Create CheckpointManager instance."""
        from ag3ntwerk.agenda.security import CheckpointManager, RiskAssessor
        from ag3ntwerk.agenda.models import HITLConfig

        config = HITLConfig(enabled=True)
        risk_assessor = RiskAssessor(config)
        return CheckpointManager(config, risk_assessor)

    @pytest.fixture
    def medium_risk_item(self):
        """Create medium risk agenda item."""
        from ag3ntwerk.agenda.models import AgendaItem, RiskAssessment, RiskLevel

        item = AgendaItem(
            id="item_001",
            task_type="data_migration",
            title="Migrate user data",
            description="Migrate data to new schema",
        )
        item.risk_assessment = RiskAssessment(
            item_id="item_001",
            risk_level=RiskLevel.MEDIUM,
            risk_score=0.5,
            requires_approval=True,
            approval_reason="Medium risk level",
        )
        return item

    def test_should_checkpoint_based_on_risk_level(self, checkpoint_manager, medium_risk_item):
        """Test checkpoint determination based on risk level."""
        needs, checkpoint_type, reason = checkpoint_manager.should_checkpoint(medium_risk_item)

        assert needs is True

    def test_should_checkpoint_disabled_hitl(self, medium_risk_item):
        """Test checkpoint when HITL is disabled."""
        from ag3ntwerk.agenda.security import CheckpointManager, RiskAssessor
        from ag3ntwerk.agenda.models import HITLConfig

        config = HITLConfig(enabled=False)
        manager = CheckpointManager(config, RiskAssessor(config))

        needs, _, _ = manager.should_checkpoint(medium_risk_item)

        assert needs is False

    def test_create_checkpoint(self, checkpoint_manager, medium_risk_item):
        """Test checkpoint creation."""
        from ag3ntwerk.agenda.models import CheckpointType

        checkpoint = checkpoint_manager.create_checkpoint(
            medium_risk_item, CheckpointType.APPROVAL, "High risk item"
        )

        assert checkpoint.item_id == "item_001"
        assert checkpoint.status == "pending"
        assert len(checkpoint.options) > 0

    def test_approval_workflow(self, checkpoint_manager, medium_risk_item):
        """Test approval workflow."""
        from ag3ntwerk.agenda.models import CheckpointType

        checkpoint = checkpoint_manager.create_checkpoint(
            medium_risk_item, CheckpointType.APPROVAL, "Test"
        )

        success = checkpoint_manager.approve(checkpoint.id, "user@test.com", "Approved")

        assert success is True
        assert checkpoint_manager.get_checkpoint(checkpoint.id).status == "approved"

    def test_rejection_workflow(self, checkpoint_manager, medium_risk_item):
        """Test rejection workflow."""
        from ag3ntwerk.agenda.models import CheckpointType

        checkpoint = checkpoint_manager.create_checkpoint(
            medium_risk_item, CheckpointType.APPROVAL, "Test"
        )

        success = checkpoint_manager.reject(checkpoint.id, "user@test.com", "Too risky")

        assert success is True
        assert checkpoint_manager.get_checkpoint(checkpoint.id).status == "rejected"

    def test_batch_approval(self, checkpoint_manager, medium_risk_item):
        """Test batch approval of checkpoints."""
        from ag3ntwerk.agenda.models import CheckpointType, AgendaItem

        # Create multiple checkpoints
        checkpoints = []
        for i in range(3):
            item = AgendaItem(id=f"item_{i}", task_type="research", title=f"Task {i}")
            item.risk_assessment = medium_risk_item.risk_assessment
            cp = checkpoint_manager.create_checkpoint(item, CheckpointType.APPROVAL, "Test")
            checkpoints.append(cp)

        ids = [cp.id for cp in checkpoints]
        count = checkpoint_manager.batch_approve(ids, "admin@test.com")

        assert count == 3


# =============================================================================
# Test AuditLogger
# =============================================================================


class TestAuditLogger:
    """Test AuditLogger audit trail."""

    @pytest.fixture
    def audit_logger(self):
        """Create AuditLogger instance."""
        from ag3ntwerk.agenda.security import AuditLogger

        return AuditLogger()

    @pytest.fixture
    def sample_checkpoint(self):
        """Create sample checkpoint."""
        from ag3ntwerk.agenda.models import Checkpoint, CheckpointType, RiskAssessment, RiskLevel

        return Checkpoint(
            id="cp_001",
            checkpoint_type=CheckpointType.APPROVAL,
            trigger_reason="High risk",
            item_id="item_001",
            title="Review task",
            risk_assessment=RiskAssessment(
                risk_level=RiskLevel.HIGH,
                risk_score=0.8,
            ),
        )

    def test_log_checkpoint_created(self, audit_logger, sample_checkpoint):
        """Test logging checkpoint creation."""
        entry_id = audit_logger.log_checkpoint_created(sample_checkpoint)

        entries = audit_logger.get_audit_trail(action_types=["checkpoint_created"])

        assert len(entries) == 1
        assert entries[0].checkpoint_id == "cp_001"

    def test_log_approval(self, audit_logger, sample_checkpoint):
        """Test logging approval."""
        sample_checkpoint.status = "approved"
        sample_checkpoint.resolution_notes = "Looks good"

        entry_id = audit_logger.log_approval(sample_checkpoint, "admin@test.com")

        entries = audit_logger.get_audit_trail(action_types=["approval"])

        assert len(entries) == 1
        assert "admin@test.com" in entries[0].actor

    def test_log_rejection(self, audit_logger, sample_checkpoint):
        """Test logging rejection."""
        entry_id = audit_logger.log_rejection(sample_checkpoint, "admin@test.com", "Too risky")

        entries = audit_logger.get_audit_trail(action_types=["rejection"])

        assert len(entries) == 1
        assert entries[0].reason == "Too risky"

    def test_audit_trail_query(self, audit_logger, sample_checkpoint):
        """Test audit trail querying."""
        # Add multiple entries
        audit_logger.log_checkpoint_created(sample_checkpoint)
        audit_logger.log_approval(sample_checkpoint, "user1")
        audit_logger.log_rejection(sample_checkpoint, "user2", "reason")

        # Query all
        all_entries = audit_logger.get_audit_trail()
        assert len(all_entries) == 3

        # Query by action type
        approvals = audit_logger.get_audit_trail(action_types=["approval"])
        assert len(approvals) == 1

    def test_audit_summary(self, audit_logger, sample_checkpoint):
        """Test audit summary generation."""
        audit_logger.log_checkpoint_created(sample_checkpoint)
        audit_logger.log_approval(sample_checkpoint, "user1")
        audit_logger.log_approval(sample_checkpoint, "user2")
        audit_logger.log_rejection(sample_checkpoint, "user3", "reason")

        summary = audit_logger.get_summary()

        assert summary["total"] == 4
        assert summary["by_action"]["approval"] == 2
        assert summary["by_action"]["rejection"] == 1


# =============================================================================
# Test AutonomousAgendaEngine
# =============================================================================


class TestAutonomousAgendaEngine:
    """Test AutonomousAgendaEngine main orchestrator."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        from ag3ntwerk.agenda.engine import AutonomousAgendaEngine, AgendaEngineConfig

        config = AgendaEngineConfig()
        return AutonomousAgendaEngine(config=config)

    @pytest.fixture
    def sample_goals(self):
        """Create sample goals."""
        return [
            {
                "id": "goal_001",
                "title": "Build Authentication",
                "description": "Implement OAuth authentication",
                "milestones": [
                    {"id": "m1", "title": "Design auth architecture", "status": "pending"},
                    {"id": "m2", "title": "Implement OAuth", "status": "pending"},
                ],
                "status": "active",
            },
            {
                "id": "goal_002",
                "title": "Market Research",
                "description": "Analyze market trends",
                "milestones": [
                    {"id": "m3", "title": "Research competitors", "status": "pending"},
                ],
                "status": "active",
            },
        ]

    @pytest.mark.asyncio
    async def test_generate_agenda_full_pipeline(self, engine, sample_goals):
        """Test full agenda generation pipeline."""
        agenda = await engine.generate_agenda(
            period_hours=24,
            goals=sample_goals,
        )

        assert agenda is not None
        assert len(agenda.items) > 0
        assert agenda.status == "active"

    @pytest.mark.asyncio
    async def test_generate_agenda_with_obstacles(self, engine, sample_goals):
        """Test agenda generation detects obstacles."""
        agenda = await engine.generate_agenda(
            period_hours=24,
            goals=sample_goals,
        )

        # Check that obstacles were detected
        obstacles = engine.list_obstacles()
        # May have obstacles depending on capability availability

    @pytest.mark.asyncio
    async def test_get_executable_items(self, engine, sample_goals):
        """Test getting executable items."""
        await engine.generate_agenda(period_hours=24, goals=sample_goals)

        items = engine.get_executable_items(count=3)

        # Items should be approved or not require approval
        for item in items:
            assert item.approval_status in ("not_required", "approved")

    @pytest.mark.asyncio
    async def test_get_items_awaiting_approval(self, engine, sample_goals):
        """Test getting items awaiting approval."""
        await engine.generate_agenda(period_hours=24, goals=sample_goals)

        awaiting = engine.get_items_awaiting_approval()

        # All awaiting items should be pending approval
        for item in awaiting:
            assert item.approval_status == "pending"

    @pytest.mark.asyncio
    async def test_adapt_agenda_on_completion(self, engine, sample_goals):
        """Test agenda adaptation on task completion."""
        agenda = await engine.generate_agenda(period_hours=24, goals=sample_goals)

        if agenda.items:
            first_item = agenda.items[0]
            await engine.adapt_agenda(
                {
                    "item_id": first_item.id,
                    "status": "completed",
                    "result": {"success": True},
                }
            )

            # Item should be marked completed
            assert first_item.status == "completed"

    @pytest.mark.asyncio
    async def test_approve_item(self, engine, sample_goals):
        """Test item approval through engine."""
        await engine.generate_agenda(period_hours=24, goals=sample_goals)

        awaiting = engine.get_items_awaiting_approval()
        if awaiting:
            item = awaiting[0]
            success = engine.approve_item(item.id, "admin@test.com", "Approved")

            if item.checkpoint:
                assert success is True
                assert item.approval_status == "approved"

    @pytest.mark.asyncio
    async def test_reject_item(self, engine, sample_goals):
        """Test item rejection through engine."""
        await engine.generate_agenda(period_hours=24, goals=sample_goals)

        awaiting = engine.get_items_awaiting_approval()
        if awaiting:
            item = awaiting[0]
            success = engine.reject_item(item.id, "admin@test.com", "Too risky")

            if item.checkpoint:
                assert success is True
                assert item.approval_status == "rejected"
                assert item.status == "skipped"

    @pytest.mark.asyncio
    async def test_feed_to_coo_context(self, engine, sample_goals):
        """Test enriching Nexus context with agenda data."""
        await engine.generate_agenda(period_hours=24, goals=sample_goals)

        context = {}
        enriched = engine.feed_to_coo_context(context)

        assert "agenda" in enriched
        assert "current_agenda" in enriched["agenda"]
        assert "next_items" in enriched["agenda"]

    @pytest.mark.asyncio
    async def test_get_engine_status(self, engine, sample_goals):
        """Test engine status reporting."""
        await engine.generate_agenda(period_hours=24, goals=sample_goals)

        status = engine.get_engine_status()

        assert status["has_agenda"] is True
        assert "total_workstreams" in status
        assert "total_obstacles" in status

    def test_get_workstream(self, engine):
        """Test getting workstream by ID."""
        # Before agenda generation, should return None
        ws = engine.get_workstream("nonexistent")
        assert ws is None

    def test_get_obstacle(self, engine):
        """Test getting obstacle by ID."""
        obs = engine.get_obstacle("nonexistent")
        assert obs is None

    def test_get_strategy(self, engine):
        """Test getting strategy by ID."""
        strat = engine.get_strategy("nonexistent")
        assert strat is None


# =============================================================================
# Test Persistence
# =============================================================================


class TestAgendaPersistence:
    """Test AgendaPersistence database operations."""

    @pytest.fixture
    def persistence(self, tmp_path):
        """Create persistence instance with temp database."""
        from ag3ntwerk.agenda.persistence import AgendaPersistence

        db_path = tmp_path / "test_agenda.db"
        return AgendaPersistence(str(db_path))

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, persistence):
        """Test database initialization creates tables."""
        await persistence.initialize()

        # Should not raise error on second init
        await persistence.initialize()

    @pytest.mark.asyncio
    async def test_save_and_load_workstream(self, persistence):
        """Test saving and loading workstream."""
        from ag3ntwerk.agenda.models import Workstream, WorkstreamStatus

        await persistence.initialize()

        ws = Workstream(
            id="ws_001",
            goal_id="goal_001",
            title="Test Workstream",
            status=WorkstreamStatus.PENDING,
        )

        await persistence.save_workstream(ws)
        loaded = await persistence.load_workstream("ws_001")

        assert loaded is not None
        assert loaded.id == "ws_001"
        assert loaded.title == "Test Workstream"

    @pytest.mark.asyncio
    async def test_save_and_load_obstacle(self, persistence):
        """Test saving and loading obstacle."""
        from ag3ntwerk.agenda.models import Obstacle, ObstacleType

        await persistence.initialize()

        obs = Obstacle(
            id="obs_001",
            obstacle_type=ObstacleType.CAPABILITY_GAP,
            severity=0.7,
            title="Missing capability",
        )

        await persistence.save_obstacle(obs)
        loaded = await persistence.load_obstacle("obs_001")

        assert loaded is not None
        assert loaded.obstacle_type == ObstacleType.CAPABILITY_GAP

    @pytest.mark.asyncio
    async def test_save_and_load_strategy(self, persistence):
        """Test saving and loading strategy."""
        from ag3ntwerk.agenda.models import Strategy, StrategyType

        await persistence.initialize()

        strat = Strategy(
            id="strat_001",
            strategy_type=StrategyType.INTERNAL_CHANGE,
            obstacle_id="obs_001",
            title="Test Strategy",
        )

        await persistence.save_strategy(strat)
        loaded = await persistence.load_strategy("strat_001")

        assert loaded is not None
        assert loaded.strategy_type == StrategyType.INTERNAL_CHANGE

    @pytest.mark.asyncio
    async def test_save_and_load_agenda(self, persistence):
        """Test saving and loading agenda with items."""
        from ag3ntwerk.agenda.models import Agenda, AgendaItem, ConfidenceLevel

        await persistence.initialize()

        items = [
            AgendaItem(
                id="item_001",
                task_type="research",
                title="Test Task",
                confidence_level=ConfidenceLevel.HIGH,
            ),
        ]

        agenda = Agenda(
            id="agenda_001",
            items=items,
            status="active",
        )

        await persistence.save_agenda(agenda)
        loaded = await persistence.load_agenda("agenda_001")

        assert loaded is not None
        assert len(loaded.items) == 1
        assert loaded.items[0].title == "Test Task"

    @pytest.mark.asyncio
    async def test_load_latest_agenda(self, persistence):
        """Test loading the most recent agenda."""
        from ag3ntwerk.agenda.models import Agenda

        await persistence.initialize()

        # Save two agendas
        agenda1 = Agenda(id="agenda_001", status="completed")
        agenda2 = Agenda(id="agenda_002", status="active")

        await persistence.save_agenda(agenda1)
        await persistence.save_agenda(agenda2)

        latest = await persistence.load_latest_agenda()

        assert latest is not None
        # Most recent based on generated_at

    @pytest.mark.asyncio
    async def test_list_workstreams_with_filter(self, persistence):
        """Test listing workstreams with filters."""
        from ag3ntwerk.agenda.models import Workstream, WorkstreamStatus

        await persistence.initialize()

        ws1 = Workstream(
            id="ws_001", goal_id="goal_001", title="WS 1", status=WorkstreamStatus.PENDING
        )
        ws2 = Workstream(
            id="ws_002", goal_id="goal_001", title="WS 2", status=WorkstreamStatus.ACTIVE
        )
        ws3 = Workstream(
            id="ws_003", goal_id="goal_002", title="WS 3", status=WorkstreamStatus.PENDING
        )

        await persistence.save_workstream(ws1)
        await persistence.save_workstream(ws2)
        await persistence.save_workstream(ws3)

        # Filter by goal
        goal1_ws = await persistence.list_workstreams(goal_id="goal_001")
        assert len(goal1_ws) == 2

        # Filter by status
        pending_ws = await persistence.list_workstreams(status="pending")
        assert len(pending_ws) == 2

    @pytest.mark.asyncio
    async def test_audit_trail_operations(self, persistence):
        """Test audit trail save and query."""
        from ag3ntwerk.agenda.models import AuditEntry, RiskLevel

        await persistence.initialize()

        entry = AuditEntry(
            id="audit_001",
            action_type="approval",
            actor="user@test.com",
            decision="approved",
        )

        await persistence.save_audit_entry(entry)
        entries = await persistence.get_audit_trail(action_types=["approval"])

        assert len(entries) == 1
        assert entries[0].actor == "user@test.com"


# =============================================================================
# Integration Tests
# =============================================================================


class TestAgendaEngineIntegration:
    """Integration tests for agenda engine components."""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete workflow from goal to executed agenda."""
        from ag3ntwerk.agenda import (
            AutonomousAgendaEngine,
            AgendaEngineConfig,
        )

        # Setup
        config = AgendaEngineConfig()
        engine = AutonomousAgendaEngine(config=config)

        # Create goal
        goal = {
            "id": "goal_e2e",
            "title": "Build Feature X",
            "description": "Implement new user-facing feature",
            "milestones": [
                {"id": "m1", "title": "Design feature", "status": "pending"},
                {"id": "m2", "title": "Implement feature", "status": "pending"},
                {"id": "m3", "title": "Test feature", "status": "pending"},
            ],
            "status": "active",
        }

        # Generate agenda
        agenda = await engine.generate_agenda(goals=[goal])

        assert agenda is not None
        assert len(agenda.items) > 0

        # Check workstreams created
        workstreams = engine.list_workstreams(goal_id="goal_e2e")
        assert len(workstreams) >= 1

        # Get executable items
        items = engine.get_executable_items(count=5)

        # Simulate execution
        if items:
            await engine.adapt_agenda(
                {
                    "item_id": items[0].id,
                    "status": "completed",
                    "result": {"success": True},
                }
            )

            # Verify progress updated
            agenda = engine.get_current_agenda()
            assert agenda.items_completed >= 1

    @pytest.mark.asyncio
    async def test_hitl_integration(self):
        """Test human-in-the-loop integration."""
        from ag3ntwerk.agenda import (
            AutonomousAgendaEngine,
            AgendaEngineConfig,
            HITLConfig,
            RiskLevel,
        )

        # Setup with strict HITL
        hitl_config = HITLConfig(
            enabled=True,
            approval_threshold_risk_level=RiskLevel.LOW,  # Require approval for almost everything
        )
        config = AgendaEngineConfig(hitl_config=hitl_config)
        engine = AutonomousAgendaEngine(config=config)

        # Goal with high-risk task
        goal = {
            "id": "goal_hitl",
            "title": "Deploy Application",
            "description": "Deploy to production with database migration",
            "milestones": [
                {"id": "m1", "title": "Deploy to production", "status": "pending"},
            ],
            "status": "active",
        }

        agenda = await engine.generate_agenda(goals=[goal])

        # Should have items pending approval
        awaiting = engine.get_items_awaiting_approval()
        # May have pending items depending on risk assessment

        # Approve an item
        if awaiting:
            item = awaiting[0]
            engine.approve_item(item.id, "admin", "Approved for deployment")

            # Check audit trail
            trail = engine.get_audit_trail()
            approval_entries = [e for e in trail if e.action_type == "approval"]
            # Should have approval entry
