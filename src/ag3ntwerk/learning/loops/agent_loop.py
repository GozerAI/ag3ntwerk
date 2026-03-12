"""
Agent-level learning loop.

Focuses on:
- Cross-domain pattern recognition
- Manager performance correlation
- Strategic routing adjustments
- Resource allocation optimization
"""

import json
import logging
import statistics
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

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


class ExecutiveLearningLoop(LearningLoop):
    """
    Learning loop for C-level agents.

    Agents learn about:
    - Which managers perform best for different task types
    - Cross-domain patterns (e.g., security issues correlate with tech debt)
    - Optimal confidence thresholds for their domain
    - When to escalate vs handle internally
    """

    def __init__(
        self,
        agent_code: str,
        managers: List[str],
        pattern_store: PatternStore,
        db: Any,
    ):
        """
        Initialize the agent learning loop.

        Args:
            agent_code: Agent agent code (e.g., "Forge")
            managers: List of manager codes under this agent
            pattern_store: Pattern persistence store
            db: Database connection
        """
        super().__init__(
            agent_code=agent_code,
            level=ScopeLevel.AGENT,
            pattern_store=pattern_store,
            db=db,
        )
        self.managers = managers

    async def analyze_outcomes(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearnedPattern]:
        """
        Analyze outcomes for agent-level patterns.

        Patterns detected:
        1. Manager routing optimization
        2. Task type confidence calibration
        3. Cross-domain correlations
        4. Escalation effectiveness
        """
        patterns = []

        if len(outcomes) < self.min_samples_for_pattern:
            return patterns

        # 1. Analyze manager performance by task type
        manager_patterns = self._analyze_manager_routing(outcomes)
        patterns.extend(manager_patterns)

        # 2. Analyze confidence calibration
        confidence_patterns = self._analyze_confidence_calibration(outcomes)
        patterns.extend(confidence_patterns)

        # 3. Detect cross-domain correlations
        correlation_patterns = self._detect_cross_domain_patterns(outcomes)
        patterns.extend(correlation_patterns)

        # Log summary
        if patterns:
            logger.info(
                f"Agent {self.agent_code}: detected {len(patterns)} patterns "
                f"from {len(outcomes)} outcomes"
            )

        return patterns

    async def apply_learning(
        self,
        task_type: str,
        patterns: List[LearnedPattern],
    ) -> LearningAdjustment:
        """
        Apply learned patterns to task routing.

        Args:
            task_type: Type of task being routed
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

            # Check if pattern applies to this task type
            if not self._matches_condition(task_type, condition):
                continue

            if pattern.pattern_type == PatternType.ROUTING:
                # Apply routing preference
                if pattern.routing_preference and pattern.confidence >= 0.7:
                    if pattern.confidence > adjustment.routing_confidence:
                        adjustment.preferred_route = pattern.routing_preference
                        adjustment.routing_confidence = pattern.confidence
                        adjustment.applied_pattern_ids.append(pattern.id)

            elif pattern.pattern_type == PatternType.CONFIDENCE:
                # Apply confidence adjustment
                adjustment.confidence_adjustment += pattern.confidence_adjustment
                adjustment.applied_pattern_ids.append(pattern.id)

            elif pattern.pattern_type == PatternType.ERROR:
                # Add warning for known error patterns
                if pattern.confidence >= 0.6:
                    adjustment.add_warning(pattern.recommendation)
                    adjustment.confidence_adjustment -= 0.05
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
        Detect agent-level issues.

        Issues detected:
        - Declining manager performance
        - Significant error rate increases
        - Confidence calibration drift
        """
        issues = []

        # Need enough data
        if len(outcomes) < 20:
            return issues

        # Check for declining manager performance
        manager_issues = self._detect_manager_performance_issues(outcomes)
        issues.extend(manager_issues)

        # Check for error rate spikes
        error_issues = self._detect_error_rate_issues(outcomes)
        issues.extend(error_issues)

        return issues

    # Private analysis methods

    def _analyze_manager_routing(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearnedPattern]:
        """
        Analyze which managers perform best for which task types.

        Returns patterns suggesting optimal routing.
        """
        patterns = []

        # Group outcomes by task type and manager
        by_type_manager: Dict[str, Dict[str, List[TaskOutcomeRecord]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for outcome in outcomes:
            if outcome.manager_code:
                by_type_manager[outcome.task_type][outcome.manager_code].append(outcome)

        # Find optimal routing patterns
        for task_type, manager_outcomes in by_type_manager.items():
            if len(manager_outcomes) < 2:
                continue  # Need multiple managers to compare

            # Calculate success rates per manager
            manager_rates: Dict[str, Dict[str, Any]] = {}

            for manager_code, mgr_outcomes in manager_outcomes.items():
                if len(mgr_outcomes) >= 5:  # Need minimum samples
                    success_rate = self._calculate_success_rate(mgr_outcomes)
                    avg_effectiveness = self._calculate_avg_effectiveness(mgr_outcomes)
                    avg_duration = (
                        statistics.mean(o.duration_ms for o in mgr_outcomes if o.duration_ms > 0)
                        if any(o.duration_ms > 0 for o in mgr_outcomes)
                        else 0
                    )

                    manager_rates[manager_code] = {
                        "success_rate": success_rate,
                        "effectiveness": avg_effectiveness,
                        "avg_duration": avg_duration,
                        "sample_size": len(mgr_outcomes),
                    }

            if len(manager_rates) < 2:
                continue

            # Find best performer using composite score
            scored_managers = [
                (
                    code,
                    stats,
                    stats["success_rate"] * 0.6 + stats["effectiveness"] * 0.4,
                )
                for code, stats in manager_rates.items()
            ]
            scored_managers.sort(key=lambda x: x[2], reverse=True)

            best_manager, best_stats, best_score = scored_managers[0]
            second_best_score = scored_managers[1][2]

            # Only create pattern if significant difference (>15%)
            if best_score - second_best_score > 0.15:
                patterns.append(
                    LearnedPattern(
                        pattern_type=PatternType.ROUTING,
                        scope_level=ScopeLevel.AGENT,
                        scope_code=self.agent_code,
                        condition_json=json.dumps({"task_type": task_type}),
                        recommendation=f"Route {task_type} tasks to {best_manager} "
                        f"(success: {best_stats['success_rate']:.1%})",
                        confidence=best_stats["success_rate"],
                        sample_size=best_stats["sample_size"],
                        success_rate=best_stats["success_rate"],
                        routing_preference=best_manager,
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
        calibrated = [
            o
            for o in outcomes
            if o.initial_confidence is not None and o.actual_accuracy is not None
        ]

        if len(calibrated) < self.min_samples_for_pattern:
            return patterns

        # Calculate average calibration error
        calibration_errors = [o.actual_accuracy - o.initial_confidence for o in calibrated]

        avg_error = statistics.mean(calibration_errors)

        # If consistently over or underconfident, create adjustment pattern
        if abs(avg_error) > 0.1:
            direction = "overconfident" if avg_error < 0 else "underconfident"

            patterns.append(
                LearnedPattern(
                    pattern_type=PatternType.CONFIDENCE,
                    scope_level=ScopeLevel.AGENT,
                    scope_code=self.agent_code,
                    condition_json=json.dumps({}),  # Applies to all tasks
                    recommendation=f"Agent {self.agent_code} is {direction} by {abs(avg_error):.1%}",
                    confidence=len(calibrated) / len(outcomes),  # Based on sample coverage
                    sample_size=len(calibrated),
                    confidence_adjustment=-avg_error * 0.5,  # Gradual correction
                )
            )

        return patterns

    def _detect_cross_domain_patterns(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearnedPattern]:
        """
        Detect correlations between task types.

        For example, security issues might correlate with tech debt.
        """
        patterns = []

        # Group outcomes by task type
        by_type: Dict[str, List[TaskOutcomeRecord]] = defaultdict(list)
        for outcome in outcomes:
            by_type[outcome.task_type].append(outcome)

        # Look for correlated failure patterns
        task_types = list(by_type.keys())

        for i, type1 in enumerate(task_types):
            if len(by_type[type1]) < 5:
                continue

            for type2 in task_types[i + 1 :]:
                if len(by_type[type2]) < 5:
                    continue

                # Check if failures tend to occur together (within short time window)
                type1_failures = [o for o in by_type[type1] if not o.success]
                type2_failures = [o for o in by_type[type2] if not o.success]

                if len(type1_failures) < 3 or len(type2_failures) < 3:
                    continue

                # Simple correlation: count co-occurrences
                # (This is a simplified heuristic; real implementation would use
                # proper time-window correlation)
                type1_failure_rate = len(type1_failures) / len(by_type[type1])
                type2_failure_rate = len(type2_failures) / len(by_type[type2])

                if type1_failure_rate > 0.3 and type2_failure_rate > 0.3:
                    correlation_score = (type1_failure_rate + type2_failure_rate) / 2

                    if correlation_score > 0.4:
                        patterns.append(
                            LearnedPattern(
                                pattern_type=PatternType.ERROR,
                                scope_level=ScopeLevel.AGENT,
                                scope_code=self.agent_code,
                                condition_json=json.dumps(
                                    {
                                        "task_type": [type1, type2],
                                        "correlation": "failure",
                                    }
                                ),
                                recommendation=f"High failure correlation between "
                                f"{type1} ({type1_failure_rate:.0%}) and "
                                f"{type2} ({type2_failure_rate:.0%})",
                                confidence=correlation_score,
                                sample_size=len(type1_failures) + len(type2_failures),
                            )
                        )

        return patterns

    def _detect_manager_performance_issues(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearningIssue]:
        """Detect declining performance in managers."""
        issues = []

        for manager in self.managers:
            manager_outcomes = [o for o in outcomes if o.manager_code == manager]

            if len(manager_outcomes) < 20:
                continue

            # Compare recent vs older performance
            sorted_outcomes = sorted(manager_outcomes, key=lambda o: o.created_at)
            midpoint = len(sorted_outcomes) // 2

            older = sorted_outcomes[:midpoint]
            recent = sorted_outcomes[midpoint:]

            older_rate = self._calculate_success_rate(older)
            recent_rate = self._calculate_success_rate(recent)

            # Significant decline (>20% drop)
            if recent_rate < older_rate - 0.2:
                severity = IssueSeverity.HIGH if recent_rate < 0.5 else IssueSeverity.MEDIUM
                priority = 3 if severity == IssueSeverity.HIGH else 5

                issues.append(
                    LearningIssue(
                        issue_type=IssueType.PATTERN_DECLINE,
                        severity=severity,
                        priority=priority,
                        source_agent_code=manager,
                        source_level=ScopeLevel.MANAGER,
                        title=f"Performance decline in {manager}",
                        description=f"Success rate dropped from {older_rate:.1%} to {recent_rate:.1%} "
                        f"({(older_rate - recent_rate):.1%} decline)",
                        evidence_json=json.dumps(
                            {
                                "older_rate": older_rate,
                                "recent_rate": recent_rate,
                                "older_sample_size": len(older),
                                "recent_sample_size": len(recent),
                            }
                        ),
                        suggested_action="investigate_performance_degradation",
                    )
                )

        return issues

    def _detect_error_rate_issues(
        self,
        outcomes: List[TaskOutcomeRecord],
    ) -> List[LearningIssue]:
        """Detect significant error rate spikes."""
        issues = []

        # Group by error category
        error_counts: Counter = Counter()
        for outcome in outcomes:
            if not outcome.success and outcome.error_category:
                error_counts[outcome.error_category.value] += 1

        total_failures = sum(error_counts.values())

        if total_failures < 5:
            return issues

        # Check for dominant error category
        most_common = error_counts.most_common(1)
        if most_common:
            category, count = most_common[0]
            error_rate = count / len(outcomes)

            if error_rate > 0.2:  # >20% of tasks fail with same error type
                issues.append(
                    LearningIssue(
                        issue_type=IssueType.ERROR_SPIKE,
                        severity=IssueSeverity.HIGH if error_rate > 0.3 else IssueSeverity.MEDIUM,
                        priority=2 if error_rate > 0.3 else 4,
                        source_agent_code=self.agent_code,
                        source_level=ScopeLevel.AGENT,
                        title=f"High {category} error rate in {self.agent_code}",
                        description=f"{count} of {len(outcomes)} tasks ({error_rate:.1%}) "
                        f"failed with {category} errors",
                        evidence_json=json.dumps(
                            {
                                "error_category": category,
                                "count": count,
                                "total_outcomes": len(outcomes),
                                "all_error_counts": dict(error_counts),
                            }
                        ),
                        suggested_action="investigate_error_source",
                    )
                )

        return issues
