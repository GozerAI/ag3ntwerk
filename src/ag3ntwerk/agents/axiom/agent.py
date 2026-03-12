"""
Axiom (Axiom) Agent - Axiom.

Codename: Axiom
Core function: Turn unknowns into knowns; produce validated insights and breakthroughs.

The Axiom handles all research and deep analysis tasks:
- Deep research and investigation
- Literature reviews and academic research
- Data analysis and interpretation
- Experiment design
- Hypothesis testing
- Research synthesis and meta-analysis

Sphere of influence: Research agenda, experiments, methodology, literature/competitive
intelligence, eval frameworks, publications/patents (if relevant).
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Manager,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider

from ag3ntwerk.agents.axiom.managers import (
    ResearchProjectManager,
    ExperimentationManager,
    DataAnalysisManager,
    AssessmentManager,
)
from ag3ntwerk.agents.axiom.specialists import (
    ResearchScientist,
    DataScientist,
    ExperimentDesigner,
    AnalyticsSpecialist,
    FeasibilityAnalyst,
)


# Research task types this agent can handle
RESEARCH_CAPABILITIES = [
    "deep_research",
    "literature_review",
    "experiment_design",
    "data_analysis",
    "hypothesis_testing",
    "meta_analysis",
    "trend_research",
    "feasibility_study",
    "technology_assessment",
    "impact_analysis",
    "root_cause_analysis",
    "benchmarking",
]


class Axiom(Manager):
    """
    Axiom - Axiom.

    The Axiom is responsible for all research and deep analysis
    within the ag3ntwerk system.

    Codename: Axiom

    Core Responsibilities:
    - Deep research and investigation
    - Literature reviews and academic research
    - Data analysis and interpretation
    - Experiment design and methodology
    - Research synthesis and meta-analysis

    Example:
        ```python
        cro = Axiom(llm_provider=llm)

        task = Task(
            description="Research state-of-the-art in LLM fine-tuning",
            task_type="literature_review",
            context={"field": "machine learning", "timeframe": "2023-2024"},
        )
        result = await cro.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__(
            code="Axiom",
            name="Axiom",
            domain="Research, Analysis, Investigation",
            llm_provider=llm_provider,
        )
        self.codename = "Axiom"

        self.capabilities = RESEARCH_CAPABILITIES

        # Research-specific state
        self._research_projects: Dict[str, Any] = {}
        self._findings_database: Dict[str, Any] = {}
        self._hypotheses: List[Dict[str, Any]] = []

        # Initialize managers and specialists hierarchy
        self._init_managers()

    def can_handle(self, task: Task) -> bool:
        """Check if this is a research-related task."""
        return task.task_type in self.capabilities

    def _init_managers(self) -> None:
        """Initialize and register managers with their specialists."""
        # Create managers
        rpm = ResearchProjectManager(llm_provider=self.llm_provider)
        exm = ExperimentationManager(llm_provider=self.llm_provider)
        dam = DataAnalysisManager(llm_provider=self.llm_provider)
        asm = AssessmentManager(llm_provider=self.llm_provider)

        # Create specialists
        research_scientist = ResearchScientist(llm_provider=self.llm_provider)
        data_scientist = DataScientist(llm_provider=self.llm_provider)
        experiment_designer = ExperimentDesigner(llm_provider=self.llm_provider)
        analytics_specialist = AnalyticsSpecialist(llm_provider=self.llm_provider)
        feasibility_analyst = FeasibilityAnalyst(llm_provider=self.llm_provider)

        # Register specialists with appropriate managers
        rpm.register_subordinate(research_scientist)
        exm.register_subordinate(experiment_designer)
        dam.register_subordinate(data_scientist)
        dam.register_subordinate(analytics_specialist)
        asm.register_subordinate(feasibility_analyst)

        # Register managers with Axiom
        self.register_subordinate(rpm)
        self.register_subordinate(exm)
        self.register_subordinate(dam)
        self.register_subordinate(asm)

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
            "experiment_design": self._handle_experiment_design,
            "data_analysis": self._handle_data_analysis,
            "hypothesis_testing": self._handle_hypothesis_testing,
            "root_cause_analysis": self._handle_root_cause_analysis,
            "feasibility_study": self._handle_feasibility_study,
        }
        return handlers.get(task_type)

    async def _handle_deep_research(self, task: Task) -> TaskResult:
        """Conduct deep research on a topic."""
        topic = task.context.get("topic", task.description)
        depth = task.context.get("depth", "comprehensive")
        focus_areas = task.context.get("focus_areas", [])

        prompt = f"""As the Axiom, conduct deep research.

Topic: {topic}
Research Depth: {depth}
Focus Areas: {focus_areas if focus_areas else 'Cover all relevant aspects'}
Description: {task.description}
Context: {task.context}

Conduct thorough research including:
1. Background and context
2. Current state of knowledge
3. Key developments and breakthroughs
4. Different perspectives and debates
5. Open questions and research gaps
6. Future directions
7. Practical implications
8. Recommended resources for further study"""

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
        """Conduct a literature review."""
        field = task.context.get("field", "")
        timeframe = task.context.get("timeframe", "recent")
        scope = task.context.get("scope", "comprehensive")

        prompt = f"""As the Axiom, conduct a literature review.

Field: {field}
Timeframe: {timeframe}
Scope: {scope}
Description: {task.description}
Context: {task.context}

Provide a structured literature review including:
1. Introduction and research question
2. Methodology and search strategy
3. Thematic analysis of key works
4. Synthesis of findings
5. Critical evaluation of the literature
6. Identification of gaps
7. Conclusions and recommendations
8. Key references and citations"""

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

    async def _handle_experiment_design(self, task: Task) -> TaskResult:
        """Design an experiment or study."""
        objective = task.context.get("objective", task.description)
        constraints = task.context.get("constraints", [])
        resources = task.context.get("resources", [])

        prompt = f"""As the Axiom, design an experiment.

Objective: {objective}
Constraints: {constraints if constraints else 'No specific constraints'}
Available Resources: {resources if resources else 'Standard resources assumed'}
Description: {task.description}
Context: {task.context}

Design an experiment including:
1. Research question and hypotheses
2. Variables (independent, dependent, controlled)
3. Methodology and approach
4. Sample size and selection
5. Data collection methods
6. Analysis plan
7. Expected outcomes
8. Potential limitations and mitigations
9. Timeline and milestones"""

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
                "research_type": "experiment_design",
                "objective": objective,
                "design": response,
            },
        )

    async def _handle_data_analysis(self, task: Task) -> TaskResult:
        """Analyze data and provide insights."""
        data_description = task.context.get("data_description", "")
        analysis_type = task.context.get("analysis_type", "exploratory")
        questions = task.context.get("questions", [])

        prompt = f"""As the Axiom, analyze the data.

Data Description: {data_description}
Analysis Type: {analysis_type}
Research Questions: {questions if questions else 'Identify key patterns and insights'}
Description: {task.description}
Context: {task.context}

Provide data analysis including:
1. Data overview and quality assessment
2. Descriptive statistics
3. Key patterns and trends
4. Statistical analysis results
5. Visualizations recommendations
6. Insights and interpretations
7. Limitations and caveats
8. Recommendations for further analysis"""

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

    async def _handle_hypothesis_testing(self, task: Task) -> TaskResult:
        """Test a hypothesis."""
        hypothesis = task.context.get("hypothesis", task.description)
        evidence = task.context.get("evidence", [])

        prompt = f"""As the Axiom, evaluate this hypothesis.

Hypothesis: {hypothesis}
Available Evidence: {evidence if evidence else 'Analyze based on general knowledge'}
Description: {task.description}
Context: {task.context}

Evaluate the hypothesis including:
1. Hypothesis statement and operationalization
2. Evidence supporting the hypothesis
3. Evidence against the hypothesis
4. Alternative explanations
5. Confidence level assessment
6. Recommended tests or validations
7. Conclusions and implications"""

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
                "research_type": "hypothesis_testing",
                "hypothesis": hypothesis,
                "evaluation": response,
            },
        )

    async def _handle_root_cause_analysis(self, task: Task) -> TaskResult:
        """Perform root cause analysis."""
        problem = task.context.get("problem", task.description)
        symptoms = task.context.get("symptoms", [])

        prompt = f"""As the Axiom, perform root cause analysis.

Problem: {problem}
Observed Symptoms: {symptoms if symptoms else 'Describe observed symptoms'}
Description: {task.description}
Context: {task.context}

Perform root cause analysis including:
1. Problem definition and scope
2. Data collection and timeline
3. Cause-and-effect analysis (fishbone diagram approach)
4. 5 Whys analysis
5. Contributing factors
6. Root cause identification
7. Verification of root cause
8. Recommended corrective actions
9. Preventive measures"""

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

    async def _handle_feasibility_study(self, task: Task) -> TaskResult:
        """Conduct a feasibility study."""
        proposal = task.context.get("proposal", task.description)
        criteria = task.context.get("criteria", [])

        prompt = f"""As the Axiom, conduct a feasibility study.

Proposal: {proposal}
Evaluation Criteria: {criteria if criteria else 'Standard feasibility criteria'}
Description: {task.description}
Context: {task.context}

Conduct feasibility analysis including:
1. Agent summary
2. Technical feasibility
3. Economic/financial feasibility
4. Operational feasibility
5. Schedule feasibility
6. Legal and regulatory considerations
7. Risk assessment
8. Alternatives analysis
9. Recommendations"""

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
                "study": response,
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

        prompt = f"""As the Axiom (Axiom) specializing in research and analysis,
handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough research-focused response."""

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

    def add_finding(self, key: str, finding: Any) -> None:
        """Add a research finding."""
        self._findings_database[key] = finding

    def get_research_status(self) -> Dict[str, Any]:
        """Get current research status."""
        return {
            "active_projects": len(self._research_projects),
            "findings": len(self._findings_database),
            "hypotheses": len(self._hypotheses),
            "capabilities": self.capabilities,
        }
