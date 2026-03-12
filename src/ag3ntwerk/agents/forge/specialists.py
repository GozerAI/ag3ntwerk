"""
Forge (Forge) Development Specialists.

Individual contributor specialists for specific development functions.
"""

import logging
from typing import Optional

from ag3ntwerk.core.base import Specialist, Task, TaskResult
from ag3ntwerk.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class SeniorDeveloper(Specialist):
    """
    Senior Developer - Expert code implementation specialist.

    Responsible for:
    - Complex code implementation
    - Code generation
    - Bug fixing
    - Code optimization
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="SD",
            name="Senior Developer",
            domain="Code Implementation, Bug Fixing, Optimization",
            capabilities=[
                "code_generation",
                "bug_fix",
                "optimization",
                "implementation",
                "debugging",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if SeniorDeveloper can handle the task."""
        dev_types = [
            "code_generation",
            "bug_fix",
            "optimization",
            "implementation",
            "debugging",
        ]
        return task.task_type in dev_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "code_generation": self._handle_code_generation,
            "bug_fix": self._handle_bug_fix,
            "optimization": self._handle_optimization,
            "implementation": self._handle_implementation,
            "debugging": self._handle_debugging,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute development task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_code_generation(self, task: Task) -> TaskResult:
        """Handle code generation."""
        context = task.context or {}

        prompt = f"""Generate code:

Requirements: {task.description}
Language: {context.get('language', 'python')}
Framework: {context.get('framework', 'None')}
Style: {context.get('style', 'clean, well-documented')}

Implementation:
1. Design approach
2. Complete, working code
3. Error handling
4. Type hints (if applicable)
5. Inline documentation

Provide production-ready code.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_bug_fix(self, task: Task) -> TaskResult:
        """Handle bug fix."""
        context = task.context or {}
        code = context.get("code", "")
        error = context.get("error", "unknown error")

        prompt = f"""Fix bug:

Bug Description: {task.description}
Error: {error}

Problematic Code:
```
{code}
```

Bug Fix:
1. Root cause analysis
2. Fixed code
3. Explanation of fix
4. Prevention strategies
5. Test cases to add

Provide complete bug fix.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_optimization(self, task: Task) -> TaskResult:
        """Handle code optimization."""
        context = task.context or {}
        code = context.get("code", "")

        prompt = f"""Optimize code:

Optimization Goal: {task.description}

Current Code:
```
{code}
```

Optimization:
1. Performance analysis
2. Optimized code
3. Complexity comparison
4. Benchmarks (if measurable)
5. Trade-offs

Provide optimized implementation.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_implementation(self, task: Task) -> TaskResult:
        """Handle feature implementation."""
        context = task.context or {}

        prompt = f"""Implement feature:

Feature: {task.description}
Language: {context.get('language', 'python')}
Constraints: {context.get('constraints', [])}

Implementation:
1. Design decisions
2. Complete code
3. Error handling
4. Tests
5. Documentation

Provide complete implementation.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_debugging(self, task: Task) -> TaskResult:
        """Handle debugging."""
        context = task.context or {}
        code = context.get("code", "")
        symptoms = context.get("symptoms", task.description)

        prompt = f"""Debug issue:

Symptoms: {symptoms}

Code:
```
{code}
```

Debugging:
1. Possible causes (ranked)
2. Diagnostic steps
3. Root cause
4. Fix recommendations
5. Prevention strategies

Provide debugging analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a Senior Developer, handle: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class CodeReviewer(Specialist):
    """
    Code Reviewer - Expert code review specialist.

    Responsible for:
    - Code review
    - Quality assessment
    - Security review
    - Best practices enforcement
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="CR",
            name="Code Reviewer",
            domain="Code Review, Quality Assessment, Security Review",
            capabilities=[
                "code_review",
                "security_review",
                "quality_assessment",
                "standards_check",
                "pr_review",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if CodeReviewer can handle the task."""
        review_types = [
            "code_review",
            "security_review",
            "quality_assessment",
            "standards_check",
            "pr_review",
        ]
        return task.task_type in review_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "code_review": self._handle_code_review,
            "security_review": self._handle_security_review,
            "quality_assessment": self._handle_quality_assessment,
            "standards_check": self._handle_standards_check,
            "pr_review": self._handle_pr_review,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute review task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_code_review(self, task: Task) -> TaskResult:
        """Handle code review."""
        context = task.context or {}
        code = context.get("code", "")
        file_path = context.get("file", "unknown")

        prompt = f"""Review code:

File: {file_path}

Code:
```
{code}
```

Review Criteria:
1. Correctness
2. Readability
3. Performance
4. Security
5. Best practices
6. Documentation

Provide review with severity ratings (Critical/High/Medium/Low).
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_security_review(self, task: Task) -> TaskResult:
        """Handle security review."""
        context = task.context or {}
        code = context.get("code", "")

        prompt = f"""Security review:

Code:
```
{code}
```

Security Focus:
1. Injection vulnerabilities
2. Authentication issues
3. Authorization flaws
4. Data exposure
5. Input validation
6. Cryptographic issues
7. Security misconfigurations

Provide security assessment with remediation.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_quality_assessment(self, task: Task) -> TaskResult:
        """Handle quality assessment."""
        context = task.context or {}
        code = context.get("code", "")

        prompt = f"""Assess code quality:

Code:
```
{code}
```

Quality Metrics:
1. Complexity score
2. Maintainability index
3. Code smells
4. Duplication
5. Coupling/cohesion
6. Test coverage potential

Provide quality assessment with improvements.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_standards_check(self, task: Task) -> TaskResult:
        """Handle standards compliance check."""
        context = task.context or {}
        code = context.get("code", "")
        standards = context.get("standards", "PEP8")

        prompt = f"""Check standards compliance:

Standards: {standards}

Code:
```
{code}
```

Compliance Check:
1. Naming conventions
2. Formatting
3. Documentation
4. Error handling
5. Type hints
6. Violations list

Provide compliance report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_pr_review(self, task: Task) -> TaskResult:
        """Handle pull request review."""
        context = task.context or {}

        prompt = f"""Review pull request:

PR Description: {task.description}
Changes: {context.get('changes', [])}
Files Modified: {context.get('files', [])}

PR Review:
1. Change summary
2. Code quality
3. Test coverage
4. Documentation
5. Breaking changes
6. Approval recommendation

Provide PR review.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a Code Reviewer, review: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class SystemArchitect(Specialist):
    """
    System Architect - Expert architecture design specialist.

    Responsible for:
    - System design
    - Architecture patterns
    - Technology evaluation
    - Scalability design
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="SA",
            name="System Architect",
            domain="System Design, Architecture, Scalability",
            capabilities=[
                "architecture_design",
                "system_design",
                "pattern_selection",
                "tech_evaluation",
                "scalability_design",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if SystemArchitect can handle the task."""
        arch_types = [
            "architecture_design",
            "system_design",
            "pattern_selection",
            "tech_evaluation",
            "scalability_design",
        ]
        return task.task_type in arch_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "architecture_design": self._handle_architecture_design,
            "system_design": self._handle_system_design,
            "pattern_selection": self._handle_pattern_selection,
            "tech_evaluation": self._handle_tech_evaluation,
            "scalability_design": self._handle_scalability_design,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute architecture task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_architecture_design(self, task: Task) -> TaskResult:
        """Handle architecture design."""
        context = task.context or {}

        prompt = f"""Design architecture:

Requirements: {task.description}
Scale: {context.get('scale', 'Medium')}
Constraints: {context.get('constraints', [])}

Architecture Design:
1. High-level design
2. Component diagram
3. Data flow
4. Technology stack
5. Scalability plan
6. Trade-offs

Provide comprehensive architecture.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_system_design(self, task: Task) -> TaskResult:
        """Handle system design."""
        context = task.context or {}

        prompt = f"""Design system:

System: {task.description}
Users: {context.get('users', 'Standard')}
Requirements: {context.get('requirements', [])}

System Design:
1. Functional design
2. Non-functional requirements
3. Component breakdown
4. API design
5. Database design
6. Deployment strategy

Provide system design.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_pattern_selection(self, task: Task) -> TaskResult:
        """Handle pattern selection."""
        context = task.context or {}

        prompt = f"""Select architecture pattern:

Problem: {task.description}
Context: {context.get('context', {})}
Constraints: {context.get('constraints', [])}

Pattern Analysis:
1. Applicable patterns
2. Comparison matrix
3. Recommended pattern
4. Implementation approach
5. Trade-offs

Provide pattern recommendation.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_tech_evaluation(self, task: Task) -> TaskResult:
        """Handle technology evaluation."""
        context = task.context or {}

        prompt = f"""Evaluate technology:

Purpose: {task.description}
Candidates: {context.get('candidates', [])}
Criteria: {context.get('criteria', [])}

Evaluation:
1. Feature comparison
2. Performance analysis
3. Community/support
4. Cost analysis
5. Risk assessment
6. Recommendation

Provide tech evaluation.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_scalability_design(self, task: Task) -> TaskResult:
        """Handle scalability design."""
        context = task.context or {}

        prompt = f"""Design for scalability:

System: {task.description}
Current State: {context.get('current', {})}
Target Scale: {context.get('target', {})}

Scalability Design:
1. Bottleneck analysis
2. Horizontal scaling
3. Vertical scaling
4. Caching strategy
5. Database scaling
6. Cost projection

Provide scalability design.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a System Architect, design: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class QAEngineer(Specialist):
    """
    QA Engineer - Expert testing specialist.

    Responsible for:
    - Test creation
    - Test execution
    - Quality assurance
    - Test automation
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="QAE",
            name="QA Engineer",
            domain="Testing, Quality Assurance, Test Automation",
            capabilities=[
                "test_creation",
                "test_execution",
                "test_automation",
                "qa_analysis",
                "regression_testing",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if QAEngineer can handle the task."""
        qa_types = [
            "test_creation",
            "test_execution",
            "test_automation",
            "qa_analysis",
            "regression_testing",
            "testing",
        ]
        return task.task_type in qa_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "test_creation": self._handle_test_creation,
            "testing": self._handle_test_creation,
            "test_execution": self._handle_test_execution,
            "test_automation": self._handle_test_automation,
            "qa_analysis": self._handle_qa_analysis,
            "regression_testing": self._handle_regression_testing,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute QA task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_test_creation(self, task: Task) -> TaskResult:
        """Handle test creation."""
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

Test Suite:
1. Unit tests
2. Edge cases
3. Error handling
4. Integration tests (if applicable)
5. Test fixtures
6. Mocking strategy

Provide complete test code.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_test_execution(self, task: Task) -> TaskResult:
        """Handle test execution planning."""
        context = task.context or {}

        prompt = f"""Plan test execution:

Test Suite: {task.description}
Environment: {context.get('environment', 'local')}
Scope: {context.get('scope', 'full')}

Execution Plan:
1. Test selection
2. Environment setup
3. Execution order
4. Data setup
5. Result analysis
6. Reporting

Provide execution plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_test_automation(self, task: Task) -> TaskResult:
        """Handle test automation."""
        context = task.context or {}

        prompt = f"""Automate tests:

Scope: {task.description}
Framework: {context.get('framework', 'pytest')}
CI/CD: {context.get('ci_cd', 'GitHub Actions')}

Automation:
1. Test selection
2. Framework setup
3. CI/CD integration
4. Reporting
5. Maintenance plan

Provide automation config.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_qa_analysis(self, task: Task) -> TaskResult:
        """Handle QA analysis."""
        context = task.context or {}

        prompt = f"""Analyze quality:

Scope: {task.description}
Metrics: {context.get('metrics', {})}
Issues: {context.get('issues', [])}

QA Analysis:
1. Quality metrics
2. Issue patterns
3. Risk areas
4. Coverage gaps
5. Improvement recommendations

Provide QA analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_regression_testing(self, task: Task) -> TaskResult:
        """Handle regression testing."""
        context = task.context or {}

        prompt = f"""Plan regression testing:

Release: {task.description}
Changes: {context.get('changes', [])}
Risk Areas: {context.get('risk_areas', [])}

Regression Plan:
1. Test selection
2. Priority order
3. Automation scope
4. Manual testing
5. Sign-off criteria

Provide regression plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a QA Engineer, handle: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class DevOpsEngineer(Specialist):
    """
    DevOps Engineer - Expert infrastructure and deployment specialist.

    Responsible for:
    - CI/CD pipelines
    - Infrastructure automation
    - Deployment
    - Containerization
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="DOE",
            name="DevOps Engineer",
            domain="CI/CD, Infrastructure, Deployment, Containers",
            capabilities=[
                "ci_cd_implementation",
                "infrastructure_automation",
                "deployment_automation",
                "containerization",
                "monitoring_setup",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if DevOpsEngineer can handle the task."""
        devops_types = [
            "ci_cd_implementation",
            "infrastructure_automation",
            "deployment_automation",
            "deployment",
            "containerization",
            "monitoring_setup",
        ]
        return task.task_type in devops_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "ci_cd_implementation": self._handle_ci_cd,
            "infrastructure_automation": self._handle_infrastructure,
            "deployment_automation": self._handle_deployment,
            "deployment": self._handle_deployment,
            "containerization": self._handle_containerization,
            "monitoring_setup": self._handle_monitoring,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute DevOps task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_ci_cd(self, task: Task) -> TaskResult:
        """Handle CI/CD implementation."""
        context = task.context or {}

        prompt = f"""Implement CI/CD:

Project: {task.description}
Platform: {context.get('platform', 'GitHub Actions')}
Tech Stack: {context.get('tech_stack', [])}

CI/CD Config:
1. Build pipeline
2. Test pipeline
3. Security scanning
4. Deployment stages
5. Configuration files

Provide working CI/CD configuration.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_infrastructure(self, task: Task) -> TaskResult:
        """Handle infrastructure automation."""
        context = task.context or {}

        prompt = f"""Automate infrastructure:

Requirements: {task.description}
Cloud: {context.get('cloud', 'AWS')}
Tool: {context.get('tool', 'Terraform')}

Infrastructure Code:
1. Resource definitions
2. Networking
3. Security groups
4. Variables
5. Outputs

Provide IaC code.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_deployment(self, task: Task) -> TaskResult:
        """Handle deployment automation."""
        context = task.context or {}

        prompt = f"""Automate deployment:

Application: {task.description}
Environment: {context.get('environment', 'production')}
Strategy: {context.get('strategy', 'rolling')}

Deployment:
1. Pre-deployment checks
2. Deployment script
3. Health checks
4. Rollback script
5. Post-deployment validation

Provide deployment automation.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_containerization(self, task: Task) -> TaskResult:
        """Handle containerization."""
        context = task.context or {}

        prompt = f"""Containerize application:

Application: {task.description}
Language: {context.get('language', 'Python')}
Dependencies: {context.get('dependencies', [])}

Container Config:
1. Dockerfile (multi-stage)
2. .dockerignore
3. docker-compose
4. Kubernetes manifests (if needed)
5. Security hardening

Provide container configuration.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_monitoring(self, task: Task) -> TaskResult:
        """Handle monitoring setup."""
        context = task.context or {}

        prompt = f"""Setup monitoring:

Application: {task.description}
Stack: {context.get('stack', 'Prometheus/Grafana')}
Components: {context.get('components', [])}

Monitoring Config:
1. Metrics collection
2. Alerting rules
3. Dashboard config
4. Log aggregation
5. Tracing setup

Provide monitoring configuration.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a DevOps Engineer, handle: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class TechnicalWriter(Specialist):
    """
    Technical Writer - Expert documentation specialist.

    Responsible for:
    - API documentation
    - Code documentation
    - Technical guides
    - Architecture documentation
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="TW",
            name="Technical Writer",
            domain="Documentation, Technical Writing, API Docs",
            capabilities=[
                "api_documentation",
                "code_documentation",
                "technical_guide",
                "architecture_documentation",
                "user_documentation",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if TechnicalWriter can handle the task."""
        doc_types = [
            "api_documentation",
            "code_documentation",
            "technical_guide",
            "architecture_documentation",
            "user_documentation",
            "documentation",
        ]
        return task.task_type in doc_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "api_documentation": self._handle_api_docs,
            "code_documentation": self._handle_code_docs,
            "technical_guide": self._handle_technical_guide,
            "architecture_documentation": self._handle_arch_docs,
            "user_documentation": self._handle_user_docs,
            "documentation": self._handle_code_docs,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute documentation task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_api_docs(self, task: Task) -> TaskResult:
        """Handle API documentation."""
        context = task.context or {}

        prompt = f"""Write API documentation:

API: {task.description}
Endpoints: {context.get('endpoints', [])}
Format: {context.get('format', 'OpenAPI')}

API Documentation:
1. Overview
2. Authentication
3. Endpoints reference
4. Request/response examples
5. Error codes
6. Rate limits

Provide comprehensive API docs.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_code_docs(self, task: Task) -> TaskResult:
        """Handle code documentation."""
        context = task.context or {}
        code = context.get("code", "")

        prompt = f"""Write code documentation:

Code:
```
{code}
```

Documentation:
1. Module overview
2. Class/function docstrings
3. Parameter descriptions
4. Return values
5. Examples
6. Edge cases

Provide comprehensive docstrings.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_technical_guide(self, task: Task) -> TaskResult:
        """Handle technical guide."""
        context = task.context or {}

        prompt = f"""Write technical guide:

Topic: {task.description}
Audience: {context.get('audience', 'Developers')}
Depth: {context.get('depth', 'Intermediate')}

Guide Structure:
1. Introduction
2. Prerequisites
3. Step-by-step guide
4. Code examples
5. Troubleshooting
6. Best practices

Provide technical guide.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_arch_docs(self, task: Task) -> TaskResult:
        """Handle architecture documentation."""
        context = task.context or {}

        prompt = f"""Write architecture documentation:

System: {task.description}
Components: {context.get('components', [])}
Audience: {context.get('audience', 'Technical team')}

Architecture Docs:
1. System overview
2. Component descriptions
3. Data flow diagrams
4. Integration points
5. Deployment architecture
6. Decision records

Provide architecture documentation.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_user_docs(self, task: Task) -> TaskResult:
        """Handle user documentation."""
        context = task.context or {}

        prompt = f"""Write user documentation:

Product: {task.description}
Audience: {context.get('audience', 'End users')}
Features: {context.get('features', [])}

User Documentation:
1. Getting started
2. Feature guides
3. Tutorials
4. FAQ
5. Troubleshooting

Provide user documentation.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a Technical Writer, document: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))
