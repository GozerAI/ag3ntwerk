"""
Constraint Detector for the Autonomous Agenda Engine.

This module detects obstacles and constraints blocking goal progress by:
1. Detecting capability gaps (missing tools/skills)
2. Detecting resource constraints (budget, time, concurrency)
3. Detecting dependencies (blocked by other work)
4. Detecting failure patterns (repeated failures)
5. Detecting missing integrations (external services)

The ConstraintDetector integrates with:
- CapabilityEvolver for capability gap detection
- FailurePredictor for risk assessment
- FailureInvestigator for failure patterns
- ToolRegistry for missing tools
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.agenda.models import (
    CapabilityRequirement,
    Obstacle,
    ObstacleType,
    Workstream,
)

logger = get_logger(__name__)


# =============================================================================
# Resource Thresholds
# =============================================================================


@dataclass
class ResourceThresholds:
    """Thresholds for detecting resource constraints."""

    min_budget_usd: float = 10.0  # Minimum budget to proceed
    max_concurrent_tasks: int = 5  # Maximum concurrent tasks
    max_queue_depth: int = 50  # Maximum queue depth before constraint
    min_executive_availability: float = 0.2  # Minimum agent availability (0-1)
    max_failure_rate: float = 0.3  # Maximum failure rate before concern


# =============================================================================
# Constraint Detector
# =============================================================================


class ConstraintDetector:
    """
    Detects constraints and obstacles blocking goal progress.

    The detector identifies various types of obstacles:
    - Capability gaps: Missing tools or skills
    - Resource constraints: Budget, time, concurrency limits
    - Dependencies: Work blocked by other tasks
    - Failure patterns: Repeated failures on similar tasks
    - Missing integrations: External services not configured

    Example:
        detector = ConstraintDetector(
            capability_evolver=evolver,
            failure_predictor=predictor,
            tool_registry=registry,
        )
        obstacles = await detector.detect_obstacles(workstream, context)
    """

    def __init__(
        self,
        capability_evolver=None,
        failure_predictor=None,
        failure_investigator=None,
        tool_registry=None,
        app_state=None,
        thresholds: Optional[ResourceThresholds] = None,
    ):
        """
        Initialize the constraint detector.

        Args:
            capability_evolver: CapabilityEvolver for gap detection
            failure_predictor: FailurePredictor for risk assessment
            failure_investigator: FailureInvestigator for root cause analysis
            tool_registry: ToolRegistry for tool availability
            app_state: AppState for resource constraints
            thresholds: Custom resource thresholds
        """
        self.capability_evolver = capability_evolver
        self.failure_predictor = failure_predictor
        self.failure_investigator = failure_investigator
        self.tool_registry = tool_registry
        self.app_state = app_state
        self.thresholds = thresholds or ResourceThresholds()

    async def detect_obstacles(
        self,
        workstream: Workstream,
        context: Optional[Dict[str, Any]] = None,
        all_workstreams: Optional[List[Workstream]] = None,
    ) -> List[Obstacle]:
        """
        Detect all obstacles for a workstream.

        Args:
            workstream: The workstream to analyze
            context: Current execution context with resources info
            all_workstreams: All workstreams for dependency analysis

        Returns:
            List of detected Obstacle objects
        """
        context = context or {}
        all_workstreams = all_workstreams or []
        obstacles = []

        # Run all detection methods
        obstacles.extend(await self._detect_capability_gaps(workstream))
        obstacles.extend(await self._detect_resource_constraints(workstream, context))
        obstacles.extend(await self._detect_dependencies(workstream, all_workstreams))
        obstacles.extend(await self._detect_failure_patterns(workstream))
        obstacles.extend(await self._detect_missing_integrations(workstream))
        obstacles.extend(await self._detect_knowledge_gaps(workstream, context))

        # Sort by severity (highest first)
        obstacles.sort(key=lambda o: o.severity, reverse=True)

        # Update workstream with obstacle IDs
        workstream.obstacle_ids = [o.id for o in obstacles]

        logger.info(f"Detected {len(obstacles)} obstacles for workstream '{workstream.title}'")

        return obstacles

    async def _detect_capability_gaps(
        self,
        workstream: Workstream,
    ) -> List[Obstacle]:
        """Find missing capabilities for workstream requirements."""
        obstacles = []

        for requirement in workstream.capability_requirements:
            if not requirement.is_available:
                # Create obstacle for missing capability
                obstacle = Obstacle(
                    obstacle_type=ObstacleType.CAPABILITY_GAP,
                    severity=self._calculate_capability_gap_severity(requirement),
                    goal_id=workstream.goal_id,
                    milestone_id=workstream.milestone_id,
                    workstream_id=workstream.id,
                    title=f"Missing capability: {requirement.name}",
                    description=(
                        f"The workstream '{workstream.title}' requires "
                        f"{requirement.name} capability which is not available. "
                        f"Task type: {requirement.task_type}"
                    ),
                    evidence=[
                        f"Required task type: {requirement.task_type}",
                        f"Availability confidence: {requirement.availability_confidence:.0%}",
                        f"Inferred from: {requirement.inferred_from}",
                    ],
                    detected_by="constraint_detector.capability_gaps",
                    related_task_types=[requirement.task_type],
                )
                obstacles.append(obstacle)

        # Also check with CapabilityEvolver if available
        if self.capability_evolver:
            try:
                detected_gaps = await self._get_evolver_gaps(workstream)
                for gap in detected_gaps:
                    if not any(o.title == gap.get("title") for o in obstacles):
                        obstacle = Obstacle(
                            obstacle_type=ObstacleType.CAPABILITY_GAP,
                            severity=gap.get("severity", 0.5),
                            goal_id=workstream.goal_id,
                            milestone_id=workstream.milestone_id,
                            workstream_id=workstream.id,
                            title=gap.get("title", "Capability gap"),
                            description=gap.get("description", ""),
                            evidence=gap.get("evidence", []),
                            detected_by="capability_evolver",
                            related_task_types=gap.get("task_types", []),
                        )
                        obstacles.append(obstacle)
            except Exception as e:
                logger.warning(f"Failed to get capability evolver gaps: {e}")

        return obstacles

    async def _get_evolver_gaps(
        self,
        workstream: Workstream,
    ) -> List[Dict[str, Any]]:
        """Get gaps from CapabilityEvolver for workstream task types."""
        gaps = []

        if not self.capability_evolver:
            return gaps

        # Get task types from workstream
        task_types = list(workstream.executive_mapping.keys())

        try:
            # Try to get detected gaps from evolver
            if hasattr(self.capability_evolver, "get_detected_gaps"):
                all_gaps = self.capability_evolver.get_detected_gaps()
                for gap in all_gaps:
                    if gap.get("task_type") in task_types:
                        gaps.append(
                            {
                                "title": f"Performance gap: {gap.get('task_type')}",
                                "description": gap.get("description", ""),
                                "severity": gap.get("severity", 0.5),
                                "evidence": gap.get("evidence", []),
                                "task_types": [gap.get("task_type")],
                            }
                        )
        except Exception as e:
            logger.warning(f"Error getting evolver gaps: {e}")

        return gaps

    def _calculate_capability_gap_severity(
        self,
        requirement: CapabilityRequirement,
    ) -> float:
        """Calculate severity of a capability gap."""
        base_severity = 0.5

        # Lower confidence = higher severity
        base_severity += (1.0 - requirement.availability_confidence) * 0.3

        # No alternatives = higher severity
        if not requirement.alternative_approaches:
            base_severity += 0.2

        return min(base_severity, 1.0)

    async def _detect_resource_constraints(
        self,
        workstream: Workstream,
        context: Dict[str, Any],
    ) -> List[Obstacle]:
        """Check budget, concurrency, time constraints."""
        obstacles = []

        # Get resources from context
        resources = context.get("resources", {})

        # Check budget
        budget_remaining = resources.get("daily_budget_remaining", float("inf"))
        if budget_remaining < self.thresholds.min_budget_usd:
            obstacles.append(
                Obstacle(
                    obstacle_type=ObstacleType.RESOURCE_CONSTRAINT,
                    severity=0.8 if budget_remaining <= 0 else 0.5,
                    goal_id=workstream.goal_id,
                    milestone_id=workstream.milestone_id,
                    workstream_id=workstream.id,
                    title="Budget constraint",
                    description=(
                        f"Daily budget remaining (${budget_remaining:.2f}) is below "
                        f"minimum threshold (${self.thresholds.min_budget_usd:.2f})"
                    ),
                    evidence=[
                        f"Budget remaining: ${budget_remaining:.2f}",
                        f"Minimum required: ${self.thresholds.min_budget_usd:.2f}",
                    ],
                    detected_by="constraint_detector.resource_constraints",
                )
            )

        # Check concurrent slots
        concurrent_available = resources.get("concurrent_slots_available", float("inf"))
        if concurrent_available <= 0:
            obstacles.append(
                Obstacle(
                    obstacle_type=ObstacleType.RESOURCE_CONSTRAINT,
                    severity=0.6,
                    goal_id=workstream.goal_id,
                    milestone_id=workstream.milestone_id,
                    workstream_id=workstream.id,
                    title="Concurrency limit reached",
                    description=(
                        f"No concurrent execution slots available. "
                        f"Maximum concurrent tasks: {self.thresholds.max_concurrent_tasks}"
                    ),
                    evidence=[
                        f"Slots available: {concurrent_available}",
                        f"Maximum: {self.thresholds.max_concurrent_tasks}",
                    ],
                    detected_by="constraint_detector.resource_constraints",
                )
            )

        # Check queue depth
        queue_depth = resources.get("queue_depth", 0)
        if queue_depth > self.thresholds.max_queue_depth:
            obstacles.append(
                Obstacle(
                    obstacle_type=ObstacleType.RESOURCE_CONSTRAINT,
                    severity=0.4,
                    goal_id=workstream.goal_id,
                    milestone_id=workstream.milestone_id,
                    workstream_id=workstream.id,
                    title="High queue depth",
                    description=(
                        f"Task queue depth ({queue_depth}) exceeds threshold "
                        f"({self.thresholds.max_queue_depth}). Processing may be delayed."
                    ),
                    evidence=[
                        f"Current queue depth: {queue_depth}",
                        f"Threshold: {self.thresholds.max_queue_depth}",
                    ],
                    detected_by="constraint_detector.resource_constraints",
                )
            )

        # Check agent availability
        for agent_code in workstream.executive_mapping.values():
            exec_availability = resources.get("executive_availability", {}).get(agent_code, 1.0)
            if exec_availability < self.thresholds.min_executive_availability:
                obstacles.append(
                    Obstacle(
                        obstacle_type=ObstacleType.RESOURCE_CONSTRAINT,
                        severity=0.5,
                        goal_id=workstream.goal_id,
                        milestone_id=workstream.milestone_id,
                        workstream_id=workstream.id,
                        title=f"Agent {agent_code} availability low",
                        description=(
                            f"Agent {agent_code} availability ({exec_availability:.0%}) "
                            f"is below minimum threshold ({self.thresholds.min_executive_availability:.0%})"
                        ),
                        evidence=[
                            f"Agent: {agent_code}",
                            f"Availability: {exec_availability:.0%}",
                            f"Minimum required: {self.thresholds.min_executive_availability:.0%}",
                        ],
                        detected_by="constraint_detector.resource_constraints",
                    )
                )

        return obstacles

    async def _detect_dependencies(
        self,
        workstream: Workstream,
        all_workstreams: List[Workstream],
    ) -> List[Obstacle]:
        """Find blocking dependencies on other work."""
        obstacles = []

        # Check explicit dependencies
        for dep_id in workstream.dependency_workstream_ids:
            dep_ws = next((ws for ws in all_workstreams if ws.id == dep_id), None)
            if dep_ws and dep_ws.status.value not in ("completed", "cancelled"):
                obstacles.append(
                    Obstacle(
                        obstacle_type=ObstacleType.DEPENDENCY,
                        severity=self._calculate_dependency_severity(dep_ws),
                        goal_id=workstream.goal_id,
                        milestone_id=workstream.milestone_id,
                        workstream_id=workstream.id,
                        title=f"Blocked by: {dep_ws.title}",
                        description=(
                            f"This workstream depends on '{dep_ws.title}' which is "
                            f"currently {dep_ws.status.value}. Progress: {dep_ws.progress:.0f}%"
                        ),
                        evidence=[
                            f"Dependency workstream: {dep_ws.id}",
                            f"Dependency status: {dep_ws.status.value}",
                            f"Dependency progress: {dep_ws.progress:.0f}%",
                        ],
                        detected_by="constraint_detector.dependencies",
                    )
                )

        # Check for implicit dependencies (same agent overloaded)
        for agent_code, task_types in workstream.executive_mapping.items():
            # Count how many other active workstreams need this agent
            competing_count = sum(
                1
                for ws in all_workstreams
                if ws.id != workstream.id
                and ws.status.value == "active"
                and agent_code in ws.executive_mapping.values()
            )

            if competing_count >= 3:  # Threshold for competition concern
                obstacles.append(
                    Obstacle(
                        obstacle_type=ObstacleType.DEPENDENCY,
                        severity=0.3,
                        goal_id=workstream.goal_id,
                        milestone_id=workstream.milestone_id,
                        workstream_id=workstream.id,
                        title=f"Agent {agent_code} has competing work",
                        description=(
                            f"Agent {agent_code} is needed by {competing_count} other "
                            f"active workstreams, which may cause delays."
                        ),
                        evidence=[
                            f"Agent: {agent_code}",
                            f"Competing workstreams: {competing_count}",
                        ],
                        detected_by="constraint_detector.dependencies",
                    )
                )

        return obstacles

    def _calculate_dependency_severity(self, dependency: Workstream) -> float:
        """Calculate severity based on dependency status."""
        if dependency.status.value == "blocked":
            return 0.9  # Very severe - dependency is also blocked
        elif dependency.status.value == "pending":
            return 0.7  # High - dependency hasn't started
        elif dependency.status.value == "active":
            # Severity decreases as progress increases
            return 0.6 * (1.0 - dependency.progress / 100.0)
        elif dependency.status.value == "deferred":
            return 0.8  # High - dependency is postponed
        return 0.5

    async def _detect_failure_patterns(
        self,
        workstream: Workstream,
    ) -> List[Obstacle]:
        """Check for historical failure patterns that may block progress."""
        obstacles = []
        task_types = list(workstream.executive_mapping.keys())

        # Use FailurePredictor if available
        if self.failure_predictor:
            for task_type in task_types:
                try:
                    risk = await self._predict_failure_risk(task_type)
                    if risk and risk.get("risk_level") in ("high", "critical"):
                        obstacles.append(
                            Obstacle(
                                obstacle_type=ObstacleType.FAILURE_PATTERN,
                                severity=risk.get("risk_score", 0.7),
                                goal_id=workstream.goal_id,
                                milestone_id=workstream.milestone_id,
                                workstream_id=workstream.id,
                                title=f"High failure risk for {task_type}",
                                description=(
                                    f"Historical data indicates {risk.get('risk_level')} "
                                    f"failure risk for {task_type} tasks. "
                                    f"Common issues: {', '.join(risk.get('common_issues', []))}"
                                ),
                                evidence=risk.get("evidence", []),
                                detected_by="failure_predictor",
                                related_task_types=[task_type],
                                related_failures=risk.get("related_failure_ids", []),
                            )
                        )
                except Exception as e:
                    logger.warning(f"Failed to predict failure risk for {task_type}: {e}")

        # Use FailureInvestigator if available
        if self.failure_investigator:
            for task_type in task_types:
                try:
                    root_causes = await self._get_common_root_causes(task_type)
                    if root_causes:
                        # Check if any root cause is unresolved
                        unresolved = [rc for rc in root_causes if not rc.get("resolved")]
                        if unresolved:
                            obstacles.append(
                                Obstacle(
                                    obstacle_type=ObstacleType.FAILURE_PATTERN,
                                    severity=0.6,
                                    goal_id=workstream.goal_id,
                                    milestone_id=workstream.milestone_id,
                                    workstream_id=workstream.id,
                                    title=f"Unresolved failure patterns for {task_type}",
                                    description=(
                                        f"There are {len(unresolved)} unresolved failure patterns "
                                        f"for {task_type} tasks that may cause issues."
                                    ),
                                    evidence=[
                                        f"Root cause: {rc.get('type')}: {rc.get('description')}"
                                        for rc in unresolved[:3]
                                    ],
                                    detected_by="failure_investigator",
                                    related_task_types=[task_type],
                                )
                            )
                except Exception as e:
                    logger.warning(f"Failed to get root causes for {task_type}: {e}")

        return obstacles

    async def _predict_failure_risk(
        self,
        task_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Get failure risk prediction for a task type."""
        if not self.failure_predictor:
            return None

        try:
            if hasattr(self.failure_predictor, "predict_failure_risk"):
                return await self.failure_predictor.predict_failure_risk(task_type=task_type)
        except Exception as e:
            logger.warning(f"Failure prediction error: {e}")

        return None

    async def _get_common_root_causes(
        self,
        task_type: str,
    ) -> List[Dict[str, Any]]:
        """Get common root causes for a task type."""
        if not self.failure_investigator:
            return []

        try:
            if hasattr(self.failure_investigator, "get_common_root_causes"):
                return self.failure_investigator.get_common_root_causes(task_type=task_type)
        except Exception as e:
            logger.warning(f"Root cause query error: {e}")

        return []

    async def _detect_missing_integrations(
        self,
        workstream: Workstream,
    ) -> List[Obstacle]:
        """Check for missing external integrations."""
        obstacles = []

        if not self.tool_registry:
            return obstacles

        # Get required tool categories from workstream
        required_categories: Set[str] = set()
        for requirement in workstream.capability_requirements:
            if requirement.tool_category:
                required_categories.add(requirement.tool_category)

        # Check each category
        for category in required_categories:
            try:
                # Check if tools are available for this category
                available_tools = self._get_tools_for_category(category)
                if not available_tools:
                    obstacles.append(
                        Obstacle(
                            obstacle_type=ObstacleType.INTEGRATION_MISSING,
                            severity=0.6,
                            goal_id=workstream.goal_id,
                            milestone_id=workstream.milestone_id,
                            workstream_id=workstream.id,
                            title=f"No tools available for {category}",
                            description=(
                                f"The workstream requires {category} tools but none "
                                f"are currently configured or available."
                            ),
                            evidence=[
                                f"Required category: {category}",
                                "No matching tools found in registry",
                            ],
                            detected_by="constraint_detector.missing_integrations",
                        )
                    )
            except Exception as e:
                logger.warning(f"Failed to check tools for {category}: {e}")

        return obstacles

    def _get_tools_for_category(self, category: str) -> List[Any]:
        """Get available tools for a category."""
        if not self.tool_registry:
            return []

        try:
            if hasattr(self.tool_registry, "get_by_category"):
                return self.tool_registry.get_by_category(category)
            elif hasattr(self.tool_registry, "find_tools_for_task"):
                return self.tool_registry.find_tools_for_task(category)
        except Exception as e:
            logger.debug("Failed to retrieve tools for category '%s': %s", category, e)

        return []

    async def _detect_knowledge_gaps(
        self,
        workstream: Workstream,
        context: Dict[str, Any],
    ) -> List[Obstacle]:
        """Detect missing data or context needed for the workstream."""
        obstacles = []

        # Check if context has required information
        required_context_keys = self._infer_required_context(workstream)

        for key in required_context_keys:
            if key not in context:
                obstacles.append(
                    Obstacle(
                        obstacle_type=ObstacleType.KNOWLEDGE_GAP,
                        severity=0.4,
                        goal_id=workstream.goal_id,
                        milestone_id=workstream.milestone_id,
                        workstream_id=workstream.id,
                        title=f"Missing context: {key}",
                        description=(
                            f"The workstream may require {key} information which "
                            f"is not present in the current context."
                        ),
                        evidence=[
                            f"Required context key: {key}",
                            "Not found in provided context",
                        ],
                        detected_by="constraint_detector.knowledge_gaps",
                    )
                )

        return obstacles

    def _infer_required_context(self, workstream: Workstream) -> List[str]:
        """Infer what context information a workstream might need."""
        required = []
        text_lower = f"{workstream.title} {workstream.description}".lower()

        # Common context requirements
        context_hints = {
            "user": ["user", "customer", "client", "account"],
            "api_credentials": ["api", "integration", "connect", "authenticate"],
            "database": ["database", "data", "query", "records"],
            "configuration": ["config", "settings", "parameters", "options"],
            "metrics": ["metrics", "analytics", "performance", "measure"],
        }

        for key, keywords in context_hints.items():
            if any(kw in text_lower for kw in keywords):
                required.append(key)

        return required

    async def detect_obstacles_for_multiple(
        self,
        workstreams: List[Workstream],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Obstacle]]:
        """
        Detect obstacles for multiple workstreams.

        Args:
            workstreams: List of workstreams to analyze
            context: Shared execution context

        Returns:
            Dict mapping workstream_id to list of obstacles
        """
        result = {}
        for ws in workstreams:
            obstacles = await self.detect_obstacles(ws, context, workstreams)
            result[ws.id] = obstacles
        return result

    def get_obstacle_summary(
        self,
        obstacles: List[Obstacle],
    ) -> Dict[str, Any]:
        """Get summary statistics for detected obstacles."""
        if not obstacles:
            return {
                "total": 0,
                "by_type": {},
                "by_severity": {"high": 0, "medium": 0, "low": 0},
                "blocking_count": 0,
            }

        by_type: Dict[str, int] = {}
        for o in obstacles:
            type_name = o.obstacle_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        by_severity = {
            "high": len([o for o in obstacles if o.severity >= 0.7]),
            "medium": len([o for o in obstacles if 0.4 <= o.severity < 0.7]),
            "low": len([o for o in obstacles if o.severity < 0.4]),
        }

        return {
            "total": len(obstacles),
            "by_type": by_type,
            "by_severity": by_severity,
            "blocking_count": len([o for o in obstacles if o.severity >= 0.7]),
            "avg_severity": sum(o.severity for o in obstacles) / len(obstacles),
        }
