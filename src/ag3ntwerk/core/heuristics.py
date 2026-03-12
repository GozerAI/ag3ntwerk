"""
Heuristic Engine for ag3ntwerk agents.

Self-tuning rules that adapt based on outcome feedback. Each agent
gets a HeuristicEngine with default heuristics that can be extended.

Heuristics have bounded thresholds and auto-deactivate when they
consistently fail (circuit breaker pattern).
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================
# Constants
# ============================================================

TUNE_STEP = 0.05
MIN_SAMPLES = 10
MIN_THRESHOLD = 0.1
MAX_THRESHOLD = 0.9
AUTO_DEACTIVATE_THRESHOLD = 0.2
AUTO_DEACTIVATE_MIN_SAMPLES = 20


# ============================================================
# Heuristic
# ============================================================


@dataclass
class Heuristic:
    """
    A self-tuning rule that fires when conditions are met.

    Thresholds auto-adjust based on outcome feedback:
    - success_rate < 0.4 -> raise threshold (fire less often)
    - success_rate > 0.8 -> lower threshold (fire more often)
    - success_rate < 0.2 after 20+ samples -> auto-deactivate
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    agent_code: str = ""
    condition: str = ""  # Description of when this heuristic applies
    action: str = ""  # Description of what this heuristic recommends
    threshold: float = 0.5  # Activation threshold (0.1-0.9)
    weight: float = 1.0  # Importance weight
    cooldown_seconds: float = 0.0  # Minimum time between firings
    times_triggered: int = 0
    success_rate: float = 0.5
    is_active: bool = True
    min_threshold: float = MIN_THRESHOLD
    max_threshold: float = MAX_THRESHOLD

    # Internal tracking
    _successes: int = field(default=0, repr=False)
    _failures: int = field(default=0, repr=False)
    _last_triggered: Optional[float] = field(default=None, repr=False)

    def __post_init__(self):
        self.threshold = max(self.min_threshold, min(self.max_threshold, self.threshold))

    @property
    def total_outcomes(self) -> int:
        return self._successes + self._failures

    @property
    def success_count(self) -> int:
        return self._successes

    @property
    def failure_count(self) -> int:
        return self._failures

    def can_fire(self, score: float) -> bool:
        """Check if this heuristic should fire given a relevance score."""
        if not self.is_active:
            return False

        if score < self.threshold:
            return False

        # Check cooldown
        if self.cooldown_seconds > 0 and self._last_triggered is not None:
            elapsed = time.time() - self._last_triggered
            if elapsed < self.cooldown_seconds:
                return False

        return True

    def fire(self) -> None:
        """Mark this heuristic as having fired."""
        self.times_triggered += 1
        self._last_triggered = time.time()

    def record_outcome(self, success: bool) -> None:
        """Record whether the heuristic's recommendation led to a good outcome."""
        if success:
            self._successes += 1
        else:
            self._failures += 1

        total = self._successes + self._failures
        if total > 0:
            self.success_rate = self._successes / total

    def tune(self) -> Optional[Dict[str, Any]]:
        """
        Auto-tune threshold based on outcomes.

        Returns dict describing the tuning action, or None.
        """
        if self.total_outcomes < MIN_SAMPLES:
            return None

        change = None

        # Auto-deactivate if consistently failing
        if (
            self.success_rate < AUTO_DEACTIVATE_THRESHOLD
            and self.total_outcomes >= AUTO_DEACTIVATE_MIN_SAMPLES
        ):
            self.is_active = False
            return {
                "heuristic_id": self.id,
                "action": "deactivated",
                "reason": f"success_rate={self.success_rate:.2f} after {self.total_outcomes} samples",
            }

        old_threshold = self.threshold

        if self.success_rate < 0.4:
            # Performing poorly: raise threshold (fire less often)
            self.threshold = min(self.max_threshold, self.threshold + TUNE_STEP)
            change = "raised"
        elif self.success_rate > 0.8:
            # Performing well: lower threshold (fire more often)
            self.threshold = max(self.min_threshold, self.threshold - TUNE_STEP)
            change = "lowered"

        if change and abs(self.threshold - old_threshold) > 1e-6:
            return {
                "heuristic_id": self.id,
                "action": f"threshold_{change}",
                "old_threshold": old_threshold,
                "new_threshold": self.threshold,
                "success_rate": self.success_rate,
            }

        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "agent_code": self.agent_code,
            "condition": self.condition,
            "action": self.action,
            "threshold": self.threshold,
            "weight": self.weight,
            "cooldown_seconds": self.cooldown_seconds,
            "times_triggered": self.times_triggered,
            "success_rate": self.success_rate,
            "is_active": self.is_active,
            "total_outcomes": self.total_outcomes,
        }


# ============================================================
# HeuristicAction
# ============================================================


@dataclass
class HeuristicAction:
    """Output from a heuristic evaluation — a recommended action."""

    heuristic_id: str
    action: str
    weight: float = 1.0
    context_modifications: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heuristic_id": self.heuristic_id,
            "action": self.action,
            "weight": self.weight,
            "context_modifications": self.context_modifications,
        }


# ============================================================
# HeuristicEngine
# ============================================================


class HeuristicEngine:
    """
    Per-agent heuristic engine.

    Manages a set of self-tuning heuristics, evaluates them against
    incoming tasks/context, and produces recommended actions.
    """

    def __init__(self, agent_code: str):
        self.agent_code = agent_code
        self._heuristics: Dict[str, Heuristic] = {}
        self._install_defaults()

    @property
    def all_heuristics(self) -> Dict[str, "Heuristic"]:
        return dict(self._heuristics)

    def _install_defaults(self) -> None:
        """Install universal default heuristics."""
        defaults = [
            Heuristic(
                name="failure_recovery",
                agent_code=self.agent_code,
                condition="consecutive_failures > 2",
                action="increase_thoroughness",
                threshold=0.3,
                weight=1.5,
                cooldown_seconds=30.0,
            ),
            Heuristic(
                name="confidence_boost",
                agent_code=self.agent_code,
                condition="recent_success_rate > 0.9",
                action="allow_higher_risk",
                threshold=0.7,
                weight=0.8,
            ),
            Heuristic(
                name="complexity_scaling",
                agent_code=self.agent_code,
                condition="task_complexity > threshold",
                action="request_collaboration",
                threshold=0.6,
                weight=1.0,
            ),
        ]

        for h in defaults:
            self._heuristics[h.id] = h

    def add_heuristic(self, heuristic: Heuristic) -> None:
        """Add a custom heuristic."""
        heuristic.agent_code = self.agent_code
        self._heuristics[heuristic.id] = heuristic

    def remove_heuristic(self, heuristic_id: str) -> bool:
        """Remove a heuristic by ID."""
        return self._heuristics.pop(heuristic_id, None) is not None

    def get_heuristic(self, heuristic_id: str) -> Optional[Heuristic]:
        """Get a heuristic by ID."""
        return self._heuristics.get(heuristic_id)

    def evaluate(
        self,
        task: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[HeuristicAction]:
        """
        Evaluate all active heuristics against the current task/context.

        Args:
            task: The current task (optional)
            context: Execution context with metrics like consecutive_failures,
                     recent_success_rate, task_complexity, etc.

        Returns:
            List of recommended actions from heuristics that fired
        """
        context = context or {}
        actions = []

        for heuristic in self._heuristics.values():
            if not heuristic.is_active:
                continue

            # Calculate a relevance score based on context
            score = self._calculate_relevance(heuristic, context)

            if heuristic.can_fire(score):
                heuristic.fire()

                action = HeuristicAction(
                    heuristic_id=heuristic.id,
                    action=heuristic.action,
                    weight=heuristic.weight,
                    context_modifications=self._get_modifications(heuristic, context),
                )
                actions.append(action)

        return actions

    def _calculate_relevance(
        self,
        heuristic: Heuristic,
        context: Dict[str, Any],
    ) -> float:
        """Calculate how relevant a heuristic is given current context."""
        name = heuristic.name

        if name == "failure_recovery":
            failures = context.get("consecutive_failures", 0)
            return min(1.0, failures / 3.0)

        elif name == "confidence_boost":
            rate = context.get("recent_success_rate", 0.5)
            return rate

        elif name == "complexity_scaling":
            complexity = context.get("task_complexity", 0.0)
            return complexity

        # For custom heuristics, use generic score
        return context.get("heuristic_score", 0.0)

    def _get_modifications(
        self,
        heuristic: Heuristic,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Get context modifications recommended by a heuristic."""
        name = heuristic.name

        if name == "failure_recovery":
            return {"increase_timeout": True, "add_validation": True}
        elif name == "confidence_boost":
            return {"allow_faster_execution": True}
        elif name == "complexity_scaling":
            return {"request_review": True, "split_task": True}

        return {}

    def record_outcome(self, heuristic_id: str, success: bool) -> None:
        """Record whether a heuristic action led to a good outcome."""
        heuristic = self._heuristics.get(heuristic_id)
        if heuristic:
            heuristic.record_outcome(success)

    def tune(self) -> List[Dict[str, Any]]:
        """
        Tune all heuristics based on accumulated outcomes.

        Returns list of tuning actions taken.
        """
        results = []
        for heuristic in self._heuristics.values():
            result = heuristic.tune()
            if result:
                results.append(result)
                logger.debug(f"Heuristic {heuristic.name} tuned: {result['action']}")
        return results

    def get_stats(self) -> Dict[str, Any]:
        active = sum(1 for h in self._heuristics.values() if h.is_active)
        return {
            "agent_code": self.agent_code,
            "total_heuristics": len(self._heuristics),
            "active_heuristics": active,
            "heuristics": [h.to_dict() for h in self._heuristics.values()],
        }
