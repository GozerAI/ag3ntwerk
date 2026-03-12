"""
Unit tests for Forge (Forge) agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.forge import Forge, Forge
from ag3ntwerk.agents.forge.managers import ArchitectureManager, DevOpsManager, CodeQualityManager
from ag3ntwerk.core.base import Task, TaskStatus


class TestCTOAgent:
    """Tests for Forge agent."""

    def test_cto_creation(self):
        """Test Forge agent creation."""
        cto = Forge()

        assert cto.code == "Forge"
        assert cto.name == "Forge"
        assert cto.codename == "Forge"
        assert cto.domain == "Development, Engineering, Architecture"

    def test_forge_alias(self):
        """Test Forge is an alias for Forge."""
        forge = Forge()

        assert forge.code == "Forge"
        assert forge.codename == "Forge"

    def test_cto_capabilities(self):
        """Test Forge has expected capabilities."""
        cto = Forge()

        # Check for core capabilities from DEVELOPMENT_CAPABILITIES
        expected_capabilities = [
            "code_review",
            "code_generation",
            "architecture",
            "debugging",
            "deployment",
            "testing",
            "documentation",
            "security_review",
            "technical_debt",
            "infrastructure",
            "ci_cd",
            "api_design",
        ]

        for cap in expected_capabilities:
            assert cap in cto.capabilities, f"Missing capability: {cap}"

    def test_can_handle_technical_tasks(self):
        """Test Forge can handle technical tasks."""
        cto = Forge()

        technical_tasks = [
            "code_review",
            "architecture",
            "debugging",
            "security_review",
            "deployment",
            "testing",
        ]

        for task_type in technical_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert cto.can_handle(task), f"Forge should handle {task_type}"

    def test_cannot_handle_non_technical_tasks(self):
        """Test Forge doesn't handle non-technical tasks."""
        cto = Forge()

        non_technical_tasks = [
            "cost_analysis",
            "campaign_creation",
            "hr_policy",
            "brand_strategy",
        ]

        for task_type in non_technical_tasks:
            task = Task(
                description=f"Test {task_type}",
                task_type=task_type,
            )
            assert not cto.can_handle(task), f"Forge should not handle {task_type}"


class TestCTOExecute:
    """Tests for Forge task execution."""

    @pytest.mark.asyncio
    async def test_execute_code_review(self):
        """Test executing code review task."""
        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Code review complete"
        mock_provider.generate = AsyncMock(return_value=mock_response)

        cto = Forge(llm_provider=mock_provider)

        task = Task(
            description="Review authentication module",
            task_type="code_review",
            context={
                "code": "def authenticate(user): pass",
                "file": "auth.py",
            },
        )

        result = await cto.execute(task)
        # Forge routes code_review to CodeQualityManager
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_architecture(self):
        """Test executing architecture design task."""
        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Architecture design complete"
        mock_provider.generate = AsyncMock(return_value=mock_response)

        cto = Forge(llm_provider=mock_provider)

        task = Task(
            description="Design microservices architecture",
            task_type="architecture",
            context={
                "requirements": "High availability, scalable",
            },
        )

        result = await cto.execute(task)
        # Forge routes architecture to ArchitectureManager
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_without_provider(self):
        """Test execution without LLM provider falls back gracefully."""
        cto = Forge(llm_provider=None)

        task = Task(
            description="Unknown technical task",
            task_type="unknown_type",
        )

        result = await cto.execute(task)
        # Without provider, execution should fail gracefully
        assert result is not None


class TestArchitectureManager:
    """Tests for ArchitectureManager."""

    def test_manager_creation(self):
        """Test architecture manager creation."""
        manager = ArchitectureManager()

        assert manager.code == "AM"
        assert manager.name == "Architecture Manager"
        assert manager.domain == "System Design, Architecture, Technology Selection"

    def test_can_handle_architecture_tasks(self):
        """Test manager handles architecture tasks."""
        manager = ArchitectureManager()

        tasks = [
            "architecture",
            "system_design",
            "api_design",
            "database_design",
            "tech_selection",
            "scalability_planning",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"

    @pytest.mark.asyncio
    async def test_execute_system_design(self):
        """Test system design execution."""
        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "System design complete"
        mock_provider.generate = AsyncMock(return_value=mock_response)

        manager = ArchitectureManager(llm_provider=mock_provider)

        task = Task(
            description="Design event-driven system",
            task_type="system_design",
            context={"requirements": "Real-time processing"},
        )

        result = await manager.execute(task)
        assert result.success is True


class TestDevOpsManager:
    """Tests for DevOpsManager."""

    def test_manager_creation(self):
        """Test devops manager creation."""
        manager = DevOpsManager()

        assert manager.code == "DOM"
        assert manager.name == "DevOps Manager"
        assert manager.domain == "CI/CD, Deployment, Infrastructure, Monitoring"

    def test_can_handle_devops_tasks(self):
        """Test manager handles devops tasks."""
        manager = DevOpsManager()

        tasks = [
            "deployment",
            "ci_cd",
            "infrastructure",
            "monitoring",
            "containerization",
            "orchestration",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"

    @pytest.mark.asyncio
    async def test_execute_ci_cd(self):
        """Test CI/CD task execution."""
        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "CI/CD configured"
        mock_provider.generate = AsyncMock(return_value=mock_response)

        manager = DevOpsManager(llm_provider=mock_provider)

        task = Task(
            description="Setup CI/CD pipeline",
            task_type="ci_cd",
            context={"platform": "GitHub Actions"},
        )

        result = await manager.execute(task)
        assert result.success is True


class TestCodeQualityManager:
    """Tests for CodeQualityManager."""

    def test_manager_creation(self):
        """Test code quality manager creation."""
        manager = CodeQualityManager()

        assert manager.code == "CQM"
        assert manager.name == "Code Quality Manager"
        assert manager.domain == "Code Review, Quality Standards, Best Practices"

    def test_can_handle_quality_tasks(self):
        """Test manager handles quality tasks."""
        manager = CodeQualityManager()

        tasks = [
            "code_review",
            "refactoring",
            "code_standards",
            "best_practices",
            "code_analysis",
            "technical_debt",
        ]

        for task_type in tasks:
            task = Task(description="Test", task_type=task_type)
            assert manager.can_handle(task), f"Should handle {task_type}"

    @pytest.mark.asyncio
    async def test_execute_code_review(self):
        """Test code review execution."""
        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Code review complete"
        mock_provider.generate = AsyncMock(return_value=mock_response)

        manager = CodeQualityManager(llm_provider=mock_provider)

        task = Task(
            description="Review authentication code",
            task_type="code_review",
            context={"code": "def login(): pass", "file": "auth.py"},
        )

        result = await manager.execute(task)
        assert result.success is True
