"""
Autonomous Agenda Engine - Main Orchestrator.

This module provides the main orchestration layer for:
1. Goal analysis - Decomposing goals into workstreams
2. Constraint detection - Finding obstacles blocking progress
3. Strategy generation - Creating plans to overcome obstacles
4. Agenda creation - Building prioritized, balanced agendas
5. Security assessment - Risk evaluation and HITL checkpoints

The AutonomousAgendaEngine is designed to integrate with the Nexus for
automated agenda-driven execution.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.agenda.models import (
    Agenda,
    AgendaItem,
    AuditEntry,
    Checkpoint,
    CheckpointType,
    ConfidenceLevel,
    HITLConfig,
    Obstacle,
    ObstacleType,
    RiskAssessment,
    RiskLevel,
    Strategy,
    StrategyType,
    Workstream,
    WorkstreamStatus,
)
from ag3ntwerk.agenda.goal_analyzer import GoalAnalyzer, AGENT_CAPABILITIES
from ag3ntwerk.agenda.constraint_detector import ConstraintDetector, ResourceThresholds
from ag3ntwerk.agenda.strategy_generator import StrategyGenerator
from ag3ntwerk.agenda.security import RiskAssessor, CheckpointManager, AuditLogger

logger = get_logger(__name__)


# =============================================================================
# Engine Configuration
# =============================================================================


@dataclass
class AgendaEngineConfig:
    """Configuration for the Autonomous Agenda Engine."""

    # Agenda generation settings
    default_period_hours: int = 24
    max_items_per_agenda: int = 50
    include_obstacle_resolution: bool = True
    max_obstacle_resolution_ratio: float = 0.3  # Max 30% for obstacle resolution

    # Balancing settings
    min_goals_coverage: float = 0.5  # Try to cover at least 50% of active goals
    max_agent_load_ratio: float = 0.4  # No exec should have >40% of items
    prefer_high_confidence: bool = True
    confidence_threshold: float = 0.5

    # Priority weights
    priority_weight_urgency: float = 0.3
    priority_weight_impact: float = 0.3
    priority_weight_confidence: float = 0.2
    priority_weight_dependencies: float = 0.2

    # HITL settings
    hitl_config: HITLConfig = field(default_factory=HITLConfig)

    # Resource thresholds
    resource_thresholds: ResourceThresholds = field(default_factory=ResourceThresholds)

    # Regeneration settings
    auto_regenerate_on_completion_ratio: float = 0.8  # Regenerate when 80% done
    stale_agenda_hours: int = 8  # Agenda is stale after 8 hours

    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_period_hours": self.default_period_hours,
            "max_items_per_agenda": self.max_items_per_agenda,
            "include_obstacle_resolution": self.include_obstacle_resolution,
            "max_obstacle_resolution_ratio": self.max_obstacle_resolution_ratio,
            "min_goals_coverage": self.min_goals_coverage,
            "max_agent_load_ratio": self.max_agent_load_ratio,
            "prefer_high_confidence": self.prefer_high_confidence,
            "confidence_threshold": self.confidence_threshold,
            "priority_weight_urgency": self.priority_weight_urgency,
            "priority_weight_impact": self.priority_weight_impact,
            "priority_weight_confidence": self.priority_weight_confidence,
            "priority_weight_dependencies": self.priority_weight_dependencies,
            "hitl_config": self.hitl_config.to_dict(),
            "auto_regenerate_on_completion_ratio": self.auto_regenerate_on_completion_ratio,
            "stale_agenda_hours": self.stale_agenda_hours,
        }


# =============================================================================
# Autonomous Agenda Engine
# =============================================================================


class AutonomousAgendaEngine:
    """
    Main orchestrator for autonomous agenda generation.

    The engine:
    1. Analyzes goals to create workstreams
    2. Detects obstacles blocking progress
    3. Generates strategies to overcome obstacles
    4. Creates balanced, prioritized agendas
    5. Assesses security and creates HITL checkpoints
    6. Adapts based on execution outcomes

    Example:
        engine = AutonomousAgendaEngine(
            app_state=state,
            config=AgendaEngineConfig(),
        )
        agenda = await engine.generate_agenda(period_hours=24)

        # Get items ready for execution
        items = engine.get_executable_items(count=5)

        # Adapt after execution
        await engine.adapt_agenda(execution_result)
    """

    def __init__(
        self,
        app_state=None,
        config: Optional[AgendaEngineConfig] = None,
        tool_registry=None,
        capability_evolver=None,
        failure_predictor=None,
        failure_investigator=None,
        issue_manager=None,
        priority_engine=None,
    ):
        """
        Initialize the Autonomous Agenda Engine.

        Args:
            app_state: Application state for goals and resources
            config: Engine configuration
            tool_registry: ToolRegistry for capability checking
            capability_evolver: CapabilityEvolver for gap detection
            failure_predictor: FailurePredictor for risk assessment
            failure_investigator: FailureInvestigator for root cause analysis
            issue_manager: IssueManager for remediation patterns
            priority_engine: PriorityEngine for scoring
        """
        self.app_state = app_state
        self.config = config or AgendaEngineConfig()

        # Initialize components
        self.goal_analyzer = GoalAnalyzer(
            tool_registry=tool_registry,
        )

        self.constraint_detector = ConstraintDetector(
            capability_evolver=capability_evolver,
            failure_predictor=failure_predictor,
            failure_investigator=failure_investigator,
            tool_registry=tool_registry,
            app_state=app_state,
            thresholds=self.config.resource_thresholds,
        )

        self.strategy_generator = StrategyGenerator(
            tool_registry=tool_registry,
            issue_manager=issue_manager,
            capability_evolver=capability_evolver,
        )

        self.risk_assessor = RiskAssessor(config=self.config.hitl_config)
        self.checkpoint_manager = CheckpointManager(
            config=self.config.hitl_config,
            risk_assessor=self.risk_assessor,
        )
        self.audit_logger = AuditLogger()

        self.priority_engine = priority_engine

        # State
        self._current_agenda: Optional[Agenda] = None
        self._workstreams: Dict[str, Workstream] = {}
        self._obstacles: Dict[str, Obstacle] = {}
        self._strategies: Dict[str, Strategy] = {}
        self._agenda_history: List[Agenda] = []

    # =========================================================================
    # Main Agenda Generation Pipeline
    # =========================================================================

    async def generate_agenda(
        self,
        period_hours: Optional[int] = None,
        goals: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Agenda:
        """
        Generate a complete agenda for the specified period.

        Pipeline:
        1. Phase 1: Goal Analysis -> Workstreams
        2. Phase 2: Constraint Detection -> Obstacles
        3. Phase 3: Strategy Generation -> Strategies
        4. Phase 4: Agenda Creation -> Prioritized Items
        5. Phase 5: Security Assessment -> Risk & Checkpoints

        Args:
            period_hours: Duration of agenda period
            goals: Optional list of goals (fetched from state if not provided)
            context: Execution context (resources, etc.)

        Returns:
            Complete Agenda object
        """
        period_hours = period_hours or self.config.default_period_hours
        context = context or await self._build_context()

        logger.info(f"Generating agenda for {period_hours} hour period")

        # Phase 1: Goal Analysis
        workstreams = await self._phase1_goal_analysis(goals)

        # Phase 2: Constraint Detection
        obstacles = await self._phase2_constraint_detection(workstreams, context)

        # Phase 3: Strategy Generation
        strategies = await self._phase3_strategy_generation(obstacles, workstreams, context)

        # Phase 4: Agenda Creation
        agenda = await self._phase4_agenda_creation(
            workstreams, obstacles, strategies, period_hours, context
        )

        # Phase 5: Security Assessment
        agenda = await self._phase5_security_assessment(agenda)

        # Store as current agenda
        self._current_agenda = agenda
        self._agenda_history.append(agenda)

        logger.info(
            f"Generated agenda with {len(agenda.items)} items, "
            f"{agenda.items_pending_approval} pending approval"
        )

        return agenda

    async def _phase1_goal_analysis(
        self,
        goals: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Workstream]:
        """
        Phase 1: Analyze goals and decompose into workstreams.

        Args:
            goals: List of goal dicts or None to fetch from state

        Returns:
            List of Workstream objects
        """
        logger.debug("Phase 1: Goal Analysis")

        # Get goals from state if not provided
        if goals is None:
            goals = await self._get_active_goals()

        if not goals:
            logger.warning("No active goals found")
            return []

        all_workstreams = []

        for goal in goals:
            # Skip completed goals
            if goal.get("status") == "completed":
                continue

            workstreams = await self.goal_analyzer.analyze_goal(goal)
            all_workstreams.extend(workstreams)

            # Store workstreams
            for ws in workstreams:
                self._workstreams[ws.id] = ws

        logger.info(f"Phase 1 complete: {len(all_workstreams)} workstreams from {len(goals)} goals")

        return all_workstreams

    async def _phase2_constraint_detection(
        self,
        workstreams: List[Workstream],
        context: Dict[str, Any],
    ) -> List[Obstacle]:
        """
        Phase 2: Detect obstacles blocking workstream progress.

        Args:
            workstreams: List of workstreams to analyze
            context: Execution context

        Returns:
            List of Obstacle objects
        """
        logger.debug("Phase 2: Constraint Detection")

        all_obstacles = []

        for ws in workstreams:
            obstacles = await self.constraint_detector.detect_obstacles(ws, context, workstreams)
            all_obstacles.extend(obstacles)

            # Store obstacles
            for obs in obstacles:
                self._obstacles[obs.id] = obs

            # Update workstream status if blocked
            if any(o.severity >= 0.8 for o in obstacles):
                ws.status = WorkstreamStatus.BLOCKED

        logger.info(f"Phase 2 complete: {len(all_obstacles)} obstacles detected")

        return all_obstacles

    async def _phase3_strategy_generation(
        self,
        obstacles: List[Obstacle],
        workstreams: List[Workstream],
        context: Dict[str, Any],
    ) -> Dict[str, List[Strategy]]:
        """
        Phase 3: Generate strategies for each obstacle.

        Args:
            obstacles: List of obstacles to address
            workstreams: List of workstreams
            context: Execution context

        Returns:
            Dict mapping obstacle_id to list of strategies
        """
        logger.debug("Phase 3: Strategy Generation")

        workstream_map = {ws.id: ws for ws in workstreams}
        all_strategies: Dict[str, List[Strategy]] = {}

        for obstacle in obstacles:
            ws = workstream_map.get(obstacle.workstream_id)
            if not ws:
                continue

            strategies = await self.strategy_generator.generate_strategies(obstacle, ws, context)
            all_strategies[obstacle.id] = strategies

            # Store strategies
            for strategy in strategies:
                self._strategies[strategy.id] = strategy

            # Update workstream with strategy IDs
            ws.strategy_ids.extend([s.id for s in strategies])

        total_strategies = sum(len(s) for s in all_strategies.values())
        logger.info(
            f"Phase 3 complete: {total_strategies} strategies for {len(obstacles)} obstacles"
        )

        return all_strategies

    async def _phase4_agenda_creation(
        self,
        workstreams: List[Workstream],
        obstacles: List[Obstacle],
        strategies: Dict[str, List[Strategy]],
        period_hours: int,
        context: Dict[str, Any],
    ) -> Agenda:
        """
        Phase 4: Create balanced, prioritized agenda.

        Args:
            workstreams: List of workstreams
            obstacles: List of obstacles
            strategies: Dict of strategies by obstacle
            period_hours: Agenda period duration
            context: Execution context

        Returns:
            Agenda with prioritized items
        """
        logger.debug("Phase 4: Agenda Creation")

        items = []

        # Create items from workstreams
        for ws in workstreams:
            workstream_items = self._create_items_from_workstream(ws)
            items.extend(workstream_items)

        # Create items from obstacle resolution strategies
        if self.config.include_obstacle_resolution:
            obstacle_items = self._create_items_from_strategies(obstacles, strategies)

            # Limit obstacle resolution items
            max_obstacle_items = int(
                self.config.max_items_per_agenda * self.config.max_obstacle_resolution_ratio
            )
            obstacle_items = obstacle_items[:max_obstacle_items]
            items.extend(obstacle_items)

        # Score and prioritize items
        items = self._score_and_prioritize(items, context)

        # Balance across goals and agents
        items = self._balance_agenda(items)

        # Limit total items
        items = items[: self.config.max_items_per_agenda]

        # Resolve dependencies (topological sort)
        items = self._resolve_dependencies(items)

        # Create agenda
        agenda = Agenda(
            period_start=datetime.now(),
            period_end=datetime.now() + timedelta(hours=period_hours),
            period_type="daily" if period_hours <= 24 else "weekly",
            items=items,
            status="active",
            generation_context=context,
        )

        # Update metrics
        agenda.update_metrics()

        logger.info(f"Phase 4 complete: {len(items)} agenda items created")

        return agenda

    async def _phase5_security_assessment(self, agenda: Agenda) -> Agenda:
        """
        Phase 5: Assess risks and create HITL checkpoints.

        Args:
            agenda: Agenda to assess

        Returns:
            Agenda with risk assessments and checkpoints
        """
        logger.debug("Phase 5: Security Assessment")

        for item in agenda.items:
            # Assess risk
            item.risk_assessment = self.risk_assessor.assess_agenda_item(item)

            # Check if checkpoint needed
            needs_checkpoint, checkpoint_type, reason = self.checkpoint_manager.should_checkpoint(
                item
            )

            if needs_checkpoint:
                item.checkpoint = self.checkpoint_manager.create_checkpoint(
                    item, checkpoint_type, reason
                )
                item.requires_approval = checkpoint_type == CheckpointType.APPROVAL
                item.approval_status = "pending" if item.requires_approval else "not_required"

                # Log checkpoint creation
                self.audit_logger.log_checkpoint_created(item.checkpoint)
            else:
                item.requires_approval = False
                item.approval_status = "not_required"

                # Log auto-execution eligibility
                if item.risk_assessment.risk_level in (RiskLevel.MINIMAL, RiskLevel.LOW):
                    self.audit_logger.log_auto_execution(item, "Low risk, no approval needed")

        # Update agenda pending approval count
        agenda.items_pending_approval = len(agenda.get_items_awaiting_approval())

        logger.info(f"Phase 5 complete: {agenda.items_pending_approval} items pending approval")

        return agenda

    # =========================================================================
    # Item Creation Helpers
    # =========================================================================

    def _create_items_from_workstream(
        self,
        workstream: Workstream,
    ) -> List[AgendaItem]:
        """Create agenda items from a workstream."""
        items = []

        # Create items based on task types
        for task_type, agent_code in workstream.executive_mapping.items():
            item = AgendaItem(
                goal_id=workstream.goal_id,
                workstream_id=workstream.id,
                milestone_id=workstream.milestone_id,
                task_type=task_type,
                title=f"{task_type.replace('_', ' ').title()}: {workstream.title[:50]}",
                description=(
                    f"Execute {task_type} task for workstream '{workstream.title}'.\n\n"
                    f"Objective: {workstream.objective}"
                ),
                context={
                    "workstream_id": workstream.id,
                    "goal_id": workstream.goal_id,
                    "milestone_id": workstream.milestone_id,
                },
                recommended_agent=agent_code,
                confidence_score=self._calculate_item_confidence(workstream, task_type),
                estimated_duration_minutes=15.0,
                estimated_cost_usd=0.5,
            )
            item.confidence_level = self._score_to_confidence_level(item.confidence_score)
            items.append(item)

        return items

    def _create_items_from_strategies(
        self,
        obstacles: List[Obstacle],
        strategies: Dict[str, List[Strategy]],
    ) -> List[AgendaItem]:
        """Create agenda items from obstacle resolution strategies."""
        items = []

        for obstacle in obstacles:
            obstacle_strategies = strategies.get(obstacle.id, [])
            if not obstacle_strategies:
                continue

            # Get the recommended strategy (highest priority)
            strategy = self.strategy_generator.get_recommended_strategy(obstacle_strategies)
            if not strategy:
                continue

            # Create item based on strategy type
            if strategy.strategy_type == StrategyType.TASK_GENERATION:
                # Create items for each generated task
                for task_spec in strategy.generated_task_specs:
                    item = AgendaItem(
                        goal_id=obstacle.goal_id,
                        workstream_id=obstacle.workstream_id,
                        milestone_id=obstacle.milestone_id,
                        strategy_id=strategy.id,
                        task_type=task_spec.get("task_type", "research"),
                        title=task_spec.get("title", strategy.title),
                        description=task_spec.get("description", strategy.description),
                        context=task_spec.get("context", {}),
                        recommended_agent=AGENT_CAPABILITIES.get(
                            task_spec.get("task_type", "research")
                        ),
                        confidence_score=strategy.confidence,
                        estimated_duration_minutes=strategy.estimated_effort_hours
                        * 60
                        / len(strategy.generated_task_specs),
                        estimated_cost_usd=strategy.estimated_cost_usd
                        / len(strategy.generated_task_specs),
                        is_obstacle_resolution=True,
                        resolves_obstacle_id=obstacle.id,
                    )
                    item.confidence_level = self._score_to_confidence_level(item.confidence_score)
                    items.append(item)
            else:
                # Create single item for strategy execution
                item = AgendaItem(
                    goal_id=obstacle.goal_id,
                    workstream_id=obstacle.workstream_id,
                    milestone_id=obstacle.milestone_id,
                    strategy_id=strategy.id,
                    task_type=self._strategy_type_to_task_type(strategy.strategy_type),
                    title=f"[Resolution] {strategy.title}",
                    description=(
                        f"{strategy.description}\n\n"
                        f"Strategy: {strategy.strategy_type.value}\n"
                        f"Obstacle: {obstacle.title}"
                    ),
                    context={
                        "strategy_id": strategy.id,
                        "obstacle_id": obstacle.id,
                        "strategy_type": strategy.strategy_type.value,
                    },
                    recommended_agent=self._get_strategy_executive(strategy),
                    confidence_score=strategy.confidence,
                    estimated_duration_minutes=strategy.estimated_effort_hours * 60,
                    estimated_cost_usd=strategy.estimated_cost_usd,
                    is_obstacle_resolution=True,
                    resolves_obstacle_id=obstacle.id,
                )
                item.confidence_level = self._score_to_confidence_level(item.confidence_score)
                items.append(item)

        return items

    def _strategy_type_to_task_type(self, strategy_type: StrategyType) -> str:
        """Map strategy type to a task type."""
        mapping = {
            StrategyType.INTERNAL_CHANGE: "architecture",
            StrategyType.TOOL_INGESTION: "infrastructure",
            StrategyType.GOAL_MODIFICATION: "strategic_analysis",
            StrategyType.TASK_GENERATION: "research",
        }
        return mapping.get(strategy_type, "research")

    def _get_strategy_executive(self, strategy: Strategy) -> str:
        """Get appropriate agent for strategy execution."""
        if strategy.strategy_type == StrategyType.INTERNAL_CHANGE:
            return "Forge"
        elif strategy.strategy_type == StrategyType.TOOL_INGESTION:
            return "Foundry"
        elif strategy.strategy_type == StrategyType.GOAL_MODIFICATION:
            return "Blueprint"
        else:
            return "Axiom"

    def _calculate_item_confidence(
        self,
        workstream: Workstream,
        task_type: str,
    ) -> float:
        """Calculate confidence score for an item."""
        base_confidence = 0.7

        # Check if capability is available
        for cap in workstream.capability_requirements:
            if cap.task_type == task_type:
                base_confidence = cap.availability_confidence
                break

        # Reduce confidence if workstream has obstacles
        if workstream.obstacle_ids:
            base_confidence *= 0.8

        return min(max(base_confidence, 0.0), 1.0)

    def _score_to_confidence_level(self, score: float) -> ConfidenceLevel:
        """Convert confidence score to level."""
        if score >= 0.8:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif score > 0:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.BLOCKED

    # =========================================================================
    # Prioritization and Balancing
    # =========================================================================

    def _score_and_prioritize(
        self,
        items: List[AgendaItem],
        context: Dict[str, Any],
    ) -> List[AgendaItem]:
        """Score and sort items by priority."""
        for item in items:
            item.priority_score = self._calculate_priority_score(item, context)

        # Sort by priority (highest first)
        items.sort(key=lambda i: i.priority_score, reverse=True)

        return items

    def _calculate_priority_score(
        self,
        item: AgendaItem,
        context: Dict[str, Any],
    ) -> float:
        """
        Calculate priority score using weighted factors.

        Factors:
        - Urgency: Based on goal/milestone deadlines
        - Impact: Based on obstacle resolution and workstream progress
        - Confidence: Preference for executable items
        - Dependencies: Boost items that unblock others
        """
        # Get weights from config
        w_urgency = self.config.priority_weight_urgency
        w_impact = self.config.priority_weight_impact
        w_confidence = self.config.priority_weight_confidence
        w_deps = self.config.priority_weight_dependencies

        # Urgency score (0-1)
        urgency = self._calculate_urgency(item, context)

        # Impact score (0-1)
        impact = 0.5
        if item.is_obstacle_resolution:
            # Obstacle resolution is high impact
            obstacle = self._obstacles.get(item.resolves_obstacle_id)
            if obstacle:
                impact = obstacle.severity
        else:
            # Regular work impact based on goal priority
            impact = 0.6

        # Confidence score
        confidence = item.confidence_score

        # Dependencies score (boost items that unblock others)
        deps_score = 0.5
        # Items without dependencies can start immediately
        if not item.dependencies:
            deps_score = 0.7

        # Calculate weighted score
        score = (
            w_urgency * urgency
            + w_impact * impact
            + w_confidence * confidence
            + w_deps * deps_score
        )

        # Boost high-confidence items if configured
        if self.config.prefer_high_confidence and item.confidence_level == ConfidenceLevel.HIGH:
            score *= 1.1

        return round(score, 3)

    def _calculate_urgency(
        self,
        item: AgendaItem,
        context: Dict[str, Any],
    ) -> float:
        """Calculate urgency based on deadlines."""
        # Default urgency
        urgency = 0.5

        # Check for goal deadline
        if item.goal_id and self.app_state:
            try:
                goals = context.get("goals", [])
                goal = next((g for g in goals if g.get("id") == item.goal_id), None)
                if goal:
                    # Higher urgency for lower progress
                    progress = goal.get("progress", 0)
                    urgency = 1.0 - (progress / 100)
            except Exception as e:
                logger.debug(
                    "Failed to calculate goal-based urgency for goal %s: %s", item.goal_id, e
                )

        # Obstacle resolution has higher urgency
        if item.is_obstacle_resolution:
            urgency = min(urgency + 0.2, 1.0)

        return urgency

    def _balance_agenda(self, items: List[AgendaItem]) -> List[AgendaItem]:
        """
        Balance agenda across goals and agents.

        Ensures:
        - Coverage across multiple goals
        - No agent is overloaded
        - Mix of regular work and obstacle resolution
        """
        balanced = []
        goal_counts: Dict[str, int] = {}
        exec_counts: Dict[str, int] = {}
        max_per_exec = int(self.config.max_items_per_agenda * self.config.max_agent_load_ratio)

        for item in items:
            # Check agent balance
            agent_code = item.recommended_agent or "unassigned"
            if exec_counts.get(agent_code, 0) >= max_per_exec:
                # Try alternative agents
                if item.alternative_executives:
                    for alt in item.alternative_executives:
                        if exec_counts.get(alt, 0) < max_per_exec:
                            item.recommended_agent = alt
                            agent_code = alt
                            break
                    else:
                        continue  # Skip if all alternatives are full
                else:
                    continue  # Skip this item

            # Add to balanced list
            balanced.append(item)
            exec_counts[agent_code] = exec_counts.get(agent_code, 0) + 1
            if item.goal_id:
                goal_counts[item.goal_id] = goal_counts.get(item.goal_id, 0) + 1

        return balanced

    def _resolve_dependencies(self, items: List[AgendaItem]) -> List[AgendaItem]:
        """Topologically sort items to respect dependencies."""
        # Build dependency graph
        item_map = {item.id: item for item in items}
        in_degree: Dict[str, int] = {item.id: 0 for item in items}

        for item in items:
            for dep_id in item.dependencies:
                if dep_id in item_map:
                    in_degree[item.id] += 1

        # Topological sort (Kahn's algorithm)
        queue = [item_id for item_id, degree in in_degree.items() if degree == 0]
        sorted_ids = []

        while queue:
            # Sort queue by priority to maintain priority order within same level
            queue.sort(key=lambda x: item_map[x].priority_score, reverse=True)
            item_id = queue.pop(0)
            sorted_ids.append(item_id)

            # Reduce in-degree of dependent items
            for item in items:
                if item_id in item.dependencies:
                    in_degree[item.id] -= 1
                    if in_degree[item.id] == 0:
                        queue.append(item.id)

        # Handle remaining items (cycles or no dependencies)
        remaining = [item.id for item in items if item.id not in sorted_ids]
        sorted_ids.extend(remaining)

        return [item_map[item_id] for item_id in sorted_ids]

    # =========================================================================
    # Item Access Methods
    # =========================================================================

    def get_executable_items(self, count: int = 5) -> List[AgendaItem]:
        """Get items ready for execution (approved or no approval needed)."""
        if not self._current_agenda:
            return []

        executable = self._current_agenda.get_executable_items()
        return executable[:count]

    def get_items_awaiting_approval(self) -> List[AgendaItem]:
        """Get items waiting for human approval."""
        if not self._current_agenda:
            return []

        return self._current_agenda.get_items_awaiting_approval()

    def get_next_items(self, count: int = 5) -> List[AgendaItem]:
        """Get next items to work on (ready or awaiting approval)."""
        if not self._current_agenda:
            return []

        # First get executable items
        items = self.get_executable_items(count)

        # If not enough, add awaiting approval items
        if len(items) < count:
            remaining = count - len(items)
            awaiting = self.get_items_awaiting_approval()[:remaining]
            items.extend(awaiting)

        return items

    # =========================================================================
    # Agenda Adaptation
    # =========================================================================

    async def adapt_agenda(self, execution_result: Dict[str, Any]) -> None:
        """
        Adapt agenda based on execution outcome.

        Updates:
        - Item status
        - Workstream progress
        - Obstacle resolution status
        - Regenerates if needed

        Args:
            execution_result: Result from task execution with format:
                {
                    "item_id": str,
                    "status": "completed" | "failed" | "skipped",
                    "result": {...},
                    "error": Optional[str],
                }
        """
        item_id = execution_result.get("item_id")
        status = execution_result.get("status", "completed")

        if not self._current_agenda or not item_id:
            return

        # Find and update item
        item = next((i for i in self._current_agenda.items if i.id == item_id), None)

        if not item:
            logger.warning(f"Item {item_id} not found in current agenda")
            return

        # Update item status
        item.status = status
        if status == "completed":
            item.completed_at = datetime.now()

        item.execution_result = execution_result.get("result")

        # Update workstream progress
        if item.workstream_id:
            ws = self._workstreams.get(item.workstream_id)
            if ws:
                if status == "completed":
                    ws.completed_task_ids.append(item_id)
                    ws.progress = min(
                        100, (len(ws.completed_task_ids) / max(ws.estimated_task_count, 1)) * 100
                    )
                elif status == "failed":
                    ws.failed_task_ids.append(item_id)

        # Update obstacle status if resolved
        if item.is_obstacle_resolution and item.resolves_obstacle_id:
            obstacle = self._obstacles.get(item.resolves_obstacle_id)
            if obstacle and status == "completed":
                obstacle.status = "resolved"
                obstacle.resolved_at = datetime.now()
                obstacle.resolution_strategy_id = item.strategy_id

        # Update agenda metrics
        self._current_agenda.update_metrics()

        # Check if regeneration needed
        if self._should_regenerate():
            logger.info("Agenda completion threshold reached, regenerating")
            await self.generate_agenda()

    def _should_regenerate(self) -> bool:
        """Check if agenda should be regenerated."""
        if not self._current_agenda:
            return True

        # Check completion ratio
        total = len(self._current_agenda.items)
        if total == 0:
            return True

        completed = self._current_agenda.items_completed
        completion_ratio = completed / total

        if completion_ratio >= self.config.auto_regenerate_on_completion_ratio:
            return True

        # Check staleness
        age = datetime.now() - self._current_agenda.generated_at
        if age > timedelta(hours=self.config.stale_agenda_hours):
            return True

        return False

    # =========================================================================
    # Nexus Integration
    # =========================================================================

    def feed_to_coo_context(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enrich Nexus context with agenda data.

        Adds:
        - Current agenda summary
        - Next items to execute
        - Pending approvals
        - Obstacle status

        Args:
            context: Nexus observation context

        Returns:
            Enriched context
        """
        agenda_data = {}

        if self._current_agenda:
            agenda_data["current_agenda"] = {
                "id": self._current_agenda.id,
                "status": self._current_agenda.status,
                "total_items": len(self._current_agenda.items),
                "completed": self._current_agenda.items_completed,
                "pending_approval": self._current_agenda.items_pending_approval,
                "goals_covered": len(self._current_agenda.goals_addressed),
                "obstacles_addressed": len(self._current_agenda.obstacles_addressed),
            }

            # Add next items summary
            next_items = self.get_next_items(5)
            agenda_data["next_items"] = [
                {
                    "id": item.id,
                    "title": item.title,
                    "task_type": item.task_type,
                    "agent": item.recommended_agent,
                    "requires_approval": item.requires_approval,
                    "confidence": item.confidence_level.value,
                }
                for item in next_items
            ]

        # Add obstacle summary
        active_obstacles = [o for o in self._obstacles.values() if o.status == "active"]
        agenda_data["active_obstacles"] = len(active_obstacles)
        agenda_data["blocking_obstacles"] = len([o for o in active_obstacles if o.severity >= 0.8])

        context["agenda"] = agenda_data
        return context

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _build_context(self) -> Dict[str, Any]:
        """Build execution context from app state."""
        context = {
            "resources": {},
            "goals": [],
        }

        if self.app_state:
            try:
                # Get resource info
                if hasattr(self.app_state, "get_resources"):
                    context["resources"] = await self.app_state.get_resources()
                elif hasattr(self.app_state, "resources"):
                    context["resources"] = self.app_state.resources

                # Get goals
                if hasattr(self.app_state, "list_goals"):
                    goals = await self.app_state.list_goals()
                    context["goals"] = goals if isinstance(goals, list) else []
                elif hasattr(self.app_state, "goals"):
                    context["goals"] = list(self.app_state.goals.values())

            except Exception as e:
                logger.warning(f"Error building context from app_state: {e}")

        return context

    async def _get_active_goals(self) -> List[Dict[str, Any]]:
        """Get active goals from app state."""
        if not self.app_state:
            return []

        try:
            if hasattr(self.app_state, "list_goals"):
                goals = await self.app_state.list_goals()
                return [g for g in goals if g.get("status") != "completed"]
            elif hasattr(self.app_state, "goals"):
                return [g for g in self.app_state.goals.values() if g.get("status") != "completed"]
        except Exception as e:
            logger.warning(f"Error getting goals: {e}")

        return []

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_current_agenda(self) -> Optional[Agenda]:
        """Get the current active agenda."""
        return self._current_agenda

    def get_workstream(self, workstream_id: str) -> Optional[Workstream]:
        """Get a workstream by ID."""
        return self._workstreams.get(workstream_id)

    def get_obstacle(self, obstacle_id: str) -> Optional[Obstacle]:
        """Get an obstacle by ID."""
        return self._obstacles.get(obstacle_id)

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get a strategy by ID."""
        return self._strategies.get(strategy_id)

    def get_workstream_progress(self, workstream_id: str) -> float:
        """Get progress percentage for a workstream."""
        ws = self._workstreams.get(workstream_id)
        return ws.progress if ws else 0.0

    def list_workstreams(
        self,
        goal_id: Optional[str] = None,
    ) -> List[Workstream]:
        """List workstreams, optionally filtered by goal."""
        workstreams = list(self._workstreams.values())
        if goal_id:
            workstreams = [ws for ws in workstreams if ws.goal_id == goal_id]
        return workstreams

    def list_obstacles(
        self,
        goal_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Obstacle]:
        """List obstacles, optionally filtered."""
        obstacles = list(self._obstacles.values())
        if goal_id:
            obstacles = [o for o in obstacles if o.goal_id == goal_id]
        if status:
            obstacles = [o for o in obstacles if o.status == status]
        return obstacles

    def list_strategies(
        self,
        obstacle_id: Optional[str] = None,
    ) -> List[Strategy]:
        """List strategies, optionally filtered by obstacle."""
        strategies = list(self._strategies.values())
        if obstacle_id:
            strategies = [s for s in strategies if s.obstacle_id == obstacle_id]
        return strategies

    # =========================================================================
    # Approval Management
    # =========================================================================

    def approve_item(self, item_id: str, approver: str, notes: str = "") -> bool:
        """Approve an agenda item."""
        if not self._current_agenda:
            return False

        item = next((i for i in self._current_agenda.items if i.id == item_id), None)

        if not item or not item.checkpoint:
            return False

        # Approve the checkpoint
        success = self.checkpoint_manager.approve(item.checkpoint.id, approver, notes)

        if success:
            item.approval_status = "approved"
            item.approved_by = approver
            item.approved_at = datetime.now()

            # Log approval
            self.audit_logger.log_approval(item.checkpoint, approver)

            # Update agenda metrics
            self._current_agenda.update_metrics()

        return success

    def reject_item(self, item_id: str, approver: str, reason: str) -> bool:
        """Reject an agenda item."""
        if not self._current_agenda:
            return False

        item = next((i for i in self._current_agenda.items if i.id == item_id), None)

        if not item or not item.checkpoint:
            return False

        # Reject the checkpoint
        success = self.checkpoint_manager.reject(item.checkpoint.id, approver, reason)

        if success:
            item.approval_status = "rejected"
            item.status = "skipped"

            # Log rejection
            self.audit_logger.log_rejection(item.checkpoint, approver, reason)

            # Update agenda metrics
            self._current_agenda.update_metrics()

        return success

    def batch_approve(self, item_ids: List[str], approver: str) -> int:
        """Batch approve multiple items."""
        count = 0
        for item_id in item_ids:
            if self.approve_item(item_id, approver):
                count += 1
        return count

    # =========================================================================
    # Audit and Reporting
    # =========================================================================

    def get_audit_trail(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditEntry]:
        """Get audit trail for the specified period."""
        return self.audit_logger.get_audit_trail(start_time, end_time)

    def get_audit_summary(self) -> Dict[str, Any]:
        """Get summary of audit trail."""
        return self.audit_logger.get_summary()

    def get_engine_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        return {
            "has_agenda": self._current_agenda is not None,
            "agenda_id": self._current_agenda.id if self._current_agenda else None,
            "total_workstreams": len(self._workstreams),
            "total_obstacles": len(self._obstacles),
            "active_obstacles": len([o for o in self._obstacles.values() if o.status == "active"]),
            "total_strategies": len(self._strategies),
            "pending_approvals": len(self.checkpoint_manager.get_pending_checkpoints()),
            "config": self.config.to_dict(),
        }
