"""
MetacognitionService — Central service managing personality profiles,
evolvers, reflectors, and heuristic engines for all agents.

Registered in MODULE_REGISTRY with Overwatch/Nexus as primary owners.
"""

import json
import os
import tempfile
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.personality import (
    PersonalityProfile,
    PersonalityEvolver,
    TraitEvolution,
    PERSONALITY_SEEDS,
    EVOLUTION_RATE,
    create_seeded_profile,
)
from ag3ntwerk.core.heuristics import HeuristicEngine, HeuristicAction
from ag3ntwerk.core.reflection import (
    AgentReflector,
    SystemReflector,
    ReflectionResult,
    SystemReflection,
)
from ag3ntwerk.core.personality_dynamics import (
    PersonalityDynamicsEngine,
    CompatibilityResult,
    ConflictDetection,
    TeamSuggestion,
)
from ag3ntwerk.core.logging import get_logger

logger = get_logger(__name__)

# Drift alerting thresholds
DRIFT_WARNING_THRESHOLD = 0.15
DRIFT_CRITICAL_THRESHOLD = 0.25

# Routing feedback loop
MIN_ROUTING_SAMPLES = 5
MAX_ROUTING_BONUS = 0.15
MAX_ROUTING_OUTCOMES = 1000

# Drift auto-response
DRIFT_STABILIZATION_BOOST = 50
DRIFT_NUDGE_DELTA = 0.02
MAX_DRIFT_RESPONSES = 500

# Performance attribution
MIN_ATTRIBUTION_SAMPLES = 10
MIN_ATTRIBUTION_AGENTS = 3
MIN_SUGGESTION_CORRELATION = 0.5

# Temporal trait tracking (Phase 5, Step 1)
MAX_TRAIT_SNAPSHOTS = 2000
SNAPSHOT_MIN_INTERVAL_SECONDS = 300
TREND_WINDOW_SIZE = 20
TREND_IMPROVING_THRESHOLD = 0.01
TREND_DECLINING_THRESHOLD = -0.01
TREND_OSCILLATION_REVERSALS = 4

# Personality coherence (Phase 5, Step 2)
COHERENCE_RULES = [
    ("risk_tolerance", "thoroughness", "same_high"),
    ("assertiveness", "collaboration", "same_high"),
    ("creativity", "thoroughness", "same_high"),
    ("risk_tolerance", "adaptability", "opposite"),
]
COHERENCE_TENSION_WEIGHT = 0.2
ANOMALY_VELOCITY_MULTIPLIER = 3.0
ANOMALY_LOOKBACK_SNAPSHOTS = 5

# Cross-agent learning (Phase 5, Step 3)
MIN_TOP_PERFORMER_SAMPLES = 10
TOP_PERFORMER_PERCENTILE = 0.75
MAX_PEER_RECOMMENDATIONS = 500
HEURISTIC_SHARE_MIN_SUCCESS_RATE = 0.7
HEURISTIC_SHARE_MIN_SAMPLES = 15

# Team composition learning (Phase 5, Step 4)
MAX_TEAM_OUTCOMES = 1000
MIN_TEAM_SAMPLES = 5
MIN_PAIR_SAMPLES = 3

# Closed-loop trait map optimization (Phase 5, Step 5)
MAX_LEARNED_TRAIT_MAP_ENTRIES = 50
MIN_APPLY_CONFIDENCE = 0.6
TRAIT_MAP_VALIDATION_WINDOW = 20
TRAIT_MAP_ROLLBACK_THRESHOLD = 0.1
MAX_TRAIT_MAP_UPDATES = 200


@dataclass
class DriftAlert:
    """Alert generated when personality trait drift exceeds thresholds."""

    agent_code: str
    trait_name: str
    current_value: float
    baseline_value: float
    drift: float
    severity: str  # "warning" or "critical"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "trait_name": self.trait_name,
            "current_value": round(self.current_value, 3),
            "baseline_value": round(self.baseline_value, 3),
            "drift": round(self.drift, 3),
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class DriftResponse:
    """Record of an automatic response to personality drift."""

    agent_code: str
    trait_name: str
    action: str  # "stabilization" or "nudge_back"
    old_value: float
    new_value: float
    sample_count_before: int
    sample_count_after: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "trait_name": self.trait_name,
            "action": self.action,
            "old_value": round(self.old_value, 4),
            "new_value": round(self.new_value, 4),
            "sample_count_before": self.sample_count_before,
            "sample_count_after": self.sample_count_after,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TraitAttribution:
    """Correlation between a trait value and task success rate."""

    task_type: str
    trait_name: str
    correlation: float  # -1.0 to 1.0
    sample_count: int
    suggested_value: float  # Mean trait of top-performing agents

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "trait_name": self.trait_name,
            "correlation": round(self.correlation, 4),
            "sample_count": self.sample_count,
            "suggested_value": round(self.suggested_value, 4),
        }


@dataclass
class TraitSnapshot:
    """Periodic snapshot of an agent's trait values."""

    agent_code: str
    trait_values: Dict[str, float]
    trait_baselines: Dict[str, float]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "trait_values": {k: round(v, 4) for k, v in self.trait_values.items()},
            "trait_baselines": {k: round(v, 4) for k, v in self.trait_baselines.items()},
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TraitTrend:
    """Trend classification for a single trait of an agent."""

    agent_code: str
    trait_name: str
    classification: str  # "improving", "stable", "declining", "oscillating"
    velocity: float
    direction_toward_baseline: Optional[bool]
    sample_count: int
    current_value: float
    baseline_value: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "trait_name": self.trait_name,
            "classification": self.classification,
            "velocity": round(self.velocity, 6),
            "direction_toward_baseline": self.direction_toward_baseline,
            "sample_count": self.sample_count,
            "current_value": round(self.current_value, 4),
            "baseline_value": round(self.baseline_value, 4),
        }


@dataclass
class CoherenceReport:
    """Personality coherence and health report for an agent."""

    agent_code: str
    coherence_score: float
    tensions: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    health_classification: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "coherence_score": round(self.coherence_score, 4),
            "tensions": self.tensions,
            "anomalies": self.anomalies,
            "health_classification": self.health_classification,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class PeerRecommendation:
    """Recommendation to adopt traits or heuristics from a peer agent."""

    target_agent: str
    source_agent: str
    task_type: str
    recommendation_type: str  # "trait_adjustment" or "heuristic_adoption"
    trait_name: Optional[str]
    source_value: float
    target_value: float
    suggested_value: float
    source_success_rate: float
    target_success_rate: float
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_agent": self.target_agent,
            "source_agent": self.source_agent,
            "task_type": self.task_type,
            "recommendation_type": self.recommendation_type,
            "trait_name": self.trait_name,
            "source_value": round(self.source_value, 4),
            "target_value": round(self.target_value, 4),
            "suggested_value": round(self.suggested_value, 4),
            "source_success_rate": round(self.source_success_rate, 4),
            "target_success_rate": round(self.target_success_rate, 4),
            "confidence": round(self.confidence, 4),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TeamOutcome:
    """Record of a team's performance on a task."""

    team: List[str]
    task_type: str
    success: bool
    task_id: str = ""
    compatibility_score: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "task_type": self.task_type,
            "success": self.success,
            "task_id": self.task_id,
            "compatibility_score": round(self.compatibility_score, 4),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TraitMapUpdate:
    """Record of a learned TASK_TRAIT_MAP update."""

    task_type: str
    trait_name: str
    old_value: Optional[float]
    new_value: float
    source_correlation: float
    source_sample_count: int
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validation_status: str = "pending"
    pre_apply_success_rate: Optional[float] = None
    post_apply_success_rate: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "trait_name": self.trait_name,
            "old_value": round(self.old_value, 4) if self.old_value is not None else None,
            "new_value": round(self.new_value, 4),
            "source_correlation": round(self.source_correlation, 4),
            "source_sample_count": self.source_sample_count,
            "applied_at": self.applied_at.isoformat(),
            "validation_status": self.validation_status,
            "pre_apply_success_rate": (
                round(self.pre_apply_success_rate, 4)
                if self.pre_apply_success_rate is not None
                else None
            ),
            "post_apply_success_rate": (
                round(self.post_apply_success_rate, 4)
                if self.post_apply_success_rate is not None
                else None
            ),
        }


def _pearson_correlation(x: List[float], y: List[float]) -> float:
    """Pearson r. Returns 0.0 if std of either is zero or n < 2."""
    n = len(x)
    if n < 2 or n != len(y):
        return 0.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    dx = [xi - mean_x for xi in x]
    dy = [yi - mean_y for yi in y]
    num = sum(dxi * dyi for dxi, dyi in zip(dx, dy))
    denom_x = sum(dxi * dxi for dxi in dx) ** 0.5
    denom_y = sum(dyi * dyi for dyi in dy) ** 0.5
    if denom_x < 1e-12 or denom_y < 1e-12:
        return 0.0
    return num / (denom_x * denom_y)


def _linear_slope(values: List[float]) -> float:
    """Simple least-squares slope. Returns 0.0 if < 2 values."""
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    dx = [i - mean_x for i in range(n)]
    dy = [v - mean_y for v in values]
    num = sum(dxi * dyi for dxi, dyi in zip(dx, dy))
    denom = sum(dxi * dxi for dxi in dx)
    if denom < 1e-12:
        return 0.0
    return num / denom


# Default profile storage location
_DEFAULT_PROFILE_DIR = os.path.join(
    os.environ.get("AGENTWERK_DATA_DIR", os.path.expanduser("~/.ag3ntwerk")),
    "metacognition",
)


class MetacognitionService:
    """
    Central service for metacognition: personality, reflection, heuristics.

    Manages per-agent components and provides a unified API for:
    - Registering agents with personality seeds
    - Processing task outcomes with reflection -> evolution
    - System-level reflection
    - Heuristic evaluation and tuning
    - Profile persistence
    """

    def __init__(self, profile_path: Optional[str] = None):
        self._profiles: Dict[str, PersonalityProfile] = {}
        self._evolvers: Dict[str, PersonalityEvolver] = {}
        self._reflectors: Dict[str, AgentReflector] = {}
        self._heuristic_engines: Dict[str, HeuristicEngine] = {}
        self._system_reflector = SystemReflector()
        self._task_outcomes: deque[Dict[str, Any]] = deque(maxlen=1000)
        self._routing_outcomes: deque[Dict[str, Any]] = deque(maxlen=MAX_ROUTING_OUTCOMES)
        self._drift_responses: deque[DriftResponse] = deque(maxlen=MAX_DRIFT_RESPONSES)
        self._reflection_count = 0
        self._system_reflection_count = 0

        # Temporal trait tracking (Phase 5)
        self._trait_snapshots: deque[TraitSnapshot] = deque(maxlen=MAX_TRAIT_SNAPSHOTS)
        # Cross-agent learning (Phase 5)
        self._peer_recommendations: deque[PeerRecommendation] = deque(
            maxlen=MAX_PEER_RECOMMENDATIONS
        )
        # Team composition learning (Phase 5)
        self._team_outcomes: deque[TeamOutcome] = deque(maxlen=MAX_TEAM_OUTCOMES)
        # Closed-loop trait map (Phase 5)
        self._learned_trait_map: Dict[str, Dict[str, float]] = {}
        self._trait_map_updates: deque[TraitMapUpdate] = deque(maxlen=MAX_TRAIT_MAP_UPDATES)

        # Personality dynamics
        self._dynamics_engine = PersonalityDynamicsEngine()

        # Auto-persistence
        self._profile_path = profile_path or os.path.join(_DEFAULT_PROFILE_DIR, "profiles.json")
        self._phase5_state_path = os.path.join(
            os.path.dirname(self._profile_path), "phase5_state.json"
        )
        self._auto_save = True

        # Concurrency lock for shared mutable state
        self._lock = threading.Lock()

    # ==================== Registration ====================

    def register_agent(
        self,
        agent_code: str,
        seed_traits: Optional[Dict[str, Any]] = None,
    ) -> PersonalityProfile:
        """
        Register an agent with the metacognition service.

        Creates profile, evolver, reflector, and heuristic engine.

        Args:
            agent_code: The agent's code (e.g., "Forge")
            seed_traits: Optional override for seed traits

        Returns:
            The created PersonalityProfile
        """
        # Create profile from seeds or provided traits
        if seed_traits:
            from ag3ntwerk.core.personality import _make_profile

            profile = _make_profile(agent_code, **seed_traits)
        else:
            profile = create_seeded_profile(agent_code)

        self._profiles[agent_code] = profile
        self._evolvers[agent_code] = PersonalityEvolver(profile)
        self._reflectors[agent_code] = AgentReflector(
            agent_code,
            personality_context=profile.to_system_prompt_fragment(),
        )
        self._heuristic_engines[agent_code] = HeuristicEngine(agent_code)

        logger.debug(
            "Registered agent with metacognition service",
            agent=agent_code,
            component="metacognition",
        )
        return profile

    @property
    def trait_map_updates(self) -> List["TraitMapUpdate"]:
        return list(self._trait_map_updates)

    @property
    def trait_snapshots(self) -> List["TraitSnapshot"]:
        return list(self._trait_snapshots)

    @property
    def team_outcomes(self) -> List["TeamOutcome"]:
        return list(self._team_outcomes)

    @property
    def learned_trait_map(self) -> Dict[str, Dict[str, float]]:
        return dict(self._learned_trait_map)

    @property
    def peer_recommendations(self) -> List["PeerRecommendation"]:
        return list(self._peer_recommendations)

    @property
    def task_outcomes_count(self) -> int:
        return len(self._task_outcomes)

    def get_heuristic_engine(self, agent_code: str) -> Optional["HeuristicEngine"]:
        return self._heuristic_engines.get(agent_code)

    def get_reflector(self, agent_code: str) -> Optional["AgentReflector"]:
        return self._reflectors.get(agent_code)

    def is_registered(self, agent_code: str) -> bool:
        """Check if an agent is registered."""
        return agent_code in self._profiles

    # ==================== Shared Helpers ====================

    def _process_reflection_outcome(
        self,
        agent_code: str,
        reflector: "AgentReflector",
        reflection: "ReflectionResult",
        task_id: str,
        task_type: str,
        success: bool,
        duration_ms: float,
    ) -> None:
        """Shared evolve + record logic for both sync and async task completion."""
        self._reflection_count += 1

        # Evolve personality based on reflection signals
        evolver = self._evolvers.get(agent_code)
        if evolver and reflection.trait_signals:
            evolver.process_reflection(
                trait_signals=reflection.trait_signals,
                reason=f"reflection on {task_type}",
                task_id=task_id,
            )
            reflector.update_personality_context(evolver.profile.to_system_prompt_fragment())

        # Record outcome for system reflection (deque maxlen=1000 handles eviction)
        self._task_outcomes.append(
            {
                "agent_code": agent_code,
                "task_id": task_id,
                "task_type": task_type,
                "success": success,
                "duration_ms": duration_ms,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    # ==================== Task Completion ====================

    def on_task_completed(
        self,
        agent_code: str,
        task_id: str,
        task_type: str,
        success: bool,
        duration_ms: float = 0.0,
        confidence: Optional[float] = None,
        error: Optional[str] = None,
    ) -> Optional[ReflectionResult]:
        """
        Process a completed task: reflect -> evolve -> record.

        Args:
            agent_code: The agent that handled the task
            task_id: Task identifier
            task_type: Type of task
            success: Whether it succeeded
            duration_ms: Execution time
            confidence: Pre-task confidence
            error: Error message if failed

        Returns:
            ReflectionResult, or None if agent not registered
        """
        if agent_code not in self._reflectors:
            return None

        # Reflect (heuristic mode — zero cost)
        reflector = self._reflectors[agent_code]
        reflection = reflector.reflect_heuristic(
            task_id=task_id,
            task_type=task_type,
            success=success,
            duration_ms=duration_ms,
            confidence=confidence,
            error=error,
        )

        # Evolve + record
        self._process_reflection_outcome(
            agent_code,
            reflector,
            reflection,
            task_id,
            task_type,
            success,
            duration_ms,
        )

        return reflection

    # ==================== Async Task Completion ====================

    # Periodic LLM reflection constants
    LLM_REFLECTION_INTERVAL = 10
    LLM_REFLECTION_ON_FAILURE_STREAK = 3

    async def on_task_completed_async(
        self,
        agent_code: str,
        task_id: str,
        task_type: str,
        success: bool,
        duration_ms: float = 0.0,
        confidence: Optional[float] = None,
        error: Optional[str] = None,
        llm_provider: Optional[Any] = None,
        task_description: str = "",
        output_summary: str = "",
    ) -> Optional[ReflectionResult]:
        """
        Async version of on_task_completed that periodically triggers LLM reflection.

        LLM reflection triggers:
        - Every LLM_REFLECTION_INTERVAL tasks
        - On LLM_REFLECTION_ON_FAILURE_STREAK consecutive failures
        """
        if agent_code not in self._reflectors:
            return None

        reflector = self._reflectors[agent_code]

        # Determine if LLM reflection should be triggered
        use_llm = False
        if llm_provider:
            total = reflector.reflection_count + 1
            if total % self.LLM_REFLECTION_INTERVAL == 0:
                use_llm = True
            if (
                reflector.consecutive_failures >= (self.LLM_REFLECTION_ON_FAILURE_STREAK - 1)
                and not success
            ):
                use_llm = True

        # Reflect (LLM or heuristic)
        if use_llm:
            reflection = await reflector.reflect_llm(
                task_id=task_id,
                task_type=task_type,
                success=success,
                task_description=task_description,
                output_summary=output_summary,
                error=error,
                llm_provider=llm_provider,
            )
        else:
            reflection = reflector.reflect_heuristic(
                task_id=task_id,
                task_type=task_type,
                success=success,
                duration_ms=duration_ms,
                confidence=confidence,
                error=error,
            )

        # Evolve + record
        self._process_reflection_outcome(
            agent_code,
            reflector,
            reflection,
            task_id,
            task_type,
            success,
            duration_ms,
        )

        return reflection

    # ==================== System Reflection ====================

    def system_reflect(
        self,
        agent_health: Optional[Dict[str, Dict[str, Any]]] = None,
        drift_summary: Optional[Dict[str, Any]] = None,
        compatibility_issues: Optional[List[Dict[str, Any]]] = None,
    ) -> SystemReflection:
        """
        Run system-level reflection.

        Args:
            agent_health: Per-agent health metrics
            drift_summary: Drift detection summary
            compatibility_issues: Detected compatibility/conflict issues

        Returns:
            SystemReflection with recommendations
        """
        # Build profile data for coherence check
        agent_profiles = {}
        for code, evolver in self._evolvers.items():
            agent_profiles[code] = evolver.get_stats()

        reflection = self._system_reflector.reflect(
            agent_health=agent_health or {},
            agent_profiles=agent_profiles,
            recent_outcomes=list(self._task_outcomes)[-100:],
            drift_summary=drift_summary,
            compatibility_issues=compatibility_issues,
        )

        self._system_reflection_count += 1
        return reflection

    # ==================== Personality Access ====================

    def get_personality_prompt(self, agent_code: str) -> str:
        """Get the personality system prompt fragment for an agent."""
        profile = self._profiles.get(agent_code)
        if not profile:
            return ""
        return profile.to_system_prompt_fragment()

    def get_profile(self, agent_code: str) -> Optional[PersonalityProfile]:
        """Get an agent's personality profile."""
        return self._profiles.get(agent_code)

    def get_all_profiles(self) -> Dict[str, PersonalityProfile]:
        """Get all personality profiles."""
        return dict(self._profiles)

    # ==================== Heuristic Access ====================

    def get_heuristic_actions(
        self,
        agent_code: str,
        task: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[HeuristicAction]:
        """Evaluate heuristics for an agent and return recommended actions."""
        engine = self._heuristic_engines.get(agent_code)
        if not engine:
            return []
        return engine.evaluate(task=task, context=context)

    def record_heuristic_outcome(
        self,
        agent_code: str,
        heuristic_id: str,
        success: bool,
    ) -> None:
        """Record outcome for a heuristic action."""
        engine = self._heuristic_engines.get(agent_code)
        if engine:
            engine.record_outcome(heuristic_id, success)

    def tune_heuristics(self, agent_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Tune heuristics for one or all agents."""
        results = []
        engines = (
            {agent_code: self._heuristic_engines[agent_code]}
            if agent_code and agent_code in self._heuristic_engines
            else self._heuristic_engines
        )
        for code, engine in engines.items():
            tunings = engine.tune()
            for t in tunings:
                t["agent_code"] = code
            results.extend(tunings)
        return results

    # ==================== Persistence ====================

    def _atomic_write_json(self, path: str, data: dict) -> None:
        """Write JSON atomically: write to temp file then replace."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp_path, str(target))
        except PermissionError:
            # Windows: target may be locked; fall back to direct write
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            with open(str(target), "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:  # Intentional catch-all: clean up temp file before re-raising
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def save_profiles(self, path: str) -> None:
        """Save all profiles to a JSON file (atomic write)."""
        data = {
            "schema_version": 1,
            "profiles": {code: profile.to_dict() for code, profile in self._profiles.items()},
        }
        self._atomic_write_json(path, data)
        logger.info(
            "Saved profiles",
            component="metacognition",
            profile_count=len(self._profiles),
            path=path,
        )

    def load_profiles(self, path: str) -> int:
        """
        Load profiles from a JSON file.

        Returns number of profiles loaded.
        """
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.info(
                "No profile file found, starting fresh", component="metacognition", path=path
            )
            return 0
        except json.JSONDecodeError as e:
            logger.warning(
                "Invalid JSON in profile file", component="metacognition", path=path, error=str(e)
            )
            return 0

        # Handle versioned and unversioned formats
        schema_version = data.get("schema_version")
        if schema_version is not None:
            if schema_version != 1:
                logger.warning(
                    "Unexpected schema_version in profile file",
                    component="metacognition",
                    schema_version=schema_version,
                    path=path,
                )
            data = data.get("profiles", {})

        count = 0
        for code, profile_data in data.items():
            try:
                profile = PersonalityProfile.from_dict(profile_data)
                self._profiles[code] = profile
                self._evolvers[code] = PersonalityEvolver(profile)
                if code not in self._reflectors:
                    self._reflectors[code] = AgentReflector(
                        code,
                        personality_context=profile.to_system_prompt_fragment(),
                    )
                if code not in self._heuristic_engines:
                    self._heuristic_engines[code] = HeuristicEngine(code)
                count += 1
            except (KeyError, ValueError, TypeError, AttributeError) as e:
                logger.warning(
                    "Failed to load profile", component="metacognition", agent=code, error=str(e)
                )

        logger.info("Loaded profiles", component="metacognition", profile_count=count, path=path)
        return count

    def save_phase5_state(self, path: Optional[str] = None) -> None:
        """Save Phase 5 state (snapshots, team outcomes, learned map, etc.) to JSON (atomic write)."""
        with self._lock:
            path = path or self._phase5_state_path
            data = {
                "schema_version": 1,
                "trait_snapshots": [s.to_dict() for s in self._trait_snapshots],
                "team_outcomes": [t.to_dict() for t in self._team_outcomes],
                "learned_trait_map": self._learned_trait_map,
                "trait_map_updates": [u.to_dict() for u in self._trait_map_updates],
                "peer_recommendations": [
                    r.to_dict() for r in list(self._peer_recommendations)[-100:]
                ],
            }
            self._atomic_write_json(path, data)
            logger.info("Saved Phase 5 state", component="metacognition", path=path)

    def load_phase5_state(self, path: Optional[str] = None) -> Dict[str, int]:
        """
        Load Phase 5 state from JSON.

        Returns counts of loaded items.
        """
        path = path or self._phase5_state_path
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.info(
                "No Phase 5 state file found, starting fresh", component="metacognition", path=path
            )
            return {
                "snapshots": 0,
                "team_outcomes": 0,
                "learned_map_entries": 0,
                "trait_map_updates": 0,
                "peer_recommendations": 0,
            }
        except json.JSONDecodeError as e:
            logger.warning(
                "Invalid JSON in Phase 5 state file",
                component="metacognition",
                path=path,
                error=str(e),
            )
            return {
                "snapshots": 0,
                "team_outcomes": 0,
                "learned_map_entries": 0,
                "trait_map_updates": 0,
                "peer_recommendations": 0,
            }

        # Check schema version
        schema_version = data.get("schema_version")
        if schema_version is not None and schema_version != 1:
            logger.warning(
                "Unexpected schema_version in Phase 5 state file",
                component="metacognition",
                schema_version=schema_version,
                path=path,
            )

        with self._lock:
            counts = {
                "snapshots": 0,
                "team_outcomes": 0,
                "learned_map_entries": 0,
                "trait_map_updates": 0,
                "peer_recommendations": 0,
            }

            # Trait snapshots
            for s in data.get("trait_snapshots", []):
                try:
                    ts = (
                        datetime.fromisoformat(s["timestamp"])
                        if isinstance(s.get("timestamp"), str)
                        else datetime.now(timezone.utc)
                    )
                    self._trait_snapshots.append(
                        TraitSnapshot(
                            agent_code=s["agent_code"],
                            trait_values=s["trait_values"],
                            trait_baselines=s["trait_baselines"],
                            timestamp=ts,
                        )
                    )
                    counts["snapshots"] += 1
                except (KeyError, ValueError) as e:
                    logger.warning(
                        "Skipping invalid snapshot", component="metacognition", error=str(e)
                    )

            # Team outcomes
            for t in data.get("team_outcomes", []):
                try:
                    self._team_outcomes.append(
                        TeamOutcome(
                            team=t["team"],
                            task_type=t["task_type"],
                            success=t["success"],
                            task_id=t.get("task_id", ""),
                            compatibility_score=t.get("compatibility_score"),
                        )
                    )
                    counts["team_outcomes"] += 1
                except (KeyError, ValueError) as e:
                    logger.warning(
                        "Skipping invalid team outcome", component="metacognition", error=str(e)
                    )

            # Learned trait map
            learned = data.get("learned_trait_map", {})
            if isinstance(learned, dict):
                for task_type, traits in learned.items():
                    if isinstance(traits, dict):
                        self._learned_trait_map[task_type] = {
                            k: float(v) for k, v in traits.items() if isinstance(v, (int, float))
                        }
                        counts["learned_map_entries"] += len(self._learned_trait_map[task_type])

            # Cap learned map entries
            total_entries = sum(len(v) for v in self._learned_trait_map.values())
            if total_entries > MAX_LEARNED_TRAIT_MAP_ENTRIES:
                # Trim oldest task types until under cap
                while (
                    sum(len(v) for v in self._learned_trait_map.values())
                    > MAX_LEARNED_TRAIT_MAP_ENTRIES
                ):
                    first_key = next(iter(self._learned_trait_map))
                    del self._learned_trait_map[first_key]

            # Trait map updates
            for u in data.get("trait_map_updates", []):
                try:
                    applied_at = None
                    if u.get("applied_at") and isinstance(u["applied_at"], str):
                        try:
                            applied_at = datetime.fromisoformat(u["applied_at"])
                        except ValueError:
                            pass
                    self._trait_map_updates.append(
                        TraitMapUpdate(
                            task_type=u["task_type"],
                            trait_name=u["trait_name"],
                            old_value=u.get("old_value"),
                            new_value=u["new_value"],
                            source_correlation=u.get("source_correlation", 0.0),
                            source_sample_count=u.get("source_sample_count", 0),
                            validation_status=u.get("validation_status", "pending"),
                            applied_at=applied_at,
                            pre_apply_success_rate=u.get("pre_apply_success_rate"),
                        )
                    )
                    counts["trait_map_updates"] += 1
                except (KeyError, ValueError) as e:
                    logger.warning(
                        "Skipping invalid trait map update", component="metacognition", error=str(e)
                    )

            # Peer recommendations
            for r in data.get("peer_recommendations", []):
                try:
                    self._peer_recommendations.append(
                        PeerRecommendation(
                            target_agent=r["target_agent"],
                            source_agent=r["source_agent"],
                            task_type=r["task_type"],
                            recommendation_type=r["recommendation_type"],
                            trait_name=r.get("trait_name"),
                            source_value=r.get("source_value"),
                            target_value=r.get("target_value"),
                            suggested_value=r.get("suggested_value"),
                            source_success_rate=r.get("source_success_rate", 0.0),
                            target_success_rate=r.get("target_success_rate", 0.0),
                            confidence=r.get("confidence", 0.0),
                        )
                    )
                    counts["peer_recommendations"] += 1
                except (KeyError, ValueError) as e:
                    logger.warning(
                        "Skipping invalid peer recommendation",
                        component="metacognition",
                        error=str(e),
                    )

            logger.info(
                "Loaded Phase 5 state",
                component="metacognition",
                path=path,
                snapshots=counts["snapshots"],
                team_outcomes=counts["team_outcomes"],
                learned_map_entries=counts["learned_map_entries"],
            )
            return counts

    # ==================== Personality Dynamics ====================

    def get_compatibility(
        self,
        agent_a: str,
        agent_b: str,
    ) -> Optional[CompatibilityResult]:
        """Get compatibility between two agents."""
        profile_a = self._profiles.get(agent_a)
        profile_b = self._profiles.get(agent_b)
        if not profile_a or not profile_b:
            return None
        return self._dynamics_engine.compute_compatibility(profile_a, profile_b)

    def detect_team_conflicts(
        self,
        agent_codes: Optional[List[str]] = None,
    ) -> List[ConflictDetection]:
        """Detect conflicts among working agents."""
        return self._dynamics_engine.detect_conflicts(
            self._profiles,
            working_together=agent_codes,
        )

    def suggest_team_for_task(
        self,
        task_traits: Dict[str, float],
        team_size: int = 3,
    ) -> TeamSuggestion:
        """Suggest a team for a given task based on personality fit."""
        return self._dynamics_engine.suggest_team(
            self._profiles,
            task_traits,
            team_size,
        )

    def get_compatibility_matrix(self) -> Dict[str, Dict[str, float]]:
        """Get full compatibility matrix for all registered agents."""
        return self._dynamics_engine.get_compatibility_matrix(self._profiles)

    # ==================== Personality Scoring ====================

    def score_agents_for_task(
        self,
        task_traits: Dict[str, float],
        agent_codes: List[str],
        task_type: Optional[str] = None,
    ) -> List[tuple]:
        """
        Score agents for a task based on personality fit + routing bonus.

        Args:
            task_traits: Desired trait values for the task
            agent_codes: List of candidate agent codes
            task_type: Optional task type for routing feedback bonus

        Returns:
            List of (agent_code, score) tuples sorted by score descending
        """
        scores = []
        for code in agent_codes:
            profile = self._profiles.get(code)
            if profile:
                personality_fit = profile.compute_task_fit(task_traits)
                routing_bonus = self.compute_routing_bonus(code, task_type) if task_type else 0.0
                scores.append((code, personality_fit + routing_bonus))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    # ==================== Routing Feedback ====================

    def record_routing_outcome(
        self,
        agent_code: str,
        task_type: str,
        personality_score: float,
        success: bool,
    ) -> None:
        """Record the outcome of a personality-aware routing decision."""
        self._routing_outcomes.append(
            {
                "agent_code": agent_code,
                "task_type": task_type,
                "personality_score": personality_score,
                "success": success,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def compute_routing_bonus(self, agent_code: str, task_type: str) -> float:
        """
        Compute a routing bonus in [-MAX_ROUTING_BONUS, +MAX_ROUTING_BONUS]
        based on historical success rate for this agent+task_type pair.

        Returns 0.0 if fewer than MIN_ROUTING_SAMPLES samples.
        """
        relevant = [
            o
            for o in self._routing_outcomes
            if o["agent_code"] == agent_code and o["task_type"] == task_type
        ]
        if len(relevant) < MIN_ROUTING_SAMPLES:
            return 0.0
        rate = sum(1 for o in relevant if o["success"]) / len(relevant)
        return (rate - 0.5) * 2 * MAX_ROUTING_BONUS

    def get_routing_stats(self) -> Dict[str, Any]:
        """Return per-agent per-task-type success rates and routing bonuses."""
        pairs: Dict[str, Dict[str, List[bool]]] = {}
        for o in self._routing_outcomes:
            agent = o["agent_code"]
            ttype = o["task_type"]
            pairs.setdefault(agent, {}).setdefault(ttype, []).append(o["success"])

        stats: Dict[str, Any] = {}
        for agent, types in pairs.items():
            agent_stats: Dict[str, Any] = {}
            for ttype, outcomes in types.items():
                n = len(outcomes)
                rate = sum(outcomes) / n if n else 0.0
                agent_stats[ttype] = {
                    "samples": n,
                    "success_rate": round(rate, 3),
                    "routing_bonus": round(self.compute_routing_bonus(agent, ttype), 4),
                }
            stats[agent] = agent_stats

        return {
            "total_routing_outcomes": len(self._routing_outcomes),
            "agents": stats,
        }

    # ==================== Auto-Persistence ====================

    def load_on_startup(self) -> int:
        """
        Load profiles and Phase 5 state from the default paths on startup.

        Returns number of profiles loaded.
        """
        count = self.load_profiles(self._profile_path)
        self.load_phase5_state(self._phase5_state_path)
        return count

    def save_if_auto(self) -> None:
        """Save profiles and Phase 5 state if auto_save is enabled."""
        if not self._auto_save:
            return
        try:
            self.save_profiles(self._profile_path)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(
                "Auto-save failed",
                component="metacognition",
                error=str(e),
                error_type=type(e).__name__,
            )
        try:
            self.save_phase5_state(self._phase5_state_path)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(
                "Phase 5 state auto-save failed",
                component="metacognition",
                error=str(e),
                error_type=type(e).__name__,
            )

    # ==================== Stats ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive metacognition statistics."""
        return {
            "registered_agents": list(self._profiles.keys()),
            "total_reflections": self._reflection_count,
            "system_reflections": self._system_reflection_count,
            "total_outcomes_tracked": len(self._task_outcomes),
            "total_routing_outcomes": len(self._routing_outcomes),
            "total_drift_responses": len(self._drift_responses),
            "total_trait_snapshots": len(self._trait_snapshots),
            "total_peer_recommendations": len(self._peer_recommendations),
            "total_team_outcomes": len(self._team_outcomes),
            "learned_trait_map_entries": sum(len(v) for v in self._learned_trait_map.values()),
            "trait_map_updates": len(self._trait_map_updates),
            "agent_health": {code: self.classify_agent_health(code) for code in self._profiles},
            "profiles": {
                code: {
                    "version": profile.version,
                    "decision_style": profile.decision_style,
                    "communication_style": profile.communication_style,
                    "traits": {
                        name: {
                            "value": round(trait.value, 3),
                            "baseline": round(trait.baseline, 3),
                            "drift": round(abs(trait.value - trait.baseline), 3),
                        }
                        for name, trait in profile.get_all_traits().items()
                    },
                }
                for code, profile in self._profiles.items()
            },
            "heuristics": {
                code: engine.get_stats() for code, engine in self._heuristic_engines.items()
            },
        }

    # ==================== Drift Alerting ====================

    def check_drift_alerts(
        self,
        agent_code: Optional[str] = None,
    ) -> List[DriftAlert]:
        """
        Scan profiles for personality drift exceeding thresholds.

        Args:
            agent_code: Optional agent code to check (None = all agents)

        Returns:
            List of DriftAlert objects sorted by drift descending
        """
        alerts: List[DriftAlert] = []
        profiles = (
            {agent_code: self._profiles[agent_code]}
            if agent_code and agent_code in self._profiles
            else self._profiles
        )

        for code, profile in profiles.items():
            for trait_name, trait in profile.get_all_traits().items():
                drift = abs(trait.value - trait.baseline)
                if drift >= DRIFT_CRITICAL_THRESHOLD:
                    alerts.append(
                        DriftAlert(
                            agent_code=code,
                            trait_name=trait_name,
                            current_value=trait.value,
                            baseline_value=trait.baseline,
                            drift=drift,
                            severity="critical",
                        )
                    )
                elif drift >= DRIFT_WARNING_THRESHOLD:
                    alerts.append(
                        DriftAlert(
                            agent_code=code,
                            trait_name=trait_name,
                            current_value=trait.value,
                            baseline_value=trait.baseline,
                            drift=drift,
                            severity="warning",
                        )
                    )

        alerts.sort(key=lambda a: a.drift, reverse=True)
        return alerts

    def get_drift_summary(self) -> Dict[str, Any]:
        """
        Get a summary of drift alerts across all agents.

        Returns:
            Dict with total, critical, warning counts and alert list
        """
        alerts = self.check_drift_alerts()
        critical = [a for a in alerts if a.severity == "critical"]
        warning = [a for a in alerts if a.severity == "warning"]
        return {
            "total_alerts": len(alerts),
            "critical_count": len(critical),
            "warning_count": len(warning),
            "alerts": [a.to_dict() for a in alerts],
        }

    # ==================== Drift Auto-Response ====================

    def respond_to_drift(
        self,
        agent_code: Optional[str] = None,
    ) -> List[DriftResponse]:
        """
        Automatically respond to critical personality drift.

        For each critical drift alert:
        - Stabilization: boost sample_count to increase resistance
        - Nudge-back: small evolve() step toward baseline

        Args:
            agent_code: Optional agent code (None = all agents)

        Returns:
            List of DriftResponse records for actions taken
        """
        alerts = self.check_drift_alerts(agent_code)
        critical_alerts = [a for a in alerts if a.severity == "critical"]

        responses: List[DriftResponse] = []
        for alert in critical_alerts:
            profile = self._profiles.get(alert.agent_code)
            if not profile:
                continue
            trait = profile.get_all_traits().get(alert.trait_name)
            if not trait:
                continue

            # Stabilization: boost sample_count
            old_sample_count = trait.sample_count
            trait.sample_count += DRIFT_STABILIZATION_BOOST
            responses.append(
                DriftResponse(
                    agent_code=alert.agent_code,
                    trait_name=alert.trait_name,
                    action="stabilization",
                    old_value=trait.value,
                    new_value=trait.value,
                    sample_count_before=old_sample_count,
                    sample_count_after=trait.sample_count,
                )
            )

            # Nudge-back: small step toward baseline
            old_value = trait.value
            direction = 1.0 if trait.baseline > trait.value else -1.0
            nudge = direction * DRIFT_NUDGE_DELTA
            trait.evolve(nudge, weight=1.0)
            responses.append(
                DriftResponse(
                    agent_code=alert.agent_code,
                    trait_name=alert.trait_name,
                    action="nudge_back",
                    old_value=old_value,
                    new_value=trait.value,
                    sample_count_before=trait.sample_count - 1,  # evolve increments
                    sample_count_after=trait.sample_count,
                )
            )

        self._drift_responses.extend(responses)

        return responses

    def get_drift_responses(
        self,
        agent_code: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get history of drift auto-responses, most recent first.

        Args:
            agent_code: Optional filter by agent
            limit: Max results to return

        Returns:
            List of DriftResponse dicts
        """
        filtered = self._drift_responses
        if agent_code:
            filtered = [r for r in filtered if r.agent_code == agent_code]
        return [r.to_dict() for r in reversed(filtered)][:limit]

    # ==================== Performance Attribution ====================

    def compute_attribution(
        self,
        task_type: Optional[str] = None,
        min_samples: int = MIN_ATTRIBUTION_SAMPLES,
    ) -> List[TraitAttribution]:
        """
        Correlate agent trait values with task success rates.

        Groups task outcomes by (agent_code, task_type), computes
        per-agent success rates, then Pearson r for each trait.

        Args:
            task_type: Optional filter to a single task type
            min_samples: Minimum outcomes per agent for inclusion

        Returns:
            List of TraitAttribution sorted by abs(correlation) descending
        """
        # Group outcomes by (agent, task_type)
        buckets: Dict[str, Dict[str, List[bool]]] = {}
        for o in self._task_outcomes:
            tt = o["task_type"]
            if task_type and tt != task_type:
                continue
            agent = o["agent_code"]
            buckets.setdefault(tt, {}).setdefault(agent, []).append(o["success"])

        attributions: List[TraitAttribution] = []

        for tt, agents_outcomes in buckets.items():
            # Filter agents with enough samples
            qualified = {
                agent: outcomes
                for agent, outcomes in agents_outcomes.items()
                if len(outcomes) >= min_samples and agent in self._profiles
            }
            if len(qualified) < MIN_ATTRIBUTION_AGENTS:
                continue

            # Per-agent success rate
            agent_rates = {
                agent: sum(outcomes) / len(outcomes) for agent, outcomes in qualified.items()
            }

            # Get trait names from first profile
            first_profile = self._profiles[next(iter(qualified))]
            trait_names = list(first_profile.get_all_traits().keys())

            rates_list = [agent_rates[a] for a in qualified]
            median_rate = sorted(rates_list)[len(rates_list) // 2]

            for trait_name in trait_names:
                trait_values = []
                success_rates = []
                top_values = []

                for agent in qualified:
                    profile = self._profiles.get(agent)
                    if not profile:
                        continue
                    traits = profile.get_all_traits()
                    trait = traits.get(trait_name)
                    if trait is None:
                        continue
                    trait_values.append(trait.value)
                    success_rates.append(agent_rates[agent])
                    if agent_rates[agent] >= median_rate:
                        top_values.append(trait.value)

                if len(trait_values) < MIN_ATTRIBUTION_AGENTS:
                    continue

                corr = _pearson_correlation(trait_values, success_rates)
                suggested = sum(top_values) / len(top_values) if top_values else 0.5

                attributions.append(
                    TraitAttribution(
                        task_type=tt,
                        trait_name=trait_name,
                        correlation=corr,
                        sample_count=sum(len(v) for v in qualified.values()),
                        suggested_value=suggested,
                    )
                )

        attributions.sort(key=lambda a: abs(a.correlation), reverse=True)
        return attributions

    def suggest_trait_map_updates(
        self,
        min_correlation: float = MIN_SUGGESTION_CORRELATION,
        min_samples: int = MIN_ATTRIBUTION_SAMPLES,
    ) -> Dict[str, Dict[str, float]]:
        """
        Suggest TASK_TRAIT_MAP updates based on attribution analysis.

        Filters attributions by min_correlation and returns suggested
        trait values per task type.

        Returns:
            {task_type: {trait_name: suggested_value}}
        """
        attributions = self.compute_attribution(min_samples=min_samples)
        suggestions: Dict[str, Dict[str, float]] = {}
        for a in attributions:
            if abs(a.correlation) >= min_correlation:
                suggestions.setdefault(a.task_type, {})[a.trait_name] = a.suggested_value
        return suggestions

    # ==================== Temporal Trait Tracking (Phase 5) ====================

    def record_trait_snapshot(
        self,
        agent_code: Optional[str] = None,
    ) -> List[TraitSnapshot]:
        """
        Snapshot current trait values for all (or one) registered agents.

        Skips agents snapshotted within SNAPSHOT_MIN_INTERVAL_SECONDS.
        Caps stored snapshots at MAX_TRAIT_SNAPSHOTS.
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            targets = (
                {agent_code: self._profiles[agent_code]}
                if agent_code and agent_code in self._profiles
                else self._profiles
            )

            new_snapshots: List[TraitSnapshot] = []
            for code, profile in targets.items():
                # Check interval
                last = None
                for s in reversed(self._trait_snapshots):
                    if s.agent_code == code:
                        last = s
                        break
                if last:
                    elapsed = (now - last.timestamp).total_seconds()
                    if elapsed < SNAPSHOT_MIN_INTERVAL_SECONDS:
                        continue

                traits = profile.get_all_traits()
                snapshot = TraitSnapshot(
                    agent_code=code,
                    trait_values={n: t.value for n, t in traits.items()},
                    trait_baselines={n: t.baseline for n, t in traits.items()},
                    timestamp=now,
                )
                self._trait_snapshots.append(snapshot)
                new_snapshots.append(snapshot)

            return new_snapshots

    def get_trait_history(
        self,
        agent_code: str,
        trait_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Return most recent snapshots for an agent, newest first.

        If trait_name given, extract just that trait's value series.
        """
        agent_snaps = [s for s in self._trait_snapshots if s.agent_code == agent_code]
        recent = list(reversed(agent_snaps))[:limit]

        if trait_name:
            return [
                {
                    "value": s.trait_values.get(trait_name),
                    "baseline": s.trait_baselines.get(trait_name),
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in recent
                if trait_name in s.trait_values
            ]
        return [s.to_dict() for s in recent]

    def classify_trait_trend(
        self,
        agent_code: str,
        trait_name: str,
    ) -> Optional[TraitTrend]:
        """
        Classify a trait's evolution trend using recent snapshots.

        Returns None if < 3 snapshots available.
        """
        agent_snaps = [s for s in self._trait_snapshots if s.agent_code == agent_code]
        # Use last TREND_WINDOW_SIZE snapshots that contain this trait
        relevant = [s for s in agent_snaps if trait_name in s.trait_values]
        window = relevant[-TREND_WINDOW_SIZE:]

        if len(window) < 3:
            return None

        values = [s.trait_values[trait_name] for s in window]
        velocity = _linear_slope(values)

        # Count direction reversals
        reversals = 0
        for i in range(2, len(values)):
            d1 = values[i - 1] - values[i - 2]
            d2 = values[i] - values[i - 1]
            if d1 * d2 < 0:
                reversals += 1

        # Classification
        if reversals >= TREND_OSCILLATION_REVERSALS:
            classification = "oscillating"
        elif velocity >= TREND_IMPROVING_THRESHOLD:
            classification = "improving"
        elif velocity <= TREND_DECLINING_THRESHOLD:
            classification = "declining"
        else:
            classification = "stable"

        # Direction toward baseline
        baseline = window[-1].trait_baselines.get(trait_name)
        direction_toward_baseline = None
        if baseline is not None and len(window) > 0:
            current = values[-1]
            first_in_window = values[0]
            direction_toward_baseline = (baseline - current) * (baseline - first_in_window) > 0

        return TraitTrend(
            agent_code=agent_code,
            trait_name=trait_name,
            classification=classification,
            velocity=velocity,
            direction_toward_baseline=direction_toward_baseline,
            sample_count=len(window),
            current_value=values[-1],
            baseline_value=baseline if baseline is not None else 0.0,
        )

    def get_trend_summary(
        self,
        agent_code: Optional[str] = None,
    ) -> Dict:
        """
        Classify all traits for each agent.

        Returns {"agents": {code: {"traits": {name: trend_dict}}}, "total_snapshots": N}
        """
        targets = (
            {agent_code: self._profiles[agent_code]}
            if agent_code and agent_code in self._profiles
            else self._profiles
        )

        agents_data: Dict[str, Dict] = {}
        for code, profile in targets.items():
            trait_names = list(profile.get_all_traits().keys())
            traits_data: Dict[str, Any] = {}
            for tn in trait_names:
                trend = self.classify_trait_trend(code, tn)
                if trend:
                    traits_data[tn] = trend.to_dict()
            agents_data[code] = {"traits": traits_data}

        return {
            "agents": agents_data,
            "total_snapshots": len(self._trait_snapshots),
        }

    # ==================== Personality Coherence (Phase 5) ====================

    def detect_anomalies(self, agent_code: str) -> List[Dict]:
        """
        Detect anomalous trait velocity from recent snapshots.

        Returns [] if < 2 snapshots.
        """
        agent_snaps = [s for s in self._trait_snapshots if s.agent_code == agent_code]
        window = agent_snaps[-ANOMALY_LOOKBACK_SNAPSHOTS:]
        if len(window) < 2:
            return []

        anomalies: List[Dict] = []
        # Get all trait names from latest snapshot
        trait_names = list(window[-1].trait_values.keys())
        for tn in trait_names:
            values = [s.trait_values[tn] for s in window if tn in s.trait_values]
            if len(values) < 2:
                continue
            velocity = abs(_linear_slope(values))
            normal_rate = EVOLUTION_RATE
            if velocity > ANOMALY_VELOCITY_MULTIPLIER * normal_rate:
                anomalies.append(
                    {
                        "trait_name": tn,
                        "velocity": round(velocity, 6),
                        "normal_rate": normal_rate,
                    }
                )
        return anomalies

    def _compute_tension_score(self, agent_code: str) -> tuple:
        """
        Compute coherence score and tension list for an agent.

        Returns (coherence_score, tensions_list).
        """
        profile = self._profiles.get(agent_code)
        if not profile:
            return 1.0, []

        traits = profile.get_all_traits()
        coherence_score = 1.0
        tensions: List[Dict[str, Any]] = []

        for trait_a_name, trait_b_name, rule_type in COHERENCE_RULES:
            ta = traits.get(trait_a_name)
            tb = traits.get(trait_b_name)
            if ta is None or tb is None:
                continue

            if rule_type == "same_high":
                tension = max(0.0, ta.value + tb.value - 1.2)
                desc = f"Both {trait_a_name} and {trait_b_name} high creates internal conflict"
            else:  # "opposite"
                tension = max(0.0, abs(ta.value - tb.value) - 0.4)
                desc = f"{trait_a_name} and {trait_b_name} diverge, creating inconsistency"

            if tension > 0:
                tensions.append(
                    {
                        "trait_a": trait_a_name,
                        "trait_b": trait_b_name,
                        "tension_value": round(tension, 4),
                        "description": desc,
                    }
                )
            coherence_score -= tension * COHERENCE_TENSION_WEIGHT

        return max(0.0, coherence_score), tensions

    def classify_agent_health(self, agent_code: str) -> str:
        """
        Classify agent health: "healthy", "drifting", "oscillating", "degrading".
        """
        # Check for anomalies
        anomalies = self.detect_anomalies(agent_code)

        # Check coherence
        coherence_score, _ = self._compute_tension_score(agent_code)

        if anomalies or coherence_score < 0.5:
            return "degrading"

        # Check for critical drift alerts
        alerts = self.check_drift_alerts(agent_code)
        critical = [a for a in alerts if a.severity == "critical"]
        if critical:
            return "drifting"

        # Check for oscillating traits
        profile = self._profiles.get(agent_code)
        agent_snaps = [s for s in self._trait_snapshots if s.agent_code == agent_code]
        if agent_snaps and profile:
            for tn in profile.get_all_traits():
                trend = self.classify_trait_trend(agent_code, tn)
                if trend and trend.classification == "oscillating":
                    return "oscillating"

        return "healthy"

    def compute_coherence(self, agent_code: str) -> Optional[CoherenceReport]:
        """
        Compute personality coherence report for an agent.

        Returns None if agent not registered.
        """
        if agent_code not in self._profiles:
            return None

        coherence_score, tensions = self._compute_tension_score(agent_code)
        anomalies = self.detect_anomalies(agent_code)
        health = self.classify_agent_health(agent_code)

        return CoherenceReport(
            agent_code=agent_code,
            coherence_score=coherence_score,
            tensions=tensions,
            anomalies=anomalies,
            health_classification=health,
        )

    # ==================== Cross-Agent Learning (Phase 5) ====================

    def extract_top_performer_patterns(
        self,
        task_type: str,
    ) -> Dict[str, Dict]:
        """
        Extract trait patterns from top-performing agents for a task type.
        """
        # Group outcomes by agent
        agent_outcomes: Dict[str, List[bool]] = {}
        for o in self._task_outcomes:
            if o["task_type"] == task_type:
                agent_outcomes.setdefault(o["agent_code"], []).append(o["success"])

        # Filter by minimum samples
        qualified = {
            agent: outcomes
            for agent, outcomes in agent_outcomes.items()
            if len(outcomes) >= MIN_TOP_PERFORMER_SAMPLES and agent in self._profiles
        }
        if not qualified:
            return {}

        # Compute success rates
        agent_rates = {agent: sum(o) / len(o) for agent, o in qualified.items()}

        # Select top 25% of agents by success rate (percentile ranking)
        sorted_agents = sorted(agent_rates.items(), key=lambda x: x[1], reverse=True)
        n = len(sorted_agents)
        if n < 4:
            top_count = 1
        else:
            fraction = n * (1.0 - TOP_PERFORMER_PERCENTILE)
            top_count = max(1, int(fraction) + (1 if fraction % 1 > 0 else 0))
        top_performers = dict(sorted_agents[:top_count])

        result: Dict[str, Dict] = {}
        for agent, rate in top_performers.items():
            profile = self._profiles.get(agent)
            if not profile:
                continue
            traits = profile.get_all_traits()
            result[agent] = {
                "success_rate": rate,
                "sample_count": len(qualified[agent]),
                "traits": {n: t.value for n, t in traits.items()},
            }
        return result

    def generate_peer_recommendations(
        self,
        agent_code: str,
        task_type: Optional[str] = None,
    ) -> List[PeerRecommendation]:
        """
        Generate trait adjustment recommendations based on top performer patterns.
        """
        if agent_code not in self._profiles:
            return []

        # Get task types the agent has outcomes in
        agent_task_types = set()
        for o in self._task_outcomes:
            if o["agent_code"] == agent_code:
                agent_task_types.add(o["task_type"])

        if task_type:
            agent_task_types = {task_type} & agent_task_types

        recommendations: List[PeerRecommendation] = []
        agent_profile = self._profiles[agent_code]
        agent_traits = agent_profile.get_all_traits()

        for tt in agent_task_types:
            top_patterns = self.extract_top_performer_patterns(tt)
            if agent_code in top_patterns:
                continue  # Agent is already a top performer

            if not top_patterns:
                continue

            # Compute agent's success rate for this task type
            agent_outcomes = [
                o["success"]
                for o in self._task_outcomes
                if o["agent_code"] == agent_code and o["task_type"] == tt
            ]
            agent_rate = sum(agent_outcomes) / len(agent_outcomes) if agent_outcomes else 0.0

            # Average top performer traits
            avg_traits: Dict[str, float] = {}
            avg_rate = 0.0
            for src_agent, data in top_patterns.items():
                avg_rate += data["success_rate"]
                for tn, tv in data["traits"].items():
                    avg_traits.setdefault(tn, [])
                    avg_traits[tn].append(tv)
            avg_rate /= len(top_patterns)

            for tn, values in avg_traits.items():
                avg_val = sum(values) / len(values)
                agent_trait = agent_traits.get(tn)
                if agent_trait is None:
                    continue
                if abs(agent_trait.value - avg_val) > 0.1:
                    sample_count = len(
                        [o for o in self._task_outcomes if o.get("agent_code") == agent_code]
                    )
                    base_confidence = avg_rate - agent_rate if avg_rate > agent_rate else 0.1
                    confidence = min(
                        1.0, base_confidence * min(1.0, sample_count / MIN_ATTRIBUTION_SAMPLES)
                    )
                    recommendations.append(
                        PeerRecommendation(
                            target_agent=agent_code,
                            source_agent=next(iter(top_patterns)),
                            task_type=tt,
                            recommendation_type="trait_adjustment",
                            trait_name=tn,
                            source_value=avg_val,
                            target_value=agent_trait.value,
                            suggested_value=avg_val,
                            source_success_rate=avg_rate,
                            target_success_rate=agent_rate,
                            confidence=confidence,
                        )
                    )

        recommendations = recommendations[:MAX_PEER_RECOMMENDATIONS]
        self._peer_recommendations.extend(recommendations)

        return recommendations

    def share_heuristic(
        self,
        source_agent: str,
        target_agent: str,
        heuristic_id: str,
    ) -> Optional[Dict]:
        """
        Copy a heuristic from source to target agent if it meets sharing thresholds.
        """
        from ag3ntwerk.core.heuristics import Heuristic
        from uuid import uuid4

        source_engine = self._heuristic_engines.get(source_agent)
        target_engine = self._heuristic_engines.get(target_agent)
        if not source_engine or not target_engine:
            return None

        heuristic = source_engine.get_heuristic(heuristic_id)
        if not heuristic:
            return None

        if heuristic.total_outcomes < HEURISTIC_SHARE_MIN_SAMPLES:
            return None
        if heuristic.success_rate < HEURISTIC_SHARE_MIN_SUCCESS_RATE:
            return None

        # Create copy for target
        new_h = Heuristic(
            id=str(uuid4()),
            name=f"{heuristic.name} (from {source_agent})",
            agent_code=target_agent,
            condition=heuristic.condition,
            action=heuristic.action,
            threshold=heuristic.threshold,
            weight=heuristic.weight,
            cooldown_seconds=heuristic.cooldown_seconds,
        )
        target_engine.add_heuristic(new_h)

        return {
            "source_agent": source_agent,
            "target_agent": target_agent,
            "source_heuristic_id": heuristic_id,
            "new_heuristic_id": new_h.id,
            "name": new_h.name,
            "success_rate": heuristic.success_rate,
        }

    def auto_share_heuristics(self) -> List[Dict]:
        """
        Find heuristics meeting sharing thresholds and share to agents missing them.
        """
        shares: List[Dict] = []
        for source_code, source_engine in self._heuristic_engines.items():
            stats = source_engine.get_stats()
            for h_info in stats.get("heuristics", []):
                hid = h_info.get("id", "")
                h = source_engine.get_heuristic(hid)
                if not h:
                    continue
                if h.total_outcomes < HEURISTIC_SHARE_MIN_SAMPLES:
                    continue
                if h.success_rate < HEURISTIC_SHARE_MIN_SUCCESS_RATE:
                    continue

                # Share to agents that lack a heuristic with the same base name
                base_name = h.name.split(" (from ")[0]
                for target_code, target_engine in self._heuristic_engines.items():
                    if target_code == source_code:
                        continue
                    # Check if target already has a heuristic with same base name
                    has_it = False
                    for th in target_engine.all_heuristics.values():
                        if th.name.split(" (from ")[0] == base_name:
                            has_it = True
                            break
                    if has_it:
                        continue

                    result = self.share_heuristic(source_code, target_code, hid)
                    if result:
                        shares.append(result)
        return shares

    # ==================== Team Composition Learning (Phase 5) ====================

    def record_team_outcome(
        self,
        team: List[str],
        task_type: str,
        success: bool,
        task_id: str = "",
        compatibility_score: float = 0.0,
    ) -> None:
        """Record a team's outcome for a task."""
        if not team:
            return
        sorted_team = sorted(team)
        with self._lock:
            self._team_outcomes.append(
                TeamOutcome(
                    team=sorted_team,
                    task_type=task_type,
                    success=success,
                    task_id=task_id,
                    compatibility_score=compatibility_score,
                )
            )

    def get_team_stats(
        self,
        task_type: Optional[str] = None,
    ) -> Dict:
        """
        Get team composition statistics.

        Groups by (frozen team, task_type) and computes success rates.
        """
        groups: Dict[tuple, List[bool]] = {}
        for to in self._team_outcomes:
            if task_type and to.task_type != task_type:
                continue
            key = (tuple(to.team), to.task_type)
            groups.setdefault(key, []).append(to.success)

        compositions = []
        for (team_tuple, tt), outcomes in groups.items():
            if len(outcomes) >= MIN_TEAM_SAMPLES:
                compositions.append(
                    {
                        "team": list(team_tuple),
                        "task_type": tt,
                        "samples": len(outcomes),
                        "success_rate": round(sum(outcomes) / len(outcomes), 4),
                    }
                )

        compositions.sort(key=lambda c: c["success_rate"], reverse=True)
        return {
            "total_team_outcomes": len(self._team_outcomes),
            "compositions": compositions,
        }

    def recommend_learned_team(
        self,
        task_type: str,
        team_size: int = 3,
    ) -> Dict:
        """
        Recommend a team based on learned outcomes, falling back to personality fit.
        """
        stats = self.get_team_stats(task_type)
        # Filter by team_size
        matching = [c for c in stats["compositions"] if len(c["team"]) == team_size]

        if matching:
            best = matching[0]  # Already sorted by success rate
            return {
                "source": "learned",
                "team": best["team"],
                "success_rate": best["success_rate"],
                "samples": best["samples"],
                "fallback_used": False,
            }

        # Fallback to personality dynamics
        suggestion = self._dynamics_engine.suggest_team(
            self._profiles,
            {},
            team_size,
        )
        return {
            "source": "personality_fit",
            "team": suggestion.suggested_agents[:team_size],
            "success_rate": 0.0,
            "samples": 0,
            "fallback_used": True,
        }

    def get_best_pairs(
        self,
        task_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Extract best agent pairs from team outcomes.
        """
        pair_outcomes: Dict[tuple, List[bool]] = {}
        for to in self._team_outcomes:
            if task_type and to.task_type != task_type:
                continue
            team = to.team
            for i in range(len(team)):
                for j in range(i + 1, len(team)):
                    pair = (team[i], team[j])
                    pair_outcomes.setdefault(pair, []).append(to.success)

        pairs = []
        for pair, outcomes in pair_outcomes.items():
            if len(outcomes) >= MIN_PAIR_SAMPLES:
                pairs.append(
                    {
                        "pair": list(pair),
                        "samples": len(outcomes),
                        "success_rate": round(sum(outcomes) / len(outcomes), 4),
                    }
                )

        pairs.sort(key=lambda p: p["success_rate"], reverse=True)
        return pairs[:limit]

    # ==================== Closed-Loop Trait Map (Phase 5) ====================

    def apply_trait_map_suggestions(
        self,
        min_confidence: float = MIN_APPLY_CONFIDENCE,
    ) -> List[TraitMapUpdate]:
        """
        Auto-apply high-confidence attribution suggestions to the learned trait map.
        """
        suggestions = self.suggest_trait_map_updates(min_correlation=min_confidence)
        updates: List[TraitMapUpdate] = []

        for task_type, trait_suggestions in suggestions.items():
            existing = self._learned_trait_map.get(task_type, {})
            for trait_name, suggested_value in trait_suggestions.items():
                old_value = existing.get(trait_name)
                if old_value is not None and abs(old_value - suggested_value) < 1e-6:
                    continue  # Skip identical

                # Compute pre-apply success rate
                outcomes = [
                    o["success"] for o in self._task_outcomes if o["task_type"] == task_type
                ]
                pre_rate = sum(outcomes) / len(outcomes) if outcomes else None

                # Find the attribution for this trait to get correlation/sample info
                attributions = self.compute_attribution(task_type=task_type)
                corr = 0.0
                samples = 0
                for a in attributions:
                    if a.trait_name == trait_name:
                        corr = a.correlation
                        samples = a.sample_count
                        break

                # Apply
                self._learned_trait_map.setdefault(task_type, {})[trait_name] = suggested_value

                update = TraitMapUpdate(
                    task_type=task_type,
                    trait_name=trait_name,
                    old_value=old_value,
                    new_value=suggested_value,
                    source_correlation=corr,
                    source_sample_count=samples,
                    pre_apply_success_rate=pre_rate,
                )
                updates.append(update)

        self._trait_map_updates.extend(updates)

        # Cap learned map entries
        total = sum(len(v) for v in self._learned_trait_map.values())
        while total > MAX_LEARNED_TRAIT_MAP_ENTRIES and self._learned_trait_map:
            # Remove oldest task_type entry
            oldest_key = next(iter(self._learned_trait_map))
            del self._learned_trait_map[oldest_key]
            total = sum(len(v) for v in self._learned_trait_map.values())

        return updates

    def get_effective_traits(
        self,
        task_type: str,
        static_traits: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Merge static traits with learned trait map. Learned values override.
        """
        result = dict(static_traits) if static_traits else {}
        learned = self._learned_trait_map.get(task_type, {})
        result.update(learned)
        return result

    def validate_trait_map_updates(self) -> List[Dict]:
        """
        Validate pending trait map updates against post-apply performance.
        """
        validations: List[Dict] = []
        for update in self._trait_map_updates:
            if update.validation_status != "pending":
                continue

            # Count post-apply outcomes
            post_outcomes = [
                o["success"]
                for o in self._task_outcomes
                if o["task_type"] == update.task_type
                and o.get("timestamp", "") >= update.applied_at.isoformat()
            ]

            if len(post_outcomes) < TRAIT_MAP_VALIDATION_WINDOW:
                continue

            post_rate = sum(post_outcomes) / len(post_outcomes)
            update.post_apply_success_rate = post_rate

            pre_rate = update.pre_apply_success_rate or 0.0
            if pre_rate - post_rate > TRAIT_MAP_ROLLBACK_THRESHOLD:
                # Rollback
                learned = self._learned_trait_map.get(update.task_type, {})
                if update.trait_name in learned:
                    del learned[update.trait_name]
                    if not learned:
                        self._learned_trait_map.pop(update.task_type, None)
                update.validation_status = "rolled_back"
            else:
                update.validation_status = "validated"

            validations.append(update.to_dict())

        return validations

    def get_learned_trait_map(self) -> Dict[str, Dict[str, float]]:
        """Return a copy of the learned trait map."""
        return {k: dict(v) for k, v in self._learned_trait_map.items()}
