"""
Foundry (Foundry) Agent - Foundry.

Codename: Foundry
Core function: Engineering execution, delivery process, and quality assurance.

The Foundry handles all engineering execution tasks:
- Sprint planning and velocity tracking
- Release coordination and delivery
- Quality gates and test automation
- CI/CD pipelines and deployment
- Infrastructure and DevOps operations
- Engineering metrics and productivity

Sphere of influence: Engineering execution, delivery management, quality assurance,
CI/CD automation, deployment strategy, infrastructure operations.

Note: While Forge (Forge) focuses on WHAT to build (architecture, technology choices),
Foundry (Foundry) focuses on HOW to build (delivery process, quality, deployment).
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Manager,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider
from ag3ntwerk.agents.foundry.managers import (
    DeliveryManager,
    QualityManager,
    DevOpsManager,
)
from ag3ntwerk.agents.foundry.specialists import (
    SprintCoordinator,
    ReleaseEngineer,
    QAEngineer,
    QAAutomationEngineer,
    BuildEngineer,
    DeploymentEngineer,
)
from ag3ntwerk.agents.foundry.models import (
    Sprint,
    SprintStatus,
    Release,
    DeliveryStatus,
    QualityGate,
    QualityGateStatus,
    TestSuite,
    TestStatus,
    CodeCoverage,
    Pipeline,
    PipelineStatus,
    Deployment,
    EnvironmentType,
    DeploymentStrategy,
    EngineeringMetrics,
    IncidentReport,
)


# Engineering execution task types
ENGINEERING_CAPABILITIES = [
    # Delivery management
    "sprint_planning",
    "sprint_review",
    "velocity_tracking",
    "release_planning",
    "release_coordination",
    "delivery_tracking",
    "backlog_management",
    # Quality assurance
    "quality_gate_check",
    "test_planning",
    "test_execution",
    "test_automation",
    "coverage_analysis",
    "defect_triage",
    "regression_testing",
    # CI/CD and DevOps
    "pipeline_design",
    "pipeline_execution",
    "build_management",
    "deployment_planning",
    "deployment_execution",
    "rollback_execution",
    "infrastructure_provisioning",
    # Metrics and reporting
    "metrics_analysis",
    "engineering_report",
    "incident_management",
    "post_mortem",
]


class Foundry(Manager):
    """
    Foundry - Foundry.

    The Foundry is responsible for engineering execution within the ag3ntwerk system.
    It manages delivery processes, quality assurance, and DevOps operations.

    Codename: Foundry

    Core Responsibilities:
    - Sprint planning and velocity management
    - Release coordination and delivery
    - Quality gates and test automation
    - CI/CD pipeline management
    - Deployment and rollback operations
    - Engineering metrics and productivity tracking

    Relationship with Forge (Forge):
    - Forge decides WHAT to build (architecture, technology)
    - Foundry decides HOW to build (process, delivery, quality)

    Example:
        ```python
        cengo = Foundry(llm_provider=llm)

        task = Task(
            description="Plan sprint 23 for the platform team",
            task_type="sprint_planning",
            context={"team": "platform", "capacity": 40},
        )
        result = await cengo.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__(
            code="Foundry",
            name="Foundry",
            domain="Engineering Execution, Delivery, Quality, DevOps",
            llm_provider=llm_provider,
        )
        self.codename = "Foundry"

        self.capabilities = ENGINEERING_CAPABILITIES

        # Engineering state
        self._sprints: Dict[str, Sprint] = {}
        self._releases: Dict[str, Release] = {}
        self._quality_gates: Dict[str, QualityGate] = {}
        self._test_suites: Dict[str, TestSuite] = {}
        self._pipelines: Dict[str, Pipeline] = {}
        self._deployments: Dict[str, Deployment] = {}
        self._incidents: Dict[str, IncidentReport] = {}

        # Team metrics
        self._team_metrics: Dict[str, EngineeringMetrics] = {}

        # Initialize managers with specialists
        self._init_managers()

    def _init_managers(self) -> None:
        """Initialize and register managers with their specialists."""
        # Create managers
        dm = DeliveryManager(llm_provider=self.llm_provider)
        qm = QualityManager(llm_provider=self.llm_provider)
        dvm = DevOpsManager(llm_provider=self.llm_provider)

        # Create specialists
        sprint_coordinator = SprintCoordinator(llm_provider=self.llm_provider)
        release_engineer = ReleaseEngineer(llm_provider=self.llm_provider)
        qa_engineer = QAEngineer(llm_provider=self.llm_provider)
        test_automation_engineer = QAAutomationEngineer(llm_provider=self.llm_provider)
        build_engineer = BuildEngineer(llm_provider=self.llm_provider)
        deployment_engineer = DeploymentEngineer(llm_provider=self.llm_provider)

        # Register specialists with appropriate managers
        dm.register_subordinate(sprint_coordinator)
        dm.register_subordinate(release_engineer)
        qm.register_subordinate(qa_engineer)
        qm.register_subordinate(test_automation_engineer)
        dvm.register_subordinate(build_engineer)
        dvm.register_subordinate(deployment_engineer)

        # Register managers with Foundry
        self.register_subordinate(dm)
        self.register_subordinate(qm)
        self.register_subordinate(dvm)

    def can_handle(self, task: Task) -> bool:
        """Check if this is an engineering execution task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute an engineering task."""
        task.status = TaskStatus.IN_PROGRESS

        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            # Delivery handlers
            "sprint_planning": self._handle_sprint_planning,
            "sprint_review": self._handle_sprint_review,
            "velocity_tracking": self._handle_velocity_tracking,
            "release_planning": self._handle_release_planning,
            "release_coordination": self._handle_release_coordination,
            "delivery_tracking": self._handle_delivery_tracking,
            # Quality handlers
            "quality_gate_check": self._handle_quality_gate,
            "test_planning": self._handle_test_planning,
            "test_execution": self._handle_test_execution,
            "coverage_analysis": self._handle_coverage_analysis,
            "defect_triage": self._handle_defect_triage,
            # DevOps handlers
            "pipeline_design": self._handle_pipeline_design,
            "pipeline_execution": self._handle_pipeline_execution,
            "deployment_planning": self._handle_deployment_planning,
            "deployment_execution": self._handle_deployment_execution,
            "rollback_execution": self._handle_rollback,
            # Metrics handlers
            "metrics_analysis": self._handle_metrics_analysis,
            "engineering_report": self._handle_engineering_report,
            "incident_management": self._handle_incident,
            "post_mortem": self._handle_post_mortem,
            # VLS handlers
            "vls_routing_delivery": self._handle_vls_routing_delivery,
        }
        return handlers.get(task_type)

    # =========================================================================
    # Delivery Management Handlers
    # =========================================================================

    async def _handle_sprint_planning(self, task: Task) -> TaskResult:
        """Plan a sprint with capacity and story allocation."""
        team = task.context.get("team", "")
        capacity = task.context.get("capacity", 0)
        stories = task.context.get("stories", [])

        prompt = f"""As the Foundry (Foundry), plan this sprint.

Team: {team}
Capacity (story points): {capacity}
Candidate Stories: {stories}
Description: {task.description}
Context: {task.context}

Create a sprint plan including:
1. Sprint goal aligned with business objectives
2. Story selection and prioritization
3. Capacity allocation and buffer
4. Risk identification
5. Dependencies to resolve
6. Success criteria
7. Daily standup schedule"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "plan_type": "sprint",
                "team": team,
                "capacity": capacity,
                "plan": response,
            },
            metrics={"task_type": "sprint_planning"},
        )

    async def _handle_sprint_review(self, task: Task) -> TaskResult:
        """Review sprint outcomes and generate retrospective."""
        sprint_id = task.context.get("sprint_id", "")
        completed = task.context.get("completed_points", 0)
        committed = task.context.get("committed_points", 0)

        prompt = f"""As the Foundry (Foundry), review this sprint.

Sprint ID: {sprint_id}
Committed Points: {committed}
Completed Points: {completed}
Velocity: {(completed/committed*100) if committed > 0 else 0:.1f}%
Description: {task.description}
Context: {task.context}

Provide sprint review including:
1. Achievement summary
2. Velocity analysis
3. What went well
4. What could be improved
5. Action items for next sprint
6. Team recognition
7. Process improvements"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "review_type": "sprint",
                "sprint_id": sprint_id,
                "velocity": (completed / committed * 100) if committed > 0 else 0,
                "review": response,
            },
        )

    async def _handle_velocity_tracking(self, task: Task) -> TaskResult:
        """Track and analyze team velocity."""
        team = task.context.get("team", "")
        sprints = task.context.get("sprint_history", [])

        prompt = f"""As the Foundry (Foundry), analyze velocity.

Team: {team}
Sprint History: {sprints}
Description: {task.description}
Context: {task.context}

Analyze velocity including:
1. Current velocity trend
2. Historical comparison
3. Capacity utilization
4. Predictability metrics
5. Bottleneck identification
6. Improvement recommendations
7. Forecasting for next sprints"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "velocity",
                "team": team,
                "analysis": response,
            },
        )

    async def _handle_release_planning(self, task: Task) -> TaskResult:
        """Plan a software release."""
        version = task.context.get("version", "")
        features = task.context.get("features", [])
        target_date = task.context.get("target_date", "")

        prompt = f"""As the Foundry (Foundry), plan this release.

Version: {version}
Target Date: {target_date}
Features: {features}
Description: {task.description}
Context: {task.context}

Create release plan including:
1. Release scope and objectives
2. Feature freeze date
3. Testing phases
4. Deployment strategy
5. Rollback plan
6. Communication plan
7. Go/No-go criteria
8. Post-release monitoring"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "plan_type": "release",
                "version": version,
                "target_date": target_date,
                "plan": response,
            },
        )

    async def _handle_release_coordination(self, task: Task) -> TaskResult:
        """Coordinate release execution."""
        release_id = task.context.get("release_id", "")

        prompt = f"""As the Foundry (Foundry), coordinate this release.

Release ID: {release_id}
Description: {task.description}
Context: {task.context}

Provide release coordination including:
1. Current release status
2. Checklist verification
3. Stakeholder communication
4. Go/No-go decision
5. Deployment sequence
6. Monitoring plan
7. Escalation contacts"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "coordination_type": "release",
                "release_id": release_id,
                "coordination": response,
            },
        )

    async def _handle_delivery_tracking(self, task: Task) -> TaskResult:
        """Track overall delivery progress."""
        prompt = f"""As the Foundry (Foundry), track delivery.

Description: {task.description}
Context: {task.context}

Provide delivery tracking including:
1. Current deliverables status
2. Timeline adherence
3. Blockers and risks
4. Resource utilization
5. Quality metrics
6. Forecast to completion
7. Recommended actions"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "tracking_type": "delivery",
                "tracking": response,
            },
        )

    # =========================================================================
    # Quality Assurance Handlers
    # =========================================================================

    async def _handle_quality_gate(self, task: Task) -> TaskResult:
        """Evaluate quality gate criteria."""
        gate_id = task.context.get("gate_id", "")
        metrics = task.context.get("metrics", {})

        # Check if gate exists in memory
        if gate_id and gate_id in self._quality_gates:
            gate = self._quality_gates[gate_id]
            status = gate.evaluate(metrics)
            return TaskResult(
                task_id=task.id,
                success=True,
                output={
                    "gate_id": gate_id,
                    "gate_name": gate.name,
                    "status": status.value,
                    "is_blocking": gate.is_blocking,
                    "metrics": metrics,
                },
            )

        prompt = f"""As the Foundry (Foundry), evaluate quality gate.

Gate ID: {gate_id}
Metrics: {metrics}
Description: {task.description}
Context: {task.context}

Evaluate quality gate including:
1. Gate criteria assessment
2. Pass/fail determination
3. Metric analysis
4. Gap identification
5. Remediation steps if failing
6. Risk assessment
7. Recommendation (proceed/block)"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "gate_type": "quality",
                "gate_id": gate_id,
                "evaluation": response,
            },
        )

    async def _handle_test_planning(self, task: Task) -> TaskResult:
        """Plan testing strategy."""
        scope = task.context.get("scope", "")
        test_types = task.context.get("test_types", ["unit", "integration", "e2e"])

        prompt = f"""As the Foundry (Foundry), plan testing.

Scope: {scope}
Test Types: {test_types}
Description: {task.description}
Context: {task.context}

Create test plan including:
1. Test objectives
2. Scope and coverage targets
3. Test types and priorities
4. Environment requirements
5. Test data needs
6. Resource allocation
7. Timeline
8. Risk mitigation"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "plan_type": "test",
                "scope": scope,
                "test_types": test_types,
                "plan": response,
            },
        )

    async def _handle_test_execution(self, task: Task) -> TaskResult:
        """Execute or review test execution."""
        suite_id = task.context.get("suite_id", "")

        prompt = f"""As the Foundry (Foundry), manage test execution.

Test Suite: {suite_id}
Description: {task.description}
Context: {task.context}

Provide test execution guidance:
1. Pre-execution checklist
2. Execution sequence
3. Monitoring approach
4. Failure handling
5. Result analysis
6. Report generation
7. Next steps"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "execution_type": "test",
                "suite_id": suite_id,
                "guidance": response,
            },
        )

    async def _handle_coverage_analysis(self, task: Task) -> TaskResult:
        """Analyze code coverage metrics."""
        coverage_data = task.context.get("coverage", {})

        prompt = f"""As the Foundry (Foundry), analyze coverage.

Coverage Data: {coverage_data}
Description: {task.description}
Context: {task.context}

Analyze code coverage including:
1. Overall coverage assessment
2. Coverage by component
3. Critical path coverage
4. Coverage trends
5. Gap identification
6. Priority areas for improvement
7. Recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "coverage",
                "analysis": response,
            },
        )

    async def _handle_defect_triage(self, task: Task) -> TaskResult:
        """Triage and prioritize defects."""
        defects = task.context.get("defects", [])

        prompt = f"""As the Foundry (Foundry), triage defects.

Defects: {defects}
Description: {task.description}
Context: {task.context}

Triage defects including:
1. Severity assessment
2. Priority assignment
3. Root cause categorization
4. Assignment recommendations
5. Resolution timeline
6. Risk to release
7. Workarounds available"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "triage_type": "defect",
                "defect_count": len(defects),
                "triage": response,
            },
        )

    # =========================================================================
    # DevOps Handlers
    # =========================================================================

    async def _handle_pipeline_design(self, task: Task) -> TaskResult:
        """Design CI/CD pipeline."""
        project = task.context.get("project", "")
        technology = task.context.get("technology", "")

        prompt = f"""As the Foundry (Foundry), design CI/CD pipeline.

Project: {project}
Technology Stack: {technology}
Description: {task.description}
Context: {task.context}

Design pipeline including:
1. Pipeline stages (build, test, deploy)
2. Trigger configuration
3. Quality gates
4. Artifact management
5. Environment promotion
6. Notification strategy
7. Security scanning
8. Performance considerations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "design_type": "pipeline",
                "project": project,
                "design": response,
            },
        )

    async def _handle_pipeline_execution(self, task: Task) -> TaskResult:
        """Manage pipeline execution."""
        pipeline_id = task.context.get("pipeline_id", "")

        prompt = f"""As the Foundry (Foundry), manage pipeline.

Pipeline ID: {pipeline_id}
Description: {task.description}
Context: {task.context}

Provide pipeline management including:
1. Current status
2. Stage progress
3. Failure handling
4. Artifact verification
5. Manual gate decisions
6. Promotion criteria
7. Notification status"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "execution_type": "pipeline",
                "pipeline_id": pipeline_id,
                "status": response,
            },
        )

    async def _handle_deployment_planning(self, task: Task) -> TaskResult:
        """Plan deployment strategy."""
        environment = task.context.get("environment", "staging")
        strategy = task.context.get("strategy", "rolling")

        prompt = f"""As the Foundry (Foundry), plan deployment.

Environment: {environment}
Strategy: {strategy}
Description: {task.description}
Context: {task.context}

Create deployment plan including:
1. Pre-deployment checklist
2. Deployment sequence
3. Health check criteria
4. Traffic management
5. Monitoring setup
6. Rollback triggers
7. Communication plan
8. Post-deployment verification"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "plan_type": "deployment",
                "environment": environment,
                "strategy": strategy,
                "plan": response,
            },
        )

    async def _handle_deployment_execution(self, task: Task) -> TaskResult:
        """Execute deployment."""
        deployment_id = task.context.get("deployment_id", "")
        environment = task.context.get("environment", "staging")

        prompt = f"""As the Foundry (Foundry), execute deployment.

Deployment ID: {deployment_id}
Environment: {environment}
Description: {task.description}
Context: {task.context}

Provide deployment execution guidance:
1. Pre-flight checks
2. Execution steps
3. Progress monitoring
4. Health verification
5. Traffic shift management
6. Incident response readiness
7. Success criteria"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "execution_type": "deployment",
                "deployment_id": deployment_id,
                "environment": environment,
                "guidance": response,
            },
        )

    async def _handle_rollback(self, task: Task) -> TaskResult:
        """Execute rollback operation."""
        deployment_id = task.context.get("deployment_id", "")
        reason = task.context.get("reason", "")

        prompt = f"""As the Foundry (Foundry), execute rollback.

Deployment ID: {deployment_id}
Reason: {reason}
Description: {task.description}
Context: {task.context}

Execute rollback including:
1. Impact assessment
2. Rollback procedure
3. Data handling
4. Service restoration steps
5. Verification process
6. Communication updates
7. Post-mortem scheduling"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "operation_type": "rollback",
                "deployment_id": deployment_id,
                "reason": reason,
                "procedure": response,
            },
        )

    # =========================================================================
    # Metrics and Reporting Handlers
    # =========================================================================

    async def _handle_metrics_analysis(self, task: Task) -> TaskResult:
        """Analyze engineering metrics."""
        team = task.context.get("team", "")
        period = task.context.get("period", "weekly")

        prompt = f"""As the Foundry (Foundry), analyze metrics.

Team: {team}
Period: {period}
Description: {task.description}
Context: {task.context}

Analyze engineering metrics including:
1. DORA metrics (lead time, deployment frequency, MTTR, change failure rate)
2. Velocity and predictability
3. Quality metrics (defect density, coverage)
4. Productivity indicators
5. Trend analysis
6. Benchmark comparison
7. Improvement recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "metrics",
                "team": team,
                "period": period,
                "analysis": response,
            },
        )

    async def _handle_engineering_report(self, task: Task) -> TaskResult:
        """Generate engineering status report."""
        report_type = task.context.get("report_type", "weekly")

        prompt = f"""As the Foundry (Foundry), generate report.

Report Type: {report_type}
Description: {task.description}
Context: {task.context}

Generate engineering report including:
1. Agent summary
2. Delivery status
3. Quality metrics
4. Team velocity
5. Risks and blockers
6. Upcoming milestones
7. Resource needs
8. Recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "report_type": report_type,
                "report": response,
            },
        )

    async def _handle_incident(self, task: Task) -> TaskResult:
        """Manage engineering incident."""
        incident_id = task.context.get("incident_id", "")
        severity = task.context.get("severity", "medium")

        prompt = f"""As the Foundry (Foundry), manage incident.

Incident ID: {incident_id}
Severity: {severity}
Description: {task.description}
Context: {task.context}

Manage incident including:
1. Impact assessment
2. Immediate actions
3. Communication plan
4. Resolution steps
5. Resource mobilization
6. Status updates
7. Resolution verification"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "management_type": "incident",
                "incident_id": incident_id,
                "severity": severity,
                "response": response,
            },
        )

    async def _handle_post_mortem(self, task: Task) -> TaskResult:
        """Conduct post-mortem analysis."""
        incident_id = task.context.get("incident_id", "")

        prompt = f"""As the Foundry (Foundry), conduct post-mortem.

Incident ID: {incident_id}
Description: {task.description}
Context: {task.context}

Conduct blameless post-mortem including:
1. Incident timeline
2. Root cause analysis
3. Contributing factors
4. What went well
5. What could be improved
6. Action items with owners
7. Process improvements
8. Prevention measures"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "post_mortem",
                "incident_id": incident_id,
                "analysis": response,
            },
        )

    # =========================================================================
    # Fallback Handler
    # =========================================================================

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM when no specific handler exists."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider and no handler for task type",
            )

        prompt = f"""As the Foundry (Foundry) specializing in
engineering execution, delivery, and DevOps, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough engineering-focused response."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )

    # =========================================================================
    # Engineering Management Methods
    # =========================================================================

    def register_sprint(self, sprint: Sprint) -> str:
        """Register a sprint."""
        self._sprints[sprint.id] = sprint
        return sprint.id

    def register_release(self, release: Release) -> str:
        """Register a release."""
        self._releases[release.id] = release
        return release.id

    def register_quality_gate(self, gate: QualityGate) -> str:
        """Register a quality gate."""
        self._quality_gates[gate.id] = gate
        return gate.id

    def register_test_suite(self, suite: TestSuite) -> str:
        """Register a test suite."""
        self._test_suites[suite.id] = suite
        return suite.id

    def register_pipeline(self, pipeline: Pipeline) -> str:
        """Register a CI/CD pipeline."""
        self._pipelines[pipeline.id] = pipeline
        return pipeline.id

    def register_deployment(self, deployment: Deployment) -> str:
        """Register a deployment."""
        self._deployments[deployment.id] = deployment
        return deployment.id

    def register_incident(self, incident: IncidentReport) -> str:
        """Register an incident."""
        self._incidents[incident.id] = incident
        return incident.id

    async def _handle_vls_routing_delivery(self, task: Task) -> TaskResult:
        """Execute VLS Stage: Routing & Delivery."""
        from ag3ntwerk.modules.vls.stages import execute_routing_delivery

        try:
            result = await execute_routing_delivery(task.context)

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
                error=f"VLS Routing & Delivery failed: {e}",
            )

    def get_sprint(self, sprint_id: str) -> Optional[Sprint]:
        """Get a sprint by ID."""
        return self._sprints.get(sprint_id)

    def get_active_sprints(self) -> List[Sprint]:
        """Get all active sprints."""
        return [s for s in self._sprints.values() if s.is_active]

    def get_release(self, release_id: str) -> Optional[Release]:
        """Get a release by ID."""
        return self._releases.get(release_id)

    def get_pending_releases(self) -> List[Release]:
        """Get releases that haven't been deployed."""
        return [
            r
            for r in self._releases.values()
            if r.status in (DeliveryStatus.PLANNED, DeliveryStatus.IN_PROGRESS)
        ]

    def get_failing_quality_gates(self) -> List[QualityGate]:
        """Get quality gates that are currently failing."""
        # Note: Would need metrics context to evaluate
        return [g for g in self._quality_gates.values() if g.is_blocking and g.is_active]

    def get_engineering_status(self) -> Dict[str, Any]:
        """Get current engineering status."""
        return {
            "sprints": {
                "total": len(self._sprints),
                "active": len(self.get_active_sprints()),
            },
            "releases": {
                "total": len(self._releases),
                "pending": len(self.get_pending_releases()),
            },
            "quality_gates": len(self._quality_gates),
            "test_suites": len(self._test_suites),
            "pipelines": {
                "total": len(self._pipelines),
                "running": len([p for p in self._pipelines.values() if p.is_running]),
            },
            "deployments": len(self._deployments),
            "incidents": {
                "total": len(self._incidents),
                "open": len([i for i in self._incidents.values() if i.status == "open"]),
            },
            "capabilities": self.capabilities,
        }

    def get_engineering_metrics(self) -> EngineeringMetrics:
        """Get current engineering metrics."""
        return EngineeringMetrics(
            total_sprints=len(self._sprints),
            active_sprints=len(self.get_active_sprints()),
            total_releases=len(self._releases),
            pending_releases=len(self.get_pending_releases()),
            active_pipelines=len([p for p in self._pipelines.values() if p.is_running]),
            total_deployments=len(self._deployments),
            deployment_count=len(self._deployments),
            quality_gates_active=len([g for g in self._quality_gates.values() if g.is_active]),
            test_suites=len(self._test_suites),
            open_incidents=len([i for i in self._incidents.values() if i.status == "open"]),
        )
