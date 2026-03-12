"""
Reflection System for ag3ntwerk agents.

Provides both agent-level and system-level reflection:

- AgentReflector: Post-task introspection (heuristic mode + LLM mode)
- SystemReflector: Overwatch periodic assessment of the whole agent hierarchy

Heuristic mode is zero-cost and always runs. LLM mode is used for
periodic deeper introspection or after significant failures.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================
# ReflectionResult (Agent-Level)
# ============================================================


@dataclass
class ReflectionResult:
    """Result of an agent's self-reflection on a completed task."""

    id: str = field(default_factory=lambda: str(uuid4()))
    agent_code: str = ""
    task_id: Optional[str] = None
    task_type: str = ""
    success: bool = True

    what_went_well: List[str] = field(default_factory=list)
    what_went_poorly: List[str] = field(default_factory=list)
    root_cause: Optional[str] = None

    # Trait signals: maps trait name to suggested delta
    # e.g. {"risk_tolerance": -0.1, "thoroughness": 0.05}
    trait_signals: Dict[str, float] = field(default_factory=dict)

    heuristic_suggestions: List[str] = field(default_factory=list)
    confidence_in_reflection: float = 0.5
    reflection_mode: str = "heuristic"  # "heuristic" or "llm"

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_code": self.agent_code,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "success": self.success,
            "what_went_well": self.what_went_well,
            "what_went_poorly": self.what_went_poorly,
            "root_cause": self.root_cause,
            "trait_signals": self.trait_signals,
            "heuristic_suggestions": self.heuristic_suggestions,
            "confidence_in_reflection": self.confidence_in_reflection,
            "reflection_mode": self.reflection_mode,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================
# SystemReflection (System-Level)
# ============================================================


@dataclass
class SystemReflection:
    """Overwatch assessment of the overall agent hierarchy."""

    id: str = field(default_factory=lambda: str(uuid4()))
    overall_health_score: float = 1.0
    agent_performance_summary: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    collaboration_effectiveness: float = 1.0
    routing_optimality: float = 1.0
    workload_balance_score: float = 1.0
    goal_alignment_score: float = 1.0
    personality_coherence: float = 1.0

    personality_recommendations: List[str] = field(default_factory=list)
    system_recommendations: List[str] = field(default_factory=list)

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "overall_health_score": self.overall_health_score,
            "agent_performance_summary": self.agent_performance_summary,
            "collaboration_effectiveness": self.collaboration_effectiveness,
            "routing_optimality": self.routing_optimality,
            "workload_balance_score": self.workload_balance_score,
            "goal_alignment_score": self.goal_alignment_score,
            "personality_coherence": self.personality_coherence,
            "personality_recommendations": self.personality_recommendations,
            "system_recommendations": self.system_recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================
# AgentReflector
# ============================================================


class AgentReflector:
    """
    Post-task introspection for a single agent.

    Two modes:
    - Heuristic mode (always, zero cost): Algorithmic trait signal generation
    - LLM mode (periodic/significant): Structured introspection prompt
    """

    def __init__(self, agent_code: str, personality_context: Optional[str] = None):
        self._agent_code = agent_code
        self._personality_context = personality_context or ""
        self._reflection_history: List[ReflectionResult] = []
        self._avg_duration_ms: float = 0.0
        self._duration_count: int = 0
        self._consecutive_successes: int = 0
        self._consecutive_failures: int = 0

    @property
    def agent_code(self) -> str:
        return self._agent_code

    @property
    def reflection_count(self) -> int:
        return len(self._reflection_history)

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def update_personality_context(self, context: str) -> None:
        """Update the personality context used for LLM reflections."""
        self._personality_context = context

    def reflect_heuristic(
        self,
        task_id: str,
        task_type: str,
        success: bool,
        duration_ms: float = 0.0,
        confidence: Optional[float] = None,
        error: Optional[str] = None,
    ) -> ReflectionResult:
        """
        Heuristic (zero-cost) reflection based on outcome metrics.

        Compares duration to average, checks confidence delta,
        counts consecutive outcomes, and generates trait signals.
        """
        result = ReflectionResult(
            agent_code=self._agent_code,
            task_id=task_id,
            task_type=task_type,
            success=success,
            reflection_mode="heuristic",
        )

        # Update consecutive counters
        if success:
            self._consecutive_successes += 1
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1
            self._consecutive_successes = 0

        # Update running average duration
        if duration_ms > 0:
            self._duration_count += 1
            self._avg_duration_ms = (
                self._avg_duration_ms * (self._duration_count - 1) + duration_ms
            ) / self._duration_count

        # Generate trait signals based on heuristics
        trait_signals: Dict[str, float] = {}

        if success:
            result.what_went_well.append(f"Task {task_type} completed successfully")

            # Duration analysis
            if self._avg_duration_ms > 0 and duration_ms > 0:
                ratio = duration_ms / self._avg_duration_ms
                if ratio < 0.5:
                    result.what_went_well.append("Completed significantly faster than average")
                    trait_signals["adaptability"] = 0.03
                elif ratio > 2.0:
                    result.what_went_poorly.append("Took much longer than average")
                    trait_signals["thoroughness"] = 0.02  # Might be more thorough

            # Consecutive success streak
            if self._consecutive_successes >= 5:
                trait_signals["risk_tolerance"] = 0.02
                trait_signals["assertiveness"] = 0.01
                result.what_went_well.append(
                    f"On a {self._consecutive_successes}-task success streak"
                )

        else:
            result.what_went_poorly.append(f"Task {task_type} failed")
            if error:
                result.root_cause = error

            # Failure signals
            trait_signals["risk_tolerance"] = -0.05
            trait_signals["thoroughness"] = 0.03

            # Consecutive failure streak
            if self._consecutive_failures >= 3:
                trait_signals["risk_tolerance"] = -0.1
                trait_signals["collaboration"] = 0.05
                result.heuristic_suggestions.append(
                    "Consider requesting peer review or collaboration"
                )
                result.what_went_poorly.append(
                    f"On a {self._consecutive_failures}-task failure streak"
                )

        # Confidence analysis
        if confidence is not None:
            if success and confidence < 0.4:
                result.what_went_well.append(
                    "Succeeded despite low confidence — may be underestimating ability"
                )
                trait_signals["assertiveness"] = 0.03
            elif not success and confidence > 0.8:
                result.what_went_poorly.append(
                    "Failed despite high confidence — overconfidence detected"
                )
                trait_signals["risk_tolerance"] = -0.05
                trait_signals["thoroughness"] = 0.05

        result.trait_signals = trait_signals
        result.confidence_in_reflection = 0.6 if trait_signals else 0.3

        self._reflection_history.append(result)
        return result

    def _parse_structured_reflection(
        self,
        response: str,
        task_id: str,
        task_type: str,
        success: bool,
        error: Optional[str] = None,
    ) -> ReflectionResult:
        """
        Parse a structured JSON reflection from LLM output.

        Handles markdown code blocks, validates trait adjustment bounds,
        and falls back gracefully on parse failure.
        """
        result = ReflectionResult(
            agent_code=self._agent_code,
            task_id=task_id,
            task_type=task_type,
            success=success,
            reflection_mode="llm",
        )

        # Try to extract JSON from response (handle ```json ... ``` blocks)
        json_str = response
        code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", response, re.DOTALL)
        if code_block:
            json_str = code_block.group(1)

        try:
            data = json.loads(json_str)

            if isinstance(data.get("what_went_well"), list):
                result.what_went_well = data["what_went_well"][:10]
            if isinstance(data.get("what_went_poorly"), list):
                result.what_went_poorly = data["what_went_poorly"][:10]
            if isinstance(data.get("root_cause"), str):
                result.root_cause = data["root_cause"]

            # Parse trait adjustments with bounds validation
            trait_adjustments = data.get("trait_adjustments", {})
            if isinstance(trait_adjustments, dict):
                valid_traits = {
                    "risk_tolerance",
                    "creativity",
                    "thoroughness",
                    "assertiveness",
                    "collaboration",
                    "adaptability",
                }
                for trait, delta in trait_adjustments.items():
                    if trait in valid_traits and isinstance(delta, (int, float)):
                        clamped = max(-0.1, min(0.1, float(delta)))
                        result.trait_signals[trait] = clamped

            if isinstance(data.get("heuristic_suggestions"), list):
                result.heuristic_suggestions = data["heuristic_suggestions"][:5]

            confidence = data.get("confidence", 0.8)
            if isinstance(confidence, (int, float)):
                result.confidence_in_reflection = max(0.0, min(1.0, float(confidence)))

        except (json.JSONDecodeError, TypeError, KeyError):
            # Graceful fallback: store raw LLM output
            result.what_went_well = [f"LLM reflection: {response[:200]}"]
            if not success and error:
                result.root_cause = error
            result.confidence_in_reflection = 0.5

        return result

    async def reflect_llm(
        self,
        task_id: str,
        task_type: str,
        success: bool,
        task_description: str = "",
        output_summary: str = "",
        error: Optional[str] = None,
        llm_provider: Optional[Any] = None,
    ) -> ReflectionResult:
        """
        LLM-based deep reflection with structured JSON output.

        Falls back to heuristic mode if no LLM is available.
        """
        if not llm_provider:
            return self.reflect_heuristic(
                task_id=task_id,
                task_type=task_type,
                success=success,
                error=error,
            )

        prompt = f"""You are {self._agent_code}, an AI agent agent reflecting on a completed task.

{self._personality_context}

Task Type: {task_type}
Description: {task_description}
Success: {success}
{"Error: " + error if error else ""}
{"Output Summary: " + output_summary if output_summary else ""}

Reflect on this task and respond with ONLY a JSON object in this exact format:
{{
    "what_went_well": ["list", "of", "items"],
    "what_went_poorly": ["list", "of", "items"],
    "root_cause": "root cause of any issues or null",
    "trait_adjustments": {{
        "risk_tolerance": 0.0,
        "creativity": 0.0,
        "thoroughness": 0.0,
        "assertiveness": 0.0,
        "collaboration": 0.0,
        "adaptability": 0.0
    }},
    "heuristic_suggestions": ["suggestions", "for", "future", "tasks"],
    "confidence": 0.8
}}

Rules for trait_adjustments: each value must be between -0.1 and +0.1.
Positive means "increase this trait", negative means "decrease"."""

        try:
            response = await llm_provider.generate(prompt)

            result = self._parse_structured_reflection(
                response=response,
                task_id=task_id,
                task_type=task_type,
                success=success,
                error=error,
            )

            self._reflection_history.append(result)
            return result

        except Exception as e:
            logger.warning(f"LLM reflection failed, falling back to heuristic: {e}")
            return self.reflect_heuristic(
                task_id=task_id,
                task_type=task_type,
                success=success,
                error=error,
            )

    def get_recent_reflections(self, limit: int = 10) -> List[ReflectionResult]:
        """Get recent reflections."""
        return self._reflection_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "agent_code": self._agent_code,
            "total_reflections": len(self._reflection_history),
            "consecutive_successes": self._consecutive_successes,
            "consecutive_failures": self._consecutive_failures,
            "avg_duration_ms": self._avg_duration_ms,
        }


# ============================================================
# SystemReflector
# ============================================================


class SystemReflector:
    """
    System-level reflector for Overwatch.

    Periodically assesses the overall health and personality coherence
    of the agent hierarchy, producing recommendations.
    """

    def __init__(self):
        self._reflection_history: List[SystemReflection] = []

    @property
    def reflection_count(self) -> int:
        return len(self._reflection_history)

    def reflect(
        self,
        agent_health: Dict[str, Dict[str, Any]],
        agent_profiles: Optional[Dict[str, Any]] = None,
        recent_outcomes: Optional[List[Dict[str, Any]]] = None,
        drift_summary: Optional[Dict[str, Any]] = None,
        compatibility_issues: Optional[List[Dict[str, Any]]] = None,
    ) -> SystemReflection:
        """
        Produce a system-level reflection.

        Args:
            agent_health: Health metrics per agent {agent_code: {health_score, success_rate, ...}}
            agent_profiles: Optional personality profiles per agent
            recent_outcomes: Optional recent task outcomes
            drift_summary: Optional drift detection summary
        """
        reflection = SystemReflection()

        # Calculate overall health
        if agent_health:
            scores = [info.get("health_score", 1.0) for info in agent_health.values()]
            reflection.overall_health_score = sum(scores) / len(scores) if scores else 1.0

            # Build performance summary
            for code, info in agent_health.items():
                reflection.agent_performance_summary[code] = {
                    "health_score": info.get("health_score", 1.0),
                    "success_rate": info.get("success_rate", 1.0),
                    "total_tasks": info.get("total_tasks", 0),
                }

        # Workload balance
        if agent_health:
            task_counts = [info.get("total_tasks", 0) for info in agent_health.values()]
            if task_counts and max(task_counts) > 0:
                avg_tasks = sum(task_counts) / len(task_counts)
                max_deviation = max(abs(tc - avg_tasks) for tc in task_counts)
                reflection.workload_balance_score = max(
                    0.0, 1.0 - (max_deviation / max(1, max(task_counts)))
                )

        # Routing optimality from drift
        if drift_summary:
            unresolved = drift_summary.get("unresolved_count", 0)
            reflection.routing_optimality = max(0.0, 1.0 - unresolved * 0.1)

        # Personality coherence: check if profiles exist
        if agent_profiles:
            reflection.personality_coherence = 1.0
            # Check for extreme drift
            for code, profile_data in agent_profiles.items():
                if isinstance(profile_data, dict):
                    traits = profile_data.get("traits", {})
                    for trait_name, trait_info in traits.items():
                        if isinstance(trait_info, dict):
                            drift = trait_info.get("drift", 0.0)
                            if drift > 0.25:
                                reflection.personality_coherence -= 0.05
                                reflection.personality_recommendations.append(
                                    f"{code}.{trait_name} has high drift ({drift:.2f})"
                                )

            reflection.personality_coherence = max(0.0, reflection.personality_coherence)

        # Include compatibility issues in recommendations
        if compatibility_issues:
            for issue in compatibility_issues:
                desc = issue.get("description", "")
                rec = issue.get("recommendation", "")
                severity = issue.get("severity", 0.0)
                if severity > 0.5:
                    reflection.personality_recommendations.append(f"High-severity conflict: {desc}")
                    if rec:
                        reflection.system_recommendations.append(rec)
                    reflection.collaboration_effectiveness -= 0.05
            reflection.collaboration_effectiveness = max(
                0.0,
                reflection.collaboration_effectiveness,
            )

        # Generate recommendations
        if reflection.overall_health_score < 0.7:
            reflection.system_recommendations.append(
                "Overall system health is below threshold — investigate failing agents"
            )

        if reflection.workload_balance_score < 0.5:
            reflection.system_recommendations.append(
                "Significant workload imbalance detected — consider rebalancing routing rules"
            )

        if reflection.routing_optimality < 0.7:
            reflection.system_recommendations.append(
                "Routing drift detected — review routing rules and fallback routes"
            )

        self._reflection_history.append(reflection)
        return reflection

    def get_recent_reflections(self, limit: int = 5) -> List[SystemReflection]:
        """Get recent system reflections."""
        return self._reflection_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_reflections": len(self._reflection_history),
            "last_health_score": (
                self._reflection_history[-1].overall_health_score
                if self._reflection_history
                else None
            ),
        }
