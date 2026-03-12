"""
Goal alignment verification for the ag3ntwerk learning system.

Ensures autonomous decisions align with user and system goals,
preventing drift and maintaining trust.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .models import TaskOutcomeRecord
from .outcome_tracker import OutcomeTracker
from .pattern_store import PatternStore


class GoalType(str, Enum):
    """Types of goals."""

    USER = "user"
    SYSTEM = "system"
    SAFETY = "safety"
    PERFORMANCE = "performance"
    EFFICIENCY = "efficiency"


class GoalPriority(str, Enum):
    """Priority levels for goals."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlignmentLevel(str, Enum):
    """Levels of alignment."""

    FULL = "full"
    PARTIAL = "partial"
    MISALIGNED = "misaligned"
    CONFLICTING = "conflicting"


class ActionRecommendation(str, Enum):
    """Recommended actions based on alignment."""

    PROCEED = "proceed"
    PROCEED_WITH_CAUTION = "proceed_with_caution"
    REQUIRES_REVIEW = "requires_review"
    BLOCK = "block"


@dataclass
class Goal:
    """A goal definition."""

    goal_id: str
    goal_type: GoalType
    priority: GoalPriority
    description: str
    criteria: Dict[str, Any]
    weight: float = 1.0
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "goal_type": self.goal_type.value,
            "priority": self.priority.value,
            "description": self.description,
            "criteria": self.criteria,
            "weight": self.weight,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AutonomousDecision:
    """An autonomous decision to verify."""

    decision_id: str
    action: str
    category: str
    description: str
    impact: str
    affected_entities: List[str]
    proposed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "action": self.action,
            "category": self.category,
            "description": self.description,
            "impact": self.impact,
            "affected_entities": self.affected_entities,
            "proposed_at": self.proposed_at.isoformat(),
            "context": self.context,
        }


@dataclass
class GoalConflict:
    """A conflict between goals or between a decision and goals."""

    goal1_id: str
    goal2_id: Optional[str]
    decision_id: Optional[str]
    conflict_type: str
    severity: float
    description: str
    resolution_suggestion: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal1_id": self.goal1_id,
            "goal2_id": self.goal2_id,
            "decision_id": self.decision_id,
            "conflict_type": self.conflict_type,
            "severity": self.severity,
            "description": self.description,
            "resolution_suggestion": self.resolution_suggestion,
        }


@dataclass
class AlignmentScore:
    """Result of alignment verification."""

    decision_id: str
    user_alignment: float
    system_alignment: float
    safety_alignment: float
    overall_alignment: float
    alignment_level: AlignmentLevel
    conflicts: List[GoalConflict]
    recommendation: ActionRecommendation
    explanation: str
    verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "user_alignment": self.user_alignment,
            "system_alignment": self.system_alignment,
            "safety_alignment": self.safety_alignment,
            "overall_alignment": self.overall_alignment,
            "alignment_level": self.alignment_level.value,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "recommendation": self.recommendation.value,
            "explanation": self.explanation,
            "verified_at": self.verified_at.isoformat(),
        }


@dataclass
class GoalProgress:
    """Progress toward a goal."""

    goal_id: str
    progress: float
    trend: str  # improving, declining, stable
    recent_contributions: int
    last_updated: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "progress": self.progress,
            "trend": self.trend,
            "recent_contributions": self.recent_contributions,
            "last_updated": self.last_updated.isoformat(),
        }


class GoalAligner:
    """
    Verifies that autonomous decisions align with user and system goals.

    Maintains goal definitions and checks decisions against them,
    detecting conflicts and ensuring trust is maintained.
    """

    # Alignment thresholds
    FULL_ALIGNMENT_THRESHOLD = 0.9
    PARTIAL_ALIGNMENT_THRESHOLD = 0.6
    MISALIGNMENT_THRESHOLD = 0.3

    # Safety weight multiplier
    SAFETY_WEIGHT_MULTIPLIER = 2.0

    def __init__(
        self,
        db: Any,
        outcome_tracker: OutcomeTracker,
        pattern_store: PatternStore,
    ):
        self._db = db
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store
        self._goals: Dict[str, Goal] = {}
        self._default_goals_initialized = False

    async def initialize_default_goals(self) -> None:
        """Initialize default system and safety goals."""
        if self._default_goals_initialized:
            return

        default_goals = [
            Goal(
                goal_id="safety_no_harm",
                goal_type=GoalType.SAFETY,
                priority=GoalPriority.CRITICAL,
                description="Never take actions that could harm users or systems",
                criteria={"max_risk_level": "medium", "requires_confirmation_above": "high"},
                weight=2.0,
            ),
            Goal(
                goal_id="system_reliability",
                goal_type=GoalType.SYSTEM,
                priority=GoalPriority.HIGH,
                description="Maintain system reliability above 99%",
                criteria={"min_success_rate": 0.99, "max_downtime_minutes": 10},
                weight=1.5,
            ),
            Goal(
                goal_id="performance_efficiency",
                goal_type=GoalType.PERFORMANCE,
                priority=GoalPriority.MEDIUM,
                description="Optimize task completion time",
                criteria={"target_p95_ms": 5000, "max_queue_depth": 100},
                weight=1.0,
            ),
            Goal(
                goal_id="efficiency_resource",
                goal_type=GoalType.EFFICIENCY,
                priority=GoalPriority.MEDIUM,
                description="Efficient resource utilization",
                criteria={"target_utilization": 0.7, "max_idle_agents": 0.2},
                weight=1.0,
            ),
        ]

        for goal in default_goals:
            self._goals[goal.goal_id] = goal
            await self._save_goal(goal)

        self._default_goals_initialized = True

    async def verify_alignment(
        self,
        decision: AutonomousDecision,
    ) -> AlignmentScore:
        """
        Verify that a decision aligns with all goals.

        Args:
            decision: The autonomous decision to verify

        Returns:
            AlignmentScore with detailed analysis
        """
        # Load goals if not loaded
        if not self._goals:
            await self._load_goals()

        # Get goals by type
        user_goals = await self._get_user_goals()
        system_goals = await self._get_system_goals()
        safety_goals = [g for g in self._goals.values() if g.goal_type == GoalType.SAFETY]

        # Measure alignment for each category
        user_alignment = self._measure_user_alignment(decision, user_goals)
        system_alignment = self._measure_system_alignment(decision, system_goals)
        safety_alignment = self._measure_safety_alignment(decision, safety_goals)

        # Detect conflicts
        conflicts = self._detect_conflicts(decision, user_goals, system_goals, safety_goals)

        # Calculate overall alignment (safety weighted higher)
        total_weight = 1.0 + 1.0 + self.SAFETY_WEIGHT_MULTIPLIER
        overall_alignment = (
            user_alignment + system_alignment + safety_alignment * self.SAFETY_WEIGHT_MULTIPLIER
        ) / total_weight

        # Determine alignment level
        alignment_level = self._determine_alignment_level(overall_alignment, conflicts)

        # Generate recommendation
        recommendation = self._recommend_action(alignment_level, conflicts, safety_alignment)

        # Generate explanation
        explanation = self._generate_explanation(
            decision, user_alignment, system_alignment, safety_alignment, conflicts
        )

        return AlignmentScore(
            decision_id=decision.decision_id,
            user_alignment=user_alignment,
            system_alignment=system_alignment,
            safety_alignment=safety_alignment,
            overall_alignment=overall_alignment,
            alignment_level=alignment_level,
            conflicts=conflicts,
            recommendation=recommendation,
            explanation=explanation,
        )

    async def _get_user_goals(self) -> List[Goal]:
        """Get user-defined goals."""
        return [g for g in self._goals.values() if g.goal_type == GoalType.USER and g.is_active]

    async def _get_system_goals(self) -> List[Goal]:
        """Get system goals."""
        return [
            g
            for g in self._goals.values()
            if g.goal_type in (GoalType.SYSTEM, GoalType.PERFORMANCE, GoalType.EFFICIENCY)
            and g.is_active
        ]

    def _measure_user_alignment(
        self,
        decision: AutonomousDecision,
        user_goals: List[Goal],
    ) -> float:
        """Measure alignment with user goals."""
        if not user_goals:
            return 1.0  # No user goals = no conflict

        alignment_scores = []
        for goal in user_goals:
            score = self._check_goal_alignment(decision, goal)
            alignment_scores.append(score * goal.weight)

        total_weight = sum(g.weight for g in user_goals)
        return sum(alignment_scores) / total_weight if total_weight > 0 else 1.0

    def _measure_system_alignment(
        self,
        decision: AutonomousDecision,
        system_goals: List[Goal],
    ) -> float:
        """Measure alignment with system goals."""
        if not system_goals:
            return 1.0

        alignment_scores = []
        for goal in system_goals:
            score = self._check_goal_alignment(decision, goal)
            alignment_scores.append(score * goal.weight)

        total_weight = sum(g.weight for g in system_goals)
        return sum(alignment_scores) / total_weight if total_weight > 0 else 1.0

    def _measure_safety_alignment(
        self,
        decision: AutonomousDecision,
        safety_goals: List[Goal],
    ) -> float:
        """Measure alignment with safety goals."""
        if not safety_goals:
            return 1.0

        # Safety alignment is strict - any violation counts heavily
        alignment_scores = []
        for goal in safety_goals:
            score = self._check_safety_goal(decision, goal)
            alignment_scores.append(score * goal.weight)

        total_weight = sum(g.weight for g in safety_goals)
        return sum(alignment_scores) / total_weight if total_weight > 0 else 1.0

    def _check_goal_alignment(
        self,
        decision: AutonomousDecision,
        goal: Goal,
    ) -> float:
        """Check if decision aligns with a specific goal."""
        criteria = goal.criteria

        # Check various criteria types
        score = 1.0

        # Check if action is in blocked list
        if "blocked_actions" in criteria:
            if decision.action in criteria["blocked_actions"]:
                return 0.0

        # Check if action is in allowed list (if specified)
        if "allowed_actions" in criteria:
            if decision.action not in criteria["allowed_actions"]:
                score *= 0.5

        # Check impact level
        if "max_impact" in criteria:
            impact_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            max_allowed = impact_levels.get(criteria["max_impact"], 4)
            actual = impact_levels.get(decision.impact.lower(), 2)
            if actual > max_allowed:
                score *= 0.3

        # Check affected entities
        if "protected_entities" in criteria:
            protected = set(criteria["protected_entities"])
            affected = set(decision.affected_entities)
            if protected & affected:
                score *= 0.5

        return score

    def _check_safety_goal(
        self,
        decision: AutonomousDecision,
        goal: Goal,
    ) -> float:
        """Check safety goal alignment (stricter than regular goals)."""
        criteria = goal.criteria
        score = 1.0

        # Check risk level
        if "max_risk_level" in criteria:
            risk_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            max_allowed = risk_levels.get(criteria["max_risk_level"], 2)
            actual = risk_levels.get(decision.impact.lower(), 2)
            if actual > max_allowed:
                return 0.0  # Strict - safety violation

        # Check if confirmation required
        if "requires_confirmation_above" in criteria:
            threshold = criteria["requires_confirmation_above"]
            threshold_levels = {"low": 1, "medium": 2, "high": 3}
            threshold_val = threshold_levels.get(threshold, 2)
            impact_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            actual = impact_levels.get(decision.impact.lower(), 2)
            if actual > threshold_val:
                score *= 0.7  # Not a full violation, but needs review

        # Check for destructive actions
        destructive_keywords = ["delete", "remove", "destroy", "reset", "clear"]
        if any(kw in decision.action.lower() for kw in destructive_keywords):
            score *= 0.5

        return score

    def _detect_conflicts(
        self,
        decision: AutonomousDecision,
        user_goals: List[Goal],
        system_goals: List[Goal],
        safety_goals: List[Goal],
    ) -> List[GoalConflict]:
        """Detect conflicts between decision and goals."""
        conflicts = []

        all_goals = user_goals + system_goals + safety_goals

        for goal in all_goals:
            alignment = self._check_goal_alignment(decision, goal)
            if alignment < 0.5:
                severity = 1.0 - alignment
                conflicts.append(
                    GoalConflict(
                        goal1_id=goal.goal_id,
                        goal2_id=None,
                        decision_id=decision.decision_id,
                        conflict_type="goal_violation",
                        severity=severity,
                        description=f"Decision conflicts with goal: {goal.description}",
                        resolution_suggestion=self._suggest_resolution(decision, goal),
                    )
                )

        # Check for inter-goal conflicts
        for i, goal1 in enumerate(all_goals):
            for goal2 in all_goals[i + 1 :]:
                conflict = self._check_goal_conflict(goal1, goal2)
                if conflict:
                    conflicts.append(conflict)

        return conflicts

    def _check_goal_conflict(
        self,
        goal1: Goal,
        goal2: Goal,
    ) -> Optional[GoalConflict]:
        """Check if two goals conflict with each other."""
        # Check for obvious conflicts (e.g., performance vs efficiency)
        if goal1.goal_type == GoalType.PERFORMANCE and goal2.goal_type == GoalType.EFFICIENCY:
            # These can conflict - high performance may require more resources
            if (
                goal1.criteria.get("target_p95_ms", 5000) < 1000
                and goal2.criteria.get("target_utilization", 0.7) < 0.5
            ):
                return GoalConflict(
                    goal1_id=goal1.goal_id,
                    goal2_id=goal2.goal_id,
                    decision_id=None,
                    conflict_type="goal_tension",
                    severity=0.3,
                    description="Performance and efficiency goals may conflict",
                    resolution_suggestion="Prioritize based on current system state",
                )

        return None

    def _determine_alignment_level(
        self,
        overall_alignment: float,
        conflicts: List[GoalConflict],
    ) -> AlignmentLevel:
        """Determine overall alignment level."""
        # Check for critical conflicts first
        critical_conflicts = [c for c in conflicts if c.severity > 0.8]
        if critical_conflicts:
            return AlignmentLevel.CONFLICTING

        if overall_alignment >= self.FULL_ALIGNMENT_THRESHOLD:
            return AlignmentLevel.FULL
        elif overall_alignment >= self.PARTIAL_ALIGNMENT_THRESHOLD:
            return AlignmentLevel.PARTIAL
        elif overall_alignment >= self.MISALIGNMENT_THRESHOLD:
            return AlignmentLevel.MISALIGNED
        else:
            return AlignmentLevel.CONFLICTING

    def _recommend_action(
        self,
        alignment_level: AlignmentLevel,
        conflicts: List[GoalConflict],
        safety_alignment: float,
    ) -> ActionRecommendation:
        """Generate action recommendation based on alignment."""
        # Safety violations always require review or block
        if safety_alignment < 0.5:
            return ActionRecommendation.BLOCK
        elif safety_alignment < 0.8:
            return ActionRecommendation.REQUIRES_REVIEW

        # Check alignment level
        if alignment_level == AlignmentLevel.FULL:
            return ActionRecommendation.PROCEED
        elif alignment_level == AlignmentLevel.PARTIAL:
            return ActionRecommendation.PROCEED_WITH_CAUTION
        elif alignment_level == AlignmentLevel.MISALIGNED:
            return ActionRecommendation.REQUIRES_REVIEW
        else:
            return ActionRecommendation.BLOCK

    def _generate_explanation(
        self,
        decision: AutonomousDecision,
        user_alignment: float,
        system_alignment: float,
        safety_alignment: float,
        conflicts: List[GoalConflict],
    ) -> str:
        """Generate human-readable explanation of alignment analysis."""
        parts = []

        parts.append(f"Decision '{decision.action}' alignment analysis:")
        parts.append(f"- User goals alignment: {user_alignment:.0%}")
        parts.append(f"- System goals alignment: {system_alignment:.0%}")
        parts.append(f"- Safety alignment: {safety_alignment:.0%}")

        if conflicts:
            parts.append(f"\nDetected {len(conflicts)} conflict(s):")
            for conflict in conflicts[:3]:  # Show top 3
                parts.append(f"- {conflict.description}")

        return "\n".join(parts)

    def _suggest_resolution(
        self,
        decision: AutonomousDecision,
        goal: Goal,
    ) -> str:
        """Suggest resolution for a goal conflict."""
        if goal.goal_type == GoalType.SAFETY:
            return "Consider reducing impact level or requiring human approval"
        elif goal.goal_type == GoalType.USER:
            return "Verify decision aligns with user preferences or request clarification"
        else:
            return "Review system constraints and adjust decision parameters"

    async def add_goal(self, goal: Goal) -> None:
        """Add a new goal."""
        self._goals[goal.goal_id] = goal
        await self._save_goal(goal)

    async def remove_goal(self, goal_id: str) -> bool:
        """Remove a goal."""
        if goal_id in self._goals:
            del self._goals[goal_id]
            await self._db.execute(
                "DELETE FROM alignment_goals WHERE id = ?",
                [goal_id],
            )
            return True
        return False

    async def update_goal(self, goal: Goal) -> None:
        """Update an existing goal."""
        self._goals[goal.goal_id] = goal
        await self._save_goal(goal)

    async def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        return self._goals.get(goal_id)

    async def get_all_goals(self) -> List[Goal]:
        """Get all goals."""
        return list(self._goals.values())

    async def get_goal_progress(
        self,
        goal_id: str,
        window_hours: int = 24,
    ) -> GoalProgress:
        """Get progress toward a goal."""
        goal = self._goals.get(goal_id)
        if not goal:
            return GoalProgress(
                goal_id=goal_id,
                progress=0.0,
                trend="unknown",
                recent_contributions=0,
                last_updated=datetime.now(timezone.utc),
            )

        # Calculate progress based on goal type
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        if goal.goal_type == GoalType.PERFORMANCE:
            # Check success rate against target
            query = """
                SELECT AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate,
                       COUNT(*) as count
                FROM learning_outcomes
                WHERE created_at >= ?
            """
            row = await self._db.fetch_one(query, [cutoff.isoformat()])
            success_rate = row["success_rate"] or 0.0
            target = goal.criteria.get("min_success_rate", 0.95)
            progress = min(1.0, success_rate / target)
            contributions = row["count"] or 0
        else:
            progress = 0.5  # Default for goals we can't measure directly
            contributions = 0

        # Determine trend (would need historical data)
        trend = "stable"

        return GoalProgress(
            goal_id=goal_id,
            progress=progress,
            trend=trend,
            recent_contributions=contributions,
            last_updated=datetime.now(timezone.utc),
        )

    async def _save_goal(self, goal: Goal) -> None:
        """Save a goal to the database."""
        await self._db.execute(
            """
            INSERT OR REPLACE INTO alignment_goals (
                id, goal_type, priority, description, criteria_json,
                weight, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                goal.goal_id,
                goal.goal_type.value,
                goal.priority.value,
                goal.description,
                json.dumps(goal.criteria),
                goal.weight,
                goal.is_active,
                goal.created_at.isoformat(),
            ],
        )

    async def _load_goals(self) -> None:
        """Load goals from database."""
        rows = await self._db.fetch_all("SELECT * FROM alignment_goals WHERE is_active = 1")

        for row in rows:
            goal = Goal(
                goal_id=row["id"],
                goal_type=GoalType(row["goal_type"]),
                priority=GoalPriority(row["priority"]),
                description=row["description"],
                criteria=json.loads(row["criteria_json"]) if row["criteria_json"] else {},
                weight=row.get("weight", 1.0),
                is_active=bool(row.get("is_active", True)),
                created_at=(
                    datetime.fromisoformat(row["created_at"])
                    if row.get("created_at")
                    else datetime.now(timezone.utc)
                ),
            )
            self._goals[goal.goal_id] = goal

    async def save_alignment_result(self, score: AlignmentScore) -> None:
        """Save alignment verification result."""
        await self._db.execute(
            """
            INSERT INTO alignment_results (
                decision_id, user_alignment, system_alignment, safety_alignment,
                overall_alignment, alignment_level, recommendation,
                conflicts_json, explanation, verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                score.decision_id,
                score.user_alignment,
                score.system_alignment,
                score.safety_alignment,
                score.overall_alignment,
                score.alignment_level.value,
                score.recommendation.value,
                json.dumps([c.to_dict() for c in score.conflicts]),
                score.explanation,
                score.verified_at.isoformat(),
            ],
        )

    async def get_stats(self) -> Dict[str, Any]:
        """Get goal aligner statistics."""
        total_goals = len(self._goals)
        goals_by_type = {}
        for goal in self._goals.values():
            goal_type = goal.goal_type.value
            goals_by_type[goal_type] = goals_by_type.get(goal_type, 0) + 1

        # Get recent alignment results
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        results_row = await self._db.fetch_one(
            """
            SELECT COUNT(*) as count,
                   AVG(overall_alignment) as avg_alignment
            FROM alignment_results
            WHERE verified_at >= ?
            """,
            [cutoff.isoformat()],
        )

        return {
            "total_goals": total_goals,
            "goals_by_type": goals_by_type,
            "recent_verifications": results_row["count"] if results_row else 0,
            "avg_alignment_24h": results_row["avg_alignment"] if results_row else None,
        }
