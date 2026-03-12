"""
Blueprint (Blueprint) Specialist Classes.

Individual contributor specialists for product operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Specialist,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class RoadmapPlanner(Specialist):
    """
    Specialist for roadmap planning.

    Handles timeline construction, dependency mapping, and milestone definition.
    """

    HANDLED_TASK_TYPES = [
        "timeline_construction",
        "dependency_mapping",
        "milestone_definition",
        "capacity_planning",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="RoadmapPlanner",
            name="Roadmap Planner",
            domain="Roadmap Planning",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute roadmap planning task."""
        task.status = TaskStatus.IN_PROGRESS

        prompt = f"""As a Roadmap Planner specialist, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide detailed roadmap planning output with:
1. Timeline with milestones
2. Dependencies identified
3. Resource requirements
4. Risk factors"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "task_type": task.task_type,
                "planning": response,
                "planned_at": _utcnow().isoformat(),
            },
        )


class FeaturePrioritizer(Specialist):
    """
    Specialist for feature prioritization.

    Handles scoring, ranking, and stack ranking of features.
    """

    HANDLED_TASK_TYPES = [
        "feature_scoring",
        "stack_ranking",
        "priority_assessment",
        "trade_off_analysis",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="FeaturePrioritizer",
            name="Feature Prioritizer",
            domain="Feature Prioritization",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute feature prioritization task."""
        task.status = TaskStatus.IN_PROGRESS

        features = task.context.get("features", [])
        framework = task.context.get("framework", "RICE")

        prompt = f"""As a Feature Prioritizer specialist using the {framework} framework:

Task: {task.description}
Features: {features}
Context: {task.context}

Provide:
1. Scored feature list with {framework} breakdown
2. Stack ranked priority order
3. Justification for top priorities
4. Trade-off analysis"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "prioritization_type": task.task_type,
                "framework": framework,
                "prioritization": response,
            },
        )


class RequirementsWriter(Specialist):
    """
    Specialist for requirements documentation.

    Handles user stories, technical specs, and acceptance criteria.
    """

    HANDLED_TASK_TYPES = [
        "user_story_writing",
        "technical_spec",
        "acceptance_criteria",
        "prd_creation",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="RequirementsWriter",
            name="Requirements Writer",
            domain="Requirements Documentation",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute requirements writing task."""
        task.status = TaskStatus.IN_PROGRESS

        prompt = f"""As a Requirements Writer specialist:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Create professional requirements documentation with:
1. Clear, actionable requirements
2. Proper formatting and numbering
3. Testable acceptance criteria
4. Edge cases and exceptions"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "documentation_type": task.task_type,
                "documentation": response,
            },
        )


class BacklogGroomer(Specialist):
    """
    Specialist for backlog maintenance.

    Handles backlog refinement, estimation, and cleanup.
    """

    HANDLED_TASK_TYPES = [
        "backlog_refinement",
        "story_estimation",
        "backlog_cleanup",
        "technical_debt_tracking",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="BacklogGroomer",
            name="Backlog Groomer",
            domain="Backlog Management",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute backlog grooming task."""
        task.status = TaskStatus.IN_PROGRESS

        backlog = task.context.get("backlog", [])

        prompt = f"""As a Backlog Groomer specialist:

Task Type: {task.task_type}
Description: {task.description}
Backlog: {backlog}
Context: {task.context}

Provide grooming output:
1. Items to refine (with refinements)
2. Items to split (with breakdown)
3. Effort estimates (story points)
4. Items to deprioritize or remove
5. Missing items to add"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "grooming_type": task.task_type,
                "grooming_results": response,
            },
        )


class MarketResearcher(Specialist):
    """
    Specialist for market and competitive research.

    Handles competitive analysis, market trends, and customer insights.
    """

    HANDLED_TASK_TYPES = [
        "competitive_analysis",
        "market_research",
        "customer_insights",
        "trend_analysis",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="MarketResearcher",
            name="Market Researcher",
            domain="Market Research",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute market research task."""
        task.status = TaskStatus.IN_PROGRESS

        competitors = task.context.get("competitors", [])
        market = task.context.get("market", "")

        prompt = f"""As a Market Researcher specialist:

Task Type: {task.task_type}
Description: {task.description}
Market: {market}
Competitors: {competitors}
Context: {task.context}

Provide research output:
1. Market landscape overview
2. Competitive positioning
3. Key differentiators
4. Market opportunities
5. Threats and risks
6. Recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "research_type": task.task_type,
                "research": response,
            },
        )


class SprintPlanner(Specialist):
    """
    Specialist for sprint planning.

    Handles sprint scope, capacity planning, and commitment.
    """

    HANDLED_TASK_TYPES = [
        "sprint_scoping",
        "capacity_analysis",
        "commitment_planning",
        "velocity_tracking",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="SprintPlanner",
            name="Sprint Planner",
            domain="Sprint Planning",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute sprint planning task."""
        task.status = TaskStatus.IN_PROGRESS

        backlog = task.context.get("backlog", [])
        capacity = task.context.get("capacity", {})
        velocity = task.context.get("velocity", 0)

        prompt = f"""As a Sprint Planner specialist:

Task Type: {task.task_type}
Description: {task.description}
Backlog: {backlog}
Team Capacity: {capacity}
Historical Velocity: {velocity}

Create sprint plan:
1. Sprint goal
2. Committed items (within velocity)
3. Stretch items
4. Capacity allocation
5. Dependencies and risks
6. Success criteria"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "planning_type": task.task_type,
                "sprint_plan": response,
                "planned_at": _utcnow().isoformat(),
            },
        )
