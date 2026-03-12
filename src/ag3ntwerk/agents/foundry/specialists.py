"""
Specialists for the Foundry (Foundry) agent.

Specialists are the workers that perform specific operational tasks
within engineering execution.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Specialist,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider


class SprintCoordinator(Specialist):
    """
    Specialist responsible for sprint coordination.

    Handles sprint planning, tracking, and retrospectives.

    Capabilities:
    - Sprint planning
    - Sprint review
    - Velocity tracking
    - Backlog grooming
    - Team capacity planning
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="SC",
            name="Sprint Coordinator",
            domain="Sprint Management, Velocity, Agile Ceremonies",
            capabilities=[
                "sprint_planning",
                "sprint_review",
                "velocity_tracking",
                "delivery_tracking",
                "backlog_management",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute sprint coordination task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "sprint_planning": self._handle_planning,
            "sprint_review": self._handle_review,
            "velocity_tracking": self._handle_velocity,
            "delivery_tracking": self._handle_delivery,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_planning(self, task: Task) -> TaskResult:
        """Handle sprint planning."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Sprint Coordinator, plan this sprint:

Description: {task.description}
Context: {task.context}

Create sprint plan including:
1. Sprint goal definition
2. Story selection criteria
3. Capacity allocation
4. Risk identification
5. Dependencies mapping
6. Acceptance criteria
7. Definition of done"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"sprint_plan": response, "specialist": self.code},
        )

    async def _handle_review(self, task: Task) -> TaskResult:
        """Handle sprint review."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Sprint Coordinator, review this sprint:

Description: {task.description}
Context: {task.context}

Provide sprint review including:
1. Completed vs committed work
2. Demo summary
3. Feedback collected
4. Blockers encountered
5. Lessons learned
6. Action items"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"sprint_review": response, "specialist": self.code},
        )

    async def _handle_velocity(self, task: Task) -> TaskResult:
        """Handle velocity tracking."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Sprint Coordinator, analyze velocity:

Description: {task.description}
Context: {task.context}

Analyze velocity including:
1. Historical trends
2. Predictability index
3. Capacity utilization
4. Impediment impact
5. Improvement suggestions"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"velocity_analysis": response, "specialist": self.code},
        )

    async def _handle_delivery(self, task: Task) -> TaskResult:
        """Handle delivery tracking."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Sprint Coordinator, track delivery:

Description: {task.description}
Context: {task.context}

Provide delivery tracking:
1. Current progress
2. Burndown status
3. Risks to completion
4. Dependencies status
5. Recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"delivery_status": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic sprint coordination task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Sprint Coordinator, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide sprint coordination guidance."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class ReleaseEngineer(Specialist):
    """
    Specialist responsible for release engineering.

    Handles release planning, coordination, and execution.

    Capabilities:
    - Release planning
    - Release coordination
    - Version management
    - Changelog generation
    - Release communication
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="RE",
            name="Release Engineer",
            domain="Release Management, Version Control, Coordination",
            capabilities=[
                "release_planning",
                "release_coordination",
                "version_management",
                "changelog_generation",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute release engineering task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "release_planning": self._handle_planning,
            "release_coordination": self._handle_coordination,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_planning(self, task: Task) -> TaskResult:
        """Handle release planning."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Release Engineer, plan this release:

Description: {task.description}
Context: {task.context}

Create release plan including:
1. Version numbering
2. Feature scope
3. Testing milestones
4. Documentation requirements
5. Communication plan
6. Rollback strategy
7. Success criteria"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"release_plan": response, "specialist": self.code},
        )

    async def _handle_coordination(self, task: Task) -> TaskResult:
        """Handle release coordination."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Release Engineer, coordinate this release:

Description: {task.description}
Context: {task.context}

Provide coordination guidance:
1. Stakeholder communication
2. Go/No-go checklist
3. Deployment sequence
4. Verification steps
5. Incident escalation"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"release_coordination": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic release task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Release Engineer, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide release engineering guidance."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class QAEngineer(Specialist):
    """
    Specialist responsible for quality assurance.

    Handles test planning, execution, and defect management.

    Capabilities:
    - Test planning
    - Test execution
    - Defect triage
    - Quality assessment
    - Test reporting
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="QAE",
            name="QA Engineer",
            domain="Quality Assurance, Testing, Defect Management",
            capabilities=[
                "quality_gate_check",
                "test_planning",
                "test_execution",
                "defect_triage",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute QA task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "quality_gate_check": self._handle_quality_gate,
            "test_planning": self._handle_test_planning,
            "test_execution": self._handle_test_execution,
            "defect_triage": self._handle_defect_triage,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_quality_gate(self, task: Task) -> TaskResult:
        """Handle quality gate evaluation."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a QA Engineer, evaluate quality gate:

Description: {task.description}
Context: {task.context}

Evaluate quality gate including:
1. Criteria checklist
2. Metric assessment
3. Risk evaluation
4. Pass/fail decision
5. Remediation guidance"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"quality_gate_evaluation": response, "specialist": self.code},
        )

    async def _handle_test_planning(self, task: Task) -> TaskResult:
        """Handle test planning."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a QA Engineer, create test plan:

Description: {task.description}
Context: {task.context}

Create test plan including:
1. Test objectives
2. Scope and coverage
3. Test types needed
4. Test data requirements
5. Environment setup
6. Timeline and resources"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"test_plan": response, "specialist": self.code},
        )

    async def _handle_test_execution(self, task: Task) -> TaskResult:
        """Handle test execution."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a QA Engineer, guide test execution:

Description: {task.description}
Context: {task.context}

Provide test execution guidance:
1. Execution sequence
2. Priority order
3. Environment verification
4. Result recording
5. Issue escalation"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"test_execution_guidance": response, "specialist": self.code},
        )

    async def _handle_defect_triage(self, task: Task) -> TaskResult:
        """Handle defect triage."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a QA Engineer, triage defects:

Description: {task.description}
Context: {task.context}

Triage defects including:
1. Severity classification
2. Priority assignment
3. Root cause hypothesis
4. Reproduction steps
5. Assignment recommendation"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"defect_triage": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic QA task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a QA Engineer, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide quality assurance guidance."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class QAAutomationEngineer(Specialist):
    """
    Specialist responsible for test automation.

    Handles automation framework, coverage analysis, and
    regression testing.

    Capabilities:
    - Test automation
    - Coverage analysis
    - Regression testing
    - Framework development
    - CI integration
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="TAE",
            name="QA Automation Engineer",
            domain="Test Automation, Coverage, Regression",
            capabilities=[
                "test_automation",
                "coverage_analysis",
                "regression_testing",
                "framework_development",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute test automation task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "test_automation": self._handle_automation,
            "coverage_analysis": self._handle_coverage,
            "regression_testing": self._handle_regression,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_automation(self, task: Task) -> TaskResult:
        """Handle test automation."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Test Automation Engineer, automate tests:

Description: {task.description}
Context: {task.context}

Provide automation guidance:
1. Automation candidates
2. Framework selection
3. Test structure
4. Data management
5. Maintenance strategy"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"automation_guidance": response, "specialist": self.code},
        )

    async def _handle_coverage(self, task: Task) -> TaskResult:
        """Handle coverage analysis."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Test Automation Engineer, analyze coverage:

Description: {task.description}
Context: {task.context}

Analyze coverage including:
1. Current coverage metrics
2. Gap identification
3. Critical path coverage
4. Improvement priorities
5. Target recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"coverage_analysis": response, "specialist": self.code},
        )

    async def _handle_regression(self, task: Task) -> TaskResult:
        """Handle regression testing."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Test Automation Engineer, manage regression:

Description: {task.description}
Context: {task.context}

Provide regression testing guidance:
1. Test selection strategy
2. Execution optimization
3. Flaky test handling
4. Result analysis
5. Maintenance needs"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"regression_guidance": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic automation task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Test Automation Engineer, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide test automation guidance."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class BuildEngineer(Specialist):
    """
    Specialist responsible for build engineering.

    Handles CI/CD pipeline design, build automation, and
    artifact management.

    Capabilities:
    - Pipeline design
    - Pipeline execution
    - Build management
    - Artifact management
    - CI optimization
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="BE",
            name="Build Engineer",
            domain="Build Automation, CI/CD Pipelines, Artifacts",
            capabilities=[
                "pipeline_design",
                "pipeline_execution",
                "build_management",
                "artifact_management",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute build engineering task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "pipeline_design": self._handle_pipeline_design,
            "pipeline_execution": self._handle_pipeline_execution,
            "build_management": self._handle_build,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_pipeline_design(self, task: Task) -> TaskResult:
        """Handle pipeline design."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Build Engineer, design CI/CD pipeline:

Description: {task.description}
Context: {task.context}

Design pipeline including:
1. Stage definition
2. Trigger configuration
3. Quality gates
4. Artifact handling
5. Notification setup
6. Security scanning"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"pipeline_design": response, "specialist": self.code},
        )

    async def _handle_pipeline_execution(self, task: Task) -> TaskResult:
        """Handle pipeline execution."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Build Engineer, manage pipeline execution:

Description: {task.description}
Context: {task.context}

Provide execution guidance:
1. Pre-flight checks
2. Stage monitoring
3. Failure handling
4. Artifact verification
5. Promotion criteria"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"pipeline_execution": response, "specialist": self.code},
        )

    async def _handle_build(self, task: Task) -> TaskResult:
        """Handle build management."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Build Engineer, manage builds:

Description: {task.description}
Context: {task.context}

Provide build management:
1. Build configuration
2. Dependency management
3. Optimization strategies
4. Caching approach
5. Reproducibility"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"build_management": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic build task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Build Engineer, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide build engineering guidance."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class DeploymentEngineer(Specialist):
    """
    Specialist responsible for deployment engineering.

    Handles deployment planning, execution, and rollback
    operations.

    Capabilities:
    - Deployment planning
    - Deployment execution
    - Rollback execution
    - Infrastructure provisioning
    - Environment management
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="DE",
            name="Deployment Engineer",
            domain="Deployment, Infrastructure, Rollback",
            capabilities=[
                "deployment_planning",
                "deployment_execution",
                "rollback_execution",
                "infrastructure_provisioning",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute deployment task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "deployment_planning": self._handle_planning,
            "deployment_execution": self._handle_execution,
            "rollback_execution": self._handle_rollback,
            "infrastructure_provisioning": self._handle_infrastructure,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_planning(self, task: Task) -> TaskResult:
        """Handle deployment planning."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Deployment Engineer, plan deployment:

Description: {task.description}
Context: {task.context}

Create deployment plan:
1. Pre-deployment checklist
2. Deployment sequence
3. Health check criteria
4. Traffic management
5. Rollback triggers
6. Communication plan"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"deployment_plan": response, "specialist": self.code},
        )

    async def _handle_execution(self, task: Task) -> TaskResult:
        """Handle deployment execution."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Deployment Engineer, execute deployment:

Description: {task.description}
Context: {task.context}

Guide deployment execution:
1. Environment verification
2. Deployment steps
3. Health monitoring
4. Traffic shifting
5. Validation checks"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"deployment_execution": response, "specialist": self.code},
        )

    async def _handle_rollback(self, task: Task) -> TaskResult:
        """Handle rollback execution."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Deployment Engineer, execute rollback:

Description: {task.description}
Context: {task.context}

Execute rollback:
1. Impact assessment
2. Rollback procedure
3. Data considerations
4. Service restoration
5. Verification steps"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"rollback_execution": response, "specialist": self.code},
        )

    async def _handle_infrastructure(self, task: Task) -> TaskResult:
        """Handle infrastructure provisioning."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Deployment Engineer, provision infrastructure:

Description: {task.description}
Context: {task.context}

Provision infrastructure:
1. Resource requirements
2. Configuration approach
3. Security setup
4. Networking
5. Monitoring integration"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"infrastructure_provisioning": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic deployment task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Deployment Engineer, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide deployment engineering guidance."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )
