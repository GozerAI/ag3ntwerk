"""
Unit tests for Axiom (Axiom) agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.axiom import Axiom, Axiom
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
from ag3ntwerk.core.base import Task, TaskStatus


class TestCROAgent:
    """Tests for Axiom agent."""

    def test_cro_creation(self):
        """Test Axiom agent creation."""
        cro = Axiom()

        assert cro.code == "Axiom"
        assert cro.name == "Axiom"
        assert cro.codename == "Axiom"
        assert cro.domain == "Research, Analysis, Investigation"

    def test_axiom_alias(self):
        """Test Axiom is an alias for Axiom."""
        axiom = Axiom()

        assert axiom.code == "Axiom"
        assert axiom.codename == "Axiom"

    def test_cro_capabilities(self):
        """Test Axiom has expected capabilities."""
        cro = Axiom()

        expected_capabilities = [
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

        for cap in expected_capabilities:
            assert cap in cro.capabilities, f"Missing capability: {cap}"

    def test_can_handle_research_tasks(self):
        """Test Axiom can handle research tasks."""
        cro = Axiom()

        research_tasks = [
            "deep_research",
            "literature_review",
            "experiment_design",
            "data_analysis",
            "hypothesis_testing",
            "root_cause_analysis",
            "feasibility_study",
            "benchmarking",
        ]

        for task_type in research_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert cro.can_handle(task), f"Axiom should handle {task_type}"

    def test_cannot_handle_non_research_tasks(self):
        """Test Axiom doesn't handle non-research tasks."""
        cro = Axiom()

        non_research_tasks = [
            "code_review",
            "campaign_creation",
            "cost_analysis",
            "security_scan",
        ]

        for task_type in non_research_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert not cro.can_handle(task), f"Axiom should not handle {task_type}"

    def test_add_finding(self):
        """Test adding research findings."""
        cro = Axiom()

        cro.add_finding("key-1", {"result": "significant correlation found"})
        cro.add_finding("key-2", {"result": "no effect observed"})

        assert len(cro._findings_database) == 2
        assert cro._findings_database["key-1"]["result"] == "significant correlation found"

    def test_get_research_status(self):
        """Test getting research status."""
        cro = Axiom()

        cro.add_finding("f1", {"result": "finding 1"})
        cro._hypotheses.append({"hypothesis": "H1", "status": "testing"})

        status = cro.get_research_status()

        assert status["active_projects"] == 0
        assert status["findings"] == 1
        assert status["hypotheses"] == 1
        assert "capabilities" in status

    def test_subordinate_managers_registered(self):
        """Test that managers are registered as subordinates."""
        cro = Axiom()

        subordinate_codes = list(cro._subordinates.keys())

        assert "RPM" in subordinate_codes  # ResearchProjectManager
        assert "EXM" in subordinate_codes  # ExperimentationManager
        assert "DAM" in subordinate_codes  # DataAnalysisManager
        assert "ASM" in subordinate_codes  # AssessmentManager


class TestCROExecute:
    """Tests for Axiom task execution."""

    @pytest.mark.asyncio
    async def test_execute_deep_research(self):
        """Test executing deep research task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Research findings complete")

        cro = Axiom(llm_provider=mock_provider)

        task = Task(
            description="Research state-of-the-art in LLM fine-tuning",
            task_type="deep_research",
            context={
                "topic": "LLM fine-tuning techniques",
                "depth": "comprehensive",
                "focus_areas": ["LoRA", "QLoRA", "RLHF"],
            },
        )

        result = await cro.execute(task)

        assert result.success is True
        assert "research_type" in result.output
        assert result.output["research_type"] == "deep_research"
        assert result.output["topic"] == "LLM fine-tuning techniques"

    @pytest.mark.asyncio
    async def test_execute_literature_review(self):
        """Test executing literature review task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Literature review complete")

        cro = Axiom(llm_provider=mock_provider)

        task = Task(
            description="Review recent papers on transformer architectures",
            task_type="literature_review",
            context={
                "field": "machine learning",
                "timeframe": "2024-2026",
                "scope": "comprehensive",
            },
        )

        result = await cro.execute(task)

        assert result.success is True
        assert "research_type" in result.output
        assert result.output["research_type"] == "literature_review"
        assert result.output["field"] == "machine learning"

    @pytest.mark.asyncio
    async def test_execute_experiment_design(self):
        """Test executing experiment design task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Experiment designed")

        cro = Axiom(llm_provider=mock_provider)

        task = Task(
            description="Design A/B test for new recommendation algorithm",
            task_type="experiment_design",
            context={
                "objective": "Compare recommendation accuracy",
                "constraints": ["limited user base", "2 week timeline"],
                "resources": ["test environment", "analytics pipeline"],
            },
        )

        result = await cro.execute(task)

        assert result.success is True
        assert "research_type" in result.output
        assert result.output["research_type"] == "experiment_design"

    @pytest.mark.asyncio
    async def test_execute_data_analysis(self):
        """Test executing data analysis task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Analysis complete")

        cro = Axiom(llm_provider=mock_provider)

        task = Task(
            description="Analyze user engagement metrics",
            task_type="data_analysis",
            context={
                "data_description": "User engagement data Q1 2026",
                "analysis_type": "exploratory",
                "questions": ["What drives retention?", "Key churn indicators?"],
            },
        )

        result = await cro.execute(task)

        assert result.success is True
        assert "analysis_type" in result.output
        assert result.output["analysis_type"] == "exploratory"

    @pytest.mark.asyncio
    async def test_execute_hypothesis_testing(self):
        """Test executing hypothesis testing task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Hypothesis evaluated")

        cro = Axiom(llm_provider=mock_provider)

        task = Task(
            description="Test hypothesis about feature adoption",
            task_type="hypothesis_testing",
            context={
                "hypothesis": "Users who complete onboarding have 2x higher retention",
                "evidence": ["survey data", "product analytics"],
            },
        )

        result = await cro.execute(task)

        assert result.success is True
        assert "research_type" in result.output
        assert result.output["research_type"] == "hypothesis_testing"

    @pytest.mark.asyncio
    async def test_execute_root_cause_analysis(self):
        """Test executing root cause analysis task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Root cause identified")

        cro = Axiom(llm_provider=mock_provider)

        task = Task(
            description="Investigate sudden increase in API latency",
            task_type="root_cause_analysis",
            context={
                "problem": "API latency increased 300% in last 24 hours",
                "symptoms": ["timeout errors", "slow response times", "queue buildup"],
            },
        )

        result = await cro.execute(task)

        assert result.success is True
        assert "analysis_type" in result.output
        assert result.output["analysis_type"] == "root_cause"

    @pytest.mark.asyncio
    async def test_execute_feasibility_study(self):
        """Test executing feasibility study task."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Feasibility assessed")

        cro = Axiom(llm_provider=mock_provider)

        task = Task(
            description="Evaluate feasibility of real-time ML inference",
            task_type="feasibility_study",
            context={
                "proposal": "Deploy ML models with sub-100ms inference",
                "criteria": ["technical", "economic", "operational"],
            },
        )

        result = await cro.execute(task)

        assert result.success is True
        assert "study_type" in result.output
        assert result.output["study_type"] == "feasibility"

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self):
        """Test handling of LLM errors during execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=Exception("LLM Error"))

        cro = Axiom(llm_provider=mock_provider)

        task = Task(
            description="Research topic",
            task_type="deep_research",
            context={"topic": "AI safety"},
        )

        result = await cro.execute(task)

        assert result.success is False
        assert "failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_without_provider(self):
        """Test execution without LLM provider."""
        cro = Axiom(llm_provider=None)

        task = Task(
            description="Unknown research task",
            task_type="unknown_type",
        )

        result = await cro.execute(task)

        assert result.success is False
        assert "No LLM provider" in result.error

    @pytest.mark.asyncio
    async def test_execute_fallback_to_llm_for_unhandled_type(self):
        """Test that tasks with capabilities but no handler fall back to LLM."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="LLM handled")

        cro = Axiom(llm_provider=mock_provider)

        task = Task(
            description="Analyze technology trends",
            task_type="technology_assessment",
        )

        result = await cro.execute(task)

        # technology_assessment is a capability but has no dedicated handler,
        # so it falls through to _handle_with_llm
        assert result.success is True


class TestResearchProjectManager:
    """Tests for ResearchProjectManager."""

    def test_manager_creation(self):
        """Test research project manager creation."""
        manager = ResearchProjectManager()

        assert manager.code == "RPM"
        assert manager.name == "Research Project Manager"
        assert manager.domain == "Research Project Management"

    def test_can_handle_research_tasks(self):
        """Test manager handles research project tasks."""
        manager = ResearchProjectManager()

        tasks = [
            "deep_research",
            "literature_review",
            "research_planning",
            "meta_analysis",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"

    @pytest.mark.asyncio
    async def test_execute_deep_research(self):
        """Test deep research execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Research complete")

        manager = ResearchProjectManager(llm_provider=mock_provider)

        task = Task(
            description="Research distributed systems",
            task_type="deep_research",
            context={"topic": "distributed systems", "depth": "comprehensive"},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["research_type"] == "deep_research"

    @pytest.mark.asyncio
    async def test_execute_literature_review(self):
        """Test literature review execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Review complete")

        manager = ResearchProjectManager(llm_provider=mock_provider)

        task = Task(
            description="Review ML papers",
            task_type="literature_review",
            context={"field": "machine learning", "timeframe": "2024-2026"},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["research_type"] == "literature_review"


class TestExperimentationManager:
    """Tests for ExperimentationManager."""

    def test_manager_creation(self):
        """Test experimentation manager creation."""
        manager = ExperimentationManager()

        assert manager.code == "EXM"
        assert manager.name == "Experimentation Manager"
        assert manager.domain == "Experimental Research"

    def test_can_handle_experiment_tasks(self):
        """Test manager handles experiment-related tasks."""
        manager = ExperimentationManager()

        tasks = [
            "experiment_design",
            "hypothesis_testing",
            "methodology_review",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"

    @pytest.mark.asyncio
    async def test_execute_experiment_design(self):
        """Test experiment design execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Experiment designed")

        manager = ExperimentationManager(llm_provider=mock_provider)

        task = Task(
            description="Design user retention experiment",
            task_type="experiment_design",
            context={"objective": "Measure impact of new onboarding flow"},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["research_type"] == "experiment_design"


class TestDataAnalysisManager:
    """Tests for DataAnalysisManager."""

    def test_manager_creation(self):
        """Test data analysis manager creation."""
        manager = DataAnalysisManager()

        assert manager.code == "DAM"
        assert manager.name == "Data Analysis Manager"
        assert manager.domain == "Data Analysis"

    def test_can_handle_analysis_tasks(self):
        """Test manager handles analysis-related tasks."""
        manager = DataAnalysisManager()

        tasks = [
            "data_analysis",
            "statistical_analysis",
            "trend_research",
            "root_cause_analysis",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"

    @pytest.mark.asyncio
    async def test_execute_data_analysis(self):
        """Test data analysis execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Analysis results")

        manager = DataAnalysisManager(llm_provider=mock_provider)

        task = Task(
            description="Analyze sales data",
            task_type="data_analysis",
            context={
                "data_description": "Q1 sales data",
                "analysis_type": "descriptive",
            },
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["analysis_type"] == "descriptive"

    @pytest.mark.asyncio
    async def test_execute_root_cause_analysis(self):
        """Test root cause analysis execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Root cause found")

        manager = DataAnalysisManager(llm_provider=mock_provider)

        task = Task(
            description="Find root cause of high churn",
            task_type="root_cause_analysis",
            context={
                "problem": "Churn increased 50%",
                "symptoms": ["lower engagement", "more support tickets"],
            },
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["analysis_type"] == "root_cause"


class TestAssessmentManager:
    """Tests for AssessmentManager."""

    def test_manager_creation(self):
        """Test assessment manager creation."""
        manager = AssessmentManager()

        assert manager.code == "ASM"
        assert manager.name == "Assessment Manager"
        assert manager.domain == "Feasibility and Assessment"

    def test_can_handle_assessment_tasks(self):
        """Test manager handles assessment-related tasks."""
        manager = AssessmentManager()

        tasks = [
            "feasibility_study",
            "technology_assessment",
            "impact_analysis",
            "benchmarking",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"

    @pytest.mark.asyncio
    async def test_execute_feasibility_study(self):
        """Test feasibility study execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Feasibility assessed")

        manager = AssessmentManager(llm_provider=mock_provider)

        task = Task(
            description="Assess feasibility of microservices migration",
            task_type="feasibility_study",
            context={"proposal": "Migrate monolith to microservices"},
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["study_type"] == "feasibility"

    @pytest.mark.asyncio
    async def test_execute_benchmarking(self):
        """Test benchmarking execution."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="Benchmark complete")

        manager = AssessmentManager(llm_provider=mock_provider)

        task = Task(
            description="Benchmark API performance against competitors",
            task_type="benchmarking",
            context={
                "subject": "API response times",
                "comparisons": ["competitor-A", "competitor-B"],
            },
        )

        result = await manager.execute(task)

        assert result.success is True
        assert result.output["study_type"] == "benchmarking"
