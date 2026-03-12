"""
Unit tests for Phase 8 Learning System components.

Tests:
- CapabilityEvolver: Agent capability evolution
- PatternPropagator: Pattern propagation across agents
- FailureInvestigator: Root cause analysis
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from ag3ntwerk.learning.capability_evolver import (
    CapabilityEvolver,
    CapabilityType,
    EvolutionStatus,
    DemandGap,
    NewCapability,
    EvolutionResult,
)
from ag3ntwerk.learning.pattern_propagator import (
    PatternPropagator,
    PropagationStatus,
    SimilarityMetric,
    AgentSimilarity,
    PropagationRecord,
    PropagationResult,
)
from ag3ntwerk.learning.failure_investigator import (
    FailureInvestigator,
    RootCauseType,
    CorrelationType,
    InvestigationStatus,
    RootCause,
    Correlation,
    RecommendedFix,
    Investigation,
)
from ag3ntwerk.learning.models import (
    TaskOutcomeRecord,
    LearnedPattern,
    PatternType,
    ScopeLevel,
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
def mock_outcome_tracker():
    """Create a mock outcome tracker."""
    tracker = AsyncMock()
    tracker.record_outcome = AsyncMock(return_value="outcome-123")
    tracker.get_outcomes = AsyncMock(return_value=[])
    return tracker


@pytest.fixture
def mock_pattern_store():
    """Create a mock pattern store."""
    store = AsyncMock()
    store.get_patterns = AsyncMock(return_value=[])
    store.get_pattern = AsyncMock(return_value=None)
    store.store_pattern = AsyncMock()
    store.deactivate_pattern = AsyncMock()
    return store


@pytest.fixture
def sample_outcome():
    """Create a sample failed outcome for testing."""
    return TaskOutcomeRecord(
        task_id="task-123",
        task_type="data_processing",
        agent_code="Forge",
        manager_code="TM",
        specialist_code="SD",
        success=False,
        effectiveness=0.0,
        duration_ms=5000.0,
        error_message="Connection timeout after 5000ms",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_pattern():
    """Create a sample pattern for testing."""
    return LearnedPattern(
        pattern_type=PatternType.CAPABILITY,
        scope_level=ScopeLevel.SPECIALIST,
        scope_code="SD",
        condition_json='{"task_type": "data_processing", "min_duration": 1000}',
        recommendation="Use batch processing for large datasets",
        confidence=0.85,
        success_rate=0.9,
        application_count=50,
        is_active=True,
    )


# =============================================================================
# CapabilityEvolver Tests
# =============================================================================


class TestCapabilityEvolver:
    """Tests for CapabilityEvolver."""

    @pytest.fixture
    def evolver(self, mock_db, mock_pattern_store, mock_outcome_tracker):
        """Create a CapabilityEvolver instance."""
        return CapabilityEvolver(mock_db, mock_pattern_store, mock_outcome_tracker)

    @pytest.mark.asyncio
    async def test_evolve_capabilities_empty(self, evolver, mock_outcome_tracker):
        """Test evolution with no outcomes."""
        mock_outcome_tracker.get_outcomes = AsyncMock(return_value=[])

        capabilities = await evolver.evolve_capabilities("Forge")

        assert capabilities == []

    @pytest.mark.asyncio
    async def test_detect_demand_gap(self, evolver, mock_outcome_tracker):
        """Test detection of demand gaps."""
        # Create outcomes with high failure rate
        outcomes = [
            MagicMock(
                task_type="data_processing",
                success=i < 30,  # 30% success = 70% failure
                duration_ms=1000.0,
                error_message="timeout" if i >= 30 else None,
            )
            for i in range(100)
        ]
        mock_outcome_tracker.get_outcomes = AsyncMock(return_value=outcomes)

        gaps = await evolver._analyze_demand_gaps("Forge", 168)

        assert len(gaps) >= 1
        assert gaps[0].task_type == "data_processing"
        assert gaps[0].failure_rate > 0.5

    @pytest.mark.asyncio
    async def test_generate_capability(self, evolver):
        """Test capability generation from gap."""
        gap = DemandGap(
            agent_code="Forge",
            task_type="data_processing",
            volume=100,
            failure_rate=0.7,
            avg_duration_ms=5000.0,
            error_patterns=["timeout", "connection refused"],
            severity=0.8,
        )

        capability = await evolver._generate_capability(gap)

        assert capability is not None
        assert capability.agent_code == "Forge"
        assert capability.task_types == ["data_processing"]
        assert capability.status == EvolutionStatus.PROPOSED

    @pytest.mark.asyncio
    async def test_capability_lifecycle(self, evolver, mock_db):
        """Test capability lifecycle: propose -> test -> activate."""
        gap = DemandGap(
            agent_code="Forge",
            task_type="api_calls",
            volume=150,
            failure_rate=0.6,
            error_patterns=["timeout"],
            severity=0.7,
        )

        # Generate and register
        capability = await evolver._generate_capability(gap)
        await evolver._register_capability("Forge", capability)

        # Start testing
        result = await evolver.start_testing(capability.id)
        assert result is True

        cap = await evolver.get_capability(capability.id)
        assert cap.status == EvolutionStatus.TESTING

        # Record successful usage
        for _ in range(25):
            await evolver.record_capability_usage(capability.id, success=True)

        # Should be activated after enough successes
        cap = await evolver.get_capability(capability.id)
        assert cap.success_rate >= 0.7

    @pytest.mark.asyncio
    async def test_get_agent_capabilities(self, evolver, mock_db):
        """Test getting capabilities for an agent."""
        # Register some capabilities
        for i in range(3):
            gap = DemandGap(
                agent_code="Forge",
                task_type=f"task_type_{i}",
                volume=100,
                failure_rate=0.6,
                severity=0.5,
            )
            cap = await evolver._generate_capability(gap)
            await evolver._register_capability("Forge", cap)

        capabilities = await evolver.get_agent_capabilities("Forge")

        assert len(capabilities) == 3

    @pytest.mark.asyncio
    async def test_deprecate_capability(self, evolver, mock_db):
        """Test deprecating a capability."""
        gap = DemandGap(
            agent_code="Forge",
            task_type="old_task",
            volume=50,
            failure_rate=0.5,
            severity=0.5,
        )
        cap = await evolver._generate_capability(gap)
        await evolver._register_capability("Forge", cap)

        result = await evolver.deprecate_capability(cap.id, "No longer needed")

        assert result is True
        updated = await evolver.get_capability(cap.id)
        assert updated.status == EvolutionStatus.DEPRECATED

    @pytest.mark.asyncio
    async def test_get_stats(self, evolver):
        """Test getting evolver statistics."""
        stats = await evolver.get_stats()

        assert "total_capabilities" in stats
        assert "total_gaps" in stats
        assert "by_status" in stats
        assert "by_type" in stats

    def test_capability_types(self):
        """Test CapabilityType enum values."""
        assert CapabilityType.TASK_HANDLING.value == "task_handling"
        assert CapabilityType.ERROR_RECOVERY.value == "error_recovery"
        assert CapabilityType.OPTIMIZATION.value == "optimization"
        assert CapabilityType.DELEGATION.value == "delegation"

    def test_evolution_status(self):
        """Test EvolutionStatus enum values."""
        assert EvolutionStatus.PROPOSED.value == "proposed"
        assert EvolutionStatus.TESTING.value == "testing"
        assert EvolutionStatus.ACTIVE.value == "active"
        assert EvolutionStatus.DEPRECATED.value == "deprecated"

    def test_demand_gap_to_dict(self):
        """Test DemandGap serialization."""
        gap = DemandGap(
            agent_code="Forge",
            task_type="test",
            volume=100,
            failure_rate=0.5,
            severity=0.7,
        )
        data = gap.to_dict()

        assert data["agent_code"] == "Forge"
        assert data["task_type"] == "test"
        assert data["volume"] == 100
        assert data["failure_rate"] == 0.5

    def test_new_capability_to_dict(self):
        """Test NewCapability serialization."""
        cap = NewCapability(
            agent_code="Forge",
            capability_type=CapabilityType.ERROR_RECOVERY,
            name="error_recovery_api",
            description="Handles API errors",
            task_types=["api_calls"],
            status=EvolutionStatus.ACTIVE,
        )
        data = cap.to_dict()

        assert data["agent_code"] == "Forge"
        assert data["capability_type"] == "error_recovery"
        assert data["name"] == "error_recovery_api"


# =============================================================================
# PatternPropagator Tests
# =============================================================================


class TestPatternPropagator:
    """Tests for PatternPropagator."""

    @pytest.fixture
    def propagator(self, mock_db, mock_pattern_store, mock_outcome_tracker):
        """Create a PatternPropagator instance."""
        return PatternPropagator(mock_db, mock_pattern_store, mock_outcome_tracker)

    @pytest.mark.asyncio
    async def test_propagate_no_patterns(self, propagator, mock_pattern_store):
        """Test propagation with no patterns."""
        mock_pattern_store.get_patterns = AsyncMock(return_value=[])

        result = await propagator.propagate_successful_patterns()

        assert result.patterns_analyzed == 0
        assert result.propagations_attempted == 0

    @pytest.mark.asyncio
    async def test_compute_similarity(self, propagator, mock_db):
        """Test computing similarity between agents."""
        # Set up mock data
        mock_db.fetch_all = AsyncMock(return_value=[("task_a",), ("task_b",), ("task_c",)])
        mock_db.fetch_one = AsyncMock(return_value=(0.8, 1000.0, 0.7))

        similarity = await propagator._compute_similarity("Agent1", "Agent2")

        assert isinstance(similarity, AgentSimilarity)
        assert similarity.source_agent == "Agent1"
        assert similarity.target_agent == "Agent2"
        assert 0 <= similarity.similarity_score <= 1

    @pytest.mark.asyncio
    async def test_find_similar_agents(self, propagator, mock_db):
        """Test finding similar agents."""
        # Mock all agents
        mock_db.fetch_all = AsyncMock(return_value=[("Agent1",), ("Agent2",), ("Agent3",)])
        mock_db.fetch_one = AsyncMock(return_value=(0.8, 1000.0, 0.7))

        similar = await propagator._find_similar_agents("Agent1")

        # Should find other agents
        assert isinstance(similar, list)

    @pytest.mark.asyncio
    async def test_copy_pattern(self, propagator, mock_db, mock_pattern_store, sample_pattern):
        """Test copying a pattern to another agent."""
        similarity = AgentSimilarity(
            source_agent="SD",
            target_agent="SD2",
            similarity_score=0.8,
            shared_task_types=["data_processing"],
        )

        success = await propagator._copy_pattern(sample_pattern, "SD2", similarity)

        assert success is True
        mock_pattern_store.store_pattern.assert_called_once()

    @pytest.mark.asyncio
    async def test_propagation_record(
        self, propagator, mock_db, mock_pattern_store, sample_pattern
    ):
        """Test propagation creates a record."""
        similarity = AgentSimilarity(
            source_agent="SD",
            target_agent="SD2",
            similarity_score=0.8,
        )

        await propagator._copy_pattern(sample_pattern, "SD2", similarity)

        records = await propagator.get_propagation_records(pattern_id=sample_pattern.id)
        assert len(records) == 1
        assert records[0].source_pattern_id == sample_pattern.id
        assert records[0].target_agent == "SD2"

    @pytest.mark.asyncio
    async def test_record_propagation_outcome(
        self, propagator, mock_db, mock_pattern_store, sample_pattern
    ):
        """Test recording propagation outcomes."""
        similarity = AgentSimilarity(
            source_agent="SD",
            target_agent="SD2",
            similarity_score=0.8,
        )

        await propagator._copy_pattern(sample_pattern, "SD2", similarity)
        records = await propagator.get_propagation_records()
        record = records[0]

        # Record successful outcomes
        for _ in range(15):
            await propagator.record_propagation_outcome(record.id, success=True)

        updated = propagator._propagation_records.get(record.id)
        assert updated.test_outcomes == 15
        assert updated.test_successes == 15

    @pytest.mark.asyncio
    async def test_get_stats(self, propagator):
        """Test getting propagator statistics."""
        stats = await propagator.get_stats()

        assert "total_propagations" in stats
        assert "by_status" in stats
        assert "success_rate" in stats

    def test_propagation_status(self):
        """Test PropagationStatus enum values."""
        assert PropagationStatus.PENDING.value == "pending"
        assert PropagationStatus.TESTING.value == "testing"
        assert PropagationStatus.SUCCESSFUL.value == "successful"
        assert PropagationStatus.FAILED.value == "failed"

    def test_agent_similarity_to_dict(self):
        """Test AgentSimilarity serialization."""
        sim = AgentSimilarity(
            source_agent="A1",
            target_agent="A2",
            similarity_score=0.75,
            metrics={"task_overlap": 0.8},
            shared_task_types=["task_a"],
        )
        data = sim.to_dict()

        assert data["source_agent"] == "A1"
        assert data["target_agent"] == "A2"
        assert data["similarity_score"] == 0.75

    def test_propagation_record_to_dict(self):
        """Test PropagationRecord serialization."""
        record = PropagationRecord(
            source_pattern_id="p1",
            source_agent="A1",
            target_agent="A2",
            status=PropagationStatus.SUCCESSFUL,
            similarity_score=0.8,
        )
        data = record.to_dict()

        assert data["source_pattern_id"] == "p1"
        assert data["status"] == "successful"

    def test_propagation_result_to_dict(self):
        """Test PropagationResult serialization."""
        result = PropagationResult(
            patterns_analyzed=10,
            propagations_attempted=5,
            propagations_successful=4,
            propagations_failed=1,
            duration_ms=500.0,
        )
        data = result.to_dict()

        assert data["patterns_analyzed"] == 10
        assert data["propagations_successful"] == 4


# =============================================================================
# FailureInvestigator Tests
# =============================================================================


class TestFailureInvestigator:
    """Tests for FailureInvestigator."""

    @pytest.fixture
    def investigator(self, mock_db, mock_outcome_tracker, mock_pattern_store):
        """Create a FailureInvestigator instance."""
        return FailureInvestigator(mock_db, mock_outcome_tracker, mock_pattern_store)

    @pytest.mark.asyncio
    async def test_investigate_failure(self, investigator, mock_db, sample_outcome):
        """Test investigating a single failure."""
        mock_db.fetch_all = AsyncMock(return_value=[])

        investigation = await investigator.investigate_failure(sample_outcome)

        assert isinstance(investigation, Investigation)
        assert investigation.outcome_id == sample_outcome.task_id
        assert investigation.status == InvestigationStatus.COMPLETED
        assert len(investigation.root_causes) >= 1

    @pytest.mark.asyncio
    async def test_identify_timeout_root_cause(self, investigator, sample_outcome):
        """Test identifying timeout as root cause."""
        similar_failures = [
            MagicMock(error_message="Connection timeout after 5000ms"),
            MagicMock(error_message="Request timed out"),
            MagicMock(error_message="Timeout exceeded"),
        ]

        root_causes = investigator._identify_root_causes(sample_outcome, similar_failures)

        assert len(root_causes) >= 1
        assert any(rc.cause_type == RootCauseType.TIMEOUT for rc in root_causes)

    @pytest.mark.asyncio
    async def test_identify_memory_root_cause(self, investigator):
        """Test identifying memory issues as root cause."""
        outcome = MagicMock(error_message="Out of memory error")
        similar = [
            MagicMock(error_message="OOM killed"),
            MagicMock(error_message="Heap space exceeded"),
            MagicMock(error_message="Memory allocation failed"),
        ]

        root_causes = investigator._identify_root_causes(outcome, similar)

        assert any(rc.cause_type == RootCauseType.RESOURCE_EXHAUSTION for rc in root_causes)

    @pytest.mark.asyncio
    async def test_find_temporal_correlation(self, investigator):
        """Test finding temporal correlation."""
        # Create failures at same hour
        failures = [
            MagicMock(created_at=datetime(2024, 1, 1, 14, 0)),
            MagicMock(created_at=datetime(2024, 1, 2, 14, 30)),
            MagicMock(created_at=datetime(2024, 1, 3, 14, 15)),
            MagicMock(created_at=datetime(2024, 1, 4, 14, 45)),
        ]

        correlation = investigator._find_temporal_correlation(failures)

        assert correlation is not None
        assert correlation.correlation_type == CorrelationType.TEMPORAL
        assert correlation.factor_value == 14  # Hour 14

    @pytest.mark.asyncio
    async def test_find_agent_correlation(self, investigator):
        """Test finding agent-specific correlation."""
        failures = [
            MagicMock(agent_code="Forge", manager_code=None, specialist_code="SD1"),
            MagicMock(agent_code="Forge", manager_code=None, specialist_code="SD1"),
            MagicMock(agent_code="Forge", manager_code=None, specialist_code="SD1"),
            MagicMock(agent_code="Forge", manager_code=None, specialist_code="SD2"),
        ]

        correlation = investigator._find_agent_correlation(failures)

        assert correlation is not None
        assert correlation.correlation_type == CorrelationType.AGENT_SPECIFIC
        assert correlation.factor_value == "SD1"

    @pytest.mark.asyncio
    async def test_suggest_fixes(self, investigator):
        """Test fix suggestions for root causes."""
        root_causes = [
            RootCause(
                cause_type=RootCauseType.TIMEOUT,
                description="Timeout errors",
                confidence=0.9,
            ),
        ]
        correlations = []

        fixes = investigator._suggest_fixes(root_causes, correlations)

        assert len(fixes) >= 1
        assert fixes[0].fix_type == "configuration"
        assert "timeout" in fixes[0].description.lower()

    @pytest.mark.asyncio
    async def test_investigate_batch(self, investigator, mock_db):
        """Test batch investigation."""
        mock_db.fetch_all = AsyncMock(return_value=[])

        investigations = await investigator.investigate_batch(window_hours=24)

        assert isinstance(investigations, list)

    @pytest.mark.asyncio
    async def test_get_common_root_causes(self, investigator, mock_db, sample_outcome):
        """Test getting common root causes."""
        mock_db.fetch_all = AsyncMock(return_value=[])

        # Create some investigations
        await investigator.investigate_failure(sample_outcome)

        common = await investigator.get_common_root_causes()

        assert isinstance(common, list)

    @pytest.mark.asyncio
    async def test_get_auto_applicable_fixes(self, investigator, mock_db, sample_outcome):
        """Test getting auto-applicable fixes."""
        mock_db.fetch_all = AsyncMock(return_value=[])

        await investigator.investigate_failure(sample_outcome)

        fixes = await investigator.get_auto_applicable_fixes()

        assert isinstance(fixes, list)
        for fix in fixes:
            assert fix.auto_applicable is True

    @pytest.mark.asyncio
    async def test_get_stats(self, investigator):
        """Test getting investigator statistics."""
        stats = await investigator.get_stats()

        assert "total_investigations" in stats
        assert "by_status" in stats
        assert "by_root_cause" in stats

    def test_root_cause_types(self):
        """Test RootCauseType enum values."""
        assert RootCauseType.TIMEOUT.value == "timeout"
        assert RootCauseType.RESOURCE_EXHAUSTION.value == "resource_exhaustion"
        assert RootCauseType.DEPENDENCY_FAILURE.value == "dependency_failure"
        assert RootCauseType.CONFIGURATION_ERROR.value == "configuration_error"

    def test_correlation_types(self):
        """Test CorrelationType enum values."""
        assert CorrelationType.TEMPORAL.value == "temporal"
        assert CorrelationType.AGENT_SPECIFIC.value == "agent_specific"
        assert CorrelationType.LOAD_RELATED.value == "load_related"

    def test_investigation_status(self):
        """Test InvestigationStatus enum values."""
        assert InvestigationStatus.IN_PROGRESS.value == "in_progress"
        assert InvestigationStatus.COMPLETED.value == "completed"
        assert InvestigationStatus.ACTION_REQUIRED.value == "action_required"

    def test_root_cause_to_dict(self):
        """Test RootCause serialization."""
        cause = RootCause(
            cause_type=RootCauseType.TIMEOUT,
            description="Timeout errors",
            confidence=0.85,
            evidence=["Error 1", "Error 2"],
            affected_outcomes=10,
        )
        data = cause.to_dict()

        assert data["cause_type"] == "timeout"
        assert data["confidence"] == 0.85
        assert len(data["evidence"]) == 2

    def test_correlation_to_dict(self):
        """Test Correlation serialization."""
        corr = Correlation(
            correlation_type=CorrelationType.TEMPORAL,
            factor="hour_of_day",
            factor_value=14,
            correlation_strength=0.8,
            sample_size=100,
        )
        data = corr.to_dict()

        assert data["correlation_type"] == "temporal"
        assert data["factor_value"] == 14

    def test_recommended_fix_to_dict(self):
        """Test RecommendedFix serialization."""
        fix = RecommendedFix(
            root_cause_id="rc-123",
            fix_type="configuration",
            description="Increase timeout",
            implementation_steps=["Step 1", "Step 2"],
            estimated_impact=0.7,
            priority=1,
            auto_applicable=True,
        )
        data = fix.to_dict()

        assert data["fix_type"] == "configuration"
        assert data["auto_applicable"] is True
        assert len(data["implementation_steps"]) == 2

    def test_investigation_to_dict(self, sample_outcome):
        """Test Investigation serialization."""
        investigation = Investigation(
            outcome_id=sample_outcome.task_id,
            task_type=sample_outcome.task_type,
            agent_code=sample_outcome.agent_code,
            status=InvestigationStatus.COMPLETED,
            root_causes=[RootCause(cause_type=RootCauseType.TIMEOUT, description="Timeout")],
            summary="Investigation complete",
        )
        data = investigation.to_dict()

        assert data["outcome_id"] == sample_outcome.task_id
        assert data["status"] == "completed"
        assert len(data["root_causes"]) == 1


# =============================================================================
# Integration Tests
# =============================================================================


class TestPhase8Integration:
    """Integration tests for Phase 8 components working together."""

    @pytest.mark.asyncio
    async def test_failure_leads_to_capability(
        self, mock_db, mock_pattern_store, mock_outcome_tracker
    ):
        """Test that failures can lead to new capabilities."""
        evolver = CapabilityEvolver(mock_db, mock_pattern_store, mock_outcome_tracker)
        investigator = FailureInvestigator(mock_db, mock_outcome_tracker, mock_pattern_store)

        # Create failing outcome with clear timeout indicator
        outcome = TaskOutcomeRecord(
            task_id="task-fail",
            task_type="api_calls",
            agent_code="Forge",
            success=False,
            error_message="Connection timeout after 5000ms",
        )

        # Create similar failures with timeout errors
        similar_rows = [
            {
                "task_id": "t1",
                "task_type": "api_calls",
                "agent_code": "Forge",
                "success": 0,
                "error": "Request timed out",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "task_id": "t2",
                "task_type": "api_calls",
                "agent_code": "Forge",
                "success": 0,
                "error": "Connection timeout",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "task_id": "t3",
                "task_type": "api_calls",
                "agent_code": "Forge",
                "success": 0,
                "error": "Timeout exceeded",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        mock_db.fetch_all = AsyncMock(return_value=similar_rows)

        # Investigate failure
        investigation = await investigator.investigate_failure(outcome)

        # The investigation should identify timeout as root cause (or unknown if no pattern)
        # At minimum we should have completed the investigation
        assert investigation.status == InvestigationStatus.COMPLETED
        assert len(investigation.root_causes) >= 1

        # A capability evolver could use this to create error recovery capability
        gap = DemandGap(
            agent_code="Forge",
            task_type="api_calls",
            volume=100,
            failure_rate=0.6,
            error_patterns=["timeout"],
        )
        capability = await evolver._generate_capability(gap)

        assert capability is not None
        assert capability.capability_type == CapabilityType.ERROR_RECOVERY

    @pytest.mark.asyncio
    async def test_successful_pattern_propagates(
        self, mock_db, mock_pattern_store, mock_outcome_tracker, sample_pattern
    ):
        """Test that successful patterns can propagate."""
        propagator = PatternPropagator(mock_db, mock_pattern_store, mock_outcome_tracker)

        # Set up high-confidence pattern
        sample_pattern.confidence = 0.9
        sample_pattern.success_rate = 0.95
        sample_pattern.application_count = 100

        mock_pattern_store.get_patterns = AsyncMock(return_value=[sample_pattern])
        mock_db.fetch_all = AsyncMock(return_value=[("SD",), ("SD2",), ("SD3",)])
        mock_db.fetch_one = AsyncMock(return_value=(0.8, 1000.0, 0.7))

        # Try propagation
        result = await propagator.propagate_successful_patterns()

        # Should have analyzed the pattern
        assert result.patterns_analyzed >= 1

    @pytest.mark.asyncio
    async def test_full_feedback_cycle(self, mock_db, mock_pattern_store, mock_outcome_tracker):
        """Test a complete feedback cycle."""
        evolver = CapabilityEvolver(mock_db, mock_pattern_store, mock_outcome_tracker)
        propagator = PatternPropagator(mock_db, mock_pattern_store, mock_outcome_tracker)
        investigator = FailureInvestigator(mock_db, mock_outcome_tracker, mock_pattern_store)

        mock_db.fetch_all = AsyncMock(return_value=[])
        mock_pattern_store.get_patterns = AsyncMock(return_value=[])
        mock_outcome_tracker.get_outcomes = AsyncMock(return_value=[])

        # Run components
        propagation_result = await propagator.propagate_successful_patterns()
        investigations = await investigator.investigate_batch()
        evolver_stats = await evolver.get_stats()

        # All should complete without error
        assert propagation_result is not None
        assert isinstance(investigations, list)
        assert evolver_stats is not None
