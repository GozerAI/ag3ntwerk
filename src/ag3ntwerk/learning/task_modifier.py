"""
Task Modifier - Proactive task modification based on predicted risks.

Modifies tasks before execution to mitigate predicted failure risks:
1. Extends timeouts for timeout-prone tasks
2. Adds retry configuration for transient errors
3. Sets fallback agents for capability issues
4. Adjusts priority based on load
5. Adds context hints for error-prone scenarios
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ag3ntwerk.learning.failure_predictor import (
    FailurePredictor,
    FailureRisk,
    RiskLevel,
    MitigationType,
)
from ag3ntwerk.learning.load_balancer import LoadBalancer, LoadBalanceDecision
from ag3ntwerk.learning.models import ErrorCategory

logger = logging.getLogger(__name__)


@dataclass
class TaskModification:
    """A single modification to apply to a task."""

    modification_type: str  # timeout, retry, fallback, priority, context
    field_name: str
    original_value: Any
    new_value: Any
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "modification_type": self.modification_type,
            "field_name": self.field_name,
            "original_value": str(self.original_value),
            "new_value": str(self.new_value),
            "reason": self.reason,
        }


@dataclass
class ModifiedTask:
    """Result of task modification."""

    original_task: Dict[str, Any]
    modified_task: Dict[str, Any]
    modifications: List[TaskModification] = field(default_factory=list)

    # Risk assessment that drove modifications
    failure_risk: Optional[FailureRisk] = None
    load_decision: Optional[LoadBalanceDecision] = None

    # Whether the task was modified
    was_modified: bool = False

    # Summary
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "was_modified": self.was_modified,
            "modification_count": len(self.modifications),
            "modifications": [m.to_dict() for m in self.modifications],
            "summary": self.summary,
            "failure_risk": self.failure_risk.to_dict() if self.failure_risk else None,
        }


class TaskModifier:
    """
    Modifies tasks proactively based on predicted risks.

    Uses failure prediction and load balancing to:
    - Extend timeouts for timeout-prone scenarios
    - Add retry configuration for transient errors
    - Assign fallback agents for capability issues
    - Adjust priorities based on system load
    """

    # Timeout multipliers by risk level
    TIMEOUT_MULTIPLIERS = {
        RiskLevel.LOW: 1.0,
        RiskLevel.MODERATE: 1.25,
        RiskLevel.HIGH: 1.5,
        RiskLevel.CRITICAL: 2.0,
    }

    # Retry configuration by error category
    RETRY_CONFIG = {
        ErrorCategory.TIMEOUT: {"max_retries": 2, "backoff_multiplier": 1.5},
        ErrorCategory.RESOURCE: {"max_retries": 3, "backoff_multiplier": 2.0},
        ErrorCategory.EXTERNAL: {"max_retries": 2, "backoff_multiplier": 1.5},
        ErrorCategory.LOGIC: {
            "max_retries": 0,
            "backoff_multiplier": 1.0,
        },  # Don't retry logic errors
        ErrorCategory.CAPABILITY: {
            "max_retries": 0,
            "backoff_multiplier": 1.0,
        },  # Don't retry capability
    }

    # Default task values
    DEFAULT_TIMEOUT_MS = 30000
    DEFAULT_PRIORITY = 5

    def __init__(
        self,
        failure_predictor: FailurePredictor,
        load_balancer: LoadBalancer,
    ):
        """
        Initialize the task modifier.

        Args:
            failure_predictor: Failure prediction component
            load_balancer: Load balancing component
        """
        self._failure_predictor = failure_predictor
        self._load_balancer = load_balancer

    async def modify_task(
        self,
        task: Dict[str, Any],
        target_agent: str,
        candidates: Optional[List[str]] = None,
    ) -> ModifiedTask:
        """
        Modify a task based on predicted risks.

        Args:
            task: Task dictionary with at least task_type
            target_agent: Initially selected target agent
            candidates: Optional list of alternative agents for load balancing

        Returns:
            ModifiedTask with modifications applied
        """
        task_type = task.get("task_type", "unknown")
        context = task.get("context", {})

        # Get failure risk prediction
        failure_risk = await self._failure_predictor.predict_failure_risk(
            task_type=task_type,
            target_agent=target_agent,
            context=context,
        )

        # Get load-balanced agent if candidates provided
        load_decision = None
        if candidates and len(candidates) > 1:
            load_decision = await self._load_balancer.get_optimal_agent(
                task_type=task_type,
                candidates=candidates,
                context=context,
            )

        # Start with copy of original task
        modified_task = dict(task)
        modifications: List[TaskModification] = []

        # Apply modifications based on risk
        modifications.extend(self._apply_timeout_modification(modified_task, failure_risk))
        modifications.extend(self._apply_retry_modification(modified_task, failure_risk))
        modifications.extend(
            self._apply_agent_modification(modified_task, target_agent, failure_risk, load_decision)
        )
        modifications.extend(
            self._apply_priority_modification(modified_task, failure_risk, load_decision)
        )
        modifications.extend(self._apply_context_hints(modified_task, failure_risk))

        # Build summary
        summary = self._build_summary(modifications, failure_risk, load_decision)

        return ModifiedTask(
            original_task=task,
            modified_task=modified_task,
            modifications=modifications,
            failure_risk=failure_risk,
            load_decision=load_decision,
            was_modified=len(modifications) > 0,
            summary=summary,
        )

    def _apply_timeout_modification(
        self,
        task: Dict[str, Any],
        risk: FailureRisk,
    ) -> List[TaskModification]:
        """Apply timeout modifications based on risk."""
        modifications = []

        # Only modify for timeout risks
        if risk.primary_risk != ErrorCategory.TIMEOUT:
            return modifications

        # Get current timeout
        current_timeout = task.get("timeout_ms", self.DEFAULT_TIMEOUT_MS)
        multiplier = self.TIMEOUT_MULTIPLIERS.get(risk.risk_level, 1.0)

        if multiplier > 1.0:
            new_timeout = int(current_timeout * multiplier)
            task["timeout_ms"] = new_timeout

            modifications.append(
                TaskModification(
                    modification_type="timeout",
                    field_name="timeout_ms",
                    original_value=current_timeout,
                    new_value=new_timeout,
                    reason=f"Extended timeout due to {risk.risk_level.value} timeout risk "
                    f"({risk.score:.0%} probability)",
                )
            )

        return modifications

    def _apply_retry_modification(
        self,
        task: Dict[str, Any],
        risk: FailureRisk,
    ) -> List[TaskModification]:
        """Apply retry configuration based on error category."""
        modifications = []

        # Get retry config for primary risk category
        if not risk.primary_risk:
            return modifications

        retry_config = self.RETRY_CONFIG.get(risk.primary_risk)
        if not retry_config or retry_config["max_retries"] == 0:
            return modifications

        # Only add retries for moderate+ risk
        if risk.risk_level in (RiskLevel.LOW,):
            return modifications

        current_retries = task.get("max_retries", 0)
        recommended_retries = retry_config["max_retries"]

        if recommended_retries > current_retries:
            task["max_retries"] = recommended_retries
            task["retry_backoff_multiplier"] = retry_config["backoff_multiplier"]

            modifications.append(
                TaskModification(
                    modification_type="retry",
                    field_name="max_retries",
                    original_value=current_retries,
                    new_value=recommended_retries,
                    reason=f"Added retry configuration for {risk.primary_risk.value} errors",
                )
            )

        return modifications

    def _apply_agent_modification(
        self,
        task: Dict[str, Any],
        original_agent: str,
        risk: FailureRisk,
        load_decision: Optional[LoadBalanceDecision],
    ) -> List[TaskModification]:
        """Apply agent modifications based on risk and load."""
        modifications = []

        # Check if load balancer recommends different agent
        if load_decision and load_decision.chosen_agent != original_agent:
            # Only switch if load-balanced agent scores significantly better
            original_score = 0.0
            for agent, score in load_decision.all_scores:
                if agent == original_agent:
                    original_score = score
                    break

            if load_decision.score > original_score + 0.15:  # 15% better
                task["target_agent"] = load_decision.chosen_agent
                task["original_agent"] = original_agent

                modifications.append(
                    TaskModification(
                        modification_type="agent",
                        field_name="target_agent",
                        original_value=original_agent,
                        new_value=load_decision.chosen_agent,
                        reason=f"Reassigned to {load_decision.chosen_agent} for better load balance "
                        f"(score: {load_decision.score:.2f} vs {original_score:.2f})",
                    )
                )

        # Add fallback agent for capability risks
        if risk.primary_risk == ErrorCategory.CAPABILITY and risk.risk_level in (
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ):

            fallback = self._get_fallback_from_mitigations(risk)
            if fallback and fallback != task.get("target_agent", original_agent):
                task["fallback_agent"] = fallback

                modifications.append(
                    TaskModification(
                        modification_type="fallback",
                        field_name="fallback_agent",
                        original_value=None,
                        new_value=fallback,
                        reason=f"Added fallback agent due to {risk.risk_level.value} capability risk",
                    )
                )

        return modifications

    def _apply_priority_modification(
        self,
        task: Dict[str, Any],
        risk: FailureRisk,
        load_decision: Optional[LoadBalanceDecision],
    ) -> List[TaskModification]:
        """Adjust priority based on risk and load."""
        modifications = []

        current_priority = task.get("priority", self.DEFAULT_PRIORITY)

        # Increase priority for critical risks (to get attention faster)
        if risk.risk_level == RiskLevel.CRITICAL:
            new_priority = max(1, current_priority - 2)  # Lower number = higher priority
            if new_priority != current_priority:
                task["priority"] = new_priority
                modifications.append(
                    TaskModification(
                        modification_type="priority",
                        field_name="priority",
                        original_value=current_priority,
                        new_value=new_priority,
                        reason="Increased priority due to critical failure risk",
                    )
                )

        # Decrease priority if load is high (to reduce pressure)
        elif load_decision and load_decision.load_metrics:
            avg_utilization = sum(m.utilization for m in load_decision.load_metrics.values()) / len(
                load_decision.load_metrics
            )

            if avg_utilization > 0.8 and current_priority < 8:
                new_priority = min(10, current_priority + 1)
                task["priority"] = new_priority
                modifications.append(
                    TaskModification(
                        modification_type="priority",
                        field_name="priority",
                        original_value=current_priority,
                        new_value=new_priority,
                        reason=f"Reduced priority due to high system load ({avg_utilization:.0%} avg utilization)",
                    )
                )

        return modifications

    def _apply_context_hints(
        self,
        task: Dict[str, Any],
        risk: FailureRisk,
    ) -> List[TaskModification]:
        """Add context hints to help execution."""
        modifications = []

        if risk.risk_level in (RiskLevel.LOW,):
            return modifications

        hints = []

        # Add hints based on risk factors
        for factor in risk.risk_factors[:3]:  # Top 3 factors
            hints.append(f"Warning: {factor}")

        # Add hints based on mitigations
        for mitigation in risk.mitigations[:2]:
            hints.append(f"Suggestion: {mitigation.description}")

        if hints:
            existing_hints = task.get("execution_hints", [])
            task["execution_hints"] = existing_hints + hints

            modifications.append(
                TaskModification(
                    modification_type="context",
                    field_name="execution_hints",
                    original_value=existing_hints,
                    new_value=task["execution_hints"],
                    reason=f"Added {len(hints)} execution hints based on risk analysis",
                )
            )

        return modifications

    def _get_fallback_from_mitigations(self, risk: FailureRisk) -> Optional[str]:
        """Extract fallback agent from mitigations if available."""
        for mitigation in risk.mitigations:
            if mitigation.mitigation_type == MitigationType.USE_FALLBACK_AGENT:
                # Check parameters for fallback agent
                if mitigation.parameters.get("fallback_agent"):
                    return mitigation.parameters["fallback_agent"]
        return None

    def _build_summary(
        self,
        modifications: List[TaskModification],
        risk: FailureRisk,
        load_decision: Optional[LoadBalanceDecision],
    ) -> str:
        """Build a human-readable summary of modifications."""
        if not modifications:
            return f"No modifications needed (risk: {risk.risk_level.value})"

        parts = [f"{len(modifications)} modification(s) applied"]

        # Group by type
        by_type = {}
        for mod in modifications:
            by_type.setdefault(mod.modification_type, []).append(mod)

        for mod_type, mods in by_type.items():
            if mod_type == "timeout":
                parts.append(f"timeout extended")
            elif mod_type == "retry":
                parts.append(f"retries configured")
            elif mod_type == "agent":
                parts.append(f"agent reassigned")
            elif mod_type == "fallback":
                parts.append(f"fallback added")
            elif mod_type == "priority":
                parts.append(f"priority adjusted")
            elif mod_type == "context":
                parts.append(f"hints added")

        parts.append(f"(risk: {risk.risk_level.value}, {risk.score:.0%})")

        return " | ".join(parts)


async def create_task_modifier(db: Any) -> TaskModifier:
    """
    Factory function to create a TaskModifier with its dependencies.

    Args:
        db: Database connection

    Returns:
        Configured TaskModifier instance
    """
    failure_predictor = FailurePredictor(db)
    load_balancer = LoadBalancer(db)

    return TaskModifier(
        failure_predictor=failure_predictor,
        load_balancer=load_balancer,
    )
