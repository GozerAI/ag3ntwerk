"""
Strategy Generator for the Autonomous Agenda Engine.

This module generates strategies to overcome detected obstacles by:
1. Internal changes - Adjust routing, retries, parameters
2. Tool ingestion - Propose new tools/integrations
3. Goal modification - Adjust scope, timeline, success criteria
4. Task generation - Create new tasks to address gaps

The StrategyGenerator integrates with:
- IssueManager patterns for remediation task generation
- ToolRegistry for tool availability checks
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.agenda.models import (
    Obstacle,
    ObstacleType,
    Strategy,
    StrategyType,
    Workstream,
)

logger = get_logger(__name__)


# =============================================================================
# Strategy Templates
# =============================================================================

# Internal change templates by obstacle type
INTERNAL_CHANGE_TEMPLATES: Dict[ObstacleType, Dict[str, Any]] = {
    ObstacleType.CAPABILITY_GAP: {
        "title": "Route to alternative agent",
        "description": "Adjust routing to use an alternative agent with similar capabilities",
        "steps": [
            "Identify alternative agent with overlapping capabilities",
            "Update routing rules to prefer alternative",
            "Monitor performance and adjust as needed",
        ],
        "parameter_adjustments": {},
        "routing_changes": {},
    },
    ObstacleType.FAILURE_PATTERN: {
        "title": "Increase resilience",
        "description": "Increase retries and adjust timeouts to handle failure patterns",
        "steps": [
            "Increase max retries to 5",
            "Implement exponential backoff",
            "Extend timeout by 50%",
            "Add circuit breaker if not present",
        ],
        "parameter_adjustments": {
            "max_retries": 5,
            "backoff_multiplier": 2.0,
            "timeout_factor": 1.5,
        },
        "retry_policy_changes": {
            "max_retries": 5,
            "backoff_seconds": 10,
            "max_backoff_seconds": 300,
        },
    },
    ObstacleType.RESOURCE_CONSTRAINT: {
        "title": "Reduce resource usage",
        "description": "Reduce concurrent tasks and batch sizes to work within constraints",
        "steps": [
            "Reduce concurrent task limit",
            "Implement task batching",
            "Add rate limiting",
        ],
        "parameter_adjustments": {
            "max_concurrent": 2,
            "batch_size": 5,
        },
    },
    ObstacleType.DEPENDENCY: {
        "title": "Reorder execution",
        "description": "Reorder task execution to respect dependencies",
        "steps": [
            "Identify blocking dependencies",
            "Reorder execution queue",
            "Add dependency tracking",
        ],
        "parameter_adjustments": {},
    },
}

# Tool suggestions by capability category
TOOL_SUGGESTIONS: Dict[str, List[Dict[str, str]]] = {
    "development": [
        {"tool": "github_integration", "description": "GitHub API for code management"},
        {"tool": "code_analyzer", "description": "Static code analysis tool"},
    ],
    "security": [
        {"tool": "security_scanner", "description": "Automated security scanning"},
        {"tool": "vulnerability_db", "description": "CVE database integration"},
    ],
    "data": [
        {"tool": "sql_runner", "description": "SQL query execution"},
        {"tool": "data_validator", "description": "Data quality validation"},
    ],
    "communication": [
        {"tool": "slack_integration", "description": "Slack messaging"},
        {"tool": "email_service", "description": "Email sending capability"},
    ],
    "analytics": [
        {"tool": "analytics_api", "description": "Analytics data retrieval"},
        {"tool": "report_generator", "description": "Automated report generation"},
    ],
}

# Task templates for obstacle resolution
REMEDIATION_TASK_TEMPLATES: Dict[ObstacleType, List[Dict[str, Any]]] = {
    ObstacleType.CAPABILITY_GAP: [
        {
            "task_type": "research",
            "title": "Research capability options",
            "description": "Research available options to address the capability gap",
        },
        {
            "task_type": "architecture",
            "title": "Design capability integration",
            "description": "Design how to integrate the required capability",
        },
    ],
    ObstacleType.FAILURE_PATTERN: [
        {
            "task_type": "debugging",
            "title": "Investigate failure root cause",
            "description": "Investigate the root cause of the failure pattern",
        },
        {
            "task_type": "testing",
            "title": "Create regression tests",
            "description": "Create tests to catch and prevent this failure pattern",
        },
    ],
    ObstacleType.RESOURCE_CONSTRAINT: [
        {
            "task_type": "budget_analysis",
            "title": "Analyze resource requirements",
            "description": "Analyze actual resource requirements vs available",
        },
        {
            "task_type": "cost_optimization",
            "title": "Optimize resource usage",
            "description": "Find ways to reduce resource consumption",
        },
    ],
    ObstacleType.INTEGRATION_MISSING: [
        {
            "task_type": "research",
            "title": "Research integration options",
            "description": "Research available integration options",
        },
        {
            "task_type": "infrastructure",
            "title": "Setup integration",
            "description": "Configure and setup the required integration",
        },
    ],
    ObstacleType.KNOWLEDGE_GAP: [
        {
            "task_type": "research",
            "title": "Gather required information",
            "description": "Research and gather the missing information",
        },
        {
            "task_type": "knowledge_management",
            "title": "Document findings",
            "description": "Document the gathered information for future use",
        },
    ],
    ObstacleType.DEPENDENCY: [
        {
            "task_type": "strategic_analysis",
            "title": "Analyze dependency chain",
            "description": "Analyze the dependency chain and find unblocking options",
        },
    ],
}


# =============================================================================
# Strategy Generator
# =============================================================================


class StrategyGenerator:
    """
    Generates strategies to overcome detected obstacles.

    Strategy types:
    1. INTERNAL_CHANGE - Adjust existing system behavior
    2. TOOL_INGESTION - Propose new tools/integrations
    3. GOAL_MODIFICATION - Adjust goal scope/timeline
    4. TASK_GENERATION - Create new tasks to address gaps

    Example:
        generator = StrategyGenerator(tool_registry=registry)
        strategies = await generator.generate_strategies(obstacle, workstream, context)
    """

    def __init__(
        self,
        tool_registry=None,
        issue_manager=None,
        capability_evolver=None,
    ):
        """
        Initialize the strategy generator.

        Args:
            tool_registry: ToolRegistry for tool availability
            issue_manager: IssueManager for remediation patterns
            capability_evolver: CapabilityEvolver for capability tracking
        """
        self.tool_registry = tool_registry
        self.issue_manager = issue_manager
        self.capability_evolver = capability_evolver

    async def generate_strategies(
        self,
        obstacle: Obstacle,
        workstream: Workstream,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Strategy]:
        """
        Generate strategies for overcoming an obstacle.

        Args:
            obstacle: The obstacle to address
            workstream: The workstream affected by the obstacle
            context: Current execution context

        Returns:
            List of Strategy objects, ranked by priority score
        """
        context = context or {}
        strategies = []

        # Generate strategies of each type
        internal_change = self._generate_internal_change_strategy(obstacle, workstream)
        if internal_change:
            strategies.append(internal_change)

        tool_ingestion = self._generate_tool_ingestion_strategy(obstacle, workstream)
        if tool_ingestion:
            strategies.append(tool_ingestion)

        goal_modification = self._generate_goal_modification_strategy(obstacle, workstream)
        if goal_modification:
            strategies.append(goal_modification)

        task_generation = self._generate_task_generation_strategy(obstacle, workstream)
        if task_generation:
            strategies.append(task_generation)

        # Score and rank strategies
        for strategy in strategies:
            strategy.priority_score = self._score_strategy(strategy, obstacle)

        # Sort by priority score (highest first)
        strategies.sort(key=lambda s: s.priority_score, reverse=True)

        logger.info(f"Generated {len(strategies)} strategies for obstacle '{obstacle.title}'")

        return strategies

    def _generate_internal_change_strategy(
        self,
        obstacle: Obstacle,
        workstream: Workstream,
    ) -> Optional[Strategy]:
        """
        Generate internal change strategy.

        Examples:
        - Increase retries for timeout-prone tasks
        - Adjust routing to use different agent
        - Change timeout parameters
        - Modify batch sizes
        """
        template = INTERNAL_CHANGE_TEMPLATES.get(obstacle.obstacle_type)
        if not template:
            return None

        # Customize based on obstacle specifics
        title = template["title"]
        description = template["description"]
        steps = template["steps"].copy()

        # Add obstacle-specific details
        if obstacle.obstacle_type == ObstacleType.CAPABILITY_GAP:
            # Find alternative agent
            alternative = self._find_alternative_executive(obstacle, workstream)
            if alternative:
                title = f"Route to {alternative} instead"
                steps = [
                    f"Update routing to prefer {alternative} for affected task types",
                    "Monitor performance after routing change",
                    "Adjust if quality decreases",
                ]
            else:
                # No alternative found, this strategy may not be viable
                return None

        elif obstacle.obstacle_type == ObstacleType.FAILURE_PATTERN:
            # Add specific failure mitigation
            for task_type in obstacle.related_task_types:
                steps.append(f"Add specific error handling for {task_type}")

        strategy = Strategy(
            strategy_type=StrategyType.INTERNAL_CHANGE,
            obstacle_id=obstacle.id,
            title=title,
            description=f"{description}\n\nObstacle: {obstacle.title}",
            rationale=(
                f"Internal changes are the fastest way to address this obstacle "
                f"without requiring external resources or approval for new tools."
            ),
            implementation_steps=steps,
            estimated_effort_hours=1.0,
            estimated_cost_usd=0.0,
            confidence=0.7,
            impact_score=0.6,
            feasibility_score=0.9,
            parameter_adjustments=template.get("parameter_adjustments", {}),
            routing_changes=template.get("routing_changes", {}),
            retry_policy_changes=template.get("retry_policy_changes", {}),
        )

        return strategy

    def _find_alternative_executive(
        self,
        obstacle: Obstacle,
        workstream: Workstream,
    ) -> Optional[str]:
        """Find an alternative agent for capability gap."""
        # Get current agent assignment
        current_executives = set(workstream.executive_mapping.values())

        # Define fallback mappings
        executive_fallbacks = {
            "Forge": ["Foundry"],
            "Foundry": ["Forge"],
            "Sentinel": ["Citadel", "Forge"],
            "Citadel": ["Sentinel"],
            "Keystone": ["Vector"],
            "Vector": ["Keystone"],
            "Echo": ["Beacon"],
            "Beacon": ["Echo"],
            "Blueprint": ["Compass"],
            "Compass": ["Blueprint"],
            "Axiom": ["Index"],
            "Index": ["Axiom"],
        }

        for agent_code in current_executives:
            fallbacks = executive_fallbacks.get(agent_code, [])
            for fallback in fallbacks:
                if fallback not in current_executives:
                    return fallback

        return None

    def _generate_tool_ingestion_strategy(
        self,
        obstacle: Obstacle,
        workstream: Workstream,
    ) -> Optional[Strategy]:
        """
        Generate tool ingestion strategy.

        Proposes:
        - New tool to add to ToolRegistry
        - New integration via IntegrationFactory
        - New capability via CapabilityEvolver
        """
        # Only applicable for capability gaps and missing integrations
        if obstacle.obstacle_type not in (
            ObstacleType.CAPABILITY_GAP,
            ObstacleType.INTEGRATION_MISSING,
        ):
            return None

        # Find relevant tool suggestions
        suggested_tools = []
        for requirement in workstream.capability_requirements:
            if requirement.tool_category:
                tools = TOOL_SUGGESTIONS.get(requirement.tool_category, [])
                suggested_tools.extend(tools)

        if not suggested_tools:
            # Generic tool suggestion
            suggested_tools = [
                {
                    "tool": "custom_integration",
                    "description": "Custom integration for missing capability",
                }
            ]

        # Pick the most relevant tool
        proposed_tool = suggested_tools[0]["tool"]
        tool_description = suggested_tools[0]["description"]

        strategy = Strategy(
            strategy_type=StrategyType.TOOL_INGESTION,
            obstacle_id=obstacle.id,
            title=f"Add {proposed_tool} tool",
            description=(
                f"Add a new tool to address the obstacle: {obstacle.title}\n\n"
                f"Proposed tool: {proposed_tool}\n"
                f"Purpose: {tool_description}"
            ),
            rationale=(
                f"Adding a new tool will provide the missing capability permanently "
                f"and enable future tasks of this type."
            ),
            implementation_steps=[
                f"Evaluate {proposed_tool} requirements and dependencies",
                "Configure credentials and access",
                "Register tool in ToolRegistry",
                "Test tool functionality",
                "Update agent capabilities",
            ],
            estimated_effort_hours=4.0,
            estimated_cost_usd=10.0,  # May include API costs
            confidence=0.6,
            impact_score=0.8,
            feasibility_score=0.7,
            proposed_tool=proposed_tool,
            proposed_integration=tool_description,
            tool_requirements=[f"Access to {proposed_tool} service or API"],
        )

        return strategy

    def _generate_goal_modification_strategy(
        self,
        obstacle: Obstacle,
        workstream: Workstream,
    ) -> Optional[Strategy]:
        """
        Generate goal modification strategy.

        Suggests:
        - Scope reduction
        - Timeline extension
        - Success criteria adjustment
        - Milestone decomposition
        """
        # Determine what kind of modification makes sense
        if obstacle.obstacle_type == ObstacleType.RESOURCE_CONSTRAINT:
            return self._suggest_scope_reduction(obstacle, workstream)
        elif obstacle.obstacle_type == ObstacleType.DEPENDENCY:
            return self._suggest_timeline_extension(obstacle, workstream)
        elif obstacle.obstacle_type == ObstacleType.CAPABILITY_GAP:
            return self._suggest_criteria_adjustment(obstacle, workstream)
        elif obstacle.severity >= 0.8:
            return self._suggest_milestone_split(obstacle, workstream)

        return None

    def _suggest_scope_reduction(
        self,
        obstacle: Obstacle,
        workstream: Workstream,
    ) -> Strategy:
        """Suggest reducing scope to work within constraints."""
        return Strategy(
            strategy_type=StrategyType.GOAL_MODIFICATION,
            obstacle_id=obstacle.id,
            title="Reduce scope to essential features",
            description=(
                f"Reduce the scope of '{workstream.title}' to work within "
                f"current resource constraints.\n\n"
                f"Obstacle: {obstacle.title}"
            ),
            rationale=(
                "Reducing scope allows progress to continue within current "
                "constraints while deferring non-essential work."
            ),
            implementation_steps=[
                "Identify essential vs nice-to-have requirements",
                "Update workstream with reduced scope",
                "Create separate workstream for deferred items",
                "Adjust success criteria accordingly",
            ],
            estimated_effort_hours=1.0,
            estimated_cost_usd=0.0,
            confidence=0.8,
            impact_score=0.5,  # Partial progress
            feasibility_score=0.9,
            scope_changes="Reduce to essential features only",
        )

    def _suggest_timeline_extension(
        self,
        obstacle: Obstacle,
        workstream: Workstream,
    ) -> Strategy:
        """Suggest extending timeline to accommodate dependencies."""
        return Strategy(
            strategy_type=StrategyType.GOAL_MODIFICATION,
            obstacle_id=obstacle.id,
            title="Extend timeline for dependencies",
            description=(
                f"Extend the timeline for '{workstream.title}' to allow "
                f"dependencies to complete first.\n\n"
                f"Obstacle: {obstacle.title}"
            ),
            rationale=(
                "Extending the timeline acknowledges the dependency and "
                "prevents starting work that cannot complete."
            ),
            implementation_steps=[
                "Calculate new timeline based on dependency completion estimates",
                "Update workstream estimated completion",
                "Communicate timeline change to stakeholders",
                "Set up dependency completion monitoring",
            ],
            estimated_effort_hours=0.5,
            estimated_cost_usd=0.0,
            confidence=0.9,
            impact_score=0.4,  # Delay but eventual completion
            feasibility_score=0.95,
            timeline_changes="Extend by estimated dependency completion time",
        )

    def _suggest_criteria_adjustment(
        self,
        obstacle: Obstacle,
        workstream: Workstream,
    ) -> Strategy:
        """Suggest adjusting success criteria to work with available capabilities."""
        return Strategy(
            strategy_type=StrategyType.GOAL_MODIFICATION,
            obstacle_id=obstacle.id,
            title="Adjust success criteria",
            description=(
                f"Adjust success criteria for '{workstream.title}' to be "
                f"achievable with available capabilities.\n\n"
                f"Obstacle: {obstacle.title}"
            ),
            rationale=(
                "Adjusting criteria allows demonstrating progress with "
                "current capabilities while planning for full capability."
            ),
            implementation_steps=[
                "Review original success criteria",
                "Identify which criteria require missing capability",
                "Define interim criteria achievable now",
                "Plan for full criteria when capability added",
            ],
            estimated_effort_hours=1.0,
            estimated_cost_usd=0.0,
            confidence=0.7,
            impact_score=0.5,
            feasibility_score=0.85,
            success_criteria_changes="Adjust to achievable with current capabilities",
        )

    def _suggest_milestone_split(
        self,
        obstacle: Obstacle,
        workstream: Workstream,
    ) -> Strategy:
        """Suggest splitting milestone into smaller pieces."""
        return Strategy(
            strategy_type=StrategyType.GOAL_MODIFICATION,
            obstacle_id=obstacle.id,
            title="Split into smaller milestones",
            description=(
                f"Split '{workstream.title}' into smaller, more manageable "
                f"milestones that can proceed independently.\n\n"
                f"Obstacle: {obstacle.title}"
            ),
            rationale=(
                "Splitting into smaller pieces allows some progress to continue "
                "while the blocked portion is addressed separately."
            ),
            implementation_steps=[
                "Identify independent portions of the workstream",
                "Create separate milestones for each portion",
                "Move blocked work to its own milestone",
                "Update dependencies between new milestones",
            ],
            estimated_effort_hours=1.5,
            estimated_cost_usd=0.0,
            confidence=0.75,
            impact_score=0.6,
            feasibility_score=0.8,
            milestone_changes=[
                {"action": "split", "reason": "Isolate blocked work"},
            ],
        )

    def _generate_task_generation_strategy(
        self,
        obstacle: Obstacle,
        workstream: Workstream,
    ) -> Optional[Strategy]:
        """
        Generate new tasks to address the obstacle.

        Creates task specs for:
        - Investigation tasks
        - Setup/preparation tasks
        - Remediation tasks
        """
        task_templates = REMEDIATION_TASK_TEMPLATES.get(obstacle.obstacle_type, [])

        if not task_templates:
            # Generic research task
            task_templates = [
                {
                    "task_type": "research",
                    "title": f"Investigate: {obstacle.title}",
                    "description": f"Research solutions for obstacle: {obstacle.description}",
                }
            ]

        # Generate task specs
        task_specs = []
        for template in task_templates:
            task_spec = {
                "task_type": template["task_type"],
                "title": f"{template['title']} - {obstacle.title[:50]}",
                "description": (
                    f"{template['description']}\n\n"
                    f"Related to obstacle: {obstacle.title}\n"
                    f"Workstream: {workstream.title}"
                ),
                "context": {
                    "obstacle_id": obstacle.id,
                    "workstream_id": workstream.id,
                    "goal_id": workstream.goal_id,
                },
                "priority": "high" if obstacle.severity >= 0.7 else "medium",
            }
            task_specs.append(task_spec)

        strategy = Strategy(
            strategy_type=StrategyType.TASK_GENERATION,
            obstacle_id=obstacle.id,
            title=f"Create {len(task_specs)} remediation tasks",
            description=(
                f"Generate specific tasks to address obstacle: {obstacle.title}\n\n"
                f"Tasks to create:\n" + "\n".join(f"- {spec['title']}" for spec in task_specs)
            ),
            rationale=(
                "Creating specific tasks to investigate and remediate the obstacle "
                "provides a clear path forward with measurable progress."
            ),
            implementation_steps=[f"Create task: {spec['title']}" for spec in task_specs]
            + ["Execute tasks through normal routing", "Mark obstacle resolved on completion"],
            estimated_effort_hours=sum(1.0 for _ in task_specs),
            estimated_cost_usd=sum(0.5 for _ in task_specs),
            confidence=0.7,
            impact_score=0.7,
            feasibility_score=0.85,
            generated_task_specs=task_specs,
        )

        return strategy

    def _score_strategy(
        self,
        strategy: Strategy,
        obstacle: Obstacle,
    ) -> float:
        """
        Calculate priority score based on impact, feasibility, and cost.

        Score = (impact × feasibility × urgency_factor) / (effort + 1)
        """
        impact = strategy.impact_score
        feasibility = strategy.feasibility_score
        effort = strategy.estimated_effort_hours

        # Urgency factor based on obstacle severity
        urgency_factor = 1.0 + (obstacle.severity * 0.5)

        # Calculate base score
        score = (impact * feasibility * urgency_factor) / (effort + 1)

        # Boost certain strategy types based on context
        if strategy.strategy_type == StrategyType.INTERNAL_CHANGE:
            # Internal changes are quick wins
            score *= 1.1
        elif strategy.strategy_type == StrategyType.TASK_GENERATION:
            # Task generation provides clear path forward
            score *= 1.05

        # Penalize high-cost strategies
        if strategy.estimated_cost_usd > 50:
            score *= 0.8

        return round(score, 3)

    async def generate_strategies_for_multiple(
        self,
        obstacles: List[Obstacle],
        workstreams: Dict[str, Workstream],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Strategy]]:
        """
        Generate strategies for multiple obstacles.

        Args:
            obstacles: List of obstacles to address
            workstreams: Dict mapping workstream_id to Workstream
            context: Shared execution context

        Returns:
            Dict mapping obstacle_id to list of strategies
        """
        result = {}
        for obstacle in obstacles:
            ws_id = obstacle.workstream_id
            workstream = workstreams.get(ws_id)
            if workstream:
                strategies = await self.generate_strategies(obstacle, workstream, context)
                result[obstacle.id] = strategies
        return result

    def get_recommended_strategy(
        self,
        strategies: List[Strategy],
    ) -> Optional[Strategy]:
        """Get the highest-scored strategy."""
        if not strategies:
            return None
        return max(strategies, key=lambda s: s.priority_score)

    def filter_by_type(
        self,
        strategies: List[Strategy],
        strategy_type: StrategyType,
    ) -> List[Strategy]:
        """Filter strategies by type."""
        return [s for s in strategies if s.strategy_type == strategy_type]

    def filter_auto_executable(
        self,
        strategies: List[Strategy],
        max_cost: float = 10.0,
        min_confidence: float = 0.7,
    ) -> List[Strategy]:
        """Filter strategies that can be executed automatically."""
        return [
            s
            for s in strategies
            if s.estimated_cost_usd <= max_cost
            and s.confidence >= min_confidence
            and s.strategy_type
            in (
                StrategyType.INTERNAL_CHANGE,
                StrategyType.TASK_GENERATION,
            )
        ]
