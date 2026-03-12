"""
Overwatch (Overwatch) - Overwatch.

The Overwatch is the operational coordinator within ag3ntwerk. It:
- Routes tasks to appropriate agents (Forge, Echo, Vector, etc.)
- Monitors health and performance
- Detects drift and escalates to Nexus (the strategic brain)
- Executes directives received from Nexus
- Integrates with the learning system for adaptive routing

NOTE: This is NOT the Nexus. The true Nexus (AutonomousCOO) will live in
the Nexus codebase and handle strategic decision-making. Overwatch operates
under strategic context provided by Nexus, escalating when operational
drift exceeds tolerances.

Codename: Overwatch
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.core.base import Agent, Manager, Specialist, Task, TaskResult, TaskStatus
from ag3ntwerk.llm.base import LLMProvider

from ag3ntwerk.agents.overwatch.models import (
    DriftType,
    DriftSignal,
    StrategicContext,
    ORCHESTRATION_CAPABILITIES,
)
from ag3ntwerk.agents.overwatch.managers import (
    WorkflowManager,
    TaskRoutingManager,
    ProcessManager,
    CoordinationManager,
)
from ag3ntwerk.agents.overwatch.specialists import (
    WorkflowDesigner,
    TaskAnalyst,
    MetricsAnalyst,
    ProcessEngineer,
    OKRCoordinator,
)
from ag3ntwerk.agents.overwatch.metacognition_mixin import MetacognitionMixin
from ag3ntwerk.agents.overwatch.learning_mixin import LearningMixin
from ag3ntwerk.agents.overwatch.nexus_mixin import NexusMixin
from ag3ntwerk.agents.overwatch.agenda_mixin import AgendaMixin
from ag3ntwerk.agents.overwatch.workbench_mixin import WorkbenchMixin

if TYPE_CHECKING:
    from ag3ntwerk.learning.orchestrator import LearningOrchestrator
    from ag3ntwerk.agents.bridges.nexus_bridge import NexusBridge

# Learning system integration (optional, imported lazily)
try:
    from ag3ntwerk.learning.models import HierarchyPath

    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False
    HierarchyPath = None

# NexusBridge integration (optional)
try:
    from ag3ntwerk.agents.bridges.nexus_bridge import NexusBridge, NexusBridgeConfig

    NEXUS_BRIDGE_AVAILABLE = True
except ImportError:
    NEXUS_BRIDGE_AVAILABLE = False
    NexusBridge = None
    NexusBridgeConfig = None

logger = get_logger(__name__)


# Import comprehensive routing rules from dedicated module
from ag3ntwerk.agents.overwatch.routing_rules import ROUTING_RULES, FALLBACK_ROUTES


@dataclass
class AgentHealthStatus:
    """Health status for an agent."""

    agent_code: str
    is_healthy: bool = True
    health_score: float = 1.0
    total_tasks: int = 0
    successful_tasks: int = 0
    consecutive_failures: int = 0
    avg_latency_ms: float = 0.0
    last_error: Optional[str] = None
    last_check: Optional[datetime] = None
    circuit_breaker_open: bool = False
    circuit_breaker_until: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 1.0
        return self.successful_tasks / self.total_tasks

    @property
    def is_available(self) -> bool:
        """Check if agent is available (circuit breaker not open)."""
        if not self.circuit_breaker_open:
            return True
        if self.circuit_breaker_until and datetime.now(timezone.utc) > self.circuit_breaker_until:
            return True
        return False


# Communication layer (simplified)
@dataclass
class AgentMessage:
    """Message between agents."""

    sender: str
    message_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AgentCommunicator:
    """Base class for agent communication."""

    async def send(self, target: str, message: AgentMessage) -> None:
        raise NotImplementedError

    async def broadcast(self, message: AgentMessage) -> None:
        raise NotImplementedError

    async def get_agent_status(self, agent_code: str) -> Dict[str, Any]:
        raise NotImplementedError


class LocalCommunicator(AgentCommunicator):
    """In-process communicator for local operation."""

    def __init__(self):
        self._agents: Dict[str, Agent] = {}

    def register_agent(self, agent: Agent) -> None:
        self._agents[agent.code] = agent

    async def send(self, target: str, message: AgentMessage) -> None:
        agent = self._agents.get(target)
        if agent:
            logger.debug(f"Message from {message.sender} to {target}: {message.message_type}")

    async def broadcast(self, message: AgentMessage) -> None:
        for code in self._agents:
            if code != message.sender:
                await self.send(code, message)

    async def get_agent_status(self, agent_code: str) -> Dict[str, Any]:
        agent = self._agents.get(agent_code)
        if not agent:
            return {"status": "not_found"}
        return {
            "code": agent.code,
            "name": agent.name,
            "is_active": agent.is_active,
        }


class HealthAwareRouter:
    """
    Health-aware task routing for Overwatch.

    Features:
    - Track agent health metrics
    - Circuit breaker pattern for failing agents
    - Fallback routing when primary agent unhealthy
    - Load balancing based on health scores
    """

    FAILURE_THRESHOLD = 3
    CIRCUIT_TIMEOUT_SECONDS = 60
    HEALTH_DECAY_FACTOR = 0.9
    HEALTH_RECOVERY_FACTOR = 1.05

    def __init__(self):
        """Initialize health-aware router."""
        self._health: Dict[str, AgentHealthStatus] = {}
        self._routing_rules = ROUTING_RULES
        self._fallback_routes = FALLBACK_ROUTES

    def get_or_create_health(self, agent_code: str) -> AgentHealthStatus:
        """Get or create health status for an agent."""
        if agent_code not in self._health:
            self._health[agent_code] = AgentHealthStatus(agent_code=agent_code)
        return self._health[agent_code]

    def record_success(self, agent_code: str, latency_ms: float) -> None:
        """Record successful task completion."""
        health = self.get_or_create_health(agent_code)
        health.total_tasks += 1
        health.successful_tasks += 1
        health.consecutive_failures = 0
        health.last_error = None
        health.health_score = min(1.0, health.health_score * self.HEALTH_RECOVERY_FACTOR)

        if health.avg_latency_ms == 0:
            health.avg_latency_ms = latency_ms
        else:
            health.avg_latency_ms = 0.8 * health.avg_latency_ms + 0.2 * latency_ms

        health.last_check = datetime.now(timezone.utc)
        health.is_healthy = True

        if health.circuit_breaker_open:
            health.circuit_breaker_open = False
            health.circuit_breaker_until = None
            logger.info(f"Circuit breaker closed for {agent_code}")

    def record_failure(self, agent_code: str, error: str) -> None:
        """Record task failure."""
        health = self.get_or_create_health(agent_code)
        health.total_tasks += 1
        health.consecutive_failures += 1
        health.last_error = error
        health.last_check = datetime.now(timezone.utc)
        health.health_score = max(0.1, health.health_score * self.HEALTH_DECAY_FACTOR)

        if health.consecutive_failures >= self.FAILURE_THRESHOLD:
            health.circuit_breaker_open = True
            health.circuit_breaker_until = datetime.now(timezone.utc) + timedelta(
                seconds=self.CIRCUIT_TIMEOUT_SECONDS
            )
            health.is_healthy = False
            logger.warning(
                f"Circuit breaker opened for {agent_code} "
                f"(failures: {health.consecutive_failures})"
            )

    def get_best_agent(
        self,
        task_type: str,
        available_agents: Dict[str, Agent],
    ) -> Optional[Tuple[str, float]]:
        """Get the best agent for a task type, considering health."""
        primary = self._routing_rules.get(task_type)

        if primary and primary in available_agents:
            health = self.get_or_create_health(primary)
            if health.is_available and health.health_score >= 0.5:
                return (primary, health.health_score)

        fallbacks = self._fallback_routes.get(task_type, [])
        for agent_code in fallbacks:
            if agent_code in available_agents and agent_code != primary:
                health = self.get_or_create_health(agent_code)
                if health.is_available and health.health_score >= 0.3:
                    logger.info(
                        f"Using fallback {agent_code} for {task_type} "
                        f"(primary {primary} unhealthy)"
                    )
                    return (agent_code, health.health_score)

        if primary and primary in available_agents:
            health = self.get_or_create_health(primary)
            if not health.circuit_breaker_open:
                logger.warning(f"Using unhealthy agent {primary} (no fallback available)")
                return (primary, health.health_score)

        return None

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all tracked agents."""
        return {
            code: {
                "is_healthy": h.is_healthy,
                "health_score": h.health_score,
                "success_rate": h.success_rate,
                "total_tasks": h.total_tasks,
                "consecutive_failures": h.consecutive_failures,
                "avg_latency_ms": h.avg_latency_ms,
                "circuit_breaker_open": h.circuit_breaker_open,
                "is_available": h.is_available,
            }
            for code, h in self._health.items()
        }

    def reset_health(self, agent_code: Optional[str] = None) -> None:
        """Reset health status for an agent or all agents."""
        if agent_code:
            if agent_code in self._health:
                self._health[agent_code] = AgentHealthStatus(agent_code=agent_code)
        else:
            self._health.clear()

    def add_fallback_route(self, task_type: str, fallbacks: List[str]) -> None:
        """Add or update fallback route for a task type."""
        self._fallback_routes[task_type] = fallbacks


class DriftMonitor:
    """
    Monitors operational drift and triggers Nexus escalation.

    Drift types monitored:
    - Performance: Success rate drops below threshold
    - Routing: Unknown task types appearing
    - Load: Sustained imbalance across agents
    - Conflict: Contradictory results from agents
    - Latency: Response times exceeding SLOs
    """

    def __init__(self, strategic_context: Optional[StrategicContext] = None):
        """Initialize drift monitor."""
        self._context = strategic_context or StrategicContext()
        self._drift_signals: List[DriftSignal] = []
        self._last_escalation: Optional[datetime] = None

        # Rolling window metrics
        self._recent_success_rates: Dict[str, List[bool]] = {}
        self._recent_latencies: Dict[str, List[float]] = {}
        self._unknown_task_types: List[str] = []

    def update_context(self, context: StrategicContext) -> None:
        """Update strategic context from Nexus."""
        self._context = context
        # Clear resolved drift signals
        self._drift_signals = [d for d in self._drift_signals if not d.resolved]
        logger.info("Strategic context updated from Nexus")

    def record_task_outcome(
        self,
        agent_code: str,
        task_type: str,
        success: bool,
        latency_ms: float,
    ) -> Optional[DriftSignal]:
        """Record task outcome and check for drift."""
        # Track success rate
        if agent_code not in self._recent_success_rates:
            self._recent_success_rates[agent_code] = []
        self._recent_success_rates[agent_code].append(success)
        # Keep last 50 outcomes
        self._recent_success_rates[agent_code] = self._recent_success_rates[agent_code][-50:]

        # Track latency
        if agent_code not in self._recent_latencies:
            self._recent_latencies[agent_code] = []
        self._recent_latencies[agent_code].append(latency_ms)
        self._recent_latencies[agent_code] = self._recent_latencies[agent_code][-50:]

        # Check for drift
        return self._check_for_drift(agent_code, task_type)

    def record_unknown_task_type(self, task_type: str) -> DriftSignal:
        """Record an unknown task type (routing drift)."""
        if task_type not in self._unknown_task_types:
            self._unknown_task_types.append(task_type)

        signal = DriftSignal(
            drift_type=DriftType.ROUTING,
            severity=0.6,
            description=f"Unknown task type encountered: {task_type}",
            affected_task_type=task_type,
        )
        self._drift_signals.append(signal)
        return signal

    def _check_for_drift(
        self,
        agent_code: str,
        task_type: str,
    ) -> Optional[DriftSignal]:
        """Check for various drift conditions."""
        # Check performance drift
        recent = self._recent_success_rates.get(agent_code, [])
        if len(recent) >= 10:
            success_rate = sum(recent) / len(recent)
            if success_rate < self._context.success_rate_threshold:
                signal = DriftSignal(
                    drift_type=DriftType.PERFORMANCE,
                    severity=1.0 - success_rate,
                    description=f"Success rate for {agent_code} dropped to {success_rate:.2%}",
                    affected_executive=agent_code,
                    current_value=success_rate,
                    threshold_value=self._context.success_rate_threshold,
                )
                self._drift_signals.append(signal)
                return signal

        # Check latency drift
        latencies = self._recent_latencies.get(agent_code, [])
        if len(latencies) >= 5:
            avg_latency = sum(latencies) / len(latencies)
            if avg_latency > self._context.latency_slo_ms:
                signal = DriftSignal(
                    drift_type=DriftType.LATENCY,
                    severity=min(1.0, avg_latency / (self._context.latency_slo_ms * 2)),
                    description=f"Average latency for {agent_code} is {avg_latency:.0f}ms",
                    affected_executive=agent_code,
                    current_value=avg_latency,
                    threshold_value=self._context.latency_slo_ms,
                )
                self._drift_signals.append(signal)
                return signal

        return None

    def get_unresolved_drift(self) -> List[DriftSignal]:
        """Get all unresolved drift signals."""
        return [d for d in self._drift_signals if not d.resolved and not d.escalated]

    def should_escalate(self) -> bool:
        """Check if drift warrants Nexus escalation."""
        if not self._context.auto_escalation_enabled:
            return False

        # Check cooldown
        if self._last_escalation:
            cooldown = timedelta(seconds=self._context.escalation_cooldown_seconds)
            if datetime.now(timezone.utc) - self._last_escalation < cooldown:
                return False

        # Check for drift exceeding tolerance
        unresolved = self.get_unresolved_drift()
        for signal in unresolved:
            if signal.severity > self._context.drift_tolerance:
                return True

        return False

    def mark_escalated(self) -> None:
        """Mark current drift signals as escalated."""
        self._last_escalation = datetime.now(timezone.utc)
        for signal in self.get_unresolved_drift():
            signal.escalated = True
            signal.escalated_at = datetime.now(timezone.utc)

    def get_drift_summary(self) -> Dict[str, Any]:
        """Get summary of current drift state."""
        unresolved = self.get_unresolved_drift()
        return {
            "total_signals": len(self._drift_signals),
            "unresolved_count": len(unresolved),
            "should_escalate": self.should_escalate(),
            "last_escalation": self._last_escalation.isoformat() if self._last_escalation else None,
            "unknown_task_types": self._unknown_task_types,
            "signals_by_type": {
                dt.value: len([s for s in unresolved if s.drift_type == dt]) for dt in DriftType
            },
        }


class Overwatch(MetacognitionMixin, LearningMixin, NexusMixin, AgendaMixin, WorkbenchMixin, Manager):
    """
    Overwatch - Overwatch.

    The Overwatch orchestrates all ag3ntwerk agents, routing tasks to the
    appropriate specialists and coordinating complex workflows.

    Operates autonomously under strategic context from the external
    Nexus (Nexus), escalating when drift is detected.

    Codename: Overwatch

    Example:
        ```python
        llm = GPT4AllProvider()
        await llm.connect()

        cos = Overwatch(llm_provider=llm)

        # Register action modules
        cos.register_subordinate(Sentinel(llm_provider=llm))
        cos.register_subordinate(Forge(llm_provider=llm))

        # Process a task
        task = Task(
            description="Review security of auth module",
            task_type="security_scan",
        )
        result = await cos.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        communicator: Optional[AgentCommunicator] = None,
        enable_health_routing: bool = True,
        nexus_bridge: Optional["NexusBridge"] = None,
    ):
        super().__init__(
            code="Overwatch",
            name="Overwatch",
            domain="Operations, Coordination, Task Routing",
            llm_provider=llm_provider,
        )
        self.codename = "Overwatch"
        self.capabilities = ORCHESTRATION_CAPABILITIES

        # Communication layer
        self.communicator = communicator or LocalCommunicator()
        if isinstance(self.communicator, LocalCommunicator):
            self.communicator.register_agent(self)

        # Health-aware routing
        self._health_routing_enabled = enable_health_routing
        self._health_router = HealthAwareRouter() if enable_health_routing else None

        # Drift detection
        self._drift_monitor = DriftMonitor()

        # Nexus bridge (for external strategic Nexus communication)
        self._nexus_bridge: Optional["NexusBridge"] = nexus_bridge

        # Learning system integration
        self._learning_orchestrator: Optional["LearningOrchestrator"] = None

        # Metacognition service (optional)
        self._metacognition_service = None
        self._active_conflicts: List = []

        # Smart router (learning-informed routing, optional)
        self._smart_router = None

        # Agenda and workbench (optional, connected later)
        self._agenda_engine = None
        self._workbench_pipeline = None

        # Task management
        self._task_queue: asyncio.Queue[Task] = asyncio.Queue()
        self._active_tasks: Dict[str, Task] = {}
        self._completed_tasks: Dict[str, TaskResult] = {}
        self._task_start_times: Dict[str, datetime] = {}

        # Metrics
        self._metrics = {
            "tasks_received": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_delegated": 0,
            "tasks_rerouted": 0,
            "tasks_dynamically_routed": 0,
            "escalations_to_coo": 0,
            "start_time": datetime.now(),
        }

        # Initialize managers
        self._init_managers()

    def _init_managers(self) -> None:
        """Initialize and register Overwatch's managers with their specialists."""
        wfm = WorkflowManager(llm_provider=self.llm_provider)
        trm = TaskRoutingManager(llm_provider=self.llm_provider)
        pm = ProcessManager(llm_provider=self.llm_provider)
        cm = CoordinationManager(llm_provider=self.llm_provider)

        workflow_designer = WorkflowDesigner(llm_provider=self.llm_provider)
        task_analyst = TaskAnalyst(llm_provider=self.llm_provider)
        metrics_analyst = MetricsAnalyst(llm_provider=self.llm_provider)
        process_engineer = ProcessEngineer(llm_provider=self.llm_provider)
        okr_coordinator = OKRCoordinator(llm_provider=self.llm_provider)

        wfm.register_subordinate(workflow_designer)
        trm.register_subordinate(task_analyst)
        pm.register_subordinate(process_engineer)
        cm.register_subordinate(metrics_analyst)
        cm.register_subordinate(okr_coordinator)

        self._cos_managers = {
            "WFM": wfm,
            "TRM": trm,
            "PRM": pm,
            "CORM": cm,
        }

    @property
    def metacognition_service(self):
        return self._metacognition_service

    def can_handle(self, task: Task) -> bool:
        """Overwatch can handle any task by routing it appropriately."""
        return True

    async def execute(self, task: Task) -> TaskResult:
        """
        Execute a task by routing to the appropriate agent.

        The Overwatch:
        1. Analyzes the task
        2. Determines the best agent to handle it (with health awareness + learning)
        3. Applies confidence calibration if learning is enabled
        4. Delegates to that agent
        5. Records health metrics and learning outcomes from the result
        """
        self._metrics["tasks_received"] += 1
        task.status = TaskStatus.IN_PROGRESS
        self._active_tasks[task.id] = task
        self._task_start_times[task.id] = datetime.now(timezone.utc)

        target_agent = None
        calibrated_confidence = None
        raw_confidence = None
        try:
            # Check for drift before execution
            if self._drift_monitor.should_escalate():
                await self._escalate_to_coo()

            # Route task (uses dynamic routing if learning enabled)
            target_agent = await self._route_task(task)

            if not target_agent:
                result = await self._handle_directly(task)
            else:
                # Apply confidence calibration before delegation
                if self._learning_orchestrator and LEARNING_AVAILABLE:
                    try:
                        # Get agent's default confidence (or from task context)
                        raw_confidence = (
                            task.context.get("raw_confidence", 0.7) if task.context else 0.7
                        )

                        # Apply calibration based on historical accuracy
                        calibrated_confidence = (
                            await self._learning_orchestrator.get_calibrated_confidence(
                                agent_code=target_agent,
                                task_type=task.task_type,
                                raw_confidence=raw_confidence,
                            )
                        )

                        # Store in task context for downstream use
                        task.context = task.context or {}
                        task.context["calibrated_confidence"] = calibrated_confidence
                        task.context["raw_confidence"] = raw_confidence
                        task.context["initial_confidence"] = calibrated_confidence

                        if abs(calibrated_confidence - raw_confidence) > 0.1:
                            logger.debug(
                                f"Calibrated confidence for {target_agent}/{task.task_type}: "
                                f"{raw_confidence:.2f} -> {calibrated_confidence:.2f}"
                            )
                    except Exception as e:
                        logger.debug(f"Confidence calibration skipped: {e}")

                # Delegate to target agent (Manager.delegate() applies heuristics internally)
                result = await self.delegate(task, target_agent)
                self._metrics["tasks_delegated"] += 1

            # Calculate latency
            latency_ms = self._calculate_task_latency(task.id)

            # Record health metrics
            if result.success:
                self._metrics["tasks_completed"] += 1
                if target_agent and self._health_router:
                    self._health_router.record_success(target_agent, latency_ms)
            else:
                self._metrics["tasks_failed"] += 1
                if target_agent and self._health_router:
                    self._health_router.record_failure(
                        target_agent, result.error or "Unknown error"
                    )

            # Record for drift detection
            if target_agent:
                drift_signal = self._drift_monitor.record_task_outcome(
                    target_agent,
                    task.task_type,
                    result.success,
                    latency_ms,
                )
                if drift_signal and drift_signal.exceeds_tolerance:
                    logger.warning(f"Drift detected: {drift_signal.description}")

            # Record outcome to learning system
            if self._learning_orchestrator and LEARNING_AVAILABLE and HierarchyPath:
                try:
                    await self._record_learning_outcome(
                        task=task,
                        target_agent=target_agent,
                        result=result,
                        latency_ms=latency_ms,
                        calibrated_confidence=calibrated_confidence,
                        raw_confidence=raw_confidence,
                    )
                except Exception as e:
                    logger.warning(f"Failed to record outcome to learning system: {e}")

            # Record to metacognition service
            if self._metacognition_service and target_agent:
                try:
                    if self.llm_provider:
                        await self._metacognition_service.on_task_completed_async(
                            agent_code=target_agent,
                            task_id=task.id,
                            task_type=task.task_type,
                            success=result.success,
                            duration_ms=latency_ms,
                            confidence=calibrated_confidence,
                            error=result.error,
                            llm_provider=self.llm_provider,
                            task_description=task.description,
                            output_summary=str(result.output)[:500] if result.output else "",
                        )
                    else:
                        self._metacognition_service.on_task_completed(
                            agent_code=target_agent,
                            task_id=task.id,
                            task_type=task.task_type,
                            success=result.success,
                            duration_ms=latency_ms,
                            confidence=calibrated_confidence,
                            error=result.error,
                        )
                except Exception as e:
                    logger.warning(f"Metacognition recording failed: {e}")

            # Record routing outcome for feedback loop
            if self._metacognition_service and target_agent:
                try:
                    task_traits = self._infer_task_traits(task)
                    if task_traits and self._metacognition_service is not None:
                        profile = self._metacognition_service.get_profile(target_agent)
                        personality_score = (
                            profile.compute_task_fit(task_traits) if profile else 0.5
                        )
                        self._metacognition_service.record_routing_outcome(
                            agent_code=target_agent,
                            task_type=task.task_type,
                            personality_score=personality_score,
                            success=result.success,
                        )
                except Exception as e:
                    logger.warning(f"Routing outcome recording failed: {e}")

            self._completed_tasks[task.id] = result
            self.record_result(result)
            return result

        except Exception as e:
            self._metrics["tasks_failed"] += 1
            if target_agent and self._health_router:
                self._health_router.record_failure(target_agent, str(e))
            result = TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
            )
            self._completed_tasks[task.id] = result
            return result

        finally:
            self._active_tasks.pop(task.id, None)
            self._task_start_times.pop(task.id, None)

    async def _record_learning_outcome(
        self,
        task: Task,
        target_agent: Optional[str],
        result: TaskResult,
        latency_ms: float,
        calibrated_confidence: Optional[float],
        raw_confidence: Optional[float],
    ) -> None:
        """Record task outcome to learning system."""
        # Determine hierarchy path from result metrics or target
        manager_code = result.metrics.get("manager_code") if result.metrics else None
        specialist_code = result.metrics.get("specialist_code") if result.metrics else None

        hierarchy_path = HierarchyPath(
            agent=target_agent or "Overwatch",
            manager=manager_code,
            specialist=specialist_code,
        )

        # Extract pattern attribution data
        routing_decision = task.context.get("_routing_decision", {}) if task.context else {}
        was_routing_influenced = not routing_decision.get("used_static_fallback", True)
        was_confidence_calibrated = calibrated_confidence is not None and raw_confidence is not None

        # Get applied pattern IDs from routing decision and adjustments
        applied_pattern_ids = []
        if routing_decision:
            for score in routing_decision.get("scores", []):
                if isinstance(score, dict):
                    applied_pattern_ids.extend(score.get("applied_patterns", []))
        adjustments_patterns = task.context.get("_applied_pattern_ids", []) if task.context else []
        applied_pattern_ids.extend(adjustments_patterns)
        applied_pattern_ids = list(set(applied_pattern_ids))  # Deduplicate

        await self._learning_orchestrator.record_outcome(
            task_id=task.id,
            task_type=task.task_type,
            hierarchy_path=hierarchy_path,
            success=result.success,
            duration_ms=latency_ms,
            effectiveness=result.metrics.get("effectiveness") if result.metrics else None,
            confidence=result.metrics.get("initial_confidence") if result.metrics else None,
            actual_accuracy=result.metrics.get("actual_accuracy") if result.metrics else None,
            error=result.error,
            output_summary=str(result.output)[:500] if result.output else None,
            context=task.context,
            applied_pattern_ids=applied_pattern_ids,
            was_routing_influenced=was_routing_influenced,
            was_confidence_calibrated=was_confidence_calibrated,
        )

        # Record routing outcome for dynamic routing improvement
        await self._learning_orchestrator.record_routing_outcome(
            task_type=task.task_type,
            chosen_agent=target_agent or "Overwatch",
            success=result.success,
            was_dynamic=was_routing_influenced,
            duration_ms=latency_ms,
        )

        # Record pattern application outcomes for effectiveness measurement
        await self._learning_orchestrator.record_pattern_outcome(
            task_id=task.id,
            success=result.success,
            duration_ms=latency_ms,
            effectiveness=result.metrics.get("effectiveness", 0.0) if result.metrics else 0.0,
        )

        # Record confidence prediction outcome for calibration
        if calibrated_confidence is not None and target_agent:
            await self._learning_orchestrator.record_confidence_prediction(
                agent_code=target_agent,
                task_type=task.task_type,
                confidence=calibrated_confidence,
                was_successful=result.success,
            )

    def _calculate_task_latency(self, task_id: str) -> float:
        """Calculate task latency in milliseconds."""
        start_time = self._task_start_times.get(task_id)
        if not start_time:
            return 0.0
        delta = datetime.now(timezone.utc) - start_time
        return delta.total_seconds() * 1000

    async def _route_task(self, task: Task) -> Optional[str]:
        """
        Determine which agent should handle a task.

        Uses a priority-based routing strategy:
        1. Dynamic routing (learning-based) - if learning system connected and confident
        2. Health-aware routing - if enabled and agent health matters
        3. Static routing rules - fallback to ROUTING_RULES
        4. Capability-based routing - find agents that can handle the task
        5. LLM-based routing - for ambiguous cases with multiple capable agents
        """
        static_route = ROUTING_RULES.get(task.task_type)

        # Check if task type is unknown (routing drift)
        if not static_route:
            self._drift_monitor.record_unknown_task_type(task.task_type)

        # === PHASE 0.5: SMART ROUTER ===
        # Use SmartRouter if connected for learning-informed ranking
        if self._smart_router:
            try:
                best = await self._smart_router.get_best_agent(
                    task.task_type,
                    self._subordinates,
                    task.context,
                )
                if best:
                    agent_code, score = best
                    if score >= 0.6 and agent_code in self._subordinates:
                        logger.info(
                            "SmartRouter: %s -> %s (score=%.2f)",
                            task.task_type,
                            agent_code,
                            score,
                        )
                        return agent_code
            except Exception as e:
                logger.debug("SmartRouter failed, falling back: %s", e)

        # === PHASE 1: DYNAMIC ROUTING ===
        # Use learning-informed routing if available
        if self._learning_orchestrator and LEARNING_AVAILABLE:
            try:
                # Get dynamic routing decision
                decision = await self._learning_orchestrator.get_routing_decision(
                    task_type=task.task_type,
                    available_agents=self._subordinates,
                    static_route=static_route,
                    context=task.context,
                )

                # Store the routing decision in task context for tracking
                task.context = task.context or {}
                task.context["_routing_decision"] = {
                    "chosen_agent": decision.chosen_agent,
                    "confidence": decision.confidence,
                    "used_static_fallback": decision.used_static_fallback,
                    "reasoning": decision.reasoning,
                }

                # Also get task adjustments for hints/warnings
                if decision.chosen_agent in self._subordinates:
                    adjustments = await self._learning_orchestrator.get_task_adjustments(
                        task_type=task.task_type,
                        target_agent=decision.chosen_agent,
                    )

                    if adjustments.effectiveness_hints:
                        task.context["effectiveness_hints"] = adjustments.effectiveness_hints

                    if adjustments.warnings:
                        task.context["learning_warnings"] = adjustments.warnings

                    # Track applied patterns for outcome measurement
                    if adjustments.applied_pattern_ids:
                        task.context["_applied_patterns"] = adjustments.applied_pattern_ids
                        # Record pattern applications
                        for pattern_id in adjustments.applied_pattern_ids:
                            try:
                                await self._learning_orchestrator.record_pattern_application(
                                    pattern_id=pattern_id,
                                    task_id=task.id,
                                    task_type=task.task_type,
                                    agent_code=decision.chosen_agent,
                                    is_routing_pattern=bool(adjustments.preferred_route),
                                    is_confidence_pattern=bool(
                                        adjustments.confidence_adjustment != 0
                                    ),
                                    baseline_agent=static_route,
                                )
                            except Exception as e:
                                logger.debug(f"Failed to record pattern application: {e}")

                # Use the dynamic routing decision if confident enough
                if decision.confidence >= 0.6 and decision.chosen_agent in self._subordinates:
                    if not decision.used_static_fallback:
                        self._metrics["tasks_dynamically_routed"] = (
                            self._metrics.get("tasks_dynamically_routed", 0) + 1
                        )
                        logger.info(
                            f"Dynamic routing: {task.task_type} -> {decision.chosen_agent} "
                            f"(confidence: {decision.confidence:.2f})"
                        )
                    return decision.chosen_agent

            except Exception as e:
                logger.warning(f"Dynamic routing failed, falling back: {e}")

        # === PHASE 2: HEALTH-AWARE ROUTING ===
        # Use health-aware routing if enabled
        if self._health_routing_enabled and self._health_router:
            result = self._health_router.get_best_agent(task.task_type, self._subordinates)
            if result:
                agent_code, health_score = result
                # Track reroutes (when health score indicates fallback was used)
                if health_score < 1.0:
                    if static_route and static_route != agent_code:
                        self._metrics["tasks_rerouted"] += 1
                        logger.info(
                            f"Health-rerouted {task.task_type} from {static_route} to "
                            f"{agent_code} (health: {health_score:.2f})"
                        )
                return agent_code

        # === PHASE 2.5: PERSONALITY-AWARE SCORING ===
        if self._metacognition_service:
            candidates = [static_route] + FALLBACK_ROUTES.get(task.task_type, [])
            candidates = [c for c in candidates if c and c in self._subordinates]
            if len(candidates) > 1:
                candidates = self._filter_conflicting_agents(task, candidates)
                pick = self._personality_score_agents(task, candidates)
                if pick:
                    return pick

        # === PHASE 3: STATIC ROUTING ===
        # Fall back to standard routing rules
        if static_route and static_route in self._subordinates:
            return static_route

        # === PHASE 4: CAPABILITY-BASED ROUTING ===
        # Check which agents can handle this task
        capable_agents = [
            agent
            for agent in self._subordinates.values()
            if agent.can_handle(task) and agent.is_active
        ]

        if not capable_agents:
            return None

        if len(capable_agents) == 1:
            return capable_agents[0].code

        # === PHASE 5: LLM-BASED ROUTING ===
        # Use LLM to decide for ambiguous cases
        return await self.find_best_agent(task)

    async def _handle_directly(self, task: Task) -> TaskResult:
        """Handle a task directly when no agent can take it."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No agent available and no LLM for direct handling",
            )

        prompt = f"""You are the Overwatch (Overwatch) of an AI system.
No specialized agent is available for this task, so you must handle it directly.

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a helpful response or explain what would be needed to complete this task."""

        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(
                task_id=task.id,
                success=True,
                output=response,
                metrics={"handled_by": "CoS_DIRECT"},
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Direct handling failed: {e}",
            )

    async def _escalate_to_coo(self) -> None:
        """Escalate drift to external Nexus (Nexus) for strategic guidance."""
        self._metrics["escalations_to_coo"] += 1
        self._drift_monitor.mark_escalated()

        drift_summary = self._drift_monitor.get_drift_summary()
        logger.warning(f"Escalating to Nexus: {drift_summary}")

        # If Nexus bridge is connected, request updated context
        if self._nexus_bridge and self._nexus_bridge.is_connected:
            try:
                new_context = await self._nexus_bridge.request_strategic_guidance(drift_summary)
                if new_context:
                    self._drift_monitor.update_context(new_context)
                    logger.info("Received updated strategic context from Nexus")
            except Exception as e:
                logger.error(f"Failed to get Nexus guidance: {e}")

    async def execute_workflow(
        self,
        tasks: List[Task],
        parallel: bool = False,
    ) -> List[TaskResult]:
        """Execute multiple tasks as a workflow."""
        if parallel:
            results = await asyncio.gather(
                *[self.execute(task) for task in tasks],
                return_exceptions=True,
            )
            return [
                (
                    r
                    if isinstance(r, TaskResult)
                    else TaskResult(
                        task_id=tasks[i].id,
                        success=False,
                        error=str(r),
                    )
                )
                for i, r in enumerate(results)
            ]
        else:
            results = []
            for task in tasks:
                result = await self.execute(task)
                results.append(result)
                if not result.success and not task.metadata.get("optional"):
                    break
            return results

    async def broadcast_message(
        self,
        message: str,
        message_type: str = "announcement",
    ) -> None:
        """Broadcast a message to all agents."""
        agent_message = AgentMessage(
            sender=self.code,
            message_type=message_type,
            payload={"message": message},
        )
        await self.communicator.broadcast(agent_message)

    async def get_system_status(self) -> Dict[str, Any]:
        """Get status of the entire system."""
        uptime = (datetime.now() - self._metrics["start_time"]).total_seconds()

        agent_statuses = {}
        for code in self._subordinates:
            status = await self.communicator.get_agent_status(code)
            agent_statuses[code] = status

        return {
            "cos_status": "active",
            "codename": "Overwatch",
            "uptime_seconds": uptime,
            "metrics": self._metrics,
            "active_tasks": len(self._active_tasks),
            "completed_tasks": len(self._completed_tasks),
            "registered_agents": list(self._subordinates.keys()),
            "agent_statuses": agent_statuses,
            "drift_summary": self._drift_monitor.get_drift_summary(),
            "llm_connected": self.llm_provider.is_connected if self.llm_provider else False,
        }

    def register_subordinate(self, agent: Agent) -> None:
        """Register an agent and add to communicator."""
        super().register_subordinate(agent)
        if isinstance(self.communicator, LocalCommunicator):
            self.communicator.register_agent(agent)

    def get_metrics(self) -> Dict[str, Any]:
        """Get Overwatch performance metrics."""
        return {
            **self._metrics,
            "uptime_seconds": (datetime.now() - self._metrics["start_time"]).total_seconds(),
            "success_rate": (
                self._metrics["tasks_completed"] / max(1, self._metrics["tasks_received"])
            ),
        }

    def get_agent_health(self, agent_code: Optional[str] = None) -> Dict[str, Any]:
        """Get agent health status."""
        if not self._health_router:
            return {"health_routing_enabled": False}

        if agent_code:
            health = self._health_router.get_or_create_health(agent_code)
            return {
                "agent_code": agent_code,
                "is_healthy": health.is_healthy,
                "health_score": health.health_score,
                "success_rate": health.success_rate,
                "total_tasks": health.total_tasks,
                "consecutive_failures": health.consecutive_failures,
                "avg_latency_ms": health.avg_latency_ms,
                "circuit_breaker_open": health.circuit_breaker_open,
                "is_available": health.is_available,
                "last_error": health.last_error,
            }

        return {
            "health_routing_enabled": True,
            "agents": self._health_router.get_all_health(),
        }

    def get_drift_status(self) -> Dict[str, Any]:
        """Get current drift detection status."""
        return self._drift_monitor.get_drift_summary()

    def update_strategic_context(self, context: StrategicContext) -> None:
        """Update strategic context (typically from Nexus)."""
        self._drift_monitor.update_context(context)

    def get_cos_managers(self) -> Dict[str, Manager]:
        """Get Overwatch's internal managers."""
        return self._cos_managers

    def connect_smart_router(self, smart_router) -> None:
        """Connect a SmartRouter for learning-informed routing.

        When connected, _route_task will query the SmartRouter before
        falling back to static ROUTING_RULES.

        Args:
            smart_router: SmartRouter instance
        """
        self._smart_router = smart_router

    def _determine_target_agent(self, task: Task) -> Optional[str]:
        """Determine target agent for a task based on routing rules."""
        return ROUTING_RULES.get(task.task_type)

    # ==========================================================================
    # Health Routing Methods
    # ==========================================================================

    def reset_agent_health(self, agent_code: Optional[str] = None) -> bool:
        """
        Reset agent health status.

        Args:
            agent_code: Specific agent to reset, or None for all

        Returns:
            True if reset successful
        """
        if not self._health_router:
            return False

        self._health_router.reset_health(agent_code)
        logger.info(f"Reset health for {'all agents' if not agent_code else agent_code}")
        return True

    def add_fallback_route(self, task_type: str, fallbacks: List[str]) -> bool:
        """
        Add or update fallback routing for a task type.

        Args:
            task_type: Task type to add fallback for
            fallbacks: Ordered list of fallback agent codes

        Returns:
            True if added successfully
        """
        if not self._health_router:
            return False

        self._health_router.add_fallback_route(task_type, fallbacks)
        return True

    def set_health_routing_enabled(self, enabled: bool) -> None:
        """Enable or disable health-aware routing."""
        self._health_routing_enabled = enabled
        if enabled and not self._health_router:
            self._health_router = HealthAwareRouter()
        logger.info(f"Health routing {'enabled' if enabled else 'disabled'}")
