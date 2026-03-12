"""
Axiom (Axiom) Research Specialists.

Individual contributor specialists for research, analysis, and experimentation.
"""

from typing import Any, Dict, Optional

from ag3ntwerk.core.base import Specialist, Task, TaskResult, TaskStatus
from ag3ntwerk.llm.base import LLMProvider


class ResearchScientist(Specialist):
    """
    Specialist in scientific research methodology.

    Responsibilities:
    - Deep research execution
    - Literature reviews
    - Research methodology design
    - Academic writing
    """

    HANDLED_TASK_TYPES = [
        "deep_research",
        "literature_review",
        "research_writing",
        "peer_review",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="RS",
            name="Research Scientist",
            domain="Scientific Research",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this is a research science task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute a research task."""
        task.status = TaskStatus.IN_PROGRESS

        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            "deep_research": self._handle_deep_research,
            "literature_review": self._handle_literature_review,
        }
        return handlers.get(task_type)

    async def _handle_deep_research(self, task: Task) -> TaskResult:
        """Handle deep research."""
        topic = task.context.get("topic", task.description)
        depth = task.context.get("depth", "comprehensive")

        prompt = f"""As a Research Scientist, conduct thorough research.

Topic: {topic}
Depth: {depth}
Description: {task.description}

Provide research output:
1. Research scope definition
2. Background and context
3. Current knowledge state
4. Key developments
5. Different perspectives
6. Open questions
7. Future directions
8. Practical implications"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Deep research failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "research_type": "deep_research",
                "topic": topic,
                "findings": response,
            },
        )

    async def _handle_literature_review(self, task: Task) -> TaskResult:
        """Handle literature review."""
        field = task.context.get("field", task.description)
        timeframe = task.context.get("timeframe", "recent")

        prompt = f"""As a Research Scientist, conduct literature review.

Field: {field}
Timeframe: {timeframe}
Description: {task.description}

Structure review:
1. Research question
2. Search methodology
3. Source analysis
4. Key themes
5. Critical evaluation
6. Gap identification
7. Conclusions"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Literature review failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "research_type": "literature_review",
                "field": field,
                "review": response,
            },
        )

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider available",
            )

        prompt = f"""As a Research Scientist, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide rigorous research output."""

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


class DataScientist(Specialist):
    """
    Specialist in data analysis and statistics.

    Responsibilities:
    - Statistical analysis
    - Data exploration
    - Pattern recognition
    - Predictive modeling
    """

    HANDLED_TASK_TYPES = [
        "data_analysis",
        "statistical_analysis",
        "trend_research",
        "qualitative_analysis",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="DS",
            name="Data Scientist",
            domain="Data Analysis and Statistics",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this is a data science task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute a data science task."""
        task.status = TaskStatus.IN_PROGRESS

        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            "data_analysis": self._handle_data_analysis,
            "statistical_analysis": self._handle_statistical_analysis,
            "trend_research": self._handle_trend_research,
        }
        return handlers.get(task_type)

    async def _handle_data_analysis(self, task: Task) -> TaskResult:
        """Handle data analysis."""
        data_description = task.context.get("data_description", "")
        analysis_type = task.context.get("analysis_type", "exploratory")

        prompt = f"""As a Data Scientist, analyze data.

Data: {data_description}
Analysis Type: {analysis_type}
Description: {task.description}

Perform analysis:
1. Data overview
2. Quality assessment
3. Descriptive statistics
4. Pattern identification
5. Key insights
6. Visualization recommendations
7. Limitations
8. Next steps"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Data analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": analysis_type,
                "analysis": response,
            },
        )

    async def _handle_statistical_analysis(self, task: Task) -> TaskResult:
        """Handle statistical analysis."""
        data = task.context.get("data", "")
        tests = task.context.get("tests", [])

        prompt = f"""As a Data Scientist, perform statistical analysis.

Data: {data}
Requested Tests: {tests if tests else 'Appropriate tests for the data'}
Description: {task.description}

Provide statistical analysis:
1. Data characteristics
2. Appropriate tests selection
3. Assumptions verification
4. Test results
5. Effect sizes
6. Confidence intervals
7. Interpretation
8. Limitations"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Statistical analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "statistical",
                "analysis": response,
            },
        )

    async def _handle_trend_research(self, task: Task) -> TaskResult:
        """Handle trend research."""
        domain = task.context.get("domain", task.description)

        prompt = f"""As a Data Scientist, analyze trends.

Domain: {domain}
Description: {task.description}
Context: {task.context}

Trend analysis:
1. Historical data review
2. Current state
3. Pattern identification
4. Trend drivers
5. Future projections
6. Confidence levels
7. Implications"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Trend research failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "trend",
                "domain": domain,
                "analysis": response,
            },
        )

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider available",
            )

        prompt = f"""As a Data Scientist, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide data-driven analysis."""

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


class ExperimentDesigner(Specialist):
    """
    Specialist in experimental design and methodology.

    Responsibilities:
    - Experiment design
    - Methodology development
    - Variable identification
    - Bias mitigation
    """

    HANDLED_TASK_TYPES = [
        "experiment_design",
        "methodology_review",
        "hypothesis_testing",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="ED",
            name="Experiment Designer",
            domain="Experimental Methodology",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this is an experiment design task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute an experiment design task."""
        task.status = TaskStatus.IN_PROGRESS

        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            "experiment_design": self._handle_experiment_design,
            "hypothesis_testing": self._handle_hypothesis_testing,
        }
        return handlers.get(task_type)

    async def _handle_experiment_design(self, task: Task) -> TaskResult:
        """Handle experiment design."""
        objective = task.context.get("objective", task.description)
        constraints = task.context.get("constraints", [])

        prompt = f"""As an Experiment Designer, create experiment design.

Objective: {objective}
Constraints: {constraints}
Description: {task.description}

Design experiment:
1. Research question
2. Hypotheses (null/alternative)
3. Variables (IV, DV, CV)
4. Methodology selection
5. Sample design
6. Control mechanisms
7. Data collection plan
8. Analysis approach
9. Validity considerations
10. Potential limitations"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Experiment design failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "design_type": "experiment",
                "objective": objective,
                "design": response,
            },
        )

    async def _handle_hypothesis_testing(self, task: Task) -> TaskResult:
        """Handle hypothesis testing."""
        hypothesis = task.context.get("hypothesis", task.description)
        evidence = task.context.get("evidence", [])

        prompt = f"""As an Experiment Designer, evaluate hypothesis.

Hypothesis: {hypothesis}
Evidence: {evidence}
Description: {task.description}

Evaluate:
1. Hypothesis clarification
2. Operationalization
3. Test design
4. Evidence analysis
5. Alternative explanations
6. Confidence assessment
7. Conclusions"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Hypothesis testing failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "evaluation_type": "hypothesis",
                "hypothesis": hypothesis,
                "evaluation": response,
            },
        )

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider available",
            )

        prompt = f"""As an Experiment Designer, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide rigorous experimental design output."""

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


class AnalyticsSpecialist(Specialist):
    """
    Specialist in root cause and impact analysis.

    Responsibilities:
    - Root cause analysis
    - Impact assessment
    - Problem investigation
    - Causal analysis
    """

    HANDLED_TASK_TYPES = [
        "root_cause_analysis",
        "impact_analysis",
        "benchmarking",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="AS",
            name="Analytics Specialist",
            domain="Root Cause and Impact Analysis",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this is an analytics task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute an analytics task."""
        task.status = TaskStatus.IN_PROGRESS

        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            "root_cause_analysis": self._handle_root_cause,
            "impact_analysis": self._handle_impact_analysis,
        }
        return handlers.get(task_type)

    async def _handle_root_cause(self, task: Task) -> TaskResult:
        """Handle root cause analysis."""
        problem = task.context.get("problem", task.description)
        symptoms = task.context.get("symptoms", [])

        prompt = f"""As an Analytics Specialist, perform root cause analysis.

Problem: {problem}
Symptoms: {symptoms}
Description: {task.description}

Conduct RCA:
1. Problem definition
2. Timeline construction
3. 5 Whys analysis
4. Fishbone diagram approach
5. Contributing factors
6. Root cause identification
7. Evidence validation
8. Corrective actions
9. Prevention measures"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Root cause analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "root_cause",
                "problem": problem,
                "analysis": response,
            },
        )

    async def _handle_impact_analysis(self, task: Task) -> TaskResult:
        """Handle impact analysis."""
        change = task.context.get("change", task.description)
        scope = task.context.get("scope", "comprehensive")

        prompt = f"""As an Analytics Specialist, assess impact.

Change/Event: {change}
Analysis Scope: {scope}
Description: {task.description}

Assess impact:
1. Scope definition
2. Stakeholder identification
3. Direct impacts
4. Indirect impacts
5. Risk assessment
6. Opportunity identification
7. Mitigation strategies
8. Recommendations"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Impact analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "impact",
                "change": change,
                "analysis": response,
            },
        )

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider available",
            )

        prompt = f"""As an Analytics Specialist, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide thorough analytical output."""

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


class FeasibilityAnalyst(Specialist):
    """
    Specialist in feasibility studies and assessments.

    Responsibilities:
    - Feasibility studies
    - Technology assessments
    - Cost-benefit analysis
    - Risk evaluation
    """

    HANDLED_TASK_TYPES = [
        "feasibility_study",
        "technology_assessment",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="FA",
            name="Feasibility Analyst",
            domain="Feasibility and Assessment",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this is a feasibility task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute a feasibility task."""
        task.status = TaskStatus.IN_PROGRESS

        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            "feasibility_study": self._handle_feasibility_study,
            "technology_assessment": self._handle_tech_assessment,
        }
        return handlers.get(task_type)

    async def _handle_feasibility_study(self, task: Task) -> TaskResult:
        """Handle feasibility study."""
        proposal = task.context.get("proposal", task.description)
        criteria = task.context.get("criteria", [])

        prompt = f"""As a Feasibility Analyst, evaluate proposal feasibility.

Proposal: {proposal}
Criteria: {criteria if criteria else 'Standard feasibility criteria'}
Description: {task.description}

Assess:
1. Technical feasibility
2. Economic feasibility
3. Operational feasibility
4. Schedule feasibility
5. Legal considerations
6. Risk assessment
7. Alternatives
8. Recommendations"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Feasibility study failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "study_type": "feasibility",
                "proposal": proposal,
                "assessment": response,
            },
        )

    async def _handle_tech_assessment(self, task: Task) -> TaskResult:
        """Handle technology assessment."""
        technology = task.context.get("technology", task.description)
        use_case = task.context.get("use_case", "")

        prompt = f"""As a Feasibility Analyst, assess technology.

Technology: {technology}
Use Case: {use_case}
Description: {task.description}

Assess:
1. Technology overview
2. Maturity level
3. Capabilities
4. Limitations
5. Competitive landscape
6. Implementation needs
7. Cost considerations
8. Risk factors
9. Recommendations"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Technology assessment failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "assessment_type": "technology",
                "technology": technology,
                "assessment": response,
            },
        )

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider available",
            )

        prompt = f"""As a Feasibility Analyst, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide thorough feasibility assessment."""

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
