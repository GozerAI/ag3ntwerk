"""
Unit tests for Index (Index) agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ag3ntwerk.agents.index_agent import Index, Index
from ag3ntwerk.agents.index_agent.models import (
    Dataset,
    Schema,
    SchemaField,
    DataQualityRule,
    QualityCheckResult,
    LineageEdge,
    DataCatalogEntry,
    KnowledgeArticle,
    DataQualityLevel,
    DataSensitivity,
    SchemaStatus,
    LineageType,
)
from ag3ntwerk.core.base import Task, TaskStatus


class TestCDOModels:
    """Test Index data models."""

    def test_schema_field_creation(self):
        field = SchemaField(
            name="user_id",
            data_type="integer",
            description="Unique user identifier",
            required=True,
        )
        assert field.name == "user_id"
        assert field.data_type == "integer"
        assert field.required is True
        assert field.nullable is False

    def test_schema_creation(self):
        schema = Schema(
            id="user_schema_v1",
            name="User Schema",
            version="1.0.0",
            description="Schema for user data",
        )
        assert schema.id == "user_schema_v1"
        assert schema.status == SchemaStatus.DRAFT
        assert len(schema.fields) == 0

    def test_schema_add_field(self):
        schema = Schema(id="test", name="Test Schema")
        field = SchemaField(name="email", data_type="string")
        schema.add_field(field)

        assert len(schema.fields) == 1
        assert schema.get_field("email") == field

    def test_schema_validate_data_success(self):
        schema = Schema(id="test", name="Test")
        schema.add_field(SchemaField(name="name", data_type="string", required=True))
        schema.add_field(SchemaField(name="age", data_type="integer", required=False))

        errors = schema.validate_data({"name": "John", "age": 30})
        assert len(errors) == 0

    def test_schema_validate_data_missing_required(self):
        schema = Schema(id="test", name="Test")
        schema.add_field(SchemaField(name="name", data_type="string", required=True))

        errors = schema.validate_data({})
        assert len(errors) == 1
        assert "Missing required field: name" in errors[0]

    def test_schema_validate_data_unknown_field(self):
        schema = Schema(id="test", name="Test")
        schema.add_field(SchemaField(name="name", data_type="string"))

        errors = schema.validate_data({"name": "John", "extra": "field"})
        assert any("Unknown field: extra" in e for e in errors)

    def test_dataset_creation(self):
        dataset = Dataset(
            id="customers_v1",
            name="Customer Data",
            description="All customer records",
            quality_level=DataQualityLevel.HIGH,
            sensitivity=DataSensitivity.CONFIDENTIAL,
        )
        assert dataset.id == "customers_v1"
        assert dataset.quality_level == DataQualityLevel.HIGH
        assert dataset.sensitivity == DataSensitivity.CONFIDENTIAL

    def test_quality_check_result_pass_rate(self):
        result = QualityCheckResult(
            rule_id="rule1",
            rule_name="Null Check",
            passed=False,
            severity="warning",
            affected_records=10,
            total_records=100,
        )
        assert result.pass_rate == 90.0

    def test_quality_check_result_zero_records(self):
        result = QualityCheckResult(
            rule_id="rule1",
            rule_name="Null Check",
            passed=True,
            severity="info",
            affected_records=0,
            total_records=0,
        )
        assert result.pass_rate == 100.0

    def test_lineage_edge_creation(self):
        edge = LineageEdge(
            id="edge1",
            source_id="raw_data",
            target_id="cleaned_data",
            lineage_type=LineageType.TRANSFORMED_FROM,
            transformation="Removed nulls and normalized",
        )
        assert edge.lineage_type == LineageType.TRANSFORMED_FROM
        assert edge.source_id == "raw_data"

    def test_knowledge_article_creation(self):
        article = KnowledgeArticle(
            id="kb001",
            title="Getting Started Guide",
            content="This is the content...",
            category="onboarding",
            tags=["getting-started", "beginner"],
        )
        assert article.id == "kb001"
        assert "getting-started" in article.tags
        assert article.status == "draft"


class TestCDOAgent:
    """Test Index agent functionality."""

    @pytest.fixture
    def cdo(self, mock_llm_provider):
        return Index(llm_provider=mock_llm_provider)

    def test_cdo_initialization(self, cdo):
        assert cdo.code == "Index"
        assert cdo.codename == "Index"
        assert cdo.name == "Index"

    def test_cdo_alias(self):
        assert Index == Index

    def test_cdo_capabilities(self, cdo):
        assert "data_governance" in cdo.capabilities
        assert "data_quality_check" in cdo.capabilities
        assert "schema_validation" in cdo.capabilities
        assert "documentation" in cdo.capabilities
        assert "knowledge_retrieval" in cdo.capabilities

    def test_can_handle_data_governance(self, cdo):
        task = Task(description="Review data governance", task_type="data_governance")
        assert cdo.can_handle(task) is True

    def test_can_handle_knowledge(self, cdo):
        task = Task(description="Create docs", task_type="documentation")
        assert cdo.can_handle(task) is True

    def test_cannot_handle_security(self, cdo):
        task = Task(description="Scan for vulnerabilities", task_type="security_scan")
        assert cdo.can_handle(task) is False

    def test_register_dataset(self, cdo):
        dataset = Dataset(id="ds1", name="Test Dataset")
        result = cdo.register_dataset(dataset)

        assert result == "ds1"
        assert cdo.get_dataset("ds1") is not None
        assert cdo.get_dataset("ds1").name == "Test Dataset"

    def test_register_schema(self, cdo):
        schema = Schema(id="sch1", name="Test Schema")
        result = cdo.register_schema(schema)

        assert result == "sch1"
        assert cdo.get_schema("sch1") is not None

    def test_search_catalog(self, cdo):
        dataset = Dataset(
            id="customers",
            name="Customer Data",
            description="All customer records",
            tags=["pii", "crm"],
        )
        cdo.register_dataset(dataset)

        results = cdo.search_catalog("customer")
        assert len(results) == 1

        results = cdo.search_catalog("pii")
        assert len(results) == 1

        results = cdo.search_catalog("nonexistent")
        assert len(results) == 0

    def test_add_lineage(self, cdo):
        edge = LineageEdge(
            id="edge1",
            source_id="raw",
            target_id="processed",
            lineage_type=LineageType.DERIVED_FROM,
        )
        cdo.add_lineage(edge)

        lineage = cdo.get_lineage("processed", direction="upstream")
        assert len(lineage) == 1
        assert lineage[0].source_id == "raw"

    def test_add_knowledge_article(self, cdo):
        article = KnowledgeArticle(id="kb1", title="Test Article", content="Content")
        result = cdo.add_knowledge_article(article)
        assert result == "kb1"

    def test_governance_status(self, cdo):
        dataset = Dataset(id="ds1", name="Dataset 1")
        schema = Schema(id="sch1", name="Schema 1")
        cdo.register_dataset(dataset)
        cdo.register_schema(schema)

        status = cdo.get_governance_status()

        assert status["datasets_registered"] == 1
        assert status["schemas_registered"] == 1
        assert "capabilities" in status

    @pytest.mark.asyncio
    async def test_execute_data_governance(self, cdo, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="Data governance analysis complete")
        )

        task = Task(
            description="Review customer data governance",
            task_type="data_governance",
            context={"governance_type": "data_access"},
        )

        result = await cdo.execute(task)

        assert result.success is True
        assert "analysis" in result.output

    @pytest.mark.asyncio
    async def test_execute_schema_validation_with_registered_schema(self, cdo):
        # Register a schema
        schema = Schema(id="user_v1", name="User Schema")
        schema.add_field(SchemaField(name="email", data_type="string", required=True))
        cdo.register_schema(schema)

        # Validate against it
        task = Task(
            description="Validate user data",
            task_type="schema_validation",
            context={
                "schema": "user_v1",
                "data": {"email": "test@example.com"},
            },
        )

        result = await cdo.execute(task)

        assert result.success is True
        assert result.output["valid"] is True

    @pytest.mark.asyncio
    async def test_execute_documentation(self, cdo, mock_llm_provider):
        mock_llm_provider.generate = AsyncMock(
            return_value=MagicMock(content="# Documentation\n\nGenerated docs...")
        )

        task = Task(
            description="Create API docs",
            task_type="documentation",
            context={"subject": "REST API", "format": "markdown"},
        )

        result = await cdo.execute(task)

        assert result.success is True
        assert result.output["doc_type"] == "documentation"

    @pytest.mark.asyncio
    async def test_execute_no_llm_provider(self):
        cdo = Index()  # No LLM provider

        task = Task(
            description="Analyze data",
            task_type="unknown_task",
        )

        result = await cdo.execute(task)

        assert result.success is False
        assert "No LLM provider" in result.error
