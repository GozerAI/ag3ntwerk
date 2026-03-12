"""
Unit tests for Phase 3 Learning System components.

Tests:
- PatternExperimenter: A/B testing for patterns
- MetaLearner: Self-tuning parameters
- HandlerGenerator: Auto-generated task handlers
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import math

from ag3ntwerk.learning.pattern_experiment import (
    PatternExperimenter,
    PatternExperiment,
    ExperimentResult,
    ExperimentStatus,
    ExperimentConclusion,
    ExperimentGroup,
)
from ag3ntwerk.learning.meta_learner import (
    MetaLearner,
    TunableParameter,
    EffectivenessMetrics,
    TuningResult,
    ParameterCategory,
)
from ag3ntwerk.learning.handler_generator import (
    HandlerGenerator,
    GeneratedHandler,
    HandlerCandidate,
    HandlerStatus,
)
from ag3ntwerk.learning.models import (
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
def mock_pattern_store():
    """Create a mock pattern store."""
    store = AsyncMock()
    store.get_pattern = AsyncMock(return_value=None)
    store.get_patterns = AsyncMock(return_value=[])
    store.store_pattern = AsyncMock(return_value="pattern-123")
    store.update_pattern = AsyncMock()
    store.update_pattern_confidence = AsyncMock()
    store.deactivate_pattern = AsyncMock()
    return store


@pytest.fixture
def sample_pattern():
    """Create a sample pattern for testing."""
    return LearnedPattern(
        pattern_type=PatternType.ROUTING,
        scope_level=ScopeLevel.AGENT,
        scope_code="Forge",
        condition_json='{"task_type": "code_review"}',
        recommendation="Route to CQM for code reviews",
        confidence=0.75,
        sample_size=50,
        success_rate=0.85,
    )


@pytest.fixture
def experimenter(mock_db, mock_pattern_store):
    """Create a PatternExperimenter instance."""
    return PatternExperimenter(mock_db, mock_pattern_store)


@pytest.fixture
def meta_learner(mock_db):
    """Create a MetaLearner instance."""
    return MetaLearner(mock_db)


@pytest.fixture
def handler_generator(mock_db, mock_pattern_store):
    """Create a HandlerGenerator instance."""
    return HandlerGenerator(mock_db, mock_pattern_store)


# =============================================================================
# PatternExperimenter Tests
# =============================================================================


class TestPatternExperimenter:
    """Tests for A/B testing functionality."""

    @pytest.mark.asyncio
    async def test_create_experiment(self, experimenter):
        """Test creating a new experiment."""
        experiment = await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
            pattern_type="routing",
            target_sample_size=100,
            traffic_percentage=0.5,
        )

        assert experiment is not None
        assert experiment.pattern_id == "pattern-001"
        assert experiment.task_type == "code_review"
        assert experiment.target_sample_size == 100
        assert experiment.traffic_percentage == 0.5
        assert experiment.status == ExperimentStatus.RUNNING

    @pytest.mark.asyncio
    async def test_should_apply_pattern_no_experiment(self, experimenter):
        """Test should_apply_pattern when no experiment exists."""
        should_apply, experiment_id = await experimenter.should_apply_pattern(
            pattern_id="non-existent",
            task_type="code_review",
        )

        # Should return True when no experiment is active
        assert should_apply is True
        assert experiment_id is None

    @pytest.mark.asyncio
    async def test_should_apply_pattern_with_experiment(self, experimenter):
        """Test should_apply_pattern with an active experiment."""
        # Create experiment
        experiment = await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
            traffic_percentage=0.5,
        )

        # Run multiple times to verify randomization
        treatment_count = 0
        for _ in range(100):
            should_apply, exp_id = await experimenter.should_apply_pattern(
                pattern_id="pattern-001",
                task_type="code_review",
            )
            if should_apply:
                treatment_count += 1
            assert exp_id == experiment.id

        # Should be roughly 50% treatment (allow wide margin for randomness)
        assert 20 < treatment_count < 80

    @pytest.mark.asyncio
    async def test_record_outcome_treatment(self, experimenter):
        """Test recording a treatment group outcome."""
        # Create experiment
        await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
        )

        result = await experimenter.record_outcome(
            pattern_id="pattern-001",
            applied_pattern=True,
            success=True,
            duration_ms=100.0,
            effectiveness=0.9,
        )

        # Should return None (not completed yet)
        assert result is None

        # Verify experiment was updated
        experiment = await experimenter.get_experiment("pattern-001")
        assert experiment.treatment.total_tasks == 1
        assert experiment.treatment.successful_tasks == 1

    @pytest.mark.asyncio
    async def test_record_outcome_control(self, experimenter):
        """Test recording a control group outcome."""
        # Create experiment
        await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
        )

        result = await experimenter.record_outcome(
            pattern_id="pattern-001",
            applied_pattern=False,
            success=False,
            duration_ms=150.0,
            effectiveness=0.5,
        )

        # Should return None (not completed yet)
        assert result is None

        # Verify experiment was updated
        experiment = await experimenter.get_experiment("pattern-001")
        assert experiment.control.total_tasks == 1
        assert experiment.control.failed_tasks == 1

    @pytest.mark.asyncio
    async def test_experiment_completion(self, experimenter, mock_pattern_store):
        """Test experiment completion with results."""
        # Create experiment with small sample size
        await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
            target_sample_size=10,
        )

        # Record enough outcomes to complete
        for i in range(10):
            await experimenter.record_outcome(
                pattern_id="pattern-001",
                applied_pattern=True,
                success=True,
                duration_ms=100.0,
                effectiveness=0.9,
            )

        for i in range(10):
            result = await experimenter.record_outcome(
                pattern_id="pattern-001",
                applied_pattern=False,
                success=i < 7,  # 70% success
                duration_ms=120.0,
                effectiveness=0.7,
            )

        # Experiment should be completed now
        assert result is not None
        assert result.conclusion in [
            ExperimentConclusion.POSITIVE,
            ExperimentConclusion.NEGATIVE,
            ExperimentConclusion.NEUTRAL,
            ExperimentConclusion.INCONCLUSIVE,
        ]

    @pytest.mark.asyncio
    async def test_list_active_experiments(self, experimenter):
        """Test listing active experiments."""
        # Create multiple experiments
        await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
        )
        await experimenter.create_experiment(
            pattern_id="pattern-002",
            task_type="bug_fix",
        )

        experiments = await experimenter.list_active_experiments()

        assert len(experiments) == 2

    @pytest.mark.asyncio
    async def test_abort_experiment(self, experimenter):
        """Test aborting an experiment."""
        await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
        )

        aborted = await experimenter.abort_experiment(
            pattern_id="pattern-001",
            reason="Testing abort",
        )

        assert aborted is not None
        assert aborted.status == ExperimentStatus.ABORTED

        # Should no longer be active
        experiments = await experimenter.list_active_experiments()
        assert len(experiments) == 0

    @pytest.mark.asyncio
    async def test_get_experiment_by_id(self, experimenter):
        """Test getting experiment by ID."""
        created = await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
        )

        found = await experimenter.get_experiment_by_id(created.id)

        assert found is not None
        assert found.id == created.id

    @pytest.mark.asyncio
    async def test_conclude_experiment_with_data(self, experimenter, mock_pattern_store):
        """Test concluding an experiment that has collected data."""
        # Create experiment with small sample size
        experiment = await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
            target_sample_size=10,
        )

        # Record treatment outcomes (high success)
        for _ in range(10):
            experiment.treatment.record_outcome(
                success=True,
                duration_ms=100.0,
                effectiveness=0.9,
            )

        # Record control outcomes (lower success)
        for i in range(10):
            experiment.control.record_outcome(
                success=(i < 7),
                duration_ms=120.0,
                effectiveness=0.7,
            )

        # Mock pattern store for _apply_experiment_result
        mock_pattern_store.get_pattern = AsyncMock(
            return_value=LearnedPattern(
                pattern_type=PatternType.ROUTING,
                scope_level=ScopeLevel.AGENT,
                scope_code="Forge",
                condition_json='{"task_type": "code_review"}',
                recommendation="Route to CQM",
                confidence=0.75,
            )
        )

        # Conclude the experiment
        result = await experimenter._conclude_experiment(experiment)

        assert result is not None
        assert isinstance(result, ExperimentResult)
        assert experiment.status == ExperimentStatus.COMPLETED
        assert experiment.completed_at is not None
        assert result.experiment_id == experiment.id
        assert result.pattern_id == "pattern-001"
        # Treatment had 100% success, control 70% -> positive diff
        assert result.success_rate_diff > 0

    @pytest.mark.asyncio
    async def test_conclude_experiment_removes_from_active(self, experimenter, mock_pattern_store):
        """Test that concluding removes the experiment from active list."""
        experiment = await experimenter.create_experiment(
            pattern_id="pattern-002",
            task_type="bug_fix",
            target_sample_size=10,
        )

        # Add some data
        for _ in range(5):
            experiment.treatment.record_outcome(success=True, duration_ms=100.0)
            experiment.control.record_outcome(success=True, duration_ms=100.0)

        # Verify it's active
        active = await experimenter.list_active_experiments()
        assert len(active) == 1

        await experimenter._conclude_experiment(experiment)

        # Should no longer be active
        active = await experimenter.list_active_experiments()
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_conclude_experiment_not_running(self, experimenter):
        """Test that concluding a non-running experiment returns None."""
        experiment = PatternExperiment(
            pattern_id="pattern-003",
            status=ExperimentStatus.COMPLETED,
        )

        result = await experimenter._conclude_experiment(experiment)

        assert result is None

    @pytest.mark.asyncio
    async def test_conclude_experiment_persists_state(
        self, experimenter, mock_db, mock_pattern_store
    ):
        """Test that concluding persists the final experiment state."""
        experiment = await experimenter.create_experiment(
            pattern_id="pattern-004",
            task_type="deployment",
            target_sample_size=10,
        )

        # Add minimal data
        for _ in range(5):
            experiment.treatment.record_outcome(success=True, duration_ms=100.0)
            experiment.control.record_outcome(success=False, duration_ms=200.0)

        # Reset call count to track conclude-specific calls
        mock_db.execute.reset_mock()

        await experimenter._conclude_experiment(experiment)

        # Should have saved the experiment (at least one execute call)
        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_conclude_experiment_adds_to_completed(self, experimenter, mock_pattern_store):
        """Test that concluded experiment result is added to completed list."""
        experiment = await experimenter.create_experiment(
            pattern_id="pattern-005",
            task_type="analysis",
            target_sample_size=10,
        )

        for _ in range(5):
            experiment.treatment.record_outcome(success=True, duration_ms=100.0)
            experiment.control.record_outcome(success=True, duration_ms=100.0)

        initial_completed = len(await experimenter.get_completed_results())

        await experimenter._conclude_experiment(experiment)

        final_completed = len(await experimenter.get_completed_results())
        assert final_completed == initial_completed + 1


class TestExperimentGroup:
    """Tests for ExperimentGroup dataclass."""

    def test_record_outcome(self):
        """Test recording outcomes in a group."""
        group = ExperimentGroup(name="treatment")

        group.record_outcome(success=True, duration_ms=100.0, effectiveness=0.9)
        group.record_outcome(success=True, duration_ms=150.0, effectiveness=0.8)
        group.record_outcome(success=False, duration_ms=200.0, effectiveness=0.3)

        assert group.total_tasks == 3
        assert group.successful_tasks == 2
        assert group.failed_tasks == 1
        assert group.success_rate == pytest.approx(2 / 3)
        assert group.avg_duration_ms == pytest.approx(150.0)
        assert group.avg_effectiveness == pytest.approx((0.9 + 0.8 + 0.3) / 3)

    def test_success_rate_zero_tasks(self):
        """Test success rate with zero tasks."""
        group = ExperimentGroup(name="control")

        # No exceptions should be raised
        assert group.success_rate == 0.0
        assert group.avg_duration_ms == 0.0

    def test_to_dict(self):
        """Test serialization to dict."""
        group = ExperimentGroup(name="treatment")
        group.record_outcome(True, 100.0, 0.9)

        data = group.to_dict()

        assert data["name"] == "treatment"
        assert data["total_tasks"] == 1
        assert data["successful_tasks"] == 1


class TestPatternExperiment:
    """Tests for PatternExperiment dataclass."""

    def test_should_apply_pattern_when_not_running(self):
        """Test that should_apply_pattern returns False when not running."""
        experiment = PatternExperiment(
            pattern_id="test",
            status=ExperimentStatus.PENDING,
        )

        assert experiment.should_apply_pattern() is False

    def test_should_apply_pattern_randomization(self):
        """Test randomization of treatment assignment."""
        experiment = PatternExperiment(
            pattern_id="test",
            status=ExperimentStatus.RUNNING,
            traffic_percentage=0.5,
        )

        treatment_count = sum(1 for _ in range(100) if experiment.should_apply_pattern())

        # Should be roughly 50%
        assert 30 < treatment_count < 70

    def test_record_outcome_when_not_running(self):
        """Test that outcomes are ignored when not running."""
        experiment = PatternExperiment(
            pattern_id="test",
            status=ExperimentStatus.COMPLETED,
        )

        experiment.record_outcome(applied_pattern=True, success=True)

        # Should not be recorded
        assert experiment.treatment.total_tasks == 0

    def test_to_dict(self):
        """Test serialization."""
        experiment = PatternExperiment(
            pattern_id="test-123",
            task_type="code_review",
            status=ExperimentStatus.RUNNING,
        )

        data = experiment.to_dict()

        assert data["pattern_id"] == "test-123"
        assert data["task_type"] == "code_review"
        assert data["status"] == "running"


class TestExperimentResult:
    """Tests for ExperimentResult dataclass."""

    def test_result_creation(self):
        """Test creating an experiment result."""
        treatment = ExperimentGroup(name="treatment")
        control = ExperimentGroup(name="control")

        # Add some data
        for _ in range(50):
            treatment.record_outcome(True, 100.0, 0.9)
        for _ in range(50):
            control.record_outcome(True, 120.0, 0.7)

        result = ExperimentResult(
            experiment_id="exp-001",
            pattern_id="pattern-001",
            treatment=treatment,
            control=control,
            success_rate_diff=0.2,
            is_significant=True,
            conclusion=ExperimentConclusion.POSITIVE,
            recommendation="PROMOTE: Pattern improves success rate",
        )

        assert result.is_significant is True
        assert result.conclusion == ExperimentConclusion.POSITIVE

    def test_to_dict(self):
        """Test serialization."""
        result = ExperimentResult(
            experiment_id="exp-001",
            pattern_id="pattern-001",
            treatment=ExperimentGroup(name="treatment"),
            control=ExperimentGroup(name="control"),
            conclusion=ExperimentConclusion.NEUTRAL,
        )

        data = result.to_dict()

        assert data["experiment_id"] == "exp-001"
        assert data["conclusion"] == "neutral"


# =============================================================================
# MetaLearner Tests
# =============================================================================


class TestMetaLearner:
    """Tests for self-tuning parameter functionality."""

    def test_initialization(self, meta_learner):
        """Test that parameters are initialized correctly."""
        # Should have default parameters
        assert len(meta_learner._parameters) > 0
        assert "min_confidence_for_override" in meta_learner._parameters

    def test_get_parameter(self, meta_learner):
        """Test getting a parameter value."""
        value = meta_learner.get_parameter("min_confidence_for_override")

        assert value is not None
        assert isinstance(value, float)
        assert 0.0 <= value <= 1.0

    def test_get_parameter_not_found(self, meta_learner):
        """Test getting non-existent parameter."""
        value = meta_learner.get_parameter("non_existent_param")

        assert value is None

    def test_get_all_parameters(self, meta_learner):
        """Test getting all parameters."""
        params = meta_learner.get_all_parameters()

        assert isinstance(params, dict)
        assert len(params) > 0
        assert "analysis_interval_seconds" in params

    def test_get_parameters_by_category(self, meta_learner):
        """Test getting parameters by category."""
        routing_params = meta_learner.get_parameters_by_category(ParameterCategory.ROUTING)

        assert isinstance(routing_params, dict)
        # Should have routing-related parameters
        assert "min_confidence_for_override" in routing_params

    @pytest.mark.asyncio
    async def test_measure_effectiveness(self, meta_learner, mock_db):
        """Test measuring learning system effectiveness."""
        mock_db.fetch_one.side_effect = [
            {"total": 100, "recent": 10},  # Pattern metrics
            {"total": 50, "successful": 40},  # Application metrics
            {"total": 200, "successful": 160, "avg_duration": 150.0},  # Outcome metrics
            {"total": 5, "resolved": 3},  # Issue metrics
        ]

        metrics = await meta_learner.measure_effectiveness()

        assert metrics is not None
        assert isinstance(metrics, EffectivenessMetrics)

    @pytest.mark.asyncio
    async def test_tune_parameters(self, meta_learner, mock_db):
        """Test parameter tuning cycle."""
        # Mock effectiveness measurements
        mock_db.fetch_one.side_effect = [
            {"total": 100, "recent": 10},
            {"total": 50, "successful": 40},
            {"total": 200, "successful": 160, "avg_duration": 150.0},
            {"total": 5, "resolved": 3},
        ] * 5  # Multiple calls

        results = await meta_learner.tune_parameters()

        # Should return list of tuning results (possibly empty if no changes needed)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_evaluate_recent_tuning(self, meta_learner, mock_db):
        """Test evaluating recent parameter changes."""
        # First run a tuning cycle
        mock_db.fetch_one.side_effect = [
            {"total": 100, "recent": 10},
            {"total": 50, "successful": 40},
            {"total": 200, "successful": 160, "avg_duration": 150.0},
            {"total": 5, "resolved": 3},
        ] * 10

        # Run tuning
        await meta_learner.tune_parameters()

        # Evaluate
        evaluation = await meta_learner.evaluate_recent_tuning()

        assert isinstance(evaluation, dict)

    @pytest.mark.asyncio
    async def test_get_stats(self, meta_learner):
        """Test getting meta-learner statistics."""
        stats = await meta_learner.get_stats()

        assert "parameters" in stats
        assert "tuning_history_count" in stats
        assert isinstance(stats["parameters"], dict)


class TestTunableParameter:
    """Tests for TunableParameter dataclass."""

    def test_parameter_creation(self):
        """Test creating a tunable parameter."""
        param = TunableParameter(
            name="test_param",
            category=ParameterCategory.ANALYSIS,
            current_value=10.0,
            min_value=1.0,
            max_value=100.0,
            step_size=1.0,
            description="Test parameter",
        )

        assert param.name == "test_param"
        assert param.current_value == 10.0
        assert param.min_value == 1.0
        assert param.max_value == 100.0

    def test_propose_increase(self):
        """Test proposing increased value."""
        param = TunableParameter(
            name="test",
            category=ParameterCategory.ANALYSIS,
            current_value=50.0,
            min_value=0.0,
            max_value=100.0,
            step_size=5.0,
        )

        assert param.propose_increase() == 55.0

    def test_propose_increase_at_max(self):
        """Test proposing increase when at max."""
        param = TunableParameter(
            name="test",
            category=ParameterCategory.ANALYSIS,
            current_value=100.0,
            min_value=0.0,
            max_value=100.0,
            step_size=5.0,
        )

        assert param.propose_increase() == 100.0  # Stays at max

    def test_propose_decrease(self):
        """Test proposing decreased value."""
        param = TunableParameter(
            name="test",
            category=ParameterCategory.ANALYSIS,
            current_value=50.0,
            min_value=0.0,
            max_value=100.0,
            step_size=5.0,
        )

        assert param.propose_decrease() == 45.0

    def test_propose_decrease_at_min(self):
        """Test proposing decrease when at min."""
        param = TunableParameter(
            name="test",
            category=ParameterCategory.ANALYSIS,
            current_value=0.0,
            min_value=0.0,
            max_value=100.0,
            step_size=5.0,
        )

        assert param.propose_decrease() == 0.0  # Stays at min

    def test_update(self):
        """Test updating parameter value."""
        param = TunableParameter(
            name="test",
            category=ParameterCategory.ANALYSIS,
            current_value=50.0,
            min_value=0.0,
            max_value=100.0,
            step_size=5.0,
        )

        param.update(75.0)

        assert param.current_value == 75.0
        assert param.tune_count == 1
        assert param.last_tuned is not None

    def test_update_respects_bounds(self):
        """Test that update respects min/max bounds."""
        param = TunableParameter(
            name="test",
            category=ParameterCategory.ANALYSIS,
            current_value=50.0,
            min_value=0.0,
            max_value=100.0,
            step_size=5.0,
        )

        param.update(150.0)  # Over max
        assert param.current_value == 100.0

        param.update(-50.0)  # Under min
        assert param.current_value == 0.0

    def test_to_dict(self):
        """Test serialization."""
        param = TunableParameter(
            name="test",
            category=ParameterCategory.ROUTING,
            current_value=0.5,
            min_value=0.0,
            max_value=1.0,
            step_size=0.1,
        )

        data = param.to_dict()

        assert data["name"] == "test"
        assert data["category"] == "routing"
        assert data["current_value"] == 0.5


class TestEffectivenessMetrics:
    """Tests for EffectivenessMetrics dataclass."""

    def test_calculate_score(self):
        """Test composite score calculation."""
        metrics = EffectivenessMetrics(
            pattern_success_rate=0.8,
            dynamic_routing_success_rate=0.75,
            prediction_accuracy=0.7,
            load_variance=0.2,
            false_positive_rate=0.1,
            overall_task_success_rate=0.85,
        )

        score = metrics.calculate_score()

        assert 0.0 <= score <= 1.0
        # With these good metrics, score should be relatively high
        assert score > 0.6

    def test_calculate_score_with_defaults(self):
        """Test score calculation with default values."""
        metrics = EffectivenessMetrics()

        score = metrics.calculate_score()

        assert 0.0 <= score <= 1.0

    def test_to_dict(self):
        """Test serialization."""
        metrics = EffectivenessMetrics(
            patterns_created=10,
            patterns_applied=50,
            pattern_success_rate=0.8,
        )

        data = metrics.to_dict()

        assert data["patterns_created"] == 10
        assert data["patterns_applied"] == 50
        assert "overall_score" in data


class TestTuningResult:
    """Tests for TuningResult dataclass."""

    def test_creation(self):
        """Test creating a tuning result."""
        result = TuningResult(
            timestamp=datetime.now(timezone.utc),
            parameter_name="test_param",
            old_value=0.5,
            new_value=0.6,
            reason="Test reason",
            effectiveness_before=0.7,
        )

        assert result.parameter_name == "test_param"
        assert result.old_value == 0.5
        assert result.new_value == 0.6

    def test_to_dict(self):
        """Test serialization."""
        result = TuningResult(
            timestamp=datetime.now(timezone.utc),
            parameter_name="test_param",
            old_value=0.5,
            new_value=0.6,
            reason="Test reason",
            effectiveness_before=0.7,
            effectiveness_after=0.75,
            was_beneficial=True,
        )

        data = result.to_dict()

        assert data["parameter_name"] == "test_param"
        assert data["was_beneficial"] is True


# =============================================================================
# HandlerGenerator Tests
# =============================================================================


class TestHandlerGenerator:
    """Tests for auto-generated handler functionality."""

    @pytest.mark.asyncio
    async def test_analyze_task_type(self, handler_generator, mock_db, mock_pattern_store):
        """Test analyzing a task type for handler generation."""
        # Mock successful outcomes
        mock_db.fetch_all.return_value = [
            {
                "task_id": f"task-{i}",
                "context_snapshot": '{"reviewer": "senior", "language": "python"}',
                "output_summary": "Code review completed successfully",
                "duration_ms": 100.0,
            }
            for i in range(25)
        ]

        mock_db.fetch_one.return_value = {"total": 30, "successful": 25}

        mock_pattern_store.get_patterns.return_value = []

        candidate = await handler_generator.analyze_task_type("code_review")

        assert candidate is not None
        assert candidate.task_type == "code_review"
        assert candidate.sample_count >= 20

    @pytest.mark.asyncio
    async def test_analyze_task_type_insufficient_data(
        self, handler_generator, mock_db, mock_pattern_store
    ):
        """Test analyzing with insufficient data."""
        mock_db.fetch_all.return_value = []  # No outcomes

        candidate = await handler_generator.analyze_task_type("rare_task_type")

        assert candidate is None

    @pytest.mark.asyncio
    async def test_analyze_task_type_low_success_rate(
        self, handler_generator, mock_db, mock_pattern_store
    ):
        """Test analyzing with low success rate."""
        mock_db.fetch_all.return_value = [
            {
                "task_id": f"task-{i}",
                "context_snapshot": "{}",
                "output_summary": "",
                "duration_ms": 100,
            }
            for i in range(25)
        ]
        mock_db.fetch_one.return_value = {"total": 100, "successful": 40}  # 40% success

        candidate = await handler_generator.analyze_task_type("failing_task")

        assert candidate is None

    @pytest.mark.asyncio
    async def test_generate_handler(self, handler_generator, mock_db, mock_pattern_store):
        """Test generating a handler from a candidate."""
        candidate = HandlerCandidate(
            task_type="code_review",
            success_rate=0.85,
            sample_count=30,
            context_keys={"code", "language", "reviewer"},
            sample_outputs=["Review complete", "No issues found"],
            common_patterns=["Uses bullet points"],
        )

        mock_pattern_store.get_patterns.return_value = []

        handler = await handler_generator.generate_handler(candidate)

        assert handler is not None
        assert handler.task_type == "code_review"
        assert handler.status == HandlerStatus.DRAFT
        assert handler.confidence > 0

    @pytest.mark.asyncio
    async def test_generate_handler_insufficient_samples(
        self, handler_generator, mock_pattern_store
    ):
        """Test that handler is not generated with insufficient samples."""
        candidate = HandlerCandidate(
            task_type="rare_task",
            success_rate=0.9,
            sample_count=5,  # Below threshold
        )

        handler = await handler_generator.generate_handler(candidate)

        assert handler is None

    @pytest.mark.asyncio
    async def test_activate_handler(self, handler_generator, mock_db, mock_pattern_store):
        """Test activating a handler for testing."""
        # First create a handler
        candidate = HandlerCandidate(
            task_type="test_task",
            success_rate=0.8,
            sample_count=25,
        )
        mock_pattern_store.get_patterns.return_value = []

        handler = await handler_generator.generate_handler(candidate)
        assert handler.status == HandlerStatus.DRAFT

        # Activate it
        activated = await handler_generator.activate_handler(handler.id)

        assert activated is True
        assert handler.status == HandlerStatus.TESTING

    @pytest.mark.asyncio
    async def test_activate_non_existent_handler(self, handler_generator):
        """Test activating a non-existent handler."""
        activated = await handler_generator.activate_handler("non-existent")

        assert activated is False

    @pytest.mark.asyncio
    async def test_record_handler_usage(self, handler_generator, mock_db, mock_pattern_store):
        """Test recording handler usage."""
        # Create and activate a handler
        candidate = HandlerCandidate(
            task_type="test_task",
            success_rate=0.8,
            sample_count=25,
        )
        mock_pattern_store.get_patterns.return_value = []

        handler = await handler_generator.generate_handler(candidate)
        await handler_generator.activate_handler(handler.id)

        # Record usage
        await handler_generator.record_handler_usage(
            handler_id=handler.id,
            success=True,
            duration_ms=95.0,
        )

        assert handler.times_used == 1
        assert handler.success_count == 1
        assert handler.avg_duration_ms == 95.0

    @pytest.mark.asyncio
    async def test_handler_auto_promotion(self, handler_generator, mock_db, mock_pattern_store):
        """Test that handlers get auto-promoted after good performance."""
        candidate = HandlerCandidate(
            task_type="test_task",
            success_rate=0.9,
            sample_count=25,
        )
        mock_pattern_store.get_patterns.return_value = []

        handler = await handler_generator.generate_handler(candidate)
        await handler_generator.activate_handler(handler.id)

        # Record 50 successful usages (threshold for promotion)
        for _ in range(50):
            await handler_generator.record_handler_usage(
                handler_id=handler.id,
                success=True,
                duration_ms=100.0,
            )

        assert handler.status == HandlerStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_handler_deprecation_on_poor_performance(
        self, handler_generator, mock_db, mock_pattern_store
    ):
        """Test that handlers get deprecated on poor performance."""
        candidate = HandlerCandidate(
            task_type="test_task",
            success_rate=0.8,
            sample_count=25,
        )
        mock_pattern_store.get_patterns.return_value = []

        handler = await handler_generator.generate_handler(candidate)
        await handler_generator.activate_handler(handler.id)

        # Record 50 mostly failed usages
        for i in range(50):
            await handler_generator.record_handler_usage(
                handler_id=handler.id,
                success=(i < 20),  # Only 40% success
                duration_ms=100.0,
            )

        assert handler.status == HandlerStatus.DEPRECATED

    @pytest.mark.asyncio
    async def test_get_handler_for_task(self, handler_generator, mock_db, mock_pattern_store):
        """Test getting handler for a task type."""
        # Create and activate a handler
        candidate = HandlerCandidate(
            task_type="code_review",
            success_rate=0.85,
            sample_count=30,
        )
        mock_pattern_store.get_patterns.return_value = []

        handler = await handler_generator.generate_handler(candidate)
        await handler_generator.activate_handler(handler.id)

        # Get handler
        found = await handler_generator.get_handler_for_task("code_review")

        assert found is not None
        assert found.task_type == "code_review"

    @pytest.mark.asyncio
    async def test_get_handler_for_task_no_match(self, handler_generator):
        """Test getting handler when none exists."""
        found = await handler_generator.get_handler_for_task("unknown_task")

        assert found is None

    @pytest.mark.asyncio
    async def test_get_all_handlers(self, handler_generator, mock_db, mock_pattern_store):
        """Test getting all handlers."""
        # Create multiple handlers
        mock_pattern_store.get_patterns.return_value = []

        for task_type in ["task_a", "task_b", "task_c"]:
            candidate = HandlerCandidate(
                task_type=task_type,
                success_rate=0.8,
                sample_count=25,
            )
            await handler_generator.generate_handler(candidate)

        handlers = await handler_generator.get_all_handlers()

        assert len(handlers) == 3

    @pytest.mark.asyncio
    async def test_deprecate_handler(self, handler_generator, mock_db, mock_pattern_store):
        """Test manually deprecating a handler."""
        candidate = HandlerCandidate(
            task_type="test_task",
            success_rate=0.8,
            sample_count=25,
        )
        mock_pattern_store.get_patterns.return_value = []

        handler = await handler_generator.generate_handler(candidate)

        deprecated = await handler_generator.deprecate_handler(
            handler_id=handler.id,
            reason="Performance degradation",
        )

        assert deprecated is True
        assert handler.status == HandlerStatus.DEPRECATED

    @pytest.mark.asyncio
    async def test_get_handlers_by_status(self, handler_generator, mock_db, mock_pattern_store):
        """Test getting handlers by status."""
        mock_pattern_store.get_patterns.return_value = []

        # Create handlers with different statuses
        for task_type in ["draft_task", "active_task"]:
            candidate = HandlerCandidate(
                task_type=task_type,
                success_rate=0.8,
                sample_count=25,
            )
            handler = await handler_generator.generate_handler(candidate)
            if task_type == "active_task":
                await handler_generator.activate_handler(handler.id)

        draft_handlers = await handler_generator.get_handlers_by_status(HandlerStatus.DRAFT)
        testing_handlers = await handler_generator.get_handlers_by_status(HandlerStatus.TESTING)

        assert len(draft_handlers) == 1
        assert len(testing_handlers) == 1


class TestGeneratedHandler:
    """Tests for GeneratedHandler dataclass."""

    def test_handler_creation(self):
        """Test creating a generated handler."""
        handler = GeneratedHandler(
            name="auto_code_review",
            task_type="code_review",
            description="Auto-generated handler",
            prompt_template="Review the code: {code}",
            parameters={"max_issues": 10},
            required_context=["code", "language"],
            output_format="json",
        )

        assert handler.name == "auto_code_review"
        assert handler.status == HandlerStatus.DRAFT
        assert handler.confidence == 0.5

    def test_success_rate_property(self):
        """Test success rate property calculation."""
        handler = GeneratedHandler(
            name="test",
            task_type="test",
        )

        handler.success_count = 85
        handler.failure_count = 15

        assert handler.success_rate == 0.85

    def test_success_rate_zero_usage(self):
        """Test success rate with no usage."""
        handler = GeneratedHandler(
            name="test",
            task_type="test",
        )

        assert handler.success_rate == 0.0

    def test_record_usage(self):
        """Test recording usage."""
        handler = GeneratedHandler(
            name="test",
            task_type="test",
        )

        handler.record_usage(success=True, duration_ms=100.0)
        handler.record_usage(success=True, duration_ms=200.0)
        handler.record_usage(success=False, duration_ms=300.0)

        assert handler.times_used == 3
        assert handler.success_count == 2
        assert handler.failure_count == 1
        assert handler.avg_duration_ms == 200.0

    def test_to_dict(self):
        """Test serialization."""
        handler = GeneratedHandler(
            name="test_handler",
            task_type="test_task",
            status=HandlerStatus.ACTIVE,
            confidence=0.8,
        )

        data = handler.to_dict()

        assert data["name"] == "test_handler"
        assert data["status"] == "active"
        assert data["confidence"] == 0.8


class TestHandlerCandidate:
    """Tests for HandlerCandidate dataclass."""

    def test_candidate_creation(self):
        """Test creating a handler candidate."""
        candidate = HandlerCandidate(
            task_type="code_review",
            success_rate=0.85,
            sample_count=100,
            context_keys={"code", "language"},
            sample_outputs=["Review complete"],
            common_patterns=["Uses bullet points"],
        )

        assert candidate.task_type == "code_review"
        assert candidate.success_rate == 0.85
        assert candidate.sample_count == 100


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestPhase3EdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_experiment_with_zero_traffic(self, experimenter):
        """Test experiment with 0% traffic (all control)."""
        experiment = await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
            traffic_percentage=0.0,
        )

        # All assignments should be control
        for _ in range(20):
            should_apply, _ = await experimenter.should_apply_pattern(
                pattern_id="pattern-001",
                task_type="code_review",
            )
            assert should_apply is False

    @pytest.mark.asyncio
    async def test_experiment_with_full_traffic(self, experimenter):
        """Test experiment with 100% traffic (all treatment)."""
        experiment = await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
            traffic_percentage=1.0,
        )

        # All assignments should be treatment
        for _ in range(20):
            should_apply, _ = await experimenter.should_apply_pattern(
                pattern_id="pattern-001",
                task_type="code_review",
            )
            assert should_apply is True

    def test_meta_learner_parameter_bounds(self, meta_learner):
        """Test that all parameters respect bounds."""
        for name, param in meta_learner._parameters.items():
            assert param.current_value >= param.min_value, f"{name} below min"
            assert param.current_value <= param.max_value, f"{name} above max"

    @pytest.mark.asyncio
    async def test_handler_generation_with_empty_context(
        self, handler_generator, mock_pattern_store
    ):
        """Test handler generation when no context keys found."""
        candidate = HandlerCandidate(
            task_type="simple_task",
            success_rate=0.8,
            sample_count=30,
            context_keys=set(),  # No context
        )
        mock_pattern_store.get_patterns.return_value = []

        handler = await handler_generator.generate_handler(candidate)

        # Should still create handler
        assert handler is not None
        assert handler.required_context == []

    @pytest.mark.asyncio
    async def test_experiment_outcome_for_different_task_type(self, experimenter):
        """Test that experiment ignores outcomes for different task types."""
        await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
        )

        # Should return True (apply pattern) for different task type
        should_apply, exp_id = await experimenter.should_apply_pattern(
            pattern_id="pattern-001",
            task_type="different_task",
        )

        # Different task type, so no experiment interference
        assert should_apply is True
        assert exp_id is None

    @pytest.mark.asyncio
    async def test_concurrent_experiments_for_same_pattern(self, experimenter):
        """Test that creating a second experiment replaces the first."""
        exp1 = await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
        )

        exp2 = await experimenter.create_experiment(
            pattern_id="pattern-001",
            task_type="code_review",
        )

        # Second experiment should replace first
        experiments = await experimenter.list_active_experiments()
        assert len(experiments) == 1
        assert experiments[0].id == exp2.id
