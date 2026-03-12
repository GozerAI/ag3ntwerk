"""
Human handoff optimization for the ag3ntwerk learning system.

Minimizes human intervention while maximizing trust by learning
which actions can be safely automated and which require human review.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .models import TaskOutcomeRecord
from .outcome_tracker import OutcomeTracker
from .pattern_store import PatternStore


class TrustLevel(str, Enum):
    """Trust levels for automated actions."""

    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FULL = "full"


class HandoffReason(str, Enum):
    """Reasons for human handoff."""

    NOVEL_SITUATION = "novel_situation"
    LOW_CONFIDENCE = "low_confidence"
    HIGH_IMPACT = "high_impact"
    SAFETY_CHECK = "safety_check"
    USER_PREFERENCE = "user_preference"
    PATTERN_VIOLATION = "pattern_violation"


class PromotionStatus(str, Enum):
    """Status of action promotion."""

    PENDING = "pending"
    PROMOTED = "promoted"
    DEMOTED = "demoted"
    STABLE = "stable"


@dataclass
class ActionTrust:
    """Trust level for a specific action."""

    action: str
    category: str
    trust_level: TrustLevel
    success_count: int
    failure_count: int
    approval_rate: float
    avg_time_to_approval_ms: float
    last_failure: Optional[datetime]
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "category": self.category,
            "trust_level": self.trust_level.value,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "approval_rate": self.approval_rate,
            "avg_time_to_approval_ms": self.avg_time_to_approval_ms,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class PromotableAction:
    """An action that could be promoted to higher autonomy."""

    action: str
    category: str
    current_trust: TrustLevel
    recommended_trust: TrustLevel
    evidence: Dict[str, Any]
    confidence: float
    risk_assessment: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "category": self.category,
            "current_trust": self.current_trust.value,
            "recommended_trust": self.recommended_trust.value,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "risk_assessment": self.risk_assessment,
        }


@dataclass
class DemotableAction:
    """An action that should be demoted to lower autonomy."""

    action: str
    category: str
    current_trust: TrustLevel
    recommended_trust: TrustLevel
    reason: str
    recent_failures: int
    failure_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "category": self.category,
            "current_trust": self.current_trust.value,
            "recommended_trust": self.recommended_trust.value,
            "reason": self.reason,
            "recent_failures": self.recent_failures,
            "failure_rate": self.failure_rate,
        }


@dataclass
class HandoffStrategy:
    """Strategy for optimizing human handoffs."""

    strategy_id: str
    created_at: datetime
    actions_to_promote: List[PromotableAction]
    actions_to_demote: List[DemotableAction]
    estimated_human_time_saved_hours: float
    estimated_risk_increase: float
    current_handoff_rate: float
    projected_handoff_rate: float
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "created_at": self.created_at.isoformat(),
            "actions_to_promote": [a.to_dict() for a in self.actions_to_promote],
            "actions_to_demote": [a.to_dict() for a in self.actions_to_demote],
            "estimated_human_time_saved_hours": self.estimated_human_time_saved_hours,
            "estimated_risk_increase": self.estimated_risk_increase,
            "current_handoff_rate": self.current_handoff_rate,
            "projected_handoff_rate": self.projected_handoff_rate,
            "recommendations": self.recommendations,
        }


@dataclass
class ApprovalHistory:
    """History of a human approval."""

    approval_id: str
    action: str
    category: str
    approved: bool
    time_to_decision_ms: float
    approver: str
    notes: Optional[str]
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "action": self.action,
            "category": self.category,
            "approved": self.approved,
            "time_to_decision_ms": self.time_to_decision_ms,
            "approver": self.approver,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


class HandoffOptimizer:
    """
    Optimizes human handoffs by learning what can be automated.

    Tracks approval history to identify:
    - Actions that can be promoted to full automation
    - Actions that need more human oversight
    - Patterns in human decisions
    """

    # Thresholds for trust level changes
    MIN_SAMPLES_FOR_PROMOTION = 20
    MIN_SUCCESS_RATE_FOR_PROMOTION = 0.95
    MAX_FAILURE_RATE_FOR_DEMOTION = 0.1
    RECENT_FAILURE_THRESHOLD = 3

    # Time windows
    ANALYSIS_WINDOW_HOURS = 168  # 1 week

    def __init__(
        self,
        db: Any,
        outcome_tracker: OutcomeTracker,
        pattern_store: PatternStore,
    ):
        self._db = db
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store
        self._action_trust: Dict[str, ActionTrust] = {}

    async def optimize_handoffs(
        self,
        window_hours: int = 168,
    ) -> HandoffStrategy:
        """
        Generate optimized handoff strategy.

        Args:
            window_hours: Time window for analysis

        Returns:
            HandoffStrategy with recommendations
        """
        import uuid

        # Get approval history
        approval_history = await self._get_approval_history(window_hours)

        # Calculate trust levels
        trust_levels = self._calculate_trust_levels(approval_history)

        # Identify promotable actions
        actions_to_promote = self._identify_promotable(trust_levels, approval_history)

        # Identify demotable actions
        actions_to_demote = self._identify_demotable(trust_levels, approval_history)

        # Calculate metrics
        current_handoff_rate = await self._calculate_handoff_rate(window_hours)
        projected_handoff_rate = self._project_handoff_rate(
            current_handoff_rate, actions_to_promote, actions_to_demote
        )
        estimated_savings = self._calculate_savings(actions_to_promote, approval_history)
        estimated_risk = self._calculate_risk_increase(actions_to_promote)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            actions_to_promote, actions_to_demote, current_handoff_rate
        )

        return HandoffStrategy(
            strategy_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            actions_to_promote=actions_to_promote,
            actions_to_demote=actions_to_demote,
            estimated_human_time_saved_hours=estimated_savings,
            estimated_risk_increase=estimated_risk,
            current_handoff_rate=current_handoff_rate,
            projected_handoff_rate=projected_handoff_rate,
            recommendations=recommendations,
        )

    async def _get_approval_history(
        self,
        window_hours: int,
    ) -> List[ApprovalHistory]:
        """Get approval history for analysis."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        query = """
            SELECT *
            FROM approval_history
            WHERE created_at >= ?
            ORDER BY created_at DESC
        """

        rows = await self._db.fetch_all(query, [cutoff.isoformat()])

        history = []
        for row in rows:
            history.append(
                ApprovalHistory(
                    approval_id=row["id"],
                    action=row["action"],
                    category=row["category"],
                    approved=bool(row["approved"]),
                    time_to_decision_ms=row.get("time_to_decision_ms", 0.0),
                    approver=row.get("approver", "unknown"),
                    notes=row.get("notes"),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )

        return history

    def _calculate_trust_levels(
        self,
        approval_history: List[ApprovalHistory],
    ) -> Dict[str, ActionTrust]:
        """Calculate trust levels for each action."""
        # Group by action
        action_stats: Dict[str, Dict[str, Any]] = {}

        for approval in approval_history:
            key = f"{approval.category}:{approval.action}"
            if key not in action_stats:
                action_stats[key] = {
                    "action": approval.action,
                    "category": approval.category,
                    "successes": 0,
                    "failures": 0,
                    "approval_times": [],
                    "last_failure": None,
                }

            if approval.approved:
                action_stats[key]["successes"] += 1
            else:
                action_stats[key]["failures"] += 1
                if (
                    not action_stats[key]["last_failure"]
                    or approval.created_at > action_stats[key]["last_failure"]
                ):
                    action_stats[key]["last_failure"] = approval.created_at

            action_stats[key]["approval_times"].append(approval.time_to_decision_ms)

        # Calculate trust levels
        trust_levels = {}
        for key, stats in action_stats.items():
            total = stats["successes"] + stats["failures"]
            if total == 0:
                continue

            success_rate = stats["successes"] / total
            avg_time = (
                sum(stats["approval_times"]) / len(stats["approval_times"])
                if stats["approval_times"]
                else 0
            )

            # Determine trust level based on history
            if total >= self.MIN_SAMPLES_FOR_PROMOTION:
                if success_rate >= 0.99:
                    trust_level = TrustLevel.FULL
                elif success_rate >= 0.95:
                    trust_level = TrustLevel.HIGH
                elif success_rate >= 0.8:
                    trust_level = TrustLevel.MEDIUM
                elif success_rate >= 0.5:
                    trust_level = TrustLevel.LOW
                else:
                    trust_level = TrustLevel.UNTRUSTED
            else:
                # Not enough data - be conservative
                trust_level = TrustLevel.LOW if success_rate >= 0.7 else TrustLevel.UNTRUSTED

            trust_levels[key] = ActionTrust(
                action=stats["action"],
                category=stats["category"],
                trust_level=trust_level,
                success_count=stats["successes"],
                failure_count=stats["failures"],
                approval_rate=success_rate,
                avg_time_to_approval_ms=avg_time,
                last_failure=stats["last_failure"],
            )

        return trust_levels

    def _identify_promotable(
        self,
        trust_levels: Dict[str, ActionTrust],
        approval_history: List[ApprovalHistory],
    ) -> List[PromotableAction]:
        """Identify actions that can be promoted to higher autonomy."""
        promotable = []

        for key, trust in trust_levels.items():
            total = trust.success_count + trust.failure_count

            # Check if eligible for promotion
            if total < self.MIN_SAMPLES_FOR_PROMOTION:
                continue

            if trust.approval_rate < self.MIN_SUCCESS_RATE_FOR_PROMOTION:
                continue

            # Determine recommended trust level
            recommended = self._get_higher_trust_level(trust.trust_level)
            if recommended == trust.trust_level:
                continue  # Already at highest level

            # Calculate confidence
            confidence = min(1.0, total / 50) * trust.approval_rate

            # Build evidence
            evidence = {
                "success_count": trust.success_count,
                "failure_count": trust.failure_count,
                "approval_rate": trust.approval_rate,
                "avg_approval_time_ms": trust.avg_time_to_approval_ms,
            }

            # Assess risk
            risk = "Low" if trust.approval_rate >= 0.99 else "Medium"

            promotable.append(
                PromotableAction(
                    action=trust.action,
                    category=trust.category,
                    current_trust=trust.trust_level,
                    recommended_trust=recommended,
                    evidence=evidence,
                    confidence=confidence,
                    risk_assessment=risk,
                )
            )

        return promotable

    def _identify_demotable(
        self,
        trust_levels: Dict[str, ActionTrust],
        approval_history: List[ApprovalHistory],
    ) -> List[DemotableAction]:
        """Identify actions that should be demoted to lower autonomy."""
        demotable = []

        # Check for recent failures
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_failures: Dict[str, int] = {}

        for approval in approval_history:
            if not approval.approved and approval.created_at >= recent_cutoff:
                key = f"{approval.category}:{approval.action}"
                recent_failures[key] = recent_failures.get(key, 0) + 1

        for key, trust in trust_levels.items():
            total = trust.success_count + trust.failure_count
            if total == 0:
                continue

            failure_rate = trust.failure_count / total
            recent = recent_failures.get(key, 0)

            # Check if should be demoted
            should_demote = False
            reason = ""

            if recent >= self.RECENT_FAILURE_THRESHOLD:
                should_demote = True
                reason = f"High recent failures ({recent} in 24h)"
            elif failure_rate > self.MAX_FAILURE_RATE_FOR_DEMOTION and total >= 10:
                should_demote = True
                reason = f"High failure rate ({failure_rate:.1%})"

            if should_demote and trust.trust_level != TrustLevel.UNTRUSTED:
                recommended = self._get_lower_trust_level(trust.trust_level)

                demotable.append(
                    DemotableAction(
                        action=trust.action,
                        category=trust.category,
                        current_trust=trust.trust_level,
                        recommended_trust=recommended,
                        reason=reason,
                        recent_failures=recent,
                        failure_rate=failure_rate,
                    )
                )

        return demotable

    def _get_higher_trust_level(self, current: TrustLevel) -> TrustLevel:
        """Get the next higher trust level."""
        levels = [
            TrustLevel.UNTRUSTED,
            TrustLevel.LOW,
            TrustLevel.MEDIUM,
            TrustLevel.HIGH,
            TrustLevel.FULL,
        ]
        idx = levels.index(current)
        return levels[min(idx + 1, len(levels) - 1)]

    def _get_lower_trust_level(self, current: TrustLevel) -> TrustLevel:
        """Get the next lower trust level."""
        levels = [
            TrustLevel.UNTRUSTED,
            TrustLevel.LOW,
            TrustLevel.MEDIUM,
            TrustLevel.HIGH,
            TrustLevel.FULL,
        ]
        idx = levels.index(current)
        return levels[max(idx - 1, 0)]

    async def _calculate_handoff_rate(self, window_hours: int) -> float:
        """Calculate current handoff rate."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # Count total actions and handoffs
        total_row = await self._db.fetch_one(
            """
            SELECT COUNT(*) as count FROM autonomy_action_logs
            WHERE created_at >= ?
            """,
            [cutoff.isoformat()],
        )
        handoff_row = await self._db.fetch_one(
            """
            SELECT COUNT(*) as count FROM approval_history
            WHERE created_at >= ?
            """,
            [cutoff.isoformat()],
        )

        total = total_row["count"] if total_row else 0
        handoffs = handoff_row["count"] if handoff_row else 0

        if total == 0:
            return 0.0

        return handoffs / total

    def _project_handoff_rate(
        self,
        current_rate: float,
        actions_to_promote: List[PromotableAction],
        actions_to_demote: List[DemotableAction],
    ) -> float:
        """Project handoff rate after applying changes."""
        # Estimate reduction from promotions
        promotion_reduction = len(actions_to_promote) * 0.02  # Each promotion reduces by ~2%

        # Estimate increase from demotions
        demotion_increase = len(actions_to_demote) * 0.01  # Each demotion increases by ~1%

        projected = current_rate - promotion_reduction + demotion_increase
        return max(0.0, min(1.0, projected))

    def _calculate_savings(
        self,
        actions_to_promote: List[PromotableAction],
        approval_history: List[ApprovalHistory],
    ) -> float:
        """Calculate estimated human time savings."""
        # Get average approval time
        if not approval_history:
            return 0.0

        avg_time_ms = sum(a.time_to_decision_ms for a in approval_history) / len(approval_history)

        # Estimate actions per week that would be automated
        automated_per_week = len(actions_to_promote) * 10  # Rough estimate

        # Calculate hours saved
        time_saved_ms = automated_per_week * avg_time_ms
        time_saved_hours = time_saved_ms / (1000 * 60 * 60)

        return time_saved_hours

    def _calculate_risk_increase(
        self,
        actions_to_promote: List[PromotableAction],
    ) -> float:
        """Calculate estimated risk increase from promotions."""
        if not actions_to_promote:
            return 0.0

        # Weight risk by confidence
        total_risk = 0.0
        for action in actions_to_promote:
            # Lower confidence = higher risk
            risk = (1 - action.confidence) * 0.1
            total_risk += risk

        return min(1.0, total_risk)

    def _generate_recommendations(
        self,
        actions_to_promote: List[PromotableAction],
        actions_to_demote: List[DemotableAction],
        current_handoff_rate: float,
    ) -> List[str]:
        """Generate recommendations for handoff optimization."""
        recommendations = []

        if actions_to_promote:
            high_confidence = [a for a in actions_to_promote if a.confidence > 0.9]
            if high_confidence:
                recommendations.append(
                    f"Consider promoting {len(high_confidence)} high-confidence actions "
                    f"to reduce human workload"
                )

        if actions_to_demote:
            recommendations.append(
                f"Review {len(actions_to_demote)} actions with elevated failure rates"
            )

        if current_handoff_rate > 0.3:
            recommendations.append(
                "Current handoff rate is high (>30%). Focus on building trust "
                "through consistent automation success"
            )
        elif current_handoff_rate < 0.05:
            recommendations.append("Very low handoff rate (<5%). Ensure safety checks are adequate")

        if not recommendations:
            recommendations.append("Handoff optimization is on track. Continue monitoring.")

        return recommendations

    async def record_approval(
        self,
        approval_id: str,
        action: str,
        category: str,
        approved: bool,
        time_to_decision_ms: float,
        approver: str,
        notes: Optional[str] = None,
    ) -> None:
        """Record a human approval decision."""
        await self._db.execute(
            """
            INSERT INTO approval_history (
                id, action, category, approved, time_to_decision_ms,
                approver, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                approval_id,
                action,
                category,
                approved,
                time_to_decision_ms,
                approver,
                notes,
                datetime.now(timezone.utc).isoformat(),
            ],
        )

        # Update cached trust levels
        await self._update_action_trust(action, category, approved)

    async def _update_action_trust(
        self,
        action: str,
        category: str,
        approved: bool,
    ) -> None:
        """Update trust level for an action after approval."""
        key = f"{category}:{action}"

        if key in self._action_trust:
            trust = self._action_trust[key]
            if approved:
                trust.success_count += 1
            else:
                trust.failure_count += 1
                trust.last_failure = datetime.now(timezone.utc)

            total = trust.success_count + trust.failure_count
            trust.approval_rate = trust.success_count / total if total > 0 else 0.0
            trust.last_updated = datetime.now(timezone.utc)

    async def get_action_trust(self, action: str, category: str) -> Optional[ActionTrust]:
        """Get trust level for a specific action."""
        key = f"{category}:{action}"
        return self._action_trust.get(key)

    async def get_all_action_trusts(self) -> List[ActionTrust]:
        """Get all action trust levels."""
        return list(self._action_trust.values())

    async def promote_action(
        self,
        action: str,
        category: str,
        new_trust: TrustLevel,
        promoter: str,
    ) -> bool:
        """Manually promote an action to higher trust."""
        key = f"{category}:{action}"

        await self._db.execute(
            """
            INSERT INTO trust_changes (
                action, category, old_trust, new_trust,
                changed_by, change_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                action,
                category,
                self._action_trust.get(
                    key,
                    ActionTrust(
                        action=action,
                        category=category,
                        trust_level=TrustLevel.UNTRUSTED,
                        success_count=0,
                        failure_count=0,
                        approval_rate=0.0,
                        avg_time_to_approval_ms=0.0,
                        last_failure=None,
                    ),
                ).trust_level.value,
                new_trust.value,
                promoter,
                "promotion",
                datetime.now(timezone.utc).isoformat(),
            ],
        )

        if key in self._action_trust:
            self._action_trust[key].trust_level = new_trust

        return True

    async def demote_action(
        self,
        action: str,
        category: str,
        new_trust: TrustLevel,
        demoter: str,
        reason: str = "",
    ) -> bool:
        """Manually demote an action to lower trust."""
        key = f"{category}:{action}"

        await self._db.execute(
            """
            INSERT INTO trust_changes (
                action, category, old_trust, new_trust,
                changed_by, change_type, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                action,
                category,
                self._action_trust.get(
                    key,
                    ActionTrust(
                        action=action,
                        category=category,
                        trust_level=TrustLevel.MEDIUM,
                        success_count=0,
                        failure_count=0,
                        approval_rate=0.0,
                        avg_time_to_approval_ms=0.0,
                        last_failure=None,
                    ),
                ).trust_level.value,
                new_trust.value,
                demoter,
                "demotion",
                reason,
                datetime.now(timezone.utc).isoformat(),
            ],
        )

        if key in self._action_trust:
            self._action_trust[key].trust_level = new_trust

        return True

    async def save_strategy(self, strategy: HandoffStrategy) -> None:
        """Save handoff strategy to database."""
        await self._db.execute(
            """
            INSERT INTO handoff_strategies (
                id, created_at, actions_to_promote_json, actions_to_demote_json,
                estimated_savings_hours, estimated_risk,
                current_handoff_rate, projected_handoff_rate,
                recommendations_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                strategy.strategy_id,
                strategy.created_at.isoformat(),
                json.dumps([a.to_dict() for a in strategy.actions_to_promote]),
                json.dumps([a.to_dict() for a in strategy.actions_to_demote]),
                strategy.estimated_human_time_saved_hours,
                strategy.estimated_risk_increase,
                strategy.current_handoff_rate,
                strategy.projected_handoff_rate,
                json.dumps(strategy.recommendations),
            ],
        )

    async def get_stats(self) -> Dict[str, Any]:
        """Get handoff optimizer statistics."""
        # Get recent stats
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        approval_row = await self._db.fetch_one(
            """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN approved THEN 1 ELSE 0 END) as approved,
                   AVG(time_to_decision_ms) as avg_time
            FROM approval_history
            WHERE created_at >= ?
            """,
            [cutoff.isoformat()],
        )

        trust_counts = {}
        for trust in self._action_trust.values():
            level = trust.trust_level.value
            trust_counts[level] = trust_counts.get(level, 0) + 1

        return {
            "total_approvals_24h": approval_row["total"] if approval_row else 0,
            "approval_rate_24h": (
                approval_row["approved"] / approval_row["total"]
                if approval_row and approval_row["total"] > 0
                else 0.0
            ),
            "avg_decision_time_ms": approval_row["avg_time"] if approval_row else 0.0,
            "actions_by_trust_level": trust_counts,
            "total_tracked_actions": len(self._action_trust),
        }
