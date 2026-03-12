"""
Specialist-level learning loop.

Focuses on:
- Task-specific skill refinement
- Confidence calibration
- Performance self-assessment
- Error recovery patterns
"""

import json
import logging
import statistics
from collections import defaultdict
from typing import Any, Dict, List

from ag3ntwerk.learning.loops.base import LearningLoop
from ag3ntwerk.learning.models import (
    IssueSeverity,
    IssueType,
    LearnedPattern,
    LearningAdjustment,
    LearningIssue,
    PatternType,
    ScopeLevel,
    TaskOutcomeRecord,
)
from ag3ntwerk.learning.pattern_store import PatternStore

logger = logging.getLogger(__name__)


class SpecialistLearningLoop(LearningLoop):
    """
    Learning loop for specialists.

    Specialists learn about:
    - Which approaches work best for specific task patterns
    - Confidence calibration for their expertise
    - Recovery strategies from failures
    - Performance optimization opportunities
    """

    def __init__(
        self,
        specialist_code: str,
        manager_code: str,
        capabilities: List[str],
        pattern_store: PatternStore,
        db: Any,
    ):
        """
        Initialize the specialist learning loop.

        Args:
            specialist_code: Specialist agent code (e.g., "SD", "CR")
            manager_code: Parent manager code
            capabilities: List of capabilities this specialist has
            pattern_store: Pattern persistence store
            db: Database connection
        """
        super().__init__(
            agent_code=specialist_code,
            level=ScopeLevel.SPECIALIST,
            pattern_store=pattern_store,
            db=db,
        )
        self.manager_code = manager_code
        self.capabilities = capabilities

    async def analyze_outcomes(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearnedPattern]:
        """
        Analyze outcomes for specialist-level patterns.

        Patterns detected:
        1. Capability-specific success rates
        2. Confidence calibration
        3. Recovery effectiveness
        4. Performance sweet spots
        """
        patterns = []

        if len(outcomes) < self.min_samples_for_pattern:
            return patterns

        # 1. Analyze per-capability performance
        capability_patterns = self._analyze_capability_performance(outcomes)
        patterns.extend(capability_patterns)

        # 2. Analyze confidence calibration
        calibration_patterns = self._analyze_confidence_calibration(outcomes)
        patterns.extend(calibration_patterns)

        # 3. Detect performance sweet spots
        sweet_spot_patterns = self._detect_performance_sweet_spots(outcomes)
        patterns.extend(sweet_spot_patterns)

        # Log summary
        if patterns:
            logger.info(
                f"Specialist {self.agent_code}: detected {len(patterns)} patterns "
                f"from {len(outcomes)} outcomes"
            )

        return patterns

    async def apply_learning(
        self,
        task_type: str,
        patterns: List[LearnedPattern],
    ) -> LearningAdjustment:
        """
        Apply learned patterns to task execution.

        Args:
            task_type: Type of task being executed
            patterns: Applicable patterns

        Returns:
            Adjustments to apply
        """
        adjustment = LearningAdjustment()

        for pattern in patterns:
            try:
                condition = json.loads(pattern.condition_json)
            except json.JSONDecodeError:
                continue

            # Check if pattern applies
            if not self._matches_condition(task_type, condition):
                continue

            if pattern.pattern_type == PatternType.CONFIDENCE:
                # Apply confidence adjustment
                adjustment.confidence_adjustment += pattern.confidence_adjustment
                adjustment.applied_pattern_ids.append(pattern.id)

            elif pattern.pattern_type == PatternType.CAPABILITY:
                # Add capability-specific hints
                if pattern.recommendation:
                    adjustment.effectiveness_hints.append(pattern.recommendation)
                adjustment.applied_pattern_ids.append(pattern.id)

            elif pattern.pattern_type == PatternType.ERROR:
                # Add warning for known issues
                adjustment.add_warning(pattern.recommendation)
                adjustment.applied_pattern_ids.append(pattern.id)

        # Clamp adjustments
        adjustment.clamp()

        return adjustment

    async def detect_issues(
        self,
        outcomes: List[TaskOutcomeRecord],
        patterns: List[LearnedPattern],
    ) -> List[LearningIssue]:
        """
        Detect specialist-level issues.

        Issues detected:
        - Consistent underperformance
        - Capability gaps
        - Confidence calibration drift
        """
        issues = []

        if len(outcomes) < 10:
            return issues

        # Check for consistent underperformance
        performance_issues = self._detect_performance_issues(outcomes)
        issues.extend(performance_issues)

        # Check for confidence calibration problems
        calibration_issues = self._detect_calibration_issues(outcomes)
        issues.extend(calibration_issues)

        return issues

    # Private analysis methods

    def _analyze_capability_performance(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearnedPattern]:
        """
        Analyze performance per capability/task type.

        Returns patterns indicating capability strengths and weaknesses.
        """
        patterns = []

        # Group by task type
        by_type: Dict[str, List[TaskOutcomeRecord]] = defaultdict(list)
        for outcome in outcomes:
            by_type[outcome.task_type].append(outcome)

        for task_type, type_outcomes in by_type.items():
            if len(type_outcomes) < 5:
                continue

            success_rate = self._calculate_success_rate(type_outcomes)
            avg_effectiveness = self._calculate_avg_effectiveness(type_outcomes)

            # Strong performance pattern
            if success_rate >= 0.8 and avg_effectiveness >= 0.7:
                patterns.append(
                    LearnedPattern(
                        pattern_type=PatternType.CAPABILITY,
                        scope_level=ScopeLevel.SPECIALIST,
                        scope_code=self.agent_code,
                        condition_json=json.dumps({"task_type": task_type}),
                        recommendation=f"High performance on {task_type} tasks "
                        f"({success_rate:.0%} success, {avg_effectiveness:.0%} effectiveness)",
                        confidence=success_rate,
                        sample_size=len(type_outcomes),
                        success_rate=success_rate,
                    )
                )

            # Weak performance pattern
            elif success_rate < 0.5:
                patterns.append(
                    LearnedPattern(
                        pattern_type=PatternType.CAPABILITY,
                        scope_level=ScopeLevel.SPECIALIST,
                        scope_code=self.agent_code,
                        condition_json=json.dumps({"task_type": task_type}),
                        recommendation=f"Struggling with {task_type} tasks "
                        f"(only {success_rate:.0%} success rate)",
                        confidence=1.0 - success_rate,  # Higher confidence in the weakness
                        sample_size=len(type_outcomes),
                        success_rate=success_rate,
                        confidence_adjustment=-0.15,  # Lower confidence on these tasks
                    )
                )

        return patterns

    def _analyze_confidence_calibration(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearnedPattern]:
        """
        Analyze how well confidence predicts actual performance.

        Returns patterns for confidence adjustment.
        """
        patterns = []

        # Only analyze outcomes with confidence data
        calibrated = [o for o in outcomes if o.initial_confidence is not None]

        if len(calibrated) < self.min_samples_for_pattern:
            return patterns

        # Group by confidence bucket
        buckets = {
            "very_low": (0.0, 0.3),
            "low": (0.3, 0.5),
            "medium": (0.5, 0.7),
            "high": (0.7, 0.85),
            "very_high": (0.85, 1.0),
        }

        for bucket_name, (low, high) in buckets.items():
            bucket_outcomes = [o for o in calibrated if low <= o.initial_confidence < high]

            if len(bucket_outcomes) < 5:
                continue

            actual_success_rate = self._calculate_success_rate(bucket_outcomes)
            expected_rate = (low + high) / 2

            calibration_error = actual_success_rate - expected_rate

            # Significant miscalibration (>15%)
            if abs(calibration_error) > 0.15:
                direction = "underconfident" if calibration_error > 0 else "overconfident"

                patterns.append(
                    LearnedPattern(
                        pattern_type=PatternType.CONFIDENCE,
                        scope_level=ScopeLevel.SPECIALIST,
                        scope_code=self.agent_code,
                        condition_json=json.dumps({"confidence_bucket": bucket_name}),
                        recommendation=f"In {bucket_name} confidence range, specialist is {direction} "
                        f"(expected ~{expected_rate:.0%}, actual {actual_success_rate:.0%})",
                        confidence=len(bucket_outcomes) / len(calibrated),
                        sample_size=len(bucket_outcomes),
                        confidence_adjustment=-calibration_error * 0.5,  # Gradual correction
                    )
                )

        return patterns

    def _detect_performance_sweet_spots(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearnedPattern]:
        """
        Detect conditions where performance is optimal.

        Returns patterns indicating performance sweet spots.
        """
        patterns = []

        # Analyze by duration buckets (fast vs slow execution)
        outcomes_with_duration = [o for o in outcomes if o.duration_ms > 0]

        if len(outcomes_with_duration) < 15:
            return patterns

        durations = [o.duration_ms for o in outcomes_with_duration]
        median_duration = statistics.median(durations)

        fast_outcomes = [o for o in outcomes_with_duration if o.duration_ms < median_duration]
        slow_outcomes = [o for o in outcomes_with_duration if o.duration_ms >= median_duration]

        fast_rate = self._calculate_success_rate(fast_outcomes)
        slow_rate = self._calculate_success_rate(slow_outcomes)

        # Significant difference
        if abs(fast_rate - slow_rate) > 0.2:
            better_bucket = "fast" if fast_rate > slow_rate else "slow"
            better_rate = max(fast_rate, slow_rate)

            patterns.append(
                LearnedPattern(
                    pattern_type=PatternType.CAPABILITY,
                    scope_level=ScopeLevel.SPECIALIST,
                    scope_code=self.agent_code,
                    condition_json=json.dumps(
                        {
                            "execution_speed": better_bucket,
                            "median_duration_ms": median_duration,
                        }
                    ),
                    recommendation=f"Better performance on {better_bucket} tasks "
                    f"({better_rate:.0%} vs {min(fast_rate, slow_rate):.0%})",
                    confidence=abs(fast_rate - slow_rate),
                    sample_size=len(outcomes_with_duration),
                )
            )

        return patterns

    def _detect_performance_issues(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearningIssue]:
        """Detect consistent underperformance."""
        issues = []

        # Check overall recent performance
        recent = outcomes[-20:] if len(outcomes) >= 20 else outcomes

        if len(recent) < 10:
            return issues

        success_rate = self._calculate_success_rate(recent)

        if success_rate < 0.5:
            issues.append(
                LearningIssue(
                    issue_type=IssueType.PATTERN_DECLINE,
                    severity=IssueSeverity.HIGH if success_rate < 0.3 else IssueSeverity.MEDIUM,
                    priority=2 if success_rate < 0.3 else 4,
                    source_agent_code=self.agent_code,
                    source_level=ScopeLevel.SPECIALIST,
                    title=f"High failure rate for {self.agent_code}",
                    description=f"Recent success rate is only {success_rate:.1%} "
                    f"over {len(recent)} tasks",
                    evidence_json=json.dumps(
                        {
                            "success_rate": success_rate,
                            "sample_size": len(recent),
                        }
                    ),
                    suggested_action="review_specialist_performance",
                )
            )

        return issues

    def _detect_calibration_issues(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearningIssue]:
        """Detect significant confidence calibration problems."""
        issues = []

        # Check outcomes with confidence data
        calibrated = [o for o in outcomes if o.initial_confidence is not None]

        if len(calibrated) < 10:
            return issues

        # Calculate overall calibration error
        calibration_errors = []
        for outcome in calibrated:
            expected = outcome.initial_confidence
            actual = 1.0 if outcome.success else 0.0
            calibration_errors.append(actual - expected)

        avg_error = statistics.mean(calibration_errors)

        # Significant systematic miscalibration
        if abs(avg_error) > 0.25:
            direction = "underconfident" if avg_error > 0 else "overconfident"

            issues.append(
                LearningIssue(
                    issue_type=IssueType.CONFIDENCE_DRIFT,
                    severity=IssueSeverity.MEDIUM,
                    priority=5,
                    source_agent_code=self.agent_code,
                    source_level=ScopeLevel.SPECIALIST,
                    title=f"Confidence calibration issue for {self.agent_code}",
                    description=f"Specialist is consistently {direction} by {abs(avg_error):.1%}",
                    evidence_json=json.dumps(
                        {
                            "avg_calibration_error": avg_error,
                            "sample_size": len(calibrated),
                            "direction": direction,
                        }
                    ),
                    suggested_action="recalibrate_confidence_thresholds",
                )
            )

        return issues
