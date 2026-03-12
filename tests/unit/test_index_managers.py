"""
Unit tests for Index (Index) managers and specialists.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.index_agent import (
    Index,
    DataGovernanceManager,
    AnalyticsManager,
    KnowledgeManager,
    DataSteward,
    SchemaAnalyst,
    QualityAnalyst,
    KnowledgeCurator,
)
from ag3ntwerk.core.base import Task, TaskStatus


class TestDataGovernanceManager:
    """Test DataGovernanceManager functionality."""

    @pytest.fixture
    def dgm(self, mock_llm_provider):
        return DataGovernanceManager(llm_provider=mock_llm_provider)

    def test_dgm_initialization(self, dgm):
        assert dgm.code == "CDGM"
        assert dgm.name == "Data Governance Manager"
        assert "data_governance" in dgm.capabilities
        assert "data_quality_check" in dgm.capabilities

    def test_dgm_can_handle_governance(self, dgm):
        task = Task(description="Assess data governance", task_type="data_governance")
        assert dgm.can_handle(task) is True

    def test_dgm_can_handle_quality(self, dgm):
        task = Task(description="Check data quality", task_type="data_quality_check")
        assert dgm.can_handle(task) is True

    def test_dgm_cannot_handle_analytics(self, dgm):
        task = Task(description="Analyze data", task_type="data_analysis")
        assert dgm.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_dgm_execute(self, dgm, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Data governance analysis complete")
        )

        task = Task(
            description="Assess data governance for customer data",
            task_type="data_governance",
            context={"scope": "customer_database"},
        )

        result = await dgm.execute(task)
        assert result.success is True


class TestAnalyticsManager:
    """Test AnalyticsManager functionality."""

    @pytest.fixture
    def am(self, mock_llm_provider):
        return AnalyticsManager(llm_provider=mock_llm_provider)

    def test_am_initialization(self, am):
        assert am.code == "AM"
        assert am.name == "Analytics Manager"
        assert "data_analysis" in am.capabilities
        assert "analytics_design" in am.capabilities

    def test_am_can_handle_analysis(self, am):
        task = Task(description="Analyze data", task_type="data_analysis")
        assert am.can_handle(task) is True

    def test_am_cannot_handle_governance(self, am):
        task = Task(description="Governance review", task_type="data_governance")
        assert am.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_am_execute(self, am, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Analytics design complete")
        )

        task = Task(
            description="Design analytics solution",
            task_type="analytics_design",
            context={"objective": "customer_insights"},
        )

        result = await am.execute(task)
        assert result.success is True


class TestKnowledgeManager:
    """Test KnowledgeManager functionality."""

    @pytest.fixture
    def km(self, mock_llm_provider):
        return KnowledgeManager(llm_provider=mock_llm_provider)

    def test_km_initialization(self, km):
        assert km.code == "CKM"
        assert km.name == "Knowledge Manager"
        assert "documentation" in km.capabilities
        assert "knowledge_retrieval" in km.capabilities

    def test_km_can_handle_documentation(self, km):
        task = Task(description="Create docs", task_type="documentation")
        assert km.can_handle(task) is True

    def test_km_cannot_handle_governance(self, km):
        task = Task(description="Governance review", task_type="data_governance")
        assert km.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_km_execute(self, km, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Documentation created")
        )

        task = Task(
            description="Create API documentation",
            task_type="documentation",
            context={"subject": "REST API"},
        )

        result = await km.execute(task)
        assert result.success is True


class TestDataSteward:
    """Test DataSteward specialist."""

    @pytest.fixture
    def ds(self, mock_llm_provider):
        return DataSteward(llm_provider=mock_llm_provider)

    def test_ds_initialization(self, ds):
        assert ds.code == "DS"
        assert ds.name == "Data Steward"
        assert "data_governance" in ds.capabilities

    def test_ds_can_handle(self, ds):
        task = Task(description="Governance task", task_type="data_governance")
        assert ds.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_ds_execute(self, ds, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Governance task complete")
        )

        task = Task(
            description="Review data ownership",
            task_type="data_governance",
        )

        result = await ds.execute(task)
        assert result.success is True


class TestSchemaAnalyst:
    """Test SchemaAnalyst specialist."""

    @pytest.fixture
    def sa(self, mock_llm_provider):
        return SchemaAnalyst(llm_provider=mock_llm_provider)

    def test_sa_initialization(self, sa):
        assert sa.code == "SA"
        assert sa.name == "Schema Analyst"
        assert "schema_validation" in sa.capabilities

    def test_sa_can_handle(self, sa):
        task = Task(description="Validate schema", task_type="schema_validation")
        assert sa.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_sa_execute(self, sa, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Schema validation complete")
        )

        task = Task(
            description="Validate customer schema",
            task_type="schema_validation",
        )

        result = await sa.execute(task)
        assert result.success is True


class TestQualityAnalyst:
    """Test QualityAnalyst specialist."""

    @pytest.fixture
    def qa(self, mock_llm_provider):
        return QualityAnalyst(llm_provider=mock_llm_provider)

    def test_qa_initialization(self, qa):
        assert qa.code == "QA"
        assert qa.name == "Quality Analyst"
        assert "data_quality_check" in qa.capabilities

    def test_qa_can_handle(self, qa):
        task = Task(description="Check quality", task_type="data_quality_check")
        assert qa.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_qa_execute(self, qa, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Quality check complete")
        )

        task = Task(
            description="Check data quality",
            task_type="data_quality_check",
        )

        result = await qa.execute(task)
        assert result.success is True


class TestKnowledgeCurator:
    """Test KnowledgeCurator specialist."""

    @pytest.fixture
    def kc(self, mock_llm_provider):
        return KnowledgeCurator(llm_provider=mock_llm_provider)

    def test_kc_initialization(self, kc):
        assert kc.code == "KC"
        assert kc.name == "Knowledge Curator"
        assert "documentation" in kc.capabilities

    def test_kc_can_handle(self, kc):
        task = Task(description="Create docs", task_type="documentation")
        assert kc.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_kc_execute(self, kc, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Documentation created")
        )

        task = Task(
            description="Create documentation",
            task_type="documentation",
        )

        result = await kc.execute(task)
        assert result.success is True


class TestCDOManagerHierarchy:
    """Test Index manager and specialist hierarchy."""

    @pytest.fixture
    def cdo(self, mock_llm_provider):
        return Index(llm_provider=mock_llm_provider)

    def test_cdo_has_managers(self, cdo):
        """Test that Index has registered managers."""
        assert len(cdo.subordinates) == 3

        manager_codes = [m.code for m in cdo.subordinates]
        assert "CDGM" in manager_codes
        assert "AM" in manager_codes
        assert "CKM" in manager_codes

    def test_dgm_has_specialists(self, cdo):
        """Test that DataGovernanceManager has specialists."""
        dgm = cdo.get_subordinate("CDGM")
        assert dgm is not None

        specialist_codes = [s.code for s in dgm.subordinates]
        assert "DS" in specialist_codes
        assert "SA" in specialist_codes
        assert "QA" in specialist_codes

    def test_km_has_specialists(self, cdo):
        """Test that KnowledgeManager has specialists."""
        km = cdo.get_subordinate("CKM")
        assert km is not None

        specialist_codes = [s.code for s in km.subordinates]
        assert "KC" in specialist_codes

    @pytest.mark.asyncio
    async def test_cdo_delegate_to_manager(self, cdo, mock_llm_provider):
        """Test delegation from Index to manager."""
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(content="Task delegated"))

        task = Task(
            description="Data governance review",
            task_type="data_governance",
        )

        result = await cdo.delegate(task, "CDGM")
        assert result.success is True
