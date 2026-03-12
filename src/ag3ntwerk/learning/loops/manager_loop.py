"""
Manager-level learning loop.

Focuses on:
- Specialist routing within domain
- Domain-specific optimizations
- Error pattern recognition
- Task decomposition effectiveness
"""

import json
import logging
import statistics
from collections import Counter, defaultdict
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


class ManagerLearningLoop(LearningLoop):
    """
    Learning loop for managers.

    Managers learn about:
    - Which specialists excel at which task sub-types
    - Domain-specific error patterns
    - Optimal task decomposition strategies
    - Resource allocation within their team
    """

    def __init__(
        self,
        manager_code: str,
        agent_code: str,
        specialists: List[str],
        pattern_store: PatternStore,
        db: Any,
    ):
        """
        Initialize the manager learning loop.

        Args:
            manager_code: Manager agent code (e.g., "AM", "CQM")
            agent_code: Parent agent code
            specialists: List of specialist codes under this manager
            pattern_store: Pattern persistence store
            db: Database connection
        """
        super().__init__(
            agent_code=manager_code,
            level=ScopeLevel.MANAGER,
            pattern_store=pattern_store,
            db=db,
        )
        self.agent_code = agent_code
        self.specialists = specialists

    async def analyze_outcomes(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearnedPattern]:
        """
        Analyze outcomes for manager-level patterns.

        Patterns detected:
        1. Specialist task affinity
        2. Domain error patterns
        3. Task complexity indicators
        4. Optimal delegation depth
        """
        patterns = []

        if len(outcomes) < self.min_samples_for_pattern:
            return patterns

        # 1. Analyze specialist performance
        specialist_patterns = self._analyze_specialist_routing(outcomes)
        patterns.extend(specialist_patterns)

        # 2. Detect error patterns
        error_patterns = self._analyze_error_patterns(outcomes)
        patterns.extend(error_patterns)

        # 3. Analyze task complexity correlation
        complexity_patterns = self._analyze_complexity_indicators(outcomes)
        patterns.extend(complexity_patterns)

        # Log summary
        if patterns:
            logger.info(
                f"Manager {self.agent_code}: detected {len(patterns)} patterns "
                f"from {len(outcomes)} outcomes"
            )

        return patterns

    async def apply_learning(
        self,
        task_type: str,
        patterns: List[LearnedPattern],
    ) -> LearningAdjustment:
        """
        Apply learned patterns to specialist routing.

        Args:
            task_type: Type of task being handled
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

            if pattern.pattern_type == PatternType.ROUTING:
                # Apply specialist routing preference
                if pattern.routing_preference and pattern.confidence >= 0.7:
                    if pattern.confidence > adjustment.routing_confidence:
                        adjustment.preferred_route = pattern.routing_preference
                        adjustment.routing_confidence = pattern.confidence
                        adjustment.applied_pattern_ids.append(pattern.id)

            elif pattern.pattern_type == PatternType.ERROR:
                # Increase caution for known problematic patterns
                adjustment.add_warning(pattern.recommendation)
                adjustment.confidence_adjustment -= 0.1
                adjustment.applied_pattern_ids.append(pattern.id)

            elif pattern.pattern_type == PatternType.CAPABILITY:
                # Add effectiveness hints
                if pattern.recommendation:
                    adjustment.effectiveness_hints.append(pattern.recommendation)
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
        Detect manager-level issues.

        Issues detected:
        - Specialist underperformance
        - Recurring error patterns
        - Capability gaps
        """
        issues = []

        if len(outcomes) < 15:
            return issues

        # Check specialist performance
        specialist_issues = self._detect_specialist_issues(outcomes)
        issues.extend(specialist_issues)

        # Check for recurring errors
        error_issues = self._detect_recurring_errors(outcomes)
        issues.extend(error_issues)

        return issues

    # Private analysis methods

    def _analyze_specialist_routing(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearnedPattern]:
        """
        Analyze which specialists perform best for which tasks.

        Returns patterns suggesting optimal specialist assignments.
        """
        patterns = []

        # Group by task type and specialist
        by_type_specialist: Dict[str, Dict[str, List[TaskOutcomeRecord]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for outcome in outcomes:
            if outcome.specialist_code:
                by_type_specialist[outcome.task_type][outcome.specialist_code].append(outcome)

        for task_type, specialist_outcomes in by_type_specialist.items():
            if len(specialist_outcomes) < 2:
                continue

            # Calculate performance per specialist
            specialist_stats: Dict[str, Dict[str, Any]] = {}

            for specialist_code, spec_outcomes in specialist_outcomes.items():
                if len(spec_outcomes) >= 3:  # Minimum samples
                    success_rate = self._calculate_success_rate(spec_outcomes)
                    avg_effectiveness = self._calculate_avg_effectiveness(spec_outcomes)
                    avg_duration = (
                        statistics.mean(o.duration_ms for o in spec_outcomes if o.duration_ms > 0)
                        if any(o.duration_ms > 0 for o in spec_outcomes)
                        else 0
                    )

                    specialist_stats[specialist_code] = {
                        "success_rate": success_rate,
                        "effectiveness": avg_effectiveness,
                        "avg_duration": avg_duration,
                        "sample_size": len(spec_outcomes),
                    }

            if len(specialist_stats) < 2:
                continue

            # Find best performer
            scored = [
                (
                    code,
                    stats,
                    stats["success_rate"] * 0.5 + stats["effectiveness"] * 0.5,
                )
                for code, stats in specialist_stats.items()
            ]
            scored.sort(key=lambda x: x[2], reverse=True)

            best_specialist, best_stats, best_score = scored[0]
            second_best_score = scored[1][2] if len(scored) > 1 else 0

            # Create pattern if significant difference
            if best_score - second_best_score > 0.1:
                patterns.append(
                    LearnedPattern(
                        pattern_type=PatternType.ROUTING,
                        scope_level=ScopeLevel.MANAGER,
                        scope_code=self.agent_code,
                        condition_json=json.dumps({"task_type": task_type}),
                        recommendation=f"Assign {task_type} to {best_specialist} "
                        f"(effectiveness: {best_stats['effectiveness']:.1%})",
                        confidence=best_stats["success_rate"],
                        sample_size=best_stats["sample_size"],
                        success_rate=best_stats["success_rate"],
                        routing_preference=best_specialist,
                    )
                )

        return patterns

    def _analyze_error_patterns(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearnedPattern]:
        """
        Detect recurring error patterns in the domain.

        Returns patterns for known problematic scenarios.
        """
        patterns = []

        # Group errors by category
        errors_by_category: Dict[str, List[TaskOutcomeRecord]] = defaultdict(list)

        for outcome in outcomes:
            if not outcome.success and outcome.error_category:
                errors_by_category[outcome.error_category.value].append(outcome)

        total_failures = sum(len(v) for v in errors_by_category.values())
        if total_failures < 5:
            return patterns

        for category, error_outcomes in errors_by_category.items():
            error_rate = len(error_outcomes) / total_failures

            if error_rate > 0.3 and len(error_outcomes) >= 5:
                # Analyze common characteristics
                common_task_types = Counter(o.task_type for o in error_outcomes)
                most_common_type, count = common_task_types.most_common(1)[0]

                task_type_rate = count / len(error_outcomes)

                if task_type_rate > 0.5:
                    patterns.append(
                        LearnedPattern(
                            pattern_type=PatternType.ERROR,
                            scope_level=ScopeLevel.MANAGER,
                            scope_code=self.agent_code,
                            condition_json=json.dumps(
                                {
                                    "task_type": most_common_type,
                                    "error_category": category,
                                }
                            ),
                            recommendation=f"Task type {most_common_type} frequently fails "
                            f"with {category} errors ({error_rate:.0%} of failures)",
                            confidence=error_rate,
                            sample_size=len(error_outcomes),
                        )
                    )

        return patterns

    def _analyze_complexity_indicators(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearnedPattern]:
        """
        Analyze what factors correlate with task complexity.

        Returns patterns indicating complexity factors.
        """
        patterns = []

        # Analyze duration vs success correlation
        # Tasks that take longer might need different handling

        by_type: Dict[str, List[TaskOutcomeRecord]] = defaultdict(list)
        for outcome in outcomes:
            if outcome.duration_ms > 0:
                by_type[outcome.task_type].append(outcome)

        for task_type, type_outcomes in by_type.items():
            if len(type_outcomes) < 10:
                continue

            durations = [o.duration_ms for o in type_outcomes]
            avg_duration = statistics.mean(durations)
            std_duration = statistics.stdev(durations) if len(durations) > 1 else 0

            # High variance in duration might indicate complexity variation
            if std_duration > avg_duration * 0.5:  # CV > 50%
                # Check if longer tasks fail more
                median_duration = statistics.median(durations)
                long_tasks = [o for o in type_outcomes if o.duration_ms > median_duration]
                short_tasks = [o for o in type_outcomes if o.duration_ms <= median_duration]

                long_success_rate = self._calculate_success_rate(long_tasks)
                short_success_rate = self._calculate_success_rate(short_tasks)

                if short_success_rate - long_success_rate > 0.2:
                    patterns.append(
                        LearnedPattern(
                            pattern_type=PatternType.CAPABILITY,
                            scope_level=ScopeLevel.MANAGER,
                            scope_code=self.agent_code,
                            condition_json=json.dumps(
                                {
                                    "task_type": task_type,
                                    "complexity_indicator": "duration",
                                }
                            ),
                            recommendation=f"Longer {task_type} tasks fail more often "
                            f"({long_success_rate:.0%} vs {short_success_rate:.0%}). "
                            f"Consider decomposition.",
                            confidence=(short_success_rate - long_success_rate),
                            sample_size=len(type_outcomes),
                        )
                    )

        return patterns

    def _detect_specialist_issues(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearningIssue]:
        """Detect underperforming specialists."""
        issues = []

        for specialist in self.specialists:
            specialist_outcomes = [o for o in outcomes if o.specialist_code == specialist]

            if len(specialist_outcomes) < 10:
                continue

            success_rate = self._calculate_success_rate(specialist_outcomes)

            # Consistent underperformance
            if success_rate < 0.5:
                issues.append(
                    LearningIssue(
                        issue_type=IssueType.PATTERN_DECLINE,
                        severity=IssueSeverity.HIGH if success_rate < 0.3 else IssueSeverity.MEDIUM,
                        priority=2 if success_rate < 0.3 else 4,
                        source_agent_code=specialist,
                        source_level=ScopeLevel.SPECIALIST,
                        title=f"Low success rate for {specialist}",
                        description=f"Success rate is only {success_rate:.1%} "
                        f"over {len(specialist_outcomes)} tasks",
                        evidence_json=json.dumps(
                            {
                                "success_rate": success_rate,
                                "sample_size": len(specialist_outcomes),
                            }
                        ),
                        suggested_action="review_specialist_capabilities",
                    )
                )

        return issues

    def _detect_recurring_errors(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearningIssue]:
        """Detect recurring error patterns needing investigation."""
        issues = []

        # Find error messages that occur multiple times
        error_messages: Counter = Counter()
        for outcome in outcomes:
            if not outcome.success and outcome.error_message:
                # Normalize error message (first 100 chars)
                normalized = outcome.error_message[:100].lower()
                error_messages[normalized] += 1

        # Find recurring errors
        for error_msg, count in error_messages.most_common(3):
            if count >= 3:  # At least 3 occurrences
                issues.append(
                    LearningIssue(
                        issue_type=IssueType.ERROR_SPIKE,
                        severity=IssueSeverity.MEDIUM,
                        priority=5,
                        source_agent_code=self.agent_code,
                        source_level=ScopeLevel.MANAGER,
                        title=f"Recurring error in {self.agent_code}",
                        description=f"Error occurred {count} times: {error_msg[:80]}...",
                        evidence_json=json.dumps(
                            {
                                "error_preview": error_msg[:200],
                                "count": count,
                            }
                        ),
                        suggested_action="investigate_recurring_error",
                    )
                )

        return issues
