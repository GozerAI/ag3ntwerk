"""
Forge (Forge) Agent - Forge.

Codename: Forge
Core function: Build and evolve the technical foundation.

The Forge handles all development-related tasks:
- Code generation and review
- Bug fixing and refactoring
- Testing and quality assurance
- Architecture and design
- Deployment and DevOps

Sphere of influence: Architecture, platform choices, engineering standards,
build/buy decisions, scalability, reliability engineering, technical talent strategy.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Manager,
    Specialist,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider
from ag3ntwerk.agents.forge.managers import (
    ArchitectureManager,
    CodeQualityManager,
    TestingManager,
    DevOpsManager,
)
from ag3ntwerk.agents.forge.specialists import (
    SeniorDeveloper,
    CodeReviewer,
    SystemArchitect,
    QAEngineer,
    DevOpsEngineer,
    TechnicalWriter,
)


# Development task types this agent can handle
DEVELOPMENT_CAPABILITIES = [
    "code_review",
    "code_generation",
    "bug_fix",
    "refactoring",
    "testing",
    "deployment",
    "architecture",
    "documentation",
    "debugging",
    "optimization",
    "api_design",
    "database_design",
    # Manager-level task types
    "system_design",
    "tech_selection",
    "scalability_planning",
    "code_standards",
    "best_practices",
    "code_analysis",
    "technical_debt",
    "test_generation",
    "test_strategy",
    "test_coverage",
    "qa_planning",
    "test_automation",
    "ci_cd",
    "infrastructure",
    "monitoring",
    "containerization",
    "orchestration",
    # Specialist-level task types
    "implementation",
    "security_review",
    "quality_assessment",
    "standards_check",
    "pr_review",
    "architecture_design",
    "pattern_selection",
    "tech_evaluation",
    "scalability_design",
    "test_creation",
    "test_execution",
    "regression_testing",
    "ci_cd_implementation",
    "infrastructure_automation",
    "deployment_automation",
    "monitoring_setup",
    "api_documentation",
    "code_documentation",
    "technical_guide",
    "architecture_documentation",
    "user_documentation",
]

# Routing from task types to managers
MANAGER_ROUTING = {
    # ArchitectureManager tasks
    "architecture": "AM",
    "system_design": "AM",
    "api_design": "AM",
    "database_design": "AM",
    "tech_selection": "AM",
    "scalability_planning": "AM",
    # CodeQualityManager tasks
    "code_review": "CQM",
    "refactoring": "CQM",
    "code_standards": "CQM",
    "best_practices": "CQM",
    "code_analysis": "CQM",
    "technical_debt": "CQM",
    # TestingManager tasks
    "testing": "TEM",
    "test_generation": "TEM",
    "test_strategy": "TEM",
    "test_coverage": "TEM",
    "qa_planning": "TEM",
    "test_automation": "TEM",
    # DevOpsManager tasks
    "deployment": "DOM",
    "ci_cd": "DOM",
    "infrastructure": "DOM",
    "monitoring": "DOM",
    "containerization": "DOM",
    "orchestration": "DOM",
}


class Forge(Manager):
    """
    Forge - Forge.

    The Forge is responsible for all development operations within the
    ag3ntwerk system. It manages development specialists and coordinates
    engineering workflows.

    Codename: Forge

    Core Responsibilities:
    - Code generation and review
    - Bug fixing and debugging
    - Testing and quality assurance
    - Architecture and system design
    - Deployment and CI/CD

    Example:
        ```python
        cto = Forge(llm_provider=llm)

        task = Task(
            description="Review authentication implementation",
            task_type="code_review",
            context={"file": "src/auth/login.py"},
        )
        result = await cto.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__(
            code="Forge",
            name="Forge",
            domain="Development, Engineering, Architecture",
            llm_provider=llm_provider,
        )
        self.codename = "Forge"

        self.capabilities = DEVELOPMENT_CAPABILITIES

        # Development-specific state
        self._active_projects: Dict[str, Any] = {}
        self._tech_stack: Dict[str, List[str]] = {}
        self._code_standards: Dict[str, str] = {}

        # Initialize and register managers with their specialists
        self._init_managers()

    def can_handle(self, task: Task) -> bool:
        """Check if this is a development-related task."""
        return task.task_type in self.capabilities

    def _init_managers(self) -> None:
        """Initialize and register managers with their specialists."""
        # Create managers
        arch_mgr = ArchitectureManager(llm_provider=self.llm_provider)
        quality_mgr = CodeQualityManager(llm_provider=self.llm_provider)
        testing_mgr = TestingManager(llm_provider=self.llm_provider)
        devops_mgr = DevOpsManager(llm_provider=self.llm_provider)

        # Create specialists
        senior_dev = SeniorDeveloper(llm_provider=self.llm_provider)
        code_reviewer = CodeReviewer(llm_provider=self.llm_provider)
        sys_architect = SystemArchitect(llm_provider=self.llm_provider)
        qa_engineer = QAEngineer(llm_provider=self.llm_provider)
        devops_engineer = DevOpsEngineer(llm_provider=self.llm_provider)
        tech_writer = TechnicalWriter(llm_provider=self.llm_provider)

        # Register specialists with appropriate managers
        arch_mgr.register_subordinate(sys_architect)
        quality_mgr.register_subordinate(senior_dev)
        quality_mgr.register_subordinate(code_reviewer)
        quality_mgr.register_subordinate(tech_writer)
        testing_mgr.register_subordinate(qa_engineer)
        devops_mgr.register_subordinate(devops_engineer)

        # Register managers with Forge
        self.register_subordinate(arch_mgr)
        self.register_subordinate(quality_mgr)
        self.register_subordinate(testing_mgr)
        self.register_subordinate(devops_mgr)

    def _route_to_manager(self, task_type: str) -> Optional[str]:
        """Route task to appropriate manager."""
        return MANAGER_ROUTING.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute a development task, routing through managers when appropriate."""
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
            "code_review": self._handle_code_review,
            "code_generation": self._handle_code_generation,
            "bug_fix": self._handle_bug_fix,
            "refactoring": self._handle_refactoring,
            "testing": self._handle_testing,
            "architecture": self._handle_architecture,
            "debugging": self._handle_debugging,
            # VLS handlers
            "vls_build_deployment": self._handle_vls_build_deployment,
        }
        return handlers.get(task_type)

    async def _handle_code_review(self, task: Task) -> TaskResult:
        """Perform code review."""
        code = task.context.get("code", "")
        file_path = task.context.get("file", "unknown")

        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider for code review",
            )

        prompt = f"""As a senior developer (Forge), perform a code review.

File: {file_path}
Description: {task.description}

Code to review:
```
{code}
```

Provide a thorough review covering:
- Code quality and readability
- Potential bugs or edge cases
- Performance considerations
- Security issues
- Best practices and patterns
- Suggestions for improvement

Format as:
SUMMARY: Brief overall assessment

ISSUES:
- [CRITICAL/HIGH/MEDIUM/LOW] Description

SUGGESTIONS:
- Improvement recommendations"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Code review failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "review_type": "code_review",
                "file": file_path,
                "review": response,
            },
            metrics={"task_type": "code_review"},
        )

    async def _handle_code_generation(self, task: Task) -> TaskResult:
        """Generate code based on requirements."""
        language = task.context.get("language", "python")
        requirements = task.description

        prompt = f"""As a senior developer (Forge), generate code.

Language: {language}
Requirements: {requirements}
Context: {task.context}

Generate clean, well-documented code that:
- Follows best practices for {language}
- Is well-structured and maintainable
- Includes appropriate error handling
- Has clear comments where needed

Provide the code with explanations of key design decisions."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Code generation failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "generation_type": "code",
                "language": language,
                "result": response,
            },
        )

    async def _handle_bug_fix(self, task: Task) -> TaskResult:
        """Analyze and fix bugs."""
        code = task.context.get("code", "")
        error = task.context.get("error", "unknown error")

        prompt = f"""As a senior developer (Forge), fix this bug.

Bug Description: {task.description}
Error: {error}

Problematic Code:
```
{code}
```

Analyze the bug and provide:
1. Root cause analysis
2. Fixed code
3. Explanation of the fix
4. How to prevent similar bugs"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Bug fix failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "fix_type": "bug_fix",
                "analysis": response,
            },
        )

    async def _handle_refactoring(self, task: Task) -> TaskResult:
        """Refactor code for improvement."""
        code = task.context.get("code", "")
        goal = task.context.get("goal", "improve code quality")

        prompt = f"""As a senior developer (Forge), refactor this code.

Goal: {goal}
Description: {task.description}

Original Code:
```
{code}
```

Provide:
1. Refactored code
2. Explanation of changes made
3. Benefits of the refactoring
4. Any trade-offs or considerations"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Refactoring failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "refactor_type": "refactoring",
                "result": response,
            },
        )

    async def _handle_testing(self, task: Task) -> TaskResult:
        """Generate or review tests."""
        code = task.context.get("code", "")
        test_type = task.context.get("test_type", "unit")

        prompt = f"""As a senior developer (Forge), create tests.

Test Type: {test_type}
Description: {task.description}

Code to Test:
```
{code}
```

Generate comprehensive tests including:
- Happy path tests
- Edge cases
- Error handling tests
- Appropriate mocking where needed

Follow testing best practices for the language/framework."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Testing failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "test_type": test_type,
                "tests": response,
            },
        )

    async def _handle_architecture(self, task: Task) -> TaskResult:
        """Design system architecture."""
        requirements = task.description
        constraints = task.context.get("constraints", [])

        prompt = f"""As a senior architect (Forge), design system architecture.

Requirements: {requirements}
Constraints: {constraints}
Context: {task.context}

Provide an architecture design including:
1. High-level system overview
2. Component breakdown
3. Data flow diagrams (described)
4. Technology recommendations
5. Scalability considerations
6. Potential challenges and mitigations"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Architecture review failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "design_type": "architecture",
                "design": response,
            },
        )

    async def _handle_debugging(self, task: Task) -> TaskResult:
        """Debug code issues."""
        code = task.context.get("code", "")
        symptoms = task.context.get("symptoms", task.description)

        prompt = f"""As a senior developer (Forge), debug this issue.

Symptoms: {symptoms}
Description: {task.description}

Code:
```
{code}
```

Provide a debugging analysis:
1. Possible causes (ranked by likelihood)
2. Diagnostic steps to confirm each cause
3. Recommended fixes for each scenario
4. Prevention strategies"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Debugging failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "debug_type": "analysis",
                "analysis": response,
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

        prompt = f"""As the Forge (Forge) specializing in development,
handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough development-focused response."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"LLM handling failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )

    def set_tech_stack(self, project: str, technologies: List[str]) -> None:
        """Set the tech stack for a project."""
        self._tech_stack[project] = technologies

    def set_code_standards(self, language: str, standards: str) -> None:
        """Set coding standards for a language."""
        self._code_standards[language] = standards

    async def _handle_vls_build_deployment(self, task: Task) -> TaskResult:
        """Execute VLS Stage: Build & Deployment."""
        from ag3ntwerk.modules.vls.stages import execute_build_deployment

        try:
            result = await execute_build_deployment(task.context)

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
                error=f"VLS Build & Deployment failed: {e}",
            )

    def get_development_status(self) -> Dict[str, Any]:
        """Get current development status."""
        return {
            "active_projects": len(self._active_projects),
            "tech_stacks": self._tech_stack,
            "code_standards": list(self._code_standards.keys()),
            "capabilities": self.capabilities,
        }
