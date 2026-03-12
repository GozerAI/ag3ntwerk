"""
Forge (Forge) Development Managers.

Middle management layer handling specific development domains.
"""

import logging
from typing import Optional

from ag3ntwerk.core.base import Manager, Task, TaskResult
from ag3ntwerk.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class ArchitectureManager(Manager):
    """
    Architecture Manager - Manages system design and architecture.

    Responsible for:
    - System architecture design
    - Technology selection
    - API design
    - Database design
    - Scalability planning
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="AM",
            name="Architecture Manager",
            domain="System Design, Architecture, Technology Selection",
            llm_provider=llm_provider,
        )

        self.capabilities = [
            "architecture",
            "system_design",
            "api_design",
            "database_design",
            "tech_selection",
            "scalability_planning",
        ]

    def can_handle(self, task: Task) -> bool:
        """Check if ArchitectureManager can handle the task."""
        arch_types = [
            "architecture",
            "system_design",
            "api_design",
            "database_design",
            "tech_selection",
            "scalability_planning",
        ]
        return task.task_type in arch_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "architecture": self._handle_architecture,
            "system_design": self._handle_system_design,
            "api_design": self._handle_api_design,
            "database_design": self._handle_database_design,
            "tech_selection": self._handle_tech_selection,
            "scalability_planning": self._handle_scalability,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute architecture management task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._route_to_specialist(task)

    async def _route_to_specialist(self, task: Task) -> TaskResult:
        """Route to appropriate specialist."""
        for specialist in self.subordinates:
            if specialist.can_handle(task):
                return await specialist.execute(task)
        return TaskResult(
            task_id=task.id,
            success=False,
            error=f"No specialist for task type: {task.task_type}",
        )

    async def _handle_architecture(self, task: Task) -> TaskResult:
        """Handle architecture design."""
        context = task.context or {}

        prompt = f"""Design system architecture:

Requirements: {task.description}
Constraints: {context.get('constraints', [])}
Scale Requirements: {context.get('scale', 'Standard')}
Tech Preferences: {context.get('tech_preferences', [])}

Architecture Design:
1. High-level overview
2. Component breakdown
3. Data flow diagrams
4. Technology recommendations
5. Scalability considerations
6. Security considerations
7. Trade-offs and rationale

Provide comprehensive architecture design.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_system_design(self, task: Task) -> TaskResult:
        """Handle system design."""
        context = task.context or {}

        prompt = f"""Design system:

System: {task.description}
Requirements: {context.get('requirements', [])}
Users: {context.get('users', 'Standard')}
Data Volume: {context.get('data_volume', 'Medium')}

System Design:
1. Functional requirements
2. Non-functional requirements
3. Component architecture
4. Integration points
5. Data model
6. Deployment strategy

Provide system design.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_api_design(self, task: Task) -> TaskResult:
        """Handle API design."""
        context = task.context or {}

        prompt = f"""Design API:

API Purpose: {task.description}
API Type: {context.get('api_type', 'REST')}
Resources: {context.get('resources', [])}
Authentication: {context.get('auth', 'Bearer token')}

API Design:
1. Endpoint structure
2. Request/response formats
3. Authentication/authorization
4. Error handling
5. Rate limiting
6. Versioning strategy
7. OpenAPI specification

Provide API design.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_database_design(self, task: Task) -> TaskResult:
        """Handle database design."""
        context = task.context or {}

        prompt = f"""Design database:

Requirements: {task.description}
Database Type: {context.get('db_type', 'PostgreSQL')}
Entities: {context.get('entities', [])}
Scale: {context.get('scale', 'Medium')}

Database Design:
1. Schema design
2. Table definitions
3. Relationships
4. Indexes strategy
5. Constraints
6. Migration plan
7. Performance optimization

Provide database design.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_tech_selection(self, task: Task) -> TaskResult:
        """Handle technology selection."""
        context = task.context or {}

        prompt = f"""Recommend technology stack:

Project: {task.description}
Requirements: {context.get('requirements', [])}
Constraints: {context.get('constraints', [])}
Team Experience: {context.get('team_experience', [])}

Technology Selection:
1. Frontend technologies
2. Backend technologies
3. Database technologies
4. Infrastructure/Cloud
5. DevOps tools
6. Comparison matrix
7. Rationale for choices

Provide technology recommendations.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_scalability(self, task: Task) -> TaskResult:
        """Handle scalability planning."""
        context = task.context or {}

        prompt = f"""Plan for scalability:

System: {task.description}
Current Scale: {context.get('current_scale', {})}
Target Scale: {context.get('target_scale', {})}
Bottlenecks: {context.get('bottlenecks', [])}

Scalability Plan:
1. Horizontal scaling strategy
2. Vertical scaling considerations
3. Caching strategy
4. Database scaling
5. Load balancing
6. CDN usage
7. Cost implications

Provide scalability plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class CodeQualityManager(Manager):
    """
    Code Quality Manager - Manages code quality and reviews.

    Responsible for:
    - Code review coordination
    - Quality standards
    - Refactoring guidance
    - Best practices
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="CQM",
            name="Code Quality Manager",
            domain="Code Review, Quality Standards, Best Practices",
            llm_provider=llm_provider,
        )

        self.capabilities = [
            "code_review",
            "refactoring",
            "code_standards",
            "best_practices",
            "code_analysis",
            "technical_debt",
        ]

    def can_handle(self, task: Task) -> bool:
        """Check if CodeQualityManager can handle the task."""
        quality_types = [
            "code_review",
            "refactoring",
            "code_standards",
            "best_practices",
            "code_analysis",
            "technical_debt",
        ]
        return task.task_type in quality_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "code_review": self._handle_code_review,
            "refactoring": self._handle_refactoring,
            "code_standards": self._handle_code_standards,
            "best_practices": self._handle_best_practices,
            "code_analysis": self._handle_code_analysis,
            "technical_debt": self._handle_technical_debt,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute code quality task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._route_to_specialist(task)

    async def _route_to_specialist(self, task: Task) -> TaskResult:
        """Route to appropriate specialist."""
        for specialist in self.subordinates:
            if specialist.can_handle(task):
                return await specialist.execute(task)
        return TaskResult(
            task_id=task.id,
            success=False,
            error=f"No specialist for task type: {task.task_type}",
        )

    async def _handle_code_review(self, task: Task) -> TaskResult:
        """Handle code review."""
        context = task.context or {}
        code = context.get("code", "")
        file_path = context.get("file", "unknown")

        prompt = f"""Perform comprehensive code review:

File: {file_path}
Description: {task.description}

Code:
```
{code}
```

Review Focus:
1. Code quality and readability
2. Potential bugs and edge cases
3. Performance considerations
4. Security vulnerabilities
5. Design patterns and architecture
6. Testing coverage
7. Documentation quality

Provide detailed review with severity ratings.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_refactoring(self, task: Task) -> TaskResult:
        """Handle refactoring guidance."""
        context = task.context or {}
        code = context.get("code", "")

        prompt = f"""Provide refactoring guidance:

Goal: {task.description}
Current Code:
```
{code}
```

Refactoring Analysis:
1. Code smells identified
2. Refactoring techniques to apply
3. Refactored code
4. Benefits of changes
5. Trade-offs
6. Testing considerations

Provide refactoring plan and implementation.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_code_standards(self, task: Task) -> TaskResult:
        """Handle code standards definition."""
        context = task.context or {}

        prompt = f"""Define coding standards:

Language: {context.get('language', 'Python')}
Framework: {context.get('framework', 'General')}
Team Size: {context.get('team_size', 'Medium')}

Standards Definition:
1. Naming conventions
2. Code formatting rules
3. Documentation requirements
4. Error handling patterns
5. Testing requirements
6. Security guidelines
7. Tool configuration (linters, formatters)

Provide comprehensive coding standards.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_best_practices(self, task: Task) -> TaskResult:
        """Handle best practices guidance."""
        context = task.context or {}

        prompt = f"""Recommend best practices:

Context: {task.description}
Technology: {context.get('technology', 'General')}
Use Case: {context.get('use_case', 'Development')}

Best Practices:
1. Code organization
2. Error handling
3. Performance optimization
4. Security practices
5. Testing strategies
6. Documentation
7. Code examples

Provide actionable best practices.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_code_analysis(self, task: Task) -> TaskResult:
        """Handle code analysis."""
        context = task.context or {}
        code = context.get("code", "")

        prompt = f"""Analyze code:

Code:
```
{code}
```

Analysis Focus: {task.description}

Analysis:
1. Complexity metrics
2. Maintainability assessment
3. Code smells
4. Security issues
5. Performance concerns
6. Improvement recommendations

Provide detailed code analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_technical_debt(self, task: Task) -> TaskResult:
        """Handle technical debt assessment."""
        context = task.context or {}

        prompt = f"""Assess technical debt:

Codebase: {task.description}
Areas of Concern: {context.get('areas', [])}
Age: {context.get('age', 'Unknown')}

Technical Debt Assessment:
1. Debt categories
2. Impact analysis
3. Prioritization matrix
4. Remediation effort
5. Action plan
6. Prevention strategies

Provide technical debt assessment.
"""
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class TestingManager(Manager):
    """
    Testing Manager - Manages testing operations.

    Responsible for:
    - Test strategy
    - Test generation
    - Test coverage
    - Quality assurance
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="TEM",
            name="Testing Manager",
            domain="Testing Strategy, QA, Test Automation",
            llm_provider=llm_provider,
        )

        self.capabilities = [
            "testing",
            "test_generation",
            "test_strategy",
            "test_coverage",
            "qa_planning",
            "test_automation",
        ]

    def can_handle(self, task: Task) -> bool:
        """Check if TestingManager can handle the task."""
        testing_types = [
            "testing",
            "test_generation",
            "test_strategy",
            "test_coverage",
            "qa_planning",
            "test_automation",
        ]
        return task.task_type in testing_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "testing": self._handle_testing,
            "test_generation": self._handle_test_generation,
            "test_strategy": self._handle_test_strategy,
            "test_coverage": self._handle_test_coverage,
            "qa_planning": self._handle_qa_planning,
            "test_automation": self._handle_test_automation,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute testing task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._route_to_specialist(task)

    async def _route_to_specialist(self, task: Task) -> TaskResult:
        """Route to appropriate specialist."""
        for specialist in self.subordinates:
            if specialist.can_handle(task):
                return await specialist.execute(task)
        return TaskResult(
            task_id=task.id,
            success=False,
            error=f"No specialist for task type: {task.task_type}",
        )

    async def _handle_testing(self, task: Task) -> TaskResult:
        """Handle general testing."""
        context = task.context or {}
        code = context.get("code", "")
        test_type = context.get("test_type", "unit")

        prompt = f"""Create tests:

Test Type: {test_type}
Description: {task.description}

Code to Test:
```
{code}
```

Testing Requirements:
1. Happy path tests
2. Edge cases
3. Error handling tests
4. Boundary conditions
5. Mock setup if needed

Generate comprehensive tests.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_test_generation(self, task: Task) -> TaskResult:
        """Handle test generation."""
        context = task.context or {}
        code = context.get("code", "")

        prompt = f"""Generate tests:

Target Code:
```
{code}
```

Test Framework: {context.get('framework', 'pytest')}
Coverage Target: {context.get('coverage', '80%')}

Generate:
1. Unit tests
2. Integration tests (if applicable)
3. Edge case tests
4. Error handling tests
5. Parameterized tests

Provide complete test code.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_test_strategy(self, task: Task) -> TaskResult:
        """Handle test strategy."""
        context = task.context or {}

        prompt = f"""Define test strategy:

Project: {task.description}
Tech Stack: {context.get('tech_stack', [])}
Team Size: {context.get('team_size', 'Medium')}

Test Strategy:
1. Testing pyramid
2. Unit testing approach
3. Integration testing approach
4. E2E testing approach
5. Performance testing
6. Security testing
7. CI/CD integration

Provide comprehensive test strategy.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_test_coverage(self, task: Task) -> TaskResult:
        """Handle test coverage analysis."""
        context = task.context or {}

        prompt = f"""Analyze test coverage:

Current Coverage: {context.get('current_coverage', 'Unknown')}
Target Coverage: {context.get('target_coverage', '80%')}
Codebase Areas: {context.get('areas', [])}

Coverage Analysis:
1. Current coverage breakdown
2. Uncovered areas
3. Critical paths needing tests
4. Test gaps
5. Prioritized test list
6. Effort estimation

Provide coverage improvement plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_qa_planning(self, task: Task) -> TaskResult:
        """Handle QA planning."""
        context = task.context or {}

        prompt = f"""Plan QA activities:

Feature/Release: {task.description}
Scope: {context.get('scope', 'Full')}
Timeline: {context.get('timeline', 'Standard')}

QA Plan:
1. Test scope
2. Test types required
3. Test cases
4. Test data requirements
5. Environment needs
6. Risk areas
7. Sign-off criteria

Provide QA plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_test_automation(self, task: Task) -> TaskResult:
        """Handle test automation."""
        context = task.context or {}

        prompt = f"""Plan test automation:

Scope: {task.description}
Current State: {context.get('current_state', 'Manual')}
Tools: {context.get('tools', [])}

Automation Plan:
1. Automation candidates
2. Framework selection
3. Implementation approach
4. CI/CD integration
5. Maintenance strategy
6. ROI analysis

Provide automation plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class DevOpsManager(Manager):
    """
    DevOps Manager - Manages deployment and infrastructure.

    Responsible for:
    - CI/CD pipelines
    - Deployment automation
    - Infrastructure as code
    - Monitoring and observability
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="DOM",
            name="DevOps Manager",
            domain="CI/CD, Deployment, Infrastructure, Monitoring",
            llm_provider=llm_provider,
        )

        self.capabilities = [
            "deployment",
            "ci_cd",
            "infrastructure",
            "monitoring",
            "containerization",
            "orchestration",
        ]

    def can_handle(self, task: Task) -> bool:
        """Check if DevOpsManager can handle the task."""
        devops_types = [
            "deployment",
            "ci_cd",
            "infrastructure",
            "monitoring",
            "containerization",
            "orchestration",
        ]
        return task.task_type in devops_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "deployment": self._handle_deployment,
            "ci_cd": self._handle_ci_cd,
            "infrastructure": self._handle_infrastructure,
            "monitoring": self._handle_monitoring,
            "containerization": self._handle_containerization,
            "orchestration": self._handle_orchestration,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute DevOps task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._route_to_specialist(task)

    async def _route_to_specialist(self, task: Task) -> TaskResult:
        """Route to appropriate specialist."""
        for specialist in self.subordinates:
            if specialist.can_handle(task):
                return await specialist.execute(task)
        return TaskResult(
            task_id=task.id,
            success=False,
            error=f"No specialist for task type: {task.task_type}",
        )

    async def _handle_deployment(self, task: Task) -> TaskResult:
        """Handle deployment."""
        context = task.context or {}

        prompt = f"""Plan deployment:

Application: {task.description}
Environment: {context.get('environment', 'production')}
Strategy: {context.get('strategy', 'rolling')}
Version: {context.get('version', 'latest')}

Deployment Plan:
1. Pre-deployment checks
2. Deployment steps
3. Rollback plan
4. Health checks
5. Monitoring setup
6. Post-deployment validation

Provide deployment plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_ci_cd(self, task: Task) -> TaskResult:
        """Handle CI/CD pipeline."""
        context = task.context or {}

        prompt = f"""Design CI/CD pipeline:

Project: {task.description}
Platform: {context.get('platform', 'GitHub Actions')}
Tech Stack: {context.get('tech_stack', [])}
Environments: {context.get('environments', ['dev', 'staging', 'prod'])}

CI/CD Pipeline:
1. Build stage
2. Test stage
3. Security scanning
4. Artifact creation
5. Deployment stages
6. Approvals and gates
7. Configuration examples

Provide CI/CD pipeline design.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_infrastructure(self, task: Task) -> TaskResult:
        """Handle infrastructure as code."""
        context = task.context or {}

        prompt = f"""Design infrastructure:

Requirements: {task.description}
Cloud Provider: {context.get('cloud', 'AWS')}
IaC Tool: {context.get('iac_tool', 'Terraform')}
Scale: {context.get('scale', 'Medium')}

Infrastructure Design:
1. Architecture diagram
2. Resource definitions
3. Networking setup
4. Security configuration
5. Cost estimation
6. IaC code snippets

Provide infrastructure design.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_monitoring(self, task: Task) -> TaskResult:
        """Handle monitoring setup."""
        context = task.context or {}

        prompt = f"""Setup monitoring:

Application: {task.description}
Components: {context.get('components', [])}
Stack: {context.get('monitoring_stack', 'Prometheus/Grafana')}

Monitoring Plan:
1. Metrics to collect
2. Alerting rules
3. Dashboard design
4. Log aggregation
5. Tracing setup
6. SLI/SLO definitions

Provide monitoring setup.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_containerization(self, task: Task) -> TaskResult:
        """Handle containerization."""
        context = task.context or {}

        prompt = f"""Containerize application:

Application: {task.description}
Language: {context.get('language', 'Python')}
Framework: {context.get('framework', 'Unknown')}
Dependencies: {context.get('dependencies', [])}

Containerization:
1. Dockerfile
2. Multi-stage build
3. Security best practices
4. Size optimization
5. docker-compose (if applicable)
6. Health checks

Provide containerization config.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_orchestration(self, task: Task) -> TaskResult:
        """Handle container orchestration."""
        context = task.context or {}

        prompt = f"""Setup container orchestration:

Application: {task.description}
Platform: {context.get('platform', 'Kubernetes')}
Scale: {context.get('scale', 'Medium')}
Components: {context.get('components', [])}

Orchestration Setup:
1. Kubernetes manifests
2. Service configuration
3. Ingress setup
4. Scaling policies
5. Resource limits
6. Secrets management

Provide orchestration config.
"""
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))
