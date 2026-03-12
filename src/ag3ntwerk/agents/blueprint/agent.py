"""
Blueprint (Blueprint) Agent - Blueprint.

Codename: Blueprint
Core function: Product direction, roadmap, and feature lifecycle.

The Blueprint handles all product management tasks:
- Feature prioritization and lifecycle
- Roadmap planning and updates
- Requirements gathering and specification
- Sprint planning and backlog grooming
- Milestone tracking and release planning

Sphere of influence: Product vision, roadmap, feature priorities,
customer requirements, market positioning, product-market fit.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Manager,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider
from ag3ntwerk.agents.blueprint.managers import (
    RoadmapManager,
    FeatureManager,
    RequirementsManager,
)
from ag3ntwerk.agents.blueprint.specialists import (
    RoadmapPlanner,
    FeaturePrioritizer,
    RequirementsWriter,
    BacklogGroomer,
    MarketResearcher,
    SprintPlanner,
)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


# Product management task types
PRODUCT_CAPABILITIES = [
    "feature_prioritization",
    "roadmap_update",
    "requirements_gathering",
    "sprint_planning",
    "backlog_grooming",
    "milestone_tracking",
    "product_spec",
    "user_story",
    "acceptance_criteria",
    "feature_scoping",
    "competitive_analysis",
    "market_research",
    # Manager-level task types
    "roadmap_review",
    "milestone_planning",
    "timeline_adjustment",
    "dependency_mapping",
    "feature_lifecycle",
    "feature_assessment",
    "feature_definition",
    "feature_tracking",
    "feature_release",
    "requirements_review",
    "requirements_validation",
    "requirements_documentation",
    "requirements_approval",
    # Specialist-level task types
    "timeline_construction",
    "milestone_definition",
    "capacity_planning",
    "feature_scoring",
    "stack_ranking",
    "priority_assessment",
    "trade_off_analysis",
    "user_story_writing",
    "technical_spec",
    "prd_creation",
    "backlog_refinement",
    "story_splitting",
    "backlog_prioritization",
    "technical_debt_grooming",
    "market_analysis",
    "market_sizing",
    "competitive_research",
    "customer_interviews",
    "market_trends",
    "sprint_capacity",
    "sprint_scope",
    "velocity_analysis",
    "sprint_review",
]

# Routing from task types to managers
MANAGER_ROUTING = {
    # RoadmapManager tasks
    "roadmap_update": "RoadmapMgr",
    "roadmap_review": "RoadmapMgr",
    "milestone_planning": "RoadmapMgr",
    "milestone_tracking": "RoadmapMgr",
    "timeline_adjustment": "RoadmapMgr",
    "dependency_mapping": "RoadmapMgr",
    # FeatureManager tasks
    "feature_prioritization": "FeatureMgr",
    "feature_lifecycle": "FeatureMgr",
    "feature_assessment": "FeatureMgr",
    "feature_definition": "FeatureMgr",
    "feature_tracking": "FeatureMgr",
    "feature_release": "FeatureMgr",
    "feature_scoping": "FeatureMgr",
    # RequirementsManager tasks
    "requirements_gathering": "ReqMgr",
    "requirements_review": "ReqMgr",
    "requirements_validation": "ReqMgr",
    "requirements_documentation": "ReqMgr",
    "requirements_approval": "ReqMgr",
    "product_spec": "ReqMgr",
    "user_story": "ReqMgr",
    "acceptance_criteria": "ReqMgr",
}


class Blueprint(Manager):
    """
    Blueprint - Blueprint.

    The Blueprint is responsible for product direction within the
    ag3ntwerk system. It manages the product lifecycle from
    ideation to release.

    Codename: Blueprint

    Core Responsibilities:
    - Feature prioritization and lifecycle management
    - Roadmap planning and milestone tracking
    - Requirements gathering and specification
    - Sprint planning and backlog management
    - Product-market fit analysis

    Example:
        ```python
        cpo = Blueprint(llm_provider=llm)

        task = Task(
            description="Prioritize Q1 feature requests",
            task_type="feature_prioritization",
            context={"features": features_list, "quarter": "Q1 2026"},
        )
        result = await cpo.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__(
            code="Blueprint",
            name="Blueprint",
            domain="Product Management, Strategy, Requirements",
            llm_provider=llm_provider,
        )
        self.codename = "Blueprint"

        self.capabilities = PRODUCT_CAPABILITIES

        # Product-specific state
        self._roadmaps: Dict[str, Any] = {}
        self._features: Dict[str, Any] = {}
        self._backlogs: Dict[str, List[str]] = {}
        self._milestones: Dict[str, Any] = {}

        # Initialize and register managers with their specialists
        self._init_managers()

    def _init_managers(self) -> None:
        """Initialize and register managers with their specialists."""
        # Create managers
        roadmap_mgr = RoadmapManager(llm_provider=self.llm_provider)
        feature_mgr = FeatureManager(llm_provider=self.llm_provider)
        req_mgr = RequirementsManager(llm_provider=self.llm_provider)

        # Create specialists
        roadmap_planner = RoadmapPlanner(llm_provider=self.llm_provider)
        feature_prioritizer = FeaturePrioritizer(llm_provider=self.llm_provider)
        req_writer = RequirementsWriter(llm_provider=self.llm_provider)
        backlog_groomer = BacklogGroomer(llm_provider=self.llm_provider)
        market_researcher = MarketResearcher(llm_provider=self.llm_provider)
        sprint_planner = SprintPlanner(llm_provider=self.llm_provider)

        # Register specialists with appropriate managers
        roadmap_mgr.register_subordinate(roadmap_planner)
        feature_mgr.register_subordinate(feature_prioritizer)
        feature_mgr.register_subordinate(market_researcher)
        req_mgr.register_subordinate(req_writer)
        req_mgr.register_subordinate(backlog_groomer)
        req_mgr.register_subordinate(sprint_planner)

        # Register managers with Blueprint
        self.register_subordinate(roadmap_mgr)
        self.register_subordinate(feature_mgr)
        self.register_subordinate(req_mgr)

    def _route_to_manager(self, task_type: str) -> Optional[str]:
        """Route task to appropriate manager."""
        return MANAGER_ROUTING.get(task_type)

    def can_handle(self, task: Task) -> bool:
        """Check if this is a product-related task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute a product management task, routing through managers when appropriate."""
        task.status = TaskStatus.IN_PROGRESS

        # First, try to route through a manager
        manager_code = self._route_to_manager(task.task_type)
        if manager_code and manager_code in self._subordinates:
            return await self.delegate(task, manager_code)

        # Fall back to direct handlers
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        # Fallback to LLM-based handling
        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            "feature_prioritization": self._handle_feature_prioritization,
            "roadmap_update": self._handle_roadmap_update,
            "requirements_gathering": self._handle_requirements_gathering,
            "sprint_planning": self._handle_sprint_planning,
            "backlog_grooming": self._handle_backlog_grooming,
            "milestone_tracking": self._handle_milestone_tracking,
            "product_spec": self._handle_product_spec,
            "user_story": self._handle_user_story,
            # VLS handlers
            "vls_blueprint_definition": self._handle_vls_blueprint_definition,
        }
        return handlers.get(task_type)

    async def _handle_feature_prioritization(self, task: Task) -> TaskResult:
        """Prioritize features based on value and effort."""
        features = task.context.get("features", [])
        criteria = task.context.get("criteria", {})
        constraints = task.context.get("constraints", {})

        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider for feature prioritization",
            )

        prompt = f"""As the Blueprint (Blueprint), prioritize these features.

Features to prioritize:
{features}

Prioritization Criteria:
- Business Value: How much value does this feature deliver?
- Customer Impact: How many customers are affected?
- Strategic Alignment: Does this align with product vision?
- Effort Estimate: Engineering complexity and time required
- Dependencies: What must be built first?

Additional Criteria: {criteria}
Constraints: {constraints}

Provide a prioritized list with:
1. PRIORITY RANKING (P0-P4 with feature name)
2. RATIONALE for each priority assignment
3. DEPENDENCIES identified
4. RECOMMENDED TIMELINE
5. TRADE-OFF ANALYSIS

Format as a structured priority matrix."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Feature prioritization failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "prioritization_type": "feature_prioritization",
                "features_count": len(features) if isinstance(features, list) else 0,
                "analysis": response,
                "prioritized_at": _utcnow().isoformat(),
            },
            metrics={"task_type": "feature_prioritization"},
        )

    async def _handle_roadmap_update(self, task: Task) -> TaskResult:
        """Update product roadmap."""
        current_roadmap = task.context.get("current_roadmap", {})
        changes = task.context.get("changes", [])
        timeframe = task.context.get("timeframe", "Q1 2026")

        prompt = f"""As the Blueprint (Blueprint), update the product roadmap.

Current Roadmap:
{current_roadmap}

Requested Changes:
{changes}

Timeframe: {timeframe}
Context: {task.description}

Provide an updated roadmap including:
1. ROADMAP OVERVIEW
   - Strategic themes for the period
   - Key objectives and OKRs

2. MILESTONE TIMELINE
   - Each milestone with target dates
   - Features included in each milestone
   - Dependencies and risks

3. CHANGES SUMMARY
   - What was added/removed/modified
   - Impact on previous commitments
   - Resource implications

4. RISKS AND MITIGATIONS
   - Timeline risks
   - Resource risks
   - Technical risks

5. STAKEHOLDER COMMUNICATION
   - Key messages for internal teams
   - Key messages for customers"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Roadmap update failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "update_type": "roadmap_update",
                "timeframe": timeframe,
                "roadmap": response,
                "updated_at": _utcnow().isoformat(),
            },
        )

    async def _handle_requirements_gathering(self, task: Task) -> TaskResult:
        """Gather and document requirements."""
        feature = task.context.get("feature", {})
        stakeholders = task.context.get("stakeholders", [])
        feedback = task.context.get("feedback", [])

        prompt = f"""As the Blueprint (Blueprint), gather requirements.

Feature: {task.description}
Feature Details: {feature}
Stakeholder Input: {stakeholders}
Customer Feedback: {feedback}

Create a comprehensive requirements document including:

1. AGENT SUMMARY
   - Feature overview
   - Business justification
   - Success metrics

2. FUNCTIONAL REQUIREMENTS
   - User-facing requirements (FR-001, FR-002, etc.)
   - Each with description, priority, and acceptance criteria

3. NON-FUNCTIONAL REQUIREMENTS
   - Performance requirements
   - Security requirements
   - Scalability requirements
   - Usability requirements

4. USER STORIES
   - As a [user type], I want [goal] so that [benefit]
   - Include acceptance criteria for each

5. OUT OF SCOPE
   - What is explicitly not included
   - Future considerations

6. DEPENDENCIES
   - Technical dependencies
   - External dependencies
   - Team dependencies

7. OPEN QUESTIONS
   - Items needing clarification
   - Decisions required"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Requirements gathering failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "requirements_type": "gathering",
                "feature": task.description,
                "requirements": response,
            },
        )

    async def _handle_sprint_planning(self, task: Task) -> TaskResult:
        """Plan sprint with prioritized work items."""
        backlog = task.context.get("backlog", [])
        capacity = task.context.get("capacity", {})
        sprint_length = task.context.get("sprint_length", 2)
        goals = task.context.get("sprint_goals", [])

        prompt = f"""As the Blueprint (Blueprint), plan the sprint.

Sprint Length: {sprint_length} weeks
Team Capacity: {capacity}
Sprint Goals: {goals}

Backlog Items:
{backlog}

Description: {task.description}

Create a sprint plan including:

1. SPRINT GOAL
   - Clear, measurable sprint objective
   - How this advances the roadmap

2. COMMITTED ITEMS
   - Items committed for this sprint
   - Story points / effort for each
   - Owner assignments

3. STRETCH GOALS
   - Items to tackle if time permits
   - Priority order for stretch items

4. CAPACITY ALLOCATION
   - Development work: X%
   - Bug fixes: X%
   - Technical debt: X%
   - Meetings/overhead: X%

5. DEPENDENCIES
   - Cross-team dependencies
   - External dependencies
   - Blockers to address

6. RISKS
   - Potential impediments
   - Mitigation strategies

7. DEFINITION OF DONE
   - Criteria for sprint success"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Sprint planning failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "planning_type": "sprint_planning",
                "sprint_length_weeks": sprint_length,
                "plan": response,
                "planned_at": _utcnow().isoformat(),
            },
        )

    async def _handle_backlog_grooming(self, task: Task) -> TaskResult:
        """Groom and refine the product backlog."""
        backlog = task.context.get("backlog", [])
        criteria = task.context.get("grooming_criteria", {})

        prompt = f"""As the Blueprint (Blueprint), groom the backlog.

Current Backlog:
{backlog}

Grooming Criteria: {criteria}
Context: {task.description}

Perform backlog grooming:

1. ITEMS TO REFINE
   - Items needing more detail
   - Suggested refinements

2. ITEMS TO SPLIT
   - Items too large for one sprint
   - Suggested breakdown

3. ITEMS TO REMOVE
   - Obsolete or duplicate items
   - Reason for removal

4. PRIORITY ADJUSTMENTS
   - Items to reprioritize
   - Rationale for changes

5. NEW ITEMS TO ADD
   - Gaps identified
   - Suggested new items

6. EFFORT ESTIMATES
   - Items needing estimation
   - Suggested story points

7. ACCEPTANCE CRITERIA
   - Items missing criteria
   - Suggested criteria"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Backlog grooming failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "grooming_type": "backlog_grooming",
                "items_reviewed": len(backlog) if isinstance(backlog, list) else 0,
                "grooming_results": response,
            },
        )

    async def _handle_milestone_tracking(self, task: Task) -> TaskResult:
        """Track milestone progress and health."""
        milestone = task.context.get("milestone", {})
        features = task.context.get("features", [])
        metrics = task.context.get("metrics", {})

        prompt = f"""As the Blueprint (Blueprint), track milestone progress.

Milestone: {task.description}
Milestone Details: {milestone}
Features: {features}
Current Metrics: {metrics}

Provide milestone status update:

1. OVERALL STATUS
   - On Track / At Risk / Off Track
   - Confidence level (1-10)

2. PROGRESS SUMMARY
   - Features completed: X/Y
   - Features in progress: X
   - Features not started: X

3. TIMELINE ANALYSIS
   - Original target date
   - Current projected date
   - Variance and reason

4. BLOCKERS AND RISKS
   - Current blockers
   - Emerging risks
   - Mitigation actions

5. RESOURCE STATUS
   - Team allocation
   - Capacity concerns

6. NEXT STEPS
   - Actions for next period
   - Decisions required

7. STAKEHOLDER UPDATE
   - Key messages for leadership"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Milestone tracking failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "tracking_type": "milestone_tracking",
                "milestone": task.description,
                "status_report": response,
                "tracked_at": _utcnow().isoformat(),
            },
        )

    async def _handle_product_spec(self, task: Task) -> TaskResult:
        """Create product specification document."""
        feature = task.context.get("feature", {})
        requirements = task.context.get("requirements", [])

        prompt = f"""As the Blueprint (Blueprint), create a product spec.

Feature: {task.description}
Feature Details: {feature}
Requirements: {requirements}

Create a Product Requirements Document (PRD):

1. OVERVIEW
   - Problem statement
   - Proposed solution
   - Target users

2. GOALS AND SUCCESS METRICS
   - Primary goal
   - Secondary goals
   - KPIs and success criteria

3. USER EXPERIENCE
   - User flows
   - Key interactions
   - Edge cases

4. TECHNICAL REQUIREMENTS
   - System requirements
   - Integration points
   - Data requirements

5. SCOPE
   - In scope (MVP)
   - Out of scope
   - Future considerations

6. TIMELINE
   - Proposed phases
   - Key milestones
   - Dependencies

7. RISKS AND MITIGATIONS
   - Known risks
   - Mitigation strategies

8. OPEN QUESTIONS
   - Unresolved items
   - Required decisions"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Product spec creation failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "spec_type": "product_spec",
                "feature": task.description,
                "specification": response,
            },
        )

    async def _handle_user_story(self, task: Task) -> TaskResult:
        """Create user stories with acceptance criteria."""
        feature = task.context.get("feature", "")
        user_types = task.context.get("user_types", ["user"])
        context = task.context.get("business_context", "")

        prompt = f"""As the Blueprint (Blueprint), write user stories.

Feature: {task.description}
Feature Context: {feature}
User Types: {user_types}
Business Context: {context}

Create comprehensive user stories:

For each user type, provide stories in this format:

USER STORY: [US-XXX]
As a [user type],
I want [goal/desire],
So that [benefit/value].

ACCEPTANCE CRITERIA:
- Given [context], when [action], then [outcome]
- Given [context], when [action], then [outcome]
- ...

NOTES:
- Implementation notes
- Edge cases
- Dependencies

Provide 3-5 user stories covering the main functionality."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"User story creation failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "story_type": "user_story",
                "feature": task.description,
                "user_stories": response,
            },
        )

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM when no specific handler exists."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider and no handler for task type",
            )

        prompt = f"""As the Blueprint (Blueprint) - Blueprint, specializing in
product management and strategy, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough product-focused response with actionable recommendations."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"LLM execution failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )

    # State management methods

    def add_feature(self, product_id: str, feature: Dict[str, Any]) -> str:
        """Add a feature to tracking."""
        feature_id = feature.get("id", f"feat-{len(self._features)}")
        self._features[feature_id] = {
            "product_id": product_id,
            **feature,
            "added_at": _utcnow().isoformat(),
        }
        return feature_id

    def update_roadmap(self, product_id: str, roadmap: Dict[str, Any]) -> None:
        """Update roadmap for a product."""
        self._roadmaps[product_id] = {
            **roadmap,
            "updated_at": _utcnow().isoformat(),
        }

    def add_to_backlog(self, product_id: str, items: List[str]) -> None:
        """Add items to product backlog."""
        if product_id not in self._backlogs:
            self._backlogs[product_id] = []
        self._backlogs[product_id].extend(items)

    def set_milestone(self, product_id: str, milestone: Dict[str, Any]) -> str:
        """Set a milestone for tracking."""
        milestone_id = milestone.get("id", f"ms-{len(self._milestones)}")
        self._milestones[milestone_id] = {
            "product_id": product_id,
            **milestone,
            "created_at": _utcnow().isoformat(),
        }
        return milestone_id

    async def _handle_vls_blueprint_definition(self, task: Task) -> TaskResult:
        """Execute VLS Stage 3: Blueprint Definition."""
        from ag3ntwerk.modules.vls.stages import execute_blueprint_definition

        try:
            result = await execute_blueprint_definition(task.context)

            return TaskResult(
                task_id=task.id,
                success=result.get("success", False),
                output=result,
                error=result.get("error"),
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"VLS Blueprint Definition failed: {e}",
            )

    def get_product_status(self, product_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current product management status."""
        if product_id:
            return {
                "roadmap": self._roadmaps.get(product_id),
                "features": [
                    f for f in self._features.values() if f.get("product_id") == product_id
                ],
                "backlog": self._backlogs.get(product_id, []),
                "milestones": [
                    m for m in self._milestones.values() if m.get("product_id") == product_id
                ],
            }

        return {
            "total_products": len(self._roadmaps),
            "total_features": len(self._features),
            "total_milestones": len(self._milestones),
            "capabilities": self.capabilities,
        }
